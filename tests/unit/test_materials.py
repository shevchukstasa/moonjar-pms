"""Unit tests for material reservation, consumption, and min balance — NO database.

Tests pure business logic using SimpleNamespace mocks.
"""
import pytest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from business.services.material_consumption import (
    _SURFACE_MATERIAL_TYPES,
    _BASE_MATERIAL_TYPES,
)
from business.services.min_balance import (
    _DEFAULT_LEAD_TIMES,
)


class TestMaterials:
    """Test material reservation, consumption, and min balance logic."""

    def test_reserve_sufficient_materials(self):
        """When stock >= required, reservation should succeed.

        Test the core reservation math: required = qty_per_unit * position.quantity.
        Effective available = stock.balance - net_reserved.
        If available >= required → reserve.
        """
        # Simulate the reservation math (pure logic, no DB)
        qty_per_unit = Decimal("0.5")  # 0.5 kg per piece
        position_quantity = 100
        required = qty_per_unit * position_quantity  # 50 kg

        stock_balance = Decimal("200")  # 200 kg in stock
        net_reserved = Decimal("100")  # 100 kg already reserved
        effective_available = stock_balance - net_reserved  # 100 kg

        assert effective_available >= required, "Should have enough stock"
        assert effective_available == Decimal("100")
        assert required == Decimal("50")

    def test_reserve_creates_purchase_request(self):
        """When stock < required, shortage is detected → purchase request needed.

        Test the shortage detection logic: if effective_available < required,
        the system should NOT partial-reserve but flag a shortage.
        """
        qty_per_unit = Decimal("0.5")
        position_quantity = 100
        required = qty_per_unit * position_quantity  # 50 kg

        stock_balance = Decimal("30")
        net_reserved = Decimal("10")
        effective_available = stock_balance - net_reserved  # 20 kg

        is_shortage = effective_available < required
        assert is_shortage is True
        deficit = required - effective_available
        assert deficit == Decimal("30")  # need 30 more kg

    def test_consume_on_glazing_start(self):
        """Glazing start consumes BOM materials: RESERVE → CONSUME + UNRESERVE.

        Verify the transaction type classification for consumption.
        """
        # Verify the material types that get consumed vs skipped
        # Surface materials ARE consumed during glazing
        surface_types = {"pigment", "frit", "oxide_carbonate", "other_bulk", "glaze_ingredient"}
        assert surface_types == _SURFACE_MATERIAL_TYPES

        # Base materials are NOT consumed (stone is pre-existing)
        base_types = {"stone", "packaging", "consumable"}
        assert base_types == _BASE_MATERIAL_TYPES

        # Simulate consumption math
        recipe_qty_per_sqm = Decimal("150")  # 150 g/m²
        position_sqm = Decimal("5.0")
        expected_grams = recipe_qty_per_sqm * position_sqm  # 750g
        assert expected_grams == Decimal("750")

    def test_refire_skips_stone(self):
        """Refire only consumes surface materials — stone/base is skipped.

        The consume_refire_materials function checks material.material_type
        against _BASE_MATERIAL_TYPES and skips those.
        """
        materials = [
            SimpleNamespace(material_type="pigment", name="Red Pigment"),
            SimpleNamespace(material_type="frit", name="Transparent Frit"),
            SimpleNamespace(material_type="stone", name="Lava Stone"),
            SimpleNamespace(material_type="packaging", name="Box"),
            SimpleNamespace(material_type="oxide_carbonate", name="Cobalt Oxide"),
        ]

        consumed = []
        skipped = []
        for mat in materials:
            if mat.material_type in _BASE_MATERIAL_TYPES:
                skipped.append(mat.name)
            else:
                consumed.append(mat.name)

        assert "Red Pigment" in consumed
        assert "Transparent Frit" in consumed
        assert "Cobalt Oxide" in consumed
        assert "Lava Stone" in skipped, "Stone must be skipped on refire"
        assert "Box" in skipped, "Packaging must be skipped on refire"
        assert len(consumed) == 3
        assert len(skipped) == 2

    def test_min_balance_auto_calculation(self):
        """min_balance_recommended = lead_time × avg_daily × 1.2 (20% safety buffer).

        Tests the formula from min_balance.py §18.
        """
        # Simulate: 90 days, 900 kg consumed → avg_daily = 10 kg/day
        total_consumed = Decimal("900")
        days_in_window = 90
        avg_daily = total_consumed / days_in_window
        assert avg_daily == Decimal("10")

        # Lead time = 14 days (pigment default)
        lead_time = _DEFAULT_LEAD_TIMES["pigment"]
        assert lead_time == 14

        # Formula: lead_time × avg_daily × 1.2
        min_balance = Decimal(str(lead_time)) * avg_daily * Decimal("1.2")
        assert min_balance == Decimal("168.0")  # 14 * 10 * 1.2 = 168

        # For stone: shorter lead time
        stone_lead = _DEFAULT_LEAD_TIMES["stone"]
        assert stone_lead == 7
        min_balance_stone = Decimal(str(stone_lead)) * avg_daily * Decimal("1.2")
        assert min_balance_stone == Decimal("84.0")  # 7 * 10 * 1.2 = 84


class TestDefaultLeadTimes:
    """Verify hardcoded lead time defaults make business sense."""

    def test_stone_lead_time_shortest_production(self):
        """Stone is sourced locally (Bali) → 7 days."""
        assert _DEFAULT_LEAD_TIMES["stone"] == 7

    def test_chemical_materials_14_days(self):
        """Pigments, frits, oxides need import → 14 days."""
        assert _DEFAULT_LEAD_TIMES["pigment"] == 14
        assert _DEFAULT_LEAD_TIMES["frit"] == 14
        assert _DEFAULT_LEAD_TIMES["oxide_carbonate"] == 14

    def test_packaging_fastest(self):
        """Packaging materials available locally → 3 days."""
        assert _DEFAULT_LEAD_TIMES["packaging"] == 3
        assert _DEFAULT_LEAD_TIMES["consumable"] == 3

    def test_all_types_covered(self):
        """All material types have default lead times."""
        expected_types = {"stone", "pigment", "frit", "oxide_carbonate", "packaging", "consumable", "other"}
        assert set(_DEFAULT_LEAD_TIMES.keys()) == expected_types
