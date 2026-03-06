"""Notifications router.
See API_CONTRACTS.md for full specification.
"""

from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user

router = APIRouter()


@router.get("/")
async def list_notifications(
    page: int = Query(1), per_page: int = Query(50),
    unread_only: bool = False,
    db: Session = Depends(get_db), current_user=Depends(get_current_user),
):
    # TODO: List user notifications — see API_CONTRACTS §12
    raise HTTPException(501, "Not implemented")


@router.patch("/{notification_id}/read")
async def mark_notification_read(notification_id: UUID, db: Session = Depends(get_db),
                                 current_user=Depends(get_current_user)):
    # TODO: Mark notification as read — see API_CONTRACTS §12
    raise HTTPException(501, "Not implemented")


@router.post("/read-all")
async def mark_all_read(db: Session = Depends(get_db),
                        current_user=Depends(get_current_user)):
    # TODO: Mark all notifications read — see API_CONTRACTS §12
    raise HTTPException(501, "Not implemented")
