"""
Validator Registry

Maps detected technologies to applicable validators and orchestrates
validation runs across a project.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from app.quality.validators.base import BaseValidator, ValidationResult, ValidationIssue
from app.quality.validators import (
    html_validator, css_validator, js_ts_validator,
    HTMLValidator, CSSValidator, JSTSValidator,
)
from app.quality.detectors import TechnologySignature

logger = logging.getLogger(__name__)

# Technology -> validator IDs mapping
TECH_VALIDATOR_MAP: dict[str, list[str]] = {
    "HTML": ["html_validator"],
    "CSS": ["css_validator"],
    "JavaScript": ["js_ts_validator"],
    "TypeScript": ["js_ts_validator"],
    "React": ["js_ts_validator"],
    "Next.js": ["js_ts_validator"],
    "Vue": ["js_ts_validator"],
    "Nuxt": ["js_ts_validator"],
    "Angular": ["js_ts_validator"],
    "Svelte": ["js_ts_validator"],
    "Python": [],  # Python validator to be added
    "Django": [],  # Django validator to be added
    "FastAPI": [],  # FastAPI validator to be added
    "Flask": [],  # Flask validator to be added
    "Express": [],  # Express validator to be added
    "NestJS": [],  # NestJS validator to be added
}

# All registered validator instances
VALIDATOR_REGISTRY: dict[str, BaseValidator] = {
    "html_validator": html_validator,
    "css_validator": css_validator,
    "js_ts_validator": js_ts_validator,
}


def register_validator(validator: BaseValidator) -> None:
    """Register a validator instance by its validator_id."""
    VALIDATOR_REGISTRY[validator.validator_id] = validator
    logger.info(f"Registered validator: {validator.validator_id}")


def get_validators_for_technologies(
    technologies: list[TechnologySignature],
) -> list[BaseValidator]:
    """Return the list of validator instances applicable to the detected technologies."""
    tech_names = {t.name for t in technologies}
    validator_ids: set[str] = set()

    for tech_name in tech_names:
        if tech_name in TECH_VALIDATOR_MAP:
            validator_ids.update(TECH_VALIDATOR_MAP[tech_name])

    # If no technology-specific validators matched, still run universally applicable ones
    if not validator_ids:
        # html_validator and css_validator apply based on file extensions anyway
        validator_ids = {"html_validator", "css_validator", "js_ts_validator"}

    return [VALIDATOR_REGISTRY[vid] for vid in validator_ids if vid in VALIDATOR_REGISTRY]


def get_applicable_validators(
    technologies: list[TechnologySignature],
    files: list[str],
) -> list[BaseValidator]:
    """Return validators that have at least one applicable file in the project."""
    all_validators = get_validators_for_technologies(technologies)
    applicable: list[BaseValidator] = []
    for v in all_validators:
        if v.filter_files(files):
            applicable.append(v)
    return applicable


async def run_validation(
    validators: list[BaseValidator],
    project_dir: Path,
    files: list[str] | None = None,
) -> dict[str, ValidationResult]:
    """Run all validators concurrently-ish (sequentially for now) and return results keyed by validator_id."""
    target_files = files or []
    results: dict[str, ValidationResult] = {}

    for validator in validators:
        try:
            start = time.time()
            # Filter files applicable to this validator
            applicable_files = validator.filter_files(target_files) if target_files else []
            result = await validator.validate(project_dir, applicable_files)
            result.execution_time_ms = (time.time() - start) * 1000
            results[validator.validator_id] = result
            logger.info(
                f"Validator {validator.validator_id}: passed={result.passed}, "
                f"issues={result.issue_count}, files={len(result.files_checked)}"
            )
        except Exception as e:
            logger.error(f"Validator {validator.validator_id} failed: {e}")
            results[validator.validator_id] = ValidationResult(
                validator_id=validator.validator_id,
                passed=False,
                issues=[
                    ValidationIssue(
                        rule_id="validator-error",
                        category="syntax",
                        severity="critical",
                        message=f"Validator execution failed: {e}",
                        file_path="",
                    )
                ],
            )

    return results


def aggregate_validation_results(
    results: dict[str, ValidationResult],
) -> dict[str, Any]:
    """Aggregate multiple ValidationResult objects into a summary dict."""
    total_issues = sum(r.issue_count for r in results.values())
    total_critical = sum(r.critical_count for r in results.values())
    total_high = sum(r.high_count for r in results.values())
    all_passed = all(r.passed for r in results.values())

    # Collect all issues by category
    issues_by_category: dict[str, list[dict]] = {}
    for vid, result in results.items():
        for issue in result.issues:
            issues_by_category.setdefault(issue.category, []).append({
                "validator": vid,
                "rule_id": issue.rule_id,
                "severity": issue.severity,
                "message": issue.message,
                "file_path": issue.file_path,
                "line_start": issue.line_start,
                "line_end": issue.line_end,
                "suggestion": issue.suggestion,
            })

    return {
        "passed": all_passed,
        "total_issues": total_issues,
        "critical_count": total_critical,
        "high_count": total_high,
        "validators_run": list(results.keys()),
        "validator_results": {
            vid: {
                "passed": r.passed,
                "issue_count": r.issue_count,
                "critical_count": r.critical_count,
                "high_count": r.high_count,
                "files_checked": r.files_checked,
                "execution_time_ms": r.execution_time_ms,
            }
            for vid, r in results.items()
        },
        "issues_by_category": issues_by_category,
    }
