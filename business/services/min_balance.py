"""
Min Balance Auto-Calculation service.
Business Logic: §18
"""
from uuid import UUID
from datetime import date, datetime, timedelta
from decimal import Decimal
from math import ceil
from typing import Optional, Dict, Any, List

import sqlalchemy as sa
from sqlalchemy.orm import Session

from api.models import (
    MaterialStock, MaterialTransaction, Material, MaterialPurchaseRequest,
    Supplier, ReferenceAuditLog,
)
from api.enums import (
    TransactionType, PurchaseStatus, ReferenceAction, MaterialType,
)


# Default lead times by material type (days)
_DEFAULT_LEAD_TIMES: Dict[str, int] = {
    "stone": 7,
    "pigment": 14,
    "frit": 14,
    "oxide_carbonate": 14,
    "packaging": 3,
    "consumable": 3,
    "other": 7,
}


def get_effective_lead_time(db: Session, material_id: UUID, factory_id: UUID) -> int:
    """
    Returns lead time in days for a material.  Priority:
    1. Avg actual delivery time from MaterialPurchaseRequest history (last 6 months)
    2. Material's supplier default_lead_time_days
    3. Hardcoded defaults by material_type
    """
    six_months_ago = datetime.utcnow() - timedelta(days=180)

    # --- Priority 1: historical purchase requests with actual delivery ---
    # MaterialPurchaseRequest.materials_json is a list of dicts containing material_id.
    # We fetch all RECEIVED requests for this factory in the last 6 months,
    # then filter in Python for ones that include our material.
    requests = (
        db.query(MaterialPurchaseRequest)
        .filter(
            MaterialPurchaseRequest.factory_id == factory_id,
            MaterialPurchaseRequest.status.in_([
                PurchaseStatus.RECEIVED,
                PurchaseStatus.PARTIALLY_RECEIVED,
            ]),
            MaterialPurchaseRequest.actual_delivery_date.isnot(None),
            MaterialPurchaseRequest.created_at >= six_months_ago,
        )
        .all()
    )

    material_id_str = str(material_id)
    delivery_days: List[int] = []

    for req in requests:
        # Check if this request contains our material
        mats = req.materials_json
        if not isinstance(mats, list):
            continue
        for item in mats:
            if isinstance(item, dict) and str(item.get("material_id", "")) == material_id_str:
                # Calculate actual lead time: actual_delivery_date - created_at date
                created_date = req.created_at.date() if isinstance(req.created_at, datetime) else req.created_at
                delivery_date = req.actual_delivery_date
                if isinstance(delivery_date, datetime):
                    delivery_date = delivery_date.date()
                delta = (delivery_date - created_date).days
                if delta > 0:
                    delivery_days.append(delta)
                break

    if delivery_days:
        avg_days = sum(delivery_days) / len(delivery_days)
        return max(1, ceil(avg_days))

    # --- Priority 2: supplier default lead time ---
    material = db.query(Material).filter(Material.id == material_id).first()
    if material and material.supplier_id:
        supplier = db.query(Supplier).filter(Supplier.id == material.supplier_id).first()
        if supplier and supplier.default_lead_time_days:
            return int(supplier.default_lead_time_days)

    # --- Priority 3: defaults by material type ---
    if material:
        return _DEFAULT_LEAD_TIMES.get(material.material_type, 7)

    return 7


def recalculate_min_balance_recommendations(
    db: Session, factory_id: UUID
) -> Dict[str, Any]:
    """
    Daily job: for each MaterialStock in the factory, recalculate consumption
    metrics and min_balance_recommended.

    Returns: {"updated": N, "alerts": [{"material_id": ..., "name": ..., "balance": ..., "min_balance": ...}, ...]}
    """
    stocks = (
        db.query(MaterialStock)
        .filter(MaterialStock.factory_id == factory_id)
        .all()
    )

    ninety_days_ago = datetime.utcnow() - timedelta(days=90)
    updated_count = 0
    alerts: List[Dict[str, Any]] = []

    for stock in stocks:
        # Sum CONSUME transactions for this material+factory over last 90 days
        total_consumed = (
            db.query(sa.func.coalesce(sa.func.sum(MaterialTransaction.quantity), 0))
            .filter(
                MaterialTransaction.material_id == stock.material_id,
                MaterialTransaction.factory_id == factory_id,
                MaterialTransaction.type == TransactionType.CONSUME,
                MaterialTransaction.created_at >= ninety_days_ago,
            )
            .scalar()
        )
        total_consumed = Decimal(str(total_consumed))

        # Calculate number of days in the window (capped at 90)
        days_in_window = 90
        avg_daily = total_consumed / days_in_window if days_in_window > 0 else Decimal("0")
        avg_monthly = avg_daily * 30

        # Get effective lead time
        lead_time = get_effective_lead_time(db, stock.material_id, factory_id)

        # min_balance_recommended = lead_time * avg_daily * 1.2 (20% safety buffer)
        min_balance_recommended = Decimal(str(lead_time)) * avg_daily * Decimal("1.2")

        # Update the stock record
        stock.avg_daily_consumption = avg_daily
        stock.avg_monthly_consumption = avg_monthly
        stock.min_balance_recommended = min_balance_recommended

        # If auto mode, also update min_balance
        if stock.min_balance_auto:
            stock.min_balance = min_balance_recommended

        stock.updated_at = datetime.utcnow()
        updated_count += 1

        # Check if current balance is below min_balance
        current_balance = Decimal(str(stock.balance)) if stock.balance else Decimal("0")
        effective_min = Decimal(str(stock.min_balance)) if stock.min_balance else Decimal("0")

        if current_balance < effective_min and effective_min > 0:
            # Fetch material name for the alert
            material = db.query(Material).filter(Material.id == stock.material_id).first()
            alerts.append({
                "material_id": str(stock.material_id),
                "name": material.name if material else "Unknown",
                "balance": float(current_balance),
                "min_balance": float(effective_min),
            })

    db.flush()

    return {"updated": updated_count, "alerts": alerts}


def pm_override_min_balance(
    db: Session,
    material_id: UUID,
    factory_id: UUID,
    new_min_balance: float,
    user_id: UUID,
) -> MaterialStock:
    """
    PM manually sets min_balance for a material.
    Disables auto-calculation and logs the change via ReferenceAuditLog.
    """
    stock = (
        db.query(MaterialStock)
        .filter(
            MaterialStock.material_id == material_id,
            MaterialStock.factory_id == factory_id,
        )
        .first()
    )

    if stock is None:
        raise ValueError(
            f"MaterialStock not found for material_id={material_id}, factory_id={factory_id}"
        )

    old_min_balance = float(stock.min_balance) if stock.min_balance else 0.0
    old_auto = stock.min_balance_auto

    # Apply override
    stock.min_balance = Decimal(str(new_min_balance))
    stock.min_balance_auto = False
    stock.updated_at = datetime.utcnow()

    # Audit log
    audit_entry = ReferenceAuditLog(
        table_name="material_stock",
        record_id=stock.id,
        action=ReferenceAction.UPDATE,
        old_values_json={
            "min_balance": old_min_balance,
            "min_balance_auto": old_auto,
        },
        new_values_json={
            "min_balance": new_min_balance,
            "min_balance_auto": False,
        },
        changed_by=user_id,
    )
    db.add(audit_entry)
    db.flush()

    return stock
