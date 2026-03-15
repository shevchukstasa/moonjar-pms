"""
Batch Formation service.
Business Logic: §7, §19

Groups kiln-ready positions into temperature-compatible batches,
assigns kilns, and attaches firing profiles.
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
            return Decimal(str(w * h)) / Decimal("10000")  # cm² → m²
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
# §3  Find best kiln for a temperature group
# ────────────────────────────────────────────────────────────────

def _find_best_kiln_for_batch(
    db: Session,
    available_kilns: list[Resource],
    batch_date: date,
    required_area_sqm: Decimal,
    position: Optional[OrderPosition] = None,
) -> Optional[Resource]:
    """
    Find the best kiln for a batch.

    Strategy:
    1. If position has an estimated_kiln_id and it's available, prefer it
    2. Otherwise, pick the least loaded kiln that has enough capacity
    3. Among equally loaded kilns, prefer the one with smallest excess capacity
       (tightest fit) to save larger kilns for bigger batches
    """
    # If a specific kiln is pre-assigned, check if it's in the available list
    if position and position.estimated_kiln_id:
        for kiln in available_kilns:
            if kiln.id == position.estimated_kiln_id:
                if _get_kiln_capacity_sqm(kiln) >= required_area_sqm:
                    return kiln

    best_kiln = None
    min_load = float("inf")
    best_excess = Decimal("999999")

    window_start = batch_date - timedelta(days=3)
    window_end = batch_date + timedelta(days=3)

    for kiln in available_kilns:
        cap = _get_kiln_capacity_sqm(kiln)
        if cap < required_area_sqm:
            continue  # too small

        # Count existing batches in the window
        batch_count = db.query(sa_func.count(Batch.id)).filter(
            Batch.resource_id == kiln.id,
            Batch.batch_date >= window_start,
            Batch.batch_date <= window_end,
            Batch.status.in_([BatchStatus.PLANNED.value, BatchStatus.IN_PROGRESS.value]),
        ).scalar() or 0

        excess = cap - required_area_sqm

        # Prefer: least loaded, then tightest fit
        if batch_count < min_load or (batch_count == min_load and excess < best_excess):
            min_load = batch_count
            best_excess = excess
            best_kiln = kiln

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
        batches_from_group = _build_batches_for_group(
            db=db,
            factory_id=factory_id,
            group_id=group_id,
            positions=group_positions,
            available_kilns=available_kilns,
            batch_date=batch_date,
            batch_status=batch_status,
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
) -> list[dict]:
    """
    Build one or more batches from a temperature group's positions.

    Fills kiln capacity greedily: keeps adding positions until the kiln
    is full, then starts a new batch on the next available kiln.
    """
    from business.services.firing_profiles import get_batch_firing_profile

    created_batches = []
    remaining_positions = list(positions)  # copy, sorted by priority already

    while remaining_positions:
        # Start a new batch: determine how many positions fit in one kiln
        batch_positions: list[OrderPosition] = []
        total_area = Decimal("0")

        # Find a kiln for this batch (use first position as reference)
        first_pos = remaining_positions[0]
        first_area = _get_position_area_sqm(first_pos)

        kiln = _find_best_kiln_for_batch(
            db, available_kilns, batch_date, first_area, first_pos,
        )

        if kiln is None:
            logger.warning(
                "BATCH_FORMATION | factory=%s | No kiln available for "
                "temperature group %s (%d remaining positions)",
                factory_id, group_id, len(remaining_positions),
            )
            break  # No more kilns available

        kiln_capacity = _get_kiln_capacity_sqm(kiln)

        # Fill the kiln
        still_remaining = []
        for pos in remaining_positions:
            pos_area = _get_position_area_sqm(pos)
            if total_area + pos_area <= kiln_capacity:
                batch_positions.append(pos)
                total_area += pos_area
            else:
                still_remaining.append(pos)

        remaining_positions = still_remaining

        if not batch_positions:
            # No positions fit — possible if single position exceeds capacity.
            # Force it into the batch anyway (oversized position still needs firing).
            if remaining_positions:
                oversized = remaining_positions.pop(0)
                batch_positions = [oversized]
                total_area = _get_position_area_sqm(oversized)
                logger.warning(
                    "BATCH_FORMATION | Oversized position %s (%.3f sqm) exceeds "
                    "kiln capacity (%.3f sqm) — forced into batch",
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
        )
        db.add(batch)
        db.flush()  # get batch.id assigned

        # Link positions to this batch
        for pos in batch_positions:
            pos.batch_id = batch.id
            pos.resource_id = kiln.id  # actual kiln assignment

        batch_detail = {
            "batch_id": str(batch.id),
            "kiln_id": str(kiln.id),
            "kiln_name": kiln.name,
            "batch_date": str(batch_date),
            "status": batch_status.value,
            "positions_count": len(batch_positions),
            "total_area_sqm": float(total_area),
            "kiln_capacity_sqm": float(kiln_capacity),
            "fill_percentage": float(
                (total_area / kiln_capacity * 100) if kiln_capacity > 0 else 0,
            ),
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
        }
        created_batches.append(batch_detail)

        logger.info(
            "BATCH_CREATED | batch=%s kiln=%s | %d positions, %.2f/%.2f sqm (%.0f%%), temp=%s",
            batch.id, kiln.name,
            len(batch_positions), total_area, kiln_capacity,
            batch_detail["fill_percentage"],
            target_temp,
        )

    return created_batches


def build_batch_proposals(
    db: Session,
    factory_id: UUID,
    positions: list[OrderPosition],
) -> list[dict]:
    """
    Group positions into optimal batch proposals without creating DB records.
    Returns list of proposal dicts for PM review.

    Steps:
    1. Group by temperature using firing_profiles.group_positions_by_temperature()
    2. Within each temperature bucket:
       a. Match to compatible kilns
       b. Fill kiln capacity
       c. Select firing profile using get_batch_firing_profile() (slowest wins)
    3. Return list of batch proposals with assigned positions + profiles
    """
    from business.services.firing_profiles import (
        group_positions_by_temperature,
        get_batch_firing_profile,
    )

    batch_date = date.today() + timedelta(days=1)
    available_kilns = _get_available_kilns(db, factory_id, batch_date)
    temp_groups = group_positions_by_temperature(db, positions)

    proposals = []
    for group_id, group_positions in temp_groups.items():
        remaining = list(group_positions)

        while remaining:
            first_pos = remaining[0]
            first_area = _get_position_area_sqm(first_pos)
            kiln = _find_best_kiln_for_batch(
                db, available_kilns, batch_date, first_area, first_pos,
            )
            if kiln is None:
                break

            kiln_capacity = _get_kiln_capacity_sqm(kiln)
            batch_positions: list[OrderPosition] = []
            total_area = Decimal("0")
            still_remaining = []

            for pos in remaining:
                pos_area = _get_position_area_sqm(pos)
                if total_area + pos_area <= kiln_capacity:
                    batch_positions.append(pos)
                    total_area += pos_area
                else:
                    still_remaining.append(pos)

            remaining = still_remaining

            if not batch_positions:
                if remaining:
                    batch_positions = [remaining.pop(0)]
                    total_area = _get_position_area_sqm(batch_positions[0])
                else:
                    break

            profile = get_batch_firing_profile(db, batch_positions)
            proposals.append({
                "kiln_id": str(kiln.id),
                "kiln_name": kiln.name,
                "temperature_group_id": str(group_id) if group_id else None,
                "positions_count": len(batch_positions),
                "total_area_sqm": float(total_area),
                "kiln_capacity_sqm": float(kiln_capacity),
                "fill_percentage": float(
                    (total_area / kiln_capacity * 100) if kiln_capacity > 0 else 0,
                ),
                "firing_profile_name": profile.name if profile else None,
                "target_temperature": profile.target_temperature if profile else None,
                "firing_duration_hours": (
                    float(profile.total_duration_hours) if profile else None
                ),
                "position_ids": [str(p.id) for p in batch_positions],
            })

    return proposals


# ────────────────────────────────────────────────────────────────
# §5  Assign firing profile to an existing batch
# ────────────────────────────────────────────────────────────────

def assign_batch_firing_profile(db: Session, batch_id: UUID) -> None:
    """
    Determine and store the firing profile for a batch.
    Uses get_batch_firing_profile() — slowest profile among batch positions wins.
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

    db.commit()
    db.refresh(batch)

    logger.info(
        "BATCH_CONFIRMED | batch=%s | by PM %s", batch_id, pm_user_id,
    )
    return batch


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

    db.commit()
    db.refresh(batch)

    logger.info(
        "BATCH_COMPLETED | batch=%s | %d positions fired in kiln %s",
        batch_id, len(positions), batch.resource_id,
    )
    return batch


# ────────────────────────────────────────────────────────────────
# §8  Fill remaining space with filler tiles
# ────────────────────────────────────────────────────────────────

def fill_with_filler_tiles(db: Session, factory_id: UUID) -> None:
    """
    Fill remaining space in PLANNED batches with filler tiles.
    Filler tiles are positions from stock collections or non-urgent orders.

    This is a placeholder — full implementation depends on factory-specific
    filler tile inventory which will be configured in a later iteration.
    """
    batches = db.query(Batch).filter(
        Batch.factory_id == factory_id,
        Batch.status == BatchStatus.PLANNED,
    ).all()

    for batch in batches:
        kiln = db.query(Resource).get(batch.resource_id)
        if not kiln:
            continue

        kiln_capacity = _get_kiln_capacity_sqm(kiln)

        # Calculate current fill
        batch_positions = db.query(OrderPosition).filter(
            OrderPosition.batch_id == batch.id,
        ).all()
        current_area = sum(
            _get_position_area_sqm(p) for p in batch_positions
        )

        remaining_capacity = kiln_capacity - current_area
        if remaining_capacity <= Decimal("0.01"):
            continue  # Already full

        logger.info(
            "FILLER_CHECK | batch=%s | %.3f sqm remaining of %.3f sqm capacity",
            batch.id, remaining_capacity, kiln_capacity,
        )
        # Future: find filler tiles from stock and add them to this batch

    db.commit()
