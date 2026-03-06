"""Reference data router — product types, stone types, etc.
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


@router.get("/product-types")
async def list_product_types(db: Session = Depends(get_db),
                             current_user=Depends(get_current_user)):
    # TODO: List product types — see API_CONTRACTS §Reference
    raise HTTPException(501, "Not implemented")


@router.get("/stone-types")
async def list_stone_types(db: Session = Depends(get_db),
                           current_user=Depends(get_current_user)):
    # TODO: List stone types — see API_CONTRACTS §Reference
    raise HTTPException(501, "Not implemented")


@router.get("/glaze-types")
async def list_glaze_types(db: Session = Depends(get_db),
                           current_user=Depends(get_current_user)):
    # TODO: List glaze types — see API_CONTRACTS §Reference
    raise HTTPException(501, "Not implemented")


@router.get("/finish-types")
async def list_finish_types(db: Session = Depends(get_db),
                            current_user=Depends(get_current_user)):
    # TODO: List finish types — see API_CONTRACTS §Reference
    raise HTTPException(501, "Not implemented")
