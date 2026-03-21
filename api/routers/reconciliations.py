"""CRUD router for inventory_reconciliations (auto-generated)."""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.models import (
    InventoryReconciliation, InventoryReconciliationItem,
    MaterialTransaction, Material, MaterialStock,
)
from api.enums import ReconciliationStatus, TransactionType
from api.schemas import InventoryReconciliationCreate, InventoryReconciliationUpdate, InventoryReconciliationResponse
from api.roles import require_management

router = APIRouter()


# ── Pydantic input models ──────────────────────────────────────────

class ReconciliationItemInput(BaseModel):
    material_id: UUID
    expected_qty: float
    actual_qty: float
    reason: Optional[str] = None
    explanation: Optional[str] = None


@router.get("", response_model=dict)
async def list_reconciliations(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    factory_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(InventoryReconciliation)
    if factory_id:
        query = query.filter(InventoryReconciliation.factory_id == factory_id)
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return {
        "items": [InventoryReconciliationResponse.model_validate(item).model_dump(mode="json") for item in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# === RECONCILIATION ITEMS + COMPLETE (Decision 2026-03-19) ===

@router.get("/{reconciliation_id}/items")
async def list_reconciliation_items(
    reconciliation_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return all items for a reconciliation, with material name."""
    recon = db.query(InventoryReconciliation).filter(
        InventoryReconciliation.id == reconciliation_id,
    ).first()
    if not recon:
        raise HTTPException(404, "Reconciliation not found")

    items = (
        db.query(InventoryReconciliationItem)
        .filter(InventoryReconciliationItem.reconciliation_id == reconciliation_id)
        .all()
    )

    result = []
    for ri in items:
        mat = db.query(Material).filter(Material.id == ri.material_id).first()
        result.append({
            "id": str(ri.id),
            "material_id": str(ri.material_id),
            "material_name": mat.name if mat else "Unknown",
            "system_quantity": float(ri.system_quantity),
            "actual_quantity": float(ri.actual_quantity),
            "difference": float(ri.difference),
            "reason": ri.reason,
            "explanation": ri.explanation,
            "adjustment_applied": ri.adjustment_applied,
        })

    return {"items": result, "total": len(result)}


@router.post("/{reconciliation_id}/items", status_code=201)
async def add_reconciliation_items(
    reconciliation_id: UUID,
    items: List[ReconciliationItemInput],
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Add items to an in-progress reconciliation.
    Each item records expected vs actual quantity for a material.
    """
    recon = db.query(InventoryReconciliation).filter(
        InventoryReconciliation.id == reconciliation_id,
    ).first()
    if not recon:
        raise HTTPException(404, "Reconciliation not found")

    if recon.status != ReconciliationStatus.IN_PROGRESS:
        raise HTTPException(400, f"Reconciliation status must be 'in_progress', got '{recon.status.value}'")

    created = []
    for item_data in items:
        # Validate material exists
        mat = db.query(Material).filter(Material.id == item_data.material_id).first()
        if not mat:
            raise HTTPException(404, f"Material {item_data.material_id} not found")

        difference = item_data.actual_qty - item_data.expected_qty

        ri = InventoryReconciliationItem(
            reconciliation_id=reconciliation_id,
            material_id=item_data.material_id,
            system_quantity=item_data.expected_qty,
            actual_quantity=item_data.actual_qty,
            difference=difference,
            reason=item_data.reason,
            explanation=item_data.explanation,
            explained_by=current_user.id if item_data.explanation else None,
            explained_at=datetime.now(timezone.utc) if item_data.explanation else None,
        )
        db.add(ri)
        created.append(ri)

    db.commit()

    result_items = []
    for ri in created:
        db.refresh(ri)
        result_items.append({
            "id": str(ri.id),
            "material_id": str(ri.material_id),
            "system_quantity": float(ri.system_quantity),
            "actual_quantity": float(ri.actual_quantity),
            "difference": float(ri.difference),
            "reason": ri.reason,
        })

    return {
        "reconciliation_id": str(reconciliation_id),
        "items_added": len(result_items),
        "items": result_items,
    }


@router.post("/{reconciliation_id}/complete")
async def complete_reconciliation(
    reconciliation_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """
    Finalize a reconciliation: mark as completed and create adjustment
    transactions for any discrepancies found in reconciliation items.
    """
    recon = db.query(InventoryReconciliation).filter(
        InventoryReconciliation.id == reconciliation_id,
    ).first()
    if not recon:
        raise HTTPException(404, "Reconciliation not found")

    if recon.status != ReconciliationStatus.IN_PROGRESS:
        raise HTTPException(400, f"Reconciliation must be 'in_progress' to complete, got '{recon.status.value}'")

    # Get all items for this reconciliation
    items = db.query(InventoryReconciliationItem).filter(
        InventoryReconciliationItem.reconciliation_id == reconciliation_id,
    ).all()

    if not items:
        raise HTTPException(400, "Cannot complete reconciliation with no items")

    adjustments_created = 0
    for item in items:
        if item.adjustment_applied:
            continue

        diff = float(item.difference)
        if abs(diff) < 0.001:
            item.adjustment_applied = True
            continue

        # Create adjustment transaction
        txn = MaterialTransaction(
            material_id=item.material_id,
            factory_id=recon.factory_id,
            type=TransactionType.INVENTORY,
            quantity=abs(diff),
            notes=f"Inventory reconciliation adjustment (recon {reconciliation_id}). "
                  f"System: {float(item.system_quantity)}, Actual: {float(item.actual_quantity)}, "
                  f"Diff: {diff}",
            created_by=current_user.id,
        )
        db.add(txn)

        # Update material stock if possible
        stock = db.query(MaterialStock).filter(
            MaterialStock.material_id == item.material_id,
            MaterialStock.factory_id == recon.factory_id,
        ).first()
        if stock:
            stock.current_quantity = item.actual_quantity

        item.adjustment_applied = True
        adjustments_created += 1

    recon.status = ReconciliationStatus.COMPLETED
    recon.completed_at = datetime.now(timezone.utc)

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(500, f"Failed to complete reconciliation: {exc}") from exc

    return {
        "reconciliation_id": str(reconciliation_id),
        "status": "completed",
        "items_count": len(items),
        "adjustments_created": adjustments_created,
        "completed_at": recon.completed_at.isoformat(),
        "completed_by": str(current_user.id),
    }


# --- Standard CRUD (after specific routes) ---

@router.get("/{item_id}", response_model=InventoryReconciliationResponse)
async def get_reconciliations_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(InventoryReconciliation).filter(InventoryReconciliation.id == item_id).first()
    if not item:
        raise HTTPException(404, "InventoryReconciliation not found")
    return item


@router.post("", response_model=InventoryReconciliationResponse, status_code=201)
async def create_reconciliations_item(
    data: InventoryReconciliationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = InventoryReconciliation(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=InventoryReconciliationResponse)
async def update_reconciliations_item(
    item_id: UUID,
    data: InventoryReconciliationUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(InventoryReconciliation).filter(InventoryReconciliation.id == item_id).first()
    if not item:
        raise HTTPException(404, "InventoryReconciliation not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
async def delete_reconciliations_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(InventoryReconciliation).filter(InventoryReconciliation.id == item_id).first()
    if not item:
        raise HTTPException(404, "InventoryReconciliation not found")
    db.delete(item)
    db.commit()
