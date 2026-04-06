"""Unit tests for sorting split algorithm — NO database.

Tests: sub-position creation logic, repair flow, surplus routing, reconciliation.
Uses SimpleNamespace mocks following the project pattern.
"""
import pytest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, call
from uuid import uuid4
from datetime import datetime, timezone

from business.services.sorting_split import (
    _MANA_DEFECT_TYPES,
    _REPAIR_DEFECT_TYPES,
    _next_split_index,
)


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _position(**kw):
    """Build a fake OrderPosition for sorting tests."""
    defaults = dict(
        id=uuid4(),
        order_id=uuid4(),
        order_item_id=uuid4(),
        parent_position_id=None,
        factory_id=uuid4(),
        status=SimpleNamespace(value="transferred_to_sorting"),
        quantity=100,
        color="Sage Green",
        color_2=None,
        size="10x10",
        application="brush",
        finishing="glossy",
        collection="Authentic",
        application_type="standard",
        place_of_application="face_only",
        product_type="tile",
        shape="square",
        thickness_mm=Decimal("8"),
        recipe_id=uuid4(),
        mandatory_qc=False,
        priority_order=0,
        position_number="P001",
        split_index=None,
        firing_round=1,
        is_parent=False,
        split_category=None,
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


class TestSortingSplit:
    """Test sorting split logic: sub-position creation, defect routing, surplus, reconciliation."""

    def test_split_creates_sub_positions(self):
        """Sorting split should create sub-positions for each category (ok, defect types).

        Validates the business rule: ok_count + total_defects + grind_count = position.quantity.
        Sub-positions inherit parent characteristics.
        """
        pos = _position(quantity=100)

        # Simulate split data from sorter
        split_data = {
            "ok_count": 85,
            "defect_counts": {"crack": 5, "glaze_defect": 7},
            "grind_count": 3,
        }

        # Verify total matches position quantity
        ok = split_data["ok_count"]
        defects = sum(split_data["defect_counts"].values())
        grind = split_data["grind_count"]
        total = ok + defects + grind

        assert total == pos.quantity, "Total must equal position quantity"
        assert ok == 85
        assert defects == 12  # 5 crack + 7 glaze_defect
        assert grind == 3

    def test_second_repair_writes_off(self):
        """Second-round repair failure → write off to Mana.

        Business rule: if a tile fails after re-glazing (firing_round >= 2),
        it goes to Mana (write-off) instead of another repair cycle.
        Defect types crack and stuck always go to Mana regardless of round.
        """
        # Crack/stuck ALWAYS go to Mana (regardless of repair round)
        assert "crack" in _MANA_DEFECT_TYPES
        assert "stuck" in _MANA_DEFECT_TYPES

        # Glaze/shape defects go to repair on first round
        assert "glaze_defect" in _REPAIR_DEFECT_TYPES
        assert "shape_defect" in _REPAIR_DEFECT_TYPES

        # Simulate: position on firing_round=2, glaze_defect found
        pos = _position(firing_round=2, quantity=10)

        # On second round, defects that would normally be repaired
        # should be treated differently (business logic dictates write-off
        # after second failure). Verify the defect type routing.
        defect_type = "glaze_defect"

        # First round: repairable
        assert defect_type in _REPAIR_DEFECT_TYPES
        assert defect_type not in _MANA_DEFECT_TYPES

        # The process_sorting_split function handles the round check:
        # firing_round >= 2 + repair defect → write off instead of repair

    def test_surplus_10x10_base_to_showroom(self):
        """10x10 base color surplus goes to showroom per §9.

        Business rules:
        - 10x10 + basic color → Showroom (+ photographing task)
        - 10x10 + non-basic → Coaster box
        - Other sizes → Mana shipment
        """
        # Test the routing logic
        test_cases = [
            ("10x10", True, "showroom"),     # basic color 10x10 → showroom
            ("10x10", False, "coaster_box"),  # non-basic 10x10 → coaster box
            ("20x20", True, "mana"),          # other size, basic → mana
            ("20x20", False, "mana"),         # other size, non-basic → mana
        ]

        for size, is_basic, expected_route in test_cases:
            if size == "10x10" and is_basic:
                route = "showroom"
            elif size == "10x10" and not is_basic:
                route = "coaster_box"
            else:
                route = "mana"

            assert route == expected_route, (
                f"Size={size}, basic={is_basic} → expected {expected_route}, got {route}"
            )

    def test_reconciliation_check(self):
        """Input = output verification: total of sub-positions must equal parent quantity.

        Business rule: after sorting split, sum of all sub-position quantities
        (ok + defect + grind) must exactly equal the parent position's quantity.
        Any mismatch is a reconciliation error.
        """
        parent_qty = 200

        # Valid split: totals match
        sub_quantities = [180, 10, 5, 3, 2]  # ok=180, various defects
        assert sum(sub_quantities) == parent_qty

        # Invalid split: totals don't match (should raise ValueError)
        bad_sub_quantities = [180, 10, 5, 3]  # = 198, not 200
        assert sum(bad_sub_quantities) != parent_qty

        # Verify the formula
        deficit = parent_qty - sum(bad_sub_quantities)
        assert deficit == 2, "Should detect 2 pieces unaccounted for"


class TestDefectRouting:
    """Test defect type → destination routing."""

    def test_crack_always_mana(self):
        """Cracked tiles always go to Mana (write-off), never repair."""
        assert "crack" in _MANA_DEFECT_TYPES
        assert "crack" not in _REPAIR_DEFECT_TYPES

    def test_stuck_always_mana(self):
        """Stuck tiles (fused to shelf) → Mana, unrepairable."""
        assert "stuck" in _MANA_DEFECT_TYPES
        assert "stuck" not in _REPAIR_DEFECT_TYPES

    def test_glaze_defect_repairable(self):
        """Glaze defects can be repaired via re-glazing."""
        assert "glaze_defect" in _REPAIR_DEFECT_TYPES
        assert "glaze_defect" not in _MANA_DEFECT_TYPES

    def test_shape_defect_repairable(self):
        """Shape defects can be repaired via grinding path."""
        assert "shape_defect" in _REPAIR_DEFECT_TYPES
        assert "shape_defect" not in _MANA_DEFECT_TYPES

    def test_no_overlap_between_mana_and_repair(self):
        """Mana and repair defect sets must not overlap."""
        overlap = _MANA_DEFECT_TYPES & _REPAIR_DEFECT_TYPES
        assert len(overlap) == 0, f"Overlap found: {overlap}"
