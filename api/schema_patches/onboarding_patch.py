"""Create onboarding_progress table.

Tracks PM onboarding completion per section with quiz scores and XP.
"""
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)

STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS onboarding_progress (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        section_id VARCHAR(50) NOT NULL,
        completed BOOLEAN NOT NULL DEFAULT false,
        quiz_score INTEGER,
        quiz_attempts INTEGER NOT NULL DEFAULT 0,
        xp_earned INTEGER NOT NULL DEFAULT 0,
        completed_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT uq_onboarding_user_section UNIQUE (user_id, section_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_onboarding_user ON onboarding_progress (user_id)",
]


def apply(conn):
    for stmt in STATEMENTS:
        try:
            conn.execute(text(stmt))
        except Exception as e:
            logger.debug("onboarding patch: %s — %s", stmt[:60], e)
    logger.info("Schema patch applied: onboarding_progress")
