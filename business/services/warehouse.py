"""
Warehouse Operations service.
Business Logic: §28
"""
from uuid import UUID
from datetime import date, datetime, timedelta
from math import ceil, floor
from typing import Optional

from sqlalchemy.orm import Session

from api.models import *  # noqa
from api.schemas import *  # noqa


def receive_material(db: Session, material_id: UUID, quantity: float, warehouse_user_id: UUID, needs_pm_approval: bool) -> None:
    """Warehouse receives material, optionally requires PM approval."""
    # TODO: implement — see BUSINESS_LOGIC.md §28
    raise NotImplementedError

def pm_approve_receipt(db: Session, receipt_id: UUID, pm_user_id: UUID, approved: bool) -> None:
    """PM approves/rejects warehouse receipt."""
    # TODO: implement — see BUSINESS_LOGIC.md §28
    raise NotImplementedError
