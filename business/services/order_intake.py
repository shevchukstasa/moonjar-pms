"""
Order Intake Pipeline service.
Business Logic: §1-3
"""
from uuid import UUID
from datetime import date, datetime, timedelta
from math import ceil, floor
from typing import Optional

from sqlalchemy.orm import Session

from api.models import *  # noqa
from api.schemas import *  # noqa
from api.enums import is_stock_collection


def process_incoming_order(db: Session, payload: dict, source: str) -> dict:
    """Entry point: webhook/PDF/manual → order + positions."""
    # TODO: implement — see BUSINESS_LOGIC.md §1-3
    raise NotImplementedError

def assign_factory(db: Session, client_location: str) -> Factory:
    """Auto-assign factory by client region + load comparison."""
    # TODO: implement — see BUSINESS_LOGIC.md §1-3
    raise NotImplementedError

def estimate_factory_lead_time(db: Session, factory_id: UUID) -> dict:
    """GET /api/factories/{id}/estimate implementation."""
    # TODO: implement — see BUSINESS_LOGIC.md §1-3
    raise NotImplementedError

def process_order_item(db: Session, order: ProductionOrder, item: ProductionOrderItem) -> Optional[OrderPosition]:
    """Recipe lookup → position creation → blocking tasks + material reservation.

    STOCK: If is_stock_collection(item.collection), create position with
    status=TRANSFERRED_TO_SORTING and skip recipe lookup, material reservation,
    and blocking tasks. Stock items are pre-made.
    """
    # TODO: implement — see BUSINESS_LOGIC.md §1-3
    raise NotImplementedError

def check_blocking_tasks(db: Session, order: ProductionOrder, position: OrderPosition, item: ProductionOrderItem) -> None:
    """Create blocking tasks (stencil, silkscreen, color matching)."""
    # TODO: implement — see BUSINESS_LOGIC.md §1-3
    raise NotImplementedError
