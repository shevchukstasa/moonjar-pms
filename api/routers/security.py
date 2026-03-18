"""Security router — audit log, sessions, IP allowlist, TOTP 2FA management.
See API_CONTRACTS.md for full specification.
"""

import logging
import secrets
from uuid import UUID
from datetime import datetime, timedelta, timezone

import pyotp
from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func

from api.config import get_settings
from api.database import get_db
from api.auth import get_current_user, log_security_event, hash_password, verify_password
from api.roles import require_admin
from api.models import SecurityAuditLog, ActiveSession, IpAllowlist, User, TotpBackupCode
from api.enums import AuditActionType, IpScope

router = APIRouter()
logger = logging.getLogger("moonjar.security")

# ---------------------------------------------------------------------------
# TOTP encryption helpers
# ---------------------------------------------------------------------------

def _get_fernet() -> Fernet:
    """Build Fernet cipher from TOTP_ENCRYPTION_KEY.

    The config value is a passphrase-style string. We pad/truncate it to
    exactly 32 bytes then base64-encode, which is what Fernet expects.
    """
    import base64
    key_bytes = get_settings().TOTP_ENCRYPTION_KEY.encode("utf-8")
    # Pad or truncate to 32 bytes
    key_bytes = key_bytes.ljust(32, b"\0")[:32]
    return Fernet(base64.urlsafe_b64encode(key_bytes))


def _encrypt_totp_secret(secret: str) -> str:
    return _get_fernet().encrypt(secret.encode("utf-8")).decode("utf-8")


def _decrypt_totp_secret(encrypted: str) -> str:
    return _get_fernet().decrypt(encrypted.encode("utf-8")).decode("utf-8")


def _generate_backup_codes(count: int = 10) -> list[str]:
    """Generate human-readable backup codes (8 hex chars each)."""
    return [secrets.token_hex(6).upper() for _ in range(count)]


def _hash_backup_code(code: str) -> str:
    """Hash a backup code using bcrypt (same as passwords)."""
    return hash_password(code.upper())


def _verify_backup_code(code: str, hashed: str) -> bool:
    """Verify a backup code against its hash."""
    return verify_password(code.upper(), hashed)


def _verify_totp_or_backup(
    db: Session,
    user: User,
    code: str,
) -> tuple[bool, str]:
    """Verify a code as either TOTP or backup code.

    Returns (valid, method) where method is 'totp' or 'backup'.
    """
    # Try TOTP first
    if user.totp_secret_encrypted:
        try:
            secret = _decrypt_totp_secret(user.totp_secret_encrypted)
            totp = pyotp.TOTP(secret)
            if totp.verify(code, valid_window=1):
                return True, "totp"
        except Exception:
            pass

    # Try backup codes
    unused_codes = db.query(TotpBackupCode).filter(
        TotpBackupCode.user_id == user.id,
        TotpBackupCode.used.is_(False),
    ).all()
    for bc in unused_codes:
        if _verify_backup_code(code, bc.code_hash):
            bc.used = True
            bc.used_at = datetime.now(timezone.utc)
            db.flush()
            return True, "backup"

    return False, ""


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class IpAllowlistCreate(BaseModel):
    cidr: str
    scope: str = "admin_panel"
    description: str = ""


class TOTPCodeRequest(BaseModel):
    code: str


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
        try:
            date_to_end = datetime.strptime(date_to, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, tzinfo=timezone.utc
            )
        except (ValueError, TypeError):
            date_to_end = date_to  # fallback to raw string for backwards compat
        q = q.filter(SecurityAuditLog.created_at <= date_to_end)

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


# --- TOTP 2FA Management ---

@router.post("/totp/setup")
async def totp_setup(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Begin TOTP setup: generate secret, provisioning URI, and backup codes.

    Does NOT enable 2FA yet — the user must call /totp/verify with a valid
    code from their authenticator app to confirm setup.
    """
    if current_user.totp_enabled:
        raise HTTPException(400, "TOTP is already enabled. Disable it first to re-setup.")

    # Generate TOTP secret
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=current_user.email,
        issuer_name="Moonjar PMS",
    )

    # Encrypt and store (not yet enabled — user must verify first)
    current_user.totp_secret_encrypted = _encrypt_totp_secret(secret)
    current_user.totp_enabled = False

    # Delete any existing backup codes for this user
    db.query(TotpBackupCode).filter(TotpBackupCode.user_id == current_user.id).delete()

    # Generate and store backup codes
    backup_codes = _generate_backup_codes(10)
    for code in backup_codes:
        db.add(TotpBackupCode(
            user_id=current_user.id,
            code_hash=_hash_backup_code(code),
        ))

    db.commit()

    logger.info(f"TOTP setup initiated for user {current_user.email}")

    return {
        "provisioning_uri": provisioning_uri,
        "backup_codes": backup_codes,
        "message": "Scan the QR code with your authenticator app, then call /totp/verify with a code to activate.",
    }


@router.post("/totp/verify")
async def totp_verify(
    data: TOTPCodeRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Verify a TOTP code to confirm setup and enable 2FA.

    Must be called after /totp/setup. Accepts only a TOTP code (not backup codes)
    to ensure the user has properly configured their authenticator app.
    """
    if current_user.totp_enabled:
        raise HTTPException(400, "TOTP is already enabled")

    if not current_user.totp_secret_encrypted:
        raise HTTPException(400, "No TOTP setup in progress. Call /totp/setup first.")

    # Verify the code against the stored secret (TOTP only, not backup)
    try:
        secret = _decrypt_totp_secret(current_user.totp_secret_encrypted)
    except Exception:
        raise HTTPException(500, "Failed to decrypt TOTP secret. Re-run /totp/setup.")

    totp = pyotp.TOTP(secret)
    if not totp.verify(data.code, valid_window=1):
        raise HTTPException(400, "Invalid TOTP code. Check your authenticator app and try again.")

    # Enable 2FA
    current_user.totp_enabled = True
    db.commit()

    # Audit log
    log_security_event(
        db,
        AuditActionType.TOTP_SETUP,
        actor_id=str(current_user.id),
        actor_email=current_user.email,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        target_entity="user",
        target_id=str(current_user.id),
    )

    logger.info(f"TOTP enabled for user {current_user.email}")

    return {"message": "Two-factor authentication enabled successfully"}


@router.post("/totp/disable")
async def totp_disable(
    data: TOTPCodeRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Disable TOTP 2FA. Requires a valid TOTP code or backup code."""
    if not current_user.totp_enabled:
        raise HTTPException(400, "TOTP is not enabled")

    # Verify the code (TOTP or backup)
    valid, method = _verify_totp_or_backup(db, current_user, data.code)
    if not valid:
        raise HTTPException(400, "Invalid code. Provide a valid TOTP or backup code.")

    # Disable 2FA and clear secret
    current_user.totp_enabled = False
    current_user.totp_secret_encrypted = None

    # Delete all backup codes
    db.query(TotpBackupCode).filter(TotpBackupCode.user_id == current_user.id).delete()

    db.commit()

    # Audit log
    log_security_event(
        db,
        AuditActionType.TOTP_DISABLE,
        actor_id=str(current_user.id),
        actor_email=current_user.email,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        target_entity="user",
        target_id=str(current_user.id),
        details={"method": method},
    )

    logger.info(f"TOTP disabled for user {current_user.email} (verified via {method})")

    return {"message": "Two-factor authentication disabled"}


@router.get("/totp/status")
async def totp_status(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Check whether TOTP 2FA is enabled for the current user."""
    backup_count = 0
    if current_user.totp_enabled:
        backup_count = db.query(TotpBackupCode).filter(
            TotpBackupCode.user_id == current_user.id,
            TotpBackupCode.used.is_(False),
        ).count()

    return {
        "totp_enabled": current_user.totp_enabled,
        "backup_codes_remaining": backup_count,
    }


@router.post("/totp/backup-codes/regenerate")
async def totp_regenerate_backup_codes(
    data: TOTPCodeRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Regenerate backup codes. Requires a valid TOTP code. Old codes are invalidated."""
    if not current_user.totp_enabled:
        raise HTTPException(400, "TOTP is not enabled")

    # Verify with TOTP code only (not backup) to prevent chicken-and-egg
    if not current_user.totp_secret_encrypted:
        raise HTTPException(500, "TOTP secret missing")
    try:
        secret = _decrypt_totp_secret(current_user.totp_secret_encrypted)
    except Exception:
        raise HTTPException(500, "Failed to decrypt TOTP secret")

    totp = pyotp.TOTP(secret)
    if not totp.verify(data.code, valid_window=1):
        raise HTTPException(400, "Invalid TOTP code")

    # Delete old backup codes
    db.query(TotpBackupCode).filter(TotpBackupCode.user_id == current_user.id).delete()

    # Generate new ones
    backup_codes = _generate_backup_codes(10)
    for code in backup_codes:
        db.add(TotpBackupCode(
            user_id=current_user.id,
            code_hash=_hash_backup_code(code),
        ))

    db.commit()

    logger.info(f"Backup codes regenerated for user {current_user.email}")

    return {
        "backup_codes": backup_codes,
        "message": "New backup codes generated. Previous codes are now invalid.",
    }
