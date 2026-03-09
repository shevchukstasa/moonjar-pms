"""CRUD router for suppliers (auto-generated)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.models import Supplier
from api.schemas import SupplierCreate, SupplierUpdate, SupplierResponse

router = APIRouter()


def _serialize_supplier(s) -> dict:
    return {
        "id": str(s.id),
        "name": s.name,
        "contact_person": s.contact_person,
        "phone": s.phone,
        "email": s.email,
        "address": s.address,
        "material_types": s.material_types,
        "default_lead_time_days": s.default_lead_time_days,
        "rating": float(s.rating) if s.rating else None,
        "notes": s.notes,
        "is_active": s.is_active,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


@router.get("", response_model=dict)
async def list_suppliers(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(Supplier)
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return {"items": [_serialize_supplier(s) for s in items], "total": total, "page": page, "per_page": per_page}


@router.get("/{item_id}")
async def get_suppliers_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(Supplier).filter(Supplier.id == item_id).first()
    if not item:
        raise HTTPException(404, "Supplier not found")
    return _serialize_supplier(item)


@router.post("", status_code=201)
async def create_suppliers_item(
    data: SupplierCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = Supplier(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_supplier(item)


@router.patch("/{item_id}")
async def update_suppliers_item(
    item_id: UUID,
    data: SupplierUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(Supplier).filter(Supplier.id == item_id).first()
    if not item:
        raise HTTPException(404, "Supplier not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return _serialize_supplier(item)


@router.delete("/{item_id}", status_code=204)
async def delete_suppliers_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(Supplier).filter(Supplier.id == item_id).first()
    if not item:
        raise HTTPException(404, "Supplier not found")
    db.delete(item)
    db.commit()
