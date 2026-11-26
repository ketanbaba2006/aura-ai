"""
AURA AI Projects Router
Provides HTTP endpoints to create, list, switch, and reset active conversation project sessions.
"""

import logging
import shutil
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query, Header
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.memory.project_manager import project_manager, get_workspace_root

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["Projects"])

class CreateProjectRequest(BaseModel):
    name: str
    description: str | None = None
    conversation_id: str | None = None
    project_type: str | None = "web"
    design_choices: str | None = ""
    user_goals: str | None = ""

class SetActiveRequest(BaseModel):
    conversation_id: str
    project_id: str

class ResetActiveRequest(BaseModel):
    conversation_id: str

@router.get("")
async def list_projects():
    """Retrieve all projects registered in the workspace."""
    try:
        return await project_manager.list_projects()
    except Exception as e:
        logger.error(f"Failed to list projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("")
async def create_project(body: CreateProjectRequest):
    """Create a new project workspace and optionally map it to a conversation."""
    try:
        return await project_manager.create_project(
            name=body.name,
            description=body.description,
            conversation_id=body.conversation_id,
            project_type=body.project_type,
            design_choices=body.design_choices,
            user_goals=body.user_goals
        )
    except Exception as e:
        logger.error(f"Failed to create project: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/active")
async def get_active_project(conversation_id: str = Query(...)):
    """Fetch the currently active project context details for a conversation session."""
    try:
        project = await project_manager.get_active_project(conversation_id)
        if not project:
            return {"active": False, "project": None}
        return {"active": True, "project": project}
    except Exception as e:
        logger.error(f"Failed to query active project for conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/active")
async def set_active_project(body: SetActiveRequest):
    """Switch active project mapping for a conversation session."""
    try:
        await project_manager.set_active_project(body.conversation_id, body.project_id)
        project = await project_manager.get_project(body.project_id)
        return {"success": True, "project": project}
    except Exception as e:
        logger.error(f"Failed to link project {body.project_id} to conversation {body.conversation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reset")
async def reset_active_project(body: ResetActiveRequest):
    """Clear active project references for a conversation session."""
    try:
        await project_manager.reset_active_project(body.conversation_id)
        return {"success": True}
    except Exception as e:
        logger.error(f"Failed to clear active project on conversation {body.conversation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class ArchiveProjectRequest(BaseModel):
    project_id: str
    archived: bool = True

@router.post("/archive")
async def archive_project(body: ArchiveProjectRequest):
    """Archive or unarchive a project workspace."""
    try:
        await project_manager.archive_project(body.project_id, body.archived)
        return {"success": True}
    except Exception as e:
        logger.error(f"Failed to archive project {body.project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download")
async def download_project(slug: str = Query(...)):
    """ZIP and download the complete project workspace."""
    try:
        project_dir = get_workspace_root() / "user_files" / "Projects" / slug
        if not project_dir.exists() or not project_dir.is_dir():
            raise HTTPException(status_code=404, detail="Project not found")

        # Create ZIP in temporary/user_files dir
        zip_path_base = get_workspace_root() / "user_files" / f"{slug}_temp"
        shutil.make_archive(str(zip_path_base), 'zip', root_dir=str(project_dir))
        
        zip_file = Path(f"{zip_path_base}.zip")
        if not zip_file.exists():
            raise HTTPException(status_code=500, detail="Failed to compile ZIP archive")

        return FileResponse(
            path=str(zip_file),
            filename=f"{slug}.zip",
            media_type="application/zip"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
