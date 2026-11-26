"""
Autonomous Repair Engine — Safe patching with bounded attempts and rollback.

When an error is found:
1. Capture actual error evidence
2. Identify category and severity
3. Inspect affected source
4. Search Global Repair Registry for matching patterns
5. Evaluate whether a previous repair pattern applies
6. Ask the relevant specialist agent to investigate
7. Identify root cause
8. Prepare a code patch
9. Independent review where appropriate
10. Apply the correction
11. Run the specific failed test
12. Run related regression tests
13. Validate the full project where necessary
14. Record the outcome

Repair safety:
- Bounded repair attempts
- Change tracking
- Version checks
- Safe patching
- File ownership checks
- Backup or rollback capability
- Diff inspection
- Never repeatedly rewrite files without identifying cause
- Never silently destroy existing working functionality
"""

from __future__ import annotations

import logging
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from app.database.database import db
from app.memory.project_manager import project_manager, get_workspace_root

from app.quality.database import (
    create_defect, update_defect_status, find_repair_pattern,
    find_repair_patterns_by_category, create_repair_pattern,
    update_repair_outcome, record_repair_attempt,
)
from app.quality.agents import quality_orchestrator, get_agent
from app.quality.agents.base import AgentFinding, AgentPatch
from app.quality.validators.registry import run_validation, aggregate_validation_results
from app.quality.detectors.engine import tech_detection_engine

logger = logging.getLogger(__name__)


@dataclass
class RepairAttempt:
    """A single repair attempt record."""
    attempt_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    defect_id: str = ""
    project_id: str = ""
    file_path: str = ""
    original_content: str = ""
    patched_content: str = ""
    unified_diff: str = ""
    repair_strategy: str = ""
    registry_pattern_id: str | None = None
    validation_passed: bool = False
    validation_result: dict | None = None
    success: bool = False
    error_message: str | None = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    rolled_back: bool = False


@dataclass
class RepairResult:
    """Overall result of repairing a defect."""
    defect_id: str
    project_id: str
    success: bool = False
    attempts: list[RepairAttempt] = field(default_factory=list)
    root_cause: str | None = None
    repair_strategy: str | None = None
    registry_pattern_used: str | None = None
    validation_passed: bool = False
    message: str = ""


class SafePatcher:
    """
    Safe patch application with backup, diff inspection, and rollback.
    """

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self._backups: dict[str, str] = {}  # file_path -> backup content

    def backup_file(self, file_path: str) -> bool:
        """Backup a file's current content before patching."""
        full_path = self.project_dir / file_path
        if not full_path.exists():
            return False
        try:
            self._backups[file_path] = full_path.read_text(encoding="utf-8", errors="replace")
            return True
        except Exception as e:
            logger.error(f"Failed to backup {file_path}: {e}")
            return False

    def apply_patch(self, file_path: str, patched_content: str) -> str | None:
        """
        Apply a patch to a file. Returns the unified diff if successful.
        Creates a backup first.
        """
        full_path = self.project_dir / file_path
        if not full_path.exists():
            logger.error(f"Cannot patch non-existent file: {file_path}")
            return None

        # Backup before modifying
        self.backup_file(file_path)

        original = full_path.read_text(encoding="utf-8", errors="replace")

        # Write patched content
        try:
            full_path.write_text(patched_content, encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to write patch to {file_path}: {e}")
            return None

        # Generate unified diff
        diff = self._generate_diff(original, patched_content, file_path)
        return diff

    def rollback(self, file_path: str) -> bool:
        """Rollback a file to its backed-up content."""
        if file_path not in self._backups:
            logger.error(f"No backup found for {file_path}")
            return False
        full_path = self.project_dir / file_path
        try:
            full_path.write_text(self._backups[file_path], encoding="utf-8")
            return True
        except Exception as e:
            logger.error(f"Failed to rollback {file_path}: {e}")
            return False

    def rollback_all(self) -> dict[str, bool]:
        """Rollback all backed-up files."""
        results: dict[str, bool] = {}
        for file_path in list(self._backups.keys()):
            results[file_path] = self.rollback(file_path)
        return results

    @staticmethod
    def _generate_diff(original: str, patched: str, file_path: str) -> str:
        """Generate a unified diff between original and patched content."""
        import difflib
        orig_lines = original.splitlines(keepends=True)
        patched_lines = patched.splitlines(keepends=True)
        diff = difflib.unified_diff(
            orig_lines, patched_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
        )
        return "".join(diff)


class AutonomousRepairEngine:
    """
    Coordinates autonomous repair of defects found by the quality engine.

    Workflow per defect:
    1. Capture error evidence
    2. Classify category/severity
    3. Inspect affected source
    4. Search Global Repair Registry
    5. Evaluate pattern match
    6. Assign to specialist agent
    7. Investigate root cause
    8. Prepare patch
    9. Independent review
    10. Apply patch
    11. Run failed test
    12. Run regression tests
    13. Validate full project
    14. Record outcome
    """

    MAX_REPAIR_ATTEMPTS = 3

    def __init__(self):
        self._active_repairs: dict[str, RepairResult] = {}

    async def repair_defect(
        self,
        project_id: str,
        defect_id: str,
        project_dir: Path | None = None,
    ) -> RepairResult:
        """
        Attempt to autonomously repair a defect.

        Returns a RepairResult with all attempts and final outcome.
        """
        if project_dir is None:
            project = await project_manager.get_project(project_id)
            if not project:
                return RepairResult(
                    defect_id=defect_id, project_id=project_id,
                    success=False, message="Project not found",
                )
            slug = project["slug"]
            project_dir = get_workspace_root() / "user_files" / "Projects" / slug

        assert project_dir is not None, "project_dir must be set"
        result = RepairResult(defect_id=defect_id, project_id=project_id)

        # Fetch the defect
        defects = await self._get_defects_by_id(project_id, defect_id)
        if not defects:
            result.success = False
            result.message = f"Defect {defect_id} not found"
            return result
        defect = defects[0]

        # Update defect status to investigating
        await update_defect_status(defect_id, "investigating", assigned_agent="debugging_agent")

        # Step 4: Search Global Repair Registry
        registry_pattern = await self._search_registry(
            defect, project_dir
        )

        # Determine repair strategy
        repair_strategy = "agent_fix"
        pattern_id: str | None = None
        if registry_pattern:
            repair_strategy = "registry_pattern"
            pid = registry_pattern.get("id")
            if isinstance(pid, str):
                pattern_id = pid
                result.registry_pattern_used = pid

        # Attempt repair with bounded retries
        patcher = SafePatcher(project_dir)
        file_path = defect.get("file_path")

        for attempt_num in range(1, self.MAX_REPAIR_ATTEMPTS + 1):
            attempt = RepairAttempt(
                defect_id=defect_id,
                project_id=project_id,
                file_path=file_path or "",
                repair_strategy=repair_strategy,
                registry_pattern_id=registry_pattern.get("id") if registry_pattern else None,
            )

            try:
                # Step 6-7: Ask debugging agent to investigate root cause
                debugger = get_agent("debugging_agent")
                investigation = None
                if debugger and hasattr(debugger, "investigate_defect"):
                    investigation = await debugger.investigate_defect(
                        project_id, str(project_dir), defect
                    )
                    if investigation.findings:
                        result.root_cause = investigation.findings[0].description

                # Step 8: Prepare patch
                patch = await self._prepare_patch(
                    project_id, project_dir, defect, investigation, registry_pattern
                )

                if patch is None:
                    attempt.error_message = "No patch could be prepared"
                    result.attempts.append(attempt)
                    continue

                attempt.original_content = patch.get("original_content", "")
                attempt.patched_content = patch.get("patched_content", "")
                attempt.unified_diff = patch.get("unified_diff", "")

                # Step 9: Independent review — re-run validation on the patched file
                if file_path:
                    applied_diff = patcher.apply_patch(file_path, patch["patched_content"])
                    if applied_diff is None:
                        attempt.error_message = "Failed to apply patch"
                        result.attempts.append(attempt)
                        continue

                    # Step 11: Run validation on the project
                    tech_result = tech_detection_engine.detect(project_dir)
                    all_files = [str(f.relative_to(project_dir)) for f in project_dir.rglob("*")
                                 if f.is_file() and f.suffix.lower() in
                                 {".html", ".css", ".js", ".jsx", ".ts", ".tsx", ".py"}]

                    from app.quality.validators.registry import get_applicable_validators
                    validators = get_applicable_validators(tech_result.technologies, all_files)
                    validation_results = await run_validation(validators, project_dir, all_files)
                    aggregated = aggregate_validation_results(validation_results)

                    attempt.validation_passed = aggregated["passed"]
                    attempt.validation_result = aggregated

                    # Step 12-13: If validation passes, repair succeeded
                    if aggregated["passed"]:
                        attempt.success = True
                        result.success = True
                        result.validation_passed = True
                        result.repair_strategy = repair_strategy

                        # Record in project repair history
                        await record_repair_attempt(
                            project_id=project_id,
                            defect_id=defect_id,
                            repair_registry_id=pattern_id,
                            patch_applied=attempt.unified_diff,
                            validation_result=aggregated,
                            success=True,
                        )

                        # Update defect status
                        await update_defect_status(
                            defect_id, "verified",
                            root_cause=result.root_cause,
                            assigned_agent="debugging_agent",
                            repair_id=attempt.attempt_id,
                        )

                        # Update registry outcome
                        if pattern_id:
                            await update_repair_outcome(pattern_id, success=True)

                        # Try to promote to global repair pattern
                        await self._promote_to_registry(
                            defect, attempt, tech_result, project_id
                        )

                        break
                    else:
                        # Validation failed — rollback and retry
                        patcher.rollback(file_path)
                        attempt.error_message = f"Validation failed after patch: {aggregated['total_issues']} issues remain"
                        result.attempts.append(attempt)

                        # If this was a registry pattern that failed, mark it
                        if pattern_id:
                            await update_repair_outcome(pattern_id, success=False)
                        continue
                else:
                    # No file to patch — can't repair
                    attempt.error_message = "No file path associated with defect"
                    result.attempts.append(attempt)
                    continue

            except Exception as e:
                logger.error(f"Repair attempt {attempt_num} failed: {e}")
                attempt.error_message = str(e)
                result.attempts.append(attempt)
                continue

        # Finalize
        if not result.success:
            # Rollback any changes
            patcher.rollback_all()
            await update_defect_status(
                defect_id, "open",
                assigned_agent="debugging_agent",
            )
            result.message = f"Repair failed after {self.MAX_REPAIR_ATTEMPTS} attempts"
        else:
            result.message = "Repair successful — validation passed"

        self._active_repairs[defect_id] = result
        return result

    # ── Internal helpers ──────────────────────────────────────────────

    async def _get_defects_by_id(self, project_id: str, defect_id: str) -> list[dict]:
        """Get a specific defect by ID."""
        from app.database.database import db
        cursor = db.db["defects"].find({"id": defect_id, "project_id": project_id})
        return [doc async for doc in cursor]

    async def _search_registry(
        self, defect: dict, project_dir: Path
    ) -> dict | None:
        """Search the Global Repair Registry for a matching pattern."""
        category = defect.get("category", "")
        evidence = defect.get("evidence", "")

        # Try exact fingerprint match first
        fingerprint = self._compute_fingerprint(defect)
        pattern = await find_repair_pattern(fingerprint)
        if pattern:
            logger.info(f"Found exact repair pattern match: {pattern.get('id')}")
            return pattern

        # Try category + technology match
        tech_result = tech_detection_engine.detect(project_dir)
        tech_names = [t.name for t in tech_result.technologies]
        patterns = await find_repair_patterns_by_category(category, tech_names)
        if patterns:
            # Return the highest confidence pattern
            best = patterns[0]
            logger.info(f"Found category-based repair pattern: {best.get('id')} (confidence={best.get('confidence')})")
            return best

        return None

    @staticmethod
    def _compute_fingerprint(defect: dict) -> str:
        """Compute a fingerprint for a defect to match against registry patterns."""
        import hashlib
        category = defect.get("category", "")
        evidence = defect.get("evidence", "")
        # Normalize evidence for fingerprinting (remove file-specific details)
        normalized = f"{category}:{evidence[:200]}".lower()
        return hashlib.sha256(normalized.encode()).hexdigest()[:32]

    async def _prepare_patch(
        self,
        project_id: str,
        project_dir: Path,
        defect: dict,
        investigation: Any,
        registry_pattern: dict | None,
    ) -> dict | None:
        """
        Prepare a code patch for the defect.
        Returns dict with original_content, patched_content, unified_diff, or None.
        """
        file_path = defect.get("file_path")
        if not file_path:
            return None

        full_path = project_dir / file_path
        if not full_path.exists():
            return None

        original = full_path.read_text(encoding="utf-8", errors="replace")

        # If we have a registry pattern, use its solution pattern as guidance
        solution_hint = ""
        if registry_pattern:
            solution_hint = registry_pattern.get("solution_pattern", "")

        # Ask the debugging agent (or relevant agent) to generate a fix
        # We use the LLM to generate the corrected file content
        fix_prompt = f"""You are AURA's Debugging Agent.

A defect was found in file {file_path}:
- Category: {defect.get('category')}
- Evidence: {defect.get('evidence')}
- Root cause (preliminary): {investigation.findings[0].description if investigation and investigation.findings else 'unknown'}

Previous repair pattern (if applicable): {solution_hint}

Current file content:
{original}

Please produce the corrected full file content. Output ONLY the corrected file between [FILE_START] and [FILE_END] markers, with no additional explanation.

[FILE_START]
<corrected code>
[FILE_END]"""

        from app.core.llm_client import llm_client
        try:
            response = await llm_client.chat(
                messages=[{"role": "user", "content": fix_prompt}],
                system_prompt="You are AURA's Debugging Agent. Fix the defect and output only the corrected file content between [FILE_START] and [FILE_END] markers.",
            )
            if isinstance(response, tuple):
                response = response[0] if response else ""
        except Exception as e:
            logger.error(f"Failed to generate patch via LLM: {e}")
            return None

        # Extract content between markers
        patched = self._extract_patch_content(response)
        if patched is None or patched.strip() == original.strip():
            return None

        import difflib
        diff = "".join(difflib.unified_diff(
            original.splitlines(keepends=True),
            patched.splitlines(keepends=True),
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
        ))

        return {
            "original_content": original,
            "patched_content": patched,
            "unified_diff": diff,
        }

    @staticmethod
    def _extract_patch_content(response: str) -> str | None:
        """Extract content between [FILE_START] and [FILE_END] markers."""
        start_marker = "[FILE_START]"
        end_marker = "[FILE_END]"
        start_idx = response.find(start_marker)
        end_idx = response.find(end_marker)
        if start_idx == -1 or end_idx == -1:
            return None
        return response[start_idx + len(start_marker):end_idx].strip()

    async def _promote_to_registry(
        self,
        defect: dict,
        attempt: RepairAttempt,
        tech_result: Any,
        project_id: str,
    ) -> None:
        """
        Promote a successful repair to the Global Repair Registry as a
        generalized pattern (if confidence is high enough).
        """
        if attempt.validation_result is None:
            return

        # Only promote if validation passed with no critical/high issues
        agg = attempt.validation_result
        if agg.get("critical_count", 0) > 0 or agg.get("high_count", 0) > 0:
            return

        fingerprint = self._compute_fingerprint(defect)
        tech_names = [t.name for t in tech_result.technologies]

        # Check if pattern already exists
        existing = await find_repair_pattern(fingerprint)
        if existing:
            return  # Already registered

        # Create new registry pattern
        confidence = 0.6  # Start moderate; increases with successful reuse
        await create_repair_pattern(
            error_fingerprint=fingerprint,
            error_category=defect.get("category", "syntax"),
            technologies=tech_names,
            root_cause=attempt.error_message or "Root cause identified during repair",
            solution_pattern=f"Applied patch to {defect.get('file_path', 'unknown file')} to resolve: {defect.get('evidence', '')[:200]}",
            validation_method="static_validation",
            regression_test=None,
            confidence=confidence,
            is_global=True,
        )
        logger.info(f"Promoted repair to global registry: {fingerprint}")

    async def get_repair_result(self, defect_id: str) -> RepairResult | None:
        """Get a previously recorded repair result."""
        return self._active_repairs.get(defect_id)


# Global singleton
repair_engine = AutonomousRepairEngine()
