"""Integration tests for service blocking timing.

Tests cover:
- should_block_for_service returns True when lead_time >= days_until_glazing
- should_block_for_service returns False when plenty of time
- block_position_for_service changes status, records status_before_block
- unblock_position_service restores original status
- check_pending_service_blocks evaluates all positions needing services
- Different service types have different default lead times
"""
import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, patch, call

import pytest

from api.enums import PositionStatus, TaskType, TaskStatus, UserRole
from business.services.service_blocking import (
    should_block_for_service,
    block_position_for_service,
    unblock_position_service,
    check_pending_service_blocks,
    get_service_lead_time,
    DEFAULT_LEAD_TIMES,
    _SERVICE_TO_TASK_TYPE,
    _infer_services_from_position,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_position(
    status=PositionStatus.PLANNED,
    planned_glazing_date=None,
    factory_id=None,
    priority_order=0,
    order_id=None,
):
    p = MagicMock()
    p.id = uuid.uuid4()
    p.factory_id = factory_id or uuid.uuid4()
    p.status = status
    p.planned_glazing_date = planned_glazing_date
    p.priority_order = priority_order
    p.order_id = order_id or uuid.uuid4()
    return p


# ---------------------------------------------------------------------------
# Tests: DEFAULT_LEAD_TIMES
# ---------------------------------------------------------------------------

class TestDefaultLeadTimes:

    def test_stencil_default_3_days(self):
        assert DEFAULT_LEAD_TIMES['stencil'] == 3

    def test_silkscreen_default_5_days(self):
        assert DEFAULT_LEAD_TIMES['silkscreen'] == 5

    def test_color_matching_default_2_days(self):
        assert DEFAULT_LEAD_TIMES['color_matching'] == 2

    def test_custom_mold_default_7_days(self):
        assert DEFAULT_LEAD_TIMES['custom_mold'] == 7

    def test_service_to_task_type_mapping(self):
        """Each service type maps to a valid TaskType name."""
        assert _SERVICE_TO_TASK_TYPE['stencil'] == 'STENCIL_ORDER'
        assert _SERVICE_TO_TASK_TYPE['silkscreen'] == 'SILK_SCREEN_ORDER'
        assert _SERVICE_TO_TASK_TYPE['color_matching'] == 'COLOR_MATCHING'
        assert _SERVICE_TO_TASK_TYPE['custom_mold'] == 'MATERIAL_ORDER'


# ---------------------------------------------------------------------------
# Tests: get_service_lead_time
# ---------------------------------------------------------------------------

class TestGetServiceLeadTime:

    def test_returns_factory_override_when_exists(self):
        """Factory-specific lead time overrides the default."""
        db = MagicMock()
        row = MagicMock()
        row.lead_time_days = 10
        db.query.return_value.filter.return_value.first.return_value = row

        result = get_service_lead_time(db, uuid.uuid4(), 'stencil')
        assert result == 10

    def test_falls_back_to_default_when_no_override(self):
        """Returns default lead time when no factory override exists."""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        result = get_service_lead_time(db, uuid.uuid4(), 'silkscreen')
        assert result == 5  # DEFAULT_LEAD_TIMES['silkscreen']

    def test_falls_back_to_3_for_unknown_service(self):
        """Returns 3 for unknown service type not in defaults."""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        result = get_service_lead_time(db, uuid.uuid4(), 'unknown_service')
        assert result == 3


# ---------------------------------------------------------------------------
# Tests: should_block_for_service
# ---------------------------------------------------------------------------

class TestShouldBlockForService:

    def test_returns_true_when_lead_time_gte_days_until_glazing(self):
        """Block when lead_time (3) >= days_until_glazing (2)."""
        pos = _make_position(planned_glazing_date=date.today() + timedelta(days=2))
        db = MagicMock()

        with patch("business.services.service_blocking.get_service_lead_time", return_value=3):
            should_block, days_left = should_block_for_service(db, pos, 'stencil')

        assert should_block is True
        assert days_left == 2

    def test_returns_false_when_plenty_of_time(self):
        """Don't block when lead_time (3) < days_until_glazing (10)."""
        pos = _make_position(planned_glazing_date=date.today() + timedelta(days=10))
        db = MagicMock()

        with patch("business.services.service_blocking.get_service_lead_time", return_value=3):
            should_block, days_left = should_block_for_service(db, pos, 'stencil')

        assert should_block is False
        assert days_left == 10

    def test_returns_false_when_no_glazing_date(self):
        """Don't block when no planned_glazing_date is set."""
        pos = _make_position(planned_glazing_date=None)
        db = MagicMock()

        should_block, days_left = should_block_for_service(db, pos, 'stencil')

        assert should_block is False
        assert days_left == 0

    def test_returns_true_when_glazing_in_past(self):
        """Block immediately when glazing date is in the past."""
        pos = _make_position(planned_glazing_date=date.today() - timedelta(days=1))
        db = MagicMock()

        should_block, days_left = should_block_for_service(db, pos, 'stencil')

        assert should_block is True
        assert days_left == 0

    def test_returns_true_when_glazing_is_today(self):
        """Block when glazing is today (days_until_glazing == 0)."""
        pos = _make_position(planned_glazing_date=date.today())
        db = MagicMock()

        should_block, days_left = should_block_for_service(db, pos, 'stencil')

        assert should_block is True
        assert days_left == 0

    def test_exact_boundary_lead_time_equals_days(self):
        """Block when lead_time exactly equals days_until_glazing."""
        pos = _make_position(planned_glazing_date=date.today() + timedelta(days=5))
        db = MagicMock()

        with patch("business.services.service_blocking.get_service_lead_time", return_value=5):
            should_block, days_left = should_block_for_service(db, pos, 'silkscreen')

        assert should_block is True
        assert days_left == 5


# ---------------------------------------------------------------------------
# Tests: block_position_for_service
# ---------------------------------------------------------------------------

class TestBlockPositionForService:

    def test_changes_status_to_awaiting(self):
        """Blocking for stencil sets status to AWAITING_STENCIL_SILKSCREEN."""
        pos = _make_position(
            status=PositionStatus.PLANNED,
            planned_glazing_date=date.today() + timedelta(days=3),
        )
        db = MagicMock()

        with patch("business.services.service_blocking.get_service_lead_time", return_value=3):
            task = block_position_for_service(db, pos, 'stencil')

        assert pos.status == PositionStatus.AWAITING_STENCIL_SILKSCREEN

    def test_color_matching_sets_correct_status(self):
        """Blocking for color_matching sets status to AWAITING_COLOR_MATCHING."""
        pos = _make_position(
            status=PositionStatus.PLANNED,
            planned_glazing_date=date.today() + timedelta(days=2),
        )
        db = MagicMock()

        with patch("business.services.service_blocking.get_service_lead_time", return_value=2):
            block_position_for_service(db, pos, 'color_matching')

        assert pos.status == PositionStatus.AWAITING_COLOR_MATCHING

    def test_records_status_before_block_via_sql(self):
        """Raw SQL UPDATE records blocked_by_service and status_before_block."""
        pos = _make_position(status=PositionStatus.PLANNED)
        pos.planned_glazing_date = date.today() + timedelta(days=3)
        db = MagicMock()

        with patch("business.services.service_blocking.get_service_lead_time", return_value=3):
            block_position_for_service(db, pos, 'stencil')

        db.execute.assert_called()

    def test_creates_blocking_task(self):
        """A blocking Task is created with correct type and role."""
        pos = _make_position(
            status=PositionStatus.PLANNED,
            planned_glazing_date=date.today() + timedelta(days=5),
        )
        db = MagicMock()

        with patch("business.services.service_blocking.get_service_lead_time", return_value=3):
            task = block_position_for_service(db, pos, 'stencil')

        db.add.assert_called_once()
        added_task = db.add.call_args[0][0]
        assert added_task.type == TaskType.STENCIL_ORDER
        assert added_task.status == TaskStatus.PENDING
        assert added_task.assigned_role == UserRole.PRODUCTION_MANAGER
        assert added_task.blocking is True


# ---------------------------------------------------------------------------
# Tests: unblock_position_service
# ---------------------------------------------------------------------------

class TestUnblockPositionService:

    def test_restores_original_status(self):
        """Unblocking restores status from status_before_block."""
        pos = _make_position(status=PositionStatus.AWAITING_STENCIL_SILKSCREEN, priority_order=5)
        db = MagicMock()
        # Simulate raw SQL returning the saved status
        row = MagicMock()
        row.__getitem__ = lambda self, i: ['planned', 'stencil'][i]
        db.execute.return_value.fetchone.return_value = row

        result = unblock_position_service(db, pos)

        assert result['unblocked'] is True
        assert result['restored_status'] == 'planned'
        assert pos.status == PositionStatus.PLANNED

    def test_boosts_priority_by_10(self):
        """Priority is increased by 10 after unblock."""
        pos = _make_position(status=PositionStatus.AWAITING_STENCIL_SILKSCREEN, priority_order=15)
        db = MagicMock()
        row = MagicMock()
        row.__getitem__ = lambda self, i: ['planned', 'stencil'][i]
        db.execute.return_value.fetchone.return_value = row

        result = unblock_position_service(db, pos)

        assert result['new_priority_order'] == 25  # 15 + 10
        assert pos.priority_order == 25

    def test_falls_back_to_planned_when_no_saved_status(self):
        """Uses PLANNED status when status_before_block is not available."""
        pos = _make_position(status=PositionStatus.AWAITING_COLOR_MATCHING, priority_order=0)
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = None

        result = unblock_position_service(db, pos)

        assert result['restored_status'] == 'planned'

    def test_clears_blocking_columns_via_sql(self):
        """Raw SQL clears blocked_by_service and status_before_block."""
        pos = _make_position(status=PositionStatus.AWAITING_STENCIL_SILKSCREEN, priority_order=0)
        db = MagicMock()
        row = MagicMock()
        row.__getitem__ = lambda self, i: ['planned', 'stencil'][i]
        db.execute.return_value.fetchone.return_value = row

        unblock_position_service(db, pos)

        # Two db.execute calls: one read, one clear
        assert db.execute.call_count >= 2


# ---------------------------------------------------------------------------
# Tests: check_pending_service_blocks
# ---------------------------------------------------------------------------

class TestCheckPendingServiceBlocks:

    def test_blocks_positions_when_timing_triggers(self):
        """Positions are blocked when should_block_for_service returns True."""
        factory_id = uuid.uuid4()
        pos = _make_position(
            factory_id=factory_id,
            status=PositionStatus.PLANNED,
            planned_glazing_date=date.today() + timedelta(days=2),
        )
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = [pos]
        # Not already blocked
        row = MagicMock()
        row.__getitem__ = lambda self, i: [None][i]
        db.execute.return_value.fetchone.return_value = row

        with patch("business.services.service_blocking._infer_services_from_position", return_value=['stencil']), \
             patch("business.services.service_blocking.should_block_for_service", return_value=(True, 2)), \
             patch("business.services.service_blocking.block_position_for_service") as mock_block:
            result = check_pending_service_blocks(db, factory_id)

        assert result['newly_blocked'] == 1
        mock_block.assert_called_once()

    def test_skips_already_blocked_positions(self):
        """Positions already blocked are skipped."""
        factory_id = uuid.uuid4()
        pos = _make_position(factory_id=factory_id, planned_glazing_date=date.today() + timedelta(days=2))
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = [pos]
        # Already blocked
        row = MagicMock()
        row.__getitem__ = lambda self, i: ['stencil'][i]
        db.execute.return_value.fetchone.return_value = row

        result = check_pending_service_blocks(db, factory_id)

        assert result['skipped_already_blocked'] == 1
        assert result['newly_blocked'] == 0

    def test_returns_summary_dict(self):
        """Result dict has expected keys."""
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []

        result = check_pending_service_blocks(db)

        expected_keys = {'factory_id', 'positions_checked', 'newly_blocked', 'skipped_already_blocked'}
        assert set(result.keys()) == expected_keys
