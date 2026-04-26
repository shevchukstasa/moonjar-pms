"""Finished Goods Stock router — CRUD + availability check across factories.
All mutations (create, update, delete) are audit-logged.

Storage model:
  - Tile area is NOT stored. Size is the source of truth (e.g. "9,5×9,5").
  - Quantity is in pieces. m² is computed on the fly from size × pieces.
  - price_per_m2 is stored but hidden from the default response (managers
    requesting it must pass include_price=true).
"""

import re
import uuid as uuid_mod
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import and_

from api.database import get_db
from api.auth import get_current_user
from api.roles import require_management
from api.models import FinishedGoodsStock, AuditLog

router = APIRouter()


_SIZE_SPLIT_RE = re.compile(r"\s*[×x*]\s*", re.IGNORECASE)


def _parse_size_to_tile_m2(size: str | None) -> float | None:
    """Parse a size string like "9,5×9,5" or "10x20" into the area of one tile in m²."""
    if not size:
        return None
    parts = _SIZE_SPLIT_RE.split(size.strip())
    if len(parts) != 2:
        return None
    try:
        w_cm = float(parts[0].replace(",", "."))
        h_cm = float(parts[1].replace(",", "."))
    except ValueError:
        return None
    if w_cm <= 0 or h_cm <= 0:
        return None
    return (w_cm / 100.0) * (h_cm / 100.0)


def _serialize_stock(s, include_price: bool = False) -> dict:
    tile_m2 = _parse_size_to_tile_m2(s.size)
    available_pcs = s.quantity - s.reserved_quantity
    out = {
        "id": str(s.id),
        "factory_id": str(s.factory_id),
        "factory_name": s.factory.name if s.factory else None,
        "color": s.color,
        "description": s.description,
        "size": s.size,
        "application": s.application,
        "collection": s.collection,
        "product_type": s.product_type.value if s.product_type else "tile",
        "quantity": s.quantity,
        "reserved_quantity": s.reserved_quantity,
        "available": available_pcs,
        "tile_m2": round(tile_m2, 6) if tile_m2 is not None else None,
        "quantity_m2": round(s.quantity * tile_m2, 4) if tile_m2 is not None else None,
        "available_m2": round(available_pcs * tile_m2, 4) if tile_m2 is not None else None,
        "location_note": s.location_note,
        "received_at": s.received_at.isoformat() if s.received_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }
    if include_price:
        out["price_per_m2"] = float(s.price_per_m2) if s.price_per_m2 is not None else None
    return out


# --- List ---
@router.get("")
async def list_finished_goods(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    factory_id: UUID | None = None,
    color: str | None = None,
    size: str | None = None,
    collection: str | None = None,
    product_type: str | None = None,
    application: str | None = None,
    location_note: str | None = None,
    include_price: bool = Query(False, description="Include price_per_m2 in response (hidden by default)"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(FinishedGoodsStock)

    if factory_id:
        query = query.filter(FinishedGoodsStock.factory_id == factory_id)
    if color:
        query = query.filter(FinishedGoodsStock.color.ilike(f"%{color}%"))
    if size:
        query = query.filter(FinishedGoodsStock.size == size)
    if collection:
        query = query.filter(FinishedGoodsStock.collection.ilike(f"%{collection}%"))
    if product_type:
        query = query.filter(FinishedGoodsStock.product_type == product_type)
    if application:
        query = query.filter(FinishedGoodsStock.application == application)
    if location_note:
        query = query.filter(FinishedGoodsStock.location_note == location_note)

    total = query.count()
    items = query.order_by(FinishedGoodsStock.updated_at.desc()).offset(
        (page - 1) * per_page
    ).limit(per_page).all()

    return {
        "items": [_serialize_stock(s, include_price=include_price) for s in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# --- Convert m² -> pcs for a specific stock row ---
@router.get("/{stock_id}/m2-to-pcs")
async def m2_to_pcs(
    stock_id: UUID,
    qty_m2: float = Query(..., gt=0, description="Requested quantity in m²"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Convert a manager's m² request into the number of tiles required for a given stock row."""
    stock = db.query(FinishedGoodsStock).filter(FinishedGoodsStock.id == stock_id).first()
    if not stock:
        raise HTTPException(404, "Stock record not found")
    tile_m2 = _parse_size_to_tile_m2(stock.size)
    if not tile_m2:
        raise HTTPException(422, f"Cannot parse tile area from size '{stock.size}'")
    pcs_exact = qty_m2 / tile_m2
    pcs_ceil = int(-(-qty_m2 // tile_m2))  # ceil
    available_pcs = stock.quantity - stock.reserved_quantity
    return {
        "stock_id": str(stock.id),
        "size": stock.size,
        "tile_m2": round(tile_m2, 6),
        "requested_m2": qty_m2,
        "pcs_exact": round(pcs_exact, 4),
        "pcs_required": pcs_ceil,
        "available_pcs": available_pcs,
        "available_m2": round(available_pcs * tile_m2, 4),
        "fits": pcs_ceil <= available_pcs,
    }


# --- Upsert ---
class StockUpsertInput(BaseModel):
    factory_id: str
    color: str
    description: str | None = None
    size: str
    application: str | None = None
    collection: str | None = None
    product_type: str = "tile"
    quantity: int
    reserved_quantity: int = 0
    location_note: str | None = None
    price_per_m2: Decimal | None = None
    received_at: date | None = None


@router.post("", status_code=201)
async def upsert_finished_goods(
    data: StockUpsertInput,
    include_price: bool = Query(False),
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Create or update finished goods stock (upsert by unique constraint).

    Unique key: (factory_id, color, size, collection, product_type, application, location_note).
    """
    existing = db.query(FinishedGoodsStock).filter(
        and_(
            FinishedGoodsStock.factory_id == UUID(data.factory_id),
            FinishedGoodsStock.color == data.color,
            FinishedGoodsStock.size == data.size,
            FinishedGoodsStock.collection == data.collection,
            FinishedGoodsStock.product_type == data.product_type,
            FinishedGoodsStock.application == data.application,
            FinishedGoodsStock.location_note == data.location_note,
        )
    ).first()

    if existing:
        old_qty = existing.quantity
        old_reserved = existing.reserved_quantity
        existing.quantity = data.quantity
        existing.reserved_quantity = data.reserved_quantity
        if data.description is not None:
            existing.description = data.description
        if data.price_per_m2 is not None:
            existing.price_per_m2 = data.price_per_m2
        if data.received_at is not None:
            existing.received_at = data.received_at
        existing.updated_at = datetime.now(timezone.utc)
        db.add(AuditLog(
            id=uuid_mod.uuid4(), action="update",
            table_name="finished_goods_stock", record_id=existing.id,
            user_id=current_user.id, user_email=current_user.email,
            old_data={"color": data.color, "size": data.size,
                      "application": data.application,
                      "location_note": data.location_note,
                      "old_qty": old_qty, "new_qty": data.quantity,
                      "old_reserved": old_reserved, "new_reserved": data.reserved_quantity},
        ))
        db.commit()
        db.refresh(existing)
        return _serialize_stock(existing, include_price=include_price)

    stock = FinishedGoodsStock(
        id=uuid_mod.uuid4(),
        factory_id=UUID(data.factory_id),
        color=data.color,
        description=data.description,
        size=data.size,
        application=data.application,
        collection=data.collection,
        product_type=data.product_type,
        quantity=data.quantity,
        reserved_quantity=data.reserved_quantity,
        location_note=data.location_note,
        price_per_m2=data.price_per_m2,
        received_at=data.received_at,
        updated_at=datetime.now(timezone.utc),
    )
    db.add(stock)
    db.add(AuditLog(
        id=uuid_mod.uuid4(), action="create",
        table_name="finished_goods_stock", record_id=stock.id,
        user_id=current_user.id, user_email=current_user.email,
        old_data={"color": data.color, "description": data.description,
                  "size": data.size, "application": data.application,
                  "collection": data.collection, "product_type": data.product_type,
                  "quantity": data.quantity, "location_note": data.location_note,
                  "received_at": data.received_at.isoformat() if data.received_at else None,
                  "factory_id": data.factory_id},
    ))
    db.commit()
    db.refresh(stock)
    return _serialize_stock(stock, include_price=include_price)


# --- Update ---
class StockUpdateInput(BaseModel):
    quantity: int | None = None
    reserved_quantity: int | None = None
    description: str | None = None
    application: str | None = None
    location_note: str | None = None
    price_per_m2: Decimal | None = None
    received_at: date | None = None


@router.patch("/{stock_id}")
async def update_finished_goods(
    stock_id: UUID,
    data: StockUpdateInput,
    include_price: bool = Query(False),
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    stock = db.query(FinishedGoodsStock).filter(FinishedGoodsStock.id == stock_id).first()
    if not stock:
        raise HTTPException(404, "Stock record not found")

    if data.quantity is not None:
        stock.quantity = data.quantity
    if data.reserved_quantity is not None:
        stock.reserved_quantity = data.reserved_quantity
    if data.description is not None:
        stock.description = data.description
    if data.application is not None:
        stock.application = data.application
    if data.location_note is not None:
        stock.location_note = data.location_note
    if data.price_per_m2 is not None:
        stock.price_per_m2 = data.price_per_m2
    if data.received_at is not None:
        stock.received_at = data.received_at
    stock.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(stock)
    return _serialize_stock(stock, include_price=include_price)


# --- Delete (write-off) ---
@router.delete("/{stock_id}", status_code=204)
async def delete_finished_goods(
    stock_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Delete / write-off a finished goods stock record. Audit-logged."""
    stock = db.query(FinishedGoodsStock).filter(FinishedGoodsStock.id == stock_id).first()
    if not stock:
        raise HTTPException(404, "Stock record not found")
    db.add(AuditLog(
        id=uuid_mod.uuid4(), action="delete",
        table_name="finished_goods_stock", record_id=stock.id,
        user_id=current_user.id, user_email=current_user.email,
        old_data={"color": stock.color, "size": stock.size,
                  "application": stock.application,
                  "location_note": stock.location_note,
                  "collection": stock.collection,
                  "quantity": stock.quantity, "reserved": stock.reserved_quantity,
                  "factory_id": str(stock.factory_id),
                  "factory_name": stock.factory.name if stock.factory else None},
    ))
    db.delete(stock)
    db.commit()
    return None
