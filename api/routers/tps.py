"""TPS (Toyota Production System) router — parameters, shift metrics, deviations."""

from datetime import date, datetime, timezone
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func

from api.database import get_db
from api.auth import get_current_user, apply_factory_filter
from api.roles import require_management
from api.models import TpsParameter, TpsShiftMetric, TpsDeviation, Factory
from api.enums import TpsStatus, TpsDeviationType

router = APIRouter()


def _ev(val):
    return val.value if hasattr(val, "value") else str(val) if val else None


# ── TPS Parameters ──────────────────────────────────────────────────────

class TpsParameterCreate(BaseModel):
    factory_id: UUID
    stage: str
    metric_name: str
    target_value: float
    tolerance_percent: float = 10.0
    unit: Optional[str] = None


class TpsParameterUpdate(BaseModel):
    target_value: Optional[float] = None
    tolerance_percent: Optional[float] = None
    unit: Optional[str] = None


def _serialize_param(p) -> dict:
    return {
        "id": str(p.id),
        "factory_id": str(p.factory_id),
        "stage": p.stage,
        "metric_name": p.metric_name,
        "target_value": float(p.target_value),
        "tolerance_percent": float(p.tolerance_percent),
        "unit": p.unit,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


@router.get("/parameters")
async def list_parameters(
    factory_id: UUID | None = None,
    stage: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List TPS parameters (targets & tolerances per stage)."""
    query = db.query(TpsParameter)
    if factory_id:
        query = query.filter(TpsParameter.factory_id == factory_id)
    else:
        query = apply_factory_filter(query, TpsParameter, current_user, db)
    if stage:
        query = query.filter(TpsParameter.stage == stage)

    items = query.order_by(TpsParameter.stage, TpsParameter.metric_name).all()
    return {"items": [_serialize_param(p) for p in items], "total": len(items)}


@router.post("/parameters", status_code=201)
async def create_parameter(
    data: TpsParameterCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Create a TPS parameter target."""
    param = TpsParameter(
        factory_id=data.factory_id,
        stage=data.stage,
        metric_name=data.metric_name,
        target_value=data.target_value,
        tolerance_percent=data.tolerance_percent,
        unit=data.unit,
    )
    db.add(param)
    db.commit()
    db.refresh(param)
    return _serialize_param(param)


@router.patch("/parameters/{param_id}")
async def update_parameter(
    param_id: UUID,
    data: TpsParameterUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Update a TPS parameter."""
    param = db.query(TpsParameter).filter(TpsParameter.id == param_id).first()
    if not param:
        raise HTTPException(404, "Parameter not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(param, field, value)

    db.commit()
    db.refresh(param)
    return _serialize_param(param)


# ── TPS Shift Metrics ──────────────────────────────────────────────────

class ShiftMetricCreate(BaseModel):
    factory_id: UUID
    shift: int
    date: date
    stage: str
    planned_output: float
    actual_output: float
    actual_output_pcs: int = 0
    defect_rate: float = 0
    downtime_minutes: float = 0
    cycle_time_minutes: float = 0
    oee_percent: float = 0
    takt_time_minutes: float = 0
    notes: Optional[str] = None


def _serialize_metric(m) -> dict:
    return {
        "id": str(m.id),
        "factory_id": str(m.factory_id),
        "shift": m.shift,
        "date": str(m.date),
        "stage": m.stage,
        "planned_output": float(m.planned_output),
        "actual_output": float(m.actual_output),
        "actual_output_pcs": m.actual_output_pcs,
        "deviation_percent": float(m.deviation_percent or 0),
        "defect_rate": float(m.defect_rate or 0),
        "downtime_minutes": float(m.downtime_minutes or 0),
        "cycle_time_minutes": float(m.cycle_time_minutes or 0),
        "oee_percent": float(m.oee_percent or 0),
        "takt_time_minutes": float(m.takt_time_minutes or 0),
        "status": _ev(m.status),
        "notes": m.notes,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


@router.get("/")
async def list_shift_metrics(
    factory_id: UUID | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    stage: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List TPS shift metrics."""
    query = db.query(TpsShiftMetric)
    if factory_id:
        query = query.filter(TpsShiftMetric.factory_id == factory_id)
    else:
        query = apply_factory_filter(query, TpsShiftMetric, current_user, db)
    if date_from:
        query = query.filter(TpsShiftMetric.date >= date.fromisoformat(date_from))
    if date_to:
        query = query.filter(TpsShiftMetric.date <= date.fromisoformat(date_to))
    if stage:
        query = query.filter(TpsShiftMetric.stage == stage)

    total = query.count()
    items = (
        query.order_by(TpsShiftMetric.date.desc(), TpsShiftMetric.shift)
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return {"items": [_serialize_metric(m) for m in items], "total": total, "page": page, "per_page": per_page}


@router.post("/", status_code=201)
async def create_shift_metric(
    data: ShiftMetricCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Record a shift metric."""
    planned = float(data.planned_output)
    actual = float(data.actual_output)
    deviation = ((actual - planned) / planned * 100) if planned > 0 else 0

    # Determine status
    if abs(deviation) <= 5:
        status = TpsStatus.NORMAL
    elif abs(deviation) <= 15:
        status = TpsStatus.WARNING
    else:
        status = TpsStatus.CRITICAL

    metric = TpsShiftMetric(
        factory_id=data.factory_id,
        shift=data.shift,
        date=data.date,
        stage=data.stage,
        planned_output=data.planned_output,
        actual_output=data.actual_output,
        actual_output_pcs=data.actual_output_pcs,
        deviation_percent=round(deviation, 2),
        defect_rate=data.defect_rate,
        downtime_minutes=data.downtime_minutes,
        cycle_time_minutes=data.cycle_time_minutes,
        oee_percent=data.oee_percent,
        takt_time_minutes=data.takt_time_minutes,
        status=status,
        notes=data.notes,
    )
    db.add(metric)
    db.commit()
    db.refresh(metric)
    return _serialize_metric(metric)


# ── TPS Deviations ──────────────────────────────────────────────────────

class DeviationCreate(BaseModel):
    factory_id: UUID
    shift: int
    stage: str
    deviation_type: str  # 'positive' or 'negative'
    description: str
    severity: str = "low"  # low, medium, high


class DeviationUpdate(BaseModel):
    resolved: Optional[bool] = None
    description: Optional[str] = None
    severity: Optional[str] = None


def _serialize_deviation(d) -> dict:
    return {
        "id": str(d.id),
        "factory_id": str(d.factory_id),
        "shift": d.shift,
        "stage": d.stage,
        "deviation_type": _ev(d.deviation_type),
        "description": d.description,
        "severity": d.severity,
        "resolved": d.resolved,
        "created_at": d.created_at.isoformat() if d.created_at else None,
    }


@router.get("/deviations")
async def list_deviations(
    factory_id: UUID | None = None,
    resolved: bool | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List TPS deviations."""
    query = db.query(TpsDeviation)
    if factory_id:
        query = query.filter(TpsDeviation.factory_id == factory_id)
    else:
        query = apply_factory_filter(query, TpsDeviation, current_user, db)
    if resolved is not None:
        query = query.filter(TpsDeviation.resolved == resolved)

    total = query.count()
    items = (
        query.order_by(TpsDeviation.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return {"items": [_serialize_deviation(d) for d in items], "total": total, "page": page, "per_page": per_page}


@router.post("/deviations", status_code=201)
async def create_deviation(
    data: DeviationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Report a TPS deviation."""
    dev = TpsDeviation(
        factory_id=data.factory_id,
        shift=data.shift,
        stage=data.stage,
        deviation_type=TpsDeviationType(data.deviation_type),
        description=data.description,
        severity=data.severity,
    )
    db.add(dev)
    db.commit()
    db.refresh(dev)
    return _serialize_deviation(dev)


@router.patch("/deviations/{deviation_id}")
async def update_deviation(
    deviation_id: UUID,
    data: DeviationUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Update/resolve a TPS deviation."""
    dev = db.query(TpsDeviation).filter(TpsDeviation.id == deviation_id).first()
    if not dev:
        raise HTTPException(404, "Deviation not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(dev, field, value)

    db.commit()
    db.refresh(dev)
    return _serialize_deviation(dev)
