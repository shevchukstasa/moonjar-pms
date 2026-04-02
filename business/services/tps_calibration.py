"""
TPS Auto-Calibration Service.

Uses Exponential Moving Average (EMA) of actual production rates
from TpsShiftMetric to detect drift and adjust ProcessStep rates.

Algorithm:
  1. Query TpsShiftMetric for last N days for a specific stage
  2. Calculate actual rate per shift: actual_output / (shift_hours)
  3. Apply EMA with alpha=0.3 (30% weight to newest data)
  4. If |EMA - planned_rate| / planned_rate > threshold (15%):
     - auto_calibrate=true -> update rate + log + return adjustment
     - auto_calibrate=false -> return suggestion only
"""

import logging
from datetime import date, datetime, timedelta, timezone as tz
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from api.models import CalibrationLog, ProcessStep, TpsShiftMetric

logger = logging.getLogger("moonjar.tps_calibration")

# Default shift duration in hours (8h per shift)
SHIFT_HOURS = 8.0
# EMA smoothing factor — 0.3 = 30% weight to newest data
DEFAULT_ALPHA = 0.3
# Drift threshold — trigger calibration if actual differs by >15%
DEFAULT_THRESHOLD = 0.15
# Minimum data points needed before calibration is considered
MIN_DATA_POINTS = 7


def calculate_ema_rate(
    db: Session,
    factory_id: UUID,
    step: ProcessStep,
    lookback_days: int = 30,
    alpha: float = DEFAULT_ALPHA,
) -> tuple[Optional[float], int]:
    """Calculate EMA of actual production rate from TpsShiftMetric.

    Returns (ema_rate, data_point_count). ema_rate is None if no data.
    """
    cutoff = date.today() - timedelta(days=lookback_days)

    metrics = (
        db.query(TpsShiftMetric)
        .filter(
            TpsShiftMetric.factory_id == factory_id,
            TpsShiftMetric.stage == step.stage,
            TpsShiftMetric.date >= cutoff,
            TpsShiftMetric.actual_output.isnot(None),
            TpsShiftMetric.actual_output > 0,
        )
        .order_by(TpsShiftMetric.date.asc(), TpsShiftMetric.shift.asc())
        .all()
    )

    if not metrics:
        return None, 0

    # Calculate rate per metric: actual_output / SHIFT_HOURS
    # This gives sqm/hour or pcs/hour depending on what's tracked
    ema = None
    count = 0

    for m in metrics:
        output = float(m.actual_output)
        # Use actual_output_pcs if the step measures in pcs
        if step.productivity_unit and "pcs" in step.productivity_unit:
            output = float(m.actual_output_pcs) if m.actual_output_pcs else output

        rate = output / SHIFT_HOURS

        if ema is None:
            ema = rate
        else:
            ema = alpha * rate + (1 - alpha) * ema
        count += 1

    return ema, count


def check_calibration_needed(
    db: Session,
    factory_id: UUID,
    step: ProcessStep,
    threshold: float = DEFAULT_THRESHOLD,
    min_data_points: int = MIN_DATA_POINTS,
) -> Optional[dict]:
    """Check if a ProcessStep needs calibration.

    Returns suggestion dict or None.
    """
    if not step.productivity_rate or float(step.productivity_rate) <= 0:
        return None

    ema, count = calculate_ema_rate(db, factory_id, step)

    if ema is None or count < min_data_points:
        return None

    planned = float(step.productivity_rate)
    drift = (ema - planned) / planned

    if abs(drift) <= threshold:
        return None

    return {
        "step_id": str(step.id),
        "step_name": step.name,
        "stage": step.stage,
        "current_rate": planned,
        "suggested_rate": round(ema, 2),
        "ema_value": round(ema, 2),
        "drift_percent": round(drift * 100, 1),
        "data_points": count,
        "auto_calibrate": step.auto_calibrate,
    }


def run_calibration(
    db: Session,
    factory_id: UUID,
    auto_apply: bool = False,
) -> list[dict]:
    """Run calibration for all active ProcessSteps in a factory.

    Returns list of suggestions/adjustments.
    """
    steps = (
        db.query(ProcessStep)
        .filter(
            ProcessStep.factory_id == factory_id,
            ProcessStep.is_active == True,  # noqa: E712
            ProcessStep.stage.isnot(None),
            ProcessStep.productivity_rate.isnot(None),
        )
        .all()
    )

    results = []
    for step in steps:
        suggestion = check_calibration_needed(db, factory_id, step)
        if not suggestion:
            continue

        if step.auto_calibrate and auto_apply:
            apply_calibration(
                db,
                step.id,
                suggestion["suggested_rate"],
                ema_value=suggestion["ema_value"],
                data_points=suggestion["data_points"],
                trigger="auto",
            )
            suggestion["applied"] = True
            logger.info(
                "AUTO_CALIBRATE | step=%s stage=%s | rate: %.2f -> %.2f (drift: %.1f%%)",
                step.name,
                step.stage,
                suggestion["current_rate"],
                suggestion["suggested_rate"],
                suggestion["drift_percent"],
            )
        else:
            suggestion["applied"] = False

        results.append(suggestion)

    return results


def apply_calibration(
    db: Session,
    step_id: UUID,
    new_rate: float,
    approved_by: UUID | None = None,
    ema_value: float | None = None,
    data_points: int = 0,
    trigger: str = "manual",
) -> None:
    """Apply calibration: update rate + log."""
    step = db.query(ProcessStep).filter(ProcessStep.id == step_id).first()
    if not step:
        return

    old_rate = float(step.productivity_rate) if step.productivity_rate else 0

    log = CalibrationLog(
        factory_id=step.factory_id,
        process_step_id=step.id,
        previous_rate=Decimal(str(old_rate)),
        new_rate=Decimal(str(new_rate)),
        ema_value=Decimal(str(ema_value)) if ema_value else None,
        data_points=data_points,
        trigger=trigger,
        approved_by=approved_by,
    )
    db.add(log)

    step.productivity_rate = Decimal(str(new_rate))
    step.calibration_ema = Decimal(str(ema_value)) if ema_value else None
    step.last_calibrated_at = datetime.now(tz.utc)

    db.flush()


def get_calibration_status(
    db: Session,
    factory_id: UUID,
) -> list[dict]:
    """Get current calibration status for all steps in a factory.

    Returns list of step statuses with drift info.
    """
    steps = (
        db.query(ProcessStep)
        .filter(
            ProcessStep.factory_id == factory_id,
            ProcessStep.is_active == True,  # noqa: E712
            ProcessStep.stage.isnot(None),
        )
        .order_by(ProcessStep.sequence)
        .all()
    )

    results = []
    for step in steps:
        ema, count = calculate_ema_rate(db, factory_id, step)
        planned = float(step.productivity_rate) if step.productivity_rate else None

        drift = None
        if ema and planned and planned > 0:
            drift = round((ema - planned) / planned * 100, 1)

        results.append({
            "step_id": str(step.id),
            "step_name": step.name,
            "stage": step.stage,
            "planned_rate": planned,
            "actual_rate_7d": round(ema, 2) if ema else None,
            "drift_percent": drift,
            "data_points": count,
            "auto_calibrate": step.auto_calibrate,
            "last_calibrated_at": (
                step.last_calibrated_at.isoformat()
                if step.last_calibrated_at
                else None
            ),
            "productivity_unit": step.productivity_unit,
        })

    return results
