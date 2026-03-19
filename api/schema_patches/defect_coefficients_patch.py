"""
Schema patch for two-dimensional defect coefficient system.
Decision 2026-03-19.

Adds:
  - production_defects table (firing-level defect records for rolling average)
  - order_positions.glaze_type column
  - order_positions.defect_coeff_override column

Usage:
    from api.schema_patches.defect_coefficients_patch import apply_patch
    apply_patch(db_connection)
"""

import logging
import sqlalchemy as sa

logger = logging.getLogger("moonjar.schema_patches.defect_coefficients")

DEFECT_PATCH_SQL = [
    # production_defects — rolling history for dynamic coefficient calculation
    """CREATE TABLE IF NOT EXISTS production_defects (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        factory_id UUID NOT NULL REFERENCES factories(id),
        position_id UUID REFERENCES order_positions(id),
        glaze_type VARCHAR(50),
        product_type VARCHAR(50),
        total_quantity INTEGER NOT NULL,
        defect_quantity INTEGER NOT NULL,
        defect_pct NUMERIC(5,4),
        fired_at DATE NOT NULL DEFAULT CURRENT_DATE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )""",
    # Index for efficient 90-day rolling lookups per factory
    "CREATE INDEX IF NOT EXISTS idx_prod_defects_factory ON production_defects(factory_id, fired_at DESC)",
    # Index for position-level lookups
    "CREATE INDEX IF NOT EXISTS idx_prod_defects_position ON production_defects(position_id)",
    # Index for glaze-type aggregation queries
    "CREATE INDEX IF NOT EXISTS idx_prod_defects_glaze ON production_defects(factory_id, glaze_type, fired_at DESC)",
    # Index for product-type aggregation queries
    "CREATE INDEX IF NOT EXISTS idx_prod_defects_product ON production_defects(factory_id, product_type, fired_at DESC)",
    # order_positions — glaze_type for two-dimensional coefficient lookup
    "ALTER TABLE order_positions ADD COLUMN IF NOT EXISTS glaze_type VARCHAR(50)",
    # order_positions — manual override for combined defect coefficient (Owner/CEO)
    "ALTER TABLE order_positions ADD COLUMN IF NOT EXISTS defect_coeff_override NUMERIC(6,4)",
]


def apply_patch(db_connection) -> list[str]:
    """
    Apply schema patch for defect coefficient system.

    Accepts a raw SQLAlchemy connection (from engine.connect()) or Session.
    Returns list of SQL statements that were successfully executed.
    """
    executed: list[str] = []
    for sql in DEFECT_PATCH_SQL:
        try:
            db_connection.execute(sa.text(sql))
            executed.append(sql)
            logger.debug("Schema patch applied: %s", sql[:80])
        except Exception as exc:
            # Table/column/index already exists or other non-fatal error — skip
            logger.debug("Schema patch skipped (%s): %s", type(exc).__name__, sql[:80])
    return executed
