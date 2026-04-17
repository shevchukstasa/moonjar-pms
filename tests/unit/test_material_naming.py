"""Unit tests for material_naming — parsing, short_name canonicalisation, unit rules.

Covers the rules documented in ``docs/BUSINESS_LOGIC_FULL.md §29``. Pure
functions; no DB, no fixtures.
"""
import pytest

from business.services import material_naming as nm


# ── Parsing & short_name canonicalisation ──────────────────────────

@pytest.mark.parametrize("raw", [
    "Grey Lava 5×20×1.2",
    "Black Lava 5×20×1.2",
    "Bali Lava Stone 5×20×1.2",
    "lava 5x20x1.2",
])
def test_color_variants_collapse_to_same_short_name(raw):
    """Per §29: all colors of same size → one canonical short_name."""
    parsed = nm.parse_stone_delivery_name(raw)
    assert nm.build_short_name(parsed) == "Lava Stone 5×20×1.2"


def test_unicode_x_normalised_to_ascii():
    """× (U+00D7) and x must produce identical short_name."""
    a = nm.build_short_name_from_raw("Grey Lava 5×20×1.2")
    b = nm.build_short_name_from_raw("Grey Lava 5x20x1.2")
    assert a == b


def test_typology_tiles_for_thin_flat():
    parsed = nm.parse_stone_delivery_name("Grey Lava 5×20×1.2")
    assert parsed.typology == "tiles"


def test_typology_3d_for_range_thickness():
    """Thickness expressed as range '1-2' → 3d typology."""
    assert nm.parse_stone_delivery_name("Black Lava 5x20x1-2").typology == "3d"
    assert nm.parse_stone_delivery_name("Lava 10x10x2/3").typology == "3d"


def test_typology_countertop_for_large_rect():
    """Any dim > 40 cm and rectangular → countertop."""
    parsed = nm.parse_stone_delivery_name("Grey Lava 60×100×3")
    assert parsed.typology == "countertop"


def test_typology_sink_for_large_round():
    parsed = nm.parse_stone_delivery_name("Lava Sink Ø45×3")
    assert parsed.typology == "sink"
    assert parsed.is_round
    assert parsed.diameter_mm == 450


def test_explicit_sink_keyword_wins():
    """Even small round with 'sink' keyword → sink."""
    parsed = nm.parse_stone_delivery_name("Lava Sink Ø20×3")
    assert parsed.typology == "sink"


def test_ambiguous_round_needs_user_choice():
    """Round 29-40 cm without keyword → ambiguous, ask user."""
    parsed = nm.parse_stone_delivery_name("Lava Ø35×3")
    assert parsed.needs_typology_choice is True


def test_color_extracted_but_not_in_short_name():
    parsed = nm.parse_stone_delivery_name("Grey Lava 5×20×1.2")
    assert parsed.color == "Grey"
    assert "Grey" not in nm.build_short_name(parsed)


def test_freeform_fallback_when_no_size():
    parsed = nm.parse_stone_delivery_name("Lava Freeform")
    assert nm.build_short_name(parsed) == "Lava Stone Freeform"


def test_dimensions_in_mm():
    parsed = nm.parse_stone_delivery_name("Grey Lava 5×20×1.2")
    assert parsed.width_mm == 50
    assert parsed.height_mm == 200
    assert parsed.thickness_mm == 12


# ── Unit validation ────────────────────────────────────────────────

@pytest.mark.parametrize("mtype,unit,ok", [
    ("stone", "pcs", True),
    ("stone", "m²", True),
    ("stone", "kg", False),
    ("stone", "g", False),
    ("pigment", "kg", True),
    ("pigment", "g", True),
    ("pigment", "pcs", False),
    ("frit", "kg", True),
    ("frit", "pcs", False),
    ("packaging", "pcs", True),
    ("packaging", "kg", True),
])
def test_unit_validation_per_type(mtype, unit, ok):
    assert nm.is_valid_unit_for_type(mtype, unit) is ok


def test_allowed_units_for_stone_excludes_kg():
    assert "kg" not in nm.allowed_units_for_type("stone")
    assert "pcs" in nm.allowed_units_for_type("stone")
    assert "m²" in nm.allowed_units_for_type("stone")


def test_allowed_units_for_pigment_excludes_pcs():
    assert "pcs" not in nm.allowed_units_for_type("pigment")
    assert "kg" in nm.allowed_units_for_type("pigment")


# ── strip_color_words helper ───────────────────────────────────────

def test_strip_color_only_at_start():
    """Color words past a non-color word stay (could be material spec)."""
    color, rest = nm.strip_color_words("Grey Lava 5x20")
    assert color == "Grey"
    assert rest == "Lava 5x20"

    # 'red' here is part of "Red" pigment NAME, not at start before non-color
    color, rest = nm.strip_color_words("Lava Red Sink")
    assert color is None
    assert "Red" in rest


def test_provenance_words_stripped():
    """'Bali' / 'Java' are provenance, not part of canonical name."""
    color, rest = nm.strip_color_words("Bali Lava Stone 5x20")
    assert color == "Bali"
    assert "Lava" in rest
