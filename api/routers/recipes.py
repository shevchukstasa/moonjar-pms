"""CRUD router for recipes — includes firing stages + materials sub-endpoints."""

from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.roles import require_admin, require_management
from api.models import (
    Recipe, RecipeFiringStage, RecipeMaterial, Material,
    FiringTemperatureGroup, FiringTemperatureGroupRecipe,
)
from business.services.firing_profiles import get_temperature_group_recipes
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

logger = logging.getLogger("moonjar.recipes")

router = APIRouter()


# ── helpers ───────────────────────────────────────────────────────────────

def _serialize_recipe_material(rm) -> dict:
    """Serialize a RecipeMaterial row + joined Material fields."""
    result = {
        "id": str(rm.id),
        "recipe_id": str(rm.recipe_id),
        "material_id": str(rm.material_id),
        "material_name": rm.material.name if rm.material else None,
        "material_type": rm.material.material_type if rm.material else None,
        "quantity_per_unit": float(rm.quantity_per_unit),
        "unit": rm.unit,
        "notes": rm.notes,
        # Per-method application rates (set by models agent; safe getattr for migration period)
        "spray_rate": float(rm.spray_rate) if getattr(rm, 'spray_rate', None) else None,
        "brush_rate": float(rm.brush_rate) if getattr(rm, 'brush_rate', None) else None,
        "splash_rate": float(rm.splash_rate) if getattr(rm, 'splash_rate', None) else None,
        "silk_screen_rate": float(rm.silk_screen_rate) if getattr(rm, 'silk_screen_rate', None) else None,
    }
    return result


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
# Shelf coating engobe recipes
# ══════════════════════════════════════════════════════════════════════════

@router.get("/engobe/shelf-coating")
async def list_shelf_coating_recipes(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    List shelf coating engobe recipes.

    Shelf coating protects kiln shelves from glaze drips.
    These are consumed per-batch based on kiln area, not per-piece.
    """
    items = (
        db.query(Recipe)
        .filter(
            Recipe.recipe_type == "engobe",
            Recipe.engobe_type == "shelf_coating",
            Recipe.is_active.is_(True),
        )
        .all()
    )
    results = []
    for item in items:
        if item.glaze_settings is None:
            item.glaze_settings = {}
        d = RecipeResponse.model_validate(item).model_dump(mode="json")
        d["ingredients_count"] = (
            db.query(RecipeMaterial)
            .filter(RecipeMaterial.recipe_id == item.id)
            .count()
        )
        d["temperature_groups"] = _get_temperature_groups_for_recipe(db, item.id)
        results.append(d)

    return {"items": results, "total": len(results)}


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


@router.post("/import-csv", status_code=201)
async def import_recipes_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Import recipes from a CSV file.

    Expected CSV columns: name, color_collection, type, temperature, duration
    - name: Recipe name (required)
    - color_collection: Color collection name
    - type: Recipe type (product, glaze, engobe). Defaults to 'product'.
    - temperature: Firing temperature (stored in glaze_settings)
    - duration: Firing duration in minutes (stored in glaze_settings)

    Skips rows where a recipe with the same name + color_collection already exists.
    """
    import csv
    import io
    from sqlalchemy.exc import IntegrityError

    content = await file.read()
    try:
        text = content.decode("utf-8-sig")  # handle BOM
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))

    created_count = 0
    skipped_count = 0
    errors = []

    for row_num, row in enumerate(reader, start=2):  # row 1 is header
        # Normalize keys (strip whitespace, lowercase)
        row = {k.strip().lower(): (v.strip() if v else "") for k, v in row.items() if k}

        name = row.get("name", "").strip()
        if not name:
            errors.append({"row": row_num, "error": "Missing required field: name"})
            continue

        color_collection = row.get("color_collection", "").strip() or None
        recipe_type = row.get("type", "").strip() or "product"
        if recipe_type not in ("product", "glaze", "engobe"):
            errors.append({"row": row_num, "error": f"Invalid type: {recipe_type}"})
            continue

        # Check for existing recipe with same name + collection
        existing = db.query(Recipe).filter(
            Recipe.name == name,
            Recipe.color_collection == color_collection,
        ).first()
        if existing:
            skipped_count += 1
            continue

        # Parse optional numeric fields
        temperature = None
        duration = None
        try:
            if row.get("temperature"):
                temperature = float(row["temperature"])
        except ValueError:
            errors.append({"row": row_num, "error": f"Invalid temperature: {row.get('temperature')}"})
            continue
        try:
            if row.get("duration"):
                duration = float(row["duration"])
        except ValueError:
            errors.append({"row": row_num, "error": f"Invalid duration: {row.get('duration')}"})
            continue

        glaze_settings = {}
        if temperature is not None:
            glaze_settings["temperature"] = temperature
        if duration is not None:
            glaze_settings["duration_minutes"] = duration

        recipe = Recipe(
            name=name,
            color_collection=color_collection,
            recipe_type=recipe_type,
            glaze_settings=glaze_settings,
        )
        db.add(recipe)
        try:
            db.flush()
            created_count += 1
        except IntegrityError:
            db.rollback()
            skipped_count += 1

    db.commit()

    return {
        "created_count": created_count,
        "skipped_count": skipped_count,
        "errors": errors,
    }


# ══════════════════════════════════════════════════════════════════════════
# Temperature Groups — convenience endpoints on /recipes prefix
# ══════════════════════════════════════════════════════════════════════════

@router.get("/temperature-groups")
async def list_temperature_groups(
    include_inactive: bool = Query(False, description="Include deactivated groups"),
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """List all firing temperature groups. Management role required."""
    query = db.query(FiringTemperatureGroup)
    if not include_inactive:
        query = query.filter(FiringTemperatureGroup.is_active.is_(True))
    groups = query.order_by(
        FiringTemperatureGroup.display_order,
        FiringTemperatureGroup.name,
    ).all()
    items = [
        {
            "id": str(g.id),
            "name": g.name,
            "temperature": g.temperature,
            "description": g.description,
            "is_active": g.is_active,
            "display_order": g.display_order,
        }
        for g in groups
    ]
    return {"items": items, "total": len(items)}


@router.get("/temperature-groups/{group_id}/recipes")
async def list_temperature_group_recipes(
    group_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Get all recipes linked to a temperature group. Management role required."""
    group = db.query(FiringTemperatureGroup).filter(
        FiringTemperatureGroup.id == group_id,
    ).first()
    if not group:
        raise HTTPException(404, "Temperature group not found")

    links = get_temperature_group_recipes(db, group_id)
    items = []
    for link in links:
        recipe = db.query(Recipe).filter(Recipe.id == link.recipe_id).first()
        if recipe:
            if recipe.glaze_settings is None:
                recipe.glaze_settings = {}
            d = RecipeResponse.model_validate(recipe).model_dump(mode="json")
            d["is_default"] = link.is_default
            items.append(d)
    return {"items": items, "total": len(items)}


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

    # ── Auto-apply new recipe to all AWAITING_RECIPE positions with matching color ──
    # When a PM creates a new recipe, any position currently blocked by
    # "awaiting_recipe" whose color matches the recipe name should be unblocked
    # in one shot — not one by one.
    try:
        from api.models import OrderPosition, Task
        from api.enums import PositionStatus, TaskStatus, TaskType
        from sqlalchemy import func
        from business.services.status_machine import transition_position_status
        from business.services.production_scheduler import reschedule_position
        from datetime import datetime, timezone
        import uuid as uuid_mod

        # Match by exact name OR by custom code (e.g. recipe "Custom K6 Red Terracotta"
        # should match positions with color "Custom K6", "Custom K6 Exclusive", etc.)
        import re as _re
        _recipe_name_lower = item.name.strip().lower()
        _custom_code_match = _re.match(r'^custom\s+([a-z]\d+)', _recipe_name_lower, _re.IGNORECASE)

        if _custom_code_match:
            _code = _custom_code_match.group(1).lower()  # e.g. "k6"
            # Match positions whose color starts with "Custom {code}" (case-insensitive)
            matching = db.query(OrderPosition).filter(
                OrderPosition.status == PositionStatus.AWAITING_RECIPE.value,
                func.lower(func.trim(OrderPosition.color)).like(f"custom {_code}%"),
            ).all()
        else:
            matching = db.query(OrderPosition).filter(
                OrderPosition.status == PositionStatus.AWAITING_RECIPE.value,
                func.lower(func.trim(OrderPosition.color)) == _recipe_name_lower,
            ).all()

        if matching:
            now = datetime.now(timezone.utc)
            unblocked_count = 0
            for pos in matching:
                try:
                    pos.recipe_id = item.id

                    # Close blocking tasks on this position
                    blocking_tasks = db.query(Task).filter(
                        Task.related_position_id == pos.id,
                        Task.blocking.is_(True),
                        Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS]),
                    ).all()
                    for t in blocking_tasks:
                        t.status = TaskStatus.DONE
                        t.completed_at = now
                        t.updated_at = now

                    # Transition back to PLANNED
                    transition_position_status(
                        db, pos.id, PositionStatus.PLANNED.value,
                        changed_by=current_user.id,
                        is_override=True,
                        notes=f"Auto-unblocked: recipe '{item.name}' created",
                    )

                    # Reschedule
                    try:
                        reschedule_position(db, pos)
                    except Exception as _e:
                        logger.warning(
                            "Failed to reschedule position %s after recipe auto-bind: %s",
                            pos.id, _e,
                        )
                    unblocked_count += 1
                except Exception as e:
                    logger.warning(
                        "Failed to auto-bind recipe %s to position %s: %s",
                        item.id, pos.id, e,
                    )
            if unblocked_count:
                db.commit()
                logger.info(
                    "RECIPE_AUTO_BIND | recipe=%s color=%s unblocked=%d positions",
                    item.name, item.name, unblocked_count,
                )
    except Exception as e:
        logger.warning("Auto-bind recipe to blocked positions failed: %s", e)
        db.rollback()

    # RAG indexing (best-effort)
    try:
        import os
        if os.getenv("OPENAI_API_KEY"):
            from business.rag.embeddings import index_recipe
            await index_recipe(db, item.id)
            db.commit()
    except Exception as e:
        logger.debug("RAG indexing failed for recipe %s: %s", item.id, e)

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

    # RAG indexing (best-effort)
    try:
        import os
        if os.getenv("OPENAI_API_KEY"):
            from business.rag.embeddings import index_recipe
            await index_recipe(db, item.id)
            db.commit()
    except Exception as e:
        logger.debug("RAG indexing failed for recipe %s: %s", item.id, e)

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
    # Clear child records before deleting (mirrors bulk_delete_recipes logic)
    db.query(RecipeMaterial).filter(RecipeMaterial.recipe_id == item_id).delete(synchronize_session=False)
    db.query(FiringTemperatureGroupRecipe).filter(FiringTemperatureGroupRecipe.recipe_id == item_id).delete(synchronize_session=False)
    db.query(RecipeFiringStage).filter(RecipeFiringStage.recipe_id == item_id).delete(synchronize_session=False)
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
        # Per-method application rates (safe setattr for migration period)
        if mat_data.spray_rate is not None and hasattr(rm, 'spray_rate'):
            rm.spray_rate = mat_data.spray_rate
        if mat_data.brush_rate is not None and hasattr(rm, 'brush_rate'):
            rm.brush_rate = mat_data.brush_rate
        if mat_data.splash_rate is not None and hasattr(rm, 'splash_rate'):
            rm.splash_rate = mat_data.splash_rate
        if mat_data.silk_screen_rate is not None and hasattr(rm, 'silk_screen_rate'):
            rm.silk_screen_rate = mat_data.silk_screen_rate
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
