"""
Sorting & Split service.
Business Logic: §8-9
"""
from uuid import UUID
import uuid as uuid_mod
from datetime import date, datetime, timedelta
from math import ceil, floor
from typing import Optional

from sqlalchemy.orm import Session

from api.models import *  # noqa
from api.schemas import *  # noqa
from api.enums import (
    TaskType, SurplusDispositionType,
    PositionStatus, UserRole, ManuShipmentStatus,
)


def process_sorting_split(db: Session, position_id: UUID, split_data: dict) -> dict:
    """Sorter enters quantities → sub-positions + defect records."""
    # TODO: implement — see BUSINESS_LOGIC.md §8-9
    raise NotImplementedError


def create_sub_position(db: Session, parent: OrderPosition, quantity: int, split_category: str, status: str) -> OrderPosition:
    """Create sub-position inheriting parent characteristics."""
    # TODO: implement — see BUSINESS_LOGIC.md §8-9
    raise NotImplementedError


def _check_is_basic_color(db: Session, color_name: str) -> bool:
    """Check if a color is basic by looking up colors.is_basic."""
    color = db.query(Color).filter(Color.name == color_name).first()
    if color is None:
        return False
    return bool(color.is_basic)


def handle_surplus(db: Session, position: OrderPosition, surplus_quantity: int) -> Optional[SurplusDisposition]:
    """
    After firing: if more tiles than needed, distribute surplus.
    Rules by size and base color (BUSINESS_LOGIC.md §9):
      - 10x10 + basic color → showroom (+ photographing task)
      - 10x10 + non-basic color → casters boxes
      - All other sizes → Manu
    """
    size = position.size
    color = position.color
    is_basic = _check_is_basic_color(db, color)

    if size == '10x10' and is_basic:
        # → Showroom: create transfer task + photographing task
        showroom_task = Task(
            id=uuid_mod.uuid4(),
            factory_id=position.factory_id,
            type=TaskType.SHOWROOM_TRANSFER,
            assigned_role=UserRole.SORTER_PACKER,
            related_order_id=position.order_id,
            related_position_id=position.id,
            description=f"Send {surplus_quantity} pcs {color} 10x10 to showroom display board",
            priority=3,
        )
        db.add(showroom_task)

        photo_task = Task(
            id=uuid_mod.uuid4(),
            factory_id=position.factory_id,
            type=TaskType.PHOTOGRAPHING,
            assigned_role=UserRole.PRODUCTION_MANAGER,
            related_order_id=position.order_id,
            related_position_id=position.id,
            description=f"Photograph surplus {color} 10x10 for catalog",
            priority=3,
        )
        db.add(photo_task)

        disposition = SurplusDisposition(
            id=uuid_mod.uuid4(),
            factory_id=position.factory_id,
            order_id=position.order_id,
            position_id=position.id,
            surplus_quantity=surplus_quantity,
            disposition_type=SurplusDispositionType.SHOWROOM,
            size=size,
            color=color,
            is_base_color=True,
            task_id=showroom_task.id,
        )
        db.add(disposition)
        return disposition

    elif size == '10x10' and not is_basic:
        # → Casters boxes: accumulate by color+size into casters_boxes table.
        # When the box has enough tiles it will be shipped to Manu.
        existing_box = db.query(CastersBox).filter(
            CastersBox.factory_id == position.factory_id,
            CastersBox.color == color,
            CastersBox.size == size,
            CastersBox.removed_at.is_(None),  # only active boxes
        ).first()
        if existing_box:
            existing_box.quantity += surplus_quantity
        else:
            new_box = CastersBox(
                id=uuid_mod.uuid4(),
                factory_id=position.factory_id,
                color=color,
                size=size,
                quantity=surplus_quantity,
                source_order_id=position.order_id,
            )
            db.add(new_box)

        disposition = SurplusDisposition(
            id=uuid_mod.uuid4(),
            factory_id=position.factory_id,
            order_id=position.order_id,
            position_id=position.id,
            surplus_quantity=surplus_quantity,
            disposition_type=SurplusDispositionType.CASTERS,
            size=size,
            color=color,
            is_base_color=False,
        )
        db.add(disposition)
        return disposition

    else:
        # All other sizes → Manu: accumulate items into the current PENDING manu shipment.
        # When ready, the manager confirms the shipment.
        pending_shipment = db.query(ManuShipment).filter(
            ManuShipment.factory_id == position.factory_id,
            ManuShipment.status == ManuShipmentStatus.PENDING,
        ).first()
        item_entry = {
            "color": color,
            "size": size,
            "quantity": surplus_quantity,
            "source_order_id": str(position.order_id),
            "source_position_id": str(position.id),
        }
        if pending_shipment:
            current_items = list(pending_shipment.items_json) if pending_shipment.items_json else []
            current_items.append(item_entry)
            pending_shipment.items_json = current_items
        else:
            new_shipment = ManuShipment(
                id=uuid_mod.uuid4(),
                factory_id=position.factory_id,
                items_json=[item_entry],
                status=ManuShipmentStatus.PENDING,
            )
            db.add(new_shipment)

        disposition = SurplusDisposition(
            id=uuid_mod.uuid4(),
            factory_id=position.factory_id,
            order_id=position.order_id,
            position_id=position.id,
            surplus_quantity=surplus_quantity,
            disposition_type=SurplusDispositionType.MANU,
            size=size,
            color=color,
            is_base_color=is_basic,
        )
        db.add(disposition)
        return disposition


def merge_sub_position_back(db: Session, sub_position_id: UUID) -> None:
    """Merge repaired sub-position back into parent."""
    # TODO: implement — see BUSINESS_LOGIC.md §8-9
    raise NotImplementedError
