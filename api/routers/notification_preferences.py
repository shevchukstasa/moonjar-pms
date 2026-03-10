"""CRUD router for notification_preferences (auto-generated)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.models import NotificationPreference
from api.schemas import NotificationPreferenceCreate, NotificationPreferenceUpdate, NotificationPreferenceResponse

router = APIRouter()


@router.get("", response_model=dict)
async def list_notification_preferences(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(NotificationPreference)
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return {
        "items": [NotificationPreferenceResponse.model_validate(item).model_dump(mode="json") for item in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/{item_id}", response_model=NotificationPreferenceResponse)
async def get_notification_preferences_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(NotificationPreference).filter(NotificationPreference.id == item_id).first()
    if not item:
        raise HTTPException(404, "NotificationPreference not found")
    return item


@router.post("", response_model=NotificationPreferenceResponse, status_code=201)
async def create_notification_preferences_item(
    data: NotificationPreferenceCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = NotificationPreference(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=NotificationPreferenceResponse)
async def update_notification_preferences_item(
    item_id: UUID,
    data: NotificationPreferenceUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(NotificationPreference).filter(NotificationPreference.id == item_id).first()
    if not item:
        raise HTTPException(404, "NotificationPreference not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
async def delete_notification_preferences_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(NotificationPreference).filter(NotificationPreference.id == item_id).first()
    if not item:
        raise HTTPException(404, "NotificationPreference not found")
    db.delete(item)
    db.commit()
