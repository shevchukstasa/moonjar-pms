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

from api.models import (
    CalibrationLog,
    ProcessStep,
    StageTypologySpeed,
    TpsShiftMetric,
)

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


# ═══════════════════════════════════════════════════════════════════
# Typology Speed Calibration
# ═══════════════════════════════════════════════════════════════════


def _calculate_typology_ema(
    db: Session,
    factory_id: UUID,
    stage: str,
    typology_id: UUID,
    rate_unit: str,
    lookback_days: int = 30,
    alpha: float = DEFAULT_ALPHA,
) -> tuple[Optional[float], int]:
    """Calculate EMA of actual production rate from TpsShiftMetric
    filtered by typology_id.

    Returns (ema_rate, data_point_count). ema_rate is None if no data.
    """
    cutoff = date.today() - timedelta(days=lookback_days)

    metrics = (
        db.query(TpsShiftMetric)
        .filter(
            TpsShiftMetric.factory_id == factory_id,
            TpsShiftMetric.stage == stage,
            TpsShiftMetric.typology_id == typology_id,
            TpsShiftMetric.date >= cutoff,
            TpsShiftMetric.actual_output.isnot(None),
            TpsShiftMetric.actual_output > 0,
        )
        .order_by(TpsShiftMetric.date.asc(), TpsShiftMetric.shift.asc())
        .all()
    )

    if not metrics:
        return None, 0

    ema = None
    count = 0

    for m in metrics:
        # Use pcs output if the speed record measures in pcs
        if rate_unit == "pcs" and m.actual_output_pcs:
            output = float(m.actual_output_pcs)
        else:
            output = float(m.actual_output)

        rate = output / SHIFT_HOURS

        if ema is None:
            ema = rate
        else:
            ema = alpha * rate + (1 - alpha) * ema
        count += 1

    return ema, count


def calibrate_typology_speeds(
    db: Session,
    factory_id: UUID,
    auto_apply: bool = True,
    threshold: float = DEFAULT_THRESHOLD,
    min_data_points: int = MIN_DATA_POINTS,
) -> list[dict]:
    """Run calibration for all auto-calibratable StageTypologySpeed records.

    Algorithm:
      1. Get all active StageTypologySpeed records with auto_calibrate=True
      2. For each, query TpsShiftMetric filtered by factory_id + stage +
         typology_id over the last 30 days
      3. Calculate EMA (alpha=0.3) from actual output
      4. Check drift (>15% threshold)
      5. If auto_calibrate: update calibration_ema and productivity_rate
      6. Log to CalibrationLog

    Returns list of suggestions/adjustments.
    """
    speeds = (
        db.query(StageTypologySpeed)
        .filter(
            StageTypologySpeed.factory_id == factory_id,
            StageTypologySpeed.auto_calibrate == True,  # noqa: E712
            StageTypologySpeed.productivity_rate.isnot(None),
        )
        .all()
    )

    results = []
    for speed in speeds:
        planned = float(speed.productivity_rate)
        if planned <= 0:
            continue

        ema, count = _calculate_typology_ema(
            db,
            factory_id=factory_id,
            stage=speed.stage,
            typology_id=speed.typology_id,
            rate_unit=speed.rate_unit or "pcs",
        )

        if ema is None or count < min_data_points:
            continue

        drift = (ema - planned) / planned

        if abs(drift) <= threshold:
            continue

        suggestion = {
            "speed_id": str(speed.id),
            "typology_id": str(speed.typology_id),
            "stage": speed.stage,
            "current_rate": planned,
            "suggested_rate": round(ema, 2),
            "ema_value": round(ema, 2),
            "drift_percent": round(drift * 100, 1),
            "data_points": count,
            "auto_calibrate": True,
            "applied": False,
        }

        if auto_apply:
            _apply_typology_calibration(
                db,
                speed=speed,
                new_rate=ema,
                ema_value=ema,
                data_points=count,
            )
            suggestion["applied"] = True
            logger.info(
                "TYPOLOGY_CALIBRATE | typology=%s stage=%s | rate: %.2f -> %.2f (drift: %.1f%%)",
                speed.typology_id,
                speed.stage,
                planned,
                ema,
                drift * 100,
            )

        results.append(suggestion)

    return results


def _apply_typology_calibration(
    db: Session,
    speed: StageTypologySpeed,
    new_rate: float,
    ema_value: float,
    data_points: int,
) -> None:
    """Apply calibration to a StageTypologySpeed record + log."""
    old_rate = float(speed.productivity_rate) if speed.productivity_rate else 0

    # Log to CalibrationLog (reuse same table, process_step_id is required
    # so we find a matching ProcessStep for the stage; otherwise log only
    # via structured logger)
    from api.models import ProcessStep

    matching_step = (
        db.query(ProcessStep)
        .filter(
            ProcessStep.factory_id == speed.factory_id,
            ProcessStep.stage == speed.stage,
            ProcessStep.is_active == True,  # noqa: E712
        )
        .first()
    )

    if matching_step:
        log = CalibrationLog(
            factory_id=speed.factory_id,
            process_step_id=matching_step.id,
            previous_rate=Decimal(str(old_rate)),
            new_rate=Decimal(str(new_rate)),
            ema_value=Decimal(str(ema_value)),
            data_points=data_points,
            trigger="auto_typology",
        )
        db.add(log)

    # Update the speed record
    speed.productivity_rate = Decimal(str(round(new_rate, 2)))
    speed.calibration_ema = Decimal(str(round(ema_value, 2)))
    speed.last_calibrated_at = datetime.now(tz.utc)

    db.flush()
