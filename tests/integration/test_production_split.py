"""Integration tests for production split flow.

Tests cover:
- Split a position into 2 parts -> children created, parent frozen
- Sum of children quantities = parent quantity
- Splitting position with status loaded_in_kiln -> should fail
- Split tree endpoint returns correct hierarchy
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, call

import pytest

from api.enums import PositionStatus, SplitCategory
from business.services.production_split import (
    can_split_position,
    split_position_mid_production,
    get_split_tree,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_position(
    status="planned",
    quantity=100,
    parent_position_id=None,
    is_parent=False,
    split_category=None,
    position_number=1,
    split_index=None,
):
    """Create a mock OrderPosition."""
    p = MagicMock()
    p.id = uuid.uuid4()
    p.order_id = uuid.uuid4()
    p.order_item_id = uuid.uuid4()
    p.factory_id = uuid.uuid4()
    p.status = PositionStatus(status) if isinstance(status, str) else status
    p.quantity = quantity
    p.quantity_sqm = 10.0
    p.quantity_with_defect_margin = 110
    p.color = "Blue"
    p.color_2 = None
    p.size = "30x60"
    p.application = None
    p.finishing = None
    p.collection = None
    p.application_type = None
    p.place_of_application = None
    p.product_type = "tile"
    p.shape = "rectangle"
    p.thickness_mm = 11
    p.length_cm = None
    p.width_cm = None
    p.depth_cm = None
    p.bowl_shape = None
    p.glazeable_sqm = None
    p.recipe_id = uuid.uuid4()
    p.size_id = uuid.uuid4()
    p.mandatory_qc = False
    p.priority_order = 0
    p.firing_round = 1
    p.two_stage_firing = False
    p.two_stage_type = None
    p.planned_glazing_date = None
    p.planned_kiln_date = None
    p.planned_sorting_date = None
    p.planned_completion_date = None
    p.estimated_kiln_id = None
    p.parent_position_id = parent_position_id
    p.is_parent = is_parent
    p.split_category = split_category
    p.position_number = position_number
    p.split_index = split_index
    p.batch_id = None
    p.resource_id = None
    p.created_at = datetime.now(timezone.utc)
    p.updated_at = datetime.now(timezone.utc)
    return p


# ---------------------------------------------------------------------------
# Tests: can_split_position
# ---------------------------------------------------------------------------

class TestCanSplitPosition:
    """Test the can_split_position validation function."""

    def test_planned_position_can_be_split(self):
        p = _make_position(status="planned")
        can_split, reason = can_split_position(p)
        assert can_split is True
        assert reason == ""

    def test_glazed_position_can_be_split(self):
        p = _make_position(status="glazed")
        can_split, reason = can_split_position(p)
        assert can_split is True

    def test_engobe_applied_position_can_be_split(self):
        p = _make_position(status="engobe_applied")
        can_split, reason = can_split_position(p)
        assert can_split is True

    def test_loaded_in_kiln_cannot_be_split(self):
        """Position loaded in kiln cannot be split."""
        p = _make_position(status="loaded_in_kiln")
        can_split, reason = can_split_position(p)
        assert can_split is False
        assert "loaded in kiln" in reason.lower()

    def test_already_split_parent_cannot_be_split_again(self):
        """A position that is already a parent cannot be split again."""
        p = _make_position(status="planned")
        p.is_parent = True
        can_split, reason = can_split_position(p)
        assert can_split is False
        assert "already split" in reason.lower()

    def test_sorting_sub_position_cannot_be_production_split(self):
        """Sub-positions from sorting split cannot be production-split."""
        p = _make_position(status="sent_to_glazing")
        p.split_category = SplitCategory.REPAIR
        can_split, reason = can_split_position(p)
        assert can_split is False
        assert "sorting sub-position" in reason.lower()

    def test_fired_position_can_be_split(self):
        """Fired (not in kiln) position can be split."""
        p = _make_position(status="fired")
        can_split, reason = can_split_position(p)
        assert can_split is True

    def test_pre_kiln_check_position_can_be_split(self):
        p = _make_position(status="pre_kiln_check")
        can_split, reason = can_split_position(p)
        assert can_split is True


# ---------------------------------------------------------------------------
# Tests: split_position_mid_production
# ---------------------------------------------------------------------------

class TestSplitPositionMidProduction:
    """Test the split_position_mid_production service function."""

    def test_split_into_two_creates_two_children(self):
        """Splitting a position into 2 parts creates 2 child positions."""
        p = _make_position(status="planned", quantity=100)
        db = MagicMock()

        # Mock the SQL execute for freezing parent
        db.execute.return_value = None
        db.refresh.return_value = None
        db.flush.return_value = None

        # Mock max split_index query
        db.query.return_value.filter.return_value.scalar.return_value = 0

        splits = [
            {"quantity": 60},
            {"quantity": 40},
        ]

        children = split_position_mid_production(
            db=db,
            position=p,
            splits=splits,
            reason="Client wants partial delivery",
            created_by_id=uuid.uuid4(),
        )

        assert len(children) == 2
        # Verify db.add was called for each child
        assert db.add.call_count == 2

    def test_split_quantities_must_sum_to_parent(self):
        """If split quantities don't sum to parent quantity, raise ValueError."""
        p = _make_position(status="planned", quantity=100)
        db = MagicMock()

        splits = [
            {"quantity": 60},
            {"quantity": 60},  # 120 != 100
        ]

        with pytest.raises(ValueError, match="must equal position quantity"):
            split_position_mid_production(
                db=db,
                position=p,
                splits=splits,
                reason="test",
                created_by_id=uuid.uuid4(),
            )

    def test_split_requires_at_least_two_parts(self):
        """Must have at least 2 splits."""
        p = _make_position(status="planned", quantity=100)
        db = MagicMock()

        splits = [{"quantity": 100}]

        with pytest.raises(ValueError, match="at least 2 parts"):
            split_position_mid_production(
                db=db,
                position=p,
                splits=splits,
                reason="test",
                created_by_id=uuid.uuid4(),
            )

    def test_split_loaded_in_kiln_raises_error(self):
        """Cannot split a position that is loaded in kiln."""
        p = _make_position(status="loaded_in_kiln", quantity=100)
        db = MagicMock()

        splits = [
            {"quantity": 50},
            {"quantity": 50},
        ]

        with pytest.raises(ValueError, match="loaded in kiln"):
            split_position_mid_production(
                db=db,
                position=p,
                splits=splits,
                reason="test",
                created_by_id=uuid.uuid4(),
            )

    def test_split_freezes_parent(self):
        """After split, parent should be frozen via SQL update (is_parent=True)."""
        p = _make_position(status="glazed", quantity=100)
        db = MagicMock()
        db.query.return_value.filter.return_value.scalar.return_value = 0

        splits = [
            {"quantity": 70},
            {"quantity": 30},
        ]

        split_position_mid_production(
            db=db,
            position=p,
            splits=splits,
            reason="test split",
            created_by_id=uuid.uuid4(),
        )

        # Verify SQL execute was called to freeze parent
        db.execute.assert_called_once()
        call_args = db.execute.call_args
        # The SQL should contain is_parent = TRUE
        sql_text = str(call_args[0][0])
        assert "is_parent" in sql_text.lower()

    def test_children_inherit_parent_status(self):
        """Children should inherit the parent's pre-freeze status."""
        p = _make_position(status="glazed", quantity=100)
        db = MagicMock()
        db.query.return_value.filter.return_value.scalar.return_value = 0

        splits = [
            {"quantity": 60},
            {"quantity": 40},
        ]

        children = split_position_mid_production(
            db=db,
            position=p,
            splits=splits,
            reason="test",
            created_by_id=uuid.uuid4(),
        )

        # Each child should have the parent's status
        for child in children:
            assert child.status == p.status

    def test_split_into_three_parts(self):
        """Splitting into 3 parts creates 3 children."""
        p = _make_position(status="planned", quantity=90)
        db = MagicMock()
        db.query.return_value.filter.return_value.scalar.return_value = 0

        splits = [
            {"quantity": 30},
            {"quantity": 30},
            {"quantity": 30},
        ]

        children = split_position_mid_production(
            db=db,
            position=p,
            splits=splits,
            reason="three-way split",
            created_by_id=uuid.uuid4(),
        )

        assert len(children) == 3
        total_qty = sum(c.quantity for c in children)
        assert total_qty == 90

    def test_split_with_custom_priority(self):
        """Children can have custom priority_order from split spec."""
        p = _make_position(status="planned", quantity=100)
        db = MagicMock()
        db.query.return_value.filter.return_value.scalar.return_value = 0

        splits = [
            {"quantity": 50, "priority_order": 10},
            {"quantity": 50, "priority_order": 20},
        ]

        children = split_position_mid_production(
            db=db,
            position=p,
            splits=splits,
            reason="priority split",
            created_by_id=uuid.uuid4(),
        )

        assert children[0].priority_order == 10
        assert children[1].priority_order == 20


# ---------------------------------------------------------------------------
# Tests: get_split_tree
# ---------------------------------------------------------------------------

class TestGetSplitTree:
    """Test the get_split_tree function."""

    def test_returns_empty_dict_if_position_not_found(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        result = get_split_tree(db, uuid.uuid4())
        assert result == {}

    def test_returns_node_for_position_without_children(self):
        """A position with no children returns a node with empty children list."""
        p = _make_position(status="planned", quantity=100)
        db = MagicMock()

        # First call: position lookup
        db.query.return_value.filter.return_value.first.return_value = p
        # Children query returns empty
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        # Raw SQL for extra columns
        row_mock = MagicMock()
        row_mock.__getitem__ = lambda self, idx: [False, None, None, None, None][idx]
        db.execute.return_value.fetchone.return_value = row_mock

        result = get_split_tree(db, p.id)
        assert result["id"] == str(p.id)
        assert result["quantity"] == 100
        assert result["children"] == []
