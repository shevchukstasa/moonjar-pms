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
    PositionStatus, UserRole,
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
        # → Casters boxes
        # TODO: add_to_casters_box — accumulate in casters_boxes table
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
        # All other sizes → Manu
        # TODO: add_to_manu_pending — accumulate in manu_shipments
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
