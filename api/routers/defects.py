"""CRUD router for defect_causes (auto-generated)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.models import DefectCause, OrderPosition
from api.schemas import DefectCauseCreate, DefectCauseUpdate, DefectCauseResponse
from api.roles import require_management, require_role

router = APIRouter()

# Owner or CEO — inline dependency (require_owner_or_ceo not in roles.py)
require_owner_or_ceo = require_role("owner", "ceo")


@router.get("", response_model=dict)
async def list_defects(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(DefectCause)
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return {
        "items": [DefectCauseResponse.model_validate(item).model_dump(mode="json") for item in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# === DEFECT COEFFICIENTS ENDPOINTS (Decision 2026-03-19) ===
# IMPORTANT: These specific routes MUST be declared BEFORE /{item_id} to avoid
# FastAPI matching "coefficients" as a UUID item_id parameter.

@router.get("/coefficients")
def get_defect_coefficients(
    factory_id: UUID = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """
    Get current effective defect coefficients for a factory.
    Returns glaze coefficients (by glaze type) and product coefficients (by product type).
    Coefficients are expressed as fractions (e.g. 0.03 = 3%).
    """
    from business.services.defect_coefficient import (
        GLAZE_DEFECT_DEFAULTS,
        PRODUCT_DEFECT_DEFAULTS,
        get_glaze_defect_coeff,
        get_product_defect_coeff,
    )

    glaze_coefficients = {
        glaze_type: get_glaze_defect_coeff(db, factory_id, glaze_type)
        for glaze_type in GLAZE_DEFECT_DEFAULTS
    }
    product_coefficients = {
        product_type: get_product_defect_coeff(db, factory_id, product_type)
        for product_type in PRODUCT_DEFECT_DEFAULTS
    }

    return {
        "factory_id": str(factory_id),
        "glaze_coefficients": glaze_coefficients,
        "product_coefficients": product_coefficients,
        "note": "Values are fractions. Combined defect margin = glaze + product coefficient.",
    }


@router.post("/positions/{position_id}/override")
def override_position_defect_coeff(
    position_id: UUID,
    coeff_value: float = Body(..., description="Total combined defect coefficient (fraction, e.g. 0.12 = 12%)"),
    reason: str = Body(..., description="Reason for manual override"),
    db: Session = Depends(get_db),
    current_user=Depends(require_owner_or_ceo),
):
    """
    Override defect coefficient for a specific position (Owner / CEO only).
    Sets position.defect_coeff_override which takes precedence over glaze+product calculation.
    """
    position = db.query(OrderPosition).filter(OrderPosition.id == position_id).first()
    if not position:
        raise HTTPException(404, "OrderPosition not found")

    if not (0.0 <= coeff_value <= 1.0):
        raise HTTPException(422, "coeff_value must be between 0.0 and 1.0")

    # Persist override — column added by schema patch
    try:
        position.defect_coeff_override = coeff_value
    except AttributeError:
        raise HTTPException(
            503,
            "defect_coeff_override column not yet applied. Run schema patch first.",
        )

    # Recalculate quantity_with_defect_margin using the new override
    import math
    position.quantity_with_defect_margin = math.ceil(position.quantity * (1 + coeff_value))

    db.commit()
    db.refresh(position)

    return {
        "position_id": str(position_id),
        "defect_coeff_override": float(coeff_value),
        "quantity_with_defect_margin": position.quantity_with_defect_margin,
        "overridden_by": str(current_user.id),
        "overridden_by_role": str(current_user.role),
        "reason": reason,
    }


@router.post("/record")
def record_defect(
    position_id: UUID = Body(...),
    actual_defect_pct: float = Body(..., description="Actual defect fraction, e.g. 0.08 = 8%"),
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """
    Record actual defect percentage after firing and check vs target threshold.
    If threshold exceeded, creates a Quality Check (5 Why) task for the Quality Manager.
    """
    position = db.query(OrderPosition).filter(OrderPosition.id == position_id).first()
    if not position:
        raise HTTPException(404, "OrderPosition not found")

    if not (0.0 <= actual_defect_pct <= 1.0):
        raise HTTPException(422, "actual_defect_pct must be between 0.0 and 1.0")

    from business.services.defect_coefficient import record_actual_defect_and_check_threshold

    result = record_actual_defect_and_check_threshold(
        db=db,
        position=position,
        actual_defect_pct=actual_defect_pct,
    )

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(500, f"Failed to record defect: {exc}") from exc

    return {
        "position_id": str(position_id),
        **result,
        "recorded_by": str(current_user.id),
    }


# --- Standard CRUD (after specific routes) ---

@router.get("/{item_id}", response_model=DefectCauseResponse)
async def get_defects_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(DefectCause).filter(DefectCause.id == item_id).first()
    if not item:
        raise HTTPException(404, "DefectCause not found")
    return item


@router.post("", response_model=DefectCauseResponse, status_code=201)
async def create_defects_item(
    data: DefectCauseCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = DefectCause(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=DefectCauseResponse)
async def update_defects_item(
    item_id: UUID,
    data: DefectCauseUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(DefectCause).filter(DefectCause.id == item_id).first()
    if not item:
        raise HTTPException(404, "DefectCause not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
async def delete_defects_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(DefectCause).filter(DefectCause.id == item_id).first()
    if not item:
        raise HTTPException(404, "DefectCause not found")
    db.delete(item)
    db.commit()
