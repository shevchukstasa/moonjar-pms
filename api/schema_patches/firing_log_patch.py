"""
Schema patch — firing_logs table for temperature logging during kiln firing.

Creates the firing_logs table if it doesn't exist.
Called from startup patches in main.py.

Usage:
    from api.schema_patches.firing_log_patch import apply_patch
    apply_patch(db_connection)
"""

import logging
import sqlalchemy as sa

logger = logging.getLogger("moonjar.schema_patches.firing_log")

FIRING_LOG_SQL = [
    """CREATE TABLE IF NOT EXISTS firing_logs (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        batch_id UUID NOT NULL REFERENCES batches(id) ON DELETE CASCADE,
        kiln_id UUID NOT NULL REFERENCES resources(id),
        started_at TIMESTAMPTZ,
        ended_at TIMESTAMPTZ,
        peak_temperature NUMERIC(6,1),
        target_temperature NUMERIC(6,1),
        temperature_readings JSONB,
        firing_profile_id UUID REFERENCES firing_profiles(id),
        result VARCHAR(30),
        notes TEXT,
        recorded_by UUID REFERENCES users(id),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )""",

    "CREATE INDEX IF NOT EXISTS ix_firing_logs_batch_id ON firing_logs(batch_id)",
    "CREATE INDEX IF NOT EXISTS ix_firing_logs_kiln_id ON firing_logs(kiln_id)",
]


def apply_patch(connection):
    """Apply firing_logs schema patch (idempotent)."""
    for sql in FIRING_LOG_SQL:
        try:
            connection.execute(sa.text(sql))
            logger.info(f"firing_log_patch: executed OK — {sql[:60]}...")
        except Exception as e:
            logger.warning(f"firing_log_patch: skip — {e}")
    try:
        connection.commit()
    except Exception:
        pass
