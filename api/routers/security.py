"""Security router — audit log, sessions, IP allowlist.
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

router = APIRouter()


@router.get("/audit-log")
async def list_audit_log(
    page: int = Query(1), per_page: int = Query(50),
    action: str | None = None, actor_id: UUID | None = None,
    db: Session = Depends(get_db), current_user=Depends(get_current_user),
):
    # TODO: List security audit events — see API_CONTRACTS §16
    raise HTTPException(501, "Not implemented")


@router.get("/sessions")
async def list_active_sessions(
    page: int = Query(1), per_page: int = Query(50),
    user_id: UUID | None = None,
    db: Session = Depends(get_db), current_user=Depends(get_current_user),
):
    # TODO: List active sessions — see API_CONTRACTS §16
    raise HTTPException(501, "Not implemented")


@router.delete("/sessions/{session_id}")
async def revoke_session(session_id: UUID, db: Session = Depends(get_db),
                         current_user=Depends(get_current_user)):
    # TODO: Revoke a session — see API_CONTRACTS §16
    raise HTTPException(501, "Not implemented")


@router.get("/ip-allowlist")
async def list_ip_allowlist(db: Session = Depends(get_db),
                            current_user=Depends(get_current_user)):
    # TODO: List IP allowlist entries — see API_CONTRACTS §16
    raise HTTPException(501, "Not implemented")


@router.post("/ip-allowlist", status_code=201)
async def add_ip_to_allowlist(request: Request, db: Session = Depends(get_db),
                              current_user=Depends(get_current_user)):
    # TODO: Add IP to allowlist — see API_CONTRACTS §16
    raise HTTPException(501, "Not implemented")


@router.delete("/ip-allowlist/{entry_id}")
async def remove_ip_from_allowlist(entry_id: UUID, db: Session = Depends(get_db),
                                   current_user=Depends(get_current_user)):
    # TODO: Remove IP from allowlist — see API_CONTRACTS §16
    raise HTTPException(501, "Not implemented")
