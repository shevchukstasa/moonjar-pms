"""CRUD router for inventory_reconciliations (auto-generated)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.models import InventoryReconciliation
from api.schemas import InventoryReconciliationCreate, InventoryReconciliationUpdate, InventoryReconciliationResponse

router = APIRouter()


@router.get("", response_model=dict)
async def list_reconciliations(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    factory_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(InventoryReconciliation)
    if factory_id:
        query = query.filter(InventoryReconciliation.factory_id == factory_id)
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return {
        "items": [InventoryReconciliationResponse.model_validate(item).model_dump(mode="json") for item in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/{item_id}", response_model=InventoryReconciliationResponse)
async def get_reconciliations_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(InventoryReconciliation).filter(InventoryReconciliation.id == item_id).first()
    if not item:
        raise HTTPException(404, "InventoryReconciliation not found")
    return item


@router.post("", response_model=InventoryReconciliationResponse, status_code=201)
async def create_reconciliations_item(
    data: InventoryReconciliationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = InventoryReconciliation(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=InventoryReconciliationResponse)
async def update_reconciliations_item(
    item_id: UUID,
    data: InventoryReconciliationUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(InventoryReconciliation).filter(InventoryReconciliation.id == item_id).first()
    if not item:
        raise HTTPException(404, "InventoryReconciliation not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
async def delete_reconciliations_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(InventoryReconciliation).filter(InventoryReconciliation.id == item_id).first()
    if not item:
        raise HTTPException(404, "InventoryReconciliation not found")
    db.delete(item)
    db.commit()
