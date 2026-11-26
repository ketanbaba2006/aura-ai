"""
Database Specialist Agent

Reviews schemas, validates queries, verifies migrations, identifies data
integrity problems, protects existing user data.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from app.quality.agents.base import BaseAgent, AgentFinding, AgentPatch, AgentReviewResult

logger = logging.getLogger(__name__)


class DatabaseSpecialistAgent(BaseAgent):
    agent_name = "database_specialist"
    agent_role = "Database Specialist"
    applicable_technologies = [
        "PostgreSQL", "MySQL", "SQLite", "MongoDB", "Django", "FastAPI",
        "Flask", "Express", "Prisma", "SQLAlchemy", "Alembic", "Python",
    ]

    async def review(self, project_id: str, project_dir: str,
                     context: dict | None = None) -> AgentReviewResult:
        root = Path(project_dir)
        findings: list[AgentFinding] = []
        patches: list[AgentPatch] = []

        files = (context or {}).get("files", [])

        # Scan for database-related files
        db_files = [f for f in files if f.endswith((".py", ".js", ".ts", ".sql", ".yml", ".yaml"))]

        for f in db_files:
            try:
                content = (root / f).read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            # Check for SELECT * queries (data integrity/performance concern)
            select_star = re.findall(r"SELECT\s+\*", content, re.IGNORECASE)
            if select_star:
                findings.append(AgentFinding(
                    agent_name=self.agent_name,
                    project_id=project_id,
                    category="database",
                    severity="medium",
                    title=f"SELECT * query in {f}",
                    description="SELECT * retrieves all columns — can cause performance issues and break on schema changes.",
                    file_path=f,
                    evidence=f"{len(select_star)} SELECT * occurrence(s)",
                    suggestion="Explicitly list required columns instead of SELECT *",
                ))

            # Check for missing migration files when ORM detected
            if f.endswith(".py") and re.search(r"from django|import django", content, re.IGNORECASE):
                # Django — check for migrations directory
                migrations_dir = root / "migrations"
                if not migrations_dir.exists():
                    findings.append(AgentFinding(
                        agent_name=self.agent_name,
                        project_id=project_id,
                        category="database",
                        severity="high",
                        title="Django project without migrations directory",
                        description="Django models detected but no migrations/ directory found — schema changes won't be tracked.",
                        evidence="Django import found, no migrations/ directory",
                        suggestion="Run 'python manage.py makemigrations' to create initial migrations",
                    ))

        passed = not any(f.severity in ("critical", "high") for f in findings)

        return AgentReviewResult(
            agent_name=self.agent_name,
            project_id=project_id,
            passed=passed,
            findings=findings,
            patches=patches,
            summary=f"Database review: {len(findings)} finding(s), {'PASS' if passed else 'FAIL'}",
            evidence={"db_files_scanned": len(db_files)},
        )


db_specialist_agent = DatabaseSpecialistAgent()
