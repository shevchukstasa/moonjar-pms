"""
Stone Defect Coefficient service.
Business Logic: §14
"""
from uuid import UUID
from datetime import date, datetime, timedelta
from math import ceil, floor
from typing import Optional
import logging

from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func

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
            existing.last_updated = datetime.utcnow()
            existing.calculation_period_days = period_days
        else:
            sdc = StoneDefectCoefficient(
                factory_id=factory_id,
                stone_type=stone_type,
                supplier_id=supplier_id,
                coefficient=round(coefficient, 3),
                sample_size=total_inspected,
                last_updated=datetime.utcnow(),
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
