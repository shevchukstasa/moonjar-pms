"""
Change Request service — handles Sales webhook order_update events.
PM must approve/reject changes. Does NOT auto-apply.

Architecture note:
- ProductionOrder has change_req_* fields for the "lightweight" flow (single pending CR per order).
- ProductionOrderChangeRequest table stores the full audit trail (one row per CR).
- Both are kept in sync: change_req_status on order mirrors the latest CR status.
"""

import logging
import uuid as uuid_mod
from datetime import datetime, timezone
from typing import Optional, Union, List
from uuid import UUID

from sqlalchemy.orm import Session

from api.enums import ChangeRequestStatus, NotificationType, RelatedEntityType, UserRole

logger = logging.getLogger("moonjar.change_request_service")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _snapshot_order(order) -> dict:
    """Capture current order state relevant to Sales changes."""
    return {
        "client": order.client,
        "client_location": order.client_location,
        "sales_manager_name": order.sales_manager_name,
        "sales_manager_contact": order.sales_manager_contact,
        "final_deadline": str(order.final_deadline) if order.final_deadline else None,
        "desired_delivery_date": str(order.desired_delivery_date) if order.desired_delivery_date else None,
        "mandatory_qc": order.mandatory_qc,
        "notes": order.notes,
    }


def _compute_diff(old: dict, new: dict) -> dict:
    """Compute a diff dict: only fields that changed."""
    diff = {}
    for key in set(old) | set(new):
        old_val = old.get(key)
        new_val = new.get(key)
        if old_val != new_val:
            diff[key] = {"old": old_val, "new": new_val}
    return diff


def _notify_pms(db: Session, order, cr_id: UUID, message_suffix: str = "") -> int:
    """Create in-app Notification for all PMs assigned to the order's factory."""
    from api.models import Notification, User, UserFactory

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
            type=NotificationType.STATUS_CHANGE,
            title=f"Change request: {order.order_number}",
            message=(
                f"Sales app sent updated order data for {order.order_number}"
                + (f" (client: {order.client})" if order.client else "")
                + f". Review and approve or reject.{message_suffix}"
            ),
            related_entity_type=RelatedEntityType.ORDER,
            related_entity_id=order.id,
        )
        db.add(notif)

    return len(pm_users)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_change_request_from_webhook(
    db: Session,
    order,
    new_order_data: dict,
    source: str = "sales_webhook",
):
    """
    Called when event_type='order_update' is received from Sales webhook.

    Creates a ProductionOrderChangeRequest record with status PENDING,
    and syncs change_req_* fields on ProductionOrder.
    Does NOT modify the order itself.

    Returns the created ProductionOrderChangeRequest instance.
    """
    from api.models import ProductionOrderChangeRequest

    # 1. Snapshot current order state
    old_data = _snapshot_order(order)

    # 2. Snapshot proposed state from webhook payload
    new_snapshot = {
        "client": new_order_data.get("client"),
        "client_location": new_order_data.get("client_location"),
        "sales_manager_name": new_order_data.get("sales_manager_name"),
        "sales_manager_contact": new_order_data.get("sales_manager_contact"),
        "final_deadline": new_order_data.get("final_deadline"),
        "desired_delivery_date": new_order_data.get("desired_delivery_date"),
        "mandatory_qc": new_order_data.get("mandatory_qc"),
        "notes": new_order_data.get("notes"),
        # Also include items summary for display in PM dashboard
        "items": new_order_data.get("items", []),
        "items_count": len(new_order_data.get("items", [])),
    }

    # 3. Compute diff (scalar fields only; items handled separately)
    diff = _compute_diff(
        {k: v for k, v in old_data.items()},
        {k: v for k, v in new_snapshot.items() if k not in ("items", "items_count")},
    )

    # If items changed, include summary in diff
    old_items_count = db.query(__import__('api.models', fromlist=['ProductionOrderItem'])
                               .ProductionOrderItem).filter_by(order_id=order.id).count()
    new_items_count = len(new_order_data.get("items", []))
    if old_items_count != new_items_count:
        diff["items_count"] = {"old": old_items_count, "new": new_items_count}

    # 4. Close any previous pending CRs for this order (superseded by newer one)
    (
        db.query(ProductionOrderChangeRequest)
        .filter(
            ProductionOrderChangeRequest.order_id == order.id,
            ProductionOrderChangeRequest.status == ChangeRequestStatus.PENDING,
        )
        .update(
            {
                "status": ChangeRequestStatus.REJECTED,
                "notes": "Superseded by newer change request from Sales",
                "reviewed_at": datetime.now(timezone.utc),
            },
            synchronize_session="fetch",
        )
    )

    # 5. Create new ChangeRequest record
    cr = ProductionOrderChangeRequest(
        id=uuid_mod.uuid4(),
        order_id=order.id,
        change_type="order_update",
        diff_json={
            "source": source,
            "diff": diff,
            "old_data": old_data,
            "new_data": new_snapshot,
            "full_payload": new_order_data,
        },
        status=ChangeRequestStatus.PENDING,
        notes=None,
    )
    db.add(cr)
    db.flush()  # get cr.id

    # 6. Sync change_req_* fields on the order (lightweight flow for dashboard)
    order.change_req_payload = new_order_data
    order.change_req_status = "pending"
    order.change_req_requested_at = datetime.now(timezone.utc)
    order.updated_at = datetime.now(timezone.utc)

    # 7. Notify PMs via in-app notifications
    pm_count = _notify_pms(db, order, cr.id)
    logger.info(
        "Change request %s created for order %s (external_id=%s), notified %d PM(s)",
        cr.id, order.order_number, order.external_id, pm_count,
    )

    return cr


def approve_change_request(
    db: Session,
    order,
    cr,
    apply_to_positions: Union[str, List[str]] = "all",
    notes: Optional[str] = None,
    approved_by_id: Optional[UUID] = None,
) -> dict:
    """
    PM approves the change request.

    Applies scalar field changes from cr.diff_json['new_data'] to the order.
    Items are NOT auto-recreated (PM must handle item changes manually if needed).
    Marks CR as APPROVED and clears change_req_* on order.

    Returns summary dict.
    """
    if cr.status != ChangeRequestStatus.PENDING:
        raise ValueError(f"Change request {cr.id} is not pending (status={cr.status})")

    diff_data = cr.diff_json or {}
    new_data = diff_data.get("new_data", {})
    full_payload = diff_data.get("full_payload", {})

    # Apply scalar fields
    UPDATABLE_FIELDS = (
        "client", "client_location", "sales_manager_name", "sales_manager_contact",
        "final_deadline", "desired_delivery_date", "mandatory_qc", "notes",
    )
    applied_fields = []
    for field in UPDATABLE_FIELDS:
        if field in new_data and new_data[field] is not None:
            val = new_data[field]
            # Parse date strings
            if field in ("final_deadline", "desired_delivery_date") and isinstance(val, str):
                try:
                    from datetime import date as date_type
                    val = date_type.fromisoformat(val)
                except (ValueError, TypeError):
                    val = None
            if val is not None:
                setattr(order, field, val)
                applied_fields.append(field)

    # Track partial apply info
    partial_log = {
        "apply_to_positions": apply_to_positions,
        "applied_fields": applied_fields,
        "items_applied": False,
        "notes": notes,
    }

    # Mark CR approved
    cr.status = ChangeRequestStatus.APPROVED
    cr.reviewed_by = approved_by_id
    cr.reviewed_at = datetime.now(timezone.utc)
    cr.notes = notes

    # Clear lightweight fields on order
    order.change_req_status = "approved"
    order.change_req_decided_at = datetime.now(timezone.utc)
    order.change_req_decided_by = approved_by_id
    order.change_req_payload = None
    order.updated_at = datetime.now(timezone.utc)

    logger.info(
        "Change request %s APPROVED for order %s by user %s, applied fields: %s",
        cr.id, order.order_number, approved_by_id, applied_fields,
    )

    return {
        "cr_id": str(cr.id),
        "order_id": str(order.id),
        "order_number": order.order_number,
        "status": "approved",
        "applied_fields": applied_fields,
        "partial_log": partial_log,
    }


def reject_change_request(
    db: Session,
    order,
    cr,
    reason: str,
    rejected_by_id: Optional[UUID] = None,
) -> dict:
    """
    PM rejects the change request.

    Discards proposed changes. Marks CR as REJECTED.
    Returns summary dict.
    """
    if cr.status != ChangeRequestStatus.PENDING:
        raise ValueError(f"Change request {cr.id} is not pending (status={cr.status})")

    cr.status = ChangeRequestStatus.REJECTED
    cr.reviewed_by = rejected_by_id
    cr.reviewed_at = datetime.now(timezone.utc)
    cr.notes = reason

    # Clear lightweight fields on order
    order.change_req_status = "rejected"
    order.change_req_decided_at = datetime.now(timezone.utc)
    order.change_req_decided_by = rejected_by_id
    order.change_req_payload = None
    order.updated_at = datetime.now(timezone.utc)

    logger.info(
        "Change request %s REJECTED for order %s by user %s, reason: %s",
        cr.id, order.order_number, rejected_by_id, reason,
    )

    return {
        "cr_id": str(cr.id),
        "order_id": str(order.id),
        "order_number": order.order_number,
        "status": "rejected",
        "reason": reason,
    }
