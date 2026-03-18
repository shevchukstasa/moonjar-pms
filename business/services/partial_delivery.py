"""
Partial Delivery service.
Business Logic: §22

Handles scenarios where a purchase delivery arrives with less than ordered:
1. Records what was received, updates stock, calculates deficits
2. Creates PM task for deficit resolution
3. PM resolves: reorder same supplier / reorder other / skip
"""
from uuid import UUID
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
import logging

from sqlalchemy.orm import Session

from api.models import (
    Material,
    MaterialStock,
    MaterialTransaction,
    MaterialPurchaseRequest,
    Task,
)
from api.enums import (
    TransactionType,
    TaskType,
    TaskStatus,
    PurchaseStatus,
    UserRole,
    NotificationType,
    RelatedEntityType,
)
from business.services.notifications import notify_pm

logger = logging.getLogger("moonjar.partial_delivery")


# ────────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────────


def handle_partial_delivery(
    db: Session,
    purchase_request_id: UUID,
    received_items: list[dict],
    pm_user_id: UUID,
) -> dict:
    """
    Accept partial delivery, update stock, create PM task for deficit decision.

    Args:
        purchase_request_id: the MaterialPurchaseRequest being delivered
        received_items: list of {material_id, received_qty, defect_qty, notes}
        pm_user_id: user performing the receiving

    Returns:
        Summary dict with received, deficits, task_id.
    """
    pr = (
        db.query(MaterialPurchaseRequest)
        .filter(MaterialPurchaseRequest.id == purchase_request_id)
        .first()
    )
    if not pr:
        raise ValueError(f"PurchaseRequest {purchase_request_id} not found")

    if pr.status not in (PurchaseStatus.SENT, PurchaseStatus.APPROVED, PurchaseStatus.PARTIALLY_RECEIVED):
        raise ValueError(
            f"PurchaseRequest {purchase_request_id} has status '{pr.status.value}', "
            "cannot receive delivery"
        )

    ordered_materials = pr.materials_json or []
    ordered_map: dict[str, float] = {}
    for item in ordered_materials:
        mid = str(item.get("material_id", ""))
        qty = float(item.get("quantity", 0))
        ordered_map[mid] = ordered_map.get(mid, 0) + qty

    now = datetime.now(timezone.utc)
    summary_items = []
    deficit_items = []
    total_received = 0
    total_deficit = 0

    for item in received_items:
        material_id = UUID(str(item["material_id"]))
        received_qty = float(item.get("received_qty", 0))
        defect_qty = float(item.get("defect_qty", 0))
        item_notes = item.get("notes")

        material = db.query(Material).filter(Material.id == material_id).first()
        if not material:
            raise ValueError(f"Material {material_id} not found")

        good_qty = received_qty - defect_qty
        if good_qty < 0:
            raise ValueError(
                f"Material {material_id}: defect_qty ({defect_qty}) "
                f"exceeds received_qty ({received_qty})"
            )

        # Create MaterialTransaction for the received amount
        txn = MaterialTransaction(
            material_id=material_id,
            factory_id=pr.factory_id,
            type=TransactionType.RECEIVE,
            quantity=Decimal(str(received_qty)),
            notes=item_notes,
            created_by=pm_user_id,
            defect_percent=(
                Decimal(str(round(defect_qty / received_qty * 100, 2)))
                if received_qty > 0 else None
            ),
            quality_notes=item_notes,
            approval_status="approved",
            approved_at=now,
            accepted_quantity=Decimal(str(good_qty)),
        )
        db.add(txn)
        db.flush()

        # Update stock with good quantity only
        if good_qty > 0:
            _update_stock_balance(db, pr.factory_id, material_id, Decimal(str(good_qty)))

        logger.info(
            "Partial delivery PR=%s material=%s received=%s defect=%s good=%s",
            purchase_request_id, material_id, received_qty, defect_qty, good_qty,
        )

        # Calculate deficit
        ordered_qty = ordered_map.get(str(material_id), 0)
        deficit = ordered_qty - received_qty
        if deficit < 0:
            deficit = 0

        item_summary = {
            "material_id": str(material_id),
            "material_name": material.name,
            "ordered_qty": ordered_qty,
            "received_qty": received_qty,
            "defect_qty": defect_qty,
            "good_qty": good_qty,
            "deficit": deficit,
        }
        summary_items.append(item_summary)
        total_received += good_qty

        if deficit > 0:
            deficit_items.append(item_summary)
            total_deficit += deficit

    # Update received_quantity_json on purchase request
    pr.received_quantity_json = [
        {
            "material_id": s["material_id"],
            "received_qty": s["received_qty"],
            "defect_qty": s["defect_qty"],
            "good_qty": s["good_qty"],
        }
        for s in summary_items
    ]
    pr.actual_delivery_date = now.date()

    task_id = None

    if deficit_items:
        # Mark as partially received
        pr.status = PurchaseStatus.PARTIALLY_RECEIVED
        pr.updated_at = now

        # Create PM task for deficit resolution
        task = Task(
            factory_id=pr.factory_id,
            type=TaskType.MATERIAL_ORDER,
            status=TaskStatus.PENDING,
            assigned_role=UserRole.PRODUCTION_MANAGER,
            blocking=False,
            description=(
                f"Partial delivery for PR #{str(purchase_request_id)[:8]}: "
                f"{len(deficit_items)} material(s) with deficit. "
                "Decide: reorder_same, reorder_other, or skip."
            ),
            priority=2,
            metadata_json={
                "purchase_request_id": str(purchase_request_id),
                "supplier_id": str(pr.supplier_id) if pr.supplier_id else None,
                "factory_id": str(pr.factory_id),
                "deficit_items": [
                    {
                        "material_id": d["material_id"],
                        "material_name": d["material_name"],
                        "ordered_qty": d["ordered_qty"],
                        "received_qty": d["received_qty"],
                        "deficit": d["deficit"],
                    }
                    for d in deficit_items
                ],
                "suggested_actions": [
                    "reorder_same — re-order deficit from same supplier",
                    "reorder_other — re-order deficit from alternative supplier",
                    "skip — accept the loss and close",
                ],
            },
        )
        db.add(task)
        db.flush()
        task_id = task.id

        # Notify PM
        notify_pm(
            db=db,
            factory_id=pr.factory_id,
            type=NotificationType.TASK_ASSIGNED.value,
            title="Partial delivery — deficit decision needed",
            message=(
                f"PR #{str(purchase_request_id)[:8]}: "
                f"received {total_received}, deficit {total_deficit}. "
                f"{len(deficit_items)} item(s) need resolution."
            ),
            related_entity_type=RelatedEntityType.TASK.value,
            related_entity_id=task.id,
        )
        logger.info(
            "Created deficit task %s for PR %s (%d items)",
            task.id, purchase_request_id, len(deficit_items),
        )
    else:
        # Everything received — mark as fully received
        pr.status = PurchaseStatus.RECEIVED
        pr.updated_at = now

        notify_pm(
            db=db,
            factory_id=pr.factory_id,
            type=NotificationType.MATERIAL_RECEIVED.value,
            title="Purchase delivery fully received",
            message=f"PR #{str(purchase_request_id)[:8]}: all items received.",
            related_entity_type=RelatedEntityType.MATERIAL.value,
            related_entity_id=purchase_request_id,
        )

    db.commit()

    return {
        "purchase_request_id": str(purchase_request_id),
        "status": pr.status.value,
        "items": summary_items,
        "deficit_items": deficit_items,
        "total_received": total_received,
        "total_deficit": total_deficit,
        "task_id": str(task_id) if task_id else None,
    }


def pm_resolve_partial_delivery(
    db: Session,
    task_id: UUID,
    decision: str,
    pm_user_id: UUID,
    alt_supplier_id: Optional[UUID] = None,
) -> dict:
    """
    PM decides what to do with the deficit from a partial delivery.

    Args:
        task_id: the deficit-resolution Task
        decision: "reorder_same" | "reorder_other" | "skip"
        pm_user_id: PM making the decision
        alt_supplier_id: required when decision == "reorder_other"

    Returns:
        Summary dict with decision outcome.
    """
    valid_decisions = ("reorder_same", "reorder_other", "skip")
    if decision not in valid_decisions:
        raise ValueError(
            f"Invalid decision '{decision}'. Must be one of: {', '.join(valid_decisions)}"
        )

    if decision == "reorder_other" and not alt_supplier_id:
        raise ValueError("alt_supplier_id is required for 'reorder_other' decision")

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise ValueError(f"Task {task_id} not found")

    if task.status not in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS):
        raise ValueError(f"Task {task_id} has status '{task.status.value}', cannot resolve")

    meta = task.metadata_json or {}
    pr_id = meta.get("purchase_request_id")
    original_supplier_id = meta.get("supplier_id")
    factory_id_str = meta.get("factory_id")
    deficit_items = meta.get("deficit_items", [])

    if not pr_id or not factory_id_str:
        raise ValueError(f"Task {task_id} metadata missing purchase_request_id or factory_id")

    factory_id = UUID(factory_id_str)
    now = datetime.now(timezone.utc)
    new_pr_id = None

    if decision in ("reorder_same", "reorder_other"):
        # Determine supplier
        if decision == "reorder_same":
            supplier_id = UUID(original_supplier_id) if original_supplier_id else None
        else:
            supplier_id = alt_supplier_id

        # Build materials_json for the new purchase request
        new_materials = [
            {
                "material_id": d["material_id"],
                "quantity": d["deficit"],
                "material_name": d.get("material_name", ""),
            }
            for d in deficit_items
            if d.get("deficit", 0) > 0
        ]

        if not new_materials:
            raise ValueError("No deficit items to reorder")

        new_pr = MaterialPurchaseRequest(
            factory_id=factory_id,
            supplier_id=supplier_id,
            materials_json=new_materials,
            status=PurchaseStatus.PENDING,
            source="partial_reorder",
            notes=(
                f"Reorder from partial delivery (original PR: {pr_id[:8]}). "
                f"Decision: {decision} by PM."
            ),
        )
        db.add(new_pr)
        db.flush()
        new_pr_id = new_pr.id

        logger.info(
            "PM resolved partial delivery: decision=%s, new PR=%s, supplier=%s, items=%d",
            decision, new_pr_id, supplier_id, len(new_materials),
        )
    else:
        # skip — accept the loss
        logger.info(
            "PM resolved partial delivery: decision=skip for PR %s, deficit accepted",
            pr_id,
        )

    # Close the original deficit task
    task.status = TaskStatus.DONE
    task.completed_at = now
    task.metadata_json = {
        **meta,
        "resolution": {
            "decision": decision,
            "resolved_by": str(pm_user_id),
            "resolved_at": now.isoformat(),
            "new_purchase_request_id": str(new_pr_id) if new_pr_id else None,
            "alt_supplier_id": str(alt_supplier_id) if alt_supplier_id else None,
        },
    }

    # Update original purchase request — mark as fully received (deficit handled)
    if pr_id:
        original_pr = (
            db.query(MaterialPurchaseRequest)
            .filter(MaterialPurchaseRequest.id == UUID(pr_id))
            .first()
        )
        if original_pr and original_pr.status == PurchaseStatus.PARTIALLY_RECEIVED:
            original_pr.status = PurchaseStatus.RECEIVED
            original_pr.updated_at = now

    db.commit()

    return {
        "task_id": str(task_id),
        "decision": decision,
        "new_purchase_request_id": str(new_pr_id) if new_pr_id else None,
        "deficit_items_count": len(deficit_items),
        "status": "resolved",
    }


# ────────────────────────────────────────────────────────────────
# Private helpers
# ────────────────────────────────────────────────────────────────


def _update_stock_balance(
    db: Session,
    factory_id: UUID,
    material_id: UUID,
    quantity: Decimal,
) -> MaterialStock:
    """Add quantity to MaterialStock balance, creating stock record if needed."""
    stock = (
        db.query(MaterialStock)
        .filter(
            MaterialStock.factory_id == factory_id,
            MaterialStock.material_id == material_id,
        )
        .first()
    )
    if not stock:
        stock = MaterialStock(
            material_id=material_id,
            factory_id=factory_id,
            balance=Decimal("0"),
        )
        db.add(stock)
        db.flush()

    stock.balance = stock.balance + quantity
    stock.updated_at = datetime.now(timezone.utc)
    return stock
