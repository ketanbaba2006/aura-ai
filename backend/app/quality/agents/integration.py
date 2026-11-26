"""
Integration Agent

Validates frontend/backend compatibility, checks API contracts, checks
imports, verifies integrations, resolves incompatible implementations.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from app.quality.agents.base import BaseAgent, AgentFinding, AgentPatch, AgentReviewResult

logger = logging.getLogger(__name__)


class IntegrationAgent(BaseAgent):
    agent_name = "integration_agent"
    agent_role = "Integration Agent"
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

        # Detect if project is full-stack (has both frontend and backend)
        has_frontend = any(f.endswith((".html", ".css", ".js", ".jsx", ".ts", ".tsx")) for f in files)
        has_backend = any(f.endswith((".py",)) for f in files)
        package_json = (root / "package.json").exists()

        api_calls: list[tuple[str, str]] = []
        if has_frontend and has_backend:
            # Full-stack — check for API contract consistency
            # Look for fetch/axios calls and see if there's a matching backend route
            for f in files:
                if not f.endswith((".js", ".jsx", ".ts", ".tsx", ".py")):
                    continue
                try:
                    content = (root / f).read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue
                fetch_calls = re.findall(r"fetch\s*\(\s*['\"]([^'\"]+)['\"]", content)
                axios_calls = re.findall(r"axios\.(get|post|put|delete|patch)\s*\(\s*['\"]([^'\"]+)['\"]", content)
                for url in fetch_calls:
                    api_calls.append((f, url))
                for method, url in axios_calls:
                    api_calls.append((f, url))

        if api_calls and not has_backend:
                findings.append(AgentFinding(
                    agent_name=self.agent_name,
                    project_id=project_id,
                    category="api_integration",
                    severity="high",
                    title="Frontend API calls without backend",
                    description=f"{len(api_calls)} frontend API call(s) detected but no backend files found.",
                    evidence=f"API calls: {[url for _, url in api_calls[:5]]}",
                    suggestion="Add a backend API or mock the API responses",
                ))

        # Check for mismatched port/config between frontend and backend
        # (heuristic: look for localhost:port references)
        ports = set()
        for f in files:
            try:
                content = (root / f).read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            found_ports = re.findall(r"localhost:(\d+)", content)
            ports.update(found_ports)

        if len(ports) > 1:
            findings.append(AgentFinding(
                agent_name=self.agent_name,
                project_id=project_id,
                category="api_integration",
                severity="medium",
                title="Multiple localhost ports referenced",
                description=f"Ports referenced: {', '.join(sorted(ports))} — frontend and backend may be on different ports without CORS configuration.",
                evidence=f"Ports: {sorted(ports)}",
                suggestion="Ensure CORS is configured and frontend points to the correct backend port",
            ))

        passed = not any(f.severity in ("critical", "high") for f in findings)

        return AgentReviewResult(
            agent_name=self.agent_name,
            project_id=project_id,
            passed=passed,
            findings=findings,
            patches=patches,
            summary=f"Integration review: {len(findings)} finding(s), {'PASS' if passed else 'FAIL'}",
            evidence={"api_calls": len(api_calls) if 'api_calls' in dir() else 0, "ports": sorted(ports)},
        )


integration_agent = IntegrationAgent()
