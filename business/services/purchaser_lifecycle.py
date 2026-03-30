"""
Purchaser Lifecycle Service.
Business Logic: auto-transitions, lead-time tracking, overdue detection.

Called from:
  - materials router (on warehouse receive transaction)
  - purchaser router (on manual status changes)
  - APScheduler (overdue check cron)
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID
import logging

from sqlalchemy.orm import Session
from sqlalchemy import and_

from api.models import (
    MaterialPurchaseRequest,
    Supplier,
    SupplierLeadTime,
    Material,
    User,
    UserFactory,
)
from api.enums import PurchaseStatus, UserRole, NotificationType, RelatedEntityType

logger = logging.getLogger("moonjar.purchaser_lifecycle")


# ── Auto-transition on warehouse material receipt ─────────────────────────

def on_material_received(
    db: Session,
    material_id: UUID,
    supplier_id: Optional[UUID],
    factory_id: UUID,
    quantity: Decimal,
    received_date: Optional[date] = None,
) -> list[dict]:
    """
    Auto-update purchase requests when material is received at warehouse.

    Finds matching open purchase requests (status in sent / in_transit)
    for the given material + supplier + factory and transitions them.

    Returns list of updated PR summaries (for logging / response enrichment).
    """
    received_date = received_date or date.today()
    updated = []

    # Build query for matching open PRs
    q = db.query(MaterialPurchaseRequest).filter(
        MaterialPurchaseRequest.factory_id == factory_id,
        MaterialPurchaseRequest.status.in_([
            PurchaseStatus.SENT.value,
            PurchaseStatus.IN_TRANSIT.value,
        ]),
    )
    if supplier_id:
        q = q.filter(MaterialPurchaseRequest.supplier_id == supplier_id)

    # Order by oldest first so we match the earliest PO
    candidates = q.order_by(MaterialPurchaseRequest.created_at.asc()).all()

    for pr in candidates:
        # Check if this PR contains the received material
        if not _pr_contains_material(pr, str(material_id)):
            continue

        # Transition to received
        pr.status = PurchaseStatus.RECEIVED.value
        pr.actual_delivery_date = received_date
        pr.updated_at = datetime.now(timezone.utc)

        # Calculate lead time variance
        lead_time_info = _calculate_lead_time(pr, received_date)

        # Update supplier lead time stats
        if pr.supplier_id and lead_time_info.get("actual_days") is not None:
            _update_supplier_lead_time_internal(
                db,
                supplier_id=pr.supplier_id,
                material_id=material_id,
                actual_days=lead_time_info["actual_days"],
            )

        # Notify purchaser
        _notify_on_received(db, pr, lead_time_info)

        # Notify PM
        _notify_pm_material_received(db, pr, material_id, quantity)

        updated.append({
            "pr_id": str(pr.id),
            "new_status": "received",
            "actual_delivery_date": received_date.isoformat(),
            **lead_time_info,
        })

        logger.info(
            f"PR {str(pr.id)[:8]} auto-transitioned to received "
            f"(material={str(material_id)[:8]}, lead_time={lead_time_info})"
        )

        # Only match one PR per receive event (first-in-first-out)
        break

    if updated:
        db.flush()

    return updated


def _pr_contains_material(pr: MaterialPurchaseRequest, material_id_str: str) -> bool:
    """Check if PR's materials_json contains the given material_id."""
    mats = pr.materials_json
    if not mats:
        return False
    if isinstance(mats, list):
        return any(str(m.get("material_id", "")) == material_id_str for m in mats)
    if isinstance(mats, dict):
        # Could be {"material_id": ..., ...} or {"items": [...]}
        items = mats.get("items", [])
        if items:
            return any(str(m.get("material_id", "")) == material_id_str for m in items)
        return str(mats.get("material_id", "")) == material_id_str
    return False


def _calculate_lead_time(pr: MaterialPurchaseRequest, received_date: date) -> dict:
    """Calculate actual lead time and variance from expected."""
    info: dict = {"actual_days": None, "expected_days": None, "variance_days": None}

    if pr.ordered_at:
        actual_days = (received_date - pr.ordered_at).days
        info["actual_days"] = actual_days

        if pr.expected_delivery_date:
            expected_days = (pr.expected_delivery_date - pr.ordered_at).days
            info["expected_days"] = expected_days
            info["variance_days"] = actual_days - expected_days  # positive = late

    return info


# ── Supplier lead time auto-adjustment ────────────────────────────────────

def update_supplier_lead_time(
    db: Session,
    supplier_id: UUID,
    material_id: UUID,
    actual_days: int,
) -> Optional[dict]:
    """
    Public API: Update supplier's average lead time from actual delivery data.
    Uses exponential moving average with sample_count weighting.

    Returns updated stats dict or None.
    """
    return _update_supplier_lead_time_internal(db, supplier_id, material_id, actual_days)


def _update_supplier_lead_time_internal(
    db: Session,
    supplier_id: UUID,
    material_id: UUID,
    actual_days: int,
) -> Optional[dict]:
    """Internal: update SupplierLeadTime record with new observation."""
    # Get material type for the lead time record
    mat = db.query(Material).filter(Material.id == material_id).first()
    if not mat:
        return None

    mat_type = mat.material_type if hasattr(mat, "material_type") else "other"
    if hasattr(mat_type, "value"):
        mat_type = mat_type.value

    # Find or create SupplierLeadTime record
    slt = db.query(SupplierLeadTime).filter(
        SupplierLeadTime.supplier_id == supplier_id,
        SupplierLeadTime.material_type == mat_type,
    ).first()

    if not slt:
        # Create new record
        slt = SupplierLeadTime(
            supplier_id=supplier_id,
            material_type=mat_type,
            default_lead_time_days=actual_days,
            avg_actual_lead_time_days=Decimal(str(actual_days)),
            sample_count=1,
            last_updated=datetime.now(timezone.utc),
        )
        db.add(slt)
    else:
        # Exponential moving average: weight recent deliveries more
        # EMA = old_avg * (n / (n+1)) + new_val * (1 / (n+1))
        n = slt.sample_count or 0
        old_avg = float(slt.avg_actual_lead_time_days or slt.default_lead_time_days)

        if n == 0:
            new_avg = float(actual_days)
        else:
            # Cap at 20 samples for EMA smoothing
            weight = min(n, 20)
            new_avg = (old_avg * weight + actual_days) / (weight + 1)

        slt.avg_actual_lead_time_days = Decimal(str(round(new_avg, 1)))
        slt.sample_count = n + 1
        slt.last_updated = datetime.now(timezone.utc)

    db.flush()

    return {
        "supplier_id": str(supplier_id),
        "material_type": mat_type,
        "avg_lead_time_days": float(slt.avg_actual_lead_time_days),
        "sample_count": slt.sample_count,
    }


# ── Overdue detection ─────────────────────────────────────────────────────

def get_overdue_requests(db: Session, factory_id: Optional[UUID] = None) -> list:
    """Find purchase requests past their expected delivery date."""
    today = date.today()
    q = db.query(MaterialPurchaseRequest).filter(
        MaterialPurchaseRequest.status.in_([
            PurchaseStatus.SENT.value,
            PurchaseStatus.IN_TRANSIT.value,
        ]),
        MaterialPurchaseRequest.expected_delivery_date < today,
    )
    if factory_id:
        q = q.filter(MaterialPurchaseRequest.factory_id == factory_id)
    return q.order_by(MaterialPurchaseRequest.expected_delivery_date.asc()).all()


def check_and_notify_overdue(db: Session) -> int:
    """
    Cron-callable: find all overdue PRs and create alerts.
    Returns count of overdue PRs found.
    """
    overdue = get_overdue_requests(db)
    today = date.today()

    for pr in overdue:
        days_overdue = (today - pr.expected_delivery_date).days if pr.expected_delivery_date else 0
        _notify_overdue(db, pr, days_overdue)

    if overdue:
        db.flush()

    return len(overdue)


# ── Dashboard stats helpers ───────────────────────────────────────────────

def compute_enhanced_stats(db: Session, factory_id: Optional[UUID] = None) -> dict:
    """
    Compute enhanced purchaser dashboard stats:
      - overdue_count
      - avg_lead_time_days (this month)
      - on_time_pct (this month)
    """
    today = date.today()
    first_of_month = today.replace(day=1)

    base = db.query(MaterialPurchaseRequest)
    if factory_id:
        base = base.filter(MaterialPurchaseRequest.factory_id == factory_id)

    # Overdue: sent/in_transit past expected date
    overdue_count = base.filter(
        MaterialPurchaseRequest.status.in_([
            PurchaseStatus.SENT.value,
            PurchaseStatus.IN_TRANSIT.value,
        ]),
        MaterialPurchaseRequest.expected_delivery_date < today,
    ).count()

    # This month's completed deliveries (received/closed with actual_delivery_date this month)
    completed_this_month = base.filter(
        MaterialPurchaseRequest.status.in_([
            PurchaseStatus.RECEIVED.value,
            PurchaseStatus.CLOSED.value,
        ]),
        MaterialPurchaseRequest.actual_delivery_date >= first_of_month,
        MaterialPurchaseRequest.ordered_at.isnot(None),
    ).all()

    lead_times = []
    on_time_count = 0
    total_with_expected = 0

    for pr in completed_this_month:
        if pr.ordered_at and pr.actual_delivery_date:
            actual_days = (pr.actual_delivery_date - pr.ordered_at).days
            lead_times.append(actual_days)

            if pr.expected_delivery_date:
                total_with_expected += 1
                if pr.actual_delivery_date <= pr.expected_delivery_date:
                    on_time_count += 1

    avg_lead_time_days = round(sum(lead_times) / len(lead_times), 1) if lead_times else None
    on_time_pct = round(on_time_count / total_with_expected * 100, 1) if total_with_expected > 0 else None

    return {
        "overdue_count": overdue_count,
        "avg_lead_time_days": avg_lead_time_days,
        "on_time_pct": on_time_pct,
        "completed_this_month": len(completed_this_month),
    }


# ── Notification helpers (private) ────────────────────────────────────────

def _notify_on_approved(db: Session, pr: MaterialPurchaseRequest):
    """Notify purchaser role: PR approved, please order."""
    from business.services.notifications import notify_role
    try:
        notify_role(
            db=db,
            factory_id=pr.factory_id,
            role=UserRole.PURCHASER,
            type=NotificationType.STATUS_CHANGE.value,
            title="Purchase request approved",
            message=f"PR {str(pr.id)[:8]} approved — please place order with supplier.",
            related_entity_type=RelatedEntityType.MATERIAL.value,
            related_entity_id=pr.id,
        )
    except Exception as e:
        logger.warning(f"Failed to notify purchaser on approval: {e}")


def _notify_on_sent(db: Session, pr: MaterialPurchaseRequest):
    """Notify warehouse: delivery expected on date."""
    from business.services.notifications import notify_role
    try:
        eta = pr.expected_delivery_date.isoformat() if pr.expected_delivery_date else "TBD"
        notify_role(
            db=db,
            factory_id=pr.factory_id,
            role=UserRole.WAREHOUSE,
            type=NotificationType.MATERIAL_RECEIVED.value,
            title="Delivery expected",
            message=f"PR {str(pr.id)[:8]} sent to supplier. Expected delivery: {eta}.",
            related_entity_type=RelatedEntityType.MATERIAL.value,
            related_entity_id=pr.id,
        )
    except Exception as e:
        logger.warning(f"Failed to notify warehouse on sent: {e}")


def _notify_on_in_transit(db: Session, pr: MaterialPurchaseRequest):
    """Notify warehouse: shipment in transit."""
    from business.services.notifications import notify_role
    try:
        eta = pr.expected_delivery_date.isoformat() if pr.expected_delivery_date else "TBD"
        notify_role(
            db=db,
            factory_id=pr.factory_id,
            role=UserRole.WAREHOUSE,
            type=NotificationType.MATERIAL_RECEIVED.value,
            title="Shipment in transit",
            message=f"PR {str(pr.id)[:8]} is in transit. Expected arrival: {eta}.",
            related_entity_type=RelatedEntityType.MATERIAL.value,
            related_entity_id=pr.id,
        )
    except Exception as e:
        logger.warning(f"Failed to notify warehouse on in_transit: {e}")


def _notify_on_received(db: Session, pr: MaterialPurchaseRequest, lead_time_info: dict):
    """Notify purchaser that material was received."""
    from business.services.notifications import notify_role
    try:
        variance = lead_time_info.get("variance_days")
        timing = ""
        if variance is not None:
            if variance > 0:
                timing = f" ({variance}d late)"
            elif variance < 0:
                timing = f" ({abs(variance)}d early)"
            else:
                timing = " (on time)"

        notify_role(
            db=db,
            factory_id=pr.factory_id,
            role=UserRole.PURCHASER,
            type=NotificationType.MATERIAL_RECEIVED.value,
            title="Material received",
            message=f"PR {str(pr.id)[:8]} delivered{timing}.",
            related_entity_type=RelatedEntityType.MATERIAL.value,
            related_entity_id=pr.id,
        )
    except Exception as e:
        logger.warning(f"Failed to notify purchaser on received: {e}")


def _notify_pm_material_received(
    db: Session,
    pr: MaterialPurchaseRequest,
    material_id: UUID,
    quantity: Decimal,
):
    """Notify PM that material was received."""
    from business.services.notifications import notify_pm
    try:
        mat = db.query(Material).filter(Material.id == material_id).first()
        mat_name = mat.name if mat else str(material_id)[:8]
        notify_pm(
            db=db,
            factory_id=pr.factory_id,
            type=NotificationType.MATERIAL_RECEIVED.value,
            title="Material received at warehouse",
            message=f"{mat_name}: {float(quantity)} units received (PR {str(pr.id)[:8]}).",
            related_entity_type=RelatedEntityType.MATERIAL.value,
            related_entity_id=pr.id,
        )
    except Exception as e:
        logger.warning(f"Failed to notify PM on material received: {e}")


def _notify_overdue(db: Session, pr: MaterialPurchaseRequest, days_overdue: int):
    """Alert purchaser + PM about overdue delivery."""
    from business.services.notifications import notify_role, notify_pm
    try:
        msg = (
            f"PR {str(pr.id)[:8]} is {days_overdue}d overdue "
            f"(expected {pr.expected_delivery_date.isoformat()})."
        )
        notify_role(
            db=db,
            factory_id=pr.factory_id,
            role=UserRole.PURCHASER,
            type=NotificationType.ALERT.value,
            title="Overdue delivery",
            message=msg,
            related_entity_type=RelatedEntityType.MATERIAL.value,
            related_entity_id=pr.id,
        )
        notify_pm(
            db=db,
            factory_id=pr.factory_id,
            type=NotificationType.ALERT.value,
            title="Overdue delivery alert",
            message=msg,
            related_entity_type=RelatedEntityType.MATERIAL.value,
            related_entity_id=pr.id,
        )
    except Exception as e:
        logger.warning(f"Failed to notify on overdue PR: {e}")
