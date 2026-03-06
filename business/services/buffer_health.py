"""
Buffer Health (TOC) service.
Business Logic: §17, §20
"""
from uuid import UUID
from datetime import date, datetime, timedelta
from math import ceil, floor
from typing import Optional

from sqlalchemy.orm import Session

from api.models import *  # noqa
from api.schemas import *  # noqa


def calculate_buffer_health(db: Session, factory_id: UUID) -> Optional[dict]:
    """Buffer = glazed items before kiln. Green/yellow/red."""
    # TODO: implement — see BUSINESS_LOGIC.md §17, §20
    raise NotImplementedError

def apply_rope_limit(db: Session, factory_id: UUID, positions: list) -> list:
    """TOC Rope: limit work release to N days ahead of kiln."""
    # TODO: implement — see BUSINESS_LOGIC.md §17, §20
    raise NotImplementedError
