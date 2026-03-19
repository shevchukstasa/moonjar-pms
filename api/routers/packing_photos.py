"""Packing photos router — CRUD for order_packing_photos."""

import logging
from uuid import UUID
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session, joinedload

from api.database import get_db
from api.auth import get_current_user
from api.roles import require_sorting
from api.models import OrderPackingPhoto, OrderPosition, ProductionOrder

logger = logging.getLogger("moonjar.packing_photos")

router = APIRouter()


class PackingPhotoCreate(BaseModel):
    order_id: UUID
    position_id: Optional[UUID] = None
    photo_url: str
    notes: Optional[str] = None

    @field_validator("photo_url")
    @classmethod
    def validate_photo_url(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("photo_url is required")
        if not v.startswith(("http://", "https://")):
            raise ValueError("photo_url must be a valid HTTP(S) URL")
        if len(v) > 2048:
            raise ValueError("photo_url too long (max 2048 chars)")
        return v


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


@router.get("")
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


@router.post("", status_code=201)
async def create_packing_photo(
    data: PackingPhotoCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_sorting),
):
    # Validate order exists
    order = db.query(ProductionOrder).filter(
        ProductionOrder.id == data.order_id
    ).first()
    if not order:
        raise HTTPException(404, "Order not found")

    # Validate position exists (if provided)
    if data.position_id:
        pos = db.query(OrderPosition).filter(
            OrderPosition.id == data.position_id
        ).first()
        if not pos:
            raise HTTPException(404, "Position not found")

    photo = OrderPackingPhoto(
        order_id=data.order_id,
        position_id=data.position_id,
        photo_url=data.photo_url,
        uploaded_by=current_user.id,
        uploaded_at=datetime.now(timezone.utc),
        notes=data.notes,
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


@router.post("/upload", status_code=201)
async def upload_packing_photo(
    order_id: UUID = Form(...),
    file: UploadFile = File(...),
    position_id: Optional[UUID] = Form(None),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_sorting),
):
    """
    Upload a packing photo file directly (multipart form).
    Stores in Supabase Storage (or local fallback) and creates DB record.
    """
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

    # Read file bytes
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(400, "Empty file")

    if len(image_bytes) > 10 * 1024 * 1024:  # 10 MB limit
        raise HTTPException(400, "File too large (max 10 MB)")

    # Determine factory_id from order or position
    factory_id = None
    if position_id:
        pos = db.query(OrderPosition).filter(OrderPosition.id == position_id).first()
        if pos:
            factory_id = pos.factory_id
    if not factory_id:
        factory_id = order.factory_id

    # Upload to Supabase / local storage
    from business.services.photo_storage import upload_photo

    try:
        storage_result = await upload_photo(
            image_bytes=image_bytes,
            category="packing",
            factory_id=factory_id,
            related_id=order_id,
            filename=file.filename,
        )
        photo_url = storage_result["url"]
    except Exception as e:
        logger.error(f"Photo upload failed: {e}")
        raise HTTPException(500, f"Photo upload failed: {e}")

    # Create DB record
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

    result = _serialize_photo(photo)
    result["storage"] = storage_result.get("storage", "unknown")
    result["storage_path"] = storage_result.get("path")
    return result
