"""Analytics router — dashboard metrics.
See API_CONTRACTS.md for full specification.
"""

from uuid import UUID
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.database import get_db
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
from business.services.anomaly_detection import (
    run_all_anomaly_checks, anomaly_to_dict,
)
from api.models import Factory, Resource, MaterialTransaction, Material, User

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


@router.get("/inventory-report")
async def inventory_report(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2024, le=2030),
    factory_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Monthly inventory adjustment report for CEO/Owner.

    Returns all materials with manual_write_off or inventory transactions
    in the given month, grouped by material.
    """
    from datetime import datetime as dt, timezone as tz
    from calendar import monthrange

    start = dt(year, month, 1, tzinfo=tz.utc)
    _, last_day = monthrange(year, month)
    end = dt(year, month, last_day, 23, 59, 59, tzinfo=tz.utc)

    query = (
        db.query(MaterialTransaction)
        .filter(
            MaterialTransaction.type.in_(["manual_write_off", "inventory"]),
            MaterialTransaction.created_at >= start,
            MaterialTransaction.created_at <= end,
        )
    )
    if factory_id:
        query = query.filter(MaterialTransaction.factory_id == factory_id)

    transactions = query.order_by(MaterialTransaction.created_at.desc()).all()

    # Group by material
    from collections import defaultdict
    grouped: dict[str, list] = defaultdict(list)
    for t in transactions:
        grouped[str(t.material_id)].append(t)

    materials_result = []
    for mat_id, txns in grouped.items():
        mat = db.query(Material).filter(Material.id == mat_id).first()
        adjustments = []
        total = 0.0
        for t in txns:
            qty = float(t.quantity)
            # manual_write_off is always negative (deduction)
            if str(t.type) == "manual_write_off" or (hasattr(t.type, 'value') and t.type.value == "manual_write_off"):
                qty = -abs(qty)
            total += qty
            creator_name = None
            creator_role = None
            if t.created_by:
                user = db.query(User).filter(User.id == t.created_by).first()
                if user:
                    creator_name = user.name
                    creator_role = user.role.value if hasattr(user.role, 'value') else str(user.role) if user.role else None
            adjustments.append({
                "id": str(t.id),
                "date": t.created_at.isoformat() if t.created_at else None,
                "user_name": creator_name,
                "user_role": creator_role,
                "quantity": float(t.quantity),
                "type": t.type.value if hasattr(t.type, 'value') else str(t.type),
                "reason": t.reason.value if hasattr(t.reason, 'value') else str(t.reason) if t.reason else None,
                "notes": t.notes,
            })

        materials_result.append({
            "material_id": mat_id,
            "material_name": mat.name if mat else None,
            "material_code": mat.material_code if mat else None,
            "total_adjustment": round(total, 3),
            "adjustment_count": len(adjustments),
            "adjustments": adjustments,
        })

    # Sort by abs total adjustment descending
    materials_result.sort(key=lambda m: abs(m["total_adjustment"]), reverse=True)

    # Summary
    total_pos = sum(m["total_adjustment"] for m in materials_result if m["total_adjustment"] > 0)
    total_neg = sum(m["total_adjustment"] for m in materials_result if m["total_adjustment"] < 0)

    return {
        "month": month,
        "year": year,
        "factory_id": str(factory_id) if factory_id else None,
        "materials": materials_result,
        "summary": {
            "total_materials_adjusted": len(materials_result),
            "total_positive_adjustments": round(total_pos, 3),
            "total_negative_adjustments": round(total_neg, 3),
        },
    }


@router.get("/anomalies")
async def get_anomalies(
    factory_id: UUID | None = None,
    severity: str | None = Query(None, pattern="^(warning|critical)$"),
    type: str | None = Query(
        None,
        alias="anomaly_type",
        pattern="^(defect_spike|throughput_drop|cycle_time|material_excess|kiln_anomaly)$",
    ),
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Get detected anomalies for a factory (or all factories).

    Runs anomaly detection in real-time and returns results.
    Filters by severity and anomaly type are optional.
    """
    # Scope to user's factory if not owner/admin
    if current_user.role not in ("owner", "administrator") and not factory_id:
        from api.models import UserFactory
        uf = db.query(UserFactory).filter(
            UserFactory.user_id == current_user.id
        ).first()
        if uf:
            factory_id = uf.factory_id

    # Determine which factories to check
    if factory_id:
        factory_ids = [factory_id]
    else:
        factories = db.query(Factory).filter(Factory.is_active.is_(True)).all()
        factory_ids = [f.id for f in factories]

    all_anomalies = []
    for fid in factory_ids:
        try:
            anomalies = run_all_anomaly_checks(db, fid)
            all_anomalies.extend(anomalies)
        except Exception:
            pass  # Logged inside run_all_anomaly_checks

    # Apply filters
    if severity:
        all_anomalies = [a for a in all_anomalies if a.severity == severity]
    if type:
        all_anomalies = [a for a in all_anomalies if a.type == type]

    # Sort: critical first, then by z-score descending
    all_anomalies.sort(key=lambda a: (0 if a.severity == "critical" else 1, -abs(a.z_score)))

    return {
        "items": [anomaly_to_dict(a) for a in all_anomalies],
        "total": len(all_anomalies),
        "critical_count": sum(1 for a in all_anomalies if a.severity == "critical"),
        "warning_count": sum(1 for a in all_anomalies if a.severity == "warning"),
    }
