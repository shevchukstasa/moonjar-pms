"""
Kiln Assignment service.
Business Logic: §6
"""
from uuid import UUID
from datetime import date, datetime, timedelta
from math import ceil, floor
from typing import Optional

from sqlalchemy.orm import Session

from api.models import *  # noqa
from api.schemas import *  # noqa


def assign_kiln(db: Session, position: OrderPosition) -> Optional[dict]:
    """Full kiln assignment: Raku → countertop → size check → capacity → alternation."""
    # TODO: implement — see BUSINESS_LOGIC.md §6
    raise NotImplementedError

def check_fits_large(db: Session, position: OrderPosition, kiln: Resource) -> Optional[dict]:
    """Check if product fits Large kiln and calculate optimal loading."""
    # TODO: implement — see BUSINESS_LOGIC.md §6
    raise NotImplementedError

def check_fits_small(db: Session, position: OrderPosition, kiln: Resource) -> Optional[dict]:
    """Check if product fits Small kiln."""
    # TODO: implement — see BUSINESS_LOGIC.md §6
    raise NotImplementedError

def can_load_on_edge(position: OrderPosition, kiln_type: str, constants: dict) -> bool:
    """Edge loading rules: face_only/edges_1/edges_2 + rectangle/triangle."""
    # TODO: implement — see BUSINESS_LOGIC.md §6
    raise NotImplementedError

def calculate_flat_loading(position: OrderPosition, kiln: Resource, constants: dict) -> dict:
    """Pieces per level × levels × coefficient."""
    # TODO: implement — see BUSINESS_LOGIC.md §6
    raise NotImplementedError

def calculate_edge_loading(position: OrderPosition, kiln: Resource, constants: dict) -> dict:
    """Edge pairs + flat-on-top per level."""
    # TODO: implement — see BUSINESS_LOGIC.md §6
    raise NotImplementedError

def get_next_kiln_in_rotation(db: Session, factory_id: UUID) -> Resource:
    """Configurable rotation: default Large→Small→Large."""
    # TODO: implement — see BUSINESS_LOGIC.md §6
    raise NotImplementedError
