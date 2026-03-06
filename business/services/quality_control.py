"""
Quality Control service.
Business Logic: §10, §25
"""
from uuid import UUID
from datetime import date, datetime, timedelta
from math import ceil, floor
from typing import Optional

from sqlalchemy.orm import Session

from api.models import *  # noqa
from api.schemas import *  # noqa


def assign_qc_checks(db: Session, factory_id: UUID, stage: str, positions: list) -> None:
    """Auto-assign minimum 2% for QC. Increase on defect."""
    # TODO: implement — see BUSINESS_LOGIC.md §10, §25
    raise NotImplementedError

def on_qc_defect_found(db: Session, factory_id: UUID, stage: str) -> None:
    """Increase inspection % when defect found."""
    # TODO: implement — see BUSINESS_LOGIC.md §10, §25
    raise NotImplementedError

def qm_block_production(db: Session, position_id: UUID, qm_user_id: UUID, reason: str, evidence_urls: list[str]) -> None:
    """QM blocks position with evidence photos."""
    # TODO: implement — see BUSINESS_LOGIC.md §10, §25
    raise NotImplementedError

def qm_unblock_production(db: Session, block_id: UUID, qm_user_id: UUID, resolution: str) -> None:
    """QM resolves block → position returns to previous status."""
    # TODO: implement — see BUSINESS_LOGIC.md §10, §25
    raise NotImplementedError
