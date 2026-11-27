"""
AURA AI Model Manager
Manages priorities, routing, streaming, caching, and automatic cloud failovers.
Delegates low-level operations to the robust ProviderManager service.
"""

import time
import logging
from collections.abc import AsyncGenerator

from app.config import settings
from app.core.provider_manager import provider_manager, PROVIDERS_CONFIG, PROVIDERS_PRIORITY

logger = logging.getLogger(__name__)


class ModelManager:
    """Manages AI requests, failover logic, caching, and latency monitoring by delegating to ProviderManager."""

    def __init__(self):
        # Maintain references to provider_manager properties for full backward compatibility
        pass

    @property
    def active_provider(self) -> str:
        return provider_manager.active_provider

    @active_provider.setter
    def active_provider(self, value: str):
        provider_manager.active_provider = value

    @property
    def stats(self) -> dict:
        return provider_manager.stats

    @stats.setter
    def stats(self, value: dict):
        provider_manager.stats = value

    @property
    def last_failure_time(self) -> dict:
        # Map to circuit breaker last failure times
        return {p: provider_manager.circuits[p].last_failure_time for p in PROVIDERS_PRIORITY}

    @property
    def last_health_check_time(self) -> float:
        return provider_manager.last_health_check_time

    @last_health_check_time.setter
    def last_health_check_time(self, value: float):
        provider_manager.last_health_check_time = value

    @property
    def cache(self) -> dict:
        return provider_manager.cache

    def get_stats(self) -> dict:
        """Returns statistics for Developer Mode tracking."""
        return provider_manager.get_stats()

    async def check_provider_health(self, provider_name: str) -> bool:
        """Runs a live diagnostic ping to verify provider status."""
        return await provider_manager.check_provider_health(provider_name)

    async def run_health_checks(self):
        """Asynchronously run health checks for all providers."""
        await provider_manager.run_health_checks()

    async def stream_chat(
        self,
        messages: list[dict],
        category: str = "chat",
        system_prompt: str | None = None,
        preferred_provider: str | None = None,
        preferred_model: str | None = None
    ) -> AsyncGenerator[tuple[str, dict | None], None]:
        """Streams chat completion with automatic failover mechanism."""
        async for chunk, meta in provider_manager.stream_chat(
            messages,
            category=category,
            system_prompt=system_prompt,
            preferred_provider=preferred_provider,
            preferred_model=preferred_model
        ):
            yield chunk, meta

    async def chat(
        self,
        messages: list[dict],
        category: str = "chat",
        system_prompt: str | None = None
    ) -> tuple[str, dict | None]:
        """Helper to fetch a complete non-streaming response with metadata."""
        return await provider_manager.chat(messages, category, system_prompt)


# Initialize global ModelManager instance to preserve integration compatibility
model_manager = ModelManager()
