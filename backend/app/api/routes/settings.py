"""
AURA AI Settings API
System settings management.
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.database.database import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["Settings"])

class SettingsUpdate(BaseModel):
    value: str

@router.get("")
async def get_settings():
    """Get all settings."""
    try:
        rows = await db.db.system_settings.find({}, {"key": 1, "value": 1}).to_list(length=None)
        return {row["key"]: row["value"] for row in rows}
    except Exception as e:
        logger.error(f"Failed to fetch settings: {e}")
        raise HTTPException(status_code=500, detail="Database query failed")

@router.get("/{key}")
async def get_setting(key: str):
    """Get a specific setting."""
    try:
        row = await db.db.system_settings.find_one({"key": key}, {"value": 1})
        if not row:
            raise HTTPException(status_code=404, detail="Setting not found")
        return {"key": key, "value": row["value"]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch setting '{key}': {e}")
        raise HTTPException(status_code=500, detail="Database query failed")

@router.put("/{key}")
async def update_setting(key: str, body: SettingsUpdate):
    """Update a specific setting."""
    if key == "web_search_mode" and body.value not in ("never", "ask_first", "automatic"):
        raise HTTPException(
            status_code=400,
            detail="Invalid web search mode. Must be 'never', 'ask_first', or 'automatic'."
        )
    try:
        await db.db.system_settings.update_one({"key": key}, {"$set": {"value": body.value}}, upsert=True)
        return {"key": key, "value": body.value}
    except Exception as e:
        logger.error(f"Failed to update setting '{key}': {e}")
        raise HTTPException(status_code=500, detail="Database update failed")
