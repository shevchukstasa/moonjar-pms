"""
Size Resolution Service.

When an order position arrives, check whether its dimensions match exactly
one record in the `sizes` reference table.

- 1 match   → auto-assign `size_id` on the position
- 0 or >1   → block the position (AWAITING_SIZE_CONFIRMATION) and create
               a SIZE_RESOLUTION task for the admin/PM to resolve manually.

This step sits RIGHT BEFORE material reservation in the order intake pipeline.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import or_

from api.models import (
    OrderPosition,
    Size,
    Task,
)
from api.enums import (
    PositionStatus,
    TaskType,
    TaskStatus,
    UserRole,
)

logger = logging.getLogger("moonjar.size_resolution")


# ────────────────────────────────────────────────────────────────
# Result dataclass
# ────────────────────────────────────────────────────────────────

@dataclass
class SizeResolutionResult:
    resolved: bool = False
    size_id: Optional[UUID] = None
    reason: str = ""
    candidates: list[dict] = field(default_factory=list)


# ────────────────────────────────────────────────────────────────
# Dimension parsing
# ────────────────────────────────────────────────────────────────

def _parse_size_string(size_str: str) -> tuple[Optional[int], Optional[int]]:
    """
    Parse a size string like "30x60" or "300x600" into (width_mm, height_mm).

    Heuristic: if both values <= 200, assume centimeters → multiply by 10.
    Otherwise assume already in mm.

    Returns (width_mm, height_mm) or (None, None) if unparseable.
    """
    if not size_str:
        return None, None

    # Try patterns: "30x60", "30X60", "30 x 60", "30×60"
    m = re.match(r'(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)', size_str.strip())
    if not m:
        return None, None

    v1 = float(m.group(1))
    v2 = float(m.group(2))

    # Heuristic: if both <= 200 → cm → convert to mm
    if v1 <= 200 and v2 <= 200:
        w_mm = int(round(v1 * 10))
        h_mm = int(round(v2 * 10))
    else:
        w_mm = int(round(v1))
        h_mm = int(round(v2))

    return w_mm, h_mm


def _extract_dimensions_mm(position: OrderPosition) -> tuple[Optional[int], Optional[int]]:
    """
    Extract width_mm and height_mm from an OrderPosition.

    Priority:
    1. Use length_cm / width_cm if both are set (convert to mm)
    2. Parse the `size` string ("30x60" → 300×600 mm)
    """
    if position.length_cm and position.width_cm:
        w_mm = int(round(float(position.width_cm) * 10))
        h_mm = int(round(float(position.length_cm) * 10))
        return w_mm, h_mm

    return _parse_size_string(position.size)


# ────────────────────────────────────────────────────────────────
# Core matching
# ────────────────────────────────────────────────────────────────

def resolve_size_for_position(
    db: Session,
    position: OrderPosition,
) -> SizeResolutionResult:
    """
    Try to match position dimensions against the sizes reference table.

    Matching rules:
    1. Extract width/height in mm
    2. Query sizes where (w, h) matches in either orientation
    3. If position has shape → filter by shape
    4. If position has thickness_mm → filter by thickness
    5. Result: 1 match = resolved, 0 or >1 = unresolved
    """
    w_mm, h_mm = _extract_dimensions_mm(position)

    if w_mm is None or h_mm is None:
        logger.warning(
            "SIZE_RESOLUTION | position=%s | cannot extract dimensions from size='%s', "
            "length_cm=%s, width_cm=%s",
            position.id, position.size, position.length_cm, position.width_cm,
        )
        return SizeResolutionResult(
            resolved=False,
            reason="missing_dimensions",
        )

    # Query both orientations: (w, h) and (h, w)
    query = db.query(Size).filter(
        or_(
            (Size.width_mm == w_mm) & (Size.height_mm == h_mm),
            (Size.width_mm == h_mm) & (Size.height_mm == w_mm),
        )
    )

    candidates = query.all()

    # Filter by shape if position has one
    pos_shape = position.shape.value if position.shape else None
    if pos_shape and candidates:
        shape_filtered = [s for s in candidates if s.shape == pos_shape]
        if shape_filtered:
            candidates = shape_filtered
        # If no match with shape filter, keep all (shape might be unset in sizes)

    # Filter by thickness if position has one and it's not the default 11
    pos_thickness = float(position.thickness_mm) if position.thickness_mm else None
    if pos_thickness and candidates:
        thickness_filtered = [
            s for s in candidates
            if s.thickness_mm is not None and abs(s.thickness_mm - pos_thickness) < 0.5
        ]
        if thickness_filtered:
            candidates = thickness_filtered
        # If no thickness matches, keep all (thickness might be unset in sizes)

    # Format candidates for metadata
    candidate_dicts = [
        {
            "id": str(s.id),
            "name": s.name,
            "width_mm": s.width_mm,
            "height_mm": s.height_mm,
            "thickness_mm": s.thickness_mm,
            "shape": s.shape,
        }
        for s in candidates
    ]

    if len(candidates) == 1:
        logger.info(
            "SIZE_RESOLVED | position=%s | matched size '%s' (%dx%d mm)",
            position.id, candidates[0].name, candidates[0].width_mm, candidates[0].height_mm,
        )
        return SizeResolutionResult(
            resolved=True,
            size_id=candidates[0].id,
            reason="auto_matched",
            candidates=candidate_dicts,
        )
    elif len(candidates) == 0:
        logger.warning(
            "SIZE_NO_MATCH | position=%s | no size found for %dx%d mm",
            position.id, w_mm, h_mm,
        )
        return SizeResolutionResult(
            resolved=False,
            reason="no_match",
            candidates=[],
        )
    else:
        logger.warning(
            "SIZE_MULTIPLE | position=%s | %d sizes match %dx%d mm: %s",
            position.id, len(candidates), w_mm, h_mm,
            [s.name for s in candidates],
        )
        return SizeResolutionResult(
            resolved=False,
            reason="multiple_matches",
            candidates=candidate_dicts,
        )


# ────────────────────────────────────────────────────────────────
# Task creation
# ────────────────────────────────────────────────────────────────

def create_size_resolution_task(
    db: Session,
    position: OrderPosition,
    order_id: UUID,
    factory_id: UUID,
    reason: str,
    candidates: list[dict],
) -> Task:
    """
    Create a blocking SIZE_RESOLUTION task for admin/PM to resolve.

    The task's metadata_json stores:
    - reason: "no_match" | "multiple_matches" | "missing_dimensions"
    - candidates: list of matching sizes (may be empty)
    - position info: size string, shape, thickness, dimensions
    """
    import json

    w_mm, h_mm = _extract_dimensions_mm(position)

    metadata = {
        "reason": reason,
        "candidates": candidates,
        "position_size_string": position.size,
        "position_shape": position.shape.value if position.shape else None,
        "position_thickness_mm": float(position.thickness_mm) if position.thickness_mm else None,
        "position_width_mm": w_mm,
        "position_height_mm": h_mm,
    }

    reason_text = {
        "no_match": "No matching size found",
        "multiple_matches": f"{len(candidates)} sizes match",
        "missing_dimensions": "Cannot extract dimensions",
    }.get(reason, reason)

    task = Task(
        factory_id=factory_id,
        type=TaskType.SIZE_RESOLUTION,
        status=TaskStatus.PENDING,
        assigned_role=UserRole.ADMINISTRATOR,
        related_order_id=order_id,
        related_position_id=position.id,
        blocking=True,
        description=f"Size resolution for '{position.size}': {reason_text}",
        metadata_json=json.dumps(metadata),
    )
    db.add(task)
    db.flush()

    logger.info(
        "SIZE_TASK_CREATED | position=%s order=%s | reason=%s candidates=%d",
        position.id, order_id, reason, len(candidates),
    )

    return task
