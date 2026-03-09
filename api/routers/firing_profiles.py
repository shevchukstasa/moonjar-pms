"""CRUD router for firing_profiles — universal firing temperature curves."""

from uuid import UUID
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_

from api.database import get_db
from api.auth import get_current_user
from api.models import FiringProfile
from api.schemas import (
    FiringProfileCreate,
    FiringProfileUpdate,
    FiringProfileResponse,
    FiringProfileMatchRequest,
)

router = APIRouter()


@router.get("", response_model=dict)
async def list_firing_profiles(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    product_type: str | None = None,
    collection: str | None = None,
    is_active: bool | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(FiringProfile)
    if product_type is not None:
        query = query.filter(FiringProfile.product_type == product_type)
    if collection is not None:
        query = query.filter(FiringProfile.collection == collection)
    if is_active is not None:
        query = query.filter(FiringProfile.is_active == is_active)
    total = query.count()
    items = query.order_by(FiringProfile.match_priority.desc()).offset(
        (page - 1) * per_page
    ).limit(per_page).all()
    return {"items": items, "total": total, "page": page, "per_page": per_page}


@router.get("/{item_id}", response_model=FiringProfileResponse)
async def get_firing_profile(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(FiringProfile).filter(FiringProfile.id == item_id).first()
    if not item:
        raise HTTPException(404, "FiringProfile not found")
    return item


@router.post("", response_model=FiringProfileResponse, status_code=201)
async def create_firing_profile(
    data: FiringProfileCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = FiringProfile(**data.model_dump(exclude_unset=True))
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=FiringProfileResponse)
async def update_firing_profile(
    item_id: UUID,
    data: FiringProfileUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(FiringProfile).filter(FiringProfile.id == item_id).first()
    if not item:
        raise HTTPException(404, "FiringProfile not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
async def delete_firing_profile(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Soft-delete: sets is_active=False."""
    item = db.query(FiringProfile).filter(FiringProfile.id == item_id).first()
    if not item:
        raise HTTPException(404, "FiringProfile not found")
    item.is_active = False
    db.commit()


@router.post("/match", response_model=FiringProfileResponse | None)
async def match_firing_profile(
    data: FiringProfileMatchRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Test endpoint: find best matching profile for given product_type + collection + thickness."""
    from business.services.firing_profiles import match_firing_profile as do_match

    profile = do_match(db, data.product_type, data.collection, Decimal(str(data.thickness_mm)))
    if not profile:
        raise HTTPException(404, "No matching firing profile found")
    return profile
