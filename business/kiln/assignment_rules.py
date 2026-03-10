"""
Per-kiln loading rules (JSONB-based) and co-firing validation.
See BUSINESS_LOGIC.md §30–§31, §37.
"""
from uuid import UUID
from typing import Optional

from sqlalchemy.orm import Session

# Default max temperature spread — overridable via kiln_constants table
_DEFAULT_COFIRING_MAX_TEMP_RANGE = 50  # °C


def get_loading_rules(db: Session, kiln_id: UUID) -> dict:
    """
    Load per-kiln JSONB rules from kiln_loading_rules table.

    Returns the rules dict (or system defaults when no row exists):
      gap_x_cm, gap_y_cm, air_gap_cm, shelf_thickness_cm,
      allowed_product_types, allowed_collections,
      edge_loading_allowed,
      max_edge_height_cm,           ← per-kiln configurable
      flat_on_edge_coefficient,     ← per-kiln configurable (default 0.30)
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
    1. Temperature range from glaze recipes (RecipeKilnConfig).
    2. Two-stage firing — warns when any position requires it.

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

    for pos in positions:
        recipe = getattr(pos, "recipe", None)
        if recipe is None:
            continue

        kiln_cfg = db.query(RecipeKilnConfig).filter(
            RecipeKilnConfig.recipe_id == recipe.id
        ).first()

        if kiln_cfg is None:
            continue

        if kiln_cfg.firing_temperature:
            temperatures.append(int(kiln_cfg.firing_temperature))

        if kiln_cfg.two_stage_firing:
            two_stage_count += 1

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

    if two_stage_count:
        warnings.append(
            f"{two_stage_count} position(s) require two-stage firing — "
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
