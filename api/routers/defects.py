"""CRUD router for defect_causes (auto-generated)."""

from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.models import DefectCause, OrderPosition, SurplusDisposition, ProductionDefect, ProductionOrder
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


@router.get("/repair-queue")
async def get_repair_queue_endpoint(
    factory_id: UUID = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return positions currently in repair status with SLA info."""
    from business.services.repair_monitoring import get_repair_queue

    items = get_repair_queue(db, factory_id)
    overdue_count = sum(1 for i in items if i["sla_status"] == "overdue")
    return {
        "items": items,
        "total": len(items),
        "overdue_count": overdue_count,
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


# === SURPLUS DISPOSITIONS (Decision 2026-03-19) ===

@router.get("/surplus-dispositions")
async def list_surplus_dispositions(
    factory_id: UUID | None = None,
    disposition_type: str | None = Query(None, description="Filter: showroom | casters | mana"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    List surplus disposition records — positions routed to showroom, casters, or mana.
    Returns position info, color, size, disposition decision, and date.
    """
    query = db.query(SurplusDisposition)

    if factory_id:
        query = query.filter(SurplusDisposition.factory_id == factory_id)
    if disposition_type:
        query = query.filter(SurplusDisposition.disposition_type == disposition_type)

    total = query.count()
    items = query.order_by(
        SurplusDisposition.created_at.desc()
    ).offset((page - 1) * per_page).limit(per_page).all()

    results = []
    for sd in items:
        pos = db.query(OrderPosition).filter(OrderPosition.id == sd.position_id).first()
        order = db.query(ProductionOrder).filter(ProductionOrder.id == sd.order_id).first()
        results.append({
            "id": str(sd.id),
            "factory_id": str(sd.factory_id),
            "order_id": str(sd.order_id),
            "order_number": order.order_number if order else None,
            "position_id": str(sd.position_id),
            "position_status": pos.status.value if pos and pos.status else None,
            "color": sd.color,
            "size": sd.size,
            "is_base_color": sd.is_base_color,
            "surplus_quantity": sd.surplus_quantity,
            "disposition_type": sd.disposition_type.value if sd.disposition_type else None,
            "task_id": str(sd.task_id) if sd.task_id else None,
            "created_at": sd.created_at.isoformat() if sd.created_at else None,
        })

    return {
        "items": results,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# === SUPPLIER DEFECT REPORTS (Decision 2026-03-19) ===

class SupplierReportGenerate(BaseModel):
    factory_id: UUID
    supplier_name: str
    date_from: date
    date_to: date


@router.get("/supplier-reports")
async def list_supplier_reports(
    factory_id: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """
    List supplier defect reports — aggregated on-the-fly from production_defects.
    Groups by glaze_type (proxy for supplier) over the given period.
    """
    query = db.query(
        ProductionDefect.glaze_type,
        ProductionDefect.factory_id,
        func.count(ProductionDefect.id).label("total_records"),
        func.sum(ProductionDefect.total_quantity).label("total_items"),
        func.sum(ProductionDefect.defect_quantity).label("defect_count"),
    ).group_by(ProductionDefect.glaze_type, ProductionDefect.factory_id)

    if factory_id:
        query = query.filter(ProductionDefect.factory_id == factory_id)
    if date_from:
        query = query.filter(ProductionDefect.fired_at >= date_from)
    if date_to:
        query = query.filter(ProductionDefect.fired_at <= date_to)

    rows = query.all()

    items = []
    for row in rows:
        total_items = int(row.total_items or 0)
        defect_count = int(row.defect_count or 0)
        defect_rate = round(defect_count / total_items, 4) if total_items > 0 else 0.0
        items.append({
            "supplier_name": row.glaze_type or "unknown",
            "factory_id": str(row.factory_id),
            "total_records": row.total_records,
            "total_items": total_items,
            "defect_count": defect_count,
            "defect_rate": defect_rate,
        })

    return {"items": items, "total": len(items)}


@router.post("/supplier-reports/generate")
async def generate_supplier_report(
    body: SupplierReportGenerate,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """
    Generate a detailed supplier defect report for a date range and supplier (glaze_type).
    Aggregates defect data from production_defects and returns top defect causes.
    """
    if body.date_from > body.date_to:
        raise HTTPException(400, "date_from must be <= date_to")

    # Aggregate defect data
    query = db.query(ProductionDefect).filter(
        ProductionDefect.factory_id == body.factory_id,
        ProductionDefect.glaze_type == body.supplier_name,
        ProductionDefect.fired_at >= body.date_from,
        ProductionDefect.fired_at <= body.date_to,
    )

    defects = query.all()
    total_items = sum(d.total_quantity for d in defects)
    defect_count = sum(d.defect_quantity for d in defects)
    defect_rate = round(defect_count / total_items, 4) if total_items > 0 else 0.0

    # Top defect causes — aggregate from linked positions' quality checks
    cause_counts: dict[str, int] = {}
    for d in defects:
        if d.position_id:
            from api.models import QualityCheck
            qcs = db.query(QualityCheck).filter(
                QualityCheck.position_id == d.position_id,
                QualityCheck.result == "defect",
            ).all()
            for qc in qcs:
                if qc.defect_cause_id:
                    cause = db.query(DefectCause).filter(DefectCause.id == qc.defect_cause_id).first()
                    label = cause.code if cause else str(qc.defect_cause_id)
                    cause_counts[label] = cause_counts.get(label, 0) + 1

    top_defect_causes = sorted(cause_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "supplier_name": body.supplier_name,
        "factory_id": str(body.factory_id),
        "period": {"from": body.date_from.isoformat(), "to": body.date_to.isoformat()},
        "total_records": len(defects),
        "total_items": total_items,
        "defect_count": defect_count,
        "defect_rate": defect_rate,
        "top_defect_causes": [{"cause": c, "count": n} for c, n in top_defect_causes],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": str(current_user.id),
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
