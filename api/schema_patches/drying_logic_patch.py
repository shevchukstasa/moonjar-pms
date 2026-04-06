"""Fix drying stage logic: rate_unit pcs→hours, seed drying rack resources.

Drying stages use fixed_duration basis where productivity_rate = hours per cycle.
The rate_unit should be 'hours' (not 'pcs' which is meaningless for drying).

Also seeds default drying rack resources for Bali factory if none exist,
so the scheduler can calculate drying capacity properly:
  tiles_per_cycle = rack_board_slots × tiles_per_board
  cycles = ceil(total_pcs / tiles_per_cycle)
  total_hours = cycles × fixed_hours_per_cycle
"""
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)


def apply(conn) -> None:
    """Fix drying stage speeds and seed drying rack resources.

    Called from main.py startup with engine.connect() context.
    Caller handles commit.
    """

    # ── 1. Fix rate_unit for drying stages ──────────────────────────
    updated = conn.execute(text("""
        UPDATE stage_typology_speeds
        SET rate_unit = 'hours'
        WHERE stage IN ('drying_engobe', 'drying_glaze')
          AND rate_basis = 'fixed_duration'
          AND rate_unit != 'hours'
    """))
    if updated.rowcount > 0:
        logger.info("DRYING_PATCH | Updated %d drying speeds: rate_unit → 'hours'", updated.rowcount)

    # ── 2. Seed drying rack resources for Bali ──────────────────────
    # Check if drying racks already exist for any factory
    existing = conn.execute(text("""
        SELECT COUNT(*) FROM production_line_resources
        WHERE resource_type = 'drying_rack' AND is_active = true
    """)).scalar()

    if existing == 0:
        # Get Bali factory ID
        bali_id = conn.execute(text("""
            SELECT id FROM factories WHERE LOWER(name) LIKE '%bali%' LIMIT 1
        """)).scalar()

        if bali_id:
            # Default drying rack setup for a typical tile factory:
            # 4 drying racks, each holds 20 boards (glazing boards with tiles)
            # Total capacity: 4 x 20 = 80 boards per drying cycle
            conn.execute(text("""
                INSERT INTO production_line_resources
                    (id, factory_id, resource_type, name, capacity_boards, num_units, is_active)
                VALUES
                    (gen_random_uuid(), :fid, 'drying_rack', 'Drying Rack 1', 20, 1, true),
                    (gen_random_uuid(), :fid, 'drying_rack', 'Drying Rack 2', 20, 1, true),
                    (gen_random_uuid(), :fid, 'drying_rack', 'Drying Rack 3', 20, 1, true),
                    (gen_random_uuid(), :fid, 'drying_rack', 'Drying Rack 4', 20, 1, true)
            """), {"fid": str(bali_id)})
            logger.info("DRYING_PATCH | Seeded 4 drying racks (80 board slots) for Bali factory")
        else:
            logger.warning("DRYING_PATCH | Bali factory not found, skipping rack seed")

    else:
        logger.info("DRYING_PATCH | %d drying racks already exist, skipping seed", existing)

    logger.info("DRYING_PATCH | Complete")
