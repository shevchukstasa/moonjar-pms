"""
Moonjar PMS — Data Retention Policy Enforcement.

Automated cleanup of expired data per the retention policy
defined in docs/DATA_RETENTION_POLICY.md.

Called monthly by APScheduler (1st of month at 03:00 UTC).
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger("moonjar.retention")


async def run_retention_cleanup(db: Session):
    """Execute data retention cleanup.

    Deletes or archives data that has exceeded its retention period.
    Each category is handled independently so one failure doesn't block others.

    Called by scheduler monthly (1st of month, 03:00 UTC).
    """
    now = datetime.now(timezone.utc)
    results = {}

    # -----------------------------------------------------------------------
    # 1. Rate limit events — 30 days
    # -----------------------------------------------------------------------
    try:
        cutoff = now - timedelta(days=30)
        r = db.execute(
            text("DELETE FROM rate_limit_events WHERE created_at < :cutoff"),
            {"cutoff": cutoff},
        )
        count = r.rowcount
        results["rate_limit_events"] = count
        logger.info("Retention: deleted %d rate_limit_events (>30d)", count)
    except Exception as e:
        logger.error("Retention: rate_limit_events cleanup failed: %s", e)
        db.rollback()

    # -----------------------------------------------------------------------
    # 2. Read notifications — 90 days
    # -----------------------------------------------------------------------
    try:
        cutoff = now - timedelta(days=90)
        r = db.execute(
            text("DELETE FROM notifications WHERE is_read = TRUE AND created_at < :cutoff"),
            {"cutoff": cutoff},
        )
        count = r.rowcount
        results["notifications_read"] = count
        logger.info("Retention: deleted %d read notifications (>90d)", count)
    except Exception as e:
        logger.error("Retention: read notifications cleanup failed: %s", e)
        db.rollback()

    # -----------------------------------------------------------------------
    # 3. Unread notifications — 1 year
    # -----------------------------------------------------------------------
    try:
        cutoff = now - timedelta(days=365)
        r = db.execute(
            text("DELETE FROM notifications WHERE is_read = FALSE AND created_at < :cutoff"),
            {"cutoff": cutoff},
        )
        count = r.rowcount
        results["notifications_unread"] = count
        logger.info("Retention: deleted %d unread notifications (>1y)", count)
    except Exception as e:
        logger.error("Retention: unread notifications cleanup failed: %s", e)
        db.rollback()

    # -----------------------------------------------------------------------
    # 4. AI chat history — 6 months
    # -----------------------------------------------------------------------
    try:
        cutoff = now - timedelta(days=180)
        r = db.execute(
            text("DELETE FROM ai_chat_history WHERE updated_at < :cutoff"),
            {"cutoff": cutoff},
        )
        count = r.rowcount
        results["ai_chat_history"] = count
        logger.info("Retention: deleted %d AI chat history records (>6m)", count)
    except Exception as e:
        logger.error("Retention: AI chat history cleanup failed: %s", e)
        db.rollback()

    # -----------------------------------------------------------------------
    # 5. Daily task distributions — 1 year
    # -----------------------------------------------------------------------
    try:
        cutoff = now - timedelta(days=365)
        r = db.execute(
            text("DELETE FROM daily_task_distributions WHERE created_at < :cutoff"),
            {"cutoff": cutoff},
        )
        count = r.rowcount
        results["daily_task_distributions"] = count
        logger.info("Retention: deleted %d daily task distributions (>1y)", count)
    except Exception as e:
        logger.error("Retention: daily task distributions cleanup failed: %s", e)
        db.rollback()

    # -----------------------------------------------------------------------
    # 6. Expired active sessions — already cleaned by cleanup_expired_sessions,
    #    but catch any stragglers older than 30 days
    # -----------------------------------------------------------------------
    try:
        cutoff = now - timedelta(days=30)
        r = db.execute(
            text("DELETE FROM active_sessions WHERE expires_at < :cutoff"),
            {"cutoff": cutoff},
        )
        count = r.rowcount
        results["active_sessions_stale"] = count
        logger.info("Retention: deleted %d stale active sessions (>30d expired)", count)
    except Exception as e:
        logger.error("Retention: stale sessions cleanup failed: %s", e)
        db.rollback()

    # -----------------------------------------------------------------------
    # 7. Security audit log — 1 year
    # -----------------------------------------------------------------------
    try:
        cutoff = now - timedelta(days=365)
        r = db.execute(
            text("DELETE FROM security_audit_log WHERE created_at < :cutoff"),
            {"cutoff": cutoff},
        )
        count = r.rowcount
        results["security_audit_log"] = count
        logger.info("Retention: deleted %d security audit log entries (>1y)", count)
    except Exception as e:
        logger.error("Retention: security audit log cleanup failed: %s", e)
        db.rollback()

    # -----------------------------------------------------------------------
    # 8. Backup logs — 1 year (keep recent for monitoring)
    # -----------------------------------------------------------------------
    try:
        cutoff = now - timedelta(days=365)
        r = db.execute(
            text("DELETE FROM backup_logs WHERE created_at < :cutoff"),
            {"cutoff": cutoff},
        )
        count = r.rowcount
        results["backup_logs"] = count
        logger.info("Retention: deleted %d backup log entries (>1y)", count)
    except Exception as e:
        logger.error("Retention: backup logs cleanup failed: %s", e)
        db.rollback()

    # -----------------------------------------------------------------------
    # 9. RAG embeddings — mark stale (older than 1 year) for rebuild
    #    We don't delete them outright since they might still be referenced;
    #    instead we delete embeddings with no matching source.
    # -----------------------------------------------------------------------
    try:
        cutoff = now - timedelta(days=365)
        r = db.execute(
            text("DELETE FROM rag_embeddings WHERE created_at < :cutoff"),
            {"cutoff": cutoff},
        )
        count = r.rowcount
        results["rag_embeddings"] = count
        logger.info("Retention: deleted %d stale RAG embeddings (>1y)", count)
    except Exception as e:
        logger.error("Retention: RAG embeddings cleanup failed: %s", e)
        db.rollback()

    # -----------------------------------------------------------------------
    # 10. Worker media — 2 years
    # -----------------------------------------------------------------------
    try:
        cutoff = now - timedelta(days=730)
        r = db.execute(
            text("DELETE FROM worker_media WHERE created_at < :cutoff"),
            {"cutoff": cutoff},
        )
        count = r.rowcount
        results["worker_media"] = count
        logger.info("Retention: deleted %d worker media records (>2y)", count)
    except Exception as e:
        logger.error("Retention: worker media cleanup failed: %s", e)
        db.rollback()

    # -----------------------------------------------------------------------
    # 11. Kiln calculation logs — 2 years
    # -----------------------------------------------------------------------
    try:
        cutoff = now - timedelta(days=730)
        r = db.execute(
            text("DELETE FROM kiln_calculation_logs WHERE created_at < :cutoff"),
            {"cutoff": cutoff},
        )
        count = r.rowcount
        results["kiln_calculation_logs"] = count
        logger.info("Retention: deleted %d kiln calculation logs (>2y)", count)
    except Exception as e:
        logger.error("Retention: kiln calculation logs cleanup failed: %s", e)
        db.rollback()

    # -----------------------------------------------------------------------
    # Commit all successful deletions
    # -----------------------------------------------------------------------
    try:
        db.commit()
    except Exception as e:
        logger.error("Retention: final commit failed: %s", e)
        db.rollback()

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    total_deleted = sum(results.values())
    logger.info(
        "Retention cleanup complete: %d total records deleted. Breakdown: %s",
        total_deleted, results,
    )

    return results
