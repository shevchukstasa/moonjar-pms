"""
Kiln capacity calculations.
See BUSINESS_LOGIC.md §6 for full algorithm.
"""
from uuid import UUID
from typing import Optional
from math import floor

from sqlalchemy.orm import Session

from business.kiln.constants import get_kiln_constants


def parse_size(size_str: str) -> dict:
    """Parse size string like '10x10' or '30x60' into {width_cm, height_cm}."""
    parts = size_str.lower().replace("х", "x").split("x")
    if len(parts) == 2:
        return {"width_cm": float(parts[0]), "height_cm": float(parts[1])}
    return {"width_cm": float(parts[0]), "height_cm": float(parts[0])}


def calculate_flat_loading(position, kiln, constants: dict) -> dict:
    """
    Calculate how many pieces fit flat in kiln.
    Returns: {method, per_level, num_levels, total_pieces, total_area_sqm}
    """
    # TODO: implement — see BUSINESS_LOGIC.md §6
    raise NotImplementedError


def calculate_edge_loading(position, kiln, constants: dict) -> dict:
    """
    Calculate edge loading with flat-on-top.
    Returns: {method, per_level, edge_pieces, flat_on_top, num_levels, total_pieces, total_area_sqm}
    """
    # TODO: implement — see BUSINESS_LOGIC.md §6
    raise NotImplementedError


def get_sqm_per_piece(size_str: str) -> float:
    """Convert tile size to m² per piece."""
    dims = parse_size(size_str)
    return (dims["width_cm"] * dims["height_cm"]) / 10000
