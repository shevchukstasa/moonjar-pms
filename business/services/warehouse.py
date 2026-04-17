"""
Warehouse Operations service.
Business Logic: §28

Two main workflows:
1. receive_material — warehouse receives material, routes through approval based on ReceivingSetting
2. pm_approve_receipt — PM approves/rejects/partially accepts a pending receipt
"""
from uuid import UUID
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
import logging

from sqlalchemy.orm import Session

from api.models import (
    MaterialStock, MaterialTransaction, Material, Task,
    ReceivingSetting, MaterialDefectThreshold,
)
from api.enums import (
    TransactionType, TaskType, TaskStatus, UserRole,
    NotificationType, RelatedEntityType,
)
from business.services.notifications import notify_pm, notify_role

logger = logging.getLogger("moonjar.warehouse")


def receive_material(
    db: Session,
    factory_id: UUID,
    material_id: UUID,
    quantity: float,
    quality_notes: Optional[str] = None,
    defect_percent: float = 0.0,
    received_by_user_id: Optional[UUID] = None,
    force_auto_approve: bool = False,
) -> dict:
    """
    Warehouse receives material, optionally requires PM approval.

    Approval modes (from ReceivingSetting):
    - 'all': PM approves every delivery — transaction created but stock NOT updated.
    - 'auto': auto-approve if defect_percent <= threshold; otherwise route to PM.

    ``force_auto_approve=True`` bypasses the gate entirely. Reserved for trusted
    flows where the same user is initiating the receipt (e.g. delivery scan
    "Create & receive" — there is nothing for a separate PM to approve).

    Returns dict with keys: transaction_id, auto_approved, task_id (optional).
    """
    # Validate material exists
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise ValueError(f"Material {material_id} not found")

    # Determine approval mode for this factory
    setting = (
        db.query(ReceivingSetting)
        .filter(ReceivingSetting.factory_id == factory_id)
        .first()
    )
    approval_mode = setting.approval_mode if setting else "all"

    # Decide whether to auto-approve
    auto_approved = bool(force_auto_approve)
    if not auto_approved and approval_mode == "auto":
        threshold = (
            db.query(MaterialDefectThreshold)
            .filter(MaterialDefectThreshold.material_id == material_id)
            .first()
        )
        max_defect = float(threshold.max_defect_percent) if threshold else 3.0
        if defect_percent <= max_defect:
            auto_approved = True

    # Create the transaction
    now = datetime.now(timezone.utc)
    txn = MaterialTransaction(
        material_id=material_id,
        factory_id=factory_id,
        type=TransactionType.RECEIVE,
        quantity=Decimal(str(quantity)),
        notes=quality_notes,
        created_by=received_by_user_id,
        defect_percent=Decimal(str(defect_percent)) if defect_percent else None,
        quality_notes=quality_notes,
        approval_status="approved" if auto_approved else "pending",
        approved_at=now if auto_approved else None,
        accepted_quantity=Decimal(str(quantity)) if auto_approved else None,
    )
    db.add(txn)
    db.flush()  # get txn.id

    result = {
        "transaction_id": txn.id,
        "auto_approved": auto_approved,
        "task_id": None,
    }

    if auto_approved:
        # Update stock balance immediately
        _update_stock_balance(db, factory_id, material_id, Decimal(str(quantity)))

        # Notify PM as info only
        notify_pm(
            db=db,
            factory_id=factory_id,
            type=NotificationType.MATERIAL_RECEIVED.value,
            title=f"Material auto-received: {material.name}",
            message=(
                f"Qty: {quantity}, defect: {defect_percent}%"
                + (f" — {quality_notes}" if quality_notes else "")
            ),
            related_entity_type=RelatedEntityType.MATERIAL.value,
            related_entity_id=material_id,
        )
    else:
        # Create approval task for PM
        task = Task(
            factory_id=factory_id,
            type=TaskType.MATERIAL_RECEIVING,
            status=TaskStatus.PENDING,
            assigned_role=UserRole.PRODUCTION_MANAGER,
            blocking=False,
            description=(
                f"Approve material receipt: {material.name}, "
                f"qty={quantity}, defect={defect_percent}%"
                + (f", notes: {quality_notes}" if quality_notes else "")
            ),
            priority=1,
            metadata_json={
                "transaction_id": str(txn.id),
                "material_id": str(material_id),
                "quantity": quantity,
                "defect_percent": defect_percent,
            },
        )
        db.add(task)
        db.flush()

        result["task_id"] = task.id

        # Notify PM about pending approval
        notify_pm(
            db=db,
            factory_id=factory_id,
            type=NotificationType.TASK_ASSIGNED.value,
            title=f"Material receipt pending approval: {material.name}",
            message=(
                f"Qty: {quantity}, defect: {defect_percent}%. "
                "Please review and approve/reject."
            ),
            related_entity_type=RelatedEntityType.TASK.value,
            related_entity_id=task.id,
        )

    db.commit()
    return result


def pm_approve_receipt(
    db: Session,
    transaction_id: UUID,
    user_id: UUID,
    decision: str = "accept",
    accepted_quantity: Optional[float] = None,
    notes: Optional[str] = None,
) -> MaterialTransaction:
    """
    PM approves/rejects/partially accepts a pending material receipt.

    Args:
        decision: 'accept', 'reject', or 'partial'
        accepted_quantity: required for 'partial', optional for 'accept'
            (defaults to original quantity)
        notes: optional PM notes

    Returns the updated MaterialTransaction.
    """
    if decision not in ("accept", "reject", "partial"):
        raise ValueError(f"Invalid decision: {decision}. Must be 'accept', 'reject', or 'partial'.")

    # Find the transaction
    txn = db.query(MaterialTransaction).filter(MaterialTransaction.id == transaction_id).first()
    if not txn:
        raise ValueError(f"Transaction {transaction_id} not found")

    if txn.approval_status != "pending":
        raise ValueError(
            f"Transaction {transaction_id} is already '{txn.approval_status}', cannot approve/reject again."
        )

    now = datetime.now(timezone.utc)
    original_qty = float(txn.quantity)

    # Find related task
    task = (
        db.query(Task)
        .filter(
            Task.type == TaskType.MATERIAL_RECEIVING,
            Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS]),
        )
        .filter(
            Task.metadata_json["transaction_id"].astext == str(transaction_id)
        )
        .first()
    )

    if decision == "accept":
        qty_to_add = Decimal(str(accepted_quantity)) if accepted_quantity is not None else txn.quantity
        _update_stock_balance(db, txn.factory_id, txn.material_id, qty_to_add)

        txn.approval_status = "approved"
        txn.approved_by = user_id
        txn.approved_at = now
        txn.accepted_quantity = qty_to_add
        if notes:
            txn.notes = (txn.notes + f"\nPM: {notes}") if txn.notes else f"PM: {notes}"

        if accepted_quantity is not None and accepted_quantity < original_qty:
            diff = original_qty - accepted_quantity
            logger.info(
                f"Transaction {transaction_id}: accepted {accepted_quantity} of {original_qty} "
                f"(difference: {diff})"
            )

        if task:
            task.status = TaskStatus.DONE
            task.completed_at = now

    elif decision == "reject":
        txn.approval_status = "rejected"
        txn.approved_by = user_id
        txn.approved_at = now
        txn.accepted_quantity = Decimal("0")
        if notes:
            txn.notes = (txn.notes + f"\nPM rejected: {notes}") if txn.notes else f"PM rejected: {notes}"

        if task:
            task.status = TaskStatus.CANCELLED
            task.completed_at = now

        # Notify warehouse workers about rejection
        material = db.query(Material).filter(Material.id == txn.material_id).first()
        material_name = material.name if material else "Unknown"
        notify_role(
            db=db,
            factory_id=txn.factory_id,
            role=UserRole.WAREHOUSE,
            type=NotificationType.MATERIAL_RECEIVED.value,
            title=f"Material receipt rejected: {material_name}",
            message=f"Qty: {original_qty} was rejected by PM." + (f" Reason: {notes}" if notes else ""),
            related_entity_type=RelatedEntityType.MATERIAL.value,
            related_entity_id=txn.material_id,
        )

    elif decision == "partial":
        if accepted_quantity is None:
            raise ValueError("accepted_quantity is required for partial acceptance")
        if accepted_quantity <= 0 or accepted_quantity >= original_qty:
            raise ValueError(
                f"For partial acceptance, accepted_quantity must be between 0 and {original_qty} (exclusive)"
            )

        qty_to_add = Decimal(str(accepted_quantity))
        _update_stock_balance(db, txn.factory_id, txn.material_id, qty_to_add)

        txn.approval_status = "partial"
        txn.approved_by = user_id
        txn.approved_at = now
        txn.accepted_quantity = qty_to_add
        diff = original_qty - accepted_quantity
        partial_note = f"Partial acceptance: {accepted_quantity} of {original_qty} (rejected {diff})"
        if notes:
            partial_note += f". PM notes: {notes}"
        txn.notes = (txn.notes + f"\n{partial_note}") if txn.notes else partial_note

        logger.info(f"Transaction {transaction_id}: partial accept {accepted_quantity}/{original_qty}")

        if task:
            task.status = TaskStatus.DONE
            task.completed_at = now

    db.commit()
    db.refresh(txn)
    return txn


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
