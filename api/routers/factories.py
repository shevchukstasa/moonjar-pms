"""CRUD router for factories (auto-generated)."""

from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.roles import require_admin
from api.models import Factory, OrderPosition, Resource
from api.enums import KilnConstantsMode, PositionStatus, ResourceType
from api.schemas import FactoryCreate, FactoryUpdate, FactoryResponse

router = APIRouter()


@router.get("", response_model=dict)
async def list_factories(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(Factory)
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return {
        "items": [FactoryResponse.model_validate(i).model_dump(mode="json") for i in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.patch("/{item_id}/kiln-mode")
async def switch_kiln_mode(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Toggle factory kiln constants mode between 'manual' and 'production'."""
    item = db.query(Factory).filter(Factory.id == item_id).first()
    if not item:
        raise HTTPException(404, "Factory not found")

    # Toggle mode
    current_mode = item.kiln_constants_mode
    if current_mode == KilnConstantsMode.MANUAL:
        item.kiln_constants_mode = KilnConstantsMode.PRODUCTION
    else:
        item.kiln_constants_mode = KilnConstantsMode.MANUAL

    db.commit()
    db.refresh(item)

    new_mode = item.kiln_constants_mode
    return {
        "id": str(item.id),
        "name": item.name,
        "kiln_constants_mode": new_mode.value if hasattr(new_mode, "value") else str(new_mode),
    }


# === FACTORY WORKLOAD ESTIMATE (Decision 2026-03-19) ===

# Terminal statuses excluded from active workload
_TERMINAL_STATUSES = {
    PositionStatus.SHIPPED,
    PositionStatus.CANCELLED,
    PositionStatus.MERGED,
}

# Map position statuses to logical stages for grouping
_STAGE_MAP = {
    PositionStatus.PLANNED: "planning",
    PositionStatus.INSUFFICIENT_MATERIALS: "planning",
    PositionStatus.AWAITING_RECIPE: "planning",
    PositionStatus.AWAITING_STENCIL_SILKSCREEN: "planning",
    PositionStatus.AWAITING_COLOR_MATCHING: "planning",
    PositionStatus.AWAITING_SIZE_CONFIRMATION: "planning",
    PositionStatus.ENGOBE_APPLIED: "glazing",
    PositionStatus.ENGOBE_CHECK: "glazing",
    PositionStatus.SENT_TO_GLAZING: "glazing",
    PositionStatus.GLAZED: "glazing",
    PositionStatus.PRE_KILN_CHECK: "pre_kiln",
    PositionStatus.LOADED_IN_KILN: "firing",
    PositionStatus.FIRED: "post_firing",
    PositionStatus.TRANSFERRED_TO_SORTING: "sorting",
    PositionStatus.REFIRE: "firing",
    PositionStatus.AWAITING_REGLAZE: "glazing",
    PositionStatus.SENT_TO_QUALITY_CHECK: "quality",
    PositionStatus.QUALITY_CHECK_DONE: "quality",
    PositionStatus.BLOCKED_BY_QM: "quality",
    PositionStatus.PACKED: "packing",
    PositionStatus.READY_FOR_SHIPMENT: "ready",
}


@router.get("/{factory_id}/estimate")
async def get_factory_estimate(
    factory_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Estimate factory workload: count open positions by stage,
    calculate estimated completion dates based on kiln capacity,
    and return utilization percentage.
    """
    factory = db.query(Factory).filter(Factory.id == factory_id).first()
    if not factory:
        raise HTTPException(404, "Factory not found")

    # Get all active (non-terminal) positions for this factory
    positions = db.query(OrderPosition).filter(
        OrderPosition.factory_id == factory_id,
        OrderPosition.status.notin_(_TERMINAL_STATUSES),
    ).all()

    total_positions = len(positions)

    # Group by stage
    by_stage: dict[str, int] = {}
    for pos in positions:
        stage = _STAGE_MAP.get(pos.status, "other")
        by_stage[stage] = by_stage.get(stage, 0) + 1

    # Kiln capacity estimate
    kilns = db.query(Resource).filter(
        Resource.factory_id == factory_id,
        Resource.resource_type == ResourceType.KILN,
        Resource.status == "active",
    ).all()

    kiln_count = len(kilns)
    # Estimate: each kiln can fire ~1 batch/day, ~20 positions/batch (rough default)
    daily_capacity = kiln_count * 20 if kiln_count > 0 else 1

    # Positions awaiting firing or earlier
    positions_before_done = sum(
        count for stage, count in by_stage.items()
        if stage not in ("ready", "packing")
    )

    estimated_days = max(1, (positions_before_done + daily_capacity - 1) // daily_capacity)
    estimated_completion_date = (date.today() + timedelta(days=estimated_days)).isoformat()

    # Utilization: active positions / daily_capacity gives days of work queued
    utilization_pct = round(min(positions_before_done / daily_capacity * 100, 100), 1) if daily_capacity > 0 else 0.0

    return {
        "factory_id": str(factory_id),
        "factory_name": factory.name,
        "total_positions": total_positions,
        "by_stage": by_stage,
        "kiln_count": kiln_count,
        "daily_capacity_estimate": daily_capacity,
        "estimated_completion_date": estimated_completion_date,
        "utilization_pct": utilization_pct,
    }


@router.get("/{item_id}", response_model=FactoryResponse)
async def get_factories_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(Factory).filter(Factory.id == item_id).first()
    if not item:
        raise HTTPException(404, "Factory not found")
    return item


@router.post("", response_model=FactoryResponse, status_code=201)
async def create_factories_item(
    data: FactoryCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    item = Factory(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=FactoryResponse)
async def update_factories_item(
    item_id: UUID,
    data: FactoryUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    item = db.query(Factory).filter(Factory.id == item_id).first()
    if not item:
        raise HTTPException(404, "Factory not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
async def delete_factories_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    item = db.query(Factory).filter(Factory.id == item_id).first()
    if not item:
        raise HTTPException(404, "Factory not found")
    db.delete(item)
    db.commit()


# ────────────────────────────────────────────────────────────────
# Factory-level Rotation Rules (defaults for all kilns)
# ────────────────────────────────────────────────────────────────

from pydantic import BaseModel as PydanticBaseModel
from datetime import datetime, timezone


class FactoryRotationRuleInput(PydanticBaseModel):
    rule_name: str
    glaze_sequence: list[str]
    cooldown_minutes: int = 0
    incompatible_pairs: list[list[str]] = []
    is_active: bool = True


def _serialize_rotation_rule(rule) -> dict:
    return {
        "id": str(rule.id),
        "factory_id": str(rule.factory_id),
        "kiln_id": str(rule.kiln_id) if rule.kiln_id else None,
        "rule_name": rule.rule_name,
        "glaze_sequence": rule.glaze_sequence or [],
        "cooldown_minutes": rule.cooldown_minutes or 0,
        "incompatible_pairs": rule.incompatible_pairs or [],
        "is_active": rule.is_active,
        "created_at": rule.created_at.isoformat() if rule.created_at else None,
        "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
    }


@router.get("/{factory_id}/rotation-rules")
async def get_factory_rotation_rules(
    factory_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get factory-wide default rotation rules (kiln_id IS NULL)."""
    from api.models import KilnRotationRule

    factory = db.query(Factory).filter(Factory.id == factory_id).first()
    if not factory:
        raise HTTPException(404, "Factory not found")

    rules = db.query(KilnRotationRule).filter(
        KilnRotationRule.factory_id == factory_id,
        KilnRotationRule.kiln_id.is_(None),
    ).all()

    return {
        "items": [_serialize_rotation_rule(r) for r in rules],
        "total": len(rules),
    }


@router.put("/{factory_id}/rotation-rules")
async def upsert_factory_rotation_rule(
    factory_id: UUID,
    data: FactoryRotationRuleInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Create or update factory-wide default rotation rule."""
    from api.models import KilnRotationRule

    factory = db.query(Factory).filter(Factory.id == factory_id).first()
    if not factory:
        raise HTTPException(404, "Factory not found")

    # Check if rule with this name already exists for factory default
    existing = db.query(KilnRotationRule).filter(
        KilnRotationRule.factory_id == factory_id,
        KilnRotationRule.kiln_id.is_(None),
        KilnRotationRule.rule_name == data.rule_name,
    ).first()

    if existing:
        existing.glaze_sequence = data.glaze_sequence
        existing.cooldown_minutes = data.cooldown_minutes
        existing.incompatible_pairs = data.incompatible_pairs
        existing.is_active = data.is_active
        existing.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        return _serialize_rotation_rule(existing)

    rule = KilnRotationRule(
        factory_id=factory_id,
        kiln_id=None,  # factory-wide default
        rule_name=data.rule_name,
        glaze_sequence=data.glaze_sequence,
        cooldown_minutes=data.cooldown_minutes,
        incompatible_pairs=data.incompatible_pairs,
        is_active=data.is_active,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return _serialize_rotation_rule(rule)
