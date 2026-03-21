"""Finished Goods Stock router — CRUD + availability check across factories.
All mutations (create, update, delete) are audit-logged."""

import uuid as uuid_mod
from datetime import datetime, timezone
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


def _serialize_stock(s) -> dict:
    return {
        "id": str(s.id),
        "factory_id": str(s.factory_id),
        "factory_name": s.factory.name if s.factory else None,
        "color": s.color,
        "size": s.size,
        "collection": s.collection,
        "product_type": s.product_type.value if s.product_type else "tile",
        "quantity": s.quantity,
        "reserved_quantity": s.reserved_quantity,
        "available": s.quantity - s.reserved_quantity,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


# --- List ---
@router.get("")
async def list_finished_goods(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    factory_id: UUID | None = None,
    color: str | None = None,
    size: str | None = None,
    collection: str | None = None,
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

    total = query.count()
    items = query.order_by(FinishedGoodsStock.updated_at.desc()).offset(
        (page - 1) * per_page
    ).limit(per_page).all()

    return {
        "items": [_serialize_stock(s) for s in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# --- Upsert ---
class StockUpsertInput(BaseModel):
    factory_id: str
    color: str
    size: str
    collection: str | None = None
    product_type: str = "tile"
    quantity: int
    reserved_quantity: int = 0


@router.post("", status_code=201)
async def upsert_finished_goods(
    data: StockUpsertInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Create or update finished goods stock (upsert by unique constraint)."""
    existing = db.query(FinishedGoodsStock).filter(
        and_(
            FinishedGoodsStock.factory_id == UUID(data.factory_id),
            FinishedGoodsStock.color == data.color,
            FinishedGoodsStock.size == data.size,
            FinishedGoodsStock.collection == data.collection,
            FinishedGoodsStock.product_type == data.product_type,
        )
    ).first()

    if existing:
        old_qty = existing.quantity
        old_reserved = existing.reserved_quantity
        existing.quantity = data.quantity
        existing.reserved_quantity = data.reserved_quantity
        existing.updated_at = datetime.now(timezone.utc)
        # Audit log
        db.add(AuditLog(
            id=uuid_mod.uuid4(), action="update",
            table_name="finished_goods_stock", record_id=existing.id,
            user_id=current_user.id, user_email=current_user.email,
            old_data={"color": data.color, "size": data.size,
                      "old_qty": old_qty, "new_qty": data.quantity,
                      "old_reserved": old_reserved, "new_reserved": data.reserved_quantity},
        ))
        db.commit()
        db.refresh(existing)
        return _serialize_stock(existing)

    stock = FinishedGoodsStock(
        id=uuid_mod.uuid4(),
        factory_id=UUID(data.factory_id),
        color=data.color,
        size=data.size,
        collection=data.collection,
        product_type=data.product_type,
        quantity=data.quantity,
        reserved_quantity=data.reserved_quantity,
        updated_at=datetime.now(timezone.utc),
    )
    db.add(stock)
    # Audit log
    db.add(AuditLog(
        id=uuid_mod.uuid4(), action="create",
        table_name="finished_goods_stock", record_id=stock.id,
        user_id=current_user.id, user_email=current_user.email,
        old_data={"color": data.color, "size": data.size, "collection": data.collection,
                  "product_type": data.product_type, "quantity": data.quantity,
                  "factory_id": data.factory_id},
    ))
    db.commit()
    db.refresh(stock)
    return _serialize_stock(stock)


# --- Update ---
class StockUpdateInput(BaseModel):
    quantity: int | None = None
    reserved_quantity: int | None = None


@router.patch("/{stock_id}")
async def update_finished_goods(
    stock_id: UUID,
    data: StockUpdateInput,
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
    stock.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(stock)
    return _serialize_stock(stock)


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
    # Audit log before delete
    db.add(AuditLog(
        id=uuid_mod.uuid4(), action="delete",
        table_name="finished_goods_stock", record_id=stock.id,
        user_id=current_user.id, user_email=current_user.email,
        old_data={"color": stock.color, "size": stock.size, "collection": stock.collection,
                  "quantity": stock.quantity, "reserved": stock.reserved_quantity,
                  "factory_id": str(stock.factory_id),
                  "factory_name": stock.factory.name if stock.factory else None},
    ))
    db.delete(stock)
    db.commit()
    return None


# --- Availability Check (cross-factory) ---
@router.get("/availability")
async def check_availability(
    color: str = Query(...),
    size: str = Query(...),
    needed: int = Query(..., ge=1),
    factory_id: UUID | None = None,
    collection: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Check finished goods availability across all factories.

    Returns availability per factory, total, and the best single factory.
    """
    query = db.query(FinishedGoodsStock).filter(
        FinishedGoodsStock.color == color,
        FinishedGoodsStock.size == size,
    )
    if collection:
        query = query.filter(FinishedGoodsStock.collection == collection)

    all_stocks = query.all()

    # Build per-factory availability
    factories_availability = []
    home_factory_info = None

    for s in all_stocks:
        available = max(0, s.quantity - s.reserved_quantity)
        entry = {
            "factory_id": str(s.factory_id),
            "factory_name": s.factory.name if s.factory else "Unknown",
            "available": available,
            "quantity": s.quantity,
            "reserved": s.reserved_quantity,
        }
        factories_availability.append(entry)

        if factory_id and s.factory_id == factory_id:
            home_factory_info = entry

    # Sort by available descending
    factories_availability.sort(key=lambda x: x["available"], reverse=True)

    total_available = sum(f["available"] for f in factories_availability)
    home_available = home_factory_info["available"] if home_factory_info else 0
    best = factories_availability[0] if factories_availability else None

    return {
        "needed": needed,
        "home_factory": home_factory_info,
        "all_factories": factories_availability,
        "total_available": total_available,
        "sufficient_on_home": home_available >= needed,
        "sufficient_total": total_available >= needed,
        "best_single_factory": best if best and (not factory_id or best["factory_id"] != str(factory_id)) else None,
    }
