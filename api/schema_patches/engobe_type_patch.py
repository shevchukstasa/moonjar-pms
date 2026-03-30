"""
Schema patch — add engobe_type column to recipes table.

Only set when recipe_type='engobe': 'standard', 'shelf_coating', 'hole_filler'.
Called from startup patches in main.py.

Usage:
    from api.schema_patches.engobe_type_patch import apply_patch
    apply_patch(db_connection)
"""

import logging
import sqlalchemy as sa

logger = logging.getLogger("moonjar.schema_patches.engobe_type")


def apply_patch(connection):
    """Add engobe_type column to recipes (idempotent)."""
    sql = """
        DO $$ BEGIN
            ALTER TABLE recipes ADD COLUMN engobe_type VARCHAR(20);
        EXCEPTION WHEN duplicate_column THEN NULL;
        END $$;
    """
    try:
        connection.execute(sa.text(sql))
        logger.info("engobe_type_patch: engobe_type column ensured on recipes")
    except Exception as e:
        logger.warning(f"engobe_type_patch: skip — {e}")
    try:
        connection.commit()
    except Exception:
        pass
