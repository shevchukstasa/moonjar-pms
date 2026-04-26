"""
Typology Matcher — matches positions to kiln loading typologies
and calculates capacity per kiln per typology.

Usage:
    # Match a position to the best typology
    typology = find_matching_typology(db, position)

    # Get effective capacity for scheduling
    cap_sqm = get_effective_capacity(db, position, kiln)

    # Recalculate all typology capacities for a factory
    results = calculate_all_typology_capacities(db, factory_id)
"""
import logging
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from api.models import (
    KilnLoadingTypology, KilnTypologyCapacity,
    OrderPosition, Resource,
)
from api.enums import ResourceType

logger = logging.getLogger("moonjar.typology_matcher")


# ---------------------------------------------------------------------------
#  Internal helpers
# ---------------------------------------------------------------------------

def _matches_jsonb(criteria: list, value) -> bool:
    """Check if value matches JSONB array criteria. Empty list = matches all."""
    if not criteria:
        return True
    # Extract .value from SQLAlchemy enums
    val = value.value if hasattr(value, "value") else str(value) if value else None
    if not val:
        return False  # non-empty criteria but no value -> no match
    return val.lower() in [c.lower() for c in criteria]


def _size_in_range(typology: KilnLoadingTypology, position: OrderPosition) -> bool:
    """Check if position size falls within typology min/max range."""
    w = float(position.width_cm or 0) if position.width_cm else 0
    l = float(position.length_cm or 0) if position.length_cm else 0

    # Fallback: parse from size string ("10x10", "30х60", "5×21,5")
    if not w and not l and position.size:
        try:
            from business.services.size_normalizer import normalize_size_str
            parts = normalize_size_str(position.size).split("x")
            w = float(parts[0])
            l = float(parts[1]) if len(parts) > 1 else w
        except (ValueError, IndexError):
            return True  # unparseable size -> don't filter

    if not w and not l:
        return True

    max_dim = max(w, l)
    min_dim = min(w, l)

    if typology.min_size_cm and min_dim < float(typology.min_size_cm):
        return False
    if typology.max_size_cm and max_dim > float(typology.max_size_cm):
        return False
    # max_short_side_cm: restrict the shorter side (e.g. 15 cm for small tiles)
    if typology.max_short_side_cm and min_dim > float(typology.max_short_side_cm):
        return False
    return True


# ---------------------------------------------------------------------------
#  Public API — matching
# ---------------------------------------------------------------------------

def find_matching_typology(
    db: Session,
    position: OrderPosition,
) -> Optional[KilnLoadingTypology]:
    """Find the best matching typology for a position (highest priority first).

    Criteria checked (all must pass):
      - product_types
      - place_of_application
      - collections
      - methods (application_method_code on position)
      - size range (min_size_cm .. max_size_cm)
    """
    typologies = (
        db.query(KilnLoadingTypology)
        .filter(
            KilnLoadingTypology.factory_id == position.factory_id,
            KilnLoadingTypology.is_active == True,  # noqa: E712
        )
        .order_by(KilnLoadingTypology.priority.desc())
        .all()
    )

    # Defensive fallback: if place_of_application is missing on a tile
    # position, treat it as 'face_only' (the dominant real-world case).
    # Historical positions ingested from webhook/PDF often had NULL here,
    # which silently failed every "Small/Large Tile …" typology and
    # left the scheduler without speeds or kiln capacity — the single
    # most common root cause of 1-day fallback across all stages.
    _pt = getattr(position, "product_type", None)
    _pt_val = _pt.value if hasattr(_pt, "value") else (str(_pt) if _pt else None)
    _place_fallback = getattr(position, "place_of_application", None)
    if not _place_fallback and _pt_val == "tile":
        _place_fallback = "face_only"

    for t in typologies:
        if not _matches_jsonb(t.product_types or [], position.product_type):
            continue
        if not _matches_jsonb(
            t.place_of_application or [],
            _place_fallback,
        ):
            continue
        if not _matches_jsonb(
            t.collections or [],
            getattr(position, "collection", None),
        ):
            continue
        if not _matches_jsonb(
            t.methods or [],
            getattr(position, "application_method_code", None),
        ):
            continue
        if not _size_in_range(t, position):
            continue
        return t

    return None


def get_typology_capacity(
    db: Session,
    typology_id: UUID,
    kiln_id: UUID,
) -> Optional[KilnTypologyCapacity]:
    """Get pre-computed capacity for a typology+kiln combination."""
    return db.query(KilnTypologyCapacity).filter(
        KilnTypologyCapacity.typology_id == typology_id,
        KilnTypologyCapacity.resource_id == kiln_id,
    ).first()


def classify_loading_zone(position) -> str:
    """Classify position into loading zone: 'edge' or 'flat'.

    Edge loading: face only, face+1 edge, face+2 edges — IF size ≤ 15cm max side.
    Flat loading: all edges, with back, OR any tile bigger than 15cm.
    """
    place = getattr(position, 'place_of_application', 'face_only') or 'face_only'
    place = place.value if hasattr(place, 'value') else str(place)

    if place in ('face_only', 'edges_1', 'edges_2'):
        # Check size — tiles > 15cm on any side can't be edge-loaded
        w = float(position.width_cm or 0) if getattr(position, 'width_cm', None) else 0
        l = float(position.length_cm or 0) if getattr(position, 'length_cm', None) else 0
        if not w and not l and getattr(position, 'size', None):
            try:
                from business.services.size_normalizer import normalize_size_str
                parts = normalize_size_str(position.size).split('x')
                w = float(parts[0])
                l = float(parts[1]) if len(parts) > 1 else w
            except (ValueError, IndexError):
                pass
        max_dim = max(w, l) if w or l else 10  # default 10cm if unknown
        if max_dim > 15:
            return 'flat'
        return 'edge'
    return 'flat'


def get_effective_capacity(
    db: Session,
    position: OrderPosition,
    kiln: Resource,
) -> float:
    """Get the effective kiln capacity (sqm) for a position, considering typology.

    Resolution order:
      1. KilnTypologyCapacity.ai_adjusted_sqm (AI-calibrated)
      2. KilnTypologyCapacity.capacity_sqm    (geometry-calculated)
      3. kiln.capacity_sqm                    (simple fallback)
      4. 1.0                                  (last resort)
    """
    typology = find_matching_typology(db, position)
    if typology:
        cap = get_typology_capacity(db, typology.id, kiln.id)
        if cap:
            if cap.ai_adjusted_sqm:
                return float(cap.ai_adjusted_sqm)
            if cap.capacity_sqm:
                return float(cap.capacity_sqm)

    if kiln.capacity_sqm:
        return float(kiln.capacity_sqm)
    return 1.0


def get_zone_capacity(
    db: Session,
    position: OrderPosition,
    kiln: Resource,
    zone: str,
) -> float:
    """Get capacity for a specific loading zone, considering typology.

    Looks up KilnTypologyCapacity filtered by zone column.
    Falls back to proportional split of total capacity if no typology data.
    """
    typology = find_matching_typology(db, position)
    if typology:
        # First try zone-specific record
        cap = (
            db.query(KilnTypologyCapacity)
            .filter(
                KilnTypologyCapacity.typology_id == typology.id,
                KilnTypologyCapacity.resource_id == kiln.id,
                KilnTypologyCapacity.zone == zone,
            )
            .first()
        )
        if cap:
            return float(cap.ai_adjusted_sqm or cap.capacity_sqm or 0)

        # Fallback: try 'primary' zone record (legacy single-zone)
        cap_primary = get_typology_capacity(db, typology.id, kiln.id)
        if cap_primary and (cap_primary.zone or 'primary') == 'primary':
            return float(cap_primary.ai_adjusted_sqm or cap_primary.capacity_sqm or 0)

    # Fallback proportional split
    total = float(kiln.capacity_sqm or 1.0)
    if zone == 'edge':
        return total * 0.85
    return total * 0.15


# ---------------------------------------------------------------------------
#  Capacity calculation
# ---------------------------------------------------------------------------

_PLACE_TO_GLAZE = {
    "face_only": "face-only",
    "edges_1": "face-1-edge",
    "edges_2": "face-2-edges",
    "all_edges": "face-3-4-edges",
    "with_back": "face-with-back",
}


def _build_ref_position(typology: KilnLoadingTypology) -> SimpleNamespace:
    """Build a synthetic position object that capacity.py can consume via getattr.

    capacity.py reads: .size, .product_type, .shape, .thickness_cm, .glaze_placement
    """
    # Reference dimensions from size range midpoint
    ref_w, ref_l = 10.0, 10.0
    if typology.min_size_cm and typology.max_size_cm:
        mid = (float(typology.min_size_cm) + float(typology.max_size_cm)) / 2
        ref_w = ref_l = round(mid, 1)
    elif typology.max_size_cm:
        ref_w = ref_l = float(typology.max_size_cm)
    elif typology.min_size_cm:
        ref_w = ref_l = float(typology.min_size_cm)

    # Reference thickness: from first existing capacity record, else 11mm = 1.1cm
    ref_thickness_cm = 1.1
    if typology.capacities:
        ref_thickness_cm = float(typology.capacities[0].ref_thickness_mm or 11) / 10.0

    # Product type
    ptypes = typology.product_types or []
    ptype = ptypes[0] if ptypes else "tile"

    # Glaze placement
    places = typology.place_of_application or []
    glaze_placement = "face-only"
    if places:
        glaze_placement = _PLACE_TO_GLAZE.get(places[0], "face-only")

    size_str = f"{ref_w}x{ref_l}"

    return SimpleNamespace(
        size=size_str,
        product_type=ptype,
        shape="rectangle",
        thickness_cm=ref_thickness_cm,
        glaze_placement=glaze_placement,
    )


def calculate_typology_for_kiln(
    db: Session,
    typology: KilnLoadingTypology,
    kiln: Resource,
) -> KilnTypologyCapacity:
    """Calculate capacity for a typology+kiln combo using the geometry engine.

    Creates or updates the KilnTypologyCapacity record.
    """
    from business.kiln.capacity import calculate_kiln_capacity
    from business.kiln.constants import get_kiln_constants
    from business.kiln.assignment_rules import get_loading_rules

    constants = get_kiln_constants(db, kiln.factory_id)
    loading_rules = get_loading_rules(db, kiln.id)

    ref_pos = _build_ref_position(typology)

    try:
        result = calculate_kiln_capacity(ref_pos, kiln, constants, loading_rules)
        optimal = result.get("optimal", {})
        cap_sqm = optimal.get("total_area_sqm", 0)
        cap_pcs = optimal.get("total_pieces", 0)
        method = optimal.get("method", "flat")
        levels = optimal.get("num_levels", 1)
    except Exception as e:
        logger.error(
            "Capacity calc failed for typology %s + kiln %s: %s",
            typology.name, kiln.name, e,
        )
        cap_sqm = 0
        cap_pcs = 0
        method = "unknown"
        levels = 1
        result = {"error": str(e)}

    # Auto-determine zone from place_of_application and loading method
    places = typology.place_of_application or []
    if not places or any(p in ('face_only', 'edges_1', 'edges_2') for p in places):
        determined_zone = 'edge' if method == 'edge' else 'flat'
    else:
        determined_zone = 'flat'

    # Upsert KilnTypologyCapacity (keyed by typology + kiln + zone)
    existing = db.query(KilnTypologyCapacity).filter(
        KilnTypologyCapacity.typology_id == typology.id,
        KilnTypologyCapacity.resource_id == kiln.id,
        KilnTypologyCapacity.zone == determined_zone,
    ).first()

    cap_record = existing or KilnTypologyCapacity(
        typology_id=typology.id,
        resource_id=kiln.id,
        zone=determined_zone,
    )
    if not existing:
        db.add(cap_record)

    ref_thickness_mm = ref_pos.thickness_cm * 10.0

    cap_record.capacity_sqm = Decimal(str(round(cap_sqm, 3)))
    cap_record.capacity_pcs = cap_pcs
    cap_record.loading_method = method
    cap_record.num_levels = levels
    cap_record.ref_size = ref_pos.size
    cap_record.ref_thickness_mm = Decimal(str(round(ref_thickness_mm, 2)))
    cap_record.ref_shape = ref_pos.shape
    cap_record.calculated_at = datetime.now(timezone.utc)
    cap_record.calculation_input = {
        "size": ref_pos.size,
        "product_type": ref_pos.product_type,
        "shape": ref_pos.shape,
        "thickness_cm": ref_pos.thickness_cm,
        "glaze_placement": ref_pos.glaze_placement,
    }
    cap_record.calculation_output = result
    cap_record.zone = determined_zone

    db.flush()
    return cap_record


def calculate_all_typology_capacities(
    db: Session,
    factory_id: UUID,
    typology_id: UUID = None,
) -> list[dict]:
    """Calculate capacities for all active kilns x typologies in a factory.

    If typology_id is given, calculates only for that typology.
    Returns list of result dicts.
    """
    kilns = db.query(Resource).filter(
        Resource.factory_id == factory_id,
        Resource.resource_type == ResourceType.KILN.value,
        Resource.is_active == True,  # noqa: E712
    ).all()

    query = db.query(KilnLoadingTypology).filter(
        KilnLoadingTypology.factory_id == factory_id,
        KilnLoadingTypology.is_active == True,  # noqa: E712
    )
    if typology_id:
        query = query.filter(KilnLoadingTypology.id == typology_id)
    typologies = query.all()

    results = []
    for typology in typologies:
        for kiln in kilns:
            cap = calculate_typology_for_kiln(db, typology, kiln)
            results.append({
                "typology_id": str(typology.id),
                "typology_name": typology.name,
                "kiln_id": str(kiln.id),
                "kiln_name": kiln.name,
                "capacity_sqm": float(cap.capacity_sqm) if cap.capacity_sqm else 0,
                "capacity_pcs": cap.capacity_pcs or 0,
                "loading_method": cap.loading_method,
                "num_levels": cap.num_levels,
            })

    return results
