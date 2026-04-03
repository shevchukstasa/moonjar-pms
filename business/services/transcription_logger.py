"""
Transcription logging service.

Handles:
1. Voice message transcription via OpenAI Whisper API
2. Persisting transcription logs to the database

Wire-in: called from telegram_bot.py when a voice/audio message arrives.
"""

import io
import logging
from typing import Optional
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from api.config import get_settings
from api.models import TranscriptionLog, User

logger = logging.getLogger("moonjar.transcription")


async def transcribe_audio(audio_bytes: bytes, filename: str = "voice.ogg") -> dict:
    """
    Transcribe audio via OpenAI Whisper API.

    Returns dict with keys: text, language, duration (if available).
    Raises on API failure.
    """
    settings = get_settings()
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not configured — cannot transcribe")

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
            files={"file": (filename, io.BytesIO(audio_bytes), "audio/ogg")},
            data={
                "model": "whisper-1",
                "response_format": "verbose_json",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    return {
        "text": data.get("text", ""),
        "language": data.get("language"),
        "duration": int(data["duration"]) if data.get("duration") else None,
    }


def save_transcription_log(
    db: Session,
    *,
    transcribed_text: str,
    user_id: Optional[UUID] = None,
    telegram_user_id: Optional[int] = None,
    telegram_chat_id: Optional[int] = None,
    audio_duration_sec: Optional[int] = None,
    ai_response_summary: Optional[str] = None,
    language_detected: Optional[str] = None,
) -> TranscriptionLog:
    """Persist a transcription log record. Returns the created row."""
    log = TranscriptionLog(
        user_id=user_id,
        telegram_user_id=telegram_user_id,
        telegram_chat_id=telegram_chat_id,
        audio_duration_sec=audio_duration_sec,
        transcribed_text=transcribed_text,
        ai_response_summary=ai_response_summary,
        language_detected=language_detected,
    )
    db.add(log)
    db.flush()
    logger.info(
        "Transcription log saved: id=%s tg_user=%s dur=%ss lang=%s len=%d",
        log.id, telegram_user_id, audio_duration_sec,
        language_detected, len(transcribed_text or ""),
    )
    return log
