import asyncio
import logging

logger = logging.getLogger(__name__)

class StreamRegistry:
    def __init__(self):
        self._paused = {}  # conversation_id -> asyncio.Event (cleared when paused, set when active)
        self._cancelled = set()  # set of cancelled conversation_ids

    def is_paused(self, conversation_id: str) -> bool:
        if conversation_id not in self._paused:
            return False
        return not self._paused[conversation_id].is_set()

    def set_paused(self, conversation_id: str, paused: bool):
        if conversation_id not in self._paused:
            evt = asyncio.Event()
            evt.set()  # Default to running
            self._paused[conversation_id] = evt

        if paused:
            self._paused[conversation_id].clear()
            logger.info(f"Stream registry: Paused conversation {conversation_id}")
        else:
            self._paused[conversation_id].set()
            logger.info(f"Stream registry: Resumed conversation {conversation_id}")

    async def wait_if_paused(self, conversation_id: str):
        if conversation_id in self._paused:
            evt = self._paused[conversation_id]
            if not evt.is_set():
                logger.info(f"Stream registry: Stream is paused, waiting for resume event on {conversation_id}...")
                await evt.wait()
                logger.info(f"Stream registry: Stream resumed on {conversation_id}!")

    def set_cancelled(self, conversation_id: str):
        self._cancelled.add(conversation_id)
        # Automatically resume so wait_if_paused finishes and handles cancellation check
        if conversation_id in self._paused:
            self._paused[conversation_id].set()
        logger.info(f"Stream registry: Cancelled conversation {conversation_id}")

    def is_cancelled(self, conversation_id: str) -> bool:
        return conversation_id in self._cancelled

    def cleanup(self, conversation_id: str):
        self._paused.pop(conversation_id, None)
        self._cancelled.discard(conversation_id)
        logger.info(f"Stream registry: Cleaned up conversation {conversation_id}")

stream_registry = StreamRegistry()
