"""
AURA AI File Reader Tool
Safe file reading with sandboxing and directory operations.
"""

import os
import fnmatch
from pathlib import Path
from typing import Any, Optional
from datetime import datetime

from app.database.schemas import ToolResult
from app.tools.base import BaseTool
from app.memory.project_manager import get_workspace_root


class FileReaderTool(BaseTool):
    """Read file contents with sandboxing to workspace directory."""

    # Max file size to read (5MB)
    MAX_FILE_SIZE = 5 * 1024 * 1024

    # Allowed text extensions
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
        return "file_reader"

    @property
    def description(self) -> str:
        return (
            "Read the contents of a text file or list directory contents. "
            "Supports reading entire files or specific line ranges. Also supports "
            "directory listing and file searching within the workspace. "
            "All paths are sandboxed to the workspace directory."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file or directory (relative to workspace or absolute)",
                },
                "max_lines": {
                    "type": "integer",
                    "description": "Maximum number of lines to read (for files only, default: all)",
                },
                "start_line": {
                    "type": "integer",
                    "description": "Start line number (1-indexed, for files only)",
                },
                "operation": {
                    "type": "string",
                    "enum": ["read", "list", "stat"],
                    "description": "Operation to perform: 'read' (default) for file content, 'list' for directory listing, 'stat' for file/directory info",
                },
                "recursive": {
                    "type": "boolean",
                    "description": "For 'list' operation: whether to list recursively (default: false)",
                },
                "pattern": {
                    "type": "string",
                    "description": "For 'list' operation: glob pattern to filter files (e.g., '*.py')",
                },
            },
            "required": ["path"],
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

    def _list_directory(self, path: Path, recursive: bool = False, pattern: Optional[str] = None) -> list[dict]:
        """List directory contents."""
        items = []
        
        try:
            if recursive:
                iterator = path.rglob("*")
            else:
                iterator = path.iterdir()
            
            for item in sorted(iterator, key=lambda x: (not x.is_dir(), x.name)):
                if pattern and not fnmatch.fnmatch(item.name, pattern):
                    continue
                
                stat = item.stat()
                items.append({
                    "name": item.name,
                    "path": str(item.relative_to(get_workspace_root())),
                    "type": "directory" if item.is_dir() else "file",
                    "size": stat.st_size,
                    "size_human": self._format_file_size(stat.st_size),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "permissions": oct(stat.st_mode & 0o777),
                })
        except Exception as e:
            raise RuntimeError(f"Failed to list directory: {str(e)}")
        
        return items

    def _get_stat(self, path: Path) -> dict:
        """Get file/directory statistics."""
        stat = path.stat()
        return {
            "path": str(path.relative_to(get_workspace_root())),
            "type": "directory" if path.is_dir() else "file",
            "exists": True,
            "size": stat.st_size,
            "size_human": self._format_file_size(stat.st_size),
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "accessed": datetime.fromtimestamp(stat.st_atime).isoformat(),
            "permissions": oct(stat.st_mode & 0o777),
            "is_file": path.is_file(),
            "is_dir": path.is_dir(),
            "is_symlink": path.is_symlink(),
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        path = kwargs.get("path", "")
        operation = kwargs.get("operation", "read")
        max_lines = kwargs.get("max_lines")
        start_line = kwargs.get("start_line", 1)
        recursive = kwargs.get("recursive", False)
        pattern = kwargs.get("pattern")

        if not path:
            return ToolResult(success=False, error="No path provided")

        try:
            target_path = self._sanitize_path(path)
            
            if operation == "stat":
                if not target_path.exists():
                    return ToolResult(
                        success=True,
                        output=f"📊 Stat Info:\n  Path: {target_path}\n  Exists: False"
                    )
                
                stat_info = self._get_stat(target_path)
                output = [f"📊 Stat Info for '{stat_info['path']}':"]
                output.append(f"  Type: {stat_info['type']}")
                output.append(f"  Size: {stat_info['size_human']} ({stat_info['size']} bytes)")
                output.append(f"  Created: {stat_info['created']}")
                output.append(f"  Modified: {stat_info['modified']}")
                output.append(f"  Accessed: {stat_info['accessed']}")
                output.append(f"  Permissions: {stat_info['permissions']}")
                
                return ToolResult(success=True, output="\n".join(output))
            
            if operation == "list":
                if not target_path.exists():
                    return ToolResult(success=False, error=f"Directory not found: {path}")
                
                if not target_path.is_dir():
                    return ToolResult(success=False, error=f"Path is not a directory: {path}")
                
                items = self._list_directory(target_path, recursive, pattern)
                
                output = [f"📁 Directory Listing for '{target_path.relative_to(get_workspace_root())}':"]
                output.append(f"  Total items: {len(items)}")
                output.append("")
                
                for item in items:
                    prefix = "📁" if item["type"] == "directory" else "📄"
                    output.append(f"{prefix} {item['name']} ({item['size_human']})")
                
                return ToolResult(success=True, output="\n".join(output))
            
            # Operation: read
            if not target_path.exists():
                return ToolResult(success=False, error=f"File not found: {path}")
            
            if not target_path.is_file():
                return ToolResult(success=False, error=f"Path is not a file: {path}")
            
            # Check extension
            if target_path.suffix.lower() not in self.TEXT_EXTENSIONS and target_path.suffix:
                return ToolResult(
                    success=False,
                    error=f"Unsupported file type: {target_path.suffix}. Only text files allowed."
                )
            
            # Check size
            file_size = target_path.stat().st_size
            if file_size > self.MAX_FILE_SIZE:
                return ToolResult(
                    success=False,
                    error=f"File too large: {self._format_file_size(file_size)} (max {self._format_file_size(self.MAX_FILE_SIZE)})"
                )
            
            # Read file
            content = target_path.read_text(encoding="utf-8", errors="replace")
            lines = content.splitlines()
            total_lines = len(lines)
            
            # Apply line range
            start_idx = max(0, start_line - 1)
            end_idx = None
            if max_lines:
                end_idx = start_idx + max_lines
            
            truncated_lines = lines[start_idx:end_idx]
            truncated_content = "\n".join(truncated_lines)
            truncated = len(truncated_lines) < total_lines or start_line > 1
            
            # Build output
            stat = target_path.stat()
            output = [
                f"📄 File: {target_path.relative_to(get_workspace_root())}",
                f"📏 Size: {self._format_file_size(file_size)} ({file_size} bytes)",
                f"📝 Lines: {len(truncated_lines)} of {total_lines}",
                f"🕐 Modified: {datetime.fromtimestamp(stat.st_mtime).isoformat()}",
            ]
            
            if truncated:
                range_str = f"Lines {start_line}-{start_line + len(truncated_lines) - 1}"
                output.append(f"⚠️  Showing {range_str}")
            
            output.append("")
            output.append("-" * 60)
            output.append(truncated_content)
            output.append("-" * 60)
            
            return ToolResult(success=True, output="\n".join(output))

        except PermissionError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            return ToolResult(success=False, error=f"Error accessing file: {str(e)}")
