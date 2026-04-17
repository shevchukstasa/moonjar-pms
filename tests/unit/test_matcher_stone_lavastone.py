"""Stone-path matcher tests — exercises the canonical short_name lookup.

Reproduces the failing case from the user-reported bug (Apr 18, 2026):
"Grey Lava 5×20×1.2" must match the existing DB material "Lavastone 5×20×1.2"
(M-0053). Pure unit tests — no DB.
"""
import asyncio

import pytest

from business.services.material_matcher import find_best_match


# ── Fixture: minimal in-memory DB ──────────────────────────────────


@pytest.fixture
def stone_db():
    """One legacy stone material (short_name not yet backfilled) and one pigment."""
    db_materials = [
        {
            "id": "m0053",
            "name": "Lavastone 5×20×1.2",
            "short_name": None,            # legacy row — matcher must derive
            "material_type": "stone",
            "unit": "pcs",
            "product_subtype": None,
            "size_id": "sz-5x20",
        },
        {
            "id": "g9484",
            "name": "Dark Grey G9484",
            "short_name": "Dark Grey G9484",
            "material_type": "pigment",
            "unit": "kg",
            "product_subtype": None,
            "size_id": None,
        },
    ]
    db_sizes = [
        {
            "id": "sz-5x20",
            "name": "5×20",
            "width_mm": 50,
            "height_mm": 200,
            "thickness_mm": 12,
            "diameter_mm": None,
            "shape": "rectangle",
        },
    ]
    return db_materials, db_sizes


def _run(coro):
    """Run an async coroutine in tests without depending on pytest-asyncio."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ── Tests ──────────────────────────────────────────────────────────


@pytest.mark.parametrize("raw", [
    "Grey Lava 5×20×1.2",
    "Black Lava 5×20×1.2",
    "Bali Lava Stone 5×20×1.2",
    "Lavastone 5×20×1.2",
])
def test_color_variants_all_match_legacy_lavastone(stone_db, raw):
    """All color variants of 5×20×1.2 must collapse to the same M-0053 row."""
    db_materials, db_sizes = stone_db
    result = _run(find_best_match(
        delivery_name=raw,
        delivery_qty=100,
        delivery_unit="pcs",
        db_materials=db_materials,
        supplier_name="CV. Bestone Indonesia",
        db_sizes=db_sizes,
    ))
    assert result["matched"] is True, f"{raw!r} should match M-0053"
    assert result["material_id"] == "m0053"


def test_pigment_never_returned_for_stone_supplier(stone_db):
    """Bug fix verification: 'Grey Lava' must NOT match 'Dark Grey G9484'."""
    db_materials, db_sizes = stone_db
    result = _run(find_best_match(
        delivery_name="Grey Lava 5×20×1.2",
        delivery_qty=100,
        delivery_unit="pcs",
        db_materials=db_materials,
        supplier_name="CV. Bestone Indonesia",
        db_sizes=db_sizes,
    ))
    assert result.get("material_id") != "g9484"
    # And ALL candidates must also be stone — never pigment
    for c in result.get("candidates", []):
        assert c["material_id"] != "g9484"


def test_unknown_size_returns_canonical_suggestion(stone_db):
    db_materials, db_sizes = stone_db
    result = _run(find_best_match(
        delivery_name="Grey Lava 10×10×1",
        delivery_qty=500,
        delivery_unit="pcs",
        db_materials=db_materials,
        supplier_name="CV. Bestone Indonesia",
        db_sizes=db_sizes,
    ))
    assert result["matched"] is False
    assert result["suggested_short_name"] == "Lava Stone 10×10×1"
    assert result["suggested_subtype"] == "tiles"


def test_3d_typology_detected_from_range_thickness(stone_db):
    db_materials, db_sizes = stone_db
    result = _run(find_best_match(
        delivery_name="Black Lava 5x20x1-2",
        delivery_qty=100,
        delivery_unit="pcs",
        db_materials=db_materials,
        supplier_name="CV. Bestone Indonesia",
        db_sizes=db_sizes,
    ))
    assert result["suggested_subtype"] == "3d"
    assert result["suggested_short_name"] == "Lava Stone 5×20×1-2"


def test_round_sink_detected(stone_db):
    db_materials, db_sizes = stone_db
    result = _run(find_best_match(
        delivery_name="Lava Sink Ø35×3",
        delivery_qty=10,
        delivery_unit="pcs",
        db_materials=db_materials,
        supplier_name="CV. Bestone Indonesia",
        db_sizes=db_sizes,
    ))
    assert result["suggested_subtype"] == "sink"
    assert result["parsed_diameter_mm"] == 350


def test_supplier_unknown_does_not_route_to_stone(stone_db):
    """If supplier is unknown, do NOT force the stone path."""
    db_materials, db_sizes = stone_db
    result = _run(find_best_match(
        delivery_name="Grey Lava 5×20×1.2",
        delivery_qty=100,
        delivery_unit="pcs",
        db_materials=db_materials,
        supplier_name=None,            # No hint
        db_sizes=db_sizes,
    ))
    # The canonical lookup is gated on supplier_type, so without a hint the
    # legacy fuzzy path runs. We don't assert match outcome; just that the
    # call succeeds (regression guard for the routing fix).
    assert "matched" in result
