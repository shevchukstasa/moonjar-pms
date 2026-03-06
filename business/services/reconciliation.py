"""
Stage Reconciliation service.
Business Logic: §13, §26
"""
from uuid import UUID
from datetime import date, datetime, timedelta
from math import ceil, floor
from typing import Optional

from sqlalchemy.orm import Session

from api.models import *  # noqa
from api.schemas import *  # noqa


def reconcile_stage_transition(db: Session, factory_id: UUID, batch_id: Optional[UUID], stage_from: str, stage_to: str, input_count: int, outputs: dict) -> dict:
    """Verify tile counts at stage transitions. Alert PM on discrepancy."""
    # TODO: implement — see BUSINESS_LOGIC.md §13, §26
    raise NotImplementedError

def inventory_reconciliation(db: Session, factory_id: UUID, section_id: UUID, counted_items: list[dict]) -> dict:
    """Periodic inventory reconciliation: counted vs system."""
    # TODO: implement — see BUSINESS_LOGIC.md §13, §26
    raise NotImplementedError
