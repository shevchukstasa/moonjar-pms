"""Create scheduler_configs table.

Per-factory scheduler configuration for configurable buffer days
and auto-buffer based on historical delays.
"""
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)

STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS scheduler_configs (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        factory_id UUID NOT NULL UNIQUE REFERENCES factories(id) ON DELETE CASCADE,
        pre_kiln_buffer_days INTEGER NOT NULL DEFAULT 1,
        post_kiln_buffer_days INTEGER NOT NULL DEFAULT 1,
        auto_buffer BOOLEAN NOT NULL DEFAULT false,
        auto_buffer_multiplier NUMERIC(4, 2) NOT NULL DEFAULT 1.5,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_by UUID REFERENCES users(id) ON DELETE SET NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_scheduler_configs_factory ON scheduler_configs (factory_id)",
]


def apply(conn):
    for stmt in STATEMENTS:
        try:
            conn.execute(text(stmt))
        except Exception as e:
            logger.debug("scheduler_config patch: %s — %s", stmt[:60], e)
    logger.info("Schema patch applied: scheduler_configs")
