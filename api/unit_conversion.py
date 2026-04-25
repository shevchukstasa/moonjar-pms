"""
Unit Conversion Utility for Material ↔ Recipe consumption calculations.

Key concept:
- Recipes define consumption in ml/m² (milliliters per square meter)
- Materials can be stored in different units: kg, g, L, ml, pcs, m, m²
- specific_gravity (SG) bridges volume ↔ weight: 1 ml × SG = SG grams

Conversion matrix (all intermediated through ml):
  ml → g   = ml × specific_gravity
  ml → kg  = ml × specific_gravity / 1000
  ml → L   = ml / 1000
  g  → ml  = g / specific_gravity
  g  → kg  = g / 1000
  kg → ml  = kg × 1000 / specific_gravity
  kg → g   = kg × 1000
  L  → ml  = L × 1000
  L  → g   = L × 1000 × specific_gravity
  L  → kg  = L × specific_gravity
"""

from decimal import Decimal
from typing import Optional
import logging

_logger = logging.getLogger("moonjar.unit_conversion")


class UnitConversionError(Exception):
    """Raised when conversion between units is impossible."""
    pass


# Units that measure volume
VOLUME_UNITS = {"ml", "l"}
# Units that measure weight/mass
WEIGHT_UNITS = {"kg", "g"}
# All convertible units
CONVERTIBLE_UNITS = VOLUME_UNITS | WEIGHT_UNITS


def convert_units(
    value: float,
    from_unit: str,
    to_unit: str,
    specific_gravity: Optional[float] = None,
) -> float:
    """
    Convert a value between material units.

    Args:
        value: The numeric value to convert
        from_unit: Source unit ('ml', 'l', 'g', 'kg')
        to_unit: Target unit ('ml', 'l', 'g', 'kg')
        specific_gravity: Required for volume↔weight conversions (e.g. 1.45)

    Returns:
        Converted value as float

    Raises:
        UnitConversionError: If conversion is not possible
    """
    from_unit = from_unit.lower().strip()
    to_unit = to_unit.lower().strip()

    if from_unit == to_unit:
        return value

    if from_unit not in CONVERTIBLE_UNITS:
        raise UnitConversionError(
            f"Cannot convert from '{from_unit}'. Supported: {', '.join(sorted(CONVERTIBLE_UNITS))}"
        )
    if to_unit not in CONVERTIBLE_UNITS:
        raise UnitConversionError(
            f"Cannot convert to '{to_unit}'. Supported: {', '.join(sorted(CONVERTIBLE_UNITS))}"
        )

    # Step 1: Convert from_unit → ml (canonical volume unit)
    ml_value = _to_ml(value, from_unit, specific_gravity)

    # Step 2: Convert ml → to_unit
    return _from_ml(ml_value, to_unit, specific_gravity)


def _to_ml(value: float, unit: str, sg: Optional[float]) -> float:
    """Convert any supported unit to milliliters."""
    if unit == "ml":
        return value
    elif unit == "l":
        return value * 1000.0
    elif unit == "g":
        if not sg or sg <= 0:
            raise UnitConversionError(
                "specific_gravity is required to convert grams → ml"
            )
        return value / sg
    elif unit == "kg":
        if not sg or sg <= 0:
            raise UnitConversionError(
                "specific_gravity is required to convert kilograms → ml"
            )
        return (value * 1000.0) / sg
    else:
        raise UnitConversionError(f"Unsupported unit: {unit}")


def _from_ml(ml: float, unit: str, sg: Optional[float]) -> float:
    """Convert milliliters to any supported unit."""
    if unit == "ml":
        return ml
    elif unit == "l":
        return ml / 1000.0
    elif unit == "g":
        if not sg or sg <= 0:
            raise UnitConversionError(
                "specific_gravity is required to convert ml → grams"
            )
        return ml * sg
    elif unit == "kg":
        if not sg or sg <= 0:
            raise UnitConversionError(
                "specific_gravity is required to convert ml → kilograms"
            )
        return (ml * sg) / 1000.0
    else:
        raise UnitConversionError(f"Unsupported unit: {unit}")


# ────────────────────────────────────────────────────────────────
# Recipe ↔ Stock unit bridge helpers
# ────────────────────────────────────────────────────────────────

def get_calculation_unit(rm_unit: str) -> str:
    """Return the physical unit that _calculate_required() produces.

    - g_per_100g  → formula outputs grams ('g')
    - per_sqm     → rate is ml/m², result is milliliters ('ml')
    - per_piece   → count ('pcs')
    """
    rm_unit_lower = (rm_unit or "").lower().strip()
    if rm_unit_lower == "g_per_100g":
        return "g"
    if rm_unit_lower == "per_sqm":
        return "ml"
    return "pcs"


def convert_to_stock_unit(
    amount: Decimal,
    calc_unit: str,
    stock_unit: str,
    specific_gravity: Optional[Decimal] = None,
    material_name: str = "",
) -> Decimal:
    """Convert a recipe-calculated amount to the material's stock unit.

    If units already match or conversion is not applicable (e.g. pcs→pcs),
    returns the original amount unchanged.

    NB: pcs ↔ m² is NOT done here — it requires geometry (shape +
    dimensions) which lives in the Material's Size row, not in this
    helper. Use `convert_pcs_to_sqm()` / `convert_sqm_to_pcs()` below
    when the geometry is available. If you call convert_to_stock_unit
    with pcs↔non-pcs units the value is returned as-is and a warning is
    logged so the caller notices.
    """
    calc_u = calc_unit.lower().strip()
    stock_u = stock_unit.lower().strip()

    # Same unit — no conversion needed
    if calc_u == stock_u:
        return amount

    # pcs is not convertible to weight/volume here. The right path for
    # pcs ↔ m² goes through convert_pcs_to_sqm/sqm_to_pcs which need
    # tile geometry — see BUSINESS_LOGIC_FULL §29.
    if calc_u == "pcs" or stock_u == "pcs":
        if {calc_u, stock_u} == {"pcs", "m2"}:
            _logger.warning(
                "UNIT_CONVERT_NEED_GEOMETRY | material=%s | %s->%s | "
                "pcs↔m² requires shape/size — use convert_pcs_to_sqm; "
                "returning raw value, this is almost certainly wrong",
                material_name, calc_u, stock_u,
            )
        return amount

    # Prepare specific_gravity as float for convert_units
    sg = float(specific_gravity) if specific_gravity and specific_gravity > 0 else 1.0

    try:
        converted = convert_units(float(amount), calc_u, stock_u, specific_gravity=sg)
        _logger.info(
            "UNIT_CONVERT | material=%s | %.4f %s -> %.4f %s (SG=%.3f)",
            material_name, float(amount), calc_u, converted, stock_u, sg,
        )
        return Decimal(str(converted))
    except UnitConversionError as exc:
        _logger.warning(
            "UNIT_CONVERT_FAIL | material=%s | %s->%s | %s -- using raw value",
            material_name, calc_u, stock_u, exc,
        )
        return amount


# ────────────────────────────────────────────────────────────────
# pcs ↔ m² with geometry (BUSINESS_LOGIC_FULL §29)
# ────────────────────────────────────────────────────────────────

class GeometryMissingError(Exception):
    """Raised when pcs↔m² conversion is requested but the geometry of
    the material is incomplete (no width/height/diameter). Loud failure
    is preferred over silently returning 0 — see how the bug bit prod
    on 25 Apr 2026 (12 round D29.2 tables looked like they had no stock
    because the rectangle path computed 58 cm² per piece instead of
    670 cm²)."""


def _tile_area_sqm_from_geometry(
    shape: Optional[str],
    width_mm: Optional[float],
    height_mm: Optional[float],
    diameter_mm: Optional[float] = None,
) -> float:
    """Compute the area of ONE tile in m² from its shape + dimensions.

    Wrapper around business.services.surface_area.calculate_glazeable_surface
    so the formulas stay in ONE place. We can't import surface_area at
    module top-level (api/ → business/ would create a cycle when
    business/services/material_consumption.py imports from api/), so the
    import is local.

    Raises GeometryMissingError when not enough data to compute area.
    """
    sh = (shape or "rectangle").lower().strip()

    # round needs diameter (or width as fallback)
    if sh == "round":
        diam = diameter_mm or width_mm
        if not diam or diam <= 0:
            raise GeometryMissingError(
                f"round geometry requires diameter (got "
                f"diameter_mm={diameter_mm} width_mm={width_mm})"
            )
        # Use surface_area helper for consistency
        from business.services.surface_area import calculate_glazeable_surface
        L_cm = float(diam) / 10.0
        return calculate_glazeable_surface(
            shape="round", length_cm=L_cm, width_cm=L_cm,
        )

    # all other shapes need W and H
    if not width_mm or not height_mm:
        raise GeometryMissingError(
            f"{sh} geometry requires width_mm + height_mm "
            f"(got width_mm={width_mm} height_mm={height_mm})"
        )

    from business.services.surface_area import calculate_glazeable_surface
    L_cm = float(width_mm) / 10.0
    W_cm = float(height_mm) / 10.0
    return calculate_glazeable_surface(
        shape=sh, length_cm=L_cm, width_cm=W_cm,
    )


def convert_pcs_to_sqm(
    qty_pcs: float,
    shape: Optional[str],
    width_mm: Optional[float],
    height_mm: Optional[float],
    diameter_mm: Optional[float] = None,
) -> float:
    """Convert a piece count to m² given the tile geometry.

    Raises GeometryMissingError on incomplete inputs. Callers should
    catch this and either fall back gracefully (with a logged ERROR)
    or surface a hard validation failure to the user. NEVER swallow
    silently and return 0 — that's the bug we just fixed.
    """
    if qty_pcs is None or qty_pcs <= 0:
        return 0.0
    one = _tile_area_sqm_from_geometry(shape, width_mm, height_mm, diameter_mm)
    return float(qty_pcs) * one


def convert_sqm_to_pcs(
    qty_sqm: float,
    shape: Optional[str],
    width_mm: Optional[float],
    height_mm: Optional[float],
    diameter_mm: Optional[float] = None,
) -> float:
    """Inverse: how many pieces to cover qty_sqm of glaze area.

    Raises GeometryMissingError on incomplete inputs. Returns float so
    the caller can decide whether to round / ceil / floor.
    """
    if qty_sqm is None or qty_sqm <= 0:
        return 0.0
    one = _tile_area_sqm_from_geometry(shape, width_mm, height_mm, diameter_mm)
    if one <= 0:
        raise GeometryMissingError(
            "tile area is zero — refuse to divide by zero"
        )
    return float(qty_sqm) / one
