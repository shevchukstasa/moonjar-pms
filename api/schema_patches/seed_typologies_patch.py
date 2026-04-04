"""Seed default speeds for existing typologies — full production process.

Runs AFTER table-creation patches. Idempotent: ON CONFLICT DO NOTHING.

Full process:
1. unpacking_sorting — Unpack from boxes, sort, lay on boards
2. engobe — Engobe application (on work tables)
3. drying_engobe — Drying on shelving racks
4. glazing — Glazing (back on work tables)
5. drying_glaze — Drying on shelving racks
6. edge_cleaning_loading — Edge cleaning + kiln loading (concurrent)
7. firing — Kiln firing
8. kiln_cooling_initial — Kiln cooling enough to unload (still hot)
9. kiln_unloading — Unload tiles from kiln
10. kiln_cooling_full — Kiln cooling to load next batch
11. tile_cooling — Tile cooling before sorting
12. sorting — Post-firing sorting
13. packing — Packing
"""
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)

# All production stages in process order
ALL_STAGES = [
    "unpacking_sorting",
    "engobe",
    "drying_engobe",
    "glazing",
    "drying_glaze",
    "edge_cleaning_loading",
    "firing",
    "kiln_cooling_initial",
    "kiln_unloading",
    "kiln_cooling_full",
    "tile_cooling",
    "sorting",
    "packing",
]


def _get_speed_map(size_class: str, is_edge: bool, is_counter_sink: bool) -> dict:
    """Return {stage: (rate, unit)} for a typology classification.

    Rates are per person per hour unless noted.
    Drying/cooling/firing times are in hours (fixed duration, not throughput).
    """
    if is_counter_sink:
        return {
            "unpacking_sorting": (2.0, "sqm"),
            "engobe": (2.0, "sqm"),
            "drying_engobe": (4.0, "hours"),     # fixed duration
            "glazing": (1.5, "sqm"),
            "drying_glaze": (6.0, "hours"),      # fixed duration
            "edge_cleaning_loading": (1.0, "sqm"),
            "firing": (12.0, "hours"),            # fixed duration
            "kiln_cooling_initial": (2.0, "hours"),
            "kiln_unloading": (1.5, "sqm"),
            "kiln_cooling_full": (4.0, "hours"),
            "tile_cooling": (2.0, "hours"),
            "sorting": (3.0, "sqm"),
            "packing": (2.0, "sqm"),
        }
    elif size_class == 'large':
        return {
            "unpacking_sorting": (5.0, "sqm"),
            "engobe": (4.0, "sqm"),
            "drying_engobe": (3.0, "hours"),
            "glazing": (3.5, "sqm"),
            "drying_glaze": (4.0, "hours"),
            "edge_cleaning_loading": (2.0, "sqm"),
            "firing": (10.0, "hours"),
            "kiln_cooling_initial": (2.0, "hours"),
            "kiln_unloading": (3.0, "sqm"),
            "kiln_cooling_full": (4.0, "hours"),
            "tile_cooling": (1.5, "hours"),
            "sorting": (5.0, "sqm"),
            "packing": (4.0, "sqm"),
        }
    elif size_class == 'small':
        if is_edge:
            return {
                "unpacking_sorting": (100, "pcs"),
                "engobe": (70, "pcs"),
                "drying_engobe": (3.0, "hours"),
                "glazing": (60, "pcs"),
                "drying_glaze": (4.0, "hours"),
                "edge_cleaning_loading": (40, "pcs"),
                "firing": (8.0, "hours"),
                "kiln_cooling_initial": (1.5, "hours"),
                "kiln_unloading": (80, "pcs"),
                "kiln_cooling_full": (3.0, "hours"),
                "tile_cooling": (1.0, "hours"),
                "sorting": (100, "pcs"),
                "packing": (80, "pcs"),
            }
        else:
            return {
                "unpacking_sorting": (80, "pcs"),
                "engobe": (50, "pcs"),
                "drying_engobe": (3.0, "hours"),
                "glazing": (40, "pcs"),
                "drying_glaze": (4.0, "hours"),
                "edge_cleaning_loading": (30, "pcs"),
                "firing": (8.0, "hours"),
                "kiln_cooling_initial": (1.5, "hours"),
                "kiln_unloading": (60, "pcs"),
                "kiln_cooling_full": (3.0, "hours"),
                "tile_cooling": (1.0, "hours"),
                "sorting": (80, "pcs"),
                "packing": (60, "pcs"),
            }
    else:
        # Medium
        if is_edge:
            return {
                "unpacking_sorting": (60, "pcs"),
                "engobe": (35, "pcs"),
                "drying_engobe": (3.0, "hours"),
                "glazing": (30, "pcs"),
                "drying_glaze": (5.0, "hours"),
                "edge_cleaning_loading": (25, "pcs"),
                "firing": (9.0, "hours"),
                "kiln_cooling_initial": (2.0, "hours"),
                "kiln_unloading": (50, "pcs"),
                "kiln_cooling_full": (3.5, "hours"),
                "tile_cooling": (1.5, "hours"),
                "sorting": (60, "pcs"),
                "packing": (45, "pcs"),
            }
        else:
            return {
                "unpacking_sorting": (50, "pcs"),
                "engobe": (35, "pcs"),
                "drying_engobe": (3.0, "hours"),
                "glazing": (30, "pcs"),
                "drying_glaze": (5.0, "hours"),
                "edge_cleaning_loading": (20, "pcs"),
                "firing": (9.0, "hours"),
                "kiln_cooling_initial": (2.0, "hours"),
                "kiln_unloading": (40, "pcs"),
                "kiln_cooling_full": (3.5, "hours"),
                "tile_cooling": (1.5, "hours"),
                "sorting": (60, "pcs"),
                "packing": (45, "pcs"),
            }


def apply(conn):
    # Check tables exist
    for tbl in ('kiln_loading_typologies', 'stage_typology_speeds', 'factories'):
        exists = conn.execute(text(
            f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{tbl}')"
        )).scalar()
        if not exists:
            logger.info("seed_typologies: table %s not found, skipping", tbl)
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

    # Check how many stages the existing speeds cover
    # If old data (only 5 stages), we need to add the new stages
    existing_stages = conn.execute(text(
        "SELECT DISTINCT stage FROM stage_typology_speeds WHERE factory_id = :fid"
    ), {"fid": factory_id}).fetchall()
    existing_stage_set = {r[0] for r in existing_stages}
    new_stages = set(ALL_STAGES) - existing_stage_set

    if not new_stages and existing_stage_set:
        logger.info("seed_typologies: all %d stages already seeded, skipping", len(ALL_STAGES))
        return

    # Determine which stages to seed
    stages_to_seed = new_stages if existing_stage_set else set(ALL_STAGES)

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

    inserted = 0

    for typo_id, typo_name, pref_loading in typos:
        typo_id = str(typo_id)
        name_lower = typo_name.lower()

        is_edge = 'edge' in name_lower or 'topface' in name_lower
        is_counter_sink = 'countertop' in name_lower or 'sink' in name_lower

        # Determine size class from name
        size_class = 'medium'
        if any(s in name_lower for s in ['5x20', '10x10', 'small']):
            size_class = 'small'
        elif any(s in name_lower for s in ['20x20', '20x40', 'large']):
            size_class = 'large'
        elif any(s in name_lower for s in ['10x20', '10x40', 'medium']):
            size_class = 'medium'

        speed_map = _get_speed_map(size_class, is_edge, is_counter_sink)

        for stage in stages_to_seed:
            if stage not in speed_map:
                continue
            rate, unit = speed_map[stage]
            # For fixed-duration stages (drying, cooling, firing), use 'hours' unit
            # rate_basis = 'fixed' for time-based, 'per_person' for throughput
            is_fixed = unit == "hours"
            conn.execute(text("""
                INSERT INTO stage_typology_speeds
                    (id, factory_id, typology_id, stage, productivity_rate,
                     rate_unit, rate_basis, time_unit)
                VALUES
                    (gen_random_uuid(), :fid, :tid, :stage, :rate,
                     :unit, :basis, :tunit)
                ON CONFLICT (typology_id, stage) DO NOTHING
            """), {
                "fid": factory_id, "tid": typo_id, "stage": stage,
                "rate": rate, "unit": "hours" if is_fixed else unit,
                "basis": "fixed_duration" if is_fixed else "per_person",
                "tunit": "hours" if is_fixed else "hour",
            })
            inserted += 1

    logger.info("Seeded %d speed records for %d typologies across %d new stages (factory %s)",
                inserted, len(typos), len(stages_to_seed), factory_id)
