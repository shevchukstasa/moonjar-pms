"""Integration router — Sales webhook receiver + production status API."""

import hashlib
import hmac as hmac_mod
import logging
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

logger = logging.getLogger("moonjar.integration")

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


@router.get("/orders/status-updates")
async def get_all_production_statuses(
    since: Optional[str] = Query(None, description="ISO date: only orders updated since this date"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """Bulk status endpoint for Sales polling (every 30 min).
    Returns all Sales-originated orders with current status, stage, progress, ETA.
    Auth: X-API-Key header or Bearer token.
    """
    settings = get_settings()

    # Authenticate (same as single-order endpoint)
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

    # Query all Sales-originated orders (active ones)
    query = db.query(ProductionOrder).filter(
        ProductionOrder.source == OrderSource.SALES_WEBHOOK,
        ProductionOrder.status.notin_([
            OrderStatus.CANCELLED.value,
        ]),
    )

    # If 'since' provided, only return orders updated after that date
    if since:
        try:
            since_dt = datetime.fromisoformat(since)
            query = query.filter(ProductionOrder.updated_at >= since_dt)
        except ValueError:
            raise HTTPException(400, "Invalid 'since' date format. Use ISO format: YYYY-MM-DD")

    orders = query.order_by(ProductionOrder.updated_at.desc()).limit(200).all()

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

    results = []
    for order in orders:
        positions = db.query(OrderPosition).filter(
            OrderPosition.order_id == order.id,
            OrderPosition.split_category.is_(None),
        ).all()

        total = len(positions)
        ready = sum(1 for p in positions if _ev(p.status) in ('ready_for_shipment', 'shipped'))

        if positions:
            stages = [stage_map.get(_ev(p.status), 'unknown') for p in positions]
            current_stage = max(set(stages), key=stages.count)
        else:
            current_stage = 'unknown'

        factory = db.query(Factory).filter(Factory.id == order.factory_id).first()

        results.append({
            "external_id": order.external_id,
            "order_number": order.order_number,
            "client": order.client,
            "status": _ev(order.status),
            "current_stage": current_stage,
            "factory_name": factory.name if factory else None,
            "positions_total": total,
            "positions_ready": ready,
            "progress_percent": round(ready / total * 100, 1) if total else 0,
            "estimated_completion_date": str(order.schedule_deadline) if order.schedule_deadline else None,
            "shipped_at": order.shipped_at.isoformat() if order.shipped_at else None,
            "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        })

    return {"items": results, "total": len(results)}


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
    Auth: X-API-Key header OR Bearer token.  HMAC-SHA256 signature verified when configured.
    Payload: flat format (Sales) or nested order_data (legacy).
    """
    settings = get_settings()

    if not settings.PRODUCTION_WEBHOOK_ENABLED:
        raise HTTPException(503, "Webhook receiver disabled")

    # Read raw body BEFORE json parsing (needed for HMAC verification)
    raw_body = await request.body()

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

    # HMAC-SHA256 signature verification (when HMAC secret is configured)
    hmac_secret = settings.PRODUCTION_WEBHOOK_HMAC_SECRET
    if hmac_secret:
        signature = request.headers.get("X-Webhook-Signature")
        if not signature:
            logger.warning("Webhook received without HMAC signature")
            raise HTTPException(401, "Missing webhook signature")
        expected = hmac_mod.new(
            hmac_secret.encode(), raw_body, hashlib.sha256
        ).hexdigest()
        if not hmac_mod.compare_digest(signature, expected):
            logger.warning("Webhook HMAC signature mismatch")
            raise HTTPException(401, "Invalid webhook signature")

    # Parse body
    import json
    body = json.loads(raw_body)

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

            # Notify Production Managers of the assigned factory (best-effort)
            try:
                from business.services.notifications import notify_pm
                positions_count = db.query(OrderPosition).filter(
                    OrderPosition.order_id == order.id,
                ).count()
                notify_pm(
                    db=db,
                    factory_id=order.factory_id,
                    type="status_change",
                    title=f"New order from Sales: {order.order_number}",
                    message=(
                        f"Client: {order.client}, "
                        f"{positions_count} position(s). "
                        f"Deadline: {order.final_deadline or 'not set'}"
                    ),
                    related_entity_type="order",
                    related_entity_id=order.id,
                )
            except Exception as e:
                logger.warning(f"Failed to notify PM about new order: {e}")

            # Schedule deadline estimation (stub — returns placeholder until
            # factory/kiln configuration is complete)
            estimated_completion = _estimate_completion_stub(order)

            # Return factory info + estimated completion so Sales can show delivery date
            factory = db.query(Factory).filter(Factory.id == order.factory_id).first()
            return {
                "status": "processed",
                "order_id": str(order.id),
                "factory_name": factory.name if factory else None,
                "factory_location": factory.location if factory else None,
                "estimated_completion_date": estimated_completion,
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


def _resolve_factory(db: Session, client_location: str | None, explicit_factory_id: str | None = None) -> Factory:
    """
    Resolve factory for an incoming order.

    Priority:
    1. Explicit factory_id from payload
    2. Single active factory → always use it (no lookup needed)
    3. Match by served_locations JSONB
    4. Fallback to first active factory

    Raises ValueError only if zero factories exist.
    """
    # 1. Explicit factory_id
    if explicit_factory_id:
        factory = db.query(Factory).filter(
            Factory.id == UUID(explicit_factory_id),
            Factory.is_active.is_(True),
        ).first()
        if factory:
            return factory
        # If explicit ID is invalid, fall through to auto-assignment
        logger.warning(f"Explicit factory_id {explicit_factory_id} not found or inactive, auto-assigning")

    # 2. Get all active factories
    active_factories = db.query(Factory).filter(Factory.is_active.is_(True)).all()
    if not active_factories:
        raise ValueError("No active factories configured in the system")

    # Single factory → always use it, skip all matching logic
    if len(active_factories) == 1:
        return active_factories[0]

    # 3. Match by served_locations (multiple factories)
    if client_location:
        loc = client_location.strip().lower()
        for f in active_factories:
            if f.served_locations:
                served = [s.lower() for s in f.served_locations]
                if loc in served:
                    return f

    # 4. Fallback: first active factory
    return active_factories[0]


def _create_order_from_webhook(db: Session, order_data: dict, raw_payload: dict) -> ProductionOrder:
    """Create a production order from Sales webhook payload."""

    # Resolve factory (handles single-factory, location matching, fallback)
    factory = _resolve_factory(
        db,
        client_location=order_data.get("client_location"),
        explicit_factory_id=order_data.get("factory_id"),
    )
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


# ────────────────────────────────────────────────────────────────
# Stubs — placeholder logic until full configuration is done.
# Can be toggled via GET/POST /api/integration/stubs endpoints.
# ────────────────────────────────────────────────────────────────

# Stub toggle state — both OFF by default (real logic active)
_stubs_state = {
    "schedule_estimation": False,       # False = real schedule estimation active
    "intermediate_callbacks": False,    # False = real callbacks active
}


def _estimate_completion_stub(order: ProductionOrder) -> Optional[str]:
    """
    Stub: return placeholder estimated completion date.
    When disabled, will use real schedule_estimation service.
    """
    if not _stubs_state["schedule_estimation"]:
        # Real calculation — use schedule_estimation service
        try:
            from business.services.schedule_estimation import calculate_schedule_deadline
            from api.database import SessionLocal
            db = SessionLocal()
            try:
                result = calculate_schedule_deadline(db, order)
                if order.schedule_deadline:
                    return str(order.schedule_deadline)
            except Exception as e:
                logger.warning(f"Schedule estimation failed, falling back: {e}")
            finally:
                db.close()
        except ImportError:
            pass

    # Stub: return final_deadline if available, else None
    if order.schedule_deadline:
        return str(order.schedule_deadline)
    if order.final_deadline:
        return str(order.final_deadline)
    return None


async def notify_sales_status_change_stub(order, position, old_status: str, new_status: str):
    """
    Stub: send intermediate status callbacks to Sales.
    When disabled (stub active), skips callback.
    When enabled, sends real callback.
    """
    if _stubs_state["intermediate_callbacks"]:
        return  # Stub: skip intermediate callbacks

    # Real callback logic
    try:
        from api.config import get_settings
        settings = get_settings()
        if not settings.SALES_APP_URL or not settings.PRODUCTION_WEBHOOK_ENABLED:
            return
        if not order.external_id:
            return

        import httpx
        payload = {
            "event": "status_change",
            "external_id": order.external_id,
            "order_number": order.order_number,
            "position_id": str(position.id),
            "old_status": old_status,
            "new_status": new_status,
            "order_status": _ev(order.status),
        }
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{settings.SALES_APP_URL}/api/webhooks/production-status",
                json=payload,
                headers={"Authorization": f"Bearer {settings.PRODUCTION_WEBHOOK_BEARER_TOKEN}"},
                timeout=10,
            )
    except Exception as e:
        logger.warning(f"Sales status callback failed: {e}")


@router.get("/stubs")
async def get_stubs_state(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get current state of integration stubs."""
    return {
        "stubs": {
            "schedule_estimation": {
                "active": _stubs_state["schedule_estimation"],
                "description": "Schedule deadline estimation — returns placeholder dates",
            },
            "intermediate_callbacks": {
                "active": _stubs_state["intermediate_callbacks"],
                "description": "Intermediate status change callbacks to Sales app",
            },
        },
    }


@router.post("/stubs")
async def toggle_stubs(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Toggle integration stubs on/off.
    Body: {"schedule_estimation": false, "intermediate_callbacks": false}
    """
    import json
    body = await request.json()

    # Only allow management roles to toggle stubs
    user_role = _ev(current_user.role) if hasattr(current_user, 'role') else None
    if user_role not in ('owner', 'administrator', 'production_manager', 'ceo'):
        from fastapi import HTTPException as HE
        raise HE(403, "Only management can toggle stubs")

    changed = {}
    for key in ("schedule_estimation", "intermediate_callbacks"):
        if key in body and isinstance(body[key], bool):
            old = _stubs_state[key]
            _stubs_state[key] = body[key]
            changed[key] = {"old": old, "new": body[key]}

    return {"status": "updated", "changed": changed, "current": _stubs_state}
