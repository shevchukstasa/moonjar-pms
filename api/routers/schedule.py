"""Schedule router — resources, batches, kiln schedule.
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


@router.get("/resources")
async def list_resources(factory_id: UUID | None = None,
                         db: Session = Depends(get_db),
                         current_user=Depends(get_current_user)):
    # TODO: List kilns and stations — see API_CONTRACTS §5
    raise HTTPException(501, "Not implemented")


@router.get("/batches")
async def list_batches(
    page: int = Query(1, ge=1), per_page: int = Query(50),
    factory_id: UUID | None = None, status: str | None = None,
    db: Session = Depends(get_db), current_user=Depends(get_current_user),
):
    # TODO: List production batches — see API_CONTRACTS §5
    raise HTTPException(501, "Not implemented")


@router.post("/batches", status_code=201)
async def create_batch(request: Request, db: Session = Depends(get_db),
                       current_user=Depends(get_current_user)):
    # TODO: Create production batch — see BL §10
    raise HTTPException(501, "Not implemented")


@router.patch("/batches/{batch_id}")
async def update_batch(batch_id: UUID, request: Request,
                       db: Session = Depends(get_db),
                       current_user=Depends(get_current_user)):
    # TODO: Update batch — see API_CONTRACTS §5
    raise HTTPException(501, "Not implemented")


@router.get("/kiln-schedule")
async def get_kiln_schedule(factory_id: UUID | None = None,
                            date_from: str | None = None, date_to: str | None = None,
                            db: Session = Depends(get_db),
                            current_user=Depends(get_current_user)):
    # TODO: Kiln schedule — see API_CONTRACTS §5, BL §11
    raise HTTPException(501, "Not implemented")


@router.post("/kiln-schedule/suggest")
async def suggest_kiln_loading(request: Request, db: Session = Depends(get_db),
                               current_user=Depends(get_current_user)):
    # TODO: AI-assisted kiln loading suggestion — see BL §11
    raise HTTPException(501, "Not implemented")


@router.post("/kiln-schedule/confirm")
async def confirm_kiln_loading(request: Request, db: Session = Depends(get_db),
                               current_user=Depends(get_current_user)):
    # TODO: Confirm kiln loading — see BL §11
    raise HTTPException(501, "Not implemented")
