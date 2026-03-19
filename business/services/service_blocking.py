"""
Service Blocking — timing-based position blocking.

Decision 2026-03-19:
Block only when service_lead_time_days >= days_until_planned_glazing_date.
NOT immediate upon position creation.

Priority boost on unblock: priority_order += 10 points.

Supported service types:
- 'stencil'        — stencil production (default 3 days)
- 'silkscreen'     — silk screen production (default 5 days)
- 'color_matching' — color matching lab work (default 2 days)
- 'custom_mold'    — custom mold fabrication (default 7 days)
"""
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger("moonjar.service_blocking")

# Default lead times in days — used when no factory-specific override exists
DEFAULT_LEAD_TIMES: dict[str, int] = {
    'stencil': 3,
    'silkscreen': 5,
    'color_matching': 2,
    'custom_mold': 7,
}

# Map service_type to TaskType enum name
_SERVICE_TO_TASK_TYPE: dict[str, str] = {
    'stencil': 'STENCIL_ORDER',
    'silkscreen': 'SILK_SCREEN_ORDER',
    'color_matching': 'COLOR_MATCHING',
    'custom_mold': 'MATERIAL_ORDER',
}


# ────────────────────────────────────────────────────────────────
# Lead time retrieval
# ────────────────────────────────────────────────────────────────

def get_service_lead_time(db: Session, factory_id: UUID, service_type: str) -> int:
    """
    Get lead time for service type. Factory-specific override first, then default.

    Returns number of days (integer >= 0).
    """
    try:
        row = db.execute(text("""
            SELECT lead_time_days FROM service_lead_times
            WHERE factory_id = :fid AND service_type = :stype
            LIMIT 1
        """), {'fid': str(factory_id), 'stype': service_type}).fetchone()
        if row:
            return int(row[0])
    except Exception as exc:
        logger.debug("get_service_lead_time fallback to default: %s", exc)
    return DEFAULT_LEAD_TIMES.get(service_type, 3)


# ────────────────────────────────────────────────────────────────
# Timing check
# ────────────────────────────────────────────────────────────────

def should_block_for_service(
    db: Session,
    position,
    service_type: str,
) -> Tuple[bool, int]:
    """
    Check if position should be blocked for a service right now.

    Returns (should_block, days_until_glazing).

    Logic:
    - If position has no planned_glazing_date — do NOT block (check later after scheduling).
    - If glazing date is in the past (days_until_glazing <= 0) — block immediately (urgent).
    - Otherwise block when: lead_time_days >= days_until_glazing.

    Example: lead_time=3 days, glazing in 2 days → 3 >= 2 → block now.
    Example: lead_time=3 days, glazing in 5 days → 3 >= 5 → False → don't block yet.
    """
    planned_glazing = getattr(position, 'planned_glazing_date', None)
    if not planned_glazing:
        return False, 0  # No date yet — check after scheduling assigns one

    today = date.today()
    days_until_glazing = (planned_glazing - today).days

    if days_until_glazing <= 0:
        # Past or today — urgent, definitely block
        return True, 0

    lead_time = get_service_lead_time(db, position.factory_id, service_type)
    should_block = lead_time >= days_until_glazing
    return should_block, days_until_glazing


# ────────────────────────────────────────────────────────────────
# Block position
# ────────────────────────────────────────────────────────────────

def block_position_for_service(
    db: Session,
    position,
    service_type: str,
    task_description: Optional[str] = None,
) -> Optional[object]:
    """
    Block a position awaiting a service. Creates Task with deadline.

    - Saves current status in status_before_block.
    - Sets blocked_by_service on position.
    - Sets position.status to AWAITING_STENCIL_SILKSCREEN or AWAITING_COLOR_MATCHING.
    - Creates a blocking Task with due_at = planned_glazing - lead_time.

    Returns created Task or None if task creation fails.
    """
    from api.enums import TaskType, TaskStatus, UserRole, PositionStatus
    from api.models import Task
    import uuid as uuid_module

    # Determine status to set
    status_map_to_blocking = {
        'stencil': PositionStatus.AWAITING_STENCIL_SILKSCREEN,
        'silkscreen': PositionStatus.AWAITING_STENCIL_SILKSCREEN,
        'color_matching': PositionStatus.AWAITING_COLOR_MATCHING,
        'custom_mold': PositionStatus.AWAITING_STENCIL_SILKSCREEN,  # closest available
    }
    blocking_status = status_map_to_blocking.get(service_type, PositionStatus.AWAITING_STENCIL_SILKSCREEN)

    # Save current status before block
    current_status = (
        position.status.value
        if hasattr(position.status, 'value')
        else str(position.status)
    )

    # Persist tracking columns (may not be in ORM yet — use raw SQL)
    try:
        db.execute(text("""
            UPDATE order_positions
            SET blocked_by_service = :stype,
                status_before_block = :prev_status
            WHERE id = :pid
        """), {
            'stype': service_type,
            'prev_status': current_status,
            'pid': str(position.id),
        })
    except Exception as exc:
        logger.debug("block_position_for_service raw SQL failed: %s", exc)

    # Update ORM status
    position.status = blocking_status

    # Calculate task deadline: planned_glazing - lead_time
    planned_glazing = getattr(position, 'planned_glazing_date', None)
    lead_time = get_service_lead_time(db, position.factory_id, service_type)
    due_at = None
    if planned_glazing:
        deadline_date = planned_glazing - timedelta(days=lead_time)
        due_at = datetime.combine(deadline_date, datetime.min.time()).replace(tzinfo=timezone.utc)

    # Resolve TaskType enum
    task_type_name = _SERVICE_TO_TASK_TYPE.get(service_type, 'STENCIL_ORDER')
    try:
        task_type = TaskType[task_type_name]
    except KeyError:
        task_type = TaskType.STENCIL_ORDER

    description = task_description or (
        f"Service required: {service_type} for position {position.id} "
        f"(glazing {'on ' + str(planned_glazing) if planned_glazing else 'date TBD'})"
    )

    try:
        task = Task(
            id=uuid_module.uuid4(),
            factory_id=position.factory_id,
            type=task_type,
            status=TaskStatus.PENDING,
            assigned_role=UserRole.PRODUCTION_MANAGER,
            related_position_id=position.id,
            related_order_id=getattr(position, 'order_id', None),
            blocking=True,
            description=description,
            due_at=due_at,
            metadata_json={
                'service_type': service_type,
                'lead_time_days': lead_time,
                'planned_glazing_date': str(planned_glazing) if planned_glazing else None,
                'blocking_reason': 'timing',
                'status_before_block': current_status,
            },
        )
        db.add(task)
        logger.info(
            "SERVICE_BLOCK | position=%s service=%s lead=%dd glazing=%s due=%s",
            position.id, service_type, lead_time, planned_glazing, due_at,
        )
        return task
    except Exception as exc:
        logger.warning("block_position_for_service task creation failed: %s", exc)
        return None


# ────────────────────────────────────────────────────────────────
# Unblock position
# ────────────────────────────────────────────────────────────────

def unblock_position_service(db: Session, position) -> dict:
    """
    Unblock a position when its service is ready.

    - Restores status from status_before_block (fallback: 'planned').
    - Boosts priority_order by 10 points.
    - Clears blocked_by_service and status_before_block columns.

    Returns dict with unblock result info.
    """
    from api.enums import PositionStatus

    # Read previous status from DB (raw SQL — column may not be in ORM)
    prev_status = None
    service_type = None
    try:
        row = db.execute(text("""
            SELECT status_before_block, blocked_by_service
            FROM order_positions
            WHERE id = :pid
        """), {'pid': str(position.id)}).fetchone()
        if row:
            prev_status = row[0]
            service_type = row[1]
    except Exception as exc:
        logger.debug("unblock_position_service read failed: %s", exc)

    if not prev_status:
        prev_status = PositionStatus.PLANNED.value

    # Restore status via ORM
    try:
        status_map = {s.value: s for s in PositionStatus}
        if prev_status in status_map:
            position.status = status_map[prev_status]
        else:
            position.status = PositionStatus.PLANNED
    except Exception as exc:
        logger.debug("unblock_position_service status restore failed: %s", exc)

    # Priority boost
    current_priority = getattr(position, 'priority_order', 0) or 0
    new_priority = current_priority + 10
    position.priority_order = new_priority

    # Clear blocking columns (raw SQL)
    try:
        db.execute(text("""
            UPDATE order_positions
            SET blocked_by_service = NULL,
                status_before_block = NULL
            WHERE id = :pid
        """), {'pid': str(position.id)})
    except Exception as exc:
        logger.debug("unblock_position_service clear failed: %s", exc)

    logger.info(
        "SERVICE_UNBLOCK | position=%s service=%s restored_status=%s new_priority=%d",
        position.id, service_type, prev_status, new_priority,
    )

    return {
        'position_id': str(position.id),
        'service_type': service_type,
        'restored_status': prev_status,
        'new_priority_order': new_priority,
        'unblocked': True,
    }


# ────────────────────────────────────────────────────────────────
# Scheduler hook: re-check positions after glazing date assigned
# ────────────────────────────────────────────────────────────────

def check_pending_service_blocks(db: Session, factory_id: Optional[UUID] = None) -> dict:
    """
    Re-evaluate service blocking for all PLANNED positions that have a
    planned_glazing_date but haven't been blocked yet.

    Called by APScheduler daily (or after production_scheduler assigns dates).

    Returns summary dict with counts.
    """
    from api.enums import PositionStatus
    from api.models import OrderPosition

    filters = [
        OrderPosition.status == PositionStatus.PLANNED,
        OrderPosition.planned_glazing_date.isnot(None),
    ]
    if factory_id:
        filters.append(OrderPosition.factory_id == factory_id)

    positions = db.query(OrderPosition).filter(*filters).all()

    blocked_count = 0
    skipped_count = 0

    for pos in positions:
        # Check each relevant service based on position metadata
        # Read blocked_by_service to skip already-blocked positions
        try:
            row = db.execute(text("""
                SELECT blocked_by_service FROM order_positions WHERE id = :pid
            """), {'pid': str(pos.id)}).fetchone()
            already_blocked = row[0] if row else None
        except Exception:
            already_blocked = None

        if already_blocked:
            skipped_count += 1
            continue

        # Determine which services this position needs from metadata
        services_needed = _infer_services_from_position(db, pos)

        for stype in services_needed:
            should_block, days_left = should_block_for_service(db, pos, stype)
            if should_block:
                block_position_for_service(db, pos, stype)
                blocked_count += 1
                break  # Only apply one block per position (highest priority service)

    if blocked_count > 0:
        db.commit()

    return {
        'factory_id': str(factory_id) if factory_id else 'all',
        'positions_checked': len(positions),
        'newly_blocked': blocked_count,
        'skipped_already_blocked': skipped_count,
    }


def _infer_services_from_position(db: Session, position) -> list[str]:
    """
    Determine which services a position needs based on its data.

    Reads pending (non-done) tasks linked to the position to see what
    services were registered during order intake but not yet completed.
    """
    from api.models import Task
    from api.enums import TaskStatus, TaskType

    service_task_types = {
        TaskType.STENCIL_ORDER.value: 'stencil',
        TaskType.SILK_SCREEN_ORDER.value: 'silkscreen',
        TaskType.COLOR_MATCHING.value: 'color_matching',
    }

    try:
        pending_tasks = db.query(Task).filter(
            Task.related_position_id == position.id,
            Task.status.in_([TaskStatus.PENDING.value, TaskStatus.IN_PROGRESS.value]),
            Task.blocking.is_(True),
            Task.type.in_(list(service_task_types.keys())),
        ).all()
        return [service_task_types[t.type.value if hasattr(t.type, 'value') else t.type]
                for t in pending_tasks
                if (t.type.value if hasattr(t.type, 'value') else t.type) in service_task_types]
    except Exception as exc:
        logger.debug("_infer_services_from_position failed: %s", exc)
        return []
