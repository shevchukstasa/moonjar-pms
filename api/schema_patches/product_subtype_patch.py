"""
Schema patch: add product_subtype to materials and update ProductType enum.
Adds table_top and custom to the product_type enum for finished goods.

Note: ALTER TYPE ... ADD VALUE cannot run inside a transaction block in PostgreSQL,
so enum additions use a separate autocommit connection.
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

    # Add index for filtering materials by product_subtype
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_materials_product_subtype
        ON materials (product_subtype) WHERE product_subtype IS NOT NULL
    """))

    # Extend ProductType enum with new values.
    # ALTER TYPE ... ADD VALUE IF NOT EXISTS cannot run inside a transaction,
    # so we use a raw DBAPI connection with autocommit.
    raw_conn = conn.connection.connection  # unwrap to raw DBAPI connection
    old_autocommit = raw_conn.autocommit
    try:
        raw_conn.autocommit = True
        cursor = raw_conn.cursor()
        for val in ('table_top', 'custom'):
            try:
                cursor.execute(f"ALTER TYPE producttype ADD VALUE IF NOT EXISTS '{val}'")
            except Exception:
                pass  # Already exists or type doesn't exist yet
        cursor.close()
    finally:
        raw_conn.autocommit = old_autocommit

    logger.info("Schema patch applied: product_subtype + extended ProductType enum")
