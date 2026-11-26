"""
AURA AI Notebook API Routes
Endpoints for the NotebookLM-style Research Workspace.
"""

import logging
from typing import Any
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.notebook.notebook_engine import notebook_engine
from app.notebook.generators import notebook_generators
from app.core.auth_security import get_current_user
import json

def _format_sse(event: str, data: Any) -> str:
    """Format data as Server-Sent Event."""
    if isinstance(data, dict):
        data = json.dumps(data)
    return f"event: {event}\ndata: {data}\n\n"

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notebook", tags=["Notebook Workspace"])

class NotebookChatRequest(BaseModel):
    query: str
    conversation_id: str
    doc_ids: list[str]

class NotebookGenerateRequest(BaseModel):
    task_type: str
    conversation_id: str
    doc_ids: list[str]

@router.post("/chat/stream")
async def stream_notebook_chat(
    req: NotebookChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """Stream a grounded RAG chat response strictly constrained to selected doc_ids."""
    
    async def sse_generator():
        try:
            async for event_type, data, metadata in notebook_engine.chat_stream(
                query=req.query,
                conversation_id=req.conversation_id,
                doc_ids=req.doc_ids
            ):
                payload = {"content": data}
                if metadata:
                    payload["metadata"] = metadata
                    
                yield _format_sse(event_type.value, payload)
        except Exception as e:
            logger.error(f"Notebook chat stream failed: {e}")
            yield _format_sse("error", {"content": str(e)})
            
    return StreamingResponse(sse_generator(), media_type="text/event-stream")

@router.post("/generate")
async def generate_notebook_document(
    req: NotebookGenerateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate specialized Notebook documents (Study Guide, FAQ, Mind Map, etc.)."""
    try:
        content = await notebook_generators.generate_document(
            task_type=req.task_type,
            conversation_id=req.conversation_id,
            doc_ids=req.doc_ids
        )
        return {"status": "success", "content": content}
    except Exception as e:
        logger.error(f"Notebook generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/source/{doc_id}/summary")
async def get_source_explorer_details(
    doc_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Fetch Summary, Key Concepts, and Quotes for a specific source document."""
    try:
        details = await notebook_generators.get_source_summary(doc_id)
        return details
    except Exception as e:
        logger.error(f"Notebook source details failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
