"""
Pull System — Event-Driven Work Pulling (TOC Rope mechanism).

When a position completes a stage, checks if there's remaining capacity today
and automatically pulls the next position forward from tomorrow/later.

Also awards Speed Bonus points when daily throughput exceeds average.
"""

import logging
from datetime import date, timedelta
from uuid import UUID
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func

from api.models import OrderPosition, ProductionOrder, Resource
from api.enums import PositionStatus, OrderStatus

logger = logging.getLogger("moonjar.pull_system")

# ── Stage completion statuses → which planned date field to check ──
# When a position reaches one of these statuses, we check capacity for that stage
_STAGE_COMPLETION_MAP = {
    # Glazing stage completions
    PositionStatus.GLAZED.value: "planned_glazing_date",
    PositionStatus.ENGOBE_APPLIED.value: "planned_glazing_date",
    PositionStatus.PRE_KILN_CHECK.value: "planned_glazing_date",
    # Firing completion
    PositionStatus.FIRED.value: "planned_kiln_date",
    # Sorting completion
    PositionStatus.PACKED.value: "planned_sorting_date",
    PositionStatus.QUALITY_CHECK_DONE.value: "planned_sorting_date",
}

# Statuses that mean "still working on this stage" (not pulled yet)
_GLAZING_ACTIVE = {
    PositionStatus.SENT_TO_GLAZING.value,
    PositionStatus.PLANNED.value,
    PositionStatus.ENGOBE_APPLIED.value,
    PositionStatus.ENGOBE_CHECK.value,
}

_FIRING_ACTIVE = {
    PositionStatus.LOADED_IN_KILN.value,
    PositionStatus.PRE_KILN_CHECK.value,
}

_SORTING_ACTIVE = {
    PositionStatus.TRANSFERRED_TO_SORTING.value,
    PositionStatus.SENT_TO_QUALITY_CHECK.value,
}


def try_pull_next_work(
    db: Session,
    completed_position: OrderPosition,
    new_status: str,
    changed_by: UUID,
) -> list[dict]:
    """
    After a position completes a stage, check if there's capacity
    to pull the next position forward to today.

    Returns list of pulled positions info for logging/notification.
    """
    date_field = _STAGE_COMPLETION_MAP.get(new_status)
    if not date_field:
        return []

    today = date.today()
    factory_id = completed_position.factory_id
    if not factory_id:
        return []

    try:
        pulled = _pull_for_stage(db, factory_id, date_field, today, changed_by)
        if pulled:
            _award_speed_bonus(db, factory_id, date_field, today, changed_by)
        return pulled
    except Exception as e:
        logger.error("Pull system error: %s", e, exc_info=True)
        return []


def _pull_for_stage(
    db: Session,
    factory_id: UUID,
    date_field: str,
    today: date,
    changed_by: UUID,
) -> list[dict]:
    """Check capacity for today and pull next positions forward."""
    # 1. Get today's capacity for this stage
    daily_cap = _get_daily_capacity(db, factory_id, date_field, today)
    if daily_cap <= 0:
        return []

    # 2. Get today's current load (sum of all positions scheduled for today)
    today_load = _get_day_load(db, factory_id, date_field, today)

    # 3. Check remaining capacity
    remaining = daily_cap - today_load
    if remaining <= 0:
        logger.debug(
            "PULL_NO_CAPACITY | factory=%s stage=%s | load=%.2f cap=%.2f",
            factory_id, date_field, today_load, daily_cap,
        )
        return []

    # 4. Find candidates from tomorrow onwards (sorted by priority, then date)
    date_col = getattr(OrderPosition, date_field)
    candidates = (
        db.query(OrderPosition)
        .join(ProductionOrder)
        .filter(
            OrderPosition.factory_id == factory_id,
            date_col > today,
            date_col <= today + timedelta(days=7),  # look ahead max 7 days
            ProductionOrder.status.in_([
                OrderStatus.NEW.value,
                OrderStatus.IN_PRODUCTION.value,
                OrderStatus.PARTIALLY_READY.value,
            ]),
            OrderPosition.status.notin_([
                PositionStatus.CANCELLED.value,
                PositionStatus.SHIPPED.value,
                PositionStatus.READY_FOR_SHIPMENT.value,
                PositionStatus.PACKED.value,
            ]),
        )
        .order_by(
            OrderPosition.priority_order.asc().nullslast(),
            date_col.asc(),
            ProductionOrder.final_deadline.asc().nullslast(),
        )
        .all()
    )

    if not candidates:
        return []

    # 5. Pull positions until capacity is filled
    pulled = []
    for pos in candidates:
        pos_area = float(pos.glazeable_sqm or 0) * float(pos.quantity or 1)
        if pos_area <= 0:
            pos_area = 0.1  # minimal area for non-tile items

        if pos_area > remaining:
            continue  # skip if doesn't fit

        old_date = getattr(pos, date_field)
        setattr(pos, date_field, today)

        # If pulling glazing forward, also adjust downstream dates
        if date_field == "planned_glazing_date":
            _adjust_downstream_dates(pos, today)

        remaining -= pos_area
        pulled.append({
            "position_id": str(pos.id),
            "order_number": pos.order.order_number if pos.order else "?",
            "color": pos.color or "",
            "area_sqm": pos_area,
            "old_date": str(old_date),
            "new_date": str(today),
        })

        logger.info(
            "PULLED_FORWARD | pos=%s order=%s | %s: %s → %s | area=%.2f remaining=%.2f",
            pos.id,
            pos.order.order_number if pos.order else "?",
            date_field, old_date, today, pos_area, remaining,
        )

        if remaining <= 0:
            break

    if pulled:
        db.flush()
        _notify_pm_about_pull(db, factory_id, pulled, date_field)

    return pulled


def _get_daily_capacity(
    db: Session,
    factory_id: UUID,
    date_field: str,
    on_date: date,
) -> float:
    """Get daily capacity for a stage at a factory."""
    if date_field == "planned_glazing_date":
        # Glazing capacity = kiln firing capacity (TOC: glazing feeds kiln)
        kilns = db.query(Resource).filter(
            Resource.factory_id == factory_id,
            Resource.resource_type == "kiln",
            Resource.status == "operational",
        ).all()
        if kilns:
            return sum(float(k.capacity_sqm or 0) for k in kilns)
        return 10.0  # fallback

    elif date_field == "planned_kiln_date":
        # Kiln capacity — sum of all operational kilns
        kilns = db.query(Resource).filter(
            Resource.factory_id == factory_id,
            Resource.resource_type == "kiln",
            Resource.status == "operational",
        ).all()
        return sum(float(k.capacity_sqm or 0) for k in kilns)

    elif date_field == "planned_sorting_date":
        # Sorting: typically unlimited compared to kiln
        return 50.0  # generous default

    return 10.0


def _get_day_load(
    db: Session,
    factory_id: UUID,
    date_field: str,
    on_date: date,
) -> float:
    """Sum of all positions' area scheduled for a given date and stage."""
    date_col = getattr(OrderPosition, date_field)
    result = (
        db.query(
            sa_func.coalesce(
                sa_func.sum(OrderPosition.glazeable_sqm * OrderPosition.quantity),
                0,
            )
        )
        .filter(
            OrderPosition.factory_id == factory_id,
            date_col == on_date,
            OrderPosition.status != PositionStatus.CANCELLED.value,
        )
        .scalar()
    )
    return float(result or 0)


def _adjust_downstream_dates(pos: OrderPosition, new_glazing_date: date) -> None:
    """When glazing is pulled forward, adjust kiln/sorting/completion forward too."""
    if not pos.planned_kiln_date or not pos.planned_glazing_date:
        return

    # Calculate original gaps between stages
    old_glaze = pos.planned_glazing_date
    if old_glaze == new_glazing_date:
        return

    delta = old_glaze - new_glazing_date  # positive = pulled earlier
    if delta.days <= 0:
        return

    # Pull downstream dates forward by the same delta (but never earlier than today)
    today = date.today()
    if pos.planned_kiln_date:
        new_kiln = pos.planned_kiln_date - delta
        pos.planned_kiln_date = max(new_kiln, today)
    if pos.planned_sorting_date:
        new_sort = pos.planned_sorting_date - delta
        pos.planned_sorting_date = max(new_sort, today)
    if pos.planned_completion_date:
        new_comp = pos.planned_completion_date - delta
        pos.planned_completion_date = max(new_comp, today)


def _notify_pm_about_pull(
    db: Session,
    factory_id: UUID,
    pulled: list[dict],
    date_field: str,
) -> None:
    """Send notification to PMs about auto-pulled positions."""
    from api.models import Notification, User, UserFactory
    from api.enums import NotificationType, UserRole

    stage_name = {
        "planned_glazing_date": "Glazing",
        "planned_kiln_date": "Firing",
        "planned_sorting_date": "Sorting",
    }.get(date_field, "Production")

    details = ", ".join(
        f"{p['order_number']} ({p['color']}, {p['area_sqm']:.1f}m\u00b2)"
        for p in pulled[:5]
    )
    if len(pulled) > 5:
        details += f" +{len(pulled) - 5} more"

    pm_ids = [
        uf.user_id for uf in db.query(UserFactory).join(User).filter(
            UserFactory.factory_id == factory_id,
            User.role.in_([UserRole.PRODUCTION_MANAGER.value, UserRole.CEO.value]),
            User.is_active.is_(True),
        ).all()
    ]

    for uid in pm_ids:
        db.add(Notification(
            user_id=uid,
            type=NotificationType.SYSTEM.value,
            title=f"{stage_name}: {len(pulled)} position(s) pulled forward",
            message=f"Capacity available — auto-pulled to today: {details}",
            data={"event": "pull_forward", "stage": date_field, "positions": pulled},
        ))


def _award_speed_bonus(
    db: Session,
    factory_id: UUID,
    date_field: str,
    today: date,
    changed_by: UUID,
) -> None:
    """
    Award speed bonus points when daily throughput exceeds average.

    Compares today's completed area vs 7-day rolling average.
    If today > avg * 1.2 (20% above average) → bonus points.
    """
    try:
        from business.services.points_system import award_points
    except ImportError:
        return

    # Calculate today's completed area for this stage
    stage_done_statuses = _get_done_statuses_for_stage(date_field)
    if not stage_done_statuses:
        return

    today_completed = float(
        db.query(
            sa_func.coalesce(
                sa_func.sum(OrderPosition.glazeable_sqm * OrderPosition.quantity),
                0,
            )
        )
        .filter(
            OrderPosition.factory_id == factory_id,
            getattr(OrderPosition, date_field) == today,
            OrderPosition.status.in_(stage_done_statuses),
        )
        .scalar() or 0
    )

    if today_completed <= 0:
        return

    # Calculate 7-day average (excluding today)
    date_col = getattr(OrderPosition, date_field)
    week_ago = today - timedelta(days=7)
    week_total = float(
        db.query(
            sa_func.coalesce(
                sa_func.sum(OrderPosition.glazeable_sqm * OrderPosition.quantity),
                0,
            )
        )
        .filter(
            OrderPosition.factory_id == factory_id,
            date_col >= week_ago,
            date_col < today,
            OrderPosition.status.in_(stage_done_statuses),
        )
        .scalar() or 0
    )

    # Count working days in the past 7 days (rough: exclude Sundays)
    working_days = sum(
        1 for d in range(1, 8)
        if (today - timedelta(days=d)).weekday() != 6  # not Sunday
    )
    avg_daily = week_total / max(working_days, 1)

    if avg_daily <= 0:
        return

    ratio = today_completed / avg_daily

    # Award bonus if 20%+ above average
    if ratio >= 1.2:
        stage_label = {
            "planned_glazing_date": "glazing",
            "planned_kiln_date": "firing",
            "planned_sorting_date": "sorting",
        }.get(date_field, "production")

        # Points scale: 20% above = 3pts, 50% = 5pts, 100%+ = 10pts
        if ratio >= 2.0:
            bonus = 10
        elif ratio >= 1.5:
            bonus = 5
        else:
            bonus = 3

        pct_above = int((ratio - 1) * 100)

        award_points(
            db=db,
            user_id=changed_by,
            factory_id=factory_id,
            points=bonus,
            reason=f"speed_bonus_{stage_label}",
            details={
                "stage": stage_label,
                "today_sqm": round(today_completed, 2),
                "avg_daily_sqm": round(avg_daily, 2),
                "pct_above_avg": pct_above,
                "date": str(today),
            },
        )

        logger.info(
            "SPEED_BONUS | user=%s factory=%s | %s: %.1fm\u00b2 today vs %.1fm\u00b2 avg "
            "(+%d%%) | +%d pts",
            changed_by, factory_id, stage_label,
            today_completed, avg_daily, pct_above, bonus,
        )


def _get_done_statuses_for_stage(date_field: str) -> list[str]:
    """Return statuses that mean 'done' for a given stage."""
    if date_field == "planned_glazing_date":
        return [
            PositionStatus.GLAZED.value,
            PositionStatus.PRE_KILN_CHECK.value,
            PositionStatus.LOADED_IN_KILN.value,
            PositionStatus.FIRED.value,
            PositionStatus.TRANSFERRED_TO_SORTING.value,
            PositionStatus.PACKED.value,
            PositionStatus.QUALITY_CHECK_DONE.value,
            PositionStatus.READY_FOR_SHIPMENT.value,
            PositionStatus.SHIPPED.value,
        ]
    elif date_field == "planned_kiln_date":
        return [
            PositionStatus.FIRED.value,
            PositionStatus.TRANSFERRED_TO_SORTING.value,
            PositionStatus.PACKED.value,
            PositionStatus.QUALITY_CHECK_DONE.value,
            PositionStatus.READY_FOR_SHIPMENT.value,
            PositionStatus.SHIPPED.value,
        ]
    elif date_field == "planned_sorting_date":
        return [
            PositionStatus.PACKED.value,
            PositionStatus.QUALITY_CHECK_DONE.value,
            PositionStatus.READY_FOR_SHIPMENT.value,
            PositionStatus.SHIPPED.value,
        ]
    return []
