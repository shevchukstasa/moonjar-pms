"""
Batch Formation service.
Business Logic: §7, §19

Groups kiln-ready positions into temperature-compatible batches,
assigns kilns, and attaches firing profiles.

Enhanced with geometry-based kiln capacity calculations from
business/kiln/capacity.py — uses actual piece-level fit instead
of simple capacity_sqm comparison.
"""
import uuid as uuid_mod
import logging
from uuid import UUID
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func

from api.models import (
    Batch,
    KilnActualLoad,
    KilnCalculationLog,
    OrderPosition,
    Resource,
    KilnMaintenanceSchedule,
    RecipeKilnConfig,
)
from api.enums import (
    PositionStatus,
    BatchStatus,
    BatchCreator,
    ResourceType,
    ResourceStatus,
    MaintenanceStatus,
)

logger = logging.getLogger("moonjar.batch_formation")


# ────────────────────────────────────────────────────────────────
# §0  Filler tile selection for unused kiln space
# ────────────────────────────────────────────────────────────────

def _select_filler_tiles(
    db: Session,
    kiln: Resource,
    batch_positions: list[OrderPosition],
    remaining_area_sqm: Decimal,
    batch_temperature: Optional[int],
    constants: dict,
    loading_rules: dict,
) -> list[tuple[OrderPosition, dict]]:
    """
    Select filler tiles from the production queue to fill unused kiln space.

    Finds positions in READY_FOR_KILN statuses (PRE_KILN_CHECK, GLAZED) that:
    - Are not already assigned to a batch
    - Are not among the current batch_positions
    - Have a compatible firing temperature (same ±50°C range as batch)
    - Fit within the remaining kiln area

    Uses a greedy largest-area-first strategy to maximize utilization.

    Args:
        db: Database session
        kiln: The kiln Resource being loaded
        batch_positions: Positions already assigned to this batch
        remaining_area_sqm: Remaining kiln area in m²
        batch_temperature: Target firing temperature for the batch (°C)
        constants: Global kiln constants dict
        loading_rules: Per-kiln loading rules dict

    Returns:
        List of (OrderPosition, loading_plan_entry) tuples for selected fillers.
        Each loading_plan_entry dict includes "is_filler": True.
    """
    if remaining_area_sqm <= Decimal("0.01"):
        return []

    # IDs already in this batch — exclude them from candidates
    batch_pos_ids = {pos.id for pos in batch_positions}

    # Query candidate positions: ready for kiln, not in any batch
    ready_statuses = [
        PositionStatus.PRE_KILN_CHECK.value,
        PositionStatus.GLAZED.value,
    ]
    candidates = (
        db.query(OrderPosition)
        .filter(
            OrderPosition.factory_id == kiln.factory_id,
            OrderPosition.status.in_(ready_statuses),
            OrderPosition.batch_id.is_(None),
            OrderPosition.id.notin_(batch_pos_ids) if batch_pos_ids else True,
        )
        .all()
    )

    if not candidates:
        return []

    # Filter by temperature compatibility (±50°C from batch target)
    TEMP_DELTA = 50
    temp_compatible = []
    for cand in candidates:
        if cand.id in batch_pos_ids:
            continue  # safety check

        if batch_temperature is not None and cand.recipe_id:
            config = (
                db.query(RecipeKilnConfig)
                .filter(RecipeKilnConfig.recipe_id == cand.recipe_id)
                .first()
            )
            cand_temp = (
                config.firing_temperature
                if config and config.firing_temperature
                else None
            )
            if cand_temp is not None:
                if abs(cand_temp - batch_temperature) > TEMP_DELTA:
                    continue  # temperature mismatch
        elif batch_temperature is not None:
            # No recipe -> skip (cannot verify temperature compatibility)
            continue

        temp_compatible.append(cand)

    if not temp_compatible:
        return []

    # Compute area for each candidate and sort largest-first (greedy)
    cand_with_area = []
    for cand in temp_compatible:
        area = _get_position_area_sqm(cand)
        cand_with_area.append((cand, area))

    cand_with_area.sort(key=lambda x: x[1], reverse=True)

    # Greedy selection: pick largest that fits
    selected: list[tuple[OrderPosition, dict]] = []
    space_left = remaining_area_sqm

    for cand, cand_area in cand_with_area:
        if cand_area > space_left:
            continue
        if cand_area <= Decimal("0"):
            continue

        # Try geometry-based loading calculation
        if _position_has_geometry(cand):
            cap_result = _calculate_position_loading(
                cand, kiln, constants, loading_rules,
            )
        else:
            cap_result = None

        if cap_result is not None:
            optimal = cap_result.get("optimal", {})
            if optimal.get("total_pieces", 0) == 0:
                continue  # does not fit in this kiln geometry-wise
            entry = _build_loading_plan_entry(cand, cap_result)
        else:
            # Fallback: simple area-based entry
            entry = {
                "position_id": str(cand.id),
                "loading_method": "flat",
                "pieces_per_level": cand.quantity,
                "levels_used": 1,
                "total_pieces": cand.quantity,
                "area_sqm": float(cand_area),
                "geometry_fallback": True,
            }

        entry["is_filler"] = True
        selected.append((cand, entry))
        space_left -= cand_area

        if space_left <= Decimal("0.01"):
            break

    if selected:
        logger.info(
            "FILLER_SELECTED | kiln=%s | %d filler positions, %.4f sqm filled "
            "(%.4f sqm remaining)",
            kiln.name, len(selected),
            float(remaining_area_sqm - space_left),
            float(space_left),
        )

    return selected


# ────────────────────────────────────────────────────────────────
# §0b  Co-firing compatibility sub-grouping
# ────────────────────────────────────────────────────────────────

def _get_cofiring_key(pos: OrderPosition) -> str:
    """
    Return a grouping key for co-firing compatibility.

    Positions are compatible within a batch only if they share the same
    co-firing key.  The key encodes:
      - two_stage_firing flag  (True / False)
      - two_stage_type         ('gold', 'countertop', or None)

    This ensures:
      - Standard (non-two-stage) positions never mix with two-stage ones.
      - Two-stage positions of different types stay separate.
      - Gold tile (two_stage_type='gold', 700 °C) is isolated from
        standard-temperature items.
    """
    is_two_stage = getattr(pos, "two_stage_firing", False)
    ts_type = getattr(pos, "two_stage_type", None)

    if is_two_stage:
        return f"two_stage:{ts_type or 'unspecified'}"
    return "standard"


def _split_by_cofiring_compatibility(
    positions: list[OrderPosition],
) -> dict[str, list[OrderPosition]]:
    """
    Split a list of positions into sub-groups that are co-firing compatible.

    Within each temperature group (already grouped by temperature), positions
    still need to be separated by two-stage firing type so that incompatible
    items are never placed in the same batch.

    Returns dict of {cofiring_key -> [positions]}.
    """
    groups: dict[str, list[OrderPosition]] = {}
    for pos in positions:
        key = _get_cofiring_key(pos)
        groups.setdefault(key, []).append(pos)
    return groups


def _validate_batch_cofiring(
    db: Session,
    batch_positions: list[OrderPosition],
    kiln_id: UUID,
    constants: Optional[dict] = None,
) -> dict:
    """
    Run co-firing validation on a candidate batch.
    Delegates to assignment_rules.validate_cofiring().

    Returns the validation result dict:
      {ok, errors, warnings, min_temperature, max_temperature}
    """
    from business.kiln.assignment_rules import validate_cofiring

    return validate_cofiring(db, batch_positions, kiln_id, constants)


# ────────────────────────────────────────────────────────────────
# §1  Collect positions ready for batching
# ────────────────────────────────────────────────────────────────

def _get_ready_positions(
    db: Session,
    factory_id: UUID,
    target_date: Optional[date] = None,
) -> list[OrderPosition]:
    """
    Collect all positions ready for kiln batching.

    Ready = status in (PRE_KILN_CHECK, GLAZED) AND not already in a batch.
    - PRE_KILN_CHECK is the primary "ready for kiln" status.
    - GLAZED positions that have passed pre-kiln QC are also eligible
      (they may not have been explicitly transitioned yet).

    Orders by priority_order DESC (higher priority first), then by
    planned_kiln_date ASC (earlier dates first).
    """
    ready_statuses = [
        PositionStatus.PRE_KILN_CHECK.value,
        PositionStatus.GLAZED.value,
    ]

    query = db.query(OrderPosition).filter(
        OrderPosition.factory_id == factory_id,
        OrderPosition.status.in_(ready_statuses),
        OrderPosition.batch_id.is_(None),
    )

    if target_date:
        # Only positions whose planned kiln date is on or before the target
        query = query.filter(
            OrderPosition.planned_kiln_date <= target_date,
        )

    positions = query.order_by(
        OrderPosition.priority_order.desc(),
        OrderPosition.planned_kiln_date.asc().nulls_last(),
        OrderPosition.created_at.asc(),
    ).all()

    return positions


# ────────────────────────────────────────────────────────────────
# §2  Get available kilns (not under maintenance)
# ────────────────────────────────────────────────────────────────

def _get_available_kilns(
    db: Session,
    factory_id: UUID,
    batch_date: date,
) -> list[Resource]:
    """
    Return active kilns for the factory that are NOT scheduled for
    maintenance on the given date.
    """
    kilns = db.query(Resource).filter(
        Resource.factory_id == factory_id,
        Resource.resource_type == ResourceType.KILN.value,
        Resource.is_active.is_(True),
        Resource.status != ResourceStatus.MAINTENANCE_EMERGENCY.value,
    ).all()

    # Filter out kilns with planned/in-progress maintenance on batch_date
    available = []
    for kiln in kilns:
        has_maintenance = db.query(KilnMaintenanceSchedule).filter(
            KilnMaintenanceSchedule.resource_id == kiln.id,
            KilnMaintenanceSchedule.scheduled_date == batch_date,
            KilnMaintenanceSchedule.status.in_([
                MaintenanceStatus.PLANNED.value,
                MaintenanceStatus.IN_PROGRESS.value,
            ]),
        ).first()

        if not has_maintenance:
            available.append(kiln)

    return available


def _get_kiln_capacity_sqm(kiln: Resource) -> Decimal:
    """Get the kiln capacity in sqm, with sensible fallback."""
    if kiln.capacity_sqm:
        return Decimal(str(kiln.capacity_sqm))
    # Fallback: derive from dimensions if available
    if kiln.kiln_working_area_cm:
        dims = kiln.kiln_working_area_cm
        w = dims.get("width", 0)
        h = dims.get("height", 0)
        if w and h:
            return Decimal(str(w * h)) / Decimal("10000")  # cm2 -> m2
    # Last resort
    return Decimal("1.0")


def _get_position_area_sqm(pos: OrderPosition) -> Decimal:
    """Get the area of a position in sqm for batch capacity calculation."""
    # Use glazeable_sqm if available, scaled by quantity
    if pos.glazeable_sqm:
        return Decimal(str(pos.glazeable_sqm)) * Decimal(str(pos.quantity))
    # Fallback to quantity_sqm
    if pos.quantity_sqm:
        return Decimal(str(pos.quantity_sqm))
    # Fallback: estimate from size (e.g., "20x20") and quantity
    if pos.length_cm and pos.width_cm:
        piece_sqm = (Decimal(str(pos.length_cm)) * Decimal(str(pos.width_cm))) / Decimal("10000")
        return piece_sqm * Decimal(str(pos.quantity))
    # Absolute fallback
    return Decimal("0.04") * Decimal(str(pos.quantity))  # ~20x20 cm default


# ────────────────────────────────────────────────────────────────
# §2b  Geometry-based capacity helpers
# ────────────────────────────────────────────────────────────────

def _get_kiln_constants_and_rules(db: Session, kiln: Resource) -> tuple:
    """
    Load global kiln constants and per-kiln loading rules.
    Returns (constants_dict, loading_rules_dict).
    """
    from business.kiln.constants import get_kiln_constants
    from business.kiln.assignment_rules import get_loading_rules

    constants = get_kiln_constants(db, kiln.factory_id)
    loading_rules = get_loading_rules(db, kiln.id)
    return constants, loading_rules


def _position_has_geometry(pos: OrderPosition) -> bool:
    """Check if position has enough data for geometry-based calculation."""
    return bool(pos.size and pos.size != "0x0")


def _calculate_position_loading(
    pos: OrderPosition,
    kiln: Resource,
    constants: dict,
    loading_rules: dict,
) -> Optional[dict]:
    """
    Calculate how a position loads in a kiln using geometry-based capacity.

    Calls calculate_kiln_capacity() from business/kiln/capacity.py.

    The capacity calculator reads position attributes via getattr():
      - size          -> "30x60" format string (from OrderPosition.size)
      - thickness_cm  -> float in cm (converted from OrderPosition.thickness_mm)
      - product_type  -> string like "tile", "sink", etc.
      - shape         -> string like "rectangle", "round", "triangle"
      - glaze_placement -> string like "face-only", "face-with-back", etc.

    Returns the full capacity result dict from calculate_kiln_capacity(),
    or None if calculation fails.
    """
    from business.kiln.capacity import calculate_kiln_capacity

    # Build a lightweight adapter object so calculate_kiln_capacity can
    # use getattr() to read position properties in the format it expects.
    class _PosAdapter:
        def __init__(self, op: OrderPosition):
            self.size = op.size or "0x0"
            # Convert thickness_mm -> thickness_cm (capacity.py expects cm)
            tmm = float(op.thickness_mm) if op.thickness_mm else 11.0
            self.thickness_cm = tmm / 10.0
            # product_type: enum -> string value
            pt = op.product_type
            self.product_type = pt.value if hasattr(pt, "value") else str(pt) if pt else "tile"
            # shape: enum -> string value
            sh = op.shape
            self.shape = sh.value if hasattr(sh, "value") else str(sh) if sh else "rectangle"
            # glaze_placement: use place_of_application, or default
            poa = op.place_of_application
            self.glaze_placement = poa if poa else "face-only"

    import time as _time

    try:
        adapter = _PosAdapter(pos)
        t0 = _time.monotonic()
        result = calculate_kiln_capacity(adapter, kiln, constants, loading_rules)
        duration_ms = int((_time.monotonic() - t0) * 1000)

        # Log calculation to KilnCalculationLog for auditability
        try:
            from sqlalchemy.orm import object_session
            db = object_session(pos) or object_session(kiln)
            if db:
                log_entry = KilnCalculationLog(
                    calculation_type="position_loading",
                    resource_id=kiln.id,
                    input_json={
                        "position_id": str(pos.id),
                        "size": adapter.size,
                        "thickness_cm": adapter.thickness_cm,
                        "product_type": adapter.product_type,
                        "shape": adapter.shape,
                        "glaze_placement": adapter.glaze_placement,
                        "kiln_type": kiln.kiln_type,
                        "kiln_capacity_sqm": float(kiln.capacity_sqm) if kiln.capacity_sqm else None,
                    },
                    output_json=result,
                    duration_ms=duration_ms,
                )
                db.add(log_entry)
                # Don't flush here — let the caller control the transaction
        except Exception as log_exc:
            logger.debug("KilnCalculationLog write failed: %s", log_exc)

        return result
    except (ValueError, ZeroDivisionError, TypeError, AttributeError) as exc:
        logger.debug(
            "GEOMETRY_CALC_FAIL | position=%s kiln=%s | %s: %s",
            pos.id, kiln.id, type(exc).__name__, exc,
        )
        return None


def _build_loading_plan_entry(
    pos: OrderPosition,
    capacity_result: dict,
) -> dict:
    """
    Build a single loading plan entry for a position from capacity result.
    """
    optimal = capacity_result.get("optimal", {})
    method = optimal.get("method", "flat")
    per_level = optimal.get("per_level", optimal.get("edge_pieces", 0))
    num_levels = optimal.get("num_levels", 1)
    total_pieces = optimal.get("total_pieces", 0)
    total_area = optimal.get("total_area_sqm", 0.0)

    entry = {
        "position_id": str(pos.id),
        "loading_method": method,
        "pieces_per_level": per_level,
        "levels_used": num_levels,
        "total_pieces": total_pieces,
        "area_sqm": round(total_area, 4),
    }

    # Include filler info if present
    filler = optimal.get("filler")
    if filler:
        entry["filler_pieces"] = filler.get("filler_pieces", 0)
        entry["filler_area_sqm"] = filler.get("filler_area_sqm", 0.0)

    # Include flat-on-top for edge loading
    if method == "edge":
        entry["edge_pieces"] = optimal.get("edge_pieces", 0)
        entry["flat_on_top"] = optimal.get("flat_on_top", 0)

    return entry


def _build_loading_plan(
    position_entries: list[dict],
    kiln_capacity_sqm: float,
) -> dict:
    """
    Build the complete loading_plan dict for batch metadata_json.
    """
    total_area = sum(e["area_sqm"] for e in position_entries)
    filler_area = sum(e.get("filler_area_sqm", 0.0) for e in position_entries)
    utilization = (total_area / kiln_capacity_sqm * 100.0) if kiln_capacity_sqm > 0 else 0.0

    return {
        "loading_plan": {
            "positions": position_entries,
            "total_area_sqm": round(total_area, 4),
            "kiln_utilization_pct": round(utilization, 1),
            "filler_area_sqm": round(filler_area, 4),
        }
    }


def preview_position_in_kiln(
    db: Session,
    position: OrderPosition,
    kiln: Resource,
) -> dict:
    """
    Preview how a position would load in a specific kiln.
    Used by the capacity-preview API endpoint.

    Returns full capacity result with flat/edge/optimal breakdown,
    plus a loading plan entry.
    """
    import time as _time

    constants, loading_rules = _get_kiln_constants_and_rules(db, kiln)
    t0 = _time.monotonic()
    result = _calculate_position_loading(position, kiln, constants, loading_rules)
    duration_ms = int((_time.monotonic() - t0) * 1000)

    # Log preview calculation
    try:
        log_entry = KilnCalculationLog(
            calculation_type="capacity_preview",
            resource_id=kiln.id,
            input_json={
                "position_id": str(position.id),
                "kiln_id": str(kiln.id),
                "size": position.size,
                "thickness_mm": float(position.thickness_mm) if position.thickness_mm else None,
            },
            output_json=result if result else {"fallback": True},
            duration_ms=duration_ms,
        )
        db.add(log_entry)
        db.flush()
    except Exception as log_exc:
        logger.debug("KilnCalculationLog preview write failed: %s", log_exc)

    if result is None:
        # Fall back to simple area comparison
        area = float(_get_position_area_sqm(position))
        cap = float(_get_kiln_capacity_sqm(kiln))
        return {
            "geometry_available": False,
            "fallback": True,
            "position_area_sqm": area,
            "kiln_capacity_sqm": cap,
            "fits": area <= cap,
        }

    entry = _build_loading_plan_entry(position, result)
    kiln_cap = float(_get_kiln_capacity_sqm(kiln))

    return {
        "geometry_available": True,
        "fallback": False,
        "loading_plan_entry": entry,
        "kiln_capacity_sqm": kiln_cap,
        "flat": result.get("flat"),
        "edge": result.get("edge"),
        "optimal": result.get("optimal"),
        "alternative": result.get("alternative"),
    }


# ────────────────────────────────────────────────────────────────
# §3  Find best kiln for a temperature group
# ────────────────────────────────────────────────────────────────

def _is_raku_kiln(kiln: Resource) -> bool:
    """Check if a kiln is a Raku kiln by its type."""
    return "raku" in (kiln.kiln_type or "").lower()


# Gold tile standard firing temperature (700 °C)
_GOLD_FIRING_TEMPERATURE = 700
_GOLD_TEMP_TOLERANCE = 50  # °C — within this range counts as gold-compatible


def _is_gold_firing(
    cofiring_key: Optional[str] = None,
    firing_temperature: Optional[int] = None,
) -> bool:
    """
    Determine if a batch is a gold/700°C firing.

    Checks both the co-firing sub-group key (set by _split_by_cofiring_compatibility)
    and the actual firing temperature.
    """
    if cofiring_key and "gold" in cofiring_key:
        return True
    if firing_temperature is not None:
        if abs(firing_temperature - _GOLD_FIRING_TEMPERATURE) <= _GOLD_TEMP_TOLERANCE:
            return True
    return False


def _find_best_kiln_for_batch(
    db: Session,
    available_kilns: list[Resource],
    batch_date: date,
    required_area_sqm: Decimal,
    position: Optional[OrderPosition] = None,
    cofiring_key: Optional[str] = None,
    firing_temperature: Optional[int] = None,
) -> Optional[Resource]:
    """
    Find the best kiln for a batch.

    Strategy:
    1. If position has an estimated_kiln_id and it's available, prefer it
    2. Rotation rules: skip kilns where proposed glaze is non-compliant
    3. Raku-specific rules:
       - Gold firings (700°C / two_stage_type='gold'): prefer Raku kiln
       - Standard-temperature firings: avoid Raku if other kilns are available
       - Raku can be used as overflow for any temperature if all others are full
    4. Otherwise, pick the least loaded kiln that has enough capacity
    5. Among equally loaded kilns, prefer the one with smallest excess capacity
       (tightest fit) to save larger kilns for bigger batches
    """
    # If a specific kiln is pre-assigned, check if it's in the available list
    if position and position.estimated_kiln_id:
        for kiln in available_kilns:
            if kiln.id == position.estimated_kiln_id:
                if _get_kiln_capacity_sqm(kiln) >= required_area_sqm:
                    return kiln

    is_gold = _is_gold_firing(cofiring_key, firing_temperature)

    # Separate kilns into Raku and non-Raku
    raku_kilns = [k for k in available_kilns if _is_raku_kiln(k)]
    non_raku_kilns = [k for k in available_kilns if not _is_raku_kiln(k)]

    if is_gold:
        # Gold firing: try Raku first, then fall back to others
        kiln_order = raku_kilns + non_raku_kilns
    else:
        # Standard firing: try non-Raku first, then Raku as overflow
        kiln_order = non_raku_kilns + raku_kilns

    best_kiln = None
    min_load = float("inf")
    best_excess = Decimal("999999")
    # Track whether we've found a kiln in the preferred group
    # so we don't pick a Raku for standard firing if non-Raku fits
    best_is_preferred = False

    window_start = batch_date - timedelta(days=3)
    window_end = batch_date + timedelta(days=3)

    # Determine proposed glaze type for rotation check
    proposed_glaze = cofiring_key or "standard"

    for kiln in kiln_order:
        cap = _get_kiln_capacity_sqm(kiln)
        if cap < required_area_sqm:
            continue  # too small

        # Rotation rules: check if proposed glaze can follow last fired glaze
        try:
            from business.services.rotation_rules import check_rotation_compliance
            rotation_result = check_rotation_compliance(
                db, kiln.id, proposed_glaze, kiln.factory_id,
            )
            if not rotation_result["compliant"]:
                logger.info(
                    "ROTATION_SKIP | kiln=%s | %s",
                    kiln.name, rotation_result["reason"],
                )
                continue  # skip this kiln, try next one
        except Exception as e:
            # Rotation check failure should not block batch formation
            logger.warning(
                "ROTATION_CHECK_ERROR | kiln=%s | %s", kiln.name, e,
            )

        is_raku = _is_raku_kiln(kiln)
        # A kiln is "preferred" if it matches the firing type:
        #   gold -> Raku is preferred; standard -> non-Raku is preferred
        kiln_is_preferred = (is_gold and is_raku) or (not is_gold and not is_raku)

        # If we already found a preferred kiln, skip non-preferred ones
        # (this implements "Raku as overflow only" for standard firings)
        if best_is_preferred and not kiln_is_preferred:
            continue

        # Count existing batches in the window
        batch_count = db.query(sa_func.count(Batch.id)).filter(
            Batch.resource_id == kiln.id,
            Batch.batch_date >= window_start,
            Batch.batch_date <= window_end,
            Batch.status.in_([BatchStatus.PLANNED.value, BatchStatus.IN_PROGRESS.value]),
        ).scalar() or 0

        excess = cap - required_area_sqm

        # If this kiln is preferred and current best is not, always take it
        if kiln_is_preferred and not best_is_preferred:
            min_load = batch_count
            best_excess = excess
            best_kiln = kiln
            best_is_preferred = True
            continue

        # Prefer: least loaded, then tightest fit
        if batch_count < min_load or (batch_count == min_load and excess < best_excess):
            min_load = batch_count
            best_excess = excess
            best_kiln = kiln
            best_is_preferred = kiln_is_preferred

    if best_kiln:
        is_raku_selected = _is_raku_kiln(best_kiln)
        if is_gold and is_raku_selected:
            logger.info(
                "RAKU_PREFERRED | Gold firing (700°C) assigned to Raku kiln %s",
                best_kiln.name,
            )
        elif not is_gold and is_raku_selected:
            logger.info(
                "RAKU_OVERFLOW | Standard firing using Raku kiln %s as overflow "
                "(all other kilns full or unavailable)",
                best_kiln.name,
            )

        # Log rotation decision
        logger.info(
            "ROTATION_OK | kiln=%s | glaze=%s assigned",
            best_kiln.name, proposed_glaze,
        )

    return best_kiln


# ────────────────────────────────────────────────────────────────
# §4  Core batch formation logic
# ────────────────────────────────────────────────────────────────

def suggest_or_create_batches(
    db: Session,
    factory_id: UUID,
    target_date: Optional[date] = None,
    mode: str = "auto",
) -> list[dict]:
    """
    Main entry: collect ready positions, group by temperature, form batches.

    Enhanced with temperature-based grouping:
    1. Get all unassigned positions ready for kiln (GLAZED, PRE_KILN_CHECK)
    2. Group into temperature-compatible buckets
    3. Within each bucket -> assign to kilns, create batches
    4. For each batch -> assign slowest firing profile

    Args:
        db: Database session
        factory_id: Factory to form batches for
        target_date: Optional. Only include positions with planned_kiln_date <= this.
                     Defaults to tomorrow if not set.
        mode: "auto" (creates PLANNED batches) or "suggest" (creates SUGGESTED batches)

    Returns:
        List of batch detail dicts with created batch info.
    """
    from business.services.firing_profiles import group_positions_by_temperature

    if target_date is None:
        target_date = date.today() + timedelta(days=1)

    batch_date = target_date

    # Step 1: Collect ready positions
    positions = _get_ready_positions(db, factory_id, target_date)
    if not positions:
        logger.info(
            "BATCH_FORMATION | factory=%s | No ready positions found for date %s",
            factory_id, target_date,
        )
        return []

    logger.info(
        "BATCH_FORMATION | factory=%s | Found %d ready positions",
        factory_id, len(positions),
    )

    # Step 2: Group by temperature
    temp_groups = group_positions_by_temperature(db, positions)

    # Step 3: Get available kilns
    available_kilns = _get_available_kilns(db, factory_id, batch_date)
    if not available_kilns:
        logger.warning(
            "BATCH_FORMATION | factory=%s | No available kilns on %s",
            factory_id, batch_date,
        )
        return []

    # Step 4: Build batches from each temperature group
    batch_status = BatchStatus.PLANNED if mode == "auto" else BatchStatus.SUGGESTED
    created_batches = []

    for group_id, group_positions in temp_groups.items():
        # Sub-split by co-firing compatibility (two-stage type, gold, etc.)
        cofiring_subgroups = _split_by_cofiring_compatibility(group_positions)

        for cofiring_key, sub_positions in cofiring_subgroups.items():
            if cofiring_key != "standard":
                logger.info(
                    "BATCH_FORMATION | factory=%s | temp_group=%s cofiring=%s | "
                    "%d positions in co-firing sub-group",
                    factory_id, group_id, cofiring_key, len(sub_positions),
                )

            batches_from_group = _build_batches_for_group(
                db=db,
                factory_id=factory_id,
                group_id=group_id,
                positions=sub_positions,
                available_kilns=available_kilns,
                batch_date=batch_date,
                batch_status=batch_status,
                cofiring_key=cofiring_key,
            )
            created_batches.extend(batches_from_group)

    db.commit()

    logger.info(
        "BATCH_FORMATION | factory=%s | Created %d batches, assigned %d positions",
        factory_id,
        len(created_batches),
        sum(b["positions_count"] for b in created_batches),
    )

    return created_batches


def _build_batches_for_group(
    db: Session,
    factory_id: UUID,
    group_id: Optional[UUID],
    positions: list[OrderPosition],
    available_kilns: list[Resource],
    batch_date: date,
    batch_status: BatchStatus,
    cofiring_key: Optional[str] = None,
) -> list[dict]:
    """
    Build one or more batches from a temperature group's positions.

    Uses geometry-based kiln capacity from calculate_kiln_capacity() to
    determine actual piece-level fit (edge vs flat optimization).
    Falls back to simple area comparison when geometry data is unavailable.

    For each position added to a batch:
    - Calls calculate_kiln_capacity() with position dimensions, shape,
      product_type, glaze placement, and kiln geometry
    - Tracks loading method (flat/edge) chosen for each position
    - Stores loading details in batch metadata_json
    """
    from business.services.firing_profiles import get_batch_firing_profile

    created_batches = []
    remaining_positions = list(positions)  # copy, sorted by priority already

    while remaining_positions:
        # Start a new batch: determine how many positions fit in one kiln
        batch_positions: list[OrderPosition] = []
        loading_entries: list[dict] = []
        total_area = Decimal("0")
        total_pieces_used = 0
        geometry_used = False

        # Find a kiln for this batch (use first position as reference)
        first_pos = remaining_positions[0]
        first_area = _get_position_area_sqm(first_pos)

        kiln = _find_best_kiln_for_batch(
            db, available_kilns, batch_date, first_area, first_pos,
            cofiring_key=cofiring_key,
        )

        if kiln is None:
            logger.warning(
                "BATCH_FORMATION | factory=%s | No kiln available for "
                "temperature group %s (%d remaining positions)",
                factory_id, group_id, len(remaining_positions),
            )
            break  # No more kilns available

        kiln_capacity = _get_kiln_capacity_sqm(kiln)

        # Load kiln constants and per-kiln rules once per batch
        constants, loading_rules = _get_kiln_constants_and_rules(db, kiln)

        # Compute kiln's max piece capacity for the first position
        # to estimate total kiln capacity in piece terms.
        # We track remaining capacity both by area (fallback) and by
        # piece count from geometry calculations.
        kiln_max_pieces = None  # will be set on first geometry calc

        # Fill the kiln
        still_remaining = []
        for pos in remaining_positions:
            pos_area = _get_position_area_sqm(pos)

            # Try geometry-based calculation first
            if _position_has_geometry(pos):
                cap_result = _calculate_position_loading(
                    pos, kiln, constants, loading_rules,
                )
            else:
                cap_result = None

            if cap_result is not None:
                optimal = cap_result.get("optimal", {})
                calc_pieces = optimal.get("total_pieces", 0)
                calc_area = optimal.get("total_area_sqm", 0.0)

                if calc_pieces == 0:
                    # Geometry says it does not fit at all (e.g. product type
                    # not allowed, too tall for edge, etc.)
                    reason = optimal.get("reason", "does not fit")
                    logger.debug(
                        "BATCH_SKIP | pos=%s kiln=%s | geometry: %s",
                        pos.id, kiln.name, reason,
                    )
                    still_remaining.append(pos)
                    continue

                # Check if adding this position exceeds kiln capacity.
                # Use the quantity the position actually needs vs. what
                # the kiln can hold for this product.
                pos_needed_pieces = pos.quantity
                if calc_pieces < pos_needed_pieces:
                    # Kiln cannot fit all pieces of this position
                    # Still try area-based fallback to see if it fits
                    if total_area + pos_area <= kiln_capacity:
                        batch_positions.append(pos)
                        total_area += pos_area
                        entry = _build_loading_plan_entry(pos, cap_result)
                        # Override with actual quantity needed
                        entry["total_pieces"] = pos_needed_pieces
                        entry["area_sqm"] = float(pos_area)
                        loading_entries.append(entry)
                        geometry_used = True
                    else:
                        still_remaining.append(pos)
                    continue

                # Geometry fit check: can the remaining kiln area hold this?
                candidate_area = total_area + pos_area
                if candidate_area <= kiln_capacity:
                    batch_positions.append(pos)
                    total_area = candidate_area
                    loading_entries.append(
                        _build_loading_plan_entry(pos, cap_result)
                    )
                    geometry_used = True
                else:
                    still_remaining.append(pos)
            else:
                # Fallback: simple area comparison (no geometry data)
                if total_area + pos_area <= kiln_capacity:
                    batch_positions.append(pos)
                    total_area += pos_area
                    # Build a basic loading entry without geometry detail
                    loading_entries.append({
                        "position_id": str(pos.id),
                        "loading_method": "flat",
                        "pieces_per_level": pos.quantity,
                        "levels_used": 1,
                        "total_pieces": pos.quantity,
                        "area_sqm": float(pos_area),
                        "geometry_fallback": True,
                    })
                else:
                    still_remaining.append(pos)

        remaining_positions = still_remaining

        if not batch_positions:
            # No positions fit -- possible if single position exceeds capacity.
            # Force it into the batch anyway (oversized position still needs firing).
            if remaining_positions:
                oversized = remaining_positions.pop(0)
                batch_positions = [oversized]
                total_area = _get_position_area_sqm(oversized)
                loading_entries = [{
                    "position_id": str(oversized.id),
                    "loading_method": "flat",
                    "pieces_per_level": oversized.quantity,
                    "levels_used": 1,
                    "total_pieces": oversized.quantity,
                    "area_sqm": float(total_area),
                    "oversized": True,
                }]
                logger.warning(
                    "BATCH_FORMATION | Oversized position %s (%.3f sqm) exceeds "
                    "kiln capacity (%.3f sqm) -- forced into batch",
                    oversized.id, _get_position_area_sqm(oversized), kiln_capacity,
                )
            else:
                break

        # Get the firing profile (slowest wins)
        profile = get_batch_firing_profile(db, batch_positions)

        # Determine target temperature from profile or recipe config
        target_temp = None
        if profile:
            target_temp = profile.target_temperature
        elif group_id:
            # Get temperature from first position's recipe
            for pos in batch_positions:
                if pos.recipe_id:
                    config = db.query(RecipeKilnConfig).filter(
                        RecipeKilnConfig.recipe_id == pos.recipe_id,
                    ).first()
                    if config and config.firing_temperature:
                        target_temp = config.firing_temperature
                        break

        # ── Filler tile selection ──────────────────────────────────
        # If there is unused kiln space, try to fill it with compatible
        # positions from the production queue.
        remaining_area = kiln_capacity - total_area
        filler_positions: list[OrderPosition] = []
        if remaining_area > Decimal("0.01"):
            fillers = _select_filler_tiles(
                db=db,
                kiln=kiln,
                batch_positions=batch_positions,
                remaining_area_sqm=remaining_area,
                batch_temperature=target_temp,
                constants=constants,
                loading_rules=loading_rules,
            )
            for filler_pos, filler_entry in fillers:
                batch_positions.append(filler_pos)
                filler_positions.append(filler_pos)
                loading_entries.append(filler_entry)
                total_area += _get_position_area_sqm(filler_pos)
                # Remove filler from remaining_positions if present
                if filler_pos in remaining_positions:
                    remaining_positions.remove(filler_pos)

        # ── Co-firing validation ──────────────────────────────────
        # Validate that all positions in this batch (including fillers)
        # are co-firing compatible.  Positions have already been sub-grouped
        # by _split_by_cofiring_compatibility() upstream, so this is a
        # safety-net check that also captures temperature spread issues.
        cofiring_result = _validate_batch_cofiring(
            db, batch_positions, kiln.id, constants,
        )
        if not cofiring_result["ok"]:
            logger.warning(
                "BATCH_COFIRING_FAIL | kiln=%s | %d positions | errors: %s",
                kiln.name, len(batch_positions),
                "; ".join(cofiring_result["errors"]),
            )
            # Remove incompatible fillers and re-validate
            if filler_positions:
                for fp in filler_positions:
                    batch_positions.remove(fp)
                    loading_entries = [
                        e for e in loading_entries
                        if e.get("position_id") != str(fp.id)
                    ]
                    total_area -= _get_position_area_sqm(fp)
                filler_positions = []
                # Re-validate without fillers
                cofiring_result = _validate_batch_cofiring(
                    db, batch_positions, kiln.id, constants,
                )

        if cofiring_result.get("warnings"):
            logger.info(
                "BATCH_COFIRING_WARN | kiln=%s | %s",
                kiln.name, "; ".join(cofiring_result["warnings"]),
            )

        # Build loading plan metadata
        kiln_cap_float = float(kiln_capacity)
        loading_plan = _build_loading_plan(loading_entries, kiln_cap_float)
        loading_plan["geometry_used"] = geometry_used
        loading_plan["cofiring_validation"] = {
            "ok": cofiring_result["ok"],
            "errors": cofiring_result["errors"],
            "warnings": cofiring_result["warnings"],
            "min_temperature": cofiring_result["min_temperature"],
            "max_temperature": cofiring_result["max_temperature"],
        }
        if filler_positions:
            loading_plan["filler_count"] = len(filler_positions)
            loading_plan["filler_position_ids"] = [
                str(p.id) for p in filler_positions
            ]

        # Create the Batch record
        batch = Batch(
            id=uuid_mod.uuid4(),
            resource_id=kiln.id,
            factory_id=factory_id,
            batch_date=batch_date,
            status=batch_status,
            created_by=BatchCreator.AUTO,
            firing_profile_id=profile.id if profile else None,
            target_temperature=target_temp,
            metadata_json=loading_plan,
        )
        db.add(batch)
        db.flush()  # get batch.id assigned

        # Link positions to this batch
        for pos in batch_positions:
            pos.batch_id = batch.id
            pos.resource_id = kiln.id  # actual kiln assignment

        fill_pct = float(
            (total_area / kiln_capacity * 100) if kiln_capacity > 0 else 0
        )

        batch_detail = {
            "batch_id": str(batch.id),
            "kiln_id": str(kiln.id),
            "kiln_name": kiln.name,
            "batch_date": str(batch_date),
            "status": batch_status.value,
            "positions_count": len(batch_positions),
            "total_area_sqm": float(total_area),
            "kiln_capacity_sqm": kiln_cap_float,
            "fill_percentage": fill_pct,
            "target_temperature": target_temp,
            "firing_profile_id": str(profile.id) if profile else None,
            "firing_profile_name": profile.name if profile else None,
            "firing_duration_hours": (
                float(profile.total_duration_hours)
                if profile and profile.total_duration_hours
                else None
            ),
            "temperature_group_id": str(group_id) if group_id else None,
            "position_ids": [str(p.id) for p in batch_positions],
            "filler_position_ids": [str(p.id) for p in filler_positions],
            "filler_count": len(filler_positions),
            "loading_plan": loading_plan.get("loading_plan"),
            "geometry_used": geometry_used,
        }
        created_batches.append(batch_detail)

        logger.info(
            "BATCH_CREATED | batch=%s kiln=%s | %d positions (%d fillers), "
            "%.2f/%.2f sqm (%.0f%%), temp=%s, geometry=%s",
            batch.id, kiln.name,
            len(batch_positions), len(filler_positions),
            total_area, kiln_capacity,
            fill_pct, target_temp, geometry_used,
        )

    return created_batches


# ────────────────────────────────────────────────────────────────
# §5  Assign firing profile to an existing batch
# ────────────────────────────────────────────────────────────────

def assign_batch_firing_profile(db: Session, batch_id: UUID) -> None:
    """
    Determine and store the firing profile for a batch.
    Uses get_batch_firing_profile() -- slowest profile among batch positions wins.
    Stores firing_profile_id and target_temperature on the batch record.
    """
    from business.services.firing_profiles import get_batch_firing_profile

    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        return

    positions = (
        db.query(OrderPosition)
        .filter(OrderPosition.batch_id == batch_id)
        .all()
    )
    if not positions:
        return

    profile = get_batch_firing_profile(db, positions)
    if profile:
        batch.firing_profile_id = profile.id
        batch.target_temperature = profile.target_temperature
        db.commit()

        logger.info(
            "BATCH_PROFILE_ASSIGNED | batch=%s | profile=%s temp=%d duration=%.1fh",
            batch_id, profile.name, profile.target_temperature,
            float(profile.total_duration_hours),
        )


# ────────────────────────────────────────────────────────────────
# §6  PM batch management
# ────────────────────────────────────────────────────────────────

def pm_confirm_batch(
    db: Session,
    batch_id: UUID,
    pm_user_id: UUID,
    adjustments: Optional[dict] = None,
) -> Batch:
    """
    PM confirms/adjusts a suggested batch.

    Adjustments can include:
    - notes: str
    - remove_position_ids: list[UUID] - positions to remove from batch
    - add_position_ids: list[UUID] - positions to add to batch
    - batch_date: date - change batch date
    """
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise ValueError(f"Batch {batch_id} not found")

    if batch.status != BatchStatus.SUGGESTED:
        raise ValueError(
            f"Can only confirm SUGGESTED batches, current status: {batch.status.value}"
        )

    if adjustments:
        if "notes" in adjustments:
            batch.notes = adjustments["notes"]

        if "batch_date" in adjustments:
            batch.batch_date = adjustments["batch_date"]

        if "remove_position_ids" in adjustments:
            for pos_id in adjustments["remove_position_ids"]:
                pos = db.query(OrderPosition).filter(
                    OrderPosition.id == pos_id,
                    OrderPosition.batch_id == batch_id,
                ).first()
                if pos:
                    pos.batch_id = None
                    pos.resource_id = None

        if "add_position_ids" in adjustments:
            for pos_id in adjustments["add_position_ids"]:
                pos = db.query(OrderPosition).filter(
                    OrderPosition.id == pos_id,
                    OrderPosition.batch_id.is_(None),
                ).first()
                if pos:
                    pos.batch_id = batch_id
                    pos.resource_id = batch.resource_id

    batch.status = BatchStatus.PLANNED
    batch.created_by = BatchCreator.MANUAL
    batch.updated_at = datetime.now(timezone.utc)

    # Re-assign firing profile after adjustments
    assign_batch_firing_profile(db, batch_id)

    # Re-generate loading plan after adjustments
    _regenerate_batch_loading_plan(db, batch)

    db.commit()
    db.refresh(batch)

    logger.info(
        "BATCH_CONFIRMED | batch=%s | by PM %s", batch_id, pm_user_id,
    )
    return batch


def _regenerate_batch_loading_plan(db: Session, batch: Batch) -> None:
    """
    Regenerate the loading plan metadata for a batch after adjustments.
    """
    kiln = db.query(Resource).filter(Resource.id == batch.resource_id).first()
    if not kiln:
        return

    positions = db.query(OrderPosition).filter(
        OrderPosition.batch_id == batch.id,
    ).all()
    if not positions:
        batch.metadata_json = None
        return

    constants, loading_rules = _get_kiln_constants_and_rules(db, kiln)
    kiln_capacity = float(_get_kiln_capacity_sqm(kiln))

    loading_entries = []
    geometry_used = False

    for pos in positions:
        if _position_has_geometry(pos):
            cap_result = _calculate_position_loading(
                pos, kiln, constants, loading_rules,
            )
        else:
            cap_result = None

        if cap_result is not None:
            optimal = cap_result.get("optimal", {})
            if optimal.get("total_pieces", 0) > 0:
                loading_entries.append(
                    _build_loading_plan_entry(pos, cap_result)
                )
                geometry_used = True
                continue

        # Fallback
        pos_area = float(_get_position_area_sqm(pos))
        loading_entries.append({
            "position_id": str(pos.id),
            "loading_method": "flat",
            "pieces_per_level": pos.quantity,
            "levels_used": 1,
            "total_pieces": pos.quantity,
            "area_sqm": pos_area,
            "geometry_fallback": True,
        })

    plan = _build_loading_plan(loading_entries, kiln_capacity)
    plan["geometry_used"] = geometry_used
    batch.metadata_json = plan


def pm_reject_batch(db: Session, batch_id: UUID, pm_user_id: UUID) -> None:
    """PM rejects suggested batch -> unassign all positions, delete batch."""
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise ValueError(f"Batch {batch_id} not found")

    if batch.status != BatchStatus.SUGGESTED:
        raise ValueError(
            f"Can only reject SUGGESTED batches, current status: {batch.status.value}"
        )

    # Unassign all positions
    positions = db.query(OrderPosition).filter(
        OrderPosition.batch_id == batch_id,
    ).all()
    for pos in positions:
        pos.batch_id = None
        pos.resource_id = None

    # Delete the batch
    db.delete(batch)
    db.commit()

    logger.info(
        "BATCH_REJECTED | batch=%s | by PM %s | %d positions unassigned",
        batch_id, pm_user_id, len(positions),
    )


# ────────────────────────────────────────────────────────────────
# §7  Batch lifecycle transitions
# ────────────────────────────────────────────────────────────────

def start_batch(db: Session, batch_id: UUID) -> Batch:
    """
    Mark batch as IN_PROGRESS (kiln loaded, firing started).
    All positions in the batch transition to LOADED_IN_KILN.
    """
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise ValueError(f"Batch {batch_id} not found")

    if batch.status not in (BatchStatus.PLANNED, BatchStatus.SUGGESTED):
        raise ValueError(
            f"Cannot start batch with status {batch.status.value}. "
            f"Must be PLANNED or SUGGESTED."
        )

    batch.status = BatchStatus.IN_PROGRESS
    batch.updated_at = datetime.now(timezone.utc)

    # Transition all positions to LOADED_IN_KILN
    positions = db.query(OrderPosition).filter(
        OrderPosition.batch_id == batch_id,
    ).all()

    from business.services.status_machine import validate_status_transition

    for pos in positions:
        old_status = pos.status.value if hasattr(pos.status, 'value') else str(pos.status)
        if validate_status_transition(old_status, PositionStatus.LOADED_IN_KILN.value):
            pos.status = PositionStatus.LOADED_IN_KILN
            pos.updated_at = datetime.now(timezone.utc)
        else:
            logger.warning(
                "BATCH_START | Cannot transition position %s from %s to LOADED_IN_KILN",
                pos.id, old_status,
            )

    db.commit()
    db.refresh(batch)

    logger.info(
        "BATCH_STARTED | batch=%s | %d positions loaded in kiln %s",
        batch_id, len(positions), batch.resource_id,
    )
    return batch


def complete_batch(db: Session, batch_id: UUID) -> Batch:
    """
    Mark batch as DONE (firing completed).
    All positions in the batch transition to FIRED,
    then route_after_firing decides their next status (sorting or re-fire).
    """
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise ValueError(f"Batch {batch_id} not found")

    if batch.status != BatchStatus.IN_PROGRESS:
        raise ValueError(
            f"Cannot complete batch with status {batch.status.value}. "
            f"Must be IN_PROGRESS."
        )

    batch.status = BatchStatus.DONE
    batch.updated_at = datetime.now(timezone.utc)

    # Transition all positions to FIRED (status_machine will route from there)
    positions = db.query(OrderPosition).filter(
        OrderPosition.batch_id == batch_id,
    ).all()

    from business.services.status_machine import (
        validate_status_transition,
        route_after_firing,
    )

    for pos in positions:
        old_status = pos.status.value if hasattr(pos.status, 'value') else str(pos.status)
        if validate_status_transition(old_status, PositionStatus.FIRED.value):
            pos.status = PositionStatus.FIRED
            pos.updated_at = datetime.now(timezone.utc)
            # Route after firing (multi-firing check)
            route_after_firing(db, pos)
        else:
            logger.warning(
                "BATCH_COMPLETE | Cannot transition position %s from %s to FIRED",
                pos.id, old_status,
            )

    # ── Record actual kiln load vs calculated capacity ──────────
    try:
        kiln = db.query(Resource).filter(Resource.id == batch.resource_id).first()
        actual_pieces = len(positions)
        actual_area = sum(_get_position_area_sqm(p) for p in positions)
        calculated_cap = int(_get_kiln_capacity_sqm(kiln)) if kiln else 0
        loading_type = "auto" if batch.created_by == BatchCreator.AUTO else "manual"

        db.add(KilnActualLoad(
            kiln_id=batch.resource_id,
            batch_id=batch.id,
            actual_pieces=actual_pieces,
            actual_area_sqm=actual_area,
            calculated_capacity=calculated_cap,
            loading_type=loading_type,
        ))
    except Exception:
        logger.warning(
            "Failed to record KilnActualLoad for batch %s", batch_id,
            exc_info=True,
        )

    db.commit()
    db.refresh(batch)

    logger.info(
        "BATCH_COMPLETED | batch=%s | %d positions fired in kiln %s",
        batch_id, len(positions), batch.resource_id,
    )

    # --- Post-completion: assign QC checks for fired positions ---
    try:
        from business.services.quality_control import assign_qc_checks
        qc_tasks = assign_qc_checks(db, batch_id, batch.factory_id)
        if qc_tasks:
            db.commit()
            logger.info(
                "BATCH_QC_ASSIGNED | batch=%s | %d QC tasks created",
                batch_id, len(qc_tasks),
            )
    except Exception as e:
        logger.error(
            "BATCH_QC_FAILED | batch=%s | Failed to assign QC checks: %s",
            batch_id, e,
        )

    # --- Post-completion: reconcile stage transition (kiln exit) ---
    try:
        from business.services.reconciliation import reconcile_stage_transition
        fired_count = sum(
            1 for p in positions
            if (hasattr(p.status, 'value') and p.status.value == PositionStatus.FIRED.value)
            or str(p.status) == PositionStatus.FIRED.value
        )
        reconcile_stage_transition(
            db=db,
            factory_id=batch.factory_id,
            batch_id=batch_id,
            stage_from="in_kiln",
            stage_to="fired",
            input_count=len(positions),
            outputs={"good": fired_count, "defect": 0, "write_off": len(positions) - fired_count},
        )
        db.commit()
    except Exception as e:
        logger.error(
            "BATCH_RECONCILIATION_FAILED | batch=%s | %s",
            batch_id, e,
        )

    return batch


