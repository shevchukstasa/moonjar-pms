"""CRUD router for kiln inspections (checklists) and repair logs."""

import logging
from uuid import UUID
from datetime import date, datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from api.database import get_db
from api.auth import get_current_user, apply_factory_filter
from api.roles import require_management
from api.models import (
    KilnInspectionItem, KilnInspection, KilnInspectionResult,
    KilnRepairLog, Resource,
)

logger = logging.getLogger("moonjar.kiln_inspections")

router = APIRouter()


# ── Pydantic Schemas ────────────────────────────────

class InspectionResultInput(BaseModel):
    item_id: str
    result: str  # ok, not_applicable, damaged, needs_repair
    notes: Optional[str] = None


class InspectionCreateInput(BaseModel):
    resource_id: str
    factory_id: str
    inspection_date: date
    results: List[InspectionResultInput]
    notes: Optional[str] = None


class RepairLogInput(BaseModel):
    resource_id: str
    factory_id: str
    date_reported: Optional[date] = None
    issue_description: str
    diagnosis: Optional[str] = None
    repair_actions: Optional[str] = None
    spare_parts_used: Optional[str] = None
    technician: Optional[str] = None
    date_completed: Optional[date] = None
    status: str = "open"
    notes: Optional[str] = None
    inspection_result_id: Optional[str] = None


class RepairLogUpdateInput(BaseModel):
    issue_description: Optional[str] = None
    diagnosis: Optional[str] = None
    repair_actions: Optional[str] = None
    spare_parts_used: Optional[str] = None
    technician: Optional[str] = None
    date_completed: Optional[date] = None
    status: Optional[str] = None
    notes: Optional[str] = None


# ── Helpers ──────────────────────────────────────────

def _serialize_item(item: KilnInspectionItem) -> dict:
    return {
        "id": str(item.id),
        "category": item.category,
        "item_text": item.item_text,
        "sort_order": item.sort_order,
        "is_active": item.is_active,
        "applies_to_kiln_types": item.applies_to_kiln_types,
    }


def _serialize_inspection(insp: KilnInspection) -> dict:
    return {
        "id": str(insp.id),
        "resource_id": str(insp.resource_id),
        "resource_name": insp.resource.name if insp.resource else None,
        "factory_id": str(insp.factory_id),
        "inspection_date": str(insp.inspection_date),
        "inspected_by_id": str(insp.inspected_by_id),
        "inspected_by_name": insp.inspected_by.full_name if insp.inspected_by else None,
        "notes": insp.notes,
        "created_at": insp.created_at.isoformat() if insp.created_at else None,
        "results": [
            {
                "id": str(r.id),
                "item_id": str(r.item_id),
                "category": r.item.category if r.item else None,
                "item_text": r.item.item_text if r.item else None,
                "result": r.result,
                "notes": r.notes,
            }
            for r in (insp.results or [])
        ],
        "summary": _summarize_results(insp.results or []),
    }


def _summarize_results(results: list) -> dict:
    total = len(results)
    ok = sum(1 for r in results if r.result == "ok")
    damaged = sum(1 for r in results if r.result in ("damaged", "needs_repair"))
    na = sum(1 for r in results if r.result == "not_applicable")
    return {"total": total, "ok": ok, "issues": damaged, "not_applicable": na}


def _serialize_repair(rep: KilnRepairLog) -> dict:
    return {
        "id": str(rep.id),
        "resource_id": str(rep.resource_id),
        "resource_name": rep.resource.name if rep.resource else None,
        "factory_id": str(rep.factory_id),
        "date_reported": str(rep.date_reported) if rep.date_reported else None,
        "reported_by_id": str(rep.reported_by_id),
        "reported_by_name": rep.reported_by.full_name if rep.reported_by else None,
        "issue_description": rep.issue_description,
        "diagnosis": rep.diagnosis,
        "repair_actions": rep.repair_actions,
        "spare_parts_used": rep.spare_parts_used,
        "technician": rep.technician,
        "date_completed": str(rep.date_completed) if rep.date_completed else None,
        "status": rep.status,
        "notes": rep.notes,
        "inspection_result_id": str(rep.inspection_result_id) if rep.inspection_result_id else None,
        "created_at": rep.created_at.isoformat() if rep.created_at else None,
        "updated_at": rep.updated_at.isoformat() if rep.updated_at else None,
    }


# ── Inspection Items (Template) ────────────────────

@router.get("/items")
async def list_inspection_items(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List all active inspection checklist items grouped by category."""
    items = (
        db.query(KilnInspectionItem)
        .filter(KilnInspectionItem.is_active == True)
        .order_by(KilnInspectionItem.sort_order)
        .all()
    )
    # Group by category
    categories: dict = {}
    for item in items:
        cat = item.category
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(_serialize_item(item))

    return {"categories": categories, "total_items": len(items)}


# ── Inspections CRUD ───────────────────────────────

@router.get("")
async def list_inspections(
    resource_id: UUID | None = Query(None),
    factory_id: UUID | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List inspections with optional filters."""
    query = (
        db.query(KilnInspection)
        .options(
            joinedload(KilnInspection.resource),
            joinedload(KilnInspection.inspected_by),
            joinedload(KilnInspection.results).joinedload(KilnInspectionResult.item),
        )
    )
    query = apply_factory_filter(query, current_user, factory_id, KilnInspection)

    if resource_id:
        query = query.filter(KilnInspection.resource_id == resource_id)
    if date_from:
        query = query.filter(KilnInspection.inspection_date >= date_from)
    if date_to:
        query = query.filter(KilnInspection.inspection_date <= date_to)

    inspections = query.order_by(KilnInspection.inspection_date.desc()).limit(200).all()
    return {
        "items": [_serialize_inspection(i) for i in inspections],
        "total": len(inspections),
    }


@router.get("/{inspection_id}")
async def get_inspection(
    inspection_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    insp = (
        db.query(KilnInspection)
        .options(
            joinedload(KilnInspection.resource),
            joinedload(KilnInspection.inspected_by),
            joinedload(KilnInspection.results).joinedload(KilnInspectionResult.item),
        )
        .filter(KilnInspection.id == inspection_id)
        .first()
    )
    if not insp:
        raise HTTPException(404, "Inspection not found")
    return _serialize_inspection(insp)


@router.delete("/{inspection_id}")
async def delete_inspection(
    inspection_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Delete a kiln inspection and its results."""
    insp = db.query(KilnInspection).filter(KilnInspection.id == inspection_id).first()
    if not insp:
        raise HTTPException(404, "Inspection not found")

    # Factory scoping: check inspection belongs to user's factory
    if (
        hasattr(current_user, "factory_id")
        and current_user.factory_id
        and str(insp.factory_id) != str(current_user.factory_id)
    ):
        raise HTTPException(403, "Cannot delete inspection from another factory")

    logger.info(
        "DELETE_INSPECTION | id=%s kiln=%s date=%s by=%s",
        inspection_id, insp.resource_id, insp.inspection_date, current_user.full_name,
    )
    db.delete(insp)
    db.commit()
    return {"ok": True}


@router.post("", status_code=201)
async def create_inspection(
    data: InspectionCreateInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Create a new kiln inspection with all checklist results."""
    # Validate kiln exists
    resource = db.query(Resource).filter(Resource.id == UUID(data.resource_id)).first()
    if not resource:
        raise HTTPException(404, "Kiln not found")

    # Check duplicate
    existing = (
        db.query(KilnInspection)
        .filter(
            KilnInspection.resource_id == UUID(data.resource_id),
            KilnInspection.inspection_date == data.inspection_date,
        )
        .first()
    )
    if existing:
        raise HTTPException(409, f"Inspection already exists for this kiln on {data.inspection_date}")

    insp = KilnInspection(
        resource_id=UUID(data.resource_id),
        factory_id=UUID(data.factory_id),
        inspection_date=data.inspection_date,
        inspected_by_id=current_user.id,
        notes=data.notes,
    )
    db.add(insp)
    db.flush()

    for r in data.results:
        result = KilnInspectionResult(
            inspection_id=insp.id,
            item_id=UUID(r.item_id),
            result=r.result,
            notes=r.notes,
        )
        db.add(result)

    db.commit()
    db.refresh(insp)

    # Reload with relationships
    insp = (
        db.query(KilnInspection)
        .options(
            joinedload(KilnInspection.resource),
            joinedload(KilnInspection.inspected_by),
            joinedload(KilnInspection.results).joinedload(KilnInspectionResult.item),
        )
        .filter(KilnInspection.id == insp.id)
        .first()
    )

    logger.info(
        "INSPECTION | kiln=%s date=%s by=%s | %d items",
        resource.name, data.inspection_date, current_user.full_name, len(data.results),
    )
    return _serialize_inspection(insp)


# ── Repair Log CRUD ────────────────────────────────

@router.get("/repairs")
async def list_repairs(
    resource_id: UUID | None = Query(None),
    factory_id: UUID | None = Query(None),
    status: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List repair log entries."""
    query = (
        db.query(KilnRepairLog)
        .options(
            joinedload(KilnRepairLog.resource),
            joinedload(KilnRepairLog.reported_by),
        )
    )
    query = apply_factory_filter(query, current_user, factory_id, KilnRepairLog)

    if resource_id:
        query = query.filter(KilnRepairLog.resource_id == resource_id)
    if status:
        query = query.filter(KilnRepairLog.status == status)

    repairs = query.order_by(KilnRepairLog.date_reported.desc()).limit(200).all()
    return {
        "items": [_serialize_repair(r) for r in repairs],
        "total": len(repairs),
    }


@router.post("/repairs", status_code=201)
async def create_repair(
    data: RepairLogInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Create a new repair log entry."""
    resource = db.query(Resource).filter(Resource.id == UUID(data.resource_id)).first()
    if not resource:
        raise HTTPException(404, "Kiln not found")

    repair = KilnRepairLog(
        resource_id=UUID(data.resource_id),
        factory_id=UUID(data.factory_id),
        date_reported=data.date_reported or date.today(),
        reported_by_id=current_user.id,
        issue_description=data.issue_description,
        diagnosis=data.diagnosis,
        repair_actions=data.repair_actions,
        spare_parts_used=data.spare_parts_used,
        technician=data.technician,
        date_completed=data.date_completed,
        status=data.status,
        notes=data.notes,
        inspection_result_id=UUID(data.inspection_result_id) if data.inspection_result_id else None,
    )
    db.add(repair)
    db.commit()
    db.refresh(repair)

    logger.info(
        "REPAIR_LOG | kiln=%s issue=%s status=%s",
        resource.name, data.issue_description[:50], data.status,
    )

    # Reload with relationships
    repair = (
        db.query(KilnRepairLog)
        .options(joinedload(KilnRepairLog.resource), joinedload(KilnRepairLog.reported_by))
        .filter(KilnRepairLog.id == repair.id)
        .first()
    )
    return _serialize_repair(repair)


@router.patch("/repairs/{repair_id}")
async def update_repair(
    repair_id: UUID,
    data: RepairLogUpdateInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Update repair log entry."""
    repair = db.query(KilnRepairLog).filter(KilnRepairLog.id == repair_id).first()
    if not repair:
        raise HTTPException(404, "Repair log entry not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(repair, field, value)
    repair.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(repair)

    # Reload with relationships
    repair = (
        db.query(KilnRepairLog)
        .options(joinedload(KilnRepairLog.resource), joinedload(KilnRepairLog.reported_by))
        .filter(KilnRepairLog.id == repair.id)
        .first()
    )
    return _serialize_repair(repair)


@router.delete("/repairs/{repair_id}")
async def delete_repair(
    repair_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    repair = db.query(KilnRepairLog).filter(KilnRepairLog.id == repair_id).first()
    if not repair:
        raise HTTPException(404, "Repair log entry not found")
    db.delete(repair)
    db.commit()
    return {"ok": True}


# ── Matrix view (for spreadsheet-like display) ────

@router.get("/matrix")
async def inspection_matrix(
    factory_id: UUID | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return inspection data in matrix format: dates × kilns × items.
    Used by the frontend to render the spreadsheet-like checklist view."""
    query = (
        db.query(KilnInspection)
        .options(
            joinedload(KilnInspection.resource),
            joinedload(KilnInspection.results).joinedload(KilnInspectionResult.item),
        )
    )
    query = apply_factory_filter(query, current_user, factory_id, KilnInspection)

    if date_from:
        query = query.filter(KilnInspection.inspection_date >= date_from)
    if date_to:
        query = query.filter(KilnInspection.inspection_date <= date_to)

    inspections = query.order_by(KilnInspection.inspection_date).all()

    # Build matrix: {date_str: {kiln_name: {item_id: result}}}
    matrix: dict = {}
    dates = set()
    kilns = {}  # id -> name

    for insp in inspections:
        d = str(insp.inspection_date)
        dates.add(d)
        kiln_name = insp.resource.name if insp.resource else str(insp.resource_id)
        kilns[str(insp.resource_id)] = kiln_name

        if d not in matrix:
            matrix[d] = {}
        if kiln_name not in matrix[d]:
            matrix[d][kiln_name] = {}

        for r in insp.results:
            matrix[d][kiln_name][str(r.item_id)] = {
                "result": r.result,
                "notes": r.notes,
            }

    return {
        "dates": sorted(dates),
        "kilns": kilns,
        "matrix": matrix,
    }
