"""
Production planning engine — schedule calculation.
Integrates: kiln assignment + batch formation + TOC rope.
"""
from uuid import UUID
from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session


def generate_production_schedule(db: Session, factory_id: UUID, horizon_days: int = 14) -> dict:
    """
    Generate production schedule for the next N days.
    Steps:
    1. Get all unscheduled positions
    2. Assign kilns (business.kiln.assign_kiln)
    3. Form batches (business.services.batch_formation)
    4. Apply TOC rope limits
    5. Create daily task distribution
    Returns: {days: [{date, glazing: [...], kiln_loading: [...]}]}
    """
    # TODO: implement
    raise NotImplementedError


def recalculate_schedule(db: Session, factory_id: UUID):
    """Recalculate after capacity change (kiln breakdown, new order, cancellation)."""
    # TODO: implement
    raise NotImplementedError
