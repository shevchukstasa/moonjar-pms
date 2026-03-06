"""
Sorting & Split service.
Business Logic: §8-9
"""
from uuid import UUID
from datetime import date, datetime, timedelta
from math import ceil, floor
from typing import Optional

from sqlalchemy.orm import Session

from api.models import *  # noqa
from api.schemas import *  # noqa


def process_sorting_split(db: Session, position_id: UUID, split_data: dict) -> dict:
    """Sorter enters quantities → sub-positions + defect records."""
    # TODO: implement — see BUSINESS_LOGIC.md §8-9
    raise NotImplementedError

def create_sub_position(db: Session, parent: OrderPosition, quantity: int, split_category: str, status: str) -> OrderPosition:
    """Create sub-position inheriting parent characteristics."""
    # TODO: implement — see BUSINESS_LOGIC.md §8-9
    raise NotImplementedError

def handle_surplus(db: Session, position: OrderPosition, surplus_quantity: int) -> None:
    """10x10 base→showroom, 10x10 non-base→casters, other→Manu."""
    # TODO: implement — see BUSINESS_LOGIC.md §8-9
    raise NotImplementedError

def merge_sub_position_back(db: Session, sub_position_id: UUID) -> None:
    """Merge repaired sub-position back into parent."""
    # TODO: implement — see BUSINESS_LOGIC.md §8-9
    raise NotImplementedError
