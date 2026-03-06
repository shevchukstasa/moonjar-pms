"""
Material Consumption service.
Business Logic: §16, §21
"""
from uuid import UUID
from datetime import date, datetime, timedelta
from math import ceil, floor
from typing import Optional

from sqlalchemy.orm import Session

from api.models import *  # noqa
from api.schemas import *  # noqa


def on_glazing_start(db: Session, position_id: UUID, actual_quantities: Optional[dict]) -> None:
    """Consume BOM materials when glazing starts."""
    # TODO: implement — see BUSINESS_LOGIC.md §16, §21
    raise NotImplementedError

def consume_refire_materials(db: Session, position_id: UUID) -> None:
    """Refire/reglaze: consume surface materials only (skip stone)."""
    # TODO: implement — see BUSINESS_LOGIC.md §16, §21
    raise NotImplementedError
