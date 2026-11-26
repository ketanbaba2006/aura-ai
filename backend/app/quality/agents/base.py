"""
Quality Agent Base Class

All specialist agents extend BaseAgent and exchange actual structured
technical findings, patches, dependencies, validation results and review feedback.
No simulated communication.
"""

from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.core.llm_client import llm_client
from app.database.database import db

logger = logging.getLogger(__name__)


@dataclass
class AgentFinding:
    """A structured technical finding produced by an agent."""
    finding_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_name: str = ""
    project_id: str = ""
    category: str = ""  # architecture, visual, code, integration, security, database, etc.
    severity: str = "medium"  # critical, high, medium, low, info
    title: str = ""
    description: str = ""
    file_path: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    evidence: str | None = None
    suggestion: str | None = None
    related_findings: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict:
        return {
            "finding_id": self.finding_id,
            "agent_name": self.agent_name,
            "project_id": self.project_id,
            "category": self.category,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "evidence": self.evidence,
            "suggestion": self.suggestion,
            "related_findings": self.related_findings,
            "created_at": self.created_at,
        }


@dataclass
class AgentPatch:
    """A proposed code patch from an agent."""
    patch_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_name: str = ""
    project_id: str = ""
    file_path: str = ""
    original_content: str = ""
    patched_content: str = ""
    unified_diff: str = ""
    description: str = ""
    addresses_finding_ids: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict:
        return {
            "patch_id": self.patch_id,
            "agent_name": self.agent_name,
            "project_id": self.project_id,
            "file_path": self.file_path,
            "description": self.description,
            "addresses_finding_ids": self.addresses_finding_ids,
            "created_at": self.created_at,
        }


@dataclass
class AgentReviewResult:
    """Result of an agent review."""
    agent_name: str
    project_id: str
    passed: bool
    findings: list[AgentFinding] = field(default_factory=list)
    patches: list[AgentPatch] = field(default_factory=list)
    summary: str = ""
    evidence: dict = field(default_factory=dict)


class BaseAgent(ABC):
    """Base class for all quality specialist agents."""

    agent_name: str = "base"
    agent_role: str = "base"
    applicable_technologies: list[str] = field(default_factory=list)

    def __init__(self):
        self._llm = llm_client

    @abstractmethod
    async def review(self, project_id: str, project_dir: str,
                     context: dict | None = None) -> AgentReviewResult:
        """Review the project and return findings/patches."""
        ...

    async def _llm_generate_json(self, prompt: str, system_prompt: str | None = None) -> dict:
        """Call the LLM to generate JSON output."""
        try:
            return await self._llm.generate_json(
                prompt, system_prompt=system_prompt or ""
            )
        except Exception as e:
            logger.error(f"{self.agent_name}: LLM call failed: {e}")
            return {}

    async def _llm_chat(self, messages: list[dict],
                        system_prompt: str | None = None) -> str:
        """Call the LLM for a chat completion."""
        try:
            result = await self._llm.chat(
                messages=messages,
                system_prompt=system_prompt or "",
            )
            # llm_client.chat returns (text, metadata)
            if isinstance(result, tuple):
                return result[0] if result else ""
            return str(result)
        except Exception as e:
            logger.error(f"{self.agent_name}: LLM chat failed: {e}")
            return ""

    def _is_applicable(self, tech_stack: list[str]) -> bool:
        """Check if this agent applies to the given technology stack."""
        if not self.applicable_technologies:
            return True
        return any(t in tech_stack for t in self.applicable_technologies)

    async def persist_findings(self, project_id: str,
                               findings: list[AgentFinding]) -> None:
        """Persist agent findings as defects in the quality engine."""
        from app.quality.database import create_defect, DEFECT_CATEGORIES, DEFECT_SEVERITIES

        severity_map = {
            "critical": "critical",
            "high": "high",
            "medium": "medium",
            "low": "low",
            "info": "low",
        }

        for finding in findings:
            category = finding.category if finding.category in DEFECT_CATEGORIES else "syntax"
            severity = severity_map.get(finding.severity, "medium")

            await create_defect(
                project_id=project_id,
                category=category,
                severity=severity,
                evidence=finding.evidence or finding.description,
                file_path=finding.file_path,
                line_start=finding.line_start,
                line_end=finding.line_end,
                root_cause=None,
                assigned_agent=self.agent_name,
            )
