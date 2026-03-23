"""
Schema patch: add productivity norm columns to process_steps + is_setup to standard_work.
Idempotent — safe to run on every startup.
"""
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)

STATEMENTS = [
    # ProcessStep — productivity norms
    "ALTER TABLE process_steps ADD COLUMN IF NOT EXISTS productivity_rate NUMERIC(10,2)",
    "ALTER TABLE process_steps ADD COLUMN IF NOT EXISTS productivity_unit VARCHAR(50)",
    "ALTER TABLE process_steps ADD COLUMN IF NOT EXISTS measurement_basis VARCHAR(50)",
    "ALTER TABLE process_steps ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true",
    "ALTER TABLE process_steps ADD COLUMN IF NOT EXISTS notes TEXT",
    # StandardWork — setup vs productive flag
    "ALTER TABLE standard_work ADD COLUMN IF NOT EXISTS is_setup BOOLEAN NOT NULL DEFAULT false",
]


def apply(conn):
    """Apply schema patch."""
    for stmt in STATEMENTS:
        try:
            conn.execute(text(stmt))
        except Exception as e:
            logger.debug("process_steps patch: %s — %s", stmt[:60], e)
    # No explicit commit — engine.begin() auto-commits
    logger.info("Schema patch applied: process_steps productivity norms")
