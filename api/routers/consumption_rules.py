"""CRUD router for consumption calculation rules (glaze/engobe ml per m2)."""

from uuid import UUID
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.roles import require_admin
from api.models import ConsumptionRule, Size

router = APIRouter()


# ── Pydantic schemas ─────────────────────────────────────────

class ConsumptionRuleInput(BaseModel):
    rule_number: int
    name: str
    description: Optional[str] = None
    collection: Optional[str] = None
    color_collection: Optional[str] = None
    product_type: Optional[str] = None
    size_id: Optional[UUID] = None
    shape: Optional[str] = None
    thickness_mm_min: Optional[float] = None
    thickness_mm_max: Optional[float] = None
    place_of_application: Optional[str] = None
    recipe_type: Optional[str] = None
    application_method: Optional[str] = None
    consumption_ml_per_sqm: float
    coats: int = 1
    specific_gravity_override: Optional[float] = None
    priority: int = 0
    is_active: bool = True
    notes: Optional[str] = None


class ConsumptionRuleUpdate(BaseModel):
    rule_number: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    collection: Optional[str] = None
    color_collection: Optional[str] = None
    product_type: Optional[str] = None
    size_id: Optional[UUID] = None
    shape: Optional[str] = None
    thickness_mm_min: Optional[float] = None
    thickness_mm_max: Optional[float] = None
    place_of_application: Optional[str] = None
    recipe_type: Optional[str] = None
    application_method: Optional[str] = None
    consumption_ml_per_sqm: Optional[float] = None
    coats: Optional[int] = None
    specific_gravity_override: Optional[float] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────

def _serialize_rule(r: ConsumptionRule) -> dict:
    size_name = None
    if r.size:
        size_name = r.size.name
    return {
        "id": str(r.id),
        "rule_number": r.rule_number,
        "name": r.name,
        "description": r.description,
        "collection": r.collection,
        "color_collection": r.color_collection,
        "product_type": r.product_type,
        "size_id": str(r.size_id) if r.size_id else None,
        "size_name": size_name,
        "shape": r.shape,
        "thickness_mm_min": float(r.thickness_mm_min) if r.thickness_mm_min else None,
        "thickness_mm_max": float(r.thickness_mm_max) if r.thickness_mm_max else None,
        "place_of_application": r.place_of_application,
        "recipe_type": r.recipe_type,
        "application_method": r.application_method,
        "consumption_ml_per_sqm": float(r.consumption_ml_per_sqm),
        "coats": r.coats,
        "specific_gravity_override": float(r.specific_gravity_override) if r.specific_gravity_override else None,
        "priority": r.priority,
        "is_active": r.is_active,
        "notes": r.notes,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }


# ── CRUD ──────────────────────────────────────────────────────

@router.get("")
async def list_consumption_rules(
    include_inactive: bool = Query(False),
    recipe_type: Optional[str] = Query(None),
    product_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List all consumption rules, ordered by rule_number."""
    query = db.query(ConsumptionRule)
    if not include_inactive:
        query = query.filter(ConsumptionRule.is_active.is_(True))
    if recipe_type:
        query = query.filter(ConsumptionRule.recipe_type == recipe_type)
    if product_type:
        query = query.filter(ConsumptionRule.product_type == product_type)
    items = query.order_by(ConsumptionRule.rule_number).all()
    return [_serialize_rule(r) for r in items]


@router.get("/{rule_id}")
async def get_consumption_rule(
    rule_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    r = db.query(ConsumptionRule).filter(ConsumptionRule.id == rule_id).first()
    if not r:
        raise HTTPException(404, "Consumption rule not found")
    return _serialize_rule(r)


@router.post("", status_code=201)
async def create_consumption_rule(
    data: ConsumptionRuleInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    r = ConsumptionRule(**data.model_dump())
    db.add(r)
    db.commit()
    db.refresh(r)
    return _serialize_rule(r)


@router.patch("/{rule_id}")
async def update_consumption_rule(
    rule_id: UUID,
    data: ConsumptionRuleUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    r = db.query(ConsumptionRule).filter(ConsumptionRule.id == rule_id).first()
    if not r:
        raise HTTPException(404, "Consumption rule not found")

    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(r, k, v)
    r.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(r)
    return _serialize_rule(r)


@router.delete("/{rule_id}")
async def delete_consumption_rule(
    rule_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    r = db.query(ConsumptionRule).filter(ConsumptionRule.id == rule_id).first()
    if not r:
        raise HTTPException(404, "Consumption rule not found")
    db.delete(r)
    db.commit()
    return {"ok": True}
