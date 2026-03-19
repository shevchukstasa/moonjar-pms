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
    QualityCheck, OrderPosition, ProductionOrder, QmBlock, ProblemCard,
    DefectCause, User,
)
from api.enums import QcResult, QcStage, PositionStatus, QmBlockType

require_qm_or_admin = require_role("administrator", "quality_manager")

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
        pos.status = PositionStatus.QUALITY_CHECK_DONE
    else:
        pos.status = PositionStatus.BLOCKED_BY_QM
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
            pos.status = PositionStatus.QUALITY_CHECK_DONE

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
            pos.status = PositionStatus.BLOCKED_BY_QM
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
