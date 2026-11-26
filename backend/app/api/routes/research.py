"""
AURA AI Deep Research API Routes
Endpoints for SSE-streamed research, settings management, history, and exports.
Completely independent from Chat API.
"""

import json
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel

from app.database.database import db
from app.search.research_engine import active_research_tasks, get_workspace_root
from app.core.auth_security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/research", tags=["Deep Research"])


# ── Request Models ──

class ResearchStartRequest(BaseModel):
    topic: str
    conversation_id: str | None = None
    depth: str = "standard"


class ResearchSettingUpdate(BaseModel):
    key: str
    value: str


# ── SSE Research Endpoint (Independent from Chat) ──

@router.post("/start")
async def start_research(request: ResearchStartRequest, current_user: dict = Depends(get_current_user)):
    """
    Start a deep research task. Returns SSE stream with progress and report tokens.
    Uses research_llm_client (Bedrock) — never Chat/Agent providers.
    """
    from app.search.research_engine import research_engine
    from app.memory.memory_engine import memory_engine
    from app.database.schemas import ChatEventType

    topic = request.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="Topic is required")

    # Validate depth
    valid_depths = ("quick", "standard", "deep", "expert")
    depth = request.depth.lower() if request.depth.lower() in valid_depths else "standard"

    # Get or create conversation
    conversation_id = request.conversation_id
    if not conversation_id:
        conversation_id = await memory_engine.create_conversation(user_id=current_user["id"])

    async def event_stream():
        """SSE event generator for deep research."""
        try:
            # Conversation ID event
            yield _format_sse("conversation_id", json.dumps({
                "conversation_id": conversation_id,
            }))

            # Store user query
            await memory_engine.add_message(conversation_id, "user", topic)

            full_report = ""

            async for event_type, data, metadata in research_engine.conduct_research(topic, conversation_id, depth):
                if event_type == ChatEventType.TOKEN:
                    full_report += data

                event_data = {"content": data}
                if metadata:
                    event_data["metadata"] = metadata

                yield _format_sse(event_type.value, json.dumps(event_data))

            # Save report as assistant message
            if full_report:
                await memory_engine.add_message(
                    conversation_id, "assistant", full_report,
                    {"mode": "deep_research", "topic": topic, "depth": depth}
                )

        except Exception as e:
            logger.error(f"Research SSE error: {e}", exc_info=True)
            yield _format_sse("error", json.dumps({"content": str(e)}))

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Cancel Research ──

@router.post("/cancel")
async def cancel_research(body: dict, current_user: dict = Depends(get_current_user)):
    """Cancel an active research task."""
    conversation_id = body.get("conversation_id")
    if not conversation_id:
        raise HTTPException(status_code=400, detail="Missing conversation_id")

    task = active_research_tasks.pop(conversation_id, None)
    if task and not task.done():
        task.cancel()
        logger.info(f"Research cancelled for conversation {conversation_id}")
        return {"status": "cancelled", "conversation_id": conversation_id}

    return {"status": "no_active_task", "conversation_id": conversation_id}


# ── Research History ──

@router.get("/history")
async def get_all_research_history(current_user: dict = Depends(get_current_user)):
    """Fetch all research reports for the research history panel."""
    try:
        rows = await db.db.research_reports.find(
            {}, {"report_content": 0}  # Exclude full content for list view
        ).sort("created_at", -1).to_list(length=50)

        reports = []
        for r in rows:
            report = dict(r)
            report.pop("_id", None)
            # Parse sources JSON
            if report.get("sources_json"):
                try:
                    report["sources"] = json.loads(report["sources_json"])
                except Exception:
                    report["sources"] = []
            if report.get("quality_check"):
                try:
                    report["quality"] = json.loads(report["quality_check"])
                except Exception:
                    report["quality"] = {}
            reports.append(report)
        return reports
    except Exception as e:
        logger.error(f"Failed to fetch research history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{conversation_id}")
async def get_research_history(conversation_id: str, current_user: dict = Depends(get_current_user)):
    """Fetch research reports for a specific conversation."""
    try:
        rows = await db.db.research_reports.find(
            {"conversation_id": conversation_id}
        ).sort("created_at", -1).to_list(length=None)

        reports = []
        for r in rows:
            report = dict(r)
            report.pop("_id", None)
            if report.get("facts_json"):
                try:
                    report["facts"] = json.loads(report["facts_json"])
                except Exception:
                    report["facts"] = []
            if report.get("sources_json"):
                try:
                    report["sources"] = json.loads(report["sources_json"])
                except Exception:
                    report["sources"] = []
            reports.append(report)
        return reports
    except Exception as e:
        logger.error(f"Failed to fetch research history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Research Report Detail ──

@router.get("/report/{report_id}")
async def get_research_report(report_id: str, current_user: dict = Depends(get_current_user)):
    """Fetch a specific research report with full content."""
    try:
        report = await db.db.research_reports.find_one({"id": report_id})
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        result = dict(report)
        result.pop("_id", None)
        if result.get("facts_json"):
            try:
                result["facts"] = json.loads(result["facts_json"])
            except Exception:
                result["facts"] = []
        if result.get("sources_json"):
            try:
                result["sources"] = json.loads(result["sources_json"])
            except Exception:
                result["sources"] = []
        if result.get("quality_check"):
            try:
                result["quality"] = json.loads(result["quality_check"])
            except Exception:
                result["quality"] = {}
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Research Settings ──

RESEARCH_SETTINGS_KEYS = {
    "research_provider", "research_api_key", "research_model",
    "research_aws_region", "research_temperature", "research_depth",
    "research_sources_limit", "research_timeout",
}

VALID_PROVIDERS = {"bedrock", "openai", "anthropic", "openrouter", "perplexity"}
VALID_DEPTHS = {"quick", "standard", "deep", "expert"}


@router.get("/settings")
async def get_research_settings(current_user: dict = Depends(get_current_user)):
    """Get all research-specific settings."""
    try:
        rows = await db.db.system_settings.find(
            {"key": {"$in": list(RESEARCH_SETTINGS_KEYS)}},
            {"key": 1, "value": 1}
        ).to_list(length=None)

        settings_map = {r["key"]: r["value"] for r in rows}

        # Mask API key for security
        if settings_map.get("research_api_key"):
            key = settings_map["research_api_key"]
            if len(key) > 8:
                settings_map["research_api_key"] = key[:4] + "****" + key[-4:]

        return settings_map
    except Exception as e:
        logger.error(f"Failed to fetch research settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/settings")
async def update_research_setting(body: ResearchSettingUpdate, current_user: dict = Depends(get_current_user)):
    """Update a research-specific setting."""
    if body.key not in RESEARCH_SETTINGS_KEYS:
        raise HTTPException(status_code=400, detail=f"Invalid setting key: {body.key}")

    # Validation
    if body.key == "research_provider" and body.value.lower() not in VALID_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Invalid provider. Must be one of: {', '.join(VALID_PROVIDERS)}")

    if body.key == "research_depth" and body.value.lower() not in VALID_DEPTHS:
        raise HTTPException(status_code=400, detail=f"Invalid depth. Must be one of: {', '.join(VALID_DEPTHS)}")

    if body.key == "research_temperature":
        try:
            temp = float(body.value)
            if temp < 0.0 or temp > 2.0:
                raise ValueError()
        except ValueError:
            raise HTTPException(status_code=400, detail="Temperature must be between 0.0 and 2.0")

    if body.key in ("research_sources_limit", "research_timeout"):
        try:
            val = int(body.value)
            if val <= 0:
                raise ValueError()
        except ValueError:
            raise HTTPException(status_code=400, detail=f"{body.key} must be a positive integer")

    try:
        await db.db.system_settings.update_one(
            {"key": body.key},
            {"$set": {"value": body.value}},
            upsert=True
        )

        # Invalidate research client settings cache
        from app.core.bedrock_research_client import research_llm_client
        research_llm_client.invalidate_cache()

        return {"key": body.key, "value": body.value, "status": "updated"}
    except Exception as e:
        logger.error(f"Failed to update research setting: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Research Health Check ──

@router.get("/health")
async def research_health(current_user: dict = Depends(get_current_user)):
    """Check the health of the research provider."""
    from app.core.bedrock_research_client import research_llm_client
    result = await research_llm_client.health_check()
    return result


# ── File Download ──

@router.get("/download")
async def download_report_file(path: str):
    """Download research documents (Markdown, Word, PDF) from workspace."""
    workspace_root = get_workspace_root()
    target_path = (workspace_root / path).resolve()

    if not str(target_path).startswith(str(workspace_root)):
        raise HTTPException(status_code=403, detail="Access denied: outside sandbox")

    if not target_path.exists() or not target_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    suffix = target_path.suffix.lower()
    if suffix not in (".md", ".docx", ".pdf"):
        raise HTTPException(status_code=400, detail="Unsupported file type")

    return FileResponse(
        path=target_path,
        filename=target_path.name,
        media_type="application/octet-stream"
    )


def _format_sse(event: str, data: str) -> str:
    """Format a Server-Sent Event."""
    return f"event: {event}\ndata: {data}\n\n"
