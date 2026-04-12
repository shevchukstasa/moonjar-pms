"""CRUD router for firing_profiles — universal firing temperature curves."""

from uuid import UUID
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from api.database import get_db
from api.auth import get_current_user
from api.models import FiringProfile, FiringTemperatureGroup
from api.schemas import (
    FiringProfileCreate,
    FiringProfileUpdate,
    FiringProfileResponse,
    FiringProfileMatchRequest,
)

router = APIRouter()


def _serialize(item: FiringProfile) -> dict:
    """Convert ORM FiringProfile to response dict with temp group + typology names."""
    resp = FiringProfileResponse.model_validate(item).model_dump(mode="json")
    # Inject names from relationships
    if item.temperature_group:
        resp["temperature_group_name"] = item.temperature_group.name
    if item.typology:
        resp["typology_name"] = item.typology.name
    return resp


@router.get("", response_model=dict)
async def list_firing_profiles(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    product_type: str | None = None,
    collection: str | None = None,
    is_active: bool | None = None,
    factory_id: UUID | None = None,
    temperature_group_id: UUID | None = None,
    typology_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(FiringProfile).options(
        joinedload(FiringProfile.temperature_group),
        joinedload(FiringProfile.typology),
    )
    if factory_id is not None:
        query = query.filter(FiringProfile.factory_id == factory_id)
    if product_type is not None:
        query = query.filter(FiringProfile.product_type == product_type)
    if collection is not None:
        query = query.filter(FiringProfile.collection == collection)
    if is_active is not None:
        query = query.filter(FiringProfile.is_active == is_active)
    if temperature_group_id is not None:
        query = query.filter(FiringProfile.temperature_group_id == temperature_group_id)
    if typology_id is not None:
        query = query.filter(FiringProfile.typology_id == typology_id)
    total = query.count()
    items = query.order_by(FiringProfile.match_priority.desc()).offset(
        (page - 1) * per_page
    ).limit(per_page).all()
    return {
        "items": [_serialize(item) for item in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/{item_id}")
async def get_firing_profile(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(FiringProfile).options(
        joinedload(FiringProfile.temperature_group),
        joinedload(FiringProfile.typology),
    ).filter(FiringProfile.id == item_id).first()
    if not item:
        raise HTTPException(404, "FiringProfile not found")
    return _serialize(item)


@router.post("", status_code=201)
async def create_firing_profile(
    data: FiringProfileCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = FiringProfile(**data.model_dump(exclude_unset=True))
    db.add(item)
    db.commit()
    db.refresh(item)
    # Reload with relationships
    item = db.query(FiringProfile).options(
        joinedload(FiringProfile.temperature_group),
        joinedload(FiringProfile.typology),
    ).filter(FiringProfile.id == item.id).first()
    return _serialize(item)


@router.patch("/{item_id}")
async def update_firing_profile(
    item_id: UUID,
    data: FiringProfileUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(FiringProfile).options(
        joinedload(FiringProfile.temperature_group),
        joinedload(FiringProfile.typology),
    ).filter(FiringProfile.id == item_id).first()
    if not item:
        raise HTTPException(404, "FiringProfile not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    # Reload with relationships
    item = db.query(FiringProfile).options(
        joinedload(FiringProfile.temperature_group),
        joinedload(FiringProfile.typology),
    ).filter(FiringProfile.id == item.id).first()
    return _serialize(item)


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


@router.post("/match")
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
    return _serialize(profile)
