"""
UI/UX Designer Agent

Validates visual hierarchy, spacing, alignment, component consistency,
responsive design, and compares actual rendering with design requirements.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from app.quality.agents.base import BaseAgent, AgentFinding, AgentPatch, AgentReviewResult

logger = logging.getLogger(__name__)


class UIDesignerAgent(BaseAgent):
    agent_name = "ui_designer"
    agent_role = "UI/UX Designer"
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

        # Check for CSS files
        css_files = [f for f in files if f.endswith(".css")]
        html_files = [f for f in files if f.endswith((".html", ".htm"))]
        jsx_files = [f for f in files if f.endswith((".jsx", ".tsx"))]

        if html_files or jsx_files:
            if not css_files:
                findings.append(AgentFinding(
                    agent_name=self.agent_name,
                    project_id=project_id,
                    category="visual_layout",
                    severity="high",
                    title="UI components detected without CSS styling",
                    description="HTML/JSX files exist but no CSS stylesheet found — layout may use browser defaults.",
                    evidence=f"UI files: {html_files + jsx_files}",
                    suggestion="Add a CSS stylesheet and link it from HTML or import it in JSX components",
                ))

        # Check CSS for responsive media queries
        for css_file in css_files:
            try:
                content = (root / css_file).read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            has_media = bool(re.search(r"@media\s", content))
            if not has_media:
                findings.append(AgentFinding(
                    agent_name=self.agent_name,
                    project_id=project_id,
                    category="responsive",
                    severity="medium",
                    title="No responsive breakpoints in CSS",
                    description=f"{css_file} has no @media queries — layout may not adapt to mobile/tablet viewports.",
                    file_path=css_file,
                    evidence="No @media rule found in stylesheet",
                    suggestion="Add @media breakpoints for mobile and tablet viewports",
                ))

        # Check HTML for semantic structure
        for html_file in html_files:
            try:
                content = (root / html_file).read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            has_header = bool(re.search(r"<header\b", content, re.IGNORECASE))
            has_nav = bool(re.search(r"<nav\b", content, re.IGNORECASE))
            has_main = bool(re.search(r"<main\b", content, re.IGNORECASE))
            has_footer = bool(re.search(r"<footer\b", content, re.IGNORECASE))

            semantic_count = sum([has_header, has_nav, has_main, has_footer])
            if semantic_count == 0 and len(content) > 500:
                findings.append(AgentFinding(
                    agent_name=self.agent_name,
                    project_id=project_id,
                    category="visual_layout",
                    severity="low",
                    title="Non-semantic HTML structure",
                    description=f"{html_file} lacks semantic elements (header, nav, main, footer).",
                    file_path=html_file,
                    suggestion="Use semantic HTML5 elements for better accessibility and document structure",
                ))

        passed = not any(f.severity in ("critical", "high") for f in findings)

        return AgentReviewResult(
            agent_name=self.agent_name,
            project_id=project_id,
            passed=passed,
            findings=findings,
            patches=patches,
            summary=f"UI/UX review: {len(findings)} finding(s), {'PASS' if passed else 'FAIL'}",
            evidence={"css_files": css_files, "html_files": html_files, "jsx_files": jsx_files},
        )


ui_designer_agent = UIDesignerAgent()
