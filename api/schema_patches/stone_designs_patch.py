"""
Schema patch: stone_designs catalog + materials.design_id FK.

Adds a first-class catalog of 3D/variant designs so two stone materials
of the same size can coexist with a clear discriminator (e.g. two
different 3D relief patterns sharing "5×20×1-2" geometry).

See BUSINESS_LOGIC_FULL §29 (addendum).
"""
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)


def apply(conn):
    # 1. stone_designs table
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS stone_designs (
            id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            code         VARCHAR(50)  NOT NULL UNIQUE,
            name         VARCHAR(100) NOT NULL,
            name_id      VARCHAR(100),
            typology     VARCHAR(30),
            photo_url    VARCHAR(500),
            description  TEXT,
            display_order INTEGER NOT NULL DEFAULT 0,
            is_active    BOOLEAN NOT NULL DEFAULT TRUE,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))

    # 2. materials.design_id FK
    conn.execute(text("""
        ALTER TABLE materials
        ADD COLUMN IF NOT EXISTS design_id UUID
        REFERENCES stone_designs(id) ON DELETE SET NULL
    """))

    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_materials_design_id
        ON materials (design_id) WHERE design_id IS NOT NULL
    """))

    # 3. Composite uniqueness: (size_id, product_subtype, design_id) cannot repeat
    #    for stone materials. Partial index — ignores rows with NULL size_id
    #    (non-stone / freeform) to keep constraint narrow.
    conn.execute(text("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_materials_size_typology_design
        ON materials (size_id, product_subtype, COALESCE(design_id, '00000000-0000-0000-0000-000000000000'::uuid))
        WHERE size_id IS NOT NULL
          AND material_type IN ('stone', 'tile', 'sink', 'custom_product')
    """))

    logger.info("Schema patch applied: stone_designs + materials.design_id")
