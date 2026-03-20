"""
Add temperature_group_id FK to firing_profiles table.
Idempotent — safe to run multiple times.
"""

import logging

logger = logging.getLogger("moonjar.schema_patches.firing_profile_temp_group")


def apply(conn):
    """Add temperature_group_id column to firing_profiles if missing."""
    result = conn.execute(
        __import__('sqlalchemy').text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'firing_profiles' AND column_name = 'temperature_group_id'"
        )
    )
    if result.fetchone():
        logger.info("firing_profiles.temperature_group_id already exists — skipping")
        return

    logger.info("Adding temperature_group_id to firing_profiles...")
    conn.execute(__import__('sqlalchemy').text("""
        ALTER TABLE firing_profiles
        ADD COLUMN temperature_group_id UUID
        REFERENCES firing_temperature_groups(id) ON DELETE SET NULL
    """))
    conn.execute(__import__('sqlalchemy').text("""
        CREATE INDEX IF NOT EXISTS ix_firing_profiles_temperature_group_id
        ON firing_profiles(temperature_group_id)
    """))
    conn.commit()
    logger.info("Done: temperature_group_id added to firing_profiles")
