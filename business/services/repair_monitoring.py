"""
Repair SLA Monitoring service.
Business Logic: §12
"""
import logging
import uuid as uuid_mod
from uuid import UUID
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from api.models import (
    OrderPosition,
    ProductionOrder,
    RepairQueue,
    Task,
)
from api.enums import (
    PositionStatus,
    RepairStatus,
    SplitCategory,
    TaskType,
    TaskStatus,
    UserRole,
)

logger = logging.getLogger("moonjar.repair_monitoring")

# --- SLA constants (working days) ---
_SLA_DAYS = {
    "reglaze": 3,
    "refire": 5,
    "grind": 5,
    "reshape": 5,
}
_ESCALATION_MULTIPLIER_CEO = 2  # 2x SLA → escalate to CEO

# Repair-related position statuses
_REPAIR_STATUSES = (
    PositionStatus.AWAITING_REGLAZE,
    PositionStatus.REFIRE,
)

# Map position status → repair type for SLA lookup
_STATUS_TO_REPAIR_TYPE = {
    PositionStatus.AWAITING_REGLAZE: "reglaze",
    PositionStatus.REFIRE: "refire",
}


def _working_days_between(start: datetime, end: datetime) -> int:
    """Count working days (Mon-Sat, excluding Sun) between two datetimes.
    Bali factories work 6 days a week (Mon-Sat).
    """
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    days = 0
    current = start.date()
    end_date = end.date()
    while current < end_date:
        # Sunday = 6 in Python's weekday()
        if current.weekday() != 6:
            days += 1
        current += timedelta(days=1)
    return days


def check_repair_sla(db: Session, factory_id: UUID) -> list[dict]:
    """Scheduled job: check repair SLA compliance for a factory.

    - Query all positions in AWAITING_REGLAZE / REFIRE status
    - Query all RepairQueue entries with IN_REPAIR status
    - If SLA exceeded → create REPAIR_SLA_ALERT task for PM
    - If SLA exceeded by 2x → create REPAIR_SLA_ALERT task for CEO
    - Returns list of overdue items with details.
    """
    now = datetime.now(timezone.utc)
    overdue_items: list[dict] = []

    # ── 1. Check positions in repair statuses ──
    positions = (
        db.query(OrderPosition)
        .filter(
            OrderPosition.factory_id == factory_id,
            OrderPosition.status.in_(_REPAIR_STATUSES),
        )
        .all()
    )

    for pos in positions:
        repair_type = _STATUS_TO_REPAIR_TYPE.get(pos.status, "refire")
        sla_days = _SLA_DAYS.get(repair_type, 5)

        # Use updated_at as proxy for when status changed; fall back to created_at
        entered_repair_at = pos.updated_at or pos.created_at
        working_days_in_repair = _working_days_between(entered_repair_at, now)

        if working_days_in_repair <= sla_days:
            continue

        overdue_by = working_days_in_repair - sla_days
        escalation_level = "ceo" if working_days_in_repair >= sla_days * _ESCALATION_MULTIPLIER_CEO else "pm"

        overdue_item = {
            "position_id": str(pos.id),
            "order_id": str(pos.order_id),
            "repair_type": repair_type,
            "sla_days": sla_days,
            "working_days_in_repair": working_days_in_repair,
            "overdue_by": overdue_by,
            "escalation_level": escalation_level,
            "color": pos.color,
            "size": pos.size,
            "quantity": pos.quantity,
        }
        overdue_items.append(overdue_item)

        # Create escalation task if one doesn't already exist
        _create_sla_escalation_task(
            db,
            factory_id=factory_id,
            position=pos,
            repair_type=repair_type,
            working_days=working_days_in_repair,
            sla_days=sla_days,
            escalation_level=escalation_level,
        )

    # ── 2. Check RepairQueue entries ──
    repair_entries = (
        db.query(RepairQueue)
        .filter(
            RepairQueue.factory_id == factory_id,
            RepairQueue.status == RepairStatus.IN_REPAIR,
        )
        .all()
    )

    for entry in repair_entries:
        # Determine repair type from defect_type field
        repair_type = _infer_repair_type(entry.defect_type)
        sla_days = _SLA_DAYS.get(repair_type, 5)

        entered_at = entry.created_at
        working_days_in_repair = _working_days_between(entered_at, now)

        if working_days_in_repair <= sla_days:
            continue

        overdue_by = working_days_in_repair - sla_days
        escalation_level = "ceo" if working_days_in_repair >= sla_days * _ESCALATION_MULTIPLIER_CEO else "pm"

        overdue_item = {
            "repair_queue_id": str(entry.id),
            "source_position_id": str(entry.source_position_id) if entry.source_position_id else None,
            "source_order_id": str(entry.source_order_id) if entry.source_order_id else None,
            "repair_type": repair_type,
            "defect_type": entry.defect_type,
            "sla_days": sla_days,
            "working_days_in_repair": working_days_in_repair,
            "overdue_by": overdue_by,
            "escalation_level": escalation_level,
            "color": entry.color,
            "size": entry.size,
            "quantity": entry.quantity,
        }
        overdue_items.append(overdue_item)

        # Create escalation task for repair queue entry
        _create_sla_escalation_task_for_queue(
            db,
            factory_id=factory_id,
            entry=entry,
            repair_type=repair_type,
            working_days=working_days_in_repair,
            sla_days=sla_days,
            escalation_level=escalation_level,
        )

    if overdue_items:
        logger.warning(
            "Repair SLA check for factory %s: %d overdue items found",
            factory_id, len(overdue_items),
        )
    else:
        logger.info("Repair SLA check for factory %s: all within SLA", factory_id)

    return overdue_items


def _infer_repair_type(defect_type: Optional[str]) -> str:
    """Infer repair type from defect_type string stored in RepairQueue."""
    if not defect_type:
        return "refire"
    lower = defect_type.lower()
    if "reglaze" in lower or "glaze" in lower:
        return "reglaze"
    if "grind" in lower:
        return "grind"
    if "reshape" in lower:
        return "reshape"
    return "refire"


def _create_sla_escalation_task(
    db: Session,
    factory_id: UUID,
    position: OrderPosition,
    repair_type: str,
    working_days: int,
    sla_days: int,
    escalation_level: str,
) -> None:
    """Create an SLA escalation task for a position, avoiding duplicates."""
    assigned_role = UserRole.CEO if escalation_level == "ceo" else UserRole.PRODUCTION_MANAGER

    # Check for existing active escalation task for this position + level
    existing = (
        db.query(Task)
        .filter(
            Task.factory_id == factory_id,
            Task.type == TaskType.REPAIR_SLA_ALERT,
            Task.related_position_id == position.id,
            Task.assigned_role == assigned_role,
            Task.status.notin_([TaskStatus.DONE, TaskStatus.CANCELLED]),
        )
        .first()
    )

    description = (
        f"Repair SLA exceeded: {position.color} {position.size} x{position.quantity} "
        f"({repair_type}) — {working_days} working days in repair "
        f"(SLA: {sla_days} days, overdue by {working_days - sla_days} days)"
    )

    if existing:
        # Update description with latest numbers
        existing.description = description
        existing.metadata_json = {
            **(existing.metadata_json or {}),
            "working_days": working_days,
            "overdue_by": working_days - sla_days,
            "last_checked": datetime.now(timezone.utc).isoformat(),
        }
        logger.debug(
            "Updated existing SLA task %s for position %s", existing.id, position.id,
        )
        return

    task = Task(
        id=uuid_mod.uuid4(),
        factory_id=factory_id,
        type=TaskType.REPAIR_SLA_ALERT,
        assigned_role=assigned_role,
        related_order_id=position.order_id,
        related_position_id=position.id,
        blocking=False,
        description=description,
        priority=8 if escalation_level == "ceo" else 5,
        metadata_json={
            "repair_type": repair_type,
            "working_days": working_days,
            "sla_days": sla_days,
            "overdue_by": working_days - sla_days,
            "escalation_level": escalation_level,
        },
    )
    db.add(task)
    logger.info(
        "Created SLA escalation task (%s) for position %s — %d days overdue",
        escalation_level, position.id, working_days - sla_days,
    )


def _create_sla_escalation_task_for_queue(
    db: Session,
    factory_id: UUID,
    entry: RepairQueue,
    repair_type: str,
    working_days: int,
    sla_days: int,
    escalation_level: str,
) -> None:
    """Create an SLA escalation task for a RepairQueue entry, avoiding duplicates."""
    assigned_role = UserRole.CEO if escalation_level == "ceo" else UserRole.PRODUCTION_MANAGER

    # Check for existing active escalation task via metadata
    existing = (
        db.query(Task)
        .filter(
            Task.factory_id == factory_id,
            Task.type == TaskType.REPAIR_SLA_ALERT,
            Task.assigned_role == assigned_role,
            Task.status.notin_([TaskStatus.DONE, TaskStatus.CANCELLED]),
        )
        .all()
    )
    for t in existing:
        meta = t.metadata_json or {}
        if meta.get("repair_queue_id") == str(entry.id):
            # Update existing task
            t.description = (
                f"Repair SLA exceeded: {entry.color} {entry.size} x{entry.quantity} "
                f"({repair_type}) — {working_days} working days in repair "
                f"(SLA: {sla_days} days, overdue by {working_days - sla_days} days)"
            )
            t.metadata_json = {
                **meta,
                "working_days": working_days,
                "overdue_by": working_days - sla_days,
                "last_checked": datetime.now(timezone.utc).isoformat(),
            }
            return

    task = Task(
        id=uuid_mod.uuid4(),
        factory_id=factory_id,
        type=TaskType.REPAIR_SLA_ALERT,
        assigned_role=assigned_role,
        related_order_id=entry.source_order_id,
        related_position_id=entry.source_position_id,
        blocking=False,
        description=(
            f"Repair SLA exceeded: {entry.color} {entry.size} x{entry.quantity} "
            f"({repair_type}) — {working_days} working days in repair "
            f"(SLA: {sla_days} days, overdue by {working_days - sla_days} days)"
        ),
        priority=8 if escalation_level == "ceo" else 5,
        metadata_json={
            "repair_queue_id": str(entry.id),
            "repair_type": repair_type,
            "working_days": working_days,
            "sla_days": sla_days,
            "overdue_by": working_days - sla_days,
            "escalation_level": escalation_level,
        },
    )
    db.add(task)
    logger.info(
        "Created SLA escalation task (%s) for repair queue %s — %d days overdue",
        escalation_level, entry.id, working_days - sla_days,
    )


# ---------------------------------------------------------------------------
# Repair queue management
# ---------------------------------------------------------------------------

_REPAIR_TYPE_PRIORITY_BONUS = {
    "reglaze": 2,   # simpler repair → slightly higher base priority (do it first)
    "grind": 1,
    "refire": 0,
    "reshape": 0,
}


def create_repair_queue_entry(
    db: Session,
    position_id: UUID,
    repair_type: str,
    priority: Optional[int] = None,
) -> Task:
    """Create a repair queue entry and associated task.

    Args:
        db: Database session.
        position_id: The position (or sub-position) needing repair.
        repair_type: One of "reglaze", "refire", "grind", "reshape".
        priority: Optional explicit priority override. If None, calculated automatically.

    Returns:
        The created (or updated) Task for tracking the repair.
    """
    now = datetime.now(timezone.utc)

    position = db.query(OrderPosition).filter(OrderPosition.id == position_id).first()
    if not position:
        raise ValueError(f"Position {position_id} not found")

    order = (
        db.query(ProductionOrder)
        .filter(ProductionOrder.id == position.order_id)
        .first()
    )

    # ── Calculate priority ──
    if priority is None:
        priority = _calculate_repair_priority(
            order=order,
            repair_type=repair_type,
            entered_at=now,
        )

    # ── Create RepairQueue entry ──
    repair_entry = RepairQueue(
        id=uuid_mod.uuid4(),
        factory_id=position.factory_id,
        color=position.color,
        size=position.size,
        quantity=position.quantity,
        defect_type=repair_type,
        source_order_id=position.order_id,
        source_position_id=position.id,
        status=RepairStatus.IN_REPAIR,
        created_at=now,
        updated_at=now,
    )
    db.add(repair_entry)

    # ── Create tracking Task ──
    sla_days = _SLA_DAYS.get(repair_type, 5)
    due_at = _add_working_days(now, sla_days)

    task = Task(
        id=uuid_mod.uuid4(),
        factory_id=position.factory_id,
        type=TaskType.REPAIR_SLA_ALERT,
        status=TaskStatus.PENDING,
        assigned_role=UserRole.PRODUCTION_MANAGER,
        related_order_id=position.order_id,
        related_position_id=position.id,
        blocking=False,
        description=(
            f"Repair ({repair_type}): {position.color} {position.size} "
            f"x{position.quantity} — SLA {sla_days} working days"
        ),
        priority=priority,
        due_at=due_at,
        created_at=now,
        updated_at=now,
        metadata_json={
            "repair_queue_id": str(repair_entry.id),
            "repair_type": repair_type,
            "sla_days": sla_days,
            "entered_at": now.isoformat(),
            "order_deadline": order.final_deadline.isoformat() if order and order.final_deadline else None,
        },
    )
    db.add(task)

    logger.info(
        "Created repair queue entry %s and task %s for position %s (%s), priority=%d",
        repair_entry.id, task.id, position_id, repair_type, priority,
    )

    return task


def _calculate_repair_priority(
    order: Optional[ProductionOrder],
    repair_type: str,
    entered_at: datetime,
) -> int:
    """Calculate repair priority (higher = more urgent).

    Factors:
      - Order deadline proximity: +5 if < 7 days, +3 if < 14 days, +1 otherwise
      - Repair type bonus: simpler repairs get a small boost
      - Base priority: 3
    """
    base = 3

    # Deadline urgency
    deadline_bonus = 0
    if order and order.final_deadline:
        days_to_deadline = (order.final_deadline - entered_at.date()).days
        if days_to_deadline < 7:
            deadline_bonus = 5
        elif days_to_deadline < 14:
            deadline_bonus = 3
        else:
            deadline_bonus = 1

    type_bonus = _REPAIR_TYPE_PRIORITY_BONUS.get(repair_type, 0)

    return base + deadline_bonus + type_bonus


def _add_working_days(start: datetime, working_days: int) -> datetime:
    """Add N working days (Mon-Sat) to a datetime."""
    current = start
    added = 0
    while added < working_days:
        current += timedelta(days=1)
        if current.weekday() != 6:  # skip Sunday
            added += 1
    return current


# ---------------------------------------------------------------------------
# Repair queue query
# ---------------------------------------------------------------------------

def get_repair_queue(db: Session, factory_id: UUID) -> list[dict]:
    """Return all active repair items for a factory, sorted by priority.

    Includes:
      - RepairQueue entries with IN_REPAIR status
      - Positions in AWAITING_REGLAZE / REFIRE status
      - Position details, repair type, time in queue, SLA status
    """
    now = datetime.now(timezone.utc)
    results: list[dict] = []

    # ── 1. RepairQueue entries ──
    repair_entries = (
        db.query(RepairQueue)
        .filter(
            RepairQueue.factory_id == factory_id,
            RepairQueue.status == RepairStatus.IN_REPAIR,
        )
        .order_by(RepairQueue.created_at)
        .all()
    )

    for entry in repair_entries:
        repair_type = _infer_repair_type(entry.defect_type)
        sla_days = _SLA_DAYS.get(repair_type, 5)
        working_days = _working_days_between(entry.created_at, now)
        overdue = working_days > sla_days

        # Find associated task for priority
        task = (
            db.query(Task)
            .filter(
                Task.factory_id == factory_id,
                Task.type == TaskType.REPAIR_SLA_ALERT,
                Task.related_position_id == entry.source_position_id,
                Task.status.notin_([TaskStatus.DONE, TaskStatus.CANCELLED]),
            )
            .first()
        )

        # Fetch order for deadline info
        order = None
        if entry.source_order_id:
            order = db.query(ProductionOrder).filter(
                ProductionOrder.id == entry.source_order_id
            ).first()

        results.append({
            "id": str(entry.id),
            "source": "repair_queue",
            "factory_id": str(entry.factory_id),
            "position_id": str(entry.source_position_id) if entry.source_position_id else None,
            "order_id": str(entry.source_order_id) if entry.source_order_id else None,
            "order_number": order.order_number if order else None,
            "order_deadline": order.final_deadline.isoformat() if order and order.final_deadline else None,
            "color": entry.color,
            "size": entry.size,
            "quantity": entry.quantity,
            "repair_type": repair_type,
            "defect_type": entry.defect_type,
            "entered_at": entry.created_at.isoformat() if entry.created_at else None,
            "working_days_in_queue": working_days,
            "sla_days": sla_days,
            "sla_status": "overdue" if overdue else "ok",
            "overdue_by": working_days - sla_days if overdue else 0,
            "priority": task.priority if task else 0,
            "task_id": str(task.id) if task else None,
        })

    # ── 2. Positions in repair statuses (not already tracked in RepairQueue) ──
    tracked_position_ids = {
        entry.source_position_id
        for entry in repair_entries
        if entry.source_position_id
    }

    positions = (
        db.query(OrderPosition)
        .filter(
            OrderPosition.factory_id == factory_id,
            OrderPosition.status.in_(_REPAIR_STATUSES),
        )
        .all()
    )

    for pos in positions:
        if pos.id in tracked_position_ids:
            continue  # already included from RepairQueue

        repair_type = _STATUS_TO_REPAIR_TYPE.get(pos.status, "refire")
        sla_days = _SLA_DAYS.get(repair_type, 5)
        entered_at = pos.updated_at or pos.created_at
        working_days = _working_days_between(entered_at, now)
        overdue = working_days > sla_days

        order = db.query(ProductionOrder).filter(
            ProductionOrder.id == pos.order_id
        ).first()

        results.append({
            "id": str(pos.id),
            "source": "position_status",
            "factory_id": str(pos.factory_id),
            "position_id": str(pos.id),
            "order_id": str(pos.order_id),
            "order_number": order.order_number if order else None,
            "order_deadline": order.final_deadline.isoformat() if order and order.final_deadline else None,
            "color": pos.color,
            "size": pos.size,
            "quantity": pos.quantity,
            "repair_type": repair_type,
            "defect_type": None,
            "entered_at": entered_at.isoformat() if entered_at else None,
            "working_days_in_queue": working_days,
            "sla_days": sla_days,
            "sla_status": "overdue" if overdue else "ok",
            "overdue_by": working_days - sla_days if overdue else 0,
            "priority": pos.priority_order or 0,
            "task_id": None,
        })

    # Sort by priority descending, then overdue_by descending
    results.sort(key=lambda r: (r["priority"], r["overdue_by"]), reverse=True)

    return results
