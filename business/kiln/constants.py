"""
Kiln constants — loaded from DB at runtime, cached.
See BUSINESS_LOGIC.md §36 for dual mode (manual + production).
"""
from uuid import UUID
from typing import Optional

from sqlalchemy.orm import Session


# Default kiln constants (used before DB values available)
DEFAULT_CONSTANTS = {
    "TILE_GAP": 0.3,             # cm gap between tiles
    "AIR_GAP": 1.5,              # cm air gap between levels
    "SHELF_THICKNESS": 2.0,      # cm kiln shelf thickness
    "FLAT_ON_EDGE_COEFFICIENT": 0.30,  # 30% of area for flat-on-edge
    "MAX_EDGE_HEIGHT_LARGE": 60,  # cm — max standing height in Large kiln
    "MAX_EDGE_HEIGHT_SMALL": 45,  # cm — max standing height in Small kiln
    "MAX_BIG_KILN_TILE_MIN": 60,  # cm — max min-dimension for tile in Large
    "MAX_BIG_KILN_TILE_MAX": 120, # cm — max max-dimension for tile in Large
    "SINK_COUNTERTOP_LARGE_MIN": 100,
    "SINK_COUNTERTOP_LARGE_MAX": 150,
}

_cache = {}


def get_kiln_constants(db: Session, factory_id: Optional[UUID] = None) -> dict:
    """Load kiln constants from DB with caching. Falls back to defaults."""
    cache_key = str(factory_id) if factory_id else "global"
    if cache_key in _cache:
        return _cache[cache_key]

    # TODO: load from kiln_constants table, merge with defaults
    # constants = db.query(KilnConstant).filter_by(factory_id=factory_id).all()
    result = dict(DEFAULT_CONSTANTS)
    _cache[cache_key] = result
    return result


def invalidate_cache(factory_id: Optional[UUID] = None):
    """Invalidate constants cache after admin update."""
    cache_key = str(factory_id) if factory_id else "global"
    _cache.pop(cache_key, None)
