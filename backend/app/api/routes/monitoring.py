import logging
import secrets
from fastapi import APIRouter, HTTPException, Header, Query, Depends
from pydantic import BaseModel
from app.core.model_manager import model_manager
from app.config import settings
from app.core.auth_security import require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])

# In-memory store for active developer session tokens
ACTIVE_DEVELOPER_TOKENS: set[str] = set()

class AuthRequest(BaseModel):
    password: str

@router.post("/auth")
async def verify_developer_auth(
    body: AuthRequest,
    current_user: dict = require_role(["OWNER"])
):
    """Verify developer password for authenticated OWNER and return a temporary access token."""
    if body.password == settings.DEVELOPER_PASSWORD:
        token = secrets.token_hex(16)
        ACTIVE_DEVELOPER_TOKENS.add(token)
        logger.info(f"Developer session token generated for OWNER: {current_user.get('email')}")
        return {"status": "authenticated", "token": token}
    raise HTTPException(status_code=401, detail="Invalid developer password")

@router.get("/stats")
async def get_monitoring_stats(
    x_developer_token: str | None = Header(None, alias="X-Developer-Token"),
    token: str | None = Query(None),
    current_user: dict = require_role(["OWNER"])
):
    """Get live LLM provider performance and failover stats."""
    active_token = x_developer_token or token
    if not active_token or active_token not in ACTIVE_DEVELOPER_TOKENS:
        raise HTTPException(status_code=401, detail="Unauthorized developer access: Session token invalid or expired")
    return model_manager.get_stats()
