"""Add role column to onboarding_progress for multi-role onboarding support.

Idempotent — uses IF NOT EXISTS / IF EXISTS checks.
"""
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)

STATEMENTS = [
    # Add role column if missing
    """
    ALTER TABLE onboarding_progress
    ADD COLUMN IF NOT EXISTS role VARCHAR(50) NOT NULL DEFAULT 'production_manager';
    """,
    # Drop old unique constraint (user_id, section_id only)
    """
    DO $$ BEGIN
        IF EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conname = 'uq_onboarding_user_section'
            AND conrelid = 'onboarding_progress'::regclass
        ) THEN
            ALTER TABLE onboarding_progress DROP CONSTRAINT uq_onboarding_user_section;
        END IF;
    END $$;
    """,
    # Create new unique constraint including role
    """
    DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conname = 'uq_onboarding_user_section_role'
            AND conrelid = 'onboarding_progress'::regclass
        ) THEN
            ALTER TABLE onboarding_progress
            ADD CONSTRAINT uq_onboarding_user_section_role UNIQUE (user_id, section_id, role);
        END IF;
    END $$;
    """,
]


def run(conn):
    for stmt in STATEMENTS:
        try:
            conn.execute(text(stmt))
        except Exception as e:
            logger.warning("onboarding_role_patch statement skipped: %s", e)
