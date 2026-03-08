"""Health check & internal cron endpoints."""

import os
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from api.database import get_db
from api.config import get_settings

logger = logging.getLogger("moonjar.health")
router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "moonjar-pms"}


def _verify_internal_auth(request: Request) -> None:
    """Verify internal endpoint access via ADMIN_IP_ALLOWLIST or X-Internal-Key header.

    In production, requires either:
    - X-Internal-Key header matching OWNER_KEY (for Cloud Scheduler)
    - Client IP in ADMIN_IP_ALLOWLIST
    In dev mode, access is open.
    """
    is_production = bool(
        os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("ENV", "").lower() == "production"
    )
    if not is_production:
        return  # Open in dev mode

    settings = get_settings()

    # Check X-Internal-Key header
    internal_key = request.headers.get("X-Internal-Key")
    if internal_key and settings.OWNER_KEY and internal_key == settings.OWNER_KEY:
        return

    # Check IP allowlist
    if settings.ADMIN_IP_ALLOWLIST:
        allowed_ips = {ip.strip() for ip in settings.ADMIN_IP_ALLOWLIST.split(",") if ip.strip()}
        client_ip = request.client.host if request.client else None
        if client_ip and client_ip in allowed_ips:
            return

    logger.warning(
        f"Unauthorized internal endpoint access from {request.client.host if request.client else 'unknown'}"
    )
    raise HTTPException(403, "Forbidden")


@router.get("/internal/poll-pms-status")
async def poll_pms_status(request: Request, db: Session = Depends(get_db)):
    """
    Cloud Scheduler keep-alive / status polling endpoint.
    Called every 30 min by GCP Scheduler to:
    - Keep Cloud Run instance warm
    - Verify DB connectivity
    - Return basic system health metrics

    Protected by X-Internal-Key header or IP allowlist in production.
    """
    _verify_internal_auth(request)

    try:
        # Quick DB connectivity check
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    return {
        "status": "ok" if db_ok else "degraded",
        "service": "moonjar-pms",
        "db": "connected" if db_ok else "unreachable",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
