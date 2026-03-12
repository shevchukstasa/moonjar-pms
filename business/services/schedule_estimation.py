"""
Schedule Estimation service.
Business Logic: §5
"""
from uuid import UUID
from datetime import date, datetime, timedelta
from math import ceil, floor
from typing import Optional
import logging

from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func

from api.models import (
    ProductionOrder, ProductionOrderItem, OrderPosition, Material, MaterialStock,
    MaterialPurchaseRequest, Task, Resource, Batch, ScheduleSlot,
    TpsShiftMetric, Size,
)
from api.enums import (
    OrderStatus, PositionStatus, TaskStatus, TaskType,
    BatchStatus, ResourceType, PurchaseStatus,
)

logger = logging.getLogger("moonjar.schedule_estimation")

# Default lead times (days) when no purchase request exists
DEFAULT_LEAD_TIME_STONE = 35
DEFAULT_LEAD_TIME_PIGMENT = 7
DEFAULT_LEAD_TIME_OTHER = 14

# Default kiln firing cycle time in days (load + fire + cool + unload)
KILN_CYCLE_DAYS = 2

# Fallback production speed when no historical data
DEFAULT_PRODUCTION_DAYS = 14


def calculate_buffer(production_days: int) -> int:
    """Buffer = max(2, min(5, ceil(production_days * 0.10)))."""
    buffer = production_days * 0.10
    return max(2, min(5, ceil(buffer)))


def calculate_position_availability(db: Session, position: OrderPosition) -> date:
    """Max across all blocking factors for a position."""
    factors: list[date] = []
    today = date.today()

    # 1. Check material availability via related order item recipe
    #    If position has materials reserved, check their availability
    if position.recipe_id:
        from api.models import RecipeMaterial
        recipe_materials = db.query(RecipeMaterial).filter(
            RecipeMaterial.recipe_id == position.recipe_id
        ).all()

        for rm in recipe_materials:
            material = db.query(Material).get(rm.material_id)
            if not material:
                continue

            stock = db.query(MaterialStock).filter(
                MaterialStock.material_id == rm.material_id,
                MaterialStock.factory_id == position.factory_id,
            ).first()

            needed_qty = float(rm.quantity_per_unit) * position.quantity
            if stock and float(stock.balance) >= needed_qty:
                factors.append(today)
            else:
                # Check for pending purchase request
                pr = db.query(MaterialPurchaseRequest).filter(
                    MaterialPurchaseRequest.factory_id == position.factory_id,
                    MaterialPurchaseRequest.status.in_([
                        PurchaseStatus.PENDING.value,
                        PurchaseStatus.APPROVED.value,
                        PurchaseStatus.SENT.value,
                    ]),
                ).first()

                if pr and pr.expected_delivery_date:
                    factors.append(pr.expected_delivery_date)
                else:
                    # Use default lead time based on material type
                    mat_type = material.material_type or ""
                    if mat_type == "stone":
                        factors.append(today + timedelta(days=DEFAULT_LEAD_TIME_STONE))
                    elif mat_type == "pigment":
                        factors.append(today + timedelta(days=DEFAULT_LEAD_TIME_PIGMENT))
                    else:
                        factors.append(today + timedelta(days=DEFAULT_LEAD_TIME_OTHER))

    # 2. Check blocking tasks
    blocking_tasks = db.query(Task).filter(
        Task.related_position_id == position.id,
        Task.blocking.is_(True),
        Task.status.in_([TaskStatus.PENDING.value, TaskStatus.IN_PROGRESS.value]),
    ).all()

    for task in blocking_tasks:
        task_type = task.type if isinstance(task.type, str) else task.type.value
        if task_type in (TaskType.STENCIL_ORDER.value, TaskType.SILK_SCREEN_ORDER.value):
            factors.append(today + timedelta(days=5))
        elif task_type == TaskType.COLOR_MATCHING.value:
            factors.append(today + timedelta(days=7))
        elif task_type == TaskType.RECIPE_CONFIGURATION.value:
            factors.append(today + timedelta(days=3))
        else:
            # Generic blocking task — 3 days default
            factors.append(today + timedelta(days=3))

    return max(factors) if factors else today


def _get_avg_production_speed(db: Session, factory_id: UUID, period_days: int = 30) -> float:
    """Get average production speed in sqm/day for a factory over the given period."""
    cutoff = date.today() - timedelta(days=period_days)

    result = db.query(
        sa_func.sum(TpsShiftMetric.actual_output)
    ).filter(
        TpsShiftMetric.factory_id == factory_id,
        TpsShiftMetric.date >= cutoff,
    ).scalar()

    total_output = float(result or 0)
    if total_output > 0:
        return total_output / period_days
    return 0.0


def _calculate_kiln_firings(db: Session, order: ProductionOrder) -> int:
    """Estimate number of kiln firings needed for an order."""
    positions = db.query(OrderPosition).filter(
        OrderPosition.order_id == order.id,
        OrderPosition.status != PositionStatus.CANCELLED.value,
    ).all()

    if not positions:
        return 0

    # Sum total sqm
    total_sqm = sum(float(p.quantity_sqm or 0) for p in positions)

    # Find average kiln capacity for this factory
    avg_capacity = db.query(
        sa_func.avg(Resource.capacity_sqm)
    ).filter(
        Resource.factory_id == order.factory_id,
        Resource.resource_type == ResourceType.KILN.value,
        Resource.is_active.is_(True),
    ).scalar()

    if avg_capacity and float(avg_capacity) > 0:
        return ceil(total_sqm / float(avg_capacity))

    # Fallback: 1 firing per 10 sqm
    return max(1, ceil(total_sqm / 10.0))


def calculate_production_days(db: Session, order: ProductionOrder) -> int:
    """Based on avg production speed + kiln schedule."""
    # Get total sqm for the order
    positions = db.query(OrderPosition).filter(
        OrderPosition.order_id == order.id,
        OrderPosition.status != PositionStatus.CANCELLED.value,
    ).all()

    total_sqm = sum(float(p.quantity_sqm or 0) for p in positions)

    # Method 1: based on historical speed
    avg_speed = _get_avg_production_speed(db, order.factory_id, period_days=30)
    if avg_speed > 0:
        base_days = ceil(total_sqm / avg_speed)
    else:
        base_days = DEFAULT_PRODUCTION_DAYS

    # Method 2: based on kiln schedule
    kilns_needed = _calculate_kiln_firings(db, order)
    kiln_days = kilns_needed * KILN_CYCLE_DAYS

    return max(base_days, kiln_days)


def calculate_schedule_deadline(db: Session, order: ProductionOrder) -> date:
    """Formula: max_availability + production_days + buffer."""
    today = date.today()
    max_availability = today

    # Find max availability across all positions
    positions = db.query(OrderPosition).filter(
        OrderPosition.order_id == order.id,
        OrderPosition.status != PositionStatus.CANCELLED.value,
    ).all()

    for position in positions:
        availability = calculate_position_availability(db, position)
        if availability > max_availability:
            max_availability = availability

    # Calculate production days and buffer
    production_days = calculate_production_days(db, order)
    buffer_days = calculate_buffer(production_days)

    schedule_deadline = max_availability + timedelta(days=production_days + buffer_days)

    # Write back to order
    order.schedule_deadline = schedule_deadline
    db.add(order)
    db.flush()

    logger.info(
        "Order %s: schedule_deadline=%s (availability=%s, prod=%d, buffer=%d)",
        order.order_number, schedule_deadline, max_availability,
        production_days, buffer_days,
    )

    return schedule_deadline


def recalculate_all_estimates(db: Session, factory_id: UUID) -> None:
    """Recalculate all active order estimates after capacity change."""
    active_orders = db.query(ProductionOrder).filter(
        ProductionOrder.factory_id == factory_id,
        ProductionOrder.status.in_([
            OrderStatus.NEW.value,
            OrderStatus.IN_PRODUCTION.value,
            OrderStatus.PARTIALLY_READY.value,
        ]),
    ).all()

    count = 0
    for order in active_orders:
        try:
            calculate_schedule_deadline(db, order)
            count += 1
        except Exception as e:
            logger.error("Failed to recalculate order %s: %s", order.order_number, e)

    db.commit()
    logger.info("Recalculated %d/%d active orders for factory %s", count, len(active_orders), factory_id)
