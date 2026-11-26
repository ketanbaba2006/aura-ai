"""
CSS Validator

Validates CSS syntax, block matching, selector validity, and responsive basics.
Uses cssutils if available, otherwise a regex-based fallback.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from app.quality.validators.base import BaseValidator, ValidationIssue, ValidationResult

logger = logging.getLogger(__name__)


class CSSValidator(BaseValidator):
    """Validates CSS syntax, unclosed blocks, invalid selectors, and responsive styling."""

    validator_id = "css_validator"
    name = "CSS Validator"
    description = "Validates CSS syntax, block structure, selectors, and responsive layout rules."
    applicable_extensions = [".css"]

    async def validate(
        self, project_dir: Path, files: list[str] | None = None
    ) -> ValidationResult:
        result = ValidationResult(validator_id=self.validator_id, passed=True)

        target_files = self.filter_files(files or [])
        result.files_checked = target_files

        for file_path in target_files:
            content = self._read_file(project_dir, file_path)
            if content is None:
                continue

            self._validate_syntax(result, file_path, content)
            self._validate_blocks(result, file_path, content)
            self._validate_selectors(result, file_path, content)
            self._validate_responsive(result, file_path, content)
            self._validate_accessibility(result, file_path, content)

        if result.critical_count > 0 or result.high_count > 0:
            result.passed = False

        return result

    # ── Checks ────────────────────────────────────────────────────────

    def _validate_syntax(
        self, result: ValidationResult, file_path: str, content: str
    ) -> None:
        """Check for basic CSS syntax problems."""
        # Remove comments
        cleaned = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)

        # Check for unmatched braces
        open_count = cleaned.count("{")
        close_count = cleaned.count("}")
        if open_count != close_count:
            result.add_issue(ValidationIssue(
                rule_id="css-unmatched-braces",
                category="css",
                severity="high",
                message=f"Unmatched CSS braces: {open_count} opening, {close_count} closing",
                file_path=file_path,
                suggestion="Ensure every { has a matching }",
            ))

        # Check for properties outside of rules (declarations not inside { })
        # Find lines with : but outside braces
        lines = cleaned.split("\n")
        brace_depth = 0
        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("//") or stripped.startswith("/*"):
                continue
            brace_depth += stripped.count("{") - stripped.count("}")
            if ":" in stripped and brace_depth == 0 and not stripped.startswith("@"):
                # Could be a declaration outside a rule
                if re.match(r"^[a-zA-Z-]+\s*:", stripped):
                    result.add_issue(ValidationIssue(
                        rule_id="css-declaration-outside-rule",
                        category="css",
                        severity="medium",
                        message=f"CSS declaration outside rule block at line {idx}: {stripped[:60]}",
                        file_path=file_path,
                        line_start=idx,
                        line_end=idx,
                        suggestion="Wrap declarations inside a selector block { }",
                    ))

    def _validate_blocks(
        self, result: ValidationResult, file_path: str, content: str
    ) -> None:
        """Check for unclosed blocks and incomplete rules."""
        # Find rule blocks
        blocks = re.findall(r"([^{}]+)\{([^{}]*)\}", content, flags=re.DOTALL)
        if not blocks and "{" in content:
            # There are braces but no complete blocks matched
            result.add_issue(ValidationIssue(
                rule_id="css-incomplete-rule",
                category="css",
                severity="high",
                message="CSS file contains braces but no complete rule blocks",
                file_path=file_path,
                suggestion="Ensure each selector has a complete { ... } block",
            ))

    def _validate_selectors(
        self, result: ValidationResult, file_path: str, content: str
    ) -> None:
        """Check for obviously invalid selectors."""
        # Find selectors (content before { )
        rules = re.findall(r"([^{]+)\{", content, flags=re.DOTALL)
        for rule in rules:
            selector = rule.strip()
            if not selector:
                continue
            # Check for empty selector
            if selector in (",", " ", ""):
                result.add_issue(ValidationIssue(
                    rule_id="css-empty-selector",
                    category="css",
                    severity="medium",
                    message="Empty CSS selector found",
                    file_path=file_path,
                    suggestion="Remove empty selector or provide a valid selector",
                ))
            # Check for double combinators
            if re.search(r"(\s*[>+~\s]\s*){2,}", selector):
                result.add_issue(ValidationIssue(
                    rule_id="css-invalid-combinator",
                    category="css",
                    severity="medium",
                    message=f"Invalid selector combinator sequence: {selector[:60]}",
                    file_path=file_path,
                    suggestion="Fix selector syntax",
                ))

    def _validate_responsive(
        self, result: ValidationResult, file_path: str, content: str
    ) -> None:
        """Check for responsive design basics."""
        has_media_query = bool(re.search(r"@media\s", content))
        # Informational only — not a failure
        if not has_media_query:
            result.add_issue(ValidationIssue(
                rule_id="css-no-media-queries",
                category="responsive",
                severity="info",
                message="No media queries found — responsive design may be limited",
                file_path=file_path,
                suggestion="Add @media queries for mobile/tablet breakpoints",
            ))

    def _validate_accessibility(
        self, result: ValidationResult, file_path: str, content: str
    ) -> None:
        """Check for accessibility-related CSS issues."""
        # Check for !important overuse
        important_count = len(re.findall(r"!important", content))
        if important_count > 10:
            result.add_issue(ValidationIssue(
                rule_id="css-important-overuse",
                category="accessibility",
                severity="medium",
                message=f"Excessive !important usage ({important_count} times)",
                file_path=file_path,
                suggestion="Reduce !important usage; use specific selectors instead",
            ))

        # Check for fixed font sizes in px (accessibility concern)
        px_sizes = re.findall(r"font-size:\s*\d+px", content, re.IGNORECASE)
        if len(px_sizes) > 5:
            result.add_issue(ValidationIssue(
                rule_id="css-px-font-sizes",
                category="accessibility",
                severity="info",
                message=f"Multiple pixel-based font sizes found ({len(px_sizes)})",
                file_path=file_path,
                suggestion="Consider using rem/em units for scalable typography",
            ))


# Module-level singleton
css_validator = CSSValidator()
