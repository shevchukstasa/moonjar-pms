"""Transcription router — stub (transcription_logs not in schema)."""

from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def list_transcriptions():
    # TODO: Implement transcription log tracking
    return {"items": [], "total": 0, "page": 1, "per_page": 50}
