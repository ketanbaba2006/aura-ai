"""
AURA AI Conversations API
CRUD endpoints for conversation management.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from app.core.auth_security import get_current_user

from app.memory.memory_engine import memory_engine
from app.database.schemas import (
    ConversationCreate,
    ConversationDetailResponse,
    ConversationResponse,
    ConversationUpdate,
    MessageResponse,
    MessageRole,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(current_user: dict = Depends(get_current_user)):
    """List all conversations, most recent first."""
    rows = await memory_engine.list_conversations(current_user["id"])

    return [
        ConversationResponse(
            id=row["id"],
            title=row["title"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            message_count=row.get("message_count", 0),
            last_message=row.get("last_message"),
        )
        for row in rows
    ]


@router.post("", response_model=ConversationResponse)
async def create_conversation(body: ConversationCreate | None = None, current_user: dict = Depends(get_current_user)):
    """Create a new conversation."""
    title = body.title if body else "New Conversation"
    conv_id = await memory_engine.create_conversation(title, current_user["id"])
    conv = await memory_engine.get_conversation(conv_id, current_user["id"])

    return ConversationResponse(
        id=conv["id"],
        title=conv["title"],
        created_at=conv["created_at"],
        updated_at=conv["updated_at"],
        message_count=0,
    )


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(conversation_id: str, current_user: dict = Depends(get_current_user)):
    """Get a conversation with all messages."""
    conv = await memory_engine.get_conversation(conversation_id, current_user["id"])
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = await memory_engine.get_history(conversation_id)

    return ConversationDetailResponse(
        id=conv["id"],
        title=conv["title"],
        created_at=conv["created_at"],
        updated_at=conv["updated_at"],
        messages=[
            MessageResponse(
                id=msg["id"],
                conversation_id=conversation_id,
                role=MessageRole(msg["role"]),
                content=msg["content"],
                metadata=msg.get("metadata"),
                created_at=msg["created_at"],
            )
            for msg in messages
        ],
    )


@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(conversation_id: str, body: ConversationUpdate, current_user: dict = Depends(get_current_user)):
    """Update conversation title."""
    conv = await memory_engine.get_conversation(conversation_id, current_user["id"])
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await memory_engine.update_conversation_title(conversation_id, body.title)
    conv = await memory_engine.get_conversation(conversation_id, current_user["id"])

    return ConversationResponse(
        id=conv["id"],
        title=conv["title"],
        created_at=conv["created_at"],
        updated_at=conv["updated_at"],
    )


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a conversation and all its messages."""
    conv = await memory_engine.get_conversation(conversation_id, current_user["id"])
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await memory_engine.delete_conversation(conversation_id, current_user["id"])
    return {"status": "deleted", "id": conversation_id}
