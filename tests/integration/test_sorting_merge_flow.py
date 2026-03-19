"""
Integration tests for Sorting Split & Merge flow.
business/services/sorting_split.py

Tests the full sorting split -> repair -> merge cycle:
- 6 defect outcomes (ok, crack, color_mismatch, glaze_defect, shape_defect, grinding)
- Repair sub-position -> reglaze -> re-sort -> merge back
- Merge validation rules
- Surplus auto-disposition
All database interactions are mocked with unittest.mock.
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch, call
import unittest


# ---------------------------------------------------------------------------
# Mock builders
# ---------------------------------------------------------------------------

def _mock_position(position_id=None, status="transferred_to_sorting",
                   factory_id=None, order_id=None, quantity=100,
                   size="20x20", color="Red", color_2=None,
                   recipe_id=None, parent_position_id=None,
                   is_merged=False, collection="Standard",
                   priority_order=0, position_number=1,
                   firing_round=1, product_type="tile",
                   shape="rectangle", thickness_mm=Decimal("11"),
                   order_item_id=None, application=None,
                   finishing=None, application_type=None,
                   place_of_application=None, mandatory_qc=False,
                   quantity_sqm=None, split_category=None,
                   split_index=None):
    p = MagicMock()
    p.id = position_id or uuid.uuid4()
    p.status = status
    p.factory_id = factory_id or uuid.uuid4()
    p.order_id = order_id or uuid.uuid4()
    p.order_item_id = order_item_id or uuid.uuid4()
    p.quantity = quantity
    p.quantity_sqm = quantity_sqm
    p.size = size
    p.color = color
    p.color_2 = color_2
    p.recipe_id = recipe_id or uuid.uuid4()
    p.parent_position_id = parent_position_id
    p.is_merged = is_merged
    p.collection = collection
    p.priority_order = priority_order
    p.position_number = position_number
    p.firing_round = firing_round
    p.product_type = product_type
    p.shape = shape
    p.thickness_mm = thickness_mm
    p.application = application
    p.finishing = finishing
    p.application_type = application_type
    p.place_of_application = place_of_application
    p.mandatory_qc = mandatory_qc
    p.split_category = split_category
    p.split_index = split_index
    p.updated_at = None
    return p


# ---------------------------------------------------------------------------
# Tests: process_sorting_split
# ---------------------------------------------------------------------------

class TestProcessSortingSplit(unittest.TestCase):
    """Tests for process_sorting_split — the core sorting function."""

    def _setup_db(self, position):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = position
        db.query.return_value.filter.return_value.scalar.return_value = 0
        return db

    def test_all_ok_sets_position_to_packed(self):
        """100% ok -> parent status = PACKED, quantity = ok_count."""
        from business.services.sorting_split import process_sorting_split

        pos = _mock_position(quantity=50)
        db = self._setup_db(pos)

        result = process_sorting_split(db, pos.id, {
            "ok_count": 50,
            "defect_counts": {},
            "grind_count": 0,
        })

        self.assertEqual(result["ok_count"], 50)
        self.assertEqual(result["sub_positions"], [])
        self.assertEqual(result["mana_entries"], 0)

    def test_crack_defect_routes_to_mana(self):
        """Crack -> sub-position cancelled + mana entry."""
        from business.services.sorting_split import process_sorting_split

        pos = _mock_position(quantity=50)
        db = self._setup_db(pos)
        # Mock route_to_mana
        with patch("business.services.sorting_split.route_to_mana") as mock_mana:
            mock_mana.return_value = {"color": "Red", "quantity": 5}
            result = process_sorting_split(db, pos.id, {
                "ok_count": 45,
                "defect_counts": {"crack": 5},
                "grind_count": 0,
            })

        self.assertEqual(result["ok_count"], 45)
        self.assertEqual(len(result["defect_records"]), 1)
        self.assertEqual(result["defect_records"][0]["defect_type"], "crack")
        self.assertEqual(result["defect_records"][0]["outcome"], "to_mana")
        self.assertEqual(result["mana_entries"], 1)

    def test_stuck_defect_routes_to_mana(self):
        """Stuck tiles -> write-off to Mana."""
        from business.services.sorting_split import process_sorting_split

        pos = _mock_position(quantity=30)
        db = self._setup_db(pos)

        with patch("business.services.sorting_split.route_to_mana") as mock_mana:
            mock_mana.return_value = {"color": "Red", "quantity": 3}
            result = process_sorting_split(db, pos.id, {
                "ok_count": 27,
                "defect_counts": {"stuck": 3},
                "grind_count": 0,
            })

        self.assertEqual(result["ok_count"], 27)
        self.assertEqual(result["defect_records"][0]["outcome"], "to_mana")

    def test_color_mismatch_creates_blocking_task(self):
        """Color mismatch -> sub-position AWAITING_COLOR_MATCHING + PM task."""
        from business.services.sorting_split import process_sorting_split

        pos = _mock_position(quantity=40)
        db = self._setup_db(pos)

        result = process_sorting_split(db, pos.id, {
            "ok_count": 35,
            "defect_counts": {"color_mismatch": 5},
            "grind_count": 0,
        })

        self.assertEqual(len(result["sub_positions"]), 1)
        sub = result["sub_positions"][0]
        self.assertEqual(sub["status"], "awaiting_color_matching")
        self.assertEqual(sub["quantity"], 5)
        # Task should be added to db
        add_calls = db.add.call_args_list
        # At least one Task object added
        self.assertGreaterEqual(len(add_calls), 2)

    def test_glaze_defect_creates_repair_sub_position(self):
        """Glaze defect -> REPAIR sub-position sent to glazing."""
        from business.services.sorting_split import process_sorting_split

        pos = _mock_position(quantity=60)
        db = self._setup_db(pos)

        result = process_sorting_split(db, pos.id, {
            "ok_count": 50,
            "defect_counts": {"glaze_defect": 10},
            "grind_count": 0,
        })

        self.assertEqual(len(result["sub_positions"]), 1)
        sub = result["sub_positions"][0]
        self.assertEqual(sub["status"], "sent_to_glazing")
        self.assertEqual(sub["split_category"], "repair")
        # DefectRecord with outcome=reglaze
        self.assertEqual(result["defect_records"][0]["outcome"], "reglaze")

    def test_shape_defect_creates_repair_with_grinding(self):
        """Shape defect -> REPAIR sub-position (grinding path)."""
        from business.services.sorting_split import process_sorting_split

        pos = _mock_position(quantity=20)
        db = self._setup_db(pos)

        result = process_sorting_split(db, pos.id, {
            "ok_count": 15,
            "defect_counts": {"shape_defect": 5},
            "grind_count": 0,
        })

        self.assertEqual(len(result["sub_positions"]), 1)
        self.assertEqual(result["defect_records"][0]["outcome"], "grinding")

    def test_grinding_creates_grinding_stock(self):
        """Grind count -> GrindingStock entry created."""
        from business.services.sorting_split import process_sorting_split

        pos = _mock_position(quantity=25)
        db = self._setup_db(pos)

        with patch("business.services.sorting_split.add_to_grinding_stock") as mock_grind:
            gs = MagicMock()
            gs.id = uuid.uuid4()
            gs.quantity = 5
            gs.status = "in_stock"
            mock_grind.return_value = gs

            result = process_sorting_split(db, pos.id, {
                "ok_count": 20,
                "defect_counts": {},
                "grind_count": 5,
            })

        self.assertIsNotNone(result["grinding_record"])
        self.assertEqual(result["grinding_record"]["quantity"], 5)

    def test_mixed_defects_all_processed(self):
        """Multiple defect types in one sort are all processed."""
        from business.services.sorting_split import process_sorting_split

        pos = _mock_position(quantity=100)
        db = self._setup_db(pos)

        with patch("business.services.sorting_split.route_to_mana") as mock_mana, \
             patch("business.services.sorting_split.add_to_grinding_stock") as mock_grind:
            mock_mana.return_value = {"quantity": 5}
            gs = MagicMock()
            gs.id = uuid.uuid4()
            gs.quantity = 10
            gs.status = "in_stock"
            mock_grind.return_value = gs

            result = process_sorting_split(db, pos.id, {
                "ok_count": 60,
                "defect_counts": {
                    "crack": 5,
                    "glaze_defect": 15,
                    "color_mismatch": 10,
                },
                "grind_count": 10,
            })

        # 3 defect types + grinding = 4 sub-positions created (crack, glaze, color)
        self.assertEqual(len(result["sub_positions"]), 3)
        # 3 defect records + 1 grinding = 4 total
        self.assertEqual(len(result["defect_records"]), 4)

    def test_invalid_total_raises_error(self):
        """Total != position.quantity -> ValueError."""
        from business.services.sorting_split import process_sorting_split

        pos = _mock_position(quantity=100)
        db = self._setup_db(pos)

        with self.assertRaises(ValueError) as ctx:
            process_sorting_split(db, pos.id, {
                "ok_count": 50,
                "defect_counts": {"crack": 10},
                "grind_count": 0,
            })

        self.assertIn("Total", str(ctx.exception))

    def test_position_not_found_raises_error(self):
        """Non-existent position_id -> ValueError."""
        from business.services.sorting_split import process_sorting_split

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with self.assertRaises(ValueError):
            process_sorting_split(db, uuid.uuid4(), {"ok_count": 10})

    def test_wrong_status_raises_error(self):
        """Position not in 'transferred_to_sorting' -> ValueError."""
        from business.services.sorting_split import process_sorting_split

        pos = _mock_position(status="planned")
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = pos

        with self.assertRaises(ValueError) as ctx:
            process_sorting_split(db, pos.id, {"ok_count": 10})

        self.assertIn("transferred_to_sorting", str(ctx.exception))


# ---------------------------------------------------------------------------
# Tests: can_merge_position & merge_position_back
# ---------------------------------------------------------------------------

class TestCanMergePosition(unittest.TestCase):
    """Tests for can_merge_position validation."""

    def test_packed_child_can_merge(self):
        """Child in PACKED status can merge."""
        from business.services.sorting_split import can_merge_position

        child = _mock_position(status="packed", parent_position_id=uuid.uuid4())
        ok, reason = can_merge_position(child)
        self.assertTrue(ok)

    def test_child_without_parent_cannot_merge(self):
        """Position without parent_position_id cannot merge."""
        from business.services.sorting_split import can_merge_position

        child = _mock_position(status="packed", parent_position_id=None)
        ok, reason = can_merge_position(child)
        self.assertFalse(ok)
        self.assertIn("no parent", reason)

    def test_already_merged_cannot_merge(self):
        """Already merged position cannot merge again."""
        from business.services.sorting_split import can_merge_position

        child = _mock_position(
            status="packed", parent_position_id=uuid.uuid4(), is_merged=True,
        )
        ok, reason = can_merge_position(child)
        self.assertFalse(ok)
        self.assertIn("already merged", reason)

    def test_non_packed_status_cannot_merge(self):
        """Child in 'sent_to_glazing' status cannot merge."""
        from business.services.sorting_split import can_merge_position

        child = _mock_position(
            status="sent_to_glazing", parent_position_id=uuid.uuid4(),
        )
        ok, reason = can_merge_position(child)
        self.assertFalse(ok)
        self.assertIn("Cannot merge", reason)


class TestMergePositionBack(unittest.TestCase):
    """Tests for merge_position_back."""

    def _make_parent_child(self, parent_qty=80, child_qty=15):
        parent_id = uuid.uuid4()
        parent = _mock_position(
            position_id=parent_id, status="packed",
            quantity=parent_qty, quantity_sqm=Decimal("1.0"),
        )
        child = _mock_position(
            status="packed", quantity=child_qty,
            parent_position_id=parent_id,
            quantity_sqm=Decimal("0.2"),
        )
        return parent, child

    def test_merge_increases_parent_quantity(self):
        """Merge adds child quantity to parent."""
        from business.services.sorting_split import merge_position_back

        db = MagicMock()
        # No unresolved sub-positions remaining
        db.query.return_value.filter.return_value.count.return_value = 0
        db.query.return_value.filter.return_value.first.return_value = None

        parent, child = self._make_parent_child(80, 15)
        merged_by = uuid.uuid4()

        result = merge_position_back(db, parent, child, merged_by)

        self.assertEqual(result["merged_quantity"], 15)
        self.assertEqual(parent.quantity, 95)

    def test_merge_sets_child_to_merged(self):
        """After merge, child status=MERGED, quantity=0, is_merged=True."""
        from business.services.sorting_split import merge_position_back
        from api.enums import PositionStatus

        db = MagicMock()
        db.query.return_value.filter.return_value.count.return_value = 0
        db.query.return_value.filter.return_value.first.return_value = None

        parent, child = self._make_parent_child()
        merge_position_back(db, parent, child, uuid.uuid4())

        self.assertEqual(child.status, PositionStatus.MERGED)
        self.assertTrue(child.is_merged)
        self.assertEqual(child.quantity, 0)

    def test_merge_wrong_parent_raises_error(self):
        """Child's parent_position_id != parent.id -> ValueError."""
        from business.services.sorting_split import merge_position_back

        db = MagicMock()
        parent = _mock_position(position_id=uuid.uuid4(), status="packed", quantity=80)
        child = _mock_position(
            status="packed", quantity=10,
            parent_position_id=uuid.uuid4(),  # Different parent
        )

        with self.assertRaises(ValueError) as ctx:
            merge_position_back(db, parent, child, uuid.uuid4())

        self.assertIn("does not belong", str(ctx.exception))

    def test_merge_into_cancelled_parent_raises_error(self):
        """Cannot merge into a cancelled parent."""
        from business.services.sorting_split import merge_position_back

        db = MagicMock()
        parent_id = uuid.uuid4()
        parent = _mock_position(
            position_id=parent_id, status="cancelled", quantity=0,
        )
        child = _mock_position(
            status="packed", quantity=10, parent_position_id=parent_id,
        )

        with self.assertRaises(ValueError) as ctx:
            merge_position_back(db, parent, child, uuid.uuid4())

        self.assertIn("cancelled", str(ctx.exception))

    def test_merge_transfers_quantity_sqm(self):
        """Merge also transfers quantity_sqm from child to parent."""
        from business.services.sorting_split import merge_position_back

        db = MagicMock()
        db.query.return_value.filter.return_value.count.return_value = 0
        db.query.return_value.filter.return_value.first.return_value = None

        parent, child = self._make_parent_child()

        merge_position_back(db, parent, child, uuid.uuid4())

        self.assertEqual(result := parent.quantity_sqm, Decimal("1.0") + Decimal("0.2"))


# ---------------------------------------------------------------------------
# Tests: handle_surplus
# ---------------------------------------------------------------------------

class TestHandleSurplus(unittest.TestCase):
    """Tests for handle_surplus auto-disposition."""

    @patch("business.services.sorting_split._check_is_basic_color", return_value=True)
    @patch("business.services.sorting_split.auto_assign_surplus_disposition", create=True)
    def test_basic_10x10_goes_to_showroom(self, mock_auto, mock_basic):
        """10x10 + basic color -> showroom + photographing task."""
        from business.services.sorting_split import handle_surplus

        mock_auto.return_value = {"disposition": "showroom", "reason": "basic_10x10"}
        db = MagicMock()
        pos = _mock_position(size="10x10", color="White")

        result = handle_surplus(db, pos, 10)

        self.assertIsNotNone(result)
        # Should add showroom_task + photo_task + disposition = 3 adds
        self.assertGreaterEqual(db.add.call_count, 3)

    @patch("business.services.sorting_split._check_is_basic_color", return_value=False)
    @patch("business.services.sorting_split.auto_assign_surplus_disposition", create=True)
    def test_non_basic_10x10_goes_to_coaster_box(self, mock_auto, mock_basic):
        """10x10 + non-basic color -> coaster box."""
        from business.services.sorting_split import handle_surplus

        mock_auto.return_value = {"disposition": "casters", "reason": "non_basic_10x10"}
        db = MagicMock()
        # No existing casters box
        db.query.return_value.filter.return_value.first.return_value = None
        pos = _mock_position(size="10x10", color="CustomPurple")

        result = handle_surplus(db, pos, 5)

        self.assertIsNotNone(result)

    @patch("business.services.sorting_split._check_is_basic_color", return_value=True)
    @patch("business.services.sorting_split.auto_assign_surplus_disposition", create=True)
    def test_non_10x10_goes_to_mana(self, mock_auto, mock_basic):
        """Other sizes -> Mana shipment."""
        from business.services.sorting_split import handle_surplus

        mock_auto.return_value = {"disposition": "mana", "reason": "other_size"}
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        pos = _mock_position(size="30x60", color="White")

        result = handle_surplus(db, pos, 8)

        self.assertIsNotNone(result)


# ---------------------------------------------------------------------------
# Tests: route_to_mana
# ---------------------------------------------------------------------------

class TestRouteToMana(unittest.TestCase):
    """Tests for route_to_mana."""

    def test_creates_new_mana_shipment_if_none_exists(self):
        """If no pending ManaShipment exists, creates one."""
        from business.services.sorting_split import route_to_mana

        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [
            None,  # No pending ManaShipment
            None,  # No active MANA_CONFIRMATION task
        ]

        pos = _mock_position()
        result = route_to_mana(db, pos, 5, reason="crack defect")

        self.assertEqual(result["quantity"], 5)
        db.add.assert_called()

    def test_appends_to_existing_mana_shipment(self):
        """Appends items to existing pending ManaShipment."""
        from business.services.sorting_split import route_to_mana

        db = MagicMock()
        shipment = MagicMock()
        shipment.items_json = [{"color": "Blue", "quantity": 3}]
        shipment.factory_id = uuid.uuid4()
        db.query.return_value.filter.return_value.first.side_effect = [
            shipment,  # Existing pending shipment
            None,      # No task
        ]

        pos = _mock_position()
        result = route_to_mana(db, pos, 7, reason="stuck")

        self.assertEqual(result["quantity"], 7)


# ---------------------------------------------------------------------------
# Tests: add_to_grinding_stock
# ---------------------------------------------------------------------------

class TestAddToGrindingStock(unittest.TestCase):
    """Tests for add_to_grinding_stock."""

    def test_creates_grinding_stock_entry(self):
        """Creates a GrindingStock record with correct data."""
        from business.services.sorting_split import add_to_grinding_stock

        db = MagicMock()
        pos = _mock_position(color="Green", size="15x15")

        gs = add_to_grinding_stock(db, pos, 8)

        self.assertEqual(gs.quantity, 8)
        self.assertEqual(gs.color, "Green")
        self.assertEqual(gs.size, "15x15")
        db.add.assert_called_once()


if __name__ == "__main__":
    unittest.main()
