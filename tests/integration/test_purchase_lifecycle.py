"""
Integration tests for Purchase Lifecycle service.
business/services/purchaser_lifecycle.py
business/services/purchase_consolidation.py

Tests:
- PR status transitions: pending->approved->sent->in_transit->received->closed
- Auto-transition on material receipt (on_material_received)
- Lead time EMA calculation (update_supplier_lead_time)
- Overdue detection (get_overdue_requests, check_and_notify_overdue)
- Consolidation: find_consolidation_candidates, consolidate_purchase_requests
All database interactions are mocked with unittest.mock.
"""
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch, call, PropertyMock
import unittest


# ---------------------------------------------------------------------------
# Mock builders
# ---------------------------------------------------------------------------

def _mock_pr(pr_id=None, factory_id=None, supplier_id=None,
             status="sent", materials_json=None,
             ordered_at=None, expected_delivery_date=None,
             actual_delivery_date=None, created_at=None,
             notes=None, source=None, approved_by=None):
    pr = MagicMock()
    pr.id = pr_id or uuid.uuid4()
    pr.factory_id = factory_id or uuid.uuid4()
    pr.supplier_id = supplier_id or uuid.uuid4()
    pr.status = status
    pr.materials_json = materials_json or [
        {"material_id": str(uuid.uuid4()), "quantity": 10.0, "material_name": "Red Pigment"}
    ]
    pr.ordered_at = ordered_at or (date.today() - timedelta(days=10))
    pr.expected_delivery_date = expected_delivery_date or (date.today() + timedelta(days=5))
    pr.actual_delivery_date = actual_delivery_date
    pr.created_at = created_at or datetime.now(timezone.utc)
    pr.updated_at = None
    pr.notes = notes
    pr.source = source
    pr.approved_by = approved_by
    return pr


def _mock_supplier_lead_time(supplier_id=None, material_type="pigment",
                              default_lead_time_days=14,
                              avg_actual_lead_time_days=Decimal("12.5"),
                              sample_count=5):
    slt = MagicMock()
    slt.supplier_id = supplier_id or uuid.uuid4()
    slt.material_type = material_type
    slt.default_lead_time_days = default_lead_time_days
    slt.avg_actual_lead_time_days = avg_actual_lead_time_days
    slt.sample_count = sample_count
    slt.last_updated = datetime.now(timezone.utc)
    return slt


def _mock_material(material_id=None, name="Red Pigment", material_type="pigment"):
    m = MagicMock()
    m.id = material_id or uuid.uuid4()
    m.name = name
    m.material_type = material_type
    return m


# ---------------------------------------------------------------------------
# Tests: on_material_received
# ---------------------------------------------------------------------------

class TestOnMaterialReceived(unittest.TestCase):
    """Tests for on_material_received — auto-transition on warehouse receipt."""

    @patch("business.services.purchaser_lifecycle._notify_pm_material_received")
    @patch("business.services.purchaser_lifecycle._notify_on_received")
    @patch("business.services.purchaser_lifecycle._update_supplier_lead_time_internal")
    def test_transitions_matching_pr_to_received(
        self, mock_lead, mock_notify_recv, mock_notify_pm
    ):
        """Matching PR transitions from sent -> received."""
        from business.services.purchaser_lifecycle import on_material_received
        from api.enums import PurchaseStatus

        db = MagicMock()
        mat_id = uuid.uuid4()
        supplier_id = uuid.uuid4()
        factory_id = uuid.uuid4()

        pr = _mock_pr(
            factory_id=factory_id,
            supplier_id=supplier_id,
            status=PurchaseStatus.SENT.value,
            materials_json=[{"material_id": str(mat_id), "quantity": 10}],
            ordered_at=date.today() - timedelta(days=7),
        )
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [pr]

        result = on_material_received(
            db, mat_id, supplier_id, factory_id, Decimal("10.0"),
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["new_status"], "received")
        self.assertEqual(pr.status, PurchaseStatus.RECEIVED.value)
        db.flush.assert_called_once()

    @patch("business.services.purchaser_lifecycle._notify_pm_material_received")
    @patch("business.services.purchaser_lifecycle._notify_on_received")
    @patch("business.services.purchaser_lifecycle._update_supplier_lead_time_internal")
    def test_in_transit_pr_also_transitions(
        self, mock_lead, mock_notify, mock_pm
    ):
        """PR in IN_TRANSIT status also transitions to received."""
        from business.services.purchaser_lifecycle import on_material_received
        from api.enums import PurchaseStatus

        db = MagicMock()
        mat_id = uuid.uuid4()
        pr = _mock_pr(
            status=PurchaseStatus.IN_TRANSIT.value,
            materials_json=[{"material_id": str(mat_id)}],
        )
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [pr]

        result = on_material_received(db, mat_id, None, pr.factory_id, Decimal("5"))

        self.assertEqual(len(result), 1)
        self.assertEqual(pr.status, PurchaseStatus.RECEIVED.value)

    def test_no_matching_pr_returns_empty(self):
        """No matching PR -> empty list, no flush."""
        from business.services.purchaser_lifecycle import on_material_received

        db = MagicMock()
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        result = on_material_received(db, uuid.uuid4(), None, uuid.uuid4(), Decimal("1"))

        self.assertEqual(result, [])
        db.flush.assert_not_called()

    @patch("business.services.purchaser_lifecycle._notify_pm_material_received")
    @patch("business.services.purchaser_lifecycle._notify_on_received")
    @patch("business.services.purchaser_lifecycle._update_supplier_lead_time_internal")
    def test_only_matches_first_pr_fifo(self, mock_lead, mock_notify, mock_pm):
        """Only the first (oldest) matching PR is transitioned (FIFO)."""
        from business.services.purchaser_lifecycle import on_material_received
        from api.enums import PurchaseStatus

        db = MagicMock()
        mat_id = uuid.uuid4()
        pr1 = _mock_pr(
            status=PurchaseStatus.SENT.value,
            materials_json=[{"material_id": str(mat_id)}],
        )
        pr2 = _mock_pr(
            status=PurchaseStatus.SENT.value,
            materials_json=[{"material_id": str(mat_id)}],
        )
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [pr1, pr2]

        result = on_material_received(db, mat_id, None, pr1.factory_id, Decimal("10"))

        self.assertEqual(len(result), 1)
        self.assertEqual(pr1.status, PurchaseStatus.RECEIVED.value)
        # pr2 should not be transitioned
        self.assertNotEqual(pr2.status, PurchaseStatus.RECEIVED.value)


# ---------------------------------------------------------------------------
# Tests: _pr_contains_material
# ---------------------------------------------------------------------------

class TestPrContainsMaterial(unittest.TestCase):
    """Tests for _pr_contains_material."""

    def test_list_format_matches(self):
        from business.services.purchaser_lifecycle import _pr_contains_material

        mat_id = uuid.uuid4()
        pr = MagicMock()
        pr.materials_json = [{"material_id": str(mat_id), "quantity": 5}]

        self.assertTrue(_pr_contains_material(pr, str(mat_id)))

    def test_dict_format_with_items_matches(self):
        from business.services.purchaser_lifecycle import _pr_contains_material

        mat_id = uuid.uuid4()
        pr = MagicMock()
        pr.materials_json = {"items": [{"material_id": str(mat_id)}]}

        self.assertTrue(_pr_contains_material(pr, str(mat_id)))

    def test_single_dict_format_matches(self):
        from business.services.purchaser_lifecycle import _pr_contains_material

        mat_id = uuid.uuid4()
        pr = MagicMock()
        pr.materials_json = {"material_id": str(mat_id)}

        self.assertTrue(_pr_contains_material(pr, str(mat_id)))

    def test_no_match_returns_false(self):
        from business.services.purchaser_lifecycle import _pr_contains_material

        pr = MagicMock()
        pr.materials_json = [{"material_id": str(uuid.uuid4())}]

        self.assertFalse(_pr_contains_material(pr, str(uuid.uuid4())))

    def test_empty_materials_returns_false(self):
        from business.services.purchaser_lifecycle import _pr_contains_material

        pr = MagicMock()
        pr.materials_json = None

        self.assertFalse(_pr_contains_material(pr, str(uuid.uuid4())))


# ---------------------------------------------------------------------------
# Tests: _calculate_lead_time
# ---------------------------------------------------------------------------

class TestCalculateLeadTime(unittest.TestCase):
    """Tests for _calculate_lead_time."""

    def test_calculates_actual_and_variance(self):
        from business.services.purchaser_lifecycle import _calculate_lead_time

        pr = MagicMock()
        pr.ordered_at = date(2026, 3, 1)
        pr.expected_delivery_date = date(2026, 3, 15)

        received = date(2026, 3, 12)
        result = _calculate_lead_time(pr, received)

        self.assertEqual(result["actual_days"], 11)
        self.assertEqual(result["expected_days"], 14)
        self.assertEqual(result["variance_days"], -3)  # 3 days early

    def test_late_delivery_positive_variance(self):
        from business.services.purchaser_lifecycle import _calculate_lead_time

        pr = MagicMock()
        pr.ordered_at = date(2026, 3, 1)
        pr.expected_delivery_date = date(2026, 3, 10)

        received = date(2026, 3, 15)
        result = _calculate_lead_time(pr, received)

        self.assertEqual(result["variance_days"], 5)  # 5 days late

    def test_no_ordered_at_returns_none_values(self):
        from business.services.purchaser_lifecycle import _calculate_lead_time

        pr = MagicMock()
        pr.ordered_at = None

        result = _calculate_lead_time(pr, date.today())

        self.assertIsNone(result["actual_days"])
        self.assertIsNone(result["variance_days"])


# ---------------------------------------------------------------------------
# Tests: update_supplier_lead_time (EMA)
# ---------------------------------------------------------------------------

class TestUpdateSupplierLeadTime(unittest.TestCase):
    """Tests for update_supplier_lead_time — EMA calculation."""

    def test_first_observation_sets_avg_to_actual(self):
        """First observation: avg = actual_days."""
        from business.services.purchaser_lifecycle import update_supplier_lead_time

        db = MagicMock()
        mat = _mock_material(material_type="pigment")
        db.query.return_value.filter.return_value.first.side_effect = [
            mat,   # Material lookup
            None,  # No existing SupplierLeadTime
        ]

        supplier_id = uuid.uuid4()
        result = update_supplier_lead_time(db, supplier_id, mat.id, 10)

        self.assertIsNotNone(result)
        db.add.assert_called_once()

    def test_ema_updates_existing_record(self):
        """Existing record: EMA weighted average is applied."""
        from business.services.purchaser_lifecycle import update_supplier_lead_time

        db = MagicMock()
        mat = _mock_material(material_type="pigment")
        slt = _mock_supplier_lead_time(
            avg_actual_lead_time_days=Decimal("12.0"),
            sample_count=5,
        )
        db.query.return_value.filter.return_value.first.side_effect = [mat, slt]

        result = update_supplier_lead_time(db, slt.supplier_id, mat.id, 18)

        # EMA: old=12.0, weight=min(5,20)=5, new_avg=(12*5+18)/(5+1)=13.0
        expected_avg = (12.0 * 5 + 18) / 6
        self.assertIsNotNone(result)
        self.assertAlmostEqual(
            float(slt.avg_actual_lead_time_days),
            round(expected_avg, 1),
            places=1,
        )

    def test_ema_weight_capped_at_20(self):
        """Sample count > 20: weight is capped at 20 for EMA smoothing."""
        from business.services.purchaser_lifecycle import update_supplier_lead_time

        db = MagicMock()
        mat = _mock_material()
        slt = _mock_supplier_lead_time(
            avg_actual_lead_time_days=Decimal("15.0"),
            sample_count=50,  # > 20
        )
        db.query.return_value.filter.return_value.first.side_effect = [mat, slt]

        update_supplier_lead_time(db, slt.supplier_id, mat.id, 10)

        # weight = min(50, 20) = 20 -> new_avg = (15*20+10)/21
        expected = (15.0 * 20 + 10) / 21
        self.assertAlmostEqual(
            float(slt.avg_actual_lead_time_days),
            round(expected, 1),
            places=1,
        )

    def test_material_not_found_returns_none(self):
        """Unknown material -> returns None."""
        from business.services.purchaser_lifecycle import update_supplier_lead_time

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        result = update_supplier_lead_time(db, uuid.uuid4(), uuid.uuid4(), 7)
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# Tests: get_overdue_requests
# ---------------------------------------------------------------------------

class TestGetOverdueRequests(unittest.TestCase):
    """Tests for get_overdue_requests."""

    def test_returns_overdue_prs(self):
        from business.services.purchaser_lifecycle import get_overdue_requests

        db = MagicMock()
        pr = _mock_pr(
            status="sent",
            expected_delivery_date=date.today() - timedelta(days=3),
        )
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [pr]

        result = get_overdue_requests(db)
        self.assertEqual(len(result), 1)

    def test_filters_by_factory_id(self):
        from business.services.purchaser_lifecycle import get_overdue_requests

        db = MagicMock()
        factory_id = uuid.uuid4()
        db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.all.return_value = []

        result = get_overdue_requests(db, factory_id=factory_id)
        self.assertEqual(result, [])


class TestCheckAndNotifyOverdue(unittest.TestCase):
    """Tests for check_and_notify_overdue."""

    @patch("business.services.purchaser_lifecycle._notify_overdue")
    @patch("business.services.purchaser_lifecycle.get_overdue_requests")
    def test_notifies_for_each_overdue(self, mock_get, mock_notify):
        from business.services.purchaser_lifecycle import check_and_notify_overdue

        pr1 = _mock_pr(expected_delivery_date=date.today() - timedelta(days=2))
        pr2 = _mock_pr(expected_delivery_date=date.today() - timedelta(days=5))
        mock_get.return_value = [pr1, pr2]

        db = MagicMock()
        count = check_and_notify_overdue(db)

        self.assertEqual(count, 2)
        self.assertEqual(mock_notify.call_count, 2)

    @patch("business.services.purchaser_lifecycle.get_overdue_requests")
    def test_no_overdue_returns_zero(self, mock_get):
        from business.services.purchaser_lifecycle import check_and_notify_overdue

        mock_get.return_value = []
        db = MagicMock()

        count = check_and_notify_overdue(db)
        self.assertEqual(count, 0)


# ---------------------------------------------------------------------------
# Tests: find_consolidation_candidates (purchase_consolidation.py)
# ---------------------------------------------------------------------------

class TestFindConsolidationCandidates(unittest.TestCase):
    """Tests for find_consolidation_candidates."""

    @patch("business.services.purchase_consolidation._get_approved_prs")
    def test_no_approved_prs_returns_empty(self, mock_prs):
        from business.services.purchase_consolidation import find_consolidation_candidates

        mock_prs.return_value = []
        db = MagicMock()

        result = find_consolidation_candidates(db, uuid.uuid4())
        self.assertEqual(result, [])

    @patch("business.services.purchase_consolidation._get_approved_prs")
    def test_single_pr_per_supplier_not_suggested(self, mock_prs):
        """Only 1 PR per supplier -> no consolidation suggestion."""
        from business.services.purchase_consolidation import find_consolidation_candidates

        pr = _mock_pr(status="approved")
        mock_prs.return_value = [pr]

        db = MagicMock()
        result = find_consolidation_candidates(db, uuid.uuid4())
        self.assertEqual(result, [])

    @patch("business.services.purchase_consolidation._get_approved_prs")
    def test_two_prs_same_supplier_creates_candidate(self, mock_prs):
        """2+ PRs with same supplier -> consolidation candidate."""
        from business.services.purchase_consolidation import find_consolidation_candidates

        supplier_id = uuid.uuid4()
        mat_id = str(uuid.uuid4())
        pr1 = _mock_pr(
            status="approved", supplier_id=supplier_id,
            materials_json=[{"material_id": mat_id, "quantity": 5, "name": "Stone"}],
        )
        pr2 = _mock_pr(
            status="approved", supplier_id=supplier_id,
            materials_json=[{"material_id": mat_id, "quantity": 3, "name": "Stone"}],
        )
        mock_prs.return_value = [pr1, pr2]

        db = MagicMock()
        sup = MagicMock()
        sup.name = "StoneSupplier"
        db.query.return_value.filter.return_value.first.return_value = sup

        result = find_consolidation_candidates(db, uuid.uuid4())

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["pr_count"], 2)
        # Combined quantity should be 5+3=8
        total = sum(m["quantity"] for m in result[0]["combined_materials"])
        self.assertEqual(total, 8.0)


# ---------------------------------------------------------------------------
# Tests: consolidate_purchase_requests (purchase_consolidation.py)
# ---------------------------------------------------------------------------

class TestConsolidatePurchaseRequests(unittest.TestCase):
    """Tests for consolidate_purchase_requests."""

    def test_fewer_than_2_prs_raises_error(self):
        from business.services.purchase_consolidation import consolidate_purchase_requests

        db = MagicMock()
        with self.assertRaises(ValueError):
            consolidate_purchase_requests(db, [uuid.uuid4()], uuid.uuid4())

    def test_missing_prs_raises_error(self):
        from business.services.purchase_consolidation import consolidate_purchase_requests

        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []

        with self.assertRaises(ValueError) as ctx:
            consolidate_purchase_requests(
                db, [uuid.uuid4(), uuid.uuid4()], uuid.uuid4(),
            )
        self.assertIn("not found", str(ctx.exception))

    def test_non_approved_pr_raises_error(self):
        from business.services.purchase_consolidation import consolidate_purchase_requests

        db = MagicMock()
        factory_id = uuid.uuid4()
        supplier_id = uuid.uuid4()

        pr1 = _mock_pr(status="approved", factory_id=factory_id, supplier_id=supplier_id)
        pr2 = _mock_pr(status="sent", factory_id=factory_id, supplier_id=supplier_id)
        db.query.return_value.filter.return_value.all.return_value = [pr1, pr2]

        with self.assertRaises(ValueError) as ctx:
            consolidate_purchase_requests(db, [pr1.id, pr2.id], uuid.uuid4())
        self.assertIn("approved", str(ctx.exception))

    def test_different_factories_raises_error(self):
        from business.services.purchase_consolidation import consolidate_purchase_requests

        db = MagicMock()
        pr1 = _mock_pr(status="approved", factory_id=uuid.uuid4())
        pr2 = _mock_pr(status="approved", factory_id=uuid.uuid4())
        db.query.return_value.filter.return_value.all.return_value = [pr1, pr2]

        with self.assertRaises(ValueError) as ctx:
            consolidate_purchase_requests(db, [pr1.id, pr2.id], uuid.uuid4())
        self.assertIn("same factory", str(ctx.exception))

    def test_different_suppliers_raises_error(self):
        from business.services.purchase_consolidation import consolidate_purchase_requests

        db = MagicMock()
        factory_id = uuid.uuid4()
        pr1 = _mock_pr(status="approved", factory_id=factory_id, supplier_id=uuid.uuid4())
        pr2 = _mock_pr(status="approved", factory_id=factory_id, supplier_id=uuid.uuid4())
        db.query.return_value.filter.return_value.all.return_value = [pr1, pr2]

        with self.assertRaises(ValueError) as ctx:
            consolidate_purchase_requests(db, [pr1.id, pr2.id], uuid.uuid4())
        self.assertIn("same supplier", str(ctx.exception))

    def test_successful_consolidation(self):
        """Valid consolidation: creates new PR, closes originals."""
        from business.services.purchase_consolidation import consolidate_purchase_requests
        from api.enums import PurchaseStatus

        db = MagicMock()
        factory_id = uuid.uuid4()
        supplier_id = uuid.uuid4()
        mat_id = str(uuid.uuid4())

        pr1 = _mock_pr(
            status="approved", factory_id=factory_id, supplier_id=supplier_id,
            materials_json=[{"material_id": mat_id, "quantity": 5}],
        )
        pr2 = _mock_pr(
            status="approved", factory_id=factory_id, supplier_id=supplier_id,
            materials_json=[{"material_id": mat_id, "quantity": 3}],
        )
        db.query.return_value.filter.return_value.all.return_value = [pr1, pr2]

        result = consolidate_purchase_requests(
            db, [pr1.id, pr2.id], uuid.uuid4(),
        )

        self.assertEqual(result["source_count"], 2)
        self.assertEqual(result["materials_count"], 1)
        # Original PRs should be closed
        self.assertEqual(pr1.status, PurchaseStatus.CLOSED.value)
        self.assertEqual(pr2.status, PurchaseStatus.CLOSED.value)
        # New consolidated PR should be added
        db.add.assert_called()


# ---------------------------------------------------------------------------
# Tests: compute_enhanced_stats
# ---------------------------------------------------------------------------

class TestComputeEnhancedStats(unittest.TestCase):
    """Tests for compute_enhanced_stats."""

    def test_returns_expected_keys(self):
        from business.services.purchaser_lifecycle import compute_enhanced_stats

        db = MagicMock()
        db.query.return_value.filter.return_value.count.return_value = 0
        db.query.return_value.filter.return_value.all.return_value = []

        result = compute_enhanced_stats(db)

        self.assertIn("overdue_count", result)
        self.assertIn("avg_lead_time_days", result)
        self.assertIn("on_time_pct", result)
        self.assertIn("completed_this_month", result)

    def test_no_completions_returns_none_for_avg(self):
        from business.services.purchaser_lifecycle import compute_enhanced_stats

        db = MagicMock()
        db.query.return_value.filter.return_value.count.return_value = 3
        db.query.return_value.filter.return_value.all.return_value = []

        result = compute_enhanced_stats(db)

        self.assertIsNone(result["avg_lead_time_days"])
        self.assertIsNone(result["on_time_pct"])


if __name__ == "__main__":
    unittest.main()
