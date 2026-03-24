"""
Moonjar PMS — Authentication & authorization.
JWT HttpOnly cookies, Google OAuth, TOTP 2FA, CSRF, lockout.
"""

import uuid
import secrets
import hmac
import hashlib
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import APIKeyCookie
from sqlalchemy.orm import Session
import jwt
from jwt.exceptions import PyJWTError as JWTError
import bcrypt as _bcrypt

from api.config import get_settings
from api.database import get_db

settings = get_settings()
cookie_scheme = APIKeyCookie(name="access_token", auto_error=False)

ALGORITHM = "HS256"
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15
MAX_SESSIONS_PER_USER = 5


# --- Password hashing (direct bcrypt, no passlib) ---

def hash_password(password: str) -> str:
    return _bcrypt.hashpw(password.encode("utf-8"), _bcrypt.gensalt(rounds=12)).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# --- JWT tokens ---

def create_access_token(user_id: str, role: str, jti: str = None) -> str:
    jti = jti or str(uuid.uuid4())
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "role": role,
        "jti": jti,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(user_id: str, jti: str = None) -> str:
    jti = jti or str(uuid.uuid4())
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_REFRESH_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "jti": jti,
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    """Decode JWT, trying current key then previous key."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        if settings.SECRET_KEY_PREVIOUS:
            return jwt.decode(token, settings.SECRET_KEY_PREVIOUS, algorithms=[ALGORITHM])
        raise


# --- Cookie helpers ---

def set_auth_cookies(response: Response, access_token: str, refresh_token: str, csrf_token: str):
    """Set HttpOnly cookies for tokens.

    Uses SameSite=None + Secure for cross-origin Railway deployment
    (frontend and API on separate *.up.railway.app subdomains).
    Path=/ so cookies are sent on all API requests regardless of prefix.

    SECURITY NOTE: SameSite=Lax would be preferable, but the frontend and API
    are on different subdomains (cross-origin). SameSite=Lax would prevent
    cookies from being sent on cross-origin requests, breaking auth entirely.
    To switch to SameSite=Lax, deploy frontend and API on the same origin
    (e.g. via reverse proxy or custom domain).

    TODO(security): Migrate to SameSite=Lax once a custom domain is configured
    so that the frontend and API share the same origin. SameSite=None exposes
    cookies to cross-site request forgery vectors that CSRF-token mitigation
    only partially addresses.
    """
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=settings.JWT_ACCESS_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=settings.JWT_REFRESH_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,  # JS needs to read this
        secure=True,
        samesite="none",
        path="/",
        max_age=settings.JWT_ACCESS_EXPIRE_MINUTES * 60,
    )
    # Also expose CSRF token in response header so the frontend can read it
    # even in cross-origin Railway deployments (where document.cookie is
    # scoped to the backend domain and JS on the frontend domain can't read it).
    # X-CSRF-Token is in CORS expose_headers so the browser allows JS to read it.
    response.headers["X-CSRF-Token"] = csrf_token

def clear_auth_cookies(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    response.delete_cookie("csrf_token", path="/")


# --- CSRF ---

def generate_csrf_token(session_id: str) -> str:
    """Generate CSRF token using HMAC-SHA256."""
    return hmac.new(
        settings.SECRET_KEY.encode(),
        session_id.encode(),
        hashlib.sha256,
    ).hexdigest()

def validate_csrf(request: Request):
    """Validate CSRF token on mutating requests.

    Supports two modes:
    1. Double-submit: cookie == header (same-origin or SameSite=None works)
    2. JWT fallback: header == HMAC(SECRET_KEY, jti) from access_token
       (cross-origin when third-party cookies are blocked)
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    csrf_cookie = request.cookies.get("csrf_token")
    csrf_header = request.headers.get("X-CSRF-Token")

    # Fast path: double-submit
    if csrf_cookie and csrf_header and csrf_cookie == csrf_header:
        return

    # Fallback: verify against JWT session
    if csrf_header:
        access_token = request.cookies.get("access_token")
        if access_token:
            try:
                payload = decode_token(access_token)
                expected = generate_csrf_token(payload.get("jti", ""))
                if csrf_header == expected:
                    return
            except Exception:
                pass

    raise HTTPException(status_code=403, detail="CSRF token mismatch")


# --- Current user dependency ---

async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
):
    """Extract user from HttpOnly access_token cookie."""
    from api.models import User, ActiveSession

    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")

    # Verify session is not revoked
    jti = payload.get("jti")
    if jti:
        session = db.query(ActiveSession).filter(
            ActiveSession.token_jti == jti,
            ActiveSession.revoked == False,
        ).first()
        if not session:
            raise HTTPException(status_code=401, detail="Session revoked")

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


# --- Lockout ---

def check_lockout(user) -> None:
    """Raise 423 if user account is locked."""
    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        raise HTTPException(
            status_code=423,
            detail="Account locked",
            headers={"Retry-After": str(int((user.locked_until - datetime.now(timezone.utc)).total_seconds()))},
        )

def record_failed_login(db: Session, user) -> None:
    user.failed_login_count += 1
    if user.failed_login_count >= MAX_FAILED_ATTEMPTS:
        user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
    db.commit()

def reset_failed_logins(db: Session, user) -> None:
    user.failed_login_count = 0
    user.locked_until = None
    db.commit()


# --- Session management ---

def create_session(db: Session, user_id: str, jti: str, request: Request) -> None:
    """Create active session record, enforce max sessions."""
    from api.models import ActiveSession

    # Count active sessions
    active_count = db.query(ActiveSession).filter(
        ActiveSession.user_id == user_id,
        ActiveSession.revoked == False,
    ).count()

    # If at limit, revoke oldest
    if active_count >= MAX_SESSIONS_PER_USER:
        oldest = db.query(ActiveSession).filter(
            ActiveSession.user_id == user_id,
            ActiveSession.revoked == False,
        ).order_by(ActiveSession.created_at.asc()).first()
        if oldest:
            oldest.revoked = True
            oldest.revoked_at = datetime.now(timezone.utc)
            oldest.revoked_reason = "max_sessions"

    session = ActiveSession(
        user_id=user_id,
        token_jti=jti,
        ip_address=request.client.host if request.client else "0.0.0.0",
        user_agent=request.headers.get("user-agent", ""),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_REFRESH_EXPIRE_MINUTES),
    )
    db.add(session)
    db.commit()


# --- Factory scoping ---

def apply_factory_filter(query, current_user, factory_id, model_class):
    """Apply factory_id filter based on user role and request.

    - Explicit factory_id parameter → always filter by that factory
    - Owner/CEO/Admin → see all factories
    - Other roles with assigned factories → see only assigned
    - Other roles WITHOUT assigned factories → see all (not blocked;
      Admin can restrict later via Dashboard Constructor)
    """
    from api.models import UserFactory

    if factory_id:
        return query.filter(model_class.factory_id == factory_id)

    # Owner/CEO/Admin always see all
    if current_user.role in ("owner", "ceo", "administrator"):
        return query

    # Other roles: filter by user's assigned factories
    user_factory_ids = [
        uf.factory_id for uf in
        current_user.user_factories  # type: ignore
    ] if hasattr(current_user, "user_factories") else []

    if user_factory_ids:
        return query.filter(model_class.factory_id.in_(user_factory_ids))

    # No factory assignments → show all (graceful default, not block)
    # Admin can restrict access later via factory assignment
    return query


# --- Security audit logging ---

def log_security_event(
    db: Session,
    action: str,
    actor_id: str = None,
    actor_email: str = None,
    ip_address: str = None,
    user_agent: str = None,
    target_entity: str = None,
    target_id: str = None,
    details: dict = None,
    factory_id: str = None,
):
    """Log a security event to security_audit_log table."""
    from api.models import SecurityAuditLog
    log_entry = SecurityAuditLog(
        action=action,
        actor_id=actor_id,
        actor_email=actor_email,
        ip_address=ip_address or "0.0.0.0",
        user_agent=user_agent,
        target_entity=target_entity,
        target_id=target_id,
        details=details or {},
        factory_id=factory_id,
    )
    db.add(log_entry)
    try:
        db.commit()
    except Exception:
        db.rollback()


# --- Google OAuth ---

async def verify_google_token(id_token: str) -> dict:
    """Verify Google OAuth ID token and return user info."""
    from google.oauth2 import id_token as google_id_token
    from google.auth.transport import requests as google_requests

    try:
        idinfo = google_id_token.verify_oauth2_token(
            id_token,
            google_requests.Request(),
            settings.GOOGLE_OAUTH_CLIENT_ID,
        )
        return {
            "google_id": idinfo["sub"],
            "email": idinfo["email"],
            "name": idinfo.get("name", idinfo["email"]),
        }
    except Exception as e:
        import logging
        logging.getLogger("moonjar.auth").warning(f"Google token verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired Google token")
