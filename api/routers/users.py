"""Users router — user management.
See API_CONTRACTS.md for full specification.
"""

from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.roles import require_admin
from api.auth import hash_password

router = APIRouter()


@router.get("/")
async def list_users(
    page: int = Query(1), per_page: int = Query(50),
    role: str | None = None, is_active: bool | None = None,
    db: Session = Depends(get_db), current_user=Depends(get_current_user),
):
    # TODO: List users — see API_CONTRACTS §11
    raise HTTPException(501, "Not implemented")


@router.get("/{user_id}")
async def get_user(user_id: UUID, db: Session = Depends(get_db),
                   current_user=Depends(get_current_user)):
    # TODO: Get user details — see API_CONTRACTS §11
    raise HTTPException(501, "Not implemented")


@router.post("/invite", status_code=201)
async def invite_user(request: Request, db: Session = Depends(get_db),
                      current_user=Depends(get_current_user)):
    # TODO: Invite new user (send email) — see API_CONTRACTS §11
    raise HTTPException(501, "Not implemented")


@router.patch("/{user_id}")
async def update_user(user_id: UUID, request: Request, db: Session = Depends(get_db),
                      current_user=Depends(get_current_user)):
    # TODO: Update user — see API_CONTRACTS §11
    raise HTTPException(501, "Not implemented")


@router.post("/{user_id}/toggle-active")
async def toggle_user_active(user_id: UUID, db: Session = Depends(get_db),
                             current_user=Depends(get_current_user)):
    # TODO: Toggle user active status — see API_CONTRACTS §11
    raise HTTPException(501, "Not implemented")


@router.get("/{user_id}/sessions")
async def list_user_sessions(user_id: UUID, db: Session = Depends(get_db),
                             current_user=Depends(get_current_user)):
    # TODO: List active sessions for user — see API_CONTRACTS §11
    raise HTTPException(501, "Not implemented")
