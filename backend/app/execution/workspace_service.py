import datetime
from typing import AsyncGenerator
from app.execution.llm_adapter import llm_service

class WorkspaceService:
    @staticmethod
    def get_templates() -> list[dict]:
        return [
            {
                "id": "neon-cyberpunk-game",
                "name": "Neon Asteroids 2084",
                "category": "Canvas Game",
                "description": "High-octane arcade space shooter with particle engines, screen shake, and neon lighting.",
                "files": {
                    "index.html": """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Neon Asteroids 2084</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div id="game-ui">
        <div class="hud">SCORE: <span id="score">0</span></div>
        <div class="hud">SHIELD: <span id="shield">100</span>%</div>
    </div>
    <canvas id="canvas"></canvas>
    <script src="app.js"></script>
</body>
</html>""",
                    "style.css": """* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #050508; overflow: hidden; font-family: monospace; }
#canvas { display: block; width: 100vw; height: 100vh; }
#game-ui { position: absolute; top: 16px; left: 16px; right: 16px; display: flex; justify-content: space-between; color: #39ff14; font-size: 18px; text-shadow: 0 0 10px #39ff14; }""",
                    "app.js": """const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
canvas.width = window.innerWidth;
canvas.height = window.innerHeight;
console.log('[GAME] Neon Asteroids 2084 initialized.');
ctx.fillStyle = '#050508';
ctx.fillRect(0, 0, canvas.width, canvas.height);
ctx.fillStyle = '#39ff14';
ctx.font = '24px monospace';
ctx.fillText('Press SPACE to Fire Thrusters', canvas.width / 2 - 180, canvas.height / 2);"""
                }
            },
            {
                "id": "saas-analytics-portal",
                "name": "AURA Cyber-SaaS Portal",
                "category": "Dashboard",
                "description": "Enterprise dark-mode telemetry dashboard with responsive layout and KPIs.",
                "files": {
                    "index.html": """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>AURA Cyber-SaaS Portal</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="app-layout">
        <aside class="nav-sidebar">
            <h2 class="logo">AURA OS</h2>
            <nav class="nav-links">
                <a href="#" class="active">Overview</a>
                <a href="#">Neural Logs</a>
                <a href="#">Security</a>
            </nav>
        </aside>
        <main class="content">
            <h1>Autonomous Intelligence Overview</h1>
            <div class="kpi-row">
                <div class="kpi-card">
                    <div class="label">NEURAL THROUGHPUT</div>
                    <div class="val">99.8%</div>
                </div>
                <div class="kpi-card">
                    <div class="label">AVG TTFT</div>
                    <div class="val">180ms</div>
                </div>
            </div>
        </main>
    </div>
    <script src="app.js"></script>
</body>
</html>""",
                    "style.css": """* { margin: 0; padding: 0; box-sizing: border-box; font-family: sans-serif; }
body { background: #080d11; color: #e2f1ec; height: 100vh; }
.app-layout { display: flex; height: 100vh; }
.nav-sidebar { width: 220px; background: #0e171d; border-right: 1px solid rgba(255,255,255,0.08); padding: 24px; }
.logo { color: #39ff14; font-size: 20px; margin-bottom: 24px; }
.nav-links a { display: block; color: #8fa39a; text-decoration: none; padding: 8px 12px; border-radius: 6px; margin-bottom: 4px; }
.nav-links a.active { background: rgba(57,255,20,0.1); color: #39ff14; }
.content { flex: 1; padding: 32px; overflow-y: auto; }
.kpi-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-top: 24px; }
.kpi-card { background: rgba(14,23,29,0.7); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 20px; }
.label { font-size: 11px; color: #8fa39a; margin-bottom: 8px; }
.val { font-size: 24px; font-weight: bold; color: #39ff14; }""",
                    "app.js": """console.log('[PORTAL] AURA Cyber-SaaS Portal Loaded Successfully.');"""
                }
            }
        ]

    async def stream_coding(
        self,
        prompt: str,
        agent_role: str = "Full-Stack Architect",
        provider: str = "auto",
        model: str = "auto",
        current_files: dict[str, str] = None,
        runtime_logs: list = None,
        custom_api_key: str | None = None,
        custom_base_url: str | None = None
    ) -> AsyncGenerator[tuple[str, dict], None]:
        yield ("status", {"stage": f"Initializing AI {agent_role}..."})

        system_prompt = f"""You are AURA {agent_role}, an expert full-stack engineer specialized in creating rich, responsive, modern web applications, canvas games, and tools.

STRICT FILE FORMAT RULES:
1. You MUST structure your entire code response using the strict file marker format:
<<<FILE:index.html>>>
... raw HTML content ...
<<<END_FILE>>>
<<<FILE:style.css>>>
... raw CSS content ...
<<<END_FILE>>>
<<<FILE:app.js>>>
... raw JavaScript content ...
<<<END_FILE>>>
2. DO NOT wrap the code inside <<<FILE:...>>> with markdown code fences (like ```html or ```js). Output pure raw file content directly between <<<FILE:name>>> and <<<END_FILE>>>.
3. Ensure the code is complete, functional, and self-contained with no missing dependencies or syntax errors.
"""

        user_content = []
        if current_files:
            user_content.append("CURRENT PROJECT FILES:\n")
            for fname, fcontent in current_files.items():
                user_content.append(f"<<<FILE:{fname}>>>\n{fcontent}\n<<<END_FILE>>>\n\n")

        if runtime_logs:
            user_content.append("ACTIVE RUNTIME CONSOLE LOGS & ERRORS:\n")
            for log_entry in runtime_logs:
                user_content.append(f"{log_entry}\n")
            user_content.append("\n")

        user_content.append(f"USER DIRECTIVE:\n{prompt}")
        full_user_prompt = "".join(user_content)

        yield ("status", {"stage": "Architecting multi-file application structure..."})

        async for event, data in llm_service.stream_chat(
            messages=[{"role": "user", "content": full_user_prompt}],
            system_prompt=system_prompt,
            requested_provider=provider,
            requested_model=model,
            custom_api_key=custom_api_key,
            custom_base_url=custom_base_url
        ):
            yield (event, data)

workspace_service = WorkspaceService()
