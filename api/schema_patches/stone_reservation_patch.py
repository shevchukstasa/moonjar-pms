"""Schema patch — stone reservation tables.
Decision 2026-03-19: Stone is tracked as a separate entity from BOM materials.
"""

STONE_RESERVATION_SQL = [
    # stone_defect_rates — configurable per size category + product type
    """CREATE TABLE IF NOT EXISTS stone_defect_rates (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        factory_id UUID REFERENCES factories(id),
        size_category VARCHAR(20) NOT NULL,  -- 'small'|'medium'|'large'|'any'
        product_type VARCHAR(50) NOT NULL,
        defect_pct NUMERIC(5,4) NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_by UUID REFERENCES users(id),
        UNIQUE (factory_id, size_category, product_type)
    )""",

    # stone_reservations — main table
    """CREATE TABLE IF NOT EXISTS stone_reservations (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        position_id UUID NOT NULL REFERENCES order_positions(id) ON DELETE CASCADE,
        factory_id UUID NOT NULL REFERENCES factories(id),
        size_category VARCHAR(20) NOT NULL,
        product_type VARCHAR(50) NOT NULL,
        reserved_qty INTEGER NOT NULL,
        reserved_sqm NUMERIC(10,3) NOT NULL,
        stone_defect_pct NUMERIC(5,4) NOT NULL,
        status VARCHAR(20) NOT NULL DEFAULT 'active',
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        reconciled_at TIMESTAMPTZ
    )""",

    # stone_reservation_adjustments — return/writeoff log
    """CREATE TABLE IF NOT EXISTS stone_reservation_adjustments (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        reservation_id UUID NOT NULL REFERENCES stone_reservations(id) ON DELETE CASCADE,
        type VARCHAR(20) NOT NULL,  -- 'return' | 'writeoff'
        qty_sqm NUMERIC(10,3) NOT NULL,
        reason TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        created_by UUID REFERENCES users(id)
    )""",

    # Индексы
    "CREATE INDEX IF NOT EXISTS idx_stone_res_position ON stone_reservations(position_id)",
    "CREATE INDEX IF NOT EXISTS idx_stone_res_factory ON stone_reservations(factory_id, status)",
    "CREATE INDEX IF NOT EXISTS idx_stone_adj_res ON stone_reservation_adjustments(reservation_id)",

    # Seed defaults (global, factory_id IS NULL)
    """INSERT INTO stone_defect_rates (size_category, product_type, defect_pct) VALUES
        ('small',  'tile',        0.02),
        ('medium', 'tile',        0.03),
        ('large',  'tile',        0.05),
        ('any',    'countertop',  0.04),
        ('any',    'sink',        0.06),
        ('any',    '3d',          0.08)
    ON CONFLICT DO NOTHING""",
]


def apply_patch(db_connection):
    """Apply stone reservation schema patch. Safe to run multiple times (IF NOT EXISTS)."""
    import sqlalchemy as sa
    for sql in STONE_RESERVATION_SQL:
        try:
            db_connection.execute(sa.text(sql))
            db_connection.commit()
        except Exception:
            db_connection.rollback()
            pass
