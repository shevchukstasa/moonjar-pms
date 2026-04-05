"""
Production Scheduler — upfront TOC/DBR backward scheduling.
Business Logic: §5, §17, §20

When an order comes in, the entire production path is planned immediately
using backward scheduling from the deadline:

  TOC/DBR model:
    Drum   = kiln (the constraint)
    Buffer = 1-day time buffers before and after the kiln
    Rope   = pull work to arrive at the kiln on time

Dates are calculated per-position (not per-order) because each position
may go to a different kiln with different availability.

Auto-reschedules on:
  - Status changes (delays)
  - Kiln breakdowns (MAINTENANCE_EMERGENCY)
  - Manual reorder by PM
  - Material blocking/unblocking
"""
from uuid import UUID
from datetime import date, timedelta
from typing import Optional
import logging

from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func

from api.models import (
    OrderPosition,
    ProductionOrder,
    Resource,
    ScheduleSlot,
    Batch,
    KilnMaintenanceSchedule,
)
from api.enums import (
    PositionStatus,
    ResourceType,
    ResourceStatus,
    BatchStatus,
    ScheduleSlotStatus,
    MaintenanceStatus,
)

logger = logging.getLogger("moonjar.production_scheduler")


# ────────────────────────────────────────────────────────────────
# Standard durations (days) — will be configurable per factory later
# ────────────────────────────────────────────────────────────────

GLAZING_DURATION_DAYS = 1        # glazing work
PRE_KILN_CHECK_DAYS = 1         # engobe check + pre-kiln QC (rounded up from 0.5)
FIRING_DURATION_DAYS = 1        # kiln firing (depends on profile, but 1 day typical)
COOLING_DAYS = 1                # kiln cooldown
SORTING_DAYS = 1                # sorting + packing
QC_DAYS = 1                     # quality check (rounded up from 0.5)
BUFFER_DAYS = 1                 # TOC buffer — safety margin around the constraint



# ────────────────────────────────────────────────────────────────
# Line Resource Constraints
# ────────────────────────────────────────────────────────────────

# Which production stage is bottlenecked by which line resource type.
# If a stage is not listed, no line resource constraint is applied.
_STAGE_RESOURCE_MAP = {
    'engobe':               'work_table',     # engobe applied on work tables
    'glazing':              'work_table',     # glazing applied on work tables
    'drying_engobe':        'drying_rack',    # drying on shelving racks
    'drying_glaze':         'drying_rack',    # drying on shelving racks
    'edge_cleaning_loading': 'glazing_board', # tiles sit on glazing boards
}


def _get_line_resource_capacity(
    db: Session,
    factory_id: UUID,
    resource_type: str,
) -> dict:
    """Get total capacity of a line resource type across all active units.

    Returns dict with aggregated values:
      total_sqm     — sum(capacity_sqm * num_units)
      total_boards  — sum(capacity_boards * num_units)
      total_pcs     — sum(capacity_pcs * num_units)

    Returns empty dict if no resources configured (= no constraint).
    """
    from sqlalchemy import text

    try:
        result = db.execute(text("""
            SELECT
                COALESCE(SUM(capacity_sqm * num_units), 0) as total_sqm,
                COALESCE(SUM(capacity_boards * num_units), 0) as total_boards,
                COALESCE(SUM(capacity_pcs * num_units), 0) as total_pcs,
                COUNT(*) as cnt
            FROM production_line_resources
            WHERE factory_id = :fid
              AND resource_type = :rtype
              AND is_active = true
        """), {"fid": str(factory_id), "rtype": resource_type}).fetchone()

        if not result or result.cnt == 0:
            return {}  # no constraint configured

        return {
            "total_sqm": float(result.total_sqm or 0),
            "total_boards": int(result.total_boards or 0),
            "total_pcs": int(result.total_pcs or 0),
        }
    except Exception as e:
        logger.debug("Line resource lookup failed for %s: %s", resource_type, e)
        return {}


def _get_tiles_per_board(
    db: Session,
    position: "Optional[OrderPosition]",
) -> int:
    """Get tiles_per_board from GlazingBoardSpec if available.

    Uses position.size_id -> glazing_board_specs lookup.
    Falls back to on-the-fly calculation from tile dimensions.
    """
    if position is None:
        return 10

    # Try GlazingBoardSpec lookup via size_id
    size_id = getattr(position, 'size_id', None)
    if size_id:
        try:
            from api.models import GlazingBoardSpec
            spec = db.query(GlazingBoardSpec).filter(
                GlazingBoardSpec.size_id == size_id,
            ).first()
            if spec and spec.tiles_per_board:
                return int(spec.tiles_per_board)
        except Exception:
            pass

    # Fallback: calculate on-the-fly from tile dimensions
    w = float(position.width_cm or 0) if getattr(position, 'width_cm', None) else 0
    h = float(position.length_cm or 0) if getattr(position, 'length_cm', None) else 0
    if w > 0 and h > 0:
        try:
            from business.services.glazing_board import calculate_glazing_board
            result = calculate_glazing_board(int(w * 10), int(h * 10))
            return result.tiles_per_board
        except Exception:
            pass

    return 10  # safe default


def _create_board_order_task(
    db: Session,
    factory_id: UUID,
    boards_needed: int,
    boards_available: int,
    deficit: int,
    position_id: "Optional[UUID]" = None,
    order_id: "Optional[UUID]" = None,
) -> None:
    """Create a PM task to order additional glazing boards if deficit detected.

    Deduplicates: won't create if a PENDING task already exists for this factory.
    """
    try:
        from api.models import Task
        from api.enums import TaskType, TaskStatus, UserRole
        import json

        # Check for existing pending task (avoid spam)
        existing = db.query(Task).filter(
            Task.factory_id == factory_id,
            Task.type == TaskType.BOARD_ORDER_NEEDED,
            Task.status == TaskStatus.PENDING,
        ).first()
        if existing:
            return  # already has a pending task

        task = Task(
            factory_id=factory_id,
            type=TaskType.BOARD_ORDER_NEEDED,
            status=TaskStatus.PENDING,
            assigned_role=UserRole.PRODUCTION_MANAGER,
            related_order_id=order_id,
            related_position_id=position_id,
            blocking=False,
            priority=6,
            description=(
                f"Glazing board shortage: need {boards_needed} boards "
                f"but only {boards_available} available (deficit: {deficit}). "
                f"Order or prepare additional boards for optimal production flow."
            ),
            metadata_json=json.dumps({
                "boards_needed": boards_needed,
                "boards_available": boards_available,
                "deficit": deficit,
            }),
        )
        db.add(task)
        db.flush()
        logger.info(
            "BOARD_ORDER_TASK | factory=%s | need=%d avail=%d deficit=%d",
            factory_id, boards_needed, boards_available, deficit,
        )
    except Exception as e:
        logger.debug("Failed to create board order task: %s", e)


def _apply_resource_constraint(
    speed_days: int,
    stage: str,
    resource_cap: dict,
    total_sqm: float,
    total_pcs: int,
    fixed_hours: float = 0,
    tiles_per_board: int = 10,
    db: "Optional[Session]" = None,
    position: "Optional[OrderPosition]" = None,
) -> int:
    """Apply line resource constraint to a stage duration.

    Logic per resource type:
      work_table: batch_area_sqm / table_total_sqm → cycles needed
      drying_rack: batch_area_sqm / rack_total_sqm → drying cycles,
                   each cycle = fixed_duration hours
      glazing_board: batch_pcs / total_pcs → cycles needed

    Returns max(speed_days, constraint_days).
    """
    import math

    if not resource_cap:
        return speed_days

    constraint_days = speed_days

    if stage in ('engobe', 'glazing'):
        # Work table constraint: total batch sqm / available table area
        # = how many "batches" need to pass through the tables
        table_sqm = resource_cap.get("total_sqm", 0)
        if table_sqm > 0 and total_sqm > 0:
            cycles = math.ceil(total_sqm / table_sqm)
            constraint_days = max(constraint_days, cycles)
            if cycles > speed_days:
                logger.info(
                    "LINE_CONSTRAINT | %s | tables=%.1f m² batch=%.1f m² "
                    "→ %d cycles (was %d days from speed)",
                    stage, table_sqm, total_sqm, cycles, speed_days,
                )

    elif stage in ('drying_engobe', 'drying_glaze'):
        # Drying rack constraint: batch sqm / rack capacity → drying cycles
        # Each cycle takes fixed_hours to dry (from stage speed)
        rack_sqm = resource_cap.get("total_sqm", 0)
        rack_boards = resource_cap.get("total_boards", 0)

        if rack_sqm > 0 and total_sqm > 0:
            cycles = math.ceil(total_sqm / rack_sqm)
            if cycles > 1:
                # Multiple drying cycles: each takes fixed_hours
                total_hours = fixed_hours * cycles if fixed_hours > 0 else cycles * 3.0
                hours_per_day = 16.0  # 2 shifts × 8h
                constraint_days = max(constraint_days, math.ceil(total_hours / hours_per_day))
                if constraint_days > speed_days:
                    logger.info(
                        "LINE_CONSTRAINT | %s | rack=%.1f m² batch=%.1f m² "
                        "→ %d cycles × %.1fh = %d days (was %d)",
                        stage, rack_sqm, total_sqm,
                        cycles, fixed_hours, constraint_days, speed_days,
                    )
        elif rack_boards > 0 and total_pcs > 0:
            # Board-based constraint using tiles_per_board from GlazingBoardSpec
            boards_needed = math.ceil(total_pcs / tiles_per_board)
            cycles = math.ceil(boards_needed / rack_boards)
            if cycles > 1:
                total_hours = fixed_hours * cycles if fixed_hours > 0 else cycles * 3.0
                hours_per_day = 16.0
                constraint_days = max(constraint_days, math.ceil(total_hours / hours_per_day))

    elif stage == 'edge_cleaning_loading':
        # Glazing board constraint: tiles sit on boards during edge cleaning
        board_pcs = resource_cap.get("total_pcs", 0)
        if board_pcs > 0 and total_pcs > 0:
            # Calculate actual boards needed using tiles_per_board
            boards_needed = math.ceil(total_pcs / tiles_per_board)
            if boards_needed > board_pcs:
                deficit = boards_needed - board_pcs
                logger.info(
                    "BOARD_DEFICIT | need=%d boards, have=%d, deficit=%d "
                    "(%d pcs, %d tiles/board)",
                    boards_needed, board_pcs, deficit,
                    total_pcs, tiles_per_board,
                )
                # Create PM task to order more boards
                if db and position:
                    _create_board_order_task(
                        db,
                        factory_id=position.factory_id,
                        boards_needed=boards_needed,
                        boards_available=board_pcs,
                        deficit=deficit,
                        position_id=getattr(position, 'id', None),
                        order_id=getattr(position, 'order_id', None),
                    )

            cycles = math.ceil(total_pcs / board_pcs)
            constraint_days = max(constraint_days, cycles)
            if cycles > speed_days:
                logger.info(
                    "LINE_CONSTRAINT | %s | boards=%d available, need=%d pcs "
                    "→ %d cycles (was %d days)",
                    stage, board_pcs, total_pcs, cycles, speed_days,
                )

    return constraint_days


def _get_effective_brigade_size(
    db: Session,
    factory_id: UUID,
    stage: str,
    static_brigade: int,
) -> int:
    """Return actual worker count assigned to a stage at this factory.

    Looks up ShiftAssignment for today.  If today has no assignments, uses
    the most recent assignment date (workers don't change daily).
    Falls back to *static_brigade* when no assignment data exists.
    """
    from api.models import ShiftAssignment
    import sqlalchemy as sa

    today = date.today()

    # Find the most recent date with assignments for this factory+stage
    latest_date = (
        db.query(sa_func.max(ShiftAssignment.date))
        .filter(
            ShiftAssignment.factory_id == factory_id,
            ShiftAssignment.stage == stage,
            ShiftAssignment.date <= today,
        )
        .scalar()
    )

    if latest_date is None:
        return static_brigade

    count = (
        db.query(sa_func.count(sa.distinct(ShiftAssignment.user_id)))
        .filter(
            ShiftAssignment.factory_id == factory_id,
            ShiftAssignment.stage == stage,
            ShiftAssignment.date == latest_date,
        )
        .scalar()
    ) or 0

    if count > 0:
        if count != static_brigade:
            logger.info(
                "DYNAMIC_BRIGADE | stage=%s | static=%d actual=%d",
                stage, static_brigade, count,
            )
        return count

    return static_brigade


def _get_stage_duration_days(
    db: Session,
    factory_id: UUID,
    stage: str,
    total_sqm: float = 0,
    total_pcs: int = 0,
    position: "Optional[OrderPosition]" = None,
) -> int:
    """Calculate duration in working days for a stage.

    Priority:
      1. StageTypologySpeed — match position to typology, then look up speed
      2. ProcessStep — generic factory-level speed for the stage
      3. Fallback to 1 day

    After calculating speed-based duration, applies line resource constraints
    (work tables, drying racks, glazing boards) — the actual days is the MAX
    of speed-based days and resource-constrained days.
    """
    import math

    speed_days = 1
    fixed_hours = 0  # track fixed_duration hours for drying constraint calc

    # ── Priority 1: StageTypologySpeed (typology-aware) ──
    if position is not None:
        try:
            from api.models import StageTypologySpeed
            from business.services.typology_matcher import find_matching_typology

            typology = find_matching_typology(db, position)
            if typology:
                speed = db.query(StageTypologySpeed).filter(
                    StageTypologySpeed.typology_id == typology.id,
                    StageTypologySpeed.stage == stage,
                ).first()

                if speed and speed.productivity_rate:
                    rate_basis = speed.rate_basis or 'per_person'
                    if rate_basis == 'fixed_duration':
                        fixed_hours = float(speed.productivity_rate)
                    dynamic_brigade = _get_effective_brigade_size(
                        db, factory_id, stage, speed.brigade_size or 1,
                    )
                    result = _calc_hours_from_speed(
                        rate=float(speed.productivity_rate),
                        rate_unit=speed.rate_unit or 'pcs',
                        rate_basis=rate_basis,
                        time_unit=speed.time_unit or 'hour',
                        shift_count=speed.shift_count or 2,
                        shift_duration_hours=float(speed.shift_duration_hours or 8.0),
                        brigade_size=dynamic_brigade,
                        total_sqm=total_sqm,
                        total_pcs=total_pcs,
                    )
                    if result is not None:
                        speed_days = result
                        # Apply resource constraint and return
                        if stage in _STAGE_RESOURCE_MAP:
                            resource_cap = _get_line_resource_capacity(
                                db, factory_id, _STAGE_RESOURCE_MAP[stage],
                            )
                            tpb = _get_tiles_per_board(db, position)
                            return _apply_resource_constraint(
                                speed_days, stage, resource_cap,
                                total_sqm, total_pcs, fixed_hours, tpb,
                                db=db, position=position,
                            )
                        return speed_days
        except Exception as e:
            logger.debug("StageTypologySpeed lookup failed for %s: %s", stage, e)

    # ── Priority 2: ProcessStep (generic) ──
    try:
        from api.models import ProcessStep
        step = db.query(ProcessStep).filter(
            ProcessStep.factory_id == factory_id,
            ProcessStep.stage == stage,
            ProcessStep.is_active == True,
            ProcessStep.productivity_rate.isnot(None),
        ).first()

        if step and step.productivity_rate:
            rate = float(step.productivity_rate)
            if rate > 0:
                shift_count = step.shift_count or 2
                hours_per_day = 8.0 * shift_count
                unit = (step.productivity_unit or '').lower()

                # Scale throughput by actual worker count
                dynamic_brigade = _get_effective_brigade_size(
                    db, factory_id, stage, 1,
                )
                effective_rate = rate * dynamic_brigade

                if 'sqm' in unit and total_sqm > 0:
                    hours_needed = total_sqm / effective_rate
                elif 'pcs' in unit and total_pcs > 0:
                    hours_needed = total_pcs / effective_rate
                else:
                    hours_needed = 8.0

                speed_days = max(1, math.ceil(hours_needed / hours_per_day))
    except Exception as e:
        logger.debug("_get_stage_duration_days fallback for %s: %s", stage, e)

    # ── Apply line resource constraint ──
    if stage in _STAGE_RESOURCE_MAP:
        try:
            resource_cap = _get_line_resource_capacity(
                db, factory_id, _STAGE_RESOURCE_MAP[stage],
            )
            tpb = _get_tiles_per_board(db, position)
            return _apply_resource_constraint(
                speed_days, stage, resource_cap,
                total_sqm, total_pcs, fixed_hours, tpb,
                db=db, position=position,
            )
        except Exception as e:
            logger.debug("Resource constraint failed for %s: %s", stage, e)

    return speed_days


def _calc_hours_from_speed(
    rate: float,
    rate_unit: str,
    rate_basis: str,
    time_unit: str,
    shift_count: int,
    shift_duration_hours: float,
    brigade_size: int,
    total_sqm: float,
    total_pcs: int,
) -> "Optional[int]":
    """Convert a StageTypologySpeed record into working days.

    Returns None if the speed cannot be applied (e.g. rate_unit is sqm but
    total_sqm is 0).
    """
    import math

    if rate <= 0:
        return None

    # Fixed-duration stages (drying, cooling, firing): rate IS the hours needed
    if rate_basis == 'fixed_duration':
        hours_needed = rate  # productivity_rate stores total hours
        hours_per_day = shift_duration_hours * shift_count
        return max(1, math.ceil(hours_needed / hours_per_day))

    # Convert rate to "units per hour"
    if time_unit == 'min':
        rate_per_hour = rate * 60.0
    elif time_unit == 'shift':
        rate_per_hour = rate / shift_duration_hours
    else:  # 'hour' (default)
        rate_per_hour = rate

    # Effective hourly throughput: for per_person, multiply by brigade_size
    if rate_basis == 'per_person':
        effective_rate = rate_per_hour * brigade_size
    else:  # 'per_brigade'
        effective_rate = rate_per_hour

    if effective_rate <= 0:
        return None

    # Calculate hours needed based on unit
    if rate_unit == 'sqm' and total_sqm > 0:
        hours_needed = total_sqm / effective_rate
    elif rate_unit == 'pcs' and total_pcs > 0:
        hours_needed = total_pcs / effective_rate
    else:
        return None  # cannot calculate — let caller fall through to next priority

    hours_per_day = shift_duration_hours * shift_count
    return max(1, math.ceil(hours_needed / hours_per_day))


def _get_factory_daily_kiln_cap(db: Session, factory_id: UUID) -> float:
    """Sum of active kiln capacities for a factory (sqm/day).

    Uses ResourceType.KILN and ResourceStatus.ACTIVE from enums.
    Falls back to checking capacity_sqm > 0 on any active resource
    if resource_type is NULL (legacy data).
    """
    from api.enums import ResourceStatus

    # Primary: typed kilns
    kilns = db.query(Resource).filter(
        Resource.factory_id == factory_id,
        Resource.resource_type == ResourceType.KILN.value,
        Resource.status == ResourceStatus.ACTIVE.value,
    ).all()

    # Fallback: resources with capacity_sqm (covers NULL resource_type)
    if not kilns:
        kilns = db.query(Resource).filter(
            Resource.factory_id == factory_id,
            Resource.status == ResourceStatus.ACTIVE.value,
            Resource.capacity_sqm.isnot(None),
            Resource.capacity_sqm > 0,
        ).all()

    cap = sum(float(k.capacity_sqm or 0) for k in kilns)
    return cap if cap > 0 else 10.0  # fallback


def _skip_weekends(target: date) -> date:
    """If target falls on Sunday, move to Monday."""
    # In Bali/Java production, Saturday is a workday; Sunday is off.
    if target.weekday() == 6:  # Sunday
        return target + timedelta(days=1)
    return target


# ────────────────────────────────────────────────────────────────
# Maintenance window helpers
# ────────────────────────────────────────────────────────────────

def get_kiln_maintenance_windows(
    db: Session,
    kiln_id: UUID,
    date_start: date,
    date_end: date,
) -> list:
    """
    Return list of blocked date ranges for a kiln due to scheduled maintenance.

    Each entry is a dict with:
      - start: date when the maintenance window starts
      - end: date when it ends (inclusive)
      - requires_empty_kiln: bool
      - maintenance_type: str description

    Only includes planned/in_progress maintenance that overlaps the given range.
    """
    try:
        schedules = db.query(KilnMaintenanceSchedule).filter(
            KilnMaintenanceSchedule.resource_id == kiln_id,
            KilnMaintenanceSchedule.scheduled_date >= date_start,
            KilnMaintenanceSchedule.scheduled_date <= date_end,
            KilnMaintenanceSchedule.status.in_([
                MaintenanceStatus.PLANNED,
                MaintenanceStatus.IN_PROGRESS,
            ]),
        ).all()
    except Exception:
        # Table may not exist yet during initial setup
        return []

    windows = []
    for s in schedules:
        # Calculate end date: maintenance_date + ceil(duration_hours / 8) working days
        duration_days = 1  # minimum 1 day
        if s.estimated_duration_hours:
            duration_days = max(1, int(float(s.estimated_duration_hours) / 8) + (1 if float(s.estimated_duration_hours) % 8 > 0 else 0))

        window_end = s.scheduled_date + timedelta(days=duration_days - 1)

        windows.append({
            "start": s.scheduled_date,
            "end": window_end,
            "requires_empty_kiln": getattr(s, 'requires_empty_kiln', False) or False,
            "requires_cooled_kiln": getattr(s, 'requires_cooled_kiln', False) or False,
            "requires_power_off": getattr(s, 'requires_power_off', False) or False,
            "maintenance_type": s.maintenance_type or "Maintenance",
        })

    return windows


def _kiln_blocked_on_date(maintenance_windows: list, target_date: date) -> bool:
    """
    Check if a kiln is blocked on a specific date by any maintenance
    that requires the kiln to be empty (i.e., cannot fire while maintenance
    is happening).
    """
    for w in maintenance_windows:
        if w["start"] <= target_date <= w["end"] and w["requires_empty_kiln"]:
            return True
    return False


# ────────────────────────────────────────────────────────────────
# Find best kiln for a position
# ────────────────────────────────────────────────────────────────

def _get_kiln_capacity_sqm(kiln: Resource) -> float:
    """Get usable kiln area in m². Same logic as batch_formation helper."""
    if kiln.capacity_sqm:
        return float(kiln.capacity_sqm)
    if kiln.kiln_working_area_cm:
        dims = kiln.kiln_working_area_cm
        w = dims.get("width_cm") or dims.get("width") or 0
        d = dims.get("depth_cm") or dims.get("depth") or 0
        if w and d:
            coeff = float(kiln.kiln_coefficient) if kiln.kiln_coefficient else 1.0
            return w * d / 10000.0 * coeff
    return 1.0


def _get_scheduled_area_sqm(db: Session, kiln_id: UUID, on_date: date) -> float:
    """Sum glazeable area of all positions already scheduled for this kiln on a date."""
    from sqlalchemy import cast, Date
    total = (
        db.query(sa_func.coalesce(
            sa_func.sum(OrderPosition.glazeable_sqm * OrderPosition.quantity), 0
        ))
        .filter(
            OrderPosition.estimated_kiln_id == kiln_id,
            OrderPosition.planned_kiln_date == on_date,
            OrderPosition.status != PositionStatus.CANCELLED.value,
        )
        .scalar()
    )
    return float(total or 0)


def find_best_kiln(
    db: Session,
    position: OrderPosition,
    target_date: date,
) -> Optional[UUID]:
    """
    Find the kiln with the fewest scheduled slots around the target date.

    Selection criteria:
    1. Only active kilns at the same factory
    2. Exclude kilns under emergency maintenance
    3. Exclude kilns with scheduled maintenance that requires empty kiln
       on/around the target date
    4. Prefer kiln with the fewest planned/in-progress batches in the
       7-day window around the target date (least congested)
    5. If no batches exist for any kiln, pick the first available
    """
    result = find_best_kiln_and_date(db, position, target_date)
    return result[0] if result else None


def find_best_kiln_and_date(
    db: Session,
    position: OrderPosition,
    target_date: date,
    max_shift_days: int = 14,
) -> Optional[tuple[UUID, date]]:
    """
    Find the best kiln AND date, respecting capacity constraints.

    Returns (kiln_id, adjusted_date) or None.
    Tries target_date first, then shifts forward day-by-day up to max_shift_days.
    """
    kilns = db.query(Resource).filter(
        Resource.factory_id == position.factory_id,
        Resource.resource_type == ResourceType.KILN.value,
        Resource.is_active.is_(True),
        Resource.status != ResourceStatus.MAINTENANCE_EMERGENCY.value,
    ).all()

    if not kilns:
        return None

    # Area this position needs
    pos_area = 0.0
    if position.glazeable_sqm and position.quantity:
        pos_area = float(position.glazeable_sqm) * float(position.quantity)
    elif position.quantity_sqm:
        pos_area = float(position.quantity_sqm)

    for day_offset in range(max_shift_days + 1):
        candidate_date = _skip_weekends(target_date + timedelta(days=day_offset))

        window_start = candidate_date - timedelta(days=3)
        window_end = candidate_date + timedelta(days=3)

        best_kiln_id = None
        min_load = float("inf")

        for kiln in kilns:
            maintenance_windows = get_kiln_maintenance_windows(
                db, kiln.id, window_start, window_end,
            )
            if _kiln_blocked_on_date(maintenance_windows, candidate_date):
                continue

            # Zone-aware capacity check for mixed loading
            try:
                from business.services.typology_matcher import (
                    classify_loading_zone, get_zone_capacity,
                )
                zone = classify_loading_zone(position)
                zone_cap = get_zone_capacity(db, position, kiln, zone)

                # Sum area of same-zone positions already scheduled on this day
                zone_used = 0.0
                scheduled = (
                    db.query(OrderPosition)
                    .filter(
                        OrderPosition.estimated_kiln_id == kiln.id,
                        OrderPosition.planned_kiln_date == candidate_date,
                        OrderPosition.status != PositionStatus.CANCELLED.value,
                    )
                    .all()
                )
                for sp in scheduled:
                    if classify_loading_zone(sp) == zone:
                        zone_used += float(sp.glazeable_sqm or 0) * float(sp.quantity or 1)

                if pos_area > 0 and zone_used + pos_area > zone_cap * 1.1:
                    continue
            except Exception as exc:
                # Fallback to simple capacity check
                logger.debug("Zone-aware capacity check failed for kiln %s: %s", kiln.id, exc)
                cap = _get_kiln_capacity_sqm(kiln)
                already_used = _get_scheduled_area_sqm(db, kiln.id, candidate_date)
                if pos_area > 0 and already_used + pos_area > cap * 1.1:
                    continue

            batch_count = db.query(sa_func.count(Batch.id)).filter(
                Batch.resource_id == kiln.id,
                Batch.batch_date >= window_start,
                Batch.batch_date <= window_end,
                Batch.status.in_([BatchStatus.PLANNED.value, BatchStatus.IN_PROGRESS.value]),
            ).scalar() or 0

            slot_count = db.query(sa_func.count(ScheduleSlot.id)).filter(
                ScheduleSlot.resource_id == kiln.id,
                sa_func.date(ScheduleSlot.start_at) >= window_start,
                sa_func.date(ScheduleSlot.start_at) <= window_end,
                ScheduleSlot.status == ScheduleSlotStatus.PLANNED.value,
            ).scalar() or 0

            maintenance_penalty = len(maintenance_windows)
            total_load = batch_count + slot_count + maintenance_penalty

            if total_load < min_load:
                min_load = total_load
                best_kiln_id = kiln.id

        if best_kiln_id is not None:
            if day_offset > 0:
                logger.info(
                    "KILN_DATE_SHIFTED | position=%s | target=%s → actual=%s (+%d days) | kiln=%s",
                    position.id, target_date, candidate_date, day_offset, best_kiln_id,
                )
            return (best_kiln_id, candidate_date)

    # Fallback: no kiln found with capacity in the window — return first available on target_date
    logger.warning(
        "NO_KILN_CAPACITY | position=%s | tried %d days from %s, falling back to first kiln",
        position.id, max_shift_days, target_date,
    )
    first_kiln = kilns[0] if kilns else None
    return (first_kiln.id, target_date) if first_kiln else None


# ────────────────────────────────────────────────────────────────
# Firing Profile Auto-Detection
# ────────────────────────────────────────────────────────────────

def _check_firing_profile_data(
    db: Session,
    position: OrderPosition,
    factory_id: UUID,
) -> None:
    """Check if firing stage speed data exists for this position's typology.

    If no StageTypologySpeed record is found for stage='firing', creates
    a FIRING_PROFILE_NEEDED task for the PM so the profile can be configured
    before the position reaches the kiln.

    Deduplicates: skips if a PENDING task already exists for the same position.
    """
    try:
        from api.models import StageTypologySpeed, Task
        from api.enums import TaskType, TaskStatus, UserRole
        from business.services.typology_matcher import find_matching_typology
        import json

        typology = find_matching_typology(db, position)

        # If typology exists, check for firing speed record
        has_firing_data = False
        if typology:
            speed = db.query(StageTypologySpeed).filter(
                StageTypologySpeed.typology_id == typology.id,
                StageTypologySpeed.stage == 'firing',
                StageTypologySpeed.productivity_rate.isnot(None),
            ).first()
            has_firing_data = speed is not None

        if has_firing_data:
            return  # All good — firing profile configured

        # No firing data — check if we already have a pending task
        existing = db.query(Task).filter(
            Task.related_position_id == position.id,
            Task.type == TaskType.FIRING_PROFILE_NEEDED,
            Task.status == TaskStatus.PENDING,
        ).first()

        if existing:
            return  # Task already created — don't spam

        # Build description
        pos_label = f"#{position.position_number}" + (
            f".{position.split_index}" if getattr(position, 'split_index', None) else ""
        )
        order_num = ""
        if hasattr(position, 'order') and position.order:
            order_num = f" (Order {position.order.order_number})"
        typology_name = typology.name if typology else "unknown"

        task = Task(
            factory_id=factory_id,
            type=TaskType.FIRING_PROFILE_NEEDED,
            status=TaskStatus.PENDING,
            blocking=False,  # not immediately blocking — escalated by eve-of-kiln check
            assigned_role=UserRole.PRODUCTION_MANAGER,
            related_position_id=position.id,
            related_order_id=position.order_id,
            priority=7,
            description=(
                f"Firing profile needed for position {pos_label}{order_num}. "
                f"No firing speed data found for typology '{typology_name}'. "
                f"Configure StageTypologySpeed for 'firing' stage before kiln date."
            ),
            due_at=(
                position.planned_kiln_date - timedelta(days=1)
                if position.planned_kiln_date else None
            ),
            metadata_json=json.dumps({
                "position_id": str(position.id),
                "order_id": str(position.order_id) if position.order_id else None,
                "typology_id": str(typology.id) if typology else None,
                "typology_name": typology_name,
                "planned_kiln_date": str(position.planned_kiln_date) if position.planned_kiln_date else None,
                "reason": "no_stage_typology_speed_for_firing",
            }),
        )
        db.add(task)

        logger.warning(
            "FIRING_PROFILE_MISSING | position=%s typology=%s | "
            "created FIRING_PROFILE_NEEDED task (fallback 1-day firing used)",
            position.id, typology_name,
        )
    except Exception as e:
        logger.debug("_check_firing_profile_data failed: %s", e)


# ────────────────────────────────────────────────────────────────
# §1  Schedule a single position (backward from deadline)
# ────────────────────────────────────────────────────────────────

def schedule_position(
    db: Session,
    position: OrderPosition,
    deadline: date,
) -> None:
    """
    Calculate planned dates for a position using backward scheduling
    from the order deadline.

    TOC/DBR:
      Drum   = kiln firing date (the constraint)
      Buffer = 1 day before kiln (pre-kiln buffer) and after kiln (post-kiln buffer)
      Rope   = work is pulled so glazing finishes just in time for kiln

    Timeline (backward from deadline):
      deadline
        - QC_DAYS                         → planned_completion_date
        - SORTING_DAYS                    → planned_sorting_date
        - BUFFER_DAYS (post-kiln)         → post-kiln buffer
        - COOLING_DAYS                    → cooling
        - FIRING_DURATION_DAYS            → planned_kiln_date (drum)
        - BUFFER_DAYS (pre-kiln)          → pre-kiln buffer
        - PRE_KILN_CHECK_DAYS             → pre-kiln QC
        - GLAZING_DURATION_DAYS           → planned_glazing_date (rope start)
    """
    # Guard: skip material-blocked positions — they cannot be scheduled
    if position.status == PositionStatus.INSUFFICIENT_MATERIALS.value:
        logger.warning(
            "SKIP_SCHEDULE | pos=%s | status=INSUFFICIENT_MATERIALS — skipping",
            position.id,
        )
        return

    # Calculate position area and quantity for duration estimation
    _pos_sqm = float(position.glazeable_sqm or 0) * float(position.quantity or 1)
    _pos_pcs = int(position.quantity or 0)
    _fid = position.factory_id

    def _dur(stage: str) -> int:
        return _get_stage_duration_days(db, _fid, stage, _pos_sqm, _pos_pcs, position=position)

    # ── Full process durations (typology-aware) ──
    # Pre-kiln stages
    unpacking_days = _dur('unpacking_sorting')
    engobe_days = _dur('engobe')
    drying_engobe_days = _dur('drying_engobe')
    glazing_days = _dur('glazing')
    drying_glaze_days = _dur('drying_glaze')
    edge_clean_load_days = _dur('edge_cleaning_loading')
    # Kiln stages (per single firing cycle)
    firing_days_single = _dur('firing')
    kiln_cool_initial_single = _dur('kiln_cooling_initial')
    kiln_unloading_single = _dur('kiln_unloading')
    tile_cooling_days = _dur('tile_cooling')
    # Post-kiln stages
    sorting_days = _dur('sorting')
    packing_days = _dur('packing')

    # ── Multiple kiln loads ──────────────────────────────────
    # Calculate how many firings are needed based on actual kiln capacity
    # for this specific product (edge vs flat loading, typology-aware).
    # KilnTypologyCapacity stores total_pieces per firing — use that.
    # If no typology data, fallback to area-based estimate.
    import math
    _num_loads = 1
    _cap_source = "fallback"
    try:
        from business.services.typology_matcher import (
            find_matching_typology, get_effective_capacity,
            classify_loading_zone, get_zone_capacity,
        )
        _typology = find_matching_typology(db, position)
        if _typology:
            # Try to get pieces-per-firing from KilnTypologyCapacity
            from api.models import KilnTypologyCapacity
            _zone = classify_loading_zone(position)
            _best_pcs = 0
            _best_cap_sqm = 0.0
            _kilns = db.query(Resource).filter(
                Resource.factory_id == _fid,
                Resource.status == 'active',
                Resource.capacity_sqm > 0,
            ).all()
            for _k in _kilns:
                _cap_rec = db.query(KilnTypologyCapacity).filter(
                    KilnTypologyCapacity.typology_id == _typology.id,
                    KilnTypologyCapacity.resource_id == _k.id,
                ).first()
                if _cap_rec and _cap_rec.capacity_pcs and _cap_rec.capacity_pcs > 0:
                    _best_pcs += int(_cap_rec.capacity_pcs)
                    _best_cap_sqm += float(_cap_rec.capacity_sqm or 0)
            if _best_pcs > 0 and _pos_pcs > _best_pcs:
                _num_loads = math.ceil(_pos_pcs / _best_pcs)
                _cap_source = f"typology_pcs({_best_pcs}/firing)"
            elif _best_cap_sqm > 0 and _pos_sqm > _best_cap_sqm:
                _num_loads = math.ceil(_pos_sqm / _best_cap_sqm)
                _cap_source = f"typology_sqm({_best_cap_sqm:.2f}/firing)"
    except Exception as e:
        logger.debug("Multi-load typology lookup failed: %s", e)

    # Fallback: area-based estimate using raw shelf capacity
    if _num_loads <= 1 and _pos_sqm > 0:
        _shelf_cap = _get_factory_daily_kiln_cap(db, _fid)
        if _shelf_cap > 0 and _pos_sqm > _shelf_cap:
            _num_loads = math.ceil(_pos_sqm / _shelf_cap)
            _cap_source = f"shelf_area({_shelf_cap:.2f})"

    firing_days = firing_days_single * _num_loads
    kiln_cool_initial_days = kiln_cool_initial_single * _num_loads
    kiln_unloading_days = kiln_unloading_single * _num_loads

    if _num_loads > 1:
        logger.info(
            "MULTI_LOAD | pos=%s | %d pcs, %.2f m² | %d loads (%s) | "
            "firing=%dd cool=%dd unload=%dd",
            position.id, _pos_pcs, _pos_sqm, _num_loads, _cap_source,
            firing_days, kiln_cool_initial_days, kiln_unloading_days,
        )

    # Pre-kiln total (everything before kiln loading)
    pre_kiln_total = (unpacking_days + engobe_days + drying_engobe_days
                      + glazing_days + drying_glaze_days + edge_clean_load_days)
    # Post-kiln total (firing + cooling + unloading + tile cooling + sorting + packing)
    post_kiln_total = (firing_days + kiln_cool_initial_days + kiln_unloading_days
                       + tile_cooling_days + sorting_days + packing_days)

    # Backward schedule calculation
    planned_completion = _skip_weekends(deadline)

    planned_sorting = _skip_weekends(
        planned_completion - timedelta(days=sorting_days + packing_days)
    )

    planned_kiln = _skip_weekends(
        planned_sorting - timedelta(
            days=firing_days + kiln_cool_initial_days + kiln_unloading_days
            + tile_cooling_days + BUFFER_DAYS
        )
    )

    planned_glazing = _skip_weekends(
        planned_kiln - timedelta(
            days=pre_kiln_total + BUFFER_DAYS
        )
    )

    # Guard: planned_glazing must be >= today.
    # When overdue, find the earliest day with available capacity instead of
    # blindly stuffing everything onto today.
    today = date.today()
    if planned_glazing < today:
        # Get daily capacity (kiln throughput = the constraint)
        _kiln_cap = _get_factory_daily_kiln_cap(db, _fid)

        # Find first day from today with room
        planned_glazing = today
        for _shift in range(30):
            candidate = _skip_weekends(today + timedelta(days=_shift))
            existing_load = float(
                db.query(sa_func.coalesce(
                    sa_func.sum(OrderPosition.glazeable_sqm * OrderPosition.quantity), 0
                )).filter(
                    OrderPosition.factory_id == _fid,
                    OrderPosition.planned_glazing_date == candidate,
                    OrderPosition.status != PositionStatus.CANCELLED.value,
                    OrderPosition.id != position.id,
                ).scalar() or 0
            )
            if existing_load + _pos_sqm <= _kiln_cap * 1.1:
                planned_glazing = candidate
                break
            # Also accept an empty day even if single position exceeds cap
            if existing_load == 0 and _shift > 0:
                planned_glazing = candidate
                break
        else:
            planned_glazing = _skip_weekends(today + timedelta(days=30))

        planned_kiln = _skip_weekends(
            planned_glazing + timedelta(days=pre_kiln_total + BUFFER_DAYS)
        )
        planned_sorting = _skip_weekends(
            planned_kiln + timedelta(
                days=firing_days + kiln_cool_initial_days + kiln_unloading_days
                + tile_cooling_days + BUFFER_DAYS
            )
        )
        planned_completion = _skip_weekends(
            planned_sorting + timedelta(days=sorting_days + packing_days)
        )
        logger.info(
            "OVERDUE_SPREAD | position=%s deadline=%s | "
            "glazing=%s (load=%.1f/%.1f sqm) completion=%s",
            position.id, deadline, planned_glazing,
            existing_load + _pos_sqm, _kiln_cap, planned_completion,
        )

    # Find best kiln with capacity-aware date adjustment
    kiln_result = find_best_kiln_and_date(db, position, planned_kiln)
    if kiln_result:
        kiln_id, actual_kiln_date = kiln_result
        position.estimated_kiln_id = kiln_id
        # If kiln date was shifted forward due to capacity, recalculate downstream dates
        if actual_kiln_date != planned_kiln:
            planned_kiln = actual_kiln_date
            planned_sorting = _skip_weekends(
                planned_kiln + timedelta(
                    days=firing_days + kiln_cool_initial_days + kiln_unloading_days
                    + tile_cooling_days + BUFFER_DAYS
                )
            )
            planned_completion = _skip_weekends(
                planned_sorting + timedelta(days=sorting_days + packing_days)
            )
    else:
        position.estimated_kiln_id = None

    # ── TOC Glazing Rate Limit ────────────────────────────────
    # Don't glaze more per day than kilns can fire.
    # Kiln = drum (constraint), glazing must match its rhythm.
    # Shift FORWARD from planned_glazing until a day with capacity is found.
    if position.estimated_kiln_id and _pos_sqm > 0:
        try:
            from business.services.typology_matcher import get_zone_capacity, classify_loading_zone
            kiln_obj = db.query(Resource).filter(Resource.id == position.estimated_kiln_id).first()
            if kiln_obj:
                zone = classify_loading_zone(position)
                daily_kiln_cap = get_zone_capacity(db, position, kiln_obj, zone)
                if daily_kiln_cap > 0:
                    for shift_fwd in range(21):  # try up to 21 days forward
                        candidate_glaze = _skip_weekends(planned_glazing + timedelta(days=shift_fwd))
                        glaze_day_load = float(
                            db.query(sa_func.coalesce(
                                sa_func.sum(OrderPosition.glazeable_sqm * OrderPosition.quantity), 0
                            ))
                            .filter(
                                OrderPosition.factory_id == position.factory_id,
                                OrderPosition.planned_glazing_date == candidate_glaze,
                                OrderPosition.status != PositionStatus.CANCELLED.value,
                                OrderPosition.id != position.id,
                            )
                            .scalar() or 0
                        )
                        if glaze_day_load + _pos_sqm <= daily_kiln_cap * 1.1:
                            if shift_fwd > 0:
                                logger.info(
                                    "GLAZING_RATE_SHIFT | position=%s | %s → %s (+%dd) | "
                                    "day_load=%.2f + pos=%.2f vs cap=%.2f",
                                    position.id, planned_glazing, candidate_glaze,
                                    shift_fwd, glaze_day_load, _pos_sqm, daily_kiln_cap,
                                )
                            planned_glazing = candidate_glaze
                            # Recalculate downstream dates from new glazing date
                            planned_kiln = _skip_weekends(
                                planned_glazing + timedelta(
                                    days=pre_kiln_total + BUFFER_DAYS
                                )
                            )
                            planned_sorting = _skip_weekends(
                                planned_kiln + timedelta(
                                    days=firing_days + kiln_cool_initial_days
                                    + kiln_unloading_days + tile_cooling_days + BUFFER_DAYS
                                )
                            )
                            planned_completion = _skip_weekends(
                                planned_sorting + timedelta(days=sorting_days + packing_days)
                            )
                            break
        except Exception as e:
            logger.debug("Glazing rate limit check skipped: %s", e)

    # Assign dates
    position.planned_glazing_date = planned_glazing
    position.planned_kiln_date = planned_kiln
    position.planned_sorting_date = planned_sorting
    position.planned_completion_date = planned_completion

    # Increment schedule version
    position.schedule_version = (position.schedule_version or 0) + 1

    # Check if firing profile data exists — create task if missing
    _check_firing_profile_data(db, position, _fid)

    logger.info(
        "SCHEDULED | position=%s v%d | glazing=%s kiln=%s sorting=%s "
        "completion=%s kiln_id=%s",
        position.id, position.schedule_version,
        planned_glazing, planned_kiln, planned_sorting, planned_completion,
        position.estimated_kiln_id,
    )


# ────────────────────────────────────────────────────────────────
# §2  Schedule all positions in an order
# ────────────────────────────────────────────────────────────────

def schedule_order(db: Session, order: ProductionOrder) -> int:
    """
    Schedule all positions in an order using backward scheduling.

    Uses the order's final_deadline. If not set, falls back to
    desired_delivery_date, then today + 30 days.

    Returns the number of positions scheduled.
    """
    deadline = (
        order.final_deadline
        or order.desired_delivery_date
        or (date.today() + timedelta(days=30))
    )

    positions = db.query(OrderPosition).filter(
        OrderPosition.order_id == order.id,
        OrderPosition.status != PositionStatus.CANCELLED.value,
        OrderPosition.status != PositionStatus.INSUFFICIENT_MATERIALS.value,
    ).all()

    count = 0
    for position in positions:
        try:
            schedule_position(db, position, deadline)
            # Flush so next position's capacity query sees this one's dates
            # (autoflush=False means ORM won't do it automatically)
            db.flush()
            count += 1
        except Exception as e:
            logger.error(
                "Failed to schedule position %s: %s", position.id, e,
                exc_info=True,
            )

    logger.info(
        "ORDER_SCHEDULED | order=%s | %d/%d positions scheduled, deadline=%s",
        order.order_number, count, len(positions), deadline,
    )

    # Also update the schedule_deadline on the order itself
    # (uses existing service for the aggregate estimate)
    try:
        from business.services.schedule_estimation import calculate_schedule_deadline
        calculate_schedule_deadline(db, order)
    except Exception as e:
        logger.warning("Failed to update schedule_deadline: %s", e)

    return count


# ────────────────────────────────────────────────────────────────
# §3  Reschedule on changes
# ────────────────────────────────────────────────────────────────

def reschedule_position(db: Session, position: OrderPosition) -> None:
    """
    Recalculate schedule for a single position.

    Called when:
    - Position is delayed (status change)
    - Material becomes available / gets blocked
    - Manual reorder
    """
    order = db.query(ProductionOrder).get(position.order_id)
    if not order:
        return

    deadline = (
        order.final_deadline
        or order.desired_delivery_date
        or (date.today() + timedelta(days=30))
    )

    schedule_position(db, position, deadline)

    logger.info(
        "RESCHEDULED | position=%s v%d",
        position.id, position.schedule_version,
    )


def reschedule_affected_by_kiln(db: Session, kiln_id: UUID) -> int:
    """
    When a kiln breaks down (MAINTENANCE_EMERGENCY) or changes status,
    recalculate all positions estimated to use that kiln.

    Finds all non-terminal positions with estimated_kiln_id == kiln_id
    and reassigns them to the next best kiln.

    Returns the number of positions rescheduled.
    """
    terminal_statuses = {
        PositionStatus.SHIPPED.value,
        PositionStatus.CANCELLED.value,
        PositionStatus.READY_FOR_SHIPMENT.value,
    }

    affected_positions = db.query(OrderPosition).filter(
        OrderPosition.estimated_kiln_id == kiln_id,
        OrderPosition.status.notin_(list(terminal_statuses)),
    ).all()

    count = 0
    for position in affected_positions:
        try:
            reschedule_position(db, position)
            count += 1
        except Exception as e:
            logger.error(
                "Failed to reschedule position %s after kiln change: %s",
                position.id, e,
            )

    if count > 0:
        # Notify PM about the mass reschedule
        try:
            from business.services.notifications import notify_pm
            factory_id = affected_positions[0].factory_id if affected_positions else None
            if factory_id:
                notify_pm(
                    db=db,
                    factory_id=factory_id,
                    type="schedule_change",
                    title=f"Kiln schedule updated: {count} positions rescheduled",
                    message=(
                        f"Kiln {kiln_id} status changed. "
                        f"{count} positions have been reassigned to other kilns."
                    ),
                    related_entity_type="resource",
                    related_entity_id=kiln_id,
                )
        except Exception as e:
            logger.warning("Failed to notify PM about kiln reschedule: %s", e)

    logger.info(
        "KILN_RESCHEDULE | kiln=%s | %d positions rescheduled", kiln_id, count,
    )
    return count


def reschedule_order(db: Session, order_id: UUID) -> int:
    """
    Reschedule all positions in an order.

    Called when:
    - Order deadline changes
    - PM triggers manual reschedule
    """
    order = db.query(ProductionOrder).get(order_id)
    if not order:
        return 0

    return schedule_order(db, order)


def reschedule_factory(db: Session, factory_id: UUID) -> int:
    """
    Reschedule all active positions in a factory.

    Called when a major change affects the whole factory
    (e.g., new kiln added, factory-wide schedule reset).
    """
    from api.enums import OrderStatus

    active_orders = db.query(ProductionOrder).filter(
        ProductionOrder.factory_id == factory_id,
        ProductionOrder.status.in_([
            OrderStatus.NEW.value,
            OrderStatus.IN_PRODUCTION.value,
            OrderStatus.PARTIALLY_READY.value,
        ]),
    ).all()

    total = 0
    for order in active_orders:
        try:
            count = schedule_order(db, order)
            total += count
            # Flush after each order so the next order's capacity queries
            # see the updated planned dates (autoflush is OFF).
            db.flush()
        except Exception as e:
            logger.error(
                "Failed to reschedule order %s: %s", order.order_number, e,
                exc_info=True,
            )

    db.commit()
    logger.info(
        "FACTORY_RESCHEDULE | factory=%s | %d positions across %d orders",
        factory_id, total, len(active_orders),
    )
    return total


# ────────────────────────────────────────────────────────────────
# §4  Schedule summary helpers (for API responses)
# ────────────────────────────────────────────────────────────────

def get_position_schedule(position: OrderPosition) -> dict:
    """Serialize schedule fields for a single position."""
    return {
        "planned_glazing_date": str(position.planned_glazing_date) if position.planned_glazing_date else None,
        "planned_kiln_date": str(position.planned_kiln_date) if position.planned_kiln_date else None,
        "planned_sorting_date": str(position.planned_sorting_date) if position.planned_sorting_date else None,
        "planned_completion_date": str(position.planned_completion_date) if position.planned_completion_date else None,
        "estimated_kiln_id": str(position.estimated_kiln_id) if position.estimated_kiln_id else None,
        "estimated_kiln_name": (
            position.estimated_kiln.name
            if position.estimated_kiln_id and hasattr(position, 'estimated_kiln') and position.estimated_kiln
            else None
        ),
        "schedule_version": position.schedule_version or 1,
        "is_on_track": _is_on_track(position),
    }


def _is_on_track(position: OrderPosition) -> bool:
    """
    Check if a position is on track based on its current status
    and planned dates.

    Returns True if:
    - Position has no schedule (not yet scheduled)
    - Position is ahead of or on its planned date for current stage
    - Position is in a terminal state
    """
    today = date.today()
    status_val = position.status.value if hasattr(position.status, 'value') else str(position.status)

    # Terminal states — always "on track"
    if status_val in ('shipped', 'cancelled', 'ready_for_shipment'):
        return True

    # No schedule — unknown
    if not position.planned_glazing_date:
        return True

    # Pre-glazing statuses: check against glazing date
    pre_glazing = {
        'planned', 'insufficient_materials', 'awaiting_recipe',
        'awaiting_stencil_silkscreen', 'awaiting_color_matching',
    }
    if status_val in pre_glazing:
        return today <= position.planned_glazing_date

    # Glazing statuses: check against kiln date
    glazing = {'engobe_applied', 'engobe_check', 'glazed', 'pre_kiln_check', 'sent_to_glazing'}
    if status_val in glazing:
        return today <= (position.planned_kiln_date or position.planned_glazing_date)

    # Firing statuses: check against sorting date
    firing = {'loaded_in_kiln', 'fired', 'refire', 'awaiting_reglaze'}
    if status_val in firing:
        return today <= (position.planned_sorting_date or position.planned_kiln_date or date.max)

    # Sorting / QC statuses: check against completion date
    return today <= (position.planned_completion_date or date.max)


def get_order_schedule_summary(db: Session, order: ProductionOrder) -> dict:
    """
    Build a complete schedule summary for an order — used by the Sales
    visibility endpoint.
    """
    positions = db.query(OrderPosition).filter(
        OrderPosition.order_id == order.id,
        OrderPosition.status != PositionStatus.CANCELLED.value,
    ).order_by(
        OrderPosition.position_number,
        OrderPosition.split_index,
    ).all()

    position_schedules = []
    all_on_track = True

    for p in positions:
        sched = get_position_schedule(p)
        status_val = p.status.value if hasattr(p.status, 'value') else str(p.status)

        pos_data = {
            "id": str(p.id),
            "position_number": p.position_number,
            "split_index": p.split_index,
            "position_label": f"#{p.position_number}" + (f".{p.split_index}" if p.split_index else ""),
            "status": status_val,
            "color": p.color,
            "size": p.size,
            "collection": p.collection,
            "quantity": p.quantity,
            "product_type": p.product_type.value if hasattr(p.product_type, 'value') else str(p.product_type) if p.product_type else None,
            **sched,
        }
        position_schedules.append(pos_data)

        if not sched["is_on_track"]:
            all_on_track = False

    # Earliest glazing and latest completion across all positions
    glazing_dates = [p.planned_glazing_date for p in positions if p.planned_glazing_date]
    completion_dates = [p.planned_completion_date for p in positions if p.planned_completion_date]

    return {
        "order_id": str(order.id),
        "order_number": order.order_number,
        "client": order.client,
        "final_deadline": str(order.final_deadline) if order.final_deadline else None,
        "schedule_deadline": str(order.schedule_deadline) if order.schedule_deadline else None,
        "earliest_glazing_start": str(min(glazing_dates)) if glazing_dates else None,
        "latest_completion": str(max(completion_dates)) if completion_dates else None,
        "all_on_track": all_on_track,
        "positions_count": len(positions),
        "positions_scheduled": sum(1 for p in positions if p.planned_glazing_date),
        "positions": position_schedules,
    }
