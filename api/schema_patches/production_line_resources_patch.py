"""Create production_line_resources table.

Stores capacity of production line equipment:
- Work tables (area in sqm, board capacity)
- Drying racks/shelving (capacity in sqm or board count)
- Glazing boards (count available)

These are constraints the scheduler uses to determine
how much work can be in progress at each stage.
"""
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)


def apply(conn):
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS production_line_resources (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            factory_id UUID NOT NULL REFERENCES factories(id),
            resource_type VARCHAR(50) NOT NULL,
            name VARCHAR(200) NOT NULL,
            capacity_sqm NUMERIC(10, 3),
            capacity_boards INTEGER,
            capacity_pcs INTEGER,
            num_units INTEGER DEFAULT 1,
            notes TEXT,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now(),
            UNIQUE(factory_id, resource_type, name)
        );
    """))

    # resource_type values:
    # 'work_table' — рабочие столы (area + board count)
    # 'drying_rack' — стеллажи для сушки (capacity sqm/boards)
    # 'glazing_board' — доски для глазурирования (count)
    # 'kiln' — печи (already in resources table, but link here for completeness)

    logger.info("production_line_resources table ensured")
