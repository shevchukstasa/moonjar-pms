"""
Batches router — auto-formation, lifecycle management, CRUD.

Endpoints:
  POST /api/batches/auto-form   — auto-form batches for a factory
  GET  /api/batches             — list batches (with filters)
  GET  /api/batches/{id}        — batch detail with positions
  POST /api/batches/{id}/start  — mark batch as in_progress
  POST /api/batches/{id}/complete — mark batch as completed
  POST /api/batches/{id}/confirm — PM confirms a suggested batch
  POST /api/batches/{id}/reject  — PM rejects a suggested batch
"""

from datetime import date, datetime
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func

from api.database import get_db
from api.auth import get_current_user, apply_factory_filter
from api.roles import require_management
from api.models import Batch, OrderPosition, Resource, PositionPhoto
from api.schemas import BatchCreate, BatchUpdate, BatchResponse
from api.enums import BatchStatus, ResourceType

router = APIRouter()


# ────────────────────────────────────────────────────────────────
# Request / Response schemas
# ────────────────────────────────────────────────────────────────

class BatchAutoFormRequest(BaseModel):
    factory_id: UUID
    target_date: Optional[date] = None
    mode: Optional[str] = "auto"  # "auto" or "suggest"


class BatchAutoFormResponse(BaseModel):
    batches_created: int
    positions_assigned: int
    details: list[dict]


class BatchConfirmRequest(BaseModel):
    notes: Optional[str] = None
    remove_position_ids: Optional[list[UUID]] = None
    add_position_ids: Optional[list[UUID]] = None
    batch_date: Optional[date] = None


class BatchPositionResponse(BaseModel):
    id: UUID
    order_id: UUID
    position_number: Optional[int] = None
    split_index: Optional[int] = None
    color: str
    size: str
    collection: Optional[str] = None
    product_type: Optional[str] = None
    quantity: int
    quantity_sqm: Optional[float] = None
    glazeable_sqm: Optional[float] = None
    status: str
    priority_order: Optional[int] = None


class BatchDetailResponse(BaseModel):
    id: UUID
    resource_id: UUID
    resource_name: Optional[str] = None
    factory_id: UUID
    batch_date: date
    status: str
    created_by: str
    notes: Optional[str] = None
    firing_profile_id: Optional[UUID] = None
    target_temperature: Optional[int] = None
    positions: list[BatchPositionResponse] = []
    positions_count: int = 0
    total_area_sqm: Optional[float] = None
    kiln_capacity_sqm: Optional[float] = None
    loading_plan: Optional[dict] = None
    created_at: Optional[str | datetime] = None
    updated_at: Optional[str | datetime] = None

    model_config = {"from_attributes": True}


def _ev(val):
    return val.value if hasattr(val, "value") else str(val) if val else None


def _serialize_position(pos: OrderPosition) -> dict:
    return {
        "id": pos.id,
        "order_id": pos.order_id,
        "position_number": pos.position_number,
        "split_index": pos.split_index,
        "color": pos.color,
        "size": pos.size,
        "collection": pos.collection,
        "product_type": _ev(pos.product_type),
        "quantity": pos.quantity,
        "quantity_sqm": float(pos.quantity_sqm) if pos.quantity_sqm else None,
        "glazeable_sqm": float(pos.glazeable_sqm) if pos.glazeable_sqm else None,
        "status": _ev(pos.status),
        "priority_order": pos.priority_order,
    }


# ────────────────────────────────────────────────────────────────
# POST /api/batches/auto-form
# ────────────────────────────────────────────────────────────────

@router.post("/auto-form", response_model=BatchAutoFormResponse)
async def auto_form_batches(
    data: BatchAutoFormRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """
    Automatically form batches for a factory.

    Collects kiln-ready positions, groups by temperature,
    assigns to kilns, and creates batch records.
    """
    from business.services.batch_formation import suggest_or_create_batches

    try:
        results = suggest_or_create_batches(
            db=db,
            factory_id=data.factory_id,
            target_date=data.target_date,
            mode=data.mode or "auto",
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    total_positions = sum(r["positions_count"] for r in results)

    return BatchAutoFormResponse(
        batches_created=len(results),
        positions_assigned=total_positions,
        details=results,
    )


# ────────────────────────────────────────────────────────────────
# POST /api/batches/capacity-preview
# ────────────────────────────────────────────────────────────────

class CapacityPreviewRequest(BaseModel):
    position_id: UUID
    kiln_id: UUID


@router.post("/capacity-preview")
async def preview_capacity(
    data: CapacityPreviewRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Preview how a position would load in a specific kiln.

    Uses geometry-based capacity calculations (edge vs flat optimization,
    per-product validation, filler integration) from kiln/capacity.py.

    Returns loading plan details including:
    - Optimal and alternative loading methods (flat/edge)
    - Pieces per level, number of levels, total pieces
    - Area utilization
    - Filler tile info (for small kilns)
    """
    position = db.query(OrderPosition).filter(
        OrderPosition.id == data.position_id,
    ).first()
    if not position:
        raise HTTPException(404, "Position not found")

    kiln = db.query(Resource).filter(
        Resource.id == data.kiln_id,
        Resource.resource_type == ResourceType.KILN.value,
    ).first()
    if not kiln:
        raise HTTPException(404, "Kiln not found")

    from business.services.batch_formation import preview_position_in_kiln

    try:
        result = preview_position_in_kiln(db, position, kiln)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Capacity calculation failed: {str(e)}",
        )

    return {
        "position_id": str(data.position_id),
        "kiln_id": str(data.kiln_id),
        "kiln_name": kiln.name,
        **result,
    }


# ────────────────────────────────────────────────────────────────
# GET /api/batches
# ────────────────────────────────────────────────────────────────

@router.get("", response_model=dict)
async def list_batches(
    factory_id: Optional[UUID] = None,
    status: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    resource_id: Optional[UUID] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List batches with optional filters."""
    query = db.query(Batch)

    # Apply factory filter based on user role
    query = apply_factory_filter(query, current_user, factory_id, Batch)

    if status:
        query = query.filter(Batch.status == status)

    if date_from:
        query = query.filter(Batch.batch_date >= date_from)

    if date_to:
        query = query.filter(Batch.batch_date <= date_to)

    if resource_id:
        query = query.filter(Batch.resource_id == resource_id)

    total = query.count()

    batches = (
        query.order_by(Batch.batch_date.desc(), Batch.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    items = []
    for batch in batches:
        positions_count = db.query(sa_func.count(OrderPosition.id)).filter(
            OrderPosition.batch_id == batch.id,
        ).scalar() or 0

        kiln = db.query(Resource).filter(Resource.id == batch.resource_id).first()

        item = BatchResponse.model_validate(batch).model_dump(mode="json")
        item["resource_name"] = kiln.name if kiln else None
        item["positions_count"] = positions_count
        items.append(item)

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# ────────────────────────────────────────────────────────────────
# GET /api/batches/{id}
# ────────────────────────────────────────────────────────────────

@router.get("/{batch_id}", response_model=BatchDetailResponse)
async def get_batch_detail(
    batch_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get batch detail with all assigned positions."""
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(404, "Batch not found")

    positions = db.query(OrderPosition).filter(
        OrderPosition.batch_id == batch_id,
    ).order_by(
        OrderPosition.priority_order.desc(),
        OrderPosition.position_number,
        OrderPosition.split_index,
    ).all()

    kiln = db.query(Resource).filter(Resource.id == batch.resource_id).first()

    # Calculate total area
    from business.services.batch_formation import _get_position_area_sqm
    total_area = sum(float(_get_position_area_sqm(p)) for p in positions)

    # Extract loading plan from metadata_json if available
    loading_plan = None
    if batch.metadata_json and isinstance(batch.metadata_json, dict):
        loading_plan = batch.metadata_json.get("loading_plan")

    return {
        "id": batch.id,
        "resource_id": batch.resource_id,
        "resource_name": kiln.name if kiln else None,
        "factory_id": batch.factory_id,
        "batch_date": batch.batch_date,
        "status": _ev(batch.status),
        "created_by": _ev(batch.created_by),
        "notes": batch.notes,
        "firing_profile_id": batch.firing_profile_id,
        "target_temperature": batch.target_temperature,
        "positions": [_serialize_position(p) for p in positions],
        "positions_count": len(positions),
        "total_area_sqm": round(total_area, 4),
        "kiln_capacity_sqm": float(kiln.capacity_sqm) if kiln and kiln.capacity_sqm else None,
        "loading_plan": loading_plan,
        "created_at": batch.created_at,
        "updated_at": batch.updated_at,
    }


# ────────────────────────────────────────────────────────────────
# POST /api/batches/{id}/start
# ────────────────────────────────────────────────────────────────

@router.post("/{batch_id}/start")
async def start_batch_endpoint(
    batch_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """
    Mark batch as in_progress (kiln loaded, firing started).
    All positions in the batch transition to LOADED_IN_KILN.
    """
    from business.services.batch_formation import start_batch

    try:
        batch = start_batch(db, batch_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    positions_count = db.query(sa_func.count(OrderPosition.id)).filter(
        OrderPosition.batch_id == batch_id,
    ).scalar() or 0

    return {
        "id": batch.id,
        "status": _ev(batch.status),
        "message": f"Batch started with {positions_count} positions",
        "positions_count": positions_count,
    }


# ────────────────────────────────────────────────────────────────
# POST /api/batches/{id}/complete
# ────────────────────────────────────────────────────────────────

@router.post("/{batch_id}/complete")
async def complete_batch_endpoint(
    batch_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """
    Mark batch as completed (firing done).
    All positions transition to FIRED and route to next status.
    """
    from business.services.batch_formation import complete_batch

    try:
        batch = complete_batch(db, batch_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    positions = db.query(OrderPosition).filter(
        OrderPosition.batch_id == batch_id,
    ).all()

    return {
        "id": batch.id,
        "status": _ev(batch.status),
        "message": f"Batch completed, {len(positions)} positions fired",
        "positions_count": len(positions),
        "position_statuses": [
            {"id": p.id, "status": _ev(p.status)} for p in positions
        ],
    }


# ────────────────────────────────────────────────────────────────
# POST /api/batches/{id}/confirm
# ────────────────────────────────────────────────────────────────

@router.post("/{batch_id}/confirm")
async def confirm_batch_endpoint(
    batch_id: UUID,
    data: Optional[BatchConfirmRequest] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """PM confirms a suggested batch (with optional adjustments)."""
    from business.services.batch_formation import pm_confirm_batch

    adjustments = None
    if data:
        adjustments = {}
        if data.notes is not None:
            adjustments["notes"] = data.notes
        if data.remove_position_ids:
            adjustments["remove_position_ids"] = data.remove_position_ids
        if data.add_position_ids:
            adjustments["add_position_ids"] = data.add_position_ids
        if data.batch_date is not None:
            adjustments["batch_date"] = data.batch_date

    try:
        batch = pm_confirm_batch(db, batch_id, current_user.id, adjustments)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "id": batch.id,
        "status": _ev(batch.status),
        "message": "Batch confirmed",
    }


# ────────────────────────────────────────────────────────────────
# POST /api/batches/{id}/reject
# ────────────────────────────────────────────────────────────────

@router.post("/{batch_id}/reject")
async def reject_batch_endpoint(
    batch_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """PM rejects a suggested batch. Positions are unassigned, batch deleted."""
    from business.services.batch_formation import pm_reject_batch

    try:
        pm_reject_batch(db, batch_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"message": "Batch rejected and deleted"}


# ────────────────────────────────────────────────────────────────
# POST /api/batches  (manual creation)
# ────────────────────────────────────────────────────────────────

@router.post("", response_model=BatchResponse, status_code=201)
async def create_batch(
    data: BatchCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Manually create a batch."""
    from api.enums import BatchCreator, ResourceStatus

    # Block batch creation when kiln is under maintenance
    kiln = db.query(Resource).filter(
        Resource.id == data.resource_id,
        Resource.resource_type == ResourceType.KILN,
    ).first()
    if kiln and kiln.status in (
        ResourceStatus.MAINTENANCE_PLANNED,
        ResourceStatus.MAINTENANCE_EMERGENCY,
    ):
        raise HTTPException(
            400,
            f"Kiln '{kiln.name}' is currently under {kiln.status.value} — "
            "cannot create a batch. Set kiln to 'active' first.",
        )

    batch = Batch(
        resource_id=data.resource_id,
        factory_id=data.factory_id,
        batch_date=data.batch_date,
        status=BatchStatus(data.status) if data.status else BatchStatus.PLANNED,
        created_by=BatchCreator.MANUAL,
        notes=data.notes,
        firing_profile_id=data.firing_profile_id,
        target_temperature=data.target_temperature,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


# ────────────────────────────────────────────────────────────────
# PATCH /api/batches/{id}
# ────────────────────────────────────────────────────────────────

@router.patch("/{batch_id}", response_model=BatchResponse)
async def update_batch(
    batch_id: UUID,
    data: BatchUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Update batch fields."""
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(404, "Batch not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        if key == "status" and val:
            val = BatchStatus(val)
        setattr(batch, key, val)

    db.commit()
    db.refresh(batch)
    return batch


# ────────────────────────────────────────────────────────────────
# POST /api/batches/{id}/photos — add firing photo
# ────────────────────────────────────────────────────────────────

class BatchPhotoCreate(BaseModel):
    photo_url: str
    position_id: Optional[UUID] = None
    caption: Optional[str] = None


@router.post("/{batch_id}/photos")
async def add_batch_photo(
    batch_id: UUID,
    data: BatchPhotoCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Upload a firing photo for a batch (after kiln unloading)."""
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(404, "Batch not found")

    import uuid as uuid_mod
    photo = PositionPhoto(
        id=uuid_mod.uuid4(),
        position_id=data.position_id,
        factory_id=batch.factory_id,
        batch_id=batch.id,
        photo_type="firing",
        photo_url=data.photo_url,
        caption=data.caption,
        uploaded_by_user_id=current_user.id,
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)

    return {
        "id": str(photo.id),
        "batch_id": str(batch_id),
        "photo_url": photo.photo_url,
        "caption": photo.caption,
        "created_at": photo.created_at.isoformat() if photo.created_at else None,
    }


@router.get("/{batch_id}/photos")
async def list_batch_photos(
    batch_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get all photos for a batch."""
    photos = db.query(PositionPhoto).filter(
        PositionPhoto.batch_id == batch_id,
    ).order_by(PositionPhoto.created_at.desc()).all()

    return {
        "items": [
            {
                "id": str(p.id),
                "position_id": str(p.position_id) if p.position_id else None,
                "photo_url": p.photo_url or (f"/api/telegram/photo/{p.telegram_file_id}" if p.telegram_file_id else None),
                "caption": p.caption,
                "photo_type": p.photo_type,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in photos
        ],
        "total": len(photos),
    }
