"""Transcription router — stub (transcription_logs not in schema)."""

from fastapi import APIRouter, Depends

from api.auth import get_current_user

router = APIRouter()


@router.get("")
async def list_transcriptions(current_user=Depends(get_current_user)):
    # TODO: Implement transcription log tracking
    return {"items": [], "total": 0, "page": 1, "per_page": 50}
