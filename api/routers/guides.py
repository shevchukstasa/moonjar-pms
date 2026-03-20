"""Guides router — serves role-based user guides in markdown format."""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse

from api.auth import get_current_user

router = APIRouter()
logger = logging.getLogger("moonjar.guides")

# Guide files location (relative to project root)
GUIDES_DIR = Path(__file__).resolve().parent.parent.parent / "docs" / "guides"

# Available guides per role
GUIDE_MAP = {
    "production_manager": {
        "en": "GUIDE_PM_EN.md",
        "id": "GUIDE_PM_ID.md",
    },
    # Future: add guides for other roles
    # "quality_manager": {"en": "GUIDE_QM_EN.md", ...},
    # "sorter_packer": {"en": "GUIDE_SP_EN.md", ...},
}


@router.get("/{role}/{language}")
async def get_guide(
    role: str,
    language: str,
    current_user=Depends(get_current_user),
):
    """Get a user guide in markdown format for a specific role and language."""
    if role not in GUIDE_MAP:
        raise HTTPException(404, f"No guide available for role: {role}")

    lang_map = GUIDE_MAP[role]
    if language not in lang_map:
        available = ", ".join(sorted(lang_map.keys()))
        raise HTTPException(404, f"Language '{language}' not available. Options: {available}")

    file_path = GUIDES_DIR / lang_map[language]
    if not file_path.exists():
        logger.error("Guide file not found: %s", file_path)
        raise HTTPException(404, "Guide file not found on server")

    content = file_path.read_text(encoding="utf-8")
    return PlainTextResponse(content, media_type="text/markdown; charset=utf-8")


@router.get("")
async def list_guides(current_user=Depends(get_current_user)):
    """List available guides and languages."""
    result = {}
    for role, langs in GUIDE_MAP.items():
        result[role] = {
            "languages": list(langs.keys()),
            "files": {lang: f"/api/guides/{role}/{lang}" for lang in langs},
        }
    return result
