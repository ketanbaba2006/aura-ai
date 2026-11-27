"""
AURA AI Authentication & Session API
Endpoints for signup, login, refresh, logout, password recovery, session tracking, and OAuth.
"""

import uuid
import logging
import httpx
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, Response, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr, Field


from app.config import settings
from app.database.database import db
from app.core.auth_security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    get_current_user,
    enforce_brute_force,
    register_failed_login,
    clear_failed_logins,
    enforce_rate_limiting,
    CSRF_SECRET_TOKEN
)
from app.core.email import generate_verification_code, send_verification_email
from app.quality.database import (
    create_verification_code,
    verify_code,
    invalidate_verification_codes,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ─── Pydantic Request Schemas ──────────────────────────────

class SignupRequest(BaseModel):
    name: str | None = None
    username: str | None = None
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)

class LoginRequest(BaseModel):
    email: str | None = None
    username: str | None = None
    password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    password: str = Field(..., min_length=6, max_length=100)

class OAuthLoginRequest(BaseModel):
    provider: str  # 'google' or 'github'
    oauth_token: str
    email: EmailStr
    name: str
    avatar_url: str | None = None

# ─── Helper: Set Authentication Cookies ─────────────────────

def set_auth_cookies(response: Response, refresh_token: str, csrf_token: str):
    """Sets Refresh Token and CSRF Token cookies on the response payload."""
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        path="/",
        max_age=7 * 24 * 3600  # 7 days
    )
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,  # Frontend must be able to read this to attach to custom X-CSRF-Token headers
        secure=False,
        samesite="lax",
        path="/",
        max_age=7 * 24 * 3600
    )

# ─── Auth Endpoints ────────────────────────────────────────

@router.post("/signup")
@router.post("/register")
async def signup(body: SignupRequest, request: Request):
    """Registers a new user. Auto-assigns the first registered user as OWNER."""
    enforce_rate_limiting(request)
    email = body.email.strip().lower()
    user_name = (body.name or body.username or email.split("@")[0]).strip()

    # Check if user already exists
    existing = await db.db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists")

    # Hash user password
    pw_hash = hash_password(body.password)

    # First user rule: if no users in db, make OWNER, else USER
    count_row = {"count": await db.db.users.count_documents({})}
    role = "OWNER" if count_row and count_row["count"] == 0 else "USER"

    user_id = str(uuid.uuid4())
    avatar_url = f"https://api.dicebear.com/7.x/bottts/svg?seed={user_name}"

    try:
        await db.db.users.insert_one({
            "id": user_id,
            "name": user_name,
            "username": user_name,
            "email": email,
            "password_hash": pw_hash,
            "avatar_url": avatar_url,
            "provider": "local",
            "role": role,
            "is_active": True,
        })
    except Exception as e:
        logger.error(f"Failed to create user during signup: {e}")
        raise HTTPException(status_code=500, detail="Database write failed")

    # Generate 6-digit verification code and store in PostgreSQL
    code = generate_verification_code(6)
    try:
        await create_verification_code(email, code, code_type="email_verification", ttl_minutes=10)
    except Exception as e:
        logger.warning(f"Could not write verification code to Postgres: {e}")

    # Send the code via email (falls back to console log if no SMTP configured)
    email_sent = send_verification_email(email, code, code_type="email_verification")

    # Generate tokens immediately so the user can be logged in
    jti = str(uuid.uuid4())
    access_token = create_access_token(user_id, role, user_name)
    refresh_token = create_refresh_token(user_id, jti)

    return {
        "success": True,
        "message": "User registered successfully.",
        "accessToken": access_token,
        "refreshToken": refresh_token,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {
            "id": user_id,
            "name": user_name,
            "username": user_name,
            "email": email,
            "role": role,
            "avatar_url": avatar_url,
            "is_active": True,
        },
        "verification_code": code,
        "email_sent": email_sent,
    }

@router.post("/login")
async def login(body: LoginRequest, request: Request, response: Response):
    """Authenticates credentials and establishes session."""
    enforce_rate_limiting(request)
    identifier = (body.email or body.username or "").strip().lower()

    # Enforce lockout protection
    enforce_brute_force(identifier)

    # Allow login by email or username
    user = await db.db.users.find_one({"$or": [{"email": identifier}, {"username": identifier}]})
    if not user:
        user = await db.db.users.find_one({"email": identifier})

    if not user or not verify_password(body.password, user.get("password_hash", "")):
        register_failed_login(identifier)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Clear brute-force attempts
    clear_failed_logins(identifier)

    # Establish session
    user_id = user["id"]
    jti = str(uuid.uuid4())
    user_name = user.get("name") or user.get("username") or identifier
    user_role = user.get("role", "USER")
    user_email = user.get("email", identifier)

    access_token = create_access_token(user_id, user_role, user_name)
    refresh_token = create_refresh_token(user_id, jti)
    csrf_token = str(uuid.uuid4())

    # Get device/IP info
    device_info = request.headers.get("user-agent", "Unknown Device")
    ip_address = request.client.host if request.client else "Unknown IP"

    try:
        await db.db.user_sessions.insert_one({"id": str(uuid.uuid4()), "user_id": user_id, "token_jti": jti, "device_info": device_info, "ip_address": ip_address, "created_at": datetime.utcnow().isoformat(), "last_active": datetime.utcnow().isoformat()})
    except Exception:
        pass

    set_auth_cookies(response, refresh_token, csrf_token)

    return {
        "success": True,
        "accessToken": access_token,
        "refreshToken": refresh_token,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "csrf_token": csrf_token,
        "user": {
            "id": user_id,
            "name": user_name,
            "username": user_name,
            "email": user_email,
            "role": user_role
        }
    }

@router.post("/refresh")
async def refresh(request: Request, response: Response):
    """Re-issues access token using the HttpOnly refresh token cookie or JSON body."""
    # Accept token from HttpOnly cookie first, then fall back to JSON body
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        try:
            body = await request.json()
            refresh_token = body.get("refreshToken") or body.get("refresh_token")
        except Exception:
            pass
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token cookie missing")

    try:
        payload = decode_refresh_token(refresh_token)
        user_id = payload.get("sub")
        jti = payload.get("jti")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # Verify session active in database
    session = await db.db.user_sessions.find_one({"user_id": user_id, "token_jti": jti})
    if not session:
        raise HTTPException(status_code=401, detail="Session revoked or logged out")

    # Fetch user
    user = await db.db.users.find_one({"id": user_id})
    if not user or not user["is_active"]:
        raise HTTPException(status_code=401, detail="User account is deactivated or missing")

    # Issue new access token
    new_access_token = create_access_token(user_id, user["role"], user["name"])
    
    # Touch session last_active
    now = datetime.utcnow().isoformat()
    await db.db.user_sessions.update_one({"token_jti": jti}, {"$set": {"last_active": now}})

    return {
        "success": True,
        "accessToken": new_access_token,
        "access_token": new_access_token,
        "user": {
            "id": user_id,
            "name": user["name"],
            "email": user["email"],
            "role": user["role"]
        }
    }

@router.post("/logout")
async def logout(request: Request, response: Response):
    """Revokes current session and deletes auth cookies."""
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        try:
            payload = decode_refresh_token(refresh_token)
            user_id = payload.get("sub")
            jti = payload.get("jti")
            # Remove session from DB
            await db.db.user_sessions.delete_one({"user_id": user_id, "token_jti": jti})
        except Exception:
            pass

    response.delete_cookie("refresh_token", path="/")
    response.delete_cookie("csrf_token", path="/")

    return {"success": True, "message": "Logged out successfully"}

@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Returns profile information of currently authenticated user."""
    return {
        "success": True, 
        "user": {
            "id": current_user["id"],
            "name": current_user["name"],
            "email": current_user["email"],
            "role": current_user["role"],
            "avatar_url": current_user.get("avatar_url")
        }
    }

# ─── Password Recovery ─────────────────────────────────────

@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest, request: Request):
    """Generates password reset link (mocked to console output)."""
    enforce_rate_limiting(request)
    email = body.email.strip().lower()

    user = await db.db.users.find_one({"email": email, "provider": "local"})
    if not user:
        # Avoid user enumeration - return standard success message
        return {"success": True, "message": "If this email is registered, a password reset link has been generated."}

    # Generate reset token
    reset_token = str(uuid.uuid4())
    expires = datetime.utcnow() + timedelta(hours=1)
    await db.db.auth_tokens.insert_one({"id": str(uuid.uuid4()), "user_id": user["id"], "token": reset_token, "token_type": "password_reset", "expires_at": expires.isoformat()})

    logger.info(f"=== PASSWORD RESET TOKEN FOR {email} ===")
    logger.info(f"Reset Link: http://localhost:3000/reset-password?token={reset_token}")
    logger.info("=========================================")

    return {
        "success": True, 
        "message": "Password reset token generated.", 
        "reset_token": reset_token # Returned for development interface
    }

@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest, request: Request):
    """Resets user password and logs out all device sessions for safety."""
    enforce_rate_limiting(request)
    
    token_row = await db.db.auth_tokens.find_one({"token": body.token, "token_type": "password_reset"})

    if not token_row:
        raise HTTPException(status_code=400, detail="Invalid password reset token")

    # Expiry check
    expires = datetime.fromisoformat(token_row["expires_at"])
    if expires < datetime.utcnow():
        await db.db.auth_tokens.delete_one({"token": body.token})
        raise HTTPException(status_code=400, detail="Reset token expired")

    user_id = token_row["user_id"]
    new_hash = hash_password(body.password)

    # Update password and clear sessions
    await db.db.users.update_one({"id": user_id}, {"$set": {"password_hash": new_hash, "updated_at": datetime.utcnow().isoformat()}})
    await db.db.user_sessions.delete_many({"user_id": user_id})
    await db.db.auth_tokens.delete_one({"token": body.token})

    return {"success": True, "message": "Password reset successfully. Please log in again."}

@router.get("/verify-email")
async def verify_email(token: str = Query(...)):
    """Verifies account registration token."""
    token_row = await db.db.auth_tokens.find_one({"token": token, "token_type": "email_verification"})

    if not token_row:
        raise HTTPException(status_code=400, detail="Invalid verification token")

    expires = datetime.fromisoformat(token_row["expires_at"])
    if expires < datetime.utcnow():
        await db.db.auth_tokens.delete_one({"token": token})
        raise HTTPException(status_code=400, detail="Verification link expired")

    user_id = token_row["user_id"]
    await db.db.users.update_one({"id": user_id}, {"$set": {"is_active": True}})
    await db.db.auth_tokens.delete_one({"token": token})

    return {"success": True, "message": "Account verified successfully. You can now log in."}


# ─── Email Verification Code ─────────────────────────────────────

class VerifyCodeRequest(BaseModel):
    email: EmailStr
    code: str


class ResendCodeRequest(BaseModel):
    email: EmailStr


@router.post("/verify-code")
async def verify_code_endpoint(body: VerifyCodeRequest):
    """Verifies the 6-digit email verification code sent on signup."""
    email = body.email.strip().lower()
    code = body.code.strip()

    user = await db.db.users.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="No account found with this email")

    if user.get("is_active"):
        return {"success": True, "message": "Account is already verified."}

    valid = await verify_code(email, code, code_type="email_verification")
    if not valid:
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")

    await db.db.users.update_one({"id": user["id"]}, {"$set": {"is_active": True}})
    await invalidate_verification_codes(email, "email_verification")

    return {"success": True, "message": "Email verified successfully. You can now log in."}


@router.post("/resend-code")
async def resend_code_endpoint(body: ResendCodeRequest, request: Request):
    """Resends a verification code to the user's email."""
    enforce_rate_limiting(request)
    email = body.email.strip().lower()

    user = await db.db.users.find_one({"email": email})
    if not user:
        # Avoid user enumeration
        return {"success": True, "message": "If this email is registered, a new code has been sent."}

    if user.get("is_active"):
        return {"success": True, "message": "Account is already verified."}

    # Invalidate any existing unused codes
    await invalidate_verification_codes(email, "email_verification")

    # Generate and store a new code
    code = generate_verification_code(6)
    await create_verification_code(email, code, code_type="email_verification", ttl_minutes=10)

    # Send via email
    email_sent = send_verification_email(email, code, code_type="email_verification")

    return {
        "success": True,
        "message": "A new verification code has been sent to your email.",
        "verification_code": code,
        "email_sent": email_sent,
    }


# ─── Session Management ───────────────────────────────────

@router.get("/sessions")
async def get_sessions(request: Request, current_user: dict = Depends(get_current_user)):
    """Lists active login sessions (connected devices/devices) for current user."""
    # Find current session jti
    refresh_token = request.cookies.get("refresh_token")
    current_jti = None
    if refresh_token:
        try:
            payload = decode_refresh_token(refresh_token)
            current_jti = payload.get("jti")
        except Exception:
            pass

    sessions = await db.db.user_sessions.find({"user_id": current_user["id"]}).sort("created_at", -1).to_list(length=None)

    res = []
    for s in sessions:
        res.append({
            "id": s["id"],
            "device_info": s["device_info"],
            "ip_address": s["ip_address"],
            "last_active": s["last_active"],
            "created_at": s["created_at"],
            "is_current": s["token_jti"] == current_jti
        })
    return {"success": True, "sessions": res}

@router.post("/sessions/logout-all")
async def logout_all_devices(request: Request, response: Response, current_user: dict = Depends(get_current_user)):
    """Logs out of all devices and clears all sessions except current or logs out completely."""
    # We clear ALL sessions for user
    await db.db.user_sessions.delete_many({"user_id": current_user["id"]})
    
    # Clear cookies
    response.delete_cookie("refresh_token", path="/")
    response.delete_cookie("csrf_token", path="/")
    
    return {"success": True, "message": "Logged out of all devices successfully."}

# ─── Google OAuth Flow ───────────────────────────────────────

@router.get("/google/login")
async def google_login(request: Request):
    """Redirects user to Google OAuth 2.0 flow, saving target origin in state."""
    referer = request.headers.get("referer")
    frontend_origin = "http://localhost:3000"
    if referer:
        from urllib.parse import urlparse
        parsed = urlparse(referer)
        if parsed.netloc:
            frontend_origin = f"{parsed.scheme}://{parsed.netloc}"

    import urllib.parse
    google_auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={settings.GOOGLE_CLIENT_ID}"
        "&redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fapi%2Fv1%2Fauth%2Foauth%2Fcallback"
        "&response_type=code"
        "&scope=openid+email+profile"
        f"&state={urllib.parse.quote(frontend_origin)}"
    )
    return RedirectResponse(url=google_auth_url)


@router.get("/oauth/callback")
async def oauth_callback(request: Request):
    """
    Standard Google OAuth callback handler.
    Exchanges code for access token, retrieves user profile, creates session, and redirects to frontend.
    """
    code = request.query_params.get("code")
    state = request.query_params.get("state") or "http://localhost:3000"
    error = request.query_params.get("error")

    # Securely parse/verify dynamic state redirect origin
    from urllib.parse import urlparse
    try:
        parsed_state = urlparse(state)
        # Verify it is localhost, 127.0.0.1, or a configured CORS origin for safety
        if parsed_state.netloc and (
            "localhost" in parsed_state.netloc or
            "127.0.0.1" in parsed_state.netloc or
            state in settings.CORS_ORIGINS
        ):
            frontend_origin = f"{parsed_state.scheme}://{parsed_state.netloc}"
        else:
            frontend_origin = "http://localhost:3000"
    except Exception:
        frontend_origin = "http://localhost:3000"

    if error or not code:
        logger.error(f"Google OAuth authorization failed: {error}")
        return RedirectResponse(url=f"{frontend_origin}/?error=google_auth_denied")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 1. Exchange Auth Code for Access Token
            token_url = "https://oauth2.googleapis.com/token"
            token_payload = {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": "http://localhost:8000/api/v1/auth/oauth/callback"
            }
            token_resp = await client.post(token_url, data=token_payload)
            token_resp.raise_for_status()
            token_data = token_resp.json()
            access_token = token_data.get("access_token")

            if not access_token:
                raise ValueError("No access token returned by Google")

            # 2. Retrieve user profile info using the access token
            userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
            userinfo_resp = await client.get(userinfo_url, headers={"Authorization": f"Bearer {access_token}"})
            userinfo_resp.raise_for_status()
            userinfo = userinfo_resp.json()

    except Exception as e:
        logger.error(f"Google OAuth token exchange or profile fetch failed: {e}")
        return RedirectResponse(url=f"{frontend_origin}/?error=google_exchange_failed")

    email = userinfo.get("email", "").strip().lower()
    name = userinfo.get("name", "").strip() or email.split("@")[0]
    avatar_url = userinfo.get("picture", "")

    if not email:
        logger.error("Google user profile is missing email address.")
        return RedirectResponse(url=f"{frontend_origin}/?error=missing_email")

    # Check if user already exists
    user = await db.db.users.find_one({"email": email})
    
    if not user:
        # Create user automatically (on-the-fly registration)
        user_id = str(uuid.uuid4())
        
        # Check first user rule
        count_row = {"count": await db.db.users.count_documents({})}
        role = "OWNER" if count_row and count_row["count"] == 0 else "USER"
        
        await db.db.users.insert_one({"id": user_id, "name": name, "email": email, "avatar_url": avatar_url, "provider": "google", "role": role, "is_active": True})
        user = {"id": user_id, "name": name, "email": email, "role": role, "is_active": True}
    else:
        # Check active status
        if not user["is_active"]:
            return RedirectResponse(url=f"{frontend_origin}/?error=account_deactivated")
        user_id = user["id"]

    # Establish session
    jti = str(uuid.uuid4())
    app_access_token = create_access_token(user_id, user["role"], user["name"])
    app_refresh_token = create_refresh_token(user_id, jti)
    csrf_token = str(uuid.uuid4())

    device_info = request.headers.get("user-agent", "Unknown Device")
    ip_address = request.client.host if request.client else "Unknown IP"
    
    await db.db.user_sessions.insert_one({"id": str(uuid.uuid4()), "user_id": user_id, "token_jti": jti, "device_info": device_info, "ip_address": ip_address, "created_at": datetime.utcnow().isoformat(), "last_active": datetime.utcnow().isoformat()})

    # Touch last login
    now = datetime.utcnow().isoformat()
    await db.db.users.update_one({"id": user_id}, {"$set": {"last_login": now, "updated_at": now}})

    # Redirect to frontend, passing token and csrf in URL, setting refresh token in secure cookie
    redirect_url = f"{frontend_origin}/?token={app_access_token}&csrf={csrf_token}"
    response = RedirectResponse(url=redirect_url)
    set_auth_cookies(response, app_refresh_token, csrf_token)
    return response


@router.post("/oauth/callback")
async def oauth_callback_post(body: OAuthLoginRequest, request: Request, response: Response):
    """
    Handles client-initiated mock OAuth login flows.
    Registers provider-specific user on-the-fly and starts session.
    """
    email = body.email.strip().lower()
    name = body.name.strip()
    avatar_url = body.avatar_url or f"https://api.dicebear.com/7.x/bottts/svg?seed={name}"
    provider = body.provider.strip().lower()

    # Check if user already exists
    user = await db.db.users.find_one({"email": email})
    
    if not user:
        # Create user automatically (on-the-fly registration)
        user_id = str(uuid.uuid4())
        
        # Check first user rule
        count_row = {"count": await db.db.users.count_documents({})}
        role = "OWNER" if count_row and count_row["count"] == 0 else "USER"
        
        await db.db.users.insert_one({"id": user_id, "name": name, "email": email, "avatar_url": avatar_url, "provider": provider, "role": role, "is_active": True})
        user = {"id": user_id, "name": name, "email": email, "role": role, "is_active": True}
    else:
        # Check active status
        if not user["is_active"]:
            raise HTTPException(status_code=401, detail="User account is deactivated")
        user_id = user["id"]

    # Establish session
    jti = str(uuid.uuid4())
    app_access_token = create_access_token(user_id, user["role"], user["name"])
    app_refresh_token = create_refresh_token(user_id, jti)
    csrf_token = str(uuid.uuid4())

    device_info = request.headers.get("user-agent", "Unknown Device")
    ip_address = request.client.host if request.client else "Unknown IP"
    
    await db.db.user_sessions.insert_one({"id": str(uuid.uuid4()), "user_id": user_id, "token_jti": jti, "device_info": device_info, "ip_address": ip_address, "created_at": datetime.utcnow().isoformat(), "last_active": datetime.utcnow().isoformat()})

    # Touch last login
    now = datetime.utcnow().isoformat()
    await db.db.users.update_one({"id": user_id}, {"$set": {"last_login": now, "updated_at": now}})

    set_auth_cookies(response, app_refresh_token, csrf_token)

    return {
        "success": True,
        "access_token": app_access_token,
        "csrf_token": csrf_token,
        "user": {
            "id": user_id,
            "name": user["name"],
            "email": user["email"],
            "role": user["role"]
        }
    }


