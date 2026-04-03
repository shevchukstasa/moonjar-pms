"""Transcription router — voice message transcription logs."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.auth import get_current_user
from api.database import get_db
from api.models import TranscriptionLog, User
from api.roles import require_management

router = APIRouter()


def _serialize(log: TranscriptionLog) -> dict:
    return {
        "id": str(log.id),
        "user_id": str(log.user_id) if log.user_id else None,
        "telegram_user_id": log.telegram_user_id,
        "telegram_chat_id": log.telegram_chat_id,
        "audio_duration_sec": log.audio_duration_sec,
        "transcribed_text": log.transcribed_text,
        "ai_response_summary": log.ai_response_summary,
        "language_detected": log.language_detected,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


@router.get("")
async def list_transcriptions(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    user_id: Optional[UUID] = None,
    telegram_user_id: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
):
    """List transcription logs with pagination and optional filters."""
    query = db.query(TranscriptionLog)

    if user_id:
        query = query.filter(TranscriptionLog.user_id == user_id)
    if telegram_user_id:
        query = query.filter(TranscriptionLog.telegram_user_id == telegram_user_id)
    if date_from:
        query = query.filter(TranscriptionLog.created_at >= date_from)
    if date_to:
        query = query.filter(TranscriptionLog.created_at <= date_to)

    total = query.count()
    logs = (
        query
        .order_by(TranscriptionLog.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return {
        "items": [_serialize(log) for log in logs],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/{log_id}")
async def get_transcription(
    log_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
):
    """Get a single transcription log by ID."""
    log = db.query(TranscriptionLog).filter(TranscriptionLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Transcription log not found")
    return _serialize(log)
