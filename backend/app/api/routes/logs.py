"""
AURA AI Activity Logs Route
Endpoints for query and management of local activity logs.
"""

import logging
from fastapi import APIRouter, HTTPException, Query

from app.logs.activity_logger import activity_logger
from app.database.schemas import ActivityLogResponse, LogStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/logs", tags=["Activity Logs"])


@router.get("", response_model=list[ActivityLogResponse])
async def get_logs(
    category: str | None = Query(None, description="Filter by category"),
    status: LogStatus | None = Query(None, description="Filter by level status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Get list of logs, filtered and paginated."""
    try:
        status_val = status.value if status else None
        logs = await activity_logger.get_logs(
            category=category, status=status_val, limit=limit, offset=offset
        )
        return [
            ActivityLogResponse(
                id=log["id"],
                timestamp=log["timestamp"],
                action_type=log["action_type"],
                category=log["category"],
                description=log["description"],
                details=log.get("details"),
                status=LogStatus(log["status"]),
            )
            for log in logs
        ]
    except Exception as e:
        logger.error(f"Failed to fetch logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("")
async def clear_logs():
    """Clear all logged activities from SQLite."""
    try:
        await activity_logger.clear_logs()
        return {"status": "cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
