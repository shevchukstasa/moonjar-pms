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
BUFFER_DAYS = 1                 # TOC buffer — default fallback (use _get_scheduler_config for per-factory)


# ────────────────────────────────────────────────────────────────
# Per-Factory Scheduler Config
# ────────────────────────────────────────────────────────────────

_scheduler_config_cache: dict[str, tuple] = {}  # factory_id_str → (pre, post, timestamp)
_CACHE_TTL_SECONDS = 300  # 5 minutes

def _get_scheduler_config(db: Session, factory_id: UUID) -> tuple[int, int]:
    """Get (pre_kiln_buffer_days, post_kiln_buffer_days) for a factory.

    Queries SchedulerConfig table, falls back to BUFFER_DAYS constant.
    Results are cached for 5 minutes to avoid repeated queries.

    If auto_buffer is enabled, calculates buffer from historical delay data.
    """
    import time
    fid_str = str(factory_id)

    # Check cache
    if fid_str in _scheduler_config_cache:
        pre, post, ts = _scheduler_config_cache[fid_str]
        if time.time() - ts < _CACHE_TTL_SECONDS:
            return (pre, post)

    try:
        from api.models import SchedulerConfig
        config = db.query(SchedulerConfig).filter(
            SchedulerConfig.factory_id == factory_id
        ).first()

        if not config:
            _scheduler_config_cache[fid_str] = (BUFFER_DAYS, BUFFER_DAYS, time.time())
            return (BUFFER_DAYS, BUFFER_DAYS)

        pre_buffer = config.pre_kiln_buffer_days
        post_buffer = config.post_kiln_buffer_days

        if config.auto_buffer:
            # Calculate buffer from historical delays
            auto_buf = _calculate_auto_buffer(db, factory_id, float(config.auto_buffer_multiplier))
            if auto_buf is not None:
                pre_buffer = max(pre_buffer, auto_buf)
                post_buffer = max(post_buffer, auto_buf)

        _scheduler_config_cache[fid_str] = (pre_buffer, post_buffer, time.time())
        return (pre_buffer, post_buffer)

    except Exception as e:
        logger.debug("_get_scheduler_config fallback: %s", e)
        return (BUFFER_DAYS, BUFFER_DAYS)


def _calculate_auto_buffer(db: Session, factory_id: UUID, multiplier: float) -> int | None:
    """Calculate auto-buffer from average historical delays over last 90 days.

    Looks at positions where actual completion exceeded planned completion.
    Returns ceil(avg_delay_days * multiplier), or None if insufficient data.
    """
    from sqlalchemy import text
    try:
        result = db.execute(text("""
            SELECT AVG(
                EXTRACT(EPOCH FROM (
                    COALESCE(updated_at, now()) - planned_completion_date::timestamp
                )) / 86400.0
            ) as avg_delay
            FROM order_positions
            WHERE factory_id = :fid
              AND planned_completion_date IS NOT NULL
              AND status NOT IN ('cancelled', 'planned')
              AND planned_completion_date < COALESCE(updated_at, now())::date
              AND planned_completion_date > (now() - interval '90 days')::date
        """), {"fid": str(factory_id)}).fetchone()

        if result and result[0] is not None:
            avg_delay = float(result[0])
            if avg_delay > 0:
                import math
                return max(1, math.ceil(avg_delay * multiplier))
    except Exception as e:
        logger.debug("_calculate_auto_buffer failed: %s", e)
    return None


def invalidate_scheduler_config_cache(factory_id: UUID | None = None):
    """Invalidate the scheduler config cache (called after config update)."""
    if factory_id:
        _scheduler_config_cache.pop(str(factory_id), None)
    else:
        _scheduler_config_cache.clear()


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
# §0.9  Material-ready date helper for INSUFFICIENT_MATERIALS positions
# ────────────────────────────────────────────────────────────────

DEFAULT_MATERIAL_FALLBACK_DAYS = 14  # ultimate fallback if no supplier lead time


def _get_material_ready_date(
    db: Session,
    position: OrderPosition,
) -> date:
    """Estimate the earliest date when ALL materials for a position will be available.

    Strategy:
    1. Look up the position's recipe -> recipe materials
    2. For each material with a deficit, call check_material_availability_smart
       to find expected_delivery_date from pending purchase requests
    3. Return the LATEST expected_delivery_date across all deficit materials
       (all materials must be ready before glazing can start)
    4. If no expected_delivery_date found, fallback to supplier lead time,
       then DEFAULT_MATERIAL_FALLBACK_DAYS

    Returns a date (never None).
    """
    from api.models import RecipeMaterial, MaterialStock, Material, Supplier
    from decimal import Decimal
    from business.services.material_reservation import check_material_availability_smart

    today = date.today()
    latest_ready_date = today  # at minimum, today

    recipe_id = getattr(position, 'recipe_id', None)
    if not recipe_id:
        logger.info(
            "MATERIAL_READY_DATE | pos=%s | no recipe — fallback +%d days",
            position.id, DEFAULT_MATERIAL_FALLBACK_DAYS,
        )
        return today + timedelta(days=DEFAULT_MATERIAL_FALLBACK_DAYS)

    factory_id = position.factory_id

    recipe_materials = (
        db.query(RecipeMaterial)
        .filter(RecipeMaterial.recipe_id == recipe_id)
        .all()
    )

    if not recipe_materials:
        logger.info(
            "MATERIAL_READY_DATE | pos=%s | no recipe materials — fallback +%d days",
            position.id, DEFAULT_MATERIAL_FALLBACK_DAYS,
        )
        return today + timedelta(days=DEFAULT_MATERIAL_FALLBACK_DAYS)

    for rm in recipe_materials:
        material = db.query(Material).get(rm.material_id)
        if not material:
            continue

        # Calculate required quantity (simplified — mirrors reserve_materials_for_position)
        required_qty = Decimal(str(rm.quantity_per_unit or 0)) * Decimal(str(position.quantity or 1))

        # Get effective available (stock balance - net reserved)
        stock = (
            db.query(MaterialStock)
            .filter(
                MaterialStock.material_id == rm.material_id,
                MaterialStock.factory_id == factory_id,
            )
            .first()
        )
        effective_available = Decimal(str(stock.balance if stock else 0))

        if effective_available >= required_qty:
            continue  # this material is fine

        # Material has deficit — check purchase requests
        result = check_material_availability_smart(
            db=db,
            material_id=rm.material_id,
            factory_id=factory_id,
            required_qty=required_qty,
            effective_available=effective_available,
            planned_glazing_date=None,  # don't evaluate timing, just get delivery date
        )

        if result.expected_delivery_date:
            if result.expected_delivery_date > latest_ready_date:
                latest_ready_date = result.expected_delivery_date
        else:
            # No expected delivery date — use supplier lead time or fallback
            fallback_days = DEFAULT_MATERIAL_FALLBACK_DAYS
            try:
                # Try to get supplier lead time from the material's supplier
                if hasattr(material, 'supplier_id') and material.supplier_id:
                    supplier = db.query(Supplier).get(material.supplier_id)
                    if supplier and supplier.default_lead_time_days:
                        fallback_days = supplier.default_lead_time_days
            except Exception:
                pass  # use default fallback

            candidate = today + timedelta(days=fallback_days)
            if candidate > latest_ready_date:
                latest_ready_date = candidate

    return latest_ready_date


# ────────────────────────────────────────────────────────────────
# Deadline Exceeded Alert
# ────────────────────────────────────────────────────────────────

def _create_deadline_exceeded_alert(
    db: Session,
    position: OrderPosition,
    deadline: date,
    planned_completion: date,
    stage_durations: dict,
) -> None:
    """Create a PM task and CEO notification when planned completion exceeds deadline."""
    try:
        from api.models import Task
        from api.enums import TaskType, TaskStatus, UserRole
        from business.services.notifications import notify_pm, notify_role
        import json
        import math

        overdue_days = (planned_completion - deadline).days
        bottleneck_stage = max(stage_durations, key=stage_durations.get)
        bottleneck_duration = stage_durations[bottleneck_stage]
        extra_workers = max(1, math.ceil(overdue_days / max(bottleneck_duration, 1)))

        pos_label = f"#{position.position_number}" + (
            f".{position.split_index}" if getattr(position, 'split_index', None) else ""
        )
        order_num = ""
        if hasattr(position, 'order') and position.order:
            order_num = position.order.order_number

        # Dedup: skip if a PENDING DEADLINE_EXCEEDED task already exists
        existing = db.query(Task).filter(
            Task.related_position_id == position.id,
            Task.type == TaskType.DEADLINE_EXCEEDED,
            Task.status == TaskStatus.PENDING,
        ).first()
        if existing:
            return

        description = (
            f"Position {pos_label} (Order {order_num}) is {overdue_days} days late. "
            f"Deadline: {deadline}, planned completion: {planned_completion}. "
            f"Bottleneck: {bottleneck_stage} ({bottleneck_duration}d). "
            f"AI suggestion: Need +{extra_workers} workers on {bottleneck_stage} "
            f"to meet deadline. Consider working Sunday/overtime."
        )

        task = Task(
            factory_id=position.factory_id,
            type=TaskType.DEADLINE_EXCEEDED,
            status=TaskStatus.PENDING,
            assigned_role=UserRole.PRODUCTION_MANAGER,
            related_order_id=position.order_id,
            related_position_id=position.id,
            blocking=False,
            priority=9,
            description=description,
            metadata_json=json.dumps({
                "position_id": str(position.id),
                "order_id": str(position.order_id) if position.order_id else None,
                "deadline": str(deadline),
                "planned_completion": str(planned_completion),
                "overdue_days": overdue_days,
                "bottleneck_stage": bottleneck_stage,
                "bottleneck_duration_days": bottleneck_duration,
                "extra_workers_suggested": extra_workers,
                "stage_durations": stage_durations,
            }),
        )
        db.add(task)
        db.flush()

        # Notify PM
        notify_pm(
            db=db,
            factory_id=position.factory_id,
            type="alert",
            title=f"Deadline exceeded: position {pos_label} +{overdue_days}d late",
            message=description,
            related_entity_type="position",
            related_entity_id=position.id,
        )

        # Notify CEO (priority 9 = critical)
        notify_role(
            db=db,
            factory_id=position.factory_id,
            role=UserRole.CEO,
            type="alert",
            title=f"DEADLINE EXCEEDED: {pos_label} (Order {order_num}) +{overdue_days}d",
            message=description,
            related_entity_type="position",
            related_entity_id=position.id,
        )

        # Notify Sales Manager who created the order
        _notify_sales_manager_deadline(
            db=db,
            position=position,
            order_num=order_num,
            pos_label=pos_label,
            deadline=deadline,
            planned_completion=planned_completion,
            overdue_days=overdue_days,
        )

        logger.warning(
            "DEADLINE_EXCEEDED | pos=%s | deadline=%s completion=%s | +%d days late",
            position.id, deadline, planned_completion, overdue_days,
        )
    except Exception as e:
        logger.debug("_create_deadline_exceeded_alert failed: %s", e)


def _notify_sales_manager_deadline(
    db: Session,
    position: OrderPosition,
    order_num: str,
    pos_label: str,
    deadline: date,
    planned_completion: date,
    overdue_days: int,
) -> None:
    """Notify the sales manager (by name/contact match) about deadline shift.

    Looks up the order's sales_manager_name / sales_manager_contact to find
    a matching PMS User.  If found, creates an in-app notification (which also
    triggers Telegram push when the user has telegram_user_id configured).
    """
    try:
        from api.models import User
        from business.services.notifications import create_notification, send_telegram_message

        order = position.order if hasattr(position, "order") else None
        if not order:
            order = db.query(ProductionOrder).filter(
                ProductionOrder.id == position.order_id,
            ).first()
        if not order:
            return

        sm_name = order.sales_manager_name
        sm_contact = order.sales_manager_contact
        if not sm_name and not sm_contact:
            logger.debug("No sales_manager info on order %s — skip SM notification", order_num)
            return

        # Try to find the PMS user: first by contact (email), then by name
        sales_user = None
        if sm_contact:
            sales_user = db.query(User).filter(
                User.email == sm_contact,
                User.is_active.is_(True),
            ).first()
        if not sales_user and sm_name:
            sales_user = db.query(User).filter(
                User.name == sm_name,
                User.is_active.is_(True),
            ).first()

        title = f"Order {order_num} deadline shifted: new completion {planned_completion}"
        message = (
            f"Position {pos_label} — original deadline: {deadline}, "
            f"new estimated: {planned_completion} (+{overdue_days} days). "
            f"Please inform the client."
        )

        if sales_user:
            # In-app notification (also pushes Telegram via create_notification)
            create_notification(
                db=db,
                user_id=sales_user.id,
                type="alert",
                title=title,
                message=message,
                related_entity_type="order",
                related_entity_id=order.id,
                factory_id=position.factory_id,
            )
            logger.info(
                "Sales manager notified (user=%s) about deadline shift on order %s",
                sales_user.id, order_num,
            )
        else:
            # User not in PMS — try direct Telegram if contact looks like a chat id,
            # otherwise log for visibility so the PM can relay manually.
            logger.info(
                "Sales manager '%s' (%s) not found in PMS — cannot send in-app notification for order %s",
                sm_name, sm_contact, order_num,
            )
    except Exception as e:
        logger.debug("_notify_sales_manager_deadline failed: %s", e)


# ────────────────────────────────────────────────────────────────
# Auto-Create Missing Typology
# ────────────────────────────────────────────────────────────────

def _auto_create_missing_typology(
    db: Session,
    position: OrderPosition,
) -> None:
    """Auto-create a KilnLoadingTypology when no match found, and create PM task.

    Finds 3 nearest existing typologies by product_type/shape as hints.
    """
    try:
        from api.models import KilnLoadingTypology, Task
        from api.enums import TaskType, TaskStatus, UserRole
        import json

        product_type = position.product_type
        pt_val = product_type.value if hasattr(product_type, 'value') else str(product_type) if product_type else 'tile'
        shape = getattr(position, 'shape', None)
        shape_val = shape.value if hasattr(shape, 'value') else str(shape) if shape else None
        collection = getattr(position, 'collection', None)
        coll_val = collection.value if hasattr(collection, 'value') else str(collection) if collection else None
        method = getattr(position, 'application_method_code', None)
        method_val = method.value if hasattr(method, 'value') else str(method) if method else None
        place = getattr(position, 'place_of_application', None)
        place_val = place.value if hasattr(place, 'value') else str(place) if place else None

        w = float(position.width_cm or 0) if getattr(position, 'width_cm', None) else 0
        l = float(position.length_cm or 0) if getattr(position, 'length_cm', None) else 0
        if not w and not l and getattr(position, 'size', None):
            try:
                parts = str(position.size).lower().replace('\u0445', 'x').split('x')
                w = float(parts[0])
                l = float(parts[1]) if len(parts) > 1 else w
            except (ValueError, IndexError):
                pass

        size_str = f"{w:.0f}x{l:.0f}" if w and l else "unknown-size"
        typology_name = f"Auto: {pt_val} {size_str}"
        if coll_val:
            typology_name += f" ({coll_val})"

        # Dedup: check if auto-created typology with same name already exists
        existing_typo = db.query(KilnLoadingTypology).filter(
            KilnLoadingTypology.factory_id == position.factory_id,
            KilnLoadingTypology.name == typology_name,
        ).first()
        if existing_typo:
            return

        new_typology = KilnLoadingTypology(
            factory_id=position.factory_id,
            name=typology_name,
            product_types=[pt_val] if pt_val else [],
            place_of_application=[place_val] if place_val else [],
            collections=[coll_val] if coll_val else [],
            methods=[method_val] if method_val else [],
            min_size_cm=min(w, l) if w and l else None,
            max_size_cm=max(w, l) if w and l else None,
            preferred_loading='auto',
            is_active=True,
            priority=0,
            notes="Auto-created by scheduler — needs stage speed configuration.",
        )
        db.add(new_typology)
        db.flush()

        # Find 3 nearest existing typologies as hints (scored by attribute match)
        hints = (
            db.query(KilnLoadingTypology)
            .filter(
                KilnLoadingTypology.factory_id == position.factory_id,
                KilnLoadingTypology.is_active == True,  # noqa: E712
                KilnLoadingTypology.id != new_typology.id,
            )
            .all()
        )

        def _score(t):
            s = 0
            if pt_val and pt_val in (t.product_types or []):
                s += 3
            if shape_val and shape_val in (t.product_types or []):
                s += 1
            if coll_val and coll_val in (t.collections or []):
                s += 1
            if method_val and method_val in (t.methods or []):
                s += 1
            return s

        hints.sort(key=_score, reverse=True)
        nearest = hints[:3]
        hint_names = [h.name for h in nearest]

        pos_label = f"#{position.position_number}" + (
            f".{position.split_index}" if getattr(position, 'split_index', None) else ""
        )

        # Dedup task
        existing_task = db.query(Task).filter(
            Task.related_position_id == position.id,
            Task.type == TaskType.TYPOLOGY_SPEEDS_NEEDED,
            Task.status == TaskStatus.PENDING,
        ).first()
        if existing_task:
            return

        task = Task(
            factory_id=position.factory_id,
            type=TaskType.TYPOLOGY_SPEEDS_NEEDED,
            status=TaskStatus.PENDING,
            assigned_role=UserRole.PRODUCTION_MANAGER,
            related_order_id=position.order_id,
            related_position_id=position.id,
            blocking=False,
            priority=6,
            description=(
                f"New typology '{typology_name}' auto-created for position {pos_label}. "
                f"Please configure stage speeds (StageTypologySpeed records). "
                f"Nearest existing typologies for reference: "
                f"{', '.join(hint_names) if hint_names else 'none'}."
            ),
            metadata_json=json.dumps({
                "typology_id": str(new_typology.id),
                "typology_name": typology_name,
                "position_id": str(position.id),
                "order_id": str(position.order_id) if position.order_id else None,
                "nearest_typologies": [
                    {"id": str(h.id), "name": h.name} for h in nearest
                ],
                "product_type": pt_val,
                "size": size_str,
                "collection": coll_val,
                "method": method_val,
            }),
        )
        db.add(task)
        db.flush()

        logger.info(
            "TYPOLOGY_AUTO_CREATED | pos=%s | typology='%s' (id=%s) | "
            "nearest=[%s] | task created",
            position.id, typology_name, new_typology.id,
            ", ".join(hint_names),
        )
    except Exception as e:
        logger.debug("_auto_create_missing_typology failed: %s", e)


# ────────────────────────────────────────────────────────────────
# Smart Deadline Fallback
# ────────────────────────────────────────────────────────────────

def _get_smart_deadline_fallback(db: Session, order: ProductionOrder) -> date:
    """Calculate a smart deadline fallback when no explicit deadline is set.

    Priority:
      1. Factory average lead time from last 30 completed orders
      2. Ultimate fallback: today + 21 days (more realistic than 30)
    """
    today = date.today()

    # Try factory average lead time from recent completed orders
    try:
        from sqlalchemy import text
        result = db.execute(text("""
            SELECT AVG(
                EXTRACT(EPOCH FROM (
                    COALESCE(shipped_at, updated_at) - created_at
                )) / 86400.0
            ) as avg_lead_days
            FROM production_orders
            WHERE factory_id = :fid
              AND status IN ('shipped', 'ready_for_shipment')
              AND created_at > (now() - interval '180 days')
            ORDER BY created_at DESC
            LIMIT 30
        """), {"fid": str(order.factory_id)}).fetchone()

        if result and result[0] is not None:
            avg_days = int(result[0])
            if 7 <= avg_days <= 90:  # sanity check
                logger.info(
                    "SMART_DEADLINE | order=%s | factory avg lead time = %d days",
                    order.order_number, avg_days,
                )
                return today + timedelta(days=avg_days)
    except Exception as e:
        logger.debug("_get_smart_deadline_fallback factory avg failed: %s", e)

    # Ultimate fallback: 21 days
    return today + timedelta(days=21)


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
    # Material-blocked positions: schedule to expected delivery date instead of skipping
    _material_ready_date = None
    if position.status == PositionStatus.INSUFFICIENT_MATERIALS.value:
        _material_ready_date = _get_material_ready_date(db, position)
        logger.info(
            "MATERIAL_WAIT | pos=%s | scheduled to delivery date %s",
            position.id, _material_ready_date,
        )

    # Calculate position area and quantity for duration estimation
    _pos_sqm = float(position.glazeable_sqm or 0) * float(position.quantity or 1)
    _pos_pcs = int(position.quantity or 0)
    _fid = position.factory_id

    # Configurable buffer days (per-factory)
    _pre_buffer, _post_buffer = _get_scheduler_config(db, _fid)

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
        else:
            # No matching typology — auto-create one and notify PM
            _auto_create_missing_typology(db, position)
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

    # Persist num_loads for batch planner
    position.estimated_num_loads = _num_loads

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
            + tile_cooling_days + _post_buffer
        )
    )

    planned_glazing = _skip_weekends(
        planned_kiln - timedelta(
            days=pre_kiln_total + _pre_buffer
        )
    )

    # ── Material-wait constraint ──────────────────────────────────
    # If position is material-blocked, glazing cannot start before materials arrive.
    # Push planned_glazing forward to material_ready_date and recalculate downstream.
    if _material_ready_date and planned_glazing < _material_ready_date:
        planned_glazing = _skip_weekends(_material_ready_date)
        planned_kiln = _skip_weekends(
            planned_glazing + timedelta(days=pre_kiln_total + _pre_buffer)
        )
        planned_sorting = _skip_weekends(
            planned_kiln + timedelta(
                days=firing_days + kiln_cool_initial_days + kiln_unloading_days
                + tile_cooling_days + _post_buffer
            )
        )
        planned_completion = _skip_weekends(
            planned_sorting + timedelta(days=sorting_days + packing_days)
        )
        logger.info(
            "MATERIAL_WAIT_SHIFT | pos=%s | glazing pushed to %s (material ready %s) | "
            "completion=%s (deadline=%s)",
            position.id, planned_glazing, _material_ready_date,
            planned_completion, deadline,
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
            planned_glazing + timedelta(days=pre_kiln_total + _pre_buffer)
        )
        planned_sorting = _skip_weekends(
            planned_kiln + timedelta(
                days=firing_days + kiln_cool_initial_days + kiln_unloading_days
                + tile_cooling_days + _post_buffer
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
                    + tile_cooling_days + _post_buffer
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
                                    days=pre_kiln_total + _pre_buffer
                                )
                            )
                            planned_sorting = _skip_weekends(
                                planned_kiln + timedelta(
                                    days=firing_days + kiln_cool_initial_days
                                    + kiln_unloading_days + tile_cooling_days + _post_buffer
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

    # Store original kiln date for batch deferral tracking.
    # Reset on each full reschedule (schedule_position call).
    _sched_meta = position.schedule_metadata if position.schedule_metadata else {}
    if not isinstance(_sched_meta, dict):
        _sched_meta = {}
    _sched_meta["original_kiln_date"] = planned_kiln.isoformat() if planned_kiln else None
    _sched_meta["num_loads"] = _num_loads
    position.schedule_metadata = _sched_meta

    # Increment schedule version
    position.schedule_version = (position.schedule_version or 0) + 1

    # Check if firing profile data exists — create task if missing
    _check_firing_profile_data(db, position, _fid)

    # ── Feature: Deadline Exceeded Alert ──────────────────────
    # If planned_completion exceeds the deadline, create a PM task + CEO notification
    if planned_completion > deadline:
        _create_deadline_exceeded_alert(
            db, position, deadline, planned_completion,
            stage_durations={
                'unpacking_sorting': unpacking_days,
                'engobe': engobe_days,
                'drying_engobe': drying_engobe_days,
                'glazing': glazing_days,
                'drying_glaze': drying_glaze_days,
                'edge_cleaning_loading': edge_clean_load_days,
                'firing': firing_days,
                'kiln_cooling_initial': kiln_cool_initial_days,
                'kiln_unloading': kiln_unloading_days,
                'tile_cooling': tile_cooling_days,
                'sorting': sorting_days,
                'packing': packing_days,
            },
        )

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

def schedule_order(
    db: Session,
    order: ProductionOrder,
    skip_batch_planning: bool = False,
) -> int:
    """
    Schedule all positions in an order using backward scheduling.

    Uses the order's final_deadline. If not set, falls back to
    desired_delivery_date, then factory average lead time, then today + 21 days.

    Args:
        db: Database session
        order: The production order to schedule
        skip_batch_planning: If True, skip batch planning step (useful when
            called from reschedule_factory which does its own batch planning pass)

    Returns the number of positions scheduled.
    """
    deadline = (
        order.final_deadline
        or order.desired_delivery_date
        or _get_smart_deadline_fallback(db, order)
    )

    positions = db.query(OrderPosition).filter(
        OrderPosition.order_id == order.id,
        OrderPosition.status != PositionStatus.CANCELLED.value,
        # INSUFFICIENT_MATERIALS positions are now scheduled to expected delivery date
        # (no longer excluded — handled in schedule_position)
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

    # Run batch planning for positions scheduled in this order.
    # Collects planned kiln dates and runs plan_kiln_batches for
    # the factory over the relevant date range.
    if not skip_batch_planning:
        try:
            kiln_dates = [
                p.planned_kiln_date for p in positions if p.planned_kiln_date
            ]
            if kiln_dates and order.factory_id:
                _date_from = min(kiln_dates)
                _date_to = max(kiln_dates)
                plan_kiln_batches(db, order.factory_id, _date_from, _date_to)
        except Exception as e:
            logger.warning(
                "Batch planning after schedule_order failed: %s", e,
                exc_info=True,
            )

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
        or _get_smart_deadline_fallback(db, order)
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
            count = schedule_order(db, order, skip_batch_planning=True)
            total += count
            # Flush after each order so the next order's capacity queries
            # see the updated planned dates (autoflush is OFF).
            db.flush()
        except Exception as e:
            logger.error(
                "Failed to reschedule order %s: %s", order.order_number, e,
                exc_info=True,
            )

    # Single batch planning pass after all orders are scheduled.
    # This enables cross-order batching: positions from different orders
    # with compatible temperatures are grouped to fill kilns completely.
    try:
        all_kiln_dates = (
            db.query(OrderPosition.planned_kiln_date)
            .filter(
                OrderPosition.factory_id == factory_id,
                OrderPosition.planned_kiln_date.isnot(None),
                OrderPosition.batch_id.is_(None),
                OrderPosition.status != PositionStatus.CANCELLED.value,
            )
            .distinct()
            .all()
        )
        if all_kiln_dates:
            dates = [row[0] for row in all_kiln_dates]
            plan_kiln_batches(
                db, factory_id,
                date_from=min(dates),
                date_to=max(dates),
            )
    except Exception as e:
        logger.warning(
            "Batch planning after reschedule_factory failed: %s", e,
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


# ────────────────────────────────────────────────────────────────
# §5  Kiln Batch Planning — bridge between scheduler & batch_formation
# ────────────────────────────────────────────────────────────────

# Configurable thresholds
MIN_KILN_FILL_PCT = 60       # minimum fill % to fire (below this: wait)
MAX_BATCH_WAIT_DAYS = 3      # maximum extra days to wait for more work
DEADLINE_PRESSURE_DAYS = 3   # if deadline within N days of kiln date, fire regardless


def plan_kiln_batches(
    db: Session,
    factory_id: UUID,
    date_from: date,
    date_to: date,
    force_partial: bool = False,
) -> list[dict]:
    """
    Group scheduled positions into optimal kiln batches.

    This is the bridge between the backward scheduler (which assigns
    planned_kiln_date per position) and batch_formation (which creates
    Batch records with kiln assignments and loading plans).

    Algorithm:
    1. Get all positions with planned_kiln_date in [date_from, date_to]
       that are NOT yet assigned to a batch.
    2. Group by temperature compatibility (reuses firing_profiles logic).
    3. For each temperature group on each date:
       a. Calculate total area vs best kiln capacity = fill %.
       b. If fill < MIN_KILN_FILL_PCT and no deadline pressure:
          - Shift those positions' planned_kiln_date forward by 1 day
            (max MAX_BATCH_WAIT_DAYS beyond original date).
          - They'll be picked up in the next batch planning cycle.
       c. If fill >= MIN_KILN_FILL_PCT OR deadline pressure OR force_partial:
          - Delegate to suggest_or_create_batches() for actual batch creation.
    4. Return batch plan summary.

    Args:
        db: Database session
        factory_id: Factory to plan batches for
        date_from: Start of planning window (inclusive)
        date_to: End of planning window (inclusive)
        force_partial: If True, fire partial kilns regardless of fill %

    Returns:
        List of batch detail dicts (from batch_formation).
    """
    from business.services.firing_profiles import group_positions_by_temperature
    from business.services.batch_formation import (
        _get_available_kilns,
        _get_position_area_sqm,
    )

    # Step 1: Collect unbatched positions in the date range
    positions = (
        db.query(OrderPosition)
        .filter(
            OrderPosition.factory_id == factory_id,
            OrderPosition.planned_kiln_date >= date_from,
            OrderPosition.planned_kiln_date <= date_to,
            OrderPosition.batch_id.is_(None),
            OrderPosition.status != PositionStatus.CANCELLED.value,
        )
        .order_by(
            OrderPosition.planned_kiln_date.asc(),
            OrderPosition.priority_order.desc().nulls_last(),
        )
        .all()
    )

    if not positions:
        logger.info(
            "BATCH_PLAN | factory=%s | No unbatched positions in %s..%s",
            factory_id, date_from, date_to,
        )
        return []

    logger.info(
        "BATCH_PLAN | factory=%s | %d unbatched positions in %s..%s",
        factory_id, len(positions), date_from, date_to,
    )

    # Step 2: Group by kiln date, then by temperature
    by_date: dict[date, list[OrderPosition]] = {}
    for pos in positions:
        d = pos.planned_kiln_date
        by_date.setdefault(d, []).append(pos)

    all_created_batches: list[dict] = []
    deferred_positions: list[OrderPosition] = []  # positions shifted forward

    for kiln_date in sorted(by_date.keys()):
        day_positions = by_date[kiln_date]

        # Get available kilns for this date
        available_kilns = _get_available_kilns(db, factory_id, kiln_date)
        if not available_kilns:
            logger.warning(
                "BATCH_PLAN | factory=%s | No kilns available on %s, "
                "deferring %d positions",
                factory_id, kiln_date, len(day_positions),
            )
            deferred_positions.extend(day_positions)
            continue

        # Best kiln capacity (largest available)
        max_kiln_cap = max(
            float(_get_kiln_capacity_sqm(k)) for k in available_kilns
        )

        # Group by temperature
        temp_groups = group_positions_by_temperature(db, day_positions)

        for group_id, group_positions in temp_groups.items():
            total_area = sum(
                float(_get_position_area_sqm(p)) for p in group_positions
            )

            fill_pct = (total_area / max_kiln_cap * 100) if max_kiln_cap > 0 else 0

            # Check deadline pressure: any position with order deadline
            # within DEADLINE_PRESSURE_DAYS of planned_kiln_date?
            has_deadline_pressure = _check_deadline_pressure(
                db, group_positions, kiln_date,
            )

            should_fire = (
                force_partial
                or fill_pct >= MIN_KILN_FILL_PCT
                or has_deadline_pressure
            )

            if not should_fire:
                # Check if we've already waited the maximum
                max_waited = _get_max_days_waited(group_positions, kiln_date)

                if max_waited >= MAX_BATCH_WAIT_DAYS:
                    # Waited too long, fire partial
                    logger.warning(
                        "PARTIAL_KILN | factory=%s date=%s temp_group=%s | "
                        "%.0f%% fill after %d days wait — firing partial "
                        "(%d positions, %.3f/%.3f sqm)",
                        factory_id, kiln_date, group_id,
                        fill_pct, max_waited,
                        len(group_positions), total_area, max_kiln_cap,
                    )
                    should_fire = True
                else:
                    # Defer: shift planned_kiln_date forward by 1 day.
                    # original_kiln_date in schedule_metadata (set by
                    # schedule_position) is preserved for wait tracking.
                    next_day = _skip_weekends(kiln_date + timedelta(days=1))
                    for pos in group_positions:
                        pos.planned_kiln_date = next_day
                        # Also shift downstream dates
                        _shift_downstream_dates(pos, days_delta=1)
                    deferred_positions.extend(group_positions)

                    logger.info(
                        "BATCH_DEFER | factory=%s | temp_group=%s | "
                        "%.0f%% fill < %d%% threshold — shifting %d positions "
                        "from %s to %s (waited %d/%d days)",
                        factory_id, group_id,
                        fill_pct, MIN_KILN_FILL_PCT,
                        len(group_positions), kiln_date, next_day,
                        max_waited + 1, MAX_BATCH_WAIT_DAYS,
                    )
                    continue

            if should_fire:
                logger.info(
                    "BATCH_FIRE | factory=%s date=%s temp_group=%s | "
                    "%.0f%% fill | %d positions, %.3f sqm | "
                    "deadline_pressure=%s",
                    factory_id, kiln_date, group_id,
                    fill_pct, len(group_positions), total_area,
                    has_deadline_pressure,
                )

    # Step 3: Flush deferred position date changes
    if deferred_positions:
        db.flush()
        logger.info(
            "BATCH_PLAN | factory=%s | Deferred %d positions to accumulate "
            "more work",
            factory_id, len(deferred_positions),
        )

    # Step 4: Delegate actual batch creation to batch_formation
    # It will pick up all positions that are ready (GLAZED/PRE_KILN_CHECK
    # and still unbatched) for the date range.
    # For scheduled-but-not-yet-ready positions, batches will be created
    # when they reach kiln-ready status and batch formation runs.
    from business.services.batch_formation import suggest_or_create_batches

    # Run batch formation for each date that had positions to fire
    dates_to_batch = sorted(set(
        pos.planned_kiln_date for pos in positions
        if pos not in deferred_positions
        and pos.batch_id is None
    ))

    for batch_date in dates_to_batch:
        try:
            batches = suggest_or_create_batches(
                db=db,
                factory_id=factory_id,
                target_date=batch_date,
                mode="auto",
            )
            all_created_batches.extend(batches)
        except Exception as e:
            logger.error(
                "BATCH_PLAN | factory=%s date=%s | batch creation failed: %s",
                factory_id, batch_date, e, exc_info=True,
            )

    logger.info(
        "BATCH_PLAN_DONE | factory=%s | %d batches created, %d positions deferred",
        factory_id, len(all_created_batches), len(deferred_positions),
    )

    return all_created_batches


def _check_deadline_pressure(
    db: Session,
    positions: list[OrderPosition],
    kiln_date: date,
) -> bool:
    """
    Check if any position in the group has deadline pressure.

    Deadline pressure = order's final_deadline is within
    DEADLINE_PRESSURE_DAYS of the planned kiln date.
    """
    if not positions:
        return False

    pressure_cutoff = kiln_date + timedelta(days=DEADLINE_PRESSURE_DAYS)

    # Single query: get orders whose deadline is within pressure window
    order_ids = list({pos.order_id for pos in positions})
    orders = (
        db.query(ProductionOrder)
        .filter(ProductionOrder.id.in_(order_ids))
        .all()
    )
    for order in orders:
        deadline = order.final_deadline or order.desired_delivery_date
        if deadline and deadline <= pressure_cutoff:
            return True
    return False


def _get_max_days_waited(
    positions: list[OrderPosition],
    current_date: date,
) -> int:
    """
    Calculate the maximum number of days any position in the group
    has been deferred from its original planned_kiln_date.

    Reads 'original_kiln_date' from position's schedule_metadata,
    which is set by schedule_position() during backward scheduling.

    Falls back to 0 if no deferral history detected.
    """
    max_waited = 0
    for pos in positions:
        meta = pos.schedule_metadata or {} if hasattr(pos, 'schedule_metadata') else {}
        original_str = meta.get("original_kiln_date") if isinstance(meta, dict) else None
        if original_str:
            try:
                original_date = date.fromisoformat(original_str)
                if current_date > original_date:
                    waited = (current_date - original_date).days
                    max_waited = max(max_waited, waited)
            except (ValueError, TypeError):
                pass
    return max_waited



def _shift_downstream_dates(pos: OrderPosition, days_delta: int) -> None:
    """
    Shift sorting and completion dates forward by days_delta
    when kiln date is deferred.
    """
    if pos.planned_sorting_date:
        pos.planned_sorting_date = _skip_weekends(
            pos.planned_sorting_date + timedelta(days=days_delta)
        )
    if pos.planned_completion_date:
        pos.planned_completion_date = _skip_weekends(
            pos.planned_completion_date + timedelta(days=days_delta)
        )
