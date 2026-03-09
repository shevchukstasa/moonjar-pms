"""TOC (Theory of Constraints) router.
See API_CONTRACTS.md for full specification.
"""

from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.roles import require_management

from api.models import BottleneckConfig, BufferStatus, Resource, Factory
from api.enums import ResourceType, BufferHealth
from business.services.buffer_health import calculate_buffer_health

router = APIRouter()


# --- Pydantic schemas ---

class ConstraintResponse(BaseModel):
    id: str
    factory_id: str
    factory_name: str | None = None
    constraint_resource_id: str | None = None
    constraint_resource_name: str | None = None
    buffer_target_hours: float
    rope_limit: int | None = None
    rope_max_days: int
    rope_min_days: int
    batch_mode: str
    current_bottleneck_utilization: float | None = None


class ConstraintUpdate(BaseModel):
    constraint_resource_id: str | None = None
    buffer_target_hours: float | None = None
    rope_limit: int | None = None
    rope_max_days: int | None = None
    rope_min_days: int | None = None
    batch_mode: str | None = None


class BufferHealthResponse(BaseModel):
    factory_id: str
    factory_name: str
    health: str
    hours: float
    target: float
    buffered_count: int
    buffered_sqm: float
    kiln_id: str | None = None
    kiln_name: str | None = None


def _serialize_constraint(config: BottleneckConfig) -> dict:
    """Serialize BottleneckConfig to dict."""
    return {
        "id": str(config.id),
        "factory_id": str(config.factory_id),
        "factory_name": config.factory.name if config.factory else None,
        "constraint_resource_id": str(config.constraint_resource_id) if config.constraint_resource_id else None,
        "constraint_resource_name": config.constraint_resource.name if config.constraint_resource else None,
        "buffer_target_hours": float(config.buffer_target_hours or 24.0),
        "rope_limit": config.rope_limit,
        "rope_max_days": config.rope_max_days,
        "rope_min_days": config.rope_min_days,
        "batch_mode": config.batch_mode.value if config.batch_mode else "hybrid",
        "current_bottleneck_utilization": float(config.current_bottleneck_utilization) if config.current_bottleneck_utilization else None,
    }


@router.get("/constraints")
async def list_constraints(
    factory_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List TOC constraints (bottleneck config per factory)."""
    query = db.query(BottleneckConfig)

    if factory_id:
        query = query.filter(BottleneckConfig.factory_id == factory_id)

    # If user is not owner/admin, scope to their factories
    if current_user.role not in ("owner", "administrator"):
        from api.models import UserFactory
        user_factory_ids = [
            uf.factory_id
            for uf in db.query(UserFactory).filter(
                UserFactory.user_id == current_user.id
            ).all()
        ]
        query = query.filter(BottleneckConfig.factory_id.in_(user_factory_ids))

    configs = query.all()
    return {
        "items": [_serialize_constraint(c) for c in configs],
        "total": len(configs),
    }


@router.patch("/constraints/{constraint_id}")
async def update_constraint(
    constraint_id: UUID,
    body: ConstraintUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Update TOC constraint parameters."""
    config = db.query(BottleneckConfig).filter(
        BottleneckConfig.id == constraint_id,
    ).first()

    if not config:
        raise HTTPException(404, "Constraint config not found")

    # Scope check: non-owner/admin can only update their factory
    if current_user.role not in ("owner", "administrator"):
        from api.models import UserFactory
        uf = db.query(UserFactory).filter(
            UserFactory.user_id == current_user.id,
            UserFactory.factory_id == config.factory_id,
        ).first()
        if not uf:
            raise HTTPException(403, "Cannot update constraints for this factory")

    update_data = body.model_dump(exclude_unset=True)

    if "constraint_resource_id" in update_data and update_data["constraint_resource_id"]:
        # Validate that the resource exists and belongs to the same factory
        resource = db.query(Resource).filter(
            Resource.id == UUID(update_data["constraint_resource_id"]),
            Resource.factory_id == config.factory_id,
            Resource.resource_type == ResourceType.KILN,
        ).first()
        if not resource:
            raise HTTPException(400, "Invalid constraint resource: must be a kiln in the same factory")
        config.constraint_resource_id = resource.id
        del update_data["constraint_resource_id"]

    if "batch_mode" in update_data and update_data["batch_mode"]:
        from api.enums import BatchMode
        try:
            config.batch_mode = BatchMode(update_data["batch_mode"])
        except ValueError:
            raise HTTPException(400, f"Invalid batch_mode: {update_data['batch_mode']}")
        del update_data["batch_mode"]

    for field, value in update_data.items():
        if value is not None and hasattr(config, field):
            setattr(config, field, value)

    db.commit()
    db.refresh(config)

    return _serialize_constraint(config)


@router.get("/buffer-health")
async def get_buffer_health(
    factory_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Buffer health metrics — glazed items before kiln constraint."""
    # If user is not owner/admin, scope to their factory
    if current_user.role not in ("owner", "administrator") and not factory_id:
        from api.models import UserFactory
        uf = db.query(UserFactory).filter(
            UserFactory.user_id == current_user.id
        ).first()
        if uf:
            factory_id = uf.factory_id

    results = []

    if factory_id:
        factory = db.query(Factory).filter(Factory.id == factory_id).first()
        if not factory:
            raise HTTPException(404, "Factory not found")

        result = calculate_buffer_health(db, factory_id)
        if result:
            result["factory_id"] = str(factory_id)
            result["factory_name"] = factory.name
            results.append(result)
    else:
        # All factories
        factories = db.query(Factory).filter(Factory.is_active.is_(True)).all()
        for f in factories:
            result = calculate_buffer_health(db, f.id)
            if result:
                result["factory_id"] = str(f.id)
                result["factory_name"] = f.name
                results.append(result)

    return {"items": results, "total": len(results)}
