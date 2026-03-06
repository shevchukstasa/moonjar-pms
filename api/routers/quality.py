"""Quality router — QC inspections.
See API_CONTRACTS.md for full specification.
"""

from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.roles import require_quality

router = APIRouter()


@router.get("/inspections")
async def list_inspections(
    page: int = Query(1), per_page: int = Query(50),
    factory_id: UUID | None = None, status: str | None = None,
    db: Session = Depends(get_db), current_user=Depends(get_current_user),
):
    # TODO: List QC inspections — see API_CONTRACTS §7
    raise HTTPException(501, "Not implemented")


@router.post("/inspections", status_code=201)
async def create_inspection(request: Request, db: Session = Depends(get_db),
                            current_user=Depends(get_current_user)):
    # TODO: Create QC inspection record — see BL §7
    raise HTTPException(501, "Not implemented")


@router.patch("/inspections/{inspection_id}")
async def update_inspection(inspection_id: UUID, request: Request,
                            db: Session = Depends(get_db),
                            current_user=Depends(get_current_user)):
    # TODO: Update inspection — see API_CONTRACTS §7
    raise HTTPException(501, "Not implemented")


@router.post("/inspections/{inspection_id}/photo")
async def upload_inspection_photo(inspection_id: UUID, file: UploadFile = File(...),
                                  db: Session = Depends(get_db),
                                  current_user=Depends(get_current_user)):
    # TODO: Upload QC photo to Supabase Storage — see API_CONTRACTS §7
    raise HTTPException(501, "Not implemented")
