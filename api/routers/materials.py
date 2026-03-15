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
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user, apply_factory_filter, require_management
from api.models import (
    Material, MaterialStock, MaterialTransaction,
    MaterialPurchaseRequest, Supplier, User,
    ConsumptionAdjustment, ShapeConsumptionCoefficient,
    OrderPosition,
)
from api.enums import PurchaseStatus

router = APIRouter()


# ── helpers ──────────────────────────────────────────────────────────────

def _ev(val):
    return val.value if hasattr(val, "value") else str(val) if val else None


def _serialize_material(mat: Material, stock: MaterialStock | None, db: Session) -> dict:
    """Serialize catalog Material + optional per-factory MaterialStock into flat dict."""
    supplier_name = None
    if mat.supplier_id:
        sup = db.query(Supplier).filter(Supplier.id == mat.supplier_id).first()
        supplier_name = sup.name if sup else None

    balance = float(stock.balance or 0) if stock else 0
    min_bal = float(stock.min_balance or 0) if stock else 0

    return {
        "id": str(mat.id),
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
        "warehouse_section": stock.warehouse_section if stock else None,
        "supplier_id": str(mat.supplier_id) if mat.supplier_id else None,
        "supplier_name": supplier_name,
        "is_low_stock": balance < min_bal if min_bal > 0 else False,
        "created_at": mat.created_at.isoformat() if mat.created_at else None,
        "updated_at": (stock.updated_at if stock else mat.updated_at).isoformat() if (stock or mat) else None,
    }


def _serialize_transaction(t, db) -> dict:
    creator_name = None
    if t.created_by:
        user = db.query(User).filter(User.id == t.created_by).first()
        creator_name = user.name if user else None

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
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


# ── Pydantic models ─────────────────────────────────────────────────────

class MaterialCreateInput(BaseModel):
    name: str
    factory_id: UUID
    material_type: str
    unit: str = "pcs"
    balance: float = 0
    min_balance: float = 0
    min_balance_auto: bool = True
    supplier_id: Optional[UUID] = None
    warehouse_section: Optional[str] = "raw_materials"


class MaterialUpdateInput(BaseModel):
    name: Optional[str] = None
    min_balance: Optional[float] = None
    min_balance_auto: Optional[bool] = None
    unit: Optional[str] = None
    warehouse_section: Optional[str] = None
    supplier_id: Optional[UUID] = None


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
    warehouse_section: str | None = None,
    low_stock: bool | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(Material, MaterialStock).outerjoin(
        MaterialStock, Material.id == MaterialStock.material_id
    )
    query = apply_factory_filter(query, current_user, factory_id, MaterialStock)

    if material_type:
        query = query.filter(Material.material_type == material_type)
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
    # Get or create catalog material
    mat = db.query(Material).filter(Material.name == data.name).first()
    if not mat:
        mat = Material(
            name=data.name,
            material_type=data.material_type,
            unit=data.unit,
            supplier_id=data.supplier_id,
        )
        db.add(mat)
        db.flush()

    # Check if stock already exists for this factory
    existing_stock = db.query(MaterialStock).filter(
        MaterialStock.material_id == mat.id,
        MaterialStock.factory_id == data.factory_id,
    ).first()
    if existing_stock:
        raise HTTPException(409, f"Material '{data.name}' already exists in this factory")

    stock = MaterialStock(
        material_id=mat.id,
        factory_id=data.factory_id,
        balance=Decimal(str(data.balance)),
        min_balance=Decimal(str(data.min_balance)),
        min_balance_auto=data.min_balance_auto,
        warehouse_section=data.warehouse_section or "raw_materials",
    )
    db.add(stock)
    db.commit()
    db.refresh(mat)
    db.refresh(stock)
    return _serialize_material(mat, stock, db)


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

    # Catalog-level fields
    catalog_fields = {'name', 'unit', 'supplier_id'}
    # Stock-level fields
    stock_fields = {'min_balance', 'min_balance_auto', 'warehouse_section'}

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
                if k == "min_balance" and v is not None:
                    setattr(stock, k, Decimal(str(v)))
                else:
                    setattr(stock, k, v)
            stock.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(mat)
    if stock:
        db.refresh(stock)
    return _serialize_material(mat, stock, db)


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
    """Manual receive or write-off transaction."""
    if data.type not in ("receive", "manual_write_off"):
        raise HTTPException(400, "Manual transactions must be 'receive' or 'manual_write_off'")

    if data.quantity <= 0:
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
    else:
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


# ── Consumption Adjustments ─────────────────────────────────────────────

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
