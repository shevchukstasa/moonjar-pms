"""
Partial Delivery service.
Business Logic: §22
"""
from uuid import UUID
from datetime import date, datetime, timedelta
from math import ceil, floor
from typing import Optional

from sqlalchemy.orm import Session

from api.models import *  # noqa
from api.schemas import *  # noqa


def handle_partial_delivery(db: Session, purchase_request_id: UUID, received_items: list[dict], pm_user_id: UUID) -> None:
    """Accept partial, create PM task for deficit decision."""
    # TODO: implement — see BUSINESS_LOGIC.md §22
    raise NotImplementedError

def pm_resolve_partial_delivery(db: Session, task_id: UUID, decision: str, pm_user_id: UUID, alt_supplier_id: Optional[UUID]) -> None:
    """PM decides: reorder_same/reorder_other/skip."""
    # TODO: implement — see BUSINESS_LOGIC.md §22
    raise NotImplementedError
