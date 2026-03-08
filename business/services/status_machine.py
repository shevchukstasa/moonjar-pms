"""
Position Status Machine service.
Business Logic: Implementation Guide §4.1, §32b
"""
from uuid import UUID
from datetime import date, datetime, timedelta
from math import ceil, floor
from typing import Optional

from sqlalchemy.orm import Session

from api.models import *  # noqa
from api.schemas import *  # noqa
from api.enums import PositionStatus


def validate_status_transition(current: str, new: str) -> bool:
    """Check if status transition is allowed."""
    # TODO: implement — see BUSINESS_LOGIC.md Implementation Guide §4.1
    raise NotImplementedError


def transition_position_status(db: Session, position_id: UUID, new_status: str, changed_by: UUID, is_override: bool = False) -> None:
    """Transition with validation + logging."""
    # TODO: implement — see BUSINESS_LOGIC.md Implementation Guide §4.1
    raise NotImplementedError


def route_after_firing(db: Session, position: OrderPosition) -> str:
    """
    Called when a position transitions to FIRED status.
    Determines next status based on multi-firing configuration.

    If position has more firing rounds remaining → route to SENT_TO_GLAZING
    (or PRE_KILN_CHECK if glazing not required) and increment firing_round.

    If this was the final firing → route to TRANSFERRED_TO_SORTING.

    Returns the new status string.
    """
    from business.services.firing_profiles import (
        get_total_firing_rounds,
        get_recipe_firing_stage,
    )

    if not position.recipe_id:
        # No recipe → single firing, go to sorting
        position.status = PositionStatus.TRANSFERRED_TO_SORTING
        return PositionStatus.TRANSFERRED_TO_SORTING.value

    total_rounds = get_total_firing_rounds(db, position.recipe_id)

    if position.firing_round < total_rounds:
        # More firing rounds needed → route back to glazing pipeline
        next_round = position.firing_round + 1
        next_stage = get_recipe_firing_stage(db, position.recipe_id, next_round)

        if next_stage and next_stage.requires_glazing_before:
            position.status = PositionStatus.SENT_TO_GLAZING
        else:
            position.status = PositionStatus.PRE_KILN_CHECK

        position.firing_round = next_round
        position.batch_id = None       # Unassign from current batch
        position.resource_id = None    # Unassign kiln

        return position.status.value
    else:
        # Final firing done → sorting
        position.status = PositionStatus.TRANSFERRED_TO_SORTING
        return PositionStatus.TRANSFERRED_TO_SORTING.value
