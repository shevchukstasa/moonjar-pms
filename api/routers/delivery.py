"""Delivery photo processing endpoint — OCR + smart material matching.

See ``docs/BUSINESS_LOGIC_FULL.md §29`` for the canonical naming/typology rules
applied here. Two endpoints:

  - ``POST /delivery/process-photo`` — OCR + match against catalog.
  - ``POST /delivery/create-material-from-scan`` — one-click material+size
    creation from the parsed_* fields returned by /process-photo.
"""

import hmac as hmac_mod
import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.models import Material, MaterialStock, MaterialTransaction, Size
from api.enums import TransactionType
from api.routers.materials import _next_material_code
from business.services import material_naming as nm

logger = logging.getLogger("moonjar.delivery")

router = APIRouter()

# Magic-byte validation for image uploads
ALLOWED_MAGIC = {
    b'\xff\xd8\xff': 'image/jpeg',
    b'\x89PNG': 'image/png',
    b'RIFF': 'image/webp',
}


def _validate_image_magic(data: bytes) -> bool:
    """Check that image data starts with a known image magic-byte signature."""
    return any(data.startswith(magic) for magic in ALLOWED_MAGIC)


async def _get_user_or_internal_key(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Authenticate via JWT (get_current_user) OR X-API-Key header.

    X-API-Key is checked against INTERNAL_API_KEY env var (used by Telegram bot
    for server-to-server calls). Falls back to OWNER_KEY from settings.
    """
    # 1. Try X-API-Key (internal / bot calls)
    x_api_key = request.headers.get("X-API-Key")
    if x_api_key:
        from api.config import get_settings
        settings = get_settings()
        expected_key = os.getenv("INTERNAL_API_KEY") or settings.OWNER_KEY
        if expected_key and hmac_mod.compare_digest(x_api_key, expected_key):
            logger.debug("Delivery endpoint authenticated via X-API-Key (internal)")
            return None  # No user object for internal calls
        raise HTTPException(401, "Invalid API key")

    # 2. Fall back to JWT auth
    return await get_current_user(request=request, db=db)


@router.post("/process-photo")
async def process_delivery_photo(
    file: UploadFile = File(...),
    supplier_hint: Optional[str] = Query(None, description="Optional supplier name hint"),
    date_hint: Optional[str] = Query(None, description="Optional date hint (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user=Depends(_get_user_or_internal_key),
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

    # Validate magic bytes to prevent non-image uploads
    if not _validate_image_magic(image_bytes):
        raise HTTPException(400, "Invalid image file. Only JPEG, PNG, and WebP are allowed.")

    logger.info(
        "DELIVERY_PHOTO | user=%s | file=%s (%d bytes) | supplier_hint=%s",
        current_user.email if current_user and hasattr(current_user, "email") else "internal-bot",
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
            "short_name": m.short_name,
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
            "thickness_mm": s.thickness_mm,
            "diameter_mm": s.diameter_mm,
            "shape": s.shape,
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

    # 8. Pre-format text for API consumers (non-Telegram channels)
    from business.services.photo_analysis import format_delivery_message

    matched_for_fmt = [m for m in matches if m.get("matched")]
    unmatched_for_fmt = [m for m in matches if not m.get("matched")]
    formatted_text = format_delivery_message(
        result,
        matched_items=matched_for_fmt,
        unmatched_items=unmatched_for_fmt,
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
        "formatted_text": formatted_text,
    }


# ──────────────────────────────────────────────────────────────────
# POST /delivery/create-material-from-scan
# ──────────────────────────────────────────────────────────────────


class CreateMaterialFromScanInput(BaseModel):
    """Payload to create a Material+Size in one shot from a delivery scan row.

    The frontend builds this from parsed_* fields returned by /process-photo,
    optionally overridden by user edits (typology choice, size override, etc).
    """
    name: str = Field(..., max_length=300, description="Long delivery-style name as it appeared")
    short_name: Optional[str] = Field(None, max_length=100)
    material_type: str = Field(..., description="stone | pigment | frit | ...")
    product_subtype: Optional[str] = Field(None, description="tiles|3d|sink|countertop|freeform")
    unit: str = Field("pcs")
    supplier_id: Optional[str] = None
    factory_id: str = Field(..., description="Factory the initial stock row will be created in")

    # Size — either size_id (existing) or size_dims (create-or-find)
    size_id: Optional[str] = None
    width_mm: Optional[int] = None
    height_mm: Optional[int] = None
    thickness_mm: Optional[int] = None
    diameter_mm: Optional[int] = None
    shape: Optional[str] = Field("rectangle", description="rectangle|round|triangle|octagon|freeform")


@router.post("/create-material-from-scan")
async def create_material_from_scan(
    payload: CreateMaterialFromScanInput,
    db: Session = Depends(get_db),
    current_user=Depends(_get_user_or_internal_key),
):
    """Create a Material (and Size if needed) from parsed delivery-scan data.

    Idempotent on `short_name` for stone — if a stone material with the same
    canonical short_name already exists, returns it without creating a duplicate.
    """
    # 1. Validate unit against material_type rules (§29 hard validation)
    if not nm.is_valid_unit_for_type(payload.material_type, payload.unit):
        raise HTTPException(
            422,
            f"Unit {payload.unit!r} is not allowed for material_type {payload.material_type!r}. "
            f"Allowed: {nm.allowed_units_for_type(payload.material_type)}",
        )

    # 2. For stone — derive canonical short_name if not provided
    short_name = payload.short_name
    if payload.material_type == "stone" and not short_name:
        short_name = nm.build_short_name_from_raw(payload.name)
    if not short_name:
        short_name = payload.name[:100]

    # 3. Idempotency on short_name for stone
    if payload.material_type == "stone":
        existing = (
            db.query(Material)
            .filter(Material.material_type == "stone", Material.short_name == short_name)
            .first()
        )
        if existing:
            logger.info(
                "create-material-from-scan: reused existing material id=%s short_name=%r",
                existing.id, short_name,
            )
            return {
                "material_id": str(existing.id),
                "material_code": existing.material_code,
                "name": existing.name,
                "short_name": existing.short_name,
                "created": False,
            }

    # 4. Resolve or create Size
    size_id = payload.size_id
    if not size_id:
        size_id = _resolve_or_create_size(db, payload)

    # 5. Create Material — assign sequential M-XXXX code so it appears in lists
    material = Material(
        name=payload.name[:300],
        short_name=short_name[:100] if short_name else None,
        material_code=_next_material_code(db),
        material_type=payload.material_type,
        product_subtype=payload.product_subtype,
        unit=payload.unit,
        supplier_id=payload.supplier_id,
        size_id=size_id,
    )
    db.add(material)
    db.flush()  # assign id

    # 6. Create initial empty MaterialStock row for the factory so the receipt has somewhere to land
    stock = MaterialStock(
        material_id=material.id,
        factory_id=payload.factory_id,
        balance=0,
        min_balance=0,
    )
    db.add(stock)
    db.commit()

    logger.info(
        "create-material-from-scan: created id=%s short_name=%r type=%s",
        material.id, material.short_name, material.material_type,
    )

    return {
        "material_id": str(material.id),
        "material_code": material.material_code,
        "name": material.name,
        "short_name": material.short_name,
        "size_id": str(size_id) if size_id else None,
        "created": True,
    }


def _resolve_or_create_size(db: Session, payload: CreateMaterialFromScanInput) -> Optional[str]:
    """Find an existing Size row matching the dimensions, else create one.

    Returns size_id or None when payload has no dimensions (e.g. freeform).
    """
    has_rect = payload.width_mm and payload.height_mm
    has_round = payload.diameter_mm

    if not has_rect and not has_round:
        return None

    if has_round:
        existing = (
            db.query(Size)
            .filter(Size.diameter_mm == payload.diameter_mm)
            .filter(Size.shape == "round")
            .first()
        )
        if existing and (
            not payload.thickness_mm or existing.thickness_mm == payload.thickness_mm
        ):
            return str(existing.id)
        d_cm = payload.diameter_mm / 10
        t_str = f"×{payload.thickness_mm / 10:g}" if payload.thickness_mm else ""
        size = Size(
            name=f"Ø{d_cm:g}{t_str}"[:50],
            width_mm=payload.diameter_mm,
            height_mm=payload.diameter_mm,
            thickness_mm=payload.thickness_mm,
            diameter_mm=payload.diameter_mm,
            shape="round",
            is_custom=True,
        )
    else:
        # Orientation-insensitive lookup
        existing = (
            db.query(Size)
            .filter(
                ((Size.width_mm == payload.width_mm) & (Size.height_mm == payload.height_mm))
                | ((Size.width_mm == payload.height_mm) & (Size.height_mm == payload.width_mm))
            )
            .first()
        )
        if existing and (
            not payload.thickness_mm or existing.thickness_mm == payload.thickness_mm
        ):
            return str(existing.id)
        w_cm = payload.width_mm / 10
        h_cm = payload.height_mm / 10
        t_str = f"×{payload.thickness_mm / 10:g}" if payload.thickness_mm else ""
        size = Size(
            name=f"{w_cm:g}×{h_cm:g}{t_str}"[:50],
            width_mm=payload.width_mm,
            height_mm=payload.height_mm,
            thickness_mm=payload.thickness_mm,
            shape=payload.shape or "rectangle",
            is_custom=True,
        )

    db.add(size)
    db.flush()
    return str(size.id)
