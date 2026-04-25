"""Express mode (Material Tracking Disabled) for an order.

Owner-level override that lets a single order proceed without material
reservation/consumption. See docs/BUSINESS_LOGIC_FULL.md §2.6 for the
business rule and docs/TEMPORARY_DELEGATIONS.md for the role gate
(currently widened to CEO).
"""
from __future__ import annotations

import logging
import uuid as uuid_mod
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

logger = logging.getLogger("moonjar.order_fast_track")


# Statuses that should be cleared to PLANNED before jumping to target_status,
# because they represent an unmet pre-condition that express mode is
# explicitly waiving.
_BLOCKING_PRE_STATUSES = {
    "insufficient_materials",
    "awaiting_recipe",
    "awaiting_stencil_silkscreen",
    "awaiting_color_matching",
    "awaiting_size_confirmation",
    "awaiting_consumption_data",
}


def enable_fast_track(
    db: Session,
    order_id: UUID,
    reason: str,
    target_status: Optional[str],
    user_id: UUID,
) -> dict:
    """Flip an order into express mode and (optionally) jump every position
    to a chosen production status.

    Idempotent only on the first call: once `material_tracking_disabled`
    is True, subsequent calls 409.
    """
    from api.models import ProductionOrder, OrderPosition, Task
    from api.enums import PositionStatus, TaskStatus, TaskType, UserRole
    from business.services.material_reservation import unreserve_materials_for_position
    from business.services.status_machine import transition_position_status

    if not reason or not reason.strip():
        raise ValueError("Reason is required for express mode (audit trail)")

    order = db.query(ProductionOrder).get(order_id)
    if not order:
        raise LookupError(f"Order {order_id} not found")

    if order.material_tracking_disabled:
        raise ValueError(
            f"Order {order.order_number} is already in express mode "
            f"(enabled at {order.material_tracking_disabled_at})"
        )

    now = datetime.now(timezone.utc)
    reason = reason.strip()

    # Validate target_status if provided
    target_ps: Optional[PositionStatus] = None
    if target_status:
        try:
            target_ps = PositionStatus(target_status)
        except ValueError as e:
            raise ValueError(f"Invalid target_status: {target_status}") from e

    # 1. Flip the flag
    order.material_tracking_disabled = True
    order.material_tracking_disabled_reason = reason
    order.material_tracking_disabled_at = now
    order.material_tracking_disabled_by = user_id
    order.updated_at = now

    positions = (
        db.query(OrderPosition)
        .filter(OrderPosition.order_id == order_id)
        .all()
    )

    reservations_released = 0
    transitioned = 0
    skipped_terminal = 0

    for p in positions:
        # 2. Release reservations + mark consumption as already settled
        try:
            unreserve_materials_for_position(db, p.id)
            reservations_released += 1
        except Exception as e:
            logger.warning(
                "FAST_TRACK_UNRESERVE_FAIL | position=%s | %s", p.id, e,
            )

        if p.materials_written_off_at is None:
            p.materials_written_off_at = now

        # 3. Move position to target_status (if requested) or just clear
        # any blocking pre-status to PLANNED so the queue is unblocked.
        current = p.status.value if hasattr(p.status, "value") else str(p.status)

        if current in {"shipped", "cancelled", "merged"}:
            skipped_terminal += 1
            continue

        if target_ps is not None:
            try:
                transition_position_status(
                    db, p.id, target_ps.value,
                    changed_by=user_id, is_override=True,
                    notes=f"[Express mode] {reason}",
                )
                transitioned += 1
            except Exception as e:
                logger.warning(
                    "FAST_TRACK_TRANSITION_FAIL | position=%s | %s -> %s | %s",
                    p.id, current, target_ps.value, e,
                )
        elif current in _BLOCKING_PRE_STATUSES:
            try:
                transition_position_status(
                    db, p.id, PositionStatus.PLANNED.value,
                    changed_by=user_id, is_override=True,
                    notes=f"[Express mode] {reason}",
                )
                transitioned += 1
            except Exception as e:
                logger.warning(
                    "FAST_TRACK_UNBLOCK_FAIL | position=%s | %s -> planned | %s",
                    p.id, current, e,
                )

    # 4. Close every still-open blocking task on the order
    blocking_tasks = (
        db.query(Task)
        .filter(
            Task.related_order_id == order_id,
            Task.blocking.is_(True),
            Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS]),
        )
        .all()
    )
    for task in blocking_tasks:
        task.status = TaskStatus.DONE
        task.completed_at = now
        task.updated_at = now

    # 5. Audit task with full metadata (visible in order activity log)
    audit_task = Task(
        id=uuid_mod.uuid4(),
        factory_id=order.factory_id,
        type=TaskType.MANA_CONFIRMATION,
        status=TaskStatus.DONE,
        assigned_role=UserRole.OWNER,
        related_order_id=order_id,
        blocking=False,
        description=f"Express mode enabled — material tracking disabled: {reason}",
        priority=0,
        completed_at=now,
        created_at=now,
        updated_at=now,
        metadata_json={
            "action": "fast_track",
            "reason": reason,
            "target_status": target_ps.value if target_ps else None,
            "user_id": str(user_id),
            "positions_total": len(positions),
            "positions_transitioned": transitioned,
            "positions_skipped_terminal": skipped_terminal,
            "reservations_released": reservations_released,
            "blocking_tasks_closed": [str(t.id) for t in blocking_tasks],
        },
    )
    db.add(audit_task)

    # 6. Security event
    try:
        from api.auth import log_security_event
        log_security_event(
            db,
            action="order_fast_track",
            actor_id=str(user_id),
            target_entity="production_order",
            target_id=str(order_id),
            details={
                "reason": reason,
                "target_status": target_ps.value if target_ps else None,
                "positions_total": len(positions),
            },
        )
    except Exception as e:
        logger.warning("FAST_TRACK_AUDIT_FAIL | %s", e)

    db.commit()
    db.refresh(order)

    logger.warning(
        "ORDER_FAST_TRACK | user=%s | order=%s (%s) | target=%s | "
        "positions=%d transitioned=%d skipped=%d | reservations_released=%d "
        "| reason=%s",
        user_id, order_id, order.order_number,
        target_ps.value if target_ps else "(none)",
        len(positions), transitioned, skipped_terminal,
        reservations_released, reason[:80],
    )

    return {
        "order_id": str(order_id),
        "order_number": order.order_number,
        "material_tracking_disabled": True,
        "material_tracking_disabled_at": now.isoformat(),
        "material_tracking_disabled_reason": reason,
        "target_status": target_ps.value if target_ps else None,
        "positions_total": len(positions),
        "positions_transitioned": transitioned,
        "positions_skipped_terminal": skipped_terminal,
        "reservations_released": reservations_released,
        "blocking_tasks_closed": len(blocking_tasks),
    }
