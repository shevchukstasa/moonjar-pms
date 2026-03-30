"""
Buffer Health (TOC) service.
Business Logic: §17, §20
"""
from uuid import UUID
from datetime import date, datetime, timedelta, timezone
from typing import Optional
import logging

from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func

from api.models import (
    OrderPosition, Resource, Batch, BottleneckConfig, BufferStatus,
    Notification, User, TpsShiftMetric, ScheduleSlot,
)
from api.enums import (
    PositionStatus, ResourceType, BatchStatus, BufferHealth,
    NotificationType, RelatedEntityType, UserRole,
)

logger = logging.getLogger("moonjar.buffer_health")

# Default buffer target hours if not configured
DEFAULT_BUFFER_TARGET_HOURS = 24.0


def _get_avg_kiln_throughput(db: Session, kiln_id: UUID, period_days: int = 30) -> float:
    """Average kiln throughput in sqm/hour over the period."""
    cutoff = date.today() - timedelta(days=period_days)

    # Count done batches and their total sqm
    done_batches = db.query(Batch).filter(
        Batch.resource_id == kiln_id,
        Batch.status == BatchStatus.DONE.value,
        Batch.batch_date >= cutoff,
    ).all()

    if not done_batches:
        return 0.0

    batch_ids = [b.id for b in done_batches]

    # Sum sqm of positions that were in those batches
    total_sqm = db.query(
        sa_func.sum(OrderPosition.quantity_sqm)
    ).filter(
        OrderPosition.batch_id.in_(batch_ids),
    ).scalar()

    total_sqm = float(total_sqm or 0)

    # Estimate hours: each batch is roughly one firing cycle
    # Average cycle time from schedule slots or default 24 hours per firing
    slot_data = db.query(
        sa_func.avg(
            sa_func.extract('epoch', ScheduleSlot.end_at - ScheduleSlot.start_at) / 3600
        )
    ).filter(
        ScheduleSlot.resource_id == kiln_id,
        ScheduleSlot.batch_id.in_(batch_ids),
    ).scalar()

    avg_cycle_hours = float(slot_data or 24.0)
    total_hours = len(done_batches) * avg_cycle_hours

    if total_hours > 0:
        return total_sqm / total_hours
    return 0.0


def calculate_buffer_health(db: Session, factory_id: UUID) -> Optional[dict]:
    """Buffer = glazed items before kiln. Green/yellow/red."""
    config = db.query(BottleneckConfig).filter(
        BottleneckConfig.factory_id == factory_id,
    ).first()

    if not config or not config.constraint_resource_id:
        logger.debug("No bottleneck config for factory %s", factory_id)
        return None

    kiln = db.query(Resource).get(config.constraint_resource_id)
    if not kiln:
        return None

    # Count glazed positions waiting for kiln
    buffered = db.query(OrderPosition).filter(
        OrderPosition.factory_id == factory_id,
        OrderPosition.status == PositionStatus.GLAZED.value,
    ).all()

    buffered_count = len(buffered)
    buffered_sqm = sum(float(p.quantity_sqm or 0) for p in buffered)

    # Calculate hours of buffer
    avg_throughput = _get_avg_kiln_throughput(db, kiln.id, period_days=30)
    if avg_throughput > 0:
        buffer_hours = buffered_sqm / avg_throughput
    else:
        buffer_hours = 0.0

    target_hours = float(config.buffer_target_hours or DEFAULT_BUFFER_TARGET_HOURS)

    # Determine health
    if buffer_hours >= target_hours * 0.66:
        health = BufferHealth.GREEN
    elif buffer_hours >= target_hours * 0.33:
        health = BufferHealth.YELLOW
    else:
        health = BufferHealth.RED

    # Upsert buffer status
    bs = db.query(BufferStatus).filter(
        BufferStatus.resource_id == kiln.id,
    ).first()

    if bs:
        bs.buffered_positions_count = buffered_count
        bs.buffered_sqm = buffered_sqm
        bs.buffer_health = health
        bs.updated_at = datetime.now(timezone.utc)
    else:
        bs = BufferStatus(
            resource_id=kiln.id,
            buffered_positions_count=buffered_count,
            buffered_sqm=buffered_sqm,
            buffer_health=health,
        )
        db.add(bs)

    db.flush()

    logger.info(
        "Buffer health for factory %s: %s (%.1f sqm, %.1f hours, target %.1f hours)",
        factory_id, health.value, buffered_sqm, buffer_hours, target_hours,
    )

    return {
        "health": health.value,
        "hours": round(buffer_hours, 1),
        "target": target_hours,
        "buffered_count": buffered_count,
        "buffered_sqm": round(buffered_sqm, 2),
        "kiln_id": str(kiln.id),
        "kiln_name": kiln.name,
    }


def _get_pm_user_id(db: Session, factory_id: UUID) -> Optional[UUID]:
    """Get production manager user ID for the factory."""
    from api.models import UserFactory
    uf = db.query(UserFactory).join(User).filter(
        UserFactory.factory_id == factory_id,
        User.role == UserRole.PRODUCTION_MANAGER.value,
        User.is_active.is_(True),
    ).first()
    return uf.user_id if uf else None


def apply_rope_limit(db: Session, factory_id: UUID, positions: list) -> list:
    """TOC Rope: limit work release to N days ahead of kiln."""
    config = db.query(BottleneckConfig).filter(
        BottleneckConfig.factory_id == factory_id,
    ).first()

    if not config or not config.constraint_resource_id:
        return positions  # No config — release all

    rope_max = config.rope_max_days or 2
    rope_min = config.rope_min_days or 1
    kiln_id = config.constraint_resource_id

    # Get next planned batch dates
    upcoming_batches = db.query(Batch).filter(
        Batch.resource_id == kiln_id,
        Batch.status.in_([BatchStatus.PLANNED.value, BatchStatus.SUGGESTED.value]),
        Batch.batch_date >= date.today(),
    ).order_by(Batch.batch_date).all()

    if not upcoming_batches:
        # No planned batches — release only urgent positions (overdue orders)
        urgent = []
        for p in positions:
            if p.order and p.order.final_deadline and p.order.final_deadline <= date.today() + timedelta(days=3):
                urgent.append(p)
        return urgent if urgent else positions[:5]  # At least release a few

    next_batch_date = upcoming_batches[0].batch_date
    rope_horizon = next_batch_date - timedelta(days=rope_max)
    today_date = date.today()

    filtered = []
    for position in positions:
        if today_date >= rope_horizon:
            # Within rope window
            if position.batch_id:
                batch = db.query(Batch).get(position.batch_id)
                if batch and batch.batch_date <= next_batch_date + timedelta(days=rope_max):
                    filtered.append(position)
            else:
                # Unassigned but within window — include
                filtered.append(position)

    # Buffer health check: if buffer is red, release extra positions
    buffer_result = calculate_buffer_health(db, factory_id)
    if buffer_result and buffer_result["health"] == "red":
        extra = [p for p in positions if p not in filtered]
        filtered.extend(extra)

        pm_user_id = _get_pm_user_id(db, factory_id)
        if pm_user_id:
            notif = Notification(
                user_id=pm_user_id,
                factory_id=factory_id,
                type=NotificationType.ALERT,
                title="Buffer critically low — releasing all positions",
                message=(
                    f"Buffer at {buffer_result['hours']:.1f}h "
                    f"(target: {buffer_result['target']}h). "
                    f"Rope limit temporarily bypassed."
                ),
                related_entity_type=RelatedEntityType.KILN,
                related_entity_id=config.constraint_resource_id,
            )
            db.add(notif)
            db.flush()

        logger.warning("Factory %s: buffer RED — rope limit bypassed", factory_id)

    return filtered
