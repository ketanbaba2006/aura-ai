"""
AURA AI Quality Engine — PostgreSQL Schema Extensions

Uses asyncpg to connect to PostgreSQL. All quality engine data
(gates, defects, repair registry, project specifications) lives in
PostgreSQL tables — no MongoDB.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Optional

import asyncpg

from app.config import settings

logger = logging.getLogger(__name__)

# ─── Connection ─────────────────────────────────────────────────────────

_pg_pool: Any = None


async def get_pg_pool() -> Any:
    """Get or create the asyncpg connection pool."""
    global _pg_pool
    if _pg_pool is None:
        database_url = settings.DATABASE_URL or (
            f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
            f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
        )
        _pg_pool = await asyncpg.create_pool(database_url, min_size=1, max_size=10)
        logger.info("PostgreSQL pool created for quality engine")
    return _pg_pool


async def close_pg_pool() -> None:
    """Close the asyncpg connection pool."""
    global _pg_pool
    if _pg_pool is not None:
        await _pg_pool.close()
        _pg_pool = None


# ─── Table Definitions ──────────────────────────────────────────────────

QUALITY_TABLES = {
    "quality_projects": """
        CREATE TABLE IF NOT EXISTS quality_projects (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL UNIQUE,
            tech_stack JSONB NOT NULL DEFAULT '{}',
            spec_version INTEGER NOT NULL DEFAULT 1,
            registered_at TIMESTAMP NOT NULL DEFAULT NOW(),
            last_validated_at TIMESTAMP
        )
    """,
    "quality_gates": """
        CREATE TABLE IF NOT EXISTS quality_gates (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            gate_number INTEGER NOT NULL,
            gate_name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            results JSONB DEFAULT '{}',
            evidence JSONB DEFAULT '{}',
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            UNIQUE(project_id, gate_number)
        )
    """,
    "defects": """
        CREATE TABLE IF NOT EXISTS defects (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            gate_id TEXT,
            category TEXT NOT NULL,
            severity TEXT NOT NULL,
            file_path TEXT,
            line_start INTEGER,
            line_end INTEGER,
            evidence TEXT NOT NULL,
            root_cause TEXT,
            assigned_agent TEXT,
            status TEXT NOT NULL DEFAULT 'open',
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            resolved_at TIMESTAMP
        )
    """,
    "repair_registry": """
        CREATE TABLE IF NOT EXISTS repair_registry (
            id TEXT PRIMARY KEY,
            error_fingerprint TEXT NOT NULL UNIQUE,
            error_category TEXT NOT NULL,
            technologies JSONB NOT NULL DEFAULT '[]',
            root_cause TEXT NOT NULL,
            solution_pattern TEXT NOT NULL,
            validation_method TEXT NOT NULL,
            regression_test JSONB,
            success_count INTEGER NOT NULL DEFAULT 0,
            failure_count INTEGER NOT NULL DEFAULT 0,
            confidence REAL NOT NULL DEFAULT 0.0,
            is_global BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            last_verified_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """,
    "project_repair_history": """
        CREATE TABLE IF NOT EXISTS project_repair_history (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            defect_id TEXT NOT NULL,
            repair_registry_id TEXT,
            patch_applied TEXT,
            validation_result JSONB DEFAULT '{}',
            success BOOLEAN NOT NULL,
            applied_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """,
    "regression_rules": """
        CREATE TABLE IF NOT EXISTS regression_rules (
            id TEXT PRIMARY KEY,
            repair_registry_id TEXT NOT NULL,
            rule_type TEXT NOT NULL,
            rule_config JSONB NOT NULL DEFAULT '{}',
            active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """,
    "project_quality_specs": """
        CREATE TABLE IF NOT EXISTS project_quality_specs (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            user_requirements TEXT,
            application_type TEXT,
            technology_stack JSONB NOT NULL DEFAULT '{}',
            project_architecture TEXT,
            design_specification TEXT,
            component_requirements JSONB DEFAULT '{}',
            api_contracts JSONB DEFAULT '{}',
            data_models JSONB DEFAULT '{}',
            responsive_requirements TEXT,
            security_requirements TEXT,
            performance_expectations TEXT,
            functional_acceptance_criteria JSONB DEFAULT '[]',
            testing_requirements JSONB DEFAULT '[]',
            deployment_constraints TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
            UNIQUE(project_id, version)
        )
    """,
    "verification_codes": """
        CREATE TABLE IF NOT EXISTS verification_codes (
            id TEXT PRIMARY KEY,
            email TEXT NOT NULL,
            code TEXT NOT NULL,
            code_type TEXT NOT NULL DEFAULT 'email_verification',
            expires_at TIMESTAMP NOT NULL,
            used BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """,
}

QUALITY_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_quality_projects_project_id ON quality_projects(project_id)",
    "CREATE INDEX IF NOT EXISTS idx_quality_gates_project_id ON quality_gates(project_id)",
    "CREATE INDEX IF NOT EXISTS idx_quality_gates_status ON quality_gates(status)",
    "CREATE INDEX IF NOT EXISTS idx_defects_project_id ON defects(project_id)",
    "CREATE INDEX IF NOT EXISTS idx_defects_gate_id ON defects(gate_id)",
    "CREATE INDEX IF NOT EXISTS idx_defects_category ON defects(category)",
    "CREATE INDEX IF NOT EXISTS idx_defects_severity ON defects(severity)",
    "CREATE INDEX IF NOT EXISTS idx_defects_status ON defects(status)",
    "CREATE INDEX IF NOT EXISTS idx_defects_file_path ON defects(file_path)",
    "CREATE INDEX IF NOT EXISTS idx_repair_registry_fingerprint ON repair_registry(error_fingerprint)",
    "CREATE INDEX IF NOT EXISTS idx_repair_registry_category ON repair_registry(error_category)",
    "CREATE INDEX IF NOT EXISTS idx_project_repair_history_project_id ON project_repair_history(project_id)",
    "CREATE INDEX IF NOT EXISTS idx_project_repair_history_defect_id ON project_repair_history(defect_id)",
    "CREATE INDEX IF NOT EXISTS idx_regression_rules_registry_id ON regression_rules(repair_registry_id)",
    "CREATE INDEX IF NOT EXISTS idx_project_quality_specs_project_id ON project_quality_specs(project_id)",
    "CREATE INDEX IF NOT EXISTS idx_verification_codes_email ON verification_codes(email)",
    "CREATE INDEX IF NOT EXISTS idx_verification_codes_code ON verification_codes(code)",
    "CREATE INDEX IF NOT EXISTS idx_verification_codes_expires ON verification_codes(expires_at)",
]

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


# ─── Schema Initialization ──────────────────────────────────────────────

async def initialize_quality_schema() -> None:
    """Create all quality engine tables and indexes in PostgreSQL."""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        for table_name, ddl in QUALITY_TABLES.items():
            await conn.execute(ddl)
            logger.debug(f"Ensured table: {table_name}")
        for idx_ddl in QUALITY_INDEXES:
            await conn.execute(idx_ddl)
        logger.info("PostgreSQL quality schema initialized")


def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, default=str)


def _json_loads(val: Any) -> Any:
    if val is None:
        return None
    if isinstance(val, (dict, list)):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, ValueError):
            return val
    return val


def _row_to_dict(row: Any) -> dict:
    """Convert an asyncpg Record to a dict, parsing JSONB fields."""
    d = dict(row)
    json_keys = (
        "tech_stack", "results", "evidence", "component_requirements",
        "api_contracts", "data_models", "functional_acceptance_criteria",
        "testing_requirements", "technology_stack", "regression_test",
        "rule_config", "technologies",
    )
    for key in json_keys:
        if key in d and d[key] is not None and isinstance(d[key], str):
            try:
                d[key] = json.loads(d[key])
            except (json.JSONDecodeError, ValueError):
                pass
    return d


# ─── Verification Codes ─────────────────────────────────────────────────

async def create_verification_code(
    email: str,
    code: str,
    code_type: str = "email_verification",
    ttl_minutes: int = 10,
) -> str:
    """Store a verification code for email verification / password reset."""
    code_id = str(uuid.uuid4())
    expires_at = datetime.utcnow() + __import__("timedelta", fromlist=["timedelta"]).timedelta(minutes=ttl_minutes)
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO verification_codes (id, email, code, code_type, expires_at)
            VALUES ($1, $2, $3, $4, $5)
            """,
            code_id, email.lower(), code, code_type, expires_at
        )
    return code_id


async def verify_code(email: str, code: str, code_type: str = "email_verification") -> bool:
    """Verify a code: marks it used if valid and not expired."""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, used, expires_at FROM verification_codes
            WHERE email = $1 AND code = $2 AND code_type = $3 AND used = FALSE
            ORDER BY created_at DESC LIMIT 1
            """,
            email.lower(), code, code_type
        )
        if not row:
            return False
        if row["expires_at"] and row["expires_at"] < datetime.utcnow():
            return False
        await conn.execute(
            "UPDATE verification_codes SET used = TRUE WHERE id = $1",
            row["id"]
        )
        return True


async def invalidate_verification_codes(email: str, code_type: str) -> None:
    """Mark all unused codes of a type as used (after successful verification)."""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE verification_codes
            SET used = TRUE
            WHERE email = $1 AND code_type = $2 AND used = FALSE
            """,
            email.lower(), code_type
        )


# ─── Quality Project Registration ───────────────────────────────────────

async def register_quality_project(project_id: str, tech_stack: dict) -> str:
    """Register a project with the quality engine. Returns quality_project id."""
    qp_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO quality_projects (id, project_id, tech_stack, registered_at, last_validated_at)
            VALUES ($1, $2, $3, $4, $4)
            ON CONFLICT (project_id) DO UPDATE SET
                tech_stack = EXCLUDED.tech_stack,
                last_validated_at = EXCLUDED.last_validated_at
            """,
            qp_id, project_id, _json_dumps(tech_stack), now
        )
    return qp_id


async def get_quality_project(project_id: str) -> dict | None:
    """Get quality project registration by project_id."""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM quality_projects WHERE project_id = $1", project_id
        )
        if row:
            return _row_to_dict(row)
    return None


async def update_quality_project_validation(project_id: str) -> None:
    """Update last_validated_at timestamp."""
    now = datetime.utcnow().isoformat()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE quality_projects SET last_validated_at = $1 WHERE project_id = $2",
            now, project_id
        )


# ─── Quality Gates ─────────────────────────────────────────────────────

async def initialize_quality_gates(project_id: str) -> list[dict]:
    """Create all 12 quality gates for a project in pending state."""
    gates = []
    now = datetime.utcnow().isoformat()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        for gate_num, gate_name, _ in GATE_DEFINITIONS:
            gate_id = str(uuid.uuid4())
            await conn.execute(
                """
                INSERT INTO quality_gates (id, project_id, gate_number, gate_name, status, created_at)
                VALUES ($1, $2, $3, $4, 'pending', $5)
                ON CONFLICT (project_id, gate_number) DO UPDATE SET
                    status = 'pending'
                """,
                gate_id, project_id, gate_num, gate_name, now
            )
            gates.append(
                {"id": gate_id, "gate_number": gate_num, "gate_name": gate_name, "status": "pending"}
            )
    return gates


async def get_quality_gates(project_id: str) -> list[dict]:
    """Get all quality gates for a project."""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM quality_gates WHERE project_id = $1 ORDER BY gate_number",
            project_id
        )
        return [_row_to_dict(r) for r in rows]


async def update_gate_status(
    gate_id: str,
    status: str,
    results: dict | None = None,
    evidence: dict | None = None,
) -> None:
    """Update a quality gate's status and results."""
    now = datetime.utcnow().isoformat()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        if status == "running":
            await conn.execute(
                """
                UPDATE quality_gates
                SET status = $1, started_at = $2, results = $3, evidence = $4
                WHERE id = $5
                """,
                status, now, _json_dumps(results or {}), _json_dumps(evidence or {}), gate_id
            )
        elif status in ("passed", "failed", "skipped"):
            await conn.execute(
                """
                UPDATE quality_gates
                SET status = $1, completed_at = $2, results = $3, evidence = $4
                WHERE id = $5
                """,
                status, now, _json_dumps(results or {}), _json_dumps(evidence or {}), gate_id
            )
        else:
            await conn.execute(
                """
                UPDATE quality_gates
                SET status = $1, results = $2, evidence = $3
                WHERE id = $4
                """,
                status, _json_dumps(results or {}), _json_dumps(evidence or {}), gate_id
            )


# ─── Defects ───────────────────────────────────────────────────────────

async def create_defect(
    project_id: str,
    category: str,
    severity: str,
    evidence: str,
    gate_id: Optional[str] = None,
    file_path: Optional[str] = None,
    line_start: Optional[int] = None,
    line_end: Optional[int] = None,
    root_cause: Optional[str] = None,
    assigned_agent: Optional[str] = None,
) -> str:
    """Create a new defect record."""
    if category not in DEFECT_CATEGORIES:
        raise ValueError(f"Invalid defect category: {category}")
    if severity not in DEFECT_SEVERITIES:
        raise ValueError(f"Invalid defect severity: {severity}")

    defect_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO defects
            (id, project_id, gate_id, category, severity, file_path,
             line_start, line_end, evidence, root_cause, assigned_agent, status, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, 'open', $12)
            """,
            defect_id, project_id, gate_id, category, severity, file_path,
            line_start, line_end, evidence, root_cause, assigned_agent, now
        )
    return defect_id


async def get_defects(
    project_id: str,
    status: Optional[str] = None,
    severity: Optional[str] = None,
) -> list[dict]:
    """Get defects for a project with optional filters."""
    query = "SELECT * FROM defects WHERE project_id = $1"
    params: list[Any] = [project_id]
    param_idx = 2

    if status:
        query += f" AND status = ${param_idx}"
        params.append(status)
        param_idx += 1
    if severity:
        query += f" AND severity = ${param_idx}"
        params.append(severity)
        param_idx += 1

    query += " ORDER BY created_at DESC"

    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *params)
        return [_row_to_dict(r) for r in rows]


async def update_defect_status(
    defect_id: str,
    status: str,
    root_cause: Optional[str] = None,
    assigned_agent: Optional[str] = None,
    repair_id: Optional[str] = None,
) -> None:
    """Update defect status and related fields."""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        if status in ("verified", "closed"):
            await conn.execute(
                """
                UPDATE defects
                SET status = $1, root_cause = COALESCE($2, root_cause),
                    assigned_agent = COALESCE($3, assigned_agent),
                    repair_id = COALESCE($4, repair_id),
                    resolved_at = $5
                WHERE id = $6
                """,
                status, root_cause, assigned_agent, repair_id,
                datetime.utcnow().isoformat(), defect_id
            )
        else:
            await conn.execute(
                """
                UPDATE defects
                SET status = $1, root_cause = COALESCE($2, root_cause),
                    assigned_agent = COALESCE($3, assigned_agent),
                    repair_id = COALESCE($4, repair_id)
                WHERE id = $5
                """,
                status, root_cause, assigned_agent, repair_id, defect_id
            )


# ─── Global Repair Registry ────────────────────────────────────────────

async def find_repair_pattern(error_fingerprint: str) -> dict | None:
    """Find a repair pattern by error fingerprint."""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM repair_registry WHERE error_fingerprint = $1 AND is_global = TRUE",
            error_fingerprint
        )
        if row:
            return _row_to_dict(row)
    return None


async def find_repair_patterns_by_category(
    category: str, technologies: Optional[list[str]] = None
) -> list[dict]:
    """Find repair patterns by category and optional technology filter."""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        if technologies:
            conditions = " OR ".join(
                [f"technologies @> ${i + 2}::jsonb" for i in range(len(technologies))]
            )
            query = (
                f"SELECT * FROM repair_registry "
                f"WHERE error_category = $1 AND is_global = TRUE AND ({conditions}) "
                f"ORDER BY confidence DESC, success_count DESC"
            )
            json_params = [json.dumps([t]) for t in technologies]
            rows = await conn.fetch(query, category, *json_params)
        else:
            rows = await conn.fetch(
                """
                SELECT * FROM repair_registry
                WHERE error_category = $1 AND is_global = TRUE
                ORDER BY confidence DESC, success_count DESC
                """,
                category
            )
        return [_row_to_dict(r) for r in rows]


async def create_repair_pattern(
    error_fingerprint: str,
    error_category: str,
    technologies: list[str],
    root_cause: str,
    solution_pattern: str,
    validation_method: str,
    regression_test: Optional[dict] = None,
    confidence: float = 0.5,
    is_global: bool = True,
) -> str:
    """Create or update a repair pattern in the global registry."""
    pattern_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO repair_registry
            (id, error_fingerprint, error_category, technologies, root_cause,
             solution_pattern, validation_method, regression_test,
             confidence, is_global, created_at, last_verified_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $11)
            ON CONFLICT (error_fingerprint) DO UPDATE SET
                success_count = repair_registry.success_count + 1,
                last_verified_at = EXCLUDED.last_verified_at,
                confidence = GREATEST(repair_registry.confidence, EXCLUDED.confidence)
            """,
            pattern_id, error_fingerprint, error_category,
            _json_dumps(technologies), root_cause, solution_pattern,
            validation_method, _json_dumps(regression_test) if regression_test else None,
            confidence, is_global, now
        )
    return pattern_id


async def update_repair_outcome(pattern_id: str, success: bool) -> None:
    """Update success/failure counts for a repair pattern."""
    now = datetime.utcnow().isoformat()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        if success:
            await conn.execute(
                """
                UPDATE repair_registry
                SET success_count = success_count + 1, last_verified_at = $1
                WHERE id = $2
                """,
                now, pattern_id
            )
        else:
            await conn.execute(
                """
                UPDATE repair_registry
                SET failure_count = failure_count + 1
                WHERE id = $1
                """,
                pattern_id
            )


# ─── Project Repair History ────────────────────────────────────────────

async def record_repair_attempt(
    project_id: str,
    defect_id: str,
    repair_registry_id: Optional[str] = None,
    patch_applied: Optional[str] = None,
    validation_result: Optional[dict] = None,
    success: bool = False,
) -> str:
    """Record a repair attempt in project history."""
    history_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO project_repair_history
            (id, project_id, defect_id, repair_registry_id, patch_applied,
             validation_result, success, applied_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            history_id, project_id, defect_id, repair_registry_id,
            patch_applied, _json_dumps(validation_result or {}), success, now
        )
    return history_id


async def get_project_repair_history(project_id: str) -> list[dict]:
    """Get all repair attempts for a project."""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM project_repair_history
            WHERE project_id = $1 ORDER BY applied_at DESC
            """,
            project_id
        )
        return [_row_to_dict(r) for r in rows]


# ─── Regression Rules ──────────────────────────────────────────────────

async def create_regression_rule(
    repair_registry_id: str,
    rule_type: str,
    rule_config: dict,
) -> str:
    """Create a regression prevention rule from a verified repair pattern."""
    rule_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO regression_rules
            (id, repair_registry_id, rule_type, rule_config, active, created_at)
            VALUES ($1, $2, $3, $4, TRUE, $5)
            """,
            rule_id, repair_registry_id, rule_type, _json_dumps(rule_config), now
        )
    return rule_id


async def get_active_regression_rules(rule_type: Optional[str] = None) -> list[dict]:
    """Get all active regression rules, optionally filtered by type."""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        if rule_type:
            rows = await conn.fetch(
                """
                SELECT * FROM regression_rules
                WHERE active = TRUE AND rule_type = $1
                ORDER BY created_at DESC
                """,
                rule_type
            )
        else:
            rows = await conn.fetch(
                """
                SELECT * FROM regression_rules
                WHERE active = TRUE
                ORDER BY created_at DESC
                """
            )
        return [_row_to_dict(r) for r in rows]


# ─── Project Quality Specification ─────────────────────────────────────

async def create_quality_spec(
    project_id: str,
    spec_data: dict,
    version: int = 1,
) -> str:
    """Create or update a project quality specification."""
    spec_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO project_quality_specs
            (id, project_id, version, user_requirements, application_type,
             technology_stack, project_architecture, design_specification,
             component_requirements, api_contracts, data_models,
             responsive_requirements, security_requirements,
             performance_expectations, functional_acceptance_criteria,
             testing_requirements, deployment_constraints,
             created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11,
                    $12, $13, $14, $15, $16, $17, $18, $18)
            ON CONFLICT (project_id, version) DO UPDATE SET
                user_requirements = EXCLUDED.user_requirements,
                application_type = EXCLUDED.application_type,
                technology_stack = EXCLUDED.technology_stack,
                project_architecture = EXCLUDED.project_architecture,
                design_specification = EXCLUDED.design_specification,
                component_requirements = EXCLUDED.component_requirements,
                api_contracts = EXCLUDED.api_contracts,
                data_models = EXCLUDED.data_models,
                responsive_requirements = EXCLUDED.responsive_requirements,
                security_requirements = EXCLUDED.security_requirements,
                performance_expectations = EXCLUDED.performance_expectations,
                functional_acceptance_criteria = EXCLUDED.functional_acceptance_criteria,
                testing_requirements = EXCLUDED.testing_requirements,
                deployment_constraints = EXCLUDED.deployment_constraints,
                updated_at = EXCLUDED.updated_at
            """,
            spec_id, project_id, version,
            spec_data.get("user_requirements"),
            spec_data.get("application_type"),
            _json_dumps(spec_data.get("technology_stack", {})),
            spec_data.get("project_architecture"),
            spec_data.get("design_specification"),
            _json_dumps(spec_data.get("component_requirements", {})),
            _json_dumps(spec_data.get("api_contracts", {})),
            _json_dumps(spec_data.get("data_models", {})),
            spec_data.get("responsive_requirements"),
            spec_data.get("security_requirements"),
            spec_data.get("performance_expectations"),
            _json_dumps(spec_data.get("functional_acceptance_criteria", [])),
            _json_dumps(spec_data.get("testing_requirements", [])),
            spec_data.get("deployment_constraints"),
            now
        )
    return spec_id


async def get_quality_spec(
    project_id: str, version: Optional[int] = None
) -> dict | None:
    """Get the quality specification for a project."""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        if version:
            row = await conn.fetchrow(
                "SELECT * FROM project_quality_specs WHERE project_id = $1 AND version = $2",
                project_id, version
            )
        else:
            row = await conn.fetchrow(
                """
                SELECT * FROM project_quality_specs
                WHERE project_id = $1 ORDER BY version DESC LIMIT 1
                """,
                project_id
            )
        if row:
            return _row_to_dict(row)
    return None


# ─── Dashboard Aggregates ──────────────────────────────────────────────

async def get_project_quality_summary(project_id: str) -> dict:
    """Get aggregated quality status for dashboard."""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        gate_rows = await conn.fetch(
            "SELECT * FROM quality_gates WHERE project_id = $1 ORDER BY gate_number",
            project_id
        )
        gates = [_row_to_dict(r) for r in gate_rows]

        severity_rows = await conn.fetch(
            """
            SELECT severity, COUNT(*) as count
            FROM defects WHERE project_id = $1 GROUP BY severity
            """,
            project_id
        )
        defect_counts = {r["severity"]: r["count"] for r in severity_rows}

        status_rows = await conn.fetch(
            """
            SELECT status, COUNT(*) as count
            FROM defects WHERE project_id = $1 GROUP BY status
            """,
            project_id
        )
        defect_statuses = {r["status"]: r["count"] for r in status_rows}

        repair_rows = await conn.fetch(
            """
            SELECT prh.*, d.category as defect_category, d.severity as defect_severity
            FROM project_repair_history prh
            JOIN defects d ON prh.defect_id = d.id
            WHERE prh.project_id = $1
            ORDER BY prh.applied_at DESC LIMIT 20
            """,
            project_id
        )
        recent_repairs = [_row_to_dict(r) for r in repair_rows]

    return {
        "gates": gates,
        "defect_counts": defect_counts,
        "defect_statuses": defect_statuses,
        "recent_repairs": recent_repairs,
    }


async def get_global_registry_stats() -> dict:
    """Get global repair registry statistics for dashboard."""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        total = await conn.fetchval(
            "SELECT COUNT(*) FROM repair_registry WHERE is_global = TRUE"
        )
        cat_rows = await conn.fetch(
            """
            SELECT error_category, COUNT(*) as count
            FROM repair_registry WHERE is_global = TRUE
            GROUP BY error_category
            """
        )
        verified_count = await conn.fetchval(
            """
            SELECT COUNT(*) FROM repair_registry
            WHERE is_global = TRUE AND confidence > 0.7 AND success_count > 0
            """
        )

    return {
        "total_patterns": total,
        "by_category": {r["error_category"]: r["count"] for r in cat_rows},
        "verified_patterns": verified_count,
    }
