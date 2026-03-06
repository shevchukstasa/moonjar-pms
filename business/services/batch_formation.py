"""
Batch Formation service.
Business Logic: §7, §19
"""
from uuid import UUID
from datetime import date, datetime, timedelta
from math import ceil, floor
from typing import Optional

from sqlalchemy.orm import Session

from api.models import *  # noqa
from api.schemas import *  # noqa


def suggest_or_create_batches(db: Session, factory_id: UUID) -> list:
    """Main entry: hybrid (suggested) or auto (planned) mode."""
    # TODO: implement — see BUSINESS_LOGIC.md §7, §19
    raise NotImplementedError

def build_batch_proposals(db: Session, factory_id: UUID, positions: list) -> list:
    """Group positions into optimal batch proposals."""
    # TODO: implement — see BUSINESS_LOGIC.md §7, §19
    raise NotImplementedError

def pm_confirm_batch(db: Session, batch_id: UUID, pm_user_id: UUID, adjustments: Optional[dict]) -> None:
    """PM confirms/adjusts a suggested batch."""
    # TODO: implement — see BUSINESS_LOGIC.md §7, §19
    raise NotImplementedError

def pm_reject_batch(db: Session, batch_id: UUID, pm_user_id: UUID) -> None:
    """PM rejects suggested batch → unassign all, delete."""
    # TODO: implement — see BUSINESS_LOGIC.md §7, §19
    raise NotImplementedError

def fill_with_filler_tiles(db: Session, factory_id: UUID) -> None:
    """Fill remaining space with filler tiles (Small kiln)."""
    # TODO: implement — see BUSINESS_LOGIC.md §7, §19
    raise NotImplementedError
