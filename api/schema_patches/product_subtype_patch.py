"""
Schema patch: add product_subtype to materials and update ProductType enum.
Adds table_top and custom to the product_type enum for finished goods.
"""
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)


def apply(conn):
    """Add product_subtype column and extend product_type enum."""
    # Add product_subtype to materials
    conn.execute(text("""
        ALTER TABLE materials ADD COLUMN IF NOT EXISTS product_subtype VARCHAR(30)
    """))

    # Extend ProductType enum with new values (safe — IF NOT EXISTS equivalent)
    for val in ('table_top', 'custom'):
        try:
            conn.execute(text(f"ALTER TYPE producttype ADD VALUE IF NOT EXISTS '{val}'"))
        except Exception:
            pass  # Already exists

    # Add index for filtering materials by product_subtype
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_materials_product_subtype
        ON materials (product_subtype) WHERE product_subtype IS NOT NULL
    """))

    logger.info("Schema patch applied: product_subtype + extended ProductType enum")
