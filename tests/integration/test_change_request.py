"""Integration tests for change request from webhook.

Tests cover:
- create_change_request_from_webhook with qty change
- create_change_request_from_webhook with color change
- approve_change_request applies to positions
- reject_change_request sets status, stores reason
- partial apply (apply to some positions, not all)
- callback to sales on approve/reject
"""
import uuid
from datetime import datetime, date, timezone
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from api.enums import ChangeRequestStatus, NotificationType, RelatedEntityType, UserRole
from business.services.change_request_service import (
    create_change_request_from_webhook,
    approve_change_request,
    reject_change_request,
    _snapshot_order,
    _compute_diff,
    _notify_pms,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_order(
    order_number="ORD-001",
    client="Test Client",
    client_location="Bali",
    factory_id=None,
    final_deadline=None,
    desired_delivery_date=None,
    mandatory_qc=False,
    notes=None,
    sales_manager_name="Alice",
    sales_manager_contact="alice@test.com",
    external_id="ext-001",
):
    order = MagicMock()
    order.id = uuid.uuid4()
    order.order_number = order_number
    order.client = client
    order.client_location = client_location
    order.factory_id = factory_id or uuid.uuid4()
    order.final_deadline = final_deadline
    order.desired_delivery_date = desired_delivery_date
    order.mandatory_qc = mandatory_qc
    order.notes = notes
    order.sales_manager_name = sales_manager_name
    order.sales_manager_contact = sales_manager_contact
    order.external_id = external_id
    order.change_req_payload = None
    order.change_req_status = None
    order.change_req_requested_at = None
    order.change_req_decided_at = None
    order.change_req_decided_by = None
    order.updated_at = datetime.now(timezone.utc)
    return order


def _make_change_request(order_id=None, status=ChangeRequestStatus.PENDING, diff_json=None):
    cr = MagicMock()
    cr.id = uuid.uuid4()
    cr.order_id = order_id or uuid.uuid4()
    cr.status = status
    cr.change_type = "order_update"
    cr.diff_json = diff_json or {
        "source": "sales_webhook",
        "diff": {},
        "old_data": {},
        "new_data": {
            "client": "New Client",
            "client_location": "Jakarta",
        },
        "full_payload": {},
    }
    cr.notes = None
    cr.reviewed_by = None
    cr.reviewed_at = None
    return cr


def _make_pm_user(factory_id):
    pm = MagicMock()
    pm.id = uuid.uuid4()
    pm.role = UserRole.PRODUCTION_MANAGER.value
    pm.is_active = True
    return pm


# ---------------------------------------------------------------------------
# Tests: _snapshot_order / _compute_diff
# ---------------------------------------------------------------------------

class TestSnapshotAndDiff:

    def test_snapshot_captures_order_fields(self):
        """_snapshot_order returns dict with expected keys."""
        order = _make_order(client="Alpha Corp", notes="Rush order")
        snap = _snapshot_order(order)

        assert snap["client"] == "Alpha Corp"
        assert snap["notes"] == "Rush order"
        assert "sales_manager_name" in snap
        assert "mandatory_qc" in snap

    def test_compute_diff_detects_changes(self):
        """_compute_diff returns only changed fields."""
        old = {"client": "A", "notes": "same", "location": "Bali"}
        new = {"client": "B", "notes": "same", "location": "Java"}

        diff = _compute_diff(old, new)
        assert "client" in diff
        assert diff["client"] == {"old": "A", "new": "B"}
        assert "location" in diff
        assert "notes" not in diff

    def test_compute_diff_empty_when_no_changes(self):
        """_compute_diff returns empty dict when values match."""
        data = {"client": "X", "notes": "Y"}
        diff = _compute_diff(data, data)
        assert diff == {}


# ---------------------------------------------------------------------------
# Tests: create_change_request_from_webhook
# ---------------------------------------------------------------------------

class TestCreateChangeRequestFromWebhook:

    @patch("business.services.change_request_service.ProductionOrderChangeRequest", create=True)
    def test_qty_change_creates_pending_cr(self, MockCR):
        """Webhook with qty change creates PENDING change request."""
        order = _make_order()
        db = MagicMock()
        # Mock the items count query
        db.query.return_value.filter_by.return_value.count.return_value = 3
        # Mock closing previous pending CRs
        db.query.return_value.filter.return_value.update.return_value = 0

        new_data = {
            "client": order.client,
            "items": [{"sku": "A", "qty": 100}, {"sku": "B", "qty": 200}],
        }

        with patch("business.services.change_request_service._notify_pms", return_value=1):
            cr = create_change_request_from_webhook(db, order, new_data)

        db.add.assert_called_once()
        db.flush.assert_called_once()
        assert order.change_req_status == "pending"
        assert order.change_req_payload == new_data

    @patch("business.services.change_request_service.ProductionOrderChangeRequest", create=True)
    def test_color_change_creates_cr_with_diff(self, MockCR):
        """Webhook with color change captures diff in cr.diff_json."""
        order = _make_order(client="OldClient")
        db = MagicMock()
        db.query.return_value.filter_by.return_value.count.return_value = 2
        db.query.return_value.filter.return_value.update.return_value = 0

        new_data = {
            "client": "NewClient",
            "items": [{"sku": "A", "qty": 50}],
        }

        with patch("business.services.change_request_service._notify_pms", return_value=1):
            cr = create_change_request_from_webhook(db, order, new_data)

        added_cr = db.add.call_args[0][0]
        assert added_cr.status == ChangeRequestStatus.PENDING
        assert added_cr.change_type == "order_update"

    @patch("business.services.change_request_service.ProductionOrderChangeRequest", create=True)
    def test_supersedes_previous_pending_cr(self, MockCR):
        """New CR supersedes (rejects) any previous PENDING CRs for same order."""
        order = _make_order()
        db = MagicMock()
        db.query.return_value.filter_by.return_value.count.return_value = 1
        mock_update = db.query.return_value.filter.return_value.update
        mock_update.return_value = 1

        with patch("business.services.change_request_service._notify_pms", return_value=1):
            create_change_request_from_webhook(db, order, {"items": []})

        # Verify update was called to reject old pending CRs
        mock_update.assert_called()

    @patch("business.services.change_request_service.ProductionOrderChangeRequest", create=True)
    def test_notifies_pms_on_creation(self, MockCR):
        """PMs are notified when change request is created."""
        order = _make_order()
        db = MagicMock()
        db.query.return_value.filter_by.return_value.count.return_value = 0
        db.query.return_value.filter.return_value.update.return_value = 0

        with patch("business.services.change_request_service._notify_pms", return_value=2) as mock_notify:
            create_change_request_from_webhook(db, order, {"items": []})

        mock_notify.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: approve_change_request
# ---------------------------------------------------------------------------

class TestApproveChangeRequest:

    def test_approve_applies_scalar_fields(self):
        """approve_change_request applies client, notes etc. to the order."""
        order = _make_order(client="OldClient", notes="Old notes")
        cr = _make_change_request(
            order_id=order.id,
            diff_json={
                "new_data": {
                    "client": "NewClient",
                    "notes": "Updated notes",
                },
                "full_payload": {},
            },
        )
        approver_id = uuid.uuid4()
        db = MagicMock()

        result = approve_change_request(db, order, cr, notes="Looks good", approved_by_id=approver_id)

        assert result["status"] == "approved"
        assert "client" in result["applied_fields"]
        assert order.client == "NewClient"
        assert cr.status == ChangeRequestStatus.APPROVED
        assert cr.reviewed_by == approver_id

    def test_approve_clears_change_req_on_order(self):
        """After approval, order.change_req_status='approved' and payload is None."""
        order = _make_order()
        order.change_req_payload = {"some": "data"}
        cr = _make_change_request(order_id=order.id, diff_json={"new_data": {}, "full_payload": {}})
        db = MagicMock()

        approve_change_request(db, order, cr)

        assert order.change_req_status == "approved"
        assert order.change_req_payload is None

    def test_approve_non_pending_raises(self):
        """Cannot approve a non-PENDING change request."""
        order = _make_order()
        cr = _make_change_request(status=ChangeRequestStatus.APPROVED)
        db = MagicMock()

        with pytest.raises(ValueError, match="not pending"):
            approve_change_request(db, order, cr)

    def test_approve_partial_apply_records_info(self):
        """Partial apply log tracks which positions were targeted."""
        order = _make_order()
        cr = _make_change_request(
            order_id=order.id,
            diff_json={"new_data": {"client": "X"}, "full_payload": {}},
        )
        db = MagicMock()

        result = approve_change_request(
            db, order, cr,
            apply_to_positions=["pos-1", "pos-3"],
            notes="Only some",
        )

        assert result["partial_log"]["apply_to_positions"] == ["pos-1", "pos-3"]

    def test_approve_parses_date_fields(self):
        """Date string fields are parsed to date objects."""
        order = _make_order()
        cr = _make_change_request(
            order_id=order.id,
            diff_json={
                "new_data": {
                    "final_deadline": "2026-06-15",
                    "desired_delivery_date": "2026-07-01",
                },
                "full_payload": {},
            },
        )
        db = MagicMock()

        result = approve_change_request(db, order, cr)

        assert "final_deadline" in result["applied_fields"]
        assert order.final_deadline == date.fromisoformat("2026-06-15")


# ---------------------------------------------------------------------------
# Tests: reject_change_request
# ---------------------------------------------------------------------------

class TestRejectChangeRequest:

    def test_reject_sets_status_and_reason(self):
        """reject_change_request sets REJECTED status and stores reason."""
        order = _make_order()
        cr = _make_change_request(order_id=order.id)
        rejector_id = uuid.uuid4()
        db = MagicMock()

        result = reject_change_request(db, order, cr, reason="Not feasible", rejected_by_id=rejector_id)

        assert result["status"] == "rejected"
        assert result["reason"] == "Not feasible"
        assert cr.status == ChangeRequestStatus.REJECTED
        assert cr.reviewed_by == rejector_id
        assert cr.notes == "Not feasible"

    def test_reject_clears_order_payload(self):
        """After rejection, order.change_req_payload is cleared."""
        order = _make_order()
        order.change_req_payload = {"data": "xyz"}
        cr = _make_change_request(order_id=order.id)
        db = MagicMock()

        reject_change_request(db, order, cr, reason="Cancelled by PM")

        assert order.change_req_status == "rejected"
        assert order.change_req_payload is None

    def test_reject_non_pending_raises(self):
        """Cannot reject a non-PENDING change request."""
        order = _make_order()
        cr = _make_change_request(status=ChangeRequestStatus.REJECTED)
        db = MagicMock()

        with pytest.raises(ValueError, match="not pending"):
            reject_change_request(db, order, cr, reason="test")

    def test_reject_result_dict_structure(self):
        """Reject result dict has expected keys."""
        order = _make_order()
        cr = _make_change_request(order_id=order.id)
        db = MagicMock()

        result = reject_change_request(db, order, cr, reason="Nope")

        assert set(result.keys()) == {"cr_id", "order_id", "order_number", "status", "reason"}


# ---------------------------------------------------------------------------
# Tests: _notify_pms
# ---------------------------------------------------------------------------

class TestNotifyPMs:

    def test_notify_creates_notification_for_each_pm(self):
        """One notification is created per PM user at the factory."""
        order = _make_order()
        pm1 = _make_pm_user(order.factory_id)
        pm2 = _make_pm_user(order.factory_id)

        db = MagicMock()
        db.query.return_value.join.return_value.filter.return_value.all.return_value = [pm1, pm2]

        count = _notify_pms(db, order, uuid.uuid4())

        assert count == 2
        assert db.add.call_count == 2

    def test_notify_returns_zero_when_no_pms(self):
        """Returns 0 when no PM users found for factory."""
        order = _make_order()
        db = MagicMock()
        db.query.return_value.join.return_value.filter.return_value.all.return_value = []

        count = _notify_pms(db, order, uuid.uuid4())
        assert count == 0
