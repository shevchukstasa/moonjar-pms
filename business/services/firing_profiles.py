"""
Firing Profile matching and multi-round routing service.
Business Logic: §32, §32a, §32b
"""
from uuid import UUID
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from api.models import (
    FiringProfile,
    RecipeFiringStage,
    OrderPosition,
    RecipeKilnConfig,
)


def match_firing_profile(
    db: Session,
    product_type: str,
    collection: Optional[str],
    thickness_mm: Decimal,
) -> Optional[FiringProfile]:
    """
    Find the best matching firing profile for given product attributes.

    Algorithm:
    1. Filter active profiles
    2. Match product_type (or NULL = matches all)
    3. Match collection (or NULL = matches all)
    4. Match thickness within [thickness_min_mm, thickness_max_mm] (NULL = no bound)
    5. Order by match_priority DESC → return top match
    6. Fallback to is_default=True if no specific match
    """
    query = db.query(FiringProfile).filter(FiringProfile.is_active.is_(True))

    # Build matching conditions
    candidates = query.filter(
        or_(FiringProfile.product_type.is_(None), FiringProfile.product_type == product_type),
        or_(FiringProfile.collection.is_(None), FiringProfile.collection == collection),
        or_(FiringProfile.thickness_min_mm.is_(None), FiringProfile.thickness_min_mm <= thickness_mm),
        or_(FiringProfile.thickness_max_mm.is_(None), FiringProfile.thickness_max_mm >= thickness_mm),
    ).order_by(FiringProfile.match_priority.desc()).all()

    if candidates:
        return candidates[0]

    # Fallback: is_default=True
    default = (
        db.query(FiringProfile)
        .filter(FiringProfile.is_active.is_(True), FiringProfile.is_default.is_(True))
        .first()
    )
    return default


def get_batch_firing_profile(
    db: Session,
    positions: list[OrderPosition],
) -> Optional[FiringProfile]:
    """
    Determine firing profile for a batch — slowest profile wins.

    For each position → match_firing_profile by product_type/collection/thickness.
    Among all matched profiles → return the one with MAX(total_duration_hours).
    """
    slowest: Optional[FiringProfile] = None
    max_duration = Decimal("0")

    for pos in positions:
        profile = match_firing_profile(
            db,
            pos.product_type.value if pos.product_type else "tile",
            pos.collection,
            pos.thickness_mm or Decimal("11.0"),
        )
        if profile and profile.total_duration_hours > max_duration:
            max_duration = profile.total_duration_hours
            slowest = profile

    return slowest


def get_total_firing_rounds(db: Session, recipe_id: UUID) -> int:
    """
    Get total number of firing rounds for a recipe.
    If recipe_firing_stages has entries → return count.
    Otherwise → return 1 (default single firing).
    """
    count = (
        db.query(RecipeFiringStage)
        .filter(RecipeFiringStage.recipe_id == recipe_id)
        .count()
    )
    return max(count, 1)


def get_recipe_firing_stage(
    db: Session,
    recipe_id: UUID,
    stage_number: int,
) -> Optional[RecipeFiringStage]:
    """Get a specific firing stage for a recipe."""
    return (
        db.query(RecipeFiringStage)
        .filter(
            RecipeFiringStage.recipe_id == recipe_id,
            RecipeFiringStage.stage_number == stage_number,
        )
        .first()
    )


def get_firing_profile_for_stage(
    db: Session,
    position: OrderPosition,
    stage_number: int,
) -> Optional[FiringProfile]:
    """
    Get the firing profile for a specific stage of a position.
    If recipe_firing_stages has an explicit firing_profile_id → use it.
    Otherwise → auto-match by product_type/collection/thickness.
    """
    stage = get_recipe_firing_stage(db, position.recipe_id, stage_number)

    if stage and stage.firing_profile_id:
        return (
            db.query(FiringProfile)
            .filter(FiringProfile.id == stage.firing_profile_id)
            .first()
        )

    # Auto-match
    return match_firing_profile(
        db,
        position.product_type.value if position.product_type else "tile",
        position.collection,
        position.thickness_mm or Decimal("11.0"),
    )


def group_positions_by_temperature(
    db: Session,
    positions: list[OrderPosition],
    max_temp_delta: int = 50,
) -> list[list[OrderPosition]]:
    """
    Group positions into temperature-compatible buckets for batch formation.

    Each bucket contains positions whose firing temperatures are within
    max_temp_delta of each other.
    """
    # Get temperature for each position from recipe_kiln_config
    pos_with_temp: list[tuple[OrderPosition, int]] = []
    for pos in positions:
        if not pos.recipe_id:
            continue
        config = (
            db.query(RecipeKilnConfig)
            .filter(RecipeKilnConfig.recipe_id == pos.recipe_id)
            .first()
        )
        temp = config.firing_temperature if config and config.firing_temperature else 1100  # default
        pos_with_temp.append((pos, temp))

    # Sort by temperature
    pos_with_temp.sort(key=lambda x: x[1])

    # Group into buckets
    buckets: list[list[OrderPosition]] = []
    current_bucket: list[OrderPosition] = []
    bucket_min_temp: int = 0
    bucket_max_temp: int = 0

    for pos, temp in pos_with_temp:
        if not current_bucket:
            current_bucket.append(pos)
            bucket_min_temp = temp
            bucket_max_temp = temp
        elif temp - bucket_min_temp <= max_temp_delta:
            current_bucket.append(pos)
            bucket_max_temp = max(bucket_max_temp, temp)
        else:
            # Start new bucket
            buckets.append(current_bucket)
            current_bucket = [pos]
            bucket_min_temp = temp
            bucket_max_temp = temp

    if current_bucket:
        buckets.append(current_bucket)

    return buckets
