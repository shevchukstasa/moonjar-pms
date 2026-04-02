"""TPS (Toyota Production System) router — parameters, shift metrics, deviations, operation time tracking."""

from datetime import date, datetime, timedelta, timezone
from uuid import UUID
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func as sa_func, or_

from api.database import get_db
from api.auth import get_current_user, apply_factory_filter
from api.roles import require_management
from api.models import (
    TpsParameter, TpsShiftMetric, TpsDeviation, Factory,
    OperationLog, Operation, OrderPosition, MasterPermission, User,
    ProcessStep, CalibrationLog,
    KilnLoadingTypology, KilnTypologyCapacity,
)
from api.enums import TpsDeviationType
from business.services.tps_metrics import (
    collect_shift_metrics as _collect_shift_metrics,
    record_shift_metric as _record_shift_metric,
    evaluate_signal as _evaluate_signal,
)

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


@router.get("")
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


@router.post("", status_code=201)
async def create_shift_metric(
    data: ShiftMetricCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Record a shift metric using the TPS metrics service.

    The service calculates OEE, takt time, cycle time, deviation status,
    and auto-creates deviation records + PM notifications on critical deviations.
    """
    try:
        result = _record_shift_metric(
            db=db,
            factory_id=data.factory_id,
            shift=data.shift,
            metric_date=data.date,
            stage=data.stage,
            planned_output=float(data.planned_output),
            actual_output=float(data.actual_output),
            actual_output_pcs=data.actual_output_pcs,
            defect_count=int(data.defect_rate) if data.defect_rate else 0,
            downtime_minutes=float(data.downtime_minutes),
            available_minutes=480.0,
        )
    except Exception as e:
        raise HTTPException(400, f"Failed to record shift metric: {e}")

    # Re-fetch the persisted metric to return full serialized data
    metric = db.query(TpsShiftMetric).filter(
        TpsShiftMetric.factory_id == data.factory_id,
        TpsShiftMetric.shift == data.shift,
        TpsShiftMetric.date == data.date,
        TpsShiftMetric.stage == data.stage,
    ).first()

    if metric:
        return _serialize_metric(metric)
    return result


# ── TPS Dashboard Summary ──────────────────────────────────────────────

@router.get("/dashboard-summary")
async def get_dashboard_summary(
    factory_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Aggregated TPS dashboard summary.

    Returns:
    - Current throughput per stage (last 7 days)
    - Deviation counts (last 24h, last 7d)
    - Top 3 bottleneck stages (highest avg cycle time)
    - Average cycle time per stage
    """
    now = datetime.now(timezone.utc)
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)

    # ── Throughput per stage (last 7 days from shift metrics) ──
    throughput_q = db.query(
        TpsShiftMetric.stage,
        sa_func.sum(TpsShiftMetric.actual_output).label("total_output"),
        sa_func.sum(TpsShiftMetric.planned_output).label("total_planned"),
        sa_func.avg(TpsShiftMetric.oee_percent).label("avg_oee"),
    ).filter(
        TpsShiftMetric.date >= last_7d.date(),
    )
    if factory_id:
        throughput_q = throughput_q.filter(TpsShiftMetric.factory_id == factory_id)
    else:
        throughput_q = apply_factory_filter(throughput_q, TpsShiftMetric, current_user, db)
    throughput_q = throughput_q.group_by(TpsShiftMetric.stage)
    throughput_rows = throughput_q.all()

    throughput_per_stage = []
    for row in throughput_rows:
        total_output = float(row.total_output or 0)
        total_planned = float(row.total_planned or 0)
        throughput_per_stage.append({
            "stage": row.stage,
            "total_output": round(total_output, 2),
            "total_planned": round(total_planned, 2),
            "fulfillment_percent": round(total_output / total_planned * 100, 1) if total_planned > 0 else 0,
            "avg_oee_percent": round(float(row.avg_oee or 0), 1),
        })

    # ── Deviation counts ──
    dev_base = db.query(TpsDeviation)
    if factory_id:
        dev_base = dev_base.filter(TpsDeviation.factory_id == factory_id)
    else:
        dev_base = apply_factory_filter(dev_base, TpsDeviation, current_user, db)

    deviations_24h = dev_base.filter(TpsDeviation.created_at >= last_24h).count()
    deviations_7d = dev_base.filter(TpsDeviation.created_at >= last_7d).count()
    unresolved_deviations = dev_base.filter(TpsDeviation.resolved == False).count()

    # ── Average cycle time per stage (from shift metrics, last 7d) ──
    cycle_q = db.query(
        TpsShiftMetric.stage,
        sa_func.avg(TpsShiftMetric.cycle_time_minutes).label("avg_cycle_time"),
        sa_func.avg(TpsShiftMetric.takt_time_minutes).label("avg_takt_time"),
        sa_func.avg(TpsShiftMetric.downtime_minutes).label("avg_downtime"),
    ).filter(
        TpsShiftMetric.date >= last_7d.date(),
        TpsShiftMetric.cycle_time_minutes > 0,
    )
    if factory_id:
        cycle_q = cycle_q.filter(TpsShiftMetric.factory_id == factory_id)
    else:
        cycle_q = apply_factory_filter(cycle_q, TpsShiftMetric, current_user, db)
    cycle_q = cycle_q.group_by(TpsShiftMetric.stage)
    cycle_rows = cycle_q.all()

    cycle_times = []
    for row in cycle_rows:
        cycle_times.append({
            "stage": row.stage,
            "avg_cycle_time_minutes": round(float(row.avg_cycle_time or 0), 2),
            "avg_takt_time_minutes": round(float(row.avg_takt_time or 0), 2),
            "avg_downtime_minutes": round(float(row.avg_downtime or 0), 2),
        })

    # ── Top 3 bottleneck stages (highest avg cycle time) ──
    bottlenecks = sorted(cycle_times, key=lambda x: x["avg_cycle_time_minutes"], reverse=True)[:3]

    return {
        "throughput_per_stage": throughput_per_stage,
        "deviations": {
            "last_24h": deviations_24h,
            "last_7d": deviations_7d,
            "unresolved": unresolved_deviations,
        },
        "bottleneck_stages": bottlenecks,
        "cycle_times_per_stage": cycle_times,
    }


# ── TPS Shift Collection & Signal ─────────────────────────────────────

@router.get("/shift-summary")
async def get_shift_summary(
    factory_id: UUID,
    shift_date: date | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Collect and return all shift metrics for a factory on a given date.

    Uses the TPS metrics service to aggregate data by shift and stage.
    Defaults to today if shift_date is not provided.
    """
    target_date = shift_date or date.today()
    try:
        return _collect_shift_metrics(db, factory_id, target_date)
    except Exception as e:
        raise HTTPException(400, f"Failed to collect shift metrics: {e}")


@router.get("/signal")
async def get_signal(
    factory_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Evaluate the TPS signal (green/yellow/red) for a factory today.

    - green: all normal or no data
    - yellow: some warnings but no critical
    - red: any critical deviation or >50% warnings
    """
    try:
        signal = _evaluate_signal(db, factory_id)
        return {"factory_id": str(factory_id), "signal": signal, "date": str(date.today())}
    except Exception as e:
        raise HTTPException(400, f"Failed to evaluate signal: {e}")


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


# ── Operation Time Tracking ──────────────────────────────────────────────

class RecordOperationTime(BaseModel):
    factory_id: UUID
    operation_id: UUID
    position_id: Optional[UUID] = None
    batch_id: Optional[UUID] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    quantity_processed: Optional[int] = None
    defect_count: int = 0
    notes: Optional[str] = None
    source: str = "dashboard"  # 'telegram', 'dashboard', 'auto'


def _serialize_op_log(log) -> dict:
    return {
        "id": str(log.id),
        "factory_id": str(log.factory_id),
        "operation_id": str(log.operation_id),
        "user_id": str(log.user_id),
        "position_id": str(log.position_id) if log.position_id else None,
        "batch_id": str(log.batch_id) if log.batch_id else None,
        "shift_date": str(log.shift_date),
        "shift_number": log.shift_number,
        "started_at": log.started_at.isoformat() if log.started_at else None,
        "completed_at": log.completed_at.isoformat() if log.completed_at else None,
        "duration_minutes": float(log.duration_minutes) if log.duration_minutes else None,
        "quantity_processed": log.quantity_processed,
        "defect_count": log.defect_count or 0,
        "notes": log.notes,
        "source": log.source,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


@router.post("/record", status_code=201)
async def record_operation_time(
    data: RecordOperationTime,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Record operation start/end time for a position.

    Masters enter via Telegram, PM enters via dashboard.
    If only started_at is provided, the operation is in progress.
    If both started_at and completed_at are provided, duration is calculated.
    """
    # Validate operation exists
    operation = db.query(Operation).filter(Operation.id == data.operation_id).first()
    if not operation:
        raise HTTPException(404, "Operation not found")

    # Check master/senior_master has permission for this operation
    if current_user.role in ("master", "senior_master"):
        has_perm = db.query(MasterPermission).filter(
            MasterPermission.user_id == current_user.id,
            MasterPermission.operation_id == data.operation_id,
        ).first()
        if not has_perm:
            raise HTTPException(403, "You do not have permission to perform this operation")

    # Validate position if provided
    if data.position_id:
        position = db.query(OrderPosition).filter(OrderPosition.id == data.position_id).first()
        if not position:
            raise HTTPException(404, "Position not found")

    # Calculate duration if both timestamps provided
    duration_minutes = None
    if data.started_at and data.completed_at:
        if data.completed_at <= data.started_at:
            raise HTTPException(400, "completed_at must be after started_at")
        delta = data.completed_at - data.started_at
        duration_minutes = round(delta.total_seconds() / 60, 2)

    # Determine shift date (use started_at date, or today)
    shift_date = data.started_at.date() if data.started_at else date.today()

    log = OperationLog(
        factory_id=data.factory_id,
        operation_id=data.operation_id,
        user_id=current_user.id,
        position_id=data.position_id,
        batch_id=data.batch_id,
        shift_date=shift_date,
        started_at=data.started_at,
        completed_at=data.completed_at,
        duration_minutes=duration_minutes,
        quantity_processed=data.quantity_processed,
        defect_count=data.defect_count,
        notes=data.notes,
        source=data.source,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return _serialize_op_log(log)


@router.get("/position/{position_id}/timeline")
async def get_position_timeline(
    position_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get full operation timeline for a position.

    Returns all operation logs ordered chronologically, showing
    how the position moved through each production stage.
    """
    position = db.query(OrderPosition).filter(OrderPosition.id == position_id).first()
    if not position:
        raise HTTPException(404, "Position not found")

    logs = (
        db.query(OperationLog)
        .filter(OperationLog.position_id == position_id)
        .order_by(OperationLog.started_at.asc().nullslast(), OperationLog.created_at.asc())
        .all()
    )

    # Enrich with operation names
    op_ids = list({log.operation_id for log in logs})
    operations = {}
    if op_ids:
        ops = db.query(Operation).filter(Operation.id.in_(op_ids)).all()
        operations = {op.id: op for op in ops}

    timeline = []
    total_duration = 0.0
    for log in logs:
        op = operations.get(log.operation_id)
        entry = _serialize_op_log(log)
        entry["operation_name"] = op.name if op else None
        entry["norm_time_minutes"] = float(op.default_time_minutes) if op and op.default_time_minutes else None
        if log.duration_minutes:
            dur = float(log.duration_minutes)
            total_duration += dur
            # Flag if exceeds norm by more than 50%
            if op and op.default_time_minutes:
                norm = float(op.default_time_minutes)
                if norm > 0:
                    entry["deviation_percent"] = round((dur - norm) / norm * 100, 1)
        timeline.append(entry)

    return {
        "position_id": str(position_id),
        "timeline": timeline,
        "total_operations": len(timeline),
        "total_duration_minutes": round(total_duration, 2),
    }


@router.get("/throughput")
async def get_stage_throughput(
    factory_id: UUID,
    date_from: str | None = None,
    date_to: str | None = None,
    operation_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Get stage throughput statistics per factory and date range.

    Returns average duration, count, and throughput rate per operation.
    """
    # Default to last 30 days
    dt_to = date.fromisoformat(date_to) if date_to else date.today()
    dt_from = date.fromisoformat(date_from) if date_from else dt_to - timedelta(days=30)

    query = (
        db.query(
            OperationLog.operation_id,
            sa_func.count(OperationLog.id).label("count"),
            sa_func.avg(OperationLog.duration_minutes).label("avg_duration"),
            sa_func.min(OperationLog.duration_minutes).label("min_duration"),
            sa_func.max(OperationLog.duration_minutes).label("max_duration"),
            sa_func.sum(OperationLog.quantity_processed).label("total_qty"),
            sa_func.sum(OperationLog.defect_count).label("total_defects"),
        )
        .filter(
            OperationLog.factory_id == factory_id,
            OperationLog.shift_date >= dt_from,
            OperationLog.shift_date <= dt_to,
            OperationLog.duration_minutes.isnot(None),
        )
    )
    if operation_id:
        query = query.filter(OperationLog.operation_id == operation_id)

    query = query.group_by(OperationLog.operation_id)
    rows = query.all()

    # Fetch operation names
    op_ids = [r.operation_id for r in rows]
    operations = {}
    if op_ids:
        ops = db.query(Operation).filter(Operation.id.in_(op_ids)).all()
        operations = {op.id: op for op in ops}

    items = []
    for r in rows:
        op = operations.get(r.operation_id)
        avg_dur = float(r.avg_duration) if r.avg_duration else 0
        total_qty = int(r.total_qty or 0)
        total_defects = int(r.total_defects or 0)
        items.append({
            "operation_id": str(r.operation_id),
            "operation_name": op.name if op else None,
            "norm_time_minutes": float(op.default_time_minutes) if op and op.default_time_minutes else None,
            "count": r.count,
            "avg_duration_minutes": round(avg_dur, 2),
            "min_duration_minutes": round(float(r.min_duration), 2) if r.min_duration else None,
            "max_duration_minutes": round(float(r.max_duration), 2) if r.max_duration else None,
            "total_quantity_processed": total_qty,
            "total_defects": total_defects,
            "defect_rate_percent": round(total_defects / total_qty * 100, 1) if total_qty > 0 else 0,
        })

    return {
        "factory_id": str(factory_id),
        "date_from": str(dt_from),
        "date_to": str(dt_to),
        "items": items,
    }


@router.get("/deviations/operations")
async def get_operation_time_deviations(
    factory_id: UUID,
    date_from: str | None = None,
    date_to: str | None = None,
    threshold_percent: float = Query(50.0, description="Deviation threshold from norm (%)"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Get positions with abnormal operation times.

    Returns operation logs where actual duration deviates from the
    operation norm by more than threshold_percent.
    """
    dt_to = date.fromisoformat(date_to) if date_to else date.today()
    dt_from = date.fromisoformat(date_from) if date_from else dt_to - timedelta(days=30)

    # Get all operations with norms for this factory
    ops_with_norms = (
        db.query(Operation)
        .filter(
            Operation.factory_id == factory_id,
            Operation.default_time_minutes.isnot(None),
            Operation.is_active.is_(True),
        )
        .all()
    )
    if not ops_with_norms:
        return {"items": [], "total": 0, "page": page, "per_page": per_page}

    norms = {op.id: float(op.default_time_minutes) for op in ops_with_norms}
    op_names = {op.id: op.name for op in ops_with_norms}

    # Query completed logs in date range for these operations
    logs = (
        db.query(OperationLog)
        .filter(
            OperationLog.factory_id == factory_id,
            OperationLog.shift_date >= dt_from,
            OperationLog.shift_date <= dt_to,
            OperationLog.duration_minutes.isnot(None),
            OperationLog.operation_id.in_(list(norms.keys())),
        )
        .order_by(OperationLog.shift_date.desc(), OperationLog.created_at.desc())
        .all()
    )

    # Filter by deviation threshold
    deviations: List[dict] = []
    for log in logs:
        norm = norms.get(log.operation_id, 0)
        if norm <= 0:
            continue
        actual = float(log.duration_minutes)
        deviation_pct = (actual - norm) / norm * 100
        if abs(deviation_pct) >= threshold_percent:
            entry = _serialize_op_log(log)
            entry["operation_name"] = op_names.get(log.operation_id)
            entry["norm_time_minutes"] = norm
            entry["deviation_percent"] = round(deviation_pct, 1)
            entry["severity"] = (
                "high" if abs(deviation_pct) >= 100
                else "medium" if abs(deviation_pct) >= 75
                else "low"
            )
            deviations.append(entry)

    total = len(deviations)
    start = (page - 1) * per_page
    paged = deviations[start:start + per_page]

    return {"items": paged, "total": total, "page": page, "per_page": per_page}


# ── Operations ──────────────────────────────────────────────────────────

def _serialize_operation(op) -> dict:
    return {
        "id": str(op.id),
        "factory_id": str(op.factory_id),
        "name": op.name,
        "description": op.description,
        "default_time_minutes": float(op.default_time_minutes) if op.default_time_minutes else None,
        "is_active": op.is_active,
        "sort_order": op.sort_order or 0,
        "created_at": op.created_at.isoformat() if op.created_at else None,
    }


@router.get("/operations")
async def list_operations(
    factory_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """List all operations for a factory."""
    query = db.query(Operation).filter(Operation.is_active == True)
    if factory_id:
        query = query.filter(Operation.factory_id == factory_id)
    else:
        query = apply_factory_filter(query, Operation, current_user, db)

    items = query.order_by(Operation.sort_order.asc(), Operation.name.asc()).all()
    return {"items": [_serialize_operation(op) for op in items], "total": len(items)}


# ── Master Permissions ──────────────────────────────────────────────────

class MasterPermissionCreate(BaseModel):
    user_id: UUID
    operation_id: UUID


def _serialize_permission(perm, operation_name: str | None = None, granted_by_name: str | None = None) -> dict:
    return {
        "id": str(perm.id),
        "user_id": str(perm.user_id),
        "operation_id": str(perm.operation_id),
        "operation_name": operation_name or (perm.operation.name if perm.operation else None),
        "granted_by": str(perm.granted_by),
        "granted_by_name": granted_by_name or (perm.grantor.name if perm.grantor else None),
        "granted_at": perm.granted_at.isoformat() if perm.granted_at else None,
    }


@router.get("/master-permissions/check/{user_id}/{operation_id}")
async def check_master_permission(
    user_id: UUID,
    operation_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Check if a user has permission for a specific operation."""
    perm = db.query(MasterPermission).filter(
        MasterPermission.user_id == user_id,
        MasterPermission.operation_id == operation_id,
    ).first()
    return {"permitted": perm is not None, "user_id": str(user_id), "operation_id": str(operation_id)}


@router.get("/master-permissions/{user_id}")
async def list_master_permissions(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """List all operation permissions for a master/senior_master."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    perms = (
        db.query(MasterPermission)
        .filter(MasterPermission.user_id == user_id)
        .all()
    )

    return {
        "items": [_serialize_permission(p) for p in perms],
        "total": len(perms),
        "user_id": str(user_id),
        "user_name": user.name,
    }


@router.post("/master-permissions", status_code=201)
async def grant_master_permission(
    data: MasterPermissionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Grant an operation permission to a master/senior_master."""
    # Validate user exists and is master/senior_master
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    if user.role not in ("master", "senior_master"):
        raise HTTPException(400, "Permissions can only be assigned to master or senior_master roles")

    # Validate operation exists
    operation = db.query(Operation).filter(Operation.id == data.operation_id).first()
    if not operation:
        raise HTTPException(404, "Operation not found")

    # Check for duplicate
    existing = db.query(MasterPermission).filter(
        MasterPermission.user_id == data.user_id,
        MasterPermission.operation_id == data.operation_id,
    ).first()
    if existing:
        raise HTTPException(409, "Permission already granted")

    perm = MasterPermission(
        user_id=data.user_id,
        operation_id=data.operation_id,
        granted_by=current_user.id,
    )
    db.add(perm)
    db.commit()
    db.refresh(perm)
    return _serialize_permission(perm, operation_name=operation.name, granted_by_name=current_user.name)


@router.delete("/master-permissions/{permission_id}")
async def revoke_master_permission(
    permission_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Revoke an operation permission from a master/senior_master."""
    perm = db.query(MasterPermission).filter(MasterPermission.id == permission_id).first()
    if not perm:
        raise HTTPException(404, "Permission not found")

    db.delete(perm)
    db.commit()
    return {"ok": True, "message": "Permission revoked"}


# ── Master Achievements ──────────────────────────────────────


@router.get("/achievements/{user_id}")
async def get_achievements(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get achievements for a user with level, progress, next milestone."""
    from business.services.achievements import get_user_achievements

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    achievements = get_user_achievements(db, user_id)
    db.commit()

    return {
        "items": achievements,
        "user_name": user.name,
    }


# ── Process Steps ──────────────────────────────────────────────────────


class ProcessStepCreate(BaseModel):
    name: str
    factory_id: UUID
    stage: str
    sequence: int = 0
    norm_time_minutes: Optional[float] = None
    productivity_rate: Optional[float] = None
    productivity_unit: Optional[str] = None
    measurement_basis: Optional[str] = None
    shift_count: int = 2
    applicable_collections: List[str] = []
    applicable_methods: List[str] = []
    applicable_product_types: List[str] = []
    auto_calibrate: bool = False
    notes: Optional[str] = None


class ProcessStepUpdate(BaseModel):
    name: Optional[str] = None
    stage: Optional[str] = None
    sequence: Optional[int] = None
    norm_time_minutes: Optional[float] = None
    productivity_rate: Optional[float] = None
    productivity_unit: Optional[str] = None
    measurement_basis: Optional[str] = None
    shift_count: Optional[int] = None
    applicable_collections: Optional[List[str]] = None
    applicable_methods: Optional[List[str]] = None
    applicable_product_types: Optional[List[str]] = None
    auto_calibrate: Optional[bool] = None
    notes: Optional[str] = None


class ReorderPayload(BaseModel):
    step_ids: List[UUID]


def _serialize_process_step(step) -> dict:
    return {
        "id": str(step.id),
        "name": step.name,
        "factory_id": str(step.factory_id),
        "stage": step.stage,
        "sequence": step.sequence,
        "norm_time_minutes": float(step.norm_time_minutes) if step.norm_time_minutes else None,
        "productivity_rate": float(step.productivity_rate) if step.productivity_rate else None,
        "productivity_unit": step.productivity_unit,
        "measurement_basis": step.measurement_basis,
        "shift_count": step.shift_count or 2,
        "applicable_collections": step.applicable_collections or [],
        "applicable_methods": step.applicable_methods or [],
        "applicable_product_types": step.applicable_product_types or [],
        "auto_calibrate": step.auto_calibrate or False,
        "calibration_ema": float(step.calibration_ema) if step.calibration_ema else None,
        "last_calibrated_at": step.last_calibrated_at.isoformat() if step.last_calibrated_at else None,
        "is_active": step.is_active,
        "notes": step.notes,
    }


@router.get("/process-steps")
async def list_process_steps(
    factory_id: UUID = Query(...),
    collection: Optional[str] = None,
    method: Optional[str] = None,
    product_type: Optional[str] = None,
    stage: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List process steps with filtering."""
    query = db.query(ProcessStep).filter(ProcessStep.factory_id == factory_id)

    if stage:
        query = query.filter(ProcessStep.stage == stage)
    if is_active is not None:
        query = query.filter(ProcessStep.is_active == is_active)

    # JSONB array filtering: empty array means "all" (include step)
    if collection:
        query = query.filter(
            or_(
                sa_func.jsonb_array_length(ProcessStep.applicable_collections) == 0,
                ProcessStep.applicable_collections.contains([collection]),
            )
        )
    if method:
        query = query.filter(
            or_(
                sa_func.jsonb_array_length(ProcessStep.applicable_methods) == 0,
                ProcessStep.applicable_methods.contains([method]),
            )
        )
    if product_type:
        query = query.filter(
            or_(
                sa_func.jsonb_array_length(ProcessStep.applicable_product_types) == 0,
                ProcessStep.applicable_product_types.contains([product_type]),
            )
        )

    items = query.order_by(ProcessStep.sequence).all()
    return {"items": [_serialize_process_step(s) for s in items], "total": len(items)}


@router.post("/process-steps", status_code=201)
async def create_process_step(
    data: ProcessStepCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Create a new process step."""
    step = ProcessStep(
        name=data.name,
        factory_id=data.factory_id,
        stage=data.stage,
        sequence=data.sequence,
        norm_time_minutes=data.norm_time_minutes,
        productivity_rate=data.productivity_rate,
        productivity_unit=data.productivity_unit,
        measurement_basis=data.measurement_basis,
        shift_count=data.shift_count,
        applicable_collections=data.applicable_collections,
        applicable_methods=data.applicable_methods,
        applicable_product_types=data.applicable_product_types,
        auto_calibrate=data.auto_calibrate,
        notes=data.notes,
    )
    db.add(step)
    db.commit()
    db.refresh(step)
    return _serialize_process_step(step)


# NOTE: reorder MUST be before {step_id} to avoid FastAPI path conflict
@router.patch("/process-steps/reorder")
async def reorder_process_steps(
    data: ReorderPayload,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Reorder process steps. Sets sequence = index for each step."""
    for idx, step_id in enumerate(data.step_ids):
        step = db.query(ProcessStep).filter(ProcessStep.id == step_id).first()
        if step:
            step.sequence = idx
    db.commit()
    return {"ok": True, "message": f"Reordered {len(data.step_ids)} steps"}


@router.get("/process-steps/pipeline")
async def get_process_pipeline(
    factory_id: UUID = Query(...),
    collection: Optional[str] = None,
    method: Optional[str] = None,
    product_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return filtered pipeline for a specific collection+method combo."""
    query = db.query(ProcessStep).filter(
        ProcessStep.factory_id == factory_id,
        ProcessStep.is_active == True,
    )

    if collection:
        query = query.filter(
            or_(
                sa_func.jsonb_array_length(ProcessStep.applicable_collections) == 0,
                ProcessStep.applicable_collections.contains([collection]),
            )
        )
    if method:
        query = query.filter(
            or_(
                sa_func.jsonb_array_length(ProcessStep.applicable_methods) == 0,
                ProcessStep.applicable_methods.contains([method]),
            )
        )
    if product_type:
        query = query.filter(
            or_(
                sa_func.jsonb_array_length(ProcessStep.applicable_product_types) == 0,
                ProcessStep.applicable_product_types.contains([product_type]),
            )
        )

    items = query.order_by(ProcessStep.sequence).all()
    return {"items": [_serialize_process_step(s) for s in items], "total": len(items)}


@router.patch("/process-steps/{step_id}")
async def update_process_step(
    step_id: UUID,
    data: ProcessStepUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Partial update of a process step."""
    step = db.query(ProcessStep).filter(ProcessStep.id == step_id).first()
    if not step:
        raise HTTPException(404, "Process step not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(step, field, value)

    db.commit()
    db.refresh(step)
    return _serialize_process_step(step)


@router.delete("/process-steps/{step_id}")
async def deactivate_process_step(
    step_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Soft-delete: set is_active=false."""
    step = db.query(ProcessStep).filter(ProcessStep.id == step_id).first()
    if not step:
        raise HTTPException(404, "Process step not found")

    step.is_active = False
    db.commit()
    return {"ok": True, "message": "Process step deactivated"}


# ── Calibration Log ──────────────────────────────────────────────────


@router.get("/calibration/log")
async def list_calibration_log(
    factory_id: Optional[UUID] = None,
    process_step_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List calibration log entries with step and factory names."""
    query = db.query(CalibrationLog)

    if factory_id:
        query = query.filter(CalibrationLog.factory_id == factory_id)
    if process_step_id:
        query = query.filter(CalibrationLog.process_step_id == process_step_id)

    items = query.order_by(CalibrationLog.created_at.desc()).all()

    result = []
    for log in items:
        step = db.query(ProcessStep).filter(ProcessStep.id == log.process_step_id).first()
        factory = db.query(Factory).filter(Factory.id == log.factory_id).first()
        result.append({
            "id": str(log.id),
            "factory_id": str(log.factory_id),
            "factory_name": factory.name if factory else None,
            "process_step_id": str(log.process_step_id),
            "step_name": step.name if step else None,
            "previous_rate": float(log.previous_rate),
            "new_rate": float(log.new_rate),
            "ema_value": float(log.ema_value) if log.ema_value else None,
            "data_points": log.data_points,
            "trigger": log.trigger,
            "approved_by": str(log.approved_by) if log.approved_by else None,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        })

    return {"items": result, "total": len(result)}


# ── Calibration Action Endpoints ─────────────────────────────

class CalibrationRunInput(BaseModel):
    factory_id: str


class CalibrationApplyInput(BaseModel):
    step_id: str
    new_rate: float


@router.get("/calibration/status")
async def get_calibration_status(
    factory_id: UUID = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Current calibration status for all steps in a factory."""
    from business.services.tps_calibration import get_calibration_status
    return get_calibration_status(db, factory_id)


@router.post("/calibration/run")
async def run_calibration(
    data: CalibrationRunInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Manually trigger calibration analysis for a factory."""
    from business.services.tps_calibration import run_calibration
    suggestions = run_calibration(db, UUID(data.factory_id), auto_apply=False)
    db.commit()
    return {"suggestions": suggestions, "total": len(suggestions)}


@router.post("/calibration/apply")
async def apply_calibration_endpoint(
    data: CalibrationApplyInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Apply a calibration suggestion."""
    from business.services.tps_calibration import apply_calibration
    apply_calibration(
        db, UUID(data.step_id), data.new_rate,
        approved_by=current_user.id,
        trigger="manual",
    )
    db.commit()
    return {"status": "applied", "step_id": data.step_id, "new_rate": data.new_rate}


# ── Kiln Loading Typologies ───────────────────────────────────────────────

class TypologyCreate(BaseModel):
    name: str
    factory_id: UUID
    product_types: list[str] = []
    place_of_application: list[str] = []
    collections: list[str] = []
    methods: list[str] = []
    min_size_cm: Optional[float] = None
    max_size_cm: Optional[float] = None
    preferred_loading: str = "auto"
    min_firing_temp: Optional[int] = None
    max_firing_temp: Optional[int] = None
    shift_count: int = 2
    auto_calibrate: bool = False
    priority: int = 0
    notes: Optional[str] = None


class TypologyUpdate(BaseModel):
    name: Optional[str] = None
    product_types: Optional[list[str]] = None
    place_of_application: Optional[list[str]] = None
    collections: Optional[list[str]] = None
    methods: Optional[list[str]] = None
    min_size_cm: Optional[float] = None
    max_size_cm: Optional[float] = None
    preferred_loading: Optional[str] = None
    min_firing_temp: Optional[int] = None
    max_firing_temp: Optional[int] = None
    shift_count: Optional[int] = None
    auto_calibrate: Optional[bool] = None
    priority: Optional[int] = None
    notes: Optional[str] = None


class TypologyCalculateAllInput(BaseModel):
    factory_id: UUID


def _serialize_typology(t: KilnLoadingTypology, db: Session = None) -> dict:
    result = {
        "id": str(t.id),
        "factory_id": str(t.factory_id),
        "name": t.name,
        "product_types": t.product_types or [],
        "place_of_application": t.place_of_application or [],
        "collections": t.collections or [],
        "methods": t.methods or [],
        "min_size_cm": float(t.min_size_cm) if t.min_size_cm else None,
        "max_size_cm": float(t.max_size_cm) if t.max_size_cm else None,
        "preferred_loading": t.preferred_loading,
        "min_firing_temp": t.min_firing_temp,
        "max_firing_temp": t.max_firing_temp,
        "shift_count": t.shift_count or 2,
        "auto_calibrate": t.auto_calibrate or False,
        "is_active": t.is_active,
        "priority": t.priority or 0,
        "notes": t.notes,
    }
    if t.capacities:
        result["capacities"] = [{
            "kiln_id": str(c.resource_id),
            "kiln_name": c.resource.name if c.resource else None,
            "capacity_sqm": float(c.capacity_sqm) if c.capacity_sqm else None,
            "capacity_pcs": c.capacity_pcs,
            "loading_method": c.loading_method,
            "num_levels": c.num_levels,
            "ai_adjusted_sqm": float(c.ai_adjusted_sqm) if c.ai_adjusted_sqm else None,
            "ref_size": c.ref_size,
        } for c in t.capacities]
    return result


@router.get("/typologies")
async def list_typologies(
    factory_id: UUID = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """List all active typologies for a factory."""
    rows = (
        db.query(KilnLoadingTypology)
        .options(
            joinedload(KilnLoadingTypology.capacities)
            .joinedload(KilnTypologyCapacity.resource)
        )
        .filter(
            KilnLoadingTypology.factory_id == factory_id,
            KilnLoadingTypology.is_active.is_(True),
        )
        .order_by(KilnLoadingTypology.priority.desc(), KilnLoadingTypology.name)
        .all()
    )
    return {"items": [_serialize_typology(t) for t in rows]}


@router.post("/typologies/calculate-all")
async def calculate_all_typologies(
    data: TypologyCalculateAllInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Recalculate capacities for ALL typologies in a factory."""
    from business.services.typology_matcher import calculate_all_typology_capacities
    results = calculate_all_typology_capacities(db, data.factory_id)
    db.commit()
    return {"status": "ok", "recalculated": len(results), "results": results}


@router.post("/typologies")
async def create_typology(
    data: TypologyCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Create a new kiln loading typology."""
    typology = KilnLoadingTypology(
        factory_id=data.factory_id,
        name=data.name,
        product_types=data.product_types,
        place_of_application=data.place_of_application,
        collections=data.collections,
        methods=data.methods,
        min_size_cm=data.min_size_cm,
        max_size_cm=data.max_size_cm,
        preferred_loading=data.preferred_loading,
        min_firing_temp=data.min_firing_temp,
        max_firing_temp=data.max_firing_temp,
        shift_count=data.shift_count,
        auto_calibrate=data.auto_calibrate,
        priority=data.priority,
        notes=data.notes,
    )
    db.add(typology)
    db.commit()
    db.refresh(typology)
    return _serialize_typology(typology)


@router.get("/typologies/match")
async def match_typology(
    factory_id: UUID = Query(...),
    product_type: Optional[str] = Query(None),
    place: Optional[str] = Query(None),
    size: Optional[float] = Query(None),
    collection: Optional[str] = Query(None),
    method: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Find matching typology for given product parameters."""
    from business.services.typology_matcher import find_matching_typology
    result = find_matching_typology(
        db,
        factory_id=factory_id,
        product_type=product_type,
        place=place,
        size=size,
        collection=collection,
        method=method,
    )
    if not result:
        return {"match": None}
    return {"match": _serialize_typology(result)}


@router.get("/typologies/{typology_id}")
async def get_typology(
    typology_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Get a single typology with capacities."""
    t = (
        db.query(KilnLoadingTypology)
        .options(
            joinedload(KilnLoadingTypology.capacities)
            .joinedload(KilnTypologyCapacity.resource)
        )
        .filter(KilnLoadingTypology.id == typology_id)
        .first()
    )
    if not t:
        raise HTTPException(404, "Typology not found")
    return _serialize_typology(t)


@router.patch("/typologies/{typology_id}")
async def update_typology(
    typology_id: UUID,
    data: TypologyUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Partially update a typology."""
    t = db.query(KilnLoadingTypology).filter(KilnLoadingTypology.id == typology_id).first()
    if not t:
        raise HTTPException(404, "Typology not found")
    updates = data.model_dump(exclude_unset=True)
    for key, val in updates.items():
        setattr(t, key, val)
    db.commit()
    db.refresh(t)
    return _serialize_typology(t)


@router.delete("/typologies/{typology_id}")
async def delete_typology(
    typology_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Soft-delete a typology (set is_active=False)."""
    t = db.query(KilnLoadingTypology).filter(KilnLoadingTypology.id == typology_id).first()
    if not t:
        raise HTTPException(404, "Typology not found")
    t.is_active = False
    db.commit()
    return {"status": "deleted", "id": str(typology_id)}


@router.post("/typologies/{typology_id}/calculate")
async def calculate_typology(
    typology_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Recalculate capacities for a single typology across all kilns."""
    from business.services.typology_matcher import calculate_typology_for_kiln
    t = db.query(KilnLoadingTypology).filter(KilnLoadingTypology.id == typology_id).first()
    if not t:
        raise HTTPException(404, "Typology not found")
    results = calculate_typology_for_kiln(db, typology_id)
    db.commit()
    return {"status": "ok", "typology_id": str(typology_id), "results": results}


@router.get("/typologies/{typology_id}/capacities")
async def get_typology_capacities(
    typology_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Get per-kiln capacities for a typology."""
    t = db.query(KilnLoadingTypology).filter(KilnLoadingTypology.id == typology_id).first()
    if not t:
        raise HTTPException(404, "Typology not found")
    caps = (
        db.query(KilnTypologyCapacity)
        .options(joinedload(KilnTypologyCapacity.resource))
        .filter(KilnTypologyCapacity.typology_id == typology_id)
        .all()
    )
    return {
        "typology_id": str(typology_id),
        "capacities": [{
            "kiln_id": str(c.resource_id),
            "kiln_name": c.resource.name if c.resource else None,
            "capacity_sqm": float(c.capacity_sqm) if c.capacity_sqm else None,
            "capacity_pcs": c.capacity_pcs,
            "loading_method": c.loading_method,
            "num_levels": c.num_levels,
            "ai_adjusted_sqm": float(c.ai_adjusted_sqm) if c.ai_adjusted_sqm else None,
            "ref_size": c.ref_size,
        } for c in caps],
    }
