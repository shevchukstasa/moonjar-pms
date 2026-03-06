"""Integration tests for order lifecycle."""
import pytest


class TestOrderFlow:
    def test_webhook_creates_order(self, client, sample_factory):
        """Test sales webhook → order + positions."""
        # TODO: implement
        pass

    def test_duplicate_webhook_ignored(self, client, sample_factory):
        """Test idempotency: same event_id → no duplicate."""
        # TODO: implement
        pass

    def test_order_cancellation_releases_materials(self, client, sample_order):
        """Test cancellation releases reserved materials."""
        # TODO: implement
        pass
