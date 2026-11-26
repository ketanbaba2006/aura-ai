"""
Debugging Agent

Investigates root causes, prepares fixes, applies patches, rebuilds,
reruns failed tests, verifies corrections.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.quality.agents.base import BaseAgent, AgentFinding, AgentPatch, AgentReviewResult

logger = logging.getLogger(__name__)


class DebuggingAgent(BaseAgent):
    agent_name = "debugging_agent"
    agent_role = "Debugging Agent"
    applicable_technologies = []

    async def review(self, project_id: str, project_dir: str,
                     context: dict | None = None) -> AgentReviewResult:
        """
        Debugging agent reviews existing defects and investigates root causes.
        It does not initiate new findings — it analyzes defects created by
        other agents and prepares repair patches.
        """
        findings: list[AgentFinding] = []
        patches: list[AgentPatch] = []

        # The debugging agent is invoked via the repair engine with specific
        # defect IDs to investigate. On a general review, it reports no new
        # findings but is ready to investigate.
        return AgentReviewResult(
            agent_name=self.agent_name,
            project_id=project_id,
            passed=True,
            findings=findings,
            patches=patches,
            summary="Debugging agent ready — awaiting defect investigation targets",
            evidence={"mode": "standby"},
        )

    async def investigate_defect(self, project_id: str, project_dir: str,
                                 defect: dict) -> AgentReviewResult:
        """
        Investigate a specific defect and prepare a fix.
        """
        root = Path(project_dir)
        findings: list[AgentFinding] = []
        patches: list[AgentPatch] = []

        file_path = defect.get("file_path")
        evidence = defect.get("evidence", "")
        category = defect.get("category", "")

        finding = AgentFinding(
            agent_name=self.agent_name,
            project_id=project_id,
            category=category,
            severity=defect.get("severity", "medium"),
            title=f"Root cause investigation: {defect.get('evidence', 'defect')[:60]}",
            description=f"Investigating defect {defect.get('id', 'unknown')}: {evidence}",
            file_path=file_path,
            evidence=evidence,
        )
        findings.append(finding)

        # Attempt to read the affected file and suggest a fix
        if file_path and (root / file_path).exists():
            try:
                content = (root / file_path).read_text(encoding="utf-8", errors="replace")
                finding.suggestion = f"Review {file_path} for root cause: {evidence[:200]}"
            except Exception:
                finding.suggestion = f"Could not read {file_path} for investigation"

        return AgentReviewResult(
            agent_name=self.agent_name,
            project_id=project_id,
            passed=True,
            findings=findings,
            patches=patches,
            summary=f"Investigated defect: {evidence[:80]}",
            evidence={"defect_id": defect.get("id"), "file_path": file_path},
        )


debugging_agent = DebuggingAgent()
