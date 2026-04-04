"""Unit tests for typology_matcher.py — matching, zone classification, capacity resolution.

All tests use mocks — NO database or production data touched.
"""
import pytest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, PropertyMock
from uuid import uuid4

from business.services.typology_matcher import (
    _matches_jsonb,
    _size_in_range,
    classify_loading_zone,
    get_effective_capacity,
    get_zone_capacity,
    _build_ref_position,
)


# ---------------------------------------------------------------------------
#  Helpers — build fake objects with SimpleNamespace
# ---------------------------------------------------------------------------

def _pos(**kw):
    """Build a fake position."""
    defaults = dict(
        factory_id=uuid4(),
        product_type="tile",
        place_of_application="face_only",
        collection=None,
        application_method_code=None,
        size="10x10",
        width_cm=Decimal("10"),
        length_cm=Decimal("10"),
        quantity=100,
        glazeable_sqm=Decimal("0.01"),
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def _typology(**kw):
    """Build a fake KilnLoadingTypology."""
    defaults = dict(
        id=uuid4(),
        factory_id=uuid4(),
        name="Test Typology",
        product_types=[],
        place_of_application=[],
        collections=[],
        methods=[],
        min_size_cm=None,
        max_size_cm=None,
        max_short_side_cm=None,
        preferred_loading="auto",
        is_active=True,
        priority=0,
        capacities=[],
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def _kiln(**kw):
    """Build a fake kiln Resource."""
    defaults = dict(
        id=uuid4(),
        name="Test Kiln",
        capacity_sqm=Decimal("8.0"),
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def _cap(**kw):
    """Build a fake KilnTypologyCapacity."""
    defaults = dict(
        capacity_sqm=Decimal("7.83"),
        ai_adjusted_sqm=None,
        zone="primary",
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


# ═══════════════════════════════════════════════════════════════════════════
#  _matches_jsonb
# ═══════════════════════════════════════════════════════════════════════════

class TestMatchesJsonb:
    def test_empty_criteria_matches_anything(self):
        assert _matches_jsonb([], "anything") is True

    def test_empty_criteria_matches_none(self):
        assert _matches_jsonb([], None) is True

    def test_criteria_matches_exact(self):
        assert _matches_jsonb(["tile"], "tile") is True

    def test_criteria_case_insensitive(self):
        assert _matches_jsonb(["Tile"], "tile") is True
        assert _matches_jsonb(["tile"], "TILE") is True

    def test_criteria_no_match(self):
        assert _matches_jsonb(["countertop"], "tile") is False

    def test_criteria_multiple_one_matches(self):
        assert _matches_jsonb(["tile", "countertop"], "tile") is True

    def test_criteria_none_value_no_match(self):
        assert _matches_jsonb(["tile"], None) is False

    def test_criteria_enum_value_extracted(self):
        class FakeEnum:
            value = "tile"
        assert _matches_jsonb(["tile"], FakeEnum()) is True

    def test_criteria_enum_no_match(self):
        class FakeEnum:
            value = "sink"
        assert _matches_jsonb(["tile"], FakeEnum()) is False


# ═══════════════════════════════════════════════════════════════════════════
#  _size_in_range
# ═══════════════════════════════════════════════════════════════════════════

class TestSizeInRange:
    """Test size matching with min/max and max_short_side_cm."""

    def test_no_constraints_matches(self):
        t = _typology()
        p = _pos(width_cm=Decimal("30"), length_cm=Decimal("60"))
        assert _size_in_range(t, p) is True

    def test_within_range(self):
        t = _typology(min_size_cm=Decimal("5"), max_size_cm=Decimal("20"))
        p = _pos(width_cm=Decimal("10"), length_cm=Decimal("10"))
        assert _size_in_range(t, p) is True

    def test_exceeds_max_size(self):
        t = _typology(max_size_cm=Decimal("20"))
        p = _pos(width_cm=Decimal("10"), length_cm=Decimal("30"))
        assert _size_in_range(t, p) is False  # max_dim=30 > 20

    def test_below_min_size(self):
        t = _typology(min_size_cm=Decimal("10"))
        p = _pos(width_cm=Decimal("5"), length_cm=Decimal("20"))
        assert _size_in_range(t, p) is False  # min_dim=5 < 10

    def test_max_short_side_blocks_20x20(self):
        """20x20 tile should NOT match 'small tile' with max_short_side_cm=15."""
        t = _typology(
            min_size_cm=Decimal("5"),
            max_size_cm=Decimal("20"),
            max_short_side_cm=Decimal("15"),
        )
        p = _pos(width_cm=Decimal("20"), length_cm=Decimal("20"))
        assert _size_in_range(t, p) is False  # min_dim=20 > 15

    def test_max_short_side_allows_10x20(self):
        """10x20 tile SHOULD match 'small tile' with max_short_side_cm=15."""
        t = _typology(
            min_size_cm=Decimal("5"),
            max_size_cm=Decimal("20"),
            max_short_side_cm=Decimal("15"),
        )
        p = _pos(width_cm=Decimal("10"), length_cm=Decimal("20"))
        assert _size_in_range(t, p) is True  # min_dim=10 <= 15

    def test_max_short_side_allows_5x20(self):
        t = _typology(max_short_side_cm=Decimal("15"))
        p = _pos(width_cm=Decimal("5"), length_cm=Decimal("20"))
        assert _size_in_range(t, p) is True

    def test_max_short_side_boundary_15x15(self):
        """15x15 is exactly at the boundary — should match."""
        t = _typology(max_short_side_cm=Decimal("15"))
        p = _pos(width_cm=Decimal("15"), length_cm=Decimal("15"))
        assert _size_in_range(t, p) is True  # min_dim=15 <= 15

    def test_size_parsed_from_string(self):
        """When width/length are 0, parse from size string."""
        t = _typology(max_size_cm=Decimal("20"))
        p = _pos(width_cm=None, length_cm=None, size="10x10")
        assert _size_in_range(t, p) is True

    def test_size_string_cyrillic_x(self):
        """Size with Cyrillic 'х' instead of Latin 'x'."""
        t = _typology(max_size_cm=Decimal("20"))
        p = _pos(width_cm=None, length_cm=None, size="10\u044510")  # 10х10
        assert _size_in_range(t, p) is True

    def test_size_string_exceeds(self):
        t = _typology(max_size_cm=Decimal("20"))
        p = _pos(width_cm=None, length_cm=None, size="30x60")
        assert _size_in_range(t, p) is False

    def test_no_dimensions_no_size_passes(self):
        """No width, no length, no size string — pass through."""
        t = _typology(max_size_cm=Decimal("20"))
        p = _pos(width_cm=None, length_cm=None, size=None)
        assert _size_in_range(t, p) is True

    def test_unparseable_size_passes(self):
        t = _typology(max_size_cm=Decimal("20"))
        p = _pos(width_cm=None, length_cm=None, size="custom-shape")
        assert _size_in_range(t, p) is True

    # ── Real-world scenarios ──

    def test_small_tile_10x10_matches_small(self):
        """Small Tile typology: max_size 20, max_short_side 15."""
        small = _typology(min_size_cm=Decimal("5"), max_size_cm=Decimal("20"), max_short_side_cm=Decimal("15"))
        assert _size_in_range(small, _pos(width_cm=Decimal("10"), length_cm=Decimal("10"))) is True

    def test_medium_tile_20x20_matches_medium_not_small(self):
        """20x20 should match medium (no max_short_side) but not small (max_short_side=15)."""
        small = _typology(min_size_cm=Decimal("5"), max_size_cm=Decimal("20"), max_short_side_cm=Decimal("15"))
        medium = _typology(min_size_cm=Decimal("5"), max_size_cm=Decimal("40"))
        pos = _pos(width_cm=Decimal("20"), length_cm=Decimal("20"))
        assert _size_in_range(small, pos) is False
        assert _size_in_range(medium, pos) is True

    def test_10x40_matches_medium_not_small(self):
        small = _typology(min_size_cm=Decimal("5"), max_size_cm=Decimal("20"), max_short_side_cm=Decimal("15"))
        medium = _typology(min_size_cm=Decimal("5"), max_size_cm=Decimal("40"))
        pos = _pos(width_cm=Decimal("10"), length_cm=Decimal("40"))
        assert _size_in_range(small, pos) is False   # 40 > max_size 20
        assert _size_in_range(medium, pos) is True


# ═══════════════════════════════════════════════════════════════════════════
#  classify_loading_zone
# ═══════════════════════════════════════════════════════════════════════════

class TestClassifyLoadingZone:
    """Test zone classification: edge vs flat."""

    def test_face_only_small_is_edge(self):
        p = _pos(place_of_application="face_only", width_cm=Decimal("10"), length_cm=Decimal("10"))
        assert classify_loading_zone(p) == "edge"

    def test_edges_1_small_is_edge(self):
        p = _pos(place_of_application="edges_1", width_cm=Decimal("10"), length_cm=Decimal("10"))
        assert classify_loading_zone(p) == "edge"

    def test_edges_2_small_is_edge(self):
        p = _pos(place_of_application="edges_2", width_cm=Decimal("10"), length_cm=Decimal("10"))
        assert classify_loading_zone(p) == "edge"

    def test_face_only_large_is_flat(self):
        """Tiles > 15cm can't be edge-loaded even if face_only."""
        p = _pos(place_of_application="face_only", width_cm=Decimal("20"), length_cm=Decimal("20"))
        assert classify_loading_zone(p) == "flat"

    def test_face_only_boundary_15cm_is_edge(self):
        """15cm exactly is still edge-loadable."""
        p = _pos(place_of_application="face_only", width_cm=Decimal("15"), length_cm=Decimal("15"))
        assert classify_loading_zone(p) == "edge"

    def test_face_only_16cm_is_flat(self):
        p = _pos(place_of_application="face_only", width_cm=Decimal("16"), length_cm=Decimal("10"))
        assert classify_loading_zone(p) == "flat"

    def test_all_edges_always_flat(self):
        p = _pos(place_of_application="all_edges", width_cm=Decimal("10"), length_cm=Decimal("10"))
        assert classify_loading_zone(p) == "flat"

    def test_with_back_always_flat(self):
        p = _pos(place_of_application="with_back", width_cm=Decimal("10"), length_cm=Decimal("10"))
        assert classify_loading_zone(p) == "flat"

    def test_none_defaults_to_edge(self):
        """No place_of_application → default face_only → edge (if small)."""
        p = _pos(place_of_application=None, width_cm=Decimal("10"), length_cm=Decimal("10"))
        assert classify_loading_zone(p) == "edge"

    def test_enum_value_extracted(self):
        """place_of_application may be an enum with .value."""
        class FakeEnum:
            value = "all_edges"
        p = _pos(place_of_application=FakeEnum(), width_cm=Decimal("10"), length_cm=Decimal("10"))
        assert classify_loading_zone(p) == "flat"

    def test_size_from_string_when_no_dimensions(self):
        """Parse size from string for zone classification."""
        p = _pos(place_of_application="face_only", width_cm=None, length_cm=None, size="20x20")
        assert classify_loading_zone(p) == "flat"  # 20 > 15

    def test_no_dimensions_defaults_small(self):
        """No dimensions at all → default 10cm → edge."""
        p = _pos(place_of_application="face_only", width_cm=None, length_cm=None, size=None)
        assert classify_loading_zone(p) == "edge"

    def test_one_side_over_15_is_flat(self):
        """10x20 face_only → max_dim=20 > 15 → flat."""
        p = _pos(place_of_application="face_only", width_cm=Decimal("10"), length_cm=Decimal("20"))
        assert classify_loading_zone(p) == "flat"


# ═══════════════════════════════════════════════════════════════════════════
#  get_effective_capacity
# ═══════════════════════════════════════════════════════════════════════════

class TestGetEffectiveCapacity:

    def test_uses_ai_adjusted_sqm_first(self):
        db = MagicMock()
        fid = uuid4()
        kiln = _kiln()
        pos = _pos(factory_id=fid)

        typ = _typology(id=uuid4(), factory_id=fid)
        cap = _cap(ai_adjusted_sqm=Decimal("9.5"), capacity_sqm=Decimal("7.83"))

        with patch("business.services.typology_matcher.find_matching_typology", return_value=typ), \
             patch("business.services.typology_matcher.get_typology_capacity", return_value=cap):
            result = get_effective_capacity(db, pos, kiln)

        assert result == 9.5

    def test_uses_capacity_sqm_when_no_ai(self):
        db = MagicMock()
        fid = uuid4()
        kiln = _kiln()
        pos = _pos(factory_id=fid)
        typ = _typology(id=uuid4())
        cap = _cap(ai_adjusted_sqm=None, capacity_sqm=Decimal("7.83"))

        with patch("business.services.typology_matcher.find_matching_typology", return_value=typ), \
             patch("business.services.typology_matcher.get_typology_capacity", return_value=cap):
            result = get_effective_capacity(db, pos, kiln)

        assert result == 7.83

    def test_fallback_to_kiln_capacity(self):
        db = MagicMock()
        kiln = _kiln(capacity_sqm=Decimal("5.0"))
        pos = _pos()

        with patch("business.services.typology_matcher.find_matching_typology", return_value=None):
            result = get_effective_capacity(db, pos, kiln)

        assert result == 5.0

    def test_fallback_to_1_when_nothing(self):
        db = MagicMock()
        kiln = _kiln(capacity_sqm=None)
        pos = _pos()

        with patch("business.services.typology_matcher.find_matching_typology", return_value=None):
            result = get_effective_capacity(db, pos, kiln)

        assert result == 1.0


# ═══════════════════════════════════════════════════════════════════════════
#  get_zone_capacity
# ═══════════════════════════════════════════════════════════════════════════

class TestGetZoneCapacity:

    def test_edge_fallback_85_percent(self):
        """No typology → edge zone = 85% of kiln capacity."""
        db = MagicMock()
        kiln = _kiln(capacity_sqm=Decimal("10.0"))
        pos = _pos()

        with patch("business.services.typology_matcher.find_matching_typology", return_value=None):
            result = get_zone_capacity(db, pos, kiln, "edge")

        assert result == pytest.approx(8.5)

    def test_flat_fallback_15_percent(self):
        """No typology → flat zone = 15% of kiln capacity."""
        db = MagicMock()
        kiln = _kiln(capacity_sqm=Decimal("10.0"))
        pos = _pos()

        with patch("business.services.typology_matcher.find_matching_typology", return_value=None):
            result = get_zone_capacity(db, pos, kiln, "flat")

        assert result == pytest.approx(1.5)

    def test_fallback_when_no_kiln_capacity(self):
        db = MagicMock()
        kiln = _kiln(capacity_sqm=None)
        pos = _pos()

        with patch("business.services.typology_matcher.find_matching_typology", return_value=None):
            result = get_zone_capacity(db, pos, kiln, "edge")

        assert result == pytest.approx(0.85)  # 1.0 * 0.85


# ═══════════════════════════════════════════════════════════════════════════
#  _build_ref_position
# ═══════════════════════════════════════════════════════════════════════════

class TestBuildRefPosition:

    def test_midpoint_dimensions(self):
        t = _typology(min_size_cm=Decimal("10"), max_size_cm=Decimal("20"))
        ref = _build_ref_position(t)
        assert ref.size == "15.0x15.0"

    def test_only_max_size(self):
        t = _typology(min_size_cm=None, max_size_cm=Decimal("30"))
        ref = _build_ref_position(t)
        assert ref.size == "30.0x30.0"

    def test_only_min_size(self):
        t = _typology(min_size_cm=Decimal("5"), max_size_cm=None)
        ref = _build_ref_position(t)
        assert ref.size == "5.0x5.0"

    def test_no_sizes_default_10(self):
        t = _typology()
        ref = _build_ref_position(t)
        assert ref.size == "10.0x10.0"

    def test_product_type_from_typology(self):
        t = _typology(product_types=["countertop"])
        ref = _build_ref_position(t)
        assert ref.product_type == "countertop"

    def test_product_type_default_tile(self):
        t = _typology(product_types=[])
        ref = _build_ref_position(t)
        assert ref.product_type == "tile"

    def test_glaze_placement_face_only(self):
        t = _typology(place_of_application=["face_only"])
        ref = _build_ref_position(t)
        assert ref.glaze_placement == "face-only"

    def test_glaze_placement_all_edges(self):
        t = _typology(place_of_application=["all_edges"])
        ref = _build_ref_position(t)
        assert ref.glaze_placement == "face-3-4-edges"

    def test_glaze_placement_with_back(self):
        t = _typology(place_of_application=["with_back"])
        ref = _build_ref_position(t)
        assert ref.glaze_placement == "face-with-back"

    def test_default_thickness(self):
        t = _typology()
        ref = _build_ref_position(t)
        assert ref.thickness_cm == 1.1

    def test_shape_always_rectangle(self):
        t = _typology()
        ref = _build_ref_position(t)
        assert ref.shape == "rectangle"
