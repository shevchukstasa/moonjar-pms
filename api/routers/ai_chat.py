"""AI Chat router — RAG-based assistant.
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


@router.post("/chat")
async def chat(request: Request, db: Session = Depends(get_db),
               current_user=Depends(get_current_user)):
    # TODO: Process chat message with RAG — see BL §13, API_CONTRACTS §19
    raise HTTPException(501, "Not implemented")


@router.get("/sessions")
async def list_chat_sessions(db: Session = Depends(get_db),
                             current_user=Depends(get_current_user)):
    # TODO: List chat sessions — see API_CONTRACTS §19
    raise HTTPException(501, "Not implemented")


@router.get("/sessions/{session_id}/messages")
async def get_chat_messages(session_id: UUID, db: Session = Depends(get_db),
                            current_user=Depends(get_current_user)):
    # TODO: Get messages for chat session — see API_CONTRACTS §19
    raise HTTPException(501, "Not implemented")
