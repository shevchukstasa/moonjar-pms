"""Packing photos router — CRUD for order_packing_photos."""

from uuid import UUID
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from api.database import get_db
from api.auth import get_current_user
from api.roles import require_sorting
from api.models import OrderPackingPhoto, OrderPosition, ProductionOrder

router = APIRouter()


def _serialize_photo(p) -> dict:
    return {
        "id": str(p.id),
        "order_id": str(p.order_id),
        "position_id": str(p.position_id) if p.position_id else None,
        "photo_url": p.photo_url,
        "uploaded_by": str(p.uploaded_by) if p.uploaded_by else None,
        "uploaded_at": p.uploaded_at.isoformat() if p.uploaded_at else None,
        "notes": p.notes,
        "order_number": p.order.order_number if p.order else None,
        "uploader_name": (
            p.uploaded_by_rel.name if p.uploaded_by_rel else None
        ),
    }


@router.get("/")
async def list_packing_photos(
    position_id: UUID | None = None,
    order_id: UUID | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(OrderPackingPhoto).options(
        joinedload(OrderPackingPhoto.order),
        joinedload(OrderPackingPhoto.uploaded_by_rel),
    )
    if position_id:
        query = query.filter(OrderPackingPhoto.position_id == position_id)
    if order_id:
        query = query.filter(OrderPackingPhoto.order_id == order_id)
    total = query.count()
    items = (
        query.order_by(OrderPackingPhoto.uploaded_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return {
        "items": [_serialize_photo(p) for p in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.post("/", status_code=201)
async def create_packing_photo(
    data: dict,
    db: Session = Depends(get_db),
    current_user=Depends(require_sorting),
):
    order_id = data.get("order_id")
    position_id = data.get("position_id")
    photo_url = data.get("photo_url")
    notes = data.get("notes")

    if not order_id or not photo_url:
        raise HTTPException(400, "order_id and photo_url are required")

    # Validate order exists
    order = db.query(ProductionOrder).filter(
        ProductionOrder.id == order_id
    ).first()
    if not order:
        raise HTTPException(404, "Order not found")

    # Validate position exists (if provided)
    if position_id:
        pos = db.query(OrderPosition).filter(
            OrderPosition.id == position_id
        ).first()
        if not pos:
            raise HTTPException(404, "Position not found")

    photo = OrderPackingPhoto(
        order_id=order_id,
        position_id=position_id,
        photo_url=photo_url,
        uploaded_by=current_user.id,
        uploaded_at=datetime.now(timezone.utc),
        notes=notes,
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return _serialize_photo(photo)


@router.delete("/{photo_id}", status_code=204)
async def delete_packing_photo(
    photo_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_sorting),
):
    photo = db.query(OrderPackingPhoto).filter(
        OrderPackingPhoto.id == photo_id
    ).first()
    if not photo:
        raise HTTPException(404, "Photo not found")
    # Only the uploader or management can delete
    if str(photo.uploaded_by) != str(current_user.id) and current_user.role not in (
        "owner", "administrator", "production_manager"
    ):
        raise HTTPException(403, "Not allowed to delete this photo")
    db.delete(photo)
    db.commit()
