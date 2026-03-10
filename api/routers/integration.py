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
    SalesWebhookEvent, Factory, Task,
)
from api.enums import (
    OrderStatus, OrderSource, PositionStatus, TaskType, TaskStatus,
    UserRole, is_stock_collection,
)

logger = logging.getLogger("moonjar.integration")

router = APIRouter()


def _ev(val):
    return val.value if hasattr(val, "value") else str(val) if val else None


# ---------- Diagnostics ----------

@router.get("/health")
async def integration_health():
    """Public diagnostic: check if Sales integration keys are configured (no secrets leaked)."""
    settings = get_settings()
    return {
        "webhook_enabled": settings.PRODUCTION_WEBHOOK_ENABLED,
        "sales_app_api_key_set": bool(settings.SALES_APP_API_KEY),
        "sales_app_api_key_length": len(settings.SALES_APP_API_KEY),
        "bearer_token_set": bool(settings.PRODUCTION_WEBHOOK_BEARER_TOKEN),
        "bearer_token_length": len(settings.PRODUCTION_WEBHOOK_BEARER_TOKEN),
        "hmac_secret_set": bool(settings.PRODUCTION_WEBHOOK_HMAC_SECRET),
        "sales_app_url_set": bool(settings.SALES_APP_URL),
    }


@router.get("/db-check")
async def db_check(db: Session = Depends(get_db)):
    """Public diagnostic: check actual database state — alembic version, key tables, row counts."""
    from sqlalchemy import text as sa_text
    result = {}
    try:
        # Alembic version
        try:
            row = db.execute(sa_text("SELECT version_num FROM alembic_version LIMIT 1")).fetchone()
            result["alembic_version"] = row[0] if row else "no_version"
        except Exception as e:
            result["alembic_version"] = f"error: {e}"

        # Check key columns existence
        col_checks = [
            ("order_positions", "firing_round"),
            ("order_positions", "quantity_sqm"),
            ("order_positions", "color_2"),
            ("factories", "served_locations"),
            ("production_orders", "shipped_at"),
            ("tasks", "metadata_json"),
            ("colors", "is_basic"),
        ]
        missing_cols = []
        for table, col in col_checks:
            try:
                db.execute(sa_text(f"SELECT {col} FROM {table} LIMIT 0"))
            except Exception:
                missing_cols.append(f"{table}.{col}")
                db.rollback()
        result["missing_columns"] = missing_cols

        # Row counts for key tables
        count_tables = ["factories", "colors", "sizes", "collections", "production_stages",
                        "resources", "warehouse_sections", "shifts", "kiln_constants",
                        "firing_profiles", "quality_assignment_config",
                        "production_orders", "order_positions", "tasks"]
        counts = {}
        for t in count_tables:
            try:
                row = db.execute(sa_text(f"SELECT COUNT(*) FROM {t}")).fetchone()
                counts[t] = row[0]
            except Exception:
                counts[t] = "table_missing"
                db.rollback()
        result["row_counts"] = counts

        # Resource details (kilns)
        try:
            rows = db.execute(sa_text(
                "SELECT r.name, r.resource_type, r.kiln_type, r.status, r.is_active, f.name as factory "
                "FROM resources r JOIN factories f ON r.factory_id = f.id "
                "ORDER BY f.name, r.name"
            )).fetchall()
            result["resources_detail"] = [
                {"name": r[0], "type": r[1], "kiln_type": r[2], "status": r[3],
                 "is_active": r[4], "factory": r[5]}
                for r in rows
            ]
        except Exception:
            result["resources_detail"] = "error"
            db.rollback()

        # Factory details
        try:
            rows = db.execute(sa_text(
                "SELECT id, name, is_active, served_locations FROM factories ORDER BY name"
            )).fetchall()
            result["factories_detail"] = [
                {"id": str(r[0]), "name": r[1], "is_active": r[2], "served_locations": r[3]}
                for r in rows
            ]
        except Exception:
            result["factories_detail"] = "error"
            db.rollback()

    except Exception as e:
        result["error"] = str(e)

    return result


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
        # Cancellation request state — so Sales app knows current decision state
        "cancellation_requested": getattr(order, "cancellation_requested", False) or False,
        "cancellation_decision": getattr(order, "cancellation_decision", None),
        "cancellation_requested_at": (
            order.cancellation_requested_at.isoformat()
            if getattr(order, "cancellation_requested_at", None) else None
        ),
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


# ---------- Cancellation Request (from Sales) ----------

class CancellationRequestPayload(BaseModel):
    external_id: str
    order_number: Optional[str] = None


@router.post("/orders/{external_id}/request-cancellation")
async def request_cancellation(
    external_id: str,
    payload: CancellationRequestPayload,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """Sales App calls this to request PM review an order cancellation.
    Auth: X-API-Key header or Bearer token.
    Returns 200 with {"message": "Cancellation requested"} on success.
    Returns 4xx/5xx with {"error": "..."} on failure.
    """
    from datetime import timezone as tz
    from api.models import Notification, User
    from api.models import UserFactory
    from api.enums import NotificationType, RelatedEntityType, UserRole
    settings = get_settings()

    # --- Auth ---
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
        raise HTTPException(401, detail={"error": "Invalid API key"})

    # --- Find order ---
    order = db.query(ProductionOrder).filter(
        ProductionOrder.external_id == external_id,
    ).first()
    if not order:
        raise HTTPException(404, detail={"error": f"Order with external_id={external_id} not found"})

    # --- Guard: already cancelled ---
    if _ev(order.status) == "cancelled":
        raise HTTPException(409, detail={"error": "Order is already cancelled"})

    # --- Guard: duplicate request ---
    if order.cancellation_requested and order.cancellation_decision == "pending":
        # Idempotent: Sales can safely retry — already pending PM review
        logger.info(
            "Cancellation already pending for order %s (external_id=%s) — idempotent return",
            order.order_number, external_id,
        )
        return {
            "message": "Cancellation requested",
            "cancellation_decision": "pending",
            "order_id": str(order.id),
            "order_status": _ev(order.status),
        }

    # --- Mark cancellation requested ---
    prev_decision = order.cancellation_decision  # log for debugging
    order.cancellation_requested = True
    order.cancellation_requested_at = datetime.now(tz.utc)
    order.cancellation_decision = "pending"
    order.updated_at = datetime.now(tz.utc)
    logger.info(
        "Cancellation request created for order %s (external_id=%s), prev_decision=%s",
        order.order_number, external_id, prev_decision,
    )

    # --- Notify all PMs for the factory ---
    pm_users = (
        db.query(User)
        .join(UserFactory, UserFactory.user_id == User.id)
        .filter(
            UserFactory.factory_id == order.factory_id,
            User.role == UserRole.PRODUCTION_MANAGER.value,
            User.is_active.is_(True),
        )
        .all()
    )
    for pm in pm_users:
        notif = Notification(
            user_id=pm.id,
            factory_id=order.factory_id,
            type=NotificationType.CANCELLATION_REQUEST,
            title=f"Cancellation request: {order.order_number}",
            message=(
                f"Sales app requested cancellation of order {order.order_number}"
                + (f" (client: {order.client})" if order.client else "")
                + f". Current status: {_ev(order.status)}. "
                "Review the request in the dashboard."
            ),
            related_entity_type=RelatedEntityType.ORDER,
            related_entity_id=order.id,
        )
        db.add(notif)

    db.commit()
    logger.info(
        "Cancellation requested for order %s (external_id=%s) by Sales App, notified %d PM(s)",
        order.order_number, external_id, len(pm_users),
    )
    return {
        "message": "Cancellation requested",
        "cancellation_decision": "pending",
        "order_id": str(order.id),
        "order_status": _ev(order.status),
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
        # Debug logging — safe (no secrets leaked, only lengths and presence)
        logger.warning(
            "Webhook auth FAILED — "
            "X-API-Key present: %s (len=%d), "
            "SALES_APP_API_KEY configured: %s (len=%d), "
            "Bearer present: %s, "
            "PRODUCTION_WEBHOOK_BEARER_TOKEN configured: %s, "
            "match_apikey: %s",
            bool(x_api_key), len(x_api_key or ""),
            bool(settings.SALES_APP_API_KEY), len(settings.SALES_APP_API_KEY or ""),
            bool(bearer_token),
            bool(settings.PRODUCTION_WEBHOOK_BEARER_TOKEN),
            x_api_key == settings.SALES_APP_API_KEY if (x_api_key and settings.SALES_APP_API_KEY) else "N/A",
        )
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
        # Check if order with this external_id already exists
        ext_id = order_data.get("external_id")
        if ext_id:
            existing_order = db.query(ProductionOrder).filter(
                ProductionOrder.external_id == ext_id,
                ProductionOrder.source == OrderSource.SALES_WEBHOOK,
            ).first()
            if existing_order:
                # Treat as a change request — store new payload and notify PMs
                try:
                    from api.models import Notification, User, UserFactory
                    from api.enums import NotificationType, RelatedEntityType, UserRole

                    existing_order.change_req_payload = order_data
                    existing_order.change_req_status = "pending"
                    existing_order.change_req_requested_at = datetime.now(timezone.utc)
                    existing_order.updated_at = datetime.now(timezone.utc)

                    # Notify all PMs for the factory
                    pm_users = (
                        db.query(User)
                        .join(UserFactory, UserFactory.user_id == User.id)
                        .filter(
                            UserFactory.factory_id == existing_order.factory_id,
                            User.role == UserRole.PRODUCTION_MANAGER.value,
                            User.is_active.is_(True),
                        )
                        .all()
                    )
                    for pm in pm_users:
                        notif = Notification(
                            user_id=pm.id,
                            factory_id=existing_order.factory_id,
                            type=NotificationType.STATUS_CHANGE,
                            title=f"Change request: {existing_order.order_number}",
                            message=(
                                f"Sales app sent an updated order for {existing_order.order_number}"
                                + (f" (client: {existing_order.client})" if existing_order.client else "")
                                + ". Review and apply or discard the changes."
                            ),
                            related_entity_type=RelatedEntityType.ORDER,
                            related_entity_id=existing_order.id,
                        )
                        db.add(notif)

                    event.processed = True
                    db.commit()
                    logger.info(
                        "Change request created for order %s (external_id=%s)",
                        existing_order.order_number, ext_id,
                    )
                    factory = db.query(Factory).filter(Factory.id == existing_order.factory_id).first()
                    return {
                        "status": "change_request_created",
                        "order_id": str(existing_order.id),
                        "factory_name": factory.name if factory else None,
                        "factory_location": factory.location if factory else None,
                    }
                except Exception as e:
                    db.rollback()
                    logger.error(f"Failed to create change request for {ext_id}: {e}")
                    event.error_message = str(e)
                    db.add(event)
                    db.commit()
                    raise HTTPException(422, f"Failed to process change request: {e}")

        try:
            order = _create_order_from_webhook(db, order_data, body)
            event.processed = True

            # Schedule deadline estimation BEFORE commit (same db session)
            estimated_completion = _estimate_completion(db, order)

            db.commit()

            # Notify Production Managers of the assigned factory (best-effort, after commit)
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
        # Sales requests cancellation — route through PM review (same as /request-cancellation).
        # We do NOT auto-cancel: PM must approve or reject.
        ext_id = order_data.get("external_id")
        order = db.query(ProductionOrder).filter(
            ProductionOrder.external_id == ext_id,
            ProductionOrder.source == OrderSource.SALES_WEBHOOK,
        ).first()
        if not order:
            event.error_message = f"Order not found: {ext_id}"
            db.commit()
            logger.warning("order_cancel webhook: order not found for external_id=%s", ext_id)
            return {"status": "not_found"}

        if _ev(order.status) == "cancelled":
            # Already cancelled — idempotent
            event.processed = True
            db.commit()
            return {"status": "already_cancelled", "order_id": str(order.id)}

        if order.cancellation_requested and order.cancellation_decision == "pending":
            # Already pending PM review — idempotent
            event.processed = True
            db.commit()
            logger.info(
                "order_cancel webhook: cancellation already pending for order %s (external_id=%s)",
                order.order_number, ext_id,
            )
            return {
                "status": "cancellation_pending_review",
                "order_id": str(order.id),
                "message": "Cancellation request is pending PM review",
            }

        # Create cancellation request → PM must decide
        try:
            from api.models import Notification, User, UserFactory
            from api.enums import NotificationType, RelatedEntityType, UserRole

            order.cancellation_requested = True
            order.cancellation_requested_at = datetime.now(timezone.utc)
            order.cancellation_decision = "pending"
            order.updated_at = datetime.now(timezone.utc)

            # Notify all PMs for the factory
            pm_users = (
                db.query(User)
                .join(UserFactory, UserFactory.user_id == User.id)
                .filter(
                    UserFactory.factory_id == order.factory_id,
                    User.role == UserRole.PRODUCTION_MANAGER.value,
                    User.is_active.is_(True),
                )
                .all()
            )
            for pm in pm_users:
                notif = Notification(
                    user_id=pm.id,
                    factory_id=order.factory_id,
                    type=NotificationType.CANCELLATION_REQUEST,
                    title=f"Cancellation request: {order.order_number}",
                    message=(
                        f"Sales app requested cancellation of order {order.order_number}"
                        + (f" (client: {order.client})" if order.client else "")
                        + f". Current status: {_ev(order.status)}. "
                        "Review the request in the dashboard."
                    ),
                    related_entity_type=RelatedEntityType.ORDER,
                    related_entity_id=order.id,
                )
                db.add(notif)

            event.processed = True
            db.commit()
            logger.info(
                "order_cancel webhook: cancellation request created for order %s (external_id=%s), "
                "notified %d PM(s)",
                order.order_number, ext_id, len(pm_users),
            )
            return {
                "status": "cancellation_requested",
                "order_id": str(order.id),
                "message": "Cancellation request sent to PM for review",
            }
        except Exception as e:
            db.rollback()
            logger.error("order_cancel webhook: failed to create cancellation request for %s: %s", ext_id, e)
            event.error_message = str(e)
            db.add(event)
            db.commit()
            raise HTTPException(422, f"Failed to create cancellation request: {e}")

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

    # --- Helpers to detect service items and stencil/silkscreen ---
    def _is_service_item(idata: dict) -> bool:
        """Detect non-production service items (stencil design, silkscreen design, color matching)."""
        # Explicit flag from Sales
        if idata.get("is_additional_item") or idata.get("is_service"):
            return True
        # Heuristic: items with no size or zero quantity are service items
        app = (idata.get("application") or "").strip().lower()
        desc = (idata.get("description") or "").strip().lower()
        name = (idata.get("name") or "").strip().lower()
        combined = f"{desc} {name} {app}"
        service_keywords = ["design", "matching service", "color matching", "design&production",
                            "design & production", "stencil design", "silkscreen design"]
        return any(kw in combined for kw in service_keywords)

    def _detect_task_type(idata: dict) -> Optional[TaskType]:
        """Determine task type for a service item."""
        app = (idata.get("application") or "").strip().lower()
        desc = (idata.get("description") or idata.get("name") or "").strip().lower()
        combined = f"{desc} {app}"
        if "stencil" in combined:
            return TaskType.STENCIL_ORDER
        if "silkscreen" in combined or "silk_screen" in combined or "silk screen" in combined:
            return TaskType.SILK_SCREEN_ORDER
        if "color matching" in combined or "color_matching" in combined:
            return TaskType.COLOR_MATCHING
        return None

    def _needs_stencil_silkscreen(idata: dict) -> bool:
        """Check if a tile position requires stencil/silkscreen work before glazing."""
        app = (idata.get("application") or "").strip().lower()
        return app in ("stencil", "silkscreen")

    def _needs_color_matching(idata: dict) -> bool:
        """Check if a tile position requires color matching work."""
        app = (idata.get("application") or "").strip().lower()
        desc = (idata.get("description") or "").strip().lower()
        return "color matching" in desc or "color_matching" in app

    items = order_data.get("items", [])
    created_tasks = []  # Track tasks created for linking
    tile_positions = []  # Track tile positions that may need blocking

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

        # --- Route: service item → Task (not a production position) ---
        if _is_service_item(item_data):
            task_type = _detect_task_type(item_data) or TaskType.STENCIL_ORDER
            task = Task(
                id=uuid_mod.uuid4(),
                factory_id=UUID(factory_id),
                type=task_type,
                status=TaskStatus.PENDING,
                assigned_role=UserRole.PRODUCTION_MANAGER,
                related_order_id=order.id,
                blocking=True,
                description=(
                    f"[{task_type.value.replace('_', ' ').title()}] "
                    f"Order {order.order_number}: "
                    f"{item_data.get('application', '')} — "
                    f"{item_data.get('color', '')} "
                    f"{'/ ' + item_data.get('color_2') if item_data.get('color_2') else ''}"
                ).strip(),
                priority=10,
                metadata_json={
                    "order_item_id": str(item.id),
                    "application": item_data.get("application"),
                    "color": item_data.get("color"),
                    "color_2": item_data.get("color_2"),
                    "source": "sales_webhook_auto",
                },
            )
            db.add(task)
            db.flush()
            created_tasks.append(task)
            logger.info(f"Created task {task_type.value} for order {order.order_number}")
            continue  # Don't create position for service items

        # --- Route: tile/product → OrderPosition ---
        # Determine initial status
        if is_stock_collection(item_data.get("collection")):
            initial_status = PositionStatus.TRANSFERRED_TO_SORTING
        elif _needs_stencil_silkscreen(item_data):
            initial_status = PositionStatus.AWAITING_STENCIL_SILKSCREEN
        elif _needs_color_matching(item_data):
            initial_status = PositionStatus.AWAITING_COLOR_MATCHING
        else:
            initial_status = PositionStatus.PLANNED

        # Compute next position_number for this order (sequential within order)
        from sqlalchemy import func as _func
        _max_pn = db.query(_func.max(OrderPosition.position_number)).filter(
            OrderPosition.order_id == order.id,
            OrderPosition.parent_position_id.is_(None),
        ).scalar()
        _next_pn = (_max_pn or 0) + 1

        position = OrderPosition(
            id=uuid_mod.uuid4(),
            order_id=order.id,
            order_item_id=item.id,
            factory_id=UUID(factory_id),
            status=initial_status,
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
            position_number=_next_pn,
        )
        db.add(position)
        db.flush()
        tile_positions.append(position)

    # Link blocking tasks to their tile positions (same order)
    for task in created_tasks:
        if task.type in (TaskType.STENCIL_ORDER, TaskType.SILK_SCREEN_ORDER):
            # Find positions that need stencil/silkscreen in this order
            for pos in tile_positions:
                if pos.status == PositionStatus.AWAITING_STENCIL_SILKSCREEN:
                    task.related_position_id = pos.id
                    break
        elif task.type == TaskType.COLOR_MATCHING:
            for pos in tile_positions:
                if pos.status == PositionStatus.AWAITING_COLOR_MATCHING:
                    task.related_position_id = pos.id
                    break

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


def _estimate_completion(db: Session, order: ProductionOrder) -> Optional[str]:
    """
    Estimate completion date for an order.
    Uses the same db session as the caller to avoid detached object errors.
    When schedule_estimation stub is off, uses real calculation.
    """
    if not _stubs_state["schedule_estimation"]:
        try:
            from business.services.schedule_estimation import calculate_schedule_deadline
            calculate_schedule_deadline(db, order)
            if order.schedule_deadline:
                return str(order.schedule_deadline)
        except Exception as e:
            logger.warning(f"Schedule estimation failed, falling back: {e}")

    # Fallback: return final_deadline if available, else None
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
