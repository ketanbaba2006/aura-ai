"""
Software Architect Agent

Reviews overall architecture, component relationships, dependency decisions,
and structural consistency. Detects architectural inconsistencies before
they become defects.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from app.quality.agents.base import BaseAgent, AgentFinding, AgentPatch, AgentReviewResult

logger = logging.getLogger(__name__)


class SoftwareArchitectAgent(BaseAgent):
    agent_name = "software_architect"
    agent_role = "Software Architect"
    applicable_technologies = [
        "React", "Vue", "Angular", "Svelte", "Next.js", "Nuxt",
        "Python", "Django", "FastAPI", "Flask", "Express", "NestJS",
        "HTML", "CSS", "JavaScript", "TypeScript",
    ]

    async def review(self, project_id: str, project_dir: str,
                     context: dict | None = None) -> AgentReviewResult:
        root = Path(project_dir)
        findings: list[AgentFinding] = []
        patches: list[AgentPatch] = []

        # Scan for architectural red flags
        tech_stack = (context or {}).get("tech_stack", [])
        files = (context or {}).get("files", [])

        # Check for missing entry point
        entry_points = ["index.html", "main.py", "app.py", "server.py", "index.js", "index.ts", "App.tsx", "App.jsx"]
        found_entry = any((root / ep).exists() for ep in entry_points)
        if not found_entry:
            findings.append(AgentFinding(
                agent_name=self.agent_name,
                project_id=project_id,
                category="architecture",
                severity="high",
                title="No application entry point detected",
                description="No index.html, main.py, app.py, server.py, index.js, index.ts, App.tsx, or App.jsx found.",
                evidence="Scanned project root for standard entry points",
                suggestion="Add an application entry point (e.g. index.html for static sites, main.py for Python apps)",
            ))

        # Check for mixed framework indicators (e.g. both React and Vue)
        has_react = "React" in tech_stack
        has_vue = "Vue" in tech_stack
        has_angular = "Angular" in tech_stack
        if sum([has_react, has_vue, has_angular]) > 1:
            findings.append(AgentFinding(
                agent_name=self.agent_name,
                project_id=project_id,
                category="architecture",
                severity="critical",
                title="Multiple frontend frameworks detected",
                description="Project declares multiple competing frontend frameworks (React, Vue, Angular).",
                evidence=f"tech_stack={tech_stack}",
                suggestion="Standardize on a single frontend framework to avoid bundle conflicts and architectural inconsistency",
            ))

        # Check for backend without API route structure
        has_backend = any(t in tech_stack for t in ("Django", "FastAPI", "Flask", "Express", "NestJS", "Python", "Node"))
        if has_backend:
            api_indicators = ["route", "api", "endpoint", "router"]
            has_api_structure = any(
                any(ind in f.lower() for ind in api_indicators) for f in files
            )
            if not has_api_structure:
                findings.append(AgentFinding(
                    agent_name=self.agent_name,
                    project_id=project_id,
                    category="architecture",
                    severity="medium",
                    title="Backend detected without clear API route structure",
                    description="Backend framework present but no route/API files identified.",
                    evidence=f"Backend techs: {[t for t in tech_stack if t in ('Django','FastAPI','Flask','Express','NestJS')]}",
                    suggestion="Organize backend code into route/controller modules with clear API paths",
                ))

        passed = not any(f.severity in ("critical", "high") for f in findings)

        return AgentReviewResult(
            agent_name=self.agent_name,
            project_id=project_id,
            passed=passed,
            findings=findings,
            patches=patches,
            summary=f"Architecture review: {len(findings)} finding(s), {'PASS' if passed else 'FAIL'}",
            evidence={"tech_stack": tech_stack, "entry_point_found": found_entry},
        )


architect_agent = SoftwareArchitectAgent()
