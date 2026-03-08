"""Health check & internal cron endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.database import get_db

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "moonjar-pms"}


@router.get("/internal/poll-pms-status")
async def poll_pms_status(db: Session = Depends(get_db)):
    """
    Cloud Scheduler keep-alive / status polling endpoint.
    Called every 30 min by GCP Scheduler to:
    - Keep Cloud Run instance warm
    - Verify DB connectivity
    - Return basic system health metrics
    """
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
