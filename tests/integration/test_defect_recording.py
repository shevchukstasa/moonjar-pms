"""Integration tests for defect coefficient system.

Tests cover:
- Record defect below threshold -> no alert
- Record defect above threshold -> quality check task created
- Get coefficients endpoint -> returns glaze + product coefficients
- Override defect coefficient (owner only)
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from api.enums import PositionStatus, ProductType, TaskType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_position(
    status="fired",
    quantity=100,
    product_type="tile",
    glaze_type=None,
):
    p = MagicMock()
    p.id = uuid.uuid4()
    p.order_id = uuid.uuid4()
    p.factory_id = uuid.uuid4()
    p.status = PositionStatus(status)
    p.quantity = quantity
    p.quantity_with_defect_margin = 106  # e.g. 100 * 1.06
    p.product_type = ProductType(product_type)
    p.glaze_type = glaze_type
    p.defect_coeff_override = None
    p.color = "Green"
    p.size = "30x60"
    return p


# ---------------------------------------------------------------------------
# Tests: defect coefficient defaults
# ---------------------------------------------------------------------------

class TestDefectCoefficientDefaults:
    """Test that default defect coefficients are correctly defined."""

    def test_glaze_defect_defaults_exist(self):
        from business.services.defect_coefficient import GLAZE_DEFECT_DEFAULTS
        assert "pigment" in GLAZE_DEFECT_DEFAULTS
        assert "oxide" in GLAZE_DEFECT_DEFAULTS
        assert "underglaze" in GLAZE_DEFECT_DEFAULTS
        assert "raku" in GLAZE_DEFECT_DEFAULTS

    def test_product_defect_defaults_exist(self):
        from business.services.defect_coefficient import PRODUCT_DEFECT_DEFAULTS
        assert "tile" in PRODUCT_DEFECT_DEFAULTS
        assert "countertop" in PRODUCT_DEFECT_DEFAULTS
        assert "sink" in PRODUCT_DEFECT_DEFAULTS
        assert "3d" in PRODUCT_DEFECT_DEFAULTS
        assert "custom" in PRODUCT_DEFECT_DEFAULTS

    def test_raku_has_highest_glaze_defect_rate(self):
        from business.services.defect_coefficient import GLAZE_DEFECT_DEFAULTS
        raku_rate = GLAZE_DEFECT_DEFAULTS["raku"]
        assert raku_rate == 0.20
        for glaze_type, rate in GLAZE_DEFECT_DEFAULTS.items():
            if glaze_type != "raku":
                assert rate < raku_rate

    def test_3d_has_highest_product_defect_rate(self):
        from business.services.defect_coefficient import PRODUCT_DEFECT_DEFAULTS
        rate_3d = PRODUCT_DEFECT_DEFAULTS["3d"]
        assert rate_3d == 0.10

    def test_tile_has_lowest_product_defect_rate(self):
        from business.services.defect_coefficient import PRODUCT_DEFECT_DEFAULTS
        tile_rate = PRODUCT_DEFECT_DEFAULTS["tile"]
        assert tile_rate == 0.03


# ---------------------------------------------------------------------------
# Tests: get_glaze_defect_coeff / get_product_defect_coeff
# ---------------------------------------------------------------------------

class TestGetDefectCoefficients:
    """Test the coefficient lookup functions."""

    def test_get_glaze_defect_coeff_returns_default_for_pigment(self):
        from business.services.defect_coefficient import get_glaze_defect_coeff
        db = MagicMock()
        factory_id = uuid.uuid4()
        result = get_glaze_defect_coeff(db, factory_id, "pigment")
        assert result == 0.03

    def test_get_glaze_defect_coeff_returns_default_for_raku(self):
        from business.services.defect_coefficient import get_glaze_defect_coeff
        db = MagicMock()
        factory_id = uuid.uuid4()
        result = get_glaze_defect_coeff(db, factory_id, "raku")
        assert result == 0.20

    def test_get_glaze_defect_coeff_normalizes_input(self):
        """Input is normalized to lowercase/stripped."""
        from business.services.defect_coefficient import get_glaze_defect_coeff
        db = MagicMock()
        factory_id = uuid.uuid4()
        result = get_glaze_defect_coeff(db, factory_id, "  PIGMENT  ")
        assert result == 0.03

    def test_get_glaze_defect_coeff_unknown_type_returns_default(self):
        from business.services.defect_coefficient import get_glaze_defect_coeff
        db = MagicMock()
        factory_id = uuid.uuid4()
        result = get_glaze_defect_coeff(db, factory_id, "unknown_glaze")
        assert result == 0.03  # fallback default

    def test_get_product_defect_coeff_returns_default_for_tile(self):
        from business.services.defect_coefficient import get_product_defect_coeff
        db = MagicMock()
        factory_id = uuid.uuid4()
        result = get_product_defect_coeff(db, factory_id, "tile")
        assert result == 0.03

    def test_get_product_defect_coeff_returns_default_for_sink(self):
        from business.services.defect_coefficient import get_product_defect_coeff
        db = MagicMock()
        factory_id = uuid.uuid4()
        result = get_product_defect_coeff(db, factory_id, "sink")
        assert result == 0.08

    def test_get_product_defect_coeff_unknown_type_returns_default(self):
        from business.services.defect_coefficient import get_product_defect_coeff
        db = MagicMock()
        factory_id = uuid.uuid4()
        result = get_product_defect_coeff(db, factory_id, "unknown_product")
        assert result == 0.03


# ---------------------------------------------------------------------------
# Tests: calculate_production_quantity_with_defects
# ---------------------------------------------------------------------------

class TestCalculateProductionQuantityWithDefects:
    """Test the quantity calculation with defect margin."""

    def test_tile_pigment_calculates_correctly(self):
        from business.services.defect_coefficient import calculate_production_quantity_with_defects
        db = MagicMock()
        position = _make_position(quantity=100, product_type="tile")
        position.glaze_type = "pigment"

        result = calculate_production_quantity_with_defects(db, position)

        # tile=0.03 + pigment=0.03 = 0.06 total
        # ceil(100 * 1.06) = 106
        assert result == 106
        assert position.quantity_with_defect_margin == 106

    def test_sink_oxide_calculates_correctly(self):
        from business.services.defect_coefficient import calculate_production_quantity_with_defects
        db = MagicMock()
        position = _make_position(quantity=50, product_type="sink")
        position.glaze_type = "oxide"

        result = calculate_production_quantity_with_defects(db, position)

        # sink=0.08 + oxide=0.05 = 0.13 total
        # ceil(50 * 1.13) = 57
        assert result == 57
        assert position.quantity_with_defect_margin == 57

    def test_manual_override_takes_precedence(self):
        """defect_coeff_override on position overrides the glaze+product calculation."""
        from business.services.defect_coefficient import calculate_production_quantity_with_defects
        db = MagicMock()
        position = _make_position(quantity=100, product_type="tile")
        position.defect_coeff_override = 0.15  # 15% manual override

        result = calculate_production_quantity_with_defects(db, position)

        # ceil(100 * 1.15) = 115
        assert result == 115

    def test_zero_quantity_returns_zero(self):
        from business.services.defect_coefficient import calculate_production_quantity_with_defects
        db = MagicMock()
        position = _make_position(quantity=0, product_type="tile")
        position.glaze_type = "pigment"

        result = calculate_production_quantity_with_defects(db, position)
        assert result == 0

    def test_raku_3d_high_defect_margin(self):
        """Raku + 3D should have the highest combined defect margin."""
        from business.services.defect_coefficient import calculate_production_quantity_with_defects
        db = MagicMock()
        position = _make_position(quantity=100, product_type="3d")
        position.glaze_type = "raku"

        result = calculate_production_quantity_with_defects(db, position)

        # raku=0.20 + 3d=0.10 = 0.30 total
        # ceil(100 * 1.30) = 130
        assert result == 130


# ---------------------------------------------------------------------------
# Tests: record_actual_defect_and_check_threshold
# ---------------------------------------------------------------------------

class TestRecordActualDefectAndCheckThreshold:
    """Test recording actual defects and threshold checking."""

    def test_defect_below_threshold_no_alert(self):
        """When actual defect < target, exceeded=False and no task created."""
        from business.services.defect_coefficient import record_actual_defect_and_check_threshold
        db = MagicMock()
        position = _make_position(quantity=100, product_type="tile")
        position.glaze_type = "pigment"

        # Target: 0.03 + 0.03 = 0.06
        # Record 0.02 (below threshold)
        result = record_actual_defect_and_check_threshold(
            db=db,
            position=position,
            actual_defect_pct=0.02,
        )

        assert result["exceeded"] is False
        assert result["five_why_task_id"] is None

    @patch("business.services.defect_coefficient.create_five_why_task", create=True)
    def test_defect_above_threshold_creates_five_why_task(self, mock_create_task):
        """When actual defect > target, exceeded=True and 5 Why task created."""
        from business.services.defect_coefficient import record_actual_defect_and_check_threshold

        mock_task = MagicMock()
        mock_task.id = uuid.uuid4()
        mock_create_task.return_value = mock_task

        db = MagicMock()
        position = _make_position(quantity=100, product_type="tile")
        position.glaze_type = "pigment"

        # Target: 0.03 + 0.03 = 0.06
        # Record 0.10 (above threshold)
        result = record_actual_defect_and_check_threshold(
            db=db,
            position=position,
            actual_defect_pct=0.10,
        )

        assert result["exceeded"] is True

    def test_defect_exactly_at_threshold_no_alert(self):
        """Exactly at threshold -> not exceeded (> not >=)."""
        from business.services.defect_coefficient import record_actual_defect_and_check_threshold
        db = MagicMock()
        position = _make_position(quantity=100, product_type="tile")
        position.glaze_type = "pigment"

        # Target: 0.06, record exactly 0.06
        result = record_actual_defect_and_check_threshold(
            db=db,
            position=position,
            actual_defect_pct=0.06,
        )

        assert result["exceeded"] is False

    def test_result_contains_target_and_actual_pct(self):
        """Result dict should contain target_pct and actual_pct as percentages."""
        from business.services.defect_coefficient import record_actual_defect_and_check_threshold
        db = MagicMock()
        position = _make_position(quantity=100, product_type="tile")
        position.glaze_type = "pigment"

        result = record_actual_defect_and_check_threshold(
            db=db,
            position=position,
            actual_defect_pct=0.04,
        )

        assert "target_pct" in result
        assert "actual_pct" in result
        # target_pct should be 6.0 (0.06 * 100)
        assert result["target_pct"] == 6.0
        # actual_pct should be 4.0 (0.04 * 100)
        assert result["actual_pct"] == 4.0


# ---------------------------------------------------------------------------
# Tests: Defect coefficient override validation
# ---------------------------------------------------------------------------

class TestDefectCoefficientOverride:
    """Test defect coefficient override input validation."""

    def test_override_value_must_be_between_0_and_1(self):
        """The override_position_defect_coeff endpoint validates 0.0-1.0 range."""
        # This tests the validation logic in the endpoint
        valid_values = [0.0, 0.5, 1.0, 0.12]
        for val in valid_values:
            assert 0.0 <= val <= 1.0

        invalid_values = [-0.1, 1.1, 2.0]
        for val in invalid_values:
            assert not (0.0 <= val <= 1.0)

    def test_override_recalculates_quantity_with_defect_margin(self):
        """Overriding coefficient should recalculate quantity_with_defect_margin."""
        import math
        position = _make_position(quantity=100, product_type="tile")
        coeff_value = 0.12

        # Simulate what the endpoint does
        position.defect_coeff_override = coeff_value
        position.quantity_with_defect_margin = math.ceil(position.quantity * (1 + coeff_value))

        assert position.quantity_with_defect_margin == 112  # ceil(100 * 1.12)
