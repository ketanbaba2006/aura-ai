"""
AURA AI Quality Engine — Database Schema Extensions (MongoDB)
Adds collections for quality gates, defects, repair registry, and project specifications.
Uses Motor async MongoDB driver via the existing `db` instance.
"""

import json
import uuid
from datetime import datetime
from typing import Optional

from app.database.database import db

# ─── Collection Names ──────────────────────────────────────────────────

COL_QUALITY_PROJECTS = "quality_projects"
COL_QUALITY_GATES = "quality_gates"
COL_DEFECTS = "defects"
COL_REPAIR_REGISTRY = "repair_registry"
COL_PROJECT_REPAIR_HISTORY = "project_repair_history"
COL_REGRESSION_RULES = "regression_rules"
COL_PROJECT_QUALITY_SPECS = "project_quality_specs"

# ─── Gate Definitions ──────────────────────────────────────────────────

GATE_DEFINITIONS = [
    (1, "Requirements", "Project requirements are clear and recorded"),
    (2, "Architecture", "Architecture and shared interfaces are validated"),
    (3, "Implementation", "Relevant agents have completed and reviewed their work"),
    (4, "Static Validation", "Applicable syntax, linting, type and structural checks pass"),
    (5, "Integration", "Relevant interfaces, dependencies and APIs are compatible"),
    (6, "Build", "The actual build succeeds where a build process applies"),
    (7, "Runtime", "The application starts and behaves correctly"),
    (8, "Visual QA", "The actual rendered UI is inspected for UI projects"),
    (9, "Functional QA", "Required user workflows are tested"),
    (10, "Security & Reliability", "Applicable security and reliability checks pass"),
    (11, "Regression", "Previously working functionality remains intact"),
    (12, "Delivery", "The final exported project matches the verified workspace revision"),
]

DEFECT_CATEGORIES = [
    "syntax", "html_structure", "css", "js_ts", "type", "import",
    "build", "runtime", "component", "dom_ref", "api_integration",
    "database", "asset_loading", "visual_layout", "responsive",
    "accessibility", "security", "performance", "dependency", "deployment",
]

DEFECT_SEVERITIES = ["critical", "high", "medium", "low"]


# ─── Schema Initialization ─────────────────────────────────────────────

async def initialize_quality_schema() -> None:
    """Create all quality engine collections and indexes."""
    database = db.db

    index_specs = [
        (COL_QUALITY_PROJECTS, [("project_id", 1)], True),
        (COL_QUALITY_GATES, [("project_id", 1), ("gate_number", 1)], True),
        (COL_QUALITY_GATES, [("status", 1)], False),
        (COL_DEFECTS, [("project_id", 1)], False),
        (COL_DEFECTS, [("gate_id", 1)], False),
        (COL_DEFECTS, [("category", 1)], False),
        (COL_DEFECTS, [("severity", 1)], False),
        (COL_DEFECTS, [("status", 1)], False),
        (COL_DEFECTS, [("file_path", 1)], False),
        (COL_REPAIR_REGISTRY, [("error_fingerprint", 1)], True),
        (COL_REPAIR_REGISTRY, [("error_category", 1)], False),
        (COL_PROJECT_REPAIR_HISTORY, [("project_id", 1)], False),
        (COL_PROJECT_REPAIR_HISTORY, [("defect_id", 1)], False),
        (COL_REGRESSION_RULES, [("repair_registry_id", 1)], False),
        (COL_REGRESSION_RULES, [("rule_type", 1)], False),
        (COL_PROJECT_QUALITY_SPECS, [("project_id", 1), ("version", 1)], True),
    ]

    for collection_name, keys, unique in index_specs:
        try:
            await database[collection_name].create_index(keys, unique=unique)
        except Exception:
            pass


# ─── Quality Project Registration ──────────────────────────────────────

async def register_quality_project(project_id: str, tech_stack: dict) -> str:
    """Register a project with the quality engine. Returns quality_project id."""
    qp_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    await db.db[COL_QUALITY_PROJECTS].update_one(
        {"project_id": project_id},
        {
            "$set": {
                "id": qp_id,
                "project_id": project_id,
                "tech_stack": tech_stack,
                "registered_at": now,
                "last_validated_at": now,
            }
        },
        upsert=True,
    )
    return qp_id


async def get_quality_project(project_id: str) -> dict | None:
    """Get quality project registration by project_id."""
    return await db.db[COL_QUALITY_PROJECTS].find_one({"project_id": project_id})


async def update_quality_project_validation(project_id: str) -> None:
    """Update last_validated_at timestamp."""
    now = datetime.utcnow().isoformat()
    await db.db[COL_QUALITY_PROJECTS].update_one(
        {"project_id": project_id},
        {"$set": {"last_validated_at": now}},
    )


# ─── Quality Gates ─────────────────────────────────────────────────────

async def initialize_quality_gates(project_id: str) -> list[dict]:
    """Create all 12 quality gates for a project in pending state."""
    gates = []
    now = datetime.utcnow().isoformat()

    for gate_num, gate_name, _ in GATE_DEFINITIONS:
        gate_id = str(uuid.uuid4())
        gate_doc = {
            "id": gate_id,
            "project_id": project_id,
            "gate_number": gate_num,
            "gate_name": gate_name,
            "status": "pending",
            "started_at": None,
            "completed_at": None,
            "results": {},
            "evidence": {},
            "created_at": now,
        }
        await db.db[COL_QUALITY_GATES].update_one(
            {"project_id": project_id, "gate_number": gate_num},
            {"$set": gate_doc},
            upsert=True,
        )
        gates.append(
            {
                "id": gate_id,
                "gate_number": gate_num,
                "gate_name": gate_name,
                "status": "pending",
            }
        )
    return gates


async def get_quality_gates(project_id: str) -> list[dict]:
    """Get all quality gates for a project."""
    cursor = db.db[COL_QUALITY_GATES].find(
        {"project_id": project_id}
    ).sort("gate_number", 1)
    return [doc async for doc in cursor]


async def update_gate_status(
    gate_id: str,
    status: str,
    results: dict | None = None,
    evidence: dict | None = None,
) -> None:
    """Update a quality gate's status and results."""
    now = datetime.utcnow().isoformat()
    updates: dict = {"status": status}

    if status == "running":
        updates["started_at"] = now
    elif status in ("passed", "failed", "skipped"):
        updates["completed_at"] = now

    if results is not None:
        updates["results"] = results
    if evidence is not None:
        updates["evidence"] = evidence

    await db.db[COL_QUALITY_GATES].update_one({"id": gate_id}, {"$set": updates})


# ─── Defects ───────────────────────────────────────────────────────────

async def create_defect(
    project_id: str,
    category: str,
    severity: str,
    evidence: str,
    gate_id: str | None = None,
    file_path: str | None = None,
    line_start: int | None = None,
    line_end: int | None = None,
    root_cause: str | None = None,
    assigned_agent: str | None = None,
) -> str:
    """Create a new defect record."""
    if category not in DEFECT_CATEGORIES:
        raise ValueError(f"Invalid defect category: {category}")
    if severity not in DEFECT_SEVERITIES:
        raise ValueError(f"Invalid defect severity: {severity}")

    defect_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    defect_doc = {
        "id": defect_id,
        "project_id": project_id,
        "gate_id": gate_id,
        "category": category,
        "severity": severity,
        "file_path": file_path,
        "line_start": line_start,
        "line_end": line_end,
        "evidence": evidence,
        "root_cause": root_cause,
        "assigned_agent": assigned_agent,
        "status": "open",
        "created_at": now,
        "resolved_at": None,
    }

    await db.db[COL_DEFECTS].insert_one(defect_doc)
    return defect_id


async def get_defects(
    project_id: str,
    status: str | None = None,
    severity: str | None = None,
) -> list[dict]:
    """Get defects for a project with optional filters."""
    query: dict = {"project_id": project_id}
    if status:
        query["status"] = status
    if severity:
        query["severity"] = severity

    cursor = db.db[COL_DEFECTS].find(query).sort("created_at", -1)
    return [doc async for doc in cursor]


async def update_defect_status(
    defect_id: str,
    status: str,
    root_cause: str | None = None,
    assigned_agent: str | None = None,
    repair_id: str | None = None,
) -> None:
    """Update defect status and related fields."""
    updates: dict = {"status": status}

    if root_cause is not None:
        updates["root_cause"] = root_cause
    if assigned_agent is not None:
        updates["assigned_agent"] = assigned_agent
    if repair_id is not None:
        updates["repair_id"] = repair_id
    if status in ("verified", "closed"):
        updates["resolved_at"] = datetime.utcnow().isoformat()

    await db.db[COL_DEFECTS].update_one({"id": defect_id}, {"$set": updates})


# ─── Global Repair Registry ────────────────────────────────────────────

async def find_repair_pattern(error_fingerprint: str) -> dict | None:
    """Find a repair pattern by error fingerprint."""
    return await db.db[COL_REPAIR_REGISTRY].find_one(
        {"error_fingerprint": error_fingerprint, "is_global": True}
    )


async def find_repair_patterns_by_category(
    category: str, technologies: list[str] | None = None
) -> list[dict]:
    """Find repair patterns by category and optional technology filter."""
    query: dict = {"error_category": category, "is_global": True}

    if technologies:
        tech_conditions = []
        for t in technologies:
            tech_conditions.append({"technologies": t})
        query["$or"] = tech_conditions

    cursor = db.db[COL_REPAIR_REGISTRY].find(query).sort(
        [("confidence", -1), ("success_count", -1)]
    )
    return [doc async for doc in cursor]


async def create_repair_pattern(
    error_fingerprint: str,
    error_category: str,
    technologies: list[str],
    root_cause: str,
    solution_pattern: str,
    validation_method: str,
    regression_test: dict | None = None,
    confidence: float = 0.5,
    is_global: bool = True,
) -> str:
    """Create or update a repair pattern in the global registry."""
    pattern_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    pattern_doc = {
        "id": pattern_id,
        "error_fingerprint": error_fingerprint,
        "error_category": error_category,
        "technologies": technologies,
        "root_cause": root_cause,
        "solution_pattern": solution_pattern,
        "validation_method": validation_method,
        "regression_test": regression_test,
        "confidence": confidence,
        "is_global": is_global,
        "created_at": now,
        "last_verified_at": now,
    }

    await db.db[COL_REPAIR_REGISTRY].update_one(
        {"error_fingerprint": error_fingerprint},
        {
            "$setOnInsert": {
                "id": pattern_id,
                "error_fingerprint": error_fingerprint,
                "error_category": error_category,
                "technologies": technologies,
                "root_cause": root_cause,
                "solution_pattern": solution_pattern,
                "validation_method": validation_method,
                "regression_test": regression_test,
                "success_count": 0,
                "failure_count": 0,
                "confidence": confidence,
                "is_global": is_global,
                "created_at": now,
                "last_verified_at": now,
            },
            "$set": {
                "last_verified_at": now,
                "confidence": max(confidence, 0.0),
            },
            "$inc": {"success_count": 1},
        },
        upsert=True,
    )
    return pattern_id


async def update_repair_outcome(pattern_id: str, success: bool) -> None:
    """Update success/failure counts for a repair pattern."""
    now = datetime.utcnow().isoformat()
    if success:
        await db.db[COL_REPAIR_REGISTRY].update_one(
            {"id": pattern_id},
            {
                "$inc": {"success_count": 1},
                "$set": {"last_verified_at": now},
            },
        )
    else:
        await db.db[COL_REPAIR_REGISTRY].update_one(
            {"id": pattern_id},
            {"$inc": {"failure_count": 1}},
        )


# ─── Project Repair History ────────────────────────────────────────────

async def record_repair_attempt(
    project_id: str,
    defect_id: str,
    repair_registry_id: str | None = None,
    patch_applied: str | None = None,
    validation_result: dict | None = None,
    success: bool = False,
) -> str:
    """Record a repair attempt in project history."""
    history_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    history_doc = {
        "id": history_id,
        "project_id": project_id,
        "defect_id": defect_id,
        "repair_registry_id": repair_registry_id,
        "patch_applied": patch_applied,
        "validation_result": validation_result or {},
        "success": success,
        "applied_at": now,
    }

    await db.db[COL_PROJECT_REPAIR_HISTORY].insert_one(history_doc)
    return history_id


async def get_project_repair_history(project_id: str) -> list[dict]:
    """Get all repair attempts for a project."""
    cursor = (
        db.db[COL_PROJECT_REPAIR_HISTORY]
        .find({"project_id": project_id})
        .sort("applied_at", -1)
    )
    return [doc async for doc in cursor]


# ─── Regression Rules ──────────────────────────────────────────────────

async def create_regression_rule(
    repair_registry_id: str,
    rule_type: str,
    rule_config: dict,
) -> str:
    """Create a regression prevention rule from a verified repair pattern."""
    rule_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    rule_doc = {
        "id": rule_id,
        "repair_registry_id": repair_registry_id,
        "rule_type": rule_type,
        "rule_config": rule_config,
        "active": True,
        "created_at": now,
    }

    await db.db[COL_REGRESSION_RULES].insert_one(rule_doc)
    return rule_id


async def get_active_regression_rules(rule_type: str | None = None) -> list[dict]:
    """Get all active regression rules, optionally filtered by type."""
    query: dict = {"active": True}
    if rule_type:
        query["rule_type"] = rule_type

    cursor = db.db[COL_REGRESSION_RULES].find(query).sort("created_at", -1)
    return [doc async for doc in cursor]


# ─── Project Quality Specification ─────────────────────────────────────

async def create_quality_spec(
    project_id: str,
    spec_data: dict,
    version: int = 1,
) -> str:
    """Create or update a project quality specification."""
    spec_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    spec_doc = {
        "id": spec_id,
        "project_id": project_id,
        "version": version,
        "user_requirements": spec_data.get("user_requirements"),
        "application_type": spec_data.get("application_type"),
        "technology_stack": spec_data.get("technology_stack", {}),
        "project_architecture": spec_data.get("project_architecture"),
        "design_specification": spec_data.get("design_specification"),
        "component_requirements": spec_data.get("component_requirements", {}),
        "api_contracts": spec_data.get("api_contracts", {}),
        "data_models": spec_data.get("data_models", {}),
        "responsive_requirements": spec_data.get("responsive_requirements"),
        "security_requirements": spec_data.get("security_requirements"),
        "performance_expectations": spec_data.get("performance_expectations"),
        "functional_acceptance_criteria": spec_data.get(
            "functional_acceptance_criteria", []
        ),
        "testing_requirements": spec_data.get("testing_requirements", []),
        "deployment_constraints": spec_data.get("deployment_constraints"),
        "created_at": now,
        "updated_at": now,
    }

    await db.db[COL_PROJECT_QUALITY_SPECS].update_one(
        {"project_id": project_id, "version": version},
        {"$set": spec_doc},
        upsert=True,
    )
    return spec_id


async def get_quality_spec(
    project_id: str, version: Optional[int] = None
) -> dict | None:
    """Get the quality specification for a project."""
    query: dict = {"project_id": project_id}
    if version:
        query["version"] = version
    else:
        result = await db.db[COL_PROJECT_QUALITY_SPECS].find(
            query
        ).sort("version", -1).limit(1).to_list(length=1)
        return result[0] if result else None

    return await db.db[COL_PROJECT_QUALITY_SPECS].find_one(query)


# ─── Dashboard Aggregates ──────────────────────────────────────────────

async def get_project_quality_summary(project_id: str) -> dict:
    """Get aggregated quality status for dashboard."""
    gates_cursor = db.db[COL_QUALITY_GATES].find(
        {"project_id": project_id}
    ).sort("gate_number", 1)
    gates = [doc async for doc in gates_cursor]

    severity_pipeline = [
        {"$match": {"project_id": project_id}},
        {"$group": {"_id": "$severity", "count": {"$sum": 1}}},
    ]
    severity_rows = await db.db[COL_DEFECTS].aggregate(severity_pipeline).to_list(None)

    status_pipeline = [
        {"$match": {"project_id": project_id}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ]
    status_rows = await db.db[COL_DEFECTS].aggregate(status_pipeline).to_list(None)

    repairs_cursor = (
        db.db[COL_PROJECT_REPAIR_HISTORY]
        .find({"project_id": project_id})
        .sort("applied_at", -1)
        .limit(20)
    )
    repairs = [doc async for doc in repairs_cursor]

    enriched_repairs = []
    for r in repairs:
        defect = await db.db[COL_DEFECTS].find_one({"id": r["defect_id"]})
        enriched_repairs.append(
            {
                **r,
                "defect_category": defect["category"] if defect else None,
                "defect_severity": defect["severity"] if defect else None,
            }
        )

    return {
        "gates": gates,
        "defect_counts": {r["_id"]: r["count"] for r in severity_rows},
        "defect_statuses": {r["_id"]: r["count"] for r in status_rows},
        "recent_repairs": enriched_repairs,
    }


async def get_global_registry_stats() -> dict:
    """Get global repair registry statistics for dashboard."""
    total_row = await db.db[COL_REPAIR_REGISTRY].count_documents({"is_global": True})

    category_pipeline = [
        {"$match": {"is_global": True}},
        {"$group": {"_id": "$error_category", "count": {"$sum": 1}}},
    ]
    cat_rows = await db.db[COL_REPAIR_REGISTRY].aggregate(category_pipeline).to_list(None)

    verified_count = await db.db[COL_REPAIR_REGISTRY].count_documents(
        {"is_global": True, "confidence": {"$gt": 0.7}, "success_count": {"$gt": 0}}
    )

    return {
        "total_patterns": total_row,
        "by_category": {r["_id"]: r["count"] for r in cat_rows},
        "verified_patterns": verified_count,
    }
