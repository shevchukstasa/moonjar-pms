"""
Kiln capacity calculations — ported from kiln-calculator app.
Source: kiln-calculator/src/utils/kilnCalculations.ts (do not modify that file).

All numeric thresholds come from two dicts:
  constants     — global kiln_constants table (get_kiln_constants())
  loading_rules — per-kiln JSONB from kiln_loading_rules (get_loading_rules())

Per-kiln values override globals; globals fall back to module-level defaults.
See BUSINESS_LOGIC.md §6 for algorithm overview.
"""
from math import floor, ceil, pi
from typing import Optional

# Module-level fallbacks (used only when both DB sources are missing)
_D = {
    "TILE_GAP": 1.2,
    "AIR_GAP": 2.0,
    "SHELF_THICKNESS": 3.0,
    "FLAT_ON_EDGE_COEFFICIENT": 0.30,
    "FILLER_COEFFICIENT": 0.50,
    "FILLER_SIZE": 10.0,
    "MAX_FILLER_AREA": 2.0,       # m²
    "MIN_SPACE_TO_FILL": 21.0,    # cm
    "MAX_EDGE_HEIGHT": 15.0,      # cm — default for any kiln
    "MIN_PRODUCT_SIZE": 3.0,
    "MIN_THICKNESS": 0.8,
    "TRIANGLE_PAIR_GAP": 1.5,
    "MAX_BIG_KILN_TILE_MAX": 40.0,
    "MAX_BIG_KILN_TILE_MIN": 30.0,
    "SINK_COUNTERTOP_LARGE_MAX": 40.0,
    "SINK_COUNTERTOP_LARGE_MIN": 20.0,
}


# ── Resolution helpers ────────────────────────────────────────────────────────

def _c(constants: dict, loading_rules: dict, key_lr: str, key_c: str, fallback):
    """Resolve a value: per-kiln rule → global constant → hardcoded fallback."""
    if key_lr and loading_rules.get(key_lr) is not None:
        return loading_rules[key_lr]
    return constants.get(key_c, fallback)


# ── Geometry helpers ──────────────────────────────────────────────────────────

def parse_size(size_str: str) -> dict:
    """Parse '30x60' / '30х60' (cyrillic) / '5×21,5' → {width_cm, height_cm}."""
    from business.services.size_normalizer import normalize_size_str
    s = normalize_size_str(size_str)
    parts = s.split("x")
    w = float(parts[0])
    h = float(parts[1]) if len(parts) > 1 else w
    return {"width_cm": w, "height_cm": h}


def _product_area(product: dict) -> float:
    """Face area of one piece in m², respecting shape."""
    shape = product.get("shape", "rectangle")
    lm = product["length"] / 100.0
    wm = product["width"] / 100.0
    if shape == "round":
        r = product["length"] / 2.0 / 100.0
        return pi * r * r
    elif shape in ("triangle", "right_triangle"):
        return (lm * wm) / 2.0
    return lm * wm


def _effective_dims(product: dict, triangle_gap: float) -> tuple:
    """Return (eff_length, eff_width, is_triangle_pair).

    Both general triangle and right_triangle are loaded as pairs so two pieces
    fit into a single rectangular footprint (with a small gap between them).
    """
    shape = product.get("shape", "rectangle")
    L, W = product["length"], product["width"]
    if shape == "round":
        return L, L, False
    elif shape in ("triangle", "right_triangle"):
        return L + triangle_gap, W + triangle_gap, True
    return L, W, False


def _tiles_along(available: float, tile_size: float, gap: float) -> int:
    if tile_size <= 0:
        return 0
    return floor((available + gap) / (tile_size + gap))


def _product_gap(product: dict, tile_gap: float) -> float:
    """Gap depends on product type: sinks/countertops need much more space."""
    ptype = product.get("type", "tile")
    if ptype in ("sink", "countertop"):
        return max(10.0, product.get("thickness", 1.0) / 2.0)
    return tile_gap


def _kiln_cfg(kiln) -> dict:
    """Normalise Resource ORM → geometry dict."""
    dims = kiln.kiln_dimensions_cm or {}
    work = kiln.kiln_working_area_cm or {}
    ktype = (kiln.kiln_type or "").lower()
    is_small = "small" in ktype
    is_raku = "raku" in ktype

    if is_raku:
        # Raku kiln: 60×100 cm working area, single level, no multi-level
        dw, dd, dh = 60.0, 100.0, None
        dm, dc = False, 0.85
    elif is_small:
        dw, dd, dh = 100.0, 150.0, None
        dm, dc = False, 0.92
    else:
        dw, dd, dh = 54.0, 84.0, 80.0
        dm, dc = True, 0.80

    return {
        "name": ktype,
        "is_small": is_small,
        "is_raku": is_raku,
        "working_width": float(work.get("width_cm") or work.get("width") or dw),
        "working_depth": float(work.get("depth_cm") or work.get("depth") or dd),
        "working_height": (
            float(work.get("height_cm") or work.get("height") or dh)
            if (work.get("height_cm") or work.get("height") or dh) else None
        ),
        "multi_level": kiln.kiln_multi_level if kiln.kiln_multi_level is not None else dm,
        "coefficient": float(kiln.kiln_coefficient or dc),
    }


# ── Small-kiln filler ─────────────────────────────────────────────────────────

def _small_kiln_filler(
    cfg: dict,
    product: dict,
    tiles_w: int,
    tiles_d: int,
    tile_depth_cm: float,   # effective tile dim along kiln depth (chosen orientation)
    tile_width_cm: float,   # effective tile dim along kiln width (chosen orientation)
    filler_size: float,
    filler_coeff: float,
    min_space: float,
    max_filler_m2: float,
    tile_gap: float,
) -> Optional[dict]:
    """10×10 filler tiles for leftover space in the small kiln (all shapes)."""
    if not cfg["is_small"]:
        return None

    eff_l, eff_w = tile_depth_cm, tile_width_cm
    gap = _product_gap(product, tile_gap)

    max_dim = max(eff_l, eff_w)
    zone_w = 100.0 if max_dim <= 100 else cfg["working_width"]
    zone_d = 150.0 if max_dim <= 100 else cfg["working_depth"]

    occ_d = tiles_d * eff_l + max(0, tiles_d - 1) * gap
    occ_w = tiles_w * eff_w + max(0, tiles_w - 1) * gap
    rem_d = zone_d - occ_d
    rem_w = zone_w - occ_w

    pieces = 0
    FILLER_THICKNESS = 1.0  # assumed cm

    if rem_d > min_space:
        pair_w = FILLER_THICKNESS * 2
        pairs = _tiles_along(zone_w, pair_w, tile_gap)
        rows = _tiles_along(rem_d, filler_size, tile_gap)
        pieces += pairs * 2 * rows

    if rem_w > min_space:
        pair_w = FILLER_THICKNESS * 2
        pairs = _tiles_along(rem_w, pair_w, tile_gap)
        rows = _tiles_along(eff_l, filler_size, tile_gap)
        pieces += pairs * 2 * rows

    if pieces == 0:
        return None

    adj = ceil(pieces * filler_coeff)
    area = adj * (filler_size * filler_size / 10000.0)  # m²

    if area > max_filler_m2:
        area = max_filler_m2
        adj = floor(max_filler_m2 / (filler_size * filler_size / 10000.0))

    return {"filler_pieces": adj, "filler_area_sqm": round(area, 4)}


# ── Main calculations ─────────────────────────────────────────────────────────

def _resolve_params(constants: dict, loading_rules: dict) -> dict:
    """
    Build a single resolved-params dict from global constants + per-kiln overrides.
    Per-kiln values (loading_rules) win over global constants win over hardcoded defaults.
    """
    lr = loading_rules or {}
    c = constants or {}

    def lr_or_c(lr_key, c_key, fallback):
        if lr_key and lr.get(lr_key) is not None:
            return lr[lr_key]
        return c.get(c_key, fallback)

    tile_gap = lr_or_c("gap_x_cm", "TILE_GAP", _D["TILE_GAP"])
    return {
        "tile_gap_x":            tile_gap,
        "tile_gap_y":            lr_or_c("gap_y_cm", "TILE_GAP", tile_gap),
        "air_gap":               lr_or_c("air_gap_cm", "AIR_GAP", _D["AIR_GAP"]),
        "shelf_thickness":       lr_or_c("shelf_thickness_cm", "SHELF_THICKNESS", _D["SHELF_THICKNESS"]),
        "flat_on_edge_coeff":    lr_or_c("flat_on_edge_coefficient", "FLAT_ON_EDGE_COEFFICIENT", _D["FLAT_ON_EDGE_COEFFICIENT"]),
        "filler_coeff":          lr_or_c("filler_coefficient", "FILLER_COEFFICIENT", _D["FILLER_COEFFICIENT"]),
        "filler_size":           c.get("FILLER_SIZE", _D["FILLER_SIZE"]),
        "max_filler_m2":         c.get("MAX_FILLER_AREA", c.get("FILLER_MAX_AREA", _D["MAX_FILLER_AREA"])),
        "min_space_to_fill":     lr_or_c("min_space_to_fill_cm", "MIN_SPACE_TO_FILL", _D["MIN_SPACE_TO_FILL"]),
        "max_edge_height":       lr_or_c("max_edge_height_cm", "MAX_EDGE_HEIGHT", _D["MAX_EDGE_HEIGHT"]),
        "min_product_size":      c.get("MIN_PRODUCT_SIZE", _D["MIN_PRODUCT_SIZE"]),
        "min_thickness":         c.get("MIN_THICKNESS", _D["MIN_THICKNESS"]),
        "triangle_gap":          c.get("TRIANGLE_PAIR_GAP", _D["TRIANGLE_PAIR_GAP"]),
        "edge_allowed":          lr.get("edge_loading_allowed", True),
        "max_product_width_cm":  lr.get("max_product_width_cm"),   # None = no limit
        "max_product_height_cm": lr.get("max_product_height_cm"),  # None = no limit
        "allowed_product_types": lr.get("allowed_product_types"),  # None = all
        "filler_enabled":        lr.get("filler_enabled", True),
    }


def calculate_flat_loading(
    position,
    kiln,
    constants: dict,
    loading_rules: Optional[dict] = None,
) -> dict:
    """
    Flat (face-up) loading calculation.

    Args:
        position: OrderPosition ORM (needs .size, .product_type, .shape,
                  .thickness_cm, .glaze_placement)
        kiln:     Resource ORM (kiln)
        constants: global kiln constants dict (get_kiln_constants())
        loading_rules: per-kiln JSONB dict (get_loading_rules()) — optional

    Returns dict with:
        method, per_level, num_levels, total_pieces, total_area_sqm, filler?
    """
    cfg = _kiln_cfg(kiln)
    p = _resolve_params(constants, loading_rules)

    size = parse_size(getattr(position, "size", "0x0") or "0x0")
    product = {
        "length": size["height_cm"],
        "width": size["width_cm"],
        "thickness": float(getattr(position, "thickness_cm", 1.0) or 1.0),
        "type": getattr(position, "product_type", "tile") or "tile",
        "shape": getattr(position, "shape", "rectangle") or "rectangle",
        "glaze": getattr(position, "glaze_placement", "face-only") or "face-only",
    }

    L, W, T = product["length"], product["width"], product["thickness"]
    ptype, shape, glaze = product["type"], product["shape"], product["glaze"]

    # Validation
    if L < p["min_product_size"] or W < p["min_product_size"] or T < p["min_thickness"]:
        raise ValueError(f"Product too small: {L}×{W}×{T} cm (min {p['min_product_size']}×{p['min_product_size']}×{p['min_thickness']})")

    # Per-kiln product type restriction
    if p["allowed_product_types"] and ptype not in p["allowed_product_types"]:
        return {"method": "flat", "total_pieces": 0, "total_area_sqm": 0.0,
                "reason": f"product type '{ptype}' not allowed in this kiln"}

    # Per-kiln max dimensions
    if p["max_product_width_cm"] and W > p["max_product_width_cm"]:
        return {"method": "flat", "total_pieces": 0, "total_area_sqm": 0.0,
                "reason": f"product width {W} cm exceeds kiln limit {p['max_product_width_cm']} cm"}
    if p["max_product_height_cm"] and L > p["max_product_height_cm"]:
        return {"method": "flat", "total_pieces": 0, "total_area_sqm": 0.0,
                "reason": f"product height {L} cm exceeds kiln limit {p['max_product_height_cm']} cm"}

    gap = _product_gap(product, p["tile_gap_x"])
    eff_L, eff_W, is_pair = _effective_dims(product, p["triangle_gap"])

    # Small kiln: extended zones
    eff_kw = cfg["working_width"]
    eff_kd = cfg["working_depth"]
    if cfg["is_small"]:
        max_d = max(eff_L, eff_W)
        min_d = min(eff_L, eff_W)
        if ptype in ("sink", "countertop"):
            if max_d <= 150 and min_d <= 100:
                eff_kw, eff_kd = 100.0, 150.0
        else:
            if max_d <= 100:
                eff_kw, eff_kd = 100.0, 150.0

    # Try both orientations and pick the one that fits more tiles per level.
    # Orientation A: eff_W along kiln width, eff_L along kiln depth (default)
    # Orientation B: eff_L along kiln width, eff_W along kiln depth (rotated 90°)
    tw_a = _tiles_along(eff_kw, eff_W, gap)
    td_a = _tiles_along(eff_kd, eff_L, gap)
    tw_b = _tiles_along(eff_kw, eff_L, gap)
    td_b = _tiles_along(eff_kd, eff_W, gap)

    if tw_b * td_b > tw_a * td_a:
        tiles_w, tiles_d = tw_b, td_b
        tile_depth_cm, tile_width_cm = eff_W, eff_L   # eff_W now runs along depth
    else:
        tiles_w, tiles_d = tw_a, td_a
        tile_depth_cm, tile_width_cm = eff_L, eff_W   # eff_L runs along depth

    per_level = tiles_w * tiles_d * (2 if is_pair else 1)

    if per_level == 0:
        return {"method": "flat", "total_pieces": 0, "total_area_sqm": 0.0,
                "reason": "product does not fit"}

    level_h = T + p["air_gap"] + p["shelf_thickness"]
    has_back_glaze = glaze == "face-with-back"

    levels = 1
    if cfg["multi_level"] and cfg["working_height"] and not has_back_glaze:
        levels = max(1, floor(cfg["working_height"] / level_h))
    if cfg["is_small"]:
        levels = 1

    coeff = 1.0 if ptype in ("sink", "countertop") else cfg["coefficient"]
    total_adj = ceil(per_level * levels * coeff)
    total_area = round(total_adj * _product_area(product), 4)

    result: dict = {
        "method": "flat",
        "per_level": per_level,
        "num_levels": levels,
        "total_pieces": total_adj,
        "total_area_sqm": total_area,
    }

    if p.get("filler_enabled", True):
        filler = _small_kiln_filler(
            cfg, product, tiles_w, tiles_d,
            tile_depth_cm, tile_width_cm,
            p["filler_size"], p["filler_coeff"],
            p["min_space_to_fill"], p["max_filler_m2"],
            p["tile_gap_x"],
        )
        if filler:
            result["filler"] = filler

    return result


def calculate_edge_loading(
    position,
    kiln,
    constants: dict,
    loading_rules: Optional[dict] = None,
) -> dict:
    """
    Edge loading (tiles standing on edge, back-to-back pairs) + flat-on-top.

    Returns dict with:
        method, edge_pieces, flat_on_top, num_levels, total_pieces, total_area_sqm
    Or total_pieces=0 with reason when not applicable.
    """
    cfg = _kiln_cfg(kiln)
    p = _resolve_params(constants, loading_rules)

    # Kiln-level edge disable
    if not p["edge_allowed"]:
        return {"method": "edge", "total_pieces": 0, "total_area_sqm": 0.0,
                "reason": "edge loading disabled for this kiln"}

    size = parse_size(getattr(position, "size", "0x0") or "0x0")
    product = {
        "length": size["height_cm"],
        "width": size["width_cm"],
        "thickness": float(getattr(position, "thickness_cm", 1.0) or 1.0),
        "type": getattr(position, "product_type", "tile") or "tile",
        "shape": getattr(position, "shape", "rectangle") or "rectangle",
        "glaze": getattr(position, "glaze_placement", "face-only") or "face-only",
    }

    L, W, T = product["length"], product["width"], product["thickness"]
    ptype, shape, glaze = product["type"], product["shape"], product["glaze"]

    if L < p["min_product_size"] or W < p["min_product_size"] or T < p["min_thickness"]:
        raise ValueError(f"Product too small: {L}×{W}×{T} cm")

    # Product-type restriction
    if p["allowed_product_types"] and ptype not in p["allowed_product_types"]:
        return {"method": "edge", "total_pieces": 0, "total_area_sqm": 0.0,
                "reason": f"product type '{ptype}' not allowed in this kiln"}

    # Sinks, countertops, 3D: flat only
    if ptype in ("sink", "countertop", "3d"):
        return {"method": "edge", "total_pieces": 0, "total_area_sqm": 0.0,
                "reason": "product type cannot be placed on edge"}

    # Glaze blocks edge loading (regardless of orientation)
    if glaze in ("face-3-4-edges", "face-with-back"):
        return {"method": "edge", "total_pieces": 0, "total_area_sqm": 0.0,
                "reason": "glaze coverage prevents edge loading"}

    # Round shapes can't stand on edge
    if shape == "round":
        return {"method": "edge", "total_pieces": 0, "total_area_sqm": 0.0,
                "reason": "round shapes cannot be placed on edge"}

    # Per-kiln max dimensions
    if p["max_product_width_cm"] and W > p["max_product_width_cm"]:
        return {"method": "edge", "total_pieces": 0, "total_area_sqm": 0.0,
                "reason": f"product width exceeds kiln limit"}

    # Effective kiln zone
    eff_kw, eff_kd = cfg["working_width"], cfg["working_depth"]
    if cfg["is_small"] and max(L, W) <= 100:
        eff_kw, eff_kd = 100.0, 150.0

    pair_w = T * 2
    pairs_w = _tiles_along(eff_kw, pair_w, p["tile_gap_x"])

    # Try both edge orientations and pick the one with maximum pieces.
    # Normal:  tile stands on its L edge (vertical height = L, rows fit by W).
    # Rotated: tile stands on its W edge (vertical height = W, rows fit by L).
    # Each orientation is only valid if its vertical dimension ≤ max_edge_height.
    rows_normal  = _tiles_along(eff_kd, W, p["tile_gap_y"]) if L <= p["max_edge_height"] else 0
    rows_rotated = _tiles_along(eff_kd, L, p["tile_gap_y"]) if W <= p["max_edge_height"] else 0

    edge_normal  = pairs_w * 2 * rows_normal
    edge_rotated = pairs_w * 2 * rows_rotated

    if edge_normal == 0 and edge_rotated == 0:
        return {"method": "edge", "total_pieces": 0, "total_area_sqm": 0.0,
                "reason": f"product too tall for edge loading "
                          f"(L={L} cm, W={W} cm, limit={p['max_edge_height']} cm)"}

    if edge_normal >= edge_rotated:
        edge_per_level = edge_normal
        vertical_dim = L   # tile height when standing on edge (normal)
    else:
        edge_per_level = edge_rotated
        vertical_dim = W   # tile height when rotated

    if edge_per_level == 0:
        return {"method": "edge", "total_pieces": 0, "total_area_sqm": 0.0,
                "reason": "no pieces fit on edge"}

    # Flat-on-top: tiles lying face-up on top of the edge-standing rows.
    # Only valid for rectangular/square tiles with face-only glaze:
    #   - triangle pairs cannot be safely stacked flat on top
    #   - face-2-edges glaze would touch adjacent standing tiles → glaze damage
    area_pp = _product_area(product)
    flat_on_top_allowed = (shape == "rectangle" and glaze == "face-only")
    if flat_on_top_allowed:
        shelf_m2 = (eff_kw * eff_kd) / 10000.0
        flat_area_avail = shelf_m2 * p["flat_on_edge_coeff"]
        flat_per_level = floor(flat_area_avail / area_pp) if area_pp > 0 else 0
        flat_per_level = min(flat_per_level, edge_per_level * 2)  # physical cap
    else:
        flat_per_level = 0

    level_h = vertical_dim + p["air_gap"] + p["shelf_thickness"] + T

    levels = 1
    if cfg["multi_level"] and cfg["working_height"]:
        levels = max(1, floor(cfg["working_height"] / level_h))

    coeff = cfg["coefficient"]
    edge_adj = ceil(edge_per_level * levels * coeff)
    flat_adj = ceil(flat_per_level * levels * coeff)

    edge_area = round(edge_adj * area_pp, 4)
    flat_area = round(flat_adj * area_pp, 4)

    return {
        "method": "edge",
        "edge_pieces": edge_adj,
        "flat_on_top": flat_adj,
        "num_levels": levels,
        "total_pieces": edge_adj + flat_adj,
        "total_area_sqm": round(edge_area + flat_area, 4),
    }


def calculate_kiln_capacity(
    position,
    kiln,
    constants: dict,
    loading_rules: Optional[dict] = None,
) -> dict:
    """
    Calculate optimal kiln loading — try both flat and edge, return the better one.

    Returns:
        {optimal, alternative, flat, edge}
    """
    flat = calculate_flat_loading(position, kiln, constants, loading_rules)
    edge = calculate_edge_loading(position, kiln, constants, loading_rules)

    flat_area = flat.get("total_area_sqm", 0.0)
    edge_area = edge.get("total_area_sqm", 0.0)

    if edge_area >= flat_area and edge_area > 0:
        optimal, alternative = edge, flat
    else:
        optimal, alternative = flat, edge

    return {
        "optimal": optimal,
        "alternative": alternative,
        "flat": flat,
        "edge": edge,
    }
