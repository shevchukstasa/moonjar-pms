"""
Per-kiln loading rules (JSONB-based) and co-firing validation.
See BUSINESS_LOGIC.md §30-§31, §37.

NOTE: Actual kiln capacity calculations (flat/edge loading, geometry,
filler tiles) live in business/kiln/capacity.py. This module provides:
  - get_loading_rules()   -- loads per-kiln JSONB rules (used by capacity.py)
  - validate_cofiring()   -- co-firing temperature compatibility check
  - get_rotation_rules()  -- factory-level kiln rotation configuration

Batch formation logic lives in business/services/batch_formation.py,
which calls capacity.py for geometry-based calculations and this module
for loading rules and co-firing validation.
"""
from uuid import UUID
from typing import Optional

from sqlalchemy.orm import Session

# Default max temperature spread — overridable via kiln_constants table
_DEFAULT_COFIRING_MAX_TEMP_RANGE = 50  # °C

# Gold tile standard firing temperature
_GOLD_FIRING_TEMPERATURE = 700  # °C


def get_loading_rules(db: Session, kiln_id: UUID) -> dict:
    """
    Load per-kiln JSONB rules from kiln_loading_rules table.

    Returns the rules dict (or system defaults when no row exists):
      gap_x_cm, gap_y_cm, air_gap_cm, shelf_thickness_cm,
      allowed_product_types, allowed_collections,
      edge_loading_allowed,
      max_edge_height_cm,           ← per-kiln configurable
      flat_on_edge_coefficient,     ← per-kiln configurable (default 0.30)
      filler_enabled,               ← enable/disable filler tile calculation (default True)
      filler_coefficient,           ← per-kiln configurable (default 0.50)
      min_space_to_fill_cm,         ← per-kiln configurable (default 21 cm)
      max_product_width_cm,
      max_product_height_cm
    """
    from api.models import KilnLoadingRule

    row = db.query(KilnLoadingRule).filter(KilnLoadingRule.kiln_id == kiln_id).first()
    if row and row.rules:
        return row.rules

    # System defaults — no per-kiln rules configured
    return {
        "gap_x_cm": 1.2,
        "gap_y_cm": 1.2,
        "air_gap_cm": 2.0,
        "shelf_thickness_cm": 3.0,
        "allowed_product_types": ["tile", "countertop", "sink", "3d"],
        "allowed_collections": [],
        "edge_loading_allowed": True,
        "max_edge_height_cm": None,          # None → global constant applies
        "flat_on_edge_coefficient": None,    # None → global constant applies
        "filler_enabled": True,              # disable to skip filler tile calculation
        "filler_coefficient": None,          # None → global constant applies
        "min_space_to_fill_cm": None,        # None → global constant applies
        "max_product_width_cm": None,
        "max_product_height_cm": None,
    }


def validate_cofiring(
    db: Session,
    positions: list,
    kiln_id: UUID,
    constants: Optional[dict] = None,
) -> dict:
    """
    Validate co-firing compatibility for a list of order positions.

    Temperature spread limit comes from constants['COFIRING_MAX_TEMP_RANGE']
    (configurable via kiln_constants table, default 50 °C).

    Checks:
    1. Temperature range from glaze recipes (RecipeKilnConfig) — all positions
       must have overlapping temperature ranges within the allowed spread.
    2. Two-stage firing — positions with two_stage_firing=True must only batch
       with other two-stage positions of the SAME two_stage_type.
    3. Gold tile (two_stage_type='gold', 700 °C) must be batched separately
       or only with other gold-compatible items (temp within spread of 700 °C).

    Returns:
      {ok, errors, warnings, min_temperature, max_temperature}
    """
    from api.models import RecipeKilnConfig

    c = constants or {}
    max_range = c.get("COFIRING_MAX_TEMP_RANGE", _DEFAULT_COFIRING_MAX_TEMP_RANGE)

    errors: list[str] = []
    warnings: list[str] = []
    temperatures: list[int] = []
    two_stage_count = 0
    two_stage_types: set[str] = set()
    non_two_stage_count = 0
    gold_count = 0

    for pos in positions:
        # Check two-stage firing from position-level flags
        is_two_stage = getattr(pos, "two_stage_firing", False)
        ts_type = getattr(pos, "two_stage_type", None)

        if is_two_stage:
            two_stage_count += 1
            if ts_type:
                two_stage_types.add(ts_type)
            if ts_type == "gold":
                gold_count += 1
        else:
            non_two_stage_count += 1

        # Get temperature from recipe kiln config
        recipe_id = getattr(pos, "recipe_id", None)
        if recipe_id is None:
            recipe = getattr(pos, "recipe", None)
            if recipe is not None:
                recipe_id = recipe.id

        if recipe_id is None:
            continue

        kiln_cfg = db.query(RecipeKilnConfig).filter(
            RecipeKilnConfig.recipe_id == recipe_id
        ).first()

        if kiln_cfg is None:
            continue

        if kiln_cfg.firing_temperature:
            temperatures.append(int(kiln_cfg.firing_temperature))

    min_temp = max_temp = None

    if temperatures:
        min_temp = min(temperatures)
        max_temp = max(temperatures)
        spread = max_temp - min_temp

        if spread > max_range:
            errors.append(
                f"Temperature range too wide for co-firing: "
                f"{min_temp}–{max_temp} °C "
                f"(spread {spread} °C exceeds limit of {max_range} °C)"
            )

    # Two-stage firing compatibility checks
    if two_stage_count > 0 and non_two_stage_count > 0:
        errors.append(
            f"Cannot mix two-stage firing positions ({two_stage_count}) with "
            f"standard firing positions ({non_two_stage_count}) in the same batch"
        )

    if len(two_stage_types) > 1:
        errors.append(
            f"Cannot mix different two-stage firing types in the same batch: "
            f"{', '.join(sorted(two_stage_types))}"
        )

    # Gold tile warning: gold fires at 700 °C which is very different
    # from standard firing temps (~1050-1200 °C)
    if gold_count > 0 and gold_count < len(positions):
        non_gold_temps = [
            t for t, p in zip(temperatures, positions)
            if getattr(p, "two_stage_type", None) != "gold"
        ]
        if non_gold_temps:
            for t in non_gold_temps:
                if abs(t - _GOLD_FIRING_TEMPERATURE) > max_range:
                    errors.append(
                        f"Gold tile (700 °C) is incompatible with position "
                        f"firing at {t} °C (exceeds {max_range} °C spread)"
                    )
                    break

    if two_stage_count and not errors:
        warnings.append(
            f"{two_stage_count} position(s) require two-stage firing "
            f"(type: {', '.join(sorted(two_stage_types)) or 'unspecified'}) — "
            "verify kiln schedule supports it"
        )

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "min_temperature": min_temp,
        "max_temperature": max_temp,
    }


def get_rotation_rules(db: Session, factory_id: UUID) -> dict:
    """
    Get configurable rotation rules per factory from factories.rotation_rules JSONB.
    See BUSINESS_LOGIC.md §37.
    """
    from api.models import Factory

    factory = db.query(Factory).filter(Factory.id == factory_id).first()
    if factory and factory.rotation_rules:
        return factory.rotation_rules

    return {
        "mode": "alternating",
        "priority_kiln_type": None,
        "skip_after_n_batches": None,
        "notes": "Default rotation — no factory-specific rules configured",
    }
