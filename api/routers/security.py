"""Security router — audit log, sessions, IP allowlist.
See API_CONTRACTS.md for full specification.
"""

from uuid import UUID
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func

from api.database import get_db
from api.auth import get_current_user
from api.roles import require_admin
from api.models import SecurityAuditLog, ActiveSession, IpAllowlist, User
from api.enums import AuditActionType, IpScope

router = APIRouter()


class IpAllowlistCreate(BaseModel):
    cidr: str
    scope: str = "admin_panel"
    description: str = ""


# --- Audit Log ---

@router.get("/audit-log")
async def list_audit_log(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    action: str | None = None,
    actor_id: UUID | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Paginated, filterable audit log."""
    q = db.query(SecurityAuditLog).order_by(SecurityAuditLog.created_at.desc())

    if action:
        q = q.filter(SecurityAuditLog.action == action)
    if actor_id:
        q = q.filter(SecurityAuditLog.actor_id == actor_id)
    if date_from:
        q = q.filter(SecurityAuditLog.created_at >= date_from)
    if date_to:
        q = q.filter(SecurityAuditLog.created_at <= date_to + " 23:59:59")

    total = q.count()
    items = q.offset((page - 1) * per_page).limit(per_page).all()

    return {
        "items": [
            {
                "id": str(item.id),
                "action": item.action if isinstance(item.action, str) else item.action.value,
                "actor_id": str(item.actor_id) if item.actor_id else None,
                "actor_email": item.actor_email,
                "ip_address": str(item.ip_address) if item.ip_address else None,
                "user_agent": item.user_agent,
                "target_entity": item.target_entity,
                "target_id": str(item.target_id) if item.target_id else None,
                "details": item.details,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in items
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/audit-log/summary")
async def audit_log_summary(
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Audit log summary: failed logins, unique IPs, anomalies."""
    now = datetime.utcnow()
    last_24h = now - timedelta(hours=24)

    # Failed logins in last 24h
    failed_logins = db.query(sa_func.count(SecurityAuditLog.id)).filter(
        SecurityAuditLog.action == AuditActionType.LOGIN_FAILED.value,
        SecurityAuditLog.created_at >= last_24h,
    ).scalar() or 0

    # Unique IPs in last 24h
    unique_ips = db.query(
        sa_func.count(sa_func.distinct(SecurityAuditLog.ip_address))
    ).filter(
        SecurityAuditLog.created_at >= last_24h,
    ).scalar() or 0

    # Total events in last 24h
    total_events = db.query(sa_func.count(SecurityAuditLog.id)).filter(
        SecurityAuditLog.created_at >= last_24h,
    ).scalar() or 0

    # Anomalies: >5 failed logins from same IP
    anomaly_ips = db.query(
        SecurityAuditLog.ip_address,
        sa_func.count(SecurityAuditLog.id).label("count"),
    ).filter(
        SecurityAuditLog.action == AuditActionType.LOGIN_FAILED.value,
        SecurityAuditLog.created_at >= last_24h,
    ).group_by(
        SecurityAuditLog.ip_address
    ).having(
        sa_func.count(SecurityAuditLog.id) > 5
    ).all()

    anomalies = [
        {"ip_address": str(row.ip_address), "failed_attempts": row.count}
        for row in anomaly_ips
    ]

    return {
        "failed_logins_24h": failed_logins,
        "unique_ips_24h": unique_ips,
        "total_events_24h": total_events,
        "anomalies": anomalies,
    }


# --- Sessions ---

@router.get("/sessions")
async def list_active_sessions(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    user_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List active sessions. Admins see all, users see own."""
    q = db.query(ActiveSession).filter(
        ActiveSession.revoked.is_(False),
        ActiveSession.expires_at > datetime.utcnow(),
    ).order_by(ActiveSession.created_at.desc())

    # Non-admin users can only see their own sessions
    if current_user.role not in ("owner", "administrator"):
        q = q.filter(ActiveSession.user_id == current_user.id)
    elif user_id:
        q = q.filter(ActiveSession.user_id == user_id)

    total = q.count()
    items = q.offset((page - 1) * per_page).limit(per_page).all()

    return {
        "items": [
            {
                "id": str(s.id),
                "user_id": str(s.user_id),
                "ip_address": str(s.ip_address) if s.ip_address else None,
                "user_agent": s.user_agent,
                "device_label": s.device_label,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "expires_at": s.expires_at.isoformat() if s.expires_at else None,
            }
            for s in items
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Revoke a specific session."""
    session = db.query(ActiveSession).filter(ActiveSession.id == session_id).first()
    if not session:
        raise HTTPException(404, "Session not found")

    # Non-admin users can only revoke their own sessions
    if current_user.role not in ("owner", "administrator") and session.user_id != current_user.id:
        raise HTTPException(403, "Cannot revoke another user's session")

    session.revoked = True
    session.revoked_at = datetime.utcnow()
    session.revoked_reason = "manual_revoke"
    db.commit()

    return {"message": "Session revoked"}


@router.delete("/sessions")
async def revoke_all_other_sessions(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Revoke all other sessions for the current user."""
    # Get current session JTI from token (if available)
    sessions = db.query(ActiveSession).filter(
        ActiveSession.user_id == current_user.id,
        ActiveSession.revoked.is_(False),
        ActiveSession.expires_at > datetime.utcnow(),
    ).all()

    revoked = 0
    for s in sessions:
        # Keep the most recent session (likely current)
        pass

    # Revoke all except the most recent
    if len(sessions) > 1:
        # Sort by created_at, keep the latest
        sorted_sessions = sorted(sessions, key=lambda x: x.created_at or datetime.min)
        for s in sorted_sessions[:-1]:
            s.revoked = True
            s.revoked_at = datetime.utcnow()
            s.revoked_reason = "revoke_all_others"
            revoked += 1

    db.commit()
    return {"message": f"Revoked {revoked} sessions"}


# --- IP Allowlist ---

@router.get("/ip-allowlist")
async def list_ip_allowlist(
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """List IP allowlist entries."""
    items = db.query(IpAllowlist).filter(IpAllowlist.is_active.is_(True)).all()
    return {
        "items": [
            {
                "id": str(item.id),
                "cidr": str(item.cidr),
                "scope": item.scope if isinstance(item.scope, str) else item.scope.value,
                "description": item.description,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in items
        ],
    }


@router.post("/ip-allowlist", status_code=201)
async def add_ip_to_allowlist(
    data: IpAllowlistCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Add IP to allowlist."""
    entry = IpAllowlist(
        cidr=data.cidr,
        scope=data.scope,
        description=data.description,
        created_by=current_user.id,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {
        "id": str(entry.id),
        "cidr": str(entry.cidr),
        "scope": entry.scope if isinstance(entry.scope, str) else entry.scope.value,
        "description": entry.description,
    }


@router.delete("/ip-allowlist/{entry_id}")
async def remove_ip_from_allowlist(
    entry_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Remove IP from allowlist (soft delete)."""
    entry = db.query(IpAllowlist).filter(IpAllowlist.id == entry_id).first()
    if not entry:
        raise HTTPException(404, "IP allowlist entry not found")
    entry.is_active = False
    db.commit()
    return {"message": "IP removed from allowlist"}
