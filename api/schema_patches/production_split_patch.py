"""
Schema patch: PM Mid-Production Split columns on order_positions.
Decision 2026-03-19.
"""

PRODUCTION_SPLIT_SQL = [
    # Add columns to order_positions for production split tracking
    "ALTER TABLE order_positions ADD COLUMN IF NOT EXISTS is_parent BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE order_positions ADD COLUMN IF NOT EXISTS split_type VARCHAR(20)",  # 'production' | 'sorting'
    "ALTER TABLE order_positions ADD COLUMN IF NOT EXISTS split_stage VARCHAR(50)",  # status at split time
    "ALTER TABLE order_positions ADD COLUMN IF NOT EXISTS split_at TIMESTAMPTZ",
    "ALTER TABLE order_positions ADD COLUMN IF NOT EXISTS split_reason TEXT",
    "ALTER TABLE order_positions ADD COLUMN IF NOT EXISTS blocked_by_service VARCHAR(50)",
    "ALTER TABLE order_positions ADD COLUMN IF NOT EXISTS status_before_block VARCHAR(50)",
    # Indices
    "CREATE INDEX IF NOT EXISTS idx_positions_is_parent ON order_positions(is_parent) WHERE is_parent = TRUE",
    "CREATE INDEX IF NOT EXISTS idx_positions_split_type ON order_positions(split_type) WHERE split_type IS NOT NULL",
]


def apply_patch(db_connection):
    """Apply production split schema patches. Idempotent — safe to run multiple times."""
    import sqlalchemy as sa
    for sql in PRODUCTION_SPLIT_SQL:
        try:
            db_connection.execute(sa.text(sql))
        except Exception:
            pass  # column/index already exists — ignore
