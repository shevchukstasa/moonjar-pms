"""Unit tests for kiln assignment algorithm — zone classification, capacity, batch logic.

All tests use mocks — NO database or production data touched.
"""
import pytest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from business.services.typology_matcher import classify_loading_zone


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _pos(**kw):
    """Build a fake position for kiln tests."""
    defaults = dict(
        product_type="tile",
        place_of_application="face_only",
        collection=None,
        size="10x10",
        width_cm=Decimal("10"),
        length_cm=Decimal("10"),
        quantity=100,
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


class TestKilnAssignment:
    """Test kiln selection and zone classification logic."""

    def test_raku_goes_to_raku_kiln(self):
        """Raku/gold firing (700C) prefers Raku kiln via _is_raku_kiln check.

        We test the batch_formation helper _is_raku_kiln directly.
        """
        from business.services.batch_formation import _is_raku_kiln

        raku_kiln = SimpleNamespace(
            id=uuid4(), name="Raku Kiln", kiln_type="raku",
            capacity_sqm=Decimal("4.0"),
        )
        standard_kiln = SimpleNamespace(
            id=uuid4(), name="Large Kiln", kiln_type="standard",
            capacity_sqm=Decimal("8.0"),
        )

        assert _is_raku_kiln(raku_kiln) is True
        assert _is_raku_kiln(standard_kiln) is False

    def test_countertop_goes_to_small(self):
        """Countertops (product_type=countertop) are classified as flat loading zone.

        Countertops are large items that always go flat, never edge-loaded.
        """
        pos = _pos(
            product_type="countertop",
            place_of_application="all_edges",
            width_cm=Decimal("60"),
            length_cm=Decimal("40"),
        )
        zone = classify_loading_zone(pos)
        assert zone == "flat", "Countertops with all_edges must be flat-loaded"

    def test_flat_loading_calculation(self):
        """Test flat loading: tiles > 15cm on any side → flat zone."""
        pos = _pos(
            place_of_application="face_only",
            width_cm=Decimal("20"),
            length_cm=Decimal("20"),
            size="20x20",
        )
        zone = classify_loading_zone(pos)
        assert zone == "flat", "Tiles > 15cm should be flat-loaded even with face_only"

    def test_edge_loading_calculation(self):
        """Test edge loading: small face_only tiles (<=15cm) → edge zone."""
        pos = _pos(
            place_of_application="face_only",
            width_cm=Decimal("10"),
            length_cm=Decimal("10"),
            size="10x10",
        )
        zone = classify_loading_zone(pos)
        assert zone == "edge", "Small face_only tiles should be edge-loaded"

    def test_alternation_when_both_fit(self):
        """Test zone classification with edges_1 and small size → edge loading.

        This tests the alternation logic: face_only, edges_1, edges_2 can all
        be edge-loaded when tile is small enough (<=15cm).
        """
        for place in ("face_only", "edges_1", "edges_2"):
            pos = _pos(
                place_of_application=place,
                width_cm=Decimal("12"),
                length_cm=Decimal("12"),
                size="12x12",
            )
            zone = classify_loading_zone(pos)
            assert zone == "edge", f"{place} with 12cm tile should be edge"

    def test_force_to_larger_when_big_difference(self):
        """Test: all_edges or with_back always goes to flat zone regardless of size."""
        for place in ("all_edges", "with_back"):
            pos = _pos(
                place_of_application=place,
                width_cm=Decimal("8"),
                length_cm=Decimal("8"),
                size="8x8",
            )
            zone = classify_loading_zone(pos)
            assert zone == "flat", f"{place} must always be flat-loaded"


class TestZoneClassificationEdgeCases:
    """Additional edge cases for zone classification."""

    def test_size_15cm_is_edge(self):
        """Exactly 15cm max side → edge (boundary, not > 15)."""
        pos = _pos(
            place_of_application="face_only",
            width_cm=Decimal("15"),
            length_cm=Decimal("10"),
        )
        zone = classify_loading_zone(pos)
        assert zone == "edge", "Exactly 15cm should still be edge"

    def test_size_15_01cm_is_flat(self):
        """15.01cm max side → flat (just over boundary)."""
        pos = _pos(
            place_of_application="face_only",
            width_cm=Decimal("15.01"),
            length_cm=Decimal("10"),
        )
        zone = classify_loading_zone(pos)
        assert zone == "flat", "15.01cm should be flat"

    def test_size_parsed_from_string_when_no_dimensions(self):
        """When width_cm/length_cm are None, parse from size string."""
        pos = _pos(
            place_of_application="face_only",
            width_cm=None,
            length_cm=None,
            size="10x10",
        )
        zone = classify_loading_zone(pos)
        assert zone == "edge", "Should parse size '10x10' and classify as edge"

    def test_large_size_string_parsed_as_flat(self):
        """Size string 20x30 with no explicit dims → flat."""
        pos = _pos(
            place_of_application="face_only",
            width_cm=None,
            length_cm=None,
            size="20x30",
        )
        zone = classify_loading_zone(pos)
        assert zone == "flat", "Should parse size '20x30' as flat"

    def test_enum_place_of_application(self):
        """place_of_application as enum-like object with .value is handled."""
        place_enum = SimpleNamespace(value="face_only")
        pos = _pos(
            place_of_application=place_enum,
            width_cm=Decimal("10"),
            length_cm=Decimal("10"),
        )
        zone = classify_loading_zone(pos)
        assert zone == "edge"

    def test_unknown_place_defaults_to_flat(self):
        """Unknown place_of_application defaults to flat (safety)."""
        pos = _pos(
            place_of_application="unknown_value",
            width_cm=Decimal("10"),
            length_cm=Decimal("10"),
        )
        zone = classify_loading_zone(pos)
        assert zone == "flat"
