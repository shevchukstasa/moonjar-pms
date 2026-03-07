"""Materials router — inventory, transactions, low-stock, purchase requests."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user, apply_factory_filter
from api.models import (
    Material, MaterialTransaction, MaterialPurchaseRequest, Supplier, User,
)
from api.enums import PurchaseStatus

router = APIRouter()


# ── helpers ──────────────────────────────────────────────────────────────

def _ev(val):
    return val.value if hasattr(val, "value") else str(val) if val else None


def _serialize_material(m, db) -> dict:
    supplier_name = None
    if m.supplier_id:
        sup = db.query(Supplier).filter(Supplier.id == m.supplier_id).first()
        supplier_name = sup.name if sup else None

    balance = float(m.balance or 0)
    min_bal = float(m.min_balance or 0)

    return {
        "id": str(m.id),
        "name": m.name,
        "factory_id": str(m.factory_id),
        "balance": balance,
        "min_balance": min_bal,
        "min_balance_recommended": float(m.min_balance_recommended) if m.min_balance_recommended else None,
        "min_balance_auto": m.min_balance_auto,
        "avg_daily_consumption": float(m.avg_daily_consumption) if m.avg_daily_consumption else 0,
        "avg_monthly_consumption": float(m.avg_monthly_consumption) if m.avg_monthly_consumption else 0,
        "unit": m.unit,
        "material_type": _ev(m.material_type),
        "warehouse_section": m.warehouse_section,
        "supplier_id": str(m.supplier_id) if m.supplier_id else None,
        "supplier_name": supplier_name,
        "is_low_stock": balance < min_bal if min_bal > 0 else False,
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "updated_at": m.updated_at.isoformat() if m.updated_at else None,
    }


def _serialize_transaction(t, db) -> dict:
    creator_name = None
    if t.created_by:
        user = db.query(User).filter(User.id == t.created_by).first()
        creator_name = user.name if user else None

    return {
        "id": str(t.id),
        "material_id": str(t.material_id),
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

@router.get("/")
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
    query = db.query(Material)
    query = apply_factory_filter(query, current_user, factory_id, Material)

    if material_type:
        query = query.filter(Material.material_type == material_type)
    if warehouse_section:
        query = query.filter(Material.warehouse_section == warehouse_section)
    if search:
        query = query.filter(Material.name.ilike(f"%{search}%"))
    if low_stock:
        query = query.filter(Material.balance < Material.min_balance, Material.min_balance > 0)

    total = query.count()
    items = query.order_by(Material.name).offset((page - 1) * per_page).limit(per_page).all()

    return {
        "items": [_serialize_material(m, db) for m in items],
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
    query = db.query(Material).filter(
        Material.balance < Material.min_balance,
        Material.min_balance > 0,
    )
    query = apply_factory_filter(query, current_user, factory_id, Material)

    items = query.order_by(
        (Material.min_balance - Material.balance).desc()
    ).all()

    result = []
    for m in items:
        s = _serialize_material(m, db)
        s["deficit"] = float(m.min_balance - m.balance)
        result.append(s)

    return {"items": result, "total": len(result)}


@router.get("/effective-balance")
async def get_effective_balance(
    factory_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    raise HTTPException(501, "Not implemented — V2 feature")


@router.get("/{material_id}")
async def get_material(
    material_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    m = db.query(Material).filter(Material.id == material_id).first()
    if not m:
        raise HTTPException(404, "Material not found")
    return _serialize_material(m, db)


@router.post("/", status_code=201)
async def create_material(
    data: MaterialCreateInput,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    existing = db.query(Material).filter(
        Material.name == data.name, Material.factory_id == data.factory_id
    ).first()
    if existing:
        raise HTTPException(409, f"Material '{data.name}' already exists in this factory")

    m = Material(
        name=data.name,
        factory_id=data.factory_id,
        material_type=data.material_type,
        unit=data.unit,
        balance=Decimal(str(data.balance)),
        min_balance=Decimal(str(data.min_balance)),
        min_balance_auto=data.min_balance_auto,
        supplier_id=data.supplier_id,
        warehouse_section=data.warehouse_section or "raw_materials",
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return _serialize_material(m, db)


@router.patch("/{material_id}")
async def update_material(
    material_id: UUID,
    data: MaterialUpdateInput,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    m = db.query(Material).filter(Material.id == material_id).first()
    if not m:
        raise HTTPException(404, "Material not found")

    updates = data.model_dump(exclude_unset=True)
    for k, v in updates.items():
        if k == "min_balance" and v is not None:
            setattr(m, k, Decimal(str(v)))
        else:
            setattr(m, k, v)

    m.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(m)
    return _serialize_material(m, db)


@router.get("/{material_id}/transactions")
async def list_material_transactions(
    material_id: UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    m = db.query(Material).filter(Material.id == material_id).first()
    if not m:
        raise HTTPException(404, "Material not found")

    query = db.query(MaterialTransaction).filter(
        MaterialTransaction.material_id == material_id
    )
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

    m = db.query(Material).filter(Material.id == data.material_id).first()
    if not m:
        raise HTTPException(404, "Material not found")

    qty = Decimal(str(data.quantity))

    if data.type == "manual_write_off":
        if m.balance < qty:
            raise HTTPException(400, f"Insufficient balance: {float(m.balance)} < {data.quantity}")
        m.balance -= qty
    else:
        m.balance += qty

    m.updated_at = datetime.now(timezone.utc)

    t = MaterialTransaction(
        material_id=data.material_id,
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
