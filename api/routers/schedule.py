"""Schedule router — resources, batches, section schedules."""

import logging
from datetime import date
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
import sqlalchemy as sa
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
        PositionStatus.ENGOBE_CHECK, PositionStatus.SENT_TO_GLAZING,
    ],
    "firing": [
        PositionStatus.GLAZED, PositionStatus.PRE_KILN_CHECK,
        PositionStatus.LOADED_IN_KILN, PositionStatus.FIRED,
        PositionStatus.REFIRE, PositionStatus.AWAITING_REGLAZE,
    ],
    "sorting": [
        # Only actively-being-sorted positions. PACKED/READY_FOR_SHIPMENT
        # belong to Warehouse dashboard (finishedgoods) and Shipment flow.
        PositionStatus.TRANSFERRED_TO_SORTING,
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
        # Blocking tasks (stone procurement, recipe, etc.)
        "has_blocking_tasks": getattr(p, "_has_blocking_tasks", False),
    }


def _annotate_blocking_tasks(db: Session, positions: list) -> list:
    """Annotate positions with blocking task status (batch query)."""
    if not positions:
        return positions
    from api.models import Task
    from api.enums import TaskStatus
    pos_ids = [p.id for p in positions]
    blocked_pos_ids = set(
        row[0] for row in
        db.query(Task.related_position_id)
        .filter(
            Task.related_position_id.in_(pos_ids),
            Task.blocking.is_(True),
            Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS]),
        )
        .distinct()
        .all()
    )
    for p in positions:
        p._has_blocking_tasks = p.id in blocked_pos_ids
    return positions


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
    _annotate_blocking_tasks(db, positions)
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
    _annotate_blocking_tasks(db, positions)
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
    Triggers a factory-wide reschedule so new priorities actually move dates
    (per-position reschedule is not enough because each position recomputes
    from its own deadline and ignores sibling priorities)."""
    reordered: list[OrderPosition] = []
    factory_ids: set[UUID] = set()
    # Use low numeric values so these positions take precedence over
    # any FIFO-assigned priority_order (which starts at 0 but grows with
    # the number of existing positions in the factory).
    for idx, pid in enumerate(data.position_ids):
        pos = db.query(OrderPosition).filter(OrderPosition.id == UUID(pid)).first()
        if pos:
            pos.priority_order = idx
            reordered.append(pos)
            if pos.order and pos.order.factory_id:
                factory_ids.add(pos.order.factory_id)
    db.commit()

    # Reschedule each affected factory so the new priority_order actually
    # changes planned dates. reschedule_factory now preserves existing
    # priority_order values, so the manual order is respected.
    try:
        from business.services.production_scheduler import reschedule_factory
        for fid in factory_ids:
            reschedule_factory(db, fid)
        db.commit()
    except Exception as e:
        logger.warning("Failed to reschedule factory after reorder: %s", e)
        db.rollback()

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


@router.post("/orders/{order_id}/reschedule-debug")
async def reschedule_order_debug(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Debug: reschedule order and return errors."""
    import traceback
    from api.models import OrderPosition
    from api.enums import PositionStatus
    order = db.query(ProductionOrder).filter(ProductionOrder.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")

    deadline = order.final_deadline or order.desired_delivery_date
    if not deadline:
        from datetime import date, timedelta
        deadline = date.today() + timedelta(days=30)

    from business.services.production_scheduler import schedule_position

    positions = db.query(OrderPosition).filter(
        OrderPosition.order_id == order.id,
        OrderPosition.status != PositionStatus.CANCELLED.value,
    ).all()

    results = []
    for pos in positions:
        try:
            schedule_position(db, pos, deadline)
            db.flush()
            results.append({
                "position_id": str(pos.id),
                "position_number": pos.position_number,
                "status": pos.status,
                "ok": True,
                "planned_glazing_date": str(pos.planned_glazing_date),
            })
        except Exception as e:
            db.rollback()  # Prevent transaction poisoning for subsequent positions
            results.append({
                "position_id": str(pos.id),
                "position_number": pos.position_number,
                "status": pos.status,
                "ok": False,
                "error": str(e),
                "traceback": traceback.format_exc()[-500:],
            })

    return {"order": order.order_number, "positions": len(positions), "results": results}


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
    import traceback as _tb
    try:
        count = reschedule_factory(db, factory_id)
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Reschedule failed: {str(e)}\n{_tb.format_exc()[-1000:]}")

    return {
        "ok": True,
        "positions_rescheduled": count,
        "factory_id": str(factory_id),
        "factory_name": factory.name,
    }


@router.post("/factory/{factory_id}/reschedule-overdue")
async def reschedule_overdue_endpoint(
    factory_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Replan all overdue positions using the full scheduling engine.

    Each overdue position goes through reschedule_position() which does:
    - backward scheduling from order deadline (or smart fallback if deadline
      itself is in the past)
    - OVERDUE_SPREAD: when planned_glazing lands before today, find the
      earliest day with kiln capacity (typology-aware, zone-aware)
    - kiln assignment via find_best_kiln_and_date
    - blocking-task & material-wait constraints

    This replaces the old naive "shift dates by N days" logic which ignored
    capacity and left positions stacked on the same day.
    """
    import logging
    from datetime import date as _date
    from business.services.production_scheduler import reschedule_position

    logger = logging.getLogger("moonjar.schedule")
    today = _date.today()

    terminal = [
        PositionStatus.SHIPPED, PositionStatus.CANCELLED,
        PositionStatus.READY_FOR_SHIPMENT, PositionStatus.PACKED,
        PositionStatus.MERGED,
    ]

    try:
        overdue = db.query(OrderPosition).join(
            ProductionOrder, OrderPosition.order_id == ProductionOrder.id
        ).filter(
            ProductionOrder.factory_id == factory_id,
            ProductionOrder.status.in_(['new', 'in_production', 'partially_ready']),
            OrderPosition.status.notin_(terminal),
            sa.or_(
                OrderPosition.planned_glazing_date < today,
                OrderPosition.planned_kiln_date < today,
                OrderPosition.planned_sorting_date < today,
            ),
        ).order_by(
            # Replan in priority_order so manually-ordered positions get
            # the earliest available slots.
            OrderPosition.priority_order.asc().nullslast(),
            OrderPosition.position_number.asc(),
        ).all()
    except Exception as e:
        logger.error("RESCHEDULE_OVERDUE query failed: %s", e)
        raise HTTPException(500, f"Query failed: {e}")

    if not overdue:
        return {"ok": True, "positions_rescheduled": 0}

    rescheduled = 0
    failed = 0
    for pos in overdue:
        try:
            with db.begin_nested():
                reschedule_position(db, pos)
                db.flush()
            rescheduled += 1
        except Exception as e:
            failed += 1
            logger.warning(
                "RESCHEDULE_OVERDUE | failed pos=%s: %s", pos.id, e,
            )

    db.commit()
    logger.info(
        "RESCHEDULE_OVERDUE | factory=%s | replanned=%d failed=%d",
        factory_id, rescheduled, failed,
    )
    return {
        "ok": True,
        "positions_rescheduled": rescheduled,
        "failed": failed,
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


@router.post("/backfill-procurement-tasks")
async def backfill_procurement_tasks(
    factory_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Re-run material reservation for every active position at a factory.

    Purpose: sync `MATERIAL_ORDER` / `STONE_PROCUREMENT` blocking tasks
    with current stock state. Creates tasks for shortages that never had
    one, closes tasks for shortages that are now resolved, sets `due_at`
    from supplier lead times. Safe to run repeatedly — idempotent.

    Covers positions in any non-terminal status (not just `planned`),
    unlike `/orders/{id}/reschedule` which skips `insufficient_materials`.

    PM/Admin only.
    """
    from api.models import Factory, OrderPosition, Recipe
    from api.enums import PositionStatus
    from business.services.material_reservation import reserve_materials_for_position
    from business.services.stone_reservation import reserve_stone_for_position

    factory = db.query(Factory).filter(Factory.id == factory_id).first()
    if not factory:
        raise HTTPException(404, detail="Factory not found")

    terminal = {
        PositionStatus.SHIPPED.value,
        PositionStatus.CANCELLED.value,
        PositionStatus.MERGED.value,
        PositionStatus.PACKED.value,
        PositionStatus.READY_FOR_SHIPMENT.value,
    }

    positions = db.query(OrderPosition).filter(
        OrderPosition.factory_id == factory_id,
        ~OrderPosition.status.in_(list(terminal)),
    ).all()

    material_ran = 0
    stone_ran = 0
    errors: list[dict] = []

    for p in positions:
        # Run stone FIRST so STONE_PROCUREMENT auto-closes if stock is now
        # sufficient; material reservation below reads open-blocker state
        # to decide whether to flip position status back to PLANNED.
        try:
            reserve_stone_for_position(db, p)
            stone_ran += 1
        except Exception as e:
            errors.append({
                "position_id": str(p.id),
                "stage": "stone",
                "error": str(e)[:200],
            })

        # Re-run material reservation — sync_material_procurement_task runs
        # at the tail, keeping MATERIAL_ORDER task lifecycle in sync AND
        # restoring position.status to PLANNED when all blockers cleared.
        if p.recipe_id:
            try:
                recipe = db.query(Recipe).filter(Recipe.id == p.recipe_id).first()
                if recipe:
                    reserve_materials_for_position(db, p, recipe, factory_id)
                    material_ran += 1
            except Exception as e:
                errors.append({
                    "position_id": str(p.id),
                    "stage": "material",
                    "error": str(e)[:200],
                })

    # Housekeeping: close stale RECIPE_CONFIGURATION tasks.
    # They become stale when:
    #   (a) the task has no related_position_id (orphan catalog spam);
    #   (b) the linked position already has recipe_id set (phantom);
    #   (c) the linked position is in a post-kiln status where a recipe
    #       is no longer needed (transferred_to_sorting / qc / packed /
    #       shipped / cancelled — covered by `terminal` plus the kiln-
    #       exit ones).
    # We only touch type=recipe_configuration; other task types have
    # their own lifecycle and aren't cleaned up here.
    recipe_closed = _cleanup_stale_recipe_tasks(db, factory_id)

    # Same treatment for CONSUMPTION_MEASUREMENT: close duplicates, close
    # post-stage / phantom; set due_at = today + 7d on survivors so the
    # scheduler doesn't apply the 14-day fallback.
    consumption_closed = _cleanup_stale_consumption_tasks(db, factory_id)

    db.commit()

    return {
        "factory_id": str(factory_id),
        "positions_processed": len(positions),
        "material_reservation_runs": material_ran,
        "stone_reservation_runs": stone_ran,
        "recipe_tasks_auto_closed": recipe_closed,
        "consumption_tasks_auto_closed": consumption_closed,
        "errors": errors,
    }


def _cleanup_stale_recipe_tasks(db, factory_id: UUID) -> dict:
    """Close RECIPE_CONFIGURATION tasks that can no longer fire.

    Returns counts by category.
    """
    from api.models import Task, OrderPosition
    from api.enums import TaskType, TaskStatus, PositionStatus

    recipe_done_statuses = {
        PositionStatus.TRANSFERRED_TO_SORTING.value,
        PositionStatus.SENT_TO_QUALITY_CHECK.value,
        PositionStatus.QUALITY_CHECK_DONE.value,
        PositionStatus.PACKED.value,
        PositionStatus.SHIPPED.value,
        PositionStatus.CANCELLED.value,
        PositionStatus.MERGED.value,
        PositionStatus.READY_FOR_SHIPMENT.value,
        # Engobe stages imply a recipe has already been used (engobe
        # itself is rooted in the recipe), so a "configure recipe" task
        # is obsolete by the time the position reaches them.
        PositionStatus.ENGOBE_APPLIED.value,
        PositionStatus.ENGOBE_CHECK.value,
        PositionStatus.GLAZED.value,
        PositionStatus.PRE_KILN_CHECK.value,
        PositionStatus.LOADED_IN_KILN.value,
        PositionStatus.FIRED.value,
    }

    open_tasks = db.query(Task).filter(
        Task.factory_id == factory_id,
        Task.type == TaskType.RECIPE_CONFIGURATION.value,
        Task.status.in_(
            [TaskStatus.PENDING.value, TaskStatus.IN_PROGRESS.value]
        ),
    ).all()

    orphan_closed = 0
    phantom_closed = 0
    post_stage_closed = 0

    for t in open_tasks:
        pid = t.related_position_id
        reason = None
        if not pid:
            reason = "orphan"
        else:
            pos = db.query(OrderPosition).filter(
                OrderPosition.id == pid,
            ).first()
            if pos is None:
                reason = "orphan"  # dangling pointer — treat like orphan
            elif pos.recipe_id:
                reason = "phantom"
            else:
                cur = pos.status.value if hasattr(pos.status, "value") else pos.status
                if cur in recipe_done_statuses:
                    reason = "post_stage"
        if reason is None:
            continue
        t.status = TaskStatus.DONE.value
        if reason == "orphan":
            orphan_closed += 1
        elif reason == "phantom":
            phantom_closed += 1
        elif reason == "post_stage":
            post_stage_closed += 1

    return {
        "orphan": orphan_closed,
        "phantom_already_configured": phantom_closed,
        "post_stage_no_longer_needed": post_stage_closed,
        "total_closed": orphan_closed + phantom_closed + post_stage_closed,
    }


def _cleanup_stale_consumption_tasks(db, factory_id: UUID) -> dict:
    """Close duplicate/stale CONSUMPTION_MEASUREMENT tasks and set due_at
    on the survivors.

    Three categories closed:
      - duplicate: same (position, description) → keep newest, close rest
      - orphan:    no related_position_id or position doesn't exist
      - post_stage: linked position has already moved past engobe/glaze
                    (consumption was either measured implicitly or is
                    no longer relevant)

    Survivors without due_at get today + 7 days (default lead for a
    measurement — one week is enough for PM to schedule it). This
    replaces the scheduler's 14-day fallback.
    """
    from api.models import Task, OrderPosition
    from api.enums import TaskType, TaskStatus, PositionStatus
    from datetime import datetime, time, timezone, date, timedelta
    from collections import defaultdict

    done_statuses = {
        PositionStatus.TRANSFERRED_TO_SORTING.value,
        PositionStatus.SENT_TO_QUALITY_CHECK.value,
        PositionStatus.QUALITY_CHECK_DONE.value,
        PositionStatus.PACKED.value,
        PositionStatus.SHIPPED.value,
        PositionStatus.CANCELLED.value,
        PositionStatus.MERGED.value,
        PositionStatus.READY_FOR_SHIPMENT.value,
        PositionStatus.LOADED_IN_KILN.value,
        PositionStatus.FIRED.value,
        PositionStatus.GLAZED.value,
        PositionStatus.PRE_KILN_CHECK.value,
        PositionStatus.ENGOBE_APPLIED.value,
        PositionStatus.ENGOBE_CHECK.value,
    }

    open_tasks = db.query(Task).filter(
        Task.factory_id == factory_id,
        Task.type == TaskType.CONSUMPTION_MEASUREMENT.value,
        Task.status.in_(
            [TaskStatus.PENDING.value, TaskStatus.IN_PROGRESS.value]
        ),
    ).all()

    duplicate_closed = 0
    orphan_closed = 0
    post_stage_closed = 0
    due_at_seeded = 0

    # Group by (position, description) to detect duplicates.
    groups: dict[tuple, list] = defaultdict(list)
    for t in open_tasks:
        key = (t.related_position_id, t.description)
        groups[key].append(t)

    survivors: list = []
    for key, tasks in groups.items():
        if len(tasks) > 1:
            # Keep the newest, close the rest.
            tasks.sort(key=lambda x: x.created_at or datetime.min, reverse=True)
            survivor = tasks[0]
            for t in tasks[1:]:
                t.status = TaskStatus.DONE.value
                duplicate_closed += 1
            survivors.append(survivor)
        else:
            survivors.append(tasks[0])

    # Orphan / post_stage filter on survivors.
    final_survivors: list = []
    for t in survivors:
        pid = t.related_position_id
        if not pid:
            t.status = TaskStatus.DONE.value
            orphan_closed += 1
            continue
        pos = db.query(OrderPosition).filter(
            OrderPosition.id == pid,
        ).first()
        if pos is None:
            t.status = TaskStatus.DONE.value
            orphan_closed += 1
            continue
        cur = pos.status.value if hasattr(pos.status, "value") else pos.status
        if cur in done_statuses:
            t.status = TaskStatus.DONE.value
            post_stage_closed += 1
            continue
        final_survivors.append(t)

    # Seed due_at on final survivors without one.
    default_due = datetime.combine(
        date.today() + timedelta(days=7), time.min,
    ).replace(tzinfo=timezone.utc)
    for t in final_survivors:
        if t.due_at is None:
            t.due_at = default_due
            due_at_seeded += 1

    return {
        "duplicates_closed": duplicate_closed,
        "orphan": orphan_closed,
        "post_stage_no_longer_needed": post_stage_closed,
        "due_at_seeded_on_survivors": due_at_seeded,
        "total_closed": duplicate_closed + orphan_closed + post_stage_closed,
        "survivors_remaining": len(final_survivors),
    }


# ────────────────────────────────────────────────────────────────
# Scheduler Config — configurable buffer days per factory
# ────────────────────────────────────────────────────────────────

class SchedulerConfigResponse(BaseModel):
    factory_id: str
    pre_kiln_buffer_days: int
    post_kiln_buffer_days: int
    auto_buffer: bool
    auto_buffer_multiplier: float
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None


class SchedulerConfigUpdate(BaseModel):
    pre_kiln_buffer_days: Optional[int] = None
    post_kiln_buffer_days: Optional[int] = None
    auto_buffer: Optional[bool] = None
    auto_buffer_multiplier: Optional[float] = None


@router.get("/config/{factory_id}")
async def get_scheduler_config(
    factory_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Get scheduler configuration for a factory (buffer days, auto-buffer settings)."""
    from api.models import SchedulerConfig, Factory

    factory = db.query(Factory).filter(Factory.id == factory_id).first()
    if not factory:
        raise HTTPException(404, detail="Factory not found")

    config = db.query(SchedulerConfig).filter(
        SchedulerConfig.factory_id == factory_id
    ).first()

    if not config:
        # Return defaults
        return SchedulerConfigResponse(
            factory_id=str(factory_id),
            pre_kiln_buffer_days=1,
            post_kiln_buffer_days=1,
            auto_buffer=False,
            auto_buffer_multiplier=1.5,
        )

    return SchedulerConfigResponse(
        factory_id=str(config.factory_id),
        pre_kiln_buffer_days=config.pre_kiln_buffer_days,
        post_kiln_buffer_days=config.post_kiln_buffer_days,
        auto_buffer=config.auto_buffer,
        auto_buffer_multiplier=float(config.auto_buffer_multiplier),
        updated_at=config.updated_at.isoformat() if config.updated_at else None,
        updated_by=str(config.updated_by) if config.updated_by else None,
    )


@router.put("/config/{factory_id}")
async def update_scheduler_config(
    factory_id: UUID,
    body: SchedulerConfigUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Update scheduler configuration for a factory. PM/CEO only.

    Partial update — only provided fields are changed.
    Invalidates scheduler config cache after update.
    """
    from api.models import SchedulerConfig, Factory
    from datetime import datetime, timezone

    factory = db.query(Factory).filter(Factory.id == factory_id).first()
    if not factory:
        raise HTTPException(404, detail="Factory not found")

    # Validate ranges
    if body.pre_kiln_buffer_days is not None and body.pre_kiln_buffer_days < 0:
        raise HTTPException(422, detail="pre_kiln_buffer_days must be >= 0")
    if body.post_kiln_buffer_days is not None and body.post_kiln_buffer_days < 0:
        raise HTTPException(422, detail="post_kiln_buffer_days must be >= 0")
    if body.auto_buffer_multiplier is not None and body.auto_buffer_multiplier <= 0:
        raise HTTPException(422, detail="auto_buffer_multiplier must be > 0")

    config = db.query(SchedulerConfig).filter(
        SchedulerConfig.factory_id == factory_id
    ).first()

    if not config:
        config = SchedulerConfig(
            factory_id=factory_id,
            pre_kiln_buffer_days=body.pre_kiln_buffer_days if body.pre_kiln_buffer_days is not None else 1,
            post_kiln_buffer_days=body.post_kiln_buffer_days if body.post_kiln_buffer_days is not None else 1,
            auto_buffer=body.auto_buffer if body.auto_buffer is not None else False,
            auto_buffer_multiplier=body.auto_buffer_multiplier if body.auto_buffer_multiplier is not None else 1.5,
            updated_by=current_user.id,
        )
        db.add(config)
    else:
        if body.pre_kiln_buffer_days is not None:
            config.pre_kiln_buffer_days = body.pre_kiln_buffer_days
        if body.post_kiln_buffer_days is not None:
            config.post_kiln_buffer_days = body.post_kiln_buffer_days
        if body.auto_buffer is not None:
            config.auto_buffer = body.auto_buffer
        if body.auto_buffer_multiplier is not None:
            config.auto_buffer_multiplier = body.auto_buffer_multiplier
        config.updated_at = datetime.now(timezone.utc)
        config.updated_by = current_user.id

    db.commit()
    db.refresh(config)

    # Invalidate cache
    from business.services.production_scheduler import invalidate_scheduler_config_cache
    invalidate_scheduler_config_cache(factory_id)

    logger.info("Scheduler config updated for factory %s by user %s", factory_id, current_user.id)

    return SchedulerConfigResponse(
        factory_id=str(config.factory_id),
        pre_kiln_buffer_days=config.pre_kiln_buffer_days,
        post_kiln_buffer_days=config.post_kiln_buffer_days,
        auto_buffer=config.auto_buffer,
        auto_buffer_multiplier=float(config.auto_buffer_multiplier),
        updated_at=config.updated_at.isoformat() if config.updated_at else None,
        updated_by=str(config.updated_by) if config.updated_by else None,
    )


# ────────────────────────────────────────────────────────────────
# Batch readiness check — verify ALL materials, stone, recipes,
# consumption rules for ALL active positions in a factory.
# Creates blocking tasks for anything missing.
# ────────────────────────────────────────────────────────────────

@router.post("/factory/{factory_id}/check-readiness")
async def batch_check_readiness(
    factory_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Re-check readiness for ALL active positions: stone, materials,
    recipe, consumption rules. Creates blocking tasks for missing items."""
    from api.models import Task, Recipe, RecipeMaterial, MaterialStock, Material
    from api.enums import TaskType, TaskStatus, UserRole
    from business.services.stone_reservation import reserve_stone_for_position
    from business.services.order_intake import _check_stone_stock
    from sqlalchemy import func as sa_func

    terminal = [
        PositionStatus.SHIPPED, PositionStatus.CANCELLED,
        PositionStatus.READY_FOR_SHIPMENT, PositionStatus.PACKED,
        PositionStatus.MERGED,
    ]

    positions = (
        db.query(OrderPosition)
        .join(ProductionOrder, OrderPosition.order_id == ProductionOrder.id)
        .filter(
            ProductionOrder.factory_id == factory_id,
            ProductionOrder.status.in_(['new', 'in_production', 'partially_ready']),
            OrderPosition.status.notin_(terminal),
        )
        .all()
    )

    # Existing blocking tasks by (position_id, type) to avoid duplicates
    existing_tasks = set()
    for row in db.query(Task.related_position_id, Task.type).filter(
        Task.blocking.is_(True),
        Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS]),
    ).all():
        if row[0]:
            t_val = row[1].value if hasattr(row[1], 'value') else str(row[1])
            existing_tasks.add((row[0], t_val))

    results = {
        "positions_checked": 0,
        "stone_tasks_created": 0,
        "recipe_tasks_created": 0,
        "material_tasks_created": 0,
        "consumption_tasks_created": 0,
        "already_blocked": 0,
        "all_ok": 0,
    }

    for pos in positions:
        results["positions_checked"] += 1
        pos_ok = True

        # 1. Stone check
        if (pos.id, 'stone_procurement') not in existing_tasks:
            try:
                stone_result = reserve_stone_for_position(db, pos, auto_commit=False)
                if stone_result:
                    available = _check_stone_stock(db, pos, factory_id, stone_result)
                    if not available:
                        db.add(Task(
                            factory_id=factory_id,
                            type=TaskType.STONE_PROCUREMENT,
                            status=TaskStatus.PENDING,
                            assigned_role=UserRole.PURCHASER,
                            related_order_id=pos.order_id,
                            related_position_id=pos.id,
                            blocking=True,
                            description=f"Stone needed: {pos.color or ''} {pos.size or ''} — {stone_result['reserved_sqm']:.2f} m² ({stone_result['reserved_qty']} pcs)",
                        ))
                        results["stone_tasks_created"] += 1
                        pos_ok = False
            except Exception as e:
                logger.warning("READINESS stone check failed pos=%s: %s", pos.id, e)
        else:
            results["already_blocked"] += 1
            pos_ok = False

        # 2. Recipe check — does position have a recipe?
        if (pos.id, 'recipe_configuration') not in existing_tasks:
            if not pos.recipe_id:
                db.add(Task(
                    factory_id=factory_id,
                    type=TaskType.RECIPE_CONFIGURATION,
                    status=TaskStatus.PENDING,
                    assigned_role=UserRole.PRODUCTION_MANAGER,
                    related_order_id=pos.order_id,
                    related_position_id=pos.id,
                    blocking=True,
                    description=f"Configure recipe for: {pos.collection or ''} / {pos.color or ''} / {pos.size or ''}",
                ))
                results["recipe_tasks_created"] += 1
                pos_ok = False
            else:
                # 3. Material check — are recipe materials available?
                recipe_mats = db.query(RecipeMaterial).filter(
                    RecipeMaterial.recipe_id == pos.recipe_id
                ).all()

                if not recipe_mats:
                    # Recipe exists but has no materials defined
                    db.add(Task(
                        factory_id=factory_id,
                        type=TaskType.RECIPE_CONFIGURATION,
                        status=TaskStatus.PENDING,
                        assigned_role=UserRole.PRODUCTION_MANAGER,
                        related_order_id=pos.order_id,
                        related_position_id=pos.id,
                        blocking=True,
                        description=f"Recipe has no materials: {pos.color or ''} / {pos.size or ''}",
                    ))
                    results["recipe_tasks_created"] += 1
                    pos_ok = False

                for rm in recipe_mats:
                    # Check if material stock exists and has balance
                    stock = db.query(MaterialStock).filter(
                        MaterialStock.material_id == rm.material_id,
                        MaterialStock.factory_id == factory_id,
                    ).first()

                    required = float(rm.quantity_per_unit or 0) * float(pos.quantity or 1)
                    available = float(stock.balance) if stock else 0

                    if available < required and required > 0:
                        mat = db.query(Material).filter(Material.id == rm.material_id).first()
                        mat_name = mat.name if mat else str(rm.material_id)[:8]
                        # Check if material shortage task already exists
                        if (pos.id, 'stock_shortage') not in existing_tasks:
                            # Don't create blocking task for materials — position status
                            # should be set to insufficient_materials instead
                            if pos.status != PositionStatus.INSUFFICIENT_MATERIALS:
                                pos.status = PositionStatus.INSUFFICIENT_MATERIALS
                                results["material_tasks_created"] += 1
                                pos_ok = False

                # 4. Consumption rules check — for non-standard shapes
                shape_val = pos.shape.value if hasattr(pos.shape, 'value') else str(pos.shape) if pos.shape else 'rectangle'
                if shape_val not in ('rectangle', 'square') and (pos.id, 'consumption_measurement') not in existing_tasks:
                    # Non-standard shape — check if consumption rules exist
                    from api.models import ConsumptionRule
                    rule = db.query(ConsumptionRule).filter(
                        ConsumptionRule.is_active.is_(True),
                        ConsumptionRule.shape == shape_val,
                    ).first()
                    if not rule:
                        method = getattr(pos, 'application_method_code', 'SS') or 'SS'
                        db.add(Task(
                            factory_id=factory_id,
                            type=TaskType.CONSUMPTION_MEASUREMENT,
                            status=TaskStatus.PENDING,
                            assigned_role=UserRole.PRODUCTION_MANAGER,
                            related_order_id=pos.order_id,
                            related_position_id=pos.id,
                            blocking=True,
                            description=f"Measure consumption for {shape_val} shape: {pos.color or ''} {pos.size or ''} (method: {method})",
                        ))
                        results["consumption_tasks_created"] += 1
                        pos_ok = False

        if pos_ok:
            results["all_ok"] += 1

    db.commit()
    logger.info("BATCH_READINESS_CHECK | factory=%s | results=%s", factory_id, results)
    return {"ok": True, **results}


# ────────────────────────────────────────────────────────────────
# Plan vs Fact — daily production tracking
# ────────────────────────────────────────────────────────────────

# Stages we track in Plan vs Fact, in production order.
# Keys must match stage_plan keys from production_scheduler.py.
_PVF_STAGES = [
    ("unpacking_sorting",     "Unpacking"),
    ("engobe",                "Engobe"),
    ("drying_engobe",         "Drying (engobe)"),
    ("glazing",               "Glazing"),
    ("drying_glaze",          "Drying (glaze)"),
    ("edge_cleaning_loading", "Edge Cleaning"),
    ("kiln_loading",          "Kiln Loading"),
    ("sorting",               "Sorting"),
    ("packing",               "Packing"),
]

# Maps operation names (in `operations` table) to stage_plan keys.
# Operation names are freeform — this mapping covers common patterns.
_OP_NAME_TO_STAGE: dict[str, str] = {
    "unpacking":            "unpacking_sorting",
    "unpack":               "unpacking_sorting",
    "unpacking sorting":    "unpacking_sorting",
    "engobe":               "engobe",
    "engobe application":   "engobe",
    "apply engobe":         "engobe",
    "drying engobe":        "drying_engobe",
    "drying_engobe":        "drying_engobe",
    "glazing":              "glazing",
    "glaze":                "glazing",
    "glaze application":    "glazing",
    "drying glaze":         "drying_glaze",
    "drying_glaze":         "drying_glaze",
    "edge cleaning":        "edge_cleaning_loading",
    "edge_cleaning":        "edge_cleaning_loading",
    "edge clean":           "edge_cleaning_loading",
    "edge cleaning loading": "edge_cleaning_loading",
    "kiln loading":         "kiln_loading",
    "kiln_loading":         "kiln_loading",
    "loading":              "kiln_loading",
    "sorting":              "sorting",
    "sort":                 "sorting",
    "packing":              "packing",
    "pack":                 "packing",
}


@router.get("/daily-plan")
async def get_daily_plan(
    factory_id: UUID,
    target_date: date | None = Query(None, alias="date"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Plan vs Fact daily production view.

    For each tracked stage (engobe, glazing, edge_cleaning, kiln_loading):
    - PLAN: from schedule_metadata.stage_plan — how many pieces are planned
      for this position on this date (qty_per_day if date falls in [start, end]).
    - FACT: from operation_logs — sum of quantity_processed grouped by
      position + stage on the given shift_date.
    - CARRYOVER: plan - fact (clamped >= 0).

    Query params:
        factory_id  — required
        date        — defaults to today
    """
    from api.models import OperationLog, Operation

    target = target_date or date.today()

    # ── 1. Active positions in this factory ──────────────────────
    # Terminal statuses — these are done or cancelled, don't include in plan.
    # Same list as production-schedule endpoint for consistency.
    terminal = [
        PositionStatus.SHIPPED, PositionStatus.CANCELLED,
        PositionStatus.MERGED, PositionStatus.PACKED,
        PositionStatus.READY_FOR_SHIPMENT,
    ]
    positions = (
        db.query(OrderPosition)
        .join(ProductionOrder, OrderPosition.order_id == ProductionOrder.id)
        .filter(
            OrderPosition.factory_id == factory_id,
            ProductionOrder.status.in_(['new', 'in_production', 'partially_ready']),
            OrderPosition.status.notin_(terminal),
        )
        .all()
    )

    # Pre-load orders for display
    order_map: dict = {}
    if positions:
        order_ids = list({p.order_id for p in positions})
        for o in db.query(ProductionOrder).filter(ProductionOrder.id.in_(order_ids)).all():
            order_map[o.id] = o

    # ── 2. Build operation name → stage mapping for this factory ─
    # Fetch all operations for the factory so we can build the mapping.
    ops = db.query(Operation).filter(Operation.factory_id == factory_id).all()
    op_stage_map: dict[str, str] = {}  # operation_id (str) → stage key
    for op in ops:
        name_lower = (op.name or "").lower().strip()
        mapped = _OP_NAME_TO_STAGE.get(name_lower)
        if mapped:
            op_stage_map[str(op.id)] = mapped
        else:
            # Try fuzzy: if any key is a substring of the name
            for pattern, stage_key in _OP_NAME_TO_STAGE.items():
                if pattern in name_lower:
                    op_stage_map[str(op.id)] = stage_key
                    break

    # ── 3. Fetch actual data (operation_logs for target date) ────
    fact_logs = (
        db.query(OperationLog)
        .filter(
            OperationLog.factory_id == factory_id,
            OperationLog.shift_date == target,
        )
        .all()
    )

    # Index: (position_id_str, stage_key) → sum(quantity_processed)
    fact_by_pos_stage: dict[tuple[str, str], int] = {}
    for log in fact_logs:
        stage_key = op_stage_map.get(str(log.operation_id))
        if not stage_key:
            continue
        pos_id_str = str(log.position_id) if log.position_id else None
        if not pos_id_str:
            continue
        key = (pos_id_str, stage_key)
        fact_by_pos_stage[key] = fact_by_pos_stage.get(key, 0) + (log.quantity_processed or 0)

    # ── 4. Compute daily capacity per stage (from first position's typology)
    # This is approximate — capacity depends on typology of the position, but
    # for the overview we use the first available position to get a factory-wide cap.
    stage_capacities: dict[str, float] = {}
    if positions:
        from business.services.production_scheduler import _get_stage_daily_capacity
        sample_pos = positions[0]
        for stage_key, _label in _PVF_STAGES:
            cap, _unit, _fixed = _get_stage_daily_capacity(db, factory_id, stage_key, sample_pos)
            stage_capacities[stage_key] = cap

    # ── 5. Build cumulative done per position per stage ──────────
    # Query ALL operation_logs for each position up to target_date to get
    # cumulative quantities. To avoid N+1, do a bulk aggregation.
    pos_ids = [p.id for p in positions]
    cumulative_by_pos_stage: dict[tuple[str, str], int] = {}
    if pos_ids and op_stage_map:
        op_ids_by_stage: dict[str, list[str]] = {}
        for oid, sk in op_stage_map.items():
            op_ids_by_stage.setdefault(sk, []).append(oid)

        for sk, op_id_list in op_ids_by_stage.items():
            op_uuids = [UUID(x) for x in op_id_list]
            rows = (
                db.query(
                    OperationLog.position_id,
                    sa.func.sum(OperationLog.quantity_processed),
                )
                .filter(
                    OperationLog.factory_id == factory_id,
                    OperationLog.shift_date <= target,
                    OperationLog.operation_id.in_(op_uuids),
                    OperationLog.position_id.in_(pos_ids),
                )
                .group_by(OperationLog.position_id)
                .all()
            )
            for pid, total in rows:
                if pid:
                    cumulative_by_pos_stage[(str(pid), sk)] = int(total or 0)

    # ── 6. Assemble response per stage ───────────────────────────
    result_stages = []
    for stage_key, stage_label in _PVF_STAGES:
        stage_positions = []
        total_planned = 0
        total_actual = 0
        total_carryover = 0

        for pos in positions:
            meta = pos.schedule_metadata or {}
            stage_plan = meta.get("stage_plan", {}) if isinstance(meta, dict) else {}
            sinfo = stage_plan.get(stage_key, {}) if isinstance(stage_plan, dict) else {}

            # Check if this date falls within this stage's planned range
            planned_today = 0
            if sinfo:
                try:
                    s_start = date.fromisoformat(sinfo["start"])
                    s_end = date.fromisoformat(sinfo["end"])
                    if s_start <= target <= s_end:
                        planned_today = int(round(float(sinfo.get("qty_per_day") or 0)))
                except (KeyError, ValueError, TypeError):
                    pass

            if planned_today == 0:
                # Also check: if stage_key is "kiln_loading" and target == planned_kiln_date
                if stage_key == "kiln_loading" and pos.planned_kiln_date == target:
                    planned_today = pos.quantity or 0

            # Skip positions with no planned work today and no actual work today
            pid_str = str(pos.id)
            actual_today = fact_by_pos_stage.get((pid_str, stage_key), 0)

            if planned_today == 0 and actual_today == 0:
                continue

            cumulative_done = cumulative_by_pos_stage.get((pid_str, stage_key), 0)
            remaining = max(0, (pos.quantity or 0) - cumulative_done)
            carryover = max(0, planned_today - actual_today)

            order = order_map.get(pos.order_id)
            pos_num = getattr(pos, "position_number", None)
            split_idx = getattr(pos, "split_index", None)
            label = f"#{pos_num}.{split_idx}" if pos_num is not None and split_idx is not None else (f"#{pos_num}" if pos_num is not None else "?")

            stage_positions.append({
                "position_id": pid_str,
                "position_label": label,
                "order_number": order.order_number if order else "",
                "client": order.client if order else None,
                "color": pos.color,
                "size": pos.size,
                "collection": pos.collection,
                "total_qty": pos.quantity or 0,
                "planned_today": planned_today,
                "actual_today": actual_today,
                "carryover": carryover,
                "cumulative_done": cumulative_done,
                "remaining": remaining,
                "status": pos.status.value if hasattr(pos.status, "value") else str(pos.status),
            })

            total_planned += planned_today
            total_actual += actual_today
            total_carryover += carryover

        result_stages.append({
            "stage": stage_key,
            "stage_label": stage_label,
            "daily_capacity": stage_capacities.get(stage_key, 0),
            "positions": stage_positions,
            "totals": {
                "planned": total_planned,
                "actual": total_actual,
                "carryover": total_carryover,
            },
        })

    return {
        "date": target.isoformat(),
        "factory_id": str(factory_id),
        "stages": result_stages,
    }
