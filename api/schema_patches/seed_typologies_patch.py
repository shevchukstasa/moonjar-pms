"""Seed default speeds for existing typologies.

Runs AFTER table-creation patches. Idempotent: ON CONFLICT DO NOTHING.
Handles both old-style (size-based) and new-style (category-based) typology names.
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

    # Check if speeds already seeded
    speed_count = conn.execute(text(
        "SELECT COUNT(*) FROM stage_typology_speeds"
    )).scalar()
    if speed_count and speed_count > 0:
        logger.info("seed_typologies: already have %d speeds, skipping", speed_count)
        return

    # Get Bali factory ID
    row = conn.execute(text(
        "SELECT id FROM factories WHERE name ILIKE '%bali%' LIMIT 1"
    )).fetchone()
    if not row:
        logger.warning("seed_typologies: Bali factory not found, skipping")
        return
    factory_id = str(row[0])

    # Get all typologies for this factory
    typos = conn.execute(text(
        "SELECT id, name, preferred_loading FROM kiln_loading_typologies WHERE factory_id = :fid"
    ), {"fid": factory_id}).fetchall()

    if not typos:
        logger.info("seed_typologies: no typologies found for factory, skipping")
        return

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

    stages = ["glazing", "sorting", "packing", "pre_kiln_check", "engobe"]
    inserted = 0

    for typo_id, typo_name, pref_loading in typos:
        typo_id = str(typo_id)
        name_lower = typo_name.lower()

        # Determine speed based on typology name/size
        # Size-based names: "Tile 10x10 edge loading", "Tile 20x40 flat (all edges)"
        # Category names: "Small Tiles Edge", "Countertops"
        is_edge = 'edge' in name_lower
        is_counter_sink = 'countertop' in name_lower or 'sink' in name_lower

        # Determine size class from name
        size_class = 'medium'  # default
        if any(s in name_lower for s in ['5x20', '10x10', 'small']):
            size_class = 'small'
        elif any(s in name_lower for s in ['20x20', '20x40', 'large']):
            size_class = 'large'
        elif any(s in name_lower for s in ['10x20', '10x40', 'medium']):
            size_class = 'medium'

        if is_counter_sink:
            # sqm-based speeds for countertops/sinks
            speed_map = {
                "glazing": (1.5, "sqm"), "sorting": (3.0, "sqm"),
                "packing": (2.0, "sqm"), "pre_kiln_check": (4.0, "sqm"),
                "engobe": (2.0, "sqm"),
            }
        elif size_class == 'large':
            # Large tiles — sqm
            speed_map = {
                "glazing": (3.5, "sqm"), "sorting": (5.0, "sqm"),
                "packing": (4.0, "sqm"), "pre_kiln_check": (6.0, "sqm"),
                "engobe": (4.0, "sqm"),
            }
        elif size_class == 'small':
            if is_edge:
                speed_map = {
                    "glazing": (60, "pcs"), "sorting": (100, "pcs"),
                    "packing": (80, "pcs"), "pre_kiln_check": (120, "pcs"),
                    "engobe": (70, "pcs"),
                }
            else:
                speed_map = {
                    "glazing": (40, "pcs"), "sorting": (80, "pcs"),
                    "packing": (60, "pcs"), "pre_kiln_check": (100, "pcs"),
                    "engobe": (50, "pcs"),
                }
        else:
            # Medium
            if is_edge:
                speed_map = {
                    "glazing": (30, "pcs"), "sorting": (60, "pcs"),
                    "packing": (45, "pcs"), "pre_kiln_check": (70, "pcs"),
                    "engobe": (35, "pcs"),
                }
            else:
                speed_map = {
                    "glazing": (30, "pcs"), "sorting": (60, "pcs"),
                    "packing": (45, "pcs"), "pre_kiln_check": (70, "pcs"),
                    "engobe": (35, "pcs"),
                }

        for stage in stages:
            rate, unit = speed_map[stage]
            conn.execute(text("""
                INSERT INTO stage_typology_speeds
                    (id, factory_id, typology_id, stage, productivity_rate,
                     rate_unit, rate_basis, time_unit)
                VALUES
                    (gen_random_uuid(), :fid, :tid, :stage, :rate, :unit, 'per_person', 'hour')
                ON CONFLICT (typology_id, stage) DO NOTHING
            """), {"fid": factory_id, "tid": typo_id, "stage": stage,
                   "rate": rate, "unit": unit})
            inserted += 1

    logger.info("Seeded %d speed records for %d typologies (factory %s)",
                inserted, len(typos), factory_id)
