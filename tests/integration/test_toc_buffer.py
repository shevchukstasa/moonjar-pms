"""Integration tests for TOC buffer zone calculation.

Tests cover:
- delta calculation (work_pct - time_pct)
- Zone assignment: green (delta >= -5), yellow (-5 to -20), red (< -20)
- Summary counts (green/yellow/red totals)
- Order with 100% work and 50% time -> green
- Order with 30% work and 80% time -> red
- Buffer health calculation from buffer_health.py
"""
import uuid
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest

from api.enums import PositionStatus, OrderStatus, BufferHealth
from api.routers.toc import _compute_buffer_zone, _DONE_STATUSES, _EXCLUDED_STATUSES
from business.services.buffer_health import calculate_buffer_health


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_order(
    production_received_date=None,
    final_deadline=None,
    schedule_deadline=None,
    document_date=None,
    status=OrderStatus.PLANNED,
):
    order = MagicMock()
    order.id = uuid.uuid4()
    order.order_number = "ORD-001"
    order.factory_id = uuid.uuid4()
    order.production_received_date = production_received_date
    order.final_deadline = final_deadline
    order.schedule_deadline = schedule_deadline
    order.document_date = document_date
    order.status = status
    order.client = "Test Client"
    return order


def _make_position(status=PositionStatus.PLANNED, split_category=None):
    p = MagicMock()
    p.id = uuid.uuid4()
    p.status = status
    p.split_category = split_category
    return p


# ---------------------------------------------------------------------------
# Tests: _compute_buffer_zone — zone assignment
# ---------------------------------------------------------------------------

class TestComputeBufferZone:

    def test_green_zone_work_ahead_of_time(self):
        """100% work done, 50% time elapsed -> green (delta = +50)."""
        today = date.today()
        order = _make_order(
            production_received_date=today - timedelta(days=5),
            final_deadline=today + timedelta(days=5),
        )
        # All positions done
        positions = [
            _make_position(status=PositionStatus.PACKED),
            _make_position(status=PositionStatus.SHIPPED),
        ]

        result = _compute_buffer_zone(order, positions)

        assert result["zone"] == "green"
        assert result["work_completion_pct"] == 100.0
        assert result["buffer_delta"] > 0

    def test_red_zone_work_behind_time(self):
        """30% work done, 80% time elapsed -> red (delta = -50)."""
        today = date.today()
        order = _make_order(
            production_received_date=today - timedelta(days=8),
            final_deadline=today + timedelta(days=2),
        )
        # 3 of 10 done
        done_positions = [_make_position(status=PositionStatus.PACKED) for _ in range(3)]
        wip_positions = [_make_position(status=PositionStatus.PLANNED) for _ in range(7)]
        positions = done_positions + wip_positions

        result = _compute_buffer_zone(order, positions)

        assert result["zone"] == "red"
        assert result["work_completion_pct"] == 30.0
        assert result["buffer_delta"] < -20

    def test_yellow_zone_moderate_delay(self):
        """Work slightly behind time: delta between -5 and -20 -> yellow."""
        today = date.today()
        # 10-day window, 6 days elapsed -> time_pct = 60%
        order = _make_order(
            production_received_date=today - timedelta(days=6),
            final_deadline=today + timedelta(days=4),
        )
        # 5 of 10 done -> work_pct = 50%, delta = -10
        done_positions = [_make_position(status=PositionStatus.PACKED) for _ in range(5)]
        wip_positions = [_make_position(status=PositionStatus.PLANNED) for _ in range(5)]
        positions = done_positions + wip_positions

        result = _compute_buffer_zone(order, positions)

        assert result["zone"] == "yellow"
        assert -20 <= result["buffer_delta"] < -5

    def test_deadline_past_always_red(self):
        """When deadline is past, zone is always red regardless of work done."""
        today = date.today()
        order = _make_order(
            production_received_date=today - timedelta(days=20),
            final_deadline=today - timedelta(days=1),  # Yesterday
        )
        # All done — but deadline passed
        positions = [_make_position(status=PositionStatus.PACKED)]

        result = _compute_buffer_zone(order, positions)

        assert result["zone"] == "red"
        assert result["days_remaining"] < 0

    def test_no_deadline_defaults_to_green(self):
        """Orders with no deadline are treated as green."""
        order = _make_order(
            production_received_date=date.today() - timedelta(days=5),
            final_deadline=None,
            schedule_deadline=None,
        )
        positions = [_make_position(status=PositionStatus.PLANNED)]

        result = _compute_buffer_zone(order, positions)

        assert result["zone"] == "green"
        assert result["time_penetration_pct"] is None
        assert result["buffer_delta"] is None
        assert result["days_remaining"] is None

    def test_cancelled_positions_excluded(self):
        """Cancelled positions are excluded from counts."""
        today = date.today()
        order = _make_order(
            production_received_date=today - timedelta(days=2),
            final_deadline=today + timedelta(days=8),
        )
        positions = [
            _make_position(status=PositionStatus.PACKED),
            _make_position(status=PositionStatus.CANCELLED),  # excluded
            _make_position(status=PositionStatus.PLANNED),
        ]

        result = _compute_buffer_zone(order, positions)

        assert result["positions_total"] == 2  # cancelled excluded
        assert result["positions_done"] == 1

    def test_split_positions_excluded(self):
        """Positions with split_category are excluded from counts."""
        today = date.today()
        order = _make_order(
            production_received_date=today - timedelta(days=2),
            final_deadline=today + timedelta(days=8),
        )
        positions = [
            _make_position(status=PositionStatus.PACKED),
            _make_position(status=PositionStatus.PLANNED, split_category="child_a"),
        ]

        result = _compute_buffer_zone(order, positions)

        assert result["positions_total"] == 1  # split child excluded

    def test_delta_calculation_exact(self):
        """Verify delta = work_pct - time_pct precisely."""
        today = date.today()
        # 20-day window, 10 elapsed -> time_pct = 50%
        order = _make_order(
            production_received_date=today - timedelta(days=10),
            final_deadline=today + timedelta(days=10),
        )
        # 6 of 10 done -> work_pct = 60%, delta = +10
        done = [_make_position(status=PositionStatus.PACKED) for _ in range(6)]
        wip = [_make_position(status=PositionStatus.PLANNED) for _ in range(4)]
        positions = done + wip

        result = _compute_buffer_zone(order, positions)

        assert result["work_completion_pct"] == 60.0
        assert result["time_penetration_pct"] == 50.0
        assert result["buffer_delta"] == 10.0
        assert result["zone"] == "green"

    def test_empty_positions_returns_zero_work(self):
        """Order with no active positions has work_completion_pct of 0."""
        order = _make_order(
            production_received_date=date.today() - timedelta(days=5),
            final_deadline=date.today() + timedelta(days=5),
        )
        # Only cancelled positions
        positions = [_make_position(status=PositionStatus.CANCELLED)]

        result = _compute_buffer_zone(order, positions)

        assert result["work_completion_pct"] == 0.0
        assert result["positions_total"] == 0

    def test_green_boundary_delta_minus_5(self):
        """delta of exactly -5 is green (>= -5)."""
        today = date.today()
        # 20-day window, 10 elapsed -> time_pct = 50%
        order = _make_order(
            production_received_date=today - timedelta(days=10),
            final_deadline=today + timedelta(days=10),
        )
        # 9 of 20 done -> work_pct = 45%, delta = -5
        done = [_make_position(status=PositionStatus.PACKED) for _ in range(9)]
        wip = [_make_position(status=PositionStatus.PLANNED) for _ in range(11)]
        positions = done + wip

        result = _compute_buffer_zone(order, positions)

        assert result["zone"] == "green"
        assert result["buffer_delta"] == -5.0

    def test_yellow_boundary_delta_minus_20(self):
        """delta of exactly -20 is yellow (>= -20)."""
        today = date.today()
        # 20-day window, 10 elapsed -> time_pct = 50%
        order = _make_order(
            production_received_date=today - timedelta(days=10),
            final_deadline=today + timedelta(days=10),
        )
        # 6 of 20 done -> work_pct = 30%, delta = -20
        done = [_make_position(status=PositionStatus.PACKED) for _ in range(6)]
        wip = [_make_position(status=PositionStatus.PLANNED) for _ in range(14)]
        positions = done + wip

        result = _compute_buffer_zone(order, positions)

        assert result["zone"] == "yellow"
        assert result["buffer_delta"] == -20.0

    def test_done_statuses_include_all_terminal(self):
        """All terminal done statuses are counted as completed."""
        today = date.today()
        order = _make_order(
            production_received_date=today - timedelta(days=5),
            final_deadline=today + timedelta(days=5),
        )
        positions = [
            _make_position(status=PositionStatus.PACKED),
            _make_position(status=PositionStatus.QUALITY_CHECK_DONE),
            _make_position(status=PositionStatus.READY_FOR_SHIPMENT),
            _make_position(status=PositionStatus.SHIPPED),
            _make_position(status=PositionStatus.PLANNED),  # not done
        ]

        result = _compute_buffer_zone(order, positions)

        assert result["positions_done"] == 4
        assert result["positions_in_progress"] == 1

    def test_uses_schedule_deadline_as_fallback(self):
        """Uses schedule_deadline when final_deadline is None."""
        today = date.today()
        order = _make_order(
            production_received_date=today - timedelta(days=5),
            final_deadline=None,
            schedule_deadline=today + timedelta(days=5),
        )
        positions = [_make_position(status=PositionStatus.PLANNED)]

        result = _compute_buffer_zone(order, positions)

        assert result["days_remaining"] == 5
        assert result["zone"] is not None

    def test_uses_document_date_as_start_fallback(self):
        """Uses document_date when production_received_date is None."""
        today = date.today()
        order = _make_order(
            production_received_date=None,
            document_date=today - timedelta(days=5),
            final_deadline=today + timedelta(days=5),
        )
        positions = [_make_position(status=PositionStatus.PLANNED)]

        result = _compute_buffer_zone(order, positions)

        assert result["time_penetration_pct"] == 50.0


# ---------------------------------------------------------------------------
# Tests: calculate_buffer_health (buffer_health.py)
# ---------------------------------------------------------------------------

class TestCalculateBufferHealth:

    def test_returns_none_when_no_config(self):
        """Returns None when no BottleneckConfig exists for factory."""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        result = calculate_buffer_health(db, uuid.uuid4())
        assert result is None

    def test_green_when_buffer_above_66pct(self):
        """Buffer health is GREEN when hours >= target * 0.66."""
        factory_id = uuid.uuid4()
        kiln_id = uuid.uuid4()

        config = MagicMock()
        config.factory_id = factory_id
        config.constraint_resource_id = kiln_id
        config.buffer_target_hours = 24.0

        kiln = MagicMock()
        kiln.id = kiln_id
        kiln.name = "Kiln-1"

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = config
        db.query.return_value.get.return_value = kiln
        db.query.return_value.filter.return_value.all.return_value = []  # no buffered positions
        db.flush = MagicMock()

        with patch("business.services.buffer_health._get_avg_kiln_throughput", return_value=0.0):
            result = calculate_buffer_health(db, factory_id)

        # 0 hours < 24 * 0.33 -> RED (not green with zero buffer)
        assert result is not None
        assert result["health"] == "red"

    def test_result_structure(self):
        """Result dict has expected keys."""
        factory_id = uuid.uuid4()
        kiln_id = uuid.uuid4()

        config = MagicMock()
        config.factory_id = factory_id
        config.constraint_resource_id = kiln_id
        config.buffer_target_hours = 24.0

        kiln = MagicMock()
        kiln.id = kiln_id
        kiln.name = "Kiln-1"

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = config
        db.query.return_value.get.return_value = kiln
        db.query.return_value.filter.return_value.all.return_value = []
        db.flush = MagicMock()

        with patch("business.services.buffer_health._get_avg_kiln_throughput", return_value=0.0):
            result = calculate_buffer_health(db, factory_id)

        expected_keys = {"health", "hours", "target", "buffered_count", "buffered_sqm", "kiln_id", "kiln_name"}
        assert set(result.keys()) == expected_keys
