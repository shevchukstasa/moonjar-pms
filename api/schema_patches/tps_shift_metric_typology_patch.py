"""
Schema patch: Add typology_id column to tps_shift_metrics.

Allows linking shift metrics to a specific kiln loading typology
for per-typology calibration of processing speeds.

Idempotent — safe to run on every startup.
"""
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)

STATEMENTS = [
    # Add typology_id FK column
    """
    ALTER TABLE tps_shift_metrics
    ADD COLUMN IF NOT EXISTS typology_id UUID
    REFERENCES kiln_loading_typologies(id) ON DELETE SET NULL
    """,

    # Index for calibration queries: factory + stage + typology + date
    """
    CREATE INDEX IF NOT EXISTS idx_tps_shift_metrics_typology
    ON tps_shift_metrics (factory_id, stage, typology_id, date)
    WHERE typology_id IS NOT NULL
    """,
]


def apply(conn):
    """Apply schema patch."""
    for stmt in STATEMENTS:
        try:
            conn.execute(text(stmt))
        except Exception as e:
            logger.debug("tps_shift_metric_typology patch: %s — %s", stmt[:60], e)
    logger.info("Schema patch applied: tps_shift_metrics.typology_id")
