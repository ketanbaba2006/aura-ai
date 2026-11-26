"""
AURA AI Git Tool
Git operations like commit, pull, push, status, etc.
"""
import subprocess
import logging
from pathlib import Path
from typing import Any

from app.database.schemas import ToolResult
from app.tools.base import BaseTool
from app.memory.project_manager import get_workspace_root

logger = logging.getLogger(__name__)


class GitTool(BaseTool):
    """Tool to interact with git repositories."""

    @property
    def name(self) -> str:
        return "git"

    @property
    def description(self) -> str:
        return (
            "Perform git operations like status, add, commit, pull, push, log, etc. "
            "All operations are sandboxed to the workspace directory."
        )

    @property
    def permission_level(self) -> str:
        return "restricted"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": [
                        "status", "add", "commit", "pull", "push", "log", "diff", 
                        "init", "clone", "checkout", "branch", "reset"
                    ],
                    "description": "Git operation to perform",
                },
                "path": {
                    "type": "string",
                    "description": "Path to the git repository (relative to workspace or absolute)",
                },
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Files to add (for 'add' operation)",
                },
                "message": {
                    "type": "string",
                    "description": "Commit message (for 'commit' operation)",
                },
                "remote": {
                    "type": "string",
                    "description": "Remote name (for 'push' or 'pull' operation, default: origin)",
                },
                "branch": {
                    "type": "string",
                    "description": "Branch name (for 'checkout', 'branch', or 'clone' operation)",
                },
                "repo_url": {
                    "type": "string",
                    "description": "Repository URL (for 'clone' operation)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of log entries to show (for 'log' operation, default: 10)",
                },
            },
            "required": ["operation"],
        }

    def _run_git_command(self, command: list[str], cwd: Path) -> tuple[str, str, int]:
        """Run a git command and return stdout, stderr, and return code."""
        try:
            result = subprocess.run(
                ["git"] + command,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=60.0,
            )
            return result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            return "", "Command timed out after 60 seconds", -1
        except Exception as e:
            return "", f"Error running git command: {e}", -1

    async def execute(self, **kwargs: Any) -> ToolResult:
        operation = kwargs.get("operation", "")
        path = kwargs.get("path", ".")
        files = kwargs.get("files", [])
        message = kwargs.get("message", "")
        remote = kwargs.get("remote", "origin")
        branch = kwargs.get("branch", "")
        repo_url = kwargs.get("repo_url", "")
        limit = kwargs.get("limit", 10)

        try:
            workspace_root = get_workspace_root()
            target_path = (workspace_root / path).resolve()
            
            # Ensure target path is within workspace root
            target_path.relative_to(workspace_root)  # Raises ValueError if outside

            stdout = ""
            stderr = ""
            return_code = 0

            if operation == "status":
                stdout, stderr, return_code = self._run_git_command(["status"], target_path)
            elif operation == "add":
                if not files:
                    return ToolResult(success=False, error="No files specified to add")
                stdout, stderr, return_code = self._run_git_command(["add"] + files, target_path)
            elif operation == "commit":
                if not message:
                    return ToolResult(success=False, error="Commit message required")
                stdout, stderr, return_code = self._run_git_command(
                    ["commit", "-m", message], target_path
                )
            elif operation == "pull":
                args = ["pull"]
                if remote and branch:
                    args.extend([remote, branch])
                stdout, stderr, return_code = self._run_git_command(args, target_path)
            elif operation == "push":
                args = ["push"]
                if remote and branch:
                    args.extend([remote, branch])
                stdout, stderr, return_code = self._run_git_command(args, target_path)
            elif operation == "log":
                stdout, stderr, return_code = self._run_git_command(
                    ["log", "--oneline", "-n", str(limit)], target_path
                )
            elif operation == "diff":
                stdout, stderr, return_code = self._run_git_command(["diff"], target_path)
            elif operation == "init":
                stdout, stderr, return_code = self._run_git_command(["init"], target_path)
            elif operation == "clone":
                if not repo_url:
                    return ToolResult(success=False, error="Repository URL required")
                clone_dir = target_path
                clone_dir.mkdir(parents=True, exist_ok=True)
                stdout, stderr, return_code = self._run_git_command(
                    ["clone", repo_url, str(clone_dir)], workspace_root
                )
            elif operation == "checkout":
                if not branch:
                    return ToolResult(success=False, error="Branch name required")
                stdout, stderr, return_code = self._run_git_command(["checkout", branch], target_path)
            elif operation == "branch":
                args = ["branch"]
                if branch:
                    args.append(branch)
                stdout, stderr, return_code = self._run_git_command(args, target_path)
            elif operation == "reset":
                stdout, stderr, return_code = self._run_git_command(["reset"], target_path)
            else:
                return ToolResult(success=False, error=f"Unknown git operation: {operation}")

            output_parts = []
            if stdout.strip():
                output_parts.append("Output:\n" + stdout.strip())
            if stderr.strip():
                output_parts.append("Error:\n" + stderr.strip())

            if return_code == 0:
                return ToolResult(
                    success=True,
                    output="\n\n".join(output_parts) if output_parts else "Command completed successfully",
                )
            else:
                return ToolResult(
                    success=False,
                    error="\n\n".join(output_parts) if output_parts else f"Command failed with return code {return_code}",
                )

        except ValueError:
            return ToolResult(
                success=False,
                error="Path is outside the workspace directory. Access denied.",
            )
        except Exception as e:
            logger.error(f"Git tool failed: {e}")
            return ToolResult(success=False, error=f"Git operation failed: {str(e)}")
