"""
Integration tests for Batch Formation service.
business/services/batch_formation.py

Tests: auto-form batch, kiln capacity check, temperature compatibility,
co-firing groups, rotation rule compliance, dual-mode kiln constants.
All database interactions are mocked with unittest.mock.
"""
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch, PropertyMock
import unittest


# ---------------------------------------------------------------------------
# Mock builders
# ---------------------------------------------------------------------------

def _mock_kiln(kiln_id=None, name="Kiln A", factory_id=None,
               capacity_sqm=Decimal("2.0"), kiln_type="standard",
               is_active=True):
    k = MagicMock()
    k.id = kiln_id or uuid.uuid4()
    k.name = name
    k.factory_id = factory_id or uuid.uuid4()
    k.capacity_sqm = capacity_sqm
    k.kiln_working_area_cm = {"width": 100, "height": 200}
    k.kiln_type = kiln_type
    k.is_active = is_active
    k.resource_type = "kiln"
    k.status = "active"
    return k


def _mock_position(position_id=None, status="pre_kiln_check", factory_id=None,
                   quantity=50, size="20x20", recipe_id=None,
                   priority_order=0, planned_kiln_date=None,
                   batch_id=None, two_stage_firing=False, two_stage_type=None,
                   glazeable_sqm=None, quantity_sqm=None,
                   length_cm=None, width_cm=None, thickness_mm=Decimal("11"),
                   product_type="tile", shape="rectangle",
                   place_of_application=None):
    p = MagicMock()
    p.id = position_id or uuid.uuid4()
    p.status = status
    p.factory_id = factory_id or uuid.uuid4()
    p.order_id = uuid.uuid4()
    p.quantity = quantity
    p.size = size
    p.recipe_id = recipe_id or uuid.uuid4()
    p.priority_order = priority_order
    p.planned_kiln_date = planned_kiln_date
    p.batch_id = batch_id
    p.two_stage_firing = two_stage_firing
    p.two_stage_type = two_stage_type
    p.estimated_kiln_id = None
    p.glazeable_sqm = glazeable_sqm
    p.quantity_sqm = quantity_sqm or Decimal("0.20")
    p.length_cm = length_cm
    p.width_cm = width_cm
    p.thickness_mm = thickness_mm
    p.product_type = product_type
    p.shape = shape
    p.place_of_application = place_of_application
    p.color = "Red"
    p.created_at = datetime.now(timezone.utc)
    return p


def _mock_recipe_kiln_config(recipe_id=None, firing_temperature=1007):
    c = MagicMock()
    c.recipe_id = recipe_id or uuid.uuid4()
    c.firing_temperature = firing_temperature
    return c


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGetReadyPositions(unittest.TestCase):
    """Tests for _get_ready_positions."""

    def test_returns_positions_with_correct_statuses(self):
        """Only returns PRE_KILN_CHECK and GLAZED positions without batch_id."""
        from business.services.batch_formation import _get_ready_positions

        db = MagicMock()
        pos1 = _mock_position(status="pre_kiln_check")
        pos2 = _mock_position(status="glazed")
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [pos1, pos2]

        factory_id = uuid.uuid4()
        result = _get_ready_positions(db, factory_id)

        self.assertEqual(len(result), 2)

    def test_empty_when_no_ready_positions(self):
        """Returns empty list when no positions are ready."""
        from business.services.batch_formation import _get_ready_positions

        db = MagicMock()
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        result = _get_ready_positions(db, uuid.uuid4())
        self.assertEqual(result, [])

    def test_target_date_filters_positions(self):
        """With target_date, only positions with planned_kiln_date <= target are included."""
        from business.services.batch_formation import _get_ready_positions

        db = MagicMock()
        # The filter chain should include target_date comparison
        db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.all.return_value = []

        result = _get_ready_positions(db, uuid.uuid4(), target_date=date.today())
        self.assertEqual(result, [])


class TestGetAvailableKilns(unittest.TestCase):
    """Tests for _get_available_kilns."""

    def test_filters_out_kilns_under_maintenance(self):
        """Kilns with maintenance on batch_date are excluded."""
        from business.services.batch_formation import _get_available_kilns

        db = MagicMock()
        kiln_ok = _mock_kiln(name="Available Kiln")
        kiln_maint = _mock_kiln(name="Maintenance Kiln")

        db.query.return_value.filter.return_value.all.return_value = [kiln_ok, kiln_maint]
        # First kiln: no maintenance; Second kiln: has maintenance
        db.query.return_value.filter.return_value.first.side_effect = [None, MagicMock()]

        result = _get_available_kilns(db, uuid.uuid4(), date.today())
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, "Available Kiln")

    def test_returns_empty_when_all_kilns_in_maintenance(self):
        """All kilns under maintenance -> empty list."""
        from business.services.batch_formation import _get_available_kilns

        db = MagicMock()
        kiln = _mock_kiln()
        db.query.return_value.filter.return_value.all.return_value = [kiln]
        db.query.return_value.filter.return_value.first.return_value = MagicMock()

        result = _get_available_kilns(db, uuid.uuid4(), date.today())
        self.assertEqual(result, [])


class TestGetKilnCapacitySqm(unittest.TestCase):
    """Tests for _get_kiln_capacity_sqm."""

    def test_returns_capacity_sqm_when_set(self):
        """Direct capacity_sqm field is returned."""
        from business.services.batch_formation import _get_kiln_capacity_sqm

        kiln = _mock_kiln(capacity_sqm=Decimal("3.5"))
        result = _get_kiln_capacity_sqm(kiln)
        self.assertEqual(result, Decimal("3.5"))

    def test_derives_from_dimensions_when_no_capacity(self):
        """Falls back to working area dimensions."""
        from business.services.batch_formation import _get_kiln_capacity_sqm

        kiln = _mock_kiln(capacity_sqm=None)
        kiln.kiln_working_area_cm = {"width": 100, "height": 200}

        result = _get_kiln_capacity_sqm(kiln)
        expected = Decimal("100") * Decimal("200") / Decimal("10000")
        self.assertEqual(result, expected)

    def test_fallback_to_default_when_no_data(self):
        """No capacity_sqm and no dimensions -> returns 1.0."""
        from business.services.batch_formation import _get_kiln_capacity_sqm

        kiln = _mock_kiln(capacity_sqm=None)
        kiln.kiln_working_area_cm = None

        result = _get_kiln_capacity_sqm(kiln)
        self.assertEqual(result, Decimal("1.0"))


class TestCofiringCompatibility(unittest.TestCase):
    """Tests for co-firing sub-grouping."""

    def test_standard_positions_grouped_together(self):
        """Non-two-stage positions share the 'standard' key."""
        from business.services.batch_formation import _get_cofiring_key

        pos = _mock_position(two_stage_firing=False)
        self.assertEqual(_get_cofiring_key(pos), "standard")

    def test_two_stage_gold_gets_own_key(self):
        """Two-stage gold positions get 'two_stage:gold' key."""
        from business.services.batch_formation import _get_cofiring_key

        pos = _mock_position(two_stage_firing=True, two_stage_type="gold")
        self.assertEqual(_get_cofiring_key(pos), "two_stage:gold")

    def test_split_separates_standard_from_two_stage(self):
        """_split_by_cofiring_compatibility separates standard from two-stage."""
        from business.services.batch_formation import _split_by_cofiring_compatibility

        p_std = _mock_position(two_stage_firing=False)
        p_gold = _mock_position(two_stage_firing=True, two_stage_type="gold")
        p_counter = _mock_position(two_stage_firing=True, two_stage_type="countertop")

        groups = _split_by_cofiring_compatibility([p_std, p_gold, p_counter])

        self.assertIn("standard", groups)
        self.assertIn("two_stage:gold", groups)
        self.assertIn("two_stage:countertop", groups)
        self.assertEqual(len(groups["standard"]), 1)
        self.assertEqual(len(groups["two_stage:gold"]), 1)


class TestFindBestKilnForBatch(unittest.TestCase):
    """Tests for _find_best_kiln_for_batch."""

    @patch("business.services.batch_formation.check_rotation_compliance", create=True)
    def test_prefers_estimated_kiln_if_available(self, mock_rotation):
        """If position has estimated_kiln_id matching an available kiln, use it."""
        from business.services.batch_formation import _find_best_kiln_for_batch

        mock_rotation.return_value = {"compliant": True}

        kiln_preferred = _mock_kiln(name="Preferred")
        kiln_other = _mock_kiln(name="Other")
        pos = _mock_position()
        pos.estimated_kiln_id = kiln_preferred.id

        db = MagicMock()
        db.query.return_value.filter.return_value.scalar.return_value = 0

        result = _find_best_kiln_for_batch(
            db, [kiln_preferred, kiln_other], date.today(),
            Decimal("0.5"), pos,
        )
        self.assertEqual(result.id, kiln_preferred.id)

    @patch("business.services.batch_formation.check_rotation_compliance", create=True)
    def test_gold_firing_prefers_raku_kiln(self, mock_rotation):
        """Gold firing (700C) should prefer Raku kiln."""
        from business.services.batch_formation import _find_best_kiln_for_batch

        mock_rotation.return_value = {"compliant": True}

        raku = _mock_kiln(name="Raku Kiln", kiln_type="raku")
        standard = _mock_kiln(name="Standard Kiln", kiln_type="standard")

        db = MagicMock()
        db.query.return_value.filter.return_value.scalar.return_value = 0

        result = _find_best_kiln_for_batch(
            db, [standard, raku], date.today(),
            Decimal("0.5"),
            cofiring_key="two_stage:gold",
            firing_temperature=700,
        )
        self.assertEqual(result.name, "Raku Kiln")

    @patch("business.services.batch_formation.check_rotation_compliance", create=True)
    def test_standard_firing_avoids_raku_when_possible(self, mock_rotation):
        """Standard firing avoids Raku if non-Raku kilns are available."""
        from business.services.batch_formation import _find_best_kiln_for_batch

        mock_rotation.return_value = {"compliant": True}

        raku = _mock_kiln(name="Raku Kiln", kiln_type="raku")
        standard = _mock_kiln(name="Standard Kiln", kiln_type="standard")

        db = MagicMock()
        db.query.return_value.filter.return_value.scalar.return_value = 0

        result = _find_best_kiln_for_batch(
            db, [raku, standard], date.today(),
            Decimal("0.5"),
            cofiring_key="standard",
            firing_temperature=1007,
        )
        self.assertEqual(result.name, "Standard Kiln")

    @patch("business.services.batch_formation.check_rotation_compliance", create=True)
    def test_kiln_too_small_is_skipped(self, mock_rotation):
        """Kiln with capacity less than required is not selected."""
        from business.services.batch_formation import _find_best_kiln_for_batch

        mock_rotation.return_value = {"compliant": True}

        small = _mock_kiln(name="Small Kiln", capacity_sqm=Decimal("0.1"))
        big = _mock_kiln(name="Big Kiln", capacity_sqm=Decimal("5.0"))

        db = MagicMock()
        db.query.return_value.filter.return_value.scalar.return_value = 0

        result = _find_best_kiln_for_batch(
            db, [small, big], date.today(), Decimal("1.0"),
        )
        self.assertEqual(result.name, "Big Kiln")

    def test_returns_none_when_no_kilns_fit(self):
        """Returns None when no kiln has enough capacity."""
        from business.services.batch_formation import _find_best_kiln_for_batch

        small = _mock_kiln(capacity_sqm=Decimal("0.1"))

        db = MagicMock()
        result = _find_best_kiln_for_batch(
            db, [small], date.today(), Decimal("10.0"),
        )
        self.assertIsNone(result)


class TestSuggestOrCreateBatches(unittest.TestCase):
    """Tests for suggest_or_create_batches — the main entry point."""

    @patch("business.services.batch_formation._build_batches_for_group")
    @patch("business.services.batch_formation._get_available_kilns")
    @patch("business.services.batch_formation._get_ready_positions")
    @patch("business.services.batch_formation.group_positions_by_temperature", create=True)
    def test_no_ready_positions_returns_empty(
        self, mock_temp_group, mock_ready, mock_kilns, mock_build
    ):
        """No ready positions -> empty result, no batches created."""
        from business.services.batch_formation import suggest_or_create_batches

        db = MagicMock()
        mock_ready.return_value = []

        result = suggest_or_create_batches(db, uuid.uuid4())
        self.assertEqual(result, [])
        mock_build.assert_not_called()

    @patch("business.services.batch_formation._build_batches_for_group")
    @patch("business.services.batch_formation._get_available_kilns")
    @patch("business.services.batch_formation._get_ready_positions")
    @patch("business.services.batch_formation.group_positions_by_temperature", create=True)
    def test_no_available_kilns_returns_empty(
        self, mock_temp_group, mock_ready, mock_kilns, mock_build
    ):
        """No available kilns -> empty result."""
        from business.services.batch_formation import suggest_or_create_batches

        db = MagicMock()
        mock_ready.return_value = [_mock_position()]
        mock_temp_group.return_value = {"group1": [_mock_position()]}
        mock_kilns.return_value = []

        result = suggest_or_create_batches(db, uuid.uuid4())
        self.assertEqual(result, [])

    @patch("business.services.batch_formation._build_batches_for_group")
    @patch("business.services.batch_formation._get_available_kilns")
    @patch("business.services.batch_formation._get_ready_positions")
    @patch("business.services.batch_formation.group_positions_by_temperature", create=True)
    def test_auto_mode_creates_planned_batches(
        self, mock_temp_group, mock_ready, mock_kilns, mock_build
    ):
        """Mode='auto' creates PLANNED batches."""
        from business.services.batch_formation import suggest_or_create_batches
        from api.enums import BatchStatus

        db = MagicMock()
        positions = [_mock_position()]
        mock_ready.return_value = positions
        mock_temp_group.return_value = {"group1": positions}
        mock_kilns.return_value = [_mock_kiln()]
        mock_build.return_value = [{"batch_id": "123", "positions_count": 1}]

        result = suggest_or_create_batches(db, uuid.uuid4(), mode="auto")

        self.assertEqual(len(result), 1)
        # Verify batch_status passed to _build_batches_for_group
        call_kwargs = mock_build.call_args[1]
        self.assertEqual(call_kwargs["batch_status"], BatchStatus.PLANNED)


class TestGetPositionAreaSqm(unittest.TestCase):
    """Tests for _get_position_area_sqm."""

    def test_uses_glazeable_sqm_when_available(self):
        """Position with glazeable_sqm uses it * quantity."""
        from business.services.batch_formation import _get_position_area_sqm

        pos = _mock_position(quantity=10, glazeable_sqm=Decimal("0.04"))
        result = _get_position_area_sqm(pos)
        self.assertEqual(result, Decimal("0.04") * Decimal("10"))

    def test_falls_back_to_quantity_sqm(self):
        """No glazeable_sqm -> uses quantity_sqm."""
        from business.services.batch_formation import _get_position_area_sqm

        pos = _mock_position(quantity=10, glazeable_sqm=None, quantity_sqm=Decimal("0.5"))
        result = _get_position_area_sqm(pos)
        self.assertEqual(result, Decimal("0.5"))

    def test_absolute_fallback(self):
        """No area data -> uses 0.04 * quantity fallback."""
        from business.services.batch_formation import _get_position_area_sqm

        pos = _mock_position(quantity=5, glazeable_sqm=None, quantity_sqm=None,
                             length_cm=None, width_cm=None)
        result = _get_position_area_sqm(pos)
        expected = Decimal("0.04") * Decimal("5")
        self.assertEqual(result, expected)


class TestFillerTileSelection(unittest.TestCase):
    """Tests for _select_filler_tiles."""

    def test_no_filler_when_remaining_area_zero(self):
        """When remaining area is 0 (or near 0), no fillers selected."""
        from business.services.batch_formation import _select_filler_tiles

        db = MagicMock()
        kiln = _mock_kiln()
        result = _select_filler_tiles(
            db, kiln, [], Decimal("0.001"), None, {}, {},
        )
        self.assertEqual(result, [])


class TestIsRakuKiln(unittest.TestCase):
    """Tests for _is_raku_kiln helper."""

    def test_raku_kiln_type_detected(self):
        from business.services.batch_formation import _is_raku_kiln
        kiln = _mock_kiln(kiln_type="raku")
        self.assertTrue(_is_raku_kiln(kiln))

    def test_standard_kiln_not_raku(self):
        from business.services.batch_formation import _is_raku_kiln
        kiln = _mock_kiln(kiln_type="standard")
        self.assertFalse(_is_raku_kiln(kiln))

    def test_mixed_case_raku(self):
        from business.services.batch_formation import _is_raku_kiln
        kiln = _mock_kiln(kiln_type="Raku Special")
        self.assertTrue(_is_raku_kiln(kiln))


if __name__ == "__main__":
    unittest.main()
