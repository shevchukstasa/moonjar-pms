"""Kiln constants — add missing rows, fix FILLER_MAX_AREA unit, normalize.

All global kiln constants must be configurable via the kiln_constants table.
Previously missing: FILLER_COEFFICIENT, MIN_SPACE_TO_FILL, COFIRING_MAX_TEMP_RANGE,
TRIANGLE_PAIR_GAP.
Also fixes: FILLER_MAX_AREA was stored as 20000 cm² — converted to 2.0 m².
Also removes the LARGE/SMALL kiln type distinction from global constants for
MAX_EDGE_HEIGHT (now a per-kiln field in kiln_loading_rules.rules JSONB).

Revision ID: 005_kiln_constants_complete
Revises: 004_schema_sync
Create Date: 2026-03-10
"""
from alembic import op
from sqlalchemy import text

revision = "005_kiln_constants_complete"
down_revision = "004_schema_sync"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Fix FILLER_MAX_AREA: was 20000 cm² — change to 2.0 m²
    conn.execute(text("""
        UPDATE kiln_constants
        SET value = 2.0, unit = 'm2',
            description = 'Max filler tile area per kiln load (m²)'
        WHERE constant_name = 'FILLER_MAX_AREA'
    """))

    # 2. Rename MAX_EDGE_HEIGHT_LARGE / _SMALL → single MAX_EDGE_HEIGHT default.
    #    The per-kiln value is now stored in kiln_loading_rules.rules JSONB
    #    (max_edge_height_cm). The global constant is just the system default.
    conn.execute(text("""
        UPDATE kiln_constants
        SET constant_name = 'MAX_EDGE_HEIGHT',
            description   = 'Default max product height (cm) for edge loading — overridable per kiln'
        WHERE constant_name = 'MAX_EDGE_HEIGHT_LARGE'
    """))
    # Remove the Small variant — it is now per-kiln
    conn.execute(text("""
        DELETE FROM kiln_constants WHERE constant_name = 'MAX_EDGE_HEIGHT_SMALL'
    """))

    # 3. Insert previously missing constants (safe: ON CONFLICT DO NOTHING)
    conn.execute(text("""
        INSERT INTO kiln_constants
            (id, constant_name, value, unit, description)
        VALUES
            (gen_random_uuid(), 'FILLER_COEFFICIENT',      0.5,  '',   'Efficiency factor applied to raw filler tile count'),
            (gen_random_uuid(), 'MIN_SPACE_TO_FILL',      21.0,  'cm', 'Min leftover shelf space (cm) before adding filler tiles'),
            (gen_random_uuid(), 'COFIRING_MAX_TEMP_RANGE', 50.0, '°C', 'Max allowed temperature spread for co-firing positions'),
            (gen_random_uuid(), 'TRIANGLE_PAIR_GAP',        1.5, 'cm', 'Extra gap when placing two triangles as a pair'),
            (gen_random_uuid(), 'MIN_PRODUCT_SIZE',         3.0, 'cm', 'Minimum product length or width')
        ON CONFLICT (constant_name) DO NOTHING
    """))

    print("INFO: Migration 005 — kiln constants normalised.")


def downgrade() -> None:
    # Best-effort: restore removed rows
    conn = op.get_bind()
    conn.execute(text("""
        UPDATE kiln_constants
        SET constant_name = 'MAX_EDGE_HEIGHT_LARGE',
            description   = 'Max tile height on edge in Large kiln'
        WHERE constant_name = 'MAX_EDGE_HEIGHT'
    """))
    conn.execute(text("""
        INSERT INTO kiln_constants (id, constant_name, value, unit, description)
        VALUES (gen_random_uuid(), 'MAX_EDGE_HEIGHT_SMALL', 30.0, 'cm',
                'Max tile height on edge in Small kiln')
        ON CONFLICT (constant_name) DO NOTHING
    """))
    conn.execute(text("""
        DELETE FROM kiln_constants
        WHERE constant_name IN ('FILLER_COEFFICIENT', 'MIN_SPACE_TO_FILL',
                                'COFIRING_MAX_TEMP_RANGE', 'TRIANGLE_PAIR_GAP')
    """))
    conn.execute(text("""
        UPDATE kiln_constants
        SET value = 20000, unit = 'cm2',
            description = 'Max filler area (2 m2 = 20000 cm2)'
        WHERE constant_name = 'FILLER_MAX_AREA'
    """))
