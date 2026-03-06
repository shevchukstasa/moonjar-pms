"""CRUD router for purchase_requests (auto-generated)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.models import PurchaseRequest
from api.schemas import PurchaseRequestCreate, PurchaseRequestUpdate, PurchaseRequestResponse

router = APIRouter()


@router.get("/", response_model=dict)
async def list_purchaser(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(PurchaseRequest)
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return {"items": items, "total": total, "page": page, "per_page": per_page}


@router.get("/{item_id}", response_model=PurchaseRequestResponse)
async def get_purchaser_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(PurchaseRequest).filter(PurchaseRequest.id == item_id).first()
    if not item:
        raise HTTPException(404, "PurchaseRequest not found")
    return item


@router.post("/", response_model=PurchaseRequestResponse, status_code=201)
async def create_purchaser_item(
    data: PurchaseRequestCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = PurchaseRequest(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=PurchaseRequestResponse)
async def update_purchaser_item(
    item_id: UUID,
    data: PurchaseRequestUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(PurchaseRequest).filter(PurchaseRequest.id == item_id).first()
    if not item:
        raise HTTPException(404, "PurchaseRequest not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
async def delete_purchaser_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(PurchaseRequest).filter(PurchaseRequest.id == item_id).first()
    if not item:
        raise HTTPException(404, "PurchaseRequest not found")
    db.delete(item)
    db.commit()
