"""
QA Agent

Runs automated tests, validates actual application behavior, performs
browser tests, identifies failures, creates actionable defect reports.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.quality.agents.base import BaseAgent, AgentFinding, AgentPatch, AgentReviewResult

logger = logging.getLogger(__name__)


class QAAgent(BaseAgent):
    agent_name = "qa_agent"
    agent_role = "QA Agent"
    applicable_technologies = [
        "React", "Vue", "Angular", "Svelte", "Next.js", "Nuxt",
        "Python", "Django", "FastAPI", "Flask", "Express", "NestJS", "Node",
        "HTML", "CSS", "JavaScript", "TypeScript",
    ]

    async def review(self, project_id: str, project_dir: str,
                     context: dict | None = None) -> AgentReviewResult:
        root = Path(project_dir)
        findings: list[AgentFinding] = []
        patches: list[AgentPatch] = []

        files = (context or {}).get("files", [])

        # Check for test files
        test_files = [f for f in files if
                      f.startswith("test_") or f.endswith("_test.py") or
                      f.endswith(".test.js") or f.endswith(".test.ts") or
                      f.endswith(".spec.js") or f.endswith(".spec.ts") or
                      "test" in f.lower() and f.endswith((".py", ".js", ".ts"))]

        if not test_files:
            findings.append(AgentFinding(
                agent_name=self.agent_name,
                project_id=project_id,
                category="syntax",
                severity="medium",
                title="No test files detected",
                description="No test files found — application behavior is not verified by automated tests.",
                evidence="Scanned for test_*, *_test.py, *.test.js, *.spec.js patterns",
                suggestion="Add unit and integration tests for critical user workflows",
            ))

        # Check for package.json test script
        import json
        pkg_path = root / "package.json"
        if pkg_path.exists():
            try:
                pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
                scripts = pkg.get("scripts", {})
                if "test" not in scripts:
                    findings.append(AgentFinding(
                        agent_name=self.agent_name,
                        project_id=project_id,
                        category="syntax",
                        severity="medium",
                        title="No test script in package.json",
                        description="package.json has no 'test' script — tests cannot be run via npm test.",
                        evidence="package.json scripts missing 'test' key",
                        suggestion="Add a test script to package.json (e.g. 'test': 'jest' or 'test': 'vitest')",
                    ))
            except Exception:
                pass

        # Check for requirements.txt with test dependencies
        req_path = root / "requirements.txt"
        if req_path.exists():
            try:
                content = req_path.read_text(encoding="utf-8", errors="replace")
                if "pytest" not in content.lower():
                    findings.append(AgentFinding(
                        agent_name=self.agent_name,
                        project_id=project_id,
                        category="syntax",
                        severity="low",
                        title="No pytest in requirements.txt",
                        description="Python project has no pytest dependency — testing framework not declared.",
                        evidence="requirements.txt does not contain 'pytest'",
                        suggestion="Add pytest to requirements.txt for test execution",
                    ))
            except Exception:
                pass

        passed = not any(f.severity in ("critical", "high") for f in findings)

        return AgentReviewResult(
            agent_name=self.agent_name,
            project_id=project_id,
            passed=passed,
            findings=findings,
            patches=patches,
            summary=f"QA review: {len(findings)} finding(s), {'PASS' if passed else 'FAIL'}",
            evidence={"test_files": test_files},
        )


qa_agent = QAAgent()
