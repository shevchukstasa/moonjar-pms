"""
Order Intake Pipeline service.
Business Logic: §1-3

Handles: webhook/PDF/manual → order + items → positions → blocking tasks.
"""
from uuid import UUID
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional
import logging

from sqlalchemy.orm import Session
from sqlalchemy import func

from api.models import (
    ProductionOrder,
    ProductionOrderItem,
    OrderPosition,
    Recipe,
    Task,
    Factory,
    SalesWebhookEvent,
    Material,
    ProductionOrderStatusLog,
)
from api.enums import (
    PositionStatus,
    OrderStatus,
    OrderSource,
    TaskType,
    TaskStatus,
    ProductType,
    ShapeType,
    UserRole,
    is_stock_collection,
    EdgeProfileType,
    ApplicationMethodCode,
    ApplicationCollectionCode,
)

logger = logging.getLogger("moonjar.order_intake")


# ────────────────────────────────────────────────────────────────
# Service item detection helpers
# ────────────────────────────────────────────────────────────────

_SERVICE_KEYWORDS = [
    "design", "matching service", "color matching", "design&production",
    "design & production", "stencil design", "silkscreen design",
]


def is_service_item(item_data: dict) -> bool:
    """Detect non-production service items (stencil design, silkscreen design, color matching).

    These items create Tasks instead of production positions.
    """
    # Explicit flag from Sales
    if item_data.get("is_additional_item") or item_data.get("is_service"):
        return True
    # Heuristic: keywords in application/description/name
    app = (item_data.get("application") or "").strip().lower()
    desc = (item_data.get("description") or "").strip().lower()
    name = (item_data.get("name") or "").strip().lower()
    combined = f"{desc} {name} {app}"
    return any(kw in combined for kw in _SERVICE_KEYWORDS)


def detect_service_task_type(item_data: dict) -> Optional[TaskType]:
    """Determine task type for a service item."""
    app = (item_data.get("application") or "").strip().lower()
    desc = (item_data.get("description") or item_data.get("name") or "").strip().lower()
    combined = f"{desc} {app}"
    if "stencil" in combined:
        return TaskType.STENCIL_ORDER
    if "silkscreen" in combined or "silk_screen" in combined or "silk screen" in combined:
        return TaskType.SILK_SCREEN_ORDER
    if "color matching" in combined or "color_matching" in combined:
        return TaskType.COLOR_MATCHING
    return None


# ────────────────────────────────────────────────────────────────
# Defect margin calculation
# ────────────────────────────────────────────────────────────────

def _get_defect_coefficient(db: Session, factory_id, size: str) -> float:
    """
    Calculate stone defect coefficient from last 90 days of defect records.
    Returns fraction (e.g., 0.05 for 5% defect rate).
    If no data, returns default 0.05.
    Capped at 0.30 (30%) to prevent extreme margins from bad data.
    """
    from api.models import DefectRecord

    cutoff = datetime.now(timezone.utc) - timedelta(days=90)

    # Total produced pieces for this size at this factory in last 90 days
    total_produced = db.query(func.coalesce(func.sum(OrderPosition.quantity), 0)).filter(
        OrderPosition.factory_id == factory_id,
        OrderPosition.size == size,
        OrderPosition.created_at >= cutoff,
        OrderPosition.status.notin_(['cancelled']),
    ).scalar()

    # Total defective pieces from DefectRecords linked to positions
    # with matching size at this factory
    total_defects = db.query(func.coalesce(func.sum(DefectRecord.quantity), 0)).join(
        OrderPosition, DefectRecord.position_id == OrderPosition.id
    ).filter(
        OrderPosition.factory_id == factory_id,
        OrderPosition.size == size,
        DefectRecord.date >= cutoff.date(),
    ).scalar()

    if total_produced and int(total_produced) > 0 and total_defects:
        coeff = float(total_defects) / float(total_produced)
        return min(coeff, 0.30)  # cap at 30%

    return 0.05  # default 5%


# ────────────────────────────────────────────────────────────────
# §1  Main entry point
# ────────────────────────────────────────────────────────────────

def process_incoming_order(
    db: Session,
    payload: dict,
    source: str,
    *,
    skip_scheduling: bool = False,
    skip_duplicate_check: bool = False,
    factory_id_override: Optional[UUID] = None,
    return_order: bool = False,
) -> dict:
    """
    Entry point: webhook/PDF/manual → order + positions.

    Args:
        skip_scheduling: If True, skip immediate TOC/DBR scheduling (caller handles it).
        skip_duplicate_check: If True, skip idempotency and existing-order checks (caller already verified).
        factory_id_override: Pre-resolved factory UUID (skips auto-assignment).
        return_order: If True, include the ORM order object under key "_order".

    Steps:
    1. Idempotency check (webhook only)
    2. Check if order already exists → create change request
    3. Create new production order
    4. Auto-assign factory
    5. Create order items (separate service items from product items)
    6. Process product items → create positions
    7. Create Tasks for service items
    8. Link service tasks to matching positions
    9. Schedule (unless skip_scheduling)
    10. Notify PM
    """
    external_id = payload.get("external_id")

    # 1-2. Idempotency & existence checks (skipped when caller already verified)
    if not skip_duplicate_check:
        # 1. Idempotency (webhook)
        if source == OrderSource.SALES_WEBHOOK.value:
            event_id = payload.get("event_id")
            if event_id:
                existing_event = (
                    db.query(SalesWebhookEvent)
                    .filter(SalesWebhookEvent.event_id == event_id)
                    .first()
                )
                if existing_event:
                    return {"status": "duplicate", "event_id": event_id}

        # 2. Check existing order by external_id
        if external_id:
            existing_order = (
                db.query(ProductionOrder)
                .filter(
                    ProductionOrder.source == source,
                    ProductionOrder.external_id == external_id,
                )
                .first()
            )
            if existing_order:
                # Order exists — for now, return info (change request handling is separate)
                return {
                    "status": "exists",
                    "order_id": str(existing_order.id),
                    "order_number": existing_order.order_number,
                }

    # 3. Determine factory
    factory_id = factory_id_override or payload.get("factory_id")
    if not factory_id:
        client_location = payload.get("client_location", "")
        factory = assign_factory(db, client_location)
        factory_id = factory.id

    # 4. Create production order
    order = ProductionOrder(
        order_number=payload.get("order_number", _generate_order_number(db)),
        client=payload.get("client", "Unknown"),
        client_location=payload.get("client_location"),
        sales_manager_name=payload.get("sales_manager_name"),
        sales_manager_contact=payload.get("sales_manager_contact"),
        factory_id=factory_id,
        document_date=_parse_date(payload.get("document_date")),
        production_received_date=date.today(),
        desired_delivery_date=_parse_date(payload.get("desired_delivery_date")),
        final_deadline=_parse_date(payload.get("final_deadline")),
        status=OrderStatus.NEW,
        source=source,
        external_id=external_id,
        sales_payload_json=(
            payload.get("sales_payload_json")
            or (payload if source == OrderSource.SALES_WEBHOOK.value else None)
        ),
        mandatory_qc=payload.get("mandatory_qc", False),
        notes=payload.get("notes"),
    )
    db.add(order)
    db.flush()  # Get order.id

    # 5. Create order items — separate service items from product items
    items_data = payload.get("items", [])
    created_items = []       # (item_orm, item_data_dict) — product items
    service_items_data = []  # raw dicts for service items
    for item_data in items_data:
        # ── Detect service items (stencil design, silkscreen design, color matching) ──
        if is_service_item(item_data):
            service_items_data.append(item_data)
            continue

        # Parse thickness: prefer thickness_mm, accept string "11mm" or number
        _raw_t = item_data.get("thickness", 11.0)
        if isinstance(_raw_t, str):
            _raw_t = float(''.join(c for c in _raw_t if c.isdigit() or c == '.') or '11')
        _thickness_val = Decimal(str(item_data.get("thickness_mm") or _raw_t))

        # Resolve size string — construct from explicit dimensions if absent
        _size_str = item_data.get("size", "")
        if not _size_str:
            _sw = item_data.get("size_width_cm")
            _sh = item_data.get("size_height_cm")
            if _sw and _sh:
                _size_str = f"{_sw:g}x{_sh:g}"

        # qty_sqm — fallback to dimension × qty calculation
        _qty_sqm_raw = item_data.get("quantity_sqm")
        if not _qty_sqm_raw:
            _sw = item_data.get("size_width_cm")
            _sh = item_data.get("size_height_cm")
            if not (_sw and _sh) and _size_str:
                try:
                    from business.kiln.capacity import parse_size as _parse_size
                    _dims = _parse_size(_size_str)
                    _sw, _sh = _dims.get("width_cm"), _dims.get("height_cm")
                except Exception:
                    _sw = _sh = None
            # Support both "quantity_pcs" (PMS native) and "quantity" (Sales)
            _qty_pcs = item_data.get("quantity_pcs") or item_data.get("quantity", 0)
            if _sw and _sh and _qty_pcs:
                _qty_sqm_raw = round((float(_sw) * float(_sh) / 10000) * _qty_pcs, 3)

        # Support both "quantity_pcs" (PMS native) and "quantity" (Sales)
        _final_qty_pcs = item_data.get("quantity_pcs") or item_data.get("quantity", 0)

        item = ProductionOrderItem(
            order_id=order.id,
            color=item_data.get("color", ""),
            color_2=item_data.get("color_2"),
            size=_size_str,
            application=item_data.get("application"),
            finishing=item_data.get("finishing"),
            thickness=_thickness_val,
            quantity_pcs=_final_qty_pcs,
            quantity_sqm=Decimal(str(_qty_sqm_raw)) if _qty_sqm_raw else None,
            collection=item_data.get("collection"),
            application_type=item_data.get("application_type"),
            place_of_application=item_data.get("place_of_application"),
            product_type=item_data.get("product_type", ProductType.TILE.value),
            # Shape & dimension data (may come from Sales app)
            shape=item_data.get("shape"),
            length_cm=item_data.get("length_cm"),
            width_cm=item_data.get("width_cm"),
            depth_cm=item_data.get("depth_cm"),
            bowl_shape=item_data.get("bowl_shape"),
            shape_dimensions=item_data.get("shape_dimensions"),
            edge_profile=item_data.get("edge_profile"),
            edge_profile_sides=item_data.get("edge_profile_sides"),
            edge_profile_notes=item_data.get("edge_profile_notes"),
        )
        db.add(item)
        db.flush()

        # Store Sales-only fields as transient attributes for process_order_item()
        item._sales_application_collection = item_data.get("application_collection")
        item._sales_application_method = item_data.get("application_method")
        item._sales_colors_for_splashing = item_data.get("colors_for_splashing")
        item._sales_is_additional_item = item_data.get("is_additional_item")
        item._sales_description = item_data.get("description")

        created_items.append((item, item_data))

    # 6. Process product items → positions
    positions = []
    for item, _item_data in created_items:
        try:
            position = process_order_item(db, order, item)
            if position:
                positions.append(position)
        except Exception as e:
            logger.error(
                "process_order_item failed for order %s item %s: %s",
                order.order_number, item.id, e,
            )

    # 7. Create Tasks for service items (stencil design, silkscreen design, color matching)
    created_service_tasks = []
    for svc_data in service_items_data:
        task_type = detect_service_task_type(svc_data) or TaskType.STENCIL_ORDER
        # Create a lightweight OrderItem record for audit trail
        svc_item = ProductionOrderItem(
            order_id=order.id,
            color=svc_data.get("color", ""),
            color_2=svc_data.get("color_2"),
            application=svc_data.get("application"),
            quantity_pcs=svc_data.get("quantity_pcs") or svc_data.get("quantity", 0),
            product_type=svc_data.get("product_type", ProductType.TILE.value),
        )
        db.add(svc_item)
        db.flush()

        task = Task(
            factory_id=order.factory_id,
            type=task_type,
            status=TaskStatus.PENDING,
            assigned_role=UserRole.PRODUCTION_MANAGER,
            related_order_id=order.id,
            blocking=True,
            description=(
                f"[{task_type.value.replace('_', ' ').title()}] "
                f"Order {order.order_number}: "
                f"{svc_data.get('application', '')} — "
                f"{svc_data.get('color', '')} "
                f"{'/ ' + svc_data.get('color_2') if svc_data.get('color_2') else ''}"
            ).strip(),
            priority=10,
            metadata_json={
                "order_item_id": str(svc_item.id),
                "application": svc_data.get("application"),
                "color": svc_data.get("color"),
                "color_2": svc_data.get("color_2"),
                "source": f"{source}_auto",
            },
        )
        db.add(task)
        db.flush()
        created_service_tasks.append(task)
        logger.info("Created service task %s for order %s", task_type.value, order.order_number)

    # 8. Link service tasks to matching positions (same order)
    for task in created_service_tasks:
        if task.type in (TaskType.STENCIL_ORDER, TaskType.SILK_SCREEN_ORDER):
            for pos in positions:
                _pos_status = pos.status.value if hasattr(pos.status, "value") else str(pos.status)
                if _pos_status == PositionStatus.AWAITING_STENCIL_SILKSCREEN.value:
                    task.related_position_id = pos.id
                    break
        elif task.type == TaskType.COLOR_MATCHING:
            for pos in positions:
                _pos_status = pos.status.value if hasattr(pos.status, "value") else str(pos.status)
                if _pos_status == PositionStatus.AWAITING_COLOR_MATCHING.value:
                    task.related_position_id = pos.id
                    break

    # 9. Upfront scheduling (TOC/DBR backward scheduling)
    #    Calculate planned dates for every position immediately so Sales
    #    can see a real-time production plan.
    #    Skip when caller handles scheduling separately (e.g. webhook with deferred estimation).
    if not skip_scheduling:
        try:
            from business.services.production_scheduler import schedule_order
            schedule_order(db, order)
        except Exception as e:
            logger.warning("Failed to schedule order %s: %s", order.order_number, e)

    # 10. Update order status
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

    # Log order status change
    if order.status != old_status:
        try:
            db.add(ProductionOrderStatusLog(
                order_id=order.id,
                old_status=old_status,
                new_status=order.status,
            ))
        except Exception as e:
            logger.warning("Failed to log order status change: %s", e)

    db.commit()

    # 11. Notify PM (best-effort)
    try:
        from business.services.notifications import notify_pm
        notify_pm(
            db=db,
            factory_id=factory_id,
            type="status_change",
            title=f"New order: {order.order_number}",
            message=f"Client: {order.client}, {len(positions)} positions",
            related_entity_type="order",
            related_entity_id=order.id,
        )
    except Exception as e:
        logger.warning(f"Failed to notify PM: {e}")

    result = {
        "status": "created",
        "order_id": str(order.id),
        "order_number": order.order_number,
        "positions_count": len(positions),
    }
    if return_order:
        result["_order"] = order
    return result


# ────────────────────────────────────────────────────────────────
# §1  Factory assignment
# ────────────────────────────────────────────────────────────────

def assign_factory(db: Session, client_location: str) -> Factory:
    """
    Auto-assign factory by client region.

    Priority:
    1. Single active factory → always use it (skip all matching)
    2. Region-based keyword matching (bali/java keywords)
    3. Load balancing: factory with fewest active positions
    """
    # Get all active factories
    factories = db.query(Factory).filter(Factory.is_active.is_(True)).all()
    if not factories:
        raise ValueError(
            "No active factories available. Deactivate at least one factory or "
            "activate an existing one before creating orders."
        )

    # Single active factory → always use it (handles disabled-factory fallback:
    # if Bali is disabled → Java only; if Java disabled → Bali only)
    if len(factories) == 1:
        return factories[0]

    # Multiple active factories: try region-based matching
    location_lower = (client_location or "").lower()

    bali_keywords = {"bali", "denpasar", "kuta", "ubud", "seminyak", "canggu",
                     "lombok", "nusa penida", "nusa lembongan"}
    java_keywords = {"java", "jakarta", "surabaya", "bandung", "semarang", "yogyakarta"}

    for keyword in bali_keywords:
        if keyword in location_lower:
            # Only match active factories
            factory = db.query(Factory).filter(
                Factory.name.ilike("%bali%"),
                Factory.is_active.is_(True),
            ).first()
            if factory:
                return factory

    for keyword in java_keywords:
        if keyword in location_lower:
            # Only match active factories
            factory = db.query(Factory).filter(
                Factory.name.ilike("%java%"),
                Factory.is_active.is_(True),
            ).first()
            if factory:
                return factory

    # Load balancing: factory with fewest active positions
    best = None
    min_load = float("inf")
    terminal = {PositionStatus.SHIPPED, PositionStatus.CANCELLED, PositionStatus.READY_FOR_SHIPMENT}

    for f in factories:
        count = (
            db.query(func.count(OrderPosition.id))
            .filter(
                OrderPosition.factory_id == f.id,
                OrderPosition.status.notin_([s.value for s in terminal]),
            )
            .scalar()
        ) or 0
        if count < min_load:
            min_load = count
            best = f

    return best


# ────────────────────────────────────────────────────────────────
# §1  Factory lead time estimation
# ────────────────────────────────────────────────────────────────

def estimate_factory_lead_time(db: Session, factory_id: UUID) -> dict:
    """
    Estimate current lead time for a factory.

    Returns:
    - active_positions: count of in-progress positions
    - avg_cycle_days: average days from PLANNED to SHIPPED (last 30 orders)
    - estimated_queue_days: rough estimate based on kiln throughput
    """
    now = datetime.now(timezone.utc)

    # Active positions count
    terminal = {PositionStatus.SHIPPED.value, PositionStatus.CANCELLED.value}
    active_count = (
        db.query(func.count(OrderPosition.id))
        .filter(
            OrderPosition.factory_id == factory_id,
            OrderPosition.status.notin_(list(terminal)),
        )
        .scalar()
    ) or 0

    # Average cycle time from recent shipped positions
    thirty_days_ago = now - timedelta(days=30)
    shipped = (
        db.query(OrderPosition)
        .filter(
            OrderPosition.factory_id == factory_id,
            OrderPosition.status == PositionStatus.SHIPPED.value,
            OrderPosition.updated_at >= thirty_days_ago,
        )
        .all()
    )

    avg_cycle_days = 0
    if shipped:
        total_days = sum(
            (p.updated_at - p.created_at).total_seconds() / 86400
            for p in shipped
            if p.updated_at and p.created_at
        )
        avg_cycle_days = round(total_days / len(shipped), 1)

    return {
        "factory_id": str(factory_id),
        "active_positions": active_count,
        "avg_cycle_days": avg_cycle_days,
        "estimated_queue_days": max(7, round(active_count / 20, 0)),  # rough: ~20 pos/day throughput
    }


# ────────────────────────────────────────────────────────────────
# §2  Process individual order item → position
# ────────────────────────────────────────────────────────────────

def process_order_item(
    db: Session,
    order: ProductionOrder,
    item: ProductionOrderItem,
) -> Optional[OrderPosition]:
    """
    Recipe lookup → position creation → blocking tasks + material check.

    STOCK: If is_stock_collection(item.collection), create position with
    status=TRANSFERRED_TO_SORTING and skip recipe lookup, material reservation,
    and blocking tasks. Stock items are pre-made.
    """
    # Determine initial status
    if is_stock_collection(item.collection):
        initial_status = PositionStatus.TRANSFERRED_TO_SORTING
    else:
        initial_status = PositionStatus.PLANNED

    # Lookup recipe by matching attributes
    recipe = _find_recipe(db, item)

    # Auto-assign sequential position_number within this order
    from sqlalchemy import func as _sqla_func
    _max_pn = db.query(_sqla_func.max(OrderPosition.position_number)).filter(
        OrderPosition.order_id == order.id,
        OrderPosition.parent_position_id.is_(None),
    ).scalar()
    _next_pn = (_max_pn or 0) + 1

    # Resolve shape from item data (Sales app sends shape/dimensions)
    _item_shape = getattr(item, "shape", None)
    _shape_val = ShapeType(_item_shape) if _item_shape and _item_shape in [s.value for s in ShapeType] else ShapeType.RECTANGLE

    # Create position
    position = OrderPosition(
        order_id=order.id,
        order_item_id=item.id,
        factory_id=order.factory_id,
        status=initial_status,
        quantity=item.quantity_pcs,
        quantity_sqm=item.quantity_sqm,
        color=item.color,
        color_2=item.color_2,
        size=item.size,
        application=item.application,
        finishing=item.finishing,
        collection=item.collection,
        application_type=item.application_type,
        place_of_application=item.place_of_application,
        product_type=item.product_type or ProductType.TILE,
        shape=_shape_val,
        length_cm=getattr(item, "length_cm", None),
        width_cm=getattr(item, "width_cm", None),
        depth_cm=getattr(item, "depth_cm", None),
        bowl_shape=getattr(item, "bowl_shape", None),
        shape_dimensions=getattr(item, "shape_dimensions", None),
        edge_profile=getattr(item, "edge_profile", None),
        edge_profile_sides=getattr(item, "edge_profile_sides", None),
        edge_profile_notes=getattr(item, "edge_profile_notes", None),
        thickness_mm=item.thickness or Decimal("11.0"),
        recipe_id=recipe.id if recipe else None,
        mandatory_qc=order.mandatory_qc,
        firing_round=1,
        position_number=_next_pn,
    )
    db.add(position)
    db.flush()

    # Calculate glazeable surface area (shape-aware)
    from business.services.surface_area import calculate_glazeable_sqm_for_position
    _glazeable = calculate_glazeable_sqm_for_position(db, position)
    if _glazeable is not None:
        position.glazeable_sqm = _glazeable

    # Store application collection and method from Sales webhook.
    # Sales sends: application="SS"/"BS"/"Stencil"/etc. → this IS the application method.
    # Sales sends: collection="Authentic"/"Exclusive"/etc. → this IS the application collection.
    _app_collection = (
        getattr(item, '_sales_application_collection', None)
        or getattr(item, 'application_collection', None)
        or getattr(item, 'collection', None)
    )

    # Map Sales "application" field → application_method_code
    # Sales uses: SS, S, BS, SB, Splashing, Stencil, Silkscreen, Gold, Raku
    _raw_app = getattr(item, 'application', None) or ''
    APPLICATION_METHOD_MAP = {
        'ss': 'ss', 's': 's', 'bs': 'bs', 'sb': 'sb',
        'splashing': 'splashing', 'stencil': 'stencil',
        'silkscreen': 'silk_screen', 'silk_screen': 'silk_screen',
        'gold': 'gold', 'raku': 'raku',
    }
    _app_method = (
        getattr(item, '_sales_application_method', None)
        or getattr(item, 'application_method', None)
        or APPLICATION_METHOD_MAP.get(_raw_app.strip().lower())
        or getattr(item, 'application_type', None)
    )

    if hasattr(position, 'application_collection_code') and _app_collection:
        _acc_val = _app_collection.strip().lower()
        position.application_collection_code = _acc_val
        if _acc_val not in [e.value for e in ApplicationCollectionCode]:
            logger.warning(
                "UNKNOWN_COLLECTION | order=%s position=%s | application_collection_code='%s' not in enum",
                order.order_number, position.id, _acc_val,
            )
    if hasattr(position, 'application_method_code') and _app_method:
        _amc_val = _app_method.strip().lower()
        position.application_method_code = _amc_val
        if _amc_val not in [e.value for e in ApplicationMethodCode]:
            logger.warning(
                "UNKNOWN_METHOD | order=%s position=%s | application_method_code='%s' not in enum",
                order.order_number, position.id, _amc_val,
            )

    # Warn if edge_profile from Sales is unknown
    _edge_val = getattr(position, 'edge_profile', None)
    if _edge_val and _edge_val not in [e.value for e in EdgeProfileType]:
        logger.warning(
            "UNKNOWN_EDGE_PROFILE | order=%s position=%s | edge_profile='%s' not in enum",
            order.order_number, position.id, _edge_val,
        )

    # Auto-detect Exclusive collection if not explicitly set
    if not _app_collection or _app_collection.strip().lower() == 'authentic':
        if _auto_detect_exclusive(db, position, item):
            if hasattr(position, 'application_collection_code'):
                position.application_collection_code = 'exclusive'
            logger.info(
                "AUTO_EXCLUSIVE | order=%s position=%s | auto-detected as Exclusive "
                "(non-base color or non-base size)",
                order.order_number, position.id,
            )

    # Validate application method against collection rules
    _final_collection = getattr(position, 'application_collection_code', None)
    _final_method = getattr(position, 'application_method_code', None)
    if not _validate_application_method(db, _final_collection, _final_method):
        logger.warning(
            "INVALID_METHOD | order=%s position=%s | method='%s' not allowed for collection='%s'",
            order.order_number, position.id, _final_method, _final_collection,
        )

    # Calculate defect margin (2D: glaze + product type coefficients)
    from business.services.defect_coefficient import calculate_production_quantity_with_defects
    calculate_production_quantity_with_defects(db, position)

    # Stock items: done, no further processing
    if is_stock_collection(item.collection):
        return position

    # Check if recipe exists
    if not recipe:
        position.status = PositionStatus.AWAITING_RECIPE
        # Create task for recipe configuration
        task = Task(
            factory_id=order.factory_id,
            type=TaskType.RECIPE_CONFIGURATION,
            status=TaskStatus.PENDING,
            related_order_id=order.id,
            related_position_id=position.id,
            blocking=True,
            description=f"Configure recipe for: {item.collection} / {item.color} / {item.size}",
        )
        db.add(task)
        db.flush()
        return position

    # Check blocking tasks (stencil, silkscreen, color matching)
    check_blocking_tasks(db, order, position, item)

    # ── Consumption rate check ──────────────────────────────────
    # For each application method (e.g. BS = Brush engobe + Spray glaze),
    # verify the recipe has the required consumption rate.
    # If missing → create a blocking task for PM to measure.
    _consumption_blocked = _check_consumption_rates(db, order, position, recipe)
    if _consumption_blocked:
        return position  # skip material reservation until rate is measured

    # Size resolution — match position dimensions against sizes reference table.
    # Must happen BEFORE material reservation because we need to know which stone
    # to reserve. If size can't be determined, block the position.
    from business.services.size_resolution import (
        resolve_size_for_position,
        create_size_resolution_task,
    )
    from business.services.notifications import notify_pm

    size_result = resolve_size_for_position(db, position)
    if size_result.resolved:
        position.size_id = size_result.size_id

        # If size was auto-created, notify PM for approval (non-blocking)
        if size_result.reason == "auto_created":
            _auto_size = size_result.candidates[0] if size_result.candidates else {}
            _approval_task = Task(
                factory_id=order.factory_id,
                type=TaskType.SIZE_RESOLUTION,
                status=TaskStatus.PENDING,
                assigned_role=UserRole.PRODUCTION_MANAGER,
                related_order_id=order.id,
                related_position_id=position.id,
                blocking=False,
                description=(
                    f"Approve auto-created size '{_auto_size.get('name', '?')}' "
                    f"({_auto_size.get('width_mm', '?')}x{_auto_size.get('height_mm', '?')} mm) "
                    f"from order {order.order_number}"
                ),
                metadata_json=__import__('json').dumps({
                    "reason": "auto_created",
                    "auto_created_size_id": str(size_result.size_id),
                    "candidates": size_result.candidates,
                    "position_size_string": position.size,
                }),
            )
            db.add(_approval_task)
            db.flush()
            notify_pm(
                db=db,
                factory_id=order.factory_id,
                type="task_assigned",
                title=f"New size auto-created: {_auto_size.get('name', position.size)}",
                message=(
                    f"Order {order.order_number}: auto-created size "
                    f"{_auto_size.get('width_mm', '?')}x{_auto_size.get('height_mm', '?')} mm. "
                    f"Please review and approve."
                ),
                related_entity_type="position",
                related_entity_id=position.id,
            )
    else:
        # Only block if position is still in PLANNED state
        # (it might already be blocked by stencil/silkscreen/color matching)
        if position.status == PositionStatus.PLANNED:
            position.status = PositionStatus.AWAITING_SIZE_CONFIRMATION

        create_size_resolution_task(
            db=db,
            position=position,
            order_id=order.id,
            factory_id=order.factory_id,
            reason=size_result.reason,
            candidates=size_result.candidates,
        )
        notify_pm(
            db=db,
            factory_id=order.factory_id,
            type="task_assigned",
            title=f"Size resolution needed: {position.size}",
            message=f"Order {order.order_number}, position {position.size} — "
                    f"cannot auto-determine stone size ({size_result.reason})",
            related_entity_type="position",
            related_entity_id=position.id,
        )
        # Don't proceed to material reservation if size is unresolved
        return position

    # Material reservation check
    # Recipe is guaranteed to exist here (no-recipe returns above).
    # Stock collections already returned above.
    from business.services.material_reservation import (
        reserve_materials_for_position,
        create_auto_purchase_request,
        check_material_availability_smart,
    )
    result = reserve_materials_for_position(db, position, recipe, order.factory_id)
    if result.shortages:
        # Smart blocking: check if materials are already ordered and will
        # arrive in time. Only block with INSUFFICIENT_MATERIALS if material
        # is truly unavailable (not ordered, or ordered but arriving too late).
        #
        # Planned glazing date approximation: use order.desired_delivery_date
        # minus a processing buffer (glazing happens before delivery).
        # If no date available, smart check defaults to "don't block if ordered".
        _glazing_date = None
        if order.desired_delivery_date:
            # Glazing must happen before delivery; approximate glazing date
            # as desired_delivery minus 7 days (firing + sorting + packing).
            _glazing_date = order.desired_delivery_date - timedelta(days=7)
        elif order.final_deadline:
            _glazing_date = order.final_deadline - timedelta(days=7)

        should_block = False
        truly_missing = []  # shortages that are NOT covered by pending orders

        for shortage in result.shortages:
            smart_result = check_material_availability_smart(
                db=db,
                material_id=shortage.material_id,
                factory_id=order.factory_id,
                required_qty=shortage.required,
                effective_available=shortage.available,
                planned_glazing_date=_glazing_date,
                buffer_days=3,
            )
            if not smart_result.available:
                should_block = True
                truly_missing.append(shortage)
                logger.warning(
                    "MATERIAL_SHORTAGE | order=%s position=%s | %s: %s "
                    "(deficit=%.3f, ordered=%.3f)",
                    order.order_number, position.id,
                    shortage.material_name, smart_result.reason,
                    float(shortage.deficit), float(smart_result.ordered_qty),
                )
            else:
                logger.info(
                    "MATERIAL_COVERED | order=%s position=%s | %s: %s "
                    "(deficit=%.3f, ordered=%.3f — will arrive in time)",
                    order.order_number, position.id,
                    shortage.material_name, smart_result.reason,
                    float(shortage.deficit), float(smart_result.ordered_qty),
                )

        # Only override status to INSUFFICIENT_MATERIALS if position is still
        # in PLANNED state AND at least one material is truly missing.
        # If it's already blocked (awaiting_stencil_silkscreen,
        # awaiting_color_matching), keep the blocking status.
        if should_block and position.status == PositionStatus.PLANNED:
            position.status = PositionStatus.INSUFFICIENT_MATERIALS

        # Always create auto purchase requests for shortages that don't have
        # pending orders yet (truly_missing). If all shortages are covered,
        # skip auto-purchase creation.
        if truly_missing:
            create_auto_purchase_request(db, order.factory_id, truly_missing, order)

    return position


# ────────────────────────────────────────────────────────────────
# §2b  Consumption rate check
# ────────────────────────────────────────────────────────────────

# Which consumption rates are required for each application method.
# Key letters: S=spray, B=brush.
# E.g. BS = first letter B (engobe brush), second letter S (glaze spray)
# → needs both brush and spray rates.
_METHOD_REQUIRED_RATES: dict[str, list[str]] = {
    'ss': ['spray'],                # spray engobe + spray glaze → spray
    's':  ['spray'],                # spray glaze only → spray
    'bs': ['brush', 'spray'],       # brush engobe + spray glaze
    'sb': ['spray', 'brush'],       # spray engobe + brush glaze
    'splashing': ['spray'],         # spray + splash
    'stencil': ['spray'],           # spray through stencil
    'silk_screen': ['spray'],       # spray + silk screen
    'gold': ['spray', 'brush'],     # 1st firing SS, 2nd brush gold
    'raku': ['spray'],              # spray, raku kiln
}


def _check_consumption_rates(
    db: Session,
    order,
    position,
    recipe,
) -> bool:
    """Check if recipe has required consumption rates for the position's method.

    Returns True if the position was blocked (missing rates), False if OK.
    """
    if not recipe:
        return False  # no recipe → already handled above

    method = getattr(position, 'application_method_code', None)
    if not method:
        return False  # no method set → nothing to check

    required = _METHOD_REQUIRED_RATES.get(method.strip().lower(), [])
    if not required:
        return False

    missing_methods: list[str] = []
    for rate_type in required:
        if rate_type == 'spray' and not recipe.consumption_spray_ml_per_sqm:
            missing_methods.append('spray')
        elif rate_type == 'brush' and not recipe.consumption_brush_ml_per_sqm:
            missing_methods.append('brush')

    if not missing_methods:
        return False  # all rates present

    # Deduplicate (e.g. 'spray' might appear once only)
    missing_methods = list(dict.fromkeys(missing_methods))

    missing_label = ' & '.join(m.capitalize() for m in missing_methods)
    recipe_name = getattr(recipe, 'name', 'Unknown')

    logger.warning(
        "CONSUMPTION_MISSING | order=%s position=%s | recipe=%s method=%s "
        "missing=[%s]",
        order.order_number, position.id, recipe_name, method,
        ', '.join(missing_methods),
    )

    # Block position if still PLANNED
    if position.status == PositionStatus.PLANNED:
        position.status = PositionStatus.AWAITING_CONSUMPTION_DATA

    # Create blocking task for PM
    task = Task(
        factory_id=order.factory_id,
        type=TaskType.CONSUMPTION_MEASUREMENT,
        status=TaskStatus.PENDING,
        assigned_role=UserRole.PRODUCTION_MANAGER,
        related_order_id=order.id,
        related_position_id=position.id,
        blocking=True,
        description=(
            f"Measure {missing_label} consumption rate for \"{recipe_name}\" "
            f"(method: {method.upper()})"
        ),
        metadata_json=__import__('json').dumps({
            "recipe_id": str(recipe.id),
            "recipe_name": recipe_name,
            "application_method": method,
            "missing_rates": missing_methods,
            "order_number": order.order_number,
            "position_color": position.color,
            "position_size": position.size,
        }),
    )
    db.add(task)
    db.flush()

    # Notify PM
    from business.services.notifications import notify_pm
    notify_pm(
        db=db,
        factory_id=order.factory_id,
        type="task_assigned",
        title=f"Consumption measurement needed: {recipe_name}",
        message=(
            f"Order {order.order_number}: recipe \"{recipe_name}\" is missing "
            f"{missing_label} consumption rate (method {method.upper()}). "
            f"Please measure and enter the rate."
        ),
        related_entity_type="position",
        related_entity_id=position.id,
    )

    return True


# ────────────────────────────────────────────────────────────────
# §3  Blocking task detection
# ────────────────────────────────────────────────────────────────

def check_blocking_tasks(
    db: Session,
    order: ProductionOrder,
    position: OrderPosition,
    item: ProductionOrderItem,
) -> None:
    """
    Create blocking tasks for stencil, silkscreen, color matching.

    Rules:
    - collection contains "stencil" → STENCIL_ORDER task
    - collection contains "silkscreen"/"silk screen" → SILK_SCREEN_ORDER task
    - collection contains "custom" or color_2 is set → COLOR_MATCHING task

    Service Blocking Timing (2026-03-19):
    Tasks are always created so the PM knows what's needed. However, the
    position is only blocked (status changed) when the service lead time is
    urgent relative to the planned glazing date.

    If planned_glazing_date is not yet assigned (position just created,
    scheduling runs after), the service is registered as a pending task
    but blocking is deferred. APScheduler's check_pending_service_blocks
    will re-evaluate daily once glazing dates are assigned.
    """
    from business.services.service_blocking import should_block_for_service

    collection_lower = (item.collection or "").lower()
    app_type_lower = (item.application_type or "").lower()
    created_blocking = False

    # Stencil check
    if "stencil" in collection_lower or "stencil" in app_type_lower:
        task = Task(
            factory_id=order.factory_id,
            type=TaskType.STENCIL_ORDER,
            status=TaskStatus.PENDING,
            assigned_role=UserRole.PRODUCTION_MANAGER,
            related_order_id=order.id,
            related_position_id=position.id,
            blocking=True,
            description=f"Order stencil for: {item.collection} / {item.color}",
        )
        db.add(task)
        # Timing check: only block position if lead time is urgent now
        _should_block, _days_left = should_block_for_service(db, position, 'stencil')
        if _should_block:
            position.status = PositionStatus.AWAITING_STENCIL_SILKSCREEN
            created_blocking = True
            logger.info(
                "SERVICE_BLOCK_NOW | order=%s position=%s service=stencil days_left=%d",
                order.order_number, position.id, _days_left,
            )
        else:
            logger.info(
                "SERVICE_BLOCK_DEFERRED | order=%s position=%s service=stencil "
                "(no glazing date yet or not urgent)",
                order.order_number, position.id,
            )

    # Silkscreen check
    elif "silkscreen" in collection_lower or "silk screen" in collection_lower or "silkscreen" in app_type_lower:
        task = Task(
            factory_id=order.factory_id,
            type=TaskType.SILK_SCREEN_ORDER,
            status=TaskStatus.PENDING,
            assigned_role=UserRole.PRODUCTION_MANAGER,
            related_order_id=order.id,
            related_position_id=position.id,
            blocking=True,
            description=f"Order silkscreen for: {item.collection} / {item.color}",
        )
        db.add(task)
        # Timing check
        _should_block, _days_left = should_block_for_service(db, position, 'silkscreen')
        if _should_block:
            position.status = PositionStatus.AWAITING_STENCIL_SILKSCREEN
            created_blocking = True
            logger.info(
                "SERVICE_BLOCK_NOW | order=%s position=%s service=silkscreen days_left=%d",
                order.order_number, position.id, _days_left,
            )
        else:
            logger.info(
                "SERVICE_BLOCK_DEFERRED | order=%s position=%s service=silkscreen "
                "(no glazing date yet or not urgent)",
                order.order_number, position.id,
            )

    # Color matching check
    if "custom" in collection_lower or item.color_2:
        task = Task(
            factory_id=order.factory_id,
            type=TaskType.COLOR_MATCHING,
            status=TaskStatus.PENDING,
            assigned_role=UserRole.PRODUCTION_MANAGER,
            related_order_id=order.id,
            related_position_id=position.id,
            blocking=True,
            description=f"Color matching: {item.color}" + (f" + {item.color_2}" if item.color_2 else ""),
        )
        db.add(task)
        if not created_blocking:
            # Timing check
            _should_block_cm, _days_left_cm = should_block_for_service(db, position, 'color_matching')
            if _should_block_cm:
                position.status = PositionStatus.AWAITING_COLOR_MATCHING
                logger.info(
                    "SERVICE_BLOCK_NOW | order=%s position=%s service=color_matching days_left=%d",
                    order.order_number, position.id, _days_left_cm,
                )
            else:
                logger.info(
                    "SERVICE_BLOCK_DEFERRED | order=%s position=%s service=color_matching "
                    "(no glazing date yet or not urgent)",
                    order.order_number, position.id,
                )


# ────────────────────────────────────────────────────────────────
# Private helpers
# ────────────────────────────────────────────────────────────────

def _find_recipe(db: Session, item: ProductionOrderItem) -> Optional[Recipe]:
    """
    Find recipe by color name (case-insensitive).

    The 'collection' from Sales (Authentic/Exclusive/etc.) is the APPLICATION
    collection, NOT the recipe's color_collection. Recipes are stored with
    color_collection like "Collection 2025/2026", so we match by color NAME.

    Strategy:
    1. Primary: exact name match on Recipe.name == item.color (case-insensitive)
    2. Fallback with optional JSONB filters (progressive relaxation)
    3. Fuzzy fallback: normalize both sides and retry
    """
    log = logging.getLogger(__name__)

    color = getattr(item, 'color', None)
    if not color:
        log.warning("No color on item id=%s — cannot find recipe", item.id)
        return None

    color_stripped = color.strip()

    # ── Primary: exact name match (case-insensitive), active recipes only ──
    recipe = db.query(Recipe).filter(
        Recipe.is_active.is_(True),
        func.lower(Recipe.name) == func.lower(color_stripped),
    ).first()

    if recipe:
        log.info(
            "Recipe matched (color name exact): '%s' → recipe '%s' (id=%s)",
            color_stripped, recipe.name, recipe.id,
        )
        return recipe

    # ── Secondary: try with optional JSONB filters for disambiguation ──
    # This handles cases where multiple recipes share a color name but differ
    # in finishing, size, shape, etc.
    optional_filters: list[tuple[str, object]] = []

    if item.thickness:
        optional_filters.append((
            "thickness",
            lambda q, v=str(item.thickness): q.filter(
                Recipe.glaze_settings["thickness"].astext == v
            ),
        ))
    if getattr(item, "shape", None):
        optional_filters.append((
            "shape",
            lambda q, v=str(item.shape): q.filter(
                Recipe.glaze_settings["shape"].astext == v
            ),
        ))
    if getattr(item, "size", None):
        optional_filters.append((
            "size",
            lambda q, v=item.size: q.filter(
                Recipe.glaze_settings["size"].astext == v
            ),
        ))
    if item.finishing:
        optional_filters.append((
            "finishing_type",
            lambda q, v=item.finishing: q.filter(
                Recipe.glaze_settings["finishing_type"].astext == v
            ),
        ))
    if item.place_of_application:
        optional_filters.append((
            "place_of_application",
            lambda q, v=item.place_of_application: q.filter(
                Recipe.glaze_settings["place_of_application"].astext == v
            ),
        ))

    # Progressive relaxation: try all optional filters, then drop least-specific
    if optional_filters:
        for drop_count in range(len(optional_filters) + 1):
            active = optional_filters[drop_count:]
            active_labels = [label for label, _ in active]

            base = db.query(Recipe).filter(
                Recipe.is_active.is_(True),
                func.lower(Recipe.name) == func.lower(color_stripped),
            )
            q = base
            for _, apply_filter in active:
                q = apply_filter(q)

            results = q.all()
            if len(results) == 1:
                log.info(
                    "Recipe matched (color + JSONB): '%s' → '%s' — fields: %s",
                    color_stripped, results[0].name,
                    ", ".join(["color"] + active_labels),
                )
                return results[0]
            if len(results) > 1:
                log.info(
                    "Recipe matched (first of %d, color + JSONB): '%s' → '%s' — fields: %s",
                    len(results), color_stripped, results[0].name,
                    ", ".join(["color"] + active_labels),
                )
                return results[0]

    # ── Fuzzy fallback: normalize (strip "glaze"/"crackle" suffixes, trim) ──
    import re
    normalized = re.sub(r'\s+(glaze|crackle|matt|matte|glossy)$', '', color_stripped, flags=re.IGNORECASE).strip()
    if normalized.lower() != color_stripped.lower():
        recipe = db.query(Recipe).filter(
            Recipe.is_active.is_(True),
            func.lower(Recipe.name) == normalized.lower(),
        ).first()
        if recipe:
            log.info(
                "Recipe matched (fuzzy normalized): '%s' → '%s' (id=%s)",
                color_stripped, recipe.name, recipe.id,
            )
            return recipe

    # ── Also try if recipe name contains the color (partial match) ──
    recipe = db.query(Recipe).filter(
        Recipe.is_active.is_(True),
        func.lower(Recipe.name).contains(color_stripped.lower()),
    ).first()
    if recipe:
        log.info(
            "Recipe matched (partial contains): '%s' → '%s' (id=%s)",
            color_stripped, recipe.name, recipe.id,
        )
        return recipe

    log.warning(
        "No recipe found for item color='%s' (collection='%s')",
        color_stripped, item.collection,
    )
    return None


def _auto_detect_exclusive(db: Session, position, item) -> bool:
    """
    Auto-detect if position should be in Exclusive collection.

    Rule: if tile + (non-base color OR non-base size) → Exclusive

    Base sizes: is_custom=False in sizes table (5x20, 10x10, 10x20, 10x40, 20x20, 20x40)
    Base colors: is_basic=True in colors table
    """
    # Only tiles can be auto-Exclusive
    _pt = getattr(position, 'product_type', None)
    _pt_val = _pt.value if hasattr(_pt, 'value') else str(_pt or '')
    if _pt_val and _pt_val != 'tile':
        return False

    # Check if color is base
    color_name = getattr(item, 'color', '') or ''
    if color_name:
        from api.models import Color
        color_record = db.query(Color).filter(
            func.lower(Color.name) == func.lower(color_name.strip())
        ).first()
        is_base_color = color_record.is_basic if color_record else False
    else:
        is_base_color = False

    # Check if size is base (standard)
    from api.models import Size
    size_str = getattr(item, 'size', '') or ''
    if size_str:
        size_record = db.query(Size).filter(Size.name == size_str).first()
        is_base_size = (size_record is not None and not size_record.is_custom)
    else:
        is_base_size = False

    # Non-base color OR non-base size → Exclusive
    if not is_base_color or not is_base_size:
        return True

    return False


def _validate_application_method(db, collection_code, method_code) -> bool:
    """Validate that the application method is allowed for the collection.

    Returns True if valid or if validation cannot be performed (missing data,
    unknown collection, or ApplicationCollection table not yet available).
    """
    if not collection_code or not method_code:
        return True  # Skip validation if not provided

    try:
        from api.models import ApplicationCollection
    except ImportError:
        return True  # Model not yet created by Agent 1

    coll = db.query(ApplicationCollection).filter(
        ApplicationCollection.code == collection_code.strip().lower()
    ).first()

    if not coll:
        return True  # Unknown collection, allow

    if getattr(coll, 'any_method', False):
        return True  # Exclusive/TopTable/WashBasin allow any method

    allowed = getattr(coll, 'allowed_methods', None) or []
    return method_code.strip().lower() in allowed


def _generate_order_number(db: Session) -> str:
    """Generate a sequential order number: MJ-YYYYMMDD-NNN."""
    today = date.today()
    prefix = f"MJ-{today.strftime('%Y%m%d')}"

    # Count orders today
    count = (
        db.query(func.count(ProductionOrder.id))
        .filter(ProductionOrder.order_number.like(f"{prefix}%"))
        .scalar()
    ) or 0

    return f"{prefix}-{count + 1:03d}"


def _parse_date(value) -> Optional[date]:
    """Parse date from string or return None."""
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value)).date()
    except (ValueError, TypeError):
        return None
