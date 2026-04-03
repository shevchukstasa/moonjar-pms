"""
Schema patch: Stage Typology Speeds — production speed per (stage x typology).
Idempotent — safe to run on every startup.
"""
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)

STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS stage_typology_speeds (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        factory_id UUID NOT NULL REFERENCES factories(id) ON DELETE CASCADE,
        typology_id UUID NOT NULL REFERENCES kiln_loading_typologies(id) ON DELETE CASCADE,
        stage VARCHAR(100) NOT NULL,
        productivity_rate NUMERIC(10,2) NOT NULL,
        rate_unit VARCHAR(20) NOT NULL DEFAULT 'pcs',
        rate_basis VARCHAR(20) NOT NULL DEFAULT 'per_person',
        time_unit VARCHAR(20) NOT NULL DEFAULT 'hour',
        shift_count INTEGER DEFAULT 2,
        shift_duration_hours NUMERIC(4,1) DEFAULT 8.0,
        brigade_size INTEGER DEFAULT 1,
        auto_calibrate BOOLEAN DEFAULT false,
        calibration_ema NUMERIC(10,2),
        last_calibrated_at TIMESTAMPTZ,
        notes TEXT,
        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ DEFAULT now(),
        UNIQUE(typology_id, stage)
    )
    """,

    "CREATE INDEX IF NOT EXISTS idx_stage_typology_speeds_lookup ON stage_typology_speeds (typology_id, stage)",
    "CREATE INDEX IF NOT EXISTS idx_stage_typology_speeds_factory ON stage_typology_speeds (factory_id)",
]


def apply(conn):
    """Apply schema patch."""
    for stmt in STATEMENTS:
        try:
            conn.execute(text(stmt))
        except Exception as e:
            logger.debug("stage_typology_speeds patch: %s — %s", stmt[:60], e)
    logger.info("Schema patch applied: stage_typology_speeds")
