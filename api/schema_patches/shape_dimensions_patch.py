"""
Schema patch for shape_dimensions JSONB column and new ShapeType enum values.

Adds shape_dimensions column to order_positions and production_order_items.
Also adds new shape enum values for the universal shape system (12 shapes).

Called from _ensure_schema (main.py) or applied manually.

Usage:
    from api.schema_patches.shape_dimensions_patch import apply_patch
    apply_patch(db_connection)
"""

import logging
import sqlalchemy as sa

logger = logging.getLogger("moonjar.schema_patches.shape_dimensions")

SHAPE_DIMENSIONS_PATCH_SQL = [
    # ── Add shape_dimensions JSONB column to order_positions ─────────────
    "ALTER TABLE order_positions ADD COLUMN IF NOT EXISTS shape_dimensions JSONB",

    # ── Add shape_dimensions JSONB column to production_order_items ──────
    "ALTER TABLE production_order_items ADD COLUMN IF NOT EXISTS shape_dimensions JSONB",

    # ── Add shape_dimensions JSONB column to sizes ───────────────────────
    # The Size model has declared this column since the universal shape
    # system landed, but the prod table missed it — every PATCH that tried
    # to set shape_dimensions silently dropped the field on commit.
    "ALTER TABLE sizes ADD COLUMN IF NOT EXISTS shape_dimensions JSONB",

    # ── Add new ShapeType enum values ────────────────────────────────────
    # PostgreSQL enums need explicit ALTER TYPE for new values.
    # Each value is added separately with IF NOT EXISTS (PG 9.3+).
    "ALTER TYPE shapetype ADD VALUE IF NOT EXISTS 'circle'",
    "ALTER TYPE shapetype ADD VALUE IF NOT EXISTS 'oval'",
    "ALTER TYPE shapetype ADD VALUE IF NOT EXISTS 'trapezoid'",
    "ALTER TYPE shapetype ADD VALUE IF NOT EXISTS 'trapezoid_truncated'",
    "ALTER TYPE shapetype ADD VALUE IF NOT EXISTS 'rhombus'",
    "ALTER TYPE shapetype ADD VALUE IF NOT EXISTS 'parallelogram'",
    "ALTER TYPE shapetype ADD VALUE IF NOT EXISTS 'semicircle'",
    "ALTER TYPE shapetype ADD VALUE IF NOT EXISTS 'right_triangle'",
]


def apply_patch(db_connection) -> list[str]:
    """
    Apply schema patch for shape_dimensions columns and new shape enum values.

    Accepts a raw SQLAlchemy connection (from engine.connect()) or Session.
    Returns list of SQL statements that were executed.
    """
    executed = []
    for sql in SHAPE_DIMENSIONS_PATCH_SQL:
        try:
            db_connection.execute(sa.text(sql))
            executed.append(sql.strip()[:80])
            logger.debug("Schema patch applied: %s", sql.strip()[:80])
        except Exception as exc:
            logger.debug("Schema patch skipped (%s): %s", type(exc).__name__, sql.strip()[:80])
    return executed
