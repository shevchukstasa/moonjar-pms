"""Export router — PDF and Excel generation.
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


@router.get("/orders/pdf")
async def export_orders_pdf(factory_id: UUID | None = None,
                            db: Session = Depends(get_db),
                            current_user=Depends(get_current_user)):
    # TODO: Generate orders PDF — see API_CONTRACTS §14
    raise HTTPException(501, "Not implemented")


@router.get("/orders/excel")
async def export_orders_excel(factory_id: UUID | None = None,
                              db: Session = Depends(get_db),
                              current_user=Depends(get_current_user)):
    # TODO: Generate orders Excel — see API_CONTRACTS §14
    raise HTTPException(501, "Not implemented")


@router.get("/positions/pdf")
async def export_positions_pdf(order_id: UUID | None = None,
                               db: Session = Depends(get_db),
                               current_user=Depends(get_current_user)):
    # TODO: Generate positions PDF — see API_CONTRACTS §14
    raise HTTPException(501, "Not implemented")
