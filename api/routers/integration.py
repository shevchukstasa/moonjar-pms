"""Integration router — Sales webhook receiver + production status API."""

import uuid as uuid_mod
from datetime import date, datetime, timezone
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from api.database import get_db
from api.auth import get_current_user
from api.config import get_settings
from api.models import (
    ProductionOrder, ProductionOrderItem, OrderPosition,
    SalesWebhookEvent, Factory,
)
from api.enums import OrderStatus, OrderSource, PositionStatus, is_stock_collection

router = APIRouter()


def _ev(val):
    return val.value if hasattr(val, "value") else str(val) if val else None


# ---------- Production Status API (for Sales app) ----------

@router.get("/orders/{external_id}/production-status")
async def get_production_status(
    external_id: str,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """Public endpoint for Sales app to query order production status.
    Auth: X-API-Key header or Bearer token.
    """
    settings = get_settings()

    # Verify authentication — accept X-API-Key OR Bearer token
    # Sales uses PMS_WEBHOOK_TOKEN (Bearer) for polling,
    # and PMS_API_KEY (X-API-Key) for sending orders
    authenticated = False
    if x_api_key and settings.SALES_APP_API_KEY and x_api_key == settings.SALES_APP_API_KEY:
        authenticated = True
    elif authorization and authorization.startswith("Bearer "):
        bearer = authorization[7:]
        if bearer and (
            (settings.SALES_APP_API_KEY and bearer == settings.SALES_APP_API_KEY)
            or (settings.PRODUCTION_WEBHOOK_BEARER_TOKEN and bearer == settings.PRODUCTION_WEBHOOK_BEARER_TOKEN)
        ):
            authenticated = True

    if not authenticated:
        raise HTTPException(401, "Invalid API key")

    # Find order by external_id
    order = db.query(ProductionOrder).filter(
        ProductionOrder.external_id == external_id,
    ).first()
    if not order:
        raise HTTPException(404, "Order not found")

    # Count positions (main only, no sub-positions)
    positions = db.query(OrderPosition).filter(
        OrderPosition.order_id == order.id,
        OrderPosition.split_category.is_(None),
    ).all()

    total = len(positions)
    ready = sum(1 for p in positions if _ev(p.status) in ('ready_for_shipment', 'shipped'))

    # Determine current stage (most common status)
    stage_map = {
        'planned': 'planning', 'insufficient_materials': 'planning',
        'awaiting_recipe': 'planning', 'awaiting_stencil_silkscreen': 'planning',
        'awaiting_color_matching': 'planning',
        'engobe_applied': 'glazing', 'engobe_check': 'glazing',
        'glazed': 'glazing', 'pre_kiln_check': 'glazing', 'sent_to_glazing': 'glazing',
        'loaded_in_kiln': 'firing', 'fired': 'firing', 'refire': 'firing',
        'transferred_to_sorting': 'sorting', 'packed': 'packing',
        'sent_to_quality_check': 'quality', 'quality_check_done': 'quality',
        'blocked_by_qm': 'quality',
        'ready_for_shipment': 'ready', 'shipped': 'shipped',
    }
    if positions:
        stages = [stage_map.get(_ev(p.status), 'unknown') for p in positions]
        current_stage = max(set(stages), key=stages.count)
    else:
        current_stage = 'unknown'

    # Include factory info
    factory = db.query(Factory).filter(Factory.id == order.factory_id).first()

    return {
        "external_id": external_id,
        "order_number": order.order_number,
        "client": order.client,
        "status": _ev(order.status),
        "current_stage": current_stage,
        "factory_id": str(order.factory_id),
        "factory_name": factory.name if factory else None,
        "factory_location": factory.location if factory else None,
        "positions_total": total,
        "positions_ready": ready,
        "progress_percent": round(ready / total * 100, 1) if total else 0,
        "estimated_completion_date": str(order.schedule_deadline) if order.schedule_deadline else None,
        "shipped_at": order.shipped_at.isoformat() if order.shipped_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
    }


# ---------- Incoming Webhook (from Sales) ----------

class SalesOrderWebhookPayload(BaseModel):
    event_id: str
    event_type: str = "new_order"  # new_order | order_update | order_cancel
    order_data: dict


@router.post("/webhook/sales-order")
async def receive_sales_order(
    request: Request,
    db: Session = Depends(get_db),
):
    """Receive order from Sales app.
    Auth: X-API-Key header OR Bearer token.
    Payload: flat format (Sales) or nested order_data (legacy).
    """
    settings = get_settings()

    if not settings.PRODUCTION_WEBHOOK_ENABLED:
        raise HTTPException(503, "Webhook receiver disabled")

    # Verify authentication — accept both X-API-Key and Bearer
    x_api_key = request.headers.get("X-API-Key")
    auth_header = request.headers.get("Authorization", "")
    bearer_token = auth_header[7:] if auth_header.startswith("Bearer ") else None

    authenticated = False
    if x_api_key and settings.SALES_APP_API_KEY and x_api_key == settings.SALES_APP_API_KEY:
        authenticated = True
    elif bearer_token and settings.PRODUCTION_WEBHOOK_BEARER_TOKEN and bearer_token == settings.PRODUCTION_WEBHOOK_BEARER_TOKEN:
        authenticated = True

    if not authenticated:
        raise HTTPException(401, "Invalid API key or bearer token")

    # Parse body
    body = await request.json()

    # Auto-generate event_id if not provided (Sales may not send it)
    event_id = body.get("event_id") or f"auto-{uuid_mod.uuid4().hex[:16]}"

    # Idempotency check
    existing = db.query(SalesWebhookEvent).filter(
        SalesWebhookEvent.event_id == event_id,
    ).first()
    if existing:
        return {"status": "duplicate", "order_id": None}

    # Store event
    event = SalesWebhookEvent(
        id=uuid_mod.uuid4(),
        event_id=event_id,
        payload_json=body,
        processed=False,
    )
    db.add(event)

    event_type = body.get("event_type", "new_order")

    # Support both flat format (Sales) and nested order_data (legacy)
    order_data = body.get("order_data")
    if order_data is None:
        # Flat format: external_id, customer_name, items are at top level
        order_data = body

    if event_type == "new_order":
        # Check if order with this external_id already exists (duplicate protection)
        ext_id = order_data.get("external_id")
        if ext_id:
            existing_order = db.query(ProductionOrder).filter(
                ProductionOrder.external_id == ext_id,
                ProductionOrder.source == OrderSource.SALES_WEBHOOK,
            ).first()
            if existing_order:
                event.processed = True
                event.error_message = f"Duplicate: order {ext_id} already exists"
                db.commit()
                factory = db.query(Factory).filter(Factory.id == existing_order.factory_id).first()
                return {
                    "status": "duplicate",
                    "order_id": str(existing_order.id),
                    "factory_name": factory.name if factory else None,
                    "factory_location": factory.location if factory else None,
                }

        try:
            order = _create_order_from_webhook(db, order_data, body)
            event.processed = True
            db.commit()
            # Return factory info + estimated completion so Sales can show delivery date
            factory = db.query(Factory).filter(Factory.id == order.factory_id).first()
            return {
                "status": "processed",
                "order_id": str(order.id),
                "factory_name": factory.name if factory else None,
                "factory_location": factory.location if factory else None,
                "estimated_completion_date": (
                    str(order.schedule_deadline) if order.schedule_deadline
                    else str(order.final_deadline) if order.final_deadline
                    else None
                ),
            }
        except Exception as e:
            db.rollback()
            event.error_message = str(e)
            db.add(event)
            db.commit()
            raise HTTPException(422, f"Failed to process order: {e}")

    elif event_type == "order_cancel":
        ext_id = order_data.get("external_id")
        order = db.query(ProductionOrder).filter(
            ProductionOrder.external_id == ext_id,
            ProductionOrder.source == OrderSource.SALES_WEBHOOK,
        ).first()
        if order:
            order.status = OrderStatus.CANCELLED
            order.updated_at = datetime.now(timezone.utc)
            db.query(OrderPosition).filter(
                OrderPosition.order_id == order.id,
            ).update({"status": PositionStatus.CANCELLED})
            event.processed = True
            db.commit()
            return {"status": "cancelled", "order_id": str(order.id)}
        else:
            event.error_message = f"Order not found: {ext_id}"
            db.commit()
            return {"status": "not_found"}

    else:
        event.processed = True
        db.commit()
        return {"status": "acknowledged", "event_type": event_type}


def _create_order_from_webhook(db: Session, order_data: dict, raw_payload: dict) -> ProductionOrder:
    """Create a production order from Sales webhook payload."""

    # Resolve factory
    factory_id = order_data.get("factory_id")
    if not factory_id:
        # Default to first factory
        factory = db.query(Factory).first()
        if not factory:
            raise ValueError("No factories configured")
        factory_id = str(factory.id)

    order = ProductionOrder(
        id=uuid_mod.uuid4(),
        order_number=order_data.get("order_number", f"SALES-{uuid_mod.uuid4().hex[:8].upper()}"),
        client=order_data.get("client") or order_data.get("customer_name", "Unknown"),
        client_location=order_data.get("client_location"),
        sales_manager_name=order_data.get("sales_manager_name"),
        sales_manager_contact=order_data.get("sales_manager_contact"),
        factory_id=UUID(factory_id),
        document_date=date.today(),
        production_received_date=date.today(),
        final_deadline=_parse_date(order_data.get("final_deadline")),
        desired_delivery_date=_parse_date(order_data.get("desired_delivery_date")),
        status=OrderStatus.NEW,
        source=OrderSource.SALES_WEBHOOK,
        external_id=order_data.get("external_id"),
        sales_payload_json=raw_payload,
        mandatory_qc=order_data.get("mandatory_qc", False),
        notes=order_data.get("notes"),
    )
    db.add(order)
    db.flush()

    items = order_data.get("items", [])
    for item_data in items:
        # Support both "quantity" (Sales) and "quantity_pcs" (PMS native)
        qty_pcs = item_data.get("quantity_pcs") or item_data.get("quantity", 0)
        qty_sqm = item_data.get("quantity_sqm")

        # Parse thickness: accept string "11mm" or number 11.0
        raw_thickness = item_data.get("thickness", 11.0)
        if isinstance(raw_thickness, str):
            raw_thickness = float(''.join(c for c in raw_thickness if c.isdigit() or c == '.') or '11')
        thickness_mm = item_data.get("thickness_mm") or raw_thickness

        item = ProductionOrderItem(
            id=uuid_mod.uuid4(),
            order_id=order.id,
            color=item_data.get("color", ""),
            color_2=item_data.get("color_2"),
            size=item_data.get("size", ""),
            application=item_data.get("application"),
            finishing=item_data.get("finishing"),
            thickness=thickness_mm,
            quantity_pcs=qty_pcs,
            quantity_sqm=qty_sqm,
            collection=item_data.get("collection"),
            application_type=item_data.get("application_type"),
            place_of_application=item_data.get("place_of_application"),
            product_type=item_data.get("product_type", "tile"),
        )
        db.add(item)
        db.flush()

        position = OrderPosition(
            id=uuid_mod.uuid4(),
            order_id=order.id,
            order_item_id=item.id,
            factory_id=UUID(factory_id),
            status=(
                PositionStatus.TRANSFERRED_TO_SORTING
                if is_stock_collection(item_data.get("collection"))
                else PositionStatus.PLANNED
            ),
            quantity=qty_pcs,
            quantity_sqm=qty_sqm,
            color=item_data.get("color", ""),
            color_2=item_data.get("color_2"),
            size=item_data.get("size", ""),
            application=item_data.get("application"),
            finishing=item_data.get("finishing"),
            collection=item_data.get("collection"),
            application_type=item_data.get("application_type"),
            place_of_application=item_data.get("place_of_application"),
            product_type=item_data.get("product_type", "tile"),
            thickness_mm=thickness_mm,
            mandatory_qc=order_data.get("mandatory_qc", False),
        )
        db.add(position)
        db.flush()

    return order


def _parse_date(val) -> Optional[date]:
    if not val:
        return None
    if isinstance(val, date):
        return val
    try:
        return date.fromisoformat(str(val))
    except (ValueError, TypeError):
        return None
