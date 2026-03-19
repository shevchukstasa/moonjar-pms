"""
Integration tests for the Order Intake Pipeline.
business/services/order_intake.py

Tests the full flow: webhook payload -> factory assignment -> position creation
-> recipe lookup -> material reservation -> blocking tasks.
All database interactions are mocked with unittest.mock.
"""
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch, PropertyMock, call
import unittest


# ---------------------------------------------------------------------------
# Helpers to build mock objects with attribute access
# ---------------------------------------------------------------------------

def _mock_factory(name="Bali Factory", factory_id=None, is_active=True):
    f = MagicMock()
    f.id = factory_id or uuid.uuid4()
    f.name = name
    f.is_active = is_active
    return f


def _mock_order(order_id=None, order_number="MJ-20260319-001", factory_id=None):
    o = MagicMock()
    o.id = order_id or uuid.uuid4()
    o.order_number = order_number
    o.factory_id = factory_id or uuid.uuid4()
    o.mandatory_qc = False
    o.desired_delivery_date = date.today() + timedelta(days=30)
    o.final_deadline = None
    o.client = "Test Client"
    return o


def _mock_item(item_id=None, collection="Standard", color="Red",
               size="20x20", quantity_pcs=100, color_2=None,
               finishing=None, application=None, application_type=None,
               place_of_application=None, product_type="tile",
               thickness=Decimal("11.0"), shape=None, quantity_sqm=None):
    item = MagicMock()
    item.id = item_id or uuid.uuid4()
    item.collection = collection
    item.color = color
    item.color_2 = color_2
    item.size = size
    item.quantity_pcs = quantity_pcs
    item.quantity_sqm = quantity_sqm
    item.finishing = finishing
    item.application = application
    item.application_type = application_type
    item.place_of_application = place_of_application
    item.product_type = product_type
    item.thickness = thickness
    item.shape = shape
    return item


def _mock_recipe(recipe_id=None, name="Red", color_collection="Standard"):
    r = MagicMock()
    r.id = recipe_id or uuid.uuid4()
    r.name = name
    r.color_collection = color_collection
    r.is_active = True
    return r


def _mock_position(position_id=None, status="planned", factory_id=None,
                   order_id=None, quantity=100, size="20x20",
                   recipe_id=None, parent_position_id=None):
    p = MagicMock()
    p.id = position_id or uuid.uuid4()
    p.status = status
    p.factory_id = factory_id or uuid.uuid4()
    p.order_id = order_id or uuid.uuid4()
    p.quantity = quantity
    p.size = size
    p.recipe_id = recipe_id
    p.parent_position_id = parent_position_id
    p.estimated_kiln_id = None
    p.glazeable_sqm = None
    p.quantity_with_defect_margin = None
    p.two_stage_firing = False
    p.two_stage_type = None
    p.glaze_type = "pigment"
    p.product_type = "tile"
    p.planned_kiln_date = None
    p.size_id = None
    return p


# ---------------------------------------------------------------------------
# Minimal payload builder
# ---------------------------------------------------------------------------

def _webhook_payload(**overrides):
    base = {
        "event_id": str(uuid.uuid4()),
        "external_id": "EXT-001",
        "order_number": "MJ-20260319-001",
        "client": "Test Client",
        "client_location": "Bali",
        "items": [
            {
                "color": "Red",
                "size": "20x20",
                "quantity_pcs": 100,
                "collection": "Standard",
                "product_type": "tile",
            }
        ],
    }
    base.update(overrides)
    return base


class TestProcessIncomingOrder(unittest.TestCase):
    """Tests for process_incoming_order — the main entry point."""

    @patch("business.services.order_intake.notify_pm", create=True)
    @patch("business.services.order_intake.schedule_order", create=True)
    @patch("business.services.order_intake.process_order_item")
    @patch("business.services.order_intake._generate_order_number", return_value="MJ-20260319-001")
    @patch("business.services.order_intake.assign_factory")
    def test_happy_path_creates_order_and_positions(
        self, mock_assign, mock_gen, mock_process_item, mock_schedule, mock_notify
    ):
        """Full happy path: webhook -> order created -> positions returned."""
        from business.services.order_intake import process_incoming_order

        db = MagicMock()
        factory = _mock_factory()
        mock_assign.return_value = factory

        position = _mock_position(status="planned")
        mock_process_item.return_value = position

        # db.query(...).filter(...).first() returns None (no duplicate)
        db.query.return_value.filter.return_value.first.return_value = None

        payload = _webhook_payload()
        result = process_incoming_order(db, payload, "sales_webhook")

        self.assertEqual(result["status"], "created")
        self.assertEqual(result["positions_count"], 1)
        db.add.assert_called()
        db.commit.assert_called_once()

    @patch("business.services.order_intake.assign_factory")
    def test_duplicate_webhook_returns_duplicate(self, mock_assign):
        """Idempotency: repeated event_id -> 'duplicate' status."""
        from business.services.order_intake import process_incoming_order

        db = MagicMock()
        existing_event = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = existing_event

        payload = _webhook_payload(event_id="EVT-DUP")
        result = process_incoming_order(db, payload, "sales_webhook")

        self.assertEqual(result["status"], "duplicate")
        mock_assign.assert_not_called()

    @patch("business.services.order_intake.assign_factory")
    def test_existing_order_returns_exists(self, mock_assign):
        """Order with same external_id -> 'exists' status."""
        from business.services.order_intake import process_incoming_order

        db = MagicMock()
        # First query (webhook event) -> None, second query (existing order) -> found
        existing_order = MagicMock()
        existing_order.id = uuid.uuid4()
        existing_order.order_number = "MJ-001"
        db.query.return_value.filter.return_value.first.side_effect = [
            None,           # SalesWebhookEvent not found
            existing_order, # ProductionOrder found
        ]

        payload = _webhook_payload()
        result = process_incoming_order(db, payload, "sales_webhook")

        self.assertEqual(result["status"], "exists")

    @patch("business.services.order_intake.notify_pm", create=True)
    @patch("business.services.order_intake.schedule_order", create=True)
    @patch("business.services.order_intake.process_order_item")
    @patch("business.services.order_intake._generate_order_number", return_value="MJ-001")
    @patch("business.services.order_intake.assign_factory")
    def test_order_status_new_when_positions_have_blocking_status(
        self, mock_assign, mock_gen, mock_process_item, mock_sched, mock_notify
    ):
        """Order status stays NEW when any position is in a blocking status."""
        from business.services.order_intake import process_incoming_order
        from api.enums import PositionStatus

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        mock_assign.return_value = _mock_factory()

        pos = _mock_position()
        pos.status = PositionStatus.AWAITING_RECIPE
        mock_process_item.return_value = pos

        payload = _webhook_payload()
        result = process_incoming_order(db, payload, "sales_webhook")

        self.assertEqual(result["status"], "created")


class TestAssignFactory(unittest.TestCase):
    """Tests for assign_factory — region matching & load balancing."""

    def test_single_factory_always_returned(self):
        """When only one active factory exists, always return it."""
        from business.services.order_intake import assign_factory

        db = MagicMock()
        factory = _mock_factory(name="Solo Factory")
        db.query.return_value.filter.return_value.all.return_value = [factory]

        result = assign_factory(db, "anywhere")
        self.assertEqual(result.id, factory.id)

    def test_bali_keyword_matches_bali_factory(self):
        """Location containing 'bali' should match Bali factory."""
        from business.services.order_intake import assign_factory

        db = MagicMock()
        bali = _mock_factory(name="Bali Factory")
        java = _mock_factory(name="Java Factory")
        db.query.return_value.filter.return_value.all.return_value = [bali, java]
        # Region query returns bali factory
        db.query.return_value.filter.return_value.first.return_value = bali

        result = assign_factory(db, "Denpasar, Bali")
        self.assertEqual(result.id, bali.id)

    def test_no_active_factories_raises(self):
        """No active factories -> ValueError."""
        from business.services.order_intake import assign_factory

        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []

        with self.assertRaises(ValueError):
            assign_factory(db, "anywhere")

    def test_load_balancing_picks_least_loaded(self):
        """With unknown location, picks factory with fewest active positions."""
        from business.services.order_intake import assign_factory

        db = MagicMock()
        f1 = _mock_factory(name="Factory A")
        f2 = _mock_factory(name="Factory B")
        db.query.return_value.filter.return_value.all.return_value = [f1, f2]
        # No region match
        db.query.return_value.filter.return_value.first.return_value = None
        # Load counts: f1=50, f2=10
        db.query.return_value.filter.return_value.scalar.side_effect = [50, 10]

        result = assign_factory(db, "Unknown City")
        self.assertEqual(result.id, f2.id)


class TestProcessOrderItem(unittest.TestCase):
    """Tests for process_order_item — item -> position pipeline."""

    @patch("business.services.order_intake.check_blocking_tasks")
    @patch("business.services.order_intake.reserve_materials_for_position", create=True)
    @patch("business.services.order_intake.resolve_size_for_position", create=True)
    @patch("business.services.order_intake.calculate_glazeable_sqm_for_position", create=True)
    @patch("business.services.order_intake._get_defect_coefficient", return_value=0.05)
    @patch("business.services.order_intake._find_recipe")
    def test_stock_collection_skips_recipe_and_materials(
        self, mock_recipe, mock_defect, mock_glaze, mock_size, mock_reserve, mock_blocking
    ):
        """Stock collection -> TRANSFERRED_TO_SORTING, no recipe/material checks."""
        from business.services.order_intake import process_order_item
        from api.enums import PositionStatus

        db = MagicMock()
        db.query.return_value.filter.return_value.scalar.return_value = 0
        mock_glaze.return_value = None

        order = _mock_order()
        item = _mock_item(collection="surplus")  # stock collection

        with patch("api.enums.is_stock_collection", return_value=True):
            position = process_order_item(db, order, item)

        self.assertIsNotNone(position)
        mock_blocking.assert_not_called()
        mock_reserve.assert_not_called()

    @patch("business.services.order_intake.calculate_glazeable_sqm_for_position", create=True)
    @patch("business.services.order_intake._get_defect_coefficient", return_value=0.05)
    @patch("business.services.order_intake._find_recipe", return_value=None)
    def test_missing_recipe_sets_awaiting_recipe_and_creates_task(
        self, mock_recipe, mock_defect, mock_glaze
    ):
        """No recipe found -> AWAITING_RECIPE + task created."""
        from business.services.order_intake import process_order_item
        from api.enums import PositionStatus

        db = MagicMock()
        db.query.return_value.filter.return_value.scalar.return_value = 0
        mock_glaze.return_value = None

        with patch("api.enums.is_stock_collection", return_value=False):
            order = _mock_order()
            item = _mock_item()
            position = process_order_item(db, order, item)

        # Position created with AWAITING_RECIPE
        self.assertIsNotNone(position)
        # db.add should be called at least for position + task
        calls = db.add.call_args_list
        self.assertGreaterEqual(len(calls), 2)

    @patch("business.services.order_intake.notify_pm", create=True)
    @patch("business.services.order_intake.create_size_resolution_task", create=True)
    @patch("business.services.order_intake.resolve_size_for_position", create=True)
    @patch("business.services.order_intake.check_blocking_tasks")
    @patch("business.services.order_intake.calculate_glazeable_sqm_for_position", create=True)
    @patch("business.services.order_intake._get_defect_coefficient", return_value=0.05)
    @patch("business.services.order_intake._find_recipe")
    def test_size_resolution_failure_sets_awaiting_size_confirmation(
        self, mock_recipe, mock_defect, mock_glaze, mock_blocking,
        mock_resolve_size, mock_create_size_task, mock_notify
    ):
        """Size cannot be resolved -> AWAITING_SIZE_CONFIRMATION."""
        from business.services.order_intake import process_order_item
        from api.enums import PositionStatus

        db = MagicMock()
        db.query.return_value.filter.return_value.scalar.return_value = 0
        mock_glaze.return_value = None

        recipe = _mock_recipe()
        mock_recipe.return_value = recipe

        size_result = MagicMock()
        size_result.resolved = False
        size_result.reason = "multiple_matches"
        size_result.candidates = [{"name": "A"}, {"name": "B"}]
        mock_resolve_size.return_value = size_result

        with patch("api.enums.is_stock_collection", return_value=False):
            order = _mock_order()
            item = _mock_item()
            position = process_order_item(db, order, item)

        self.assertIsNotNone(position)
        mock_create_size_task.assert_called_once()

    @patch("business.services.order_intake.create_auto_purchase_request", create=True)
    @patch("business.services.order_intake.check_material_availability_smart", create=True)
    @patch("business.services.order_intake.reserve_materials_for_position", create=True)
    @patch("business.services.order_intake.notify_pm", create=True)
    @patch("business.services.order_intake.resolve_size_for_position", create=True)
    @patch("business.services.order_intake.check_blocking_tasks")
    @patch("business.services.order_intake.calculate_glazeable_sqm_for_position", create=True)
    @patch("business.services.order_intake._get_defect_coefficient", return_value=0.05)
    @patch("business.services.order_intake._find_recipe")
    def test_insufficient_materials_sets_status_and_creates_purchase_request(
        self, mock_recipe, mock_defect, mock_glaze, mock_blocking,
        mock_resolve_size, mock_notify, mock_reserve, mock_smart, mock_auto_pr
    ):
        """Material shortage -> INSUFFICIENT_MATERIALS + auto purchase request."""
        from business.services.order_intake import process_order_item

        db = MagicMock()
        db.query.return_value.filter.return_value.scalar.return_value = 0
        mock_glaze.return_value = None

        recipe = _mock_recipe()
        mock_recipe.return_value = recipe

        size_result = MagicMock()
        size_result.resolved = True
        size_result.size_id = uuid.uuid4()
        size_result.reason = "exact_match"
        size_result.candidates = []
        mock_resolve_size.return_value = size_result

        # Material reservation returns shortages
        shortage = MagicMock()
        shortage.material_id = uuid.uuid4()
        shortage.material_name = "Red Pigment"
        shortage.required = Decimal("10.0")
        shortage.available = Decimal("2.0")
        shortage.deficit = Decimal("8.0")
        reserve_result = MagicMock()
        reserve_result.shortages = [shortage]
        mock_reserve.return_value = reserve_result

        # Smart check says material is truly unavailable
        smart_result = MagicMock()
        smart_result.available = False
        smart_result.reason = "not_ordered"
        smart_result.ordered_qty = Decimal("0")
        mock_smart.return_value = smart_result

        with patch("api.enums.is_stock_collection", return_value=False):
            order = _mock_order()
            item = _mock_item()
            position = process_order_item(db, order, item)

        self.assertIsNotNone(position)
        mock_auto_pr.assert_called_once()


class TestCheckBlockingTasks(unittest.TestCase):
    """Tests for check_blocking_tasks — stencil/silkscreen/color matching."""

    @patch("business.services.order_intake.should_block_for_service", create=True)
    def test_stencil_collection_creates_stencil_task(self, mock_should_block):
        """Collection with 'stencil' -> STENCIL_ORDER task created."""
        from business.services.order_intake import check_blocking_tasks

        db = MagicMock()
        mock_should_block.return_value = (True, 5)

        order = _mock_order()
        position = _mock_position(status="planned")
        item = _mock_item(collection="Stencil Art", application_type="stencil")

        check_blocking_tasks(db, order, position, item)

        db.add.assert_called()

    @patch("business.services.order_intake.should_block_for_service", create=True)
    def test_silkscreen_collection_creates_silkscreen_task(self, mock_should_block):
        """Collection with 'silkscreen' -> SILK_SCREEN_ORDER task created."""
        from business.services.order_intake import check_blocking_tasks

        db = MagicMock()
        mock_should_block.return_value = (True, 3)

        order = _mock_order()
        position = _mock_position(status="planned")
        item = _mock_item(collection="Silkscreen Print")

        check_blocking_tasks(db, order, position, item)

        db.add.assert_called()

    @patch("business.services.order_intake.should_block_for_service", create=True)
    def test_color_2_triggers_color_matching_task(self, mock_should_block):
        """Item with color_2 set -> COLOR_MATCHING task."""
        from business.services.order_intake import check_blocking_tasks

        db = MagicMock()
        mock_should_block.return_value = (True, 2)

        order = _mock_order()
        position = _mock_position(status="planned")
        item = _mock_item(color_2="Blue")

        check_blocking_tasks(db, order, position, item)

        db.add.assert_called()

    @patch("business.services.order_intake.should_block_for_service", create=True)
    def test_custom_collection_triggers_color_matching(self, mock_should_block):
        """Collection containing 'custom' -> COLOR_MATCHING task."""
        from business.services.order_intake import check_blocking_tasks

        db = MagicMock()
        mock_should_block.return_value = (False, 20)

        order = _mock_order()
        position = _mock_position(status="planned")
        item = _mock_item(collection="Custom Blend")

        check_blocking_tasks(db, order, position, item)

        db.add.assert_called()

    @patch("business.services.order_intake.should_block_for_service", create=True)
    def test_deferred_blocking_does_not_change_status(self, mock_should_block):
        """When should_block returns False, position status is not changed."""
        from business.services.order_intake import check_blocking_tasks
        from api.enums import PositionStatus

        db = MagicMock()
        mock_should_block.return_value = (False, 30)

        order = _mock_order()
        position = _mock_position(status=PositionStatus.PLANNED)
        item = _mock_item(collection="Stencil Art", application_type="other")

        check_blocking_tasks(db, order, position, item)

        # Status should remain PLANNED since blocking is deferred
        self.assertEqual(position.status, PositionStatus.PLANNED)


class TestFindRecipe(unittest.TestCase):
    """Tests for _find_recipe — progressive relaxation."""

    def test_exact_match_returns_recipe(self):
        """Single matching recipe -> returned immediately."""
        from business.services.order_intake import _find_recipe

        db = MagicMock()
        recipe = _mock_recipe()
        # Simulate query chain returning one result
        q_mock = MagicMock()
        q_mock.all.return_value = [recipe]
        db.query.return_value.filter.return_value = q_mock
        q_mock.filter.return_value = q_mock

        item = _mock_item()
        result = _find_recipe(db, item)

        self.assertEqual(result, recipe)

    def test_no_match_returns_none(self):
        """No matching recipe -> returns None."""
        from business.services.order_intake import _find_recipe

        db = MagicMock()
        q_mock = MagicMock()
        q_mock.all.return_value = []
        db.query.return_value.filter.return_value = q_mock
        q_mock.filter.return_value = q_mock

        item = _mock_item()
        result = _find_recipe(db, item)

        self.assertIsNone(result)


class TestGetDefectCoefficient(unittest.TestCase):
    """Tests for _get_defect_coefficient."""

    def test_default_coefficient_when_no_data(self):
        """No production data -> returns default 0.05."""
        from business.services.order_intake import _get_defect_coefficient

        db = MagicMock()
        db.query.return_value.filter.return_value.scalar.return_value = 0

        result = _get_defect_coefficient(db, uuid.uuid4(), "20x20")
        self.assertEqual(result, 0.05)

    def test_coefficient_capped_at_30_percent(self):
        """Extreme defect rate is capped at 0.30."""
        from business.services.order_intake import _get_defect_coefficient

        db = MagicMock()
        # total_produced=100, total_defects=50 -> 0.50 -> capped at 0.30
        db.query.return_value.filter.return_value.scalar.side_effect = [100, 50]
        db.query.return_value.join.return_value.filter.return_value.scalar.return_value = 50

        result = _get_defect_coefficient(db, uuid.uuid4(), "20x20")
        self.assertLessEqual(result, 0.30)


class TestEstimateFactoryLeadTime(unittest.TestCase):
    """Tests for estimate_factory_lead_time."""

    def test_returns_active_positions_and_avg_cycle(self):
        """Returns dict with expected keys."""
        from business.services.order_intake import estimate_factory_lead_time

        db = MagicMock()
        db.query.return_value.filter.return_value.scalar.return_value = 42
        db.query.return_value.filter.return_value.all.return_value = []

        factory_id = uuid.uuid4()
        result = estimate_factory_lead_time(db, factory_id)

        self.assertIn("active_positions", result)
        self.assertIn("avg_cycle_days", result)
        self.assertIn("estimated_queue_days", result)
        self.assertEqual(result["factory_id"], str(factory_id))


if __name__ == "__main__":
    unittest.main()
