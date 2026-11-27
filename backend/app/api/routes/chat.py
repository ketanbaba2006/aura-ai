"""
AURA AI Chat API
Main chat endpoint with SSE streaming.
"""

import json
import logging

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.memory.memory_engine import memory_engine
from app.router.router_engine import router_engine
from app.database.schemas import ChatEventType, ChatRequest
from app.core.auth_security import get_current_user
from app.memory.project_manager import project_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("")
async def chat(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    """
    Main chat endpoint. Returns SSE stream.

    Events:
    - token: LLM response chunk
    - tool_use: Tool being invoked
    - tool_result: Tool execution result
    - done: Response complete
    - error: Error occurred
    """
    # Get or create conversation
    conversation_id = request.conversation_id or request.conversationId
    if not conversation_id:
        conversation_id = await memory_engine.create_conversation(user_id=current_user["id"])

    async def event_stream():
        """Generate SSE events."""
        from app.router.stream_registry import stream_registry
        try:
            # Send conversation ID first
            yield _format_sse("conversation_id", json.dumps({
                "conversation_id": conversation_id,
            }))

            # Pure Chatbot Routing
            responder = router_engine.route_and_respond(
                request.message,
                conversation_id,
                request.timezone,
                preferred_provider=request.provider,
                preferred_model=request.model
            )

            async for event_type, data, metadata in responder:
                # Check for cancellation or pause in the registry
                if stream_registry.is_cancelled(conversation_id):
                    logger.info(f"SSE event_stream: detected cancellation for {conversation_id}, aborting loop.")
                    break
                
                await stream_registry.wait_if_paused(conversation_id)

                event_data = {
                    "content": data,
                }
                if metadata:
                    event_data["metadata"] = metadata

                yield _format_sse(event_type.value, json.dumps(event_data))

        except Exception as e:
            logger.error(f"Chat error: {e}", exc_info=True)
            error_data = json.dumps({"content": str(e)})
            yield _format_sse("error", error_data)
        finally:
            stream_registry.cleanup(conversation_id)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/pause")
async def pause_chat(body: dict, current_user: dict = Depends(get_current_user)):
    """Pause the active streaming generation for a conversation."""
    conversation_id = body.get("conversation_id")
    if not conversation_id:
        raise HTTPException(status_code=400, detail="Missing conversation_id")
    from app.router.stream_registry import stream_registry
    stream_registry.set_paused(conversation_id, True)
    return {"status": "paused", "conversation_id": conversation_id}


@router.post("/resume")
async def resume_chat(body: dict, current_user: dict = Depends(get_current_user)):
    """Resume the active streaming generation for a conversation."""
    conversation_id = body.get("conversation_id")
    if not conversation_id:
        raise HTTPException(status_code=400, detail="Missing conversation_id")
    from app.router.stream_registry import stream_registry
    stream_registry.set_paused(conversation_id, False)
    return {"status": "resumed", "conversation_id": conversation_id}


def _format_sse(event: str, data: str) -> str:
    """Format a Server-Sent Event."""
    return f"event: {event}\ndata: {data}\n\n"
