"""
AURA AI Files Router
Provides endpoints to list project directory structure and read files safely, with access levels sandbox.
"""

import os
from pathlib import Path
import logging
from fastapi import APIRouter, HTTPException, Query, Header
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["Files"])

# Directories to exclude from listing
EXCLUDE_DIRS = {
    ".git",
    "node_modules",
    "venv",
    "__pycache__",
    ".next",
    ".gemini",
    ".idea",
    ".vscode",
    "build",
    "dist"
}

# Safe text extensions allowed for reading
TEXT_EXTENSIONS = {
    ".txt", ".md", ".py", ".js", ".ts", ".tsx", ".jsx",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".html", ".css", ".scss", ".xml", ".csv", ".log",
    ".sh", ".bash", ".zsh", ".env", ".gitignore",
    ".sql", ".rs", ".go", ".java", ".cpp", ".c", ".h",
    ".rb", ".php", ".swift", ".kt", ".r", ".m",
}

def get_project_root() -> Path:
    # Resolves to workspace folder /Users/ketanbaba/Desktop/Extra/AURA AI [ Autonomous Universal Reasoning Agent ]
    return Path(__file__).resolve().parent.parent.parent.parent.parent

@router.get("")
async def list_files(
    x_developer_token: str | None = Header(None, alias="X-Developer-Token"),
    token: str | None = Query(None)
):
    """Recursively list files in the project workspace or user files sandbox."""
    root_path = get_project_root()
    active_token = x_developer_token or token
    is_developer = (active_token == "developer_authorized_token")
    
    # Select path based on developer mode status
    scan_root = root_path if is_developer else (root_path / "user_files")
    scan_root.mkdir(parents=True, exist_ok=True)
    
    def walk_dir(path: Path) -> dict:
        node = {
            "name": path.name or str(path),
            "path": str(path.relative_to(scan_root if not is_developer else root_path)),
            "type": "directory" if path.is_dir() else "file",
        }
        if path.is_file():
            node["size"] = path.stat().st_size
        else:
            children = []
            try:
                for child in sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                    if child.name in EXCLUDE_DIRS:
                        continue
                    children.append(walk_dir(child))
            except PermissionError:
                pass
            except Exception as e:
                logger.error(f"Error reading path {path}: {e}")
            node["children"] = children
        return node

    try:
        tree = walk_dir(scan_root)
        if not is_developer:
            tree["name"] = "User Files"
        return tree
    except Exception as e:
        logger.error(f"Failed to list files: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/read")
async def read_file(
    path: str = Query(..., description="Relative path"),
    x_developer_token: str | None = Header(None, alias="X-Developer-Token"),
    token: str | None = Query(None)
):
    """Read a specific file's content in the workspace safely."""
    root_path = get_project_root()
    active_token = x_developer_token or token
    is_developer = (active_token == "developer_authorized_token")
    
    base_dir = root_path if is_developer else (root_path / "user_files")
    target_path = (base_dir / path).resolve()
    
    # Sandbox boundary check
    if not str(target_path).startswith(str(base_dir)):
        raise HTTPException(status_code=403, detail="Access denied: target path is outside allowed sandbox")
        
    if not target_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
        
    if not target_path.is_file():
        raise HTTPException(status_code=400, detail="Requested path is not a file")
        
    # Extension check
    suffix = target_path.suffix.lower()
    if suffix not in TEXT_EXTENSIONS and target_path.name not in (".env", ".gitignore", "Dockerfile"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {suffix or 'none'}. Only text files are viewable."
        )
        
    # Limit max read size (e.g. 500KB)
    if target_path.stat().st_size > 512_000:
        raise HTTPException(status_code=400, detail="File too large to display (limit 500KB)")
        
    try:
        content = target_path.read_text(encoding="utf-8", errors="replace")
        return {
            "name": target_path.name,
            "path": path,
            "content": content,
            "size": target_path.stat().st_size,
            "extension": suffix
        }
    except Exception as e:
        logger.error(f"Failed to read file {path}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to read file contents: {str(e)}")


class WriteFileRequest(BaseModel):
    path: str
    content: str


@router.post("/write")
async def write_file(
    body: WriteFileRequest,
    x_developer_token: str | None = Header(None, alias="X-Developer-Token"),
    token: str | None = Query(None)
):
    """Write content to a specific file in the workspace securely."""
    root_path = get_project_root()
    active_token = x_developer_token or token
    is_developer = (active_token == "developer_authorized_token")
    
    base_dir = root_path if is_developer else (root_path / "user_files")
    target_path = (base_dir / body.path).resolve()
    
    # Sandbox boundary check
    if not str(target_path).startswith(str(base_dir)):
        raise HTTPException(status_code=403, detail="Access denied: target path is outside allowed sandbox")
        
    # Extension check
    suffix = target_path.suffix.lower()
    if suffix not in TEXT_EXTENSIONS and target_path.name not in (".env", ".gitignore", "Dockerfile"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {suffix or 'none'}. Only text files are writable."
        )
        
    try:
        # Create parent directories if they don't exist
        target_path.parent.mkdir(parents=True, exist_ok=True)
        # Write file content
        target_path.write_text(body.content, encoding="utf-8")
        return {
            "success": True,
            "path": body.path,
            "size": target_path.stat().st_size
        }
    except Exception as e:
        logger.error(f"Failed to write file {body.path}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to write file contents: {str(e)}")

