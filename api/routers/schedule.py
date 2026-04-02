"""Schedule router — resources, batches, section schedules."""

import logging
from datetime import date
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user, apply_factory_filter
from api.roles import require_management
from api.models import Resource, Batch, OrderPosition, ProductionOrder
from api.enums import ResourceType, BatchStatus, BatchCreator, PositionStatus, ResourceStatus

logger = logging.getLogger("moonjar.schedule")

router = APIRouter()


def _ev(val):
    return val.value if hasattr(val, "value") else str(val) if val else None


# Section → status mapping (same as positions router)
SECTION_STATUSES = {
    "glazing": [
        PositionStatus.PLANNED, PositionStatus.INSUFFICIENT_MATERIALS,
        PositionStatus.AWAITING_RECIPE, PositionStatus.AWAITING_STENCIL_SILKSCREEN,
        PositionStatus.AWAITING_COLOR_MATCHING, PositionStatus.ENGOBE_APPLIED,
        PositionStatus.ENGOBE_CHECK, PositionStatus.GLAZED,
        PositionStatus.PRE_KILN_CHECK, PositionStatus.SENT_TO_GLAZING,
    ],
    "firing": [
        PositionStatus.LOADED_IN_KILN, PositionStatus.FIRED,
        PositionStatus.REFIRE, PositionStatus.AWAITING_REGLAZE,
    ],
    "sorting": [
        PositionStatus.TRANSFERRED_TO_SORTING, PositionStatus.PACKED,
        PositionStatus.READY_FOR_SHIPMENT,
    ],
    "qc": [
        PositionStatus.SENT_TO_QUALITY_CHECK, PositionStatus.QUALITY_CHECK_DONE,
        PositionStatus.BLOCKED_BY_QM,
    ],
}


def _serialize_resource(r) -> dict:
    return {
        "id": str(r.id),
        "name": r.name,
        "resource_type": _ev(r.resource_type),
        "factory_id": str(r.factory_id),
        "capacity_sqm": float(r.capacity_sqm) if r.capacity_sqm else None,
        "capacity_pcs": r.capacity_pcs,
        "num_levels": r.num_levels,
        "status": _ev(r.status),
        "kiln_dimensions_cm": r.kiln_dimensions_cm,
        "kiln_working_area_cm": r.kiln_working_area_cm,
        "kiln_multi_level": r.kiln_multi_level,
        "kiln_coefficient": float(r.kiln_coefficient) if r.kiln_coefficient else None,
        "kiln_type": r.kiln_type,
        "is_active": r.is_active,
    }


def _serialize_batch(b, db: Session) -> dict:
    positions = db.query(OrderPosition).filter(OrderPosition.batch_id == b.id).all()
    total_pcs = sum(p.quantity or 0 for p in positions)
    return {
        "id": str(b.id),
        "resource_id": str(b.resource_id),
        "resource_name": b.resource.name if b.resource else "",
        "factory_id": str(b.factory_id),
        "batch_date": str(b.batch_date) if b.batch_date else None,
        "status": _ev(b.status),
        "created_by": _ev(b.created_by),
        "notes": b.notes,
        "total_pcs": total_pcs,
        "positions_count": len(positions),
        "created_at": b.created_at.isoformat() if b.created_at else None,
    }


def _position_label_brief(p) -> str | None:
    """Compute #N or #N.M label from position_number + split_index."""
    num = getattr(p, "position_number", None)
    idx = getattr(p, "split_index", None)
    if num is None:
        return None
    return f"#{num}.{idx}" if idx is not None else f"#{num}"


def _compute_material_status(p) -> str:
    """Derive material status from position fields (no extra DB queries)."""
    if getattr(p, "materials_written_off_at", None):
        return "consumed"
    if getattr(p, "reservation_at", None):
        return "reserved"
    status_val = p.status.value if hasattr(p.status, "value") else str(p.status) if p.status else ""
    if status_val == "insufficient_materials":
        return "insufficient"
    if status_val == "awaiting_consumption_data":
        return "awaiting_data"
    return "not_reserved"


def _serialize_position_brief(p) -> dict:
    return {
        "id": str(p.id),
        "order_id": str(p.order_id),
        "factory_id": str(p.factory_id) if p.factory_id else None,
        "order_number": p.order.order_number if p.order else "",
        "client": p.order.client if p.order else None,
        "final_deadline": str(p.order.final_deadline) if p.order and p.order.final_deadline else None,
        "status": _ev(p.status),
        "color": p.color,
        "size": p.size,
        "application": p.application,
        "application_method": getattr(p, "application_method_code", None),
        "collection": p.collection,
        "quantity": p.quantity,
        "product_type": _ev(p.product_type),
        "delay_hours": float(p.delay_hours) if p.delay_hours else 0,
        "priority_order": p.priority_order,
        "batch_id": str(p.batch_id) if p.batch_id else None,
        # Position numbering — for display in schedule and tablo
        "position_number": getattr(p, "position_number", None),
        "split_index": getattr(p, "split_index", None),
        "position_label": _position_label_brief(p),
        "parent_position_id": str(p.parent_position_id) if p.parent_position_id else None,
        "is_merged": getattr(p, "is_merged", False),
        # Physical properties — needed for schedule/tablo display
        "shape": _ev(p.shape) if getattr(p, "shape", None) else None,
        "shape_dimensions": p.shape_dimensions if getattr(p, "shape_dimensions", None) else None,
        "thickness_mm": float(p.thickness_mm) if getattr(p, "thickness_mm", None) else None,
        "width_cm": float(p.width_cm) if getattr(p, "width_cm", None) else None,
        "length_cm": float(p.length_cm) if getattr(p, "length_cm", None) else None,
        "calculated_area_cm2": float(p.calculated_area_cm2) if getattr(p, "calculated_area_cm2", None) else None,
        "place_of_application": getattr(p, "place_of_application", None),
        "edge_profile": getattr(p, "edge_profile", None),
        "edge_profile_sides": getattr(p, "edge_profile_sides", None),
        "edge_profile_notes": getattr(p, "edge_profile_notes", None),
        # Upfront schedule (TOC/DBR)
        "planned_glazing_date": str(p.planned_glazing_date) if p.planned_glazing_date else None,
        "planned_kiln_date": str(p.planned_kiln_date) if p.planned_kiln_date else None,
        "planned_sorting_date": str(p.planned_sorting_date) if p.planned_sorting_date else None,
        "planned_completion_date": str(p.planned_completion_date) if p.planned_completion_date else None,
        "estimated_kiln_id": str(p.estimated_kiln_id) if p.estimated_kiln_id else None,
        "schedule_version": getattr(p, "schedule_version", None),
        # Material tracking
        "material_status": _compute_material_status(p),
    }


class BatchCreateInput(BaseModel):
    resource_id: str
    factory_id: str
    batch_date: date
    position_ids: list[str] = []
    notes: Optional[str] = None


class PositionReorderInput(BaseModel):
    position_ids: list[str]


class BatchAssignPositionsInput(BaseModel):
    position_ids: list[str]


# --- Endpoints ---

@router.get("/resources")
async def list_resources(
    factory_id: UUID | None = None,
    resource_type: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(Resource).filter(Resource.is_active == True)
    query = apply_factory_filter(query, current_user, factory_id, Resource)
    if resource_type:
        query = query.filter(Resource.resource_type == resource_type)
    resources = query.order_by(Resource.name).all()
    return {"items": [_serialize_resource(r) for r in resources], "total": len(resources)}


@router.get("/batches")
async def list_batches(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    factory_id: UUID | None = None,
    resource_id: UUID | None = None,
    status: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(Batch)
    query = apply_factory_filter(query, current_user, factory_id, Batch)
    if resource_id:
        query = query.filter(Batch.resource_id == resource_id)
    if status:
        query = query.filter(Batch.status == status)
    if date_from:
        query = query.filter(Batch.batch_date >= date_from)
    if date_to:
        query = query.filter(Batch.batch_date <= date_to)

    total = query.count()
    batches = query.order_by(Batch.batch_date.desc()).offset(
        (page - 1) * per_page
    ).limit(per_page).all()

    return {
        "items": [_serialize_batch(b, db) for b in batches],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.post("/batches", status_code=201)
async def create_batch(
    data: BatchCreateInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    # Block batch creation on kilns under maintenance
    kiln = db.query(Resource).filter(
        Resource.id == UUID(data.resource_id),
        Resource.resource_type == ResourceType.KILN,
    ).first()
    if kiln and kiln.status in (
        ResourceStatus.MAINTENANCE_PLANNED,
        ResourceStatus.MAINTENANCE_EMERGENCY,
    ):
        other_kilns = db.query(Resource).filter(
            Resource.factory_id == kiln.factory_id,
            Resource.resource_type == ResourceType.KILN,
            Resource.status == ResourceStatus.ACTIVE,
            Resource.id != kiln.id,
        ).all()
        if other_kilns:
            alternatives = ", ".join(f"'{k.name}'" for k in other_kilns)
            raise HTTPException(
                400,
                detail=f"Kiln '{kiln.name}' is under {kiln.status.value}. Available alternatives: {alternatives}.",
            )
        raise HTTPException(
            400,
            detail=f"Kiln '{kiln.name}' is under {kiln.status.value} and no other active kilns are available.",
        )

    batch = Batch(
        resource_id=UUID(data.resource_id),
        factory_id=UUID(data.factory_id),
        batch_date=data.batch_date,
        status=BatchStatus.PLANNED,
        created_by=BatchCreator.MANUAL,
        notes=data.notes,
    )
    db.add(batch)
    db.flush()

    # Assign positions to batch
    for pid in data.position_ids:
        pos = db.query(OrderPosition).filter(OrderPosition.id == UUID(pid)).first()
        if pos:
            pos.batch_id = batch.id
            pos.resource_id = UUID(data.resource_id)

    db.commit()
    db.refresh(batch)
    return _serialize_batch(batch, db)


def _apply_schedule_order(query):
    """Sort: manual priority → order deadline (nulls last) → position # → split index."""
    return query.outerjoin(
        ProductionOrder, OrderPosition.order_id == ProductionOrder.id
    ).order_by(
        OrderPosition.priority_order,
        ProductionOrder.final_deadline.asc().nullslast(),
        OrderPosition.position_number,
        OrderPosition.split_index,
        OrderPosition.created_at,
    )


@router.get("/glazing-schedule")
async def get_glazing_schedule(
    factory_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(OrderPosition).filter(
        OrderPosition.status.in_(SECTION_STATUSES["glazing"])
    )
    query = apply_factory_filter(query, current_user, factory_id, OrderPosition)
    positions = _apply_schedule_order(query).all()
    return {"items": [_serialize_position_brief(p) for p in positions], "total": len(positions)}


@router.get("/firing-schedule")
async def get_firing_schedule(
    factory_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(OrderPosition).filter(
        OrderPosition.status.in_(SECTION_STATUSES["firing"])
    )
    query = apply_factory_filter(query, current_user, factory_id, OrderPosition)
    positions = _apply_schedule_order(query).all()
    return {"items": [_serialize_position_brief(p) for p in positions], "total": len(positions)}


@router.get("/sorting-schedule")
async def get_sorting_schedule(
    factory_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(OrderPosition).filter(
        OrderPosition.status.in_(SECTION_STATUSES["sorting"])
    )
    query = apply_factory_filter(query, current_user, factory_id, OrderPosition)
    positions = _apply_schedule_order(query).all()
    return {"items": [_serialize_position_brief(p) for p in positions], "total": len(positions)}


@router.get("/qc-schedule")
async def get_qc_schedule(
    factory_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Positions currently in QC pipeline."""
    query = db.query(OrderPosition).filter(
        OrderPosition.status.in_(SECTION_STATUSES["qc"])
    )
    query = apply_factory_filter(query, current_user, factory_id, OrderPosition)
    positions = _apply_schedule_order(query).all()
    return {"items": [_serialize_position_brief(p) for p in positions], "total": len(positions)}


@router.get("/kiln-schedule")
async def get_kiln_schedule(
    factory_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Batches grouped by kiln."""
    query = db.query(Resource).filter(
        Resource.resource_type == ResourceType.KILN,
        Resource.is_active == True,
    )
    query = apply_factory_filter(query, current_user, factory_id, Resource)
    kilns = query.order_by(Resource.name).all()

    result = []
    for kiln in kilns:
        batches = db.query(Batch).filter(
            Batch.resource_id == kiln.id,
            Batch.status.in_([BatchStatus.PLANNED, BatchStatus.IN_PROGRESS]),
        ).order_by(Batch.batch_date).all()

        result.append({
            "kiln": _serialize_resource(kiln),
            "batches": [_serialize_batch(b, db) for b in batches],
        })

    return {"items": result, "total": len(result)}


@router.patch("/positions/reorder")
async def reorder_positions(
    data: PositionReorderInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Bulk reorder positions — assigns sequential priority_order values.
    Also triggers reschedule for affected positions."""
    reordered = []
    for idx, pid in enumerate(data.position_ids):
        pos = db.query(OrderPosition).filter(OrderPosition.id == UUID(pid)).first()
        if pos:
            pos.priority_order = idx
            reordered.append(pos)
    db.commit()

    # Reschedule reordered positions (best-effort)
    try:
        from business.services.production_scheduler import reschedule_position
        for pos in reordered:
            reschedule_position(db, pos)
        db.commit()
    except Exception as e:
        logger.warning("Failed to reschedule reordered positions: %s", e)

    return {"ok": True, "count": len(data.position_ids)}


@router.post("/batches/{batch_id}/positions")
async def assign_batch_positions(
    batch_id: UUID,
    data: BatchAssignPositionsInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Assign positions to an existing batch."""
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(404, "Batch not found")
    count = 0
    for pid in data.position_ids:
        pos = db.query(OrderPosition).filter(OrderPosition.id == UUID(pid)).first()
        if pos:
            pos.batch_id = batch.id
            pos.resource_id = batch.resource_id
            count += 1
    db.commit()
    return _serialize_batch(batch, db)


# ── Schedule visibility endpoints (Sales + management) ───────────

@router.get("/orders/{order_id}/schedule")
async def get_order_schedule(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Full production schedule for an order — visible to Sales for
    real-time plan updates.

    Returns planned dates for every position (glazing, kiln, sorting,
    completion), kiln assignments, and on-track status.
    """
    order = db.query(ProductionOrder).filter(ProductionOrder.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")

    from business.services.production_scheduler import get_order_schedule_summary
    return get_order_schedule_summary(db, order)


@router.post("/orders/{order_id}/reschedule")
async def reschedule_order_endpoint(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """
    Manually trigger a full reschedule of all positions in an order.
    PM/Admin only.
    """
    order = db.query(ProductionOrder).filter(ProductionOrder.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")

    from business.services.production_scheduler import reschedule_order
    count = reschedule_order(db, order_id)
    db.commit()

    return {"ok": True, "positions_rescheduled": count, "order_id": str(order_id)}


@router.post("/factory/{factory_id}/reschedule")
async def reschedule_factory_endpoint(
    factory_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """
    Reschedule all active positions across all orders in a factory.
    PM/Admin only — use after major changes (new kiln, factory reset).
    """
    from api.models import Factory
    factory = db.query(Factory).filter(Factory.id == factory_id).first()
    if not factory:
        raise HTTPException(404, "Factory not found")

    from business.services.production_scheduler import reschedule_factory
    count = reschedule_factory(db, factory_id)

    return {
        "ok": True,
        "positions_rescheduled": count,
        "factory_id": str(factory_id),
        "factory_name": factory.name,
    }


@router.get("/positions/{position_id}/schedule")
async def get_position_schedule_endpoint(
    position_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Schedule details for a single position — planned dates, kiln
    assignment, on-track status.
    """
    position = db.query(OrderPosition).filter(OrderPosition.id == position_id).first()
    if not position:
        raise HTTPException(404, "Position not found")

    from business.services.production_scheduler import get_position_schedule
    sched = get_position_schedule(position)

    return {
        "position_id": str(position.id),
        "order_id": str(position.order_id),
        "status": _ev(position.status),
        **sched,
    }


# ────────────────────────────────────────────────────────────────
# Planning engine endpoints
# ────────────────────────────────────────────────────────────────

@router.post("/optimize-batch/{batch_id}")
async def optimize_batch_endpoint(
    batch_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """
    Find candidate positions to fill remaining capacity in a batch.
    Returns ranked suggestions without modifying any records.
    """
    from business.planning_engine.optimizer import optimize_batch_fill

    result = optimize_batch_fill(db, batch_id)
    if "error" in result:
        error = result["error"]
        if error == "batch_not_found":
            raise HTTPException(404, detail="Batch not found")
        if error == "kiln_not_found":
            raise HTTPException(404, detail="Kiln not found for this batch")
        if error == "invalid_status":
            raise HTTPException(
                400,
                detail=result.get("message", "Batch cannot be optimized in current status"),
            )
    return result


@router.get("/kiln-utilization")
async def kiln_utilization_endpoint(
    factory_id: UUID,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Kiln utilization metrics for a factory over the past N days.
    Per-kiln stats: firings, avg fill %, idle days, total area.
    """
    from api.models import Factory
    factory = db.query(Factory).filter(Factory.id == factory_id).first()
    if not factory:
        raise HTTPException(404, detail="Factory not found")

    from business.planning_engine.optimizer import calculate_kiln_utilization
    return calculate_kiln_utilization(db, factory_id, period_days=days)


@router.get("/production-schedule")
async def production_schedule_endpoint(
    factory_id: UUID,
    days: int = Query(14, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Forward-looking daily production schedule view for N days.
    Read-only aggregation: glazing, kiln loading, firing, cooling,
    sorting, QC sections per day.
    """
    from api.models import Factory
    factory = db.query(Factory).filter(Factory.id == factory_id).first()
    if not factory:
        raise HTTPException(404, detail="Factory not found")

    from business.planning_engine.scheduler import generate_production_schedule
    return generate_production_schedule(db, factory_id, horizon_days=days)


@router.post("/recalculate")
async def recalculate_schedule_endpoint(
    factory_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """
    Full factory schedule recalculation orchestrator.
    Runs: estimate recalc → backward scheduling → batch suggestion → utilization.
    PM/Admin only.
    """
    from api.models import Factory
    factory = db.query(Factory).filter(Factory.id == factory_id).first()
    if not factory:
        raise HTTPException(404, detail="Factory not found")

    from business.planning_engine.scheduler import recalculate_schedule
    return recalculate_schedule(db, factory_id)
