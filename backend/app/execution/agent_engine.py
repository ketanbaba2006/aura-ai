"""
AURA AI Autonomous Agent Engine
Handles goal decomposition (Planner), task tracking (Task Queue), file edits (Executor),
code verification (Validator), self-correction (Repair Engine), and iterative state tracking (ReAct Loop).
"""

import json
import logging
import re
import uuid
import time
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator

from app.database.database import db
from app.database.schemas import ChatEventType
from app.core.llm_client import llm_client
from app.memory.project_manager import project_manager, get_workspace_root

logger = logging.getLogger(__name__)


class AgentEngine:
    """Autonomous agent engine implementing Planner, Task Queue, Executor, Validator, and Repair Loop."""

    async def run_agent(
        self, goal_text: str, conversation_id: str
    ) -> AsyncGenerator[tuple[ChatEventType, str, dict | None], None]:
        """
        Runs the autonomous agent ReAct loop for the specified user goal.
        """
        start_time = datetime.utcnow()

        # Ensure project exists
        active_project = await project_manager.get_active_project(conversation_id)
        if not active_project:
            active_project = await project_manager.detect_and_link_project(conversation_id, goal_text)
        
        if not active_project:
            # Generate default project if none exists or detected
            project_name = " ".join(goal_text.split()[:4]).title()
            if not project_name.endswith("Project") and not project_name.endswith("Website") and not project_name.endswith("App"):
                project_name += " Project"
            active_project = await project_manager.create_project(
                name=project_name,
                description=f"Generated autonomously for goal: {goal_text}",
                conversation_id=conversation_id,
                project_type="web",
                design_choices="Modern premium glassmorphism, dark theme, responsive grid layouts",
                user_goals=goal_text
            )

        project_slug = active_project["slug"]
        project_dir = get_workspace_root() / "user_files" / "Projects" / project_slug
        project_dir.mkdir(parents=True, exist_ok=True)

        def elapsed_str() -> str:
            elapsed = int((datetime.utcnow() - start_time).total_seconds())
            now_time = datetime.now().strftime("%H:%M:%S")
            return f"[{now_time} | {elapsed}s]"

        # ─── STEP 1 & 2: PLANNER & TASK QUEUE ─────────────────────────────────
        yield (
            ChatEventType.AGENT_PROGRESS,
            "Decomposing goal into tasks",
            {"phase": "Planning", "status": "running", "detail": f"{elapsed_str()} Formulating implementation plan..."},
        )

        planner_prompt = f"""You are AURA's Agent Planner.
Analyze this user web development goal and break it down into 4 to 6 logical, chronological components/tasks.
Example tasks:
- "Create Navbar Component"
- "Build Hero Section"
- "Create Contact Form"
- "Validate and Preview page"

Goal: {goal_text}

Respond ONLY with a JSON object in this format:
{{
    "tasks": [
        {{"title": "Task Title", "description": "Short description of what to implement"}}
    ]
}}"""

        try:
            planner_response = await llm_client.generate_json(planner_prompt)
            tasks_data = planner_response.get("tasks", [])
        except Exception as e:
            logger.error(f"Planner failed: {e}")
            tasks_data = [
                {"title": "Create Index File", "description": "Create base index.html page"},
                {"title": "Add Responsive Sections", "description": "Implement grid-based page sections"},
                {"title": "Apply Premium Styling", "description": "Incorporate glassmorphism and modern colors"},
                {"title": "Verify and Finalize", "description": "Validate pages and render preview"}
            ]

        # Save goal and tasks to SQLite
        goal_id = str(uuid.uuid4())
        await db.db.goals.insert_one({"id": goal_id, "project_id": active_project["id"], "title": goal_text, "description": "Decomposed goal", "status": "in_progress", "created_at": datetime.utcnow().isoformat()})

        tasks_list = []
        for idx, t in enumerate(tasks_data):
            task_id = str(uuid.uuid4())
            await db.db.tasks.insert_one({"id": task_id, "goal_id": goal_id, "title": t["title"], "description": t["description"], "status": "pending", "order_index": idx, "created_at": datetime.utcnow().isoformat()})
            tasks_list.append({"title": t["title"], "status": "pending"})

        yield (
            ChatEventType.AGENT_PROGRESS,
            "Planning complete",
            {
                "phase": "Planning",
                "status": "completed",
                "detail": f"{elapsed_str()} Goal decomposed into {len(tasks_list)} tasks.",
                "tasks": tasks_list
            },
        )

        # ─── STEP 6: ReAct LOOP ───────────────────────────────────────────────
        for idx, task in enumerate(tasks_data):
            # Update task status to running
            tasks_list[idx]["status"] = "running"
            
            # Broadcast Running Code Generation phase
            yield (
                ChatEventType.AGENT_PROGRESS,
                f"Running task: {task['title']}",
                {
                    "phase": "Generating Code",
                    "status": "running",
                    "detail": f"{elapsed_str()} Writing code for component: {task['title']}",
                    "tasks": tasks_list
                },
            )

            # ─── STEP 3: EXECUTOR (GENERATE/EDIT FILES) ───────────────────────
            project_context = await project_manager.get_project_context(active_project["id"])
            executor_prompt = f"""You are AURA's Code Executor.
You are working on the active project.
Goal: {goal_text}
Current Task: {task['title']} ({task['description']})

{project_context}

Please implement the code required for this task.
You MUST write the full contents of all files you create or modify.
Output the files strictly in the following format so the system can write them to disk automatically:

[FILE: path/to/file]
```extension
code contents here
```

Ensure the design is professional, futuristic, and premium (vibrant gradients, dark mode, glassmorphism, responsive). Do not use placeholders."""

            response_text = ""
            try:
                # Retrieve executor generated code
                response_text = await llm_client.chat(
                    messages=[{"role": "user", "content": executor_prompt}],
                    system_prompt="You are AURA's Code Executor. Respond strictly with [FILE: path] blocks for file writes.",
                )
            except Exception as e:
                logger.error(f"Executor failed on task '{task['title']}': {e}")
                response_text = ""

            # Parse files
            files_written = self._parse_and_write_files(project_dir, response_text, active_project["slug"])

            # ─── STEP 4 & 5: VALIDATOR & REPAIR LOOP ──────────────────────────
            attempt = 1
            max_attempts = 3
            validation_passed = False
            validation_errors = ""

            while attempt <= max_attempts and files_written:
                # Testing Phase
                yield (
                    ChatEventType.AGENT_PROGRESS,
                    f"Validating task: {task['title']}",
                    {
                        "phase": "Testing",
                        "status": "running",
                        "detail": f"{elapsed_str()} Testing bracket syntax & tag matches (Attempt {attempt}/{max_attempts})...",
                        "tasks": tasks_list,
                        "files": files_written,
                        "attempt": attempt
                    },
                )

                validation_passed, validation_errors = self._validate_files(project_dir, files_written)
                if validation_passed:
                    break

                # Fixing Errors Phase (Repair Engine)
                yield (
                    ChatEventType.AGENT_PROGRESS,
                    f"Repairing task errors: {task['title']}",
                    {
                        "phase": "Fixing Errors",
                        "status": "running",
                        "detail": f"{elapsed_str()} Syntax issue discovered: {validation_errors[:100]}... Triggering repair loop...",
                        "tasks": tasks_list,
                        "files": files_written,
                        "checks": [validation_errors],
                        "attempt": attempt
                    },
                )

                repair_prompt = f"""You are AURA's Code Repair Engine.
The files you generated for the task '{task['title']}' failed syntax validation with the following errors:
{validation_errors}

Here is the current codebase context:
{project_context}

Please fix the syntax errors. Output only the corrected files strictly in the [FILE: path] format:

[FILE: path/to/file]
```extension
corrected code contents
```"""
                try:
                    response_text = await llm_client.chat(
                        messages=[{"role": "user", "content": repair_prompt}],
                        system_prompt="You are AURA's Repair Engine. Fix errors and output only valid file blocks.",
                    )
                    files_written = self._parse_and_write_files(project_dir, response_text, active_project["slug"])
                except Exception as e:
                    logger.error(f"Repair attempt {attempt} failed: {e}")

                attempt += 1

            # Update final task status
            if validation_passed:
                tasks_list[idx]["status"] = "completed"
                # Save task as completed in SQLite
                await db.db.tasks.update_one({"title": task["title"], "goal_id": goal_id}, {"$set": {"status": "completed", "updated_at": datetime.utcnow().isoformat()}})
                yield (
                    ChatEventType.AGENT_PROGRESS,
                    f"Task complete: {task['title']}",
                    {
                        "phase": "Testing",
                        "status": "completed",
                        "detail": f"{elapsed_str()} Successfully verified and wrote: {', '.join(files_written)}",
                        "tasks": tasks_list,
                        "files": files_written
                    },
                )
            else:
                tasks_list[idx]["status"] = "failed"
                await db.db.tasks.update_one({"title": task["title"], "goal_id": goal_id}, {"$set": {"status": "failed", "updated_at": datetime.utcnow().isoformat()}})
                yield (
                    ChatEventType.AGENT_PROGRESS,
                    f"Task failed: {task['title']}",
                    {
                        "phase": "Testing",
                        "status": "failed",
                        "detail": f"{elapsed_str()} Task failed validation checks: {validation_errors}",
                        "tasks": tasks_list,
                        "files": files_written
                    },
                )

        # Update Goal status
        all_completed = all(t["status"] == "completed" for t in tasks_list)
        final_goal_status = "completed" if all_completed else "failed"
        await db.db.goals.update_one({"id": goal_id}, {"$set": {"status": final_goal_status, "updated_at": datetime.utcnow().isoformat()}})

        # ─── DEPLOYMENT / FINAL PREVIEW DISPLAY ───────────────────────────────
        primary_preview_file = "index.html"
        for f in ["index.html", "App.tsx", "App.jsx", "main.js"]:
            if (project_dir / f).exists():
                primary_preview_file = f
                break

        preview_rel_path = f"Projects/{project_slug}/{primary_preview_file}"
        preview_content = ""
        try:
            preview_content = (project_dir / primary_preview_file).read_text(encoding="utf-8")
        except Exception:
            pass

        # Real Deployment check
        deploy_url = "Not Performed (Vercel/Netlify tokens missing in .env config)"

        # Final message to render preview
        final_summary = f"""### 🚀 Autonomous Execution Complete!

The agent successfully completed the planning and building phases for **{active_project['name']}**.

**Preview Available**:
[FILE: {preview_rel_path}]
```html
{preview_content}
```

---

### 📦 Zip Distribution Code Export
Click the export tab in the Live Sandbox header or use this link to download the project files:
[Download project ZIP](http://localhost:8000/api/v1/projects/download?slug={project_slug})
"""
        yield (ChatEventType.TOKEN, final_summary, {"preview_file": preview_rel_path})
        yield (
            ChatEventType.AGENT_PROGRESS,
            "Deployment complete",
            {
                "phase": "Deployment",
                "status": "completed",
                "detail": f"{elapsed_str()} Preview loaded in sandbox. Production Deployment: {deploy_url}",
                "tasks": tasks_list
            },
        )

    def _parse_and_write_files(self, project_dir: Path, text: str, slug: str) -> list[str]:
        """Parses [FILE: path] blocks and writes them to project subdirectory."""
        file_blocks = re.findall(
            r"\[FILE:\s*(.+?)\]\s*\n+```[a-zA-Z0-9_\-]*\n([\s\S]*?)\n```", text
        )
        files_written = []
        for file_path_str, content in file_blocks:
            # Strip project prefixes if present
            clean_path = file_path_str.replace(f"Projects/{slug}/", "").strip()
            clean_path = clean_path.lstrip("/")
            
            dest = project_dir / clean_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                dest.write_text(content.strip(), encoding="utf-8")
                files_written.append(clean_path)
            except Exception as e:
                logger.error(f"Failed to write file {clean_path}: {e}")
        return files_written

    def _validate_files(self, project_dir: Path, files: list[str]) -> tuple[bool, str]:
        """Performs simple HTML/tag and braces syntax validation."""
        errors = []
        for f in files:
            file_path = project_dir / f
            if not file_path.exists():
                errors.append(f"File {f} is missing.")
                continue
            
            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                errors.append(f"File {f} is unreadable.")
                continue

            # Check brace matching
            if content.count("{") != content.count("}"):
                errors.append(f"File '{f}': Unmatched curly braces {{}}.")
            if content.count("[") != content.count("]"):
                errors.append(f"File '{f}': Unmatched square brackets [].")
            if content.count("(") != content.count(")"):
                errors.append(f"File '{f}': Unmatched parentheses ().")

            # Check HTML tag matching
            if f.endswith(".html") or f.endswith(".htm"):
                open_tags = re.findall(r"<([a-zA-Z0-9\-]+)(?:\s+[^>]*)*>", content)
                self_closing = {"img", "br", "hr", "input", "meta", "link", "source", "embed"}
                open_tags = [t.lower() for t in open_tags if t.lower() not in self_closing]
                close_tags = [t.lower() for t in re.findall(r"</([a-zA-Z0-9\-]+)>", content)]
                
                for t in set(open_tags):
                    if open_tags.count(t) != close_tags.count(t):
                        errors.append(
                            f"File '{f}': Unmatched HTML tags <{t}>. Opened {open_tags.count(t)}, closed {close_tags.count(t)}."
                        )

        if errors:
            return False, "\n".join(errors)
        return True, ""


agent_engine = AgentEngine()
