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


def calculate_area_from_dimensions(shape: str, dimensions: dict) -> Optional[float]:
    """Calculate area in cm² from shape type and dimensions dict.

    All dimension values are in centimeters.
    Returns area in cm² or None if insufficient data.

    Supported shapes and their required dimension keys:
        rectangle:            width_cm (or w), height_cm (or h)
        square:               width_cm (or side_cm or w)
        triangle:             side_a_cm (or a), side_b_cm (or b), side_c_cm (or c)  — Heron's formula
        circle / round:       diameter_cm (or d)
        oval:                 diameter1_cm (or d1), diameter2_cm (or d2)
        octagon:              width_cm (or w), height_cm (or h), cut_cm (or cut)
        trapezoid:            side_a_cm (or a), side_b_cm (or b), height_cm (or h)
        trapezoid_truncated:  side_a_cm (or a), side_b_cm (or b), height_cm (or h)
        rhombus:              diagonal1_cm (or d1), diagonal2_cm (or d2)
        parallelogram:        base_cm (or b), height_cm (or h)
        semicircle:           diameter_cm (or d)
        freeform:             manual_area_cm2 (or area)
    """
    if not dimensions or not isinstance(dimensions, dict):
        return None

    shape = shape.lower()

    if shape in ('rectangle',):
        w = dimensions.get('width_cm') or dimensions.get('w')
        h = dimensions.get('height_cm') or dimensions.get('h')
        if w and h:
            return float(w) * float(h)

    elif shape in ('square',):
        w = dimensions.get('width_cm') or dimensions.get('side_cm') or dimensions.get('w')
        if w:
            return float(w) * float(w)

    elif shape in ('triangle',):
        a = dimensions.get('side_a_cm') or dimensions.get('a')
        b = dimensions.get('side_b_cm') or dimensions.get('b')
        c = dimensions.get('side_c_cm') or dimensions.get('c')
        if a and b and c:
            a, b, c = float(a), float(b), float(c)
            p = (a + b + c) / 2
            area_sq = p * (p - a) * (p - b) * (p - c)
            return sqrt(max(area_sq, 0))

    elif shape in ('circle', 'round'):
        d = dimensions.get('diameter_cm') or dimensions.get('d')
        if d:
            return pi * (float(d) / 2) ** 2

    elif shape in ('oval',):
        d1 = dimensions.get('diameter1_cm') or dimensions.get('d1')
        d2 = dimensions.get('diameter2_cm') or dimensions.get('d2')
        if d1 and d2:
            return pi * (float(d1) / 2) * (float(d2) / 2)

    elif shape in ('octagon',):
        w = dimensions.get('width_cm') or dimensions.get('w')
        h = dimensions.get('height_cm') or dimensions.get('h')
        cut = dimensions.get('cut_cm') or dimensions.get('cut')
        if w and h and cut:
            return float(w) * float(h) - 4 * (0.5 * float(cut) ** 2)

    elif shape in ('trapezoid', 'trapezoid_truncated'):
        a = dimensions.get('side_a_cm') or dimensions.get('a')  # parallel side 1
        b = dimensions.get('side_b_cm') or dimensions.get('b')  # parallel side 2
        h = dimensions.get('height_cm') or dimensions.get('h')
        if a and b and h:
            return (float(a) + float(b)) / 2 * float(h)

    elif shape in ('rhombus',):
        d1 = dimensions.get('diagonal1_cm') or dimensions.get('d1')
        d2 = dimensions.get('diagonal2_cm') or dimensions.get('d2')
        if d1 and d2:
            return (float(d1) * float(d2)) / 2

    elif shape in ('parallelogram',):
        b = dimensions.get('base_cm') or dimensions.get('b')
        h = dimensions.get('height_cm') or dimensions.get('h')
        if b and h:
            return float(b) * float(h)

    elif shape in ('semicircle',):
        d = dimensions.get('diameter_cm') or dimensions.get('d')
        if d:
            return pi * (float(d) / 2) ** 2 / 2

    elif shape in ('freeform',):
        manual = dimensions.get('manual_area_cm2') or dimensions.get('area')
        if manual:
            return float(manual)

    return None


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

    After base face area is computed, adjusts for place_of_application
    (edges_1, edges_2, all_edges, with_back).
    """
    shape = getattr(position, "shape", None)
    shape_str = shape.value if hasattr(shape, "value") else str(shape or "rectangle")
    product_type = getattr(position, "product_type", None)
    pt_str = product_type.value if hasattr(product_type, "value") else str(product_type or "tile")

    face_area: Optional[Decimal] = None

    # 0. Precise calculation from shape_dimensions JSONB (universal shape system)
    dims = getattr(position, "shape_dimensions", None)
    if dims and isinstance(dims, dict):
        area_cm2 = calculate_area_from_dimensions(shape_str, dims)
        if area_cm2 is not None:
            area_sqm = area_cm2 / 10000.0
            # For sinks, add bowl surface if depth is available
            depth_for_sink = getattr(position, "depth_cm", None)
            bowl_for_sink = getattr(position, "bowl_shape", None)
            if pt_str == "sink" and depth_for_sink and float(depth_for_sink) > 0:
                # Use bounding dimensions for bowl calculation
                L = dims.get("width_cm") or dims.get("w") or dims.get("diameter_cm") or dims.get("d") or 0
                W = dims.get("height_cm") or dims.get("h") or dims.get("diameter_cm") or dims.get("d") or 0
                if L and W:
                    bowl_cm2 = _calculate_bowl_surface(float(L), float(W), float(depth_for_sink), bowl_for_sink)
                    area_sqm += bowl_cm2 / 10000.0
            face_area = Decimal(str(round(area_sqm, 4)))

    if face_area is None:
        length = getattr(position, "length_cm", None)
        width = getattr(position, "width_cm", None)
        depth = getattr(position, "depth_cm", None)
        bowl = getattr(position, "bowl_shape", None)

        # 1. Exact dimensions available (legacy: length_cm / width_cm)
        if length and width and float(length) > 0 and float(width) > 0:
            area = calculate_glazeable_surface(
                shape=shape_str,
                length_cm=float(length),
                width_cm=float(width),
                depth_cm=float(depth) if depth else 0,
                bowl_shape=bowl,
                product_type=pt_str,
            )
            face_area = Decimal(str(area))

    if face_area is None:
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
                    face_area = Decimal(str(area))
                else:
                    # Non-standard shape: use bounding box × coefficient
                    bounding_area_sqm = (w_cm * h_cm) / 10000.0
                    coeff = get_shape_coefficient(db, shape_str, pt_str)
                    face_area = Decimal(str(round(bounding_area_sqm * coeff, 4)))

    if face_area is None:
        # 3. Fallback: use existing quantity_sqm / quantity × coefficient
        qty_sqm = getattr(position, "quantity_sqm", None)
        qty = getattr(position, "quantity", None)
        if qty_sqm and qty and int(qty) > 0:
            area_per_piece = float(qty_sqm) / int(qty)
            coeff = get_shape_coefficient(db, shape_str, pt_str)
            face_area = Decimal(str(round(area_per_piece * coeff, 4)))

    if face_area is None:
        return None

    # --- Adjust for place_of_application (edges/back add surface) ---
    poa = getattr(position, 'place_of_application', None) or ''
    poa = poa.strip().lower()

    # Edge profile coefficients — multiply edge area when profile is non-straight
    EDGE_PROFILE_COEFFICIENTS = {
        'straight': Decimal('1.0'),
        'beveled_45': Decimal('1.0'),
        'beveled_30': Decimal('1.05'),
        'rounded': Decimal('1.15'),
        'bullnose': Decimal('1.57'),
        'pencil': Decimal('1.05'),
        'ogee': Decimal('1.25'),
        'waterfall': Decimal('1.15'),
        'stepped': Decimal('1.1'),
        'custom': Decimal('1.2'),
    }

    if poa and poa != 'face_only' and face_area > 0:
        original_face = face_area

        # Get thickness in meters
        t_m = Decimal('0')
        thickness = getattr(position, 'thickness_mm', None)
        if thickness and float(thickness) > 0:
            t_m = Decimal(str(thickness)) / Decimal('1000')

        # Get W and H in meters
        w_m = Decimal('0')
        h_m = Decimal('0')
        w_cm = getattr(position, 'width_cm', None)
        h_cm = getattr(position, 'length_cm', None)
        if w_cm and float(w_cm) > 0:
            w_m = Decimal(str(w_cm)) / Decimal('100')
        if h_cm and float(h_cm) > 0:
            h_m = Decimal(str(h_cm)) / Decimal('100')

        # If no explicit dimensions, try parsing from size string
        if (w_m == 0 or h_m == 0) and getattr(position, 'size', None):
            try:
                from business.kiln.capacity import parse_size
                parsed = parse_size(position.size)
                if parsed:
                    pw, ph = parsed  # in cm
                    w_m = Decimal(str(pw)) / Decimal('100')
                    h_m = Decimal(str(ph)) / Decimal('100')
            except Exception:
                pass

        # Determine edge profile coefficient
        _edge_profile = getattr(position, 'edge_profile', None) or ''
        _edge_coeff = EDGE_PROFILE_COEFFICIENTS.get(_edge_profile.strip().lower(), Decimal('1.0'))

        if t_m > 0 and (w_m > 0 or h_m > 0):
            perimeter = Decimal('2') * (w_m + h_m)
            one_long_edge = h_m * t_m * _edge_coeff  # one long side, adjusted for profile

            if poa == 'edges_1':
                face_area += one_long_edge
            elif poa == 'edges_2':
                face_area += Decimal('2') * one_long_edge
            elif poa == 'all_edges':
                face_area += perimeter * t_m * _edge_coeff
            elif poa == 'with_back':
                face_area += face_area + perimeter * t_m * _edge_coeff  # double face + all edges

        position_label = getattr(position, 'id', None) or getattr(position, 'position_number', '?')
        logger.info(
            "POA_ADJUST | position=%s | poa=%s | edge_profile=%s | coeff=%s | face=%.4f → adjusted=%.4f",
            position_label, poa, _edge_profile or 'none', _edge_coeff, original_face, face_area,
        )

    return face_area
