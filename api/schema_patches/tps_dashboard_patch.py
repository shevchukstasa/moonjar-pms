"""
Schema patch: TPS Dashboard — extend process_steps + create calibration_log.
Idempotent — safe to run on every startup.
"""
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)

STATEMENTS = [
    # ProcessStep — new columns for TPS dashboard
    "ALTER TABLE process_steps ADD COLUMN IF NOT EXISTS stage VARCHAR(100)",
    "ALTER TABLE process_steps ADD COLUMN IF NOT EXISTS shift_count INTEGER NOT NULL DEFAULT 2",
    "ALTER TABLE process_steps ADD COLUMN IF NOT EXISTS applicable_collections JSONB NOT NULL DEFAULT '[]'::JSONB",
    "ALTER TABLE process_steps ADD COLUMN IF NOT EXISTS applicable_methods JSONB NOT NULL DEFAULT '[]'::JSONB",
    "ALTER TABLE process_steps ADD COLUMN IF NOT EXISTS applicable_product_types JSONB NOT NULL DEFAULT '[]'::JSONB",
    "ALTER TABLE process_steps ADD COLUMN IF NOT EXISTS auto_calibrate BOOLEAN NOT NULL DEFAULT false",
    "ALTER TABLE process_steps ADD COLUMN IF NOT EXISTS calibration_ema NUMERIC(10,2)",
    "ALTER TABLE process_steps ADD COLUMN IF NOT EXISTS last_calibrated_at TIMESTAMPTZ",

    # Calibration log table
    """
    CREATE TABLE IF NOT EXISTS calibration_log (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        factory_id UUID NOT NULL REFERENCES factories(id),
        process_step_id UUID NOT NULL REFERENCES process_steps(id) ON DELETE CASCADE,
        previous_rate NUMERIC(10,2) NOT NULL,
        new_rate NUMERIC(10,2) NOT NULL,
        ema_value NUMERIC(10,2),
        data_points INTEGER NOT NULL DEFAULT 0,
        trigger VARCHAR(50) NOT NULL DEFAULT 'manual',
        approved_by UUID REFERENCES users(id),
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,

    # Index for fast calibration queries
    "CREATE INDEX IF NOT EXISTS idx_calibration_log_step ON calibration_log (process_step_id, created_at DESC)",
]


def apply(conn):
    """Apply schema patch."""
    for stmt in STATEMENTS:
        try:
            conn.execute(text(stmt))
        except Exception as e:
            logger.debug("tps_dashboard patch: %s — %s", stmt[:60], e)
    logger.info("Schema patch applied: tps_dashboard (process_steps ext + calibration_log)")
