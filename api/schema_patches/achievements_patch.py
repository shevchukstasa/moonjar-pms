"""
Schema patch — master_achievements table for gamification Phase 6.
Decision 2026-03-30: Achievement system for masters.
"""

import logging
import sqlalchemy as sa

logger = logging.getLogger("moonjar.schema_patches.achievements")

ACHIEVEMENTS_SQL = [
    # master_achievements — per user achievement tracking
    """CREATE TABLE IF NOT EXISTS master_achievements (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        achievement_type VARCHAR(30) NOT NULL,
        level INTEGER NOT NULL DEFAULT 0,
        unlocked_at TIMESTAMPTZ,
        progress_current INTEGER NOT NULL DEFAULT 0,
        progress_target INTEGER NOT NULL DEFAULT 100,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE(user_id, achievement_type)
    )""",

    # Indexes
    "CREATE INDEX IF NOT EXISTS idx_master_achievements_user ON master_achievements(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_master_achievements_type ON master_achievements(achievement_type)",
    "CREATE INDEX IF NOT EXISTS idx_master_achievements_level ON master_achievements(level)",
]


def apply_patch(db_connection) -> list[str]:
    """
    Apply schema patch for master_achievements table.

    Accepts a raw SQLAlchemy connection (from engine.connect()).
    Returns list of SQL statements that were executed.
    """
    executed = []
    for sql in ACHIEVEMENTS_SQL:
        try:
            db_connection.execute(sa.text(sql))
            executed.append(sql)
            logger.debug("Schema patch applied: %s", sql[:80])
        except Exception as exc:
            logger.debug("Schema patch skipped (%s): %s", type(exc).__name__, sql[:80])
    return executed
