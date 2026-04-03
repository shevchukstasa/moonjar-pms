"""Orders router — production order management."""

import logging
import uuid as uuid_mod
from datetime import date, datetime, timezone
from uuid import UUID
from typing import Optional, Union, List

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, text

from api.database import get_db
from api.auth import apply_factory_filter
from api.roles import require_management
from api.models import ProductionOrder, ProductionOrderItem, OrderPosition, Factory, FinishedGoodsStock, Task, ProductionOrderStatusLog
from api.enums import OrderStatus, OrderSource, PositionStatus, TaskStatus, is_stock_collection, ChangeRequestStatus
from business.services.status_machine import transition_position_status

logger = logging.getLogger("moonjar.orders")

router = APIRouter()


def _ev(val):
    """Enum value to string."""
    return val.value if hasattr(val, "value") else str(val) if val else None


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


# --- Input schemas ---

class OrderItemInput(BaseModel):
    color: str
    size: str
    application: Optional[str] = None
    finishing: Optional[str] = None
    thickness: float = 11.0
    quantity_pcs: int
    quantity_sqm: Optional[float] = None
    collection: Optional[str] = None
    application_type: Optional[str] = None
    place_of_application: Optional[str] = None
    product_type: str = "tile"
    # Shape & dimension data for surface area calculation
    shape: Optional[str] = None        # rectangle, square, round, triangle, octagon, freeform
    length_cm: Optional[float] = None  # Length in cm
    width_cm: Optional[float] = None   # Width in cm
    depth_cm: Optional[float] = None   # Depth in cm (sinks only)
    bowl_shape: Optional[str] = None   # Bowl shape: parallelepiped, half_oval, other (sinks only)
    edge_profile: Optional[str] = None  # straight, bullnose, ogee, etc.
    color_2: Optional[str] = None       # Second color for Stencil/Silkscreen/Custom


class OrderCreateInput(BaseModel):
    order_number: str
    client: str
    client_location: Optional[str] = None
    sales_manager_name: Optional[str] = None
    factory_id: str
    document_date: Optional[date] = None
    final_deadline: Optional[date] = None
    desired_delivery_date: Optional[date] = None
    mandatory_qc: bool = False
    notes: Optional[str] = None
    items: list[OrderItemInput] = []
    source: Optional[str] = None  # 'pdf_upload' when confirmed from PDF parse


class OrderUpdateInput(BaseModel):
    order_number: Optional[str] = None
    client: Optional[str] = None
    client_location: Optional[str] = None
    sales_manager_name: Optional[str] = None
    sales_manager_contact: Optional[str] = None
    final_deadline: Optional[date] = None
    schedule_deadline: Optional[date] = None
    desired_delivery_date: Optional[date] = None
    mandatory_qc: Optional[bool] = None
    notes: Optional[str] = None
    factory_id: Optional[str] = None
    status: Optional[str] = None
    status_override: Optional[bool] = None


# --- Serializers ---

def _order_list_item(order, pos_count: int, pos_ready: int) -> dict:
    return {
        "id": str(order.id),
        "order_number": order.order_number,
        "client": order.client,
        "sales_manager_name": order.sales_manager_name,
        "factory_id": str(order.factory_id),
        "factory_name": order.factory.name if order.factory else "",
        "document_date": str(order.document_date) if order.document_date else None,
        "final_deadline": str(order.final_deadline) if order.final_deadline else None,
        "desired_delivery_date": str(order.desired_delivery_date) if order.desired_delivery_date else None,
        "status": _ev(order.status),
        "status_override": order.status_override,
        "source": _ev(order.source),
        "mandatory_qc": order.mandatory_qc,
        "positions_count": pos_count,
        "positions_ready": pos_ready,
        "days_remaining": (order.final_deadline - date.today()).days if order.final_deadline else None,
        "created_at": order.created_at.isoformat() if order.created_at else None,
    }


def _position_label(p) -> str:
    """Compute display label like #3 or #3.1 from position_number + split_index."""
    num = getattr(p, "position_number", None)
    idx = getattr(p, "split_index", None)
    if num is None:
        return None  # frontend falls back to index
    if idx is not None:
        return f"#{num}.{idx}"
    return f"#{num}"


def _order_detail(order, db: Session) -> dict:
    items = db.query(ProductionOrderItem).filter(
        ProductionOrderItem.order_id == order.id
    ).all()
    positions = db.query(OrderPosition).filter(
        OrderPosition.order_id == order.id
    ).order_by(OrderPosition.priority_order, OrderPosition.created_at).all()

    return {
        "id": str(order.id),
        "order_number": order.order_number,
        "client": order.client,
        "client_location": order.client_location,
        "sales_manager_name": order.sales_manager_name,
        "sales_manager_contact": order.sales_manager_contact,
        "factory_id": str(order.factory_id),
        "factory_name": order.factory.name if order.factory else "",
        "document_date": str(order.document_date) if order.document_date else None,
        "production_received_date": str(order.production_received_date) if order.production_received_date else None,
        "final_deadline": str(order.final_deadline) if order.final_deadline else None,
        "schedule_deadline": str(order.schedule_deadline) if order.schedule_deadline else None,
        "desired_delivery_date": str(order.desired_delivery_date) if order.desired_delivery_date else None,
        "status": _ev(order.status),
        "status_override": getattr(order, "status_override", None),
        "source": _ev(order.source),
        "mandatory_qc": order.mandatory_qc,
        "notes": order.notes,
        "days_remaining": (order.final_deadline - date.today()).days if order.final_deadline else None,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        # Cancellation request state — exposed so Sales/frontend can check current state
        "cancellation_requested": getattr(order, "cancellation_requested", False) or False,
        "cancellation_decision": getattr(order, "cancellation_decision", None),
        "cancellation_requested_at": (
            order.cancellation_requested_at.isoformat()
            if getattr(order, "cancellation_requested_at", None) else None
        ),
        "cancellation_decided_at": (
            order.cancellation_decided_at.isoformat()
            if getattr(order, "cancellation_decided_at", None) else None
        ),
        "items": [
            {
                "id": str(it.id),
                "color": it.color, "size": it.size,
                "application": it.application, "finishing": it.finishing,
                "thickness": float(it.thickness) if it.thickness else 11.0,
                "quantity_pcs": it.quantity_pcs,
                "quantity_sqm": float(it.quantity_sqm) if it.quantity_sqm else None,
                "collection": it.collection,
                "application_type": it.application_type,
                "place_of_application": it.place_of_application,
                "product_type": _ev(it.product_type),
            }
            for it in items
        ],
        "positions": [
            {
                "id": str(p.id),
                "order_item_id": str(p.order_item_id) if p.order_item_id else None,
                "status": _ev(p.status),
                "batch_id": str(p.batch_id) if p.batch_id else None,
                "resource_id": str(p.resource_id) if p.resource_id else None,
                "quantity": p.quantity,
                "color": p.color, "size": p.size,
                "application": p.application, "finishing": p.finishing,
                "collection": p.collection,
                "product_type": _ev(p.product_type),
                "thickness_mm": float(p.thickness_mm) if p.thickness_mm else 11.0,
                "delay_hours": float(p.delay_hours) if p.delay_hours else 0,
                "mandatory_qc": p.mandatory_qc,
                "priority_order": p.priority_order,
                "place_of_application": p.place_of_application,
                "shape": _ev(p.shape),
                "width_cm": float(p.width_cm) if getattr(p, 'width_cm', None) else None,
                "length_cm": float(p.length_cm) if getattr(p, 'length_cm', None) else None,
                "edge_profile": getattr(p, 'edge_profile', None),
                "edge_profile_sides": getattr(p, 'edge_profile_sides', None),
                "color_2": getattr(p, 'color_2', None),
                "application_method_code": getattr(p, 'application_method_code', None),
                # Position numbering fields (added for display)
                "position_number": getattr(p, "position_number", None),
                "split_index": getattr(p, "split_index", None),
                "position_label": _position_label(p),
                # Upfront schedule (TOC/DBR)
                "planned_glazing_date": str(p.planned_glazing_date) if p.planned_glazing_date else None,
                "planned_kiln_date": str(p.planned_kiln_date) if p.planned_kiln_date else None,
                "planned_sorting_date": str(p.planned_sorting_date) if p.planned_sorting_date else None,
                "planned_completion_date": str(p.planned_completion_date) if p.planned_completion_date else None,
                "estimated_kiln_id": str(p.estimated_kiln_id) if p.estimated_kiln_id else None,
                "estimated_kiln_name": (
                    p.estimated_kiln.name
                    if p.estimated_kiln_id and hasattr(p, 'estimated_kiln') and p.estimated_kiln
                    else None
                ),
                "schedule_version": getattr(p, "schedule_version", None),
                "created_at": p.created_at.isoformat() if p.created_at else None,
                # Material tracking
                "material_status": _compute_material_status(p),
            }
            for p in positions
        ],
        "positions_count": len(positions),
        "positions_ready": sum(1 for p in positions if _ev(p.status) in ("ready_for_shipment", "shipped")),
        "shipped_at": order.shipped_at.isoformat() if order.shipped_at else None,
    }


# --- Endpoint helpers (avoid duplication between GET and moved static routes) ---

def _stage_map_label(status_str: str) -> str:
    _map = {
        'planned': 'Planning', 'insufficient_materials': 'Planning',
        'awaiting_recipe': 'Planning', 'awaiting_stencil_silkscreen': 'Planning',
        'awaiting_color_matching': 'Planning',
        'engobe_applied': 'Glazing', 'engobe_check': 'Glazing',
        'glazed': 'Glazing', 'pre_kiln_check': 'Glazing', 'sent_to_glazing': 'Glazing',
        'in_kiln': 'Firing', 'fired': 'Fired',
        'sorting': 'Sorting', 'packing': 'Packing',
        'ready_for_shipment': 'Ready', 'shipped': 'Shipped',
    }
    return _map.get(status_str, status_str.replace("_", " ").title())


def _cancel_order_tasks(db: Session, order_id) -> int:
    """Cancel all non-terminal tasks linked to the order. Returns count of cancelled tasks.
    Records are kept in DB (soft-cancel) — only status changes to CANCELLED.
    Tasks that are already DONE or CANCELLED are left untouched.
    """
    result = db.query(Task).filter(
        Task.related_order_id == order_id,
        Task.status.notin_([TaskStatus.DONE, TaskStatus.CANCELLED]),
    ).all()
    for task in result:
        task.status = TaskStatus.CANCELLED
    return len(result)


def _order_queue_summary(order, db: Session) -> dict:
    """Shared position summary used by cancellation-requests and change-requests list."""
    positions = db.query(OrderPosition).filter(OrderPosition.order_id == order.id).all()
    pos_count = len(positions)
    pos_ready = sum(1 for p in positions if _ev(p.status) in ("ready_for_shipment", "shipped"))
    if positions:
        statuses = [_ev(p.status) for p in positions]
        most_common = max(set(statuses), key=statuses.count)
        current_stage = _stage_map_label(most_common)
    else:
        current_stage = "No positions"
    return {"pos_count": pos_count, "pos_ready": pos_ready, "current_stage": current_stage}


# --- Endpoints ---
# IMPORTANT: Static paths (/cancellation-requests, /change-requests) MUST be declared
# BEFORE parameterized paths (/{order_id}) to avoid route shadowing in Starlette.

@router.get("")
async def list_orders(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    factory_id: UUID | None = None,
    status: str | None = None,
    search: str | None = None,
    tab: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    query = db.query(ProductionOrder)
    query = apply_factory_filter(query, current_user, factory_id, ProductionOrder)

    if tab == "archive":
        query = query.filter(ProductionOrder.status.in_([
            OrderStatus.READY_FOR_SHIPMENT, OrderStatus.SHIPPED, OrderStatus.CANCELLED
        ]))
    elif tab != "all":
        query = query.filter(ProductionOrder.status.notin_([
            OrderStatus.READY_FOR_SHIPMENT, OrderStatus.SHIPPED, OrderStatus.CANCELLED
        ]))

    if status:
        query = query.filter(ProductionOrder.status == status)
    if search:
        query = query.filter(or_(
            ProductionOrder.order_number.ilike(f"%{search}%"),
            ProductionOrder.client.ilike(f"%{search}%"),
        ))

    total = query.count()
    ALLOWED_SORT_COLUMNS = {"created_at", "order_number", "client", "final_deadline", "status", "priority", "updated_at"}
    if sort_by not in ALLOWED_SORT_COLUMNS:
        sort_by = "created_at"
    sort_col = getattr(ProductionOrder, sort_by, ProductionOrder.created_at)
    query = query.order_by(sort_col.asc() if sort_order == "asc" else sort_col.desc())
    orders = query.offset((page - 1) * per_page).limit(per_page).all()

    items = []
    for o in orders:
        pc = db.query(func.count(OrderPosition.id)).filter(OrderPosition.order_id == o.id).scalar() or 0
        pr = db.query(func.count(OrderPosition.id)).filter(
            OrderPosition.order_id == o.id,
            OrderPosition.status.in_([PositionStatus.READY_FOR_SHIPMENT, PositionStatus.SHIPPED]),
        ).scalar() or 0
        items.append(_order_list_item(o, pc, pr))

    return {"items": items, "total": total, "page": page, "per_page": per_page}


@router.get("/cancellation-requests")
async def list_cancellation_requests_v2(
    factory_id: UUID | None = None,
    decision: str = Query("pending", description="Filter by decision: pending|accepted|rejected|all"),
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """List orders with pending (or all) cancellation requests. PM dashboard uses this.
    Declared before /{order_id} to avoid route shadowing.
    """
    query = db.query(ProductionOrder).filter(
        ProductionOrder.cancellation_requested.is_(True)
    )
    if decision != "all":
        query = query.filter(ProductionOrder.cancellation_decision == decision)

    query = apply_factory_filter(query, current_user, factory_id, ProductionOrder)
    orders = query.order_by(ProductionOrder.cancellation_requested_at.desc()).all()

    results = []
    for order in orders:
        summary = _order_queue_summary(order, db)
        results.append({
            "id": str(order.id),
            "order_number": order.order_number,
            "client": order.client,
            "client_location": order.client_location,
            "factory_id": str(order.factory_id),
            "factory_name": order.factory.name if order.factory else "",
            "status": _ev(order.status),
            "current_stage": summary["current_stage"],
            "positions_count": summary["pos_count"],
            "positions_ready": summary["pos_ready"],
            "final_deadline": str(order.final_deadline) if order.final_deadline else None,
            "external_id": order.external_id,
            "cancellation_requested_at": (
                order.cancellation_requested_at.isoformat()
                if order.cancellation_requested_at else None
            ),
            "cancellation_decision": order.cancellation_decision,
            "cancellation_decided_at": (
                order.cancellation_decided_at.isoformat()
                if getattr(order, "cancellation_decided_at", None) else None
            ),
        })
    return {"items": results, "total": len(results)}


@router.get("/change-requests")
async def list_change_requests_v2(
    factory_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """List orders with pending change requests from Sales. PM dashboard uses this.
    Declared before /{order_id} to avoid route shadowing.
    """
    query = db.query(ProductionOrder).filter(
        ProductionOrder.change_req_status == "pending"
    )
    query = apply_factory_filter(query, current_user, factory_id, ProductionOrder)
    orders = query.order_by(ProductionOrder.change_req_requested_at.desc()).all()

    results = []
    for order in orders:
        summary = _order_queue_summary(order, db)
        payload = order.change_req_payload or {}
        change_summary = {
            field: payload[field]
            for field in ("client", "final_deadline", "desired_delivery_date", "notes", "items")
            if field in payload
        }
        results.append({
            "id": str(order.id),
            "order_number": order.order_number,
            "client": order.client,
            "client_location": order.client_location,
            "factory_id": str(order.factory_id),
            "factory_name": order.factory.name if order.factory else "",
            "status": _ev(order.status),
            "current_stage": summary["current_stage"],
            "positions_count": summary["pos_count"],
            "positions_ready": summary["pos_ready"],
            "final_deadline": str(order.final_deadline) if order.final_deadline else None,
            "external_id": order.external_id,
            "change_req_requested_at": (
                order.change_req_requested_at.isoformat()
                if getattr(order, "change_req_requested_at", None) else None
            ),
            "change_req_status": getattr(order, "change_req_status", None),
            "change_req_payload": order.change_req_payload,
            "change_summary": change_summary,
        })
    return {"items": results, "total": len(results)}


# --- PDF Upload (parse + create) ---
# MUST be before /{order_id} to avoid route shadowing.

@router.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    factory_id: str = Query(..., description="Factory UUID — PDF orders still need a factory"),
    current_user=Depends(require_management),
):
    """Upload a PDF order document for parsing.

    Returns parsed data (preview) with confidence score and warnings.
    PM reviews the parsed data, edits if needed, then confirms via POST /orders.
    """
    from business.services.pdf_parser_service import parse_order_pdf, validate_pdf_file

    # Read file
    file_bytes = await file.read()

    # Validate
    errors = validate_pdf_file(file_bytes, file.filename or "unknown.pdf")
    if errors:
        raise HTTPException(400, detail="; ".join(errors))

    # Parse
    result = parse_order_pdf(file_bytes)

    # Inject factory_id so frontend can pre-fill
    parsed = result.to_dict()
    parsed["parsed_order"]["factory_id"] = factory_id

    return parsed


# --- PDF Confirm (reviewed parsed data → create order) ---

class PdfConfirmItemInput(BaseModel):
    color: str
    size: str
    quantity_pcs: int
    quantity_sqm: Optional[float] = None
    application: Optional[str] = None
    finishing: Optional[str] = None
    collection: Optional[str] = None
    product_type: str = "tile"
    application_type: Optional[str] = None
    place_of_application: Optional[str] = None
    thickness: float = 11.0


class PdfConfirmInput(BaseModel):
    order_number: str
    client: str
    client_location: Optional[str] = None
    sales_manager_name: Optional[str] = None
    factory_id: str
    document_date: Optional[date] = None
    final_deadline: Optional[date] = None
    desired_delivery_date: Optional[date] = None
    mandatory_qc: bool = False
    notes: Optional[str] = None
    items: list[PdfConfirmItemInput]


@router.post("/confirm-pdf", status_code=201)
async def confirm_pdf_order(
    data: PdfConfirmInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Confirm a parsed PDF order — creates the actual order and positions.

    The PM has reviewed and optionally edited the parsed data from upload-pdf.
    This endpoint creates the order using the same pipeline as manual creation.
    """
    if not data.items:
        raise HTTPException(400, "Order must have at least one item")

    order = ProductionOrder(
        order_number=data.order_number,
        client=data.client,
        client_location=data.client_location,
        sales_manager_name=data.sales_manager_name,
        factory_id=UUID(data.factory_id),
        document_date=data.document_date,
        production_received_date=date.today(),
        final_deadline=data.final_deadline,
        desired_delivery_date=data.desired_delivery_date,
        mandatory_qc=data.mandatory_qc,
        notes=data.notes,
        status=OrderStatus.NEW,
        source=OrderSource.PDF_UPLOAD,
    )
    db.add(order)
    db.flush()

    from business.services.order_intake import process_order_item

    for item_data in data.items:
        item = ProductionOrderItem(
            order_id=order.id,
            color=item_data.color,
            size=item_data.size,
            application=item_data.application,
            finishing=item_data.finishing,
            thickness=item_data.thickness,
            quantity_pcs=item_data.quantity_pcs,
            quantity_sqm=item_data.quantity_sqm,
            collection=item_data.collection,
            application_type=item_data.application_type,
            place_of_application=item_data.place_of_application,
            product_type=item_data.product_type,
        )
        db.add(item)
        db.flush()

        try:
            position = process_order_item(db, order, item)
        except Exception as e:
            logger.warning("Failed to process PDF item %s: %s", item_data.color, e)
            position = None

        if position and is_stock_collection(item_data.collection):
            _distribute_stock_position(db, position, item_data.quantity_pcs)

    db.commit()
    db.refresh(order)
    return _order_detail(order, db)


@router.post("/{order_id}/reprocess")
async def reprocess_order(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Re-run the intake pipeline for all positions of an existing order.

    Useful when positions were created before recipe lookup or material
    reservation was working correctly. For each position this will:
    1. Re-run recipe lookup (if recipe_id is None)
    2. Recalculate glazeable_sqm from shape_dimensions
    3. Recalculate quantity_with_defect_margin
    4. Run size resolution
    5. Reserve materials (if recipe exists)
    6. Create blocking tasks (stencil, silkscreen, color matching, service)
    7. Schedule production dates
    """
    from business.services.order_intake import (
        _find_recipe, _auto_detect_exclusive, _check_consumption_rates,
    )
    from business.services.surface_area import calculate_glazeable_sqm_for_position
    from business.services.size_resolution import resolve_size_for_position, create_size_resolution_task
    from business.services.material_reservation import reserve_materials_for_position

    order = db.query(ProductionOrder).filter(ProductionOrder.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")

    positions = (
        db.query(OrderPosition)
        .filter(OrderPosition.order_id == order_id)
        .all()
    )

    # Create positions for items that don't have one yet
    existing_item_ids = {p.order_item_id for p in positions if p.order_item_id}
    all_items = db.query(ProductionOrderItem).filter(
        ProductionOrderItem.order_id == order_id,
    ).all()
    new_positions_created = 0
    for item in all_items:
        if item.id not in existing_item_ids:
            try:
                from business.services.order_intake import process_order_item
                new_pos = process_order_item(db, order, item)
                if new_pos:
                    positions.append(new_pos)
                    new_positions_created += 1
                    logger.info(
                        "REPROCESS_NEW_POSITION | order=%s item=%s color=%s",
                        order.order_number, item.id, item.color,
                    )
            except Exception as e:
                logger.error("Failed to create position for item %s: %s", item.id, e)
    if new_positions_created:
        db.flush()

    results = []
    for p in positions:
        pos_result = {"position_number": p.position_number, "actions": []}

        # 1. Recipe lookup (if missing)
        if not p.recipe_id:
            item = db.query(ProductionOrderItem).filter(
                ProductionOrderItem.id == p.order_item_id
            ).first()
            if item:
                recipe = _find_recipe(db, item)
                if recipe:
                    p.recipe_id = recipe.id
                    pos_result["actions"].append(f"recipe_bound={recipe.name}")
                else:
                    pos_result["actions"].append("recipe_not_found")

        # 2. Recalculate glazeable_sqm
        new_area = calculate_glazeable_sqm_for_position(db, p)
        if new_area is not None:
            _area_f = float(new_area)
            _qsqm = round(_area_f * (p.quantity or 1), 4)
            p.glazeable_sqm = new_area
            p.quantity_sqm = _qsqm
            db.add(p)  # mark dirty explicitly
            db.flush()
            # Verify persistence by re-reading
            db.refresh(p)
            pos_result["actions"].append(
                f"area={_area_f:.4f},total_sqm={_qsqm},persisted={p.glazeable_sqm}"
            )

        # 3. Recalculate defect margin (2D: glaze + product type coefficients)
        if p.quantity and not p.quantity_with_defect_margin:
            from business.services.defect_coefficient import calculate_production_quantity_with_defects
            calculate_production_quantity_with_defects(db, p)
            pos_result["actions"].append(f"margin={p.quantity_with_defect_margin}")

        # 4. Size resolution (if no size_id)
        if not p.size_id:
            sr = resolve_size_for_position(db, p)
            if sr.resolved and sr.size_id:
                p.size_id = sr.size_id
                pos_result["actions"].append(f"size_resolved={sr.reason}")
            elif not sr.resolved and sr.reason != "missing_dimensions":
                create_size_resolution_task(db, p, order.id, order.factory_id, sr.reason, sr.candidates)
                pos_result["actions"].append(f"size_task_created={sr.reason}")

        # 4.5. Check consumption rates (if recipe bound)
        #   Blocks position with AWAITING_CONSUMPTION_DATA if spray/brush rates missing
        if p.recipe_id and _ev(p.status) == "planned":
            from api.models import Recipe as RecipeModel
            recipe_obj_for_check = db.query(RecipeModel).filter(RecipeModel.id == p.recipe_id).first()
            if recipe_obj_for_check:
                was_blocked = _check_consumption_rates(db, order, p, recipe_obj_for_check)
                if was_blocked:
                    db.flush()
                    pos_result["actions"].append("blocked_awaiting_consumption_data")

        # 5. Reserve materials (if recipe exists)
        #    ALWAYS clear old reserves and re-create from scratch during reprocess.
        #    This handles: quantity changes, recipe changes, rate changes.
        if p.recipe_id:
            try:
                from api.models import Recipe, MaterialTransaction
                from api.enums import TransactionType

                # Always clear old reserves — reprocess means "recalculate everything"
                old_reserves = (
                    db.query(MaterialTransaction)
                    .filter(
                        MaterialTransaction.related_position_id == p.id,
                        MaterialTransaction.type == TransactionType.RESERVE,
                    )
                    .all()
                )
                if old_reserves:
                    for txn in old_reserves:
                        db.delete(txn)
                    db.flush()
                    pos_result["actions"].append(f"old_reserves_cleared={len(old_reserves)}")
                # Reset reservation status
                p.status = PositionStatus.PLANNED
                p.reservation_at = None
                db.flush()

                recipe_obj = db.query(Recipe).filter(Recipe.id == p.recipe_id).first()
                res = reserve_materials_for_position(db, p, recipe_obj, order.factory_id)
                if res.all_sufficient:
                    pos_result["actions"].append("materials=reserved")
                else:
                    pos_result["actions"].append(f"materials=insufficient({len(res.shortages)} shortages)")
                    # Smart check + auto purchase + blocking — same as intake
                    from business.services.material_reservation import (
                        check_material_availability_smart, create_auto_purchase_request,
                    )
                    truly_missing = []
                    _glazing_date = None
                    if order.desired_delivery_date:
                        _glazing_date = order.desired_delivery_date - timedelta(days=7)
                    elif order.final_deadline:
                        _glazing_date = order.final_deadline - timedelta(days=7)

                    for shortage in res.shortages:
                        smart = check_material_availability_smart(
                            db=db, material_id=shortage.material_id,
                            factory_id=order.factory_id, required_qty=shortage.required,
                            effective_available=shortage.available,
                            planned_glazing_date=_glazing_date, buffer_days=3,
                        )
                        if not smart.available:
                            truly_missing.append(shortage)

                    if truly_missing:
                        if _ev(p.status) == "planned":
                            p.status = PositionStatus.INSUFFICIENT_MATERIALS
                            pos_result["actions"].append("blocked_insufficient_materials")
                        create_auto_purchase_request(db, order.factory_id, truly_missing, order)
                        pos_result["actions"].append(f"purchase_request_created({len(truly_missing)})")
            except Exception as e:
                pos_result["actions"].append(f"materials_error={str(e)[:50]}")

        # 6. Auto-detect exclusive
        if hasattr(p, 'application_collection_code'):
            item = db.query(ProductionOrderItem).filter(
                ProductionOrderItem.id == p.order_item_id
            ).first()
            if item and _auto_detect_exclusive(db, p, item):
                p.application_collection_code = 'exclusive'
                pos_result["actions"].append("auto_exclusive")

        p.updated_at = datetime.now(timezone.utc)
        results.append(pos_result)

    # 7. Schedule
    try:
        from business.services.production_scheduler import schedule_order
        schedule_order(db, order)
        for r in results:
            r["actions"].append("scheduled")
    except Exception as e:
        for r in results:
            r["actions"].append(f"schedule_error={str(e)[:50]}")

    db.commit()

    return {
        "ok": True,
        "order_id": str(order_id),
        "positions_reprocessed": len(results),
        "results": results,
    }


@router.post("/{order_id}/reschedule")
async def reschedule_order(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Reschedule an order: recalculate planned dates, assign kilns, reserve materials.

    1. Recalculate planned dates for all positions (backward scheduling from deadline)
    2. Assign estimated_kiln_id for positions that don't have one
    3. Reserve materials for planned positions that haven't been reserved yet

    Requires management role (PM / Admin / Owner).
    """
    import logging as _logging
    from business.services.production_scheduler import schedule_order as _schedule_order
    from business.services.production_scheduler import find_best_kiln
    from business.services.material_reservation import reserve_materials_for_position

    _logger = _logging.getLogger("moonjar.orders.reschedule")

    order = db.query(ProductionOrder).filter(ProductionOrder.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")

    # 1. Recalculate dates (schedule_order also assigns kilns internally)
    scheduled_count = _schedule_order(db, order)

    # 2. Double-check kiln assignment for any positions still missing estimated_kiln_id
    positions = (
        db.query(OrderPosition)
        .filter(
            OrderPosition.order_id == order_id,
            OrderPosition.status != PositionStatus.CANCELLED.value,
        )
        .all()
    )

    kiln_count = 0
    for p in positions:
        if not p.estimated_kiln_id and p.planned_kiln_date:
            kiln_id = find_best_kiln(db, p, p.planned_kiln_date)
            if kiln_id:
                p.estimated_kiln_id = kiln_id
                kiln_count += 1

    # 3. Reserve materials for planned positions without reservation
    from api.models import Recipe
    reserved_count = 0
    reservation_errors = []
    for p in positions:
        if not getattr(p, "reservation_at", None) and _ev(p.status) == "planned" and p.recipe_id:
            try:
                recipe = db.query(Recipe).filter(Recipe.id == p.recipe_id).first()
                if recipe:
                    result = reserve_materials_for_position(db, p, recipe, order.factory_id)
                    if result and not result.shortages:
                        reserved_count += 1
                    elif result and result.shortages:
                        reservation_errors.append({
                            "position": p.position_number,
                            "reason": "insufficient_materials",
                        })
            except Exception as e:
                _logger.warning(
                    "RESCHEDULE_RESERVE_FAIL | order=%s position=%s | %s",
                    order.order_number, p.id, e,
                )
                reservation_errors.append({
                    "position": p.position_number,
                    "reason": str(e)[:100],
                })

    db.commit()

    return {
        "ok": True,
        "order_id": str(order_id),
        "scheduled": scheduled_count,
        "kilns_assigned": kiln_count,
        "materials_reserved": reserved_count,
        "reservation_errors": reservation_errors,
    }


@router.get("/{order_id}")
async def get_order(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    order = db.query(ProductionOrder).filter(ProductionOrder.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    return _order_detail(order, db)


@router.post("", status_code=201)
async def create_order(
    data: OrderCreateInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Create an order manually (PM form or future PDF upload).

    Uses the same intake pipeline as webhook orders:
    recipe lookup → blocking tasks → material reservation → defect margin.
    """
    if not data.items:
        raise HTTPException(400, "Order must have at least one item")

    # Normalize product_type: table_top → countertop (unified name, PG enum uses 'countertop')
    for item in data.items:
        if item.product_type == "table_top":
            item.product_type = "countertop"

    # Auto-derive dimensions from size for large-format products
    for item in data.items:
        if item.product_type in ("countertop", "sink") and not (item.length_cm and item.width_cm):
            if item.size and "x" in item.size.lower():
                try:
                    parts = item.size.lower().replace(" ", "").split("x")
                    item.length_cm = float(parts[0])
                    item.width_cm = float(parts[1]) if len(parts) > 1 else item.length_cm
                except (ValueError, IndexError):
                    pass

    order = ProductionOrder(
        order_number=data.order_number,
        client=data.client,
        client_location=data.client_location,
        sales_manager_name=data.sales_manager_name,
        factory_id=UUID(data.factory_id),
        document_date=data.document_date,
        production_received_date=date.today(),
        final_deadline=data.final_deadline,
        desired_delivery_date=data.desired_delivery_date,
        mandatory_qc=data.mandatory_qc,
        notes=data.notes,
        status=OrderStatus.NEW,
        source=OrderSource.PDF_UPLOAD if data.source == "pdf_upload" else OrderSource.MANUAL,
    )
    db.add(order)
    db.flush()

    # Log initial order status
    try:
        db.add(ProductionOrderStatusLog(
            order_id=order.id,
            old_status=None,
            new_status=OrderStatus.NEW,
            changed_by=current_user.id,
        ))
    except Exception as e:
        logger.warning("Failed to log initial order status: %s", e)

    # Lazy import to avoid circular dependency
    from business.services.order_intake import process_order_item
    import logging as _logging
    _logger = _logging.getLogger("moonjar.orders.create")

    positions = []
    for item_data in data.items:
        item = ProductionOrderItem(
            order_id=order.id,
            color=item_data.color, size=item_data.size,
            application=item_data.application, finishing=item_data.finishing,
            thickness=item_data.thickness, quantity_pcs=item_data.quantity_pcs,
            quantity_sqm=item_data.quantity_sqm, collection=item_data.collection,
            application_type=item_data.application_type,
            place_of_application=item_data.place_of_application,
            product_type=item_data.product_type,
            # Shape & dimension data for glaze surface area
            shape=item_data.shape, length_cm=item_data.length_cm,
            width_cm=item_data.width_cm, depth_cm=item_data.depth_cm,
            bowl_shape=item_data.bowl_shape,
            edge_profile=item_data.edge_profile,
            color_2=item_data.color_2,
        )
        db.add(item)
        try:
            db.flush()
        except Exception as flush_err:
            import logging as _logging
            _logging.getLogger("moonjar.orders.create").error(
                "Item flush failed for color=%s size=%s product_type=%s thickness=%s: %s",
                item_data.color, item_data.size, item_data.product_type, item_data.thickness, flush_err
            )
            db.rollback()
            raise HTTPException(500, f"Failed to create item '{item_data.color} {item_data.size}': {str(flush_err)[:200]}")

        # Use the full intake pipeline: recipe lookup → blocking tasks →
        # material reservation → defect margin (same as webhook orders)
        try:
            position = process_order_item(db, order, item)
        except Exception as e:
            logger.warning("Failed to process item %s: %s", item_data.color, e)
            position = None

        if position:
            positions.append(position)

        # Stock positions: distribute across factories based on finished goods availability
        if position and is_stock_collection(item_data.collection):
            _distribute_stock_position(db, position, item_data.quantity_pcs)

    # ── Post-processing: same as webhook path ──────────────────
    # Backward scheduling (TOC/DBR) — calculate planned dates for positions
    try:
        from business.services.production_scheduler import schedule_order
        schedule_order(db, order)
    except Exception as e:
        _logger.warning("Failed to schedule manual order %s: %s", order.order_number, e)

    # Update order status based on position statuses
    old_status = order.status
    if positions and any(
        p.status in (
            PositionStatus.INSUFFICIENT_MATERIALS,
            PositionStatus.AWAITING_RECIPE,
            PositionStatus.AWAITING_STENCIL_SILKSCREEN,
            PositionStatus.AWAITING_COLOR_MATCHING,
            PositionStatus.AWAITING_SIZE_CONFIRMATION,
        )
        for p in positions
    ):
        order.status = OrderStatus.NEW
    elif positions:
        order.status = OrderStatus.IN_PRODUCTION

    # Log order status transition (NEW → IN_PRODUCTION if all positions are clean)
    if order.status != old_status:
        try:
            db.add(ProductionOrderStatusLog(
                order_id=order.id,
                old_status=old_status,
                new_status=order.status,
                changed_by=current_user.id,
            ))
        except Exception as e:
            logger.warning("Failed to log order status transition: %s", e)

    db.commit()
    db.refresh(order)

    # Notify PM about new manual order (best-effort, after commit)
    try:
        from business.services.notifications import notify_pm
        notify_pm(
            db=db,
            factory_id=order.factory_id,
            type="status_change",
            title=f"New manual order: {order.order_number}",
            message=(
                f"Client: {order.client}, "
                f"{len(positions)} position(s). "
                f"Deadline: {order.final_deadline or 'not set'}"
            ),
            related_entity_type="order",
            related_entity_id=order.id,
        )
    except Exception as e:
        _logger.warning("Failed to notify PM about manual order %s: %s", order.order_number, e)

    # Immediate overdue alert if deadline is already in the past
    if order.final_deadline and order.final_deadline < date.today():
        try:
            from api.models import Notification, User, UserFactory
            from api.enums import NotificationType, UserRole
            days_late = (date.today() - order.final_deadline).days
            alert_title = f"OVERDUE ORDER: {order.order_number} ({days_late}d late)"
            alert_msg = (
                f"Order created with a past deadline! "
                f"Client: {order.client}, Deadline: {order.final_deadline}"
            )
            notify_roles = [
                UserRole.PRODUCTION_MANAGER.value,
                UserRole.CEO.value,
                UserRole.OWNER.value,
            ]
            notified: set = set()
            for role in notify_roles:
                for uf in (
                    db.query(UserFactory)
                    .join(User)
                    .filter(
                        UserFactory.factory_id == order.factory_id,
                        User.role == role,
                        User.is_active.is_(True),
                    )
                    .all()
                ):
                    if uf.user_id in notified:
                        continue
                    notified.add(uf.user_id)
                    db.add(Notification(
                        user_id=uf.user_id,
                        factory_id=order.factory_id,
                        type=NotificationType.ALERT,
                        title=alert_title,
                        message=alert_msg,
                    ))
            if notified:
                db.commit()
        except Exception as e:
            _logger.warning("Failed to send overdue alert for order %s: %s", order.order_number, e)

    # RAG indexing (background, best-effort)
    try:
        import os
        if os.getenv("OPENAI_API_KEY"):
            from business.rag.embeddings import index_order
            await index_order(db, order.id)
            db.commit()
    except Exception as e:
        logger.debug("RAG indexing failed for order %s: %s", order.id, e)

    return _order_detail(order, db)


@router.patch("/{order_id}")
async def update_order(
    order_id: UUID,
    data: OrderUpdateInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    order = db.query(ProductionOrder).filter(ProductionOrder.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    updates = data.model_dump(exclude_unset=True)
    # Convert factory_id string to UUID if provided
    if "factory_id" in updates and updates["factory_id"] is not None:
        updates["factory_id"] = UUID(updates["factory_id"])
    for k, v in updates.items():
        setattr(order, k, v)
    order.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(order)
    return _order_detail(order, db)


@router.delete("/{order_id}", status_code=204)
async def cancel_order(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    from business.services.order_cancellation import process_order_cancellation
    import logging
    _logger = logging.getLogger("moonjar.orders")

    order = db.query(ProductionOrder).filter(ProductionOrder.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")

    try:
        process_order_cancellation(db, order_id, confirmed_by=current_user.id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        _logger.error("Order cancellation failed for %s: %s", order_id, e)
        raise HTTPException(500, "Order cancellation failed")


@router.patch("/{order_id}/ship")
async def mark_order_shipped(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Mark order as shipped. All READY_FOR_SHIPMENT positions → SHIPPED."""
    order = db.query(ProductionOrder).filter(ProductionOrder.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    if _ev(order.status) == "cancelled":
        raise HTTPException(400, "Cannot ship a cancelled order")

    # Transition all ready positions to shipped
    positions = db.query(OrderPosition).filter(
        OrderPosition.order_id == order_id,
        OrderPosition.status == PositionStatus.READY_FOR_SHIPMENT,
    ).all()

    if not positions:
        raise HTTPException(400, "No positions are ready for shipment")

    for p in positions:
        transition_position_status(db, p.id, PositionStatus.SHIPPED.value, changed_by=current_user.id)

    old_status = order.status
    order.status = OrderStatus.SHIPPED
    order.shipped_at = datetime.now(timezone.utc)
    order.updated_at = datetime.now(timezone.utc)

    # Log order status change
    try:
        db.add(ProductionOrderStatusLog(
            order_id=order.id,
            old_status=old_status,
            new_status=OrderStatus.SHIPPED,
            changed_by=current_user.id,
        ))
    except Exception as e:
        logger.warning("Failed to log shipped status change: %s", e)

    db.commit()

    # Notify Sales app if order has external_id (with retry)
    if order.external_id:
        from business.services.webhook_sender import send_webhook
        await send_webhook(
            {
                "event": "order_shipped",
                "external_id": order.external_id,
                "order_number": order.order_number,
                "client": order.client,
                "shipped_at": order.shipped_at.isoformat(),
                "positions_shipped": len(positions),
                "status": "shipped",
            },
            event_type="order_shipped",
            external_id=order.external_id,
        )

    return {
        "status": "shipped",
        "positions_shipped": len(positions),
        "shipped_at": order.shipped_at.isoformat(),
    }


# --- Cancellation request management (PM side) ---
# Note: GET /cancellation-requests is declared earlier (before /{order_id}) to avoid route shadowing.


@router.post("/{order_id}/accept-cancellation")
async def accept_cancellation(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """PM accepts the cancellation request → order status → CANCELLED."""
    from api.models import Notification
    from api.enums import NotificationType, RelatedEntityType

    order = db.query(ProductionOrder).filter(ProductionOrder.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    if not order.cancellation_requested or order.cancellation_decision != "pending":
        raise HTTPException(400, "No pending cancellation request for this order")

    # Apply decision metadata
    order.cancellation_decision = "accepted"
    order.cancellation_decided_at = datetime.now(timezone.utc)
    order.cancellation_decided_by = current_user.id

    # Delegate full cancellation logic to service
    from business.services.order_cancellation import process_order_cancellation
    import logging
    _logger = logging.getLogger("moonjar.orders")

    try:
        result = process_order_cancellation(db, order_id, confirmed_by=current_user.id)
        tasks_cancelled = result.get("tasks_cancelled", 0)
    except Exception as e:
        _logger.error("Order cancellation service failed for %s: %s", order_id, e)
        raise HTTPException(500, "Order cancellation failed")

    # Notify PMs at this factory about cancellation (best-effort)
    try:
        from business.services.notifications import notify_pm
        notify_pm(
            db=db,
            factory_id=order.factory_id,
            type=NotificationType.ORDER_CANCELLED.value,
            title=f"Order {order.order_number} has been cancelled",
            message=f"Client: {order.client}. Cancelled by {current_user.name}.",
            related_entity_type=RelatedEntityType.ORDER.value,
            related_entity_id=order.id,
        )
    except Exception as exc:
        _logger.warning("Failed to notify PMs about cancellation of %s: %s", order.order_number, exc)

    # Notify Sales App of cancellation (with retry)
    if order.external_id:
        from business.services.webhook_sender import send_webhook
        await send_webhook(
            {
                "event": "cancellation_accepted",
                "external_id": order.external_id,
                "order_number": order.order_number,
                "status": "cancelled",
                "decided_by": current_user.name,
                "decided_at": order.cancellation_decided_at.isoformat(),
            },
            event_type="cancellation_accepted",
            external_id=order.external_id,
        )

    return {
        "status": "accepted",
        "order_id": str(order_id),
        "order_number": order.order_number,
        "decided_by": current_user.name,
        "tasks_cancelled": tasks_cancelled,
    }


@router.post("/{order_id}/reject-cancellation")
async def reject_cancellation(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """PM rejects the cancellation request → order continues as-is."""
    order = db.query(ProductionOrder).filter(ProductionOrder.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    if not order.cancellation_requested or order.cancellation_decision != "pending":
        raise HTTPException(400, "No pending cancellation request for this order")

    order.cancellation_decision = "rejected"
    order.cancellation_decided_at = datetime.now(timezone.utc)
    order.cancellation_decided_by = current_user.id
    order.updated_at = datetime.now(timezone.utc)
    db.commit()

    # Notify Sales App of rejection (with retry)
    if order.external_id:
        from business.services.webhook_sender import send_webhook
        await send_webhook(
            {
                "event": "cancellation_rejected",
                "external_id": order.external_id,
                "order_number": order.order_number,
                "status": _ev(order.status),
                "decided_by": current_user.name,
                "decided_at": order.cancellation_decided_at.isoformat(),
            },
            event_type="cancellation_rejected",
            external_id=order.external_id,
        )

    return {
        "status": "rejected",
        "order_id": str(order_id),
        "order_number": order.order_number,
        "decided_by": current_user.name,
    }


# --- Change request management (PM side) ---
# Note: GET /change-requests is declared earlier (before /{order_id}) to avoid route shadowing.


class ChangeRequestApproveRequest(BaseModel):
    apply_to_positions: Union[str, List[str]] = "all"  # "all" or list of position UUIDs
    notes: Optional[str] = None


class ChangeRequestRejectRequest(BaseModel):
    reason: str


@router.get("/{order_id}/change-requests")
async def list_order_change_requests(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """List all change requests for a specific order (history + pending)."""
    from api.models import ProductionOrderChangeRequest

    order = db.query(ProductionOrder).filter(ProductionOrder.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")

    crs = (
        db.query(ProductionOrderChangeRequest)
        .filter(ProductionOrderChangeRequest.order_id == order_id)
        .order_by(ProductionOrderChangeRequest.created_at.desc())
        .all()
    )

    return {
        "order_id": str(order_id),
        "order_number": order.order_number,
        "items": [
            {
                "id": str(cr.id),
                "change_type": cr.change_type,
                "status": _ev(cr.status),
                "diff": cr.diff_json.get("diff") if cr.diff_json else None,
                "new_data": cr.diff_json.get("new_data") if cr.diff_json else None,
                "old_data": cr.diff_json.get("old_data") if cr.diff_json else None,
                "source": (cr.diff_json or {}).get("source"),
                "notes": cr.notes,
                "reviewed_by": str(cr.reviewed_by) if cr.reviewed_by else None,
                "created_at": cr.created_at.isoformat() if cr.created_at else None,
                "reviewed_at": cr.reviewed_at.isoformat() if cr.reviewed_at else None,
            }
            for cr in crs
        ],
        "total": len(crs),
    }


@router.post("/{order_id}/approve-change")
async def approve_change_request(
    order_id: UUID,
    body: ChangeRequestApproveRequest = ChangeRequestApproveRequest(),
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """PM approves the change request → apply stored payload changes to the order."""
    from api.models import ProductionOrderChangeRequest
    from business.services.change_request_service import approve_change_request as svc_approve

    order = db.query(ProductionOrder).filter(ProductionOrder.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    if order.change_req_status != "pending":
        raise HTTPException(400, "No pending change request for this order")

    # Find the latest pending CR record
    cr = (
        db.query(ProductionOrderChangeRequest)
        .filter(
            ProductionOrderChangeRequest.order_id == order_id,
            ProductionOrderChangeRequest.status == ChangeRequestStatus.PENDING,
        )
        .order_by(ProductionOrderChangeRequest.created_at.desc())
        .first()
    )

    if cr:
        # Use service for full flow (sets cr.status, order fields, logs)
        result = svc_approve(
            db=db,
            order=order,
            cr=cr,
            apply_to_positions=body.apply_to_positions,
            notes=body.notes,
            approved_by_id=current_user.id,
        )
    else:
        # Fallback: no CR record (legacy path — only change_req_* fields on order)
        payload = order.change_req_payload or {}
        updatable_fields = ("client", "client_location", "final_deadline", "desired_delivery_date",
                            "notes", "sales_manager_name", "sales_manager_contact", "mandatory_qc")
        applied_fields = []
        for field in updatable_fields:
            if field in payload:
                val = payload[field]
                if field in ("final_deadline", "desired_delivery_date") and isinstance(val, str):
                    try:
                        from datetime import date as date_type
                        val = date_type.fromisoformat(val)
                    except (ValueError, TypeError):
                        val = None
                setattr(order, field, val)
                applied_fields.append(field)
        order.change_req_status = "approved"
        order.change_req_decided_at = datetime.now(timezone.utc)
        order.change_req_decided_by = current_user.id
        order.change_req_payload = None
        order.updated_at = datetime.now(timezone.utc)
        result = {"applied_fields": applied_fields}

    db.commit()

    # Notify Sales App (fire-and-forget)
    if order.external_id:
        from business.services.webhook_sender import send_webhook
        await send_webhook(
            {
                "event": "change_request_approved",
                "external_id": order.external_id,
                "order_number": order.order_number,
                "decided_by": current_user.name,
                "decided_at": order.change_req_decided_at.isoformat() if order.change_req_decided_at else None,
                "applied_fields": result.get("applied_fields", []),
                "notes": body.notes,
            },
            event_type="change_request_approved",
            external_id=order.external_id,
        )

    return {
        "status": "approved",
        "order_id": str(order_id),
        "order_number": order.order_number,
        "decided_by": current_user.name,
        "applied_fields": result.get("applied_fields", []),
        "notes": body.notes,
    }


@router.post("/{order_id}/reject-change")
async def reject_change_request(
    order_id: UUID,
    body: ChangeRequestRejectRequest = ChangeRequestRejectRequest(reason=""),
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """PM rejects the change request → discard stored changes."""
    from api.models import ProductionOrderChangeRequest
    from business.services.change_request_service import reject_change_request as svc_reject

    order = db.query(ProductionOrder).filter(ProductionOrder.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    if order.change_req_status != "pending":
        raise HTTPException(400, "No pending change request for this order")

    # Find the latest pending CR record
    cr = (
        db.query(ProductionOrderChangeRequest)
        .filter(
            ProductionOrderChangeRequest.order_id == order_id,
            ProductionOrderChangeRequest.status == ChangeRequestStatus.PENDING,
        )
        .order_by(ProductionOrderChangeRequest.created_at.desc())
        .first()
    )

    if cr:
        svc_reject(
            db=db,
            order=order,
            cr=cr,
            reason=body.reason,
            rejected_by_id=current_user.id,
        )
    else:
        # Fallback: no CR record (legacy path)
        order.change_req_status = "rejected"
        order.change_req_decided_at = datetime.now(timezone.utc)
        order.change_req_decided_by = current_user.id
        order.change_req_payload = None
        order.updated_at = datetime.now(timezone.utc)

    db.commit()

    # Notify Sales App (with retry)
    if order.external_id:
        from business.services.webhook_sender import send_webhook
        await send_webhook(
            {
                "event": "change_request_rejected",
                "external_id": order.external_id,
                "order_number": order.order_number,
                "status": _ev(order.status),
                "decided_by": current_user.name,
                "decided_at": order.change_req_decided_at.isoformat() if order.change_req_decided_at else None,
                "reason": body.reason,
            },
            event_type="change_request_rejected",
            external_id=order.external_id,
        )

    return {
        "status": "rejected",
        "order_id": str(order_id),
        "order_number": order.order_number,
        "decided_by": current_user.name,
        "reason": body.reason,
    }


# --- Stock distribution helper ---

def _distribute_stock_position(db: Session, position: OrderPosition, needed_qty: int):
    """Distribute a stock position across factories based on finished goods availability.

    Logic:
    1. Check home factory → if sufficient, do nothing
    2. Check if any single factory has full quantity → auto-transfer (change factory_id)
    3. No single factory has full qty → split across multiple factories (create sibling positions)
    """
    home_factory_id = position.factory_id

    # Get all available stock for this color + size across factories
    all_stocks = db.query(FinishedGoodsStock).filter(
        FinishedGoodsStock.color == position.color,
        FinishedGoodsStock.size == position.size,
    ).all()

    def _available(stock: FinishedGoodsStock) -> int:
        return max(0, stock.quantity - stock.reserved_quantity)

    # 1. Check home factory
    home_stock = next((s for s in all_stocks if s.factory_id == home_factory_id), None)
    home_available = _available(home_stock) if home_stock else 0

    if home_available >= needed_qty:
        return  # Sufficient on home factory

    # 2. Check if any single factory has full quantity
    for s in sorted(all_stocks, key=_available, reverse=True):
        if s.factory_id != home_factory_id and _available(s) >= needed_qty:
            # Single factory has everything → auto-transfer
            position.factory_id = s.factory_id
            return

    # 3. Distribute across multiple factories
    # Home factory keeps what it has, create siblings on other factories
    if home_available > 0:
        position.quantity = home_available
    else:
        position.quantity = 0  # Will be updated below if no stock on home

    remaining = needed_qty - position.quantity

    # If home has 0, try to use all from other factories
    for s in sorted(all_stocks, key=_available, reverse=True):
        if remaining <= 0:
            break
        if s.factory_id == home_factory_id:
            continue
        avail = _available(s)
        if avail <= 0:
            continue

        take = min(avail, remaining)

        sibling = OrderPosition(
            id=uuid_mod.uuid4(),
            order_id=position.order_id,
            order_item_id=position.order_item_id,
            parent_position_id=position.id,
            factory_id=s.factory_id,
            status=PositionStatus.TRANSFERRED_TO_SORTING,
            quantity=take,
            color=position.color,
            size=position.size,
            application=position.application,
            finishing=position.finishing,
            collection=position.collection,
            application_type=position.application_type,
            place_of_application=position.place_of_application,
            product_type=position.product_type,
            thickness_mm=position.thickness_mm,
            mandatory_qc=position.mandatory_qc,
            priority_order=position.priority_order,
        )
        db.add(sibling)
        remaining -= take

    # If home had 0 stock and we created siblings, remove the empty home position
    # Actually keep it — position.quantity=0 won't show in sorting meaningfully
    # But better to set quantity to whatever was allocated
    if position.quantity == 0 and home_available == 0:
        # No stock on home — if we distributed all to other factories, mark position quantity=0
        # The siblings carry the actual quantities
        pass
