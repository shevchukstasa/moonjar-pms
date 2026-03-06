"""
Schedule Estimation service.
Business Logic: §5
"""
from uuid import UUID
from datetime import date, datetime, timedelta
from math import ceil, floor
from typing import Optional

from sqlalchemy.orm import Session

from api.models import *  # noqa
from api.schemas import *  # noqa


def calculate_schedule_deadline(db: Session, order: ProductionOrder) -> date:
    """Formula: max_availability + production_days + buffer."""
    # TODO: implement — see BUSINESS_LOGIC.md §5
    raise NotImplementedError

def calculate_position_availability(db: Session, position: OrderPosition) -> date:
    """Max across all blocking factors for a position."""
    # TODO: implement — see BUSINESS_LOGIC.md §5
    raise NotImplementedError

def calculate_production_days(db: Session, order: ProductionOrder) -> int:
    """Based on avg production speed + kiln schedule."""
    # TODO: implement — see BUSINESS_LOGIC.md §5
    raise NotImplementedError

def calculate_buffer(production_days: int) -> int:
    """Buffer = max(2, min(5, ceil(production_days * 0.10)))."""
    # TODO: implement — see BUSINESS_LOGIC.md §5
    raise NotImplementedError

def recalculate_all_estimates(db: Session, factory_id: UUID) -> None:
    """Recalculate all active order estimates after capacity change."""
    # TODO: implement — see BUSINESS_LOGIC.md §5
    raise NotImplementedError
