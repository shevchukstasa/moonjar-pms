"""
Schema patch — user_streaks + daily_challenges tables for gamification.
Decision 2026-03-30: Streak tracking + daily challenges for PM dashboard.
"""

import logging
import sqlalchemy as sa

logger = logging.getLogger("moonjar.schema_patches.streaks")

STREAKS_SQL = [
    # user_streaks — per user + factory streak tracking
    """CREATE TABLE IF NOT EXISTS user_streaks (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        factory_id UUID NOT NULL REFERENCES factories(id) ON DELETE CASCADE,
        streak_type VARCHAR(30) NOT NULL,
        current_streak INTEGER NOT NULL DEFAULT 0,
        best_streak INTEGER NOT NULL DEFAULT 0,
        last_activity_date DATE,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE(user_id, factory_id, streak_type)
    )""",

    # daily_challenges — one per factory per day (deterministic)
    """CREATE TABLE IF NOT EXISTS daily_challenges (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        factory_id UUID NOT NULL REFERENCES factories(id) ON DELETE CASCADE,
        challenge_date DATE NOT NULL,
        challenge_type VARCHAR(30) NOT NULL,
        title VARCHAR(300) NOT NULL,
        description TEXT,
        target_value INTEGER NOT NULL DEFAULT 1,
        actual_value INTEGER NOT NULL DEFAULT 0,
        completed BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE(factory_id, challenge_date)
    )""",

    # Indexes
    "CREATE INDEX IF NOT EXISTS idx_user_streaks_user_factory ON user_streaks(user_id, factory_id)",
    "CREATE INDEX IF NOT EXISTS idx_user_streaks_type ON user_streaks(streak_type)",
    "CREATE INDEX IF NOT EXISTS idx_daily_challenges_factory_date ON daily_challenges(factory_id, challenge_date)",
]


def apply_patch(db_connection) -> list[str]:
    """
    Apply schema patch for streak + challenge tables.

    Accepts a raw SQLAlchemy connection (from engine.connect()).
    Returns list of SQL statements that were executed.
    """
    executed = []
    for sql in STREAKS_SQL:
        try:
            db_connection.execute(sa.text(sql))
            executed.append(sql)
            logger.debug("Schema patch applied: %s", sql[:80])
        except Exception as exc:
            logger.debug("Schema patch skipped (%s): %s", type(exc).__name__, sql[:80])
    return executed
