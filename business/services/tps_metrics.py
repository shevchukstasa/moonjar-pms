"""
TPS Lean Metrics service.
Business Logic: §23
"""
from uuid import UUID
from datetime import date, datetime, timedelta
from math import ceil, floor
from typing import Optional

from sqlalchemy.orm import Session

from api.models import *  # noqa
from api.schemas import *  # noqa


def collect_shift_metrics(db: Session, factory_id: UUID, shift_date: date) -> dict:
    """Collect TPS metrics for a shift."""
    # TODO: implement — see BUSINESS_LOGIC.md §23
    raise NotImplementedError

def evaluate_signal(db: Session, factory_id: UUID) -> str:
    """Signal system: green/red based on targets."""
    # TODO: implement — see BUSINESS_LOGIC.md §23
    raise NotImplementedError
