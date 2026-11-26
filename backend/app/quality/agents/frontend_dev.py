"""
Frontend Developer Agent

Writes and maintains frontend code. Fixes component errors, resolves CSS
and layout problems, corrects broken interactions, implements responsive
behavior.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from app.quality.agents.base import BaseAgent, AgentFinding, AgentPatch, AgentReviewResult

logger = logging.getLogger(__name__)


class FrontendDeveloperAgent(BaseAgent):
    agent_name = "frontend_developer"
    agent_role = "Frontend Developer"
    applicable_technologies = [
        "React", "Vue", "Angular", "Svelte", "Next.js", "Nuxt",
        "HTML", "CSS", "JavaScript", "TypeScript",
    ]

    async def review(self, project_id: str, project_dir: str,
                     context: dict | None = None) -> AgentReviewResult:
        root = Path(project_dir)
        findings: list[AgentFinding] = []
        patches: list[AgentPatch] = []

        files = (context or {}).get("files", [])

        # Scan JS/TS files for common frontend issues
        for f in files:
            if not f.endswith((".js", ".jsx", ".ts", ".tsx")):
                continue
            try:
                content = (root / f).read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            # Check for unused/unresolved imports (heuristic)
            imports = re.findall(r"from\s+['\"]([^'\"]+)['\"]", content)
            for imp in imports:
                if imp.startswith("."):
                    # Relative import — check existence
                    import_path = (root / f).parent / imp
                    found = False
                    for ext in (".js", ".jsx", ".ts", ".tsx", ".json", ""):
                        if ext:
                            cand = import_path.with_suffix(ext)
                        else:
                            cand = import_path
                        if cand.exists() or (cand.is_dir() and (cand / "index.js").exists()) or \
                           (cand.is_dir() and (cand / "index.jsx").exists()) or \
                           (cand.is_dir() and (cand / "index.ts").exists()) or \
                           (cand.is_dir() and (cand / "index.tsx").exists()):
                            found = True
                            break
                    if not found:
                        findings.append(AgentFinding(
                            agent_name=self.agent_name,
                            project_id=project_id,
                            category="import",
                            severity="high",
                            title=f"Unresolved import: {imp}",
                            description=f"Relative import '{imp}' in {f} does not resolve to an existing file.",
                            file_path=f,
                            evidence=f"Import statement: from '{imp}'",
                            suggestion=f"Verify the import path '{imp}' exists relative to {f}",
                        ))

            # Check for console.log leftovers (production concern)
            console_logs = re.findall(r"console\.(log|error|warn)\s*\(", content)
            if len(console_logs) > 5:
                findings.append(AgentFinding(
                    agent_name=self.agent_name,
                    project_id=project_id,
                    category="js_ts",
                    severity="low",
                    title=f"Excessive console statements in {f}",
                    description=f"{len(console_logs)} console.log/error/warn calls found — may indicate incomplete debugging.",
                    file_path=f,
                    evidence=f"{len(console_logs)} console statements",
                    suggestion="Remove debug console statements before production",
                ))

        passed = not any(f.severity in ("critical", "high") for f in findings)

        return AgentReviewResult(
            agent_name=self.agent_name,
            project_id=project_id,
            passed=passed,
            findings=findings,
            patches=patches,
            summary=f"Frontend review: {len(findings)} finding(s), {'PASS' if passed else 'FAIL'}",
            evidence={"files_scanned": len([f for f in files if f.endswith(('.js', '.jsx', '.ts', '.tsx'))])},
        )


frontend_dev_agent = FrontendDeveloperAgent()
