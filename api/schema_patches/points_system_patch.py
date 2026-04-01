"""
Schema patch — points system + recipe verification tables for gamified photo verification.
Decision 2026-04-01: Gamified recipe preparation with weighing accuracy scoring.
"""

import logging
import sqlalchemy as sa

logger = logging.getLogger("moonjar.schema_patches.points_system")

POINTS_SYSTEM_SQL = [
    # user_points — yearly accumulation per user+factory
    """CREATE TABLE IF NOT EXISTS user_points (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        factory_id UUID NOT NULL REFERENCES factories(id),
        points_total INTEGER NOT NULL DEFAULT 0,
        points_this_month INTEGER NOT NULL DEFAULT 0,
        points_this_week INTEGER NOT NULL DEFAULT 0,
        year INTEGER NOT NULL DEFAULT 2026,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE(user_id, factory_id, year)
    )""",

    # point_transactions — audit trail for every point award
    """CREATE TABLE IF NOT EXISTS point_transactions (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id),
        factory_id UUID NOT NULL REFERENCES factories(id),
        points INTEGER NOT NULL,
        reason VARCHAR(50) NOT NULL,
        details JSONB,
        position_id UUID REFERENCES order_positions(id) ON DELETE SET NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",

    # recipe_verifications — per-ingredient photo verification records
    """CREATE TABLE IF NOT EXISTS recipe_verifications (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id),
        factory_id UUID NOT NULL REFERENCES factories(id),
        position_id UUID REFERENCES order_positions(id),
        recipe_id UUID REFERENCES recipes(id),
        material_id UUID NOT NULL REFERENCES materials(id),
        target_grams NUMERIC(10,2) NOT NULL,
        actual_grams NUMERIC(10,2),
        accuracy_pct NUMERIC(5,2),
        points_awarded INTEGER DEFAULT 0,
        photo_url TEXT,
        ai_reading TEXT,
        verified_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",

    # Indexes
    "CREATE INDEX IF NOT EXISTS idx_user_points_user ON user_points(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_user_points_factory_year ON user_points(factory_id, year)",
    "CREATE INDEX IF NOT EXISTS idx_point_transactions_user ON point_transactions(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_point_transactions_factory ON point_transactions(factory_id)",
    "CREATE INDEX IF NOT EXISTS idx_point_transactions_created ON point_transactions(created_at)",
    "CREATE INDEX IF NOT EXISTS idx_recipe_verifications_user ON recipe_verifications(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_recipe_verifications_recipe ON recipe_verifications(recipe_id)",
    "CREATE INDEX IF NOT EXISTS idx_recipe_verifications_position ON recipe_verifications(position_id)",
]


def apply_patch(db_connection) -> list[str]:
    """
    Apply schema patch for points system + recipe verification tables.

    Accepts a raw SQLAlchemy connection (from engine.connect()).
    Returns list of SQL statements that were executed.
    """
    executed = []
    for sql in POINTS_SYSTEM_SQL:
        try:
            db_connection.execute(sa.text(sql))
            executed.append(sql)
            logger.debug("Schema patch applied: %s", sql[:80])
        except Exception as exc:
            logger.debug("Schema patch skipped (%s): %s", type(exc).__name__, sql[:80])
    return executed
