"""
Surface Area Calculation Service — shape-aware glazeable surface per piece.

Used by:
- order_intake.py → calculate glazeable_sqm on position creation
- material_reservation.py → correct material requirements for non-rectangular shapes
- material_consumption.py → expected vs actual comparison

Formulas aligned with kiln capacity.py:_product_area() but extended for glaze consumption.
"""

from math import pi, sqrt
from decimal import Decimal
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def calculate_glazeable_surface(
    shape: str,
    length_cm: float,
    width_cm: float,
    depth_cm: float = 0,
    bowl_shape: Optional[str] = None,
    product_type: str = "tile",
) -> float:
    """Calculate glazeable surface area for ONE piece in m².

    Standard shapes (tiles, countertops, 3D):
        rectangle/square: L × W / 10000
        round:            π × (L/2)² / 10000
        triangle:         (L × W) / 2 / 10000
        octagon:          2 × (1 + √2) × s² / 10000  (regular octagon, s = side)
        freeform:         L × W / 10000 (bounding box, apply coefficient separately)

    Sinks (product_type='sink'):
        Flat area (top surface) + interior bowl surface.
        Bowl shapes:
        - parallelepiped: bottom (L×W) + 2 side walls (L×D + W×D)
        - half_oval:      approximate ellipsoidal interior
        - other:          flat area × 1.3 (default safe estimate)

    Args:
        shape: ShapeType value (rectangle, square, round, triangle, octagon, freeform)
        length_cm: Length in cm
        width_cm: Width in cm
        depth_cm: Depth in cm (sinks only)
        bowl_shape: Bowl shape (parallelepiped, half_oval, other) — sinks only
        product_type: ProductType value (tile, countertop, sink, 3d)

    Returns:
        Glazeable surface area in square meters (m²)
    """
    if length_cm <= 0 or width_cm <= 0:
        return 0.0

    L = float(length_cm)
    W = float(width_cm)
    D = float(depth_cm) if depth_cm else 0.0

    # 1. Calculate flat face area based on shape
    if shape == "round":
        # Circular: π × r²
        r = L / 2.0
        flat_area_cm2 = pi * r * r
    elif shape == "triangle":
        # Triangle: (base × height) / 2
        flat_area_cm2 = (L * W) / 2.0
    elif shape == "octagon":
        # Regular octagon: 2(1+√2) × s²
        # The "size" is typically the bounding dimension, so side = L / (1 + √2)
        s = L / (1 + sqrt(2))
        flat_area_cm2 = 2 * (1 + sqrt(2)) * s * s
    else:
        # rectangle, square, freeform — use bounding box
        flat_area_cm2 = L * W

    flat_area_sqm = flat_area_cm2 / 10000.0

    # 2. For sinks: add interior bowl surface
    if product_type == "sink" and D > 0:
        bowl_area_cm2 = _calculate_bowl_surface(L, W, D, bowl_shape)
        bowl_area_sqm = bowl_area_cm2 / 10000.0
        return round(flat_area_sqm + bowl_area_sqm, 4)

    return round(flat_area_sqm, 4)


def _calculate_bowl_surface(
    length_cm: float,
    width_cm: float,
    depth_cm: float,
    bowl_shape: Optional[str],
) -> float:
    """Calculate interior bowl surface area in cm².

    For sinks, the interior is glazed in addition to the top surface.
    """
    L, W, D = length_cm, width_cm, depth_cm

    if bowl_shape == "parallelepiped":
        # Rectangular bowl: bottom + 4 walls
        # Bottom is slightly smaller (assume ~80% of outer dims)
        inner_l = L * 0.8
        inner_w = W * 0.8
        bottom = inner_l * inner_w
        walls = 2 * (inner_l * D) + 2 * (inner_w * D)
        return bottom + walls

    elif bowl_shape == "half_oval":
        # Approximate half-ellipsoid interior
        # Surface area of half-ellipsoid ≈ π × (((a^p × b^p + a^p × c^p + b^p × c^p) / 3)^(1/p))
        # where a, b, c are semi-axes and p ≈ 1.6
        # Simplified: use average of ellipses
        a = L * 0.4  # semi-major
        b = W * 0.4  # semi-minor
        c = D * 0.9  # depth
        p = 1.6
        # Knud Thomsen's formula for surface of ellipsoid
        approx = (a**p * b**p + a**p * c**p + b**p * c**p) / 3.0
        if approx > 0:
            full_surface = 4 * pi * (approx ** (1.0 / p))
            return full_surface / 2.0  # half-ellipsoid
        return L * W  # fallback

    else:
        # Unknown bowl shape → conservative estimate: flat area × 0.8
        # (80% of the flat area added as interior surface)
        return L * W * 0.8


def get_shape_coefficient(
    db,
    shape: str,
    product_type: str = "tile",
) -> float:
    """Get consumption coefficient for a shape × product_type combination.

    Falls back to:
    1. Exact match (shape, product_type)
    2. Match (shape, 'tile') as default product_type
    3. Built-in defaults
    """
    from api.models import ShapeConsumptionCoefficient

    # Try exact match
    coeff = db.query(ShapeConsumptionCoefficient).filter(
        ShapeConsumptionCoefficient.shape == shape,
        ShapeConsumptionCoefficient.product_type == product_type,
    ).first()

    if coeff:
        return float(coeff.coefficient)

    # Try default product_type
    if product_type != "tile":
        coeff = db.query(ShapeConsumptionCoefficient).filter(
            ShapeConsumptionCoefficient.shape == shape,
            ShapeConsumptionCoefficient.product_type == "tile",
        ).first()
        if coeff:
            return float(coeff.coefficient)

    # Built-in fallbacks
    DEFAULTS = {
        "rectangle": 1.0,
        "square": 1.0,
        "round": pi / 4,       # ≈ 0.785
        "triangle": 0.5,
        "octagon": 2 * (1 + sqrt(2)) / (1 + sqrt(2)) ** 2,  # ≈ 0.828
        "freeform": 0.85,
    }
    return DEFAULTS.get(shape, 1.0)


def calculate_glazeable_sqm_for_position(db, position) -> Optional[Decimal]:
    """Calculate glazeable_sqm for a position, using dimensions or coefficients.

    Strategy:
    1. If length_cm and width_cm are available → exact calculation
    2. If only size string available → parse "WxH" → exact for standard shapes,
       coefficient for non-standard
    3. Fallback: quantity_sqm / quantity × coefficient
    """
    shape = getattr(position, "shape", None)
    shape_str = shape.value if hasattr(shape, "value") else str(shape or "rectangle")
    product_type = getattr(position, "product_type", None)
    pt_str = product_type.value if hasattr(product_type, "value") else str(product_type or "tile")

    length = getattr(position, "length_cm", None)
    width = getattr(position, "width_cm", None)
    depth = getattr(position, "depth_cm", None)
    bowl = getattr(position, "bowl_shape", None)

    # 1. Exact dimensions available
    if length and width and float(length) > 0 and float(width) > 0:
        area = calculate_glazeable_surface(
            shape=shape_str,
            length_cm=float(length),
            width_cm=float(width),
            depth_cm=float(depth) if depth else 0,
            bowl_shape=bowl,
            product_type=pt_str,
        )
        return Decimal(str(area))

    # 2. Parse size string "WxH" (e.g., "30x60", "10x10")
    size = getattr(position, "size", None)
    if size:
        import re
        m = re.match(r"(\d+)\s*[x×X]\s*(\d+)", str(size))
        if m:
            w_cm = float(m.group(1))
            h_cm = float(m.group(2))

            if shape_str in ("rectangle", "square"):
                # Exact for standard shapes
                area = calculate_glazeable_surface(
                    shape=shape_str,
                    length_cm=h_cm,
                    width_cm=w_cm,
                    product_type=pt_str,
                )
                return Decimal(str(area))
            else:
                # Non-standard shape: use bounding box × coefficient
                bounding_area_sqm = (w_cm * h_cm) / 10000.0
                coeff = get_shape_coefficient(db, shape_str, pt_str)
                return Decimal(str(round(bounding_area_sqm * coeff, 4)))

    # 3. Fallback: use existing quantity_sqm / quantity × coefficient
    qty_sqm = getattr(position, "quantity_sqm", None)
    qty = getattr(position, "quantity", None)
    if qty_sqm and qty and int(qty) > 0:
        area_per_piece = float(qty_sqm) / int(qty)
        coeff = get_shape_coefficient(db, shape_str, pt_str)
        return Decimal(str(round(area_per_piece * coeff, 4)))

    return None
