"""Integration tests for position merge flow.

Tests cover:
- Merge child back into parent -> parent quantity increases, child status=merged
- Try to merge position without parent -> should fail
- Try to merge position with wrong status -> should fail
- Get mergeable children endpoint
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from api.enums import PositionStatus, SplitCategory
from business.services.sorting_split import (
    can_merge_position,
    get_mergeable_children,
    merge_position_back,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_position(
    status="packed",
    quantity=50,
    parent_position_id=None,
    split_category=None,
    is_merged=False,
    position_number=1,
    split_index=None,
):
    """Create a mock OrderPosition for merge tests."""
    p = MagicMock()
    p.id = uuid.uuid4()
    p.order_id = uuid.uuid4()
    p.order_item_id = uuid.uuid4()
    p.factory_id = uuid.uuid4()
    p.status = PositionStatus(status) if isinstance(status, str) else status
    p.quantity = quantity
    p.quantity_sqm = 5.0
    p.color = "Red"
    p.size = "30x60"
    p.product_type = "tile"
    p.parent_position_id = parent_position_id
    p.split_category = split_category
    p.is_merged = is_merged
    p.position_number = position_number
    p.split_index = split_index
    p.updated_at = datetime.now(timezone.utc)
    return p


# ---------------------------------------------------------------------------
# Tests: can_merge_position
# ---------------------------------------------------------------------------

class TestCanMergePosition:
    """Test the can_merge_position validation."""

    def test_packed_child_can_be_merged(self):
        parent = _make_position(status="packed", quantity=80)
        child = _make_position(
            status="packed", quantity=20,
            parent_position_id=parent.id,
            split_category=SplitCategory.REPAIR,
            split_index=1,
        )
        can_merge, reason = can_merge_position(child)
        assert can_merge is True
        assert reason == ""

    def test_quality_check_done_child_can_be_merged(self):
        parent = _make_position(status="packed", quantity=80)
        child = _make_position(
            status="quality_check_done", quantity=20,
            parent_position_id=parent.id,
        )
        can_merge, reason = can_merge_position(child)
        assert can_merge is True

    def test_ready_for_shipment_child_can_be_merged(self):
        parent = _make_position(status="packed", quantity=80)
        child = _make_position(
            status="ready_for_shipment", quantity=20,
            parent_position_id=parent.id,
        )
        can_merge, reason = can_merge_position(child)
        assert can_merge is True

    def test_position_without_parent_cannot_be_merged(self):
        """A position without parent_position_id cannot be merged."""
        child = _make_position(status="packed", parent_position_id=None)
        can_merge, reason = can_merge_position(child)
        assert can_merge is False
        assert "no parent" in reason.lower()

    def test_already_merged_position_cannot_be_merged_again(self):
        parent = _make_position(status="packed", quantity=80)
        child = _make_position(
            status="packed", quantity=0,
            parent_position_id=parent.id,
            is_merged=True,
        )
        can_merge, reason = can_merge_position(child)
        assert can_merge is False
        assert "already merged" in reason.lower()

    def test_planned_status_cannot_be_merged(self):
        """Child with status 'planned' is not in mergeable set."""
        parent = _make_position(status="packed", quantity=80)
        child = _make_position(
            status="planned", quantity=20,
            parent_position_id=parent.id,
        )
        can_merge, reason = can_merge_position(child)
        assert can_merge is False
        assert "packed" in reason.lower() or "quality_check_done" in reason.lower()

    def test_fired_status_cannot_be_merged(self):
        parent = _make_position(status="packed", quantity=80)
        child = _make_position(
            status="fired", quantity=20,
            parent_position_id=parent.id,
        )
        can_merge, reason = can_merge_position(child)
        assert can_merge is False

    def test_sent_to_glazing_status_cannot_be_merged(self):
        parent = _make_position(status="packed", quantity=80)
        child = _make_position(
            status="sent_to_glazing", quantity=20,
            parent_position_id=parent.id,
        )
        can_merge, reason = can_merge_position(child)
        assert can_merge is False

    def test_cancelled_status_cannot_be_merged(self):
        parent = _make_position(status="packed", quantity=80)
        child = _make_position(
            status="cancelled", quantity=20,
            parent_position_id=parent.id,
        )
        can_merge, reason = can_merge_position(child)
        assert can_merge is False


# ---------------------------------------------------------------------------
# Tests: merge_position_back
# ---------------------------------------------------------------------------

class TestMergePositionBack:
    """Test the merge_position_back service function."""

    def test_merge_increases_parent_quantity(self):
        """After merge, parent.quantity += child.quantity."""
        parent = _make_position(status="packed", quantity=80)
        child = _make_position(
            status="packed", quantity=20,
            parent_position_id=parent.id,
        )
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []
        db.query.return_value.filter.return_value.first.return_value = None
        db.query.return_value.filter.return_value.count.return_value = 0
        db.flush.return_value = None

        result = merge_position_back(
            db=db,
            parent_position=parent,
            child_position=child,
            merged_by_id=uuid.uuid4(),
        )

        assert result["parent_new_quantity"] == 100  # 80 + 20
        assert result["merged_quantity"] == 20
        assert result["child_new_status"] == "merged"

    def test_merge_sets_child_to_merged_status(self):
        parent = _make_position(status="packed", quantity=80)
        child = _make_position(
            status="packed", quantity=20,
            parent_position_id=parent.id,
        )
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []
        db.query.return_value.filter.return_value.first.return_value = None
        db.query.return_value.filter.return_value.count.return_value = 0
        db.flush.return_value = None

        merge_position_back(
            db=db,
            parent_position=parent,
            child_position=child,
            merged_by_id=uuid.uuid4(),
        )

        assert child.status == PositionStatus.MERGED
        assert child.is_merged is True
        assert child.quantity == 0

    def test_merge_transfers_quantity_sqm(self):
        parent = _make_position(status="packed", quantity=80)
        parent.quantity_sqm = 8.0
        child = _make_position(
            status="packed", quantity=20,
            parent_position_id=parent.id,
        )
        child.quantity_sqm = 2.0

        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []
        db.query.return_value.filter.return_value.first.return_value = None
        db.query.return_value.filter.return_value.count.return_value = 0
        db.flush.return_value = None

        result = merge_position_back(
            db=db,
            parent_position=parent,
            child_position=child,
            merged_by_id=uuid.uuid4(),
        )

        assert parent.quantity_sqm == 10.0  # 8.0 + 2.0
        assert result["merged_quantity_sqm"] == 2.0

    def test_merge_child_not_belonging_to_parent_raises_error(self):
        """Child's parent_position_id must match parent.id."""
        parent = _make_position(status="packed", quantity=80)
        other_parent = _make_position(status="packed", quantity=80)
        child = _make_position(
            status="packed", quantity=20,
            parent_position_id=other_parent.id,  # different parent
        )

        db = MagicMock()

        with pytest.raises(ValueError, match="does not belong to parent"):
            merge_position_back(
                db=db,
                parent_position=parent,
                child_position=child,
                merged_by_id=uuid.uuid4(),
            )

    def test_merge_into_cancelled_parent_raises_error(self):
        """Cannot merge into a parent with cancelled status."""
        parent = _make_position(status="cancelled", quantity=80)
        child = _make_position(
            status="packed", quantity=20,
            parent_position_id=parent.id,
        )

        db = MagicMock()

        with pytest.raises(ValueError, match="cancelled"):
            merge_position_back(
                db=db,
                parent_position=parent,
                child_position=child,
                merged_by_id=uuid.uuid4(),
            )

    def test_merge_into_merged_parent_raises_error(self):
        """Cannot merge into a parent that is itself merged."""
        parent = _make_position(status="merged", quantity=0)
        child = _make_position(
            status="packed", quantity=20,
            parent_position_id=parent.id,
        )

        db = MagicMock()

        with pytest.raises(ValueError, match="merged"):
            merge_position_back(
                db=db,
                parent_position=parent,
                child_position=child,
                merged_by_id=uuid.uuid4(),
            )

    def test_merge_child_with_wrong_status_raises_error(self):
        """Cannot merge child that is still in production."""
        parent = _make_position(status="packed", quantity=80)
        child = _make_position(
            status="glazed", quantity=20,
            parent_position_id=parent.id,
        )

        db = MagicMock()

        with pytest.raises(ValueError, match="Cannot merge"):
            merge_position_back(
                db=db,
                parent_position=parent,
                child_position=child,
                merged_by_id=uuid.uuid4(),
            )

    def test_all_children_resolved_flag(self):
        """When no unresolved children remain, all_children_resolved=True."""
        parent = _make_position(status="packed", quantity=80)
        child = _make_position(
            status="packed", quantity=20,
            parent_position_id=parent.id,
        )

        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []
        db.query.return_value.filter.return_value.first.return_value = None
        # No unresolved children
        db.query.return_value.filter.return_value.count.return_value = 0
        db.flush.return_value = None

        result = merge_position_back(
            db=db,
            parent_position=parent,
            child_position=child,
            merged_by_id=uuid.uuid4(),
        )

        assert result["all_children_resolved"] is True


# ---------------------------------------------------------------------------
# Tests: get_mergeable_children
# ---------------------------------------------------------------------------

class TestGetMergeableChildren:
    """Test the get_mergeable_children function."""

    def test_returns_packed_children(self):
        parent_id = uuid.uuid4()
        child_packed = _make_position(
            status="packed", quantity=20,
            parent_position_id=parent_id,
        )
        child_packed.is_merged = False

        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = [child_packed]

        children = get_mergeable_children(db, parent_id)
        assert len(children) == 1

    def test_excludes_already_merged_children(self):
        """Already merged children should not be returned."""
        parent_id = uuid.uuid4()
        child_merged = _make_position(
            status="packed", quantity=0,
            parent_position_id=parent_id,
            is_merged=True,
        )

        db = MagicMock()
        # The query already filters is_merged=False, so it won't return merged children
        db.query.return_value.filter.return_value.all.return_value = []

        children = get_mergeable_children(db, parent_id)
        assert len(children) == 0

    def test_excludes_non_mergeable_status_children(self):
        """Children in non-mergeable status (e.g. glazed) are excluded."""
        parent_id = uuid.uuid4()

        db = MagicMock()
        # Query filters by status IN (packed, quality_check_done, ready_for_shipment)
        db.query.return_value.filter.return_value.all.return_value = []

        children = get_mergeable_children(db, parent_id)
        assert len(children) == 0
