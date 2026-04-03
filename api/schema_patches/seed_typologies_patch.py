"""Seed standard typologies and default speeds.

Runs AFTER table-creation patches, so kiln_loading_typologies
and stage_typology_speeds are guaranteed to exist.
Idempotent: ON CONFLICT DO NOTHING.
"""
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)


def apply(conn):
    # Check tables exist
    for tbl in ('kiln_loading_typologies', 'stage_typology_speeds', 'factories'):
        exists = conn.execute(text(
            f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{tbl}')"
        )).scalar()
        if not exists:
            logger.info("seed_typologies: table %s not found, skipping", tbl)
            return

    # Check if already seeded
    count = conn.execute(text(
        "SELECT COUNT(*) FROM kiln_loading_typologies"
    )).scalar()
    if count and count > 0:
        logger.info("seed_typologies: already seeded (%d typologies), skipping", count)
        return

    # Get Bali factory ID
    row = conn.execute(text(
        "SELECT id FROM factories WHERE name ILIKE '%bali%' LIMIT 1"
    )).fetchone()
    if not row:
        logger.warning("seed_typologies: Bali factory not found, skipping")
        return
    factory_id = str(row[0])

    # Ensure unique constraint
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

    # Typologies
    typologies = [
        ("Small Tiles Edge", '["tile"]', '["face_only"]', '[]', '[]', 5, 15, "edge", 10),
        ("Small Tiles Flat", '["tile"]', '["all_edges", "with_back"]', '[]', '[]', 5, 15, "flat", 10),
        ("Medium Tiles Edge", '["tile"]', '["face_only", "edges_1", "edges_2"]', '[]', '[]', 15, 25, "edge", 8),
        ("Medium Tiles Flat", '["tile"]', '["all_edges", "with_back"]', '[]', '[]', 15, 25, "flat", 8),
        ("Large Tiles Flat", '["tile"]', '[]', '[]', '[]', 25, 45, "flat", 6),
        ("Raku Tiles", '["tile"]', '[]', '["Raku"]', '["Raku"]', None, None, "flat", 15),
        ("Stencil Tiles", '["tile"]', '[]', '[]', '["Stencil"]', None, None, "edge", 12),
        ("Silkscreen Tiles", '["tile"]', '[]', '[]', '["Silkscreen"]', None, None, "edge", 12),
        ("Countertops", '["countertop"]', '[]', '[]', '[]', None, None, "flat", 5),
        ("Sinks", '["sink"]', '[]', '[]', '[]', None, None, "flat", 5),
        ("3D Products", '["3d"]', '[]', '[]', '[]', None, None, "flat", 5),
    ]

    for (name, ptypes, places, colls, methods, min_sz, max_sz, pref, prio) in typologies:
        conn.execute(text("""
            INSERT INTO kiln_loading_typologies
                (id, factory_id, name, product_types, place_of_application,
                 collections, methods, min_size_cm, max_size_cm,
                 preferred_loading, priority, is_active, auto_calibrate)
            VALUES
                (gen_random_uuid(), :fid, :name,
                 :pt::JSONB, :pl::JSONB, :co::JSONB, :me::JSONB,
                 :min, :max, :pref, :prio, TRUE, FALSE)
            ON CONFLICT (factory_id, name) DO NOTHING
        """), {"fid": factory_id, "name": name, "pt": ptypes, "pl": places,
               "co": colls, "me": methods, "min": min_sz, "max": max_sz,
               "pref": pref, "prio": prio})

    # Default speeds per (typology, stage)
    speeds = [
        ("Small Tiles Edge", "glazing", 60, "pcs"), ("Small Tiles Edge", "sorting", 100, "pcs"),
        ("Small Tiles Edge", "packing", 80, "pcs"), ("Small Tiles Edge", "pre_kiln_check", 120, "pcs"),
        ("Small Tiles Edge", "engobe", 70, "pcs"),
        ("Small Tiles Flat", "glazing", 40, "pcs"), ("Small Tiles Flat", "sorting", 80, "pcs"),
        ("Small Tiles Flat", "packing", 60, "pcs"), ("Small Tiles Flat", "pre_kiln_check", 100, "pcs"),
        ("Small Tiles Flat", "engobe", 50, "pcs"),
        ("Medium Tiles Edge", "glazing", 30, "pcs"), ("Medium Tiles Edge", "sorting", 60, "pcs"),
        ("Medium Tiles Edge", "packing", 45, "pcs"), ("Medium Tiles Edge", "pre_kiln_check", 70, "pcs"),
        ("Medium Tiles Edge", "engobe", 35, "pcs"),
        ("Medium Tiles Flat", "glazing", 30, "pcs"), ("Medium Tiles Flat", "sorting", 60, "pcs"),
        ("Medium Tiles Flat", "packing", 45, "pcs"), ("Medium Tiles Flat", "pre_kiln_check", 70, "pcs"),
        ("Medium Tiles Flat", "engobe", 35, "pcs"),
        ("Large Tiles Flat", "glazing", 3.5, "sqm"), ("Large Tiles Flat", "sorting", 5.0, "sqm"),
        ("Large Tiles Flat", "packing", 4.0, "sqm"), ("Large Tiles Flat", "pre_kiln_check", 6.0, "sqm"),
        ("Large Tiles Flat", "engobe", 4.0, "sqm"),
        ("Raku Tiles", "glazing", 20, "pcs"), ("Raku Tiles", "sorting", 40, "pcs"),
        ("Raku Tiles", "packing", 30, "pcs"), ("Raku Tiles", "pre_kiln_check", 50, "pcs"),
        ("Raku Tiles", "engobe", 25, "pcs"),
        ("Stencil Tiles", "glazing", 15, "pcs"), ("Stencil Tiles", "sorting", 50, "pcs"),
        ("Stencil Tiles", "packing", 40, "pcs"), ("Stencil Tiles", "pre_kiln_check", 60, "pcs"),
        ("Stencil Tiles", "engobe", 30, "pcs"),
        ("Silkscreen Tiles", "glazing", 15, "pcs"), ("Silkscreen Tiles", "sorting", 50, "pcs"),
        ("Silkscreen Tiles", "packing", 40, "pcs"), ("Silkscreen Tiles", "pre_kiln_check", 60, "pcs"),
        ("Silkscreen Tiles", "engobe", 30, "pcs"),
        ("Countertops", "glazing", 1.5, "sqm"), ("Countertops", "sorting", 3.0, "sqm"),
        ("Countertops", "packing", 2.0, "sqm"), ("Countertops", "pre_kiln_check", 4.0, "sqm"),
        ("Countertops", "engobe", 2.0, "sqm"),
        ("Sinks", "glazing", 5, "pcs"), ("Sinks", "sorting", 10, "pcs"),
        ("Sinks", "packing", 8, "pcs"), ("Sinks", "pre_kiln_check", 12, "pcs"),
        ("Sinks", "engobe", 6, "pcs"),
        ("3D Products", "glazing", 5, "pcs"), ("3D Products", "sorting", 10, "pcs"),
        ("3D Products", "packing", 8, "pcs"), ("3D Products", "pre_kiln_check", 12, "pcs"),
        ("3D Products", "engobe", 6, "pcs"),
    ]

    # Ensure unique constraint on stage_typology_speeds
    conn.execute(text("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_stage_typology_speeds_typology_stage'
            ) THEN
                ALTER TABLE stage_typology_speeds
                ADD CONSTRAINT uq_stage_typology_speeds_typology_stage
                UNIQUE (typology_id, stage);
            END IF;
        END $$;
    """))

    for typo_name, stage, rate, unit in speeds:
        conn.execute(text("""
            INSERT INTO stage_typology_speeds
                (id, factory_id, typology_id, stage, productivity_rate,
                 rate_unit, rate_basis, time_unit)
            SELECT gen_random_uuid(), t.factory_id, t.id, :stage, :rate, :unit, 'per_person', 'hour'
            FROM kiln_loading_typologies t
            WHERE t.factory_id = :fid AND t.name = :tn
            ON CONFLICT (typology_id, stage) DO NOTHING
        """), {"fid": factory_id, "stage": stage, "rate": rate, "unit": unit, "tn": typo_name})

    logger.info("Seeded %d typologies and %d speeds for Bali factory", len(typologies), len(speeds))
