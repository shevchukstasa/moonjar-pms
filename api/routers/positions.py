"""Positions router — list, status transitions, filtering by section."""

from datetime import datetime, timezone
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_

from api.database import get_db
from api.auth import get_current_user, apply_factory_filter
from api.roles import require_management
from api.models import OrderPosition, ProductionOrder
from api.enums import PositionStatus

router = APIRouter()


def _ev(val):
    return val.value if hasattr(val, "value") else str(val) if val else None


# Section → status mapping
SECTION_STATUSES = {
    "glazing": [
        PositionStatus.PLANNED, PositionStatus.INSUFFICIENT_MATERIALS,
        PositionStatus.AWAITING_RECIPE, PositionStatus.AWAITING_STENCIL_SILKSCREEN,
        PositionStatus.AWAITING_COLOR_MATCHING, PositionStatus.ENGOBE_APPLIED,
        PositionStatus.ENGOBE_CHECK, PositionStatus.GLAZED,
        PositionStatus.PRE_KILN_CHECK, PositionStatus.SENT_TO_GLAZING,
    ],
    "firing": [
        PositionStatus.LOADED_IN_KILN, PositionStatus.FIRED,
        PositionStatus.REFIRE, PositionStatus.AWAITING_REGLAZE,
    ],
    "sorting": [
        PositionStatus.TRANSFERRED_TO_SORTING, PositionStatus.PACKED,
        PositionStatus.SENT_TO_QUALITY_CHECK, PositionStatus.QUALITY_CHECK_DONE,
        PositionStatus.READY_FOR_SHIPMENT, PositionStatus.BLOCKED_BY_QM,
    ],
}


def _serialize_position(p) -> dict:
    return {
        "id": str(p.id),
        "order_id": str(p.order_id),
        "order_item_id": str(p.order_item_id),
        "parent_position_id": str(p.parent_position_id) if p.parent_position_id else None,
        "factory_id": str(p.factory_id),
        "status": _ev(p.status),
        "batch_id": str(p.batch_id) if p.batch_id else None,
        "resource_id": str(p.resource_id) if p.resource_id else None,
        "placement_position": p.placement_position,
        "placement_level": p.placement_level,
        "delay_hours": float(p.delay_hours) if p.delay_hours else 0,
        "quantity": p.quantity,
        "quantity_with_defect_margin": p.quantity_with_defect_margin,
        "color": p.color,
        "size": p.size,
        "application": p.application,
        "finishing": p.finishing,
        "collection": p.collection,
        "application_type": p.application_type,
        "place_of_application": p.place_of_application,
        "product_type": _ev(p.product_type),
        "shape": _ev(p.shape),
        "thickness_mm": float(p.thickness_mm) if p.thickness_mm else 11.0,
        "recipe_id": str(p.recipe_id) if p.recipe_id else None,
        "mandatory_qc": p.mandatory_qc,
        "split_category": _ev(p.split_category),
        "is_merged": p.is_merged,
        "priority_order": p.priority_order,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        # Include order_number via relationship
        "order_number": p.order.order_number if p.order else "",
    }


class StatusChangeInput(BaseModel):
    status: str
    notes: Optional[str] = None


@router.get("/")
async def list_positions(
    page: int = Query(1, ge=1),
    per_page: int = Query(100, ge=1, le=500),
    factory_id: UUID | None = None,
    order_id: UUID | None = None,
    status: str | None = None,
    section: str | None = None,
    batch_id: UUID | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(OrderPosition)
    query = apply_factory_filter(query, current_user, factory_id, OrderPosition)

    if order_id:
        query = query.filter(OrderPosition.order_id == order_id)
    if batch_id:
        query = query.filter(OrderPosition.batch_id == batch_id)

    # Filter by section (group of statuses)
    if section and section in SECTION_STATUSES:
        query = query.filter(OrderPosition.status.in_(SECTION_STATUSES[section]))
    elif status:
        # Comma-separated statuses
        statuses = [s.strip() for s in status.split(",")]
        query = query.filter(OrderPosition.status.in_(statuses))

    if search:
        query = query.join(ProductionOrder, OrderPosition.order_id == ProductionOrder.id).filter(
            or_(
                ProductionOrder.order_number.ilike(f"%{search}%"),
                OrderPosition.color.ilike(f"%{search}%"),
            )
        )

    total = query.count()
    positions = query.order_by(
        OrderPosition.priority_order, OrderPosition.created_at
    ).offset((page - 1) * per_page).limit(per_page).all()

    return {
        "items": [_serialize_position(p) for p in positions],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/{position_id}")
async def get_position(
    position_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    p = db.query(OrderPosition).filter(OrderPosition.id == position_id).first()
    if not p:
        raise HTTPException(404, "Position not found")

    result = _serialize_position(p)

    # Include sub-positions
    children = db.query(OrderPosition).filter(
        OrderPosition.parent_position_id == position_id
    ).all()
    result["sub_positions"] = [_serialize_position(c) for c in children]

    return result


@router.patch("/{position_id}")
async def update_position(
    position_id: UUID,
    data: dict,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    p = db.query(OrderPosition).filter(OrderPosition.id == position_id).first()
    if not p:
        raise HTTPException(404, "Position not found")

    allowed = {"batch_id", "resource_id", "placement_position", "placement_level",
               "delay_hours", "priority_order", "recipe_id", "mandatory_qc"}
    for k, v in data.items():
        if k in allowed:
            setattr(p, k, v)
    p.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(p)
    return _serialize_position(p)


@router.post("/{position_id}/status")
async def change_position_status(
    position_id: UUID,
    data: StatusChangeInput,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    p = db.query(OrderPosition).filter(OrderPosition.id == position_id).first()
    if not p:
        raise HTTPException(404, "Position not found")

    # Validate status exists
    try:
        new_status = PositionStatus(data.status)
    except ValueError:
        raise HTTPException(400, f"Invalid status: {data.status}")

    p.status = new_status
    p.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(p)
    return _serialize_position(p)
