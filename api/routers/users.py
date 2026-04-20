"""Users router — user management (CRUD + factory assignment)."""

from uuid import UUID
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_

from api.database import get_db
from api.auth import hash_password, log_security_event
from api.roles import require_admin, require_management
from api.models import User, UserFactory, Factory, ActiveSession
from api.enums import UserRole, LanguagePreference

router = APIRouter()


def _ev(val):
    return val.value if hasattr(val, "value") else str(val) if val else None


def _serialize_user(user: User, db: Session) -> dict:
    """Serialize user with factory assignments."""
    factories = (
        db.query(Factory.id, Factory.name)
        .join(UserFactory, UserFactory.factory_id == Factory.id)
        .filter(UserFactory.user_id == user.id)
        .all()
    )
    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "role": _ev(user.role),
        "language": _ev(user.language),
        "telegram_user_id": user.telegram_user_id,
        "is_active": user.is_active,
        "totp_enabled": user.totp_enabled,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        "factories": [{"id": str(f.id), "name": f.name} for f in factories],
    }


class UserCreateInput(BaseModel):
    email: str
    name: str
    role: str
    password: Optional[str] = None  # Optional for Google OAuth users
    google_auth: bool = False       # If True, user logs in via Google only
    factory_ids: list[str] = []
    language: Optional[str] = "en"


class UserUpdateInput(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    language: Optional[str] = None
    telegram_user_id: Optional[int] = None
    factory_ids: Optional[list[str]] = None


# --- Endpoints ---

@router.get("")
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    role: str | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    factory_id: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    query = db.query(User)

    if role:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    if search:
        term = f"%{search}%"
        query = query.filter(or_(User.name.ilike(term), User.email.ilike(term)))
    if factory_id:
        query = query.join(UserFactory, UserFactory.user_id == User.id).filter(
            UserFactory.factory_id == UUID(factory_id)
        )

    total = query.count()
    users = query.order_by(User.name).offset((page - 1) * per_page).limit(per_page).all()

    return {
        "items": [_serialize_user(u, db) for u in users],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/{user_id}")
async def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    return _serialize_user(user, db)


@router.post("", status_code=201)
async def create_user(
    data: UserCreateInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    # Check duplicate email
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(409, f"User with email '{data.email}' already exists")

    # Validate role
    valid_roles = [r.value for r in UserRole]
    if data.role not in valid_roles:
        raise HTTPException(422, f"Invalid role '{data.role}'. Valid: {', '.join(valid_roles)}")

    # Validate language
    valid_langs = [l.value for l in LanguagePreference]
    lang = data.language if data.language in valid_langs else "en"

    # Validate: either password or google_auth must be provided
    if not data.password and not data.google_auth:
        raise HTTPException(422, "Either password or Google Auth must be provided")

    if data.password:
        if len(data.password) < 10:
            raise HTTPException(422, "Password must be at least 10 characters")
        if not any(c.isdigit() for c in data.password):
            raise HTTPException(422, "Password must contain at least one digit")
        if not any(c.isalpha() for c in data.password):
            raise HTTPException(422, "Password must contain at least one letter")

    # Create user
    user = User(
        email=data.email,
        name=data.name,
        role=data.role,
        password_hash=hash_password(data.password) if data.password else None,
        language=lang,
        is_active=True,
    )
    db.add(user)
    db.flush()

    # Assign factories
    for fid in data.factory_ids:
        factory = db.query(Factory).filter(Factory.id == UUID(fid)).first()
        if factory:
            db.add(UserFactory(user_id=user.id, factory_id=factory.id))

    db.commit()
    db.refresh(user)
    return _serialize_user(user, db)


@router.patch("/{user_id}")
async def update_user(
    user_id: UUID,
    data: UserUpdateInput,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    if data.name is not None:
        user.name = data.name
    if data.role is not None:
        valid_roles = [r.value for r in UserRole]
        if data.role not in valid_roles:
            raise HTTPException(422, f"Invalid role '{data.role}'")
        old_role = user.role.value if hasattr(user.role, 'value') else str(user.role)
        if old_role != data.role:
            log_security_event(
                db,
                action="role_change",
                actor_id=str(current_user.id),
                actor_email=current_user.email,
                ip_address=request.client.host if request.client else None,
                target_entity="user",
                target_id=str(user_id),
                details={"old_role": old_role, "new_role": data.role, "user_email": user.email},
            )
        user.role = data.role
    if data.language is not None:
        valid_langs = [l.value for l in LanguagePreference]
        if data.language in valid_langs:
            user.language = data.language
    if data.telegram_user_id is not None:
        user.telegram_user_id = data.telegram_user_id

    # Sync factory assignments
    if data.factory_ids is not None:
        db.query(UserFactory).filter(UserFactory.user_id == user.id).delete()
        for fid in data.factory_ids:
            factory = db.query(Factory).filter(Factory.id == UUID(fid)).first()
            if factory:
                db.add(UserFactory(user_id=user.id, factory_id=factory.id))

    user.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return _serialize_user(user, db)


@router.post("/{user_id}/toggle-active")
async def toggle_user_active(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    # Prevent self-deactivation
    if user.id == current_user.id:
        raise HTTPException(400, "Cannot deactivate yourself")

    user.is_active = not user.is_active
    user.updated_at = datetime.now(timezone.utc)

    # If deactivating, revoke all sessions
    if not user.is_active:
        db.query(ActiveSession).filter(
            ActiveSession.user_id == user.id,
            ActiveSession.revoked == False,
        ).update({
            "revoked": True,
            "revoked_at": datetime.now(timezone.utc),
            "revoked_reason": "user_deactivated",
        })

    db.commit()
    db.refresh(user)
    return _serialize_user(user, db)


@router.post("/{user_id}/reset-password")
async def admin_reset_password(
    user_id: UUID,
    data: dict,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Admin resets another user's password."""
    from api.auth import hash_password

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    new_pw = data.get("new_password", "")
    if len(new_pw) < 10:
        raise HTTPException(422, "Password must be at least 10 characters")

    user.password_hash = hash_password(new_pw)
    user.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "ok", "message": f"Password reset for {user.email}"}


@router.post("/debug/fire-evening-summary")
async def debug_fire_evening_summary(
    data: dict | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Manually trigger `_send_evening_summary` for a factory — debugging only.

    Body: {"factory_id": "<uuid>"}  (defaults to the first factory the user
    has access to). Useful to verify owner DM delivery without waiting for
    18:00 local.
    """
    from api.scheduler import _send_evening_summary
    from api.models import Factory

    factory_id = (data or {}).get("factory_id") if data else None
    if factory_id:
        factory = db.query(Factory).filter(Factory.id == factory_id).first()
    else:
        factory = db.query(Factory).first()
    if not factory:
        raise HTTPException(404, "Factory not found")

    _send_evening_summary(db, factory)
    return {"status": "ok", "factory": factory.name}
