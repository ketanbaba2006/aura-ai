import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.execution.code_runner import CodeRunner

code_runner = CodeRunner()

router = APIRouter(prefix="/execution", tags=["Execution"])

class ExecutionRequest(BaseModel):
    lang: str
    code: str

@router.post("/run")
async def run_code(req: ExecutionRequest):
    """
    Execute code and stream stdout/stderr line-by-line as Server-Sent Events (SSE).
    """
    async def sse_generator():
        try:
            async for chunk in code_runner.execute_code_stream(req.lang, req.code, timeout=30.0):
                # chunk is a dict with 'type' (log/error) and 'data' (string)
                yield f"data: {json.dumps(chunk)}\n\n"
            yield "data: {\"type\": \"done\", \"data\": \"\"}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")
