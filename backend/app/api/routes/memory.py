"""
AURA AI Memory API
Memory retrieval and search endpoints.
"""

import logging

from fastapi import APIRouter, Query

from app.memory.memory_engine import memory_engine
from app.database.schemas import MemorySearchResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/memory", tags=["Memory"])


@router.get("/{conversation_id}")
async def get_conversation_memory(conversation_id: str, limit: int = 50):
    """Get conversation memory (message history)."""
    history = await memory_engine.get_history(conversation_id, limit)
    return {"conversation_id": conversation_id, "messages": history, "count": len(history)}


@router.get("/search/", response_model=list[MemorySearchResult])
async def search_memory(
    q: str = Query(..., min_length=1, description="Search query"),
    conversation_id: str | None = Query(None, description="Limit to conversation"),
    limit: int = Query(10, ge=1, le=50),
):
    """Search conversation memory by keyword."""
    results = await memory_engine.search_memory(q, conversation_id, limit)
    return results
