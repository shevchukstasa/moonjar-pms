"""Seed standard kiln loading typologies and default stage typology speeds.

Creates 11 typologies covering all standard product/loading combinations
and populates default processing speeds for key stages (glazing, sorting,
packing, pre_kiln_check, engobe).

Safe to re-run: uses INSERT ... ON CONFLICT DO NOTHING on typology name
and (typology_id, stage) for speeds.

Revision ID: 018
Revises: 017
Create Date: 2026-04-03
"""
from alembic import op
from sqlalchemy import text

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # ── Get Bali factory ID ──────────────────────────────────────
    row = conn.execute(text(
        "SELECT id FROM factories WHERE name ILIKE '%bali%' LIMIT 1"
    )).fetchone()
    if not row:
        print("WARNING: Bali factory not found — skipping typology seed.")
        return
    factory_id = str(row[0])

    # ── Ensure unique constraint on (factory_id, name) exists ────
    # so ON CONFLICT works for idempotent inserts.
    conn.execute(text("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_kiln_loading_typologies_factory_name'
            ) THEN
                ALTER TABLE kiln_loading_typologies
                ADD CONSTRAINT uq_kiln_loading_typologies_factory_name
                UNIQUE (factory_id, name);
            END IF;
        END $$;
    """))

    # ── Insert typologies ────────────────────────────────────────
    typologies = [
        # (name, product_types, place_of_application, collections, methods,
        #  min_size_cm, max_size_cm, preferred_loading, priority)
        (
            "Small Tiles Edge",
            '["tile"]', '["face_only"]', '[]', '[]',
            5, 15, "edge", 10,
        ),
        (
            "Small Tiles Flat",
            '["tile"]', '["all_edges", "with_back"]', '[]', '[]',
            5, 15, "flat", 10,
        ),
        (
            "Medium Tiles Edge",
            '["tile"]', '["face_only", "edges_1", "edges_2"]', '[]', '[]',
            15, 25, "edge", 8,
        ),
        (
            "Medium Tiles Flat",
            '["tile"]', '["all_edges", "with_back"]', '[]', '[]',
            15, 25, "flat", 8,
        ),
        (
            "Large Tiles Flat",
            '["tile"]', '[]', '[]', '[]',
            25, 45, "flat", 6,
        ),
        (
            "Raku Tiles",
            '["tile"]', '[]', '["Raku"]', '["Raku"]',
            None, None, "flat", 15,
        ),
        (
            "Stencil Tiles",
            '["tile"]', '[]', '[]', '["Stencil"]',
            None, None, "edge", 12,
        ),
        (
            "Silkscreen Tiles",
            '["tile"]', '[]', '[]', '["Silkscreen"]',
            None, None, "edge", 12,
        ),
        (
            "Countertops",
            '["countertop"]', '[]', '[]', '[]',
            None, None, "flat", 5,
        ),
        (
            "Sinks",
            '["sink"]', '[]', '[]', '[]',
            None, None, "flat", 5,
        ),
        (
            "3D Products",
            '["3d"]', '[]', '[]', '[]',
            None, None, "flat", 5,
        ),
    ]

    for (name, ptypes, places, colls, methods,
         min_sz, max_sz, pref_loading, priority) in typologies:
        conn.execute(text("""
            INSERT INTO kiln_loading_typologies
                (id, factory_id, name, product_types, place_of_application,
                 collections, methods, min_size_cm, max_size_cm,
                 preferred_loading, priority, is_active, auto_calibrate)
            VALUES
                (gen_random_uuid(), :factory_id, :name,
                 :ptypes::JSONB, :places::JSONB, :colls::JSONB, :methods::JSONB,
                 :min_sz, :max_sz, :pref_loading, :priority, TRUE, FALSE)
            ON CONFLICT (factory_id, name) DO NOTHING
        """), {
            "factory_id": factory_id,
            "name": name,
            "ptypes": ptypes,
            "places": places,
            "colls": colls,
            "methods": methods,
            "min_sz": min_sz,
            "max_sz": max_sz,
            "pref_loading": pref_loading,
            "priority": priority,
        })

    # ── Seed default stage typology speeds ───────────────────────
    # Format: (typology_name, stage, rate, unit)
    # unit: 'pcs' (per person per hour) or 'sqm' (per person per hour)
    speeds = [
        # Small Tiles Edge
        ("Small Tiles Edge", "glazing", 60, "pcs"),
        ("Small Tiles Edge", "sorting", 100, "pcs"),
        ("Small Tiles Edge", "packing", 80, "pcs"),
        ("Small Tiles Edge", "pre_kiln_check", 120, "pcs"),
        ("Small Tiles Edge", "engobe", 70, "pcs"),

        # Small Tiles Flat
        ("Small Tiles Flat", "glazing", 40, "pcs"),
        ("Small Tiles Flat", "sorting", 80, "pcs"),
        ("Small Tiles Flat", "packing", 60, "pcs"),
        ("Small Tiles Flat", "pre_kiln_check", 100, "pcs"),
        ("Small Tiles Flat", "engobe", 50, "pcs"),

        # Medium Tiles Edge
        ("Medium Tiles Edge", "glazing", 30, "pcs"),
        ("Medium Tiles Edge", "sorting", 60, "pcs"),
        ("Medium Tiles Edge", "packing", 45, "pcs"),
        ("Medium Tiles Edge", "pre_kiln_check", 70, "pcs"),
        ("Medium Tiles Edge", "engobe", 35, "pcs"),

        # Medium Tiles Flat
        ("Medium Tiles Flat", "glazing", 30, "pcs"),
        ("Medium Tiles Flat", "sorting", 60, "pcs"),
        ("Medium Tiles Flat", "packing", 45, "pcs"),
        ("Medium Tiles Flat", "pre_kiln_check", 70, "pcs"),
        ("Medium Tiles Flat", "engobe", 35, "pcs"),

        # Large Tiles Flat
        ("Large Tiles Flat", "glazing", 3.5, "sqm"),
        ("Large Tiles Flat", "sorting", 5.0, "sqm"),
        ("Large Tiles Flat", "packing", 4.0, "sqm"),
        ("Large Tiles Flat", "pre_kiln_check", 6.0, "sqm"),
        ("Large Tiles Flat", "engobe", 4.0, "sqm"),

        # Raku Tiles
        ("Raku Tiles", "glazing", 20, "pcs"),
        ("Raku Tiles", "sorting", 40, "pcs"),
        ("Raku Tiles", "packing", 30, "pcs"),
        ("Raku Tiles", "pre_kiln_check", 50, "pcs"),
        ("Raku Tiles", "engobe", 25, "pcs"),

        # Stencil Tiles
        ("Stencil Tiles", "glazing", 15, "pcs"),
        ("Stencil Tiles", "sorting", 50, "pcs"),
        ("Stencil Tiles", "packing", 40, "pcs"),
        ("Stencil Tiles", "pre_kiln_check", 60, "pcs"),
        ("Stencil Tiles", "engobe", 30, "pcs"),

        # Silkscreen Tiles
        ("Silkscreen Tiles", "glazing", 15, "pcs"),
        ("Silkscreen Tiles", "sorting", 50, "pcs"),
        ("Silkscreen Tiles", "packing", 40, "pcs"),
        ("Silkscreen Tiles", "pre_kiln_check", 60, "pcs"),
        ("Silkscreen Tiles", "engobe", 30, "pcs"),

        # Countertops
        ("Countertops", "glazing", 1.5, "sqm"),
        ("Countertops", "sorting", 3.0, "sqm"),
        ("Countertops", "packing", 2.0, "sqm"),
        ("Countertops", "pre_kiln_check", 4.0, "sqm"),
        ("Countertops", "engobe", 2.0, "sqm"),

        # Sinks
        ("Sinks", "glazing", 5, "pcs"),
        ("Sinks", "sorting", 10, "pcs"),
        ("Sinks", "packing", 8, "pcs"),
        ("Sinks", "pre_kiln_check", 12, "pcs"),
        ("Sinks", "engobe", 6, "pcs"),

        # 3D Products
        ("3D Products", "glazing", 5, "pcs"),
        ("3D Products", "sorting", 10, "pcs"),
        ("3D Products", "packing", 8, "pcs"),
        ("3D Products", "pre_kiln_check", 12, "pcs"),
        ("3D Products", "engobe", 6, "pcs"),
    ]

    for typo_name, stage, rate, unit in speeds:
        conn.execute(text("""
            INSERT INTO stage_typology_speeds
                (id, factory_id, typology_id, stage, productivity_rate,
                 rate_unit, rate_basis, time_unit)
            SELECT
                gen_random_uuid(),
                t.factory_id,
                t.id,
                :stage,
                :rate,
                :unit,
                'per_person',
                'hour'
            FROM kiln_loading_typologies t
            WHERE t.factory_id = :factory_id AND t.name = :typo_name
            ON CONFLICT (typology_id, stage) DO NOTHING
        """), {
            "factory_id": factory_id,
            "stage": stage,
            "rate": rate,
            "unit": unit,
            "typo_name": typo_name,
        })

    print(f"INFO: Migration 018 — {len(typologies)} typologies and "
          f"{len(speeds)} speed records seeded for factory {factory_id}.")


def downgrade() -> None:
    conn = op.get_bind()

    row = conn.execute(text(
        "SELECT id FROM factories WHERE name ILIKE '%bali%' LIMIT 1"
    )).fetchone()
    if not row:
        return
    factory_id = str(row[0])

    typology_names = [
        "Small Tiles Edge", "Small Tiles Flat",
        "Medium Tiles Edge", "Medium Tiles Flat",
        "Large Tiles Flat", "Raku Tiles",
        "Stencil Tiles", "Silkscreen Tiles",
        "Countertops", "Sinks", "3D Products",
    ]

    # Delete speeds first (FK cascade would handle it, but be explicit)
    conn.execute(text("""
        DELETE FROM stage_typology_speeds
        WHERE typology_id IN (
            SELECT id FROM kiln_loading_typologies
            WHERE factory_id = :fid AND name = ANY(:names)
        )
    """), {"fid": factory_id, "names": typology_names})

    conn.execute(text("""
        DELETE FROM kiln_loading_typologies
        WHERE factory_id = :fid AND name = ANY(:names)
    """), {"fid": factory_id, "names": typology_names})

    # Drop the unique constraint we added
    conn.execute(text("""
        ALTER TABLE kiln_loading_typologies
        DROP CONSTRAINT IF EXISTS uq_kiln_loading_typologies_factory_name
    """))
