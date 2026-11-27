"""
AURA AI Auth Security & Cryptography Utilities
Handles password hashing, JWT generation, dependencies, rate limiting, and CSRF check.
"""

import jwt
import bcrypt
import time
import logging
from datetime import datetime, timedelta
from fastapi import Request, Header, HTTPException, Depends
from app.config import settings
from app.database.database import db

logger = logging.getLogger(__name__)

# In-memory stores for rate limiting and brute force protection
# Tracks failed logins: {email: [timestamp1, timestamp2, ...]}
FAILED_LOGIN_ATTEMPTS: dict[str, list[float]] = {}
# Tracks general rate limits: {ip_address: [timestamp1, ...]}
RATE_LIMIT_TRACKER: dict[str, list[float]] = {}

# CSRF Secret Token Helper
CSRF_SECRET_TOKEN = "aura_csrf_access_token_validation_2026"

# ─── Password Hashing ─────────────────────────────────────

def hash_password(password: str) -> str:
    """Hashes a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(password: str, hashed: str) -> bool:
    """Verifies a password against its bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception as e:
        logger.error(f"Password verification failed: {e}")
        return False

# ─── JWT Token Management ──────────────────────────────────

def create_access_token(user_id: str, role: str, name: str) -> str:
    """Generates a short-lived Access JWT Token."""
    payload = {
        "sub": user_id,
        "role": role,
        "name": name,
        "exp": datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": datetime.utcnow(),
        "type": "access"
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")

def create_refresh_token(user_id: str, jti: str) -> str:
    """Generates a long-lived Refresh JWT Token."""
    payload = {
        "sub": user_id,
        "jti": jti,
        "exp": datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        "iat": datetime.utcnow(),
        "type": "refresh"
    }
    return jwt.encode(payload, settings.JWT_REFRESH_SECRET_KEY, algorithm="HS256")

def decode_access_token(token: str) -> dict:
    """Decodes and validates an Access Token. Raises jwt.PyJWTError on invalid."""
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])

def decode_refresh_token(token: str) -> dict:
    """Decodes and validates a Refresh Token. Raises jwt.PyJWTError on invalid."""
    return jwt.decode(token, settings.JWT_REFRESH_SECRET_KEY, algorithms=["HS256"])

# ─── Security Dependencies & Guards ─────────────────────────

async def get_current_user(request: Request, authorization: str = Header(None)) -> dict:
    """
    FastAPI Dependency to retrieve the logged-in user.
    Extracts Bearer token from authorization header or cookie.
    """
    token = None
    
    # 1. Try to read from Authorization header
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    
    # 2. Try to read from cookie fallback (for WebSockets or specific GET streams)
    if not token:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Access token expired")
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid authentication token: {e}")

    # Fetch user from database
    user = await db.db.users.find_one({"id": user_id})
    if not user:
        # Fallback query directly against Neon PostgreSQL if SQLite cache is empty
        try:
            from app.database.database import _fallback_store
            user = await _fallback_store.users._pg_sync_load_user({"id": user_id})
        except Exception:
            user = None

    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.get("is_active", True):
        raise HTTPException(status_code=401, detail="User account is deactivated")

    user.pop("_id", None)
    return dict(user)

class RoleGuard:
    """Dependency checker to enforce role constraints (OWNER, ADMIN, USER)."""
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: dict = Depends(get_current_user)) -> dict:
        if current_user["role"] not in self.allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied: requires role in {self.allowed_roles}"
            )
        return current_user

def require_role(roles: list[str]):
    """Helper shortcut for role guard dependency."""
    return Depends(RoleGuard(roles))

# ─── Brute Force & Rate Limit Protection ───────────────────

def enforce_brute_force(email: str):
    """Enforces login brute force lockout (5 failed attempts locks for 15 minutes)."""
    now = time.time()
    # Clean old attempts
    attempts = FAILED_LOGIN_ATTEMPTS.get(email, [])
    attempts = [t for t in attempts if now - t < 900] # 15 minutes window
    FAILED_LOGIN_ATTEMPTS[email] = attempts

    if len(attempts) >= 5:
        lock_remaining = int(900 - (now - attempts[0]))
        raise HTTPException(
            status_code=429,
            detail=f"Too many failed login attempts. Locked out for {lock_remaining // 60} minutes."
        )

def register_failed_login(email: str):
    """Logs a failed login attempt."""
    now = time.time()
    attempts = FAILED_LOGIN_ATTEMPTS.get(email, [])
    attempts.append(now)
    FAILED_LOGIN_ATTEMPTS[email] = attempts

def clear_failed_logins(email: str):
    """Clears failed login attempts for an email after successful login."""
    if email in FAILED_LOGIN_ATTEMPTS:
        del FAILED_LOGIN_ATTEMPTS[email]

def enforce_rate_limiting(request: Request):
    """Simple sliding-window rate limiter per client IP (max 100 requests per minute)."""
    client_ip = request.client.host if request.client else "unknown_ip"
    now = time.time()

    # Clean old attempts
    timestamps = RATE_LIMIT_TRACKER.get(client_ip, [])
    timestamps = [t for t in timestamps if now - t < 60] # 1 minute window
    RATE_LIMIT_TRACKER[client_ip] = timestamps

    if len(timestamps) >= 100:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please slow down (max 100 requests per minute)."
        )

    timestamps.append(now)
    RATE_LIMIT_TRACKER[client_ip] = timestamps

# ─── CSRF Protection Middleware Helper ─────────────────────

def verify_csrf_token(request: Request):
    """
    Validates CSRF Protection double-submit header for unsafe state-modifying requests.
    Checks x-csrf-token header against the csrf_token cookie.
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return

    csrf_header = request.headers.get("x-csrf-token")
    csrf_cookie = request.cookies.get("csrf_token")

    if not csrf_header or not csrf_cookie or csrf_header != csrf_cookie:
        raise HTTPException(status_code=403, detail="CSRF token validation failed")
