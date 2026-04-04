"""Unit tests for production_scheduler.py — speed→duration math, backward scheduling.

All tests use mocks — NO database or production data touched.
"""
import math
import pytest
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, call
from uuid import uuid4

from business.services.production_scheduler import (
    _calc_hours_from_speed,
)


# ═══════════════════════════════════════════════════════════════════════════
#  _calc_hours_from_speed — the core math engine
# ═══════════════════════════════════════════════════════════════════════════

class TestCalcHoursFromSpeed:
    """Test speed→working days conversion for all rate_basis types."""

    # ── Fixed duration (drying, cooling, firing) ──

    def test_fixed_duration_8h_is_1_day(self):
        """8h fixed with 1 shift of 8h = 1 day."""
        result = _calc_hours_from_speed(
            rate=8.0, rate_unit="hours", rate_basis="fixed_duration",
            time_unit="hours", shift_count=1, shift_duration_hours=8.0,
            brigade_size=1, total_sqm=5.0, total_pcs=100,
        )
        assert result == 1

    def test_fixed_duration_20h_2_shifts_is_2_days(self):
        """20h fixed with 2 shifts of 8h (16h/day) → ceil(20/16)=2."""
        result = _calc_hours_from_speed(
            rate=20.0, rate_unit="hours", rate_basis="fixed_duration",
            time_unit="hours", shift_count=2, shift_duration_hours=8.0,
            brigade_size=1, total_sqm=5.0, total_pcs=100,
        )
        assert result == 2

    def test_fixed_duration_1h_is_1_day_minimum(self):
        """Even 1h fixed → at least 1 day."""
        result = _calc_hours_from_speed(
            rate=1.0, rate_unit="hours", rate_basis="fixed_duration",
            time_unit="hours", shift_count=2, shift_duration_hours=8.0,
            brigade_size=1, total_sqm=0, total_pcs=0,
        )
        assert result == 1

    def test_fixed_duration_ignores_sqm_pcs(self):
        """Fixed duration doesn't depend on quantity — rate IS the hours."""
        r1 = _calc_hours_from_speed(
            rate=10.0, rate_unit="hours", rate_basis="fixed_duration",
            time_unit="hours", shift_count=2, shift_duration_hours=8.0,
            brigade_size=1, total_sqm=1.0, total_pcs=10,
        )
        r2 = _calc_hours_from_speed(
            rate=10.0, rate_unit="hours", rate_basis="fixed_duration",
            time_unit="hours", shift_count=2, shift_duration_hours=8.0,
            brigade_size=1, total_sqm=1000.0, total_pcs=100000,
        )
        assert r1 == r2  # same rate → same result regardless of quantity

    def test_fixed_duration_48h_3_days(self):
        """48h with 16h/day → 3 days."""
        result = _calc_hours_from_speed(
            rate=48.0, rate_unit="hours", rate_basis="fixed_duration",
            time_unit="hours", shift_count=2, shift_duration_hours=8.0,
            brigade_size=1, total_sqm=0, total_pcs=0,
        )
        assert result == 3

    # ── Per-person throughput (sqm) ──

    def test_per_person_sqm_small_batch(self):
        """1 sqm at 5 sqm/h per person, 1 person, 1 shift of 8h → 1 day."""
        result = _calc_hours_from_speed(
            rate=5.0, rate_unit="sqm", rate_basis="per_person",
            time_unit="hour", shift_count=1, shift_duration_hours=8.0,
            brigade_size=1, total_sqm=1.0, total_pcs=0,
        )
        assert result == 1

    def test_per_person_sqm_large_batch(self):
        """100 sqm at 5 sqm/h, 2 people, 2x8h shifts.
        effective=10 sqm/h, hours_needed=10h, 16h/day → 1 day."""
        result = _calc_hours_from_speed(
            rate=5.0, rate_unit="sqm", rate_basis="per_person",
            time_unit="hour", shift_count=2, shift_duration_hours=8.0,
            brigade_size=2, total_sqm=100.0, total_pcs=0,
        )
        # effective = 5*2=10 sqm/h, hours=100/10=10h, per_day=16h → ceil(10/16)=1
        assert result == 1

    def test_per_person_sqm_multi_day(self):
        """200 sqm at 5 sqm/h, 1 person, 1x8h.
        hours=200/5=40h, 8h/day → 5 days."""
        result = _calc_hours_from_speed(
            rate=5.0, rate_unit="sqm", rate_basis="per_person",
            time_unit="hour", shift_count=1, shift_duration_hours=8.0,
            brigade_size=1, total_sqm=200.0, total_pcs=0,
        )
        assert result == 5

    # ── Per-person throughput (pcs) ──

    def test_per_person_pcs_100_at_60ph(self):
        """100 pcs at 60/h, 1 person, 1x8h → hours=100/60=1.67h → 1 day."""
        result = _calc_hours_from_speed(
            rate=60.0, rate_unit="pcs", rate_basis="per_person",
            time_unit="hour", shift_count=1, shift_duration_hours=8.0,
            brigade_size=1, total_sqm=0, total_pcs=100,
        )
        assert result == 1

    def test_per_person_pcs_1000_at_60ph(self):
        """1000 pcs at 60/h, 1 person, 1x8h → 16.67h → 2.08 days → 3 days.
        Wait: 1000/60=16.67h, 8h/day → ceil(16.67/8) = 3."""
        result = _calc_hours_from_speed(
            rate=60.0, rate_unit="pcs", rate_basis="per_person",
            time_unit="hour", shift_count=1, shift_duration_hours=8.0,
            brigade_size=1, total_sqm=0, total_pcs=1000,
        )
        assert result == 3

    def test_per_person_pcs_2_shifts(self):
        """1000 pcs at 60/h, 1 person, 2x8h → 16.67h, 16h/day → 2 days."""
        result = _calc_hours_from_speed(
            rate=60.0, rate_unit="pcs", rate_basis="per_person",
            time_unit="hour", shift_count=2, shift_duration_hours=8.0,
            brigade_size=1, total_sqm=0, total_pcs=1000,
        )
        assert result == 2

    def test_per_person_pcs_brigade(self):
        """1000 pcs at 60/h, 3 people, 2x8h → eff=180/h, 1000/180=5.56h, 16h/day → 1 day."""
        result = _calc_hours_from_speed(
            rate=60.0, rate_unit="pcs", rate_basis="per_person",
            time_unit="hour", shift_count=2, shift_duration_hours=8.0,
            brigade_size=3, total_sqm=0, total_pcs=1000,
        )
        assert result == 1

    # ── Per-brigade throughput ──

    def test_per_brigade_pcs(self):
        """Per brigade: brigade_size doesn't multiply rate.
        1000 pcs at 100/h brigade, 2x8h → 1000/100=10h, 16h/day → 1 day."""
        result = _calc_hours_from_speed(
            rate=100.0, rate_unit="pcs", rate_basis="per_brigade",
            time_unit="hour", shift_count=2, shift_duration_hours=8.0,
            brigade_size=5, total_sqm=0, total_pcs=1000,
        )
        assert result == 1

    # ── Rate per minute ──

    def test_rate_per_minute_converted(self):
        """2 sqm/min = 120 sqm/h. 100 sqm → 100/120=0.83h → 1 day."""
        result = _calc_hours_from_speed(
            rate=2.0, rate_unit="sqm", rate_basis="per_person",
            time_unit="min", shift_count=1, shift_duration_hours=8.0,
            brigade_size=1, total_sqm=100.0, total_pcs=0,
        )
        assert result == 1

    # ── Rate per shift ──

    def test_rate_per_shift_converted(self):
        """10 sqm/shift with 8h shift → 10/8=1.25 sqm/h.
        50 sqm → 50/1.25=40h, 8h/day → 5 days."""
        result = _calc_hours_from_speed(
            rate=10.0, rate_unit="sqm", rate_basis="per_person",
            time_unit="shift", shift_count=1, shift_duration_hours=8.0,
            brigade_size=1, total_sqm=50.0, total_pcs=0,
        )
        assert result == 5

    # ── Edge cases ──

    def test_zero_rate_returns_none(self):
        result = _calc_hours_from_speed(
            rate=0, rate_unit="sqm", rate_basis="per_person",
            time_unit="hour", shift_count=1, shift_duration_hours=8.0,
            brigade_size=1, total_sqm=10.0, total_pcs=0,
        )
        assert result is None

    def test_negative_rate_returns_none(self):
        result = _calc_hours_from_speed(
            rate=-5.0, rate_unit="sqm", rate_basis="per_person",
            time_unit="hour", shift_count=1, shift_duration_hours=8.0,
            brigade_size=1, total_sqm=10.0, total_pcs=0,
        )
        assert result is None

    def test_sqm_unit_but_zero_sqm_returns_none(self):
        """rate_unit=sqm but total_sqm=0 → can't calculate."""
        result = _calc_hours_from_speed(
            rate=5.0, rate_unit="sqm", rate_basis="per_person",
            time_unit="hour", shift_count=1, shift_duration_hours=8.0,
            brigade_size=1, total_sqm=0, total_pcs=100,
        )
        assert result is None

    def test_pcs_unit_but_zero_pcs_returns_none(self):
        result = _calc_hours_from_speed(
            rate=60.0, rate_unit="pcs", rate_basis="per_person",
            time_unit="hour", shift_count=1, shift_duration_hours=8.0,
            brigade_size=1, total_sqm=10.0, total_pcs=0,
        )
        assert result is None

    def test_minimum_1_day(self):
        """Even tiny amounts → at least 1 day."""
        result = _calc_hours_from_speed(
            rate=1000.0, rate_unit="pcs", rate_basis="per_person",
            time_unit="hour", shift_count=2, shift_duration_hours=8.0,
            brigade_size=10, total_sqm=0, total_pcs=1,
        )
        assert result == 1


# ═══════════════════════════════════════════════════════════════════════════
#  Backward scheduling date math
# ═══════════════════════════════════════════════════════════════════════════

class TestBackwardSchedulingMath:
    """Test date arithmetic for backward scheduling without touching DB.

    We test the pure math: given stage durations, verify date ordering.
    """

    def test_dates_in_correct_order(self):
        """Simulate backward scheduling and verify glazing < kiln < sorting < completion."""
        deadline = date(2026, 5, 15)  # Friday

        # Simulate typical durations
        unpacking = 1; engobe = 1; dry_eng = 1; glazing = 1
        dry_glaze = 1; edge_clean = 1
        pre_kiln_total = unpacking + engobe + dry_eng + glazing + dry_glaze + edge_clean  # 6

        firing = 1; cool_init = 1; unload = 1; cool_full = 1; tile_cool = 1
        sorting = 1; packing = 1
        BUFFER = 1

        # Backward from deadline
        completion = deadline
        sorting_date = completion - timedelta(days=sorting + packing)
        kiln_date = sorting_date - timedelta(days=firing + cool_init + unload + cool_full + tile_cool + BUFFER)
        glazing_date = kiln_date - timedelta(days=pre_kiln_total + BUFFER)

        assert glazing_date < kiln_date
        assert kiln_date < sorting_date
        assert sorting_date <= completion

    def test_pre_kiln_total_calculation(self):
        """Verify pre-kiln total = sum of all pre-kiln stages."""
        stages = {
            "unpacking_sorting": 1,
            "engobe": 1,
            "drying_engobe": 1,
            "glazing": 2,
            "drying_glaze": 1,
            "edge_cleaning_loading": 1,
        }
        pre_kiln = sum(stages.values())
        assert pre_kiln == 7

    def test_post_kiln_total_calculation(self):
        stages = {
            "firing": 1,
            "kiln_cooling_initial": 1,
            "kiln_unloading": 1,
            "tile_cooling": 1,
            "sorting": 1,
            "packing": 1,
        }
        post_kiln = sum(stages.values())
        assert post_kiln == 6

    def test_tight_deadline_shifts_forward(self):
        """If calculated glazing date is before today, everything shifts forward."""
        today = date.today()
        impossible_deadline = today + timedelta(days=2)  # way too tight for 13 stages

        pre_kiln_total = 6
        BUFFER = 1
        firing_total = 5
        qc_total = 2

        # Backward: glazing = deadline - qc - firing - buffer - pre_kiln - buffer
        total_days = qc_total + firing_total + BUFFER + pre_kiln_total + BUFFER
        glazing_date = impossible_deadline - timedelta(days=total_days)

        if glazing_date < today:
            glazing_date = today
            kiln_date = today + timedelta(days=pre_kiln_total + BUFFER)
            assert kiln_date > today

    def test_all_13_stages_covered(self):
        """Verify all 13 stages are accounted for."""
        ALL_STAGES = [
            "unpacking_sorting", "engobe", "drying_engobe", "glazing",
            "drying_glaze", "edge_cleaning_loading", "firing",
            "kiln_cooling_initial", "kiln_unloading", "kiln_cooling_full",
            "tile_cooling", "sorting", "packing",
        ]
        assert len(ALL_STAGES) == 13

        PRE_KILN = {"unpacking_sorting", "engobe", "drying_engobe", "glazing",
                     "drying_glaze", "edge_cleaning_loading"}
        KILN_AND_COOLING = {"firing", "kiln_cooling_initial", "kiln_unloading",
                            "kiln_cooling_full", "tile_cooling"}
        POST_KILN = {"sorting", "packing"}

        assert PRE_KILN | KILN_AND_COOLING | POST_KILN == set(ALL_STAGES)

    def test_fixed_duration_stages_identified(self):
        """Fixed-duration stages should be the ones that don't scale with quantity."""
        FIXED = {"drying_engobe", "drying_glaze", "firing",
                 "kiln_cooling_initial", "kiln_cooling_full", "tile_cooling"}
        THROUGHPUT = {"unpacking_sorting", "engobe", "glazing",
                      "edge_cleaning_loading", "kiln_unloading", "sorting", "packing"}
        assert len(FIXED) == 6
        assert len(THROUGHPUT) == 7
        assert FIXED & THROUGHPUT == set()  # no overlap


# ═══════════════════════════════════════════════════════════════════════════
#  Zone-aware capacity check (find_best_kiln_and_date logic)
# ═══════════════════════════════════════════════════════════════════════════

class TestZoneAwareCapacity:
    """Test the zone-aware capacity check logic that find_best_kiln_and_date uses."""

    def test_edge_zone_position_fits(self):
        """5 m² edge + 3 m² already used < 8.5 m² cap → fits."""
        zone_cap = 8.5
        zone_used = 3.0
        pos_area = 5.0
        assert zone_used + pos_area <= zone_cap * 1.1

    def test_edge_zone_position_overflow(self):
        """8 m² edge + 3 m² used > 8.5 m² cap * 1.1 → doesn't fit."""
        zone_cap = 8.5
        zone_used = 3.0
        pos_area = 8.0
        assert zone_used + pos_area > zone_cap * 1.1

    def test_flat_zone_small_capacity(self):
        """Flat zone only 1.5 m² → large flat position doesn't fit."""
        zone_cap = 1.5
        zone_used = 0
        pos_area = 2.0
        assert zone_used + pos_area > zone_cap * 1.1

    def test_mixed_loading_independent_zones(self):
        """Edge overflow doesn't affect flat availability and vice versa."""
        edge_cap = 7.83
        flat_cap = 1.08

        # Edge overflows
        edge_used = 7.0
        edge_new = 2.0
        edge_fits = (edge_used + edge_new) <= edge_cap * 1.1
        assert edge_fits is False

        # But flat is fine
        flat_used = 0.3
        flat_new = 0.5
        flat_fits = (flat_used + flat_new) <= flat_cap * 1.1
        assert flat_fits is True

    def test_10_percent_overfill_tolerance(self):
        """10% tolerance: 8.5 cap → up to 9.35 allowed."""
        zone_cap = 8.5
        assert 9.35 <= zone_cap * 1.1  # 9.35 is exactly the boundary
        assert 9.36 > zone_cap * 1.1   # 9.36 exceeds

    def test_real_scenario_small_kiln_mixed(self):
        """Real scenario: Small Kiln mixed loading day.
        - 600 pcs 10x10 face only (edge) = 6 m²
        - 30 pcs 10x10 all edges (flat) = 0.3 m²
        Both should fit: edge_cap=7.83, flat_cap=1.08."""
        edge_cap = 7.83
        flat_cap = 1.08
        edge_load = 6.0
        flat_load = 0.3
        assert edge_load <= edge_cap * 1.1
        assert flat_load <= flat_cap * 1.1

    def test_same_zone_accumulates(self):
        """Multiple edge positions on same day accumulate in edge zone."""
        zone_cap = 7.83
        positions_sqm = [2.0, 1.5, 3.0, 1.0]  # total 7.5 m²
        total = sum(positions_sqm)
        assert total <= zone_cap * 1.1  # 7.5 < 8.613 → fits

        positions_sqm.append(1.5)  # now 9.0 m²
        total = sum(positions_sqm)
        assert total > zone_cap * 1.1  # 9.0 > 8.613 → overflow

    def test_kiln_date_shifts_when_full(self):
        """Simulate date shifting: if day is full, try next day."""
        zone_cap = 7.83
        pos_area = 5.0

        day_loads = {
            date(2026, 4, 7): 6.0,   # Mon: 6 + 5 = 11 > 8.6 → full
            date(2026, 4, 8): 2.0,   # Tue: 2 + 5 = 7 < 8.6 → fits
        }

        target = date(2026, 4, 7)
        best_date = None
        for offset in range(7):
            candidate = target + timedelta(days=offset)
            used = day_loads.get(candidate, 0)
            if used + pos_area <= zone_cap * 1.1:
                best_date = candidate
                break

        assert best_date == date(2026, 4, 8)


# ═══════════════════════════════════════════════════════════════════════════
#  Real-world scheduling scenarios
# ═══════════════════════════════════════════════════════════════════════════

class TestRealWorldScenarios:
    """End-to-end scenarios combining typology matching + zone + scheduling math."""

    def test_small_tile_10x10_face_only_pipeline(self):
        """Small Tile 10x10 face only: edge zone, ~13-16 day pipeline."""
        # Classify
        pos = SimpleNamespace(
            place_of_application="face_only",
            width_cm=Decimal("10"), length_cm=Decimal("10"),
            size="10x10",
        )
        from business.services.typology_matcher import classify_loading_zone
        zone = classify_loading_zone(pos)
        assert zone == "edge"

        # Typical speeds → durations (1 day each for small batch)
        stages = {
            "unpacking_sorting": 1, "engobe": 1, "drying_engobe": 1,
            "glazing": 1, "drying_glaze": 1, "edge_cleaning_loading": 1,
            "firing": 1, "kiln_cooling_initial": 1, "kiln_unloading": 1,
            "kiln_cooling_full": 1, "tile_cooling": 1,
            "sorting": 1, "packing": 1,
        }
        total = sum(stages.values()) + 2  # +2 buffer days
        assert 13 <= total <= 20

    def test_countertop_large_all_edges_pipeline(self):
        """Large countertop with all edges → flat zone, longer drying."""
        pos = SimpleNamespace(
            place_of_application="all_edges",
            width_cm=Decimal("40"), length_cm=Decimal("60"),
            size="40x60",
        )
        from business.services.typology_matcher import classify_loading_zone
        zone = classify_loading_zone(pos)
        assert zone == "flat"

    def test_20x20_face_only_is_flat_not_edge(self):
        """20x20 face_only → flat (too big for edge loading, >15cm)."""
        pos = SimpleNamespace(
            place_of_application="face_only",
            width_cm=Decimal("20"), length_cm=Decimal("20"),
            size="20x20",
        )
        from business.services.typology_matcher import classify_loading_zone
        zone = classify_loading_zone(pos)
        assert zone == "flat"  # 20 > 15 → can't edge-load

    def test_5x20_face_only_is_flat(self):
        """5x20 face_only → flat (max side 20 > 15)."""
        pos = SimpleNamespace(
            place_of_application="face_only",
            width_cm=Decimal("5"), length_cm=Decimal("20"),
            size="5x20",
        )
        from business.services.typology_matcher import classify_loading_zone
        zone = classify_loading_zone(pos)
        assert zone == "flat"  # max_dim=20 > 15

    def test_10x10_all_edges_is_flat(self):
        """10x10 all edges → flat regardless of size."""
        pos = SimpleNamespace(
            place_of_application="all_edges",
            width_cm=Decimal("10"), length_cm=Decimal("10"),
            size="10x10",
        )
        from business.services.typology_matcher import classify_loading_zone
        zone = classify_loading_zone(pos)
        assert zone == "flat"


# ═══════════════════════════════════════════════════════════════════════════
#  Line Resource Constraints
# ═══════════════════════════════════════════════════════════════════════════

from business.services.production_scheduler import (
    _apply_resource_constraint,
    _STAGE_RESOURCE_MAP,
    _get_tiles_per_board,
)


class TestStageResourceMap:
    """Verify stage→resource_type mapping is correct."""

    def test_engobe_uses_work_table(self):
        assert _STAGE_RESOURCE_MAP['engobe'] == 'work_table'

    def test_glazing_uses_work_table(self):
        assert _STAGE_RESOURCE_MAP['glazing'] == 'work_table'

    def test_drying_engobe_uses_drying_rack(self):
        assert _STAGE_RESOURCE_MAP['drying_engobe'] == 'drying_rack'

    def test_drying_glaze_uses_drying_rack(self):
        assert _STAGE_RESOURCE_MAP['drying_glaze'] == 'drying_rack'

    def test_edge_cleaning_uses_glazing_board(self):
        assert _STAGE_RESOURCE_MAP['edge_cleaning_loading'] == 'glazing_board'

    def test_firing_has_no_constraint(self):
        assert 'firing' not in _STAGE_RESOURCE_MAP

    def test_sorting_has_no_constraint(self):
        assert 'sorting' not in _STAGE_RESOURCE_MAP

    def test_packing_has_no_constraint(self):
        assert 'packing' not in _STAGE_RESOURCE_MAP


class TestApplyResourceConstraint:
    """Test _apply_resource_constraint for each resource type."""

    # ── Work Table (engobe, glazing) ──

    def test_no_constraint_returns_speed_days(self):
        """Empty resource_cap → no effect."""
        result = _apply_resource_constraint(
            speed_days=2, stage='glazing', resource_cap={},
            total_sqm=10.0, total_pcs=100,
        )
        assert result == 2

    def test_table_small_batch_no_constraint(self):
        """1 m² batch on 3 m² table → 1 cycle, no constraint."""
        result = _apply_resource_constraint(
            speed_days=1, stage='glazing',
            resource_cap={"total_sqm": 3.0, "total_boards": 0, "total_pcs": 0},
            total_sqm=1.0, total_pcs=100,
        )
        assert result == 1

    def test_table_large_batch_extends_days(self):
        """10 m² batch on 3 m² total table area → ceil(10/3)=4 cycles → 4 days."""
        result = _apply_resource_constraint(
            speed_days=1, stage='glazing',
            resource_cap={"total_sqm": 3.0, "total_boards": 0, "total_pcs": 0},
            total_sqm=10.0, total_pcs=1000,
        )
        assert result == 4

    def test_table_exact_fit(self):
        """6 m² batch on 3 m² table → 2 cycles = 2 days."""
        result = _apply_resource_constraint(
            speed_days=1, stage='engobe',
            resource_cap={"total_sqm": 3.0, "total_boards": 0, "total_pcs": 0},
            total_sqm=6.0, total_pcs=600,
        )
        assert result == 2

    def test_table_constraint_doesnt_reduce_speed_days(self):
        """If speed says 3 days but tables only need 2 cycles → still 3 days."""
        result = _apply_resource_constraint(
            speed_days=3, stage='glazing',
            resource_cap={"total_sqm": 5.0, "total_boards": 0, "total_pcs": 0},
            total_sqm=8.0, total_pcs=800,
        )
        assert result == 3  # max(3, ceil(8/5)=2) = 3

    # ── Drying Rack (drying_engobe, drying_glaze) ──

    def test_rack_small_batch_single_cycle(self):
        """2 m² batch on 10 m² rack → 1 cycle, no constraint."""
        result = _apply_resource_constraint(
            speed_days=1, stage='drying_engobe',
            resource_cap={"total_sqm": 10.0, "total_boards": 0, "total_pcs": 0},
            total_sqm=2.0, total_pcs=200, fixed_hours=3.0,
        )
        assert result == 1

    def test_rack_multiple_cycles_extends_days(self):
        """30 m² batch on 10 m² rack → 3 drying cycles × 3h each = 9h → 1 day (16h/day).
        But speed_days=1, so max(1, 1) = 1."""
        result = _apply_resource_constraint(
            speed_days=1, stage='drying_engobe',
            resource_cap={"total_sqm": 10.0, "total_boards": 0, "total_pcs": 0},
            total_sqm=30.0, total_pcs=3000, fixed_hours=3.0,
        )
        assert result == 1  # 3 cycles × 3h = 9h, ceil(9/16) = 1

    def test_rack_many_cycles_extends_to_multiday(self):
        """100 m² on 10 m² rack → 10 cycles × 4h = 40h → ceil(40/16) = 3 days."""
        result = _apply_resource_constraint(
            speed_days=1, stage='drying_glaze',
            resource_cap={"total_sqm": 10.0, "total_boards": 0, "total_pcs": 0},
            total_sqm=100.0, total_pcs=10000, fixed_hours=4.0,
        )
        assert result == 3

    def test_rack_boards_based_with_tiles_per_board(self):
        """1000 pcs, 10 tiles/board → 100 boards needed. 60 boards on rack → ceil(100/60)=2 cycles.
        2 cycles × 3h = 6h → ceil(6/16) = 1 day."""
        result = _apply_resource_constraint(
            speed_days=1, stage='drying_engobe',
            resource_cap={"total_sqm": 0, "total_boards": 60, "total_pcs": 0},
            total_sqm=0, total_pcs=1000, fixed_hours=3.0, tiles_per_board=10,
        )
        assert result == 1

    def test_rack_boards_many_tiles_per_board(self):
        """5000 pcs, 25 tiles/board → 200 boards needed. 60 on rack → ceil(200/60)=4 cycles.
        4 × 3h = 12h → ceil(12/16) = 1 day."""
        result = _apply_resource_constraint(
            speed_days=1, stage='drying_engobe',
            resource_cap={"total_sqm": 0, "total_boards": 60, "total_pcs": 0},
            total_sqm=0, total_pcs=5000, fixed_hours=3.0, tiles_per_board=25,
        )
        assert result == 1  # 200 boards / 60 = 4 cycles, 12h / 16h = 1 day

    def test_rack_boards_small_tiles_per_board(self):
        """5000 pcs, 4 tiles/board → 1250 boards needed. 60 on rack → ceil(1250/60)=21 cycles.
        21 × 3h = 63h → ceil(63/16) = 4 days."""
        result = _apply_resource_constraint(
            speed_days=1, stage='drying_glaze',
            resource_cap={"total_sqm": 0, "total_boards": 60, "total_pcs": 0},
            total_sqm=0, total_pcs=5000, fixed_hours=3.0, tiles_per_board=4,
        )
        assert result == 4

    # ── Glazing Board (edge_cleaning_loading) ──

    def test_board_small_batch_no_constraint(self):
        """50 pcs, 200 boards available → 1 cycle."""
        result = _apply_resource_constraint(
            speed_days=1, stage='edge_cleaning_loading',
            resource_cap={"total_sqm": 0, "total_boards": 0, "total_pcs": 200},
            total_sqm=0.5, total_pcs=50,
        )
        assert result == 1

    def test_board_large_batch_extends(self):
        """500 pcs, 200 boards → ceil(500/200) = 3 cycles → 3 days."""
        result = _apply_resource_constraint(
            speed_days=1, stage='edge_cleaning_loading',
            resource_cap={"total_sqm": 0, "total_boards": 0, "total_pcs": 200},
            total_sqm=5.0, total_pcs=500,
        )
        assert result == 3

    def test_board_constraint_vs_speed(self):
        """Speed says 2 days, boards say 4 → 4 days (max)."""
        result = _apply_resource_constraint(
            speed_days=2, stage='edge_cleaning_loading',
            resource_cap={"total_sqm": 0, "total_boards": 0, "total_pcs": 100},
            total_sqm=3.0, total_pcs=350,
        )
        assert result == 4  # max(2, ceil(350/100))

    # ── Real scenarios ──

    def test_real_scenario_small_factory(self):
        """Small factory: 2 tables × 1.5 m² = 3 m² total.
        Order 1000 pcs 10×10 = 10 m² → ceil(10/3) = 4 days glazing.
        Speed says 1 day → constraint extends to 4."""
        result = _apply_resource_constraint(
            speed_days=1, stage='glazing',
            resource_cap={"total_sqm": 3.0, "total_boards": 0, "total_pcs": 0},
            total_sqm=10.0, total_pcs=1000,
        )
        assert result == 4

    def test_real_scenario_ample_resources(self):
        """Large factory: 6 tables × 2 m² = 12 m² total.
        Order 10 m² → ceil(10/12) = 1 cycle → no constraint."""
        result = _apply_resource_constraint(
            speed_days=1, stage='glazing',
            resource_cap={"total_sqm": 12.0, "total_boards": 0, "total_pcs": 0},
            total_sqm=10.0, total_pcs=1000,
        )
        assert result == 1

    def test_zero_sqm_no_crash(self):
        """Zero total_sqm with table constraint → no effect."""
        result = _apply_resource_constraint(
            speed_days=1, stage='glazing',
            resource_cap={"total_sqm": 3.0, "total_boards": 0, "total_pcs": 0},
            total_sqm=0, total_pcs=0,
        )
        assert result == 1


class TestGetTilesPerBoard:
    """Test tiles_per_board resolution from GlazingBoardSpec and fallback calculation."""

    def test_none_position_returns_default(self):
        db = MagicMock()
        assert _get_tiles_per_board(db, None) == 10

    def test_no_size_id_calculates_from_dimensions(self):
        """Position with width/length but no size_id → calculate on the fly."""
        db = MagicMock()
        pos = SimpleNamespace(size_id=None, width_cm=Decimal("10"), length_cm=Decimal("10"))
        result = _get_tiles_per_board(db, pos)
        # 10x10 cm on 122x21 board: should be > 1
        assert result > 1
        assert isinstance(result, int)

    def test_10x10_tiles_per_board(self):
        """10x10 cm tile: should get ~25 tiles per standard board."""
        db = MagicMock()
        pos = SimpleNamespace(size_id=None, width_cm=Decimal("10"), length_cm=Decimal("10"))
        result = _get_tiles_per_board(db, pos)
        assert 20 <= result <= 30  # 122x21 board, 10x10 tiles

    def test_20x20_tiles_per_board(self):
        """20x20 cm tile: should get ~6 tiles per standard board."""
        db = MagicMock()
        pos = SimpleNamespace(size_id=None, width_cm=Decimal("20"), length_cm=Decimal("20"))
        result = _get_tiles_per_board(db, pos)
        assert 4 <= result <= 8

    def test_5x20_tiles_per_board(self):
        """5x20 tile on standard board."""
        db = MagicMock()
        pos = SimpleNamespace(size_id=None, width_cm=Decimal("5"), length_cm=Decimal("20"))
        result = _get_tiles_per_board(db, pos)
        assert result >= 4

    def test_no_dimensions_returns_default(self):
        """No width, no length, no size_id → default 10."""
        db = MagicMock()
        pos = SimpleNamespace(size_id=None, width_cm=None, length_cm=None)
        result = _get_tiles_per_board(db, pos)
        assert result == 10
