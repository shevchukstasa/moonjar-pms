"""CRUD router for factories (auto-generated)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.roles import require_admin
from api.models import Factory
from api.schemas import FactoryCreate, FactoryUpdate, FactoryResponse

router = APIRouter()


@router.get("", response_model=dict)
async def list_factories(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(Factory)
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return {
        "items": [FactoryResponse.model_validate(i).model_dump(mode="json") for i in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/{item_id}", response_model=FactoryResponse)
async def get_factories_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(Factory).filter(Factory.id == item_id).first()
    if not item:
        raise HTTPException(404, "Factory not found")
    return item


@router.post("", response_model=FactoryResponse, status_code=201)
async def create_factories_item(
    data: FactoryCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    item = Factory(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=FactoryResponse)
async def update_factories_item(
    item_id: UUID,
    data: FactoryUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    item = db.query(Factory).filter(Factory.id == item_id).first()
    if not item:
        raise HTTPException(404, "Factory not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
async def delete_factories_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    item = db.query(Factory).filter(Factory.id == item_id).first()
    if not item:
        raise HTTPException(404, "Factory not found")
    db.delete(item)
    db.commit()
