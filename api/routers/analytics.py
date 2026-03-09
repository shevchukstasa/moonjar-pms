"""Analytics router — dashboard metrics.
See API_CONTRACTS.md for full specification.
"""

from uuid import UUID
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.roles import require_management, require_owner

from business.services.daily_kpi import (
    calculate_dashboard_summary,
    calculate_production_metrics,
    calculate_material_metrics,
    calculate_factory_comparison,
    calculate_trend_data,
    get_activity_feed,
)
from business.services.buffer_health import calculate_buffer_health
from api.models import Factory, BottleneckConfig, Resource
from api.enums import ResourceType

router = APIRouter()


@router.get("/dashboard-summary")
async def dashboard_summary(
    factory_id: UUID | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Summary metrics for Owner/CEO dashboard."""
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to = date.fromisoformat(date_to) if date_to else None

    # Scope to user's factory if not owner
    if current_user.role not in ("owner", "administrator") and not factory_id:
        from api.models import UserFactory
        uf = db.query(UserFactory).filter(
            UserFactory.user_id == current_user.id
        ).first()
        if uf:
            factory_id = uf.factory_id

    return calculate_dashboard_summary(db, factory_id, d_from, d_to)


@router.get("/production-metrics")
async def production_metrics(
    factory_id: UUID | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Production metrics: daily output, pipeline funnel, critical positions."""
    d_from = date.fromisoformat(date_from) if date_from else None
    d_to = date.fromisoformat(date_to) if date_to else None

    if current_user.role not in ("owner", "administrator") and not factory_id:
        from api.models import UserFactory
        uf = db.query(UserFactory).filter(
            UserFactory.user_id == current_user.id
        ).first()
        if uf:
            factory_id = uf.factory_id

    return calculate_production_metrics(db, factory_id, d_from, d_to)


@router.get("/material-metrics")
async def material_metrics(
    factory_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Material usage metrics: deficit items."""
    if current_user.role not in ("owner", "administrator") and not factory_id:
        from api.models import UserFactory
        uf = db.query(UserFactory).filter(
            UserFactory.user_id == current_user.id
        ).first()
        if uf:
            factory_id = uf.factory_id

    return calculate_material_metrics(db, factory_id)


@router.get("/factory-comparison")
async def factory_comparison(
    db: Session = Depends(get_db),
    current_user=Depends(require_owner),
):
    """Owner only: per-factory KPI comparison cards."""
    return calculate_factory_comparison(db)


@router.get("/buffer-health")
async def buffer_health(
    factory_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """CEO: per-kiln buffer health status."""
    if current_user.role not in ("owner", "administrator") and not factory_id:
        from api.models import UserFactory
        uf = db.query(UserFactory).filter(
            UserFactory.user_id == current_user.id
        ).first()
        if uf:
            factory_id = uf.factory_id

    if not factory_id:
        # Return buffer health for all factories
        factories = db.query(Factory).filter(Factory.is_active.is_(True)).all()
        results = []
        for f in factories:
            result = calculate_buffer_health(db, f.id)
            if result:
                result["factory_name"] = f.name
                results.append(result)
        return {"items": results}

    result = calculate_buffer_health(db, factory_id)
    if not result:
        return {"items": []}
    return {"items": [result]}


@router.get("/trend-data")
async def trend_data(
    metric: str = Query(..., pattern="^(output|on_time|defects|revenue)$"),
    factory_id: UUID | None = None,
    months: int = Query(6, ge=1, le=24),
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Time series data for trend charts."""
    if current_user.role not in ("owner", "administrator") and not factory_id:
        from api.models import UserFactory
        uf = db.query(UserFactory).filter(
            UserFactory.user_id == current_user.id
        ).first()
        if uf:
            factory_id = uf.factory_id

    return calculate_trend_data(db, metric, factory_id, months)


@router.get("/activity-feed")
async def activity_feed(
    factory_id: UUID | None = None,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """CEO: recent activity events feed."""
    if current_user.role not in ("owner", "administrator") and not factory_id:
        from api.models import UserFactory
        uf = db.query(UserFactory).filter(
            UserFactory.user_id == current_user.id
        ).first()
        if uf:
            factory_id = uf.factory_id

    return get_activity_feed(db, factory_id, limit)
