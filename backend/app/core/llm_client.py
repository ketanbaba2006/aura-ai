"""
AURA AI LLM Client
Async model routing client using ModelManager.
"""

import json
import logging
from collections.abc import AsyncGenerator

import httpx

from app.config import settings
from app.core.model_manager import model_manager

logger = logging.getLogger(__name__)


class LLMClient:
    """Async client that delegates to ModelManager for multi-provider routing."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
    ):
        self.base_url = (base_url or "https://api.cloud").rstrip("/")
        self.model = model or "cloud"
        self.timeout = timeout or 30.0

    async def health_check(self) -> bool:
        """Check if cloud API keys are configured."""
        if settings.GROQ_API_KEY or settings.GEMINI_API_KEY or settings.OPENROUTER_API_KEY:
            return True
        return False

    async def stream_chat(
        self,
        messages: list[dict],
        model: str | None = None,
        system_prompt: str | None = None,
        category: str = "chat",
    ) -> AsyncGenerator[tuple[str, dict | None], None]:
        """
        Stream chat completion via ModelManager.
        """
        async for chunk, meta in model_manager.stream_chat(
            messages=messages,
            category=category,
            system_prompt=system_prompt,
        ):
            yield chunk, meta

    async def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        system_prompt: str | None = None,
        category: str = "chat",
    ) -> tuple[str, dict | None]:
        """
        Non-streaming chat completion via ModelManager.
        """
        return await model_manager.chat(
            messages=messages,
            category=category,
            system_prompt=system_prompt,
        )

    async def generate_json(
        self,
        prompt: str,
        model: str | None = None,
        system_prompt: str | None = None,
        category: str = "chat",
    ) -> dict:
        """
        Generate a JSON response from a single prompt via ModelManager.
        """
        messages = [{"role": "user", "content": prompt}]
        response, _meta = await self.chat(
            messages=messages,
            system_prompt=system_prompt,
            category=category,
        )
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Clean possible markdown block formatting
            cleaned = response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                logger.warning(f"LLM returned non-JSON: {response[:200]}")
                return {"raw": response}


# Global instance
llm_client = LLMClient()

