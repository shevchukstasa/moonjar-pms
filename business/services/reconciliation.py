"""
Stage Reconciliation service.
Business Logic: §13, §26
"""
from uuid import UUID
from datetime import date, datetime, timezone
from typing import Optional
import logging

from sqlalchemy.orm import Session

from api.models import (
    StageReconciliationLog, Notification, User, Material, MaterialStock,
    MaterialTransaction,
)
from api.enums import (
    NotificationType, RelatedEntityType, UserRole, TransactionType,
)

logger = logging.getLogger("moonjar.reconciliation")


def _get_pm_user_id(db: Session, factory_id: UUID) -> Optional[UUID]:
    """Get production manager user ID for the factory."""
    from api.models import UserFactory
    uf = db.query(UserFactory).join(User).filter(
        UserFactory.factory_id == factory_id,
        User.role == UserRole.PRODUCTION_MANAGER.value,
        User.is_active.is_(True),
    ).first()
    return uf.user_id if uf else None


def reconcile_stage_transition(
    db: Session,
    factory_id: UUID,
    batch_id: Optional[UUID],
    stage_from: str,
    stage_to: str,
    input_count: int,
    outputs: dict,
) -> dict:
    """Verify tile counts at stage transitions. Alert PM on discrepancy."""
    output_good = outputs.get("good", 0)
    output_defect = outputs.get("defect", 0)
    output_write_off = outputs.get("write_off", 0)
    output_total = output_good + output_defect + output_write_off
    discrepancy = input_count - output_total
    is_balanced = discrepancy == 0

    # Create reconciliation log
    log = StageReconciliationLog(
        factory_id=factory_id,
        batch_id=batch_id,
        stage_from=stage_from,
        stage_to=stage_to,
        input_count=input_count,
        output_good=output_good,
        output_defect=output_defect,
        output_write_off=output_write_off,
        discrepancy=discrepancy,
        is_balanced=is_balanced,
        alert_sent=False,
    )
    db.add(log)
    db.flush()

    if not is_balanced:
        log.alert_sent = True

        # Alert PM
        pm_user_id = _get_pm_user_id(db, factory_id)
        if pm_user_id:
            notif = Notification(
                user_id=pm_user_id,
                factory_id=factory_id,
                type=NotificationType.RECONCILIATION_DISCREPANCY,
                title=f"Tile count mismatch: {stage_from} → {stage_to}",
                message=(
                    f"Input: {input_count}, Output: {output_total}, "
                    f"Discrepancy: {discrepancy} tiles"
                ),
                related_entity_type=RelatedEntityType.KILN if batch_id else RelatedEntityType.ORDER,
                related_entity_id=batch_id,
            )
            db.add(notif)

        logger.warning(
            "Reconciliation discrepancy: %s → %s, input=%d, output=%d, diff=%d",
            stage_from, stage_to, input_count, output_total, discrepancy,
        )

    db.flush()

    return {
        "log_id": str(log.id),
        "is_balanced": is_balanced,
        "discrepancy": discrepancy,
        "input_count": input_count,
        "output_total": output_total,
        "output_good": output_good,
        "output_defect": output_defect,
        "output_write_off": output_write_off,
        "alert_sent": log.alert_sent,
    }


def inventory_reconciliation(
    db: Session,
    factory_id: UUID,
    section_id: UUID,
    counted_items: list[dict],
) -> dict:
    """Periodic inventory reconciliation: counted vs system.

    counted_items = [{"material_id": "uuid", "actual_quantity": 42.0}, ...]
    """
    adjustments_count = 0
    total_positive = 0.0
    total_negative = 0.0
    details = []

    for item in counted_items:
        material_id = item.get("material_id")
        actual_qty = float(item.get("actual_quantity", 0))

        material = db.query(Material).get(material_id)
        if not material:
            logger.warning("Material %s not found during reconciliation", material_id)
            continue

        stock = db.query(MaterialStock).filter(
            MaterialStock.material_id == material_id,
            MaterialStock.factory_id == factory_id,
        ).first()
        if not stock:
            logger.warning("MaterialStock not found for %s in factory %s", material_id, factory_id)
            continue

        system_qty = float(stock.balance or 0)
        difference = actual_qty - system_qty

        if abs(difference) < 0.001:
            details.append({
                "material_id": str(material_id),
                "material_name": material.name,
                "system_quantity": system_qty,
                "actual_quantity": actual_qty,
                "difference": 0,
                "adjusted": False,
            })
            continue

        # Create adjustment transaction
        txn = MaterialTransaction(
            material_id=material.id,
            factory_id=factory_id,
            type=TransactionType.MANUAL_WRITE_OFF,
            quantity=difference,
            notes=f"Inventory reconciliation: section {section_id}",
        )
        db.add(txn)

        # Update stock balance
        stock.balance = actual_qty
        stock.updated_at = datetime.now(timezone.utc)

        adjustments_count += 1
        if difference > 0:
            total_positive += difference
        else:
            total_negative += abs(difference)

        details.append({
            "material_id": str(material_id),
            "material_name": material.name,
            "system_quantity": system_qty,
            "actual_quantity": actual_qty,
            "difference": round(difference, 3),
            "adjusted": True,
        })

    db.flush()

    logger.info(
        "Inventory reconciliation: %d adjustments, +%.2f / -%.2f",
        adjustments_count, total_positive, total_negative,
    )

    return {
        "adjustments_count": adjustments_count,
        "total_positive": round(total_positive, 3),
        "total_negative": round(total_negative, 3),
        "details": details,
    }
