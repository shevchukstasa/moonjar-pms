"""
Stone Defect Coefficient service.
Business Logic: §14
"""
from uuid import UUID
from datetime import date, datetime, timedelta, timezone
from math import ceil
from typing import Optional
import logging

from sqlalchemy.orm import Session

from api.models import DefectRecord, StoneDefectCoefficient, OrderPosition
from api.enums import DefectStage, DefectOutcome

logger = logging.getLogger("moonjar.defect_coefficient")

# Stages used for stone defect calculation
DEFECT_STAGES = [
    DefectStage.INCOMING_INSPECTION.value,
    DefectStage.PRE_GLAZING.value,
]

# Default rolling period
DEFAULT_PERIOD_DAYS = 30


def update_stone_defect_coefficient(db: Session, factory_id: UUID) -> None:
    """Daily: running defect coefficient from stages 1+2."""
    period_days = DEFAULT_PERIOD_DAYS
    cutoff = date.today() - timedelta(days=period_days)

    # Query defect records for the relevant stages
    records = db.query(DefectRecord).filter(
        DefectRecord.factory_id == factory_id,
        DefectRecord.stage.in_(DEFECT_STAGES),
        DefectRecord.date >= cutoff,
    ).all()

    if not records:
        logger.info("No defect records found for factory %s in last %d days", factory_id, period_days)
        return

    # Group by (defect_type as stone_type proxy, supplier_id)
    # DefectRecord doesn't have stone_type directly, so we derive from position's color/size
    # or use defect_type as a grouping key
    grouped: dict[tuple[str, Optional[UUID]], list[DefectRecord]] = {}
    for r in records:
        # Use defect_type as stone_type proxy, or derive from position
        stone_type = r.defect_type or "unknown"

        # Try to get more specific stone type from position
        if r.position_id:
            pos = db.query(OrderPosition).get(r.position_id)
            if pos:
                stone_type = f"{pos.color}_{pos.size}" if pos.color else stone_type

        supplier_id = r.supplier_id
        key = (stone_type, supplier_id)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(r)

    updated_count = 0
    for (stone_type, supplier_id), group_records in grouped.items():
        total_inspected = sum(
            r.quantity for r in group_records
            if r.outcome != DefectOutcome.WRITE_OFF.value
        )
        total_defective = sum(
            r.quantity for r in group_records
            if r.outcome in (DefectOutcome.WRITE_OFF.value, DefectOutcome.RETURN_TO_WORK.value)
        )

        if total_inspected > 0:
            coefficient = total_defective / total_inspected
        else:
            coefficient = 0.0

        coefficient = min(coefficient, 1.0)

        # Upsert
        existing = db.query(StoneDefectCoefficient).filter(
            StoneDefectCoefficient.factory_id == factory_id,
            StoneDefectCoefficient.stone_type == stone_type,
            StoneDefectCoefficient.supplier_id == supplier_id,
        ).first()

        if existing:
            existing.coefficient = round(coefficient, 3)
            existing.sample_size = total_inspected
            existing.last_updated = datetime.now(timezone.utc)
            existing.calculation_period_days = period_days
        else:
            sdc = StoneDefectCoefficient(
                factory_id=factory_id,
                stone_type=stone_type,
                supplier_id=supplier_id,
                coefficient=round(coefficient, 3),
                sample_size=total_inspected,
                last_updated=datetime.now(timezone.utc),
                calculation_period_days=period_days,
            )
            db.add(sdc)

        updated_count += 1

    db.flush()
    logger.info(
        "Updated %d stone defect coefficients for factory %s",
        updated_count, factory_id,
    )


def get_stone_defect_coefficient(db: Session, factory_id: UUID, stone_type: str) -> float:
    """Get current coefficient for a stone type."""
    sdc = db.query(StoneDefectCoefficient).filter(
        StoneDefectCoefficient.factory_id == factory_id,
        StoneDefectCoefficient.stone_type == stone_type,
    ).first()

    if sdc:
        return float(sdc.coefficient)

    # Try partial match (without supplier-specific)
    sdc_any = db.query(StoneDefectCoefficient).filter(
        StoneDefectCoefficient.factory_id == factory_id,
        StoneDefectCoefficient.stone_type == stone_type,
        StoneDefectCoefficient.supplier_id.is_(None),
    ).first()

    if sdc_any:
        return float(sdc_any.coefficient)

    return 0.0  # No data — assume no defects


# ============================================================
# ДВУХМЕРНЫЕ КОЭФФИЦИЕНТЫ (Decision 2026-03-19)
# ============================================================

# Defaults — target defect rates by glaze type (temperature proxy)
GLAZE_DEFECT_DEFAULTS: dict[str, float] = {
    'pigment':    0.03,   # ~1007°C, standard colored glazes
    'oxide':      0.05,   # ~900°C
    'underglaze': 0.04,
    'raku':       0.20,   # low-temp raku firing
}

# Defaults — target defect rates by product type
PRODUCT_DEFECT_DEFAULTS: dict[str, float] = {
    'tile':        0.03,
    'countertop':  0.05,
    'sink':        0.08,
    '3d':          0.10,
    'custom':      0.06,
}

DEFECT_LOOKBACK_DAYS = 90
MIN_SAMPLE_SIZE = 10


def get_glaze_defect_coeff(db: Session, factory_id: UUID, glaze_type: str) -> float:
    """
    Get effective glaze defect coefficient.
    Uses 90-day historical data from production_defects if sufficient (>= MIN_SAMPLE_SIZE),
    otherwise falls back to GLAZE_DEFECT_DEFAULTS.
    """
    glaze_type_norm = (glaze_type or 'pigment').lower().strip()

    # TODO: когда production_defects будет заполняться, добавить rolling average:
    # cutoff = date.today() - timedelta(days=DEFECT_LOOKBACK_DAYS)
    # rows = db.execute(text(
    #     "SELECT SUM(defect_quantity), SUM(total_quantity) FROM production_defects "
    #     "WHERE factory_id = :fid AND glaze_type = :gt AND fired_at >= :cutoff"
    # ), {"fid": factory_id, "gt": glaze_type_norm, "cutoff": cutoff}).fetchone()
    # if rows and rows[1] and rows[1] >= MIN_SAMPLE_SIZE:
    #     return float(rows[0]) / float(rows[1])

    return GLAZE_DEFECT_DEFAULTS.get(glaze_type_norm, 0.03)


def get_product_defect_coeff(db: Session, factory_id: UUID, product_type: str) -> float:
    """
    Get effective product defect coefficient.
    Uses 90-day historical data from production_defects if sufficient (>= MIN_SAMPLE_SIZE),
    otherwise falls back to PRODUCT_DEFECT_DEFAULTS.
    """
    product_type_norm = (product_type or 'tile').lower().strip()

    # TODO: rolling average from production_defects when data is available (same pattern as glaze)

    return PRODUCT_DEFECT_DEFAULTS.get(product_type_norm, 0.03)


def calculate_production_quantity_with_defects(
    db: Session,
    position,  # OrderPosition
) -> int:
    """
    Calculate how many pieces to produce to cover expected defects.
    Two-dimensional: glaze + product defect coefficients combined.
    Used at material reservation stage.
    Updates position.quantity_with_defect_margin in-place (caller must flush/commit).
    """
    import math

    # Check manual override on position
    if getattr(position, 'defect_coeff_override', None) is not None:
        total_coeff = float(position.defect_coeff_override)
    else:
        glaze_type = (getattr(position, 'glaze_type', None) or 'pigment')
        product_type_raw = position.product_type
        product_type_val = (
            product_type_raw.value
            if hasattr(product_type_raw, 'value')
            else str(product_type_raw)
        )

        glaze_coeff = get_glaze_defect_coeff(db, position.factory_id, glaze_type)
        product_coeff = get_product_defect_coeff(db, position.factory_id, product_type_val)
        total_coeff = glaze_coeff + product_coeff

    result = math.ceil(position.quantity * (1 + total_coeff))

    # Persist to existing model field
    position.quantity_with_defect_margin = result

    logger.debug(
        "Position %s: quantity=%d coeff=%.4f → with_defect_margin=%d",
        position.id, position.quantity, total_coeff, result,
    )
    return result


def record_actual_defect_and_check_threshold(
    db: Session,
    position,              # OrderPosition
    actual_defect_pct: float,
    fired_date=None,
) -> dict:
    """
    Called after firing when actual defect % is known.
    1. Records fact to production_defects table (via raw SQL — table added by schema patch).
    2. Checks actual vs target threshold.
    3. If exceeded: creates 5 Why task via defect_alert service.

    Returns: {exceeded: bool, target_pct: float, actual_pct: float, five_why_task_id: Optional[str]}
    """
    from datetime import date as date_cls
    import sqlalchemy as _sa

    glaze_type = (getattr(position, 'glaze_type', None) or 'pigment')
    product_type_raw = position.product_type
    product_type_val = (
        product_type_raw.value
        if hasattr(product_type_raw, 'value')
        else str(product_type_raw)
    )

    glaze_coeff = get_glaze_defect_coeff(db, position.factory_id, glaze_type)
    product_coeff = get_product_defect_coeff(db, position.factory_id, product_type_val)
    target_pct = glaze_coeff + product_coeff

    result: dict = {
        'exceeded': actual_defect_pct > target_pct,
        'target_pct': round(target_pct * 100, 1),
        'actual_pct': round(actual_defect_pct * 100, 1),
        'five_why_task_id': None,
    }

    # Record to production_defects (table created by schema patch; skip silently if missing)
    total_qty = getattr(position, 'quantity_with_defect_margin', None) or position.quantity
    defect_qty = round(actual_defect_pct * total_qty)
    fired_at = fired_date or date_cls.today()

    try:
        db.execute(
            _sa.text(
                """
                INSERT INTO production_defects
                    (factory_id, position_id, glaze_type, product_type,
                     total_quantity, defect_quantity, defect_pct, fired_at)
                VALUES
                    (:factory_id, :position_id, :glaze_type, :product_type,
                     :total_qty, :defect_qty, :defect_pct, :fired_at)
                """
            ),
            {
                'factory_id': str(position.factory_id),
                'position_id': str(position.id),
                'glaze_type': glaze_type,
                'product_type': product_type_val,
                'total_qty': total_qty,
                'defect_qty': defect_qty,
                'defect_pct': round(actual_defect_pct, 4),
                'fired_at': fired_at,
            },
        )
    except Exception as exc:
        logger.warning("Could not record to production_defects: %s", exc)

    if actual_defect_pct > target_pct:
        try:
            from business.services.defect_alert import create_five_why_task
            task = create_five_why_task(
                db, position, actual_defect_pct, target_pct,
                glaze_type, product_type_val,
            )
            if task:
                result['five_why_task_id'] = str(task.id)
        except Exception as exc:
            logger.warning("Could not create 5 Why task: %s", exc)

    return result
