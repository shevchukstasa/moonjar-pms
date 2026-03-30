"""Quality router — QC inspections, positions for QC, stats, QM blocks."""

from datetime import datetime, date, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user, apply_factory_filter
from api.roles import require_role
from api.models import (
    QualityCheck, QualityChecklist, OrderPosition, ProductionOrder, QmBlock,
    ProblemCard, DefectCause, User, Notification,
)
from api.enums import (
    QcResult, QcStage, PositionStatus, QmBlockType, NotificationType,
    RelatedEntityType, UserRole,
)
from business.services.status_machine import transition_position_status

require_qm_or_admin = require_role("owner", "administrator", "quality_manager")

router = APIRouter()


# ── helpers ──────────────────────────────────────────────────────────────

def _ev(val):
    return val.value if hasattr(val, "value") else str(val) if val else None


def _serialize_inspection(qc, db) -> dict:
    # Position info
    pos_info = {}
    if qc.position_id:
        pos = db.query(OrderPosition).filter(OrderPosition.id == qc.position_id).first()
        if pos:
            order = db.query(ProductionOrder).filter(ProductionOrder.id == pos.order_id).first()
            pos_info = {
                "order_number": order.order_number if order else None,
                "color": pos.color,
                "size": pos.size,
                "quantity": pos.quantity,
                "position_status": _ev(pos.status),
            }

    # Checker name
    checker_name = None
    if qc.checked_by:
        user = db.query(User).filter(User.id == qc.checked_by).first()
        checker_name = user.name if user else None

    # Defect cause
    cause_info = None
    if qc.defect_cause_id:
        cause = db.query(DefectCause).filter(DefectCause.id == qc.defect_cause_id).first()
        if cause:
            cause_info = {"id": str(cause.id), "code": cause.code, "description": cause.description}

    return {
        "id": str(qc.id),
        "position_id": str(qc.position_id) if qc.position_id else None,
        "factory_id": str(qc.factory_id),
        "stage": _ev(qc.stage),
        "result": _ev(qc.result),
        "defect_cause_id": str(qc.defect_cause_id) if qc.defect_cause_id else None,
        "defect_cause": cause_info,
        "notes": qc.notes,
        "checked_by": str(qc.checked_by) if qc.checked_by else None,
        "checked_by_name": checker_name,
        "created_at": qc.created_at.isoformat() if qc.created_at else None,
        **pos_info,
    }


def _serialize_position_for_qc(pos, db) -> dict:
    order = db.query(ProductionOrder).filter(ProductionOrder.id == pos.order_id).first()
    return {
        "id": str(pos.id),
        "order_id": str(pos.order_id),
        "order_number": order.order_number if order else None,
        "factory_id": str(pos.factory_id),
        "status": _ev(pos.status),
        "color": pos.color,
        "size": pos.size,
        "quantity": pos.quantity,
        "product_type": pos.product_type,
    }


# ── Pydantic models ─────────────────────────────────────────────────────

class DefectCauseCreateInput(BaseModel):
    code: str
    category: str
    description: Optional[str] = None


class InspectionInput(BaseModel):
    position_id: UUID
    factory_id: UUID
    stage: str = "sorting"  # glazing | firing | sorting
    result: str  # "ok" | "defect"
    defect_cause_id: Optional[UUID] = None
    notes: Optional[str] = None


class InspectionUpdateInput(BaseModel):
    result: Optional[str] = None
    notes: Optional[str] = None
    defect_cause_id: Optional[UUID] = None


class ChecklistInput(BaseModel):
    position_id: UUID
    factory_id: UUID
    checklist_results: dict  # {item_key: "pass"|"fail"|"na"}
    overall_result: str  # "pass" | "fail" | "needs_rework"
    notes: Optional[str] = None


# === QC CALENDAR MATRIX (Decision 2026-03-19) ===

@router.get("/calendar-matrix")
async def get_calendar_matrix(
    date_from: date = Query(..., description="Start date (inclusive)"),
    date_to: date = Query(..., description="End date (inclusive)"),
    factory_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    QC calendar matrix -- for each day in a date range, returns:
    inspections_count, pass_count, fail_count, and inspectors list.
    """
    from datetime import timedelta

    if date_from > date_to:
        raise HTTPException(400, "date_from must be <= date_to")

    if (date_to - date_from).days > 90:
        raise HTTPException(400, "Date range must not exceed 90 days")

    query = db.query(QualityCheck).filter(
        func.date(QualityCheck.created_at) >= date_from,
        func.date(QualityCheck.created_at) <= date_to,
    )
    query = apply_factory_filter(query, current_user, factory_id, QualityCheck)

    inspections = query.all()

    # Group by date
    by_date: dict[date, list] = {}
    for qc in inspections:
        d = qc.created_at.date() if qc.created_at else None
        if d is None:
            continue
        by_date.setdefault(d, []).append(qc)

    # Build calendar array for every day in range
    result = []
    current = date_from
    while current <= date_to:
        day_inspections = by_date.get(current, [])
        pass_count = sum(1 for qc in day_inspections if _ev(qc.result) == "ok")
        fail_count = sum(1 for qc in day_inspections if _ev(qc.result) == "defect")

        # Unique inspectors for the day
        inspector_ids: set = set()
        inspectors = []
        for qc in day_inspections:
            if qc.checked_by and qc.checked_by not in inspector_ids:
                inspector_ids.add(qc.checked_by)
                user = db.query(User).filter(User.id == qc.checked_by).first()
                inspectors.append({
                    "id": str(qc.checked_by),
                    "name": user.name if user else None,
                })

        result.append({
            "date": current.isoformat(),
            "inspections_count": len(day_inspections),
            "pass_count": pass_count,
            "fail_count": fail_count,
            "inspectors": inspectors,
        })
        current = current + timedelta(days=1)

    return {"items": result, "total": len(result)}


# ── endpoints ────────────────────────────────────────────────────────────

@router.get("/defect-causes")
async def list_defect_causes(
    category: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List all defect causes, optional filter by category."""
    query = db.query(DefectCause).filter(DefectCause.is_active.is_(True))
    if category:
        query = query.filter(DefectCause.category == category)
    items = query.order_by(DefectCause.code).all()
    return {
        "items": [
            {
                "id": str(c.id),
                "code": c.code,
                "category": c.category,
                "description": c.description,
                "is_active": c.is_active,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in items
        ],
        "total": len(items),
    }


@router.post("/defect-causes", status_code=201)
async def create_defect_cause(
    data: DefectCauseCreateInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_qm_or_admin),
):
    """Create a new defect cause (admin or quality_manager only)."""
    existing = db.query(DefectCause).filter(DefectCause.code == data.code).first()
    if existing:
        raise HTTPException(409, f"Defect cause with code '{data.code}' already exists")
    item = DefectCause(
        code=data.code,
        category=data.category,
        description=data.description,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {
        "id": str(item.id),
        "code": item.code,
        "category": item.category,
        "description": item.description,
        "is_active": item.is_active,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


@router.get("/inspections")
async def list_inspections(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    factory_id: UUID | None = None,
    stage: str | None = None,
    result: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(QualityCheck)
    query = apply_factory_filter(query, current_user, factory_id, QualityCheck)

    if stage:
        query = query.filter(QualityCheck.stage == stage)
    if result:
        query = query.filter(QualityCheck.result == result)

    total = query.count()
    items = query.order_by(
        QualityCheck.created_at.desc()
    ).offset((page - 1) * per_page).limit(per_page).all()

    return {
        "items": [_serialize_inspection(qc, db) for qc in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.post("/inspections", status_code=201)
async def create_inspection(
    data: InspectionInput,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create QC inspection. OK → quality_check_done. Defect → blocked_by_qm + QmBlock."""
    pos = db.query(OrderPosition).filter(OrderPosition.id == data.position_id).first()
    if not pos:
        raise HTTPException(404, "Position not found")

    if _ev(pos.status) != "sent_to_quality_check":
        raise HTTPException(400, f"Position status must be 'sent_to_quality_check', got '{_ev(pos.status)}'")

    if data.result not in ("ok", "defect"):
        raise HTTPException(400, "Result must be 'ok' or 'defect'")

    if data.result == "defect" and not data.defect_cause_id:
        raise HTTPException(400, "Defect cause is required when result is 'defect'")

    # Create QC record
    qc = QualityCheck(
        position_id=data.position_id,
        factory_id=data.factory_id,
        stage=data.stage,
        result=data.result,
        defect_cause_id=data.defect_cause_id,
        notes=data.notes,
        checked_by=current_user.id,
    )
    db.add(qc)

    if data.result == "ok":
        transition_position_status(db, pos.id, PositionStatus.QUALITY_CHECK_DONE.value, changed_by=current_user.id)
    else:
        transition_position_status(db, pos.id, PositionStatus.BLOCKED_BY_QM.value, changed_by=current_user.id)
        # Auto-create QmBlock
        block = QmBlock(
            factory_id=data.factory_id,
            block_type=QmBlockType.POSITION,
            position_id=data.position_id,
            reason=data.notes or "Defect found during QC inspection",
            severity="critical",
            blocked_by=current_user.id,
        )
        db.add(block)

    db.commit()
    db.refresh(qc)
    return _serialize_inspection(qc, db)


@router.patch("/inspections/{inspection_id}")
async def update_inspection(
    inspection_id: UUID,
    data: InspectionUpdateInput,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    qc = db.query(QualityCheck).filter(QualityCheck.id == inspection_id).first()
    if not qc:
        raise HTTPException(404, "Inspection not found")

    old_result = _ev(qc.result)
    updates = data.model_dump(exclude_unset=True)

    for k, v in updates.items():
        setattr(qc, k, v)

    new_result = updates.get("result", old_result)

    # Handle result change
    if old_result == "defect" and new_result == "ok" and qc.position_id:
        pos = db.query(OrderPosition).filter(OrderPosition.id == qc.position_id).first()
        if pos and _ev(pos.status) == "blocked_by_qm":
            transition_position_status(db, pos.id, PositionStatus.QUALITY_CHECK_DONE.value, changed_by=current_user.id)

        # Resolve any active QmBlock for this position
        block = db.query(QmBlock).filter(
            QmBlock.position_id == qc.position_id,
            QmBlock.resolved_at.is_(None),
        ).first()
        if block:
            block.resolved_by = current_user.id
            block.resolved_at = datetime.now(timezone.utc)
            block.resolution_note = "Inspection updated to OK"

    elif old_result == "ok" and new_result == "defect" and qc.position_id:
        pos = db.query(OrderPosition).filter(OrderPosition.id == qc.position_id).first()
        if pos:
            transition_position_status(db, pos.id, PositionStatus.BLOCKED_BY_QM.value, changed_by=current_user.id)
            block = QmBlock(
                factory_id=qc.factory_id,
                block_type=QmBlockType.POSITION,
                position_id=qc.position_id,
                reason=data.notes or "Inspection updated to defect",
                severity="critical",
                blocked_by=current_user.id,
            )
            db.add(block)

    db.commit()
    db.refresh(qc)
    return _serialize_inspection(qc, db)


@router.post("/inspections/{inspection_id}/photo")
async def upload_inspection_photo(
    inspection_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Upload a photo for a QC inspection. Stores as base64 data URL in DB."""
    import base64

    qc = db.query(QualityCheck).filter(QualityCheck.id == inspection_id).first()
    if not qc:
        raise HTTPException(404, "Inspection not found")

    # Validate file type
    content_type = file.content_type or "image/jpeg"
    if not content_type.startswith("image/"):
        raise HTTPException(400, "Only image files are allowed")

    # Read and encode (max 5MB)
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 5MB)")

    b64 = base64.b64encode(content).decode("utf-8")
    data_url = f"data:{content_type};base64,{b64}"

    # Append to photos array
    photos = list(qc.photos or [])
    photos.append(data_url)
    qc.photos = photos

    db.commit()
    db.refresh(qc)

    return {
        "status": "uploaded",
        "inspection_id": str(inspection_id),
        "photo_index": len(photos) - 1,
        "photos_count": len(photos),
    }


@router.get("/positions-for-qc")
async def get_positions_for_qc(
    factory_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Positions awaiting quality check."""
    query = db.query(OrderPosition).filter(
        OrderPosition.status == PositionStatus.SENT_TO_QUALITY_CHECK
    )
    query = apply_factory_filter(query, current_user, factory_id, OrderPosition)

    items = query.order_by(OrderPosition.created_at).all()
    return {
        "items": [_serialize_position_for_qc(p, db) for p in items],
        "total": len(items),
    }


@router.get("/stats")
async def get_quality_stats(
    factory_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Dashboard KPI stats."""
    # Pending QC
    qc_query = db.query(OrderPosition).filter(
        OrderPosition.status == PositionStatus.SENT_TO_QUALITY_CHECK
    )
    qc_query = apply_factory_filter(qc_query, current_user, factory_id, OrderPosition)
    pending_qc = qc_query.count()

    # Active QM blocks
    block_query = db.query(QmBlock).filter(QmBlock.resolved_at.is_(None))
    if factory_id:
        block_query = block_query.filter(QmBlock.factory_id == factory_id)
    blocked = block_query.count()

    # Open problem cards
    pc_query = db.query(ProblemCard).filter(ProblemCard.status.in_(["open", "in_progress"]))
    if factory_id:
        pc_query = pc_query.filter(ProblemCard.factory_id == factory_id)
    open_cards = pc_query.count()

    # Inspections today
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_query = db.query(QualityCheck).filter(QualityCheck.created_at >= today_start)
    today_query = apply_factory_filter(today_query, current_user, factory_id, QualityCheck)
    inspections_today = today_query.count()

    return {
        "pending_qc": pending_qc,
        "blocked": blocked,
        "open_problem_cards": open_cards,
        "inspections_today": inspections_today,
    }


# ── LLM Photo Analysis ───────────────────────────────────────────────────

@router.post("/analyze-photo")
async def analyze_production_photo(
    file: UploadFile = File(...),
    analysis_type: str = Query("quality", description="scale | quality | packing"),
    position_id: UUID | None = Query(None, description="Optional position to link analysis to"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Analyze a production photo using LLM vision (Claude).

    Accepts an image file and returns structured analysis:
    - scale: reads weight, identifies pigment color
    - quality: detects defects, cracks, color issues
    - packing: reads label data (order number, quantity, size)
    """
    from business.services.photo_analysis import analyze_photo, format_analysis_message

    # Validate analysis_type
    if analysis_type not in ("scale", "quality", "packing"):
        raise HTTPException(400, "analysis_type must be 'scale', 'quality', or 'packing'")

    # Validate file type
    content_type = file.content_type or "image/jpeg"
    if not content_type.startswith("image/"):
        raise HTTPException(400, "Only image files are allowed")

    # Read image (max 10MB for analysis)
    image_bytes = await file.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 10MB)")

    if not image_bytes:
        raise HTTPException(400, "Empty file")

    # Build context
    context = {}
    if position_id:
        pos = db.query(OrderPosition).filter(OrderPosition.id == position_id).first()
        if pos:
            order = db.query(ProductionOrder).filter(ProductionOrder.id == pos.order_id).first()
            context["position"] = order.order_number if order else str(position_id)
            if pos.color:
                context["expected_color"] = pos.color

    # Call LLM analysis
    result = await analyze_photo(
        image_bytes=image_bytes,
        analysis_type=analysis_type,
        context=context if context else None,
    )

    if result is None:
        raise HTTPException(
            503,
            "Photo analysis unavailable. ANTHROPIC_API_KEY may not be configured or the API call failed.",
        )

    return {
        "analysis_type": result["analysis_type"],
        "readings": result["readings"],
        "confidence": result["confidence"],
        "issues": result["issues"],
        "raw_description": result["raw_description"],
        "position_id": str(position_id) if position_id else None,
        "message": format_analysis_message(result),
    }


# ── Structured QC Checklists ─────────────────────────────────────────────

# Pre-kiln checklist item definitions
PRE_KILN_CHECKLIST_ITEMS = {
    "glaze_coverage_uniform": "Glaze coverage uniform",
    "glaze_thickness_correct": "Glaze thickness correct",
    "no_drips_or_runs": "No drips or runs",
    "engobe_applied_correctly": "Engobe applied correctly",
    "edge_glazing_complete": "Edge glazing complete",
    "correct_color_recipe_verified": "Correct color/recipe verified",
    "tile_dimensions_within_tolerance": "Tile dimensions within tolerance",
    "no_cracks_or_chips": "No cracks or chips",
}

# Final QC checklist item definitions
FINAL_CHECKLIST_ITEMS = {
    "correct_quantity_matches_order": "Correct quantity matches order",
    "all_tiles_match_color_sample": "All tiles match color sample",
    "no_visible_defects": "No visible defects",
    "correct_packaging_label": "Correct packaging label",
    "packaging_intact_no_damage": "Packaging intact, no damage",
    "size_matches_order_specification": "Size matches order specification",
    "documentation_complete": "Documentation complete",
}


def _serialize_checklist(cl: QualityChecklist, db: Session) -> dict:
    """Serialize a QualityChecklist with position context."""
    pos_info: dict = {}
    if cl.position_id:
        pos = db.query(OrderPosition).filter(OrderPosition.id == cl.position_id).first()
        if pos:
            order = db.query(ProductionOrder).filter(ProductionOrder.id == pos.order_id).first()
            pos_info = {
                "order_number": order.order_number if order else None,
                "color": pos.color,
                "size": pos.size,
                "quantity": pos.quantity,
                "position_status": _ev(pos.status),
            }

    checker_name = None
    if cl.checked_by:
        user = db.query(User).filter(User.id == cl.checked_by).first()
        checker_name = user.name if user else None

    return {
        "id": str(cl.id),
        "position_id": str(cl.position_id),
        "factory_id": str(cl.factory_id),
        "check_type": cl.check_type,
        "checklist_results": cl.checklist_results,
        "overall_result": cl.overall_result,
        "checked_by": str(cl.checked_by) if cl.checked_by else None,
        "checked_by_name": checker_name,
        "notes": cl.notes,
        "created_at": cl.created_at.isoformat() if cl.created_at else None,
        **pos_info,
    }


def _notify_pm_on_fail(db: Session, position: OrderPosition, check_type: str, factory_id) -> None:
    """Create notification for production managers when a QC checklist fails."""
    order = db.query(ProductionOrder).filter(ProductionOrder.id == position.order_id).first()
    order_num = order.order_number if order else "?"
    label = "Pre-Kiln QC" if check_type == "pre_kiln" else "Final QC"

    pms = db.query(User).filter(
        User.role == UserRole.PRODUCTION_MANAGER,
        User.is_active.is_(True),
    ).all()
    for pm in pms:
        notif = Notification(
            user_id=pm.id,
            factory_id=factory_id,
            type=NotificationType.ALERT,
            title=f"{label} Failed — {order_num}",
            message=f"Position {position.color} {position.size} failed {label.lower()}.",
            related_entity_type=RelatedEntityType.POSITION,
            related_entity_id=position.id,
        )
        db.add(notif)


@router.get("/checklist-items")
async def get_checklist_items(
    check_type: str = Query(..., description="pre_kiln or final"),
    current_user=Depends(get_current_user),
):
    """Return the list of checklist items for a given check type."""
    if check_type == "pre_kiln":
        return {"check_type": check_type, "items": PRE_KILN_CHECKLIST_ITEMS}
    elif check_type == "final":
        return {"check_type": check_type, "items": FINAL_CHECKLIST_ITEMS}
    else:
        raise HTTPException(400, "check_type must be 'pre_kiln' or 'final'")


# ── Pre-Kiln QC (Step 12) ────────────────────────────────────────────────

@router.post("/pre-kiln-check", status_code=201)
async def create_pre_kiln_check(
    data: ChecklistInput,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Create a pre-kiln quality checklist.

    Position must be in 'glazed' status.
    - pass → position status → 'pre_kiln_check' (can proceed to kiln loading)
    - fail / needs_rework → position stays 'glazed', PM gets notification
    """
    pos = db.query(OrderPosition).filter(OrderPosition.id == data.position_id).first()
    if not pos:
        raise HTTPException(404, "Position not found")

    if _ev(pos.status) != "glazed":
        raise HTTPException(
            400,
            f"Position must be in 'glazed' status for pre-kiln check, got '{_ev(pos.status)}'",
        )

    if data.overall_result not in ("pass", "fail", "needs_rework"):
        raise HTTPException(400, "overall_result must be 'pass', 'fail', or 'needs_rework'")

    # Validate checklist keys
    for key in data.checklist_results:
        if key not in PRE_KILN_CHECKLIST_ITEMS:
            raise HTTPException(400, f"Unknown checklist item: '{key}'")
    for val in data.checklist_results.values():
        if val not in ("pass", "fail", "na"):
            raise HTTPException(400, f"Checklist value must be 'pass', 'fail', or 'na', got '{val}'")

    cl = QualityChecklist(
        position_id=data.position_id,
        factory_id=data.factory_id,
        check_type="pre_kiln",
        checklist_results=data.checklist_results,
        overall_result=data.overall_result,
        checked_by=current_user.id,
        notes=data.notes,
    )
    db.add(cl)

    if data.overall_result == "pass":
        transition_position_status(db, pos.id, PositionStatus.PRE_KILN_CHECK.value, changed_by=current_user.id)
    else:
        # Position stays at 'glazed', notify PM
        _notify_pm_on_fail(db, pos, "pre_kiln", data.factory_id)

    db.commit()
    db.refresh(cl)
    return _serialize_checklist(cl, db)


@router.get("/pre-kiln-checks")
async def list_pre_kiln_checks(
    position_id: UUID | None = None,
    factory_id: UUID | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get pre-kiln checklist records, optionally filtered by position or factory."""
    query = db.query(QualityChecklist).filter(QualityChecklist.check_type == "pre_kiln")
    if position_id:
        query = query.filter(QualityChecklist.position_id == position_id)
    query = apply_factory_filter(query, current_user, factory_id, QualityChecklist)

    total = query.count()
    items = query.order_by(QualityChecklist.created_at.desc()).offset(
        (page - 1) * per_page
    ).limit(per_page).all()

    return {
        "items": [_serialize_checklist(cl, db) for cl in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# ── Final QC (Step 21) ───────────────────────────────────────────────────

@router.post("/final-check", status_code=201)
async def create_final_check(
    data: ChecklistInput,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Create a final quality checklist for packed goods.

    Position must be in 'packed' status.
    - pass → position status → 'ready_for_shipment'
    - fail → position stays 'packed', PM gets notification
    """
    pos = db.query(OrderPosition).filter(OrderPosition.id == data.position_id).first()
    if not pos:
        raise HTTPException(404, "Position not found")

    if _ev(pos.status) != "packed":
        raise HTTPException(
            400,
            f"Position must be in 'packed' status for final check, got '{_ev(pos.status)}'",
        )

    if data.overall_result not in ("pass", "fail"):
        raise HTTPException(400, "overall_result for final check must be 'pass' or 'fail'")

    # Validate checklist keys
    for key in data.checklist_results:
        if key not in FINAL_CHECKLIST_ITEMS:
            raise HTTPException(400, f"Unknown checklist item: '{key}'")
    for val in data.checklist_results.values():
        if val not in ("pass", "fail", "na"):
            raise HTTPException(400, f"Checklist value must be 'pass', 'fail', or 'na', got '{val}'")

    cl = QualityChecklist(
        position_id=data.position_id,
        factory_id=data.factory_id,
        check_type="final",
        checklist_results=data.checklist_results,
        overall_result=data.overall_result,
        checked_by=current_user.id,
        notes=data.notes,
    )
    db.add(cl)

    if data.overall_result == "pass":
        transition_position_status(db, pos.id, PositionStatus.READY_FOR_SHIPMENT.value, changed_by=current_user.id)
    else:
        # Position stays at 'packed', notify PM
        _notify_pm_on_fail(db, pos, "final", data.factory_id)

    db.commit()
    db.refresh(cl)
    return _serialize_checklist(cl, db)


@router.get("/final-checks")
async def list_final_checks(
    position_id: UUID | None = None,
    factory_id: UUID | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get final checklist records, optionally filtered by position or factory."""
    query = db.query(QualityChecklist).filter(QualityChecklist.check_type == "final")
    if position_id:
        query = query.filter(QualityChecklist.position_id == position_id)
    query = apply_factory_filter(query, current_user, factory_id, QualityChecklist)

    total = query.count()
    items = query.order_by(QualityChecklist.created_at.desc()).offset(
        (page - 1) * per_page
    ).limit(per_page).all()

    return {
        "items": [_serialize_checklist(cl, db) for cl in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }
