"""
AURA AI Tool Base
Abstract base class for all tools.
"""

from abc import ABC, abstractmethod
from typing import Any

from app.database.schemas import ToolResult


class BaseTool(ABC):
    """
    Abstract base class for AURA tools.

    All tools must implement:
    - name: unique identifier
    - description: human-readable description for LLM
    - parameters: JSON Schema describing accepted parameters
    - execute(): async method that runs the tool
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool name."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description."""
        ...

    @property
    def parameters(self) -> dict:
        """JSON Schema for tool parameters. Override to define params."""
        return {}

    @property
    def permission_level(self) -> str:
        """Permission level required for this tool ('safe', 'restricted', 'admin')."""
        return "safe"

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with given parameters."""
        ...

    def to_dict(self) -> dict:
        """Serialize tool info for API responses."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "permission_level": self.permission_level,
        }
