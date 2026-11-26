"""
AURA AI Tool Manager
Plugin registry for tool discovery, permission mapping, and execution.
"""

import logging
import uuid
from typing import Any
from collections import OrderedDict

from app.database.schemas import ToolInfo, ToolResult
from app.tools.base import BaseTool

logger = logging.getLogger(__name__)


class LRUCache:
    """Simple LRU cache for idempotency keys."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: OrderedDict[str, ToolResult] = OrderedDict()
    
    def get(self, key: str) -> ToolResult | None:
        if key in self._cache:
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            return self._cache[key]
        return None
    
    def set(self, key: str, value: ToolResult) -> None:
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = value
        if len(self._cache) > self.max_size:
            self._cache.popitem(last=False)


class ToolManager:
    """
    Plugin registry for managing and executing tools.

    Handles tool registration, discovery, and execution.
    New tools just need to inherit BaseTool and register here.
    """

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
        self._idempotency_cache = LRUCache(max_size=1000)

    def register(self, tool: BaseTool) -> None:
        """Register a tool in the registry."""
        if tool.name in self._tools:
            logger.warning(f"Tool '{tool.name}' already registered, overwriting")
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def get_tool(self, name: str) -> BaseTool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    @property
    def tools(self) -> dict[str, BaseTool]:
        """Get dict of registered tools."""
        return self._tools

    def list_tools(self) -> list[ToolInfo]:
        """List all registered tools."""
        return [
            ToolInfo(
                name=tool.name,
                description=tool.description,
                parameters=tool.parameters,
                permission_level=tool.permission_level,
            )
            for tool in self._tools.values()
        ]

    def get_tools_description(self) -> str:
        """
        Get formatted tool descriptions for LLM system prompt.
        """
        if not self._tools:
            return "No tools available."

        lines = ["Available tools:"]
        for tool in self._tools.values():
            params = tool.parameters.get("properties", {})
            param_str = ", ".join(
                f"{k}: {v.get('type', 'any')}" for k, v in params.items()
            )
            lines.append(f"- {tool.name}({param_str}): {tool.description} (Permissions: {tool.permission_level})")

        return "\n".join(lines)

    async def execute(self, name: str, *, idempotency_key: str | None = None, **kwargs: Any) -> ToolResult:
        """
        Execute a tool by name with given parameters.
        
        Args:
            name: Tool name
            idempotency_key: Optional key to ensure idempotent execution
            **kwargs: Tool parameters
        """
        tool = self.get_tool(name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"Tool '{name}' not found. Available: {list(self._tools.keys())}",
            )

        # Check idempotency cache
        if idempotency_key:
            cached = self._idempotency_cache.get(idempotency_key)
            if cached:
                logger.info(f"Idempotency hit for tool '{name}' with key '{idempotency_key}'")
                return cached

        try:
            logger.info(f"Executing tool: {name} with params: {kwargs}")
            result = await tool.execute(**kwargs)
            logger.info(f"Tool '{name}' completed. Success: {result.success}")
            
            # Cache successful results for idempotency
            if idempotency_key and result.success:
                self._idempotency_cache.set(idempotency_key, result)
            
            return result
        except Exception as e:
            logger.error(f"Tool '{name}' failed: {e}")
            return ToolResult(success=False, error=f"Tool execution error: {str(e)}")

    def register_defaults(self) -> None:
        """Register all built-in tools."""
        from app.tools.calculator import CalculatorTool
        from app.tools.file_reader import FileReaderTool
        from app.tools.file_writer import FileWriterTool
        from app.tools.system_info import SystemInfoTool
        from app.tools.web_search import WebSearchTool
        from app.tools.code_runner import CodeRunnerTool
        from app.tools.knowledge_retrieval import KnowledgeRetrievalTool
        from app.tools.git_tool import GitTool
        from app.tools.browser_automation import BrowserAutomationTool

        self.register(CalculatorTool())
        self.register(FileReaderTool())
        self.register(FileWriterTool())
        self.register(SystemInfoTool())
        self.register(WebSearchTool())
        self.register(CodeRunnerTool())
        self.register(KnowledgeRetrievalTool())
        self.register(GitTool())
        self.register(BrowserAutomationTool())

        logger.info(f"Registered {len(self._tools)} default tools")


# Global instance
tool_manager = ToolManager()
