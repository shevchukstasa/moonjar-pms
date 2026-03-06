"""Auth router — login, Google OAuth, refresh, logout, TOTP."""

import uuid as _uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import (
    verify_password, create_access_token, create_refresh_token,
    decode_token, set_auth_cookies, clear_auth_cookies, generate_csrf_token,
    check_lockout, record_failed_login, reset_failed_logins, create_session,
    verify_google_token, log_security_event, get_current_user,
)
from api.models import User, ActiveSession

router = APIRouter()


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
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(401, "Invalid credentials")
    check_lockout(user)
    if not verify_password(data.password, user.password_hash or ""):
        record_failed_login(db, user)
        raise HTTPException(401, "Invalid credentials")
    reset_failed_logins(db, user)
    jti = str(_uuid.uuid4())
    access = create_access_token(str(user.id), user.role, jti)
    refresh = create_refresh_token(str(user.id), jti)
    csrf = generate_csrf_token(jti)
    create_session(db, str(user.id), jti, request)
    set_auth_cookies(response, access, refresh, csrf)
    log_security_event(db, "login", actor_id=str(user.id), actor_email=user.email,
                       ip_address=request.client.host if request.client else None)
    return {"access_token": access, "token_type": "bearer",
            "user": {"id": str(user.id), "email": user.email, "role": user.role, "name": user.name}}


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
    access = create_access_token(str(user.id), user.role, jti)
    refresh = create_refresh_token(str(user.id), jti)
    csrf = generate_csrf_token(jti)
    create_session(db, str(user.id), jti, request)
    set_auth_cookies(response, access, refresh, csrf)
    return {"access_token": access, "token_type": "bearer",
            "user": {"id": str(user.id), "email": user.email, "role": user.role, "name": user.name}}


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
    user = db.query(User).filter(User.id == payload["sub"], User.is_active == True).first()
    if not user:
        raise HTTPException(401, "User not found")
    jti = str(_uuid.uuid4())
    access = create_access_token(str(user.id), user.role, jti)
    csrf = generate_csrf_token(jti)
    response.set_cookie("access_token", access, httponly=True, secure=True, samesite="strict", path="/api")
    response.set_cookie("csrf_token", csrf, httponly=False, secure=True, samesite="strict", path="/")
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
async def get_me(current_user=Depends(get_current_user)):
    return {"id": str(current_user.id), "email": current_user.email,
            "role": current_user.role, "name": current_user.name}


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
