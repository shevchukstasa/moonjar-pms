"""Delivery photo processing endpoint — OCR + smart material matching."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.models import Material, Size

logger = logging.getLogger("moonjar.delivery")

router = APIRouter()


@router.post("/process-photo")
async def process_delivery_photo(
    file: UploadFile = File(...),
    supplier_hint: Optional[str] = Query(None, description="Optional supplier name hint"),
    date_hint: Optional[str] = Query(None, description="Optional date hint (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Process a delivery note photo end-to-end:

    1. Vision API reads the document (OpenAI GPT-4o for OCR)
    2. Material matcher matches items against DB
    3. Returns structured result for bot/frontend to display

    Used by: Telegram bot /delivery command, warehouse PWA upload.
    """
    # 1. Read photo bytes
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(400, "Empty file uploaded")

    # Basic content-type check
    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(400, f"Expected image file, got {content_type}")

    logger.info(
        "DELIVERY_PHOTO | user=%s | file=%s (%d bytes) | supplier_hint=%s",
        current_user.email if hasattr(current_user, "email") else "unknown",
        file.filename,
        len(image_bytes),
        supplier_hint,
    )

    # 2. Call Vision API
    from business.services.photo_analysis import analyze_photo

    result = await analyze_photo(image_bytes, analysis_type="delivery")
    if result is None:
        raise HTTPException(
            503,
            "Vision API unavailable — no OPENAI_API_KEY or ANTHROPIC_API_KEY configured",
        )

    readings = result.get("readings", {})

    # 3. Determine supplier from Vision result or hint
    supplier_name = supplier_hint or readings.get("supplier")

    # 4. Get all materials from DB
    materials = db.query(Material).all()
    db_materials = [
        {
            "id": str(m.id),
            "name": m.name,
            "material_type": m.material_type,
            "unit": m.unit,
            "product_subtype": m.product_subtype,
            "size_id": str(m.size_id) if m.size_id else None,
        }
        for m in materials
    ]

    # 5. Get all sizes from DB
    sizes = db.query(Size).all()
    db_sizes = [
        {
            "id": str(s.id),
            "name": s.name,
            "width_mm": s.width_mm,
            "height_mm": s.height_mm,
        }
        for s in sizes
    ]

    # 6. Match each item
    from business.services.material_matcher import match_delivery_items

    items = readings.get("items", [])
    matches = await match_delivery_items(
        items=[
            {
                "name": i.get("material_name", i.get("name", "")),
                "quantity": i.get("quantity", 0),
                "unit": i.get("unit", "pcs"),
            }
            for i in items
        ],
        db_materials=db_materials,
        supplier_name=supplier_name,
        db_sizes=db_sizes,
    )

    # 7. Return structured result
    matched_count = sum(1 for m in matches if m.get("matched"))
    logger.info(
        "DELIVERY_PHOTO | matched %d/%d items | supplier=%s",
        matched_count, len(matches), supplier_name,
    )

    return {
        "supplier": supplier_name,
        "delivery_date": date_hint or readings.get("delivery_date"),
        "reference_number": readings.get("reference_number"),
        "items": matches,
        "total_items": len(matches),
        "matched_items": matched_count,
        "vision_raw": readings,
        "confidence": result.get("confidence"),
    }
