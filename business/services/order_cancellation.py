"""
Order Cancellation service.
Business Logic: §15
"""
from uuid import UUID
from datetime import date, datetime, timedelta
from math import ceil, floor
from typing import Optional

from sqlalchemy.orm import Session

from api.models import *  # noqa
from api.schemas import *  # noqa


def process_order_cancellation(db: Session, order_id: UUID, confirmed_by: UUID) -> None:
    """Cancel positions → tasks → release materials → handle produced tiles."""
    # TODO: implement — see BUSINESS_LOGIC.md §15
    raise NotImplementedError
