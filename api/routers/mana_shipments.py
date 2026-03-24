"""CRUD router for mana_shipments."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.models import ManaShipment
from api.enums import ManaShipmentStatus
from api.schemas import ManaShipmentUpdate, ManaShipmentResponse

router = APIRouter()


@router.get("", response_model=dict)
async def list_mana_shipments(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    factory_id: UUID | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(ManaShipment)
    if factory_id:
        query = query.filter(ManaShipment.factory_id == factory_id)
    if status:
        query = query.filter(ManaShipment.status == status)
    query = query.order_by(ManaShipment.created_at.desc())
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return {
        "items": [ManaShipmentResponse.model_validate(item).model_dump(mode="json") for item in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/{item_id}", response_model=ManaShipmentResponse)
async def get_mana_shipment(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(ManaShipment).filter(ManaShipment.id == item_id).first()
    if not item:
        raise HTTPException(404, "ManaShipment not found")
    return item


@router.patch("/{item_id}", response_model=ManaShipmentResponse)
async def update_mana_shipment(
    item_id: UUID,
    data: ManaShipmentUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(ManaShipment).filter(ManaShipment.id == item_id).first()
    if not item:
        raise HTTPException(404, "ManaShipment not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


@router.post("/{item_id}/confirm", response_model=ManaShipmentResponse)
async def confirm_mana_shipment(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(ManaShipment).filter(ManaShipment.id == item_id).first()
    if not item:
        raise HTTPException(404, "ManaShipment not found")
    if item.status != ManaShipmentStatus.PENDING:
        raise HTTPException(400, f"Cannot confirm shipment with status '{item.status.value}'")
    item.status = ManaShipmentStatus.CONFIRMED
    item.confirmed_by = current_user.id
    item.confirmed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)
    return item


@router.post("/{item_id}/ship", response_model=ManaShipmentResponse)
async def ship_mana_shipment(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(ManaShipment).filter(ManaShipment.id == item_id).first()
    if not item:
        raise HTTPException(404, "ManaShipment not found")
    if item.status != ManaShipmentStatus.CONFIRMED:
        raise HTTPException(400, f"Cannot ship shipment with status '{item.status.value}'")
    item.status = ManaShipmentStatus.SHIPPED
    item.shipped_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
async def delete_mana_shipment(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(ManaShipment).filter(ManaShipment.id == item_id).first()
    if not item:
        raise HTTPException(404, "ManaShipment not found")
    if item.status == ManaShipmentStatus.SHIPPED:
        raise HTTPException(400, "Cannot delete a shipped shipment")
    db.delete(item)
    db.commit()
