"""Auth router — login, Google OAuth, refresh, logout, TOTP."""

import uuid as _uuid
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.database import get_db
from api.enums import AuditActionType
from api.auth import (
    verify_password, create_access_token, create_refresh_token,
    decode_token, set_auth_cookies, clear_auth_cookies, generate_csrf_token,
    check_lockout, record_failed_login, reset_failed_logins, create_session,
    verify_google_token, log_security_event, get_current_user,
)
from api.models import User, ActiveSession  # ActiveSession needed for refresh token rotation

router = APIRouter()
logger = logging.getLogger("moonjar.auth")


def _role_str(role) -> str:
    """Safely convert role to string value."""
    return role.value if hasattr(role, 'value') else str(role)


class LoginRequest(BaseModel):
    email: str
    password: str

class GoogleLoginRequest(BaseModel):
    id_token: str

class TOTPVerifyRequest(BaseModel):
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
        return {"access_token": access, "token_type": "bearer",
                "user": {"id": str(user.id), "email": user.email,
                         "role": role_val, "name": user.name}}
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
    return {"access_token": access, "token_type": "bearer",
            "user": {"id": str(user.id), "email": user.email,
                     "role": role_val, "name": user.name}}


@router.post("/refresh")
async def refresh_token(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(401, "No refresh token")
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(401, "Invalid refresh token")
    if payload.get("type") != "refresh":
        raise HTTPException(401, "Invalid token type")

    # Verify old session is still valid
    old_jti = payload.get("jti")
    if old_jti:
        old_session = db.query(ActiveSession).filter(
            ActiveSession.token_jti == old_jti,
            ActiveSession.revoked == False,
        ).first()
        if not old_session:
            raise HTTPException(401, "Session revoked")
        # Revoke old session (token rotation)
        old_session.revoked = True
        old_session.revoked_at = datetime.now(timezone.utc)
        old_session.revoked_reason = "token_rotation"

    user = db.query(User).filter(User.id == payload["sub"], User.is_active == True).first()
    if not user:
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
        except Exception:
            pass
    clear_auth_cookies(response)
    return {"detail": "Logged out"}


@router.get("/me")
async def get_me(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    from api.models import UserFactory, Factory
    role = _role_str(current_user.role)
    # Owner/administrator see ALL factories automatically (no manual assignment needed)
    if role in ("owner", "administrator"):
        all_factories = db.query(Factory.id, Factory.name).filter(Factory.is_active.is_(True)).all()
        factories = [{"id": str(f.id), "name": f.name} for f in all_factories]
    else:
        user_factories = (
            db.query(Factory.id, Factory.name)
            .join(UserFactory, UserFactory.factory_id == Factory.id)
            .filter(UserFactory.user_id == current_user.id)
            .all()
        )
        factories = [{"id": str(f.id), "name": f.name} for f in user_factories]
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "role": _role_str(current_user.role),
        "name": current_user.name,
        "language": getattr(current_user, 'language', None) or "en",
        "is_active": current_user.is_active,
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
    if data.key != settings.OWNER_KEY:
        raise HTTPException(403, "Invalid owner key")
    # Check if owner already exists
    owner = db.query(User).filter(User.role == "owner").first()
    if owner:
        return {"status": "owner_exists", "email": owner.email,
                "message": "Owner account already configured"}
    return {"status": "key_valid", "message": "Key verified. Proceed to create owner account."}


@router.post("/totp/setup")
async def totp_setup(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    # TODO: Implement TOTP setup — see BUSINESS_LOGIC.md §Security
    import pyotp
    secret = pyotp.random_base32()
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name=current_user.email, issuer_name="Moonjar PMS")
    return {"secret": secret, "qr_uri": uri}


@router.post("/totp/verify")
async def totp_verify(data: TOTPVerifyRequest, db: Session = Depends(get_db),
                      current_user=Depends(get_current_user)):
    # TODO: Verify TOTP code and enable 2FA — see BUSINESS_LOGIC.md §Security
    raise HTTPException(501, "Not implemented")


@router.post("/totp/disable")
async def totp_disable(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    # TODO: Disable TOTP 2FA — see BUSINESS_LOGIC.md §Security
    raise HTTPException(501, "Not implemented")
