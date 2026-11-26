"""
Technology Detection — Base Adapter Architecture

Each technology adapter defines:
- Project detection (is this stack present?)
- Supported validators
- Build/test/runtime commands
- Common failure checks
- Repair capabilities
- Available quality gates
"""

from __future__ import annotations

import json
import logging
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TechnologySignature:
    """A detected technology with confidence and evidence."""
    name: str
    category: str  # frontend, backend, mobile, database, other
    version: str | None = None
    confidence: float = 0.0  # 0.0 to 1.0
    evidence: dict[str, Any] = field(default_factory=dict)
    files_found: list[str] = field(default_factory=list)


@dataclass
class TechnologyDetectionResult:
    """Result of scanning a project directory."""
    project_type: str  # e.g. "web", "fullstack", "mobile", "api", "cli", "library"
    primary_language: str | None = None
    technologies: list[TechnologySignature] = field(default_factory=list)
    build_commands: list[str] = field(default_factory=list)
    test_commands: list[str] = field(default_factory=list)
    runtime_commands: list[str] = field(default_factory=list)
    supported_validators: list[str] = field(default_factory=list)
    unsupported_checks: list[str] = field(default_factory=list)
    detector_notes: list[str] = field(default_factory=list)


class TechnologyDetector(ABC):
    """Base class for technology-specific detection adapters."""

    #: Human-readable name of the adapter
    name: str = "base"
    #: Technology category this adapter handles
    category: str = "other"

    @abstractmethod
    def detect(self, project_dir: Path) -> list[TechnologySignature]:
        """Scan project directory and return detected technology signatures."""
        ...

    @abstractmethod
    def get_supported_validators(self) -> list[str]:
        """Return validator IDs this adapter supports."""
        ...

    @abstractmethod
    def get_build_commands(self, signatures: list[TechnologySignature]) -> list[str]:
        """Return build commands for detected stack."""
        ...

    @abstractmethod
    def get_test_commands(self, signatures: list[TechnologySignature]) -> list[str]:
        """Return test commands for detected stack."""
        ...

    @abstractmethod
    def get_runtime_commands(self, signatures: list[TechnologySignature]) -> list[str]:
        """Return runtime/start commands for detected stack."""
        ...

    def get_common_failure_checks(self) -> list[str]:
        """Return common failure patterns to check for this stack."""
        return []

    def get_repair_capabilities(self) -> list[str]:
        """Return repair capabilities offered by this adapter."""
        return []

    def get_applicable_quality_gates(self) -> list[int]:
        """Return gate numbers applicable to this technology stack."""
        return [1, 2, 3, 4, 5, 10, 11, 12]  # Default universal gates


class BaseTechnologyDetector(TechnologyDetector):
    """Helper with common file-scanning utilities."""

    # Files that indicate a project root
    PROJECT_ROOT_MARKERS: list[str] = [
        ".git", ".gitignore", "README.md", "package.json",
        "requirements.txt", "setup.py", "pyproject.toml",
        "Cargo.toml", "go.mod", "pom.xml", "build.gradle",
        "index.html", "main.py", "app.py", "server.py",
    ]

    # Common package/dependency file names
    DEPENDENCY_FILES: list[str] = [
        "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
        "requirements.txt", "requirements-dev.txt", "Pipfile", "Pipfile.lock",
        "pyproject.toml", "setup.py", "setup.cfg", "poetry.lock",
        "Cargo.toml", "Cargo.lock", "go.mod", "go.sum",
        "pom.xml", "build.gradle", "build.gradle.kts",
        "composer.json", "Gemfile", "Gemfile.lock",
    ]

    # Configuration file indicators
    CONFIG_FILES: list[str] = [
        "tsconfig.json", "jsconfig.json", "babel.config.js", "babel.config.json",
        "vite.config.ts", "vite.config.js", "webpack.config.js", "next.config.js",
        "nuxt.config.ts", "angular.json", "vue.config.js", "svelte.config.js",
        "tailwind.config.js", "postcss.config.js", "eslint.config.js",
        "Dockerfile", "docker-compose.yml", ".env.example",
    ]

    def _read_file(self, path: Path) -> str | None:
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return None

    def _parse_json(self, path: Path) -> dict | None:
        content = self._read_file(path)
        if content is None:
            return None
        try:
            return json.loads(content)
        except (json.JSONDecodeError, ValueError):
            return None

    def _find_files(self, project_dir: Path, names: list[str]) -> list[Path]:
        """Find files by name (recursive shallow search, max depth 3)."""
        found: list[Path] = []
        for root, dirs, files in os.walk(project_dir):
            # Prune deep/node_modules/.git dirs
            dirs[:] = [d for d in dirs if d not in (
                "node_modules", ".git", ".next", "dist", "build",
                "__pycache__", ".venv", "venv", "target", ".cache",
            )]
            depth = len(Path(root).relative_to(project_dir).parts)
            if depth > 3:
                dirs[:] = []
                continue
            for fname in files:
                if fname in names:
                    found.append(Path(root) / fname)
        return found

    def _detect_from_package_json(
        self, project_dir: Path
    ) -> list[TechnologySignature]:
        """Detect frontend/backend technologies from package.json dependencies."""
        sigs: list[TechnologySignature] = []
        pkg_files = self._find_files(project_dir, ["package.json"])
        for pkg_path in pkg_files:
            data = self._parse_json(pkg_path)
            if not data:
                continue
            deps = {}
            for key in ("dependencies", "devDependencies", "peerDependencies"):
                deps.update(data.get(key, {}) or {})

            dep_lower = {k.lower(): v for k, v in deps.items()}

            # React ecosystem
            if "react" in dep_lower:
                sigs.append(TechnologySignature(
                    name="React",
                    category="frontend",
                    version=dep_lower.get("react"),
                    confidence=0.95,
                    evidence={"source": "package.json", "dependency": "react"},
                    files_found=[str(pkg_path.relative_to(project_dir))],
                ))
            if "next" in dep_lower:
                sigs.append(TechnologySignature(
                    name="Next.js",
                    category="frontend",
                    version=dep_lower.get("next"),
                    confidence=0.95,
                    evidence={"source": "package.json", "dependency": "next"},
                    files_found=[str(pkg_path.relative_to(project_dir))],
                ))
            if "vue" in dep_lower:
                sigs.append(TechnologySignature(
                    name="Vue",
                    category="frontend",
                    version=dep_lower.get("vue"),
                    confidence=0.9,
                    evidence={"source": "package.json", "dependency": "vue"},
                    files_found=[str(pkg_path.relative_to(project_dir))],
                ))
            if "nuxt" in dep_lower:
                sigs.append(TechnologySignature(
                    name="Nuxt",
                    category="frontend",
                    version=dep_lower.get("nuxt"),
                    confidence=0.9,
                    evidence={"source": "package.json", "dependency": "nuxt"},
                    files_found=[str(pkg_path.relative_to(project_dir))],
                ))
            if "angular" in dep_lower or "@angular/core" in dep_lower:
                sigs.append(TechnologySignature(
                    name="Angular",
                    category="frontend",
                    version=dep_lower.get("@angular/core") or dep_lower.get("angular"),
                    confidence=0.9,
                    evidence={"source": "package.json", "dependency": "angular"},
                    files_found=[str(pkg_path.relative_to(project_dir))],
                ))
            if "svelte" in dep_lower:
                sigs.append(TechnologySignature(
                    name="Svelte",
                    category="frontend",
                    version=dep_lower.get("svelte"),
                    confidence=0.9,
                    evidence={"source": "package.json", "dependency": "svelte"},
                    files_found=[str(pkg_path.relative_to(project_dir))],
                ))
            if "react-native" in dep_lower:
                sigs.append(TechnologySignature(
                    name="React Native",
                    category="mobile",
                    version=dep_lower.get("react-native"),
                    confidence=0.95,
                    evidence={"source": "package.json", "dependency": "react-native"},
                    files_found=[str(pkg_path.relative_to(project_dir))],
                ))
            if "express" in dep_lower:
                sigs.append(TechnologySignature(
                    name="Express",
                    category="backend",
                    version=dep_lower.get("express"),
                    confidence=0.9,
                    evidence={"source": "package.json", "dependency": "express"},
                    files_found=[str(pkg_path.relative_to(project_dir))],
                ))
            if "@nestjs/core" in dep_lower:
                sigs.append(TechnologySignature(
                    name="NestJS",
                    category="backend",
                    version=dep_lower.get("@nestjs/core"),
                    confidence=0.9,
                    evidence={"source": "package.json", "dependency": "@nestjs/core"},
                    files_found=[str(pkg_path.relative_to(project_dir))],
                ))
            if "typescript" in dep_lower:
                sigs.append(TechnologySignature(
                    name="TypeScript",
                    category="frontend",
                    version=dep_lower.get("typescript"),
                    confidence=0.85,
                    evidence={"source": "package.json", "dependency": "typescript"},
                    files_found=[str(pkg_path.relative_to(project_dir))],
                ))
            if "tailwindcss" in dep_lower:
                sigs.append(TechnologySignature(
                    name="Tailwind CSS",
                    category="frontend",
                    version=dep_lower.get("tailwindcss"),
                    confidence=0.8,
                    evidence={"source": "package.json", "dependency": "tailwindcss"},
                    files_found=[str(pkg_path.relative_to(project_dir))],
                ))

        return sigs

    def _detect_from_python_files(
        self, project_dir: Path
    ) -> list[TechnologySignature]:
        """Detect Python backend technologies from requirements/setup files."""
        sigs: list[TechnologySignature] = []
        req_files = self._find_files(project_dir, [
            "requirements.txt", "requirements-dev.txt", "Pipfile",
            "pyproject.toml", "setup.py", "setup.cfg",
        ])
        for req_path in req_files:
            content = self._read_file(req_path) or ""
            rel = str(req_path.relative_to(project_dir))

            # Django
            if re.search(r"django", content, re.IGNORECASE):
                sigs.append(TechnologySignature(
                    name="Django",
                    category="backend",
                    confidence=0.9,
                    evidence={"source": rel, "match": "django"},
                    files_found=[rel],
                ))
            # FastAPI
            if re.search(r"fastapi", content, re.IGNORECASE):
                sigs.append(TechnologySignature(
                    name="FastAPI",
                    category="backend",
                    confidence=0.9,
                    evidence={"source": rel, "match": "fastapi"},
                    files_found=[rel],
                ))
            # Flask
            if re.search(r"flask", content, re.IGNORECASE):
                sigs.append(TechnologySignature(
                    name="Flask",
                    category="backend",
                    confidence=0.85,
                    evidence={"source": rel, "match": "flask"},
                    files_found=[rel],
                ))
            # Python generally
            sigs.append(TechnologySignature(
                name="Python",
                category="backend",
                confidence=0.7,
                evidence={"source": rel},
                files_found=[rel],
            ))

        return sigs

    def _detect_from_config_files(
        self, project_dir: Path
    ) -> list[TechnologySignature]:
        """Detect technologies from config files."""
        sigs: list[TechnologySignature] = []
        config_files = self._find_files(project_dir, self.CONFIG_FILES)
        for cfg_path in config_files:
            rel = str(cfg_path.relative_to(project_dir))
            content = self._read_file(cfg_path) or ""
            name_lower = cfg_path.name.lower()

            if name_lower == "next.config.js" or name_lower == "next.config.ts":
                sigs.append(TechnologySignature(
                    name="Next.js",
                    category="frontend",
                    confidence=0.95,
                    evidence={"source": rel},
                    files_found=[rel],
                ))
            elif name_lower == "nuxt.config.ts" or name_lower == "nuxt.config.js":
                sigs.append(TechnologySignature(
                    name="Nuxt",
                    category="frontend",
                    confidence=0.95,
                    evidence={"source": rel},
                    files_found=[rel],
                ))
            elif name_lower == "angular.json":
                sigs.append(TechnologySignature(
                    name="Angular",
                    category="frontend",
                    confidence=0.95,
                    evidence={"source": rel},
                    files_found=[rel],
                ))
            elif name_lower == "vue.config.js":
                sigs.append(TechnologySignature(
                    name="Vue",
                    category="frontend",
                    confidence=0.9,
                    evidence={"source": rel},
                    files_found=[rel],
                ))
            elif name_lower == "svelte.config.js":
                sigs.append(TechnologySignature(
                    name="Svelte",
                    category="frontend",
                    confidence=0.9,
                    evidence={"source": rel},
                    files_found=[rel],
                ))
            elif name_lower == "tsconfig.json":
                sigs.append(TechnologySignature(
                    name="TypeScript",
                    category="frontend",
                    confidence=0.8,
                    evidence={"source": rel},
                    files_found=[rel],
                ))
            elif name_lower == "dockerfile":
                sigs.append(TechnologySignature(
                    name="Docker",
                    category="other",
                    confidence=0.7,
                    evidence={"source": rel},
                    files_found=[rel],
                ))
            elif "tailwind" in name_lower:
                sigs.append(TechnologySignature(
                    name="Tailwind CSS",
                    category="frontend",
                    confidence=0.85,
                    evidence={"source": rel},
                    files_found=[rel],
                ))

        return sigs

    def _detect_from_html_files(
        self, project_dir: Path
    ) -> list[TechnologySignature]:
        """Detect HTML/CSS/JS projects from static files."""
        sigs: list[TechnologySignature] = []
        html_files = list(project_dir.rglob("*.html")) + list(project_dir.rglob("*.htm"))
        # Limit depth
        html_files = [f for f in html_files if len(f.relative_to(project_dir).parts) <= 4]

        if html_files:
            sigs.append(TechnologySignature(
                name="HTML",
                category="frontend",
                confidence=0.8,
                evidence={"files": [str(f.relative_to(project_dir)) for f in html_files[:5]]},
                files_found=[str(f.relative_to(project_dir)) for f in html_files[:5]],
            ))

        css_files = list(project_dir.rglob("*.css"))
        css_files = [f for f in css_files if len(f.relative_to(project_dir).parts) <= 4]
        if css_files:
            sigs.append(TechnologySignature(
                name="CSS",
                category="frontend",
                confidence=0.8,
                evidence={"files": [str(f.relative_to(project_dir)) for f in css_files[:5]]},
                files_found=[str(f.relative_to(project_dir)) for f in css_files[:5]],
            ))

        js_files = list(project_dir.rglob("*.js"))
        js_files = [f for f in js_files if "node_modules" not in f.parts and len(f.relative_to(project_dir).parts) <= 4]
        if js_files:
            sigs.append(TechnologySignature(
                name="JavaScript",
                category="frontend",
                confidence=0.75,
                evidence={"files": [str(f.relative_to(project_dir)) for f in js_files[:5]]},
                files_found=[str(f.relative_to(project_dir)) for f in js_files[:5]],
            ))

        return sigs

    def _merge_signatures(
        self, existing: list[TechnologySignature], new: list[TechnologySignature]
    ) -> list[TechnologySignature]:
        """Merge signatures, deduplicating by name and boosting confidence."""
        merged = list(existing)
        for sig in new:
            found = False
            for i, existing_sig in enumerate(merged):
                if existing_sig.name == sig.name and existing_sig.category == sig.category:
                    # Boost confidence and merge evidence
                    merged[i] = TechnologySignature(
                        name=existing_sig.name,
                        category=existing_sig.category,
                        version=sig.version or existing_sig.version,
                        confidence=min(1.0, existing_sig.confidence + 0.1),
                        evidence={**existing_sig.evidence, **sig.evidence},
                        files_found=list(set(
                            existing_sig.files_found + sig.files_found
                        )),
                    )
                    found = True
                    break
            if not found:
                merged.append(sig)
        return merged


class WebTechnologyDetector(BaseTechnologyDetector):
    """Detector for web frontend technologies: HTML, CSS, JS, TS, React, Vue, etc."""

    name = "web"
    category = "frontend"

    def detect(self, project_dir: Path) -> list[TechnologySignature]:
        sigs: list[TechnologySignature] = []

        # package.json based detection
        sigs = self._merge_signatures(sigs, self._detect_from_package_json(project_dir))
        # Python requirements (for fullstack)
        sigs = self._merge_signatures(sigs, self._detect_from_python_files(project_dir))
        # Config files
        sigs = self._merge_signatures(sigs, self._detect_from_config_files(project_dir))
        # Static HTML/CSS/JS files
        sigs = self._merge_signatures(sigs, self._detect_from_html_files(project_dir))

        # If package.json exists but no framework detected, still mark as web
        pkg_files = self._find_files(project_dir, ["package.json"])
        if pkg_files and not any(s.name in ("React", "Vue", "Angular", "Svelte", "Next.js", "Nuxt") for s in sigs):
            sigs.append(TechnologySignature(
                name="JavaScript",
                category="frontend",
                confidence=0.6,
                evidence={"source": "package.json"},
                files_found=[str(pkg_files[0].relative_to(project_dir))],
            ))

        return sigs

    def get_supported_validators(self) -> list[str]:
        return [
            "html_validator",
            "css_validator",
            "javascript_validator",
            "typescript_validator",
            "react_validator",
            "vue_validator",
            "accessibility_validator",
            "responsive_validator",
        ]

    def get_build_commands(self, signatures: list[TechnologySignature]) -> list[str]:
        names = {s.name for s in signatures}
        cmds = []
        if "Next.js" in names:
            cmds.append("npm run build")
        elif "React" in names or "Vue" in names or "Angular" in names or "Svelte" in names:
            cmds.append("npm run build")
        elif "HTML" in names:
            cmds.append("none (static files)")
        return cmds or ["npm run build"]

    def get_test_commands(self, signatures: list[TechnologySignature]) -> list[str]:
        names = {s.name for s in signatures}
        cmds = []
        if any(n in names for n in ("React", "Vue", "Angular", "Svelte", "Next.js", "Nuxt")):
            cmds.append("npm test")
        return cmds or ["npm test"]

    def get_runtime_commands(self, signatures: list[TechnologySignature]) -> list[str]:
        names = {s.name for s in signatures}
        cmds = []
        if "Next.js" in names:
            cmds.append("npm run dev")
        elif "Express" in names:
            cmds.append("node server.js")
        else:
            cmds.append("python3 -m http.server 8000")
        return cmds

    def get_applicable_quality_gates(self) -> list[int]:
        return [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]


class PythonTechnologyDetector(BaseTechnologyDetector):
    """Detector for Python backend technologies: Django, FastAPI, Flask, CLI."""

    name = "python"
    category = "backend"

    def detect(self, project_dir: Path) -> list[TechnologySignature]:
        sigs: list[TechnologySignature] = []
        sigs = self._merge_signatures(sigs, self._detect_from_python_files(project_dir))

        # Check for Python source files
        py_files = list(project_dir.rglob("*.py"))
        py_files = [f for f in py_files if "__pycache__" not in f.parts and ".venv" not in f.parts and "venv" not in f.parts]
        if py_files:
            sigs.append(TechnologySignature(
                name="Python",
                category="backend",
                confidence=0.7,
                evidence={"files": [str(f.relative_to(project_dir)) for f in py_files[:5]]},
                files_found=[str(f.relative_to(project_dir)) for f in py_files[:5]],
            ))

        # Detect specific frameworks from source content
        for py_file in py_files[:20]:
            content = self._read_file(py_file) or ""
            rel = str(py_file.relative_to(project_dir))
            if re.search(r"from django|import django", content):
                sigs.append(TechnologySignature(
                    name="Django",
                    category="backend",
                    confidence=0.85,
                    evidence={"source": rel},
                    files_found=[rel],
                ))
            if re.search(r"from fastapi|import fastapi", content, re.IGNORECASE):
                sigs.append(TechnologySignature(
                    name="FastAPI",
                    category="backend",
                    confidence=0.85,
                    evidence={"source": rel},
                    files_found=[rel],
                ))
            if re.search(r"from flask|import flask", content, re.IGNORECASE):
                sigs.append(TechnologySignature(
                    name="Flask",
                    category="backend",
                    confidence=0.8,
                    evidence={"source": rel},
                    files_found=[rel],
                ))

        return sigs

    def get_supported_validators(self) -> list[str]:
        return [
            "python_validator",
            "django_validator",
            "fastapi_validator",
            "flask_validator",
            "security_validator",
            "dependency_validator",
        ]

    def get_build_commands(self, signatures: list[TechnologySignature]) -> list[str]:
        return ["pip install -r requirements.txt"]

    def get_test_commands(self, signatures: list[TechnologySignature]) -> list[str]:
        return ["pytest", "python -m pytest"]

    def get_runtime_commands(self, signatures: list[TechnologySignature]) -> list[str]:
        names = {s.name for s in signatures}
        if "Django" in names:
            return ["python manage.py runserver"]
        if "FastAPI" in names:
            return ["uvicorn main:app --reload"]
        if "Flask" in names:
            return ["flask run"]
        return ["python main.py"]

    def get_applicable_quality_gates(self) -> list[int]:
        return [1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12]


class NodeTechnologyDetector(BaseTechnologyDetector):
    """Detector for Node.js backend: Express, NestJS, CLI."""

    name = "node"
    category = "backend"

    def detect(self, project_dir: Path) -> list[TechnologySignature]:
        sigs = self._detect_from_package_json(project_dir)
        # Filter to backend-relevant only
        backend_names = {"Express", "NestJS"}
        return [s for s in sigs if s.category == "backend" or s.name in backend_names or s.name == "JavaScript"]

    def get_supported_validators(self) -> list[str]:
        return [
            "javascript_validator",
            "typescript_validator",
            "express_validator",
            "nestjs_validator",
            "api_contract_validator",
            "security_validator",
            "dependency_validator",
        ]

    def get_build_commands(self, signatures: list[TechnologySignature]) -> list[str]:
        return ["npm install", "npm run build"]

    def get_test_commands(self, signatures: list[TechnologySignature]) -> list[str]:
        return ["npm test"]

    def get_runtime_commands(self, signatures: list[TechnologySignature]) -> list[str]:
        names = {s.name for s in signatures}
        if "NestJS" in names:
            return ["npm run start:dev"]
        if "Express" in names:
            return ["node server.js", "npm start"]
        return ["node index.js", "npm start"]

    def get_applicable_quality_gates(self) -> list[int]:
        return [1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12]


class MobileTechnologyDetector(BaseTechnologyDetector):
    """Detector for mobile/cross-platform: React Native, Flutter."""

    name = "mobile"
    category = "mobile"

    def detect(self, project_dir: Path) -> list[TechnologySignature]:
        sigs = self._detect_from_package_json(project_dir)
        # React Native already detected via package.json
        # Check for Flutter
        pubspec = project_dir / "pubspec.yaml"
        if pubspec.exists():
            content = self._read_file(pubspec) or ""
            if "flutter" in content.lower():
                sigs.append(TechnologySignature(
                    name="Flutter",
                    category="mobile",
                    confidence=0.95,
                    evidence={"source": "pubspec.yaml"},
                    files_found=["pubspec.yaml"],
                ))
        return [s for s in sigs if s.category == "mobile"]

    def get_supported_validators(self) -> list[str]:
        return ["react_native_validator", "flutter_validator"]

    def get_build_commands(self, signatures: list[TechnologySignature]) -> list[str]:
        names = {s.name for s in signatures}
        if "Flutter" in names:
            return ["flutter build apk"]
        return ["npm run build"]

    def get_test_commands(self, signatures: list[TechnologySignature]) -> list[str]:
        names = {s.name for s in signatures}
        if "Flutter" in names:
            return ["flutter test"]
        return ["npm test"]

    def get_runtime_commands(self, signatures: list[TechnologySignature]) -> list[str]:
        names = {s.name for s in signatures}
        if "Flutter" in names:
            return ["flutter run"]
        return ["npm start"]

    def get_applicable_quality_gates(self) -> list[int]:
        return [1, 2, 3, 4, 5, 7, 9, 10, 11, 12]


class DatabaseTechnologyDetector(BaseTechnologyDetector):
    """Detector for database technologies: PostgreSQL, MySQL, SQLite, MongoDB."""

    name = "database"
    category = "database"

    def detect(self, project_dir: Path) -> list[TechnologySignature]:
        sigs: list[TechnologySignature] = []

        # Check config/source files for database references
        all_files = []
        for pattern in ("*.py", "*.js", "*.ts", "*.json", "*.yml", "*.yaml", "*.env*", "*.conf"):
            all_files.extend(project_dir.rglob(pattern))

        db_indicators = {
            "postgresql": "PostgreSQL",
            "postgres": "PostgreSQL",
            "psycopg": "PostgreSQL",
            "asyncpg": "PostgreSQL",
            "mysql": "MySQL",
            "pymysql": "MySQL",
            "sqlite3": "SQLite",
            "sqlite": "SQLite",
            "mongodb": "MongoDB",
            "pymongo": "MongoDB",
            "mongoose": "MongoDB",
            "redis": "Redis",
            "prisma": "Prisma ORM",
            "sqlalchemy": "SQLAlchemy",
            "alembic": "Alembic",
        }

        checked = 0
        for f in all_files:
            if checked > 50:
                break
            if "node_modules" in f.parts or ".git" in f.parts or "__pycache__" in f.parts:
                continue
            content = self._read_file(f) or ""
            content_lower = content.lower()
            rel = str(f.relative_to(project_dir))
            checked += 1

            for indicator, db_name in db_indicators.items():
                if indicator in content_lower:
                    sigs.append(TechnologySignature(
                        name=db_name,
                        category="database",
                        confidence=0.7,
                        evidence={"source": rel, "match": indicator},
                        files_found=[rel],
                    ))
                    break  # One match per file

        return sigs

    def get_supported_validators(self) -> list[str]:
        return ["database_validator", "migration_validator", "query_validator"]

    def get_build_commands(self, signatures: list[TechnologySignature]) -> list[str]:
        return ["alembic upgrade head", "prisma migrate deploy"]

    def get_test_commands(self, signatures: list[TechnologySignature]) -> list[str]:
        return []

    def get_runtime_commands(self, signatures: list[TechnologySignature]) -> list[str]:
        return []

    def get_applicable_quality_gates(self) -> list[int]:
        return [4, 5, 10, 11]


class GenericDetector(BaseTechnologyDetector):
    """Fallback detector for unknown/unsupported stacks."""

    name = "generic"
    category = "other"

    def detect(self, project_dir: Path) -> list[TechnologySignature]:
        return [TechnologySignature(
            name="Unknown",
            category="other",
            confidence=0.3,
            evidence={"note": "No recognized technology markers found"},
            files_found=[],
        )]

    def get_supported_validators(self) -> list[str]:
        return []

    def get_build_commands(self, signatures: list[TechnologySignature]) -> list[str]:
        return []

    def get_test_commands(self, signatures: list[TechnologySignature]) -> list[str]:
        return []

    def get_runtime_commands(self, signatures: list[TechnologySignature]) -> list[str]:
        return []

    def get_applicable_quality_gates(self) -> list[int]:
        return [1, 2, 3, 10, 12]
