"""CRUD router for recipes — includes firing stages sub-endpoints."""

from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.models import Recipe, RecipeFiringStage
from api.schemas import (
    RecipeCreate,
    RecipeUpdate,
    RecipeResponse,
    RecipeFiringStageCreate,
    RecipeFiringStageResponse,
    RecipeFiringStagesBulkUpdate,
)

router = APIRouter()


@router.get("", response_model=dict)
async def list_recipes(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(Recipe)
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return {
        "items": [RecipeResponse.model_validate(item).model_dump(mode="json") for item in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/{item_id}", response_model=RecipeResponse)
async def get_recipes_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(Recipe).filter(Recipe.id == item_id).first()
    if not item:
        raise HTTPException(404, "Recipe not found")
    return item


@router.post("", response_model=RecipeResponse, status_code=201)
async def create_recipes_item(
    data: RecipeCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = Recipe(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=RecipeResponse)
async def update_recipes_item(
    item_id: UUID,
    data: RecipeUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(Recipe).filter(Recipe.id == item_id).first()
    if not item:
        raise HTTPException(404, "Recipe not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
async def delete_recipes_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(Recipe).filter(Recipe.id == item_id).first()
    if not item:
        raise HTTPException(404, "Recipe not found")
    db.delete(item)
    db.commit()


# --- Recipe Firing Stages sub-endpoints ---


@router.get("/{recipe_id}/firing-stages", response_model=List[RecipeFiringStageResponse])
async def list_recipe_firing_stages(
    recipe_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get all firing stages for a recipe, ordered by stage_number."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(404, "Recipe not found")
    stages = (
        db.query(RecipeFiringStage)
        .filter(RecipeFiringStage.recipe_id == recipe_id)
        .order_by(RecipeFiringStage.stage_number)
        .all()
    )
    return stages


@router.put("/{recipe_id}/firing-stages", response_model=List[RecipeFiringStageResponse])
async def bulk_update_recipe_firing_stages(
    recipe_id: UUID,
    data: RecipeFiringStagesBulkUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Replace all firing stages for a recipe (bulk upsert)."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(404, "Recipe not found")

    # Delete existing stages
    db.query(RecipeFiringStage).filter(RecipeFiringStage.recipe_id == recipe_id).delete()

    # Create new stages
    new_stages = []
    for stage_data in data.stages:
        stage = RecipeFiringStage(
            recipe_id=recipe_id,
            **stage_data.model_dump(),
        )
        db.add(stage)
        new_stages.append(stage)

    db.commit()
    for s in new_stages:
        db.refresh(s)
    return new_stages
