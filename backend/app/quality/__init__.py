"""
AURA AI Global Quality Engine (AGQE)

Centralized, reusable software quality assurance and autonomous repair
infrastructure for every project created through Aura AI Coding Studio.
"""

from app.quality.database import (
    initialize_quality_schema,
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
    get_project_repair_history,
    create_regression_rule,
    get_active_regression_rules,
    create_quality_spec,
    get_quality_spec,
    get_project_quality_summary,
    get_global_registry_stats,
    GATE_DEFINITIONS,
    DEFECT_CATEGORIES,
    DEFECT_SEVERITIES,
)

__all__ = [
    "initialize_quality_schema",
    "register_quality_project",
    "get_quality_project",
    "update_quality_project_validation",
    "initialize_quality_gates",
    "get_quality_gates",
    "update_gate_status",
    "create_defect",
    "get_defects",
    "update_defect_status",
    "find_repair_pattern",
    "find_repair_patterns_by_category",
    "create_repair_pattern",
    "update_repair_outcome",
    "record_repair_attempt",
    "get_project_repair_history",
    "create_regression_rule",
    "get_active_regression_rules",
    "create_quality_spec",
    "get_quality_spec",
    "get_project_quality_summary",
    "get_global_registry_stats",
    "GATE_DEFINITIONS",
    "DEFECT_CATEGORIES",
    "DEFECT_SEVERITIES",
]
