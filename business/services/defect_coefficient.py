"""
Stone Defect Coefficient service.
Business Logic: §14
"""
from uuid import UUID
from datetime import date, datetime, timedelta
from math import ceil, floor
from typing import Optional

from sqlalchemy.orm import Session

from api.models import *  # noqa
from api.schemas import *  # noqa


def update_stone_defect_coefficient(db: Session, factory_id: UUID) -> None:
    """Daily: running defect coefficient from stages 1+2."""
    # TODO: implement — see BUSINESS_LOGIC.md §14
    raise NotImplementedError

def get_stone_defect_coefficient(db: Session, factory_id: UUID, stone_type: str) -> float:
    """Get current coefficient for a stone type."""
    # TODO: implement — see BUSINESS_LOGIC.md §14
    raise NotImplementedError
