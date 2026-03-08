"""Notifications router — list, mark read, mark all read."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from api.database import get_db
from api.auth import get_current_user
from api.models import Notification
from api.schemas import NotificationResponse

router = APIRouter()


@router.get("/", response_model=dict)
async def list_notifications(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    unread_only: bool = False,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List notifications for the current user, newest first."""
    query = db.query(Notification).filter(Notification.user_id == current_user.id)

    if unread_only:
        query = query.filter(Notification.is_read.is_(False))

    total = query.count()
    items = (
        query
        .order_by(desc(Notification.created_at))
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    # Unread count (always useful for badge)
    unread_count = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id, Notification.is_read.is_(False))
        .count()
    )

    return {
        "items": [NotificationResponse.model_validate(n) for n in items],
        "total": total,
        "unread_count": unread_count,
        "page": page,
        "per_page": per_page,
    }


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Mark a single notification as read."""
    notif = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == current_user.id)
        .first()
    )
    if not notif:
        raise HTTPException(404, "Notification not found")

    notif.is_read = True
    db.commit()
    db.refresh(notif)
    return notif


@router.post("/read-all")
async def mark_all_read(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Mark all notifications as read for the current user."""
    updated = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id, Notification.is_read.is_(False))
        .update({Notification.is_read: True})
    )
    db.commit()
    return {"marked_read": updated}
