"""Shipments router — full shipment workflow with partial shipment support."""

import logging
from datetime import datetime, timezone
from uuid import UUID
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from api.database import get_db
from api.auth import get_current_user
from api.roles import require_management
from api.models import (
    Shipment, ShipmentItem, ProductionOrder, OrderPosition,
    ProductionOrderStatusLog,
)
from api.enums import OrderStatus, PositionStatus
from business.services.status_machine import transition_position_status

router = APIRouter()
_logger = logging.getLogger("moonjar.shipments")


def _ev(val):
    """Enum value to string."""
    return val.value if hasattr(val, "value") else str(val) if val else None


# --- Pydantic schemas ---

class ShipmentItemCreate(BaseModel):
    position_id: UUID
    quantity_shipped: int = Field(..., gt=0)
    box_number: Optional[int] = None
    notes: Optional[str] = None


class ShipmentCreate(BaseModel):
    order_id: UUID
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None
    shipping_method: Optional[str] = None
    total_boxes: Optional[int] = None
    total_weight_kg: Optional[float] = None
    estimated_delivery: Optional[str] = None  # ISO date string
    notes: Optional[str] = None
    items: List[ShipmentItemCreate]


class ShipmentUpdate(BaseModel):
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None
    shipping_method: Optional[str] = None
    total_boxes: Optional[int] = None
    total_weight_kg: Optional[float] = None
    estimated_delivery: Optional[str] = None
    received_by: Optional[str] = None
    delivery_note_url: Optional[str] = None
    notes: Optional[str] = None


class ShipmentItemResponse(BaseModel):
    id: UUID
    shipment_id: UUID
    position_id: UUID
    quantity_shipped: int
    box_number: Optional[int] = None
    notes: Optional[str] = None
    # Denormalized position info
    color: Optional[str] = None
    size: Optional[str] = None
    position_label: Optional[str] = None

    model_config = {"from_attributes": True}


class ShipmentResponse(BaseModel):
    id: UUID
    order_id: UUID
    factory_id: UUID
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None
    shipping_method: Optional[str] = None
    total_pieces: int
    total_boxes: Optional[int] = None
    total_weight_kg: Optional[float] = None
    status: str
    shipped_at: Optional[str] = None
    estimated_delivery: Optional[str] = None
    delivered_at: Optional[str] = None
    shipped_by: Optional[UUID] = None
    received_by: Optional[str] = None
    delivery_note_url: Optional[str] = None
    notes: Optional[str] = None
    created_at: str
    items: List[ShipmentItemResponse] = []

    model_config = {"from_attributes": True}


def _shipment_to_dict(s: Shipment) -> dict:
    """Convert Shipment ORM object to response dict with items."""
    items = []
    for si in (s.items or []):
        pos = si.position
        items.append({
            "id": str(si.id),
            "shipment_id": str(si.shipment_id),
            "position_id": str(si.position_id),
            "quantity_shipped": si.quantity_shipped,
            "box_number": si.box_number,
            "notes": si.notes,
            "color": pos.color if pos else None,
            "size": pos.size if pos else None,
            "position_label": getattr(pos, "position_label", None) or (
                f"#{pos.position_number}.{pos.split_index}" if getattr(pos, "split_index", None)
                else f"#{pos.position_number}" if getattr(pos, "position_number", None)
                else None
            ) if pos else None,
        })
    return {
        "id": str(s.id),
        "order_id": str(s.order_id),
        "factory_id": str(s.factory_id),
        "tracking_number": s.tracking_number,
        "carrier": s.carrier,
        "shipping_method": s.shipping_method,
        "total_pieces": s.total_pieces or 0,
        "total_boxes": s.total_boxes,
        "total_weight_kg": float(s.total_weight_kg) if s.total_weight_kg else None,
        "status": s.status,
        "shipped_at": s.shipped_at.isoformat() if s.shipped_at else None,
        "estimated_delivery": s.estimated_delivery.isoformat() if s.estimated_delivery else None,
        "delivered_at": s.delivered_at.isoformat() if s.delivered_at else None,
        "shipped_by": str(s.shipped_by) if s.shipped_by else None,
        "received_by": s.received_by,
        "delivery_note_url": s.delivery_note_url,
        "notes": s.notes,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "items": items,
    }


# --- Endpoints ---

@router.get("", response_model=dict)
async def list_shipments(
    order_id: UUID | None = None,
    factory_id: UUID | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List shipments, optionally filtered by order_id, factory_id, status."""
    query = db.query(Shipment).options(
        joinedload(Shipment.items).joinedload(ShipmentItem.position)
    )
    if order_id:
        query = query.filter(Shipment.order_id == order_id)
    if factory_id:
        query = query.filter(Shipment.factory_id == factory_id)
    if status:
        query = query.filter(Shipment.status == status)
    query = query.order_by(Shipment.created_at.desc())

    # Count before pagination (without joinedload for correct count)
    count_query = db.query(func.count(Shipment.id))
    if order_id:
        count_query = count_query.filter(Shipment.order_id == order_id)
    if factory_id:
        count_query = count_query.filter(Shipment.factory_id == factory_id)
    if status:
        count_query = count_query.filter(Shipment.status == status)
    total = count_query.scalar()

    shipments = query.offset((page - 1) * per_page).limit(per_page).unique().all()
    return {
        "items": [_shipment_to_dict(s) for s in shipments],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/{shipment_id}", response_model=ShipmentResponse)
async def get_shipment(
    shipment_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get a single shipment with all items."""
    s = db.query(Shipment).options(
        joinedload(Shipment.items).joinedload(ShipmentItem.position)
    ).filter(Shipment.id == shipment_id).first()
    if not s:
        raise HTTPException(404, "Shipment not found")
    return _shipment_to_dict(s)


@router.post("", status_code=201)
async def create_shipment(
    data: ShipmentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Create a new shipment with selected positions (partial shipment support)."""
    order = db.query(ProductionOrder).filter(ProductionOrder.id == data.order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    if _ev(order.status) == "cancelled":
        raise HTTPException(400, "Cannot create shipment for cancelled order")

    # Validate all positions belong to this order and are ready
    if not data.items:
        raise HTTPException(400, "At least one position item is required")

    position_ids = [item.position_id for item in data.items]
    positions = db.query(OrderPosition).filter(
        OrderPosition.id.in_(position_ids),
        OrderPosition.order_id == data.order_id,
    ).all()

    if len(positions) != len(position_ids):
        raise HTTPException(400, "One or more positions not found or don't belong to this order")

    # Check positions are in a shippable state (ready_for_shipment or shipped for re-shipment)
    for pos in positions:
        pos_status = _ev(pos.status)
        if pos_status not in ("ready_for_shipment", "shipped"):
            raise HTTPException(
                400,
                f"Position #{getattr(pos, 'position_number', '?')} is not ready for shipment (status: {pos_status})"
            )

    # Check quantities don't exceed available
    pos_map = {pos.id: pos for pos in positions}
    for item in data.items:
        pos = pos_map.get(item.position_id)
        if pos and item.quantity_shipped > pos.quantity:
            raise HTTPException(
                400,
                f"Cannot ship {item.quantity_shipped} pcs for position #{getattr(pos, 'position_number', '?')} "
                f"(available: {pos.quantity})"
            )

    # Parse estimated_delivery
    est_delivery = None
    if data.estimated_delivery:
        from datetime import date
        try:
            est_delivery = date.fromisoformat(data.estimated_delivery)
        except ValueError:
            raise HTTPException(400, "Invalid estimated_delivery date format (expected YYYY-MM-DD)")

    total_pieces = sum(item.quantity_shipped for item in data.items)

    shipment = Shipment(
        order_id=data.order_id,
        factory_id=order.factory_id,
        tracking_number=data.tracking_number,
        carrier=data.carrier,
        shipping_method=data.shipping_method,
        total_pieces=total_pieces,
        total_boxes=data.total_boxes,
        total_weight_kg=data.total_weight_kg,
        estimated_delivery=est_delivery,
        notes=data.notes,
        status="prepared",
    )
    db.add(shipment)
    db.flush()  # get shipment.id

    for item in data.items:
        db.add(ShipmentItem(
            shipment_id=shipment.id,
            position_id=item.position_id,
            quantity_shipped=item.quantity_shipped,
            box_number=item.box_number,
            notes=item.notes,
        ))

    db.commit()
    db.refresh(shipment)

    # Reload with joins
    shipment = db.query(Shipment).options(
        joinedload(Shipment.items).joinedload(ShipmentItem.position)
    ).filter(Shipment.id == shipment.id).first()

    _logger.info("Shipment %s created for order %s (%d pieces)", shipment.id, order.order_number, total_pieces)
    return _shipment_to_dict(shipment)


@router.patch("/{shipment_id}")
async def update_shipment(
    shipment_id: UUID,
    data: ShipmentUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Update shipment details (tracking, carrier, weight, etc.)."""
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(404, "Shipment not found")
    if shipment.status in ("delivered", "cancelled"):
        raise HTTPException(400, f"Cannot update shipment with status '{shipment.status}'")

    update_data = data.model_dump(exclude_unset=True)

    # Handle estimated_delivery as date
    if "estimated_delivery" in update_data:
        val = update_data.pop("estimated_delivery")
        if val:
            from datetime import date
            try:
                shipment.estimated_delivery = date.fromisoformat(val)
            except ValueError:
                raise HTTPException(400, "Invalid estimated_delivery date format")
        else:
            shipment.estimated_delivery = None

    for k, v in update_data.items():
        setattr(shipment, k, v)

    db.commit()
    db.refresh(shipment)

    shipment = db.query(Shipment).options(
        joinedload(Shipment.items).joinedload(ShipmentItem.position)
    ).filter(Shipment.id == shipment.id).first()

    return _shipment_to_dict(shipment)


@router.post("/{shipment_id}/ship")
async def mark_shipped(
    shipment_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Mark shipment as shipped. Transitions positions to SHIPPED, notifies Sales webhook."""
    shipment = db.query(Shipment).options(
        joinedload(Shipment.items).joinedload(ShipmentItem.position)
    ).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(404, "Shipment not found")
    if shipment.status != "prepared":
        raise HTTPException(400, f"Cannot ship a shipment with status '{shipment.status}'")

    order = db.query(ProductionOrder).filter(ProductionOrder.id == shipment.order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")

    # Mark shipment as shipped
    now = datetime.now(timezone.utc)
    shipment.status = "shipped"
    shipment.shipped_at = now
    shipment.shipped_by = current_user.id

    # Transition shipped positions to SHIPPED status
    shipped_position_ids = [item.position_id for item in shipment.items]
    positions = db.query(OrderPosition).filter(
        OrderPosition.id.in_(shipped_position_ids)
    ).all()

    for p in positions:
        if _ev(p.status) == "ready_for_shipment":
            transition_position_status(db, p.id, PositionStatus.SHIPPED.value, changed_by=current_user.id)

    # Check if ALL order positions are now shipped → update order status
    all_positions = db.query(OrderPosition).filter(
        OrderPosition.order_id == order.id
    ).all()
    all_shipped = all(
        _ev(p.status) in ("shipped", "cancelled")
        for p in all_positions
    )
    some_shipped = any(_ev(p.status) == "shipped" for p in all_positions)

    old_order_status = order.status
    if all_shipped:
        order.status = OrderStatus.SHIPPED
        order.shipped_at = now
        order.updated_at = now
    elif some_shipped and _ev(order.status) not in ("shipped",):
        # Partial shipment: keep as partially_ready or current status
        order.updated_at = now

    # Log order status change if changed
    if order.status != old_order_status:
        try:
            db.add(ProductionOrderStatusLog(
                order_id=order.id,
                old_status=old_order_status,
                new_status=order.status,
                changed_by=current_user.id,
            ))
        except Exception as e:
            _logger.warning("Failed to log order status change: %s", e)

    db.commit()

    # Notify Sales app via webhook
    if order.external_id:
        try:
            from business.services.webhook_sender import send_webhook
            await send_webhook(
                {
                    "event": "order_shipped",
                    "external_id": order.external_id,
                    "order_number": order.order_number,
                    "client": order.client,
                    "shipped_at": shipment.shipped_at.isoformat(),
                    "tracking_number": shipment.tracking_number,
                    "carrier": shipment.carrier,
                    "shipping_method": shipment.shipping_method,
                    "total_pieces": shipment.total_pieces,
                    "total_boxes": shipment.total_boxes,
                    "positions_shipped": len(shipped_position_ids),
                    "partial": not all_shipped,
                    "status": "shipped" if all_shipped else "partially_shipped",
                },
                event_type="order_shipped",
                external_id=order.external_id,
            )
        except Exception as e:
            _logger.error("Failed to send webhook for shipment %s: %s", shipment_id, e)

    # Reload
    shipment = db.query(Shipment).options(
        joinedload(Shipment.items).joinedload(ShipmentItem.position)
    ).filter(Shipment.id == shipment.id).first()

    _logger.info("Shipment %s marked as shipped for order %s", shipment_id, order.order_number)
    return _shipment_to_dict(shipment)


@router.post("/{shipment_id}/deliver")
async def mark_delivered(
    shipment_id: UUID,
    received_by: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Mark shipment as delivered."""
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(404, "Shipment not found")
    if shipment.status not in ("shipped", "in_transit"):
        raise HTTPException(400, f"Cannot deliver a shipment with status '{shipment.status}'")

    shipment.status = "delivered"
    shipment.delivered_at = datetime.now(timezone.utc)
    if received_by:
        shipment.received_by = received_by

    db.commit()

    # Notify Sales
    order = db.query(ProductionOrder).filter(ProductionOrder.id == shipment.order_id).first()
    if order and order.external_id:
        try:
            from business.services.webhook_sender import send_webhook
            await send_webhook(
                {
                    "event": "order_delivered",
                    "external_id": order.external_id,
                    "order_number": order.order_number,
                    "shipment_id": str(shipment.id),
                    "delivered_at": shipment.delivered_at.isoformat(),
                    "received_by": shipment.received_by,
                },
                event_type="order_delivered",
                external_id=order.external_id,
            )
        except Exception as e:
            _logger.error("Failed to send delivery webhook for shipment %s: %s", shipment_id, e)

    shipment = db.query(Shipment).options(
        joinedload(Shipment.items).joinedload(ShipmentItem.position)
    ).filter(Shipment.id == shipment.id).first()

    return _shipment_to_dict(shipment)


@router.delete("/{shipment_id}", status_code=204)
async def cancel_shipment(
    shipment_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Cancel (delete) a shipment. Only allowed when status is 'prepared'."""
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(404, "Shipment not found")
    if shipment.status != "prepared":
        raise HTTPException(400, f"Cannot cancel a shipment with status '{shipment.status}'. Only 'prepared' shipments can be cancelled.")

    db.delete(shipment)
    db.commit()
    _logger.info("Shipment %s cancelled/deleted", shipment_id)
