"""
AURA Global Quality Engine (AGQE) — Central Coordinator

Orchestrates:
- Project registration & technology detection
- Quality gate pipeline (12 gates)
- Validator execution
- Defect creation & tracking
- Integration with existing ProjectManager & AgentEngine
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.database.database import db
from app.memory.project_manager import project_manager, get_workspace_root

from app.quality.database import (
    register_quality_project,
    get_quality_project,
    update_quality_project_validation,
    initialize_quality_gates,
    get_quality_gates,
    update_gate_status,
    create_defect,
    get_defects,
    update_defect_status,
    find_repair_pattern,
    find_repair_patterns_by_category,
    create_repair_pattern,
    update_repair_outcome,
    record_repair_attempt,
    create_quality_spec,
    get_quality_spec,
    get_project_quality_summary,
    GATE_DEFINITIONS,
)
from app.quality.detectors.engine import tech_detection_engine, TechnologyDetectionEngine
from app.quality.validators.registry import (
    get_applicable_validators,
    run_validation,
    aggregate_validation_results,
)

logger = logging.getLogger(__name__)


class AGQE:
    """
    AURA Global Quality Engine — single centralized instance.

    Every Coding Studio project automatically registers with this engine.
    """

    def __init__(self):
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the quality engine schema and gate templates."""
        if self._initialized:
            return
        from app.quality.database import initialize_quality_schema
        await initialize_quality_schema()
        self._initialized = True
        logger.info("AGQE initialized")

    # ── Project Lifecycle ─────────────────────────────────────────────

    async def register_project(
        self, project_id: str, project_dir: Path | None = None
    ) -> dict[str, Any]:
        """
        Register a project with the quality engine.
        Runs technology detection and initializes all 12 quality gates.
        """
        await self.initialize()

        # Detect technology stack
        if project_dir is None:
            project_dir = get_workspace_root() / "user_files" / "Projects"
        tech_result = tech_detection_engine.detect(project_dir)

        # Register with quality engine
        qp_id = await register_quality_project(
            project_id=project_id,
            tech_stack={
                "project_type": tech_result.project_type,
                "primary_language": tech_result.primary_language,
                "technologies": [
                    {"name": t.name, "category": t.category, "version": t.version, "confidence": t.confidence}
                    for t in tech_result.technologies
                ],
                "build_commands": tech_result.build_commands,
                "test_commands": tech_result.test_commands,
                "runtime_commands": tech_result.runtime_commands,
                "supported_validators": tech_result.supported_validators,
                "unsupported_checks": tech_result.unsupported_checks,
            },
        )

        # Initialize quality gates
        gates = await initialize_quality_gates(project_id)

        # Create quality specification record (version 1, empty template)
        await create_quality_spec(
            project_id=project_id,
            spec_data={
                "user_requirements": None,
                "application_type": tech_result.project_type,
                "technology_stack": {
                    "project_type": tech_result.project_type,
                    "primary_language": tech_result.primary_language,
                    "technologies": [t.name for t in tech_result.technologies],
                },
                "project_architecture": None,
                "design_specification": None,
                "component_requirements": {},
                "api_contracts": {},
                "data_models": {},
                "responsive_requirements": None,
                "security_requirements": None,
                "performance_expectations": None,
                "functional_acceptance_criteria": [],
                "testing_requirements": [],
                "deployment_constraints": None,
            },
            version=1,
        )

        logger.info(
            f"Project {project_id} registered with AGQE: "
            f"type={tech_result.project_type}, techs={[t.name for t in tech_result.technologies]}"
        )

        return {
            "quality_project_id": qp_id,
            "project_id": project_id,
            "technology_detection": {
                "project_type": tech_result.project_type,
                "primary_language": tech_result.primary_language,
                "technologies": [
                    {"name": t.name, "category": t.category, "confidence": t.confidence}
                    for t in tech_result.technologies
                ],
                "supported_validators": tech_result.supported_validators,
                "unsupported_checks": tech_result.unsupported_checks,
            },
            "quality_gates": gates,
        }

    async def get_project_status(self, project_id: str) -> dict[str, Any]:
        """Get the full quality status for a project (dashboard aggregate)."""
        qp = await get_quality_project(project_id)
        gates = await get_quality_gates(project_id)
        defects = await get_defects(project_id)
        summary = await get_project_quality_summary(project_id)

        return {
            "registered": qp is not None,
            "tech_stack": qp.get("tech_stack") if qp else None,
            "last_validated_at": qp.get("last_validated_at") if qp else None,
            "gates": gates,
            "defects": defects,
            "summary": summary,
        }

    # ── Validation Pipeline ───────────────────────────────────────────

    async def run_static_validation(
        self, project_id: str, project_dir: Path, files: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Run static code validation (Gate 4).
        Detects tech stack if not already registered, selects validators, runs them,
        and creates defects for any issues found.
        """
        # Ensure project is registered
        qp = await get_quality_project(project_id)
        if not qp:
            reg = await self.register_project(project_id, project_dir)
        else:
            reg = None

        # Re-detect tech for validator selection
        tech_result = tech_detection_engine.detect(project_dir)

        # Get applicable validators
        all_files = files or []
        if not all_files:
            # Scan project dir for text files
            exclude_dirs = {".git", "node_modules", "venv", "__pycache__", ".next", "dist", "build"}
            text_extensions = {".html", ".css", ".js", ".jsx", ".ts", ".tsx", ".md", ".json", ".txt", ".py"}
            if project_dir.exists():
                for filepath in sorted(project_dir.rglob("*")):
                    if any(p in filepath.parts for p in exclude_dirs):
                        continue
                    if filepath.is_file() and filepath.suffix.lower() in text_extensions:
                        all_files.append(str(filepath.relative_to(project_dir)))

        validators = get_applicable_validators(tech_result.technologies, all_files)
        if not validators:
            # Still register unsupported status
            await update_gate_status(
                (await self._get_gate_id(project_id, 4)), "skipped",
                results={"reason": "No applicable validators for detected stack"},
                evidence={"tech_stack": tech_result.project_type},
            )
            return {
                "passed": True,
                "message": "No validators available — validation skipped",
                "unsupported": True,
                "tech_stack": tech_result.project_type,
            }

        # Run validation
        results = await run_validation(validators, project_dir, all_files)
        aggregated = aggregate_validation_results(results)

        # Update Gate 4
        gate_id = await self._get_gate_id(project_id, 4)
        await update_gate_status(
            gate_id,
            "passed" if aggregated["passed"] else "failed",
            results=aggregated,
            evidence={"files_checked": all_files, "tech_stack": tech_result.project_type},
        )

        # Create defects for critical/high issues
        for vid, result in results.items():
            for issue in result.issues:
                if issue.severity in ("critical", "high"):
                    await create_defect(
                        project_id=project_id,
                        gate_id=gate_id,
                        category=issue.category,
                        severity=issue.severity,
                        evidence=issue.message,
                        file_path=issue.file_path,
                        line_start=issue.line_start,
                        line_end=issue.line_end,
                        root_cause=None,
                        assigned_agent=None,
                    )

        await update_quality_project_validation(project_id)

        return {
            "passed": aggregated["passed"],
            "total_issues": aggregated["total_issues"],
            "critical_count": aggregated["critical_count"],
            "high_count": aggregated["high_count"],
            "validators_run": aggregated["validators_run"],
            "issues_by_category": aggregated["issues_by_category"],
            "gate_id": gate_id,
            "tech_stack": tech_result.project_type,
        }

    # ── Gate Helpers ──────────────────────────────────────────────────

    async def _get_gate_id(self, project_id: str, gate_number: int) -> str:
        """Get the gate ID for a project+gate number."""
        gates = await get_quality_gates(project_id)
        for g in gates:
            if g["gate_number"] == gate_number:
                return g["id"]
        # Initialize if missing
        await initialize_quality_gates(project_id)
        gates = await get_quality_gates(project_id)
        for g in gates:
            if g["gate_number"] == gate_number:
                return g["id"]
        raise RuntimeError(f"Gate {gate_number} not found for project {project_id}")

    # ── Integration Hook ──────────────────────────────────────────────

    async def on_project_created(self, project_id: str, project_dir: Path | None = None) -> None:
        """
        Call this whenever a new project is created in the Coding Studio.
        Auto-registers the project with AGQE.
        """
        try:
            await self.register_project(project_id, project_dir)
        except Exception as e:
            logger.error(f"Failed to auto-register project {project_id} with AGQE: {e}")


# Global singleton instance
agqe = AGQE()
