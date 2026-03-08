"""
Position Status Machine service.
Business Logic: Implementation Guide §4.1, §32b

Defines allowed transitions and provides validated transition logic.
"""
from uuid import UUID
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from api.models import OrderPosition
from api.enums import PositionStatus


# ────────────────────────────────────────────────────────────────
# §4.1  Allowed status transitions
# ────────────────────────────────────────────────────────────────
# Key = current status, Value = set of allowed next statuses.
# "blocked_by_qm" and "cancelled" are reachable from ANY status.

_TRANSITIONS: dict[PositionStatus, set[PositionStatus]] = {
    PositionStatus.PLANNED: {
        PositionStatus.INSUFFICIENT_MATERIALS,
        PositionStatus.AWAITING_RECIPE,
        PositionStatus.AWAITING_STENCIL_SILKSCREEN,
        PositionStatus.AWAITING_COLOR_MATCHING,
        PositionStatus.ENGOBE_APPLIED,
        PositionStatus.GLAZED,  # if no engobe needed
    },
    PositionStatus.INSUFFICIENT_MATERIALS: {
        PositionStatus.PLANNED,
    },
    PositionStatus.AWAITING_RECIPE: {
        PositionStatus.PLANNED,
    },
    PositionStatus.AWAITING_STENCIL_SILKSCREEN: {
        PositionStatus.PLANNED,
    },
    PositionStatus.AWAITING_COLOR_MATCHING: {
        PositionStatus.PLANNED,
    },
    PositionStatus.ENGOBE_APPLIED: {
        PositionStatus.ENGOBE_CHECK,
    },
    PositionStatus.ENGOBE_CHECK: {
        PositionStatus.GLAZED,
        PositionStatus.ENGOBE_APPLIED,  # redo
    },
    PositionStatus.GLAZED: {
        PositionStatus.PRE_KILN_CHECK,
    },
    PositionStatus.PRE_KILN_CHECK: {
        PositionStatus.LOADED_IN_KILN,
        PositionStatus.SENT_TO_GLAZING,  # needs redo
    },
    PositionStatus.SENT_TO_GLAZING: {
        PositionStatus.PLANNED,  # re-enters glazing pipeline
    },
    PositionStatus.LOADED_IN_KILN: {
        PositionStatus.FIRED,
    },
    PositionStatus.FIRED: {
        PositionStatus.TRANSFERRED_TO_SORTING,
        PositionStatus.REFIRE,
        PositionStatus.SENT_TO_GLAZING,  # multi-firing route
    },
    PositionStatus.TRANSFERRED_TO_SORTING: {
        PositionStatus.PACKED,
        PositionStatus.SENT_TO_GLAZING,  # repair
        PositionStatus.AWAITING_REGLAZE,
    },
    PositionStatus.AWAITING_REGLAZE: {
        PositionStatus.SENT_TO_GLAZING,
    },
    PositionStatus.REFIRE: {
        PositionStatus.LOADED_IN_KILN,
    },
    PositionStatus.PACKED: {
        PositionStatus.SENT_TO_QUALITY_CHECK,
        PositionStatus.READY_FOR_SHIPMENT,
    },
    PositionStatus.SENT_TO_QUALITY_CHECK: {
        PositionStatus.QUALITY_CHECK_DONE,
    },
    PositionStatus.QUALITY_CHECK_DONE: {
        PositionStatus.READY_FOR_SHIPMENT,
    },
    PositionStatus.READY_FOR_SHIPMENT: {
        PositionStatus.SHIPPED,
    },
    PositionStatus.BLOCKED_BY_QM: set(),  # dynamically returns to previous status
    PositionStatus.SHIPPED: set(),
    PositionStatus.CANCELLED: set(),
}

# Universal transitions: any status → blocked_by_qm / cancelled
_UNIVERSAL_TARGETS = {PositionStatus.BLOCKED_BY_QM, PositionStatus.CANCELLED}


# ────────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────────

def validate_status_transition(current: str, new: str) -> bool:
    """
    Check if status transition is allowed.
    Returns True if the transition is valid, False otherwise.
    """
    try:
        current_ps = PositionStatus(current)
        new_ps = PositionStatus(new)
    except ValueError:
        return False

    # Universal targets (blocked_by_qm, cancelled) allowed from any status
    if new_ps in _UNIVERSAL_TARGETS:
        return True

    # blocked_by_qm can go to any status (returns to previous)
    if current_ps == PositionStatus.BLOCKED_BY_QM:
        return True

    allowed = _TRANSITIONS.get(current_ps, set())
    return new_ps in allowed


def get_allowed_transitions(current: str) -> list[str]:
    """Return list of allowed next statuses for a given current status."""
    try:
        current_ps = PositionStatus(current)
    except ValueError:
        return []

    allowed = set(_TRANSITIONS.get(current_ps, set()))
    # Always add universal targets
    allowed |= _UNIVERSAL_TARGETS
    return sorted([s.value for s in allowed])


def transition_position_status(
    db: Session,
    position_id: UUID,
    new_status: str,
    changed_by: UUID,
    is_override: bool = False,
    notes: Optional[str] = None,
) -> OrderPosition:
    """
    Validate and apply a status transition on an OrderPosition.

    - Validates transition (unless is_override=True for PM/admin overrides)
    - Updates position status
    - Fires special routing for FIRED status (multi-firing)
    - Returns updated position

    Raises ValueError if transition is invalid.
    """
    position = db.query(OrderPosition).filter(OrderPosition.id == position_id).first()
    if not position:
        raise ValueError(f"Position {position_id} not found")

    old_status = position.status.value if isinstance(position.status, PositionStatus) else str(position.status)
    new_status_str = new_status

    # Validate unless override
    if not is_override:
        if not validate_status_transition(old_status, new_status_str):
            allowed = get_allowed_transitions(old_status)
            raise ValueError(
                f"Invalid transition: {old_status} → {new_status_str}. "
                f"Allowed: {allowed}"
            )

    # Apply status
    try:
        new_ps = PositionStatus(new_status_str)
    except ValueError:
        raise ValueError(f"Invalid status value: {new_status_str}")

    position.status = new_ps
    position.updated_at = datetime.now(timezone.utc)

    # Special routing: FIRED → multi-firing check
    if new_ps == PositionStatus.FIRED:
        route_after_firing(db, position)

    db.commit()
    db.refresh(position)
    return position


# ────────────────────────────────────────────────────────────────
# Multi-firing routing (from §32b)
# ────────────────────────────────────────────────────────────────

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
