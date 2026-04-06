"""One-time cleanup: delete E2E test tasks and duplicates.

Removes tasks matching:
- description containing 'E2E' (test data)
- description = 'Test task' or 'Test with role' or 'Test repair SLA task'
- duplicate repair_sla_alert tasks

Keeps all real tasks (recipe_configuration, consumption_measurement, INVESTIGATE, etc.)
"""
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)


def apply(conn) -> None:
    # Delete test tasks
    result = conn.execute(text("""
        DELETE FROM tasks
        WHERE description LIKE '%E2E%'
           OR description IN ('Test task', 'Test with role', 'Test repair SLA task')
    """))
    logger.info("CLEANUP_TASKS | Deleted %d test/E2E tasks", result.rowcount)
