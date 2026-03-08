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
)
from api.enums import (
    PositionStatus,
    OrderStatus,
    OrderSource,
    TaskType,
    TaskStatus,
    ProductType,
    ShapeType,
    is_stock_collection,
)

logger = logging.getLogger("moonjar.order_intake")


# ────────────────────────────────────────────────────────────────
# §1  Main entry point
# ────────────────────────────────────────────────────────────────

def process_incoming_order(db: Session, payload: dict, source: str) -> dict:
    """
    Entry point: webhook/PDF/manual → order + positions.

    Steps:
    1. Idempotency check (webhook only)
    2. Check if order already exists → create change request
    3. Create new production order
    4. Auto-assign factory
    5. Create order items
    6. Process each item → create positions
    7. Notify PM
    """
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
    external_id = payload.get("external_id")
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
    factory_id = payload.get("factory_id")
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
        sales_payload_json=payload if source == OrderSource.SALES_WEBHOOK.value else None,
        mandatory_qc=payload.get("mandatory_qc", False),
        notes=payload.get("notes"),
    )
    db.add(order)
    db.flush()  # Get order.id

    # 5. Create order items
    items_data = payload.get("items", [])
    created_items = []
    for item_data in items_data:
        item = ProductionOrderItem(
            order_id=order.id,
            color=item_data.get("color", ""),
            color_2=item_data.get("color_2"),
            size=item_data.get("size", ""),
            application=item_data.get("application"),
            finishing=item_data.get("finishing"),
            thickness=Decimal(str(item_data.get("thickness", 11.0))),
            quantity_pcs=item_data.get("quantity_pcs", 0),
            quantity_sqm=Decimal(str(item_data.get("quantity_sqm", 0))) if item_data.get("quantity_sqm") else None,
            collection=item_data.get("collection"),
            application_type=item_data.get("application_type"),
            place_of_application=item_data.get("place_of_application"),
            product_type=item_data.get("product_type", ProductType.TILE.value),
        )
        db.add(item)
        db.flush()
        created_items.append(item)

    # 6. Process each item → positions
    positions = []
    for item in created_items:
        position = process_order_item(db, order, item)
        if position:
            positions.append(position)

    # 7. Update order status
    if any(
        p.status == PositionStatus.INSUFFICIENT_MATERIALS
        or p.status == PositionStatus.AWAITING_RECIPE
        or p.status == PositionStatus.AWAITING_STENCIL_SILKSCREEN
        or p.status == PositionStatus.AWAITING_COLOR_MATCHING
        for p in positions
    ):
        order.status = OrderStatus.NEW
    else:
        order.status = OrderStatus.IN_PRODUCTION

    db.commit()

    # 8. Notify PM (best-effort)
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

    return {
        "status": "created",
        "order_id": str(order.id),
        "order_number": order.order_number,
        "positions_count": len(positions),
    }


# ────────────────────────────────────────────────────────────────
# §1  Factory assignment
# ────────────────────────────────────────────────────────────────

def assign_factory(db: Session, client_location: str) -> Factory:
    """
    Auto-assign factory by client region.

    Logic:
    - If client_location contains "bali"/"denpasar" → Bali factory
    - If "java"/"jakarta"/"surabaya" → Java factory
    - Default: factory with fewer active positions (load balancing)
    """
    location_lower = (client_location or "").lower()

    # Region-based matching
    bali_keywords = {"bali", "denpasar", "kuta", "ubud", "seminyak", "canggu"}
    java_keywords = {"java", "jakarta", "surabaya", "bandung", "semarang", "yogyakarta"}

    for keyword in bali_keywords:
        if keyword in location_lower:
            factory = db.query(Factory).filter(Factory.name.ilike("%bali%")).first()
            if factory:
                return factory

    for keyword in java_keywords:
        if keyword in location_lower:
            factory = db.query(Factory).filter(Factory.name.ilike("%java%")).first()
            if factory:
                return factory

    # Fallback: factory with least active positions (load balancing)
    factories = db.query(Factory).all()
    if not factories:
        raise ValueError("No factories configured in the system")

    if len(factories) == 1:
        return factories[0]

    # Count active (non-terminal) positions per factory
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
        thickness_mm=item.thickness or Decimal("11.0"),
        recipe_id=recipe.id if recipe else None,
        mandatory_qc=order.mandatory_qc,
        firing_round=1,
    )
    db.add(position)
    db.flush()

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

    return position


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
    """
    collection_lower = (item.collection or "").lower()
    app_type_lower = (item.application_type or "").lower()
    created_blocking = False

    # Stencil check
    if "stencil" in collection_lower or "stencil" in app_type_lower:
        task = Task(
            factory_id=order.factory_id,
            type=TaskType.STENCIL_ORDER,
            status=TaskStatus.PENDING,
            related_order_id=order.id,
            related_position_id=position.id,
            blocking=True,
            description=f"Order stencil for: {item.collection} / {item.color}",
        )
        db.add(task)
        position.status = PositionStatus.AWAITING_STENCIL_SILKSCREEN
        created_blocking = True

    # Silkscreen check
    elif "silkscreen" in collection_lower or "silk screen" in collection_lower or "silkscreen" in app_type_lower:
        task = Task(
            factory_id=order.factory_id,
            type=TaskType.SILK_SCREEN_ORDER,
            status=TaskStatus.PENDING,
            related_order_id=order.id,
            related_position_id=position.id,
            blocking=True,
            description=f"Order silkscreen for: {item.collection} / {item.color}",
        )
        db.add(task)
        position.status = PositionStatus.AWAITING_STENCIL_SILKSCREEN
        created_blocking = True

    # Color matching check
    if "custom" in collection_lower or item.color_2:
        task = Task(
            factory_id=order.factory_id,
            type=TaskType.COLOR_MATCHING,
            status=TaskStatus.PENDING,
            related_order_id=order.id,
            related_position_id=position.id,
            blocking=True,
            description=f"Color matching: {item.color}" + (f" + {item.color_2}" if item.color_2 else ""),
        )
        db.add(task)
        if not created_blocking:
            position.status = PositionStatus.AWAITING_COLOR_MATCHING


# ────────────────────────────────────────────────────────────────
# Private helpers
# ────────────────────────────────────────────────────────────────

def _find_recipe(db: Session, item: ProductionOrderItem) -> Optional[Recipe]:
    """
    Find matching recipe by collection + color + size + application_type +
    place_of_application + finishing + thickness.

    Uses the unique constraint columns on recipes table.
    """
    query = db.query(Recipe).filter(Recipe.is_active.is_(True))

    if item.collection:
        query = query.filter(Recipe.collection == item.collection)
    if item.color:
        query = query.filter(Recipe.color == item.color)
    if item.size:
        query = query.filter(Recipe.size == item.size)
    if item.application_type:
        query = query.filter(Recipe.application_type == item.application_type)
    if item.place_of_application:
        query = query.filter(Recipe.place_of_application == item.place_of_application)
    if item.finishing:
        query = query.filter(Recipe.finishing_type == item.finishing)

    return query.first()


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
