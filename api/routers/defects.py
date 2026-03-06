"""CRUD router for defect_types (auto-generated)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.models import DefectType
from api.schemas import DefectTypeCreate, DefectTypeUpdate, DefectTypeResponse

router = APIRouter()


@router.get("/", response_model=dict)
async def list_defects(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(DefectType)
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return {"items": items, "total": total, "page": page, "per_page": per_page}


@router.get("/{item_id}", response_model=DefectTypeResponse)
async def get_defects_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(DefectType).filter(DefectType.id == item_id).first()
    if not item:
        raise HTTPException(404, "DefectType not found")
    return item


@router.post("/", response_model=DefectTypeResponse, status_code=201)
async def create_defects_item(
    data: DefectTypeCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = DefectType(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=DefectTypeResponse)
async def update_defects_item(
    item_id: UUID,
    data: DefectTypeUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(DefectType).filter(DefectType.id == item_id).first()
    if not item:
        raise HTTPException(404, "DefectType not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
async def delete_defects_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(DefectType).filter(DefectType.id == item_id).first()
    if not item:
        raise HTTPException(404, "DefectType not found")
    db.delete(item)
    db.commit()
