"""
Kiln constants — loaded from DB at runtime, cached.
Values match kiln-calculator app (src/utils/constants.ts, kilnCalculations.ts).
See BUSINESS_LOGIC.md §36 for dual mode (manual + production).

Global constants live in the kiln_constants table and are configurable by admin.
Per-kiln overrides (including max_edge_height_cm) live in kiln_loading_rules.rules JSONB.
"""
from uuid import UUID
from typing import Optional

from sqlalchemy.orm import Session


# ── Module-level hardcoded defaults ──────────────────────────────────────────
# Used only when the DB is unavailable. Authoritative values are in kiln_constants.
DEFAULT_CONSTANTS: dict = {
    "TILE_GAP": 1.2,                  # cm — gap between tiles (X and Y)
    "AIR_GAP": 2.0,                   # cm — vertical gap between shelf levels
    "SHELF_THICKNESS": 3.0,           # cm — kiln shelf thickness
    "FLAT_ON_EDGE_COEFFICIENT": 0.30, # fraction of shelf for flat-on-top tiles
    "FILLER_SIZE": 10.0,              # cm — filler tile side (10×10)
    "FILLER_MAX_AREA": 2.0,           # m² — max filler area per load
    "FILLER_COEFFICIENT": 0.50,       # efficiency factor for filler count
    "MIN_SPACE_TO_FILL": 21.0,        # cm — min leftover space before adding filler
    "MAX_EDGE_HEIGHT": 15.0,          # cm — default per-kiln edge-loading height limit
    "MIN_PRODUCT_SIZE": 3.0,          # cm — minimum product length or width
    "MIN_THICKNESS": 0.8,             # cm — minimum product thickness
    "TRIANGLE_PAIR_GAP": 1.5,         # cm — gap when placing triangle pairs
    "COFIRING_MAX_TEMP_RANGE": 50.0,  # °C — max temperature spread for co-firing
    "MAX_BIG_KILN_TILE_MAX": 40.0,    # cm — max product max-dim for large kiln
    "MAX_BIG_KILN_TILE_MIN": 30.0,    # cm — max product min-dim for large kiln
    "SINK_COUNTERTOP_LARGE_MAX": 40.0,
    "SINK_COUNTERTOP_LARGE_MIN": 20.0,
    "KILN_COEFF_LARGE": 0.80,
    "KILN_COEFF_SMALL": 0.92,
}

_cache: dict = {}


def get_kiln_constants(db: Session, factory_id: Optional[UUID] = None) -> dict:
    """
    Load kiln constants from the kiln_constants table.
    Results are cached per factory (None = global/no factory filter).
    Falls back to DEFAULT_CONSTANTS when a row is absent.
    """
    from api.models import KilnConstant

    cache_key = str(factory_id) if factory_id else "global"
    if cache_key in _cache:
        return _cache[cache_key]

    result = dict(DEFAULT_CONSTANTS)

    rows = db.query(KilnConstant).all()
    for row in rows:
        name = row.constant_name
        val = float(row.value)
        result[name] = val
        # Convenience aliases so capacity.py can use either name form
        if name == "TILE_GAP":
            result["TILE_GAP_X"] = val
            result["TILE_GAP_Y"] = val

    _cache[cache_key] = result
    return result


def invalidate_cache(factory_id: Optional[UUID] = None) -> None:
    """Call after any kiln_constants UPDATE to clear stale values."""
    if factory_id is None:
        _cache.clear()
    else:
        _cache.pop(str(factory_id), None)
        _cache.pop("global", None)
