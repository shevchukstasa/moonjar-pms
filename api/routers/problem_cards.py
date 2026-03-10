"""CRUD router for problem_cards (auto-generated)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.models import ProblemCard
from api.schemas import ProblemCardCreate, ProblemCardUpdate, ProblemCardResponse

router = APIRouter()


@router.get("", response_model=dict)
async def list_problem_cards(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    factory_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(ProblemCard)
    if factory_id:
        query = query.filter(ProblemCard.factory_id == factory_id)
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return {
        "items": [ProblemCardResponse.model_validate(item).model_dump(mode="json") for item in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/{item_id}", response_model=ProblemCardResponse)
async def get_problem_cards_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(ProblemCard).filter(ProblemCard.id == item_id).first()
    if not item:
        raise HTTPException(404, "ProblemCard not found")
    return item


@router.post("", response_model=ProblemCardResponse, status_code=201)
async def create_problem_cards_item(
    data: ProblemCardCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = ProblemCard(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=ProblemCardResponse)
async def update_problem_cards_item(
    item_id: UUID,
    data: ProblemCardUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(ProblemCard).filter(ProblemCard.id == item_id).first()
    if not item:
        raise HTTPException(404, "ProblemCard not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
async def delete_problem_cards_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(ProblemCard).filter(ProblemCard.id == item_id).first()
    if not item:
        raise HTTPException(404, "ProblemCard not found")
    db.delete(item)
    db.commit()
