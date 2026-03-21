"""
Schema patch: create audit_logs table for tracking all DELETE operations.
Idempotent — safe to run on every startup.
"""
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)


def apply(conn):
    """Create audit_logs table if not exists."""
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            action VARCHAR(20) NOT NULL,
            table_name VARCHAR(100) NOT NULL,
            record_id UUID NOT NULL,
            old_data JSONB,
            user_id UUID,
            user_email VARCHAR(255),
            ip_address VARCHAR(45),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """))
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_audit_logs_table_record
        ON audit_logs (table_name, record_id)
    """))
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_audit_logs_created
        ON audit_logs (created_at DESC)
    """))
    conn.commit()
    logger.info("Schema patch applied: audit_logs table")
