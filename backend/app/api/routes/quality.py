"""
AURA Global Quality Engine — Dashboard API

REST endpoints exposing real quality engine activity for the Coding Studio UI.
All data comes from actual backend records and execution events.
"""

import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Any

from app.memory.project_manager import project_manager, get_workspace_root
from app.quality.engine import agqe
from app.quality.repair import repair_engine
from app.quality.database import (
    get_quality_project,
    get_quality_gates,
    get_defects,
    update_defect_status,
    find_repair_pattern,
    find_repair_patterns_by_category,
    create_repair_pattern,
    get_project_quality_summary,
    get_global_registry_stats,
    create_quality_spec,
    get_quality_spec,
    DEFECT_CATEGORIES,
    DEFECT_SEVERITIES,
    GATE_DEFINITIONS,
)
from app.quality.detectors.engine import tech_detection_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/quality", tags=["Quality Engine"])


# ─── Request/Response Schemas ──────────────────────────────────────────

class ValidateRequest(BaseModel):
    project_id: str
    files: list[str] | None = None


class SpecCreateRequest(BaseModel):
    project_id: str
    spec_data: dict
    version: int = 1


class RepairPatternCreateRequest(BaseModel):
    error_fingerprint: str
    error_category: str
    technologies: list[str]
    root_cause: str
    solution_pattern: str
    validation_method: str
    regression_test: dict | None = None
    confidence: float = 0.5
    is_global: bool = True


# ─── Project Registration & Status ─────────────────────────────────────

@router.post("/projects/{project_id}/register")
async def register_project(project_id: str):
    """Register a project with the quality engine and run technology detection."""
    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    slug = project["slug"]
    project_dir = get_workspace_root() / "user_files" / "Projects" / slug

    result = await agqe.register_project(project_id, project_dir)
    return result


@router.get("/projects/{project_id}/status")
async def get_project_status(project_id: str):
    """Get full quality status for a project (dashboard aggregate)."""
    status = await agqe.get_project_status(project_id)
    return status


@router.get("/projects/{project_id}/gates")
async def get_gates(project_id: str):
    """List all 12 quality gates for a project."""
    gates = await get_quality_gates(project_id)
    if not gates:
        raise HTTPException(status_code=404, detail="No quality gates found for project")
    return {"gates": gates}


@router.get("/projects/{project_id}/defects")
async def list_defects(
    project_id: str,
    status: str | None = Query(None),
    severity: str | None = Query(None),
):
    """List defects for a project with optional filters."""
    defects = await get_defects(project_id, status=status, severity=severity)
    return {"defects": defects}


@router.get("/projects/{project_id}/summary")
async def get_summary(project_id: str):
    """Get aggregated quality summary for dashboard."""
    summary = await get_project_quality_summary(project_id)
    return summary


# ─── Validation ────────────────────────────────────────────────────────

@router.post("/validate")
async def run_validation(req: ValidateRequest):
    """Run static validation on a project (Gate 4)."""
    project = await project_manager.get_project(req.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    slug = project["slug"]
    project_dir = get_workspace_root() / "user_files" / "Projects" / slug

    result = await agqe.run_static_validation(req.project_id, project_dir, req.files)
    return result


# ─── Quality Specification ─────────────────────────────────────────────

@router.post("/specs")
async def create_spec(req: SpecCreateRequest):
    """Create or update a project quality specification."""
    spec_id = await create_quality_spec(
        project_id=req.project_id,
        spec_data=req.spec_data,
        version=req.version,
    )
    return {"spec_id": spec_id}


@router.get("/projects/{project_id}/specs")
async def get_spec(project_id: str, version: int | None = None):
    """Get the quality specification for a project."""
    spec = await get_quality_spec(project_id, version=version)
    if not spec:
        raise HTTPException(status_code=404, detail="No quality spec found for project")
    return spec


# ─── Repair Registry ───────────────────────────────────────────────────

@router.get("/registry")
async def list_repair_patterns(
    category: str | None = Query(None),
    technologies: str | None = Query(None, description="Comma-separated tech list"),
):
    """List global repair patterns, optionally filtered by category and technologies."""
    tech_list = [t.strip() for t in technologies.split(",")] if technologies else None

    if category:
        patterns = await find_repair_patterns_by_category(category, tech_list)
    else:
        # Return all global patterns
        from app.database.database import db
        cursor = db.db["repair_registry"].find({"is_global": True}).sort("confidence", -1)
        patterns = [doc async for doc in cursor]

    return {"patterns": patterns}


@router.get("/registry/{error_fingerprint}")
async def get_repair_pattern(error_fingerprint: str):
    """Get a specific repair pattern by error fingerprint."""
    pattern = await find_repair_pattern(error_fingerprint)
    if not pattern:
        raise HTTPException(status_code=404, detail="Repair pattern not found")
    return pattern


@router.post("/registry")
async def create_repair_pattern_endpoint(req: RepairPatternCreateRequest):
    """Create a new repair pattern in the global registry."""
    pattern_id = await create_repair_pattern(
        error_fingerprint=req.error_fingerprint,
        error_category=req.error_category,
        technologies=req.technologies,
        root_cause=req.root_cause,
        solution_pattern=req.solution_pattern,
        validation_method=req.validation_method,
        regression_test=req.regression_test,
        confidence=req.confidence,
        is_global=req.is_global,
    )
    return {"pattern_id": pattern_id}


@router.get("/registry/stats")
async def get_registry_stats():
    """Get global repair registry statistics."""
    stats = await get_global_registry_stats()
    return stats


# ─── Tech Detection ────────────────────────────────────────────────────

@router.get("/projects/{project_id}/tech-detect")
async def tech_detect(project_id: str):
    """Run technology detection on a project directory."""
    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    slug = project["slug"]
    project_dir = get_workspace_root() / "user_files" / "Projects" / slug

    result = tech_detection_engine.detect_and_summarize(project_dir)
    return result


# ─── Metadata ──────────────────────────────────────────────────────────

@router.get("/metadata/defect-categories")
async def defect_categories():
    return {"categories": DEFECT_CATEGORIES}


@router.get("/metadata/defect-severities")
async def defect_severities():
    return {"severities": DEFECT_SEVERITIES}


@router.get("/metadata/gates")
async def gates_metadata():
    return {
        "gates": [
            {"gate_number": n, "gate_name": name, "description": desc}
            for n, name, desc in GATE_DEFINITIONS
        ]
    }


@router.get("/metadata/supported-technologies")
async def supported_technologies():
    """Report which technologies have validator coverage."""
    return {
        "covered": ["HTML", "CSS", "JavaScript", "TypeScript", "React", "Vue", "Angular", "Svelte", "Next.js", "Nuxt"],
        "planned": ["Python", "Django", "FastAPI", "Flask", "Express", "NestJS", "PostgreSQL", "MySQL", "SQLite", "MongoDB"],
        "note": "Validator coverage matches actually implemented validators; unsupported stacks are disclosed honestly.",
    }


# ─── Repair ────────────────────────────────────────────────────────────

class RepairDefectRequest(BaseModel):
    project_id: str
    defect_id: str


@router.post("/repair")
async def repair_defect(req: RepairDefectRequest):
    """Attempt to autonomously repair a defect."""
    project = await project_manager.get_project(req.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    slug = project["slug"]
    project_dir = get_workspace_root() / "user_files" / "Projects" / slug

    result = await repair_engine.repair_defect(
        req.project_id, req.defect_id, project_dir
    )

    return {
        "defect_id": result.defect_id,
        "project_id": result.project_id,
        "success": result.success,
        "root_cause": result.root_cause,
        "repair_strategy": result.repair_strategy,
        "registry_pattern_used": result.registry_pattern_used,
        "validation_passed": result.validation_passed,
        "message": result.message,
        "attempts": [
            {
                "attempt_id": a.attempt_id,
                "repair_strategy": a.repair_strategy,
                "validation_passed": a.validation_passed,
                "success": a.success,
                "error_message": a.error_message,
                "created_at": a.created_at,
            }
            for a in result.attempts
        ],
    }


@router.get("/projects/{project_id}/repair-history")
async def get_repair_history(project_id: str):
    """Get all repair attempts for a project."""
    from app.quality.database import get_project_repair_history
    history = await get_project_repair_history(project_id)
    return {"history": history}

