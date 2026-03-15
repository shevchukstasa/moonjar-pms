"""Materials router — inventory, transactions, low-stock, purchase requests,
consumption adjustments.

Material = shared catalog (name, type, unit, supplier).
MaterialStock = per-factory stock (balance, min_balance, consumption).
ConsumptionAdjustment = actual vs expected material usage (PM review).
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
import sqlalchemy as sa
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user, apply_factory_filter
from api.roles import require_management, require_admin
from api.models import (
    Material, MaterialStock, MaterialTransaction,
    MaterialPurchaseRequest, Supplier, User,
    ConsumptionAdjustment, ShapeConsumptionCoefficient,
    OrderPosition, RecipeMaterial, KilnMaintenanceMaterial,
    InventoryReconciliationItem,
    PackagingBoxType, PackagingSpacerRule,
)
from api.enums import PurchaseStatus

router = APIRouter()


# ── helpers ──────────────────────────────────────────────────────────────

def _ev(val):
    return val.value if hasattr(val, "value") else str(val) if val else None


def _next_material_code(db: Session) -> str:
    """Generate the next sequential material code: M-0001, M-0002, ..."""
    from sqlalchemy import func as sa_func
    result = db.query(
        sa_func.max(
            sa_func.cast(
                sa_func.substr(Material.material_code, 3),  # strip "M-"
                sa.Integer,
            )
        )
    ).filter(
        Material.material_code.ilike('M-%'),
    ).scalar()
    next_num = (result or 0) + 1
    return f"M-{next_num:04d}"


def _serialize_material(mat: Material, stock: MaterialStock | None, db: Session) -> dict:
    """Serialize catalog Material + optional per-factory MaterialStock into flat dict."""
    supplier_name = None
    if mat.supplier_id:
        sup = db.query(Supplier).filter(Supplier.id == mat.supplier_id).first()
        supplier_name = sup.name if sup else None

    balance = float(stock.balance or 0) if stock else 0
    min_bal = float(stock.min_balance or 0) if stock else 0

    # Subgroup / group info
    subgroup_id = None
    subgroup_name = None
    group_name = None
    if mat.subgroup_id:
        subgroup_id = str(mat.subgroup_id)
        if hasattr(mat, 'subgroup') and mat.subgroup:
            subgroup_name = mat.subgroup.name
            if mat.subgroup.group:
                group_name = mat.subgroup.group.name

    return {
        "id": str(mat.id),
        "material_code": mat.material_code,
        "stock_id": str(stock.id) if stock else None,
        "name": mat.name,
        "factory_id": str(stock.factory_id) if stock else None,
        "balance": balance,
        "min_balance": min_bal,
        "min_balance_recommended": float(stock.min_balance_recommended) if stock and stock.min_balance_recommended else None,
        "min_balance_auto": stock.min_balance_auto if stock else True,
        "avg_daily_consumption": float(stock.avg_daily_consumption) if stock and stock.avg_daily_consumption else 0,
        "avg_monthly_consumption": float(stock.avg_monthly_consumption) if stock and stock.avg_monthly_consumption else 0,
        "unit": mat.unit,
        "material_type": _ev(mat.material_type),
        "subgroup_id": subgroup_id,
        "subgroup_name": subgroup_name,
        "group_name": group_name,
        "warehouse_section": stock.warehouse_section if stock else None,
        "supplier_id": str(mat.supplier_id) if mat.supplier_id else None,
        "supplier_name": supplier_name,
        "size_id": str(mat.size_id) if mat.size_id else None,
        "is_low_stock": balance < min_bal if min_bal > 0 else False,
        "created_at": mat.created_at.isoformat() if mat.created_at else None,
        "updated_at": (stock.updated_at if stock else mat.updated_at).isoformat() if (stock or mat) else None,
    }


def _serialize_material_aggregate(mat: Material, stocks: list[MaterialStock], db: Session) -> dict:
    """Serialize catalog Material with aggregated data from ALL factory stocks."""
    supplier_name = None
    if mat.supplier_id:
        sup = db.query(Supplier).filter(Supplier.id == mat.supplier_id).first()
        supplier_name = sup.name if sup else None

    total_balance = sum(float(s.balance or 0) for s in stocks)
    total_min_bal = sum(float(s.min_balance or 0) for s in stocks)
    is_low = any(
        float(s.balance or 0) < float(s.min_balance or 0) and float(s.min_balance or 0) > 0
        for s in stocks
    )

    subgroup_id = None
    subgroup_name = None
    group_name = None
    if mat.subgroup_id:
        subgroup_id = str(mat.subgroup_id)
        if hasattr(mat, 'subgroup') and mat.subgroup:
            subgroup_name = mat.subgroup.name
            if mat.subgroup.group:
                group_name = mat.subgroup.group.name

    return {
        "id": str(mat.id),
        "material_code": mat.material_code,
        "stock_id": None,
        "name": mat.name,
        "factory_id": None,  # aggregate mode
        "balance": total_balance,
        "min_balance": total_min_bal,
        "min_balance_recommended": None,
        "min_balance_auto": True,
        "avg_daily_consumption": sum(float(s.avg_daily_consumption or 0) for s in stocks),
        "avg_monthly_consumption": sum(float(s.avg_monthly_consumption or 0) for s in stocks),
        "unit": mat.unit,
        "material_type": _ev(mat.material_type),
        "subgroup_id": subgroup_id,
        "subgroup_name": subgroup_name,
        "group_name": group_name,
        "warehouse_section": stocks[0].warehouse_section if stocks else None,
        "supplier_id": str(mat.supplier_id) if mat.supplier_id else None,
        "supplier_name": supplier_name,
        "size_id": str(mat.size_id) if mat.size_id else None,
        "is_low_stock": is_low,
        "factory_count": len(stocks),
        "created_at": mat.created_at.isoformat() if mat.created_at else None,
        "updated_at": mat.updated_at.isoformat() if mat.updated_at else None,
    }


def _serialize_transaction(t, db) -> dict:
    creator_name = None
    creator_role = None
    if t.created_by:
        user = db.query(User).filter(User.id == t.created_by).first()
        if user:
            creator_name = user.name
            creator_role = _ev(user.role) if user.role else None

    return {
        "id": str(t.id),
        "material_id": str(t.material_id),
        "factory_id": str(t.factory_id) if t.factory_id else None,
        "type": _ev(t.type),
        "quantity": float(t.quantity),
        "related_order_id": str(t.related_order_id) if t.related_order_id else None,
        "related_position_id": str(t.related_position_id) if t.related_position_id else None,
        "reason": _ev(t.reason),
        "notes": t.notes,
        "created_by": str(t.created_by) if t.created_by else None,
        "created_by_name": creator_name,
        "created_by_role": creator_role,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


# ── Pydantic models ─────────────────────────────────────────────────────

class MaterialCreateInput(BaseModel):
    name: str
    factory_id: Optional[UUID] = None  # None → auto-create stock for ALL active factories
    material_type: str = ""
    subgroup_id: Optional[UUID] = None
    unit: str = "pcs"
    balance: float = 0
    min_balance: float = 0
    min_balance_auto: bool = True
    supplier_id: Optional[UUID] = None
    warehouse_section: Optional[str] = "raw_materials"
    size_id: Optional[UUID] = None  # For stone materials — link to sizes reference


class MaterialUpdateInput(BaseModel):
    name: Optional[str] = None
    subgroup_id: Optional[UUID] = None
    balance: Optional[float] = None
    min_balance: Optional[float] = None
    min_balance_auto: Optional[bool] = None
    unit: Optional[str] = None
    warehouse_section: Optional[str] = None
    supplier_id: Optional[UUID] = None
    size_id: Optional[UUID] = None


class TransactionInput(BaseModel):
    material_id: UUID
    factory_id: UUID
    type: str  # "receive" | "manual_write_off"
    quantity: float
    reason: Optional[str] = None
    notes: Optional[str] = None


class PurchaseRequestInput(BaseModel):
    factory_id: UUID
    supplier_id: Optional[UUID] = None
    materials_json: dict
    notes: Optional[str] = None


# ── endpoints ────────────────────────────────────────────────────────────

@router.get("")
async def list_materials(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    factory_id: UUID | None = None,
    material_type: str | None = None,
    subgroup_id: UUID | None = None,
    group_id: UUID | None = None,
    warehouse_section: str | None = None,
    low_stock: bool | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from api.models import MaterialSubgroup, Factory

    # ── Aggregate mode: no factory_id → deduplicated catalog with summed balances ──
    if not factory_id and current_user.role in ("owner", "ceo", "administrator"):
        query = db.query(Material)

        if material_type:
            query = query.filter(Material.material_type == material_type)
        if subgroup_id:
            query = query.filter(Material.subgroup_id == subgroup_id)
        if group_id:
            query = query.join(
                MaterialSubgroup, Material.subgroup_id == MaterialSubgroup.id
            ).filter(MaterialSubgroup.group_id == group_id)
        if search:
            query = query.filter(Material.name.ilike(f"%{search}%"))

        # For low_stock / warehouse_section filters we still need stock join
        if low_stock or warehouse_section:
            query = query.join(MaterialStock, Material.id == MaterialStock.material_id)
            if warehouse_section:
                query = query.filter(MaterialStock.warehouse_section == warehouse_section)
            if low_stock:
                query = query.filter(
                    MaterialStock.balance < MaterialStock.min_balance,
                    MaterialStock.min_balance > 0,
                )
            # Deduplicate after join
            query = query.distinct(Material.id)

        total = query.count()
        mats = query.order_by(Material.name).offset((page - 1) * per_page).limit(per_page).all()

        # Batch-load all stocks for these materials (avoid N+1)
        mat_ids = [m.id for m in mats]
        all_stocks = db.query(MaterialStock).filter(
            MaterialStock.material_id.in_(mat_ids)
        ).all() if mat_ids else []

        stocks_map: dict = {}
        for s in all_stocks:
            stocks_map.setdefault(s.material_id, []).append(s)

        items = [
            _serialize_material_aggregate(mat, stocks_map.get(mat.id, []), db)
            for mat in mats
        ]

        return {"items": items, "total": total, "page": page, "per_page": per_page}

    # ── Per-factory mode (existing behavior) ──
    query = db.query(Material, MaterialStock).outerjoin(
        MaterialStock, Material.id == MaterialStock.material_id
    )
    query = apply_factory_filter(query, current_user, factory_id, MaterialStock)

    if material_type:
        query = query.filter(Material.material_type == material_type)
    if subgroup_id:
        query = query.filter(Material.subgroup_id == subgroup_id)
    if group_id:
        query = query.join(
            MaterialSubgroup, Material.subgroup_id == MaterialSubgroup.id
        ).filter(MaterialSubgroup.group_id == group_id)
    if warehouse_section:
        query = query.filter(MaterialStock.warehouse_section == warehouse_section)
    if search:
        query = query.filter(Material.name.ilike(f"%{search}%"))
    if low_stock:
        query = query.filter(
            MaterialStock.balance < MaterialStock.min_balance,
            MaterialStock.min_balance > 0,
        )

    total = query.count()
    items = query.order_by(Material.name).offset((page - 1) * per_page).limit(per_page).all()

    return {
        "items": [_serialize_material(mat, stock, db) for mat, stock in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/low-stock")
async def get_low_stock(
    factory_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Low stock alerts — accessible to warehouse + purchaser."""
    query = db.query(Material, MaterialStock).join(
        MaterialStock, Material.id == MaterialStock.material_id
    ).filter(
        MaterialStock.balance < MaterialStock.min_balance,
        MaterialStock.min_balance > 0,
    )
    query = apply_factory_filter(query, current_user, factory_id, MaterialStock)

    items = query.order_by(
        (MaterialStock.min_balance - MaterialStock.balance).desc()
    ).all()

    result = []
    for mat, stock in items:
        s = _serialize_material(mat, stock, db)
        s["deficit"] = float(stock.min_balance - stock.balance)
        result.append(s)

    return {"items": result, "total": len(result)}


@router.get("/effective-balance")
async def get_effective_balance(
    factory_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Effective balance = current balance minus reserved for active orders."""
    from api.models import RecipeMaterial, OrderPosition, ProductionOrderItem, Recipe
    from api.enums import PositionStatus

    query = db.query(Material, MaterialStock).join(
        MaterialStock, Material.id == MaterialStock.material_id
    )
    if factory_id:
        query = query.filter(MaterialStock.factory_id == factory_id)
    else:
        query = apply_factory_filter(query, current_user, None, MaterialStock)

    rows = query.all()

    active_statuses = [
        PositionStatus.PLANNED.value,
        PositionStatus.SENT_TO_GLAZING.value,
        PositionStatus.ENGOBE_APPLIED.value,
        PositionStatus.ENGOBE_CHECK.value,
        PositionStatus.GLAZED.value,
        PositionStatus.AWAITING_RECIPE.value,
        PositionStatus.AWAITING_COLOR_MATCHING.value,
    ]

    result = []
    for mat, stock in rows:
        balance = float(stock.balance or 0)

        reserved = 0.0
        try:
            recipe_mats = db.query(RecipeMaterial).filter(
                RecipeMaterial.material_id == mat.id,
            ).all()

            for rm in recipe_mats:
                active_positions = db.query(OrderPosition).join(
                    ProductionOrderItem, OrderPosition.order_item_id == ProductionOrderItem.id
                ).filter(
                    OrderPosition.factory_id == stock.factory_id,
                    OrderPosition.status.in_(active_statuses),
                    ProductionOrderItem.recipe_id == rm.recipe_id,
                ).all()

                for pos in active_positions:
                    qty = float(pos.quantity or 0)
                    recipe_qty = float(rm.quantity_per_unit or 0)
                    reserved += qty * recipe_qty
        except Exception:
            pass

        effective = balance - reserved
        min_bal = float(stock.min_balance or 0)

        result.append({
            "id": str(mat.id),
            "stock_id": str(stock.id),
            "name": mat.name,
            "factory_id": str(stock.factory_id),
            "unit": mat.unit,
            "material_type": _ev(mat.material_type),
            "balance": balance,
            "reserved": round(reserved, 3),
            "effective_balance": round(effective, 3),
            "min_balance": min_bal,
            "is_low_stock": effective < min_bal if min_bal > 0 else False,
        })

    return {"items": result, "total": len(result)}


# ── Consumption Adjustments ─────────────────────────────────────────────
# NOTE: These routes MUST be defined BEFORE /{material_id} to avoid
# "consumption-adjustments" being captured as a UUID path parameter.

def _serialize_adjustment(adj: ConsumptionAdjustment, db: Session) -> dict:
    """Serialize a ConsumptionAdjustment for API response."""
    mat = db.query(Material).filter(Material.id == adj.material_id).first()
    pos = db.query(OrderPosition).filter(OrderPosition.id == adj.position_id).first()

    approver_name = None
    if adj.approved_by:
        user = db.query(User).filter(User.id == adj.approved_by).first()
        approver_name = user.name if user else None

    return {
        "id": str(adj.id),
        "factory_id": str(adj.factory_id),
        "position_id": str(adj.position_id),
        "position_number": pos.position_number if pos else None,
        "order_number": pos.order.order_number if pos and pos.order else None,
        "material_id": str(adj.material_id),
        "material_name": mat.name if mat else None,
        "expected_qty": float(adj.expected_qty),
        "actual_qty": float(adj.actual_qty),
        "variance_pct": float(adj.variance_pct) if adj.variance_pct else None,
        "shape": adj.shape,
        "product_type": adj.product_type,
        "suggested_coefficient": float(adj.suggested_coefficient) if adj.suggested_coefficient else None,
        "status": adj.status,
        "approved_by": str(adj.approved_by) if adj.approved_by else None,
        "approved_by_name": approver_name,
        "approved_at": adj.approved_at.isoformat() if adj.approved_at else None,
        "notes": adj.notes,
        "created_at": adj.created_at.isoformat() if adj.created_at else None,
    }


class AdjustmentDecisionInput(BaseModel):
    notes: Optional[str] = None


@router.get("/consumption-adjustments")
async def list_consumption_adjustments(
    factory_id: UUID | None = None,
    status: str | None = Query(None, description="Filter by status: pending, approved, rejected"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List consumption adjustments — pending corrections for PM review."""
    query = db.query(ConsumptionAdjustment)

    if factory_id:
        query = query.filter(ConsumptionAdjustment.factory_id == factory_id)
    if status:
        query = query.filter(ConsumptionAdjustment.status == status)

    total = query.count()
    items = query.order_by(
        ConsumptionAdjustment.created_at.desc()
    ).offset((page - 1) * per_page).limit(per_page).all()

    return {
        "items": [_serialize_adjustment(a, db) for a in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.post("/consumption-adjustments/{adj_id}/approve")
async def approve_consumption_adjustment(
    adj_id: UUID,
    body: AdjustmentDecisionInput = AdjustmentDecisionInput(),
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Approve a consumption adjustment — updates shape coefficient.

    When approved, if the adjustment has a suggested_coefficient,
    the shape_consumption_coefficients table is updated for future calculations.
    """
    adj = db.query(ConsumptionAdjustment).filter(ConsumptionAdjustment.id == adj_id).first()
    if not adj:
        raise HTTPException(404, "Adjustment not found")
    if adj.status != "pending":
        raise HTTPException(400, f"Adjustment is already {adj.status}")

    adj.status = "approved"
    adj.approved_by = current_user.id
    adj.approved_at = datetime.now(timezone.utc)
    if body.notes:
        adj.notes = body.notes

    # Update shape coefficient if suggested
    if adj.suggested_coefficient and adj.shape and adj.product_type:
        coeff = db.query(ShapeConsumptionCoefficient).filter(
            ShapeConsumptionCoefficient.shape == adj.shape,
            ShapeConsumptionCoefficient.product_type == adj.product_type,
        ).first()

        if coeff:
            coeff.coefficient = adj.suggested_coefficient
            coeff.updated_by = current_user.id
            coeff.updated_at = datetime.now(timezone.utc)
        else:
            # Create new coefficient entry
            coeff = ShapeConsumptionCoefficient(
                shape=adj.shape,
                product_type=adj.product_type,
                coefficient=adj.suggested_coefficient,
                description=f"Auto-created from consumption adjustment #{str(adj.id)[:8]}",
                updated_by=current_user.id,
            )
            db.add(coeff)

    db.commit()
    db.refresh(adj)
    return _serialize_adjustment(adj, db)


@router.post("/consumption-adjustments/{adj_id}/reject")
async def reject_consumption_adjustment(
    adj_id: UUID,
    body: AdjustmentDecisionInput = AdjustmentDecisionInput(),
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Reject a consumption adjustment — no coefficient change."""
    adj = db.query(ConsumptionAdjustment).filter(ConsumptionAdjustment.id == adj_id).first()
    if not adj:
        raise HTTPException(404, "Adjustment not found")
    if adj.status != "pending":
        raise HTTPException(400, f"Adjustment is already {adj.status}")

    adj.status = "rejected"
    adj.approved_by = current_user.id
    adj.approved_at = datetime.now(timezone.utc)
    if body.notes:
        adj.notes = body.notes

    db.commit()
    db.refresh(adj)
    return _serialize_adjustment(adj, db)


# ── Duplicates & Merge ────────────────────────────────────────────────
# NOTE: These routes MUST be defined BEFORE /{material_id} to avoid
# "duplicates" / "merge" / "cleanup-duplicates" being captured as UUID.

@router.get("/duplicates")
async def find_duplicates(
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Find potential duplicate materials by similar names."""
    all_mats = db.query(Material).order_by(Material.name).all()

    # Group by normalized name (lowercase, strip whitespace)
    groups: dict[str, list] = {}
    for mat in all_mats:
        key = mat.name.strip().lower()
        groups.setdefault(key, []).append(mat)

    duplicates = []
    for key, mats in groups.items():
        if len(mats) > 1:
            duplicates.append({
                "normalized_name": key,
                "materials": [
                    {
                        "id": str(m.id),
                        "name": m.name,
                        "material_type": _ev(m.material_type),
                        "unit": m.unit,
                        "stock_count": db.query(MaterialStock).filter(
                            MaterialStock.material_id == m.id
                        ).count(),
                        "recipe_count": db.query(RecipeMaterial).filter(
                            RecipeMaterial.material_id == m.id
                        ).count(),
                        "transaction_count": db.query(MaterialTransaction).filter(
                            MaterialTransaction.material_id == m.id
                        ).count(),
                    }
                    for m in mats
                ],
            })

    # Also list all materials for overview
    summary = []
    for mat in all_mats:
        stock = db.query(MaterialStock).filter(MaterialStock.material_id == mat.id).first()
        summary.append({
            "id": str(mat.id),
            "name": mat.name,
            "material_type": _ev(mat.material_type),
            "unit": mat.unit,
            "has_stock": stock is not None,
            "balance": float(stock.balance) if stock else 0,
        })

    return {
        "total_materials": len(all_mats),
        "duplicate_groups": duplicates,
        "all_materials": summary,
    }


class MergeMaterialsInput(BaseModel):
    target_id: UUID = Field(description="Material ID to keep (target)")
    source_ids: list[UUID] = Field(description="Material IDs to merge into target and delete")
    new_name: Optional[str] = Field(None, description="Optional new name for the target material")


@router.post("/merge")
async def merge_materials(
    data: MergeMaterialsInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Merge multiple materials into one. Moves all references, sums stock balances,
    then deletes the source materials.

    Admin-only operation. Used for deduplication.

    IMPORTANT: Session uses autoflush=False, so we must flush() all re-pointing
    changes BEFORE db.delete(source). Otherwise ORM cascade='delete-orphan' on
    Material.stocks would reload stale data from DB and cascade-delete the
    re-pointed stocks, silently losing balances.
    """
    import logging
    log = logging.getLogger(__name__)

    target = db.query(Material).filter(Material.id == data.target_id).first()
    if not target:
        raise HTTPException(404, "Target material not found")

    if data.target_id in data.source_ids:
        raise HTTPException(400, "Target ID cannot be in source IDs")

    sources = db.query(Material).filter(Material.id.in_(data.source_ids)).all()
    if len(sources) != len(data.source_ids):
        found = {s.id for s in sources}
        missing = [str(sid) for sid in data.source_ids if sid not in found]
        raise HTTPException(404, f"Source materials not found: {missing}")

    moved = {"stocks": 0, "recipes": 0, "transactions": 0, "adjustments": 0,
             "maintenance": 0, "reconciliation": 0, "packaging": 0}

    for source in sources:
        sid = source.id
        tid = target.id
        log.info("Merging material %s (%s) into %s (%s)", sid, source.name, tid, target.name)

        # 1. MaterialStock — merge balances per factory
        source_stocks = db.query(MaterialStock).filter(MaterialStock.material_id == sid).all()
        for ss in source_stocks:
            existing = db.query(MaterialStock).filter(
                MaterialStock.material_id == tid,
                MaterialStock.factory_id == ss.factory_id,
            ).first()
            if existing:
                # Sum balances
                existing.balance = (existing.balance or 0) + (ss.balance or 0)
                # Keep higher min_balance
                if (ss.min_balance or 0) > (existing.min_balance or 0):
                    existing.min_balance = ss.min_balance
                db.delete(ss)
            else:
                # Move stock to target
                ss.material_id = tid
            moved["stocks"] += 1

        # 2. RecipeMaterial — re-point to target
        recipe_mats = db.query(RecipeMaterial).filter(RecipeMaterial.material_id == sid).all()
        for rm in recipe_mats:
            # Check if target already has this recipe link
            existing = db.query(RecipeMaterial).filter(
                RecipeMaterial.recipe_id == rm.recipe_id,
                RecipeMaterial.material_id == tid,
            ).first()
            if existing:
                db.delete(rm)  # Duplicate link, remove
            else:
                rm.material_id = tid
            moved["recipes"] += 1

        # 3. MaterialTransaction — re-point to target
        txns = db.query(MaterialTransaction).filter(MaterialTransaction.material_id == sid).all()
        for t in txns:
            t.material_id = tid
            moved["transactions"] += 1

        # 4. ConsumptionAdjustment — re-point to target
        adjs = db.query(ConsumptionAdjustment).filter(ConsumptionAdjustment.material_id == sid).all()
        for a in adjs:
            a.material_id = tid
            moved["adjustments"] += 1

        # 5. KilnMaintenanceMaterial — re-point
        maint = db.query(KilnMaintenanceMaterial).filter(KilnMaintenanceMaterial.material_id == sid).all()
        for m in maint:
            m.material_id = tid
            moved["maintenance"] += 1

        # 6. InventoryReconciliationItem — re-point
        recon = db.query(InventoryReconciliationItem).filter(
            InventoryReconciliationItem.material_id == sid
        ).all()
        for r in recon:
            r.material_id = tid
            moved["reconciliation"] += 1

        # 7. PackagingBoxType — re-point box material to target
        box_types = db.query(PackagingBoxType).filter(PackagingBoxType.material_id == sid).all()
        for bt in box_types:
            bt.material_id = tid
            moved["packaging"] += 1

        # 8. PackagingSpacerRule — re-point spacer material to target
        spacer_rules = db.query(PackagingSpacerRule).filter(PackagingSpacerRule.spacer_material_id == sid).all()
        for sr in spacer_rules:
            sr.spacer_material_id = tid
            moved["packaging"] += 1

        # CRITICAL: flush all re-pointing changes to DB BEFORE deleting source.
        # With autoflush=False, the ORM cascade on Material.stocks would otherwise
        # reload stale FK data from the DB and cascade-delete re-pointed stocks,
        # causing the merge to silently lose stock balances.
        db.flush()

        # Now safe to delete — all FK references already point to target in DB
        db.delete(source)

    # Rename target if requested
    if data.new_name:
        target.name = data.new_name
        target.updated_at = datetime.now(timezone.utc)

    try:
        db.commit()
    except Exception as exc:
        log.error("Material merge commit failed: %s", exc, exc_info=True)
        db.rollback()
        raise HTTPException(500, f"Merge failed during commit: {exc}")

    db.refresh(target)
    log.info("Merge complete: %d sources into %s, moved=%s", len(sources), target.name, moved)

    return {
        "ok": True,
        "target": {"id": str(target.id), "name": target.name},
        "merged_count": len(sources),
        "moved_references": moved,
    }


class BulkCleanupInput(BaseModel):
    """Auto-cleanup: merge exact duplicates + normalize frit names."""
    dry_run: bool = Field(True, description="If true, only show what would be done")
    frit_mappings: Optional[dict[str, list[str]]] = Field(
        None,
        description="Canonical name → list of alternate names to merge",
    )


@router.post("/cleanup-duplicates")
async def cleanup_duplicates(
    data: BulkCleanupInput = BulkCleanupInput(),
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Auto-detect and merge duplicate materials.

    1. Exact name duplicates (case-insensitive)
    2. Frit normalization per provided mappings

    Use dry_run=true first to preview changes.
    """
    all_mats = db.query(Material).order_by(Material.name).all()
    actions = []

    # 1. Find exact duplicates (case-insensitive)
    seen: dict[str, Material] = {}
    for mat in all_mats:
        key = mat.name.strip().lower()
        if key in seen:
            actions.append({
                "action": "merge_duplicate",
                "source": {"id": str(mat.id), "name": mat.name},
                "target": {"id": str(seen[key].id), "name": seen[key].name},
            })
        else:
            seen[key] = mat

    # 2. Frit normalization
    default_frit_mappings = {
        "Fritt Tomatec 12-3614P": [],
        "Fritt Kasmaji K 0387": [],
        "Fritt 360": [],
        "Fritt Fajar": [],
    }
    frit_map = data.frit_mappings or default_frit_mappings

    # Auto-detect frit variations: find all materials with "frit" in name
    frit_mats = [m for m in all_mats if "frit" in m.name.lower()]

    # Try to match frit materials to canonical names
    for mat in frit_mats:
        name_lower = mat.name.strip().lower()
        matched = False

        for canonical, alternates in frit_map.items():
            canon_lower = canonical.lower()
            alt_lowers = [a.lower() for a in alternates]

            if name_lower == canon_lower:
                matched = True
                break
            if name_lower in alt_lowers:
                matched = True
                canon_mat = next((m for m in all_mats if m.name.strip().lower() == canon_lower), None)
                if canon_mat and mat.id != canon_mat.id:
                    actions.append({
                        "action": "merge_frit",
                        "source": {"id": str(mat.id), "name": mat.name},
                        "target": {"id": str(canon_mat.id), "name": canon_mat.name},
                    })
                break

            # Fuzzy: check if canonical name is contained in material name
            if canon_lower in name_lower or any(a in name_lower for a in alt_lowers):
                matched = True
                canon_mat = next((m for m in all_mats if m.name.strip().lower() == canon_lower), None)
                if canon_mat and mat.id != canon_mat.id:
                    actions.append({
                        "action": "merge_frit_fuzzy",
                        "source": {"id": str(mat.id), "name": mat.name},
                        "target": {"id": str(canon_mat.id), "name": canon_mat.name},
                    })
                break

        if not matched:
            actions.append({
                "action": "unmatched_frit",
                "material": {"id": str(mat.id), "name": mat.name},
                "note": "Could not auto-match to canonical frit name",
            })

    if data.dry_run:
        return {
            "dry_run": True,
            "total_materials": len(all_mats),
            "frit_materials": [{"id": str(m.id), "name": m.name} for m in frit_mats],
            "planned_actions": actions,
        }

    # Execute merges
    merged = 0
    for act in actions:
        if act["action"] in ("merge_duplicate", "merge_frit", "merge_frit_fuzzy"):
            source_id = UUID(act["source"]["id"])
            target_id = UUID(act["target"]["id"])
            source = db.query(Material).filter(Material.id == source_id).first()
            target_mat = db.query(Material).filter(Material.id == target_id).first()
            if not source or not target_mat:
                continue

            # Move all references
            for stock in db.query(MaterialStock).filter(MaterialStock.material_id == source_id).all():
                existing = db.query(MaterialStock).filter(
                    MaterialStock.material_id == target_id,
                    MaterialStock.factory_id == stock.factory_id,
                ).first()
                if existing:
                    existing.balance = (existing.balance or 0) + (stock.balance or 0)
                    if (stock.min_balance or 0) > (existing.min_balance or 0):
                        existing.min_balance = stock.min_balance
                    db.delete(stock)
                else:
                    stock.material_id = target_id

            for rm in db.query(RecipeMaterial).filter(RecipeMaterial.material_id == source_id).all():
                existing = db.query(RecipeMaterial).filter(
                    RecipeMaterial.recipe_id == rm.recipe_id,
                    RecipeMaterial.material_id == target_id,
                ).first()
                if existing:
                    db.delete(rm)
                else:
                    rm.material_id = target_id

            db.query(MaterialTransaction).filter(
                MaterialTransaction.material_id == source_id
            ).update({MaterialTransaction.material_id: target_id})

            db.query(ConsumptionAdjustment).filter(
                ConsumptionAdjustment.material_id == source_id
            ).update({ConsumptionAdjustment.material_id: target_id})

            db.query(KilnMaintenanceMaterial).filter(
                KilnMaintenanceMaterial.material_id == source_id
            ).update({KilnMaintenanceMaterial.material_id: target_id})

            db.query(InventoryReconciliationItem).filter(
                InventoryReconciliationItem.material_id == source_id
            ).update({InventoryReconciliationItem.material_id: target_id})

            db.delete(source)
            merged += 1

    db.commit()

    return {
        "dry_run": False,
        "merged_count": merged,
        "planned_actions": actions,
    }


@router.post("/ensure-all-stocks")
async def ensure_all_stocks(
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Backfill: create missing MaterialStock rows for all active factories.
    For each Material → for each active Factory → if no stock → create with balance=0."""
    from api.models import Factory

    active_factories = db.query(Factory).filter(Factory.is_active == True).all()
    all_materials = db.query(Material).all()

    # Existing stock pairs
    existing = set(
        (row.material_id, row.factory_id)
        for row in db.query(MaterialStock.material_id, MaterialStock.factory_id).all()
    )

    created = 0
    for mat in all_materials:
        for factory in active_factories:
            if (mat.id, factory.id) not in existing:
                db.add(MaterialStock(
                    material_id=mat.id,
                    factory_id=factory.id,
                    balance=Decimal("0"),
                    min_balance=Decimal("0"),
                    min_balance_auto=True,
                    warehouse_section="raw_materials",
                ))
                created += 1

    db.commit()
    return {"detail": f"Created {created} missing stock records", "created": created}


# ── Single material CRUD (parameterized routes MUST come AFTER literal routes) ──

@router.get("/{material_id}")
async def get_material(
    material_id: UUID,
    factory_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    mat = db.query(Material).filter(Material.id == material_id).first()
    if not mat:
        raise HTTPException(404, "Material not found")

    stock = None
    if factory_id:
        stock = db.query(MaterialStock).filter(
            MaterialStock.material_id == material_id,
            MaterialStock.factory_id == factory_id,
        ).first()
    else:
        # Return first available stock
        stock = db.query(MaterialStock).filter(
            MaterialStock.material_id == material_id,
        ).first()

    return _serialize_material(mat, stock, db)


@router.post("", status_code=201)
async def create_material(
    data: MaterialCreateInput,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from api.models import MaterialSubgroup, Factory

    # Resolve material_type from subgroup if provided
    material_type = data.material_type
    subgroup_id = data.subgroup_id
    if subgroup_id:
        sg = db.query(MaterialSubgroup).filter(MaterialSubgroup.id == subgroup_id).first()
        if not sg:
            raise HTTPException(404, "Material subgroup not found")
        material_type = sg.code  # sync material_type from subgroup.code

    # Get or create catalog material
    mat = db.query(Material).filter(Material.name == data.name).first()
    is_new_mat = mat is None
    if not mat:
        mat = Material(
            name=data.name,
            material_code=_next_material_code(db),
            material_type=material_type,
            unit=data.unit,
            supplier_id=data.supplier_id,
            subgroup_id=subgroup_id,
            size_id=data.size_id,
        )
        db.add(mat)
        db.flush()
    elif subgroup_id and not mat.subgroup_id:
        # Existing material without subgroup — assign it
        mat.subgroup_id = subgroup_id
        mat.material_type = material_type

    primary_stock = None

    if data.factory_id:
        # ── Specific factory mode: create stock for one factory ──
        existing_stock = db.query(MaterialStock).filter(
            MaterialStock.material_id == mat.id,
            MaterialStock.factory_id == data.factory_id,
        ).first()
        if existing_stock:
            raise HTTPException(409, f"Material '{data.name}' already exists in this factory")

        primary_stock = MaterialStock(
            material_id=mat.id,
            factory_id=data.factory_id,
            balance=Decimal(str(data.balance)),
            min_balance=Decimal(str(data.min_balance)),
            min_balance_auto=data.min_balance_auto,
            warehouse_section=data.warehouse_section or "raw_materials",
        )
        db.add(primary_stock)
    else:
        # ── Auto mode: create stock for ALL active factories ──
        active_factories = db.query(Factory).filter(Factory.is_active == True).all()
        existing_factory_ids = set(
            fid for (fid,) in db.query(MaterialStock.factory_id).filter(
                MaterialStock.material_id == mat.id
            ).all()
        )

        for factory in active_factories:
            if factory.id in existing_factory_ids:
                continue
            s = MaterialStock(
                material_id=mat.id,
                factory_id=factory.id,
                balance=Decimal(str(data.balance)),
                min_balance=Decimal(str(data.min_balance)),
                min_balance_auto=data.min_balance_auto,
                warehouse_section=data.warehouse_section or "raw_materials",
            )
            db.add(s)
            if primary_stock is None:
                primary_stock = s

        if primary_stock is None and not is_new_mat:
            raise HTTPException(409, f"Material '{data.name}' already has stock for all factories")

    db.commit()
    db.refresh(mat)
    if primary_stock:
        db.refresh(primary_stock)
    return _serialize_material(mat, primary_stock, db)


@router.patch("/{material_id}")
async def update_material(
    material_id: UUID,
    data: MaterialUpdateInput,
    factory_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    mat = db.query(Material).filter(Material.id == material_id).first()
    if not mat:
        raise HTTPException(404, "Material not found")

    updates = data.model_dump(exclude_unset=True)

    # Handle subgroup_id change — sync material_type from subgroup.code
    if 'subgroup_id' in updates:
        from api.models import MaterialSubgroup
        new_sg_id = updates.pop('subgroup_id')
        if new_sg_id:
            sg = db.query(MaterialSubgroup).filter(MaterialSubgroup.id == new_sg_id).first()
            if not sg:
                raise HTTPException(404, "Material subgroup not found")
            mat.subgroup_id = new_sg_id
            mat.material_type = sg.code
        else:
            mat.subgroup_id = None

    # Handle size_id
    if 'size_id' in updates:
        mat.size_id = updates.pop('size_id')

    # Catalog-level fields
    catalog_fields = {'name', 'unit', 'supplier_id'}
    # Stock-level fields
    stock_fields = {'balance', 'min_balance', 'min_balance_auto', 'warehouse_section'}

    for k, v in updates.items():
        if k in catalog_fields:
            setattr(mat, k, v)

    mat.updated_at = datetime.now(timezone.utc)

    # Update stock if factory_id provided and stock fields present
    stock = None
    stock_updates = {k: v for k, v in updates.items() if k in stock_fields}
    if stock_updates:
        if factory_id:
            stock = db.query(MaterialStock).filter(
                MaterialStock.material_id == material_id,
                MaterialStock.factory_id == factory_id,
            ).first()
        else:
            stock = db.query(MaterialStock).filter(
                MaterialStock.material_id == material_id,
            ).first()

        if stock:
            for k, v in stock_updates.items():
                if k in ("balance", "min_balance") and v is not None:
                    setattr(stock, k, Decimal(str(v)))
                else:
                    setattr(stock, k, v)
            stock.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(mat)
    if stock:
        db.refresh(stock)
    return _serialize_material(mat, stock, db)


@router.delete("/{material_id}")
async def delete_material(
    material_id: UUID,
    factory_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Delete a material and all its related records. Owner/Admin only."""
    mat = db.query(Material).filter(Material.id == material_id).first()
    if not mat:
        raise HTTPException(404, "Material not found")

    should_delete_mat = True

    if factory_id:
        # Delete only stock for the specific factory
        db.query(MaterialStock).filter(
            MaterialStock.material_id == material_id,
            MaterialStock.factory_id == factory_id,
        ).delete(synchronize_session=False)
        remaining = db.query(MaterialStock).filter(
            MaterialStock.material_id == material_id,
        ).count()
        if remaining > 0:
            should_delete_mat = False

    if should_delete_mat:
        # Clean up ALL FK-dependent records before deleting the material
        db.query(MaterialStock).filter(
            MaterialStock.material_id == material_id,
        ).delete(synchronize_session=False)
        db.query(RecipeMaterial).filter(
            RecipeMaterial.material_id == material_id,
        ).delete(synchronize_session=False)
        db.query(MaterialTransaction).filter(
            MaterialTransaction.material_id == material_id,
        ).delete(synchronize_session=False)
        db.query(KilnMaintenanceMaterial).filter(
            KilnMaintenanceMaterial.material_id == material_id,
        ).delete(synchronize_session=False)
        db.query(ConsumptionAdjustment).filter(
            ConsumptionAdjustment.material_id == material_id,
        ).delete(synchronize_session=False)
        db.query(InventoryReconciliationItem).filter(
            InventoryReconciliationItem.material_id == material_id,
        ).delete(synchronize_session=False)
        db.delete(mat)

    db.commit()
    return {"detail": "Material deleted"}


@router.get("/{material_id}/transactions")
async def list_material_transactions(
    material_id: UUID,
    factory_id: UUID | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    mat = db.query(Material).filter(Material.id == material_id).first()
    if not mat:
        raise HTTPException(404, "Material not found")

    query = db.query(MaterialTransaction).filter(
        MaterialTransaction.material_id == material_id
    )
    if factory_id:
        query = query.filter(MaterialTransaction.factory_id == factory_id)

    total = query.count()
    items = query.order_by(
        MaterialTransaction.created_at.desc()
    ).offset((page - 1) * per_page).limit(per_page).all()

    return {
        "items": [_serialize_transaction(t, db) for t in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.post("/transactions", status_code=201)
async def create_transaction(
    data: TransactionInput,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Manual receive, write-off, or inventory adjustment transaction."""
    if data.type not in ("receive", "manual_write_off", "inventory"):
        raise HTTPException(400, "Manual transactions must be 'receive', 'manual_write_off', or 'inventory'")

    if data.type in ("receive", "manual_write_off") and data.quantity <= 0:
        raise HTTPException(400, "Quantity must be positive")

    if data.type == "manual_write_off" and not data.reason:
        raise HTTPException(400, "Reason is required for write-off")

    mat = db.query(Material).filter(Material.id == data.material_id).first()
    if not mat:
        raise HTTPException(404, "Material not found")

    stock = db.query(MaterialStock).filter(
        MaterialStock.material_id == data.material_id,
        MaterialStock.factory_id == data.factory_id,
    ).first()
    if not stock:
        raise HTTPException(404, "Material stock not found for this factory")

    qty = Decimal(str(data.quantity))

    if data.type == "manual_write_off":
        if stock.balance < qty:
            raise HTTPException(400, f"Insufficient balance: {float(stock.balance)} < {data.quantity}")
        stock.balance -= qty
    elif data.type == "inventory":
        # Inventory adjustment: qty is the difference (actual − system), can be negative
        stock.balance += qty
    else:
        # receive
        stock.balance += qty

    stock.updated_at = datetime.now(timezone.utc)

    t = MaterialTransaction(
        material_id=data.material_id,
        factory_id=data.factory_id,
        type=data.type,
        quantity=qty,
        reason=data.reason,
        notes=data.notes,
        created_by=current_user.id,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return _serialize_transaction(t, db)


@router.post("/purchase-requests", status_code=201)
async def create_purchase_request(
    data: PurchaseRequestInput,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    pr = MaterialPurchaseRequest(
        factory_id=data.factory_id,
        supplier_id=data.supplier_id,
        materials_json=data.materials_json,
        status=PurchaseStatus.PENDING,
        source="manual",
        notes=data.notes,
    )
    db.add(pr)
    db.commit()
    db.refresh(pr)

    supplier_name = None
    if pr.supplier_id:
        sup = db.query(Supplier).filter(Supplier.id == pr.supplier_id).first()
        supplier_name = sup.name if sup else None

    return {
        "id": str(pr.id),
        "factory_id": str(pr.factory_id),
        "supplier_id": str(pr.supplier_id) if pr.supplier_id else None,
        "supplier_name": supplier_name,
        "materials_json": pr.materials_json,
        "status": _ev(pr.status),
        "source": pr.source,
        "notes": pr.notes,
        "created_at": pr.created_at.isoformat() if pr.created_at else None,
    }
