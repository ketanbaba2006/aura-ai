"""
AURA AI Project Memory Manager
Handles SQLite project mapping, filesystem code scans, active context linkage, and LLM prompt context injection.
"""

import json
import logging
import re
import uuid
from datetime import datetime
from pathlib import Path

from app.database.database import db

logger = logging.getLogger(__name__)

def get_workspace_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent

class ProjectManager:
    """Manages active project contexts, directories, file summaries, and prompt mapping."""

    def _slugify(self, name: str) -> str:
        """Convert a project name into a clean directory name."""
        slug = name.lower().strip()
        slug = re.sub(r"[^a-z0-9\s_-]", "", slug)
        slug = re.sub(r"[\s_-]+", "_", slug)
        return slug or "default_project"

    async def create_project(
        self,
        name: str,
        description: str | None = None,
        conversation_id: str | None = None,
        project_type: str | None = "web",
        design_choices: str | None = "",
        user_goals: str | None = ""
    ) -> dict:
        """Create a new project entry and initialize its workspace folder."""
        project_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        # Insert project record in SQLite
        await db.db.projects.insert_one({"id": project_id, "name": name, "description": description, "conversation_id": conversation_id, "project_type": project_type, "design_choices": design_choices, "user_goals": user_goals, "created_at": now, "updated_at": now})

        # Link conversation to this project if conversation_id provided
        if conversation_id:
            await self.set_active_project(conversation_id, project_id)

        # Initialize workspace folder
        slug = self._slugify(name)
        project_dir = get_workspace_root() / "user_files" / "Projects" / slug
        project_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Created project record '{name}' ({project_id}) with folder path 'user_files/Projects/{slug}'")

        # Auto-register with AURA Global Quality Engine
        try:
            from app.quality.engine import agqe
            import asyncio
            # Schedule registration (non-blocking); project_dir already created above
            project_dir = get_workspace_root() / "user_files" / "Projects" / slug
            asyncio.create_task(agqe.on_project_created(project_id, project_dir))
        except Exception as e:
            logger.warning(f"AGQE auto-registration skipped for project {project_id}: {e}")

        return {
            "id": project_id,
            "name": name,
            "description": description,
            "conversation_id": conversation_id,
            "project_type": project_type,
            "design_choices": design_choices,
            "user_goals": user_goals,
            "slug": slug,
        }

    async def get_project(self, project_id: str) -> dict | None:
        """Retrieve project metadata."""
        row = await db.db.projects.find_one({"id": project_id})
        if not row:
            return None
        project = dict(row)
        project["slug"] = self._slugify(project["name"])
        return project

    async def list_projects(self, include_archived: bool = False) -> list[dict]:
        """List all projects in the database, ordered by latest updated."""
        if include_archived:
            rows = await db.db.projects.find({}).sort("updated_at", -1).to_list(length=None)
        else:
            rows = await db.db.projects.find({"archived": 0}).sort("updated_at", -1).to_list(length=None)
        projects = []
        for r in rows:
            p = dict(r)
            p["slug"] = self._slugify(p["name"])
            projects.append(p)
        return projects

    async def archive_project(self, project_id: str, archived: bool = True) -> None:
        """Mark a project as archived or active."""
        now = datetime.utcnow().isoformat()
        val = 1 if archived else 0
        await db.db.projects.update_one({"id": project_id}, {"$set": {"archived": val, "updated_at": now}})
        logger.info(f"Project {project_id} archived status set to {archived}")

    async def get_active_project(self, conversation_id: str) -> dict | None:
        """Get the active project linked to the specified conversation."""
        row = await db.db.conversations.find_one({"id": conversation_id}, {"active_project_id": 1})
        if not row or not row.get("active_project_id"):
            return None
        return await self.get_project(row.get("active_project_id"))

    async def set_active_project(self, conversation_id: str, project_id: str) -> None:
        """Associate a project as the active target for a conversation session."""
        now = datetime.utcnow().isoformat()
        # Set active project
        await db.db.conversations.update_one({"id": conversation_id}, {"$set": {"active_project_id": project_id, "updated_at": now}})
        # Update project modified time
        await db.db.projects.update_one({"id": project_id}, {"$set": {"updated_at": now}})
        logger.info(f"Linked conversation {conversation_id} to active project {project_id}")

    async def reset_active_project(self, conversation_id: str) -> None:
        """Unlink the active project context from a conversation session."""
        await db.db.conversations.update_one({"id": conversation_id}, {"$set": {"active_project_id": None, "updated_at": datetime.utcnow().isoformat()}})
        logger.info(f"Reset active project context for conversation {conversation_id}")

    async def detect_and_link_project(self, conversation_id: str, message: str) -> dict | None:
        """
        No keyword heuristics. If no active project is linked to the conversation,
        link the most recently active project globally.
        """
        try:
            # First check if there is already an active project
            active = await self.get_active_project(conversation_id)
            if active:
                return active

            # Find the most recently updated project
            row = await db.db.projects.find_one({}, sort=[("updated_at", -1)])
            if row:
                project_id = row["id"]
                await self.set_active_project(conversation_id, project_id)
                logger.info(f"Persistently linked conversation {conversation_id} to most recent project {project_id}")
                return await self.get_project(project_id)
        except Exception as e:
            logger.warning(f"detect_and_link_project failed (non-fatal): {e}")
            
        return None

    async def get_project_context(self, project_id: str) -> str:
        """
        Scan the project subdirectory under user_files/Projects/{slug}/, reads text contents,
        and constructs a structured codebase summary for LLM context injection.
        """
        project = await self.get_project(project_id)
        if not project:
            return ""

        slug = project["slug"]
        project_dir = get_workspace_root() / "user_files" / "Projects" / slug
        
        # Context header
        context_parts = []
        context_parts.append("=========================================")
        context_parts.append(f"CURRENT ACTIVE PROJECT CONTEXT: {project['name']}")
        context_parts.append(f"Project Type: {project.get('project_type') or 'web'}")
        if project.get("description"):
            context_parts.append(f"Description: {project['description']}")
        if project.get("design_choices"):
            context_parts.append(f"Design Choices: {project['design_choices']}")
        if project.get("user_goals"):
            context_parts.append(f"User Goals: {project['user_goals']}")
        context_parts.append("=========================================\n")

        context_parts.append("=========================================")
        context_parts.append("CRITICAL INSTRUCTIONS FOR PROJECT EDITING:")
        context_parts.append("1. You are modifying an EXISTING project. Do NOT restart or recreate the project from scratch unless explicitly asked.")
        context_parts.append("2. Output surgical diffs or file edits for existing files, instead of rewriting the entire file contents.")
        context_parts.append("3. Only provide the code that changed, mentioning the exact file name. Assume the user will apply these edits natively.")
        context_parts.append("4. Retain all previous structure and only respond with the necessary updates to fulfill the user's latest prompt.")
        context_parts.append("=========================================\n")

        # Associated goals and sub-tasks history checklist
        goals = await db.db.goals.find({"project_id": project_id}).sort("created_at", 1).to_list(length=None)
        if goals:
            context_parts.append("=========================================")
            context_parts.append("PROJECT GOALS & SUB-TASKS HISTORY CHECKLIST:")
            for g in goals:
                context_parts.append(f"Goal: {g['title']} [Status: {g['status']}]")
                tasks = await db.db.tasks.find({"goal_id": g["id"]}).sort("order_index", 1).to_list(length=None)
                for t in tasks:
                    status_marker = "[✓]" if t["status"] == "completed" else "[ ]"
                    context_parts.append(f"  {status_marker} {t['title']} (Status: {t['status']})")
            context_parts.append("=========================================\n")

        # Exclude patterns
        exclude_dirs = {".git", "node_modules", "venv", "__pycache__", ".next", "dist", "build"}
        text_extensions = {".html", ".css", ".js", ".jsx", ".ts", ".tsx", ".md", ".json", ".txt"}

        # Scan files
        files_found = []
        if project_dir.exists() and project_dir.is_dir():
            for filepath in sorted(project_dir.rglob("*")):
                if any(p in filepath.parts for p in exclude_dirs):
                    continue
                if filepath.is_file() and filepath.suffix.lower() in text_extensions:
                    files_found.append(filepath)

        if not files_found:
            context_parts.append("No files generated in workspace yet.")
        else:
            context_parts.append("Current Codebase Summary:")
            # File list
            for filepath in files_found:
                rel_path = filepath.relative_to(project_dir)
                size_kb = filepath.stat().st_size / 1024
                context_parts.append(f"- Projects/{slug}/{rel_path} ({size_kb:.2f} KB)")
            context_parts.append("\nFile Contents:")
            
            # Content dump
            for filepath in files_found:
                rel_path = filepath.relative_to(project_dir)
                try:
                    content = filepath.read_text(encoding="utf-8", errors="replace")
                    context_parts.append(f"--- START FILE: Projects/{slug}/{rel_path} ---")
                    context_parts.append(content)
                    context_parts.append(f"--- END FILE: Projects/{slug}/{rel_path} ---\n")
                except Exception as e:
                    logger.error(f"Failed to read project file {filepath}: {e}")

        return "\n".join(context_parts)

# Global project manager instance
project_manager = ProjectManager()
