"""
Min Balance Auto-Calculation service.
Business Logic: §18
"""
from uuid import UUID
from datetime import date, datetime, timedelta
from math import ceil, floor
from typing import Optional

from sqlalchemy.orm import Session

from api.models import *  # noqa
from api.schemas import *  # noqa


def recalculate_min_balance_recommendations(db: Session, factory_id: UUID) -> None:
    """Daily: min_balance = lead_time × avg_daily_consumption × 1.2."""
    # TODO: implement — see BUSINESS_LOGIC.md §18
    raise NotImplementedError

def get_effective_lead_time(db: Session, material: Material) -> int:
    """Supplier avg actual → supplier default → material type default."""
    # TODO: implement — see BUSINESS_LOGIC.md §18
    raise NotImplementedError

def pm_override_min_balance(db: Session, material_id: UUID, new_min_balance: float, pm_user_id: UUID) -> None:
    """PM manual override disables auto-calculation."""
    # TODO: implement — see BUSINESS_LOGIC.md §18
    raise NotImplementedError
