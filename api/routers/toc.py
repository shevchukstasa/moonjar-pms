"""TOC (Theory of Constraints) router.
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


@router.get("/constraints")
async def list_constraints(factory_id: UUID | None = None,
                           db: Session = Depends(get_db),
                           current_user=Depends(get_current_user)):
    # TODO: List TOC constraints — see API_CONTRACTS §15, BL §12
    raise HTTPException(501, "Not implemented")


@router.patch("/constraints/{constraint_id}")
async def update_constraint(constraint_id: UUID, request: Request,
                            db: Session = Depends(get_db),
                            current_user=Depends(get_current_user)):
    # TODO: Update constraint params — see API_CONTRACTS §15
    raise HTTPException(501, "Not implemented")


@router.get("/buffer-health")
async def get_buffer_health(factory_id: UUID | None = None,
                            db: Session = Depends(get_db),
                            current_user=Depends(get_current_user)):
    # TODO: Buffer health metrics — see BL §12
    raise HTTPException(501, "Not implemented")
