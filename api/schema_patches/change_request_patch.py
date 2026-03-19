"""
Schema patch for production_order_change_requests table extensions.

Adds columns that may not exist in older deployments.
Called from _ensure_schema (main.py) or applied manually.

Usage:
    from api.schema_patches.change_request_patch import apply_patch
    apply_patch(db_connection)
"""

import logging
import sqlalchemy as sa

logger = logging.getLogger("moonjar.schema_patches.change_request")

CHANGE_REQUEST_PATCH_SQL = [
    # Source of the change request (e.g. 'sales_webhook', 'manual')
    "ALTER TABLE production_order_change_requests ADD COLUMN IF NOT EXISTS source VARCHAR(50) DEFAULT 'manual'",
    # Flag: was this request initiated externally (not by a PMS user)?
    "ALTER TABLE production_order_change_requests ADD COLUMN IF NOT EXISTS requested_by_external BOOLEAN NOT NULL DEFAULT FALSE",
    # Full snapshot of old order data at the time of request
    "ALTER TABLE production_order_change_requests ADD COLUMN IF NOT EXISTS old_data JSONB",
    # Full snapshot of proposed new data
    "ALTER TABLE production_order_change_requests ADD COLUMN IF NOT EXISTS new_data JSONB",
    # Rejection reason (filled when PM rejects)
    "ALTER TABLE production_order_change_requests ADD COLUMN IF NOT EXISTS rejection_reason TEXT",
    # Log of partial apply (which fields/positions were applied)
    "ALTER TABLE production_order_change_requests ADD COLUMN IF NOT EXISTS partial_apply_log JSONB",
]


def apply_patch(db_connection) -> list[str]:
    """
    Apply schema patch for change_requests table.

    Accepts a raw SQLAlchemy connection (from engine.connect()) or Session.
    Returns list of SQL statements that were executed.
    """
    executed = []
    for sql in CHANGE_REQUEST_PATCH_SQL:
        try:
            db_connection.execute(sa.text(sql))
            executed.append(sql)
            logger.debug("Schema patch applied: %s", sql[:80])
        except Exception as exc:
            # Column already exists or other non-fatal error — skip
            logger.debug("Schema patch skipped (%s): %s", type(exc).__name__, sql[:80])
    return executed
