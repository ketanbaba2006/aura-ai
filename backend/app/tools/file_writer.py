"""
AURA AI File Writer Tool
Safe file writing and directory creation.
"""

import shutil
from pathlib import Path
from typing import Any
from datetime import datetime

from app.database.schemas import ToolResult
from app.tools.base import BaseTool
from app.memory.project_manager import get_workspace_root


class FileWriterTool(BaseTool):
    """Write files, create directories, and manage filesystem operations safely."""

    # Max file size to write (10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024

    # Allowed text extensions (same as FileReaderTool)
    TEXT_EXTENSIONS = {
        ".txt", ".md", ".py", ".js", ".ts", ".tsx", ".jsx",
        ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
        ".html", ".css", ".scss", ".sass", ".less",
        ".xml", ".csv", ".log", ".sh", ".bash", ".zsh",
        ".env", ".gitignore", ".sql", ".rs", ".go", ".java",
        ".cpp", ".c", ".h", ".hpp", ".rb", ".php", ".swift",
        ".kt", ".r", ".m", ".mm", ".pl", ".pm", ".lua",
        ".vim", ".vimrc", ".fish", ".ps1", ".bat", ".cmd",
        ".dockerfile", ".makefile", ".cmake", ".gradle",
        ".properties", ".conf", ".cfg", ".htaccess",
        ".tsv", ".json5", ".jsonc", ".graphql", ".gql",
        ".proto", ".thrift", ".avsc", ".avdl", ".avpr",
        ".html", ".htm", ".xhtml", ".xml", ".xsl", ".xslt",
        ".svg", ".webmanifest", ".jsonld", ".yaml", ".yml"
    }

    @property
    def name(self) -> str:
        return "file_writer"

    @property
    def description(self) -> str:
        return (
            "Write files, create directories, copy, move, or delete files and directories. "
            "All operations are sandboxed to the workspace directory."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["write", "append", "mkdir", "copy", "move", "delete"],
                    "description": "Operation to perform: 'write' (default), 'append', 'mkdir', 'copy', 'move', 'delete'",
                },
                "path": {
                    "type": "string",
                    "description": "Path to the file or directory (for write, append, mkdir, delete)",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write or append (for write and append operations)",
                },
                "source_path": {
                    "type": "string",
                    "description": "Source path for copy and move operations",
                },
                "destination_path": {
                    "type": "string",
                    "description": "Destination path for copy and move operations",
                },
                "overwrite": {
                    "type": "boolean",
                    "description": "Whether to overwrite existing files (default: false)",
                },
                "parents": {
                    "type": "boolean",
                    "description": "For mkdir: whether to create parent directories (default: true)",
                },
            },
            "required": ["operation"],
        }

    @property
    def permission_level(self) -> str:
        return "restricted"

    def _sanitize_path(self, path: str) -> Path:
        """Ensure path is within workspace directory."""
        workspace_root = get_workspace_root()
        target_path = Path(path).resolve()
        
        # Check if path is within workspace
        try:
            target_path.relative_to(workspace_root)
        except ValueError:
            # If not, try to make it relative to workspace
            target_path = (workspace_root / path).resolve()
            try:
                target_path.relative_to(workspace_root)
            except ValueError:
                raise PermissionError(f"Access to path '{path}' is denied. Path must be within workspace: {workspace_root}")
        
        return target_path

    def _format_file_size(self, size: int) -> str:
        """Format file size in human-readable format."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    async def execute(self, **kwargs: Any) -> ToolResult:
        operation = kwargs.get("operation", "write")
        path = kwargs.get("path", "")
        content = kwargs.get("content", "")
        source_path = kwargs.get("source_path", "")
        destination_path = kwargs.get("destination_path", "")
        overwrite = kwargs.get("overwrite", False)
        parents = kwargs.get("parents", True)

        try:
            if operation in ["write", "append", "mkdir", "delete"]:
                if not path:
                    return ToolResult(success=False, error="No path provided")
                target_path = self._sanitize_path(path)
            
            if operation in ["copy", "move"]:
                if not source_path or not destination_path:
                    return ToolResult(success=False, error="Source and destination paths are required")
                src_path = self._sanitize_path(source_path)
                dst_path = self._sanitize_path(destination_path)

            if operation == "write":
                # Validate file extension
                if target_path.suffix.lower() not in self.TEXT_EXTENSIONS and target_path.suffix:
                    return ToolResult(
                        success=False,
                        error=f"Unsupported file type: {target_path.suffix}. Only text files allowed."
                    )
                
                # Check size
                content_bytes = content.encode("utf-8")
                if len(content_bytes) > self.MAX_FILE_SIZE:
                    return ToolResult(
                        success=False,
                        error=f"Content too large: {self._format_file_size(len(content_bytes))} (max {self._format_file_size(self.MAX_FILE_SIZE)})"
                    )
                
                # Check overwrite
                if target_path.exists() and not overwrite:
                    return ToolResult(success=False, error=f"File already exists: {path}. Set overwrite=true to replace.")
                
                # Create parent directories
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Write file
                target_path.write_text(content, encoding="utf-8")
                
                return ToolResult(
                    success=True,
                    output=f"✅ Successfully wrote file: {target_path.relative_to(get_workspace_root())} ({self._format_file_size(len(content_bytes))})"
                )

            elif operation == "append":
                # Validate file extension
                if target_path.suffix.lower() not in self.TEXT_EXTENSIONS and target_path.suffix:
                    return ToolResult(
                        success=False,
                        error=f"Unsupported file type: {target_path.suffix}. Only text files allowed."
                    )
                
                # Check size
                content_bytes = content.encode("utf-8")
                
                # Create parent directories
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Append file
                with open(target_path, "a", encoding="utf-8") as f:
                    f.write(content)
                
                return ToolResult(
                    success=True,
                    output=f"✅ Successfully appended to file: {target_path.relative_to(get_workspace_root())}"
                )

            elif operation == "mkdir":
                target_path.mkdir(parents=parents, exist_ok=overwrite)
                return ToolResult(
                    success=True,
                    output=f"✅ Successfully created directory: {target_path.relative_to(get_workspace_root())}"
                )

            elif operation == "copy":
                if not src_path.exists():
                    return ToolResult(success=False, error=f"Source not found: {source_path}")
                
                if dst_path.exists() and not overwrite:
                    return ToolResult(success=False, error=f"Destination already exists: {destination_path}. Set overwrite=true to replace.")
                
                # Create parent directories
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                
                if src_path.is_dir():
                    shutil.copytree(src_path, dst_path, dirs_exist_ok=overwrite)
                else:
                    shutil.copy2(src_path, dst_path)
                
                return ToolResult(
                    success=True,
                    output=f"✅ Successfully copied: {src_path.relative_to(get_workspace_root())} to {dst_path.relative_to(get_workspace_root())}"
                )

            elif operation == "move":
                if not src_path.exists():
                    return ToolResult(success=False, error=f"Source not found: {source_path}")
                
                if dst_path.exists() and not overwrite:
                    return ToolResult(success=False, error=f"Destination already exists: {destination_path}. Set overwrite=true to replace.")
                
                # Create parent directories
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                
                shutil.move(str(src_path), str(dst_path))
                
                return ToolResult(
                    success=True,
                    output=f"✅ Successfully moved: {src_path.relative_to(get_workspace_root())} to {dst_path.relative_to(get_workspace_root())}"
                )

            elif operation == "delete":
                if not target_path.exists():
                    return ToolResult(success=False, error=f"Path not found: {path}")
                
                if target_path.is_dir():
                    shutil.rmtree(target_path)
                else:
                    target_path.unlink()
                
                return ToolResult(
                    success=True,
                    output=f"✅ Successfully deleted: {target_path.relative_to(get_workspace_root())}"
                )

            else:
                return ToolResult(success=False, error=f"Unknown operation: {operation}")

        except PermissionError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            return ToolResult(success=False, error=f"Error during operation: {str(e)}")
