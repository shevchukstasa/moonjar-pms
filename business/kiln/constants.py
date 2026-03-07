"""
Kiln constants — loaded from DB at runtime, cached.
See BUSINESS_LOGIC.md §36 for dual mode (manual + production).
"""
from uuid import UUID
from typing import Optional

from sqlalchemy.orm import Session


# Default kiln constants (used before per-kiln values available).
# Each kiln can override these via kiln_loading_rules JSONB.
DEFAULT_CONSTANTS = {
    "TILE_GAP_X": 1.2,           # cm gap between tiles along X axis
    "TILE_GAP_Y": 1.2,           # cm gap between tiles along Y axis
    "AIR_GAP": 2.0,              # cm air gap between shelf levels
    "SHELF_THICKNESS": 3.0,      # cm kiln shelf thickness
    "FLAT_ON_EDGE_COEFFICIENT": 0.30,  # 30% of area for flat-on-edge loading
    "MAX_EDGE_HEIGHT_LARGE": 60,  # cm — max standing height in Large kiln
    "MAX_EDGE_HEIGHT_SMALL": 45,  # cm — max standing height in Small kiln
}
# NOTE: Max product dimensions and allowed collections are per-kiln,
# stored in kiln_loading_rules.rules JSONB (not here).

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
