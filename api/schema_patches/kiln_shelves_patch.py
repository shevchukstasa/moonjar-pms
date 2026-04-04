"""Create kiln_shelves table.

Tracks kiln shelves (fire-resistant platforms) with dimensions,
linked to specific kilns. Supports write-off with reason and photo.
"""
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)

STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS kiln_shelves (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        resource_id UUID NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
        factory_id UUID NOT NULL REFERENCES factories(id),
        name VARCHAR(200) NOT NULL,
        length_cm NUMERIC(8, 2) NOT NULL,
        width_cm NUMERIC(8, 2) NOT NULL,
        thickness_mm NUMERIC(6, 2) NOT NULL DEFAULT 15,
        material VARCHAR(100) DEFAULT 'silicon_carbide',
        area_sqm NUMERIC(10, 4) GENERATED ALWAYS AS (length_cm * width_cm / 10000.0) STORED,
        status VARCHAR(30) NOT NULL DEFAULT 'active',
        condition_notes TEXT,
        write_off_reason TEXT,
        write_off_photo_url VARCHAR(500),
        written_off_at TIMESTAMPTZ,
        written_off_by UUID REFERENCES users(id),
        purchase_date DATE,
        purchase_cost NUMERIC(10, 2),
        firing_cycles_count INTEGER DEFAULT 0,
        max_firing_cycles INTEGER,
        is_active BOOLEAN NOT NULL DEFAULT true,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_kiln_shelves_resource ON kiln_shelves (resource_id, is_active)",
    "CREATE INDEX IF NOT EXISTS idx_kiln_shelves_factory ON kiln_shelves (factory_id, status)",
]


def apply(conn):
    for stmt in STATEMENTS:
        try:
            conn.execute(text(stmt))
        except Exception as e:
            logger.debug("kiln_shelves patch: %s — %s", stmt[:60], e)
    logger.info("Schema patch applied: kiln_shelves")
