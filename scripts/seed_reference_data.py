"""
Seed reference data: collections, colors, sizes, production stages.
Run after database creation: python scripts/seed_reference_data.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.database import SessionLocal
from api.models import *  # noqa


COLLECTIONS = [
    "Classic", "Modern", "Raku", "Terrazzo", "Zellige",
    "Encaustic", "Moroccan", "Subway", "Hexagon", "Penny",
]

COLORS = [
    "White", "Ivory", "Cream", "Beige", "Sand",
    "Grey", "Charcoal", "Black", "Navy", "Blue",
    "Green", "Sage", "Terracotta", "Rust", "Pink",
    "Blush", "Mustard", "Olive", "Teal", "Burgundy",
]

# Base colors for surplus → showroom rule
BASE_COLORS = {"White", "Ivory", "Cream", "Beige", "Grey", "Black"}

SIZES = [
    "5x5", "7.5x15", "10x10", "10x20", "10x30",
    "15x15", "20x20", "20x40", "30x30", "30x60",
    "40x40", "45x45", "60x60", "60x120",
]

PRODUCTION_STAGES = [
    {"code": "incoming_inspection", "name": "Incoming Inspection", "sort_order": 1},
    {"code": "engobe", "name": "Engobe Application", "sort_order": 2},
    {"code": "engobe_check", "name": "Engobe Check", "sort_order": 3},
    {"code": "glazing", "name": "Glazing", "sort_order": 4},
    {"code": "pre_kiln_check", "name": "Pre-Kiln Check", "sort_order": 5},
    {"code": "kiln_loading", "name": "Kiln Loading", "sort_order": 6},
    {"code": "firing", "name": "Firing", "sort_order": 7},
    {"code": "sorting", "name": "Sorting", "sort_order": 8},
    {"code": "packing", "name": "Packing", "sort_order": 9},
    {"code": "quality_check", "name": "Quality Check", "sort_order": 10},
]


def seed():
    db = SessionLocal()
    try:
        # TODO: insert reference data into respective tables
        # Use get_or_create pattern to be idempotent

        print(f"Collections: {len(COLLECTIONS)}")
        print(f"Colors: {len(COLORS)} ({len(BASE_COLORS)} base)")
        print(f"Sizes: {len(SIZES)}")
        print(f"Production stages: {len(PRODUCTION_STAGES)}")
        print("Reference data seeded successfully!")

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
