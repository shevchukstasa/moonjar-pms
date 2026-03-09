"""Reports router — order summaries, kiln load reports.
See API_CONTRACTS.md for full specification.
"""

from uuid import UUID
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func

from api.database import get_db
from api.auth import get_current_user
from api.roles import require_management
from api.models import (
    ProductionOrder, OrderPosition, Resource, Batch,
)
from api.enums import (
    OrderStatus, PositionStatus, ResourceType, BatchStatus,
)

router = APIRouter()


@router.get("")
async def list_reports(
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Available report types."""
    return {
        "items": [
            {"id": "orders-summary", "name": "Orders Summary", "description": "Order statistics and on-time %"},
            {"id": "kiln-load", "name": "Kiln Load Report", "description": "Per-kiln utilization"},
        ],
        "total": 2,
        "page": 1,
        "per_page": 50,
    }


@router.get("/orders-summary")
async def orders_summary_report(
    factory_id: UUID | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Orders summary report: totals, completion stats, on-time %."""
    d_from = date.fromisoformat(date_from) if date_from else date.today() - timedelta(days=30)
    d_to = date.fromisoformat(date_to) if date_to else date.today()

    # Total orders created in period
    total_q = db.query(sa_func.count(ProductionOrder.id)).filter(
        ProductionOrder.created_at >= d_from,
    )
    if factory_id:
        total_q = total_q.filter(ProductionOrder.factory_id == factory_id)
    total_orders = total_q.scalar() or 0

    # Completed (shipped) in period
    shipped_q = db.query(ProductionOrder).filter(
        ProductionOrder.status == OrderStatus.SHIPPED.value,
        ProductionOrder.shipped_at.isnot(None),
        sa_func.date(ProductionOrder.shipped_at) >= d_from,
        sa_func.date(ProductionOrder.shipped_at) <= d_to,
    )
    if factory_id:
        shipped_q = shipped_q.filter(ProductionOrder.factory_id == factory_id)
    shipped_orders = shipped_q.all()
    completed = len(shipped_orders)

    # On-time rate
    on_time = sum(
        1 for o in shipped_orders
        if o.final_deadline and o.shipped_at and o.shipped_at.date() <= o.final_deadline
    )
    on_time_pct = (on_time / completed * 100) if completed > 0 else 0

    # Avg completion days
    completion_days = []
    for o in shipped_orders:
        if o.shipped_at and o.created_at:
            delta = o.shipped_at - o.created_at
            completion_days.append(delta.days)
    avg_completion_days = (
        sum(completion_days) / len(completion_days)
        if completion_days else 0
    )

    # In-progress
    in_progress_q = db.query(sa_func.count(ProductionOrder.id)).filter(
        ProductionOrder.status.in_([
            OrderStatus.IN_PRODUCTION.value,
            OrderStatus.PARTIALLY_READY.value,
        ]),
    )
    if factory_id:
        in_progress_q = in_progress_q.filter(ProductionOrder.factory_id == factory_id)
    in_progress = in_progress_q.scalar() or 0

    return {
        "period": {"from": str(d_from), "to": str(d_to)},
        "total_orders": total_orders,
        "completed": completed,
        "in_progress": in_progress,
        "on_time_count": on_time,
        "on_time_percent": round(on_time_pct, 1),
        "avg_completion_days": round(avg_completion_days, 1),
    }


@router.get("/kiln-load")
async def kiln_load_report(
    factory_id: UUID | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Per-kiln utilization report."""
    d_from = date.fromisoformat(date_from) if date_from else date.today() - timedelta(days=30)
    d_to = date.fromisoformat(date_to) if date_to else date.today()

    kiln_q = db.query(Resource).filter(
        Resource.resource_type == ResourceType.KILN.value,
        Resource.is_active.is_(True),
    )
    if factory_id:
        kiln_q = kiln_q.filter(Resource.factory_id == factory_id)
    kilns = kiln_q.all()

    results = []
    for kiln in kilns:
        capacity = float(kiln.capacity_sqm or 0)

        # Batches in period
        batches = db.query(Batch).filter(
            Batch.resource_id == kiln.id,
            Batch.batch_date >= d_from,
            Batch.batch_date <= d_to,
        ).all()

        total_batches = len(batches)
        done_batches = sum(1 for b in batches if b.status == BatchStatus.DONE.value)

        # Loaded sqm from done batches
        done_batch_ids = [b.id for b in batches if b.status == BatchStatus.DONE.value]
        loaded_sqm = 0.0
        if done_batch_ids:
            loaded = db.query(
                sa_func.sum(OrderPosition.quantity_sqm)
            ).filter(
                OrderPosition.batch_id.in_(done_batch_ids),
            ).scalar()
            loaded_sqm = float(loaded or 0)

        avg_load = loaded_sqm / done_batches if done_batches > 0 else 0
        utilization = (avg_load / capacity * 100) if capacity > 0 else 0

        results.append({
            "kiln_id": str(kiln.id),
            "kiln_name": kiln.name,
            "factory_id": str(kiln.factory_id),
            "capacity_sqm": capacity,
            "total_batches": total_batches,
            "done_batches": done_batches,
            "total_loaded_sqm": round(loaded_sqm, 2),
            "avg_load_sqm": round(avg_load, 2),
            "utilization_percent": round(min(utilization, 100), 1),
        })

    return {
        "period": {"from": str(d_from), "to": str(d_to)},
        "kilns": results,
    }
