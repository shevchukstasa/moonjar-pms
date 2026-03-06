"""Integration router — Sales webhook receiver.
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


@router.post("/webhook/sales-order")
async def receive_sales_order(request: Request, db: Session = Depends(get_db)):
    # TODO: Receive order from Sales app, verify HMAC — see BL §1, API_CONTRACTS §10
    raise HTTPException(501, "Not implemented")
