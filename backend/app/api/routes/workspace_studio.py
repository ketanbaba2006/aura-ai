"""
AURA Studio / Workspace API
Autonomous multi-agent development engine routes:
- /api/workspace/studio/templates
- /api/workspace/studio/stream
- /api/workspace/studio/state
- /api/workspace/studio/exec
- /api/workspace/studio/control
- /api/workspace/studio/export
- /api/workspace/studio/fs/*
"""

import json
import logging
from fastapi import APIRouter, HTTPException, Depends, Request, Header
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel

from app.execution.workspace_service import workspace_service
from app.execution.multi_agent_engine import multi_agent_engine, WorkspaceFilesystem, WorkflowPersistence
from app.core.auth_security import decode_access_token
from app.database.database import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspace/studio", tags=["Coding Studio"])

class StudioStreamRequest(BaseModel):
    prompt: str
    workspaceId: str | None = "default"
    agentRole: str | None = "Full-Stack Architect"
    provider: str | None = "auto"
    model: str | None = "auto"
    files: dict[str, str] | None = None
    logs: list | None = None
    media: str | None = None

class FileWriteRequest(BaseModel):
    path: str
    content: str

class FileRenameRequest(BaseModel):
    oldPath: str
    newPath: str

class MkdirRequest(BaseModel):
    path: str

class ControlRequest(BaseModel):
    action: str  # pause | resume | cancel

class ExecRequest(BaseModel):
    command: str

async def get_optional_user(request: Request, authorization: str = Header(None)) -> dict | None:
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if user_id:
            user = await db.db.users.find_one({"id": user_id})
            if user:
                return dict(user)
    except Exception:
        pass
    return None

# --- Multi-Agent Studio Stream with Real Filesystem Pipeline ---

@router.get("/templates")
async def get_studio_templates():
    return workspace_service.get_templates()

@router.post("/stream")
async def stream_studio(req: StudioStreamRequest, user: dict | None = Depends(get_optional_user)):
    user_id = user["id"] if user else "guest"
    workspace_id = f"{user_id}_{req.workspaceId or 'default'}"

    async def event_generator():
        try:
            async for event_payload in multi_agent_engine.execute_task_stream(
                workspace_id=workspace_id,
                user_prompt=req.prompt,
                requested_provider=req.provider or "auto",
                requested_model=req.model or "auto",
                current_files=req.files,
                runtime_logs=req.logs,
                custom_api_key=None,
                custom_base_url=None
            ):
                event_type = event_payload.get("type", "message")
                yield f"event: {event_type}\ndata: {json.dumps(event_payload)}\n\n"
        except Exception as e:
            logger.error(f"Studio stream execution failed: {e}", exc_info=True)
            yield f"event: error\ndata: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# --- Persistent Workspace Filesystem REST API ---

@router.get("/fs/files")
async def list_workspace_files(workspaceId: str = "default", user: dict | None = Depends(get_optional_user)):
    user_id = user["id"] if user else "guest"
    target_ws = f"{user_id}_{workspaceId}"
    fs = multi_agent_engine.get_filesystem(target_ws)
    return {"workspaceId": workspaceId, "files": fs.list_files()}

@router.get("/fs/read")
async def read_workspace_file(path: str, workspaceId: str = "default", user: dict | None = Depends(get_optional_user)):
    user_id = user["id"] if user else "guest"
    target_ws = f"{user_id}_{workspaceId}"
    fs = multi_agent_engine.get_filesystem(target_ws)
    try:
        content = fs.read_file(path)
        return {"path": path, "content": content}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except ValueError as ve:
        raise HTTPException(status_code=403, detail=str(ve))

@router.post("/fs/write")
async def write_workspace_file(req: FileWriteRequest, workspaceId: str = "default", user: dict | None = Depends(get_optional_user)):
    user_id = user["id"] if user else "guest"
    target_ws = f"{user_id}_{workspaceId}"
    fs = multi_agent_engine.get_filesystem(target_ws)
    try:
        stat = fs.write_file(req.path, req.content)
        return {"status": "ok", "file": stat}
    except ValueError as ve:
        raise HTTPException(status_code=403, detail=str(ve))

@router.delete("/fs/delete")
async def delete_workspace_file(path: str, workspaceId: str = "default", user: dict | None = Depends(get_optional_user)):
    user_id = user["id"] if user else "guest"
    target_ws = f"{user_id}_{workspaceId}"
    fs = multi_agent_engine.get_filesystem(target_ws)
    try:
        deleted = fs.delete_file(path)
        return {"path": path, "deleted": deleted}
    except ValueError as ve:
        raise HTTPException(status_code=403, detail=str(ve))

@router.get("/fs/bundle")
async def get_workspace_bundle(workspaceId: str = "default", user: dict | None = Depends(get_optional_user)):
    user_id = user["id"] if user else "guest"
    target_ws = f"{user_id}_{workspaceId}"
    fs = multi_agent_engine.get_filesystem(target_ws)
    return {"workspaceId": workspaceId, "files": fs.get_all_files_dict()}

@router.post("/fs/mkdir")
async def mkdir_workspace(req: MkdirRequest, workspaceId: str = "default", user: dict | None = Depends(get_optional_user)):
    user_id = user["id"] if user else "guest"
    fs = multi_agent_engine.get_filesystem(f"{user_id}_{workspaceId}")
    try:
        created = fs.mkdir(req.path)
        return {"status": "ok", "path": created}
    except ValueError as ve:
        raise HTTPException(status_code=403, detail=str(ve))

@router.post("/fs/rename")
async def rename_workspace_file(req: FileRenameRequest, workspaceId: str = "default", user: dict | None = Depends(get_optional_user)):
    user_id = user["id"] if user else "guest"
    fs = multi_agent_engine.get_filesystem(f"{user_id}_{workspaceId}")
    try:
        return fs.rename_file(req.oldPath, req.newPath)
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=404, detail=str(fnf))
    except ValueError as ve:
        raise HTTPException(status_code=403, detail=str(ve))

@router.get("/fs/search")
async def search_workspace_files(q: str, workspaceId: str = "default", user: dict | None = Depends(get_optional_user)):
    user_id = user["id"] if user else "guest"
    fs = multi_agent_engine.get_filesystem(f"{user_id}_{workspaceId}")
    return {"query": q, "matches": fs.search_files(q)}

@router.get("/state")
async def get_studio_workflow_state(workspaceId: str = "default", user: dict | None = Depends(get_optional_user)):
    user_id = user["id"] if user else "guest"
    fs = multi_agent_engine.get_filesystem(f"{user_id}_{workspaceId}")
    store = WorkflowPersistence(fs)
    loaded = store.load_state()
    return {
        "workspaceId": workspaceId,
        "files": fs.get_all_files_dict(),
        "state": loaded["state"],
        "events": loaded["events"]
    }

@router.post("/control")
async def control_studio_workflow(req: ControlRequest, workspaceId: str = "default", user: dict | None = Depends(get_optional_user)):
    user_id = user["id"] if user else "guest"
    target_ws = f"{user_id}_{workspaceId}"
    ctrl = multi_agent_engine.set_control(target_ws, req.action.lower())
    return {"workspaceId": workspaceId, "control": ctrl}

@router.post("/exec")
async def exec_studio_command(req: ExecRequest, workspaceId: str = "default", user: dict | None = Depends(get_optional_user)):
    user_id = user["id"] if user else "guest"
    fs = multi_agent_engine.get_filesystem(f"{user_id}_{workspaceId}")
    return multi_agent_engine.run_sandboxed_command(fs, req.command)

@router.get("/export")
async def export_studio_zip(workspaceId: str = "default", title: str = "aura-project", user: dict | None = Depends(get_optional_user)):
    user_id = user["id"] if user else "guest"
    fs = multi_agent_engine.get_filesystem(f"{user_id}_{workspaceId}")
    zip_bytes = fs.export_verified_zip(project_title=title)
    safe_title = "".join(c if c.isalnum() or c in ("-", "_") else "-" for c in title.lower()).strip("-") or "aura-project"
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{safe_title}.zip"'}
    )
