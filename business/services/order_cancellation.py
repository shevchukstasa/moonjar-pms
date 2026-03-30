"""
Order Cancellation service.
Business Logic: §15

Cancels all non-terminal positions, unreserves their materials,
and cancels linked tasks.
"""
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy.orm import Session
import logging

from api.models import ProductionOrder, OrderPosition, Task, ProductionOrderStatusLog
from api.enums import OrderStatus, PositionStatus, TaskStatus

logger = logging.getLogger("moonjar.order_cancellation")


def process_order_cancellation(db: Session, order_id: UUID, confirmed_by: UUID) -> dict:
    """Cancel positions -> tasks -> release materials -> handle produced tiles.

    Returns summary dict with counts of cancelled positions and tasks.
    """
    from business.services.material_reservation import unreserve_materials_for_position

    order = db.query(ProductionOrder).filter(ProductionOrder.id == order_id).first()
    if not order:
        raise ValueError(f"Order {order_id} not found")

    # Cancel all non-terminal positions
    positions = db.query(OrderPosition).filter(
        OrderPosition.order_id == order_id,
        OrderPosition.status != PositionStatus.CANCELLED,
        OrderPosition.status != PositionStatus.SHIPPED,
    ).all()

    for p in positions:
        p.status = PositionStatus.CANCELLED
        p.updated_at = datetime.now(timezone.utc)
        try:
            unreserve_materials_for_position(db, p.id)
        except Exception as e:
            logger.warning("Failed to unreserve materials for position %s: %s", p.id, e)

    # Cancel all non-terminal tasks
    tasks = db.query(Task).filter(
        Task.related_order_id == order_id,
        Task.status.notin_([TaskStatus.DONE, TaskStatus.CANCELLED]),
    ).all()
    for task in tasks:
        task.status = TaskStatus.CANCELLED

    # Update order status
    old_status = order.status
    order.status = OrderStatus.CANCELLED
    order.updated_at = datetime.now(timezone.utc)

    # Log order status change
    try:
        db.add(ProductionOrderStatusLog(
            order_id=order.id,
            old_status=old_status,
            new_status=OrderStatus.CANCELLED,
            changed_by=confirmed_by,
        ))
    except Exception as e:
        logger.warning("Failed to log cancellation status change: %s", e)

    logger.info(
        "ORDER_CANCELLED | order=%s | positions=%d | tasks=%d | by=%s",
        order.order_number, len(positions), len(tasks), confirmed_by,
    )

    return {
        "positions_cancelled": len(positions),
        "tasks_cancelled": len(tasks),
    }
