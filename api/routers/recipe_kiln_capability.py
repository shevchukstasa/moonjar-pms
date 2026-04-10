"""Recipe × kiln capability matrix endpoints — Layer 4 of the firing model.

Determines which recipes can be fired on which kilns. If no capability
rows exist for a recipe, the scheduler assumes it can go anywhere (open
policy). As soon as at least one row exists, the recipe is locked to
those kilns only (closed policy).

Main endpoints:
- GET  /recipes/{recipe_id}/kiln-capabilities           — list matrix
- PUT  /recipes/{recipe_id}/kiln-capabilities/{kiln_id} — upsert
- DELETE /recipes/{recipe_id}/kiln-capabilities/{kiln_id}
- GET  /kilns/{kiln_id}/recipe-capabilities             — reverse lookup
- POST /kilns/{kiln_id}/recipe-capabilities/mark-requalification
       — called when equipment changes; flips needs_requalification
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session, joinedload

from api.auth import get_current_user
from api.database import get_db
from api.models import (
    KilnEquipmentConfig,
    Recipe,
    RecipeKilnCapability,
    Resource,
    ResourceType,
)

router = APIRouter()


# ── Pydantic ────────────────────────────────────────────────────────────────

class CapabilityRow(BaseModel):
    id: Optional[UUID] = None
    recipe_id: UUID
    kiln_id: UUID
    kiln_name: Optional[str] = None
    factory_id: Optional[UUID] = None
    is_qualified: bool = False
    quality_rating: Optional[int] = Field(None, ge=1, le=5)
    success_count: int = 0
    failure_count: int = 0
    last_fired_at: Optional[datetime] = None
    needs_requalification: bool = False
    notes: Optional[str] = None
    current_equipment_config_id: Optional[UUID] = None
    last_qualified_equipment_config_id: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)


class CapabilityUpsert(BaseModel):
    is_qualified: bool
    quality_rating: Optional[int] = Field(None, ge=1, le=5)
    notes: Optional[str] = None


class RecipeCapRow(BaseModel):
    recipe_id: UUID
    recipe_name: Optional[str] = None
    is_qualified: bool
    quality_rating: Optional[int] = None
    needs_requalification: bool
    last_fired_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ── Helpers ─────────────────────────────────────────────────────────────────

def _current_config_id(db: Session, kiln_id: UUID) -> Optional[UUID]:
    row = (
        db.query(KilnEquipmentConfig.id)
        .filter(
            KilnEquipmentConfig.kiln_id == kiln_id,
            KilnEquipmentConfig.effective_to.is_(None),
        )
        .first()
    )
    return row[0] if row else None


def _to_row(cap: RecipeKilnCapability, current_cfg: Optional[UUID]) -> CapabilityRow:
    return CapabilityRow(
        id=cap.id,
        recipe_id=cap.recipe_id,
        kiln_id=cap.kiln_id,
        kiln_name=cap.kiln.name if cap.kiln else None,
        factory_id=cap.kiln.factory_id if cap.kiln else None,
        is_qualified=cap.is_qualified,
        quality_rating=cap.quality_rating,
        success_count=cap.success_count,
        failure_count=cap.failure_count,
        last_fired_at=cap.last_fired_at,
        needs_requalification=cap.needs_requalification,
        notes=cap.notes,
        current_equipment_config_id=current_cfg,
        last_qualified_equipment_config_id=cap.last_qualified_equipment_config_id,
    )


# ── Recipe → kilns ──────────────────────────────────────────────────────────

@router.get(
    "/recipes/{recipe_id}/kiln-capabilities",
    response_model=list[CapabilityRow],
)
def list_recipe_capabilities(
    recipe_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Returns one row per active kiln in the system (across factories).

    Kilns that have no capability row yet are returned as non-qualified
    rows with id=None so the frontend can render the full matrix and
    let the user toggle them.
    """
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(404, "Recipe not found")

    kilns = (
        db.query(Resource)
        .filter(
            Resource.resource_type == ResourceType.KILN,
            Resource.is_active.is_(True),
        )
        .order_by(Resource.name)
        .all()
    )
    existing: dict[UUID, RecipeKilnCapability] = {
        c.kiln_id: c
        for c in db.query(RecipeKilnCapability)
        .options(joinedload(RecipeKilnCapability.kiln))
        .filter(RecipeKilnCapability.recipe_id == recipe_id)
        .all()
    }

    out: list[CapabilityRow] = []
    for kiln in kilns:
        current_cfg = _current_config_id(db, kiln.id)
        cap = existing.get(kiln.id)
        if cap is not None:
            out.append(_to_row(cap, current_cfg))
        else:
            out.append(
                CapabilityRow(
                    id=None,
                    recipe_id=recipe_id,
                    kiln_id=kiln.id,
                    kiln_name=kiln.name,
                    factory_id=kiln.factory_id,
                    is_qualified=False,
                    quality_rating=None,
                    success_count=0,
                    failure_count=0,
                    needs_requalification=False,
                    notes=None,
                    current_equipment_config_id=current_cfg,
                    last_qualified_equipment_config_id=None,
                )
            )
    return out


@router.put(
    "/recipes/{recipe_id}/kiln-capabilities/{kiln_id}",
    response_model=CapabilityRow,
)
def upsert_capability(
    recipe_id: UUID,
    kiln_id: UUID,
    payload: CapabilityUpsert,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not db.query(Recipe).filter(Recipe.id == recipe_id).first():
        raise HTTPException(404, "Recipe not found")
    kiln = (
        db.query(Resource)
        .filter(Resource.id == kiln_id, Resource.resource_type == ResourceType.KILN)
        .first()
    )
    if not kiln:
        raise HTTPException(404, "Kiln not found")

    cap = (
        db.query(RecipeKilnCapability)
        .filter(
            RecipeKilnCapability.recipe_id == recipe_id,
            RecipeKilnCapability.kiln_id == kiln_id,
        )
        .first()
    )
    if cap is None:
        cap = RecipeKilnCapability(recipe_id=recipe_id, kiln_id=kiln_id)
        db.add(cap)

    cap.is_qualified = payload.is_qualified
    cap.quality_rating = payload.quality_rating
    cap.notes = payload.notes
    # Recording qualification clears the requalification flag and
    # pins the current equipment config as the baseline
    if payload.is_qualified:
        cap.needs_requalification = False
        cap.last_qualified_equipment_config_id = _current_config_id(db, kiln_id)
        cap.qualified_by = current_user.id

    db.commit()
    db.refresh(cap)
    cap.kiln = kiln
    return _to_row(cap, _current_config_id(db, kiln_id))


@router.delete(
    "/recipes/{recipe_id}/kiln-capabilities/{kiln_id}",
    status_code=204,
)
def delete_capability(
    recipe_id: UUID,
    kiln_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    cap = (
        db.query(RecipeKilnCapability)
        .filter(
            RecipeKilnCapability.recipe_id == recipe_id,
            RecipeKilnCapability.kiln_id == kiln_id,
        )
        .first()
    )
    if cap:
        db.delete(cap)
        db.commit()


# ── Kiln → recipes (reverse lookup) ─────────────────────────────────────────

@router.get(
    "/kilns/{kiln_id}/recipe-capabilities",
    response_model=list[RecipeCapRow],
)
def list_kiln_recipes(
    kiln_id: UUID,
    qualified_only: bool = False,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = (
        db.query(RecipeKilnCapability)
        .options(joinedload(RecipeKilnCapability.recipe))
        .filter(RecipeKilnCapability.kiln_id == kiln_id)
    )
    if qualified_only:
        q = q.filter(RecipeKilnCapability.is_qualified.is_(True))
    rows = q.all()
    return [
        RecipeCapRow(
            recipe_id=c.recipe_id,
            recipe_name=c.recipe.name if c.recipe else None,
            is_qualified=c.is_qualified,
            quality_rating=c.quality_rating,
            needs_requalification=c.needs_requalification,
            last_fired_at=c.last_fired_at,
        )
        for c in rows
    ]


@router.post(
    "/kilns/{kiln_id}/recipe-capabilities/mark-requalification",
    response_model=dict,
)
def mark_requalification(
    kiln_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Flip needs_requalification=true on all capabilities for this kiln.

    Called automatically when equipment changes (Layer 1). Also exposed
    as a manual endpoint in case production wants to force requalification
    (e.g. after a major incident).
    """
    count = (
        db.query(RecipeKilnCapability)
        .filter(RecipeKilnCapability.kiln_id == kiln_id)
        .update({"needs_requalification": True}, synchronize_session=False)
    )
    db.commit()
    return {"updated": count}
