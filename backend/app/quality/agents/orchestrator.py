"""
Quality Orchestrator

Coordinates the overall quality lifecycle across specialist agents.
Maintains the task dependency graph, enforces quality gates, assigns
review tasks, monitors quality results, prioritizes defects, and
coordinates repair activities.

Does not require every agent to review every file — dynamically selects
relevant reviewers based on technology stack and file types.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from app.memory.project_manager import project_manager, get_workspace_root
from app.quality.engine import agqe
from app.quality.database import (
    update_gate_status, create_defect, update_defect_status,
    get_defects, get_quality_gates, get_quality_spec,
)
from app.quality.agents.base import BaseAgent, AgentFinding, AgentPatch, AgentReviewResult

logger = logging.getLogger(__name__)

# Agent registry — populated by register_agent()
AGENT_REGISTRY: dict[str, BaseAgent] = {}


def register_agent(agent: BaseAgent) -> None:
    """Register a specialist agent."""
    AGENT_REGISTRY[agent.agent_name] = agent
    logger.info(f"Registered quality agent: {agent.agent_name}")


def get_agent(name: str) -> BaseAgent | None:
    """Get a registered agent by name."""
    return AGENT_REGISTRY.get(name)


def list_agents() -> list[str]:
    """List all registered agent names."""
    return list(AGENT_REGISTRY.keys())


class QualityOrchestrator:
    """
    Central coordinator for the quality lifecycle.

    Responsibilities:
    - Coordinate development across specialist agents
    - Maintain the task dependency graph
    - Enforce quality gates
    - Assign review tasks to relevant agents
    - Monitor quality results
    - Prioritize defects
    - Coordinate repair activities
    - Approve final delivery
    """

    def __init__(self):
        self._initialized = False

    async def initialize(self) -> None:
        if self._initialized:
            return
        await agqe.initialize()
        self._initialized = True
        logger.info("Quality Orchestrator initialized")

    # ── Project Lifecycle ─────────────────────────────────────────────

    async def onboard_project(self, project_id: str,
                              project_dir: Path | None = None) -> dict[str, Any]:
        """
        Onboard a new project into the quality lifecycle.
        Registers with AGQE, initializes gates, creates quality spec v1.
        """
        await self.initialize()
        if project_dir is None:
            project_dir = get_workspace_root() / "user_files" / "Projects"

        result = await agqe.register_project(project_id, project_dir)
        logger.info(f"Project {project_id} onboarded to quality lifecycle")
        return result

    # ── Agent Selection ───────────────────────────────────────────────

    def select_reviewers(self, tech_stack: list[str],
                         file_types: list[str] | None = None,
                         review_scope: str = "full") -> list[str]:
        """
        Dynamically select relevant reviewers for a project/review.
        Does not require every agent to review every file.

        Args:
            tech_stack: Detected technology names.
            file_types: File extensions present (e.g. [".html", ".py"]).
            review_scope: "full", "security", "visual", "code".

        Returns:
            List of agent names to involve.
        """
        selected: list[str] = []

        # Always include architect for architecture review
        if "software_architect" in AGENT_REGISTRY:
            selected.append("software_architect")

        # Security agent for all projects
        if "security_agent" in AGENT_REGISTRY:
            selected.append("security_agent")

        # Technology-specific agents
        tech_lower = {t.lower() for t in tech_stack}

        if any(t in tech_lower for t in ("react", "vue", "angular", "svelte", "html", "javascript", "typescript", "next.js", "nuxt")):
            if "frontend_developer" in AGENT_REGISTRY:
                selected.append("frontend_developer")
            if "ui_designer" in AGENT_REGISTRY:
                selected.append("ui_designer")

        if any(t in tech_lower for t in ("python", "django", "fastapi", "flask", "express", "nestjs", "node")):
            if "backend_developer" in AGENT_REGISTRY:
                selected.append("backend_developer")

        if any(t in tech_lower for t in ("postgresql", "mysql", "sqlite", "mongodb", "django", "fastapi", "flask", "express")):
            if "database_specialist" in AGENT_REGISTRY:
                selected.append("database_specialist")

        # Integration agent for full-stack projects
        if len(tech_stack) > 1 and "integration_agent" in AGENT_REGISTRY:
            selected.append("integration_agent")

        # QA agent for functional testing
        if "qa_agent" in AGENT_REGISTRY:
            selected.append("qa_agent")

        # Debugging agent always available for repair
        if "debugging_agent" in AGENT_REGISTRY:
            selected.append("debugging_agent")

        # Deduplicate while preserving order
        seen: set[str] = set()
        result: list[str] = []
        for name in selected:
            if name not in seen:
                seen.add(name)
                result.append(name)

        logger.info(f"Selected reviewers: {result} for tech_stack={tech_stack}")
        return result

    # ── Review Coordination ───────────────────────────────────────────

    async def run_review_cycle(self, project_id: str,
                               project_dir: Path,
                               tech_stack: list[str],
                               files: list[str] | None = None,
                               reviewers: list[str] | None = None) -> dict[str, Any]:
        """
        Run a coordinated review cycle across selected specialist agents.

        Each agent produces actual findings and patches. Results are
        aggregated and defects are created for critical/high issues.
        """
        await self.initialize()

        if files is None:
            files = []

        if reviewers is None:
            file_exts = [f.rsplit(".", 1)[-1] if "." in f else "" for f in files]
            reviewers = self.select_reviewers(tech_stack, file_exts)

        results: dict[str, AgentReviewResult] = {}

        # Run all selected agents concurrently
        async def run_agent(agent_name: str) -> tuple[str, AgentReviewResult]:
            agent = get_agent(agent_name)
            if agent is None:
                return agent_name, AgentReviewResult(
                    agent_name=agent_name,
                    project_id=project_id,
                    passed=False,
                    findings=[AgentFinding(
                        agent_name=agent_name,
                        project_id=project_id,
                        category="syntax",
                        severity="high",
                        title=f"Agent {agent_name} not available",
                        description=f"Specialist agent '{agent_name}' is not registered.",
                        file_path=None,
                    )],
                )
            try:
                context = {"tech_stack": tech_stack, "files": files}
                result = await agent.review(project_id, str(project_dir), context)
                return agent_name, result
            except Exception as e:
                logger.error(f"Agent {agent_name} review failed: {e}")
                return agent_name, AgentReviewResult(
                    agent_name=agent_name,
                    project_id=project_id,
                    passed=False,
                    findings=[AgentFinding(
                        agent_name=agent_name,
                        project_id=project_id,
                        category="syntax",
                        severity="high",
                        title=f"Agent {agent_name} error",
                        description=str(e),
                        file_path=None,
                    )],
                )

        agent_results = await asyncio.gather(
            *[run_agent(name) for name in reviewers],
            return_exceptions=True,
        )

        all_findings: list[AgentFinding] = []
        all_patches: list[AgentPatch] = []

        for item in agent_results:
            if isinstance(item, BaseException):
                logger.error(f"Review cycle agent error: {item}")
                continue
            agent_name, result = item
            results[agent_name] = result
            all_findings.extend(result.findings)
            all_patches.extend(result.patches)

        # Persist findings as defects
        for finding in all_findings:
            try:
                defect_id = await create_defect(
                    project_id=project_id,
                    category=finding.category,
                    severity=finding.severity,
                    evidence=finding.evidence or finding.description,
                    file_path=finding.file_path,
                    line_start=finding.line_start,
                    line_end=finding.line_end,
                    root_cause=None,
                    assigned_agent=finding.agent_name,
                )
                finding.finding_id = defect_id  # reuse as reference
            except Exception as e:
                logger.error(f"Failed to persist finding: {e}")

        # Update Gate 3 (Implementation) based on review results
        gate_id = await self._get_gate_id(project_id, 3)
        critical_findings = [f for f in all_findings if f.severity == "critical"]
        high_findings = [f for f in all_findings if f.severity == "high"]

        gate_passed = len(critical_findings) == 0 and len(high_findings) == 0
        await update_gate_status(
            gate_id,
            "passed" if gate_passed else "failed",
            results={
                "reviewers": reviewers,
                "findings_count": len(all_findings),
                "critical_count": len(critical_findings),
                "high_count": len(high_findings),
                "agents": {name: r.passed for name, r in results.items()},
            },
            evidence={"findings": [f.to_dict() for f in all_findings]},
        )

        return {
            "project_id": project_id,
            "reviewers": reviewers,
            "agent_results": {
                name: {
                    "passed": r.passed,
                    "findings": [f.to_dict() for f in r.findings],
                    "patches": [p.to_dict() for p in r.patches],
                    "summary": r.summary,
                }
                for name, r in results.items()
            },
            "total_findings": len(all_findings),
            "critical_findings": len(critical_findings),
            "high_findings": len(high_findings),
            "gate_3_passed": gate_passed,
            "patches": [p.to_dict() for p in all_patches],
        }

    # ── Gate Enforcement ──────────────────────────────────────────────

    async def check_quality_gates(self, project_id: str) -> dict[str, Any]:
        """Check all quality gate statuses for a project."""
        gates = await get_quality_gates(project_id)
        if not gates:
            return {"all_passed": False, "gates": [], "blocking": True}

        gate_list = []
        blocking = False
        all_passed = True

        for g in gates:
            gate_list.append({
                "gate_number": g["gate_number"],
                "gate_name": g["gate_name"],
                "status": g["status"],
                "blocking": g["status"] == "failed",
            })
            if g["status"] == "failed":
                blocking = True
                all_passed = False
            elif g["status"] == "pending":
                all_passed = False

        return {
            "all_passed": all_passed,
            "blocking": blocking,
            "gates": gate_list,
        }

    async def approve_delivery(self, project_id: str) -> dict[str, Any]:
        """
        Approve final delivery only if all applicable quality gates pass
        and no critical/high defects remain open.
        """
        gate_check = await self.check_quality_gates(project_id)
        open_defects = await get_defects(project_id, status="open")
        critical_open = [d for d in open_defects if d.get("severity") == "critical"]

        approved = gate_check["all_passed"] and not gate_check["blocking"] and len(critical_open) == 0

        return {
            "approved": approved,
            "gate_check": gate_check,
            "open_defects": len(open_defects),
            "critical_open": len(critical_open),
            "reason": "All quality gates passed and no critical defects open" if approved else
                      "Cannot approve: gates blocking or critical defects remain open",
        }

    # ── Helpers ───────────────────────────────────────────────────────

    async def _get_gate_id(self, project_id: str, gate_number: int) -> str:
        gates = await get_quality_gates(project_id)
        for g in gates:
            if g["gate_number"] == gate_number:
                return g["id"]
        # Initialize if missing
        from app.quality.database import initialize_quality_gates
        await initialize_quality_gates(project_id)
        gates = await get_quality_gates(project_id)
        for g in gates:
            if g["gate_number"] == gate_number:
                return g["id"]
        raise RuntimeError(f"Gate {gate_number} not found for project {project_id}")


# Global singleton
quality_orchestrator = QualityOrchestrator()
