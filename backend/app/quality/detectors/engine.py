"""
Technology Detection Engine

Orchestrates all technology adapters, merges their signatures,
and produces a unified TechnologyDetectionResult for the AGQE.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.quality.detectors.base import (
    TechnologyDetector,
    BaseTechnologyDetector,
    WebTechnologyDetector,
    PythonTechnologyDetector,
    NodeTechnologyDetector,
    MobileTechnologyDetector,
    DatabaseTechnologyDetector,
    GenericDetector,
    TechnologySignature,
    TechnologyDetectionResult,
)

logger = logging.getLogger(__name__)

# Default ordered list of detectors
DEFAULT_DETECTORS: list[type[TechnologyDetector]] = [
    WebTechnologyDetector,
    PythonTechnologyDetector,
    NodeTechnologyDetector,
    MobileTechnologyDetector,
    DatabaseTechnologyDetector,
    GenericDetector,  # Always last as fallback
]


class TechnologyDetectionEngine:
    """
    Runs all registered technology detectors against a project directory,
    merges their signatures, and produces a unified detection result.
    """

    def __init__(self, detectors: list[type[TechnologyDetector]] | None = None):
        self.detectors: list[TechnologyDetector] = [
            d() for d in (detectors or DEFAULT_DETECTORS)
        ]

    def detect(self, project_dir: Path) -> TechnologyDetectionResult:
        """
        Run all detectors and merge results into a single TechnologyDetectionResult.

        Args:
            project_dir: Absolute path to the project workspace directory.

        Returns:
            TechnologyDetectionResult with merged signatures and commands.
        """
        if not project_dir.exists() or not project_dir.is_dir():
            logger.warning(f"Project directory does not exist: {project_dir}")
            return TechnologyDetectionResult(
                project_type="unknown",
                detector_notes=[f"Directory not found: {project_dir}"],
            )

        all_signatures: list[TechnologySignature] = []
        detector_notes: list[str] = []

        for detector in self.detectors:
            try:
                sigs = detector.detect(project_dir)
                if sigs:
                    detector_notes.append(
                        f"{detector.name}: detected {[s.name for s in sigs]}"
                    )
                all_signatures = self._merge_all_signatures(all_signatures, sigs)
            except Exception as e:
                logger.error(f"Detector {detector.name} failed: {e}")
                detector_notes.append(f"{detector.name}: error ({e})")

        # If any real (non-generic) detector found signatures, drop the generic "Unknown" fallback
        has_real_signatures = any(
            not (s.name == "Unknown" and s.category == "other")
            for s in all_signatures
        )
        if has_real_signatures:
            all_signatures = [
                s for s in all_signatures
                if not (s.name == "Unknown" and s.category == "other")
            ]

        # Determine project type and primary language
        project_type = self._infer_project_type(all_signatures)
        primary_language = self._infer_primary_language(all_signatures)

        # Collect build/test/runtime commands from all applicable detectors
        build_commands: list[str] = []
        test_commands: list[str] = []
        runtime_commands: list[str] = []
        supported_validators: list[str] = []
        applicable_gates: set[int] = set()

        for sig in all_signatures:
            for detector in self.detectors:
                if detector.name == sig.name.lower().replace(" ", "_") or (
                    detector.category == sig.category
                ):
                    try:
                        build_commands.extend(detector.get_build_commands([sig]))
                        test_commands.extend(detector.get_test_commands([sig]))
                        runtime_commands.extend(detector.get_runtime_commands([sig]))
                        supported_validators.extend(detector.get_supported_validators())
                        applicable_gates.update(detector.get_applicable_quality_gates())
                    except Exception as e:
                        logger.debug(
                            f"Command collection failed for {detector.name}: {e}"
                        )

        # Deduplicate commands while preserving order
        build_commands = self._dedupe(build_commands)
        test_commands = self._dedupe(test_commands)
        runtime_commands = self._dedupe(runtime_commands)
        supported_validators = self._dedupe(supported_validators)

        # Determine unsupported checks
        unsupported_checks: list[str] = []
        if not supported_validators:
            unsupported_checks.append(
                "No technology-specific validators available for detected stack"
            )
        if not build_commands:
            unsupported_checks.append("No build commands detected")
        if not test_commands:
            unsupported_checks.append("No test commands detected")

        result = TechnologyDetectionResult(
            project_type=project_type,
            primary_language=primary_language,
            technologies=all_signatures,
            build_commands=build_commands,
            test_commands=test_commands,
            runtime_commands=runtime_commands,
            supported_validators=supported_validators,
            unsupported_checks=unsupported_checks,
            detector_notes=detector_notes,
        )

        logger.info(
            f"Technology detection complete: type={project_type}, "
            f"lang={primary_language}, techs={[t.name for t in all_signatures]}"
        )
        return result

    # ── Internal helpers ──────────────────────────────────────────────

    def _merge_all_signatures(
        self, existing: list[TechnologySignature], new: list[TechnologySignature]
    ) -> list[TechnologySignature]:
        merged = list(existing)
        for sig in new:
            found_idx = None
            for i, existing_sig in enumerate(merged):
                if (
                    existing_sig.name == sig.name
                    and existing_sig.category == sig.category
                ):
                    found_idx = i
                    break
            if found_idx is not None:
                existing_sig = merged[found_idx]
                merged[found_idx] = TechnologySignature(
                    name=existing_sig.name,
                    category=existing_sig.category,
                    version=sig.version or existing_sig.version,
                    confidence=min(1.0, existing_sig.confidence + 0.05),
                    evidence={**existing_sig.evidence, **sig.evidence},
                    files_found=list(
                        set(existing_sig.files_found + sig.files_found)
                    ),
                )
            else:
                merged.append(sig)
        return merged

    def _infer_project_type(
        self, signatures: list[TechnologySignature]
    ) -> str:
        names = {s.name for s in signatures}
        categories = {s.category for s in signatures}

        if "mobile" in categories:
            return "mobile"
        if "frontend" in categories and "backend" in categories:
            return "fullstack"
        if "frontend" in categories:
            return "web"
        if "backend" in categories:
            return "api"
        if "database" in categories:
            return "database"
        return "unknown"

    def _infer_primary_language(
        self, signatures: list[TechnologySignature]
    ) -> str | None:
        # Priority order for primary language
        priority = [
            "TypeScript", "JavaScript", "Python", "Dart", "Java",
            "Go", "Rust", "C++", "C#", "Ruby", "PHP",
        ]
        name_to_lang = {
            "TypeScript": "TypeScript",
            "JavaScript": "JavaScript",
            "React": "JavaScript",
            "Next.js": "JavaScript",
            "Vue": "JavaScript",
            "Nuxt": "JavaScript",
            "Angular": "TypeScript",
            "Svelte": "JavaScript",
            "React Native": "JavaScript",
            "Express": "JavaScript",
            "NestJS": "TypeScript",
            "Python": "Python",
            "Django": "Python",
            "FastAPI": "Python",
            "Flask": "Python",
            "Flutter": "Dart",
        }
        for lang in priority:
            for sig in signatures:
                if sig.name in name_to_lang and name_to_lang[sig.name] == lang:
                    return lang
        # Fallback: first signature's inferred language
        for sig in signatures:
            if sig.name in name_to_lang:
                return name_to_lang[sig.name]
        return None

    @staticmethod
    def _dedupe(items: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for item in items:
            if item not in seen:
                seen.add(item)
                result.append(item)
        return result

    def detect_and_summarize(self, project_dir: Path) -> dict[str, Any]:
        """Run detection and return a JSON-serializable summary."""
        result = self.detect(project_dir)
        return {
            "project_type": result.project_type,
            "primary_language": result.primary_language,
            "technologies": [
                {
                    "name": t.name,
                    "category": t.category,
                    "version": t.version,
                    "confidence": t.confidence,
                    "evidence": t.evidence,
                    "files_found": t.files_found,
                }
                for t in result.technologies
            ],
            "build_commands": result.build_commands,
            "test_commands": result.test_commands,
            "runtime_commands": result.runtime_commands,
            "supported_validators": result.supported_validators,
            "unsupported_checks": result.unsupported_checks,
            "detector_notes": result.detector_notes,
        }


# Global instance
tech_detection_engine = TechnologyDetectionEngine()
