"""Auth router — login, Google OAuth, refresh, logout, TOTP login verification."""

import hmac
import uuid as _uuid
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from jwt.exceptions import PyJWTError as JWTError
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.config import get_settings
from api.database import get_db
from api.enums import AuditActionType
from api.auth import (
    verify_password, hash_password, create_access_token, create_refresh_token,
    decode_token, set_auth_cookies, clear_auth_cookies, generate_csrf_token,
    check_lockout, record_failed_login, reset_failed_logins, create_session,
    verify_google_token, log_security_event, get_current_user,
    ALGORITHM,
)
from api.models import User, ActiveSession, UserFactory, Factory  # ActiveSession needed for refresh token rotation

router = APIRouter()
logger = logging.getLogger("moonjar.auth")

# Roles that automatically see ALL active factories (no manual assignment needed)
_GLOBAL_FACTORY_ROLES = {"owner", "administrator"}


def _get_user_factories(db: Session, user: User, role: str) -> list[dict]:
    """Return list of {id, name} for factories accessible by this user."""
    if role in _GLOBAL_FACTORY_ROLES:
        rows = db.query(Factory.id, Factory.name).filter(Factory.is_active.is_(True)).all()
    else:
        rows = (
            db.query(Factory.id, Factory.name)
            .join(UserFactory, UserFactory.factory_id == Factory.id)
            .filter(UserFactory.user_id == user.id)
            .all()
        )
    return [{"id": str(r.id), "name": r.name} for r in rows]

# Temporary pre-2FA token lifetime (5 minutes)
_TOTP_PENDING_EXPIRE_MINUTES = 5


def _role_str(role) -> str:
    """Safely convert role to string value."""
    return role.value if hasattr(role, 'value') else str(role)


def _create_totp_pending_token(user_id: str) -> str:
    """Create a short-lived JWT that proves the user passed password auth
    but still needs to complete 2FA. This token cannot be used as an access
    token because its ``type`` is ``totp_pending``.
    """
    import jwt
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=_TOTP_PENDING_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "exp": expire,
        "type": "totp_pending",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def _decode_totp_pending_token(token: str) -> dict:
    """Decode and validate a totp_pending token."""
    import jwt
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        if settings.SECRET_KEY_PREVIOUS:
            payload = jwt.decode(token, settings.SECRET_KEY_PREVIOUS, algorithms=[ALGORITHM])
        else:
            raise
    if payload.get("type") != "totp_pending":
        raise ValueError("Not a TOTP pending token")
    return payload


class LoginRequest(BaseModel):
    email: str
    password: str

class GoogleLoginRequest(BaseModel):
    id_token: str

class TOTPLoginVerifyRequest(BaseModel):
    """Used during the login flow when 2FA is required."""
    totp_pending_token: str
    code: str


@router.post("/login")
async def login(data: LoginRequest, request: Request, response: Response,
                db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.email == data.email).first()
        if not user:
            raise HTTPException(401, "Invalid credentials")
        check_lockout(user)
        if not verify_password(data.password, user.password_hash or ""):
            record_failed_login(db, user)
            raise HTTPException(401, "Invalid credentials")
        reset_failed_logins(db, user)

        # --- 2FA gate ---
        if user.totp_enabled:
            # Password is correct but 2FA is required.
            # Return a short-lived pending token; no session or cookies yet.
            pending_token = _create_totp_pending_token(str(user.id))
            return {
                "requires_totp": True,
                "totp_pending_token": pending_token,
                "message": "Two-factor authentication required",
            }

        # --- Normal login (no 2FA) ---
        jti = str(_uuid.uuid4())
        role_val = _role_str(user.role)
        access = create_access_token(str(user.id), role_val, jti)
        refresh = create_refresh_token(str(user.id), jti)
        csrf = generate_csrf_token(jti)
        create_session(db, str(user.id), jti, request)
        set_auth_cookies(response, access, refresh, csrf)
        log_security_event(db, AuditActionType.LOGIN_SUCCESS,
                           actor_id=str(user.id), actor_email=user.email,
                           ip_address=request.client.host if request.client else None)
        # NOTE: access_token is returned in both HttpOnly cookies AND the JSON body.
        # This is intentional — the SPA reads access_token from the response for
        # in-memory storage (e.g. WebSocket auth query param). Cookies provide the
        # primary auth mechanism; the body token is a convenience for non-cookie flows.
        factories = _get_user_factories(db, user, role_val)
        return {"access_token": access, "token_type": "bearer",
                "user": {"id": str(user.id), "email": user.email,
                         "role": role_val, "name": user.name,
                         "factories": factories}}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(500, "An unexpected error occurred during login")


@router.post("/google")
async def google_login(data: GoogleLoginRequest, request: Request, response: Response,
                       db: Session = Depends(get_db)):
    info = await verify_google_token(data.id_token)
    user = db.query(User).filter(User.email == info["email"]).first()
    if not user:
        raise HTTPException(403, "User not registered. Contact administrator.")
    if not user.google_id:
        user.google_id = info["google_id"]
        db.commit()

    # --- 2FA gate ---
    if user.totp_enabled:
        pending_token = _create_totp_pending_token(str(user.id))
        return {
            "requires_totp": True,
            "totp_pending_token": pending_token,
            "message": "Two-factor authentication required",
        }

    # --- Normal login (no 2FA) ---
    jti = str(_uuid.uuid4())
    role_val = _role_str(user.role)
    access = create_access_token(str(user.id), role_val, jti)
    refresh = create_refresh_token(str(user.id), jti)
    csrf = generate_csrf_token(jti)
    create_session(db, str(user.id), jti, request)
    set_auth_cookies(response, access, refresh, csrf)
    log_security_event(db, AuditActionType.LOGIN_SUCCESS,
                       actor_id=str(user.id), actor_email=user.email,
                       ip_address=request.client.host if request.client else None)
    factories = _get_user_factories(db, user, role_val)
    return {"access_token": access, "token_type": "bearer",
            "user": {"id": str(user.id), "email": user.email,
                     "role": role_val, "name": user.name,
                     "factories": factories}}


@router.post("/refresh")
async def refresh_token(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get("refresh_token")
    if not token:
        logger.info("REFRESH_401: no cookie")
        raise HTTPException(401, "No refresh token")
    try:
        payload = decode_token(token)
    except Exception as e:
        logger.info("REFRESH_401: decode failed: %s", type(e).__name__)
        raise HTTPException(401, "Invalid refresh token")
    if payload.get("type") != "refresh":
        logger.info("REFRESH_401: wrong token type: %s", payload.get("type"))
        raise HTTPException(401, "Invalid token type")

    # Verify old session is still valid
    old_jti = payload.get("jti")
    user_id_from_token = payload.get("sub")
    if old_jti:
        old_session = db.query(ActiveSession).filter(
            ActiveSession.token_jti == old_jti,
            ActiveSession.revoked == False,
        ).first()
        if not old_session:
            logger.info("REFRESH_401: session revoked for user=%s jti=%s", user_id_from_token, old_jti[:8])
            raise HTTPException(401, "Session revoked")
        # Revoke old session (token rotation)
        old_session.revoked = True
        old_session.revoked_at = datetime.now(timezone.utc)
        old_session.revoked_reason = "token_rotation"

    user = db.query(User).filter(User.id == payload["sub"], User.is_active == True).first()
    if not user:
        logger.info("REFRESH_401: user not found/inactive user_id=%s", user_id_from_token)
        raise HTTPException(401, "User not found")

    # Create new session with new JTI
    jti = str(_uuid.uuid4())
    role_val = _role_str(user.role)
    access = create_access_token(str(user.id), role_val, jti)
    refresh = create_refresh_token(str(user.id), jti)
    csrf = generate_csrf_token(jti)
    create_session(db, str(user.id), jti, request)
    set_auth_cookies(response, access, refresh, csrf)
    return {"access_token": access, "token_type": "bearer"}


@router.post("/logout")
async def logout(request: Request, response: Response, db: Session = Depends(get_db),
                 current_user=Depends(get_current_user)):
    token = request.cookies.get("access_token")
    if token:
        try:
            payload = decode_token(token)
            jti = payload.get("jti")
            if jti:
                session = db.query(ActiveSession).filter(ActiveSession.token_jti == jti).first()
                if session:
                    session.revoked = True
                    session.revoked_at = datetime.now(timezone.utc)
                    session.revoked_reason = "logout"
                    db.commit()
        except Exception as e:
            logger.warning("Failed to revoke session on logout: %s", e)
    clear_auth_cookies(response)
    return {"detail": "Logged out"}


@router.get("/me")
async def get_me(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    role = _role_str(current_user.role)
    factories = _get_user_factories(db, current_user, role)
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "role": _role_str(current_user.role),
        "name": current_user.name,
        "language": getattr(current_user, 'language', None) or "en",
        "is_active": current_user.is_active,
        "totp_enabled": bool(current_user.totp_enabled),
        "factories": factories,
    }


@router.post("/logout-all")
async def logout_all(request: Request, response: Response, db: Session = Depends(get_db),
                     current_user=Depends(get_current_user)):
    """Revoke ALL active sessions for the current user."""
    revoked = db.query(ActiveSession).filter(
        ActiveSession.user_id == str(current_user.id),
        ActiveSession.revoked == False,
    ).update({
        "revoked": True,
        "revoked_at": datetime.now(timezone.utc),
        "revoked_reason": "logout_all",
    })
    db.commit()
    clear_auth_cookies(response)
    log_security_event(db, AuditActionType.LOGOUT,
                       actor_id=str(current_user.id), actor_email=current_user.email,
                       ip_address=request.client.host if request.client else None,
                       details={"type": "logout_all", "sessions_revoked": revoked})
    return {"detail": f"Logged out from all devices", "sessions_revoked": revoked}


class OwnerKeyRequest(BaseModel):
    key: str

@router.post("/verify-owner-key")
async def verify_owner_key(data: OwnerKeyRequest, db: Session = Depends(get_db)):
    """First-time owner setup: verify the OWNER_KEY to claim the owner account."""
    from api.config import get_settings
    settings = get_settings()
    if not settings.OWNER_KEY or settings.OWNER_KEY in ("change-me", ""):
        raise HTTPException(503, "Owner key not configured. Contact system administrator.")
    if not hmac.compare_digest(data.key, settings.OWNER_KEY):
        raise HTTPException(403, "Invalid owner key")
    # Check if owner already exists
    owner = db.query(User).filter(User.role == "owner").first()
    if owner:
        return {"status": "owner_exists", "email": owner.email,
                "message": "Owner account already configured"}
    return {"status": "key_valid", "message": "Key verified. Proceed to create owner account."}


@router.post("/totp-verify")
async def totp_login_verify(
    data: TOTPLoginVerifyRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Complete login by verifying a TOTP code (or backup code) after password auth.

    The client must send the ``totp_pending_token`` received from ``/login`` or
    ``/google`` along with a valid TOTP or backup code. On success, full JWT
    cookies are issued and a session is created.
    """
    # Decode the pending token
    try:
        payload = _decode_totp_pending_token(data.totp_pending_token)
    except Exception:
        raise HTTPException(401, "Invalid or expired TOTP pending token. Please log in again.")

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(401, "User not found")

    if not user.totp_enabled:
        raise HTTPException(400, "TOTP is not enabled for this user")

    # Verify the code (TOTP or backup)
    from api.routers.security import _verify_totp_or_backup
    valid, method = _verify_totp_or_backup(db, user, data.code)
    if not valid:
        log_security_event(
            db, AuditActionType.LOGIN_FAILED,
            actor_id=str(user.id), actor_email=user.email,
            ip_address=request.client.host if request.client else None,
            details={"reason": "invalid_totp_code"},
        )
        raise HTTPException(401, "Invalid TOTP or backup code")

    # Issue full session
    jti = str(_uuid.uuid4())
    role_val = _role_str(user.role)
    access = create_access_token(str(user.id), role_val, jti)
    refresh = create_refresh_token(str(user.id), jti)
    csrf = generate_csrf_token(jti)
    create_session(db, str(user.id), jti, request)
    set_auth_cookies(response, access, refresh, csrf)

    log_security_event(
        db, AuditActionType.LOGIN_SUCCESS,
        actor_id=str(user.id), actor_email=user.email,
        ip_address=request.client.host if request.client else None,
        details={"totp_method": method},
    )

    factories = _get_user_factories(db, user, role_val)
    return {
        "access_token": access,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "role": role_val,
            "name": user.name,
            "factories": factories,
        },
    }


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Change password for the authenticated user.

    Validates current password, enforces complexity on new password,
    updates the hash, and logs the change in the security audit log.
    """
    # Verify current password
    if not current_user.password_hash or not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(400, "Current password is incorrect")

    # Validate new password complexity
    if len(data.new_password) < 10:
        raise HTTPException(422, "New password must be at least 10 characters")
    if not any(c.isdigit() for c in data.new_password):
        raise HTTPException(422, "New password must contain at least one digit")
    if not any(c.isalpha() for c in data.new_password):
        raise HTTPException(422, "New password must contain at least one letter")

    # Update password
    current_user.password_hash = hash_password(data.new_password)
    db.commit()

    # Audit log
    log_security_event(
        db,
        AuditActionType.PASSWORD_CHANGE,
        actor_id=str(current_user.id),
        actor_email=current_user.email,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        target_entity="user",
        target_id=str(current_user.id),
    )

    return {"message": "Password changed successfully"}
