"""
Glazing Board Calculator.

For each tile size, determines how many tiles fit on a standard glazing board
(122×20cm cut from plywood), and suggests a custom board width if needed.

Standard board target: 0.22–0.23 m² of tile area per board.
This matches the workshop norm: masters measure glaze in mL per two boards,
calibrated to approximately 0.22–0.23 m² per board.
"""

from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger("moonjar.glazing_board")

BOARD_LENGTH_CM = 122.0
BOARD_WIDTH_STANDARD_CM = 20.0
SEAM_CM = 0.3
OVERHANG_MAX_CM = 1.0
TARGET_AREA_MIN_M2 = 0.22
TARGET_AREA_MAX_M2 = 0.23
TARGET_AREA_MID_M2 = 0.225


@dataclass
class GlazingBoardCalcResult:
    is_standard_board: bool       # True = standard 122×20 works; False = custom needed
    board_length_cm: float        # always 122
    board_width_cm: float         # 20.0 or custom
    tiles_per_board: int
    area_per_board_m2: float
    tiles_along_length: int       # how many tiles along 122cm
    tiles_across_width: int       # how many tiles across the width
    tile_orientation_cm: str      # e.g. "10×30" (width_axis × length_axis in cm)
    notes: str = ""


def calculate_glazing_board(width_mm: int, height_mm: int) -> GlazingBoardCalcResult:
    """
    Calculate optimal glazing board dimensions for a tile of given size.

    Args:
        width_mm: tile width in mm
        height_mm: tile height in mm

    Returns:
        GlazingBoardCalcResult with board dimensions and tile count
    """
    w_cm = width_mm / 10.0
    h_cm = height_mm / 10.0
    tile_area_m2 = (width_mm / 1000.0) * (height_mm / 1000.0)

    if tile_area_m2 <= 0:
        raise ValueError(f"Invalid tile dimensions: {width_mm}×{height_mm} mm")

    # Try both orientations of the tile on the board.
    # Orientation A: tile placed so dimension `along_dim` runs along the 122cm length,
    #                and `across_dim` runs across the board width.
    # We try (w along length, h across) and (h along length, w across).
    best_standard = None
    all_candidates = []

    for along_cm, across_cm in [(h_cm, w_cm), (w_cm, h_cm)]:
        # Tiles can slightly overhang the board edge (max OVERHANG_MAX_CM).
        # Formula: n_tiles such that n*tile + (n-1)*seam <= board + overhang
        # → n <= (board + overhang + seam) / (tile + seam)
        n_along = int((BOARD_LENGTH_CM + OVERHANG_MAX_CM + SEAM_CM) / (along_cm + SEAM_CM))
        if n_along == 0:
            continue

        # Standard board: how many tiles fit across (with overhang allowance)?
        n_across_std = int((BOARD_WIDTH_STANDARD_CM + OVERHANG_MAX_CM + SEAM_CM) / (across_cm + SEAM_CM))
        if n_across_std == 0:
            n_across_std = 0

        if n_across_std > 0:
            count_std = n_along * n_across_std
            area_std = count_std * tile_area_m2
            # Check if fits within standard board (with allowed overhang)
            actual_width = n_across_std * across_cm + max(0, n_across_std - 1) * SEAM_CM
            fits = actual_width <= BOARD_WIDTH_STANDARD_CM + OVERHANG_MAX_CM

            _eps = 1e-9  # float tolerance
            cand = {
                'along_cm': along_cm,
                'across_cm': across_cm,
                'n_along': n_along,
                'n_across': n_across_std,
                'count': count_std,
                'area': area_std,
                'board_width': BOARD_WIDTH_STANDARD_CM,
                'is_standard': fits and (TARGET_AREA_MIN_M2 - _eps) <= area_std <= (TARGET_AREA_MAX_M2 + _eps),
                'area_deviation': abs(area_std - TARGET_AREA_MID_M2),
            }
            all_candidates.append(cand)

            if cand['is_standard'] and (
                best_standard is None or cand['area_deviation'] < best_standard['area_deviation']
            ):
                best_standard = cand

    # If standard board works, return it
    if best_standard:
        return GlazingBoardCalcResult(
            is_standard_board=True,
            board_length_cm=BOARD_LENGTH_CM,
            board_width_cm=BOARD_WIDTH_STANDARD_CM,
            tiles_per_board=best_standard['count'],
            area_per_board_m2=round(best_standard['area'], 4),
            tiles_along_length=best_standard['n_along'],
            tiles_across_width=best_standard['n_across'],
            tile_orientation_cm=f"{best_standard['across_cm']}×{best_standard['along_cm']}",
            notes="Standard 122×20cm board",
        )

    # Standard board doesn't achieve target area — compute custom width
    target_tiles = round(TARGET_AREA_MID_M2 / tile_area_m2)
    if target_tiles < 1:
        target_tiles = 1

    custom_candidates = []
    for along_cm, across_cm in [(h_cm, w_cm), (w_cm, h_cm)]:
        n_along = int((BOARD_LENGTH_CM + SEAM_CM) / (along_cm + SEAM_CM))
        if n_along == 0:
            continue

        # Find n_across that gets us closest to target_tiles
        n_across = max(1, round(target_tiles / n_along))
        count = n_along * n_across
        area = count * tile_area_m2

        # Custom board width: exactly n_across tiles + seams between them
        # Add a tiny margin (2mm) to avoid tiles being exactly flush
        custom_width = n_across * across_cm + max(0, n_across - 1) * SEAM_CM + 0.2

        custom_candidates.append({
            'along_cm': along_cm,
            'across_cm': across_cm,
            'n_along': n_along,
            'n_across': n_across,
            'count': count,
            'area': area,
            'board_width': custom_width,
            'area_deviation': abs(area - TARGET_AREA_MID_M2),
        })

    if not custom_candidates:
        # Fallback: one tile per board
        w_max = max(w_cm, h_cm)
        h_max = min(w_cm, h_cm)
        return GlazingBoardCalcResult(
            is_standard_board=False,
            board_length_cm=BOARD_LENGTH_CM,
            board_width_cm=round(h_max + 0.2, 1),
            tiles_per_board=int((BOARD_LENGTH_CM + SEAM_CM) / (w_max + SEAM_CM)),
            area_per_board_m2=round(
                int((BOARD_LENGTH_CM + SEAM_CM) / (w_max + SEAM_CM)) * tile_area_m2, 4
            ),
            tiles_along_length=int((BOARD_LENGTH_CM + SEAM_CM) / (w_max + SEAM_CM)),
            tiles_across_width=1,
            tile_orientation_cm=f"{h_max}×{w_max}",
            notes="Very large tile — one tile per board row",
        )

    best = min(custom_candidates, key=lambda c: c['area_deviation'])

    logger.info(
        "GLAZING_BOARD | tile=%dx%d mm | custom board: %.1fcm wide, "
        "%d tiles (%dx%d), area=%.4f m²",
        width_mm, height_mm, best['board_width'],
        best['count'], best['n_across'], best['n_along'], best['area'],
    )

    return GlazingBoardCalcResult(
        is_standard_board=False,
        board_length_cm=BOARD_LENGTH_CM,
        board_width_cm=round(best['board_width'], 1),
        tiles_per_board=best['count'],
        area_per_board_m2=round(best['area'], 4),
        tiles_along_length=best['n_along'],
        tiles_across_width=best['n_across'],
        tile_orientation_cm=f"{best['across_cm']}×{best['along_cm']}",
        notes=f"Custom board: {round(best['board_width'], 1)}cm wide (standard 20cm doesn't fit neatly)",
    )
