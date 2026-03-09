"""Orders router — production order management."""

import uuid as uuid_mod
from datetime import date, datetime, timezone
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from api.database import get_db
from api.auth import get_current_user, apply_factory_filter
from api.roles import require_management
from api.models import ProductionOrder, ProductionOrderItem, OrderPosition, Factory, FinishedGoodsStock
from api.enums import OrderStatus, OrderSource, PositionStatus, is_stock_collection

router = APIRouter()


def _ev(val):
    """Enum value to string."""
    return val.value if hasattr(val, "value") else str(val) if val else None


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


class OrderUpdateInput(BaseModel):
    order_number: Optional[str] = None
    client: Optional[str] = None
    final_deadline: Optional[date] = None
    schedule_deadline: Optional[date] = None
    desired_delivery_date: Optional[date] = None
    mandatory_qc: Optional[bool] = None
    notes: Optional[str] = None
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
        "status_override": order.status_override,
        "source": _ev(order.source),
        "mandatory_qc": order.mandatory_qc,
        "notes": order.notes,
        "days_remaining": (order.final_deadline - date.today()).days if order.final_deadline else None,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
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
                "order_item_id": str(p.order_item_id),
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
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in positions
        ],
        "positions_count": len(positions),
        "positions_ready": sum(1 for p in positions if _ev(p.status) in ("ready_for_shipment", "shipped")),
        "shipped_at": order.shipped_at.isoformat() if order.shipped_at else None,
    }


# --- Endpoints ---

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
        source=OrderSource.MANUAL,
    )
    db.add(order)
    db.flush()

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
        )
        db.add(item)
        db.flush()

        position = OrderPosition(
            order_id=order.id, order_item_id=item.id,
            factory_id=UUID(data.factory_id),
            status=(
                PositionStatus.TRANSFERRED_TO_SORTING
                if is_stock_collection(item_data.collection)
                else PositionStatus.PLANNED
            ),
            quantity=item_data.quantity_pcs,
            color=item_data.color, size=item_data.size,
            application=item_data.application, finishing=item_data.finishing,
            collection=item_data.collection,
            application_type=item_data.application_type,
            place_of_application=item_data.place_of_application,
            product_type=item_data.product_type,
            thickness_mm=item_data.thickness,
            mandatory_qc=data.mandatory_qc,
        )
        db.add(position)
        db.flush()

        # Stock positions: distribute across factories based on finished goods availability
        if is_stock_collection(item_data.collection):
            _distribute_stock_position(db, position, item_data.quantity_pcs)

    db.commit()
    db.refresh(order)
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
    for k, v in data.model_dump(exclude_unset=True).items():
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
    order = db.query(ProductionOrder).filter(ProductionOrder.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    order.status = OrderStatus.CANCELLED
    order.updated_at = datetime.now(timezone.utc)
    db.query(OrderPosition).filter(OrderPosition.order_id == order_id).update(
        {"status": PositionStatus.CANCELLED}
    )
    db.commit()


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
        p.status = PositionStatus.SHIPPED

    order.status = OrderStatus.SHIPPED
    order.shipped_at = datetime.now(timezone.utc)
    order.updated_at = datetime.now(timezone.utc)
    db.commit()

    # Notify Sales app if order has external_id (async, fire-and-forget)
    if order.external_id:
        try:
            from api.config import get_settings
            settings = get_settings()
            if settings.SALES_APP_URL and settings.PRODUCTION_WEBHOOK_ENABLED:
                import httpx
                payload = {
                    "event": "order_shipped",
                    "external_id": order.external_id,
                    "order_number": order.order_number,
                    "shipped_at": order.shipped_at.isoformat(),
                    "status": "shipped",
                }
                async with httpx.AsyncClient() as client:
                    await client.post(
                        f"{settings.SALES_APP_URL}/api/webhooks/production-status",
                        json=payload,
                        headers={"Authorization": f"Bearer {settings.PRODUCTION_WEBHOOK_BEARER_TOKEN}"},
                        timeout=10,
                    )
        except Exception:
            pass  # Log error; webhook retry can be added later

    return {
        "status": "shipped",
        "positions_shipped": len(positions),
        "shipped_at": order.shipped_at.isoformat(),
    }


# --- Cancellation request management (PM side) ---

@router.get("/cancellation-requests")
async def list_cancellation_requests(
    factory_id: UUID | None = None,
    decision: str = Query("pending", description="Filter by decision: pending|accepted|rejected|all"),
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """List orders with pending (or all) cancellation requests. PM dashboard uses this."""
    query = db.query(ProductionOrder).filter(
        ProductionOrder.cancellation_requested.is_(True)
    )
    if decision != "all":
        query = query.filter(ProductionOrder.cancellation_decision == decision)

    query = apply_factory_filter(query, current_user, factory_id, ProductionOrder)

    orders = query.order_by(ProductionOrder.cancellation_requested_at.desc()).all()

    results = []
    for order in orders:
        # Get position summary
        positions = db.query(OrderPosition).filter(OrderPosition.order_id == order.id).all()
        pos_count = len(positions)
        pos_ready = sum(1 for p in positions if _ev(p.status) in ("ready_for_shipment", "shipped"))

        # Most common position status (represents "current stage")
        stage_map = {
            'planned': 'Planning', 'insufficient_materials': 'Planning',
            'awaiting_recipe': 'Planning', 'awaiting_stencil_silkscreen': 'Planning',
            'awaiting_color_matching': 'Planning',
            'engobe_applied': 'Glazing', 'engobe_check': 'Glazing',
            'glazed': 'Glazing', 'pre_kiln_check': 'Glazing', 'sent_to_glazing': 'Glazing',
            'in_kiln': 'Firing', 'fired': 'Fired',
            'sorting': 'Sorting', 'packing': 'Packing',
            'ready_for_shipment': 'Ready', 'shipped': 'Shipped',
        }
        if positions:
            statuses = [_ev(p.status) for p in positions]
            most_common = max(set(statuses), key=statuses.count)
            current_stage = stage_map.get(most_common, most_common.replace("_", " ").title())
        else:
            current_stage = "No positions"

        results.append({
            "id": str(order.id),
            "order_number": order.order_number,
            "client": order.client,
            "client_location": order.client_location,
            "factory_id": str(order.factory_id),
            "factory_name": order.factory.name if order.factory else "",
            "status": _ev(order.status),
            "current_stage": current_stage,
            "positions_count": pos_count,
            "positions_ready": pos_ready,
            "final_deadline": str(order.final_deadline) if order.final_deadline else None,
            "external_id": order.external_id,
            "cancellation_requested_at": order.cancellation_requested_at.isoformat() if order.cancellation_requested_at else None,
            "cancellation_decision": order.cancellation_decision,
            "cancellation_decided_at": order.cancellation_decided_at.isoformat() if order.cancellation_decided_at else None,
        })

    return {"items": results, "total": len(results)}


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

    # Apply decision
    order.cancellation_decision = "accepted"
    order.cancellation_decided_at = datetime.now(timezone.utc)
    order.cancellation_decided_by = current_user.id
    order.status = OrderStatus.CANCELLED
    order.updated_at = datetime.now(timezone.utc)

    # Cancel all positions
    db.query(OrderPosition).filter(OrderPosition.order_id == order_id).update(
        {"status": PositionStatus.CANCELLED}
    )
    db.commit()

    # Async: notify Sales App of cancellation (fire-and-forget)
    if order.external_id:
        try:
            from api.config import get_settings
            settings = get_settings()
            if settings.SALES_APP_URL and settings.PRODUCTION_WEBHOOK_ENABLED:
                import httpx
                payload = {
                    "event": "cancellation_accepted",
                    "external_id": order.external_id,
                    "order_number": order.order_number,
                    "status": "cancelled",
                    "decided_by": current_user.name,
                    "decided_at": order.cancellation_decided_at.isoformat(),
                }
                async with httpx.AsyncClient() as client:
                    await client.post(
                        f"{settings.SALES_APP_URL}/api/webhooks/production-status",
                        json=payload,
                        headers={"Authorization": f"Bearer {settings.PRODUCTION_WEBHOOK_BEARER_TOKEN}"},
                        timeout=10,
                    )
        except Exception:
            pass

    return {
        "status": "accepted",
        "order_id": str(order_id),
        "order_number": order.order_number,
        "decided_by": current_user.name,
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

    # Notify Sales App of rejection (fire-and-forget)
    if order.external_id:
        try:
            from api.config import get_settings
            settings = get_settings()
            if settings.SALES_APP_URL and settings.PRODUCTION_WEBHOOK_ENABLED:
                import httpx
                payload = {
                    "event": "cancellation_rejected",
                    "external_id": order.external_id,
                    "order_number": order.order_number,
                    "status": _ev(order.status),  # status unchanged
                    "decided_by": current_user.name,
                    "decided_at": order.cancellation_decided_at.isoformat(),
                }
                async with httpx.AsyncClient() as client:
                    await client.post(
                        f"{settings.SALES_APP_URL}/api/webhooks/production-status",
                        json=payload,
                        headers={"Authorization": f"Bearer {settings.PRODUCTION_WEBHOOK_BEARER_TOKEN}"},
                        timeout=10,
                    )
        except Exception:
            pass

    return {
        "status": "rejected",
        "order_id": str(order_id),
        "order_number": order.order_number,
        "decided_by": current_user.name,
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
