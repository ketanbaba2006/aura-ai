"""
HTML Validator

Validates HTML document structure using html5lib when available,
with a regex-based fallback for environments without it.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from app.quality.validators.base import BaseValidator, ValidationIssue, ValidationResult

logger = logging.getLogger(__name__)


class HTMLValidator(BaseValidator):
    """Validates HTML structure, tag matching, metadata, and accessibility basics."""

    validator_id = "html_validator"
    name = "HTML Validator"
    description = "Validates HTML document structure, tag nesting, metadata, and viewport."
    applicable_extensions = [".html", ".htm"]

    # Self-closing / void HTML elements
    VOID_ELEMENTS = {
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    }

    # Elements that must not be nested inside certain parents
    INVALID_NESTING = {
        "a": {"a"},           # anchor cannot contain anchor
        "p": {"div", "p", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "table"},
        "button": {"button", "a", "input", "select", "textarea"},
    }

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

            self._validate_structure(result, file_path, content)
            self._validate_tags(result, file_path, content)
            self._validate_metadata(result, file_path, content)
            self._validate_ids(result, file_path, content)
            self._validate_links(result, file_path, content)

        if result.critical_count > 0 or result.high_count > 0:
            result.passed = False

        return result

    # ── Checks ────────────────────────────────────────────────────────

    def _validate_structure(
        self, result: ValidationResult, file_path: str, content: str
    ) -> None:
        """Check for DOCTYPE, html, head, body essential elements."""
        has_doctype = bool(re.search(r"<!DOCTYPE\s+html", content, re.IGNORECASE))
        has_html = bool(re.search(r"<html\b", content, re.IGNORECASE))
        has_head = bool(re.search(r"<head\b", content, re.IGNORECASE))
        has_body = bool(re.search(r"<body\b", content, re.IGNORECASE))

        if not has_doctype:
            result.add_issue(ValidationIssue(
                rule_id="html-missing-doctype",
                category="html_structure",
                severity="high",
                message="Missing <!DOCTYPE html> declaration",
                file_path=file_path,
                suggestion="Add <!DOCTYPE html> at the top of the document",
            ))

        if not has_html:
            result.add_issue(ValidationIssue(
                rule_id="html-missing-root",
                category="html_structure",
                severity="critical",
                message="Missing <html> root element",
                file_path=file_path,
                suggestion="Wrap document in <html> element",
            ))

        if not has_head:
            result.add_issue(ValidationIssue(
                rule_id="html-missing-head",
                category="html_structure",
                severity="medium",
                message="Missing <head> element",
                file_path=file_path,
                suggestion="Add <head> element for metadata",
            ))

        if not has_body:
            result.add_issue(ValidationIssue(
                rule_id="html-missing-body",
                category="html_structure",
                severity="critical",
                message="Missing <body> element",
                file_path=file_path,
                suggestion="Add <body> element for page content",
            ))

    def _validate_tags(
        self, result: ValidationResult, file_path: str, content: str
    ) -> None:
        """Check for unmatched opening/closing tags."""
        # Remove script and style content to avoid false matches on < and > inside
        cleaned = re.sub(r"<script[^>]*>.*?</script>", "", content, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r"<style[^>]*>.*?</style>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r"<!--.*?-->", "", cleaned, flags=re.DOTALL)

        open_tags = re.findall(r"<([a-zA-Z][a-zA-Z0-9\-]*)(?:\s[^>]*)?>", cleaned)
        close_tags = re.findall(r"</([a-zA-Z][a-zA-Z0-9\-]*)>", cleaned)

        open_lower = [t.lower() for t in open_tags if t.lower() not in self.VOID_ELEMENTS]
        close_lower = [t.lower() for t in close_tags]

        for tag in set(open_lower):
            if open_lower.count(tag) != close_lower.count(tag):
                result.add_issue(ValidationIssue(
                    rule_id="html-unmatched-tag",
                    category="html_structure",
                    severity="high",
                    message=f"Unmatched <{tag}> tags: opened {open_lower.count(tag)}, closed {close_lower.count(tag)}",
                    file_path=file_path,
                    suggestion=f"Ensure every <{tag}> has a matching </{tag}>",
                ))

        # Check invalid nesting
        for parent, forbidden_children in self.INVALID_NESTING.items():
            for child in forbidden_children:
                # Simple pattern: <parent>...<child>...</child>...</parent>
                pattern = rf"<{parent}\b[^>]*>.*?<{child}\b[^>]*>.*?</{child}>.*?</{parent}>"
                if re.search(pattern, cleaned, flags=re.DOTALL | re.IGNORECASE):
                    result.add_issue(ValidationIssue(
                        rule_id="html-invalid-nesting",
                        category="html_structure",
                        severity="medium",
                        message=f"Invalid nesting: <{child}> inside <{parent}>",
                        file_path=file_path,
                        suggestion=f"Move <{child}> outside of <{parent}>",
                    ))

    def _validate_metadata(
        self, result: ValidationResult, file_path: str, content: str
    ) -> None:
        """Check for charset, viewport, title."""
        has_charset = bool(re.search(r'<meta[^>]+charset\s*=', content, re.IGNORECASE))
        has_viewport = bool(re.search(r'<meta[^>]+viewport\s*=', content, re.IGNORECASE))
        has_title = bool(re.search(r"<title[^>]*>.*?</title>", content, re.IGNORECASE | re.DOTALL))

        if not has_charset:
            result.add_issue(ValidationIssue(
                rule_id="html-missing-charset",
                category="html_structure",
                severity="medium",
                message="Missing charset meta declaration",
                file_path=file_path,
                suggestion='Add <meta charset="UTF-8"> to <head>',
            ))

        if not has_viewport:
            result.add_issue(ValidationIssue(
                rule_id="html-missing-viewport",
                category="html_structure",
                severity="high",
                message="Missing viewport meta declaration (required for responsive web apps)",
                file_path=file_path,
                suggestion='Add <meta name="viewport" content="width=device-width, initial-scale=1.0"> to <head>',
            ))

        if not has_title:
            result.add_issue(ValidationIssue(
                rule_id="html-missing-title",
                category="html_structure",
                severity="medium",
                message="Missing <title> element",
                file_path=file_path,
                suggestion="Add a descriptive <title> to <head>",
            ))

    def _validate_ids(
        self, result: ValidationResult, file_path: str, content: str
    ) -> None:
        """Check for duplicate IDs."""
        ids = re.findall(r'id\s*=\s*["\']([^"\']+)["\']', content)
        seen: dict[str, int] = {}
        for i, id_val in enumerate(ids):
            if id_val in seen:
                result.add_issue(ValidationIssue(
                    rule_id="html-duplicate-id",
                    category="html_structure",
                    severity="high",
                    message=f'Duplicate ID "{id_val}" found in document',
                    file_path=file_path,
                    suggestion=f'Change one of the duplicate id="{id_val}" attributes to a unique value',
                ))
            else:
                seen[id_val] = i

    def _validate_links(
        self, result: ValidationResult, file_path: str, content: str
    ) -> None:
        """Check for local asset references (informational only)."""
        hrefs = re.findall(r'href\s*=\s*["\']([^"\']+)["\']', content)
        local_refs = [
            h for h in hrefs
            if not h.startswith(("http://", "https://", "//", "mailto:", "tel:", "#"))
        ]
        if local_refs:
            result.add_issue(ValidationIssue(
                rule_id="html-local-asset-refs",
                category="asset_loading",
                severity="info",
                message=f"{len(local_refs)} local asset reference(s) found — verify they resolve at build time",
                file_path=file_path,
                suggestion="Ensure all local href targets exist and are reachable",
            ))


# Module-level singleton
html_validator = HTMLValidator()
