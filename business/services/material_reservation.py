"""
Material Reservation service.
Business Logic: §4
"""
from uuid import UUID
from datetime import date, datetime, timedelta
from math import ceil, floor
from typing import Optional

from sqlalchemy.orm import Session

from api.models import *  # noqa
from api.schemas import *  # noqa


def reserve_materials(db: Session, order: ProductionOrder, position: OrderPosition, recipe: Recipe) -> None:
    """Reserve BOM materials. Create purchase request if shortage."""
    # TODO: implement — see BUSINESS_LOGIC.md §4
    raise NotImplementedError

def create_consolidated_purchase_request(db: Session, order: ProductionOrder, shortages: list[dict]) -> None:
    """Merge shortages by supplier into purchase requests."""
    # TODO: implement — see BUSINESS_LOGIC.md §4
    raise NotImplementedError

def calculate_purchase_quantity(material: Material, deficit: float) -> float:
    """Pigments=exact, stone/frits=1 month ahead."""
    # TODO: implement — see BUSINESS_LOGIC.md §4
    raise NotImplementedError

def release_reservation(db: Session, material_id: UUID, position_id: UUID) -> None:
    """Release material reservation for a position."""
    # TODO: implement — see BUSINESS_LOGIC.md §4
    raise NotImplementedError
