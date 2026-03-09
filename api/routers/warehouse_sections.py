"""CRUD router for warehouse_sections (auto-generated)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.models import WarehouseSection
from api.schemas import WarehouseSectionCreate, WarehouseSectionUpdate, WarehouseSectionResponse

router = APIRouter()


@router.get("", response_model=dict)
async def list_warehouse_sections(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    factory_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(WarehouseSection)
    if factory_id:
        query = query.filter(WarehouseSection.factory_id == factory_id)
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return {"items": items, "total": total, "page": page, "per_page": per_page}


@router.get("/{item_id}", response_model=WarehouseSectionResponse)
async def get_warehouse_sections_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(WarehouseSection).filter(WarehouseSection.id == item_id).first()
    if not item:
        raise HTTPException(404, "WarehouseSection not found")
    return item


@router.post("", response_model=WarehouseSectionResponse, status_code=201)
async def create_warehouse_sections_item(
    data: WarehouseSectionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = WarehouseSection(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=WarehouseSectionResponse)
async def update_warehouse_sections_item(
    item_id: UUID,
    data: WarehouseSectionUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(WarehouseSection).filter(WarehouseSection.id == item_id).first()
    if not item:
        raise HTTPException(404, "WarehouseSection not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
async def delete_warehouse_sections_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(WarehouseSection).filter(WarehouseSection.id == item_id).first()
    if not item:
        raise HTTPException(404, "WarehouseSection not found")
    db.delete(item)
    db.commit()
