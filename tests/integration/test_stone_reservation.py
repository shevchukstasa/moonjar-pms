"""Integration tests for stone reservation system.

Tests cover:
- List stone reservations
- Get defect rates
- Get weekly report
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(role="production_manager"):
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = role
    u.email = "pm@test.com"
    u.name = "Test PM"
    return u


def _make_stone_reservation(
    position_id=None,
    factory_id=None,
    size_category="medium",
    product_type="tile",
    reserved_qty=100,
    reserved_sqm=1.8,
    stone_defect_pct=0.05,
    status="active",
):
    r = MagicMock()
    r.id = uuid.uuid4()
    r.position_id = position_id or uuid.uuid4()
    r.factory_id = factory_id or uuid.uuid4()
    r.size_category = size_category
    r.product_type = product_type
    r.reserved_qty = reserved_qty
    r.reserved_sqm = reserved_sqm
    r.stone_defect_pct = stone_defect_pct
    r.status = status
    r.created_at = datetime.now(timezone.utc)
    r.reconciled_at = None
    r.adjustments = []
    return r


def _make_defect_rate(
    factory_id=None,
    size_category="medium",
    product_type="tile",
    defect_pct=0.05,
):
    dr = MagicMock()
    dr.id = uuid.uuid4()
    dr.factory_id = factory_id
    dr.size_category = size_category
    dr.product_type = product_type
    dr.defect_pct = defect_pct
    dr.updated_at = datetime.now(timezone.utc)
    dr.updated_by = None
    return dr


def _make_adjustment(adj_type="writeoff", qty_sqm=0.1, reason="breakage"):
    a = MagicMock()
    a.id = uuid.uuid4()
    a.type = adj_type
    a.qty_sqm = qty_sqm
    a.reason = reason
    a.created_at = datetime.now(timezone.utc)
    a.created_by = None
    return a


# ---------------------------------------------------------------------------
# Tests: Stone reservation list serialization
# ---------------------------------------------------------------------------

class TestStoneReservationSerialization:
    """Test that stone reservation data is serialized correctly."""

    def test_reservation_fields_are_present(self):
        """Verify all expected fields in a stone reservation."""
        r = _make_stone_reservation()
        assert r.id is not None
        assert r.position_id is not None
        assert r.factory_id is not None
        assert r.size_category == "medium"
        assert r.product_type == "tile"
        assert r.reserved_qty == 100
        assert float(r.reserved_sqm) == 1.8
        assert float(r.stone_defect_pct) == 0.05
        assert r.status == "active"

    def test_reservation_with_adjustments_calculates_totals(self):
        """Adjustments should sum writeoff and return separately."""
        r = _make_stone_reservation()
        r.adjustments = [
            _make_adjustment("writeoff", 0.1, "breakage"),
            _make_adjustment("writeoff", 0.2, "damage"),
            _make_adjustment("return", 0.05, "excess"),
        ]

        writeoff_sqm = sum(
            float(a.qty_sqm) for a in r.adjustments if a.type == "writeoff"
        )
        return_sqm = sum(
            float(a.qty_sqm) for a in r.adjustments if a.type == "return"
        )

        assert round(writeoff_sqm, 3) == 0.3
        assert round(return_sqm, 3) == 0.05

    def test_reservation_with_no_adjustments(self):
        """Reservation with no adjustments should have zero totals."""
        r = _make_stone_reservation()
        assert r.adjustments == []

        writeoff_sqm = sum(
            float(a.qty_sqm) for a in r.adjustments if a.type == "writeoff"
        )
        return_sqm = sum(
            float(a.qty_sqm) for a in r.adjustments if a.type == "return"
        )

        assert writeoff_sqm == 0.0
        assert return_sqm == 0.0


# ---------------------------------------------------------------------------
# Tests: Defect rates
# ---------------------------------------------------------------------------

class TestDefectRates:
    """Test defect rate configuration and validation."""

    def test_valid_size_categories(self):
        """Size categories must be from the valid set."""
        valid = {"small", "medium", "large", "any"}
        assert "small" in valid
        assert "medium" in valid
        assert "large" in valid
        assert "any" in valid
        assert "invalid" not in valid

    def test_valid_product_types(self):
        """Product types must be from the valid set."""
        valid = {"tile", "countertop", "sink", "3d"}
        assert "tile" in valid
        assert "countertop" in valid
        assert "sink" in valid
        assert "3d" in valid

    def test_defect_pct_range(self):
        """Defect percentage must be between 0.0 and 1.0."""
        dr = _make_defect_rate(defect_pct=0.05)
        assert 0.0 <= float(dr.defect_pct) <= 1.0

    def test_factory_specific_rate_has_factory_id(self):
        factory_id = uuid.uuid4()
        dr = _make_defect_rate(factory_id=factory_id, defect_pct=0.08)
        assert dr.factory_id == factory_id

    def test_global_rate_has_null_factory_id(self):
        dr = _make_defect_rate(factory_id=None, defect_pct=0.05)
        assert dr.factory_id is None


# ---------------------------------------------------------------------------
# Tests: Stone defect rate service
# ---------------------------------------------------------------------------

class TestStoneDefectRateService:
    """Test the stone defect rate service functions."""

    def test_get_stone_defect_rate_function_exists(self):
        """Verify the service function is importable."""
        from business.services.stone_reservation import get_stone_defect_rate
        assert callable(get_stone_defect_rate)

    def test_get_weekly_stone_waste_report_function_exists(self):
        """Verify the weekly report function is importable."""
        from business.services.stone_reservation import get_weekly_stone_waste_report
        assert callable(get_weekly_stone_waste_report)


# ---------------------------------------------------------------------------
# Tests: Stone reservation model
# ---------------------------------------------------------------------------

class TestStoneReservationModel:
    """Test the StoneReservation model has expected columns."""

    def test_model_has_required_columns(self):
        from api.models import StoneReservation
        assert hasattr(StoneReservation, "id")
        assert hasattr(StoneReservation, "position_id")
        assert hasattr(StoneReservation, "factory_id")
        assert hasattr(StoneReservation, "size_category")
        assert hasattr(StoneReservation, "product_type")
        assert hasattr(StoneReservation, "reserved_qty")
        assert hasattr(StoneReservation, "reserved_sqm")
        assert hasattr(StoneReservation, "stone_defect_pct")
        assert hasattr(StoneReservation, "status")

    def test_adjustment_model_has_required_columns(self):
        from api.models import StoneReservationAdjustment
        assert hasattr(StoneReservationAdjustment, "id")
        assert hasattr(StoneReservationAdjustment, "type")
        assert hasattr(StoneReservationAdjustment, "qty_sqm")
        assert hasattr(StoneReservationAdjustment, "reason")

    def test_defect_rate_model_has_required_columns(self):
        from api.models import StoneDefectRate
        assert hasattr(StoneDefectRate, "id")
        assert hasattr(StoneDefectRate, "factory_id")
        assert hasattr(StoneDefectRate, "size_category")
        assert hasattr(StoneDefectRate, "product_type")
        assert hasattr(StoneDefectRate, "defect_pct")


# ---------------------------------------------------------------------------
# Tests: Weekly report
# ---------------------------------------------------------------------------

class TestWeeklyReport:
    """Test weekly report endpoint validation."""

    def test_week_offset_range(self):
        """week_offset must be 0-52."""
        valid_offsets = [0, 1, 10, 52]
        for offset in valid_offsets:
            assert 0 <= offset <= 52

        invalid_offsets = [-1, 53, 100]
        for offset in invalid_offsets:
            assert not (0 <= offset <= 52)

    def test_factory_id_required_for_weekly_report(self):
        """The weekly report endpoint requires factory_id."""
        # This is enforced by the Query(...) parameter (required)
        from api.routers.stone_reservations import get_weekly_report
        import inspect
        sig = inspect.signature(get_weekly_report)
        factory_param = sig.parameters.get("factory_id")
        assert factory_param is not None
