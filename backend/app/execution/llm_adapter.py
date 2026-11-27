"""
Bridge adapter that maps multi_agent_engine llm_service calls to backend llm_client / model_manager.
"""

import logging
from typing import AsyncGenerator
from app.core.llm_client import llm_client

logger = logging.getLogger(__name__)

class LLMServiceAdapter:
    async def stream_chat(
        self,
        messages: list[dict],
        system_prompt: str | None = None,
        requested_provider: str | None = None,
        requested_model: str | None = None,
        custom_api_key: str | None = None,
        custom_base_url: str | None = None,
    ) -> AsyncGenerator[tuple[str, dict], None]:
        prov = requested_provider if requested_provider and requested_provider != "auto" else "groq"
        mod = requested_model if requested_model and requested_model != "auto" else "qwen/qwen3.8-27b"
        
        try:
            async for chunk, _meta in llm_client.stream_chat(
                messages=messages,
                system_prompt=system_prompt,
                preferred_provider=prov,
                preferred_model=mod,
                category="code",
            ):
                if chunk:
                    yield ("token", {"text": chunk})
        except Exception as e:
            logger.error(f"LLMServiceAdapter error: {e}", exc_info=True)
            yield ("token", {"text": f"\n/* Synthesis note: {str(e)} */\n"})

llm_service = LLMServiceAdapter()
