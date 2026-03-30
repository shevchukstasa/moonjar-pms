"""TOC (Theory of Constraints) router.
See API_CONTRACTS.md for full specification.
"""

from datetime import date
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.roles import require_management

from api.models import BottleneckConfig, Resource, Factory, ProductionOrder, OrderPosition
from api.enums import ResourceType, BufferHealth, OrderStatus, PositionStatus
from business.services.buffer_health import calculate_buffer_health


# Statuses that count as "work done" for buffer penetration
_DONE_STATUSES = {
    PositionStatus.PACKED,
    PositionStatus.QUALITY_CHECK_DONE,
    PositionStatus.READY_FOR_SHIPMENT,
    PositionStatus.SHIPPED,
}

# Statuses that mean the position is cancelled/excluded from count
_EXCLUDED_STATUSES = {
    PositionStatus.CANCELLED,
}


def _compute_buffer_zone(order: ProductionOrder, positions: list) -> dict:
    """
    Compute TOC buffer zone for a single order.

    Buffer penetration = time elapsed / total time window  (how much of the clock has ticked)
    Work completion    = done positions / total positions   (how much work is actually done)
    delta              = work_pct - time_pct
      >= -5%  → green   (work keeps up with time)
      >= -20% → yellow  (buffer eroding)
      <  -20% → red     (critical)
    Deadline today or past → always red.
    """
    today = date.today()

    # Filter out cancelled/split sub-positions
    active = [p for p in positions if p.status not in _EXCLUDED_STATUSES and p.split_category is None]
    total = len(active)
    done = sum(1 for p in active if p.status in _DONE_STATUSES)
    in_progress = total - done

    work_pct = round(done / total * 100, 1) if total else 0.0

    # Time window
    start = order.production_received_date or order.document_date
    deadline = order.final_deadline or order.schedule_deadline

    if deadline is None:
        # No deadline set → treat as green with no time data
        return {
            "time_penetration_pct": None,
            "work_completion_pct": work_pct,
            "buffer_delta": None,
            "zone": "green",
            "days_remaining": None,
            "positions_total": total,
            "positions_done": done,
            "positions_in_progress": in_progress,
        }

    days_remaining = (deadline - today).days

    if start and (deadline - start).days > 0:
        total_window = (deadline - start).days
        elapsed = (today - start).days
        time_pct = round(min(max(elapsed / total_window * 100, 0), 100), 1)
    else:
        time_pct = 100.0 if days_remaining <= 0 else 0.0

    delta = work_pct - time_pct

    if days_remaining <= 0:
        zone = "red"
    elif delta >= -5:
        zone = "green"
    elif delta >= -20:
        zone = "yellow"
    else:
        zone = "red"

    return {
        "time_penetration_pct": time_pct,
        "work_completion_pct": work_pct,
        "buffer_delta": round(delta, 1),
        "zone": zone,
        "days_remaining": days_remaining,
        "positions_total": total,
        "positions_done": done,
        "positions_in_progress": in_progress,
    }

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


class ConstraintListResponse(BaseModel):
    items: list[ConstraintResponse]
    total: int


class BufferHealthListResponse(BaseModel):
    items: list[BufferHealthResponse]
    total: int


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


@router.get("/constraints", response_model=ConstraintListResponse)
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


# === BOTTLENECK CONFIGURATION ENDPOINTS (Decision 2026-03-19) ===

class BatchModeToggle(BaseModel):
    factory_id: UUID
    enabled: bool  # True = auto, False = hybrid


class BufferTargetUpdate(BaseModel):
    factory_id: UUID
    buffer_target_hours: float


@router.patch("/bottleneck/batch-mode")
async def toggle_batch_mode(
    body: BatchModeToggle,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """
    Toggle constraint batch processing mode.
    enabled=True sets batch_mode to 'auto', enabled=False sets to 'hybrid'.
    """
    config = db.query(BottleneckConfig).filter(
        BottleneckConfig.factory_id == body.factory_id,
    ).first()

    if not config:
        raise HTTPException(404, "Bottleneck config not found for this factory")

    from api.enums import BatchMode as BM
    config.batch_mode = BM.AUTO if body.enabled else BM.HYBRID

    db.commit()
    db.refresh(config)

    return {
        "factory_id": str(body.factory_id),
        "batch_mode": config.batch_mode.value,
        "updated_by": str(current_user.id),
    }


@router.patch("/bottleneck/buffer-target")
async def set_buffer_target(
    body: BufferTargetUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """
    Set buffer target hours for a factory's constraint.
    Controls the target buffer time before the bottleneck (kiln).
    """
    if body.buffer_target_hours <= 0:
        raise HTTPException(400, "buffer_target_hours must be positive")

    config = db.query(BottleneckConfig).filter(
        BottleneckConfig.factory_id == body.factory_id,
    ).first()

    if not config:
        raise HTTPException(404, "Bottleneck config not found for this factory")

    config.buffer_target_hours = body.buffer_target_hours

    db.commit()
    db.refresh(config)

    return {
        "factory_id": str(body.factory_id),
        "buffer_target_hours": float(config.buffer_target_hours),
        "updated_by": str(current_user.id),
    }


@router.get("/buffer-health", response_model=BufferHealthListResponse)
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


@router.get("/buffer-zones")
async def get_buffer_zones(
    factory_id: Optional[UUID] = None,
    zone: Optional[str] = Query(None, description="Filter by zone: green | yellow | red"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    TOC buffer zones for active orders.

    Returns per-order buffer status based on:
    - time penetration: elapsed / total time window to deadline
    - work completion: done positions / total positions
    - delta = work_pct - time_pct → determines green / yellow / red zone

    Accessible by all authenticated users (scoped to their factory).
    """
    # Scope to user's factory if not owner/admin
    if current_user.role not in ("owner", "administrator", "ceo") and not factory_id:
        from api.models import UserFactory
        uf = db.query(UserFactory).filter(
            UserFactory.user_id == current_user.id
        ).first()
        if uf:
            factory_id = uf.factory_id

    # Query active orders (exclude cancelled/shipped)
    query = db.query(ProductionOrder).filter(
        ProductionOrder.status.notin_([
            OrderStatus.CANCELLED,
            OrderStatus.SHIPPED,
        ])
    )
    if factory_id:
        query = query.filter(ProductionOrder.factory_id == factory_id)

    orders = query.order_by(ProductionOrder.final_deadline.asc().nullslast()).all()

    # Build per-order buffer data
    items = []
    for order in orders:
        positions = db.query(OrderPosition).filter(
            OrderPosition.order_id == order.id,
        ).all()

        buf = _compute_buffer_zone(order, positions)

        # Apply zone filter
        if zone and buf["zone"] != zone:
            continue

        factory = db.query(Factory).filter(Factory.id == order.factory_id).first()

        items.append({
            "order_id": str(order.id),
            "order_number": order.order_number,
            "client": order.client,
            "factory_id": str(order.factory_id),
            "factory_name": factory.name if factory else None,
            "deadline": str(order.final_deadline) if order.final_deadline else None,
            "order_status": order.status.value if order.status else None,
            **buf,
        })

    # Summary counters
    summary = {"green": 0, "yellow": 0, "red": 0}
    for item in items:
        summary[item["zone"]] = summary.get(item["zone"], 0) + 1

    return {
        "items": items,
        "total": len(items),
        "summary": summary,
    }
