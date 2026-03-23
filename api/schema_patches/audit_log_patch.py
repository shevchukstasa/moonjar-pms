"""
Schema patch: create/update audit_logs table.
Adds new_data JSONB and request_path columns for the automatic audit system.
Idempotent — safe to run on every startup.
"""
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)


def apply(conn):
    """Create audit_logs table if not exists, then add new columns."""
    # Create table (original schema)
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            action VARCHAR(20) NOT NULL,
            table_name VARCHAR(100) NOT NULL,
            record_id VARCHAR(100),
            old_data JSONB,
            user_id UUID,
            user_email VARCHAR(255),
            ip_address VARCHAR(45),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """))

    # Add new_data JSONB column (tracks what was changed TO, not just FROM)
    conn.execute(text("""
        ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS new_data JSONB
    """))

    # Add request_path column (which API endpoint triggered the change)
    conn.execute(text("""
        ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS request_path VARCHAR(255)
    """))

    # Indexes
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_audit_logs_table_record
        ON audit_logs (table_name, record_id)
    """))
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_audit_logs_created
        ON audit_logs (created_at DESC)
    """))
    # New index: look up by user
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id
        ON audit_logs (user_id)
    """))
    # New index: look up by action type
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_audit_logs_action
        ON audit_logs (action)
    """))
    # No explicit commit needed — engine.begin() auto-commits
    logger.info("Schema patch applied: audit_logs table (with new_data, request_path)")
