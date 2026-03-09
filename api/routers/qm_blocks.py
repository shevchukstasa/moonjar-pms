"""CRUD router for qm_blocks (auto-generated)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.models import QmBlock
from api.schemas import QmBlockCreate, QmBlockUpdate, QmBlockResponse

router = APIRouter()


@router.get("", response_model=dict)
async def list_qm_blocks(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    factory_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(QmBlock)
    if factory_id:
        query = query.filter(QmBlock.factory_id == factory_id)
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return {"items": items, "total": total, "page": page, "per_page": per_page}


@router.get("/{item_id}", response_model=QmBlockResponse)
async def get_qm_blocks_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(QmBlock).filter(QmBlock.id == item_id).first()
    if not item:
        raise HTTPException(404, "QmBlock not found")
    return item


@router.post("", response_model=QmBlockResponse, status_code=201)
async def create_qm_blocks_item(
    data: QmBlockCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = QmBlock(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=QmBlockResponse)
async def update_qm_blocks_item(
    item_id: UUID,
    data: QmBlockUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(QmBlock).filter(QmBlock.id == item_id).first()
    if not item:
        raise HTTPException(404, "QmBlock not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
async def delete_qm_blocks_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(QmBlock).filter(QmBlock.id == item_id).first()
    if not item:
        raise HTTPException(404, "QmBlock not found")
    db.delete(item)
    db.commit()
