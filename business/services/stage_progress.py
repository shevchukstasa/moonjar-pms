"""
Stage progression mapping — single source of truth for "which stages
has a position already passed?".

Used by:
  - business/planning_engine/scheduler.py::generate_production_schedule
    (calendar view — hide finished stages from future calendar days)
  - api/routers/schedule.py::get_daily_plan
    (Plan vs Fact view — same filter so the two views agree)

See docs/BUSINESS_LOGIC_FULL.md §4 →
  "Отображение графика: скрытие уже выполненных стадий"
"""

from __future__ import annotations


# Canonical pipeline order. Index = "stage number" used for comparison.
STAGE_INDEX: dict[str, int] = {
    "unpacking_sorting":     1,
    "engobe":                2,
    "drying_engobe":         3,
    "glazing":               4,
    "drying_glaze":          5,
    "edge_cleaning_loading": 6,
    "kiln_loading":          7,
    "firing":                8,
    "cooling":               9,
    "unloading":            10,
    "sorting":              11,
    "packing":              12,
}


# How many stages each PositionStatus has already completed. 0 = nothing
# done yet, 12 = whole pipeline finished. Keys are the lowercase string
# values of api.enums.PositionStatus.
STATUS_COMPLETED_STAGE_INDEX: dict[str, int] = {
    # Pre-production — nothing physically done
    "planned":                       0,
    "insufficient_materials":        0,
    "awaiting_recipe":               0,
    "awaiting_stencil_silkscreen":   0,
    "awaiting_color_matching":       0,
    "awaiting_size_confirmation":    0,
    "awaiting_consumption_data":     0,
    # Through engobe
    "engobe_applied":                2,
    "engobe_check":                  3,
    "sent_to_glazing":               3,
    "awaiting_reglaze":              3,
    # Glazing done
    "glazed":                        4,
    # Through edge cleaning, ready for kiln
    "pre_kiln_check":                6,
    # In kiln / fired
    "loaded_in_kiln":                7,
    "refire":                        7,
    "fired":                         8,
    # Past cooling / unloading
    "transferred_to_sorting":       10,
    # Sorted
    "sorted":                       11,
    "sent_to_quality_check":        11,
    "quality_check_done":           11,
    "blocked_by_qm":                11,
    # Terminal
    "packed":                       12,
    "ready_for_shipment":           12,
    "shipped":                      12,
    "merged":                       12,
    "cancelled":                    12,
}


def position_completed_index(position) -> int:
    """How many stages this position has already completed, per its status."""
    st = getattr(position, "status", None)
    if hasattr(st, "value"):
        st = st.value
    return STATUS_COMPLETED_STAGE_INDEX.get(str(st or "").lower(), 0)


def stage_already_done(position, stage_name: str) -> bool:
    """True when the named stage has already finished for this position
    based on its current status — i.e. should be hidden from any future-
    facing schedule view (calendar, Plan vs Fact, etc.)."""
    idx = STAGE_INDEX.get(stage_name)
    if idx is None:
        return False
    return idx <= position_completed_index(position)
