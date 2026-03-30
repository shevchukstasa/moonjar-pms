"""
PM Mid-Production Split service.
Splits a position during production (any stage except loaded_in_kiln).
Parent position is frozen (is_parent=True); children run full cycle independently.
Decision 2026-03-19.
"""
import uuid
from datetime import datetime, timezone
from typing import List
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import text

from api.models import OrderPosition


def can_split_position(position: OrderPosition) -> tuple[bool, str]:
    """
    Check if position can be split mid-production.
    Returns (can_split, reason_if_not).
    """
    status_val = position.status.value if hasattr(position.status, 'value') else str(position.status)

    if status_val == 'loaded_in_kiln':
        return False, "Cannot split position while loaded in kiln"

    if getattr(position, 'is_parent', False):
        return False, "Position is already split (is_parent=True)"

    # Sorting sub-positions (split_category is set) cannot be production-split
    if position.split_category is not None:
        return False, "Cannot production-split a sorting sub-position"

    return True, ""


def split_position_mid_production(
    db: Session,
    position: OrderPosition,
    splits: List[dict],  # [{quantity, quantity_sqm?, priority_order?, note?}]
    reason: str,
    created_by_id: UUID,
) -> List[OrderPosition]:
    """
    Split position during production.

    splits must sum to parent.quantity.
    Returns list of child positions.
    """
    # 1. Validate
    can_split, err = can_split_position(position)
    if not can_split:
        raise ValueError(err)

    if len(splits) < 2:
        raise ValueError("Need at least 2 parts to split")

    total_qty = sum(s['quantity'] for s in splits)
    if total_qty != position.quantity:
        raise ValueError(
            f"Split quantities ({total_qty}) must equal position quantity ({position.quantity})"
        )

    # 2. Capture original status
    original_status = position.status.value if hasattr(position.status, 'value') else str(position.status)

    # 3. Freeze parent — use raw SQL for the new columns that may not be in the ORM model yet
    now = datetime.now(timezone.utc)

    db.execute(
        text("""
            UPDATE order_positions
            SET is_parent      = TRUE,
                split_type     = 'production',
                split_stage    = :stage,
                split_at       = :split_at,
                split_reason   = :reason,
                updated_at     = :now
            WHERE id = :id
        """),
        {
            'stage': original_status,
            'split_at': now,
            'reason': reason,
            'now': now,
            'id': str(position.id),
        },
    )

    # Refresh in-memory object so subsequent reads see the updated columns
    db.refresh(position)

    # 4. Determine next split_index base for new children
    from sqlalchemy import func
    base_si_result = db.query(func.max(OrderPosition.split_index)).filter(
        OrderPosition.parent_position_id == position.id,
    ).scalar()
    base_si = base_si_result or 0

    # 5. Create child positions
    children: List[OrderPosition] = []
    for i, split_spec in enumerate(splits):
        base_si += 1
        child = _clone_position_for_split(
            db=db,
            parent=position,
            split_spec=split_spec,
            split_index=base_si,
            original_status=original_status,
            reason=reason,
            now=now,
        )
        db.add(child)
        children.append(child)

    db.flush()
    return children


def _clone_position_for_split(
    db: Session,
    parent: OrderPosition,
    split_spec: dict,
    split_index: int,
    original_status: str,
    reason: str,
    now: datetime,
) -> OrderPosition:
    """Create a child position by cloning parent with new quantity."""
    child = OrderPosition(
        id=uuid.uuid4(),
        order_id=parent.order_id,
        order_item_id=parent.order_item_id,
        parent_position_id=parent.id,
        factory_id=parent.factory_id,
        # Inherit the parent's pre-freeze status so child continues from the same stage
        status=parent.status,
        quantity=split_spec['quantity'],
        color=parent.color,
        color_2=parent.color_2,
        size=parent.size,
        application=parent.application,
        finishing=parent.finishing,
        collection=parent.collection,
        application_type=parent.application_type,
        place_of_application=parent.place_of_application,
        product_type=parent.product_type,
        shape=parent.shape,
        thickness_mm=parent.thickness_mm,
        length_cm=parent.length_cm,
        width_cm=parent.width_cm,
        depth_cm=parent.depth_cm,
        bowl_shape=parent.bowl_shape,
        glazeable_sqm=parent.glazeable_sqm,
        recipe_id=parent.recipe_id,
        size_id=parent.size_id,
        mandatory_qc=parent.mandatory_qc,
        priority_order=split_spec.get('priority_order', parent.priority_order or 0),
        firing_round=parent.firing_round,
        two_stage_firing=parent.two_stage_firing,
        two_stage_type=parent.two_stage_type,
        planned_glazing_date=parent.planned_glazing_date,
        planned_kiln_date=parent.planned_kiln_date,
        planned_sorting_date=parent.planned_sorting_date,
        planned_completion_date=parent.planned_completion_date,
        estimated_kiln_id=parent.estimated_kiln_id,
        position_number=parent.position_number,
        split_index=split_index,
        created_at=now,
        updated_at=now,
    )

    # quantity_sqm: use explicit value if provided, otherwise scale proportionally
    if split_spec.get('quantity_sqm') is not None:
        child.quantity_sqm = split_spec['quantity_sqm']
    elif parent.quantity_sqm and parent.quantity > 0:
        proportion = split_spec['quantity'] / parent.quantity
        child.quantity_sqm = round(float(parent.quantity_sqm) * proportion, 3)

    # quantity_with_defect_margin: scale proportionally
    if parent.quantity_with_defect_margin and parent.quantity > 0:
        proportion = split_spec['quantity'] / parent.quantity
        child.quantity_with_defect_margin = round(parent.quantity_with_defect_margin * proportion)

    return child


def get_split_tree(db: Session, position_id: UUID) -> dict:
    """
    Get full split tree for a position.
    Returns nested dict: position + all descendants.
    """
    position = db.query(OrderPosition).filter(OrderPosition.id == position_id).first()
    if not position:
        return {}

    def build_node(pos: OrderPosition) -> dict:
        children = (
            db.query(OrderPosition)
            .filter(OrderPosition.parent_position_id == pos.id)
            .order_by(OrderPosition.split_index)
            .all()
        )
        status_val = pos.status.value if hasattr(pos.status, 'value') else str(pos.status)

        # Read new columns safely (may not be present on older ORM instances)
        try:
            row = db.execute(
                text("SELECT is_parent, split_type, split_stage, split_at, split_reason FROM order_positions WHERE id = :id"),
                {'id': str(pos.id)},
            ).fetchone()
            is_parent_val = row[0] if row else False
            split_type_val = row[1] if row else None
            split_stage_val = row[2] if row else None
            split_at_val = row[3].isoformat() if row and row[3] else None
            split_reason_val = row[4] if row else None
        except Exception:
            is_parent_val = False
            split_type_val = None
            split_stage_val = None
            split_at_val = None
            split_reason_val = None

        return {
            'id': str(pos.id),
            'quantity': pos.quantity,
            'quantity_sqm': float(pos.quantity_sqm) if pos.quantity_sqm else None,
            'status': status_val,
            'priority_order': pos.priority_order,
            'split_index': pos.split_index,
            'position_number': pos.position_number,
            'is_parent': is_parent_val,
            'split_type': split_type_val,
            'split_stage': split_stage_val,
            'split_at': split_at_val,
            'split_reason': split_reason_val,
            'children': [build_node(c) for c in children],
        }

    return build_node(position)
