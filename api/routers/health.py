"""Health check router."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from api.database import get_db

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "moonjar-pms"}


@router.get("/debug/triggers")
async def debug_triggers(db: Session = Depends(get_db)):
    """Temporary endpoint to inspect DB triggers. Remove after debugging."""
    result = db.execute(text("""
        SELECT pg_get_functiondef(oid)
        FROM pg_proc
        WHERE proname = 'compute_order_status'
    """))
    compute_fn = [row[0] for row in result]

    result2 = db.execute(text("""
        SELECT pg_get_functiondef(oid)
        FROM pg_proc
        WHERE proname = 'trigger_update_order_status'
    """))
    trigger_fn = [row[0] for row in result2]

    result3 = db.execute(text("""
        SELECT tgname, tgtype, pg_get_triggerdef(oid)
        FROM pg_trigger
        WHERE tgrelid = 'order_positions'::regclass
        AND NOT tgisinternal
    """))
    triggers = [{"name": row[0], "type": row[1], "definition": row[2]} for row in result3]

    return {
        "compute_order_status": compute_fn,
        "trigger_update_order_status": trigger_fn,
        "triggers_on_order_positions": triggers,
    }
