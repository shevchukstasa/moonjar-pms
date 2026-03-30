"""
Weekly Summary Card for Telegram.
Generates and sends a rich weekly report per factory.

Sent every Sunday at 20:00 UTC (Monday 04:00 Bali).
"""

import logging
from datetime import date, timedelta, timezone, datetime
from uuid import UUID
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func, cast, Date

from api.models import (
    ProductionOrder, OrderPosition, Batch, DefectRecord,
    QualityCheck, Factory, User, UserFactory,
)
from api.enums import (
    OrderStatus, PositionStatus, BatchStatus, QcResult, UserRole,
)
from business.services.notifications import send_telegram_message

logger = logging.getLogger("moonjar.weekly_summary")


def generate_weekly_summary(db: Session, factory_id: UUID) -> str:
    """Generate a rich weekly summary message for a factory.

    Covers the last 7 days: Mon-Sun (or partial if called mid-week).
    """
    today = date.today()
    week_start = today - timedelta(days=7)
    week_end = today - timedelta(days=1)

    factory = db.query(Factory).filter(Factory.id == factory_id).first()
    factory_name = factory.name if factory else "Unknown"

    # Previous week for delta comparison
    prev_start = week_start - timedelta(days=7)
    prev_end = week_start - timedelta(days=1)

    # ── 1. Orders shipped this week ──
    shipped_this = _count_shipped(db, factory_id, week_start, week_end)
    shipped_prev = _count_shipped(db, factory_id, prev_start, prev_end)
    shipped_delta = shipped_this - shipped_prev

    # ── 2. Positions completed (reached READY_FOR_SHIPMENT or SHIPPED) ──
    completed_this = _count_completed_positions(db, factory_id, week_start, week_end)

    # ── 3. Firings + kiln utilization ──
    firings_this = _count_firings(db, factory_id, week_start, week_end)
    kiln_util = _avg_kiln_utilization(db, factory_id, week_start, week_end)

    # ── 4. Defect rate ──
    defect_rate = _calc_defect_rate(db, factory_id, week_start, week_end)

    # ── 5. On-time % ──
    on_time_pct = _calc_on_time_pct(db, factory_id, week_start, week_end)

    # ── 6. Best master (most positions completed) ──
    best_master_name, best_master_count = _find_best_master(
        db, factory_id, week_start, week_end,
    )

    # ── Build message ──
    delta_str = f"+{shipped_delta}" if shipped_delta >= 0 else str(shipped_delta)

    lines = [
        f"\U0001F4CA Недельный отчёт: {factory_name}",
        "\u2500" * 25,
        f"\U0001F4E6 Заказов отгружено: {shipped_this} ({delta_str} vs прошлая неделя)",
        f"\u2705 Позиций завершено: {completed_this}",
        f"\U0001F525 Обжигов: {firings_this} | Утилизация: {kiln_util:.0f}%",
        f"\U0001F6A8 Дефект-рейт: {defect_rate:.1f}% (цель: <5%)",
        f"\u23F0 Вовремя: {on_time_pct:.0f}%",
    ]

    if best_master_name:
        lines.append(f"\U0001F3C6 Лучший мастер: {best_master_name} ({best_master_count} позиций)")

    lines.append("\u2500" * 25)

    # Mood indicator
    if defect_rate < 3 and on_time_pct >= 95:
        lines.append("Отличная неделя! \U0001F4AA")
    elif defect_rate < 5 and on_time_pct >= 85:
        lines.append("Хорошая неделя! \U0001F44D")
    else:
        lines.append("Есть над чем поработать. \U0001F4AD")

    return "\n".join(lines)


def send_weekly_summary(db: Session, factory_id: UUID) -> int:
    """Generate and send the weekly summary to PM + CEO users.

    Returns number of messages sent.
    """
    message = generate_weekly_summary(db, factory_id)
    sent = 0

    # Find PM, CEO, Owner users with telegram
    users = (
        db.query(User)
        .join(UserFactory, UserFactory.user_id == User.id)
        .filter(
            UserFactory.factory_id == factory_id,
            User.role.in_([
                UserRole.PRODUCTION_MANAGER.value,
                UserRole.CEO.value,
                UserRole.OWNER.value,
            ]),
            User.is_active.is_(True),
            User.telegram_user_id.isnot(None),
        )
        .all()
    )

    for user in users:
        try:
            send_telegram_message(str(user.telegram_user_id), message)
            sent += 1
        except Exception as e:
            logger.warning("Failed to send weekly summary to user %s: %s", user.id, e)

    logger.info(
        "Weekly summary sent for factory %s: %d recipients",
        factory_id, sent,
    )
    return sent


# ── Helper queries ─────────────────────────────────────────────


def _count_shipped(db: Session, factory_id: UUID, d_from: date, d_to: date) -> int:
    return db.query(sa_func.count(ProductionOrder.id)).filter(
        ProductionOrder.factory_id == factory_id,
        ProductionOrder.status == OrderStatus.SHIPPED.value,
        ProductionOrder.shipped_at.isnot(None),
        cast(ProductionOrder.shipped_at, Date) >= d_from,
        cast(ProductionOrder.shipped_at, Date) <= d_to,
    ).scalar() or 0


def _count_completed_positions(db: Session, factory_id: UUID, d_from: date, d_to: date) -> int:
    return db.query(sa_func.count(OrderPosition.id)).filter(
        OrderPosition.factory_id == factory_id,
        OrderPosition.status.in_([
            PositionStatus.READY_FOR_SHIPMENT.value,
            PositionStatus.SHIPPED.value,
        ]),
        cast(OrderPosition.updated_at, Date) >= d_from,
        cast(OrderPosition.updated_at, Date) <= d_to,
    ).scalar() or 0


def _count_firings(db: Session, factory_id: UUID, d_from: date, d_to: date) -> int:
    return db.query(sa_func.count(Batch.id)).filter(
        Batch.factory_id == factory_id,
        Batch.status == BatchStatus.DONE.value,
        cast(Batch.updated_at, Date) >= d_from,
        cast(Batch.updated_at, Date) <= d_to,
    ).scalar() or 0


def _avg_kiln_utilization(db: Session, factory_id: UUID, d_from: date, d_to: date) -> float:
    """Average kiln utilization % via the planning engine."""
    try:
        from business.services.daily_kpi import calculate_kiln_utilization
        period_days = max(1, (d_to - d_from).days)
        return calculate_kiln_utilization(db, factory_id, d_from, d_to)
    except Exception:
        return 0.0


def _calc_defect_rate(db: Session, factory_id: UUID, d_from: date, d_to: date) -> float:
    defect_qty = db.query(sa_func.sum(DefectRecord.quantity)).filter(
        DefectRecord.factory_id == factory_id,
        DefectRecord.date >= d_from,
        DefectRecord.date <= d_to,
    ).scalar() or 0

    total_checked = db.query(sa_func.count(QualityCheck.id)).filter(
        QualityCheck.factory_id == factory_id,
        cast(QualityCheck.created_at, Date) >= d_from,
        cast(QualityCheck.created_at, Date) <= d_to,
    ).scalar() or 0

    if total_checked == 0:
        return 0.0
    return (float(defect_qty) / float(total_checked)) * 100


def _calc_on_time_pct(db: Session, factory_id: UUID, d_from: date, d_to: date) -> float:
    shipped = db.query(ProductionOrder).filter(
        ProductionOrder.factory_id == factory_id,
        ProductionOrder.status == OrderStatus.SHIPPED.value,
        ProductionOrder.shipped_at.isnot(None),
        cast(ProductionOrder.shipped_at, Date) >= d_from,
        cast(ProductionOrder.shipped_at, Date) <= d_to,
    ).all()

    if not shipped:
        return 100.0

    on_time = sum(
        1 for o in shipped
        if o.final_deadline and o.shipped_at and o.shipped_at.date() <= o.final_deadline
    )
    return (on_time / len(shipped)) * 100


def _find_best_master(
    db: Session, factory_id: UUID, d_from: date, d_to: date,
) -> tuple[Optional[str], int]:
    """Find the master who completed the most positions this week.

    Looks at positions that moved to a terminal status (READY_FOR_SHIPMENT/SHIPPED)
    and tries to identify the user who last updated them.
    Returns (name, count) or (None, 0).
    """
    # Use OperationLog if available, otherwise fall back to simple count
    try:
        from sqlalchemy import literal_column
        # Count positions completed per user via updated_by
        results = (
            db.query(
                OrderPosition.updated_by,
                sa_func.count(OrderPosition.id).label("cnt"),
            )
            .filter(
                OrderPosition.factory_id == factory_id,
                OrderPosition.status.in_([
                    PositionStatus.READY_FOR_SHIPMENT.value,
                    PositionStatus.SHIPPED.value,
                ]),
                cast(OrderPosition.updated_at, Date) >= d_from,
                cast(OrderPosition.updated_at, Date) <= d_to,
                OrderPosition.updated_by.isnot(None),
            )
            .group_by(OrderPosition.updated_by)
            .order_by(sa_func.count(OrderPosition.id).desc())
            .first()
        )
        if results and results[0]:
            user = db.query(User).filter(User.id == results[0]).first()
            if user:
                return user.name, results[1]
    except Exception:
        pass

    return None, 0
