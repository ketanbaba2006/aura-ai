"""
Universal Code Validation — Base Validator

Each validator defines:
- validate(project_dir, files) -> ValidationResult
- applicable file extensions
- technology requirements
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ValidationIssue:
    """A single validation finding."""
    rule_id: str
    category: str  # syntax, html_structure, css, js_ts, type, import, etc.
    severity: str  # critical, high, medium, low, info
    message: str
    file_path: str
    line_start: int | None = None
    line_end: int | None = None
    evidence: str | None = None
    suggestion: str | None = None


@dataclass
class ValidationResult:
    """Result of running a validator."""
    validator_id: str
    passed: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    files_checked: list[str] = field(default_factory=list)
    execution_time_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_issue(self, issue: ValidationIssue) -> None:
        self.issues.append(issue)
        if issue.severity in ("critical", "high"):
            self.passed = False

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "critical")

    @property
    def high_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "high")


class BaseValidator(ABC):
    """Base class for all technology-aware validators."""

    validator_id: str = "base"
    name: str = "Base Validator"
    description: str = "Base validation class"
    applicable_extensions: list[str] = field(default_factory=list)
    required_technologies: list[str] = field(default_factory=list)

    @abstractmethod
    async def validate(
        self, project_dir: Path, files: list[str] | None = None
    ) -> ValidationResult:
        """Run validation against project files. Returns ValidationResult."""
        ...

    def is_applicable(self, file_path: str) -> bool:
        """Check if this validator applies to a given file path."""
        if not self.applicable_extensions:
            return True  # Applies to all files
        return any(file_path.endswith(ext) for ext in self.applicable_extensions)

    def filter_files(self, files: list[str]) -> list[str]:
        """Return only files applicable to this validator."""
        return [f for f in files if self.is_applicable(f)]

    def _read_file(self, project_dir: Path, file_path: str) -> str | None:
        try:
            return (project_dir / file_path).read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            logger.debug(f"Failed to read {file_path}: {e}")
            return None
