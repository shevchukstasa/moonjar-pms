"""
Glazing Board Calculator.

For each tile size, determines how many tiles fit on a standard glazing board
(122×21 cm cut from plywood), and suggests a custom board width if needed.

Standard board: 122 × 21 cm.
Tile overhang: max 0.5 cm per side (tiles can stick out slightly).
Max tile size for standard boards: 20×40 cm. Larger tiles → other technology.

Workshop norm: masters measure glaze in mL per TWO boards (~0.44–0.46 m²).
Target: ~0.22–0.23 m² of tile area per ONE board (soft target, not strict).

Rules:
1. Tiles ≤ 20×40 cm → ALWAYS standard 122×21 board, pick best arrangement
2. Tiles > 20×40 cm → custom board or "no standard board" flag
"""

from dataclasses import dataclass
import logging

logger = logging.getLogger("moonjar.glazing_board")

BOARD_LENGTH_CM = 122.0
BOARD_WIDTH_STANDARD_CM = 21.0   # standard board width is 21 cm
SEAM_CM = 0.3                    # gap between tiles
OVERHANG_PER_SIDE_CM = 0.5       # tiles can overhang 0.5 cm on each side
OVERHANG_MAX_CM = OVERHANG_PER_SIDE_CM * 2  # total overhang = 1.0 cm
MAX_TILE_WIDTH_CM = 20.0         # max short side for standard boards
MAX_TILE_HEIGHT_CM = 40.0        # max long side for standard boards
TARGET_AREA_MID_M2 = 0.225      # target: 0.22-0.23 m² per board


@dataclass
class GlazingBoardCalcResult:
    is_standard_board: bool       # True = standard 122×21 works; False = custom needed
    board_length_cm: float        # always 122
    board_width_cm: float         # 21.0 or custom
    tiles_per_board: int
    area_per_board_m2: float
    tiles_along_length: int       # how many tiles along 122cm
    tiles_across_width: int       # how many tiles across the width
    tile_orientation_cm: str      # e.g. "10×30" (width_axis × length_axis in cm)
    area_per_two_boards_m2: float = 0.0  # 2× area — workers glaze 2 boards at a time
    notes: str = ""


def _fit_tiles(board_length: float, board_width: float,
               along_cm: float, across_cm: float) -> dict:
    """Calculate how many tiles fit in a given orientation on a board."""
    n_along = int((board_length + OVERHANG_MAX_CM + SEAM_CM) / (along_cm + SEAM_CM))
    n_across = int((board_width + OVERHANG_MAX_CM + SEAM_CM) / (across_cm + SEAM_CM))

    if n_along <= 0 or n_across <= 0:
        return None

    count = n_along * n_across
    tile_area_m2 = (along_cm * across_cm) / 10000.0
    area = count * tile_area_m2

    return {
        'along_cm': along_cm,
        'across_cm': across_cm,
        'n_along': n_along,
        'n_across': n_across,
        'count': count,
        'area': area,
        'area_deviation': abs(area - TARGET_AREA_MID_M2),
    }


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

    # Check if tile fits on standard boards (≤ 20×40 cm)
    tile_min = min(w_cm, h_cm)
    tile_max = max(w_cm, h_cm)
    fits_standard = (tile_min <= MAX_TILE_WIDTH_CM and tile_max <= MAX_TILE_HEIGHT_CM)

    # ────────────────────────────────────────────────────
    # Case 1: Tile fits on standard board (≤ 20×40)
    # ALWAYS use standard 122×21, pick best arrangement
    # ────────────────────────────────────────────────────
    if fits_standard:
        candidates = []
        for along_cm, across_cm in [(h_cm, w_cm), (w_cm, h_cm)]:
            result = _fit_tiles(BOARD_LENGTH_CM, BOARD_WIDTH_STANDARD_CM,
                                along_cm, across_cm)
            if result:
                candidates.append(result)

        if not candidates:
            # Tile too big even for one — shouldn't happen for ≤ 20×40
            area1 = tile_area_m2
            return GlazingBoardCalcResult(
                is_standard_board=True,
                board_length_cm=BOARD_LENGTH_CM,
                board_width_cm=BOARD_WIDTH_STANDARD_CM,
                tiles_per_board=1,
                area_per_board_m2=round(area1, 4),
                tiles_along_length=1,
                tiles_across_width=1,
                tile_orientation_cm=f"{tile_min}×{tile_max}",
                area_per_two_boards_m2=round(area1 * 2, 4),
                notes=f"Standard 122×{BOARD_WIDTH_STANDARD_CM:.0f}cm board (1 tile fits)",
            )

        # Pick arrangement closest to target 0.225 m²
        best = min(candidates, key=lambda c: c['area_deviation'])
        area1 = round(best['area'], 4)

        return GlazingBoardCalcResult(
            is_standard_board=True,
            board_length_cm=BOARD_LENGTH_CM,
            board_width_cm=BOARD_WIDTH_STANDARD_CM,
            tiles_per_board=best['count'],
            area_per_board_m2=area1,
            tiles_along_length=best['n_along'],
            tiles_across_width=best['n_across'],
            tile_orientation_cm=f"{best['across_cm']}×{best['along_cm']}",
            area_per_two_boards_m2=round(area1 * 2, 4),
            notes=f"Standard 122×{BOARD_WIDTH_STANDARD_CM:.0f}cm board",
        )

    # ────────────────────────────────────────────────────
    # Case 2: Tile exceeds 20×40 — compute custom board
    # ────────────────────────────────────────────────────
    target_tiles = max(1, round(TARGET_AREA_MID_M2 / tile_area_m2))

    custom_candidates = []
    for along_cm, across_cm in [(h_cm, w_cm), (w_cm, h_cm)]:
        n_along = int((BOARD_LENGTH_CM + SEAM_CM) / (along_cm + SEAM_CM))
        if n_along == 0:
            continue

        # Find n_across that gets closest to target area
        n_across = max(1, round(target_tiles / n_along))
        count = n_along * n_across
        area = count * tile_area_m2

        # Custom board width: tiles + seams + small margin
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
        # Fallback: one tile per board row
        w_max = max(w_cm, h_cm)
        h_max = min(w_cm, h_cm)
        n_fb = max(1, int((BOARD_LENGTH_CM + SEAM_CM) / (w_max + SEAM_CM)))
        area_fb = round(n_fb * tile_area_m2, 4)
        return GlazingBoardCalcResult(
            is_standard_board=False,
            board_length_cm=BOARD_LENGTH_CM,
            board_width_cm=round(h_max + 0.2, 1),
            tiles_per_board=n_fb,
            area_per_board_m2=area_fb,
            tiles_along_length=n_fb,
            tiles_across_width=1,
            tile_orientation_cm=f"{h_max}×{w_max}",
            area_per_two_boards_m2=round(area_fb * 2, 4),
            notes=f"Very large tile ({tile_min:.0f}×{tile_max:.0f}cm) — exceeds standard board max 20×40",
        )

    best = min(custom_candidates, key=lambda c: c['area_deviation'])
    area_best = round(best['area'], 4)

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
        area_per_board_m2=area_best,
        tiles_along_length=best['n_along'],
        tiles_across_width=best['n_across'],
        tile_orientation_cm=f"{best['across_cm']}×{best['along_cm']}",
        area_per_two_boards_m2=round(area_best * 2, 4),
        notes=f"Custom board: {round(best['board_width'], 1)}cm wide (tile {tile_min:.0f}×{tile_max:.0f}cm exceeds standard 20×40)",
    )
