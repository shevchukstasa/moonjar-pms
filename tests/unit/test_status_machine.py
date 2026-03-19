"""Unit tests for the Position Status Machine service."""
import pytest
from unittest.mock import MagicMock, patch

from api.enums import PositionStatus
from business.services.status_machine import (
    validate_status_transition,
    get_allowed_transitions,
)


class TestValidateStatusTransition:
    """Test validate_status_transition for valid and invalid transitions."""

    # --- Valid forward transitions ---

    def test_planned_to_engobe_applied(self):
        assert validate_status_transition("planned", "engobe_applied") is True

    def test_planned_to_glazed(self):
        assert validate_status_transition("planned", "glazed") is True

    def test_planned_to_insufficient_materials(self):
        assert validate_status_transition("planned", "insufficient_materials") is True

    def test_planned_to_awaiting_recipe(self):
        assert validate_status_transition("planned", "awaiting_recipe") is True

    def test_planned_to_awaiting_stencil_silkscreen(self):
        assert validate_status_transition("planned", "awaiting_stencil_silkscreen") is True

    def test_planned_to_awaiting_color_matching(self):
        assert validate_status_transition("planned", "awaiting_color_matching") is True

    def test_insufficient_materials_to_planned(self):
        assert validate_status_transition("insufficient_materials", "planned") is True

    def test_awaiting_recipe_to_planned(self):
        assert validate_status_transition("awaiting_recipe", "planned") is True

    def test_engobe_applied_to_engobe_check(self):
        assert validate_status_transition("engobe_applied", "engobe_check") is True

    def test_engobe_check_to_glazed(self):
        assert validate_status_transition("engobe_check", "glazed") is True

    def test_glazed_to_pre_kiln_check(self):
        assert validate_status_transition("glazed", "pre_kiln_check") is True

    def test_pre_kiln_check_to_loaded_in_kiln(self):
        assert validate_status_transition("pre_kiln_check", "loaded_in_kiln") is True

    def test_loaded_in_kiln_to_fired(self):
        assert validate_status_transition("loaded_in_kiln", "fired") is True

    def test_fired_to_transferred_to_sorting(self):
        assert validate_status_transition("fired", "transferred_to_sorting") is True

    def test_transferred_to_sorting_to_packed(self):
        assert validate_status_transition("transferred_to_sorting", "packed") is True

    def test_packed_to_sent_to_quality_check(self):
        assert validate_status_transition("packed", "sent_to_quality_check") is True

    def test_packed_to_ready_for_shipment(self):
        assert validate_status_transition("packed", "ready_for_shipment") is True

    def test_sent_to_quality_check_to_quality_check_done(self):
        assert validate_status_transition("sent_to_quality_check", "quality_check_done") is True

    def test_quality_check_done_to_ready_for_shipment(self):
        assert validate_status_transition("quality_check_done", "ready_for_shipment") is True

    def test_ready_for_shipment_to_shipped(self):
        assert validate_status_transition("ready_for_shipment", "shipped") is True

    def test_refire_to_loaded_in_kiln(self):
        assert validate_status_transition("refire", "loaded_in_kiln") is True

    # --- Universal transitions ---

    def test_any_status_to_cancelled(self):
        """cancelled is reachable from any status."""
        for status in PositionStatus:
            assert validate_status_transition(status.value, "cancelled") is True, (
                f"Expected {status.value} -> cancelled to be valid"
            )

    def test_any_status_to_blocked_by_qm(self):
        """blocked_by_qm is reachable from any status."""
        for status in PositionStatus:
            assert validate_status_transition(status.value, "blocked_by_qm") is True, (
                f"Expected {status.value} -> blocked_by_qm to be valid"
            )

    def test_blocked_by_qm_can_go_to_any_status(self):
        """blocked_by_qm can return to any status (returns to previous)."""
        assert validate_status_transition("blocked_by_qm", "planned") is True
        assert validate_status_transition("blocked_by_qm", "fired") is True
        assert validate_status_transition("blocked_by_qm", "packed") is True

    # --- Invalid transitions ---

    def test_planned_to_fired_is_invalid(self):
        """Cannot skip from planned directly to fired."""
        assert validate_status_transition("planned", "fired") is False

    def test_planned_to_shipped_is_invalid(self):
        assert validate_status_transition("planned", "shipped") is False

    def test_fired_to_packed_is_invalid(self):
        """fired must go through transferred_to_sorting first."""
        assert validate_status_transition("fired", "packed") is False

    def test_loaded_in_kiln_to_packed_is_invalid(self):
        assert validate_status_transition("loaded_in_kiln", "packed") is False

    def test_engobe_applied_to_loaded_in_kiln_is_invalid(self):
        assert validate_status_transition("engobe_applied", "loaded_in_kiln") is False

    # --- Terminal states ---

    def test_shipped_cannot_transition_further(self):
        """shipped is terminal (except universal targets)."""
        assert validate_status_transition("shipped", "planned") is False
        assert validate_status_transition("shipped", "packed") is False
        # But universal targets still work
        assert validate_status_transition("shipped", "cancelled") is True

    def test_merged_cannot_transition_further(self):
        """merged is terminal (except universal targets)."""
        assert validate_status_transition("merged", "planned") is False
        assert validate_status_transition("merged", "packed") is False
        assert validate_status_transition("merged", "cancelled") is True

    def test_cancelled_cannot_transition_further(self):
        """cancelled is terminal (except universal targets)."""
        assert validate_status_transition("cancelled", "planned") is False
        # But cancelled -> cancelled is valid (universal target)
        assert validate_status_transition("cancelled", "cancelled") is True

    # --- Invalid status values ---

    def test_invalid_current_status_returns_false(self):
        assert validate_status_transition("nonexistent", "planned") is False

    def test_invalid_new_status_returns_false(self):
        assert validate_status_transition("planned", "nonexistent") is False

    def test_both_invalid_returns_false(self):
        assert validate_status_transition("foo", "bar") is False


class TestGetAllowedTransitions:
    """Test get_allowed_transitions returns correct next statuses."""

    def test_planned_allowed_transitions(self):
        allowed = get_allowed_transitions("planned")
        assert "engobe_applied" in allowed
        assert "glazed" in allowed
        assert "insufficient_materials" in allowed
        assert "awaiting_recipe" in allowed
        # Universal targets always included
        assert "blocked_by_qm" in allowed
        assert "cancelled" in allowed
        # Not allowed
        assert "fired" not in allowed
        assert "shipped" not in allowed

    def test_loaded_in_kiln_allowed_transitions(self):
        allowed = get_allowed_transitions("loaded_in_kiln")
        assert "fired" in allowed
        assert "blocked_by_qm" in allowed
        assert "cancelled" in allowed
        assert "planned" not in allowed

    def test_shipped_terminal_only_universal(self):
        allowed = get_allowed_transitions("shipped")
        # Only universal targets
        assert "blocked_by_qm" in allowed
        assert "cancelled" in allowed
        assert len(allowed) == 2

    def test_merged_terminal_only_universal(self):
        allowed = get_allowed_transitions("merged")
        assert "blocked_by_qm" in allowed
        assert "cancelled" in allowed
        assert len(allowed) == 2

    def test_invalid_status_returns_empty(self):
        allowed = get_allowed_transitions("nonexistent_status")
        assert allowed == []

    def test_packed_includes_merge_and_qc(self):
        allowed = get_allowed_transitions("packed")
        assert "sent_to_quality_check" in allowed
        assert "ready_for_shipment" in allowed
        assert "merged" in allowed
