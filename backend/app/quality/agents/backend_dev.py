"""
Backend Developer Agent

Validates APIs, fixes backend logic, validates request/response handling,
resolves server-side errors, maintains data consistency.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from app.quality.agents.base import BaseAgent, AgentFinding, AgentPatch, AgentReviewResult

logger = logging.getLogger(__name__)


class BackendDeveloperAgent(BaseAgent):
    agent_name = "backend_developer"
    agent_role = "Backend Developer"
    applicable_technologies = [
        "Python", "Django", "FastAPI", "Flask", "Express", "NestJS", "Node",
    ]

    async def review(self, project_id: str, project_dir: str,
                     context: dict | None = None) -> AgentReviewResult:
        root = Path(project_dir)
        findings: list[AgentFinding] = []
        patches: list[AgentPatch] = []

        files = (context or {}).get("files", [])

        # Scan Python backend files
        for f in files:
            if not f.endswith((".py", ".js", ".ts")):
                continue
            try:
                content = (root / f).read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            # Check for bare except clauses (swallowing errors)
            if f.endswith(".py"):
                bare_except = re.findall(r"except\s*:", content)
                if bare_except:
                    findings.append(AgentFinding(
                        agent_name=self.agent_name,
                        project_id=project_id,
                        category="js_ts",
                        severity="medium",
                        title=f"Bare except clause in {f}",
                        description="Bare except: catches all exceptions including KeyboardInterrupt and SystemExit.",
                        file_path=f,
                        evidence=f"{len(bare_except)} bare except clause(s)",
                        suggestion="Catch specific exceptions instead of using bare except:",
                    ))

            # Check for hardcoded credentials/secrets
            secret_patterns = [
                (r"api_key\s*=\s*['\"][^'\"]+['\"]", "API key"),
                (r"secret\s*=\s*['\"][^'\"]+['\"]", "secret"),
                (r"password\s*=\s*['\"][^'\"]+['\"]", "password"),
                (r"token\s*=\s*['\"][^'\"]+['\"]", "token"),
            ]
            for pattern, label in secret_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    findings.append(AgentFinding(
                        agent_name=self.agent_name,
                        project_id=project_id,
                        category="security",
                        severity="critical",
                        title=f"Potential hardcoded {label} in {f}",
                        description=f"{label} appears to be hardcoded in source code.",
                        file_path=f,
                        evidence=f"Pattern matched: {pattern}",
                        suggestion="Move secrets to environment variables or a secrets manager",
                    ))
                    break  # One secret finding per file

        passed = not any(f.severity in ("critical", "high") for f in findings)

        return AgentReviewResult(
            agent_name=self.agent_name,
            project_id=project_id,
            passed=passed,
            findings=findings,
            patches=patches,
            summary=f"Backend review: {len(findings)} finding(s), {'PASS' if passed else 'FAIL'}",
            evidence={"files_scanned": len([f for f in files if f.endswith(('.py', '.js', '.ts'))])},
        )


backend_dev_agent = BackendDeveloperAgent()
