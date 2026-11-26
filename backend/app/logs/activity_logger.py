"""
AURA AI Activity Logger
Records events and actions asynchronously to SQLite.
"""

import json
import logging
import uuid
from datetime import datetime

from app.database.database import db

logger = logging.getLogger(__name__)


class ActivityLogger:
    """Helper to record user actions, tool executions, memory ops, and errors."""

    async def log(
        self,
        action_type: str,
        category: str,
        description: str,
        details: dict | None = None,
        status: str = "info",
    ) -> str:
        """
        Write a log entry to SQLite database.
        Returns the log ID.
        """
        log_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        details_json = json.dumps(details) if details else None

        try:
            await db.db.activity_logs.insert_one({"id": log_id, "timestamp": now, "action_type": action_type, "category": category, "description": description, "details": details_json, "status": status})
        except Exception as e:
            # Fallback to standard logging if db write fails
            logger.error(f"Failed to save activity log: {e}")
            logger.warning(
                f"[AURA ActivityLog] [{status.upper()}] [{category}] {action_type} - {description} details={details}"
            )

        return log_id

    async def get_logs(
        self,
        category: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """Fetch logs with filtering and pagination."""
        filter_query = {}
        if category:
            filter_query["category"] = category
        if status:
            filter_query["status"] = status
        return await db.db.activity_logs.find(filter_query).sort("timestamp", -1).skip(offset).limit(limit).to_list(length=None)

    async def clear_logs(self) -> None:
        """Purge all records in activity_logs."""
        await db.db.activity_logs.delete_many({})


activity_logger = ActivityLogger()
