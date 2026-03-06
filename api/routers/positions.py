"""Positions router — CRUD + status transitions + split/merge.
See API_CONTRACTS.md for full specification.
"""

from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.roles import require_management

router = APIRouter()


@router.get("/")
async def list_positions(
    page: int = Query(1, ge=1), per_page: int = Query(50, ge=1, le=200),
    factory_id: UUID | None = None, order_id: UUID | None = None,
    status: str | None = None, stage: str | None = None,
    db: Session = Depends(get_db), current_user=Depends(get_current_user),
):
    # TODO: Implement with filters — see API_CONTRACTS §8
    raise HTTPException(501, "Not implemented")


@router.get("/{position_id}")
async def get_position(position_id: UUID, db: Session = Depends(get_db),
                       current_user=Depends(get_current_user)):
    # TODO: Implement — see API_CONTRACTS §8
    raise HTTPException(501, "Not implemented")


@router.post("/", status_code=201)
async def create_position(request: Request, db: Session = Depends(get_db),
                          current_user=Depends(get_current_user)):
    # TODO: Implement position creation — see BL §1
    raise HTTPException(501, "Not implemented")


@router.patch("/{position_id}")
async def update_position(position_id: UUID, request: Request,
                          db: Session = Depends(get_db),
                          current_user=Depends(get_current_user)):
    # TODO: Implement — see API_CONTRACTS §8
    raise HTTPException(501, "Not implemented")


@router.post("/{position_id}/status")
async def change_position_status(position_id: UUID, request: Request,
                                 db: Session = Depends(get_db),
                                 current_user=Depends(get_current_user)):
    # TODO: Status transition with validation (20 statuses) — see BL §6
    raise HTTPException(501, "Not implemented")


@router.post("/split")
async def split_position(request: Request, db: Session = Depends(get_db),
                         current_user=Depends(get_current_user)):
    # TODO: Split position into children — see BL §8
    raise HTTPException(501, "Not implemented")


@router.post("/merge")
async def merge_positions(request: Request, db: Session = Depends(get_db),
                          current_user=Depends(get_current_user)):
    # TODO: Merge positions — see BL §9
    raise HTTPException(501, "Not implemented")
