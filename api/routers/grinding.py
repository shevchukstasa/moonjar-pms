"""Grinding stock management router."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.roles import require_management
from api.models import GrindingStock
from api.enums import GrindingStatus
from api.schemas import (
    GrindingStockCreate,
    GrindingStockResponse,
    GrindingStockDecision,
)

router = APIRouter()

VALID_DECISIONS = {
    "grinding": GrindingStatus.GRINDING,
    "pending": GrindingStatus.PENDING,
    "sent_to_mana": GrindingStatus.SENT_TO_MANA,
}


@router.get("", response_model=dict)
async def list_grinding_stock(
    factory_id: UUID | None = Query(None, description="Filter by factory"),
    status: str | None = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List grinding stock items, optionally filtered by factory and status."""
    query = db.query(GrindingStock)
    if factory_id:
        query = query.filter(GrindingStock.factory_id == factory_id)
    if status:
        query = query.filter(GrindingStock.status == status)
    total = query.count()
    items = (
        query.order_by(GrindingStock.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return {
        "items": [
            GrindingStockResponse.model_validate(item).model_dump(mode="json")
            for item in items
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/stats", response_model=dict)
async def grinding_stock_stats(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Count grinding stock items by status per factory."""
    rows = (
        db.query(
            GrindingStock.factory_id,
            GrindingStock.status,
            func.count(GrindingStock.id).label("count"),
        )
        .group_by(GrindingStock.factory_id, GrindingStock.status)
        .all()
    )
    stats: dict = {}
    for factory_id, status, count in rows:
        fid = str(factory_id)
        if fid not in stats:
            stats[fid] = {}
        stats[fid][status.value if hasattr(status, "value") else status] = count
    return {"stats": stats}


@router.get("/{item_id}", response_model=GrindingStockResponse)
async def get_grinding_stock_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get a single grinding stock item by ID."""
    item = db.query(GrindingStock).filter(GrindingStock.id == item_id).first()
    if not item:
        raise HTTPException(404, "GrindingStock item not found")
    return item


@router.post("", response_model=GrindingStockResponse, status_code=201)
async def create_grinding_stock_item(
    data: GrindingStockCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Create a new grinding stock entry (PM/management only)."""
    item = GrindingStock(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
async def delete_grinding_stock_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Delete a grinding stock item (management only)."""
    item = db.query(GrindingStock).filter(GrindingStock.id == item_id).first()
    if not item:
        raise HTTPException(404, "GrindingStock item not found")
    db.delete(item)
    db.commit()
    return None


@router.post("/{item_id}/decide", response_model=GrindingStockResponse)
async def decide_grinding_stock(
    item_id: UUID,
    data: GrindingStockDecision,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """PM decision on a grinding stock item: grind, wait (pending), or send to Mana."""
    item = db.query(GrindingStock).filter(GrindingStock.id == item_id).first()
    if not item:
        raise HTTPException(404, "GrindingStock item not found")

    if data.decision not in VALID_DECISIONS:
        raise HTTPException(
            400,
            f"Invalid decision '{data.decision}'. Must be one of: {', '.join(VALID_DECISIONS.keys())}",
        )

    item.status = VALID_DECISIONS[data.decision]
    item.decided_by = current_user.id
    item.decided_at = datetime.now(timezone.utc)
    if data.notes is not None:
        item.notes = data.notes
    item.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(item)
    return item
