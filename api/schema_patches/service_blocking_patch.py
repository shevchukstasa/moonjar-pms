"""
Schema patch for Service Blocking Timing feature.

Adds:
- service_lead_times table: configurable lead times per factory/service
- order_positions.blocked_by_service: which service is blocking
- order_positions.status_before_block: status to restore on unblock

Decision 2026-03-19: Block only when lead_time >= days_until_planned_glazing_date.

Usage:
    from api.schema_patches.service_blocking_patch import apply_patch
    apply_patch(db_connection)
"""

import logging
import sqlalchemy as sa

logger = logging.getLogger("moonjar.schema_patches.service_blocking")

SERVICE_BLOCKING_SQL = [
    # New table for configurable lead times per factory
    """CREATE TABLE IF NOT EXISTS service_lead_times (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        factory_id UUID NOT NULL REFERENCES factories(id),
        service_type VARCHAR(50) NOT NULL,
        lead_time_days INTEGER NOT NULL DEFAULT 3,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_by UUID REFERENCES users(id),
        UNIQUE (factory_id, service_type)
    )""",
    # Add columns to order_positions for blocking state tracking
    "ALTER TABLE order_positions ADD COLUMN IF NOT EXISTS blocked_by_service VARCHAR(50)",
    "ALTER TABLE order_positions ADD COLUMN IF NOT EXISTS status_before_block VARCHAR(50)",
]


def apply_patch(db_connection) -> list[str]:
    """
    Apply schema patch for service blocking timing.

    Accepts a raw SQLAlchemy connection (from engine.connect()) or Session.
    Returns list of SQL statements that were executed.
    """
    executed = []
    for sql in SERVICE_BLOCKING_SQL:
        try:
            db_connection.execute(sa.text(sql))
            executed.append(sql)
            logger.debug("Schema patch applied: %s", sql[:80])
        except Exception as exc:
            # Table/column already exists or other non-fatal error — skip
            logger.debug("Schema patch skipped (%s): %s", type(exc).__name__, sql[:80])
    return executed
