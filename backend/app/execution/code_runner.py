"""
AURA AI Code Runner
Safe local code execution sandbox for Python and JavaScript, supporting auto-correction.
"""

import os
import uuid
import logging
import asyncio
from pathlib import Path

from app.config import settings
from app.core.llm_client import llm_client

logger = logging.getLogger(__name__)

# System prompt for the code self-correction agent
SELF_CORRECTION_PROMPT = """You are AURA's Code Debugger.
You receive a piece of code (Python or JavaScript) that was executed and failed, along with the stdout and stderr output.
Analyze the crash, locate the bug, and write the corrected code.

Return ONLY the code blocks. Do not explain anything. Your output must be purely the corrected python or javascript source code, enclosed in ```python or ```javascript code blocks. No other text."""


class CodeRunner:
    """Manages sandboxed execution of code snippets in subprocesses with retry repair capability."""

    def __init__(self):
        # Work inside backend/execution_sandbox/
        self.sandbox_dir = Path(settings.DATABASE_PATH).parent / "execution_sandbox"
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)

        # Write .gitignore inside sandbox to prevent committing scratch code
        gitignore = self.sandbox_dir / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text("*\n")

    async def execute_code(
        self, lang: str, code: str, timeout: float = 10.0
    ) -> dict:
        """
        Execute code locally inside the workspace sandbox directory.
        Returns a dict containing: success (bool), output (str), error (str), return_code (int).
        """
        lang = lang.lower()
        supported_languages = [
            "python", "py", "javascript", "js", "node", "typescript", "ts",
            "cpp", "c++", "c", "java", "go", "golang", "rust", "rs", "bash", "sh", "zsh"
        ]
        if lang not in supported_languages:
            return {
                "success": False,
                "output": "",
                "error": f"Unsupported language '{lang}'. Supported: {', '.join(supported_languages)}",
                "return_code": -1,
            }

        file_uuid = str(uuid.uuid4()).replace("-", "")
        run_cmd = ""
        sandbox_sub = None
        
        if lang in ["python", "py"]:
            file_name = f"script_{file_uuid}.py"
            file_path = self.sandbox_dir / file_name
            run_cmd = f"python3 {file_path}"
        elif lang in ["javascript", "js", "node"]:
            file_name = f"script_{file_uuid}.js"
            file_path = self.sandbox_dir / file_name
            run_cmd = f"node {file_path}"
        elif lang in ["typescript", "ts"]:
            file_name = f"script_{file_uuid}.ts"
            file_path = self.sandbox_dir / file_name
            # Use tsx if available, otherwise ts-node
            run_cmd = f"npx tsx {file_path} || npx ts-node {file_path}"
        elif lang in ["cpp", "c++", "c"]:
            file_name = f"script_{file_uuid}.cpp"
            file_path = self.sandbox_dir / file_name
            out_path = self.sandbox_dir / f"out_{file_uuid}"
            run_cmd = f"g++ {file_path} -o {out_path} && {out_path}"
        elif lang == "java":
            # Java needs class name to match file name, usually Main
            import re
            match = re.search(r'public\s+class\s+(\w+)', code)
            class_name = match.group(1) if match else "Main"
            file_name = f"{class_name}.java"
            
            # Since multiple java executions might clash if they all use Main.java in the same dir,
            # we should create a subfolder for this execution.
            sandbox_sub = self.sandbox_dir / file_uuid
            sandbox_sub.mkdir(exist_ok=True)
            file_path = sandbox_sub / file_name
            run_cmd = f"cd {sandbox_sub} && javac {file_name} && java {class_name}"
        elif lang in ["go", "golang"]:
            file_name = f"script_{file_uuid}.go"
            file_path = self.sandbox_dir / file_name
            # Create a temporary go module
            run_cmd = f"go run {file_path}"
        elif lang in ["rust", "rs"]:
            file_name = f"script_{file_uuid}.rs"
            file_path = self.sandbox_dir / file_name
            out_path = self.sandbox_dir / f"out_{file_uuid}"
            run_cmd = f"rustc {file_path} -o {out_path} && {out_path}"
        elif lang in ["bash", "sh", "zsh"]:
            file_name = f"script_{file_uuid}.sh"
            file_path = self.sandbox_dir / file_name
            run_cmd = f"bash {file_path}"
        else:
            file_name = f"script_{file_uuid}.txt"
            file_path = self.sandbox_dir / file_name

        # 2. Write code to sandbox path
        try:
            file_path.write_text(code, encoding="utf-8")
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": f"Failed to write sandbox file: {e}",
                "return_code": -1,
            }

        # 3. Spawn asynchronous subprocess
        process = None
        try:
            process = await asyncio.create_subprocess_shell(
                run_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Wait for execution with timeout
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
            return_code = process.returncode

            stdout_str = stdout.decode("utf-8", errors="ignore")
            stderr_str = stderr.decode("utf-8", errors="ignore")

            # Limit output sizes to avoid RAM spikes
            max_out_len = 5000
            if len(stdout_str) > max_out_len:
                stdout_str = stdout_str[:max_out_len] + "\n... [Output truncated by AURA]"
            if len(stderr_str) > max_out_len:
                stderr_str = stderr_str[:max_out_len] + "\n... [Error truncated by AURA]"

            success = (return_code == 0) and (not stderr_str.strip())
            
            return {
                "success": success,
                "output": stdout_str,
                "error": stderr_str,
                "return_code": return_code,
            }

        except asyncio.TimeoutError:
            # Handle execution hang
            if process:
                try:
                    process.terminate()
                    await process.wait()
                except Exception:
                    pass
            return {
                "success": False,
                "output": "",
                "error": f"Execution timed out after {timeout} seconds.",
                "return_code": -9,
            }
        except Exception as e:
            logger.error(f"Sandbox execution crashed: {e}")
            return {
                "success": False,
                "output": "",
                "error": f"Internal execution crash: {e}",
                "return_code": -2,
            }
        finally:
            # 4. Clean up file and subdirectories
            try:
                if file_path.exists():
                    os.remove(file_path)
                if lang in ["cpp", "c++", "c", "rust", "rs"]:
                    out_path = self.sandbox_dir / f"out_{file_uuid}"
                    if out_path.exists():
                        os.remove(out_path)
                if lang == "java" and sandbox_sub:
                    import shutil
                    if sandbox_sub.exists():
                        shutil.rmtree(sandbox_sub)
            except Exception as e:
                logger.warning(f"Could not clean up temporary sandbox files: {e}")

    async def execute_code_stream(
        self, lang: str, code: str, timeout: float = 10.0
    ):
        """
        Execute code locally and yield stdout/stderr line by line.
        """
        lang = lang.lower()
        supported_languages = [
            "python", "py", "javascript", "js", "node", "typescript", "ts",
            "cpp", "c++", "c", "java", "go", "golang", "rust", "rs", "bash", "sh", "zsh"
        ]
        if lang not in supported_languages:
            yield {"type": "error", "data": f"Unsupported language '{lang}'"}
            return

        file_uuid = str(uuid.uuid4()).replace("-", "")
        run_cmd = ""
        sandbox_sub = None
        
        if lang in ["python", "py"]:
            file_name = f"script_{file_uuid}.py"
            file_path = self.sandbox_dir / file_name
            # Unbuffered output for python
            run_cmd = f"python3 -u {file_path}"
        elif lang in ["javascript", "js", "node"]:
            file_name = f"script_{file_uuid}.js"
            file_path = self.sandbox_dir / file_name
            run_cmd = f"node {file_path}"
        elif lang in ["typescript", "ts"]:
            file_name = f"script_{file_uuid}.ts"
            file_path = self.sandbox_dir / file_name
            run_cmd = f"npx tsx {file_path} || npx ts-node {file_path}"
        elif lang in ["cpp", "c++", "c"]:
            file_name = f"script_{file_uuid}.cpp"
            file_path = self.sandbox_dir / file_name
            out_path = self.sandbox_dir / f"out_{file_uuid}"
            run_cmd = f"g++ {file_path} -o {out_path} && {out_path}"
        elif lang == "java":
            import re
            match = re.search(r'public\s+class\s+(\w+)', code)
            class_name = match.group(1) if match else "Main"
            file_name = f"{class_name}.java"
            sandbox_sub = self.sandbox_dir / file_uuid
            sandbox_sub.mkdir(exist_ok=True)
            file_path = sandbox_sub / file_name
            run_cmd = f"cd {sandbox_sub} && javac {file_name} && java {class_name}"
        elif lang in ["go", "golang"]:
            file_name = f"script_{file_uuid}.go"
            file_path = self.sandbox_dir / file_name
            run_cmd = f"go run {file_path}"
        elif lang in ["rust", "rs"]:
            file_name = f"script_{file_uuid}.rs"
            file_path = self.sandbox_dir / file_name
            out_path = self.sandbox_dir / f"out_{file_uuid}"
            run_cmd = f"rustc {file_path} -o {out_path} && {out_path}"
        elif lang in ["bash", "sh", "zsh"]:
            file_name = f"script_{file_uuid}.sh"
            file_path = self.sandbox_dir / file_name
            run_cmd = f"bash {file_path}"

        try:
            file_path.write_text(code, encoding="utf-8")
        except Exception as e:
            yield {"type": "error", "data": f"Failed to write sandbox file: {e}"}
            return

        process = None
        try:
            process = await asyncio.create_subprocess_shell(
                run_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            async def read_stream(stream, stream_type):
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    yield {"type": stream_type, "data": line.decode("utf-8", errors="ignore")}

            # Merge and yield stdout and stderr in real-time
            from asyncio import as_completed
            
            async def wrap_gen(stream, stream_type):
                async for chunk in read_stream(stream, stream_type):
                    yield chunk

            # A simpler way to yield from both streams as data arrives:
            import asyncio
            q = asyncio.Queue()

            async def pump(stream, stream_type):
                try:
                    while True:
                        line = await stream.readline()
                        if not line:
                            break
                        await q.put({"type": stream_type, "data": line.decode("utf-8", errors="ignore")})
                finally:
                    await q.put(None) # Signal completion

            t1 = asyncio.create_task(pump(process.stdout, "log"))
            t2 = asyncio.create_task(pump(process.stderr, "error"))
            
            finished_streams = 0
            
            # Wait for execution with timeout
            async def consume_queue():
                nonlocal finished_streams
                while finished_streams < 2:
                    try:
                        item = await asyncio.wait_for(q.get(), timeout=timeout)
                        if item is None:
                            finished_streams += 1
                        else:
                            yield item
                    except asyncio.TimeoutError:
                        yield {"type": "error", "data": f"\\n... Execution timed out after {timeout} seconds."}
                        if process:
                            try:
                                process.terminate()
                            except Exception:
                                pass
                        break

            async for item in consume_queue():
                yield item

            await process.wait()
            if process.returncode != 0:
                yield {"type": "error", "data": f"\\nProcess exited with code {process.returncode}"}

        except Exception as e:
            yield {"type": "error", "data": f"Internal execution crash: {e}"}
        finally:
            try:
                if file_path.exists():
                    os.remove(file_path)
                if lang in ["cpp", "c++", "c", "rust", "rs"]:
                    out_path = self.sandbox_dir / f"out_{file_uuid}"
                    if out_path.exists():
                        os.remove(out_path)
                if lang == "java" and sandbox_sub:
                    import shutil
                    if sandbox_sub.exists():
                        shutil.rmtree(sandbox_sub)
            except Exception:
                pass

    async def execute_with_retry(
        self, lang: str, code: str, retries: int = 1, timeout: float = 10.0
    ) -> dict:
        """
        Execute code. If it crashes, request LLM to debug and fix it, and retry.
        """
        result = await self.execute_code(lang, code, timeout)
        
        if result["success"] or retries <= 0:
            return result

        logger.warning(f"Initial run failed (code runner). Attempting LLM correction. Error: {result['error']}")

        # Compile debugging query for LLM
        prompt = f"""Language: {lang}
Code that failed:
```
{code}
```

Standard Output (stdout):
{result['output']}

Standard Error (stderr):
{result['error']}

Return only the corrected code block. Do not write explanation."""

        try:
            # Request LLM to fix the code
            corrected_resp = await llm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=SELF_CORRECTION_PROMPT,
            )

            # Extract code block from response
            cleaned_code = self._clean_llm_code_blocks(corrected_resp, lang)
            if cleaned_code and cleaned_code.strip() != code.strip():
                logger.info("Retrying with LLM corrected code...")
                # Re-run execution
                retry_result = await self.execute_code(lang, cleaned_code, timeout)
                # Attach code modification details
                retry_result["code_modified"] = True
                retry_result["original_code"] = code
                retry_result["corrected_code"] = cleaned_code
                return retry_result
        except Exception as e:
            logger.error(f"Code runner auto-correction repair loop failed: {e}")

        return result

    def _clean_llm_code_blocks(self, text: str, lang: str) -> str:
        """Parses output from LLM and strips markdown fence codes."""
        lines = text.split("\n")
        code_lines = []
        in_block = False
        
        for line in lines:
            if line.startswith("```"):
                in_block = not in_block
                continue
            if in_block or (not text.strip().startswith("```")):
                # Collect lines inside code blocks, or collect everything if LLM ignored instructions
                code_lines.append(line)

        # If we collected nothing, return the original text
        result = "\n".join(code_lines) if code_lines else text
        
        # If there are residual markdown fences at beginning/end, clean them
        result = result.replace(f"```python\n", "").replace(f"```javascript\n", "")
        result = result.replace("```py\n", "").replace("```js\n", "")
        result = result.replace("```\n", "").replace("```", "")
        return result.strip()


# Global instance
code_runner = CodeRunner()
