"""
AURA AI Code Runner Tool
Wrapper around sandbox execution engine.
"""

from typing import Any
import logging

from app.tools.base import BaseTool
from app.database.schemas import ToolResult
from app.execution.code_runner import code_runner

logger = logging.getLogger(__name__)


class CodeRunnerTool(BaseTool):
    """Executes scripts safely inside sandbox subprocesses."""

    @property
    def name(self) -> str:
        return "code_runner"

    @property
    def description(self) -> str:
        return (
            "Run Python, JavaScript, TypeScript, C++, Java, Go, Rust, or Bash scripts locally. "
            "Use this tool for running script files, complex computations, scripting filesystem jobs, "
            "or parsing output formats. Supports automatic debugging and self-correction repair on failure."
        )

    @property
    def permission_level(self) -> str:
        return "restricted"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "language": {
                    "type": "string",
                    "enum": [
                        "python", "javascript", "typescript", "cpp", "c++", "c", 
                        "java", "go", "golang", "rust", "rs", "bash", "sh", "zsh"
                    ],
                    "description": "Programming language of code snippet.",
                },
                "code": {
                    "type": "string",
                    "description": "Clean script source code to run.",
                },
                "retries": {
                    "type": "integer",
                    "description": "Auto-correct debug retry count. Set to 1 to allow LLM debugging fallback, or 0.",
                    "default": 1,
                },
                "timeout": {
                    "type": "number",
                    "description": "Execution timeout in seconds (default: 10).",
                    "default": 10,
                },
            },
            "required": ["language", "code"],
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        language = kwargs.get("language")
        code = kwargs.get("code")
        retries = kwargs.get("retries", 1)
        timeout = kwargs.get("timeout", 10)

        if not language or not code:
            return ToolResult(
                success=False, error="Missing required parameters: 'language' or 'code'."
            )

        try:
            res = await code_runner.execute_with_retry(
                lang=language, code=code, retries=retries, timeout=timeout
            )
            
            output = res["output"]
            error = res["error"]
            success = res["success"]
            
            # Formulate detailed outcome string
            outcome = []
            if success:
                outcome.append(f"Execution Succeeded.\nStandard Output:\n{output}")
            else:
                outcome.append(f"Execution Failed (Code {res['return_code']}).")
                if output.strip():
                    outcome.append(f"Standard Output:\n{output}")
                if error.strip():
                    outcome.append(f"Standard Error:\n{error}")
            
            if res.get("code_modified"):
                outcome.append("\n[AURA NOTE] Code failed initially and was corrected by AURA Debugger:")
                outcome.append(f"Original Code:\n{res['original_code']}\n")
                outcome.append(f"Corrected Code:\n{res['corrected_code']}")

            return ToolResult(
                success=success,
                output="\n".join(outcome),
                error=error if not success else None,
            )

        except Exception as e:
            logger.error(f"Code runner tool execution failed: {e}")
            return ToolResult(success=False, error=str(e))
