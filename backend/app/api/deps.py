"""
AURA AI API Dependencies
Dependency injection for FastAPI routes.
"""

from app.core.llm_client import llm_client
from app.memory.memory_engine import memory_engine
from app.router.router_engine import router_engine
from app.tools.tool_manager import tool_manager
from app.database.database import db


async def get_db():
    """Get database instance."""
    return db


async def get_memory_engine():
    """Get memory engine instance."""
    return memory_engine


async def get_tool_manager():
    """Get tool manager instance."""
    return tool_manager


async def get_router_engine():
    """Get router engine instance."""
    return router_engine


async def get_llm_client():
    """Get LLM client instance."""
    return llm_client
