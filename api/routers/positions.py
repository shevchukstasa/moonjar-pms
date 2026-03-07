"""Positions router — list, status transitions, sorting split, filtering by section."""

import uuid as uuid_mod
from datetime import datetime, timezone
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_

from api.database import get_db
from api.auth import get_current_user, apply_factory_filter
from api.roles import require_management, require_sorting
from api.models import OrderPosition, ProductionOrder, DefectRecord, GrindingStock, RepairQueue
from api.enums import (
    PositionStatus, SplitCategory, DefectStage, DefectOutcome,
    GrindingStatus, RepairStatus,
)

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


# ---------- Sorting Split ----------

class SortingSplitRequest(BaseModel):
    good_quantity: int
    repair_quantity: int = 0
    color_mismatch_quantity: int = 0
    grinding_quantity: int = 0
    write_off_quantity: int = 0
    notes: Optional[str] = None


@router.post("/{position_id}/split")
async def split_position(
    position_id: UUID,
    data: SortingSplitRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_sorting),
):
    """Sort a fired position: split into good/repair/color_mismatch/grinding/write-off."""

    p = db.query(OrderPosition).filter(OrderPosition.id == position_id).first()
    if not p:
        raise HTTPException(404, "Position not found")

    if _ev(p.status) != "transferred_to_sorting":
        raise HTTPException(400, f"Position status must be 'transferred_to_sorting', got '{_ev(p.status)}'")

    total = (
        data.good_quantity + data.repair_quantity + data.color_mismatch_quantity
        + data.grinding_quantity + data.write_off_quantity
    )
    if total != p.quantity:
        raise HTTPException(
            400,
            f"Total ({total}) must equal position quantity ({p.quantity})",
        )

    now = datetime.now(timezone.utc)
    sub_positions = []
    grinding_record = None
    defect_record = None

    # 1. Update parent — good quantity, mark as packed
    p.quantity = data.good_quantity
    p.status = PositionStatus.PACKED
    p.updated_at = now

    # 2. Repair sub-position
    if data.repair_quantity > 0:
        repair_pos = OrderPosition(
            id=uuid_mod.uuid4(),
            order_id=p.order_id,
            order_item_id=p.order_item_id,
            parent_position_id=p.id,
            factory_id=p.factory_id,
            status=PositionStatus.SENT_TO_GLAZING,
            quantity=data.repair_quantity,
            color=p.color,
            size=p.size,
            application=p.application,
            finishing=p.finishing,
            collection=p.collection,
            application_type=p.application_type,
            place_of_application=p.place_of_application,
            product_type=p.product_type,
            shape=p.shape,
            thickness_mm=p.thickness_mm,
            recipe_id=p.recipe_id,
            mandatory_qc=p.mandatory_qc,
            split_category=SplitCategory.REPAIR,
            priority_order=p.priority_order,
            created_at=now,
            updated_at=now,
        )
        db.add(repair_pos)
        sub_positions.append(repair_pos)

        # Repair queue entry for SLA tracking
        rq = RepairQueue(
            id=uuid_mod.uuid4(),
            factory_id=p.factory_id,
            color=p.color,
            size=p.size,
            quantity=data.repair_quantity,
            defect_type="sorting_repair",
            source_order_id=p.order_id,
            source_position_id=p.id,
            status=RepairStatus.IN_REPAIR,
            created_at=now,
            updated_at=now,
        )
        db.add(rq)

    # 3. Color mismatch sub-position
    if data.color_mismatch_quantity > 0:
        cm_pos = OrderPosition(
            id=uuid_mod.uuid4(),
            order_id=p.order_id,
            order_item_id=p.order_item_id,
            parent_position_id=p.id,
            factory_id=p.factory_id,
            status=PositionStatus.PLANNED,
            quantity=data.color_mismatch_quantity,
            color=p.color,
            size=p.size,
            application=p.application,
            finishing=p.finishing,
            collection=p.collection,
            application_type=p.application_type,
            place_of_application=p.place_of_application,
            product_type=p.product_type,
            shape=p.shape,
            thickness_mm=p.thickness_mm,
            recipe_id=p.recipe_id,
            mandatory_qc=p.mandatory_qc,
            split_category=SplitCategory.COLOR_MISMATCH,
            priority_order=p.priority_order,
            created_at=now,
            updated_at=now,
        )
        db.add(cm_pos)
        sub_positions.append(cm_pos)

    # 4. Grinding stock
    if data.grinding_quantity > 0:
        gs = GrindingStock(
            id=uuid_mod.uuid4(),
            factory_id=p.factory_id,
            color=p.color,
            size=p.size,
            quantity=data.grinding_quantity,
            source_order_id=p.order_id,
            source_position_id=p.id,
            status=GrindingStatus.IN_STOCK,
            created_at=now,
            updated_at=now,
        )
        db.add(gs)
        grinding_record = {
            "id": str(gs.id),
            "color": gs.color,
            "size": gs.size,
            "quantity": gs.quantity,
        }

    # 5. Write-off defect record
    if data.write_off_quantity > 0:
        dr = DefectRecord(
            id=uuid_mod.uuid4(),
            factory_id=p.factory_id,
            stage=DefectStage.SORTING,
            position_id=p.id,
            defect_type="sorting_write_off",
            quantity=data.write_off_quantity,
            outcome=DefectOutcome.WRITE_OFF,
            reported_by=current_user.id,
            reported_via="dashboard",
            notes=data.notes,
            created_at=now,
        )
        db.add(dr)
        defect_record = {
            "id": str(dr.id),
            "quantity": dr.quantity,
            "outcome": "write_off",
        }

    db.commit()
    db.refresh(p)
    for sp in sub_positions:
        db.refresh(sp)

    return {
        "parent_position": _serialize_position(p),
        "sub_positions": [_serialize_position(sp) for sp in sub_positions],
        "grinding_record": grinding_record,
        "defect_record": defect_record,
        "reconciliation": {
            "input_total": total,
            "good": data.good_quantity,
            "repair": data.repair_quantity,
            "color_mismatch": data.color_mismatch_quantity,
            "grinding": data.grinding_quantity,
            "write_off": data.write_off_quantity,
        },
    }
