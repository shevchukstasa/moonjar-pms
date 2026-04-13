"""Add full_name column to materials table.

Short name (name) for UI/recipes, full name (full_name) for documents and search.
Example: name="Zircosil", full_name="Zirconium Silicate Micronized"
"""
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)


def run(conn):
    try:
        conn.execute(text(
            "ALTER TABLE materials ADD COLUMN IF NOT EXISTS full_name VARCHAR(500)"
        ))
    except Exception as e:
        logger.warning("material_full_name_patch: %s", e)

    # Seed: Zircosil full name
    try:
        conn.execute(text(
            "UPDATE materials SET full_name = 'Zirconium Silicate Micronized' "
            "WHERE lower(name) = 'zircosil' AND full_name IS NULL"
        ))
    except Exception as e:
        logger.warning("material_full_name_patch seed: %s", e)
