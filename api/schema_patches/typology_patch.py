"""
Schema patch: Kiln Loading Typologies + per-kiln capacity.
Idempotent — safe to run on every startup.
"""
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)

STATEMENTS = [
    # Kiln Loading Typologies — named configurations that define capacity
    """
    CREATE TABLE IF NOT EXISTS kiln_loading_typologies (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        factory_id UUID NOT NULL REFERENCES factories(id),
        name VARCHAR(200) NOT NULL,
        product_types JSONB NOT NULL DEFAULT '[]'::JSONB,
        place_of_application JSONB NOT NULL DEFAULT '[]'::JSONB,
        collections JSONB NOT NULL DEFAULT '[]'::JSONB,
        methods JSONB NOT NULL DEFAULT '[]'::JSONB,
        min_size_cm NUMERIC(8,2),
        max_size_cm NUMERIC(8,2),
        preferred_loading VARCHAR(20) NOT NULL DEFAULT 'auto',
        min_firing_temp INTEGER,
        max_firing_temp INTEGER,
        shift_count INTEGER NOT NULL DEFAULT 2,
        auto_calibrate BOOLEAN NOT NULL DEFAULT false,
        is_active BOOLEAN NOT NULL DEFAULT true,
        priority INTEGER NOT NULL DEFAULT 0,
        notes TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,

    # Pre-computed capacity per kiln per typology
    """
    CREATE TABLE IF NOT EXISTS kiln_typology_capacities (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        typology_id UUID NOT NULL REFERENCES kiln_loading_typologies(id) ON DELETE CASCADE,
        resource_id UUID NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
        capacity_sqm NUMERIC(10,3),
        capacity_pcs INTEGER,
        loading_method VARCHAR(20),
        num_levels INTEGER DEFAULT 1,
        ref_size VARCHAR(20),
        ref_thickness_mm NUMERIC(6,2) DEFAULT 11,
        ref_shape VARCHAR(20) DEFAULT 'rectangle',
        ai_adjusted_sqm NUMERIC(10,3),
        calibration_ema NUMERIC(10,3),
        last_calibrated_at TIMESTAMPTZ,
        calculated_at TIMESTAMPTZ DEFAULT now(),
        calculation_input JSONB,
        calculation_output JSONB,
        UNIQUE(typology_id, resource_id)
    )
    """,

    "CREATE INDEX IF NOT EXISTS idx_typology_factory ON kiln_loading_typologies (factory_id, is_active)",
    "CREATE INDEX IF NOT EXISTS idx_typology_cap_lookup ON kiln_typology_capacities (typology_id, resource_id)",

    # Zone column for mixed loading support
    "ALTER TABLE kiln_typology_capacities ADD COLUMN IF NOT EXISTS zone VARCHAR(20) NOT NULL DEFAULT 'primary'",
]


def apply(conn):
    """Apply schema patch."""
    for stmt in STATEMENTS:
        try:
            conn.execute(text(stmt))
        except Exception as e:
            logger.debug("typology patch: %s — %s", stmt[:60], e)
    logger.info("Schema patch applied: kiln_loading_typologies + kiln_typology_capacities")
