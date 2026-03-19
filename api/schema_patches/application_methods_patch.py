"""
Schema patch for application_methods and application_collections tables.

Creates the reference tables and seeds them with initial data.
Also adds application_collection_code / application_method_code columns
to order_positions, and per-method consumption rate columns to recipe_materials.

Called from _ensure_schema (main.py) or applied manually.

Usage:
    from api.schema_patches.application_methods_patch import apply_patch
    apply_patch(db_connection)
"""

import logging
import sqlalchemy as sa

logger = logging.getLogger("moonjar.schema_patches.application_methods")

APPLICATION_METHODS_PATCH_SQL = [
    # ── Table: application_methods ──────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS application_methods (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        code VARCHAR(20) UNIQUE NOT NULL,
        name VARCHAR(100) NOT NULL,
        engobe_method VARCHAR(20),
        glaze_method VARCHAR(20) NOT NULL,
        needs_engobe BOOLEAN NOT NULL DEFAULT TRUE,
        two_stage_firing BOOLEAN NOT NULL DEFAULT FALSE,
        special_kiln VARCHAR(20),
        consumption_group_engobe VARCHAR(20),
        consumption_group_glaze VARCHAR(20) NOT NULL,
        blocking_task_type VARCHAR(50),
        sort_order INTEGER NOT NULL DEFAULT 0,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,

    # ── Table: application_collections ──────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS application_collections (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        code VARCHAR(30) UNIQUE NOT NULL,
        name VARCHAR(100) NOT NULL,
        allowed_methods JSONB NOT NULL DEFAULT '[]',
        any_method BOOLEAN NOT NULL DEFAULT FALSE,
        no_base_colors BOOLEAN NOT NULL DEFAULT FALSE,
        no_base_sizes BOOLEAN NOT NULL DEFAULT FALSE,
        product_type_restriction VARCHAR(50),
        sort_order INTEGER NOT NULL DEFAULT 0,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,

    # ── Seed: application_methods ───────────────────────────────────────
    """
    INSERT INTO application_methods (code, name, engobe_method, glaze_method, needs_engobe, two_stage_firing, special_kiln, consumption_group_engobe, consumption_group_glaze, blocking_task_type, sort_order) VALUES
    ('ss', 'Spray-Spray', 'spray', 'spray', TRUE, FALSE, NULL, 'spray', 'spray', NULL, 1),
    ('s', 'Spray Only', NULL, 'spray', FALSE, FALSE, NULL, NULL, 'spray', NULL, 2),
    ('bs', 'Brush-Spray', 'brush', 'spray', TRUE, FALSE, NULL, 'brush', 'spray', NULL, 3),
    ('sb', 'Spray-Brush', 'spray', 'brush', TRUE, FALSE, NULL, 'spray', 'brush', NULL, 4),
    ('splashing', 'Splashing', 'spray', 'splash', TRUE, FALSE, NULL, 'spray', 'splash', NULL, 5),
    ('stencil', 'Stencil', 'spray', 'spray_stencil', TRUE, FALSE, NULL, 'spray', 'spray', 'stencil_order', 6),
    ('silk_screen', 'Silk Screen', 'spray', 'silk_screen', TRUE, FALSE, NULL, 'spray', 'silk_screen', 'silk_screen_order', 7),
    ('gold', 'Gold', 'spray', 'spray', TRUE, TRUE, NULL, 'spray', 'spray', NULL, 8),
    ('raku', 'Raku', 'spray', 'spray', TRUE, FALSE, 'raku', 'spray', 'spray', NULL, 9)
    ON CONFLICT (code) DO NOTHING
    """,

    # ── Seed: application_collections ───────────────────────────────────
    """
    INSERT INTO application_collections (code, name, allowed_methods, any_method, no_base_colors, no_base_sizes, product_type_restriction, sort_order) VALUES
    ('authentic', 'Authentic', '["ss", "s"]', FALSE, FALSE, FALSE, NULL, 1),
    ('creative', 'Creative', '["sb", "bs", "splashing"]', FALSE, FALSE, FALSE, NULL, 2),
    ('silk_screen', 'Silk Screen', '["silk_screen"]', FALSE, FALSE, FALSE, NULL, 3),
    ('stencil', 'Stencil', '["stencil"]', FALSE, FALSE, FALSE, NULL, 4),
    ('gold', 'Gold', '["gold"]', FALSE, FALSE, FALSE, NULL, 5),
    ('raku', 'Raku', '["raku"]', FALSE, FALSE, FALSE, NULL, 6),
    ('exclusive', 'Exclusive', '[]', TRUE, TRUE, TRUE, NULL, 7),
    ('top_table', 'Top Table', '[]', TRUE, FALSE, FALSE, 'countertop', 8),
    ('wash_basin', 'Wash Basin', '[]', TRUE, FALSE, FALSE, 'sink', 9)
    ON CONFLICT (code) DO NOTHING
    """,

    # ── Columns on order_positions ──────────────────────────────────────
    "ALTER TABLE order_positions ADD COLUMN IF NOT EXISTS application_collection_code VARCHAR(30)",
    "ALTER TABLE order_positions ADD COLUMN IF NOT EXISTS application_method_code VARCHAR(20)",

    # ── Per-method consumption rate columns on recipe_materials ──────────
    "ALTER TABLE recipe_materials ADD COLUMN IF NOT EXISTS spray_rate NUMERIC(10, 4)",
    "ALTER TABLE recipe_materials ADD COLUMN IF NOT EXISTS brush_rate NUMERIC(10, 4)",
    "ALTER TABLE recipe_materials ADD COLUMN IF NOT EXISTS splash_rate NUMERIC(10, 4)",
    "ALTER TABLE recipe_materials ADD COLUMN IF NOT EXISTS silk_screen_rate NUMERIC(10, 4)",
]


def apply_patch(db_connection) -> list[str]:
    """
    Apply schema patch for application_methods & application_collections.

    Accepts a raw SQLAlchemy connection (from engine.connect()) or Session.
    Returns list of SQL statements that were executed.
    """
    executed = []
    for sql in APPLICATION_METHODS_PATCH_SQL:
        try:
            db_connection.execute(sa.text(sql))
            executed.append(sql.strip()[:80])
            logger.debug("Schema patch applied: %s", sql.strip()[:80])
        except Exception as exc:
            logger.debug("Schema patch skipped (%s): %s", type(exc).__name__, sql.strip()[:80])
    return executed
