"""
AURA AI — Autonomous Universal Reasoning Agent
FastAPI Application Entry Point
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.llm_client import llm_client
from app.tools.tool_manager import tool_manager
from app.database.database import db
from app.memory.vector_store import vector_store
from app.search.search_manager import search_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown."""
    # ── Startup ──
    # ── Startup Security Validation & Hardening ──
    import secrets
    logger.info("=" * 60)
    logger.info("  AURA OS Production Security Hardening Checker")
    logger.info("=" * 60)
    
    # Validate production secrets
    production_issues = settings.validate_production_secrets()
    if production_issues:
        for issue in production_issues:
            logger.warning(f"🔒 SECURITY ADVISORY: {issue}")
        logger.info("Proceeding with startup: non-configured services will gracefully operate with active providers.")
    
    if not settings.BYOK_ENCRYPTION_KEY or settings.BYOK_ENCRYPTION_KEY == "INSECURE_DEFAULT_BYOK_KEY":
        logger.warning("🔒 SECURITY ADVISORY: BYOK_ENCRYPTION_KEY is unconfigured. Generating secure dynamic key.")
        settings.BYOK_ENCRYPTION_KEY = secrets.token_hex(32)

    if settings.JWT_SECRET_KEY == "INSECURE_DEFAULT_JWT_ACCESS_KEY" or settings.JWT_REFRESH_SECRET_KEY == "INSECURE_DEFAULT_JWT_REFRESH_KEY":
        logger.warning("🔒 SECURITY WARNING: JWT secrets are using insecure defaults or are unconfigured.")
        logger.warning("🔒 Action: Generating dynamic session keys for secure single-session fallback.")
        settings.JWT_SECRET_KEY = secrets.token_hex(32)
        settings.JWT_REFRESH_SECRET_KEY = secrets.token_hex(32)
    else:
        logger.info("🛡️ JWT Access and Refresh secrets verified (Custom configurations loaded).")

    if settings.DEVELOPER_PASSWORD == "INSECURE_DEFAULT_DEV_PASSWORD":
        logger.warning("🔒 SECURITY WARNING: AURA_DEVELOPER_PASSWORD is using insecure default placeholders.")
        logger.warning("🔒 Action: Falling back to local debug password 'aura_admin'.")
        settings.DEVELOPER_PASSWORD = "aura_admin"
    else:
        logger.info("🛡️ Developer Mode password verified.")

    providers = {
        "GROQ": settings.GROQ_API_KEY,
        "GEMINI": settings.GEMINI_API_KEY,
        "OPENROUTER": settings.OPENROUTER_API_KEY
    }
    for name, key in providers.items():
        if key == f"INSECURE_DEFAULT_{name}_KEY":
            logger.warning(f"🔒 API KEY WARNING: {name}_API_KEY is not configured in the environment.")
           
    logger.info("=" * 60)

    # Initialize sandboxed user workspace
    from pathlib import Path
    try:
        root_dir = Path(__file__).resolve().parent.parent.parent
        user_files_dir = root_dir / "user_files"
        subdirs = ["User Documents", "Uploaded Files", "Generated Reports", "Projects", "Notes"]
        for s in subdirs:
            (user_files_dir / s).mkdir(parents=True, exist_ok=True)
           
        welcome_file = user_files_dir / "User Documents" / "Welcome.md"
        if not welcome_file.exists():
            welcome_file.write_text("# Welcome to AURA OS\n\nThis is your secure, sandboxed workspace documents folder.", encoding="utf-8")
           
        notes_file = user_files_dir / "Notes" / "Scratchpad.md"
        if not notes_file.exists():
            notes_file.write_text("# Notes & Scratchpad\n\nWrite down your ideas and thoughts here.", encoding="utf-8")

        reports_file = user_files_dir / "Generated Reports" / "System Status.md"
        if not reports_file.exists():
            reports_file.write_text("# System Status Report\n\nAll systems are operating normally. Telemetry active under developer authorization.", encoding="utf-8")
           
        logger.info("Initializing User Sandbox Workspace complete")
    except Exception as e:
        logger.error(f"Failed to initialize user workspace directories: {e}")

    # Connect database
    try:
        await db.connect()
        logger.info("Database connected")
    except Exception as e:
        logger.warning(f"MongoDB connection skipped or unavailable: {e}. Running with PostgreSQL / Neon fallback.")

    # Initialize local vector store
    try:
        vector_store.initialize()
    except Exception as e:
        logger.error(f"Failed to initialize vector store: {e}")

    # Register tools
    tool_manager.register_defaults()
    tools = tool_manager.list_tools()
    logger.info(f"Registered {len(tools)} tools: {[t.name for t in tools]}")

    # Initialize AURA Global Quality Engine
    try:
        from app.quality.engine import agqe
        await agqe.initialize()
        logger.info("AURA Global Quality Engine initialized")
    except Exception as e:
        logger.warning(f"AGQE initialization failed: {e}")

    # Initialize search engine (Playwright browser)
    try:
        await search_manager.initialize()
        logger.info("Search engine initialized (Playwright + Chromium)")
    except Exception as e:
        logger.warning(f"Search engine failed to initialize: {e}")
        logger.warning("Web search will not be available until Playwright is installed")

    # Startup Cloud Provider Validation
    logger.info("Verifying cloud provider API connectivity...")
    from app.core.model_manager import model_manager, PROVIDERS_PRIORITY
    await model_manager.run_health_checks()
    
    for provider in PROVIDERS_PRIORITY:
        status = model_manager.stats["status"].get(provider)
        if status == "active":
            logger.info(f"Cloud Provider: {provider.upper()} -> CONNECTED (Healthy)")
        elif status == "unconfigured":
            logger.warning(f"Cloud Provider: {provider.upper()} -> SKIPPED (API Key missing)")
        else:
            logger.error(f"Cloud Provider: {provider.upper()} -> FAILED (Check API key or network)")

    # Deep Research Provider Health Check (Isolated)
    logger.info("Verifying Deep Research provider...")
    research_key = settings.RESEARCH_API_KEY
    if research_key and research_key != "INSECURE_DEFAULT_RESEARCH_KEY":
        logger.info(f"Deep Research Provider: {settings.RESEARCH_PROVIDER.upper()} -> CONFIGURED (Model: {settings.RESEARCH_MODEL})")
    else:
        logger.warning("Deep Research Provider: NOT CONFIGURED (Set AURA_RESEARCH_API_KEY in .env)")

    logger.info("AURA AI ready")

    yield

    # ── Shutdown ──
    await search_manager.shutdown()
    await db.disconnect()
    from app.quality.database import close_pg_pool
    await close_pg_pool()
    logger.info("AURA AI shut down")


# ── Create app ──
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Autonomous Universal Reasoning Agent — AI Operating System by Ketan Lade",
    lifespan=lifespan,
)

# ── CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://.*\.vercel\.app|https://.*auraainet\.xyz|http://localhost:.*|http://127\.0\.0\.1:.*",
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global unhandled error on {request.method} {request.url.path}: {exc}", exc_info=True)
    origin = request.headers.get("origin", "*")
    return JSONResponse(
        status_code=500,
        content={"success": False, "detail": str(exc) or "Internal server error"},
        headers={
            "Access-Control-Allow-Origin": origin if origin != "null" else "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

# ── Mount routers ──
from app.core.auth_security import get_current_user, require_role
from app.api.routes import chat, conversations, memory, tools, search, knowledge, logs, settings as settings_route, files, monitoring, auth, projects, research, execution, notebook, identity, quality, models as models_route, image as image_route, workspace_studio  # noqa: E402

# Unprotected Authentication Router (supports both /api/v1/auth and /api/auth)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api")

# Models and Image discovery (accessible publicly / optionally authenticated)
app.include_router(models_route.router, prefix="/api/v1")
app.include_router(models_route.router, prefix="/api")
app.include_router(image_route.router, prefix="/api/v1")
app.include_router(image_route.router, prefix="/api")

# Coding Studio & Workspace (accessible publicly or optionally authenticated with guest fallback)
app.include_router(workspace_studio.router, prefix="/api/v1")
app.include_router(workspace_studio.router, prefix="/api")

# Protected Workspace / Assistant Routers (supports both /api/v1 and /api)
app.include_router(chat.router, prefix="/api/v1", dependencies=[Depends(get_current_user)])
app.include_router(chat.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(conversations.router, prefix="/api/v1", dependencies=[Depends(get_current_user)])
app.include_router(conversations.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(conversations.router, prefix="/api/v1/chat", dependencies=[Depends(get_current_user)])
app.include_router(conversations.router, prefix="/api/chat", dependencies=[Depends(get_current_user)])
app.include_router(memory.router, prefix="/api/v1", dependencies=[Depends(get_current_user)])
app.include_router(tools.router, prefix="/api/v1", dependencies=[Depends(get_current_user)])
app.include_router(search.router, prefix="/api/v1", dependencies=[Depends(get_current_user)])
app.include_router(knowledge.router, prefix="/api/v1", dependencies=[Depends(get_current_user)])

app.include_router(files.router, prefix="/api/v1", dependencies=[Depends(get_current_user)])
app.include_router(projects.router, prefix="/api/v1", dependencies=[Depends(get_current_user)])
app.include_router(quality.router, prefix="/api/v1", dependencies=[Depends(get_current_user)])
app.include_router(research.router, prefix="/api/v1", dependencies=[Depends(get_current_user)])
app.include_router(execution.router, prefix="/api/v1", dependencies=[Depends(get_current_user)])
app.include_router(notebook.router, prefix="/api/v1", dependencies=[Depends(get_current_user)])

# Identity Router (public - no auth required for basic info)
app.include_router(identity.router, prefix="/api/v1")
app.include_router(identity.router, prefix="/api")

# Settings & Models Routers (accessible publicly or optionally authenticated)
app.include_router(settings_route.router, prefix="/api/v1")
app.include_router(settings_route.router, prefix="/api")

# Protected OWNER-only System Routers
app.include_router(logs.router, prefix="/api/v1", dependencies=[require_role(["OWNER"])])
app.include_router(monitoring.router, prefix="/api/v1", dependencies=[require_role(["OWNER"])])



# ── Health check ──
@app.api_route("/", methods=["GET", "HEAD"], tags=["System"])
async def root_ping():
    return {"status": "UP", "message": "AURA AI API Online"}


@app.api_route("/health", methods=["GET", "HEAD"], tags=["System"])
@app.api_route("/healthz", methods=["GET", "HEAD"], tags=["System"])
@app.api_route("/api/v1/health", methods=["GET", "HEAD"], tags=["System"])
async def health_check():
    """Health check endpoint with dynamic LLM provider telemetry."""
    import time
    import asyncio
    from app.core.model_manager import model_manager, PROVIDERS_CONFIG, PROVIDERS_PRIORITY

    # Trigger background health pings if last run was > 60 seconds ago
    now = time.time()
    if now - model_manager.last_health_check_time > 60:
        model_manager.last_health_check_time = now
        asyncio.create_task(model_manager.run_health_checks())

    # Dynamic active provider telemetry
    active_provider = model_manager.active_provider
    config = PROVIDERS_CONFIG.get(active_provider, {})
    active_model = config.get("models", {}).get("chat", "unknown")
    
    # Latency for active provider
    latencies = model_manager.stats["latencies"].get(active_provider, [])
    latency = round(latencies[-1], 3) if latencies else 0.0
    
    # Quota Status check
    provider_status = model_manager.stats["status"].get(active_provider, "active")
    if provider_status == "active":
        quota_status = "Healthy / Active"
    elif provider_status == "unconfigured":
        quota_status = "Unconfigured"
    else:
        quota_status = "Degraded / Quota Exceeded"

    # Construct the failover chain display string
    chain_list = []
    for p in PROVIDERS_PRIORITY:
        p_status = model_manager.stats["status"].get(p, "active")
        if p_status == "active":
            color = "#34d399"  # green
        elif p_status == "unconfigured":
            color = "#94a3b8"  # slate / muted
        else:
            color = "#f87171"  # red
        chain_list.append(f"<span style='color:{color}; font-weight:600;'>{p.upper()}</span>")
        
    failover_chain = " &rarr; ".join(chain_list)

    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "active_provider": active_provider.upper(),
        "active_model": active_model,
        "latency": f"{latency:.3f}s" if latency > 0.0 else "N/A",
        "quota_status": quota_status,
        "failover_chain": failover_chain,
        "requests_today": model_manager.stats["requests_today"],
        "tools_loaded": len(tool_manager.list_tools()),
        "search_cache": search_manager.get_cache_stats()["active_cached"],
    }


@app.get("/", tags=["System"])
async def root():
    """Root endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/api/v1/health",
    }
