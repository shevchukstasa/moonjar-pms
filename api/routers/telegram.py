"""Telegram bot router.
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


@router.post("/webhook")
async def telegram_webhook(request: Request, db: Session = Depends(get_db)):
    # TODO: Process Telegram bot updates — see API_CONTRACTS §18
    raise HTTPException(501, "Not implemented")


@router.post("/subscribe")
async def telegram_subscribe(request: Request, db: Session = Depends(get_db),
                             current_user=Depends(get_current_user)):
    # TODO: Subscribe user to Telegram notifications — see API_CONTRACTS §18
    raise HTTPException(501, "Not implemented")


@router.delete("/unsubscribe")
async def telegram_unsubscribe(db: Session = Depends(get_db),
                               current_user=Depends(get_current_user)):
    # TODO: Unsubscribe from Telegram — see API_CONTRACTS §18
    raise HTTPException(501, "Not implemented")
