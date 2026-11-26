"""
AURA AI Tools API
Tool listing and direct execution endpoints.
"""

import logging

from fastapi import APIRouter, HTTPException

from app.tools.tool_manager import tool_manager
from app.database.schemas import ToolExecuteRequest, ToolInfo, ToolResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tools", tags=["Tools"])


@router.get("", response_model=list[ToolInfo])
async def list_tools():
    """List all available tools."""
    return tool_manager.list_tools()


@router.post("/{tool_name}/execute", response_model=ToolResult)
async def execute_tool(tool_name: str, body: ToolExecuteRequest):
    """Execute a tool directly."""
    tool = tool_manager.get_tool(tool_name)
    if not tool:
        raise HTTPException(
            status_code=404,
            detail=f"Tool '{tool_name}' not found",
        )

    result = await tool_manager.execute(tool_name, **body.params)
    return result
