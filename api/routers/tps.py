"""CRUD router for tps_improvements (auto-generated)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.models import TpsImprovement
from api.schemas import TpsImprovementCreate, TpsImprovementUpdate, TpsImprovementResponse

router = APIRouter()


@router.get("/", response_model=dict)
async def list_tps(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(TpsImprovement)
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return {"items": items, "total": total, "page": page, "per_page": per_page}


@router.get("/{item_id}", response_model=TpsImprovementResponse)
async def get_tps_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(TpsImprovement).filter(TpsImprovement.id == item_id).first()
    if not item:
        raise HTTPException(404, "TpsImprovement not found")
    return item


@router.post("/", response_model=TpsImprovementResponse, status_code=201)
async def create_tps_item(
    data: TpsImprovementCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = TpsImprovement(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=TpsImprovementResponse)
async def update_tps_item(
    item_id: UUID,
    data: TpsImprovementUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(TpsImprovement).filter(TpsImprovement.id == item_id).first()
    if not item:
        raise HTTPException(404, "TpsImprovement not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
async def delete_tps_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(TpsImprovement).filter(TpsImprovement.id == item_id).first()
    if not item:
        raise HTTPException(404, "TpsImprovement not found")
    db.delete(item)
    db.commit()
