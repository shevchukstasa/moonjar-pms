"""Schedule router — resources, batches, section schedules."""

from datetime import date, datetime, timezone
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from api.database import get_db
from api.auth import get_current_user, apply_factory_filter
from api.roles import require_management
from api.models import Resource, Batch, OrderPosition, ScheduleSlot
from api.enums import ResourceType, ResourceStatus, BatchStatus, BatchCreator, PositionStatus

router = APIRouter()


def _ev(val):
    return val.value if hasattr(val, "value") else str(val) if val else None


# Section → status mapping (same as positions router)
SECTION_STATUSES = {
    "glazing": [
        PositionStatus.PLANNED, PositionStatus.INSUFFICIENT_MATERIALS,
        PositionStatus.AWAITING_RECIPE, PositionStatus.AWAITING_STENCIL_SILKSCREEN,
        PositionStatus.AWAITING_COLOR_MATCHING, PositionStatus.ENGOBE_APPLIED,
        PositionStatus.ENGOBE_CHECK, PositionStatus.GLAZED,
        PositionStatus.PRE_KILN_CHECK, PositionStatus.SENT_TO_GLAZING,
    ],
    "firing": [
        PositionStatus.LOADED_IN_KILN, PositionStatus.FIRED,
        PositionStatus.REFIRE, PositionStatus.AWAITING_REGLAZE,
    ],
    "sorting": [
        PositionStatus.TRANSFERRED_TO_SORTING, PositionStatus.PACKED,
        PositionStatus.SENT_TO_QUALITY_CHECK, PositionStatus.QUALITY_CHECK_DONE,
        PositionStatus.READY_FOR_SHIPMENT, PositionStatus.BLOCKED_BY_QM,
    ],
}


def _serialize_resource(r) -> dict:
    return {
        "id": str(r.id),
        "name": r.name,
        "resource_type": _ev(r.resource_type),
        "factory_id": str(r.factory_id),
        "capacity_sqm": float(r.capacity_sqm) if r.capacity_sqm else None,
        "capacity_pcs": r.capacity_pcs,
        "num_levels": r.num_levels,
        "status": _ev(r.status),
        "kiln_dimensions_cm": r.kiln_dimensions_cm,
        "kiln_working_area_cm": r.kiln_working_area_cm,
        "kiln_multi_level": r.kiln_multi_level,
        "kiln_coefficient": float(r.kiln_coefficient) if r.kiln_coefficient else None,
        "kiln_type": r.kiln_type,
        "is_active": r.is_active,
    }


def _serialize_batch(b, db: Session) -> dict:
    positions = db.query(OrderPosition).filter(OrderPosition.batch_id == b.id).all()
    total_pcs = sum(p.quantity or 0 for p in positions)
    return {
        "id": str(b.id),
        "resource_id": str(b.resource_id),
        "resource_name": b.resource.name if b.resource else "",
        "factory_id": str(b.factory_id),
        "batch_date": str(b.batch_date) if b.batch_date else None,
        "status": _ev(b.status),
        "created_by": _ev(b.created_by),
        "notes": b.notes,
        "total_pcs": total_pcs,
        "positions_count": len(positions),
        "created_at": b.created_at.isoformat() if b.created_at else None,
    }


def _serialize_position_brief(p) -> dict:
    return {
        "id": str(p.id),
        "order_id": str(p.order_id),
        "order_number": p.order.order_number if p.order else "",
        "status": _ev(p.status),
        "color": p.color,
        "size": p.size,
        "quantity": p.quantity,
        "product_type": _ev(p.product_type),
        "delay_hours": float(p.delay_hours) if p.delay_hours else 0,
        "priority_order": p.priority_order,
        "batch_id": str(p.batch_id) if p.batch_id else None,
    }


class BatchCreateInput(BaseModel):
    resource_id: str
    factory_id: str
    batch_date: date
    position_ids: list[str] = []
    notes: Optional[str] = None


# --- Endpoints ---

@router.get("/resources")
async def list_resources(
    factory_id: UUID | None = None,
    resource_type: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(Resource).filter(Resource.is_active == True)
    if factory_id:
        query = query.filter(Resource.factory_id == factory_id)
    if resource_type:
        query = query.filter(Resource.resource_type == resource_type)
    resources = query.order_by(Resource.name).all()
    return {"items": [_serialize_resource(r) for r in resources], "total": len(resources)}


@router.get("/batches")
async def list_batches(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    factory_id: UUID | None = None,
    resource_id: UUID | None = None,
    status: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(Batch)
    if factory_id:
        query = query.filter(Batch.factory_id == factory_id)
    if resource_id:
        query = query.filter(Batch.resource_id == resource_id)
    if status:
        query = query.filter(Batch.status == status)
    if date_from:
        query = query.filter(Batch.batch_date >= date_from)
    if date_to:
        query = query.filter(Batch.batch_date <= date_to)

    total = query.count()
    batches = query.order_by(Batch.batch_date.desc()).offset(
        (page - 1) * per_page
    ).limit(per_page).all()

    return {
        "items": [_serialize_batch(b, db) for b in batches],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.post("/batches", status_code=201)
async def create_batch(
    data: BatchCreateInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    batch = Batch(
        resource_id=UUID(data.resource_id),
        factory_id=UUID(data.factory_id),
        batch_date=data.batch_date,
        status=BatchStatus.PLANNED,
        created_by=BatchCreator.MANUAL,
        notes=data.notes,
    )
    db.add(batch)
    db.flush()

    # Assign positions to batch
    for pid in data.position_ids:
        pos = db.query(OrderPosition).filter(OrderPosition.id == UUID(pid)).first()
        if pos:
            pos.batch_id = batch.id
            pos.resource_id = UUID(data.resource_id)

    db.commit()
    db.refresh(batch)
    return _serialize_batch(batch, db)


@router.get("/glazing-schedule")
async def get_glazing_schedule(
    factory_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(OrderPosition).filter(
        OrderPosition.status.in_(SECTION_STATUSES["glazing"])
    )
    if factory_id:
        query = query.filter(OrderPosition.factory_id == factory_id)
    positions = query.order_by(OrderPosition.priority_order, OrderPosition.created_at).all()
    return {"items": [_serialize_position_brief(p) for p in positions], "total": len(positions)}


@router.get("/firing-schedule")
async def get_firing_schedule(
    factory_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(OrderPosition).filter(
        OrderPosition.status.in_(SECTION_STATUSES["firing"])
    )
    if factory_id:
        query = query.filter(OrderPosition.factory_id == factory_id)
    positions = query.order_by(OrderPosition.priority_order, OrderPosition.created_at).all()
    return {"items": [_serialize_position_brief(p) for p in positions], "total": len(positions)}


@router.get("/sorting-schedule")
async def get_sorting_schedule(
    factory_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(OrderPosition).filter(
        OrderPosition.status.in_(SECTION_STATUSES["sorting"])
    )
    if factory_id:
        query = query.filter(OrderPosition.factory_id == factory_id)
    positions = query.order_by(OrderPosition.priority_order, OrderPosition.created_at).all()
    return {"items": [_serialize_position_brief(p) for p in positions], "total": len(positions)}


@router.get("/kiln-schedule")
async def get_kiln_schedule(
    factory_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Batches grouped by kiln."""
    query = db.query(Resource).filter(
        Resource.resource_type == ResourceType.KILN,
        Resource.is_active == True,
    )
    if factory_id:
        query = query.filter(Resource.factory_id == factory_id)
    kilns = query.order_by(Resource.name).all()

    result = []
    for kiln in kilns:
        batches = db.query(Batch).filter(
            Batch.resource_id == kiln.id,
            Batch.status.in_([BatchStatus.PLANNED, BatchStatus.IN_PROGRESS]),
        ).order_by(Batch.batch_date).all()

        result.append({
            "kiln": _serialize_resource(kiln),
            "batches": [_serialize_batch(b, db) for b in batches],
        })

    return {"items": result, "total": len(result)}
