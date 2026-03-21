"""
TPS Lean Metrics service.
Business Logic: §23
"""
from uuid import UUID
from datetime import date, timedelta
from typing import Optional
import logging

from sqlalchemy.orm import Session

from api.models import (
    TpsShiftMetric, TpsDeviation, TpsParameter,
    Notification, User, ProductionOrder, OrderPosition,
)
from api.enums import (
    TpsDeviationType, TpsStatus, NotificationType,
    UserRole, OrderStatus, PositionStatus,
)

logger = logging.getLogger("moonjar.tps_metrics")

# Default shift duration in minutes (8 hours)
DEFAULT_SHIFT_MINUTES = 480


def _get_daily_demand_sqm(db: Session, factory_id: UUID, stage: str) -> float:
    """Calculate customer demand rate for takt time.

    Based on total ordered m² with deadline within next 30 days.
    """
    upcoming_orders = db.query(ProductionOrder).filter(
        ProductionOrder.factory_id == factory_id,
        ProductionOrder.status.in_([
            OrderStatus.IN_PRODUCTION.value,
            OrderStatus.PARTIALLY_READY.value,
        ]),
        ProductionOrder.final_deadline <= date.today() + timedelta(days=30),
    ).all()

    total_sqm = 0.0
    for order in upcoming_orders:
        positions = db.query(OrderPosition).filter(
            OrderPosition.order_id == order.id,
            OrderPosition.status.notin_([
                PositionStatus.CANCELLED.value,
                PositionStatus.READY_FOR_SHIPMENT.value,
                PositionStatus.SHIPPED.value,
            ]),
        ).all()
        total_sqm += sum(float(p.quantity_sqm or 0) for p in positions)

    return total_sqm / 30.0 if total_sqm > 0 else 0.0


def _get_pm_user_id(db: Session, factory_id: UUID) -> Optional[UUID]:
    """Get production manager user ID."""
    from api.models import UserFactory
    uf = db.query(UserFactory).join(User).filter(
        UserFactory.factory_id == factory_id,
        User.role == UserRole.PRODUCTION_MANAGER.value,
        User.is_active.is_(True),
    ).first()
    return uf.user_id if uf else None


def collect_shift_metrics(db: Session, factory_id: UUID, shift_date: date) -> dict:
    """Collect TPS metrics for a shift."""
    metrics = db.query(TpsShiftMetric).filter(
        TpsShiftMetric.factory_id == factory_id,
        TpsShiftMetric.date == shift_date,
    ).all()

    if not metrics:
        return {
            "date": str(shift_date),
            "factory_id": str(factory_id),
            "shifts": [],
            "totals": {
                "output_sqm": 0,
                "output_pcs": 0,
                "avg_oee": 0,
                "avg_defect_rate": 0,
            },
        }

    shifts = {}
    for m in metrics:
        shift_num = m.shift
        if shift_num not in shifts:
            shifts[shift_num] = []
        shifts[shift_num].append({
            "stage": m.stage,
            "planned_output": float(m.planned_output or 0),
            "actual_output": float(m.actual_output or 0),
            "actual_output_pcs": int(m.actual_output_pcs or 0),
            "deviation_percent": float(m.deviation_percent or 0),
            "defect_rate": float(m.defect_rate or 0),
            "downtime_minutes": float(m.downtime_minutes or 0),
            "cycle_time_minutes": float(m.cycle_time_minutes or 0),
            "oee_percent": float(m.oee_percent or 0),
            "takt_time_minutes": float(m.takt_time_minutes or 0),
            "status": m.status if isinstance(m.status, str) else m.status.value,
        })

    total_output = sum(float(m.actual_output or 0) for m in metrics)
    total_pcs = sum(int(m.actual_output_pcs or 0) for m in metrics)
    avg_oee = sum(float(m.oee_percent or 0) for m in metrics) / len(metrics) if metrics else 0
    avg_defect = sum(float(m.defect_rate or 0) for m in metrics) / len(metrics) if metrics else 0

    return {
        "date": str(shift_date),
        "factory_id": str(factory_id),
        "shifts": [
            {"shift": k, "stages": v}
            for k, v in sorted(shifts.items())
        ],
        "totals": {
            "output_sqm": round(total_output, 2),
            "output_pcs": total_pcs,
            "avg_oee": round(avg_oee, 1),
            "avg_defect_rate": round(avg_defect, 1),
        },
    }


def record_shift_metric(
    db: Session,
    factory_id: UUID,
    shift: int,
    metric_date: date,
    stage: str,
    planned_output: float,
    actual_output: float,
    actual_output_pcs: int,
    defect_count: int = 0,
    downtime_minutes: float = 0,
    available_minutes: float = DEFAULT_SHIFT_MINUTES,
) -> dict:
    """Record comprehensive shift metrics. Called at end of each shift."""
    # Calculate derived metrics
    defect_rate = (defect_count / actual_output_pcs * 100) if actual_output_pcs > 0 else 0
    cycle_time = ((available_minutes - downtime_minutes) / actual_output_pcs) if actual_output_pcs > 0 else 0
    deviation_percent = (
        ((actual_output - planned_output) / planned_output * 100)
        if planned_output > 0 else 0
    )

    # OEE = Availability × Performance × Quality
    availability = (
        (available_minutes - downtime_minutes) / available_minutes
        if available_minutes > 0 else 0
    )
    performance = actual_output / planned_output if planned_output > 0 else 0
    quality = (
        (actual_output_pcs - defect_count) / actual_output_pcs
        if actual_output_pcs > 0 else 0
    )
    oee = availability * performance * quality * 100

    # Takt time
    daily_demand = _get_daily_demand_sqm(db, factory_id, stage)
    takt_time = (
        (available_minutes - downtime_minutes) / daily_demand
        if daily_demand > 0 else 0
    )

    # Status classification
    if abs(deviation_percent) <= 5:
        status = TpsStatus.NORMAL
    elif abs(deviation_percent) <= 15:
        status = TpsStatus.WARNING
    else:
        status = TpsStatus.CRITICAL

    # Upsert metric
    existing = db.query(TpsShiftMetric).filter(
        TpsShiftMetric.factory_id == factory_id,
        TpsShiftMetric.shift == shift,
        TpsShiftMetric.date == metric_date,
        TpsShiftMetric.stage == stage,
    ).first()

    if existing:
        existing.planned_output = planned_output
        existing.actual_output = actual_output
        existing.actual_output_pcs = actual_output_pcs
        existing.deviation_percent = round(deviation_percent, 2)
        existing.defect_rate = round(defect_rate, 2)
        existing.downtime_minutes = downtime_minutes
        existing.cycle_time_minutes = round(cycle_time, 2)
        existing.oee_percent = round(oee, 2)
        existing.takt_time_minutes = round(takt_time, 2)
        existing.status = status
        metric = existing
    else:
        metric = TpsShiftMetric(
            factory_id=factory_id,
            shift=shift,
            date=metric_date,
            stage=stage,
            planned_output=planned_output,
            actual_output=actual_output,
            actual_output_pcs=actual_output_pcs,
            deviation_percent=round(deviation_percent, 2),
            defect_rate=round(defect_rate, 2),
            downtime_minutes=downtime_minutes,
            cycle_time_minutes=round(cycle_time, 2),
            oee_percent=round(oee, 2),
            takt_time_minutes=round(takt_time, 2),
            status=status,
        )
        db.add(metric)

    # Create deviation record if critical
    if status == TpsStatus.CRITICAL:
        deviation = TpsDeviation(
            factory_id=factory_id,
            shift=shift,
            stage=stage,
            deviation_type=(
                TpsDeviationType.NEGATIVE if deviation_percent < 0
                else TpsDeviationType.POSITIVE
            ),
            description=(
                f"Deviation {deviation_percent:+.1f}% from plan at {stage}"
            ),
            severity="high",
        )
        db.add(deviation)

        pm_user_id = _get_pm_user_id(db, factory_id)
        if pm_user_id:
            notif = Notification(
                user_id=pm_user_id,
                factory_id=factory_id,
                type=NotificationType.ALERT,
                title=f"Critical deviation at {stage}, shift {shift}",
                message=(
                    f"Planned: {planned_output}, Actual: {actual_output} "
                    f"({deviation_percent:+.1f}%). OEE: {oee:.1f}%"
                ),
            )
            db.add(notif)

    db.flush()

    return {
        "status": status.value,
        "deviation_percent": round(deviation_percent, 2),
        "oee_percent": round(oee, 2),
        "defect_rate": round(defect_rate, 2),
        "cycle_time_minutes": round(cycle_time, 2),
        "takt_time_minutes": round(takt_time, 2),
    }


def evaluate_signal(db: Session, factory_id: UUID) -> str:
    """Signal system: green/red based on targets."""
    today = date.today()

    # Get today's metrics
    metrics = db.query(TpsShiftMetric).filter(
        TpsShiftMetric.factory_id == factory_id,
        TpsShiftMetric.date == today,
    ).all()

    if not metrics:
        return "green"  # No data = no alarm

    # Check for any critical status
    critical_count = sum(
        1 for m in metrics
        if (m.status if isinstance(m.status, str) else m.status.value) == TpsStatus.CRITICAL.value
    )

    warning_count = sum(
        1 for m in metrics
        if (m.status if isinstance(m.status, str) else m.status.value) == TpsStatus.WARNING.value
    )

    if critical_count > 0:
        return "red"
    elif warning_count > len(metrics) * 0.5:
        return "red"  # More than half warnings = red
    elif warning_count > 0:
        return "yellow"
    return "green"
