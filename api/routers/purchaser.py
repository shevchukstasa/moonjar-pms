"""Purchaser router — purchase requests with status workflow, stats, deliveries."""

from datetime import datetime, date, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.models import (
    MaterialPurchaseRequest, Supplier, Material, MaterialStock, MaterialTransaction, User,
)
from api.enums import PurchaseStatus
from api.schemas import MaterialPurchaseRequestCreate, MaterialPurchaseRequestUpdate

router = APIRouter()


# ── helpers ──────────────────────────────────────────────────────────────

def _ev(val):
    return val.value if hasattr(val, "value") else str(val) if val else None


def _serialize_request(pr, db) -> dict:
    supplier_name = None
    if pr.supplier_id:
        sup = db.query(Supplier).filter(Supplier.id == pr.supplier_id).first()
        supplier_name = sup.name if sup else None

    approved_by_name = None
    if pr.approved_by:
        user = db.query(User).filter(User.id == pr.approved_by).first()
        approved_by_name = user.name if user else None

    return {
        "id": str(pr.id),
        "factory_id": str(pr.factory_id),
        "supplier_id": str(pr.supplier_id) if pr.supplier_id else None,
        "supplier_name": supplier_name,
        "materials_json": pr.materials_json,
        "status": _ev(pr.status),
        "source": pr.source,
        "approved_by": str(pr.approved_by) if pr.approved_by else None,
        "approved_by_name": approved_by_name,
        "ordered_at": pr.ordered_at.isoformat() if pr.ordered_at else None,
        "expected_delivery_date": pr.expected_delivery_date.isoformat() if pr.expected_delivery_date else None,
        "actual_delivery_date": pr.actual_delivery_date.isoformat() if pr.actual_delivery_date else None,
        "received_quantity_json": pr.received_quantity_json,
        "notes": pr.notes,
        "created_at": pr.created_at.isoformat() if pr.created_at else None,
        "updated_at": pr.updated_at.isoformat() if pr.updated_at else None,
    }


# ── Pydantic models ─────────────────────────────────────────────────────

class StatusChangeInput(BaseModel):
    status: str  # "approved" | "sent" | "in_transit" | "received" | "closed"
    notes: Optional[str] = None
    expected_delivery_date: Optional[str] = None  # ISO date
    actual_delivery_date: Optional[str] = None  # ISO date


# ── endpoints ────────────────────────────────────────────────────────────

@router.get("", response_model=dict)
async def list_purchaser(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    factory_id: UUID | None = None,
    status: str | None = None,
    supplier_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(MaterialPurchaseRequest)

    if factory_id:
        query = query.filter(MaterialPurchaseRequest.factory_id == factory_id)
    if status:
        statuses = [s.strip() for s in status.split(",")]
        query = query.filter(MaterialPurchaseRequest.status.in_(statuses))
    if supplier_id:
        query = query.filter(MaterialPurchaseRequest.supplier_id == supplier_id)

    total = query.count()
    items = query.order_by(
        MaterialPurchaseRequest.created_at.desc()
    ).offset((page - 1) * per_page).limit(per_page).all()

    return {
        "items": [_serialize_request(pr, db) for pr in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/stats")
async def get_purchaser_stats(
    factory_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Dashboard KPI stats with lead-time analytics."""
    from business.services.purchaser_lifecycle import compute_enhanced_stats

    base = db.query(MaterialPurchaseRequest)
    if factory_id:
        base = base.filter(MaterialPurchaseRequest.factory_id == factory_id)

    active = base.filter(
        MaterialPurchaseRequest.status.in_(["pending", "approved", "sent", "in_transit"])
    ).count()

    pending = base.filter(MaterialPurchaseRequest.status == "pending").count()
    awaiting = base.filter(
        MaterialPurchaseRequest.status.in_(["sent", "in_transit"])
    ).count()

    today = date.today()
    overdue = base.filter(
        MaterialPurchaseRequest.status.in_(["sent", "in_transit"]),
        MaterialPurchaseRequest.expected_delivery_date < today,
    ).count()

    # Enhanced stats: lead time, on-time %
    enhanced = compute_enhanced_stats(db, factory_id)

    return {
        "active_requests": active,
        "pending_approval": pending,
        "awaiting_delivery": awaiting,
        "overdue_deliveries": overdue,
        # Enhanced metrics
        "overdue_count": enhanced["overdue_count"],
        "avg_lead_time_days": enhanced["avg_lead_time_days"],
        "on_time_pct": enhanced["on_time_pct"],
        "completed_this_month": enhanced["completed_this_month"],
    }


@router.get("/deliveries")
async def list_deliveries(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    factory_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Completed or partially received deliveries."""
    query = db.query(MaterialPurchaseRequest).filter(
        MaterialPurchaseRequest.status.in_(["partially_received", "received", "closed"])
    )
    if factory_id:
        query = query.filter(MaterialPurchaseRequest.factory_id == factory_id)

    total = query.count()
    items = query.order_by(
        MaterialPurchaseRequest.actual_delivery_date.desc().nullslast(),
        MaterialPurchaseRequest.updated_at.desc(),
    ).offset((page - 1) * per_page).limit(per_page).all()

    return {
        "items": [_serialize_request(pr, db) for pr in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/deficits")
async def get_material_deficits(
    factory_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Material deficits — materials where current balance < min_balance."""
    query = db.query(MaterialStock, Material).join(
        Material, MaterialStock.material_id == Material.id
    ).filter(MaterialStock.balance < MaterialStock.min_balance)

    if factory_id:
        query = query.filter(MaterialStock.factory_id == factory_id)

    rows = query.order_by(
        (MaterialStock.min_balance - MaterialStock.balance).desc()
    ).all()

    items = []
    for stock, mat in rows:
        deficit = float(stock.min_balance - stock.balance)
        # Count open orders that use this material type (approximate)
        open_orders_count = 0
        items.append({
            "material_id": str(mat.id),
            "material_code": mat.material_code,
            "material_name": mat.name,
            "material_type": mat.material_type,
            "unit": mat.unit,
            "factory_id": str(stock.factory_id),
            "current_balance": float(stock.balance),
            "min_balance": float(stock.min_balance),
            "deficit": round(deficit, 3),
            "avg_daily_consumption": float(stock.avg_daily_consumption or 0),
            "days_until_stockout": (
                round(float(stock.balance) / float(stock.avg_daily_consumption), 1)
                if stock.avg_daily_consumption and float(stock.avg_daily_consumption) > 0
                else None
            ),
        })

    return {
        "items": items,
        "total": len(items),
    }


@router.get("/consolidation-suggestions")
async def get_consolidation_suggestions(
    factory_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return suggestions for consolidating approved PRs by supplier."""
    from business.services.purchase_consolidation import get_consolidation_suggestions as _get_suggestions

    if not factory_id:
        raise HTTPException(400, "factory_id is required for consolidation suggestions")

    suggestions = _get_suggestions(db, factory_id)
    return {
        "items": suggestions,
        "total": len(suggestions),
    }


class ConsolidateInput(BaseModel):
    pr_ids: list[UUID]


@router.post("/consolidate")
async def consolidate_requests(
    data: ConsolidateInput,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Execute consolidation of specified PR IDs into a single PR."""
    from business.services.purchase_consolidation import consolidate_purchase_requests

    try:
        result = consolidate_purchase_requests(db, data.pr_ids, current_user.id)
        db.commit()
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/lead-times")
async def get_lead_times(
    supplier_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Supplier lead times from supplier_lead_times table."""
    from api.models import SupplierLeadTime, Supplier

    query = db.query(SupplierLeadTime, Supplier).join(
        Supplier, SupplierLeadTime.supplier_id == Supplier.id
    )
    if supplier_id:
        query = query.filter(SupplierLeadTime.supplier_id == supplier_id)

    rows = query.order_by(Supplier.name, SupplierLeadTime.material_type).all()

    items = []
    for lt, sup in rows:
        items.append({
            "id": str(lt.id),
            "supplier_id": str(sup.id),
            "supplier_name": sup.name,
            "material_type": lt.material_type,
            "default_lead_time_days": lt.default_lead_time_days,
            "avg_actual_lead_time_days": float(lt.avg_actual_lead_time_days) if lt.avg_actual_lead_time_days else None,
            "sample_count": lt.sample_count,
            "last_updated": lt.last_updated.isoformat() if lt.last_updated else None,
            "reliability_pct": (
                round(100.0 * min(lt.default_lead_time_days / float(lt.avg_actual_lead_time_days), 1.0), 1)
                if lt.avg_actual_lead_time_days and float(lt.avg_actual_lead_time_days) > 0
                else None
            ),
        })

    return {
        "items": items,
        "total": len(items),
    }


@router.get("/{item_id}")
async def get_purchaser_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    pr = db.query(MaterialPurchaseRequest).filter(
        MaterialPurchaseRequest.id == item_id
    ).first()
    if not pr:
        raise HTTPException(404, "Purchase request not found")
    return _serialize_request(pr, db)


@router.post("", status_code=201)
async def create_purchaser_item(
    data: MaterialPurchaseRequestCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = MaterialPurchaseRequest(**data.model_dump())
    if not item.source:
        item.source = "manual"
    if not item.status:
        item.status = PurchaseStatus.PENDING
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_request(item, db)


@router.patch("/{item_id}")
async def update_purchaser_item(
    item_id: UUID,
    data: MaterialPurchaseRequestUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(MaterialPurchaseRequest).filter(
        MaterialPurchaseRequest.id == item_id
    ).first()
    if not item:
        raise HTTPException(404, "Purchase request not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    item.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)
    return _serialize_request(item, db)


@router.patch("/{item_id}/status")
async def change_request_status(
    item_id: UUID,
    data: StatusChangeInput,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Full status workflow:
      pending → approved → sent → in_transit → received → closed
                                  └→ partially_received → received
    """
    from business.services.purchaser_lifecycle import (
        _notify_on_approved,
        _notify_on_sent,
        _notify_on_in_transit,
        _notify_on_received,
        _calculate_lead_time,
        update_supplier_lead_time,
    )

    pr = db.query(MaterialPurchaseRequest).filter(
        MaterialPurchaseRequest.id == item_id
    ).first()
    if not pr:
        raise HTTPException(404, "Purchase request not found")

    current_status = _ev(pr.status)
    new_status = data.status

    # Validate transitions
    valid_transitions = {
        "pending": ["approved"],
        "approved": ["sent"],
        "sent": ["in_transit", "partially_received", "received"],
        "in_transit": ["partially_received", "received"],
        "partially_received": ["received"],
        "received": ["closed"],
    }

    if current_status not in valid_transitions:
        raise HTTPException(400, f"Cannot transition from '{current_status}'")
    if new_status not in valid_transitions[current_status]:
        raise HTTPException(
            400,
            f"Invalid transition: {current_status} → {new_status}. "
            f"Allowed: {valid_transitions[current_status]}"
        )

    pr.status = new_status
    pr.updated_at = datetime.now(timezone.utc)

    if data.notes:
        pr.notes = data.notes

    if new_status == "approved":
        pr.approved_by = current_user.id
        _notify_on_approved(db, pr)

    elif new_status == "sent":
        pr.ordered_at = date.today()
        if data.expected_delivery_date:
            pr.expected_delivery_date = date.fromisoformat(data.expected_delivery_date)
        _notify_on_sent(db, pr)

    elif new_status == "in_transit":
        if data.expected_delivery_date:
            pr.expected_delivery_date = date.fromisoformat(data.expected_delivery_date)
        _notify_on_in_transit(db, pr)

    elif new_status == "received":
        pr.actual_delivery_date = date.today()
        if data.actual_delivery_date:
            pr.actual_delivery_date = date.fromisoformat(data.actual_delivery_date)

        # Calculate lead time
        lead_time_info = _calculate_lead_time(pr, pr.actual_delivery_date)
        _notify_on_received(db, pr, lead_time_info)

        # Update supplier lead time stats
        if pr.supplier_id and lead_time_info.get("actual_days") is not None:
            # Use first material_id from PR for lead time tracking
            first_mat_id = _get_first_material_id(pr)
            if first_mat_id:
                update_supplier_lead_time(db, pr.supplier_id, first_mat_id, lead_time_info["actual_days"])

        # Auto-receive: update material stock balances
        if pr.materials_json and isinstance(pr.materials_json, list):
            for item in pr.materials_json:
                mat_id = item.get("material_id")
                qty = item.get("quantity", 0)
                if mat_id and qty > 0:
                    stock = db.query(MaterialStock).filter(
                        MaterialStock.material_id == mat_id,
                        MaterialStock.factory_id == pr.factory_id,
                    ).first()
                    if stock:
                        stock.balance += Decimal(str(qty))
                        stock.updated_at = datetime.now(timezone.utc)
                        t = MaterialTransaction(
                            material_id=mat_id,
                            factory_id=pr.factory_id,
                            type="receive",
                            quantity=Decimal(str(qty)),
                            notes=f"Auto-received from PO {str(pr.id)[:8]}",
                            created_by=current_user.id,
                        )
                        db.add(t)

    elif new_status == "closed":
        pass  # Final state, no side effects

    db.commit()
    db.refresh(pr)
    return _serialize_request(pr, db)


def _get_first_material_id(pr: MaterialPurchaseRequest) -> Optional[UUID]:
    """Extract first material_id from PR's materials_json."""
    mats = pr.materials_json
    if isinstance(mats, list) and mats:
        mid = mats[0].get("material_id")
        if mid:
            try:
                from uuid import UUID as _UUID
                return _UUID(str(mid))
            except (ValueError, TypeError):
                return None
    if isinstance(mats, dict):
        items = mats.get("items", [])
        if items:
            mid = items[0].get("material_id")
        else:
            mid = mats.get("material_id")
        if mid:
            try:
                from uuid import UUID as _UUID
                return _UUID(str(mid))
            except (ValueError, TypeError):
                return None
    return None


@router.delete("/{item_id}", status_code=204)
async def delete_purchaser_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(MaterialPurchaseRequest).filter(
        MaterialPurchaseRequest.id == item_id
    ).first()
    if not item:
        raise HTTPException(404, "Purchase request not found")
    db.delete(item)
    db.commit()
