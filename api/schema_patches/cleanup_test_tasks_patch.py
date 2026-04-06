"""One-time cleanup: delete E2E test tasks and duplicates."""
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)


def apply(conn) -> None:
    try:
        # Count before
        before = conn.execute(text("SELECT COUNT(*) FROM tasks")).scalar()

        # Delete E2E test tasks
        r1 = conn.execute(text("""
            DELETE FROM tasks WHERE description LIKE '%%E2E%%'
        """))
        logger.warning("CLEANUP_TASKS | Deleted %d E2E tasks", r1.rowcount)
        print(f"CLEANUP_TASKS | Deleted {r1.rowcount} E2E tasks")

        # Delete test tasks by exact description
        r2 = conn.execute(text("""
            DELETE FROM tasks WHERE description IN ('Test task', 'Test with role', 'Test repair SLA task')
        """))
        logger.warning("CLEANUP_TASKS | Deleted %d test tasks", r2.rowcount)
        print(f"CLEANUP_TASKS | Deleted {r2.rowcount} test tasks")

        after = conn.execute(text("SELECT COUNT(*) FROM tasks")).scalar()
        logger.warning("CLEANUP_TASKS | Before=%d After=%d", before, after)
        print(f"CLEANUP_TASKS | Before={before} After={after}")

    except Exception as e:
        logger.error("CLEANUP_TASKS FAILED: %s", e)
        print(f"CLEANUP_TASKS FAILED: {e}")
        raise
