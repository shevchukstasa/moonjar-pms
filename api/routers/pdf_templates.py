"""PDF Templates router — list and retrieve registered PDF parsing templates."""

import logging
from fastapi import APIRouter, Depends, HTTPException

from api.auth import get_current_user
from business.services.pdf_templates import get_template, list_templates

logger = logging.getLogger("moonjar.pdf_templates")

router = APIRouter()


@router.get("/")
async def list_pdf_templates(user=Depends(get_current_user)):
    """List all registered PDF templates with metadata."""
    return {"items": list_templates()}


@router.get("/{template_id}")
async def get_pdf_template(template_id: str, user=Depends(get_current_user)):
    """Get a specific PDF template by ID."""
    template = get_template(template_id)
    if template.id == "generic_fallback" and template_id != "generic_fallback":
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")
    return {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "language": template.language,
        "detection_keywords": template.detection_keywords,
        "detection_patterns": template.detection_patterns,
    }
