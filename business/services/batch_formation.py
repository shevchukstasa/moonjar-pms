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
from api.enums import PositionStatus, BatchStatus


def suggest_or_create_batches(db: Session, factory_id: UUID) -> list:
    """
    Main entry: hybrid (suggested) or auto (planned) mode.

    Enhanced with temperature-based grouping:
    1. Get all unassigned positions ready for kiln (GLAZED, PRE_KILN_CHECK)
    2. Group into temperature-compatible buckets
    3. Within each bucket → assign to kilns, create batches
    4. For each batch → assign slowest firing profile
    """
    # TODO: implement full logic — see BUSINESS_LOGIC.md §7, §19
    # Temperature grouping is implemented in firing_profiles.group_positions_by_temperature()
    raise NotImplementedError


def build_batch_proposals(db: Session, factory_id: UUID, positions: list) -> list:
    """
    Group positions into optimal batch proposals.

    Steps:
    1. Group by temperature using firing_profiles.group_positions_by_temperature()
    2. Within each temperature bucket:
       a. Match to compatible kilns (from kiln_loading_rules)
       b. Fill kiln capacity, respecting co-firing rules
       c. Select firing profile using get_batch_firing_profile() — slowest wins
    3. Return list of batch proposals with assigned positions + profiles
    """
    # TODO: implement — see BUSINESS_LOGIC.md §7, §19
    raise NotImplementedError


def assign_batch_firing_profile(db: Session, batch_id: UUID) -> None:
    """
    Determine and store the firing profile for a batch.
    Uses get_batch_firing_profile() — slowest profile among batch positions wins.
    Stores firing_profile_id and target_temperature on the batch record.
    """
    from business.services.firing_profiles import get_batch_firing_profile

    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        return

    positions = (
        db.query(OrderPosition)
        .filter(OrderPosition.batch_id == batch_id)
        .all()
    )
    if not positions:
        return

    profile = get_batch_firing_profile(db, positions)
    if profile:
        batch.firing_profile_id = profile.id
        batch.target_temperature = profile.target_temperature
        db.commit()


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
