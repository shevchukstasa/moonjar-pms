"""CRUD router for suppliers — with subgroup links and safe delete."""

from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.models import (
    Supplier, SupplierSubgroup, Material, MaterialPurchaseRequest,
    DefectRecord, StoneDefectCoefficient, SupplierDefectReport,
    MaterialSubgroup, MaterialGroup,
)
from api.schemas import SupplierCreate, SupplierUpdate, SupplierResponse

router = APIRouter()


def _serialize_supplier(s, db: Session) -> dict:
    # Load linked subgroups
    links = (
        db.query(SupplierSubgroup.subgroup_id)
        .filter(SupplierSubgroup.supplier_id == s.id)
        .all()
    )
    sg_ids = [str(row[0]) for row in links]
    sg_names: list[str] = []
    if sg_ids:
        sgs = (
            db.query(MaterialSubgroup.name, MaterialGroup.name)
            .join(MaterialGroup, MaterialSubgroup.group_id == MaterialGroup.id)
            .filter(MaterialSubgroup.id.in_([row[0] for row in links]))
            .all()
        )
        sg_names = [f"{g_name} / {sg_name}" for sg_name, g_name in sgs]

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
        "subgroup_ids": sg_ids,
        "subgroup_names": sg_names,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


def _sync_subgroups(db: Session, supplier_id, subgroup_ids: list[UUID]):
    """Replace all subgroup links for a supplier."""
    db.query(SupplierSubgroup).filter(SupplierSubgroup.supplier_id == supplier_id).delete()
    for sg_id in subgroup_ids:
        db.add(SupplierSubgroup(supplier_id=supplier_id, subgroup_id=sg_id))
    db.flush()


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
    return {"items": [_serialize_supplier(s, db) for s in items], "total": total, "page": page, "per_page": per_page}


@router.get("/{item_id}")
async def get_suppliers_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(Supplier).filter(Supplier.id == item_id).first()
    if not item:
        raise HTTPException(404, "Supplier not found")
    return _serialize_supplier(item, db)


@router.post("", status_code=201)
async def create_suppliers_item(
    data: SupplierCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    payload = data.model_dump(exclude={"subgroup_ids"})
    item = Supplier(**payload)
    db.add(item)
    db.flush()
    if data.subgroup_ids:
        _sync_subgroups(db, item.id, data.subgroup_ids)
    db.commit()
    db.refresh(item)
    return _serialize_supplier(item, db)


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
    update_data = data.model_dump(exclude_unset=True, exclude={"subgroup_ids"})
    for k, v in update_data.items():
        setattr(item, k, v)
    if data.subgroup_ids is not None:
        _sync_subgroups(db, item.id, data.subgroup_ids)
    db.commit()
    db.refresh(item)
    return _serialize_supplier(item, db)


@router.delete("/{item_id}", status_code=204)
async def delete_suppliers_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(Supplier).filter(Supplier.id == item_id).first()
    if not item:
        raise HTTPException(404, "Supplier not found")
    # Nullify all FK references before deletion
    db.query(Material).filter(Material.supplier_id == item_id).update({"supplier_id": None})
    db.query(MaterialPurchaseRequest).filter(MaterialPurchaseRequest.supplier_id == item_id).update({"supplier_id": None})
    db.query(DefectRecord).filter(DefectRecord.supplier_id == item_id).update({"supplier_id": None})
    db.query(StoneDefectCoefficient).filter(StoneDefectCoefficient.supplier_id == item_id).update({"supplier_id": None})
    db.query(SupplierDefectReport).filter(SupplierDefectReport.supplier_id == item_id).delete()
    # SupplierSubgroup + SupplierLeadTime — CASCADE handles them
    db.delete(item)
    db.commit()
