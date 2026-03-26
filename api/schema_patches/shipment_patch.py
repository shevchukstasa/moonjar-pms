"""
Schema patch — shipment tables for order shipment workflow.
Decision 2026-03-26: Replace simple status flip with full shipment tracking + partial shipments.
"""

import logging
import sqlalchemy as sa

logger = logging.getLogger("moonjar.schema_patches.shipment")

SHIPMENT_SQL = [
    # shipments — main table
    """CREATE TABLE IF NOT EXISTS shipments (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        order_id UUID NOT NULL REFERENCES production_orders(id),
        factory_id UUID NOT NULL REFERENCES factories(id),
        tracking_number VARCHAR(100),
        carrier VARCHAR(100),
        shipping_method VARCHAR(50),
        total_pieces INTEGER NOT NULL DEFAULT 0,
        total_boxes INTEGER,
        total_weight_kg NUMERIC(10,2),
        status VARCHAR(30) NOT NULL DEFAULT 'prepared',
        shipped_at TIMESTAMPTZ,
        estimated_delivery DATE,
        delivered_at TIMESTAMPTZ,
        shipped_by UUID REFERENCES users(id),
        received_by VARCHAR(200),
        delivery_note_url VARCHAR(500),
        notes TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )""",

    # shipment_items — per-position line items for partial shipments
    """CREATE TABLE IF NOT EXISTS shipment_items (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        shipment_id UUID NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
        position_id UUID NOT NULL REFERENCES order_positions(id),
        quantity_shipped INTEGER NOT NULL,
        box_number INTEGER,
        notes TEXT
    )""",

    # Indexes
    "CREATE INDEX IF NOT EXISTS idx_shipments_order_id ON shipments(order_id)",
    "CREATE INDEX IF NOT EXISTS idx_shipments_factory_id ON shipments(factory_id)",
    "CREATE INDEX IF NOT EXISTS idx_shipments_status ON shipments(status)",
    "CREATE INDEX IF NOT EXISTS idx_shipment_items_shipment_id ON shipment_items(shipment_id)",
    "CREATE INDEX IF NOT EXISTS idx_shipment_items_position_id ON shipment_items(position_id)",
]


def apply_patch(db_connection) -> list[str]:
    """
    Apply schema patch for shipment tables.

    Accepts a raw SQLAlchemy connection (from engine.connect()).
    Returns list of SQL statements that were executed.
    """
    executed = []
    for sql in SHIPMENT_SQL:
        try:
            db_connection.execute(sa.text(sql))
            executed.append(sql)
            logger.debug("Schema patch applied: %s", sql[:80])
        except Exception as exc:
            logger.debug("Schema patch skipped (%s): %s", type(exc).__name__, sql[:80])
    return executed
