"""Cleanup typologies: create 13 clean typologies with full 14-stage speeds.

Idempotent: checks if cleanup already done by looking for exact typology names.

13 typologies:
 Tiles (by size × glaze coverage):
  1. Small Tile topface glaze or +1 edge  (≤15cm, face/1-2 edges)
  2. Small Tile flat (2-4 edge)           (≤15cm, all edges/back)
  3. Large Tile topface glaze or +1 edge  (>15cm, face/1-2 edges)
  4. Large Tile flat (2-4 edge)           (>15cm, all edges/back)
 Specialty tiles (also split by size):
  5. Small Stencil Tile   (≤15cm)
  6. Large Stencil Tile   (>15cm)
  7. Small Silkscreen Tile (≤15cm)
  8. Large Silkscreen Tile (>15cm)
 Countertops (by area):
  9. Countertop Small (≤0.4 m²)
  10. Countertop Large (>0.4 m²)
 Sinks (by glaze coverage):
  11. Sink topface
  12. Sink topface + edges
 Other:
  13. 3D Product
"""
import json
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)

ALL_STAGES = [
    "unpacking_sorting", "engobe", "drying_engobe", "glazing", "drying_glaze",
    "edge_cleaning_loading", "pre_kiln_check", "firing", "kiln_cooling_initial",
    "kiln_unloading", "kiln_cooling_full", "tile_cooling", "sorting", "packing",
]

SPEEDS = {
    # ── Small tiles: high pcs/h throughput ────────────────────────
    "small_topface": {
        # face_only or +1 edge — fast, edge loading
        "unpacking_sorting": (100, "per_person"), "engobe": (70, "per_person"),
        "drying_engobe": (3.0, "fixed_duration"), "glazing": (60, "per_person"),
        "drying_glaze": (4.0, "fixed_duration"), "edge_cleaning_loading": (40, "per_person"),
        "pre_kiln_check": (120, "per_person"), "firing": (8.0, "fixed_duration"),
        "kiln_cooling_initial": (1.5, "fixed_duration"), "kiln_unloading": (80, "per_person"),
        "kiln_cooling_full": (3.0, "fixed_duration"), "tile_cooling": (1.0, "fixed_duration"),
        "sorting": (100, "per_person"), "packing": (80, "per_person"),
    },
    "small_flat": {
        # all edges / with back — slower, flat loading, more glaze work
        "unpacking_sorting": (80, "per_person"), "engobe": (50, "per_person"),
        "drying_engobe": (3.0, "fixed_duration"), "glazing": (40, "per_person"),
        "drying_glaze": (4.0, "fixed_duration"), "edge_cleaning_loading": (30, "per_person"),
        "pre_kiln_check": (100, "per_person"), "firing": (8.0, "fixed_duration"),
        "kiln_cooling_initial": (1.5, "fixed_duration"), "kiln_unloading": (60, "per_person"),
        "kiln_cooling_full": (3.0, "fixed_duration"), "tile_cooling": (1.0, "fixed_duration"),
        "sorting": (80, "per_person"), "packing": (60, "per_person"),
    },
    # ── Large tiles: lower pcs/h, longer firing ──────────────────
    "large_topface": {
        "unpacking_sorting": (60, "per_person"), "engobe": (35, "per_person"),
        "drying_engobe": (3.0, "fixed_duration"), "glazing": (30, "per_person"),
        "drying_glaze": (5.0, "fixed_duration"), "edge_cleaning_loading": (25, "per_person"),
        "pre_kiln_check": (70, "per_person"), "firing": (9.0, "fixed_duration"),
        "kiln_cooling_initial": (2.0, "fixed_duration"), "kiln_unloading": (50, "per_person"),
        "kiln_cooling_full": (3.5, "fixed_duration"), "tile_cooling": (1.5, "fixed_duration"),
        "sorting": (60, "per_person"), "packing": (45, "per_person"),
    },
    "large_flat": {
        "unpacking_sorting": (50, "per_person"), "engobe": (35, "per_person"),
        "drying_engobe": (3.0, "fixed_duration"), "glazing": (30, "per_person"),
        "drying_glaze": (5.0, "fixed_duration"), "edge_cleaning_loading": (20, "per_person"),
        "pre_kiln_check": (70, "per_person"), "firing": (10.0, "fixed_duration"),
        "kiln_cooling_initial": (2.0, "fixed_duration"), "kiln_unloading": (40, "per_person"),
        "kiln_cooling_full": (4.0, "fixed_duration"), "tile_cooling": (1.5, "fixed_duration"),
        "sorting": (60, "per_person"), "packing": (45, "per_person"),
    },
    # ── Stencil tiles: slower glazing due to stencil application ──
    "small_stencil": {
        # Small stencil ≤15cm — faster handling than large
        "unpacking_sorting": (40, "per_person"), "engobe": (35, "per_person"),
        "drying_engobe": (3.0, "fixed_duration"), "glazing": (18, "per_person"),
        "drying_glaze": (5.0, "fixed_duration"), "edge_cleaning_loading": (25, "per_person"),
        "pre_kiln_check": (70, "per_person"), "firing": (8.0, "fixed_duration"),
        "kiln_cooling_initial": (1.5, "fixed_duration"), "kiln_unloading": (50, "per_person"),
        "kiln_cooling_full": (3.0, "fixed_duration"), "tile_cooling": (1.0, "fixed_duration"),
        "sorting": (60, "per_person"), "packing": (50, "per_person"),
    },
    "large_stencil": {
        # Large stencil >15cm — slower, heavier tiles
        "unpacking_sorting": (25, "per_person"), "engobe": (25, "per_person"),
        "drying_engobe": (3.0, "fixed_duration"), "glazing": (12, "per_person"),
        "drying_glaze": (5.5, "fixed_duration"), "edge_cleaning_loading": (18, "per_person"),
        "pre_kiln_check": (50, "per_person"), "firing": (9.0, "fixed_duration"),
        "kiln_cooling_initial": (2.0, "fixed_duration"), "kiln_unloading": (35, "per_person"),
        "kiln_cooling_full": (3.5, "fixed_duration"), "tile_cooling": (1.5, "fixed_duration"),
        "sorting": (40, "per_person"), "packing": (35, "per_person"),
    },
    # ── Silkscreen tiles: slower glazing due to silkscreen application ──
    "small_silkscreen": {
        # Small silkscreen ≤15cm
        "unpacking_sorting": (40, "per_person"), "engobe": (35, "per_person"),
        "drying_engobe": (3.0, "fixed_duration"), "glazing": (18, "per_person"),
        "drying_glaze": (5.0, "fixed_duration"), "edge_cleaning_loading": (25, "per_person"),
        "pre_kiln_check": (70, "per_person"), "firing": (8.0, "fixed_duration"),
        "kiln_cooling_initial": (1.5, "fixed_duration"), "kiln_unloading": (50, "per_person"),
        "kiln_cooling_full": (3.0, "fixed_duration"), "tile_cooling": (1.0, "fixed_duration"),
        "sorting": (60, "per_person"), "packing": (50, "per_person"),
    },
    "large_silkscreen": {
        # Large silkscreen >15cm
        "unpacking_sorting": (25, "per_person"), "engobe": (25, "per_person"),
        "drying_engobe": (3.0, "fixed_duration"), "glazing": (12, "per_person"),
        "drying_glaze": (5.5, "fixed_duration"), "edge_cleaning_loading": (18, "per_person"),
        "pre_kiln_check": (50, "per_person"), "firing": (9.0, "fixed_duration"),
        "kiln_cooling_initial": (2.0, "fixed_duration"), "kiln_unloading": (35, "per_person"),
        "kiln_cooling_full": (3.5, "fixed_duration"), "tile_cooling": (1.5, "fixed_duration"),
        "sorting": (40, "per_person"), "packing": (35, "per_person"),
    },
    # ── Countertops: sqm-based, heavy, slow ──────────────────────
    "countertop_small": {
        "unpacking_sorting": (3.0, "per_person"), "engobe": (2.5, "per_person"),
        "drying_engobe": (4.0, "fixed_duration"), "glazing": (2.0, "per_person"),
        "drying_glaze": (6.0, "fixed_duration"), "edge_cleaning_loading": (1.5, "per_person"),
        "pre_kiln_check": (5.0, "per_person"), "firing": (12.0, "fixed_duration"),
        "kiln_cooling_initial": (2.0, "fixed_duration"), "kiln_unloading": (2.0, "per_person"),
        "kiln_cooling_full": (4.0, "fixed_duration"), "tile_cooling": (2.0, "fixed_duration"),
        "sorting": (4.0, "per_person"), "packing": (3.0, "per_person"),
    },
    "countertop_large": {
        "unpacking_sorting": (1.5, "per_person"), "engobe": (1.5, "per_person"),
        "drying_engobe": (5.0, "fixed_duration"), "glazing": (1.0, "per_person"),
        "drying_glaze": (7.0, "fixed_duration"), "edge_cleaning_loading": (0.8, "per_person"),
        "pre_kiln_check": (3.0, "per_person"), "firing": (12.0, "fixed_duration"),
        "kiln_cooling_initial": (2.0, "fixed_duration"), "kiln_unloading": (1.2, "per_person"),
        "kiln_cooling_full": (4.0, "fixed_duration"), "tile_cooling": (2.0, "fixed_duration"),
        "sorting": (2.5, "per_person"), "packing": (1.5, "per_person"),
    },
    # ── Sinks: pcs-based ─────────────────────────────────────────
    "sink_topface": {
        # Only top surface glazed — faster
        "unpacking_sorting": (8.0, "per_person"), "engobe": (6.0, "per_person"),
        "drying_engobe": (4.0, "fixed_duration"), "glazing": (5.0, "per_person"),
        "drying_glaze": (6.0, "fixed_duration"), "edge_cleaning_loading": (4.0, "per_person"),
        "pre_kiln_check": (12.0, "per_person"), "firing": (12.0, "fixed_duration"),
        "kiln_cooling_initial": (2.0, "fixed_duration"), "kiln_unloading": (6.0, "per_person"),
        "kiln_cooling_full": (4.0, "fixed_duration"), "tile_cooling": (2.0, "fixed_duration"),
        "sorting": (10.0, "per_person"), "packing": (8.0, "per_person"),
    },
    "sink_edges": {
        # Top + edges — slower glazing, more edge work
        "unpacking_sorting": (6.0, "per_person"), "engobe": (4.0, "per_person"),
        "drying_engobe": (5.0, "fixed_duration"), "glazing": (3.0, "per_person"),
        "drying_glaze": (7.0, "fixed_duration"), "edge_cleaning_loading": (2.0, "per_person"),
        "pre_kiln_check": (10.0, "per_person"), "firing": (12.0, "fixed_duration"),
        "kiln_cooling_initial": (2.0, "fixed_duration"), "kiln_unloading": (5.0, "per_person"),
        "kiln_cooling_full": (4.0, "fixed_duration"), "tile_cooling": (2.0, "fixed_duration"),
        "sorting": (8.0, "per_person"), "packing": (6.0, "per_person"),
    },
    # ── 3D Products ──────────────────────────────────────────────
    "3d": {
        "unpacking_sorting": (6.0, "per_person"), "engobe": (6.0, "per_person"),
        "drying_engobe": (4.0, "fixed_duration"), "glazing": (5.0, "per_person"),
        "drying_glaze": (6.0, "fixed_duration"), "edge_cleaning_loading": (3.0, "per_person"),
        "pre_kiln_check": (12.0, "per_person"), "firing": (12.0, "fixed_duration"),
        "kiln_cooling_initial": (2.0, "fixed_duration"), "kiln_unloading": (6.0, "per_person"),
        "kiln_cooling_full": (4.0, "fixed_duration"), "tile_cooling": (2.0, "fixed_duration"),
        "sorting": (10.0, "per_person"), "packing": (8.0, "per_person"),
    },
}

TYPOLOGIES = [
    # ── Stencil tiles (highest priority — matched first, split by size) ──
    {"name": "Small Stencil Tile", "product_types": ["tile"],
     "place_of_application": [],
     "collections": ["Stencil"], "methods": ["Stencil"],
     "min_size_cm": 3, "max_size_cm": 15, "max_short_side_cm": None,
     "preferred_loading": "edge", "priority": 12, "speed_key": "small_stencil"},
    {"name": "Large Stencil Tile", "product_types": ["tile"],
     "place_of_application": [],
     "collections": ["Stencil"], "methods": ["Stencil"],
     "min_size_cm": 15, "max_size_cm": 100, "max_short_side_cm": None,
     "preferred_loading": "edge", "priority": 12, "speed_key": "large_stencil"},
    # ── Silkscreen tiles (highest priority, split by size) ────────
    {"name": "Small Silkscreen Tile", "product_types": ["tile"],
     "place_of_application": [],
     "collections": ["Silkscreen"], "methods": ["Silkscreen"],
     "min_size_cm": 3, "max_size_cm": 15, "max_short_side_cm": None,
     "preferred_loading": "edge", "priority": 12, "speed_key": "small_silkscreen"},
    {"name": "Large Silkscreen Tile", "product_types": ["tile"],
     "place_of_application": [],
     "collections": ["Silkscreen"], "methods": ["Silkscreen"],
     "min_size_cm": 15, "max_size_cm": 100, "max_short_side_cm": None,
     "preferred_loading": "edge", "priority": 12, "speed_key": "large_silkscreen"},

    # ── Small tiles (≤15cm) ──────────────────────────────────────
    {"name": "Small Tile topface glaze or +1 edge", "product_types": ["tile"],
     "place_of_application": ["face_only", "edges_1", "edges_2"],
     "collections": [], "methods": [],
     "min_size_cm": 3, "max_size_cm": 15, "max_short_side_cm": None,
     "preferred_loading": "edge", "priority": 10, "speed_key": "small_topface"},
    {"name": "Small Tile flat (2-4 edge)", "product_types": ["tile"],
     "place_of_application": ["all_edges", "with_back"],
     "collections": [], "methods": [],
     "min_size_cm": 3, "max_size_cm": 15, "max_short_side_cm": None,
     "preferred_loading": "flat", "priority": 10, "speed_key": "small_flat"},

    # ── Large tiles (>15cm) ──────────────────────────────────────
    {"name": "Large Tile topface glaze or +1 edge", "product_types": ["tile"],
     "place_of_application": ["face_only", "edges_1", "edges_2"],
     "collections": [], "methods": [],
     "min_size_cm": 15, "max_size_cm": 100, "max_short_side_cm": None,
     "preferred_loading": "edge", "priority": 8, "speed_key": "large_topface"},
    {"name": "Large Tile flat (2-4 edge)", "product_types": ["tile"],
     "place_of_application": ["all_edges", "with_back"],
     "collections": [], "methods": [],
     "min_size_cm": 15, "max_size_cm": 100, "max_short_side_cm": None,
     "preferred_loading": "flat", "priority": 8, "speed_key": "large_flat"},

    # ── Countertops ──────────────────────────────────────────────
    {"name": "Countertop Small (\u22640.4 m\u00b2)", "product_types": ["countertop"],
     "place_of_application": [],
     "collections": [], "methods": [],
     "min_size_cm": None, "max_size_cm": 63, "max_short_side_cm": None,
     "preferred_loading": "flat", "priority": 6, "speed_key": "countertop_small"},
    {"name": "Countertop Large (>0.4 m\u00b2)", "product_types": ["countertop"],
     "place_of_application": [],
     "collections": [], "methods": [],
     "min_size_cm": 63, "max_size_cm": None, "max_short_side_cm": None,
     "preferred_loading": "flat", "priority": 5, "speed_key": "countertop_large"},

    # ── Sinks ────────────────────────────────────────────────────
    {"name": "Sink topface", "product_types": ["sink"],
     "place_of_application": ["face_only"],
     "collections": [], "methods": [],
     "min_size_cm": None, "max_size_cm": None, "max_short_side_cm": None,
     "preferred_loading": "flat", "priority": 6, "speed_key": "sink_topface"},
    {"name": "Sink topface + edges", "product_types": ["sink"],
     "place_of_application": ["edges_1", "edges_2", "all_edges", "with_back"],
     "collections": [], "methods": [],
     "min_size_cm": None, "max_size_cm": None, "max_short_side_cm": None,
     "preferred_loading": "flat", "priority": 5, "speed_key": "sink_edges"},

    # ── 3D Products ──────────────────────────────────────────────
    {"name": "3D Product", "product_types": ["3d"],
     "place_of_application": [],
     "collections": [], "methods": [],
     "min_size_cm": None, "max_size_cm": None, "max_short_side_cm": None,
     "preferred_loading": "flat", "priority": 5, "speed_key": "3d"},
]

EXPECTED_NAMES = {t["name"] for t in TYPOLOGIES}


def run(conn):
    """Idempotent: skip if clean typologies already exist."""
    for tbl in ('kiln_loading_typologies', 'stage_typology_speeds'):
        exists = conn.execute(text(
            f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{tbl}')"
        )).scalar()
        if not exists:
            logger.info("cleanup_typologies: table %s not found, skipping", tbl)
            return

    row = conn.execute(text(
        "SELECT id FROM factories WHERE name ILIKE '%bali%' LIMIT 1"
    )).fetchone()
    if not row:
        logger.warning("cleanup_typologies: Bali factory not found")
        return
    factory_id = str(row[0])

    # Idempotency check: if exactly our typologies exist with speeds, skip
    existing = conn.execute(text(
        "SELECT name FROM kiln_loading_typologies WHERE factory_id = :fid AND is_active = true"
    ), {"fid": factory_id}).fetchall()
    existing_names = {r[0] for r in existing}

    if existing_names == EXPECTED_NAMES and len(existing_names) == len(TYPOLOGIES):
        speed_count = conn.execute(text(
            "SELECT COUNT(*) FROM stage_typology_speeds WHERE factory_id = :fid"
        ), {"fid": factory_id}).scalar()
        if speed_count >= len(TYPOLOGIES) * 13:
            logger.info("cleanup_typologies: already clean (%d typologies, %d speeds)",
                       len(existing_names), speed_count)
            return

    logger.info("cleanup_typologies: need update — existing=%d expected=%d, diff=%s",
               len(existing_names), len(EXPECTED_NAMES),
               (EXPECTED_NAMES - existing_names) or "names match but speeds missing")

    # ── Cleanup (safe even if already empty) ─────────────────────
    conn.execute(text(
        "DELETE FROM stage_typology_speeds WHERE factory_id = :fid"
    ), {"fid": factory_id})
    conn.execute(text("""
        DELETE FROM kiln_typology_capacities
        WHERE typology_id IN (SELECT id FROM kiln_loading_typologies WHERE factory_id = :fid)
    """), {"fid": factory_id})
    conn.execute(text(
        "DELETE FROM kiln_loading_typologies WHERE factory_id = :fid"
    ), {"fid": factory_id})
    logger.info("cleanup_typologies: cleaned old data")

    # ── Create ───────────────────────────────────────────────────
    for t in TYPOLOGIES:
        conn.execute(text("""
            INSERT INTO kiln_loading_typologies (
                factory_id, name, product_types, place_of_application,
                collections, methods, min_size_cm, max_size_cm,
                max_short_side_cm, preferred_loading, priority,
                shift_count, auto_calibrate, is_active
            ) VALUES (
                CAST(:fid AS uuid), :name,
                CAST(:pt AS jsonb), CAST(:poa AS jsonb),
                CAST(:coll AS jsonb), CAST(:meth AS jsonb),
                :min_s, :max_s, :max_short, :pref, :prio,
                2, false, true
            )
        """), {
            "fid": factory_id, "name": t["name"],
            "pt": json.dumps(t["product_types"]),
            "poa": json.dumps(t["place_of_application"]),
            "coll": json.dumps(t["collections"]),
            "meth": json.dumps(t["methods"]),
            "min_s": t["min_size_cm"], "max_s": t["max_size_cm"],
            "max_short": t["max_short_side_cm"],
            "pref": t["preferred_loading"], "prio": t["priority"],
        })

    new_typos = conn.execute(text(
        "SELECT id, name FROM kiln_loading_typologies WHERE factory_id = :fid"
    ), {"fid": factory_id}).fetchall()

    name_to_key = {t["name"]: t["speed_key"] for t in TYPOLOGIES}
    total = 0
    for tid, tname in new_typos:
        key = name_to_key.get(tname)
        if not key or key not in SPEEDS:
            continue
        for stage, (rate, basis) in SPEEDS[key].items():
            conn.execute(text("""
                INSERT INTO stage_typology_speeds (typology_id, factory_id, stage, productivity_rate, rate_basis)
                VALUES (CAST(:tid AS uuid), CAST(:fid AS uuid), :stage, :rate, :basis)
            """), {"tid": str(tid), "fid": factory_id, "stage": stage, "rate": rate, "basis": basis})
            total += 1

    logger.info("cleanup_typologies: created %d typologies, %d speeds",
               len(TYPOLOGIES), total)
