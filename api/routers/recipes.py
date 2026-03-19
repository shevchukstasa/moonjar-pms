"""CRUD router for recipes — includes firing stages + materials sub-endpoints."""

from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.models import (
    Recipe, RecipeFiringStage, RecipeMaterial, Material,
    FiringTemperatureGroup, FiringTemperatureGroupRecipe,
)
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

import logging

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


def _get_temperature_groups_for_recipe(db: Session, recipe_id: UUID) -> list[dict]:
    """Get temperature groups linked to a recipe."""
    links = (
        db.query(FiringTemperatureGroupRecipe)
        .filter(FiringTemperatureGroupRecipe.recipe_id == recipe_id)
        .all()
    )
    result = []
    for link in links:
        group = db.query(FiringTemperatureGroup).filter(
            FiringTemperatureGroup.id == link.temperature_group_id
        ).first()
        if group:
            result.append({
                "id": str(group.id),
                "name": group.name,
                "temperature": group.temperature,
                "min_temperature": group.min_temperature,  # deprecated
                "max_temperature": group.max_temperature,  # deprecated
                "description": group.description,
                "is_default": link.is_default,
            })
    return result


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
        # Guard against NULL glaze_settings in DB (legacy data)
        if item.glaze_settings is None:
            item.glaze_settings = {}
        d = RecipeResponse.model_validate(item).model_dump(mode="json")
        # Count ingredients for the list view
        d["ingredients_count"] = (
            db.query(RecipeMaterial)
            .filter(RecipeMaterial.recipe_id == item.id)
            .count()
        )
        # Temperature groups for this recipe
        d["temperature_groups"] = _get_temperature_groups_for_recipe(db, item.id)
        results.append(d)

    return {
        "items": results,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/lookup")
async def lookup_recipe(
    collection: str = Query(None),
    color: str = Query(None),
    size: str = Query(None),
    shape: str = Query(None),
    finish: str = Query(None),
    thickness: float = Query(None),
    application_type: str = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Look up recipe by up to 7 fields.  Returns best match + alternatives.

    Priority fields (match on Recipe columns):
      - collection  → Recipe.color_collection
      - color       → Recipe.name

    Optional fields (match via Recipe.glaze_settings JSONB):
      - finish      → glaze_settings.finishing_type
      - application_type → glaze_settings.place_of_application
      - size        → glaze_settings.size
      - shape       → glaze_settings.shape
      - thickness   → glaze_settings.thickness
    """
    log = logging.getLogger(__name__)

    # ── optional JSONB filters (least-specific → most-specific ordering) ──
    optional_filters: list[tuple[str, object]] = []

    if thickness is not None:
        optional_filters.append((
            "thickness",
            lambda q, v=str(thickness): q.filter(
                Recipe.glaze_settings["thickness"].astext == v
            ),
        ))
    if shape:
        optional_filters.append((
            "shape",
            lambda q, v=shape: q.filter(
                Recipe.glaze_settings["shape"].astext == v
            ),
        ))
    if size:
        optional_filters.append((
            "size",
            lambda q, v=size: q.filter(
                Recipe.glaze_settings["size"].astext == v
            ),
        ))
    if finish:
        optional_filters.append((
            "finish",
            lambda q, v=finish: q.filter(
                Recipe.glaze_settings["finishing_type"].astext == v
            ),
        ))
    if application_type:
        optional_filters.append((
            "application_type",
            lambda q, v=application_type: q.filter(
                Recipe.glaze_settings["place_of_application"].astext == v
            ),
        ))

    best_match = None
    match_type = "none"
    fields_matched: list[str] = []

    for drop_count in range(len(optional_filters) + 1):
        active = optional_filters[drop_count:]
        active_labels = [label for label, _ in active]

        base = db.query(Recipe).filter(Recipe.is_active.is_(True))
        if collection:
            base = base.filter(Recipe.color_collection == collection)
        if color:
            base = base.filter(Recipe.name == color)

        q = base
        for _, apply_filter in active:
            q = apply_filter(q)

        results = q.all()
        if results:
            best_match = results[0]
            matched = []
            if collection:
                matched.append("collection")
            if color:
                matched.append("color")
            matched.extend(active_labels)
            fields_matched = matched

            total_optional = len(optional_filters)
            used_optional = len(active)
            if used_optional == total_optional and total_optional >= 5:
                match_type = "exact_7"
            elif used_optional == total_optional and total_optional >= 2:
                match_type = "exact_4"
            elif used_optional > 0:
                match_type = "partial"
            else:
                match_type = "partial"
            break

    # Collect alternatives: all active recipes matching collection+color
    alt_query = db.query(Recipe).filter(Recipe.is_active.is_(True))
    if collection:
        alt_query = alt_query.filter(Recipe.color_collection == collection)
    if color:
        alt_query = alt_query.filter(Recipe.name == color)
    all_candidates = alt_query.all()

    alternatives = []
    for r in all_candidates:
        if best_match and str(r.id) == str(best_match.id):
            continue
        if r.glaze_settings is None:
            r.glaze_settings = {}
        alternatives.append(
            RecipeResponse.model_validate(r).model_dump(mode="json")
        )

    match_data = None
    if best_match:
        if best_match.glaze_settings is None:
            best_match.glaze_settings = {}
        match_data = RecipeResponse.model_validate(best_match).model_dump(mode="json")

    return {
        "match": match_data,
        "match_type": match_type,
        "fields_matched": fields_matched,
        "alternatives": alternatives[:10],
        "total_candidates": len(all_candidates),
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

    # Guard against NULL glaze_settings in DB (legacy data)
    if item.glaze_settings is None:
        item.glaze_settings = {}
    d = RecipeResponse.model_validate(item).model_dump(mode="json")

    # Include materials (ingredients)
    mats = (
        db.query(RecipeMaterial)
        .filter(RecipeMaterial.recipe_id == item_id)
        .all()
    )
    d["materials"] = [_serialize_recipe_material(rm) for rm in mats]

    # Temperature groups for this recipe
    d["temperature_groups"] = _get_temperature_groups_for_recipe(db, item_id)
    return d


@router.post("", response_model=RecipeResponse, status_code=201)
async def create_recipes_item(
    data: RecipeCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    import uuid as uuid_mod
    from sqlalchemy.exc import IntegrityError

    create_data = data.model_dump(exclude={'clone_from_id'}, exclude_none=True)
    # Ensure glaze_settings is always a dict (never None)
    create_data.setdefault('glaze_settings', {})
    item = Recipe(**create_data)
    db.add(item)
    try:
        db.flush()
    except IntegrityError as e:
        db.rollback()
        err_msg = str(e.orig) if e.orig else str(e)
        if 'uq_recipes_colcollection_name' in err_msg or 'duplicate key' in err_msg.lower():
            raise HTTPException(
                409,
                f"Recipe '{data.name}' already exists in this color collection"
            )
        raise HTTPException(400, f"Database error: {err_msg}")

    # Clone materials + firing stages from source recipe if specified
    if data.clone_from_id:
        source = db.query(Recipe).filter(Recipe.id == data.clone_from_id).first()
        if source:
            # Clone recipe materials
            try:
                source_materials = db.query(RecipeMaterial).filter(
                    RecipeMaterial.recipe_id == source.id
                ).all()
                for rm in source_materials:
                    new_rm = RecipeMaterial(
                        id=uuid_mod.uuid4(),
                        recipe_id=item.id,
                        material_id=rm.material_id,
                        quantity_per_unit=rm.quantity_per_unit,
                        unit=rm.unit,
                        notes=rm.notes,
                    )
                    db.add(new_rm)
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Clone materials failed: {e}")

            # Clone firing stages
            try:
                source_stages = db.query(RecipeFiringStage).filter(
                    RecipeFiringStage.recipe_id == source.id
                ).all()
                for stage in source_stages:
                    new_stage = RecipeFiringStage(
                        id=uuid_mod.uuid4(),
                        recipe_id=item.id,
                        stage_number=stage.stage_number,
                        firing_profile_id=stage.firing_profile_id,
                        requires_glazing_before=stage.requires_glazing_before,
                        description=stage.description,
                    )
                    db.add(new_stage)
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Clone firing stages failed: {e}")

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
    # Ensure glaze_settings is never None
    if item.glaze_settings is None:
        item.glaze_settings = {}
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


from pydantic import BaseModel as _BM

class _BulkDeleteInput(_BM):
    ids: List[str]

@router.post("/bulk-delete", status_code=200)
async def bulk_delete_recipes(
    data: _BulkDeleteInput,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Delete multiple recipes by IDs."""
    if not data.ids:
        return {"deleted": 0}
    # Delete linked recipe_materials first
    db.query(RecipeMaterial).filter(
        RecipeMaterial.recipe_id.in_(data.ids)
    ).delete(synchronize_session=False)
    # Delete linked temperature group assignments
    db.query(FiringTemperatureGroupRecipe).filter(
        FiringTemperatureGroupRecipe.recipe_id.in_(data.ids)
    ).delete(synchronize_session=False)
    # Delete linked firing stages
    db.query(RecipeFiringStage).filter(
        RecipeFiringStage.recipe_id.in_(data.ids)
    ).delete(synchronize_session=False)
    # Delete recipes
    deleted = db.query(Recipe).filter(
        Recipe.id.in_(data.ids)
    ).delete(synchronize_session=False)
    db.commit()
    return {"deleted": deleted}


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
