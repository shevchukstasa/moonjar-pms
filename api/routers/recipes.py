"""CRUD router for recipes — includes firing stages + materials sub-endpoints."""

from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.models import Recipe, RecipeFiringStage, RecipeMaterial, Material
from api.schemas import (
    RecipeCreate,
    RecipeUpdate,
    RecipeResponse,
    RecipeFiringStageCreate,
    RecipeFiringStageResponse,
    RecipeFiringStagesBulkUpdate,
    RecipeMaterialBulkItem,
    RecipeMaterialsBulkUpdate,
    RecipeMaterialResponse,
)

router = APIRouter()


# ── helpers ───────────────────────────────────────────────────────────────

def _serialize_recipe_material(rm) -> dict:
    """Serialize a RecipeMaterial row + joined Material fields."""
    return {
        "id": str(rm.id),
        "recipe_id": str(rm.recipe_id),
        "material_id": str(rm.material_id),
        "material_name": rm.material.name if rm.material else None,
        "material_type": rm.material.material_type if rm.material else None,
        "quantity_per_unit": float(rm.quantity_per_unit),
        "unit": rm.unit,
        "notes": rm.notes,
    }


# ══════════════════════════════════════════════════════════════════════════
# Recipe CRUD
# ══════════════════════════════════════════════════════════════════════════

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

    results = []
    for item in items:
        d = RecipeResponse.model_validate(item).model_dump(mode="json")
        # Count ingredients for the list view
        d["ingredients_count"] = (
            db.query(RecipeMaterial)
            .filter(RecipeMaterial.recipe_id == item.id)
            .count()
        )
        results.append(d)

    return {
        "items": results,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/{item_id}")
async def get_recipes_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(Recipe).filter(Recipe.id == item_id).first()
    if not item:
        raise HTTPException(404, "Recipe not found")

    d = RecipeResponse.model_validate(item).model_dump(mode="json")

    # Include materials (ingredients)
    mats = (
        db.query(RecipeMaterial)
        .filter(RecipeMaterial.recipe_id == item_id)
        .all()
    )
    d["materials"] = [_serialize_recipe_material(rm) for rm in mats]
    return d


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


# ══════════════════════════════════════════════════════════════════════════
# Recipe Materials (ingredients) — bulk upsert
# ══════════════════════════════════════════════════════════════════════════

@router.get("/{recipe_id}/materials", response_model=List[dict])
async def list_recipe_materials(
    recipe_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get all ingredients for a recipe, with material name/type."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(404, "Recipe not found")
    mats = (
        db.query(RecipeMaterial)
        .filter(RecipeMaterial.recipe_id == recipe_id)
        .all()
    )
    return [_serialize_recipe_material(rm) for rm in mats]


@router.put("/{recipe_id}/materials", response_model=List[dict])
async def bulk_update_recipe_materials(
    recipe_id: UUID,
    data: RecipeMaterialsBulkUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Replace all ingredients of a recipe (bulk upsert)."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(404, "Recipe not found")

    # Delete existing
    db.query(RecipeMaterial).filter(RecipeMaterial.recipe_id == recipe_id).delete()

    # Create new
    new_items = []
    for mat_data in data.materials:
        rm = RecipeMaterial(
            recipe_id=recipe_id,
            material_id=mat_data.material_id,
            quantity_per_unit=mat_data.quantity_per_unit,
            unit=mat_data.unit,
            notes=mat_data.notes,
        )
        db.add(rm)
        new_items.append(rm)

    db.commit()
    for rm in new_items:
        db.refresh(rm)

    return [_serialize_recipe_material(rm) for rm in new_items]


# ══════════════════════════════════════════════════════════════════════════
# Recipe Firing Stages sub-endpoints
# ══════════════════════════════════════════════════════════════════════════

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
