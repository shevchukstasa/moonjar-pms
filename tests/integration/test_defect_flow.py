"""
Integration tests for Defect Coefficient service.
business/services/defect_coefficient.py

Tests:
- calculate_production_quantity_with_defects() for different glaze x product combos
- record_actual_defect_and_check_threshold() with below/above threshold
- Manual override of defect coefficient
- Running average updates (update_stone_defect_coefficient)
All database interactions are mocked with unittest.mock.
"""
import uuid
import math
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch, call
import unittest


# ---------------------------------------------------------------------------
# Mock builders
# ---------------------------------------------------------------------------

def _mock_position(position_id=None, factory_id=None, quantity=100,
                   product_type="tile", glaze_type="pigment",
                   defect_coeff_override=None,
                   quantity_with_defect_margin=None):
    p = MagicMock()
    p.id = position_id or uuid.uuid4()
    p.factory_id = factory_id or uuid.uuid4()
    p.quantity = quantity
    p.product_type = product_type
    p.glaze_type = glaze_type
    p.defect_coeff_override = defect_coeff_override
    p.quantity_with_defect_margin = quantity_with_defect_margin
    return p


def _mock_defect_record(defect_type="crack", quantity=5,
                        outcome="write_off", stage="incoming_inspection",
                        position_id=None, factory_id=None, supplier_id=None):
    r = MagicMock()
    r.id = uuid.uuid4()
    r.defect_type = defect_type
    r.quantity = quantity
    r.outcome = outcome
    r.stage = stage
    r.position_id = position_id or uuid.uuid4()
    r.factory_id = factory_id or uuid.uuid4()
    r.supplier_id = supplier_id
    r.date = date.today()
    return r


def _mock_sdc(stone_type="Red_20x20", factory_id=None, supplier_id=None,
              coefficient=0.05, sample_size=50):
    s = MagicMock()
    s.factory_id = factory_id or uuid.uuid4()
    s.stone_type = stone_type
    s.supplier_id = supplier_id
    s.coefficient = coefficient
    s.sample_size = sample_size
    s.last_updated = datetime.now(timezone.utc)
    s.calculation_period_days = 30
    return s


# ---------------------------------------------------------------------------
# Tests: GLAZE & PRODUCT DEFECT DEFAULTS
# ---------------------------------------------------------------------------

class TestGlazeDefectDefaults(unittest.TestCase):
    """Tests for GLAZE_DEFECT_DEFAULTS and PRODUCT_DEFECT_DEFAULTS constants."""

    def test_pigment_default(self):
        from business.services.defect_coefficient import GLAZE_DEFECT_DEFAULTS
        self.assertEqual(GLAZE_DEFECT_DEFAULTS["pigment"], 0.03)

    def test_oxide_default(self):
        from business.services.defect_coefficient import GLAZE_DEFECT_DEFAULTS
        self.assertEqual(GLAZE_DEFECT_DEFAULTS["oxide"], 0.05)

    def test_raku_default(self):
        from business.services.defect_coefficient import GLAZE_DEFECT_DEFAULTS
        self.assertEqual(GLAZE_DEFECT_DEFAULTS["raku"], 0.20)

    def test_tile_product_default(self):
        from business.services.defect_coefficient import PRODUCT_DEFECT_DEFAULTS
        self.assertEqual(PRODUCT_DEFECT_DEFAULTS["tile"], 0.03)

    def test_sink_product_default(self):
        from business.services.defect_coefficient import PRODUCT_DEFECT_DEFAULTS
        self.assertEqual(PRODUCT_DEFECT_DEFAULTS["sink"], 0.08)

    def test_3d_product_default(self):
        from business.services.defect_coefficient import PRODUCT_DEFECT_DEFAULTS
        self.assertEqual(PRODUCT_DEFECT_DEFAULTS["3d"], 0.10)


# ---------------------------------------------------------------------------
# Tests: get_glaze_defect_coeff & get_product_defect_coeff
# ---------------------------------------------------------------------------

class TestGetGlazeDefectCoeff(unittest.TestCase):
    """Tests for get_glaze_defect_coeff."""

    def test_returns_default_for_pigment(self):
        from business.services.defect_coefficient import get_glaze_defect_coeff
        db = MagicMock()
        result = get_glaze_defect_coeff(db, uuid.uuid4(), "pigment")
        self.assertEqual(result, 0.03)

    def test_returns_default_for_raku(self):
        from business.services.defect_coefficient import get_glaze_defect_coeff
        db = MagicMock()
        result = get_glaze_defect_coeff(db, uuid.uuid4(), "raku")
        self.assertEqual(result, 0.20)

    def test_unknown_glaze_type_returns_003(self):
        from business.services.defect_coefficient import get_glaze_defect_coeff
        db = MagicMock()
        result = get_glaze_defect_coeff(db, uuid.uuid4(), "unknown_glaze")
        self.assertEqual(result, 0.03)

    def test_normalizes_case_and_whitespace(self):
        from business.services.defect_coefficient import get_glaze_defect_coeff
        db = MagicMock()
        result = get_glaze_defect_coeff(db, uuid.uuid4(), "  Pigment  ")
        self.assertEqual(result, 0.03)

    def test_none_glaze_type_defaults_to_pigment(self):
        from business.services.defect_coefficient import get_glaze_defect_coeff
        db = MagicMock()
        result = get_glaze_defect_coeff(db, uuid.uuid4(), None)
        self.assertEqual(result, 0.03)


class TestGetProductDefectCoeff(unittest.TestCase):
    """Tests for get_product_defect_coeff."""

    def test_returns_default_for_tile(self):
        from business.services.defect_coefficient import get_product_defect_coeff
        db = MagicMock()
        result = get_product_defect_coeff(db, uuid.uuid4(), "tile")
        self.assertEqual(result, 0.03)

    def test_returns_default_for_countertop(self):
        from business.services.defect_coefficient import get_product_defect_coeff
        db = MagicMock()
        result = get_product_defect_coeff(db, uuid.uuid4(), "countertop")
        self.assertEqual(result, 0.05)

    def test_none_product_type_defaults_to_tile(self):
        from business.services.defect_coefficient import get_product_defect_coeff
        db = MagicMock()
        result = get_product_defect_coeff(db, uuid.uuid4(), None)
        self.assertEqual(result, 0.03)


# ---------------------------------------------------------------------------
# Tests: calculate_production_quantity_with_defects
# ---------------------------------------------------------------------------

class TestCalculateProductionQuantityWithDefects(unittest.TestCase):
    """Tests for calculate_production_quantity_with_defects."""

    def test_tile_pigment_standard_defect(self):
        """Tile + pigment: total_coeff = 0.03 + 0.03 = 0.06."""
        from business.services.defect_coefficient import calculate_production_quantity_with_defects

        db = MagicMock()
        pos = _mock_position(quantity=100, product_type="tile", glaze_type="pigment")

        result = calculate_production_quantity_with_defects(db, pos)

        expected = math.ceil(100 * (1 + 0.06))
        self.assertEqual(result, expected)
        self.assertEqual(pos.quantity_with_defect_margin, expected)

    def test_sink_oxide_higher_defect(self):
        """Sink + oxide: total_coeff = 0.05 + 0.08 = 0.13."""
        from business.services.defect_coefficient import calculate_production_quantity_with_defects

        db = MagicMock()
        pos = _mock_position(quantity=50, product_type="sink", glaze_type="oxide")

        result = calculate_production_quantity_with_defects(db, pos)

        expected = math.ceil(50 * (1 + 0.13))
        self.assertEqual(result, expected)

    def test_3d_raku_high_defect(self):
        """3D + raku: total_coeff = 0.20 + 0.10 = 0.30."""
        from business.services.defect_coefficient import calculate_production_quantity_with_defects

        db = MagicMock()
        pos = _mock_position(quantity=20, product_type="3d", glaze_type="raku")

        result = calculate_production_quantity_with_defects(db, pos)

        expected = math.ceil(20 * (1 + 0.30))
        self.assertEqual(result, expected)

    def test_manual_override_uses_custom_coefficient(self):
        """defect_coeff_override set -> uses it instead of calculated."""
        from business.services.defect_coefficient import calculate_production_quantity_with_defects

        db = MagicMock()
        pos = _mock_position(quantity=100, defect_coeff_override=0.15)

        result = calculate_production_quantity_with_defects(db, pos)

        expected = math.ceil(100 * 1.15)
        self.assertEqual(result, expected)

    def test_zero_override_means_no_extra(self):
        """Override = 0 means produce exactly the ordered quantity."""
        from business.services.defect_coefficient import calculate_production_quantity_with_defects

        db = MagicMock()
        pos = _mock_position(quantity=50, defect_coeff_override=0.0)

        result = calculate_production_quantity_with_defects(db, pos)

        self.assertEqual(result, 50)

    def test_updates_position_field_in_place(self):
        """The function sets position.quantity_with_defect_margin."""
        from business.services.defect_coefficient import calculate_production_quantity_with_defects

        db = MagicMock()
        pos = _mock_position(quantity=100)

        calculate_production_quantity_with_defects(db, pos)

        self.assertIsNotNone(pos.quantity_with_defect_margin)
        self.assertGreater(pos.quantity_with_defect_margin, 100)

    def test_product_type_enum_value_extraction(self):
        """Product type as enum (with .value) is handled correctly."""
        from business.services.defect_coefficient import calculate_production_quantity_with_defects

        db = MagicMock()
        # Simulate enum object with .value
        pt_enum = MagicMock()
        pt_enum.value = "countertop"
        pos = _mock_position(quantity=80, product_type=pt_enum, glaze_type="underglaze")

        result = calculate_production_quantity_with_defects(db, pos)

        # underglaze=0.04 + countertop=0.05 = 0.09
        expected = math.ceil(80 * (1 + 0.09))
        self.assertEqual(result, expected)


# ---------------------------------------------------------------------------
# Tests: record_actual_defect_and_check_threshold
# ---------------------------------------------------------------------------

class TestRecordActualDefectAndCheckThreshold(unittest.TestCase):
    """Tests for record_actual_defect_and_check_threshold."""

    def test_below_threshold_no_alert(self):
        """Actual defect below target -> exceeded=False, no 5-Why task."""
        from business.services.defect_coefficient import record_actual_defect_and_check_threshold

        db = MagicMock()
        # tile+pigment target = 0.06
        pos = _mock_position(quantity=100, product_type="tile", glaze_type="pigment")
        pos.quantity_with_defect_margin = 106

        result = record_actual_defect_and_check_threshold(db, pos, 0.02)

        self.assertFalse(result["exceeded"])
        self.assertIsNone(result["five_why_task_id"])

    @patch("business.services.defect_coefficient.create_five_why_task", create=True)
    def test_above_threshold_creates_five_why_task(self, mock_five_why):
        """Actual defect above target -> exceeded=True, 5-Why task created."""
        from business.services.defect_coefficient import record_actual_defect_and_check_threshold

        task = MagicMock()
        task.id = uuid.uuid4()
        mock_five_why.return_value = task

        db = MagicMock()
        # tile+pigment target = 0.06
        pos = _mock_position(quantity=100, product_type="tile", glaze_type="pigment")
        pos.quantity_with_defect_margin = 106

        result = record_actual_defect_and_check_threshold(db, pos, 0.10)  # 10% > 6%

        self.assertTrue(result["exceeded"])
        self.assertEqual(result["five_why_task_id"], str(task.id))
        mock_five_why.assert_called_once()

    def test_exact_threshold_not_exceeded(self):
        """Actual == target -> not exceeded (strict >)."""
        from business.services.defect_coefficient import record_actual_defect_and_check_threshold

        db = MagicMock()
        pos = _mock_position(quantity=100, product_type="tile", glaze_type="pigment")

        result = record_actual_defect_and_check_threshold(db, pos, 0.06)

        self.assertFalse(result["exceeded"])

    def test_records_to_production_defects_table(self):
        """Calls db.execute with INSERT INTO production_defects."""
        from business.services.defect_coefficient import record_actual_defect_and_check_threshold

        db = MagicMock()
        pos = _mock_position(quantity=100, product_type="tile", glaze_type="pigment")

        record_actual_defect_and_check_threshold(db, pos, 0.02)

        db.execute.assert_called_once()

    def test_target_pct_in_result(self):
        """Result contains target_pct and actual_pct as percentages."""
        from business.services.defect_coefficient import record_actual_defect_and_check_threshold

        db = MagicMock()
        pos = _mock_position(quantity=100, product_type="tile", glaze_type="pigment")

        result = record_actual_defect_and_check_threshold(db, pos, 0.04)

        # target = (0.03+0.03)*100 = 6.0
        self.assertEqual(result["target_pct"], 6.0)
        self.assertEqual(result["actual_pct"], 4.0)


# ---------------------------------------------------------------------------
# Tests: get_stone_defect_coefficient
# ---------------------------------------------------------------------------

class TestGetStoneDefectCoefficient(unittest.TestCase):
    """Tests for get_stone_defect_coefficient."""

    def test_returns_coefficient_when_found(self):
        from business.services.defect_coefficient import get_stone_defect_coefficient

        db = MagicMock()
        sdc = _mock_sdc(coefficient=0.07)
        db.query.return_value.filter.return_value.first.return_value = sdc

        result = get_stone_defect_coefficient(db, uuid.uuid4(), "Red_20x20")
        self.assertEqual(result, 0.07)

    def test_returns_zero_when_no_data(self):
        from business.services.defect_coefficient import get_stone_defect_coefficient

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        result = get_stone_defect_coefficient(db, uuid.uuid4(), "Unknown")
        self.assertEqual(result, 0.0)


# ---------------------------------------------------------------------------
# Tests: update_stone_defect_coefficient
# ---------------------------------------------------------------------------

class TestUpdateStoneDefectCoefficient(unittest.TestCase):
    """Tests for update_stone_defect_coefficient (daily runner)."""

    def test_no_records_returns_early(self):
        """No defect records in last 30 days -> logs info, no updates."""
        from business.services.defect_coefficient import update_stone_defect_coefficient

        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []

        update_stone_defect_coefficient(db, uuid.uuid4())

        db.flush.assert_not_called()

    def test_updates_existing_coefficient(self):
        """Existing StoneDefectCoefficient record is updated."""
        from business.services.defect_coefficient import update_stone_defect_coefficient

        db = MagicMock()
        factory_id = uuid.uuid4()

        # Create mock records
        rec = _mock_defect_record(
            defect_type="crack", quantity=10,
            outcome="write_off", factory_id=factory_id,
        )
        pos = MagicMock()
        pos.color = "Red"
        pos.size = "20x20"

        db.query.return_value.filter.return_value.all.return_value = [rec]
        db.query.return_value.get.return_value = pos

        existing_sdc = _mock_sdc(factory_id=factory_id)
        db.query.return_value.filter.return_value.first.return_value = existing_sdc

        update_stone_defect_coefficient(db, factory_id)

        db.flush.assert_called_once()

    def test_creates_new_coefficient_when_not_exists(self):
        """New StoneDefectCoefficient is created when none exists."""
        from business.services.defect_coefficient import update_stone_defect_coefficient

        db = MagicMock()
        factory_id = uuid.uuid4()

        rec = _mock_defect_record(
            defect_type="crack", quantity=5,
            outcome="write_off", factory_id=factory_id,
        )
        pos = MagicMock()
        pos.color = "Blue"
        pos.size = "30x30"

        db.query.return_value.filter.return_value.all.return_value = [rec]
        db.query.return_value.get.return_value = pos
        db.query.return_value.filter.return_value.first.return_value = None

        update_stone_defect_coefficient(db, factory_id)

        db.add.assert_called()
        db.flush.assert_called_once()


if __name__ == "__main__":
    unittest.main()
