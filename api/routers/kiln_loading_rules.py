"""CRUD router for kiln_loading_rules (auto-generated)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.roles import require_admin
from api.models import KilnLoadingRule
from api.schemas import KilnLoadingRuleCreate, KilnLoadingRuleUpdate, KilnLoadingRuleResponse

router = APIRouter()


@router.get("", response_model=dict)
async def list_kiln_loading_rules(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(KilnLoadingRule)
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return {"items": items, "total": total, "page": page, "per_page": per_page}


@router.get("/{item_id}", response_model=KilnLoadingRuleResponse)
async def get_kiln_loading_rules_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(KilnLoadingRule).filter(KilnLoadingRule.id == item_id).first()
    if not item:
        raise HTTPException(404, "KilnLoadingRule not found")
    return item


@router.post("", response_model=KilnLoadingRuleResponse, status_code=201)
async def create_kiln_loading_rules_item(
    data: KilnLoadingRuleCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    item = KilnLoadingRule(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=KilnLoadingRuleResponse)
async def update_kiln_loading_rules_item(
    item_id: UUID,
    data: KilnLoadingRuleUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    item = db.query(KilnLoadingRule).filter(KilnLoadingRule.id == item_id).first()
    if not item:
        raise HTTPException(404, "KilnLoadingRule not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
async def delete_kiln_loading_rules_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    item = db.query(KilnLoadingRule).filter(KilnLoadingRule.id == item_id).first()
    if not item:
        raise HTTPException(404, "KilnLoadingRule not found")
    db.delete(item)
    db.commit()
