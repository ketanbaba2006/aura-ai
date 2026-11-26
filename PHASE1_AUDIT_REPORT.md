# AURA AI Coding Studio — Phase 1 Architecture Audit Report

**Date:** 2026-11-27  
**Auditor:** Hermes Agent  
**Target:** AURA AI [ Autonomous Universal Reasoning Agent ] — Backend + Frontend  
**Purpose:** Baseline audit before implementing the AURA Global Quality Engine (AGQE)

---

## 1. Executive Summary

The existing Aura AI Coding Studio is a **functional but limited** autonomous web development platform. It successfully implements:
- A **RouterEngine** for intent classification and request routing
- An **AgentEngine** with Planner → Executor → Validator → Repair loop (3 attempts max)
- A **ProjectManager** for workspace isolation and context injection
- A **CodeRunner** sandbox with LLM-based self-correction
- **BrowserAutomation** via Playwright for web scraping
- **LiveSandbox** frontend with iframe-based preview (HTML/React/Markdown/JSON/SQL)
- SQLite persistence for projects, goals, tasks, conversations, and logs

**Critical Gaps for AGQE Requirements:**
| Requirement | Current Status | Gap Severity |
|-------------|----------------|--------------|
| Universal technology detection | ❌ Hardcoded `"web"` project_type | **CRITICAL** |
| Multi-agent collaboration | ❌ Single AgentEngine, no specialist agents | **CRITICAL** |
| Visual QA / Browser-based testing | ❌ Only iframe preview, no automated visual diff | **CRITICAL** |
| Global Repair Registry | ❌ No persistent repair knowledge base | **CRITICAL** |
| Quality gates pipeline | ⚠️ Basic syntax validation only | **HIGH** |
| Technology-specific validators | ❌ HTML-only tag/brace checking | **HIGH** |
| Regression testing framework | ❌ None | **HIGH** |
| Security validation | ⚠️ Basic BYOK, no code scanning | **MEDIUM** |
| Performance/load testing | ❌ None | **MEDIUM** |
| Accessibility validation | ❌ None | **MEDIUM** |

**Bottom Line:** The platform works for **single-file HTML/React prototypes** but lacks the architectural foundation for a universal, multi-technology, multi-agent quality engine. **Phase 2+ implementation requires substantial new infrastructure.**

---

## 2. Current Architecture Deep Dive

### 2.1 Orchestrator Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      RouterEngine (main entry)                  │
│  Intent Classification → Context → Tools → LLM → Validation     │
└──────────────────────────────┬──────────────────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
       ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
       │  Planner    │  │  Tools      │  │  Knowledge  │
       │ (LLM-based) │  │ (10 tools)  │  │  (ChromaDB) │
       └─────────────┘  └─────────────┘  └─────────────┘
              │
              ▼
       ┌─────────────────────────────────────┐
       │         AgentEngine                 │
       │  ┌───────────────────────────────┐  │
       │  │ 1. PLANNER   → Task Decomposition│  │
       │  │ 2. EXECUTOR  → File Generation  │  │
       │  │ 3. VALIDATOR → Syntax Check     │  │
       │  │ 4. REPAIR    → LLM Fix (×3)     │  │
       │  └───────────────────────────────┘  │
       └─────────────────────────────────────┘
              │
              ▼
       ┌─────────────────────────────────────┐
       │         Project Workspace           │
       │  user_files/Projects/{slug}/        │
       └─────────────────────────────────────┘
```

**Key Classes:**
- `RouterEngine` (`app/router/router_engine.py:179`) — 1215 lines, monolithic routing + execution
- `AgentEngine` (`app/execution/agent_engine.py:24`) — 379 lines, ReAct loop with 3 repair attempts
- `ProjectManager` (`app/memory/project_manager.py:20`) — 222 lines, workspace + context injection

### 2.2 Existing Subagents

**No true subagents exist.** The system has:
- **Single AgentEngine** that acts as Planner + Executor + Validator + Repairer
- **ToolManager** with 10 registered tools (calculator, file_reader, file_writer, system_info, web_search, code_runner, knowledge_retrieval, git, browser_automation)
- **QualityValidator** (`app/core/quality_validator.py`) — LLM-based semantic scoring, NOT code validation

**Missing specialist agents per spec:**
| Spec Agent | Current Equivalent | Gap |
|------------|-------------------|-----|
| Software Architect | None | ❌ |
| UI/UX Designer | None | ❌ |
| Frontend Developer | AgentEngine (monolithic) | ❌ |
| Backend Developer | None | ❌ |
| Database Specialist | None | ❌ |
| Integration Agent | None | ❌ |
| QA Agent | QualityValidator (output only) | ❌ |
| Debugging Agent | CodeRunner self-correction | Partial |
| Security Agent | None | ❌ |

### 2.3 Agent Communication

**No inter-agent communication.** The AgentEngine is a single sequential loop:
```
Planner → Executor → Validator → (Repair ×3) → Next Task
```
- No structured message passing
- No shared task dependency graph
- No review/approval workflows
- No parallel execution

### 2.4 Agent Task Management

**SQLite-backed Goals + Tasks:**
```python
# app/execution/agent_engine.py:100-107
goal_id = uuid.uuid4()
await db.db.goals.insert_one({"id": goal_id, "project_id": ..., "title": goal_text, "status": "in_progress"})
for idx, task in enumerate(tasks_data):
    task_id = uuid.uuid4()
    await db.db.tasks.insert_one({"id": task_id, "goal_id": goal_id, "title": task["title"], "status": "pending", "order_index": idx})
```
- Linear task queue (order_index)
- No dependencies between tasks
- No retry/rollback at task level
- Status: `pending` → `running` → `completed`/`failed`

### 2.5 Shared Workspace & Filesystem

**ProjectManager** (`app/memory/project_manager.py`):
- Workspace root: `get_workspace_root() / "user_files" / "Projects" / {slug}`
- Files scanned for context injection (text extensions only)
- **No version control** (git tool exists but not auto-used)
- **No file locking** or concurrent edit protection
- FileWriterTool writes directly to workspace

### 2.6 Code Generation

**AgentEngine._parse_and_write_files()** (lines 317-336):
- Parses `[FILE: path]\n```ext\ncode\n``` blocks from LLM output
- Writes full file contents (no diff/patch support)
- No syntax validation before write
- No import/dependency analysis

### 2.7 Code Editing

**No surgical editing.** Only full-file rewrites via LLM output parsing.  
FileWriterTool supports `write`, `append`, `mkdir`, `copy`, `move`, `delete` but AgentEngine doesn't use it for edits.

### 2.8 Build System

**None.** Projects are static file collections. No:
- Package.json / dependency management
- Build scripts (vite, webpack, next.js)
- TypeScript compilation
- Bundling/minification
- The LiveSandbox runs React via Babel standalone in-browser

### 2.9 Runtime Environment

**CodeRunner** (`app/execution/code_runner.py`):
- Sandbox directory: `backend/execution_sandbox/`
- Supports: Python, JS/Node, TypeScript (tsx), C++, Java, Go, Rust, Bash
- **Per-execution subprocess** (no persistent process)
- LLM-based self-correction on failure (1 retry)
- 10-30s timeout

**LiveSandbox** (frontend) — iframe preview only:
- HTML: Tailwind CDN + raw HTML body
- React/JSX: Babel standalone + React UMD + lucide-react mock
- CSS: Visual test harness with mock components
- Python/JS/Go/Rust: SSE stream to backend CodeRunner
- SQL: Mock data simulator

### 2.10 Preview Infrastructure

**LiveSandbox.tsx** — Client-side iframe preview:
- No server-side rendering
- No real browser automation for testing
- Console capture via `postMessage`
- Manual reload button
- **No visual regression, no responsive testing, no accessibility audit**

### 2.11 Testing System

**None.** Only:
- `CodeRunner` executes user code snippets
- `AgentEngine._validate_files()` — brace/tag matching only
- `QualityValidator` — LLM scores output completeness (not code correctness)

### 2.12 Debugging System

**CodeRunner.execute_with_retry()** (lines 344-393):
- On failure → LLM prompt with stdout/stderr → corrected code → re-run
- Single retry, no root cause analysis
- No breakpoint/step debugging
- No stack trace correlation with source

### 2.13 Error Handling

| Layer | Mechanism |
|-------|-----------|
| Tool execution | Try/catch → ToolResult(success=False, error) |
| AgentEngine | Try/catch per task → validation errors → repair loop (×3) |
| RouterEngine | Try/catch per stage → fallback to direct LLM response |
| CodeRunner | Subprocess timeout/termination → error output |
| Frontend | Error boundaries absent; try/catch in event handlers |

### 2.14 Project Persistence

**SQLite (aiosqlite)** via `app/database/database.py`:
- Tables: projects, conversations, messages, goals, tasks, knowledge_documents, activity_logs, system_settings
- Vector store: ChromaDB for memories + knowledge base
- File storage: `user_files/Projects/{slug}/` (raw files)
- **No migration system**, **no schema versioning**

### 2.15 Database

**SQLite + ChromaDB:**
- SQLite: `aura.db` in backend root
- ChromaDB: `chroma_db/` for embeddings
- No connection pooling (single-file SQLite)
- No backup/replication

### 2.16 Logging

**ActivityLogger** (`app/logs/activity_logger.py`):
- Structured logs to SQLite: action_type, category, description, details(JSON), status
- Categories: router, tools, knowledge, memory, chat, agent, security
- **No structured error tracking**, no correlation IDs

### 2.17 Export Functionality

**ProjectsRouter.download_project** (`app/api/routes/projects.py:106-126`):
- `shutil.make_archive()` → ZIP download
- No verification that exported files match validated revision
- No manifest/checksum

---

## 3. Existing Quality Checks Assessment

| Check | Implementation | Status | Evidence |
|-------|---------------|--------|----------|
| HTML tag matching | `_validate_files()` regex | ✅ Implemented | agent_engine.py:362-372 |
| Brace/bracket matching | `_validate_files()` count | ✅ Implemented | agent_engine.py:353-359 |
| Semantic output quality | `QualityValidator` (LLM) | ⚠️ Partial | quality_validator.py:76-151 |
| Code execution | `CodeRunner` sandbox | ✅ Implemented | code_runner.py:38-192 |
| Self-correction | `execute_with_retry()` | ⚠️ Basic | code_runner.py:344-393 |
| Browser automation | `BrowserAutomationTool` | ✅ Implemented | browser_automation.py:16-139 |
| Visual QA | **None** | ❌ Missing | — |
| Type checking | **None** | ❌ Missing | — |
| Linting | **None** | ❌ Missing | — |
| Dependency validation | **None** | ❌ Missing | — |
| Security scanning | **None** | ❌ Missing | — |
| Accessibility | **None** | ❌ Missing | — |
| Performance | **None** | ❌ Missing | — |
| Regression testing | **None** | ❌ Missing | — |

**Why coding errors reach final application:**
1. **Validator only checks syntax** (braces, tags) — no semantic correctness
2. **No build step** — TypeScript/React errors only surface in LiveSandbox iframe
3. **No integration testing** — frontend/backend/API contracts never verified
4. **Repair loop is local** — fixes syntax only, not logic/architecture
5. **No visual regression** — UI breaks invisible to automated checks
6. **Single-agent** — no specialist review (security, DB, UX, etc.)

---

## 4. Technology Stack Detection — Current State

**Hardcoded to "web":**
```python
# agent_engine.py:49
active_project = await project_manager.create_project(
    ...
    project_type="web",  # HARDCODED
    ...
)

# project_manager.py:35
project_type: str | None = "web",  # DEFAULT
```

**No detection of:**
- package.json / requirements.txt / Cargo.toml / go.mod / pom.xml
- Framework markers (next.config.js, vite.config.ts, django settings, etc.)
- Language composition of project files
- Build/test commands

---

## 5. AGQE Implementation — Required New Components

Based on the 20-phase specification, the following **new modules** must be created:

### 5.1 Core AGQE Service (`app/quality/`)
```
app/quality/
├── __init__.py
├── engine.py                 # AGQE central coordinator
├── registry.py               # Global Repair Registry (SQLite + ChromaDB)
├── detectors/
│   ├── __init__.py
│   ├── base.py               # TechnologyDetector interface
│   ├── web.py                # HTML/CSS/JS/TS/React/Next/Vue/Svelte
│   ├── python.py             # Django/FastAPI/Flask/CLI
│   ├── node.py               # Express/NestJS/CLI
│   ├── mobile.py             # React Native/Flutter
│   ├── database.py           # PostgreSQL/MySQL/SQLite/MongoDB
│   └── generic.py            # Fallback detector
├── validators/
│   ├── __init__.py
│   ├── base.py               # Validator interface
│   ├── html_validator.py     # html5lib, tidy
│   ├── css_validator.py      # css-tree, stylelint
│   ├── js_ts_validator.py    # eslint, tsc, biome
│   ├── python_validator.py   # ruff, mypy, bandit
│   ├── framework_validator.py# React/Vue/Angular/Svelte specific
│   ├── backend_validator.py  # OpenAPI, pydantic, SQLAlchemy
│   ├── database_validator.py # alembic, prisma, migrations
│   ├── security_validator.py # bandit, semgrep, dependency-check
│   ├── accessibility_validator.py # axe-core
│   └── performance_validator.py  # lighthouse, custom
├── visual_qa/
│   ├── __init__.py
│   ├── browser_engine.py     # Playwright manager (persistent)
│   ├── screenshot.py         # Capture + diff
│   ├── responsive.py         # Multi-viewport testing
│   └── design_spec.py        # Design token comparison
├── gates/
│   ├── __init__.py
│   ├── pipeline.py           # QualityGatePipeline
│   ├── gate_1_requirements.py
│   ├── gate_2_architecture.py
│   ├── gate_3_implementation.py
│   ├── gate_4_static.py
│   ├── gate_5_integration.py
│   ├── gate_6_build.py
│   ├── gate_7_runtime.py
│   ├── gate_8_visual.py
│   ├── gate_9_functional.py
│   ├── gate_10_security.py
│   ├── gate_11_regression.py
│   └── gate_12_delivery.py
├── repair/
│   ├── __init__.py
│   ├── engine.py             # AutonomousRepairEngine
│   ├── patterns.py           # RepairPattern matching
│   ├── patcher.py            # Safe patch application
│   └── rollback.py           # Version tracking + rollback
├── agents/
│   ├── __init__.py
│   ├── orchestrator.py       # QualityOrchestrator
│   ├── architect.py          # SoftwareArchitectAgent
│   ├── ui_designer.py        # UIDesignerAgent
│   ├── frontend_dev.py       # FrontendDeveloperAgent
│   ├── backend_dev.py        # BackendDeveloperAgent
│   ├── db_specialist.py      # DatabaseSpecialistAgent
│   ├── integration.py        # IntegrationAgent
│   ├── qa_agent.py           # QAAgent
│   ├── debugger.py           # DebuggingAgent
│   └── security.py           # SecurityAgent
├── specs/
│   ├── __init__.py
│   ├── project_spec.py       # ProjectQualitySpecification
│   └── versioning.py         # Spec version control
└── dashboard/
    ├── __init__.py
    ├── api.py                # Dashboard REST API
    └── websocket.py          # Real-time updates
```

### 5.2 Database Schema Extensions
```sql
-- Quality engine tables
CREATE TABLE quality_projects (
    id TEXT PRIMARY KEY,
    project_id TEXT REFERENCES projects(id),
    tech_stack JSON,           -- detected technologies
    spec_version INTEGER,
    registered_at TIMESTAMP,
    last_validated_at TIMESTAMP
);

CREATE TABLE quality_gates (
    id TEXT PRIMARY KEY,
    project_id TEXT,
    gate_number INTEGER,
    gate_name TEXT,
    status TEXT,               -- pending, running, passed, failed, skipped
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    results JSON,
    evidence JSON
);

CREATE TABLE defects (
    id TEXT PRIMARY KEY,
    project_id TEXT,
    gate_id TEXT,
    category TEXT,             -- per spec classification
    severity TEXT,             -- critical, high, medium, low
    file_path TEXT,
    line_start INTEGER,
    line_end INTEGER,
    evidence TEXT,
    root_cause TEXT,
    assigned_agent TEXT,
    repair_id TEXT,
    status TEXT,               -- open, investigating, repairing, verified, closed
    created_at TIMESTAMP,
    resolved_at TIMESTAMP
);

CREATE TABLE repair_registry (
    id TEXT PRIMARY KEY,
    error_fingerprint TEXT UNIQUE,  -- hash of generalized pattern
    error_category TEXT,
    technologies JSON,              -- applicable tech stack
    root_cause TEXT,
    solution_pattern TEXT,          -- generalized fix
    validation_method TEXT,
    regression_test TEXT,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    confidence REAL,
    created_at TIMESTAMP,
    last_verified_at TIMESTAMP,
    is_global BOOLEAN DEFAULT 1
);

CREATE TABLE project_repair_history (
    id TEXT PRIMARY KEY,
    project_id TEXT,
    defect_id TEXT,
    repair_registry_id TEXT,
    patch_applied TEXT,          -- unified diff
    validation_result JSON,
    success BOOLEAN,
    applied_at TIMESTAMP
);

CREATE TABLE regression_rules (
    id TEXT PRIMARY KEY,
    repair_registry_id TEXT,
    rule_type TEXT,              -- validator, pattern, template
    rule_config JSON,
    active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP
);
```

### 5.3 Integration Points with Existing Code

| Existing Component | Integration Required |
|-------------------|---------------------|
| `RouterEngine` | Route `WEBSITE_BUILDER`/`APP_BUILDER` → AGQE pipeline |
| `AgentEngine` | Replace Validator/Repair loop with AGQE gates |
| `ProjectManager` | Auto-register projects with AGQE on creation |
| `CodeRunner` | Use as runtime validator (Gate 7) |
| `BrowserAutomationTool` | Upgrade to persistent browser pool for Visual QA |
| `LiveSandbox` | Add AGQE status panel, gate results, defect list |
| `QualityValidator` | Repurpose as output-quality gate (Gate 12) |
| `ToolManager` | Register AGQE validator tools |
| `activity_logger` | Extend with quality events |

---

## 6. Implementation Priority & Effort Estimate

| Phase | Component | Effort | Dependencies |
|-------|-----------|--------|--------------|
| 1 | **Audit** (this report) | ✅ Done | — |
| 2 | **AGQE Core + Tech Detection** | 3-4 days | Database schema |
| 3 | **Validator Adapters (Web)** | 2-3 days | AGQE Core |
| 4 | **Validator Adapters (Python/Node/DB)** | 2-3 days | AGQE Core |
| 5 | **Agent Framework + Specialist Agents** | 4-5 days | AGQE Core, LLM prompts |
| 6 | **Quality Gates Pipeline** | 2-3 days | Validators, Agents |
| 7 | **Visual QA Engine** | 3-4 days | Playwright pool, design spec |
| 8 | **Error Classification + Defect DB** | 1-2 days | Database schema |
| 9 | **Global Repair Registry** | 2-3 days | ChromaDB, pattern matching |
| 10 | **Autonomous Repair Engine** | 3-4 days | Agents, Patcher, Rollback |
| 11 | **Quality Dashboard API + UI** | 2-3 days | WebSocket, React components |
| 12 | **Regression Testing Framework** | 2-3 days | Test fixtures, CI integration |
| 13 | **Security/Privacy Hardening** | 1-2 days | Sanitization, access control |
| 14 | **Performance Optimization** | 1-2 days | Caching, parallelization |
| 15 | **Multi-Project Verification** | 2-3 days | Test fixtures, automation |
| **Total** | **Core AGQE MVP** | **~30-40 days** | — |

---

## 7. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| LLM repair loops diverge | High | High | Bounded attempts, diff inspection, rollback |
| Visual QA flakiness | High | Medium | Retry logic, deterministic viewports, baseline images |
| Repair registry pollution | Medium | High | Strict sanitization, confidence thresholds, human review |
| Performance degradation | Medium | High | Incremental validation, caching, background workers |
| Schema migration complexity | Medium | Medium | Alembic migrations, versioned specs |
| Agent prompt engineering | High | Medium | Structured prompts, few-shot examples, evaluation harness |

---

## 8. Conclusion

The current Aura AI Coding Studio is a **promising prototype** for autonomous HTML/React generation but **architecturally insufficient** for the AGQE vision. The monolithic AgentEngine, hardcoded web-only assumption, absence of specialist agents, and lack of any persistent quality infrastructure mean **Phases 2-20 require building ~80% new code**.

**Recommended next step:** Begin Phase 2 implementation with:
1. Database migration for quality tables
2. `TechnologyDetector` interface + Web/Python/Node adapters
3. `QualityValidator` base class + HTML/CSS/JS validators
4. `ProjectQualitySpecification` model + auto-registration hook in `ProjectManager.create_project()`

This establishes the foundation for all subsequent phases.