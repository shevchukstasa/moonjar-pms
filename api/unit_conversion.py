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

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional


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


def calculate_material_consumption(
    area_sqm: float,
    consumption_ml_per_sqm: float,
    material_unit: str,
    specific_gravity: Optional[float] = None,
) -> float:
    """
    Calculate how much material to consume/reserve for a given area.

    Example:
        Recipe says 850 ml/m², area is 2.5 m², material stored in kg, SG=1.45
        → 850 × 2.5 = 2125 ml → 2125 × 1.45 / 1000 = 3.08125 kg

    Args:
        area_sqm: Area in square meters
        consumption_ml_per_sqm: Recipe consumption rate (ml per m²)
        material_unit: Unit the material is stored in ('kg', 'g', 'ml', 'l')
        specific_gravity: Required for weight-based materials

    Returns:
        Amount of material needed in material_unit
    """
    total_ml = area_sqm * consumption_ml_per_sqm
    return convert_units(total_ml, "ml", material_unit, specific_gravity)


def format_conversion_info(
    from_value: float,
    from_unit: str,
    to_value: float,
    to_unit: str,
    precision: int = 3,
) -> str:
    """Format a human-readable conversion string."""
    fv = round(from_value, precision)
    tv = round(to_value, precision)
    return f"{fv} {from_unit} = {tv} {to_unit}"
