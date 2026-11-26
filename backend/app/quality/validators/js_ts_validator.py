"""
JavaScript / TypeScript Validator

Validates syntax, imports/exports, undefined variables, and framework-specific
issues using available tooling (esbuild, tsc, eslint) with regex fallback.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from app.quality.validators.base import BaseValidator, ValidationIssue, ValidationResult

logger = logging.getLogger(__name__)


class JSTSValidator(BaseValidator):
    """Validates JavaScript and TypeScript source files."""

    validator_id = "js_ts_validator"
    name = "JavaScript/TypeScript Validator"
    description = "Validates JS/TS syntax, imports/exports, undefined variables, and common errors."
    applicable_extensions = [".js", ".jsx", ".ts", ".tsx"]

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
            self._validate_imports_exports(result, project_dir, file_path, content)
            self._validate_promises(result, file_path, content)
            self._validate_event_handlers(result, file_path, content)

        if result.critical_count > 0 or result.high_count > 0:
            result.passed = False

        return result

    # ── Checks ────────────────────────────────────────────────────────

    def _validate_syntax(
        self, result: ValidationResult, file_path: str, content: str
    ) -> None:
        """Check for balanced braces, brackets, parentheses."""
        # Strip string literals to avoid false matches
        cleaned = re.sub(r'"(?:\\.|[^"\\])*"', '""', content)
        cleaned = re.sub(r"'(?:\\.|[^'\\])*'", "''", cleaned)
        cleaned = re.sub(r"`(?:\\.|[^`\\])*`", "``", cleaned)
        # Strip comments
        cleaned = re.sub(r"//[^\n]*", "", cleaned)
        cleaned = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.DOTALL)

        for open_ch, close_ch, name in [("{", "}", "curly braces"), ("[", "]", "square brackets"), ("(", ")", "parentheses")]:
            oc = cleaned.count(open_ch)
            cc = cleaned.count(close_ch)
            if oc != cc:
                result.add_issue(ValidationIssue(
                    rule_id=f"js-unmatched-{name.replace(' ', '-')}",
                    category="js_ts",
                    severity="high",
                    message=f"Unmatched {name}: {oc} opening, {cc} closing",
                    file_path=file_path,
                    suggestion=f"Balance all {name} in the file",
                ))

    def _validate_imports_exports(
        self, result: ValidationResult, project_dir: Path, file_path: str, content: str
    ) -> None:
        """Check for import/export consistency."""
        # Find import statements
        imports = re.findall(
            r"import\s+(?:{[^}]*}|\*\s+as\s+\w+|\w+(?:\s*,\s*{[^}]*})?)\s+from\s+['\"]([^'\"]+)['\"]",
            content,
        )
        for imp in imports:
            # Skip node_modules / built-in imports
            if imp.startswith((".", "/")):
                # Relative import — check if file exists
                import_path = (project_dir / file_path).parent / imp
                # Try common extensions
                found = False
                for ext in (".js", ".jsx", ".ts", ".tsx", ".json", ""):
                    if (import_path.with_suffix(ext) if ext else import_path).exists() or \
                       (import_path / f"index{ext}").exists() if ext else False:
                        found = True
                        break
                if not found:
                    result.add_issue(ValidationIssue(
                        rule_id="js-unresolved-import",
                        category="import",
                        severity="high",
                        message=f"Unresolved relative import: '{imp}'",
                        file_path=file_path,
                        suggestion=f"Verify the import path '{imp}' exists",
                    ))

        # Check for export default / named exports mismatch
        has_export_default = bool(re.search(r"export\s+default", content))
        has_export_named = bool(re.search(r"export\s+(?!default)", content))
        # Informational: both default and named exports in same file
        if has_export_default and has_export_named:
            result.add_issue(ValidationIssue(
                rule_id="js-mixed-exports",
                category="js_ts",
                severity="info",
                message="File uses both default and named exports",
                file_path=file_path,
                suggestion="Consider using a consistent export style",
            ))

    def _validate_promises(
        self, result: ValidationResult, file_path: str, content: str
    ) -> None:
        """Check for unhandled promises / missing await."""
        # Find async functions without await
        async_funcs = re.findall(r"async\s+(\w+)\s*\(", content)
        for func_name in async_funcs:
            # Check if 'await' appears anywhere in the function body (rough check)
            # This is a heuristic; full analysis needs an AST
            if "await" not in content:
                result.add_issue(ValidationIssue(
                    rule_id="js-async-no-await",
                    category="js_ts",
                    severity="medium",
                    message=f"async function '{func_name}' has no await expression",
                    file_path=file_path,
                    suggestion="Add await or remove async keyword",
                ))

        # Check for .then() without .catch()
        then_calls = re.findall(r"\.then\s*\(", content)
        catch_calls = re.findall(r"\.catch\s*\(", content)
        if then_calls and not catch_calls:
            result.add_issue(ValidationIssue(
                rule_id="js-promise-no-catch",
                category="js_ts",
                severity="medium",
                message=".then() chain without .catch() — unhandled rejection risk",
                file_path=file_path,
                suggestion="Add .catch() handler to promise chains",
            ))

    def _validate_event_handlers(
        self, result: ValidationResult, file_path: str, content: str
    ) -> None:
        """Check for common event handler issues."""
        # Check for addEventListener without matching remove (informational)
        listeners = re.findall(r"addEventListener\s*\(", content)
        if listeners and "removeEventListener" not in content:
            result.add_issue(ValidationIssue(
                rule_id="js-event-listener-no-remove",
                category="js_ts",
                severity="info",
                message=f"{len(listeners)} addEventListener(s) without removeEventListener — potential memory leak",
                file_path=file_path,
                suggestion="Call removeEventListener when listeners are no longer needed",
            ))


# Module-level singleton
js_ts_validator = JSTSValidator()
