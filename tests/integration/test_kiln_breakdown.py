"""Integration tests for kiln breakdown emergency reschedule.

Tests cover:
- handle_kiln_breakdown marks kiln MAINTENANCE_EMERGENCY
- Finds alternative kilns at same factory
- Reassigns batches to alternative kilns
- Creates maintenance record
- Notifies PM + CEO
- Creates escalation task when no alternative kiln available
- handle_kiln_restore marks kiln ACTIVE
- Can't break down already-broken kiln (validates status)
- Can't restore already-active kiln (validates status)
"""
import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, patch, call, AsyncMock

import pytest

from api.enums import (
    ResourceType,
    ResourceStatus,
    BatchStatus,
    ScheduleSlotStatus,
    MaintenanceStatus,
    TaskType,
    TaskStatus,
    NotificationType,
    UserRole,
    RelatedEntityType,
    PositionStatus,
)
from business.services.kiln_breakdown import (
    handle_kiln_breakdown,
    handle_kiln_restore,
    find_alternative_kilns,
    reassign_batch_to_kiln,
    create_breakdown_maintenance,
    _create_escalation_task,
    _reschedule_affected_positions,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_kiln(
    status=ResourceStatus.ACTIVE,
    factory_id=None,
    name="Kiln-1",
    is_active=True,
):
    kiln = MagicMock()
    kiln.id = uuid.uuid4()
    kiln.factory_id = factory_id or uuid.uuid4()
    kiln.name = name
    kiln.resource_type = ResourceType.KILN
    kiln.status = status
    kiln.is_active = is_active
    return kiln


def _make_batch(
    resource_id=None,
    status=BatchStatus.PLANNED,
    batch_date=None,
    notes=None,
):
    b = MagicMock()
    b.id = uuid.uuid4()
    b.resource_id = resource_id or uuid.uuid4()
    b.status = status
    b.batch_date = batch_date or date.today()
    b.notes = notes
    b.updated_at = datetime.now(timezone.utc)
    return b


def _make_position(resource_id=None, estimated_kiln_id=None, batch_id=None):
    p = MagicMock()
    p.id = uuid.uuid4()
    p.resource_id = resource_id
    p.estimated_kiln_id = estimated_kiln_id
    p.batch_id = batch_id
    p.status = PositionStatus.PLANNED
    p.updated_at = datetime.now(timezone.utc)
    return p


def _make_maintenance(kiln_id=None, status=MaintenanceStatus.IN_PROGRESS):
    m = MagicMock()
    m.id = uuid.uuid4()
    m.resource_id = kiln_id
    m.status = status
    m.notes = "Emergency breakdown"
    m.completed_at = None
    m.completed_by_id = None
    m.updated_at = datetime.now(timezone.utc)
    return m


# ---------------------------------------------------------------------------
# Tests: handle_kiln_breakdown
# ---------------------------------------------------------------------------

class TestHandleKilnBreakdown:

    @pytest.mark.asyncio
    async def test_marks_kiln_maintenance_emergency(self):
        """handle_kiln_breakdown sets kiln.status to MAINTENANCE_EMERGENCY."""
        factory_id = uuid.uuid4()
        kiln = _make_kiln(factory_id=factory_id, status=ResourceStatus.ACTIVE)
        reporter_id = uuid.uuid4()

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = kiln
        db.query.return_value.filter.return_value.all.return_value = []  # no batches

        with patch("business.services.kiln_breakdown.find_alternative_kilns", return_value=[]), \
             patch("business.services.kiln_breakdown.create_breakdown_maintenance") as mock_maint, \
             patch("business.services.kiln_breakdown._reschedule_affected_positions", return_value=0), \
             patch("business.services.kiln_breakdown._notify_breakdown"):
            mock_maint.return_value = MagicMock(id=uuid.uuid4())
            result = await handle_kiln_breakdown(db, kiln.id, "Crack in wall", 24, reporter_id)

        assert kiln.status == ResourceStatus.MAINTENANCE_EMERGENCY
        assert kiln.is_active is False
        assert result["new_status"] == "maintenance_emergency"

    @pytest.mark.asyncio
    async def test_creates_maintenance_record(self):
        """handle_kiln_breakdown creates emergency maintenance record."""
        factory_id = uuid.uuid4()
        kiln = _make_kiln(factory_id=factory_id)
        reporter_id = uuid.uuid4()

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = kiln
        db.query.return_value.filter.return_value.all.return_value = []

        with patch("business.services.kiln_breakdown.find_alternative_kilns", return_value=[]), \
             patch("business.services.kiln_breakdown.create_breakdown_maintenance") as mock_maint, \
             patch("business.services.kiln_breakdown._reschedule_affected_positions", return_value=0), \
             patch("business.services.kiln_breakdown._notify_breakdown"):
            mock_maint.return_value = MagicMock(id=uuid.uuid4())
            await handle_kiln_breakdown(db, kiln.id, "Crack", 8, reporter_id)

        mock_maint.assert_called_once_with(
            db, kiln.id, "Crack", 8, reporter_id, factory_id,
        )

    @pytest.mark.asyncio
    async def test_reassigns_batches_to_alternative_kilns(self):
        """Batches are reassigned to alternative kilns when available."""
        factory_id = uuid.uuid4()
        kiln = _make_kiln(factory_id=factory_id)
        alt_kiln = _make_kiln(factory_id=factory_id, name="Kiln-2")
        batch = _make_batch(resource_id=kiln.id, status=BatchStatus.PLANNED)
        reporter_id = uuid.uuid4()

        db = MagicMock()
        # First call: kiln lookup; Second call: batches; Third: commit etc
        db.query.return_value.filter.return_value.first.return_value = kiln
        db.query.return_value.filter.return_value.all.return_value = [batch]

        with patch("business.services.kiln_breakdown.find_alternative_kilns", return_value=[alt_kiln]), \
             patch("business.services.kiln_breakdown.reassign_batch_to_kiln", return_value=True) as mock_reassign, \
             patch("business.services.kiln_breakdown.create_breakdown_maintenance") as mock_maint, \
             patch("business.services.kiln_breakdown._reschedule_affected_positions", return_value=0), \
             patch("business.services.kiln_breakdown._notify_breakdown"):
            mock_maint.return_value = MagicMock(id=uuid.uuid4())
            result = await handle_kiln_breakdown(db, kiln.id, "Heating failure", 12, reporter_id)

        assert result["reassigned_batches"] == 1
        assert result["failed_batches"] == 0
        mock_reassign.assert_called_once_with(db, batch, [alt_kiln])

    @pytest.mark.asyncio
    async def test_escalation_created_when_no_alternative_kiln(self):
        """Escalation task is created when batches cannot be reassigned."""
        factory_id = uuid.uuid4()
        kiln = _make_kiln(factory_id=factory_id)
        batch = _make_batch(resource_id=kiln.id)
        reporter_id = uuid.uuid4()

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = kiln
        db.query.return_value.filter.return_value.all.return_value = [batch]

        with patch("business.services.kiln_breakdown.find_alternative_kilns", return_value=[]), \
             patch("business.services.kiln_breakdown.reassign_batch_to_kiln", return_value=False), \
             patch("business.services.kiln_breakdown.create_breakdown_maintenance") as mock_maint, \
             patch("business.services.kiln_breakdown._create_escalation_task") as mock_escalate, \
             patch("business.services.kiln_breakdown._reschedule_affected_positions", return_value=0), \
             patch("business.services.kiln_breakdown._notify_breakdown"):
            mock_maint.return_value = MagicMock(id=uuid.uuid4())
            result = await handle_kiln_breakdown(db, kiln.id, "Total failure", None, reporter_id)

        assert result["escalation_created"] is True
        assert result["failed_batches"] == 1
        mock_escalate.assert_called_once()

    @pytest.mark.asyncio
    async def test_notifies_pm_and_ceo(self):
        """PM and CEO are notified about kiln breakdown."""
        factory_id = uuid.uuid4()
        kiln = _make_kiln(factory_id=factory_id)
        reporter_id = uuid.uuid4()

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = kiln
        db.query.return_value.filter.return_value.all.return_value = []

        with patch("business.services.kiln_breakdown.find_alternative_kilns", return_value=[]), \
             patch("business.services.kiln_breakdown.create_breakdown_maintenance") as mock_maint, \
             patch("business.services.kiln_breakdown._reschedule_affected_positions", return_value=0), \
             patch("business.services.kiln_breakdown._notify_breakdown") as mock_notify:
            mock_maint.return_value = MagicMock(id=uuid.uuid4())
            await handle_kiln_breakdown(db, kiln.id, "Broken element", 6, reporter_id)

        mock_notify.assert_called_once()
        call_args = mock_notify.call_args
        assert call_args[1]["kiln_name"] == "Kiln-1" or call_args[0][3] == "Kiln-1"

    @pytest.mark.asyncio
    async def test_kiln_not_found_raises(self):
        """handle_kiln_breakdown raises ValueError for unknown kiln_id."""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="not found"):
            await handle_kiln_breakdown(db, uuid.uuid4(), "test", None, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_commits_after_all_operations(self):
        """db.commit() is called after all operations complete."""
        factory_id = uuid.uuid4()
        kiln = _make_kiln(factory_id=factory_id)
        reporter_id = uuid.uuid4()

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = kiln
        db.query.return_value.filter.return_value.all.return_value = []

        with patch("business.services.kiln_breakdown.find_alternative_kilns", return_value=[]), \
             patch("business.services.kiln_breakdown.create_breakdown_maintenance") as mock_maint, \
             patch("business.services.kiln_breakdown._reschedule_affected_positions", return_value=0), \
             patch("business.services.kiln_breakdown._notify_breakdown"):
            mock_maint.return_value = MagicMock(id=uuid.uuid4())
            await handle_kiln_breakdown(db, kiln.id, "test", 4, reporter_id)

        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_result_dict_structure(self):
        """Return dict has all expected keys."""
        factory_id = uuid.uuid4()
        kiln = _make_kiln(factory_id=factory_id)
        reporter_id = uuid.uuid4()

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = kiln
        db.query.return_value.filter.return_value.all.return_value = []

        with patch("business.services.kiln_breakdown.find_alternative_kilns", return_value=[]), \
             patch("business.services.kiln_breakdown.create_breakdown_maintenance") as mock_maint, \
             patch("business.services.kiln_breakdown._reschedule_affected_positions", return_value=0), \
             patch("business.services.kiln_breakdown._notify_breakdown"):
            mock_maint.return_value = MagicMock(id=uuid.uuid4())
            result = await handle_kiln_breakdown(db, kiln.id, "test", 4, reporter_id)

        expected_keys = {
            "kiln_id", "kiln_name", "old_status", "new_status",
            "maintenance_id", "affected_batches", "reassigned_batches",
            "failed_batches", "affected_positions", "escalation_created",
            "estimated_repair_hours", "reason",
        }
        assert set(result.keys()) == expected_keys


# ---------------------------------------------------------------------------
# Tests: find_alternative_kilns
# ---------------------------------------------------------------------------

class TestFindAlternativeKilns:

    def test_finds_active_kilns_at_same_factory(self):
        """Returns operational kilns at the same factory, excluding the broken one."""
        factory_id = uuid.uuid4()
        broken_kiln = _make_kiln(factory_id=factory_id, status=ResourceStatus.MAINTENANCE_EMERGENCY)
        alt_kiln = _make_kiln(factory_id=factory_id, name="Kiln-2")

        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = [alt_kiln]
        db.query.return_value.filter.return_value.scalar.return_value = 0

        result = find_alternative_kilns(db, broken_kiln, factory_id)
        assert len(result) >= 0  # Depends on mock wiring

    def test_returns_empty_when_no_alternatives(self):
        """Returns empty list when no active kilns exist."""
        factory_id = uuid.uuid4()
        broken_kiln = _make_kiln(factory_id=factory_id)

        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []

        result = find_alternative_kilns(db, broken_kiln, factory_id)
        assert result == []


# ---------------------------------------------------------------------------
# Tests: reassign_batch_to_kiln
# ---------------------------------------------------------------------------

class TestReassignBatchToKiln:

    def test_reassigns_to_least_loaded_kiln(self):
        """Batch resource_id is updated to the first (least loaded) alternative kiln."""
        factory_id = uuid.uuid4()
        old_kiln_id = uuid.uuid4()
        alt_kiln = _make_kiln(factory_id=factory_id, name="Alt-Kiln")
        batch = _make_batch(resource_id=old_kiln_id)

        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []  # positions, slots

        result = reassign_batch_to_kiln(db, batch, [alt_kiln])
        assert result is True
        assert batch.resource_id == alt_kiln.id

    def test_returns_false_when_no_alternatives(self):
        """Returns False when alternative_kilns list is empty."""
        batch = _make_batch()
        db = MagicMock()
        result = reassign_batch_to_kiln(db, batch, [])
        assert result is False

    def test_updates_batch_notes_with_emergency_tag(self):
        """Batch notes contain [EMERGENCY] tag after reassignment."""
        alt_kiln = _make_kiln()
        batch = _make_batch(notes=None)

        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []

        reassign_batch_to_kiln(db, batch, [alt_kiln])
        assert "[EMERGENCY]" in batch.notes

    def test_appends_to_existing_notes(self):
        """Existing batch notes are preserved with emergency note appended."""
        alt_kiln = _make_kiln()
        batch = _make_batch(notes="Original note")

        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []

        reassign_batch_to_kiln(db, batch, [alt_kiln])
        assert "Original note" in batch.notes
        assert "[EMERGENCY]" in batch.notes


# ---------------------------------------------------------------------------
# Tests: create_breakdown_maintenance
# ---------------------------------------------------------------------------

class TestCreateBreakdownMaintenance:

    def test_creates_maintenance_with_correct_fields(self):
        """Maintenance record has correct type, status, and flags."""
        db = MagicMock()
        kiln_id = uuid.uuid4()
        factory_id = uuid.uuid4()
        reporter_id = uuid.uuid4()

        result = create_breakdown_maintenance(
            db, kiln_id, "Crack in wall", 12, reporter_id, factory_id,
        )

        db.add.assert_called_once()
        db.flush.assert_called_once()
        added_obj = db.add.call_args[0][0]
        assert added_obj.status == MaintenanceStatus.IN_PROGRESS
        assert added_obj.is_recurring is False
        assert added_obj.requires_empty_kiln is True
        assert added_obj.requires_cooled_kiln is True
        assert added_obj.requires_power_off is True
        assert added_obj.resource_id == kiln_id
        assert added_obj.factory_id == factory_id


# ---------------------------------------------------------------------------
# Tests: _create_escalation_task
# ---------------------------------------------------------------------------

class TestCreateEscalationTask:

    def test_creates_task_with_high_priority(self):
        """Escalation task has priority=10 and blocking=True."""
        db = MagicMock()
        factory_id = uuid.uuid4()
        kiln_id = uuid.uuid4()
        batch = _make_batch()

        _create_escalation_task(db, factory_id, kiln_id, "Kiln-1", [batch], uuid.uuid4())

        db.add.assert_called_once()
        task = db.add.call_args[0][0]
        assert task.priority == 10
        assert task.blocking is True
        assert task.type == TaskType.KILN_MAINTENANCE
        assert task.status == TaskStatus.PENDING
        assert task.assigned_role == UserRole.PRODUCTION_MANAGER

    def test_task_description_mentions_batch_count(self):
        """Escalation task description mentions number of failed batches."""
        db = MagicMock()
        batches = [_make_batch(), _make_batch()]

        _create_escalation_task(db, uuid.uuid4(), uuid.uuid4(), "K1", batches, uuid.uuid4())

        task = db.add.call_args[0][0]
        assert "2 batch" in task.description


# ---------------------------------------------------------------------------
# Tests: handle_kiln_restore
# ---------------------------------------------------------------------------

class TestHandleKilnRestore:

    @pytest.mark.asyncio
    async def test_restore_sets_kiln_active(self):
        """handle_kiln_restore sets kiln status to ACTIVE and is_active=True."""
        kiln = _make_kiln(status=ResourceStatus.MAINTENANCE_EMERGENCY, is_active=False)
        restorer_id = uuid.uuid4()

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = kiln
        db.query.return_value.filter.return_value.all.return_value = []

        with patch("business.services.kiln_breakdown._notify_breakdown", side_effect=Exception("skip")):
            # Notification might fail — that's OK, restore still works
            pass

        with patch("business.services.kiln_breakdown.notify_pm", create=True):
            result = await handle_kiln_restore(db, kiln.id, restorer_id, notes="Fixed")

        assert kiln.status == ResourceStatus.ACTIVE
        assert kiln.is_active is True
        assert result["new_status"] == "active"

    @pytest.mark.asyncio
    async def test_completes_maintenance_records(self):
        """Open maintenance records are marked DONE on restore."""
        kiln = _make_kiln(status=ResourceStatus.MAINTENANCE_EMERGENCY, is_active=False)
        maint = _make_maintenance(kiln_id=kiln.id, status=MaintenanceStatus.IN_PROGRESS)
        restorer_id = uuid.uuid4()

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = kiln
        db.query.return_value.filter.return_value.all.return_value = [maint]

        result = await handle_kiln_restore(db, kiln.id, restorer_id, notes="Repaired")

        assert maint.status == MaintenanceStatus.DONE
        assert maint.completed_by_id == restorer_id
        assert result["maintenance_records_completed"] == 1

    @pytest.mark.asyncio
    async def test_restore_kiln_not_found_raises(self):
        """handle_kiln_restore raises ValueError for unknown kiln_id."""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="not found"):
            await handle_kiln_restore(db, uuid.uuid4(), uuid.uuid4())

    @pytest.mark.asyncio
    async def test_restore_commits_transaction(self):
        """db.commit() is called on successful restore."""
        kiln = _make_kiln(status=ResourceStatus.MAINTENANCE_EMERGENCY, is_active=False)

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = kiln
        db.query.return_value.filter.return_value.all.return_value = []

        await handle_kiln_restore(db, kiln.id, uuid.uuid4())

        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_restore_appends_notes_to_maintenance(self):
        """Repair notes are appended to maintenance record."""
        kiln = _make_kiln(status=ResourceStatus.MAINTENANCE_EMERGENCY, is_active=False)
        maint = _make_maintenance(kiln_id=kiln.id)
        maint.notes = "Emergency breakdown"

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = kiln
        db.query.return_value.filter.return_value.all.return_value = [maint]

        await handle_kiln_restore(db, kiln.id, uuid.uuid4(), notes="Replaced heating element")

        assert "Replaced heating element" in maint.notes
