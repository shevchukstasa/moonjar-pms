"""Positions router — list, status transitions, sorting split, filtering by section,
   blocking summary, material reservations, PM force-unblock."""

import uuid as uuid_mod
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from api.database import get_db
from api.auth import get_current_user, apply_factory_filter
from api.roles import require_management, require_sorting
from api.models import (
    OrderPosition, ProductionOrder, ProductionOrderItem, DefectRecord,
    GrindingStock, RepairQueue, FinishedGoodsStock, Task,
    MaterialTransaction, MaterialStock, RecipeMaterial, Material, Recipe,
)
from api.enums import (
    PositionStatus, OrderStatus, SplitCategory, DefectStage, DefectOutcome,
    GrindingStatus, RepairStatus, TaskType, TaskStatus, UserRole,
    TransactionType, is_stock_collection,
)

# Import handle_surplus lazily to avoid circular imports
def _handle_surplus(db, position, surplus_qty):
    from business.services.sorting_split import handle_surplus
    handle_surplus(db, position, surplus_qty)

router = APIRouter()


def _ev(val):
    return val.value if hasattr(val, "value") else str(val) if val else None


def _next_position_number(db: Session, order_id) -> int:
    """Return the next sequential position_number for a root position in this order."""
    from sqlalchemy import func
    result = db.query(func.max(OrderPosition.position_number)).filter(
        OrderPosition.order_id == order_id,
        OrderPosition.parent_position_id.is_(None),
    ).scalar()
    return (result or 0) + 1


def _next_split_index(db: Session, parent_position_id) -> int:
    """Return the next sequential split_index for a sub-position under this parent."""
    from sqlalchemy import func
    result = db.query(func.max(OrderPosition.split_index)).filter(
        OrderPosition.parent_position_id == parent_position_id,
    ).scalar()
    return (result or 0) + 1


def position_label(p) -> str:
    """Human-readable label: '#3' for root, '#3.1' for split sub-position."""
    num = getattr(p, 'position_number', None)
    idx = getattr(p, 'split_index', None)
    if num is None:
        return '—'
    if idx is not None:
        return f'#{num}.{idx}'
    return f'#{num}'


def _recalculate_order_status(db: Session, order_id) -> tuple:
    """Recalculate order status based on main position statuses (excluding sub-positions).

    Returns (old_status, new_status, order) or (None, None, None) if no change.
    """
    order = db.query(ProductionOrder).filter(ProductionOrder.id == order_id).first()
    if not order or order.status_override:
        return None, None, None  # Don't override manual status

    positions = db.query(OrderPosition).filter(
        OrderPosition.order_id == order_id,
        OrderPosition.split_category.is_(None),  # main positions only
    ).all()

    if not positions:
        return None, None, None

    statuses = {_ev(p.status) for p in positions}

    if all(s == 'cancelled' for s in statuses):
        new_status = OrderStatus.CANCELLED
    elif all(s == 'shipped' for s in statuses):
        new_status = OrderStatus.SHIPPED
    elif all(s in ('ready_for_shipment', 'shipped') for s in statuses):
        new_status = OrderStatus.READY_FOR_SHIPMENT
    elif any(s in ('ready_for_shipment', 'shipped', 'packed', 'quality_check_done') for s in statuses):
        new_status = OrderStatus.PARTIALLY_READY
    elif all(s == 'planned' for s in statuses):
        new_status = OrderStatus.NEW
    else:
        new_status = OrderStatus.IN_PRODUCTION

    old_status = order.status
    if old_status != new_status:
        order.status = new_status
        order.updated_at = datetime.now(timezone.utc)
        return old_status, new_status, order

    return None, None, None


async def _notify_sales_order_event(order, event_type: str, extra: dict | None = None):
    """Send order status event to Sales app with retry."""
    if not order.external_id:
        return
    from business.services.webhook_sender import send_webhook
    payload = {
        "event": event_type,
        "external_id": order.external_id,
        "order_number": order.order_number,
        "status": _ev(order.status),
        "shipped_at": order.shipped_at.isoformat() if order.shipped_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
    }
    if extra:
        payload.update(extra)
    await send_webhook(payload, event_type=event_type, external_id=order.external_id)


# Blocking statuses that PM can force-unblock
BLOCKING_STATUSES = {
    PositionStatus.INSUFFICIENT_MATERIALS,
    PositionStatus.AWAITING_RECIPE,
    PositionStatus.AWAITING_STENCIL_SILKSCREEN,
    PositionStatus.AWAITING_COLOR_MATCHING,
    PositionStatus.AWAITING_SIZE_CONFIRMATION,
    PositionStatus.BLOCKED_BY_QM,
}

# Section → status mapping
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
        PositionStatus.SENT_TO_QUALITY_CHECK, PositionStatus.QUALITY_CHECK_DONE,
        PositionStatus.READY_FOR_SHIPMENT, PositionStatus.BLOCKED_BY_QM,
    ],
}


def _serialize_position(p) -> dict:
    return {
        "id": str(p.id),
        "order_id": str(p.order_id),
        "order_item_id": str(p.order_item_id),
        "parent_position_id": str(p.parent_position_id) if p.parent_position_id else None,
        "position_number": p.position_number,
        "split_index": p.split_index,
        "position_label": position_label(p),
        "factory_id": str(p.factory_id),
        "status": _ev(p.status),
        "batch_id": str(p.batch_id) if p.batch_id else None,
        "resource_id": str(p.resource_id) if p.resource_id else None,
        "placement_position": p.placement_position,
        "placement_level": p.placement_level,
        "delay_hours": float(p.delay_hours) if p.delay_hours else 0,
        "quantity": p.quantity,
        "quantity_with_defect_margin": p.quantity_with_defect_margin,
        "color": p.color,
        "size": p.size,
        "application": p.application,
        "finishing": p.finishing,
        "collection": p.collection,
        "application_type": p.application_type,
        "place_of_application": p.place_of_application,
        "product_type": _ev(p.product_type),
        "shape": _ev(p.shape),
        "shape_dimensions": p.shape_dimensions if getattr(p, 'shape_dimensions', None) else None,
        "thickness_mm": float(p.thickness_mm) if p.thickness_mm else 11.0,
        "recipe_id": str(p.recipe_id) if p.recipe_id else None,
        "mandatory_qc": p.mandatory_qc,
        "split_category": _ev(p.split_category),
        "is_merged": p.is_merged,
        "priority_order": p.priority_order,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        # Application method system
        "application_method_code": getattr(p, 'application_method_code', None),
        "application_collection_code": getattr(p, 'application_collection_code', None),
        # Production data
        "glazeable_sqm": float(p.glazeable_sqm) if getattr(p, 'glazeable_sqm', None) else None,
        "size_id": str(p.size_id) if getattr(p, 'size_id', None) else None,
        "recipe_name": p.recipe.name if getattr(p, 'recipe', None) and p.recipe else None,
        # Schedule
        "planned_glazing_date": p.planned_glazing_date.isoformat() if getattr(p, 'planned_glazing_date', None) else None,
        "planned_kiln_date": p.planned_kiln_date.isoformat() if getattr(p, 'planned_kiln_date', None) else None,
        "planned_sorting_date": p.planned_sorting_date.isoformat() if getattr(p, 'planned_sorting_date', None) else None,
        # Include order_number via relationship
        "order_number": p.order.order_number if p.order else "",
    }


class StatusChangeInput(BaseModel):
    status: str
    notes: Optional[str] = None


@router.get("")
async def list_positions(
    page: int = Query(1, ge=1),
    per_page: int = Query(100, ge=1, le=500),
    factory_id: UUID | None = None,
    order_id: UUID | None = None,
    status: str | None = None,
    section: str | None = None,
    batch_id: UUID | None = None,
    split_category: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(OrderPosition)
    query = apply_factory_filter(query, current_user, factory_id, OrderPosition)

    if order_id:
        query = query.filter(OrderPosition.order_id == order_id)
    if batch_id:
        query = query.filter(OrderPosition.batch_id == batch_id)
    if split_category:
        query = query.filter(OrderPosition.split_category == split_category)

    # Filter by section (group of statuses)
    if section and section in SECTION_STATUSES:
        query = query.filter(OrderPosition.status.in_(SECTION_STATUSES[section]))
    elif status:
        # Comma-separated statuses
        statuses = [s.strip() for s in status.split(",")]
        query = query.filter(OrderPosition.status.in_(statuses))

    if search:
        query = query.join(ProductionOrder, OrderPosition.order_id == ProductionOrder.id).filter(
            or_(
                ProductionOrder.order_number.ilike(f"%{search}%"),
                OrderPosition.color.ilike(f"%{search}%"),
            )
        )

    total = query.count()
    positions = query.order_by(
        OrderPosition.priority_order, OrderPosition.created_at
    ).offset((page - 1) * per_page).limit(per_page).all()

    return {
        "items": [_serialize_position(p) for p in positions],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# ================================================================
# Blocking Summary — MUST be defined before /{position_id} routes
# ================================================================

@router.get("/blocking-summary")
async def get_blocking_summary(
    factory_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return a summary of all blocked positions with related tasks and shortages.

    Used by the PM dashboard Blocking tab to show all positions needing attention.
    """
    query = db.query(OrderPosition).filter(
        OrderPosition.status.in_(list(BLOCKING_STATUSES)),
    )
    query = apply_factory_filter(query, current_user, factory_id, OrderPosition)

    blocked_positions = query.order_by(OrderPosition.created_at).all()

    # Count by type
    by_type = {}
    for status in BLOCKING_STATUSES:
        key = _ev(status)
        by_type[key] = sum(1 for p in blocked_positions if _ev(p.status) == key)

    positions_data = []
    for p in blocked_positions:
        order = p.order

        # Related blocking tasks
        related_tasks = (
            db.query(Task)
            .filter(
                Task.related_position_id == p.id,
                Task.blocking.is_(True),
                Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS]),
            )
            .all()
        )
        tasks_data = [
            {
                "task_id": str(t.id),
                "type": _ev(t.type),
                "status": _ev(t.status),
                "description": t.description,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                **({"metadata": t.metadata_json} if t.metadata_json else {}),
            }
            for t in related_tasks
        ]

        # Material shortages (for insufficient_materials positions)
        material_shortages = []
        if _ev(p.status) == "insufficient_materials" and p.recipe_id:
            recipe = db.query(Recipe).filter(Recipe.id == p.recipe_id).first()
            if recipe:
                rms = db.query(RecipeMaterial).filter(RecipeMaterial.recipe_id == recipe.id).all()
                for rm in rms:
                    mat = db.query(Material).get(rm.material_id)
                    if not mat:
                        continue
                    # Quick effective available calculation
                    stk = (
                        db.query(MaterialStock)
                        .filter(
                            MaterialStock.material_id == rm.material_id,
                            MaterialStock.factory_id == p.factory_id,
                        )
                        .first()
                    )
                    bal = Decimal(str(stk.balance)) if stk else Decimal("0")
                    t_res = Decimal(str(
                        db.query(func.coalesce(func.sum(MaterialTransaction.quantity), 0))
                        .filter(
                            MaterialTransaction.material_id == rm.material_id,
                            MaterialTransaction.factory_id == p.factory_id,
                            MaterialTransaction.type == TransactionType.RESERVE,
                        ).scalar()
                    ))
                    t_unres = Decimal(str(
                        db.query(func.coalesce(func.sum(MaterialTransaction.quantity), 0))
                        .filter(
                            MaterialTransaction.material_id == rm.material_id,
                            MaterialTransaction.factory_id == p.factory_id,
                            MaterialTransaction.type == TransactionType.UNRESERVE,
                        ).scalar()
                    ))
                    eff = bal - (t_res - t_unres)
                    if rm.unit == "per_sqm" and p.quantity_sqm:
                        req = Decimal(str(rm.quantity_per_unit)) * Decimal(str(p.quantity_sqm))
                    else:
                        req = Decimal(str(rm.quantity_per_unit)) * Decimal(str(p.quantity))
                    deficit = max(Decimal("0"), req - max(eff, Decimal("0")))
                    if deficit > 0:
                        material_shortages.append({
                            "name": mat.name,
                            "deficit": float(deficit),
                            "required": float(req),
                            "available": float(eff),
                        })

        positions_data.append({
            "id": str(p.id),
            "order_number": order.order_number if order else "",
            "position_label": position_label(p),
            "color": p.color,
            "size": p.size,
            "collection": p.collection,
            "quantity": p.quantity,
            "status": _ev(p.status),
            "blocking_reason": _ev(p.status),
            "blocking_since": p.created_at.isoformat() if p.created_at else None,
            "related_tasks": tasks_data,
            "material_shortages": material_shortages,
            "recipe_id": str(p.recipe_id) if p.recipe_id else None,
            "factory_id": str(p.factory_id),
        })

    return {
        "total_blocked": len(blocked_positions),
        "by_type": by_type,
        "positions": positions_data,
    }


# ================================================================

@router.get("/{position_id}")
async def get_position(
    position_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    p = db.query(OrderPosition).filter(OrderPosition.id == position_id).first()
    if not p:
        raise HTTPException(404, "Position not found")

    result = _serialize_position(p)

    # Include sub-positions
    children = db.query(OrderPosition).filter(
        OrderPosition.parent_position_id == position_id
    ).all()
    result["sub_positions"] = [_serialize_position(c) for c in children]

    return result


@router.patch("/{position_id}")
async def update_position(
    position_id: UUID,
    data: dict,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    p = db.query(OrderPosition).filter(OrderPosition.id == position_id).first()
    if not p:
        raise HTTPException(404, "Position not found")

    allowed = {"batch_id", "resource_id", "placement_position", "placement_level",
               "delay_hours", "priority_order", "recipe_id", "mandatory_qc",
               "application_method_code", "application_collection_code",
               "glazeable_sqm", "thickness_mm", "shape", "shape_dimensions",
               "product_type", "quantity_with_defect_margin", "place_of_application"}
    for k, v in data.items():
        if k in allowed:
            setattr(p, k, v)

    # Recalculate glazeable_sqm if shape or shape_dimensions changed
    if "shape" in data or "shape_dimensions" in data:
        from business.services.surface_area import calculate_glazeable_sqm_for_position
        _glazeable = calculate_glazeable_sqm_for_position(db, p)
        if _glazeable is not None:
            p.glazeable_sqm = _glazeable

    p.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(p)
    return _serialize_position(p)


@router.get("/{position_id}/allowed-transitions")
async def get_allowed_transitions(
    position_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return list of allowed next statuses for a position."""
    from business.services.status_machine import get_allowed_transitions as _get_allowed

    p = db.query(OrderPosition).filter(OrderPosition.id == position_id).first()
    if not p:
        raise HTTPException(404, "Position not found")

    current = _ev(p.status)
    return {"current_status": current, "allowed": _get_allowed(current)}


@router.post("/{position_id}/status")
async def change_position_status(
    position_id: UUID,
    data: StatusChangeInput,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from business.services.status_machine import validate_status_transition

    p = db.query(OrderPosition).filter(OrderPosition.id == position_id).first()
    if not p:
        raise HTTPException(404, "Position not found")

    # Validate status exists
    try:
        new_status = PositionStatus(data.status)
    except ValueError:
        raise HTTPException(400, f"Invalid status: {data.status}")

    # Validate transition
    current = _ev(p.status)
    is_management = hasattr(current_user, 'role') and _ev(current_user.role) in (
        'production_manager', 'administrator', 'owner'
    )
    if not is_management and not validate_status_transition(current, data.status):
        from business.services.status_machine import get_allowed_transitions as _get_allowed
        allowed = _get_allowed(current)
        raise HTTPException(
            400,
            f"Invalid transition: {current} → {data.status}. Allowed: {allowed}",
        )

    old_status = current
    p.status = new_status
    p.updated_at = datetime.now(timezone.utc)

    # Special routing: FIRED → multi-firing check
    if new_status == PositionStatus.FIRED:
        from business.services.status_machine import route_after_firing
        route_after_firing(db, p)

    # ── Material consumption on glazing start ─────────────────────
    # When position transitions to ENGOBE_APPLIED or GLAZED (first time),
    # consume BOM materials and release reservations.
    if new_status in (PositionStatus.ENGOBE_APPLIED, PositionStatus.GLAZED):
        if not p.materials_written_off_at:
            try:
                from business.services.material_consumption import on_glazing_start
                on_glazing_start(db, p.id)
            except Exception as _mc_err:
                import logging
                logging.getLogger("moonjar.positions").warning(
                    "Failed to consume materials for position %s on glazing start: %s",
                    position_id, _mc_err,
                )
        elif (p.firing_round or 1) > 1:
            # Refire/reglaze cycle — consume only surface materials
            try:
                from business.services.material_consumption import consume_refire_materials
                consume_refire_materials(db, p.id)
            except Exception as _mc_err:
                import logging
                logging.getLogger("moonjar.positions").warning(
                    "Failed to consume refire materials for position %s: %s",
                    position_id, _mc_err,
                )

    # Unreserve materials when position is cancelled
    if new_status == PositionStatus.CANCELLED:
        try:
            from business.services.material_reservation import unreserve_materials_for_position
            unreserve_materials_for_position(db, p.id)
        except Exception as _e:
            import logging
            logging.getLogger("moonjar.positions").warning(
                "Failed to unreserve materials for position %s: %s", position_id, _e
            )

    # Auto-recalculate parent order status
    old_order_status, new_order_status, order = _recalculate_order_status(db, p.order_id)

    db.commit()
    db.refresh(p)

    # Send order_ready webhook to Sales when all positions become ready_for_shipment
    if (
        new_order_status == OrderStatus.READY_FOR_SHIPMENT
        and order
        and order.external_id
    ):
        # Count total positions for the enriched payload
        total_pos = db.query(OrderPosition).filter(
            OrderPosition.order_id == order.id,
            OrderPosition.split_category.is_(None),
        ).count()
        await _notify_sales_order_event(order, "order_ready", extra={
            "client": order.client,
            "positions_total": total_pos,
            "factory_name": order.factory.name if order.factory else None,
        })

    # Send intermediate status callback to Sales (stub-aware)
    try:
        _order = order or db.query(ProductionOrder).filter(ProductionOrder.id == p.order_id).first()
        if _order and _order.external_id and old_status != _ev(p.status):
            from api.routers.integration import notify_sales_status_change_stub
            await notify_sales_status_change_stub(_order, p, old_status, _ev(p.status))
    except Exception:
        pass  # Best-effort

    return _serialize_position(p)


# ---------- Sorting Split ----------

class SortingSplitRequest(BaseModel):
    good_quantity: int
    refire_quantity: int = 0          # Already glazed, bubbles/underfired → back to kiln (REFIRE status)
    repair_quantity: int = 0          # Needs re-glazing first → SENT_TO_GLAZING
    color_mismatch_quantity: int = 0  # Wrong color → re-starts from PLANNED
    grinding_quantity: int = 0
    write_off_quantity: int = 0
    notes: Optional[str] = None


@router.post("/{position_id}/split")
async def split_position(
    position_id: UUID,
    data: SortingSplitRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_sorting),
):
    """Sort a fired position: split into good/refire/repair/color_mismatch/grinding/write-off."""

    p = db.query(OrderPosition).filter(OrderPosition.id == position_id).first()
    if not p:
        raise HTTPException(404, "Position not found")

    if _ev(p.status) != "transferred_to_sorting":
        raise HTTPException(400, f"Position status must be 'transferred_to_sorting', got '{_ev(p.status)}'")

    total = (
        data.good_quantity + data.refire_quantity + data.repair_quantity
        + data.color_mismatch_quantity + data.grinding_quantity + data.write_off_quantity
    )
    if total != p.quantity:
        raise HTTPException(
            400,
            f"Total ({total}) must equal position quantity ({p.quantity})",
        )

    now = datetime.now(timezone.utc)
    sub_positions = []
    grinding_record = None
    defect_record = None

    # Split-index counter: sub-positions share parent's position_number,
    # and get sequential split_index values (1, 2, 3, …).
    _base_si = _next_split_index(db, p.id) - 1  # will be incremented before each use

    def _si():
        nonlocal _base_si
        _base_si += 1
        return _base_si

    # 1. Update parent — good quantity, mark as packed
    p.quantity = data.good_quantity
    p.status = PositionStatus.PACKED
    p.updated_at = now

    # Consume packaging materials (boxes + spacers)
    try:
        from business.services.packaging_consumption import consume_packaging
        if p.factory_id:
            consume_packaging(db, p.id, p.factory_id, user_id=current_user.id)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(
            "Failed to consume packaging for position %s: %s", p.id, e
        )

    # 2. Refire sub-position — tile is already glazed, just needs another firing pass
    if data.refire_quantity > 0:
        refire_pos = OrderPosition(
            id=uuid_mod.uuid4(),
            order_id=p.order_id,
            order_item_id=p.order_item_id,
            parent_position_id=p.id,
            factory_id=p.factory_id,
            status=PositionStatus.REFIRE,
            quantity=data.refire_quantity,
            color=p.color,
            size=p.size,
            application=p.application,
            finishing=p.finishing,
            collection=p.collection,
            application_type=p.application_type,
            place_of_application=p.place_of_application,
            product_type=p.product_type,
            shape=p.shape,
            thickness_mm=p.thickness_mm,
            recipe_id=p.recipe_id,
            mandatory_qc=p.mandatory_qc,
            split_category=SplitCategory.REFIRE,
            priority_order=p.priority_order,
            position_number=p.position_number,
            split_index=_si(),
            created_at=now,
            updated_at=now,
        )
        db.add(refire_pos)
        sub_positions.append(refire_pos)

    # 4. Repair sub-position — needs re-glazing before re-firing
    if data.repair_quantity > 0:
        repair_pos = OrderPosition(
            id=uuid_mod.uuid4(),
            order_id=p.order_id,
            order_item_id=p.order_item_id,
            parent_position_id=p.id,
            factory_id=p.factory_id,
            status=PositionStatus.SENT_TO_GLAZING,
            quantity=data.repair_quantity,
            color=p.color,
            size=p.size,
            application=p.application,
            finishing=p.finishing,
            collection=p.collection,
            application_type=p.application_type,
            place_of_application=p.place_of_application,
            product_type=p.product_type,
            shape=p.shape,
            thickness_mm=p.thickness_mm,
            recipe_id=p.recipe_id,
            mandatory_qc=p.mandatory_qc,
            split_category=SplitCategory.REPAIR,
            priority_order=p.priority_order,
            position_number=p.position_number,
            split_index=_si(),
            created_at=now,
            updated_at=now,
        )
        db.add(repair_pos)
        sub_positions.append(repair_pos)

        # Repair queue entry for SLA tracking
        rq = RepairQueue(
            id=uuid_mod.uuid4(),
            factory_id=p.factory_id,
            color=p.color,
            size=p.size,
            quantity=data.repair_quantity,
            defect_type="sorting_repair",
            source_order_id=p.order_id,
            source_position_id=p.id,
            status=RepairStatus.IN_REPAIR,
            created_at=now,
            updated_at=now,
        )
        db.add(rq)

    # 5. Color mismatch sub-position
    if data.color_mismatch_quantity > 0:
        cm_pos = OrderPosition(
            id=uuid_mod.uuid4(),
            order_id=p.order_id,
            order_item_id=p.order_item_id,
            parent_position_id=p.id,
            factory_id=p.factory_id,
            status=PositionStatus.PLANNED,
            quantity=data.color_mismatch_quantity,
            color=p.color,
            size=p.size,
            application=p.application,
            finishing=p.finishing,
            collection=p.collection,
            application_type=p.application_type,
            place_of_application=p.place_of_application,
            product_type=p.product_type,
            shape=p.shape,
            thickness_mm=p.thickness_mm,
            recipe_id=p.recipe_id,
            mandatory_qc=p.mandatory_qc,
            split_category=SplitCategory.COLOR_MISMATCH,
            priority_order=p.priority_order,
            position_number=p.position_number,
            split_index=_si(),
            created_at=now,
            updated_at=now,
        )
        db.add(cm_pos)
        sub_positions.append(cm_pos)

    # 6. Grinding stock
    if data.grinding_quantity > 0:
        gs = GrindingStock(
            id=uuid_mod.uuid4(),
            factory_id=p.factory_id,
            color=p.color,
            size=p.size,
            quantity=data.grinding_quantity,
            source_order_id=p.order_id,
            source_position_id=p.id,
            status=GrindingStatus.IN_STOCK,
            created_at=now,
            updated_at=now,
        )
        db.add(gs)
        grinding_record = {
            "id": str(gs.id),
            "color": gs.color,
            "size": gs.size,
            "quantity": gs.quantity,
        }

    # 7. Write-off defect record
    if data.write_off_quantity > 0:
        dr = DefectRecord(
            id=uuid_mod.uuid4(),
            factory_id=p.factory_id,
            stage=DefectStage.SORTING,
            position_id=p.id,
            defect_type="sorting_write_off",
            quantity=data.write_off_quantity,
            outcome=DefectOutcome.WRITE_OFF,
            reported_by=current_user.id,
            reported_via="dashboard",
            notes=data.notes,
            created_at=now,
        )
        db.add(dr)
        defect_record = {
            "id": str(dr.id),
            "quantity": dr.quantity,
            "outcome": "write_off",
        }

    db.commit()
    db.refresh(p)
    for sp in sub_positions:
        db.refresh(sp)

    # --- Stock fulfillment check (only for stock positions) ---
    stock_fulfillment = None
    if is_stock_collection(p.collection):
        stock_fulfillment = _check_stock_fulfillment(db, p, data.good_quantity)

    # --- Surplus handling for regular (non-stock) orders ---
    surplus_handled = None
    if not is_stock_collection(p.collection):
        surplus = _calculate_surplus(db, p, data.good_quantity)
        if surplus > 0:
            try:
                _handle_surplus(db, p, surplus)
                db.commit()
                surplus_handled = surplus
            except Exception as surplus_err:
                # Surplus handling is non-critical — log but don't fail the split
                import logging
                logging.getLogger(__name__).warning(f"Surplus handling failed: {surplus_err}")

    return {
        "parent_position": _serialize_position(p),
        "sub_positions": [_serialize_position(sp) for sp in sub_positions],
        "grinding_record": grinding_record,
        "defect_record": defect_record,
        "reconciliation": {
            "input_total": total,
            "good": data.good_quantity,
            "refire": data.refire_quantity,
            "repair": data.repair_quantity,
            "color_mismatch": data.color_mismatch_quantity,
            "grinding": data.grinding_quantity,
            "write_off": data.write_off_quantity,
        },
        "stock_fulfillment": stock_fulfillment,
        "surplus_handled": surplus_handled,
    }


# ---------- Surplus Calculation ----------

def _calculate_surplus(db: Session, position: OrderPosition, good_quantity: int) -> int:
    """Calculate surplus tiles: good_quantity minus what was actually ordered.
    Only applies to single-factory positions (multi-factory is handled separately).
    """
    order_item = db.query(ProductionOrderItem).filter(
        ProductionOrderItem.id == position.order_item_id
    ).first()
    if not order_item:
        return 0
    needed = order_item.quantity_pcs or 0
    # Only calculate surplus for single-factory production (one root position per item)
    sibling_count = db.query(OrderPosition).filter(
        OrderPosition.order_item_id == position.order_item_id,
        OrderPosition.parent_position_id.is_(None),
    ).count()
    if sibling_count > 1:
        return 0  # Multi-factory: surplus determined after all are sorted
    return max(0, good_quantity - needed)


# ---------- Stock Fulfillment Check ----------

def _check_stock_fulfillment(db: Session, position: OrderPosition, good_quantity: int):
    """After sorting a stock position, check if ALL sibling positions are also sorted.

    If all sorted: compare total good vs needed quantity from order item.
    - Sufficient → create STOCK_TRANSFER tasks for non-home factory positions
    - Insufficient → create STOCK_SHORTAGE task for PM
    """
    order_item = db.query(ProductionOrderItem).filter(
        ProductionOrderItem.id == position.order_item_id
    ).first()
    if not order_item:
        return None

    needed = order_item.quantity_pcs

    # Find ALL positions for this order_item
    all_positions = db.query(OrderPosition).filter(
        OrderPosition.order_item_id == position.order_item_id,
        OrderPosition.status != PositionStatus.CANCELLED,
    ).all()

    # Check if ALL are sorted (none still in transferred_to_sorting)
    unsorted = [
        p for p in all_positions
        if _ev(p.status) == "transferred_to_sorting"
    ]
    if unsorted:
        return {
            "status": "waiting",
            "message": f"Waiting for {len(unsorted)} position(s) on other factories to be sorted",
            "unsorted_count": len(unsorted),
        }

    # All sorted! Sum good quantities (packed positions without split_category = the "good" ones)
    total_good = sum(
        p.quantity for p in all_positions
        if _ev(p.status) == "packed" and p.split_category is None
    )

    # Get the home factory (from the order)
    order = db.query(ProductionOrder).filter(
        ProductionOrder.id == position.order_id
    ).first()
    home_factory_id = order.factory_id if order else position.factory_id

    now = datetime.now(timezone.utc)

    if total_good >= needed:
        # Sufficient! Create transfer tasks for non-home factories
        transfer_tasks = []
        for p in all_positions:
            if p.factory_id != home_factory_id and _ev(p.status) == "packed" and p.split_category is None:
                home_factory = db.query(ProductionOrder).filter(
                    ProductionOrder.id == p.order_id
                ).first()
                home_name = "home factory"
                hf = db.query(OrderPosition).first()  # placeholder
                factory_obj = db.query(FinishedGoodsStock).first()  # placeholder

                # Get factory name
                from api.models import Factory
                dest_factory = db.query(Factory).filter(Factory.id == home_factory_id).first()
                dest_name = dest_factory.name if dest_factory else "home factory"

                task = Task(
                    id=uuid_mod.uuid4(),
                    factory_id=p.factory_id,
                    type=TaskType.STOCK_TRANSFER,
                    status=TaskStatus.PENDING,
                    assigned_role=UserRole.WAREHOUSE,
                    related_order_id=p.order_id,
                    related_position_id=p.id,
                    blocking=False,
                    description=f"Ship {p.quantity} pcs ({p.color} {p.size}) to {dest_name}",
                    priority=3,
                    metadata_json={
                        "destination_factory_id": str(home_factory_id),
                        "destination_factory_name": dest_name,
                        "quantity": p.quantity,
                        "color": p.color,
                        "size": p.size,
                    },
                    created_at=now,
                    updated_at=now,
                )
                db.add(task)
                transfer_tasks.append(str(task.id))

        db.commit()
        return {
            "status": "sufficient",
            "total_good": total_good,
            "needed": needed,
            "transfer_tasks_created": len(transfer_tasks),
        }

    else:
        # Shortage! Create PM task
        shortage = needed - total_good
        sorted_positions_info = [
            {
                "position_id": str(p.id),
                "factory_id": str(p.factory_id),
                "good": p.quantity,
                "status": _ev(p.status),
            }
            for p in all_positions
            if _ev(p.status) == "packed" and p.split_category is None
        ]

        task = Task(
            id=uuid_mod.uuid4(),
            factory_id=position.factory_id,
            type=TaskType.STOCK_SHORTAGE,
            status=TaskStatus.PENDING,
            assigned_role=UserRole.PRODUCTION_MANAGER,
            related_order_id=position.order_id,
            related_position_id=position.id,
            blocking=False,
            description=f"Stock shortage: {shortage} pcs needed ({position.color} {position.size})",
            priority=5,
            metadata_json={
                "needed": needed,
                "total_good": total_good,
                "shortage": shortage,
                "color": position.color,
                "size": position.size,
                "collection": position.collection,
                "order_item_id": str(position.order_item_id),
                "sorted_positions": sorted_positions_info,
            },
            created_at=now,
            updated_at=now,
        )
        db.add(task)
        db.commit()

        return {
            "status": "shortage",
            "total_good": total_good,
            "needed": needed,
            "shortage": shortage,
            "task_id": str(task.id),
        }


# ---------- Color Mismatch Resolution (PM Decision) ----------

class ColorMismatchResolveRequest(BaseModel):
    refire_qty: int = 0     # Already glazed; bubbles/wrong tone → re-fire only
    reglaze_qty: int = 0    # Needs full re-glaze + re-fire → SENT_TO_GLAZING
    stock_qty: int = 0      # Acceptable tiles → PACKED (enters QC → stock)
    notes: Optional[str] = None


@router.post("/{position_id}/resolve-color-mismatch")
async def resolve_color_mismatch(
    position_id: UUID,
    data: ColorMismatchResolveRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """PM resolves a color-mismatch sub-position by directing tiles into up to 3 paths:
    refire only / re-glaze+refire / accept to stock.
    The original color-mismatch position is cancelled (quantity zeroed out) and
    replaced by new sibling sub-positions under the same parent.
    """
    p = db.query(OrderPosition).filter(OrderPosition.id == position_id).first()
    if not p:
        raise HTTPException(404, "Position not found")
    if _ev(p.split_category) != "color_mismatch":
        raise HTTPException(400, "Position split_category must be 'color_mismatch'")
    if _ev(p.status) not in ("planned", "insufficient_materials"):
        raise HTTPException(400, f"Color-mismatch position must have status 'planned', got '{_ev(p.status)}'")

    total = data.refire_qty + data.reglaze_qty + data.stock_qty
    if total != p.quantity:
        raise HTTPException(400, f"Total ({total}) must equal position quantity ({p.quantity})")

    now = datetime.now(timezone.utc)
    new_positions: list[OrderPosition] = []

    # New positions are siblings of this CM position (same parent)
    parent_id = p.parent_position_id
    _base_si = _next_split_index(db, parent_id) - 1

    def _si() -> int:
        nonlocal _base_si
        _base_si += 1
        return _base_si

    def _clone(status: PositionStatus, qty: int, split_cat) -> OrderPosition:
        return OrderPosition(
            id=uuid_mod.uuid4(),
            order_id=p.order_id,
            order_item_id=p.order_item_id,
            parent_position_id=parent_id,
            factory_id=p.factory_id,
            status=status,
            quantity=qty,
            color=p.color, size=p.size,
            application=p.application, finishing=p.finishing,
            collection=p.collection, application_type=p.application_type,
            place_of_application=p.place_of_application,
            product_type=p.product_type, shape=p.shape,
            thickness_mm=p.thickness_mm, recipe_id=p.recipe_id,
            mandatory_qc=p.mandatory_qc,
            split_category=split_cat,
            priority_order=p.priority_order,
            position_number=p.position_number,
            split_index=_si(),
            created_at=now, updated_at=now,
        )

    if data.refire_qty > 0:
        pos = _clone(PositionStatus.REFIRE, data.refire_qty, SplitCategory.REFIRE)
        db.add(pos)
        new_positions.append(pos)

    if data.reglaze_qty > 0:
        pos = _clone(PositionStatus.SENT_TO_GLAZING, data.reglaze_qty, SplitCategory.REPAIR)
        db.add(pos)
        new_positions.append(pos)
        # Track in repair queue for SLA monitoring
        rq = RepairQueue(
            id=uuid_mod.uuid4(),
            factory_id=p.factory_id,
            color=p.color, size=p.size,
            quantity=data.reglaze_qty,
            defect_type="color_mismatch_reglaze",
            source_order_id=p.order_id,
            source_position_id=p.id,
            status=RepairStatus.IN_REPAIR,
            created_at=now, updated_at=now,
        )
        db.add(rq)

    if data.stock_qty > 0:
        pos = _clone(PositionStatus.PACKED, data.stock_qty, None)
        db.add(pos)
        new_positions.append(pos)

    # Mark original color-mismatch position as resolved
    p.status = PositionStatus.CANCELLED
    p.quantity = 0
    p.updated_at = now

    # Release reserved materials for the cancelled position
    try:
        from business.services.material_reservation import unreserve_materials_for_position
        unreserve_materials_for_position(db, p.id)
    except Exception as _e:
        import logging
        logging.getLogger("moonjar.positions").warning(
            "Failed to unreserve materials for color-mismatch position %s: %s", p.id, _e
        )

    db.commit()
    for np in new_positions:
        db.refresh(np)

    return {
        "resolved_position_id": str(position_id),
        "new_positions": [_serialize_position(np) for np in new_positions],
        "breakdown": {
            "refire": data.refire_qty,
            "reglaze": data.reglaze_qty,
            "stock": data.stock_qty,
        },
    }


# ---------- Stock Availability ----------

@router.get("/{position_id}/stock-availability")
async def get_stock_availability(
    position_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Check finished goods availability for a stock position (informational, shown before sorting)."""
    position = db.query(OrderPosition).filter(OrderPosition.id == position_id).first()
    if not position:
        raise HTTPException(404, "Position not found")

    if not is_stock_collection(position.collection):
        return {"error": "Not a stock position", "is_stock": False}

    # Get needed quantity from order item
    order_item = db.query(ProductionOrderItem).filter(
        ProductionOrderItem.id == position.order_item_id
    ).first()
    needed = order_item.quantity_pcs if order_item else position.quantity

    # Get stock on this factory
    local_stock = db.query(FinishedGoodsStock).filter(
        FinishedGoodsStock.factory_id == position.factory_id,
        FinishedGoodsStock.color == position.color,
        FinishedGoodsStock.size == position.size,
    ).first()
    local_available = max(0, local_stock.quantity - local_stock.reserved_quantity) if local_stock else 0

    # Get stock on all factories
    all_stocks = db.query(FinishedGoodsStock).filter(
        FinishedGoodsStock.color == position.color,
        FinishedGoodsStock.size == position.size,
    ).all()

    from api.models import Factory
    factories_info = []
    for s in all_stocks:
        avail = max(0, s.quantity - s.reserved_quantity)
        factory = db.query(Factory).filter(Factory.id == s.factory_id).first()
        factories_info.append({
            "factory_id": str(s.factory_id),
            "factory_name": factory.name if factory else "Unknown",
            "available": avail,
            "is_home": s.factory_id == position.factory_id,
        })

    total_available = sum(f["available"] for f in factories_info)

    # Check sibling positions (multi-factory fulfillment)
    siblings = db.query(OrderPosition).filter(
        OrderPosition.order_item_id == position.order_item_id,
        OrderPosition.id != position.id,
        OrderPosition.status != PositionStatus.CANCELLED,
    ).all()

    return {
        "is_stock": True,
        "needed": needed,
        "position_quantity": position.quantity,
        "factory_available": local_available,
        "all_factories": factories_info,
        "total_available": total_available,
        "sufficient_on_factory": local_available >= needed,
        "sufficient_total": total_available >= needed,
        "is_multi_factory": len(siblings) > 0,
        "sibling_count": len(siblings),
    }


# ================================================================
# STAGE 2 — PM Force Unblock
# ================================================================

class ForceUnblockInput(BaseModel):
    notes: str  # PM must provide a reason


@router.post("/{position_id}/force-unblock")
async def force_unblock_position(
    position_id: UUID,
    data: ForceUnblockInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """PM force-unblock: override any blocking status, force-reserve if needed.

    - insufficient_materials → force-reserve (may go negative), set PLANNED
    - awaiting_recipe → set PLANNED (PM takes responsibility)
    - awaiting_stencil_silkscreen / awaiting_color_matching → close blocking tasks, set PLANNED
    - blocked_by_qm → close QM block tasks, set PLANNED
    All actions are logged for audit.
    """
    import logging
    logger = logging.getLogger("moonjar.force_unblock")

    p = db.query(OrderPosition).filter(OrderPosition.id == position_id).first()
    if not p:
        raise HTTPException(404, "Position not found")

    current_status = p.status
    if current_status not in BLOCKING_STATUSES:
        raise HTTPException(
            400,
            f"Position status '{_ev(current_status)}' is not a blocking status. "
            f"Allowed: {[_ev(s) for s in BLOCKING_STATUSES]}",
        )

    if not data.notes or not data.notes.strip():
        raise HTTPException(400, "Notes are required for force-unblock (audit trail)")

    now = datetime.now(timezone.utc)
    negative_balances = []

    # --- Handle INSUFFICIENT_MATERIALS: force-reserve ---
    if current_status == PositionStatus.INSUFFICIENT_MATERIALS:
        recipe = db.query(Recipe).filter(Recipe.id == p.recipe_id).first() if p.recipe_id else None
        if recipe:
            from business.services.material_reservation import force_reserve_materials
            negative_balances = force_reserve_materials(db, p, recipe, p.factory_id)
        # Even without recipe (edge case), transition to planned

    # --- Close related blocking tasks ---
    blocking_tasks = (
        db.query(Task)
        .filter(
            Task.related_position_id == position_id,
            Task.blocking.is_(True),
            Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS]),
        )
        .all()
    )
    for task in blocking_tasks:
        task.status = TaskStatus.DONE
        task.completed_at = now
        task.updated_at = now

    # --- Transition to PLANNED ---
    old_status_str = _ev(p.status)
    p.status = PositionStatus.PLANNED
    p.updated_at = now

    # --- Audit metadata ---
    audit_task = Task(
        id=uuid_mod.uuid4(),
        factory_id=p.factory_id,
        type=TaskType.MANA_CONFIRMATION,  # Reuse for audit log of PM overrides
        status=TaskStatus.DONE,
        assigned_role=UserRole.PRODUCTION_MANAGER,
        related_order_id=p.order_id,
        related_position_id=p.id,
        blocking=False,
        description=f"PM Force-Unblock: {old_status_str} → planned",
        priority=0,
        completed_at=now,
        created_at=now,
        updated_at=now,
        metadata_json={
            "action": "force_unblock",
            "previous_status": old_status_str,
            "notes": data.notes.strip(),
            "user_id": str(current_user.id),
            "user_name": getattr(current_user, 'full_name', None) or str(current_user.id),
            "blocking_tasks_closed": [str(t.id) for t in blocking_tasks],
            "negative_balances": negative_balances,
        },
    )
    db.add(audit_task)

    # Recalculate order status
    _recalculate_order_status(db, p.order_id)

    # Reschedule position now that it is unblocked
    try:
        from business.services.production_scheduler import reschedule_position
        reschedule_position(db, p)
    except Exception as _e:
        logger.warning("Failed to reschedule position %s after force-unblock: %s", p.id, _e)

    db.commit()
    db.refresh(p)

    logger.warning(
        "FORCE_UNBLOCK | user=%s | position=%s | %s → planned | tasks_closed=%d | negatives=%d | notes=%s",
        current_user.id, p.id, old_status_str,
        len(blocking_tasks), len(negative_balances), data.notes[:80],
    )

    return {
        "position_id": str(p.id),
        "previous_status": old_status_str,
        "new_status": "planned",
        "blocking_tasks_closed": len(blocking_tasks),
        "negative_balances": negative_balances,
        "audit_note": data.notes.strip(),
    }


# ================================================================
# STAGE 3a — Material Reservations for a Position
# ================================================================

@router.get("/{position_id}/material-reservations")
async def get_material_reservations(
    position_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return material reservation details for a position.

    Shows each recipe material with required / reserved / available / deficit.
    """
    p = db.query(OrderPosition).filter(OrderPosition.id == position_id).first()
    if not p:
        raise HTTPException(404, "Position not found")

    recipe = db.query(Recipe).filter(Recipe.id == p.recipe_id).first() if p.recipe_id else None
    if not recipe:
        return {
            "position_id": str(p.id),
            "recipe_name": None,
            "materials": [],
            "has_recipe": False,
        }

    recipe_materials = (
        db.query(RecipeMaterial)
        .filter(RecipeMaterial.recipe_id == recipe.id)
        .all()
    )

    materials_info = []
    for rm in recipe_materials:
        material = db.query(Material).get(rm.material_id)
        if not material:
            continue

        # Calculate required
        if rm.unit == "per_sqm" and p.quantity_sqm:
            required = Decimal(str(rm.quantity_per_unit)) * Decimal(str(p.quantity_sqm))
        else:
            required = Decimal(str(rm.quantity_per_unit)) * Decimal(str(p.quantity))

        # Current stock balance
        stock = (
            db.query(MaterialStock)
            .filter(
                MaterialStock.material_id == rm.material_id,
                MaterialStock.factory_id == p.factory_id,
            )
            .first()
        )
        balance = Decimal(str(stock.balance)) if stock else Decimal("0")

        # Net reserved for this position
        pos_reserved = (
            db.query(func.coalesce(func.sum(MaterialTransaction.quantity), 0))
            .filter(
                MaterialTransaction.related_position_id == position_id,
                MaterialTransaction.material_id == rm.material_id,
                MaterialTransaction.type == TransactionType.RESERVE,
            )
            .scalar()
        )
        pos_unreserved = (
            db.query(func.coalesce(func.sum(MaterialTransaction.quantity), 0))
            .filter(
                MaterialTransaction.related_position_id == position_id,
                MaterialTransaction.material_id == rm.material_id,
                MaterialTransaction.type == TransactionType.UNRESERVE,
            )
            .scalar()
        )
        net_reserved_pos = Decimal(str(pos_reserved)) - Decimal(str(pos_unreserved))

        # Total net reserved across ALL positions for this material+factory
        total_reserved_all = (
            db.query(func.coalesce(func.sum(MaterialTransaction.quantity), 0))
            .filter(
                MaterialTransaction.material_id == rm.material_id,
                MaterialTransaction.factory_id == p.factory_id,
                MaterialTransaction.type == TransactionType.RESERVE,
            )
            .scalar()
        )
        total_unreserved_all = (
            db.query(func.coalesce(func.sum(MaterialTransaction.quantity), 0))
            .filter(
                MaterialTransaction.material_id == rm.material_id,
                MaterialTransaction.factory_id == p.factory_id,
                MaterialTransaction.type == TransactionType.UNRESERVE,
            )
            .scalar()
        )
        effective_available = balance - (Decimal(str(total_reserved_all)) - Decimal(str(total_unreserved_all)))

        # Determine status
        if net_reserved_pos >= required and net_reserved_pos > 0:
            if effective_available < 0:
                mat_status = "force_reserved"
            else:
                mat_status = "reserved"
        elif net_reserved_pos > 0:
            mat_status = "partially_reserved"
        else:
            if effective_available >= required:
                mat_status = "available"
            else:
                mat_status = "insufficient"

        deficit = max(Decimal("0"), required - max(effective_available, Decimal("0")))

        materials_info.append({
            "material_id": str(rm.material_id),
            "name": material.name,
            "type": material.material_type or "",
            "required": float(required),
            "reserved": float(net_reserved_pos),
            "available": float(effective_available),
            "deficit": float(deficit),
            "status": mat_status,
        })

    return {
        "position_id": str(p.id),
        "recipe_name": recipe.name if recipe else None,
        "materials": materials_info,
        "has_recipe": True,
    }


# ────────────────────────────────────────────────────────────────
# POST /api/positions/reorder — batch priority reorder
# ────────────────────────────────────────────────────────────────

class ReorderItem(BaseModel):
    id: UUID
    priority_order: int


class ReorderRequest(BaseModel):
    items: list[ReorderItem]


@router.post("/reorder")
async def reorder_positions(
    data: ReorderRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """
    Batch update priority_order for multiple positions.
    Used by Tablo drag-and-drop reordering.
    """
    if len(data.items) > 200:
        raise HTTPException(400, "Too many items (max 200)")

    updated = 0
    for item in data.items:
        pos = db.query(OrderPosition).filter(OrderPosition.id == item.id).first()
        if pos:
            pos.priority_order = item.priority_order
            updated += 1

    db.commit()
    return {"updated": updated, "total": len(data.items)}


# ────────────────────────────────────────────────────────────────
# POST /api/positions/{id}/reassign-batch — move to another batch
# ────────────────────────────────────────────────────────────────

class ReassignBatchRequest(BaseModel):
    target_batch_id: Optional[UUID] = None  # None = remove from batch
    notes: Optional[str] = None


@router.post("/{position_id}/reassign-batch")
async def reassign_position_batch(
    position_id: UUID,
    data: ReassignBatchRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Move a position to a different batch (or remove from batch)."""
    from api.models import Batch

    pos = db.query(OrderPosition).filter(OrderPosition.id == position_id).first()
    if not pos:
        raise HTTPException(404, "Position not found")

    old_batch_id = pos.batch_id

    if data.target_batch_id:
        target_batch = db.query(Batch).filter(Batch.id == data.target_batch_id).first()
        if not target_batch:
            raise HTTPException(404, "Target batch not found")
        if target_batch.factory_id != pos.factory_id:
            raise HTTPException(400, "Cannot move position to batch in different factory")
        pos.batch_id = target_batch.id
    else:
        pos.batch_id = None

    db.commit()

    return {
        "position_id": str(pos.id),
        "old_batch_id": str(old_batch_id) if old_batch_id else None,
        "new_batch_id": str(pos.batch_id) if pos.batch_id else None,
        "message": "Position reassigned",
    }


# ====================================================================
# PM MID-PRODUCTION SPLIT (Decision 2026-03-19)
# ====================================================================
from typing import List  # noqa: E402
from pydantic import Field  # noqa: E402


class ProductionSplitPart(BaseModel):
    quantity: int = Field(..., gt=0)
    quantity_sqm: Optional[float] = None
    priority_order: Optional[int] = None
    note: Optional[str] = None


class ProductionSplitRequest(BaseModel):
    splits: List[ProductionSplitPart] = Field(..., min_length=2)
    reason: str = Field(..., min_length=1)


@router.post("/{position_id}/split-production")
def split_position_production(
    position_id: UUID,
    body: ProductionSplitRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """
    PM splits a position during production.
    Parent is frozen (is_parent=True), children start from same stage.
    Cannot split while status=loaded_in_kiln.
    """
    from business.services.production_split import (
        split_position_mid_production,
        can_split_position,
    )

    position = db.query(OrderPosition).filter(OrderPosition.id == position_id).first()
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")

    can_split, reason_err = can_split_position(position)
    if not can_split:
        raise HTTPException(status_code=400, detail=reason_err)

    splits_data = [
        {
            'quantity': part.quantity,
            'quantity_sqm': part.quantity_sqm,
            'priority_order': part.priority_order,
            'note': part.note,
        }
        for part in body.splits
    ]

    try:
        children = split_position_mid_production(
            db=db,
            position=position,
            splits=splits_data,
            reason=body.reason,
            created_by_id=current_user.id,
        )
        db.commit()
        for c in children:
            db.refresh(c)
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Split failed: {str(e)}")

    return {
        "parent_position_id": str(position_id),
        "parent_is_parent": True,
        "children_count": len(children),
        "children": [
            {
                "id": str(c.id),
                "split_index": c.split_index,
                "quantity": c.quantity,
                "quantity_sqm": float(c.quantity_sqm) if c.quantity_sqm else None,
                "status": _ev(c.status),
            }
            for c in children
        ],
    }


@router.get("/{position_id}/split-tree")
def get_position_split_tree(
    position_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Get full split tree (parent + all descendants) for a position."""
    from business.services.production_split import get_split_tree

    tree = get_split_tree(db, position_id)
    if not tree:
        raise HTTPException(status_code=404, detail="Position not found")
    return tree


# ---------- Position Merge ----------

@router.get("/{position_id}/mergeable-children")
def get_mergeable_children_endpoint(
    position_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get list of children that can be merged back into this parent."""
    from business.services.sorting_split import get_mergeable_children

    parent = db.query(OrderPosition).filter(OrderPosition.id == position_id).first()
    if not parent:
        raise HTTPException(status_code=404, detail="Parent position not found")

    children = get_mergeable_children(db, position_id)
    return {
        "parent_id": str(position_id),
        "mergeable_children": [
            {
                "id": str(c.id),
                "status": _ev(c.status),
                "quantity": c.quantity,
                "split_category": _ev(c.split_category),
                "split_index": c.split_index,
                "position_label": position_label(c),
            }
            for c in children
        ],
    }


@router.post("/{position_id}/merge")
def merge_child_position(
    position_id: UUID,
    child_position_id: UUID = Body(..., embed=True, description="ID of child position to merge back"),
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Merge a child sub-position back into parent position."""
    from business.services.sorting_split import merge_position_back

    parent = db.query(OrderPosition).filter(OrderPosition.id == position_id).first()
    if not parent:
        raise HTTPException(status_code=404, detail="Parent position not found")

    child = db.query(OrderPosition).filter(OrderPosition.id == child_position_id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child position not found")

    try:
        result = merge_position_back(
            db=db,
            parent_position=parent,
            child_position=child,
            merged_by_id=current_user.id,
        )
        db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
