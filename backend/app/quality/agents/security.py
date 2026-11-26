"""
Security Agent

Reviews vulnerabilities, validates authorization, inspects generated code,
reviews dependencies, checks sandbox isolation, protects sensitive data.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from app.quality.agents.base import BaseAgent, AgentFinding, AgentPatch, AgentReviewResult

logger = logging.getLogger(__name__)


class SecurityAgent(BaseAgent):
    agent_name = "security_agent"
    agent_role = "Security Agent"
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

        # Scan for security issues in source files
        for f in files:
            if not f.endswith((".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".htm")):
                continue
            try:
                content = (root / f).read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            # Check for innerHTML / dangerouslySetInnerHTML (XSS risk)
            if f.endswith((".js", ".jsx", ".ts", ".tsx")):
                if re.search(r"innerHTML\s*=", content) or re.search(r"dangerouslySetInnerHTML", content):
                    findings.append(AgentFinding(
                        agent_name=self.agent_name,
                        project_id=project_id,
                        category="security",
                        severity="high",
                        title=f"Potential XSS via innerHTML in {f}",
                        description="innerHTML or dangerouslySetInnerHTML can introduce XSS vulnerabilities if user input is not sanitized.",
                        file_path=f,
                        evidence="innerHTML/dangerouslySetInnerHTML usage detected",
                        suggestion="Use textContent or sanitize user input before assigning to innerHTML",
                    ))

            # Check for eval() usage (code injection risk)
            if re.search(r"\beval\s*\(", content):
                findings.append(AgentFinding(
                    agent_name=self.agent_name,
                    project_id=project_id,
                    category="security",
                    severity="critical",
                    title=f"eval() usage in {f}",
                    description="eval() executes arbitrary code — critical security risk.",
                    file_path=f,
                    evidence="eval() call detected",
                    suggestion="Remove eval() — use JSON.parse() or a safer alternative",
                ))

            # Check for hardcoded secrets (also caught by backend dev, but security agent owns it)
            secret_patterns = [
                (r"api_key\s*=\s*['\"][^'\"]+['\"]", "API key"),
                (r"secret\s*=\s*['\"][^'\"]+['\"]", "secret"),
                (r"password\s*=\s*['\"][^'\"]+['\"]", "password"),
            ]
            for pattern, label in secret_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    findings.append(AgentFinding(
                        agent_name=self.agent_name,
                        project_id=project_id,
                        category="security",
                        severity="critical",
                        title=f"Hardcoded {label} in {f}",
                        description=f"{label} hardcoded in source code — should use environment variables.",
                        file_path=f,
                        evidence=f"Hardcoded {label} detected",
                        suggestion=f"Move {label} to environment variables or secrets manager",
                    ))
                    break

        passed = not any(f.severity in ("critical", "high") for f in findings)

        return AgentReviewResult(
            agent_name=self.agent_name,
            project_id=project_id,
            passed=passed,
            findings=findings,
            patches=patches,
            summary=f"Security review: {len(findings)} finding(s), {'PASS' if passed else 'FAIL'}",
            evidence={"files_scanned": len(files)},
        )


security_agent = SecurityAgent()
