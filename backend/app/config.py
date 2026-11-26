"""
AURA AI Configuration
Central settings for the application.
"""

from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "AURA AI"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # Auth & Security Settings
    JWT_SECRET_KEY: str = "INSECURE_DEFAULT_JWT_ACCESS_KEY"
    JWT_REFRESH_SECRET_KEY: str = "INSECURE_DEFAULT_JWT_REFRESH_KEY"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # OAuth Credentials (Google & GitHub)
    GOOGLE_CLIENT_ID: str = "aura-mock-google-client-id"
    GOOGLE_CLIENT_SECRET: str = "aura-mock-google-client-secret"
    GITHUB_CLIENT_ID: str = "aura-mock-github-client-id"
    GITHUB_CLIENT_SECRET: str = "aura-mock-github-client-secret"



    # Cloud Providers
    GROQ_API_KEY: str = "INSECURE_DEFAULT_GROQ_KEY"
    GEMINI_API_KEY: str = "INSECURE_DEFAULT_GEMINI_KEY"
    OPENROUTER_API_KEY: str = "INSECURE_DEFAULT_OPENROUTER_KEY"

    # Deep Research Provider (Completely isolated from Chat/Agent providers)
    RESEARCH_PROVIDER: str = "bedrock"
    RESEARCH_API_KEY: str = "INSECURE_DEFAULT_RESEARCH_KEY"
    RESEARCH_MODEL: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    RESEARCH_AWS_REGION: str = "us-east-1"
    RESEARCH_TEMPERATURE: float = 0.3
    RESEARCH_DEPTH: str = "standard"
    RESEARCH_SOURCES_LIMIT: int = 8
    RESEARCH_TIMEOUT: int = 300

    # Database (PostgreSQL)
    DATABASE_URL: str | None = None
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "aura"
    POSTGRES_PASSWORD: str = "aura_password"
    POSTGRES_DB: str = "aura_ai"

    # SMTP / Email verification
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM_EMAIL: str = "noreply@auraainet.xyz"
    SMTP_FROM_NAME: str = "AURA AI"

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ]

    # Memory
    MAX_CONVERSATION_HISTORY: int = 50
    SHORT_TERM_MEMORY_SIZE: int = 20

    # Autonomous agent
    AUTONOMOUS_MAX_REPAIR_ATTEMPTS: int = 2
    AUTONOMOUS_COMMAND_TIMEOUT: float = 90.0

    # Search
    SEARCH_MAX_RESULTS: int = 3
    SEARCH_CACHE_TTL: int = 3600       # seconds
    SEARCH_RATE_LIMIT: int = 3         # searches per minute
    SEARCH_PAGE_TIMEOUT: int = 10      # seconds per page
    SEARCH_MAX_CONTENT_LENGTH: int = 3000  # chars per page
    SEARCH_HEADLESS: bool = True

    DEVELOPER_PASSWORD: str = "INSECURE_DEFAULT_DEV_PASSWORD"

    # ─── BYOK (Bring Your Own Key) ────────────────────────────
    # Master key used to encrypt user-supplied gateway credentials at rest.
    # Leave empty to auto-generate a key file next to the backend (0600).
    BYOK_ENCRYPTION_KEY: str = ""
    BYOK_KEY_FILE: str = str(Path(__file__).parent.parent / ".byok_master.key")
    # SSRF: private / loopback / link-local targets are blocked unless an
    # operator explicitly opts in (needed for self-hosted gateways on a LAN).
    BYOK_ALLOW_PRIVATE_NETWORKS: bool = False
    BYOK_REQUIRE_HTTPS: bool = False
    BYOK_CONNECT_TIMEOUT: float = 10.0
    BYOK_REQUEST_TIMEOUT: float = 60.0
    BYOK_STREAM_TIMEOUT: float = 300.0
    BYOK_MODEL_CACHE_TTL: int = 600          # seconds (spec: 5-15 minutes)
    BYOK_MAX_CONNECTIONS_PER_USER: int = 20
    BYOK_MAX_MODELS: int = 2000
    BYOK_MAX_RESPONSE_BYTES: int = 8 * 1024 * 1024
    BYOK_MAX_REDIRECTS: int = 3

    # ─── Identity Configuration ──────────────────────────────
    APP_CREATOR: str = "Ketanbaba"
    APP_DOMAIN: str = "auraainet.xyz"
    APP_DESCRIPTION: str = "An intelligent personal AI assistant for conversations, research, programming, document analysis, problem-solving, productivity and intelligent task execution."
    APP_PURPOSE: str = "Provide users with a powerful, fast, reliable, personalized and intelligent AI experience."
    SUPPORTED_LANGUAGES: list[str] = ["English", "Hindi", "Marathi", "Hinglish"]
    AVAILABLE_CAPABILITIES: list[str] = [
        "chat", "reasoning", "coding", "research", "file_analysis",
        "web_search", "document_generation", "image_understanding",
        "voice_conversation", "agent_workflows", "memory", "tools"
    ]
    SUPPORTED_PROVIDERS: list[str] = ["gemini", "groq", "openrouter", "bedrock", "openai", "anthropic", "perplexity"]

    model_config = {"env_prefix": "AURA_", "env_file": ".env", "extra": "ignore"}

    def validate_production_secrets(self) -> list[str]:
        """Validate that production secrets are properly configured. Returns list of issues."""
        issues = []
        if self.DEBUG:
            return issues  # Skip in development
        if self.JWT_SECRET_KEY == "INSECURE_DEFAULT_JWT_ACCESS_KEY":
            issues.append("JWT_SECRET_KEY is using insecure default")
        if self.JWT_REFRESH_SECRET_KEY == "INSECURE_DEFAULT_JWT_REFRESH_KEY":
            issues.append("JWT_REFRESH_SECRET_KEY is using insecure default")
        if self.GROQ_API_KEY == "INSECURE_DEFAULT_GROQ_KEY":
            issues.append("GROQ_API_KEY is not configured")
        if self.GEMINI_API_KEY == "INSECURE_DEFAULT_GEMINI_KEY":
            issues.append("GEMINI_API_KEY is not configured")
        if self.OPENROUTER_API_KEY == "INSECURE_DEFAULT_OPENROUTER_KEY":
            issues.append("OPENROUTER_API_KEY is not configured")
        if self.GOOGLE_CLIENT_ID == "aura-mock-google-client-id":
            issues.append("GOOGLE_CLIENT_ID is using mock value")
        if self.GITHUB_CLIENT_ID == "aura-mock-github-client-id":
            issues.append("GITHUB_CLIENT_ID is using mock value")
        if not self.BYOK_ENCRYPTION_KEY:
            issues.append("BYOK_ENCRYPTION_KEY is not set (required for production)")
        return issues


settings = Settings()
