"""CRUD router for financial_entries (auto-generated)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.models import FinancialEntry
from api.schemas import FinancialEntryCreate, FinancialEntryUpdate, FinancialEntryResponse

router = APIRouter()


@router.get("/", response_model=dict)
async def list_financials(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(FinancialEntry)
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return {"items": items, "total": total, "page": page, "per_page": per_page}


@router.get("/{item_id}", response_model=FinancialEntryResponse)
async def get_financials_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(FinancialEntry).filter(FinancialEntry.id == item_id).first()
    if not item:
        raise HTTPException(404, "FinancialEntry not found")
    return item


@router.post("/", response_model=FinancialEntryResponse, status_code=201)
async def create_financials_item(
    data: FinancialEntryCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = FinancialEntry(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=FinancialEntryResponse)
async def update_financials_item(
    item_id: UUID,
    data: FinancialEntryUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(FinancialEntry).filter(FinancialEntry.id == item_id).first()
    if not item:
        raise HTTPException(404, "FinancialEntry not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
async def delete_financials_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(FinancialEntry).filter(FinancialEntry.id == item_id).first()
    if not item:
        raise HTTPException(404, "FinancialEntry not found")
    db.delete(item)
    db.commit()
