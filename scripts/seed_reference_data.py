"""
Seed reference data: collections, colors, sizes, production stages,
material groups/subgroups, application methods, application collections.

Idempotent — safe to run multiple times (uses INSERT ON CONFLICT DO NOTHING
via merge-or-check pattern).

Run after database creation:
    python scripts/seed_reference_data.py
"""
import sys
import os
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from api.database import SessionLocal
from api.models import (
    Collection, Color, Size, ProductionStage,
    MaterialGroup, MaterialSubgroup,
    ApplicationMethod, ApplicationCollection,
)


# ═══════════════════════════════════════════════════════════════════════════
#  Reference data definitions
# ═══════════════════════════════════════════════════════════════════════════

COLLECTIONS = [
    "Classic", "Modern", "Raku", "Terrazzo", "Zellige",
    "Encaustic", "Moroccan", "Subway", "Hexagon", "Penny",
]

COLORS = [
    # (name, code, is_basic)
    ("White", "WHT", True),
    ("Ivory", "IVR", True),
    ("Cream", "CRM", True),
    ("Beige", "BGE", True),
    ("Sand", "SND", False),
    ("Grey", "GRY", True),
    ("Charcoal", "CHR", False),
    ("Black", "BLK", True),
    ("Navy", "NVY", False),
    ("Blue", "BLU", False),
    ("Green", "GRN", False),
    ("Sage", "SGE", False),
    ("Terracotta", "TRC", False),
    ("Rust", "RST", False),
    ("Pink", "PNK", False),
    ("Blush", "BLS", False),
    ("Mustard", "MSD", False),
    ("Olive", "OLV", False),
    ("Teal", "TEA", False),
    ("Burgundy", "BRG", False),
]

# (name, width_mm, height_mm, thickness_mm, shape)
SIZES = [
    ("5x5", 50, 50, 11, "square"),
    ("7.5x15", 75, 150, 11, "rectangle"),
    ("10x10", 100, 100, 11, "square"),
    ("10x20", 100, 200, 11, "rectangle"),
    ("10x30", 100, 300, 11, "rectangle"),
    ("15x15", 150, 150, 11, "square"),
    ("20x20", 200, 200, 11, "square"),
    ("20x40", 200, 400, 11, "rectangle"),
    ("30x30", 300, 300, 11, "square"),
    ("30x60", 300, 600, 11, "rectangle"),
    ("40x40", 400, 400, 11, "square"),
    ("45x45", 450, 450, 11, "square"),
    ("60x60", 600, 600, 11, "square"),
    ("60x120", 600, 1200, 11, "rectangle"),
]

PRODUCTION_STAGES = [
    ("Incoming Inspection", 1),
    ("Engobe Application", 2),
    ("Engobe Check", 3),
    ("Glazing", 4),
    ("Pre-Kiln Check", 5),
    ("Kiln Loading", 6),
    ("Firing", 7),
    ("Sorting", 8),
    ("Packing", 9),
    ("Quality Check", 10),
]

# Material groups → subgroups hierarchy
MATERIAL_GROUPS = [
    {
        "code": "tile_materials",
        "name": "Tile Materials",
        "description": "Raw materials for tile production",
        "icon": "🧱",
        "display_order": 1,
        "subgroups": [
            {"code": "stone", "name": "Stone (Bisque)", "description": "Base lava stone tiles", "icon": "🪨", "default_lead_time_days": 14, "default_unit": "pcs", "display_order": 1},
            {"code": "pigment", "name": "Pigments", "description": "Color pigments for glazes", "icon": "🎨", "default_lead_time_days": 35, "default_unit": "kg", "display_order": 2},
            {"code": "frit", "name": "Frits", "description": "Glass frits for glazes", "icon": "✨", "default_lead_time_days": 35, "default_unit": "kg", "display_order": 3},
            {"code": "oxide_carbonate", "name": "Oxides & Carbonates", "description": "Metal oxides and carbonates", "icon": "⚗️", "default_lead_time_days": 35, "default_unit": "kg", "display_order": 4},
            {"code": "other_bulk", "name": "Other Bulk Materials", "description": "Other dry/bulk materials", "icon": "📦", "default_lead_time_days": 21, "default_unit": "kg", "display_order": 5},
        ],
    },
    {
        "code": "packaging",
        "name": "Packaging",
        "description": "Packaging materials for shipping",
        "icon": "📦",
        "display_order": 2,
        "subgroups": [
            {"code": "boxes", "name": "Boxes", "description": "Cardboard boxes", "icon": "📦", "default_lead_time_days": 7, "default_unit": "pcs", "display_order": 1},
            {"code": "pallets", "name": "Pallets", "description": "Wooden pallets", "icon": "🪵", "default_lead_time_days": 7, "default_unit": "pcs", "display_order": 2},
            {"code": "wrapping", "name": "Wrapping & Padding", "description": "Bubble wrap, foam, tape", "icon": "🧻", "default_lead_time_days": 7, "default_unit": "roll", "display_order": 3},
        ],
    },
    {
        "code": "consumables",
        "name": "Consumables",
        "description": "Consumable supplies for production",
        "icon": "🔧",
        "display_order": 3,
        "subgroups": [
            {"code": "spray_guns", "name": "Spray Gun Parts", "description": "Nozzles, needles, gaskets", "icon": "🔫", "default_lead_time_days": 14, "default_unit": "pcs", "display_order": 1},
            {"code": "brushes", "name": "Brushes & Applicators", "description": "Glazing brushes", "icon": "🖌️", "default_lead_time_days": 7, "default_unit": "pcs", "display_order": 2},
            {"code": "kiln_consumables", "name": "Kiln Consumables", "description": "Kiln wash, stilts, cones", "icon": "🔥", "default_lead_time_days": 14, "default_unit": "pcs", "display_order": 3},
        ],
    },
    {
        "code": "equipment",
        "name": "Equipment",
        "description": "Production equipment and tools",
        "icon": "⚙️",
        "display_order": 4,
        "subgroups": [
            {"code": "kiln_shelves", "name": "Kiln Shelves", "description": "SiC, Cordierite, Mullite shelves", "icon": "🧱", "default_lead_time_days": 30, "default_unit": "pcs", "display_order": 1},
            {"code": "glazing_boards", "name": "Glazing Boards", "description": "Boards for tile glazing", "icon": "📐", "default_lead_time_days": 7, "default_unit": "pcs", "display_order": 2},
        ],
    },
]

# Application methods (code, name, engobe_method, glaze_method, needs_engobe, two_stage, special_kiln,
#                       consumption_group_engobe, consumption_group_glaze, blocking_task_type, sort_order)
APPLICATION_METHODS = [
    ("ss", "Spray + Spray", "spray", "spray", True, False, None, "spray", "spray", None, 1),
    ("s", "Spray Only", None, "spray", False, False, None, None, "spray", None, 2),
    ("bs", "Brush + Spray", "brush", "spray", True, False, None, "brush", "spray", None, 3),
    ("sb", "Spray + Brush", "spray", "brush", True, False, None, "spray", "brush", None, 4),
    ("splashing", "Splashing", "spray", "splash", True, False, None, "spray", "splash", None, 5),
    ("stencil", "Stencil", "spray", "spray_stencil", True, False, None, "spray", "spray", "stencil_order", 6),
    ("silk_screen", "Silk Screen", "spray", "silk_screen", True, False, None, "spray", "silk_screen", "silk_screen_order", 7),
    ("gold", "Gold", "spray", "brush", True, True, None, "spray", "brush", None, 8),
    ("raku", "Raku", "spray", "spray", True, False, "raku", "spray", "spray", None, 9),
]

# Application collections (code, name, allowed_methods, any_method, no_base_colors, no_base_sizes, product_type_restriction, sort_order)
APPLICATION_COLLECTIONS = [
    ("authentic", "Authentic", ["ss", "s"], False, False, False, None, 1),
    ("creative", "Creative", ["ss", "bs", "sb", "splashing"], False, False, False, None, 2),
    ("silk_screen", "Silk Screen", ["silk_screen"], False, False, False, None, 3),
    ("stencil", "Stencil", ["stencil"], False, False, False, None, 4),
    ("gold", "Gold", ["gold"], False, False, False, None, 5),
    ("raku", "Raku", ["raku"], False, False, False, None, 6),
    ("exclusive", "Exclusive", [], True, True, True, None, 7),
    ("top_table", "Top Table", [], True, False, False, "countertop", 8),
    ("wash_basin", "Wash Basin", [], True, False, False, "sink", 9),
]


# ═══════════════════════════════════════════════════════════════════════════
#  Seed logic
# ═══════════════════════════════════════════════════════════════════════════

def _get_or_create(db, model, unique_filter: dict, defaults: dict = None):
    """Find existing row by unique_filter or create a new one.

    Returns (instance, created: bool).
    """
    instance = db.query(model).filter_by(**unique_filter).first()
    if instance:
        return instance, False
    instance = model(**{**unique_filter, **(defaults or {})})
    db.add(instance)
    db.flush()
    return instance, True


def seed():
    db = SessionLocal()
    stats = {"created": 0, "skipped": 0}

    def _track(created: bool):
        if created:
            stats["created"] += 1
        else:
            stats["skipped"] += 1

    try:
        # ── Collections ──
        for name in COLLECTIONS:
            _, created = _get_or_create(db, Collection, {"name": name})
            _track(created)
        print(f"  Collections: {len(COLLECTIONS)} checked")

        # ── Colors ──
        for name, code, is_basic in COLORS:
            _, created = _get_or_create(
                db, Color,
                {"name": name},
                {"code": code, "is_basic": is_basic},
            )
            _track(created)
        print(f"  Colors: {len(COLORS)} checked")

        # ── Sizes ──
        for name, w, h, t, shape in SIZES:
            _, created = _get_or_create(
                db, Size,
                {"name": name},
                {"width_mm": w, "height_mm": h, "thickness_mm": t, "shape": shape},
            )
            _track(created)
        print(f"  Sizes: {len(SIZES)} checked")

        # ── Production Stages ──
        for name, order in PRODUCTION_STAGES:
            _, created = _get_or_create(
                db, ProductionStage,
                {"name": name},
                {"order": order},
            )
            _track(created)
        print(f"  Production stages: {len(PRODUCTION_STAGES)} checked")

        # ── Material Groups + Subgroups ──
        group_count = 0
        subgroup_count = 0
        for g in MATERIAL_GROUPS:
            group, g_created = _get_or_create(
                db, MaterialGroup,
                {"code": g["code"]},
                {
                    "name": g["name"],
                    "description": g["description"],
                    "icon": g["icon"],
                    "display_order": g["display_order"],
                },
            )
            _track(g_created)
            group_count += 1

            for sg in g["subgroups"]:
                _, sg_created = _get_or_create(
                    db, MaterialSubgroup,
                    {"code": sg["code"]},
                    {
                        "group_id": group.id,
                        "name": sg["name"],
                        "description": sg["description"],
                        "icon": sg["icon"],
                        "default_lead_time_days": sg["default_lead_time_days"],
                        "default_unit": sg["default_unit"],
                        "display_order": sg["display_order"],
                    },
                )
                _track(sg_created)
                subgroup_count += 1

        print(f"  Material groups: {group_count} checked")
        print(f"  Material subgroups: {subgroup_count} checked")

        # ── Application Methods ──
        for (code, name, engobe_method, glaze_method, needs_engobe,
             two_stage, special_kiln, cg_engobe, cg_glaze, blocking, sort_order) in APPLICATION_METHODS:
            _, created = _get_or_create(
                db, ApplicationMethod,
                {"code": code},
                {
                    "name": name,
                    "engobe_method": engobe_method,
                    "glaze_method": glaze_method,
                    "needs_engobe": needs_engobe,
                    "two_stage_firing": two_stage,
                    "special_kiln": special_kiln,
                    "consumption_group_engobe": cg_engobe,
                    "consumption_group_glaze": cg_glaze,
                    "blocking_task_type": blocking,
                    "sort_order": sort_order,
                },
            )
            _track(created)
        print(f"  Application methods: {len(APPLICATION_METHODS)} checked")

        # ── Application Collections ──
        for (code, name, allowed_methods, any_method,
             no_base_colors, no_base_sizes, product_type, sort_order) in APPLICATION_COLLECTIONS:
            _, created = _get_or_create(
                db, ApplicationCollection,
                {"code": code},
                {
                    "name": name,
                    "allowed_methods": allowed_methods,
                    "any_method": any_method,
                    "no_base_colors": no_base_colors,
                    "no_base_sizes": no_base_sizes,
                    "product_type_restriction": product_type,
                    "sort_order": sort_order,
                },
            )
            _track(created)
        print(f"  Application collections: {len(APPLICATION_COLLECTIONS)} checked")

        db.commit()
        print(f"\nDone! Created: {stats['created']}, Already existed: {stats['skipped']}")

    except Exception as e:
        db.rollback()
        print(f"Error seeding reference data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
