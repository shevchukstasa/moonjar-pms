"""
Daily KPI Calculation Engine.
Business Logic: §34, dashboard metrics

Core KPI engine for Owner and CEO dashboards.
All calculations are LIVE from existing tables (no snapshot).
"""
from uuid import UUID
from datetime import date, datetime, timedelta
from math import ceil
from typing import Optional
import logging

from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func, case, and_, or_

from api.models import (
    ProductionOrder, OrderPosition, Resource, Batch,
    DefectRecord, TpsShiftMetric, FinancialEntry, OrderFinancial,
    Factory, Material, MaterialStock, BottleneckConfig, BufferStatus,
)
from api.enums import (
    OrderStatus, PositionStatus, ResourceType, BatchStatus,
    DefectStage, ExpenseType, ExpenseCategory, BufferHealth,
)

logger = logging.getLogger("moonjar.daily_kpi")


def calculate_dashboard_summary(
    db: Session,
    factory_id: Optional[UUID] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> dict:
    """Dashboard summary KPIs for Owner/CEO.

    Returns: orders_in_progress, output_sqm, on_time_rate,
    defect_rate, kiln_utilization, oee, cost_per_sqm
    """
    if not date_from:
        date_from = date.today() - timedelta(days=30)
    if not date_to:
        date_to = date.today()

    # --- Orders in progress ---
    orders_q = db.query(sa_func.count(ProductionOrder.id)).filter(
        ProductionOrder.status.in_([
            OrderStatus.IN_PRODUCTION.value,
            OrderStatus.PARTIALLY_READY.value,
        ])
    )
    if factory_id:
        orders_q = orders_q.filter(ProductionOrder.factory_id == factory_id)
    orders_in_progress = orders_q.scalar() or 0

    # --- Total orders ---
    total_orders_q = db.query(sa_func.count(ProductionOrder.id))
    if factory_id:
        total_orders_q = total_orders_q.filter(ProductionOrder.factory_id == factory_id)
    total_orders = total_orders_q.scalar() or 0

    # --- Output sqm (from TPS metrics in period) ---
    output_q = db.query(
        sa_func.sum(TpsShiftMetric.actual_output)
    ).filter(
        TpsShiftMetric.date >= date_from,
        TpsShiftMetric.date <= date_to,
    )
    if factory_id:
        output_q = output_q.filter(TpsShiftMetric.factory_id == factory_id)
    output_sqm = float(output_q.scalar() or 0)

    # --- On-time rate ---
    on_time_rate = calculate_on_time_rate(db, factory_id, date_from, date_to)

    # --- Defect rate ---
    defect_rate = calculate_defect_rate(db, factory_id, date_from, date_to)

    # --- Kiln utilization ---
    kiln_utilization = calculate_kiln_utilization(db, factory_id, date_from, date_to)

    # --- OEE (avg from TPS) ---
    oee_q = db.query(
        sa_func.avg(TpsShiftMetric.oee_percent)
    ).filter(
        TpsShiftMetric.date >= date_from,
        TpsShiftMetric.date <= date_to,
    )
    if factory_id:
        oee_q = oee_q.filter(TpsShiftMetric.factory_id == factory_id)
    oee = float(oee_q.scalar() or 0)

    # --- Cost per sqm ---
    cost_q = db.query(
        sa_func.sum(FinancialEntry.amount)
    ).filter(
        FinancialEntry.entry_date >= date_from,
        FinancialEntry.entry_date <= date_to,
        FinancialEntry.entry_type == ExpenseType.OPEX.value,
    )
    if factory_id:
        cost_q = cost_q.filter(FinancialEntry.factory_id == factory_id)
    total_cost = float(cost_q.scalar() or 0)
    cost_per_sqm = round(total_cost / output_sqm, 2) if output_sqm > 0 else 0

    return {
        "orders_in_progress": orders_in_progress,
        "total_orders": total_orders,
        "output_sqm": round(output_sqm, 2),
        "on_time_rate": round(on_time_rate, 1),
        "defect_rate": round(defect_rate, 1),
        "kiln_utilization": round(kiln_utilization, 1),
        "oee": round(oee, 1),
        "cost_per_sqm": cost_per_sqm,
    }


def calculate_on_time_rate(
    db: Session,
    factory_id: Optional[UUID],
    date_from: date,
    date_to: date,
) -> float:
    """% orders completed on time within the period."""
    shipped_q = db.query(ProductionOrder).filter(
        ProductionOrder.status == OrderStatus.SHIPPED.value,
        ProductionOrder.shipped_at.isnot(None),
        sa_func.date(ProductionOrder.shipped_at) >= date_from,
        sa_func.date(ProductionOrder.shipped_at) <= date_to,
    )
    if factory_id:
        shipped_q = shipped_q.filter(ProductionOrder.factory_id == factory_id)

    shipped_orders = shipped_q.all()
    if not shipped_orders:
        return 100.0  # No data — assume 100%

    on_time = sum(
        1 for o in shipped_orders
        if o.final_deadline and o.shipped_at
        and o.shipped_at.date() <= o.final_deadline
    )

    return (on_time / len(shipped_orders)) * 100


def calculate_defect_rate(
    db: Session,
    factory_id: Optional[UUID],
    date_from: date,
    date_to: date,
) -> float:
    """Defect rate % = defect_count / total_inspected × 100."""
    q = db.query(
        sa_func.sum(DefectRecord.quantity)
    ).filter(
        DefectRecord.date >= date_from,
        DefectRecord.date <= date_to,
    )
    if factory_id:
        q = q.filter(DefectRecord.factory_id == factory_id)
    total_defects = float(q.scalar() or 0)

    # Total output pcs from TPS
    output_pcs_q = db.query(
        sa_func.sum(TpsShiftMetric.actual_output_pcs)
    ).filter(
        TpsShiftMetric.date >= date_from,
        TpsShiftMetric.date <= date_to,
    )
    if factory_id:
        output_pcs_q = output_pcs_q.filter(TpsShiftMetric.factory_id == factory_id)
    total_output_pcs = float(output_pcs_q.scalar() or 0)

    if total_output_pcs > 0:
        return (total_defects / total_output_pcs) * 100
    return 0.0


def calculate_kiln_utilization(
    db: Session,
    factory_id: Optional[UUID],
    date_from: date,
    date_to: date,
) -> float:
    """Avg kiln utilization % = avg(loaded/capacity) × 100."""
    # Get kilns
    kiln_q = db.query(Resource).filter(
        Resource.resource_type == ResourceType.KILN.value,
        Resource.is_active.is_(True),
    )
    if factory_id:
        kiln_q = kiln_q.filter(Resource.factory_id == factory_id)
    kilns = kiln_q.all()

    if not kilns:
        return 0.0

    utilizations = []
    for kiln in kilns:
        capacity = float(kiln.capacity_sqm or 0)
        if capacity <= 0:
            continue

        # Batches done in period
        batches = db.query(Batch).filter(
            Batch.resource_id == kiln.id,
            Batch.status == BatchStatus.DONE.value,
            Batch.batch_date >= date_from,
            Batch.batch_date <= date_to,
        ).all()

        if not batches:
            utilizations.append(0.0)
            continue

        batch_ids = [b.id for b in batches]
        loaded_sqm = db.query(
            sa_func.sum(OrderPosition.quantity_sqm)
        ).filter(
            OrderPosition.batch_id.in_(batch_ids),
        ).scalar()

        loaded_sqm = float(loaded_sqm or 0)
        avg_load = loaded_sqm / len(batches)
        util = (avg_load / capacity) * 100
        utilizations.append(min(util, 100.0))

    return sum(utilizations) / len(utilizations) if utilizations else 0.0


def calculate_production_metrics(
    db: Session,
    factory_id: Optional[UUID] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> dict:
    """Production metrics for CEO dashboard.

    Returns: daily_output[], pipeline_funnel[], critical_positions[]
    """
    if not date_from:
        date_from = date.today() - timedelta(days=30)
    if not date_to:
        date_to = date.today()

    # --- Daily output (last 30 days) ---
    daily_q = db.query(
        TpsShiftMetric.date,
        sa_func.sum(TpsShiftMetric.actual_output).label("output_sqm"),
        sa_func.sum(TpsShiftMetric.actual_output_pcs).label("output_pcs"),
    ).filter(
        TpsShiftMetric.date >= date_from,
        TpsShiftMetric.date <= date_to,
    ).group_by(TpsShiftMetric.date).order_by(TpsShiftMetric.date)

    if factory_id:
        daily_q = daily_q.filter(TpsShiftMetric.factory_id == factory_id)

    daily_output = [
        {
            "date": str(row.date),
            "output_sqm": float(row.output_sqm or 0),
            "output_pcs": int(row.output_pcs or 0),
        }
        for row in daily_q.all()
    ]

    # --- Pipeline funnel (positions by status) ---
    pipeline_stages = [
        PositionStatus.PLANNED.value,
        PositionStatus.SENT_TO_GLAZING.value,
        PositionStatus.GLAZED.value,
        PositionStatus.LOADED_IN_KILN.value,
        PositionStatus.FIRED.value,
        PositionStatus.TRANSFERRED_TO_SORTING.value,
        PositionStatus.PACKED.value,
        PositionStatus.READY_FOR_SHIPMENT.value,
    ]

    pipeline_q = db.query(
        OrderPosition.status,
        sa_func.count(OrderPosition.id).label("count"),
        sa_func.sum(OrderPosition.quantity_sqm).label("sqm"),
    ).filter(
        OrderPosition.status.in_(pipeline_stages),
    )
    if factory_id:
        pipeline_q = pipeline_q.filter(OrderPosition.factory_id == factory_id)
    pipeline_q = pipeline_q.group_by(OrderPosition.status)

    pipeline_funnel = [
        {
            "stage": row.status if isinstance(row.status, str) else row.status.value,
            "count": int(row.count or 0),
            "sqm": float(row.sqm or 0),
        }
        for row in pipeline_q.all()
    ]

    # --- Critical positions (overdue or blocked) ---
    today = date.today()
    critical_q = db.query(OrderPosition).join(ProductionOrder).filter(
        OrderPosition.status.notin_([
            PositionStatus.SHIPPED.value,
            PositionStatus.CANCELLED.value,
            PositionStatus.READY_FOR_SHIPMENT.value,
        ]),
        or_(
            # Overdue: order deadline passed
            and_(
                ProductionOrder.final_deadline.isnot(None),
                ProductionOrder.final_deadline < today,
            ),
            # Delayed: delay > 0
            OrderPosition.delay_hours > 0,
            # Blocked statuses
            OrderPosition.status.in_([
                PositionStatus.INSUFFICIENT_MATERIALS.value,
                PositionStatus.AWAITING_RECIPE.value,
                PositionStatus.AWAITING_STENCIL_SILKSCREEN.value,
                PositionStatus.AWAITING_COLOR_MATCHING.value,
                PositionStatus.BLOCKED_BY_QM.value,
            ]),
        ),
    )
    if factory_id:
        critical_q = critical_q.filter(OrderPosition.factory_id == factory_id)

    critical_positions = [
        {
            "position_id": str(p.id),
            "order_number": p.order.order_number if p.order else None,
            "status": p.status if isinstance(p.status, str) else p.status.value,
            "color": p.color,
            "size": p.size,
            "quantity": p.quantity,
            "delay_hours": float(p.delay_hours or 0),
            "deadline": str(p.order.final_deadline) if p.order and p.order.final_deadline else None,
        }
        for p in critical_q.limit(50).all()
    ]

    return {
        "daily_output": daily_output,
        "pipeline_funnel": pipeline_funnel,
        "critical_positions": critical_positions,
    }


def calculate_material_metrics(
    db: Session,
    factory_id: Optional[UUID] = None,
) -> dict:
    """Material deficit items — materials below min_balance."""
    q = db.query(Material, MaterialStock).join(
        MaterialStock, Material.id == MaterialStock.material_id
    ).filter(
        MaterialStock.balance < MaterialStock.min_balance,
    )
    if factory_id:
        q = q.filter(MaterialStock.factory_id == factory_id)

    deficit_items = [
        {
            "material_id": str(mat.id),
            "name": mat.name,
            "balance": float(stock.balance or 0),
            "min_balance": float(stock.min_balance or 0),
            "deficit": round(float(stock.min_balance or 0) - float(stock.balance or 0), 3),
            "unit": mat.unit,
            "material_type": mat.material_type,
            "factory_id": str(stock.factory_id),
        }
        for mat, stock in q.all()
    ]

    return {
        "deficit_items": deficit_items,
        "deficit_count": len(deficit_items),
    }


def calculate_factory_comparison(db: Session) -> list[dict]:
    """Per-factory KPIs for Owner dashboard."""
    factories = db.query(Factory).filter(Factory.is_active.is_(True)).all()
    date_from = date.today() - timedelta(days=30)
    date_to = date.today()

    result = []
    for factory in factories:
        summary = calculate_dashboard_summary(db, factory.id, date_from, date_to)
        summary["factory_id"] = str(factory.id)
        summary["factory_name"] = factory.name
        summary["factory_location"] = factory.location
        result.append(summary)

    return result


def calculate_trend_data(
    db: Session,
    metric: str,
    factory_id: Optional[UUID] = None,
    months: int = 6,
) -> list[dict]:
    """Time series data for trend charts.

    Supported metrics: output, on_time, defects, revenue
    """
    today = date.today()
    result = []

    for i in range(months - 1, -1, -1):
        # Calculate month boundaries
        month_end = today.replace(day=1) - timedelta(days=1) if i > 0 else today
        if i > 0:
            # Go back i months
            year = today.year
            month = today.month - i
            while month <= 0:
                month += 12
                year -= 1
            month_start = date(year, month, 1)
            # End of that month
            next_month = month + 1
            next_year = year
            if next_month > 12:
                next_month = 1
                next_year += 1
            month_end = date(next_year, next_month, 1) - timedelta(days=1)
        else:
            month_start = today.replace(day=1)
            month_end = today

        point = {
            "date": str(month_start),
            "label": month_start.strftime("%b %Y"),
        }

        if metric == "output":
            q = db.query(sa_func.sum(TpsShiftMetric.actual_output)).filter(
                TpsShiftMetric.date >= month_start,
                TpsShiftMetric.date <= month_end,
            )
            if factory_id:
                q = q.filter(TpsShiftMetric.factory_id == factory_id)
            point["value"] = float(q.scalar() or 0)

        elif metric == "on_time":
            point["value"] = calculate_on_time_rate(db, factory_id, month_start, month_end)

        elif metric == "defects":
            point["value"] = calculate_defect_rate(db, factory_id, month_start, month_end)

        elif metric == "revenue":
            q = db.query(sa_func.sum(OrderFinancial.total_price)).join(
                ProductionOrder
            ).filter(
                ProductionOrder.shipped_at.isnot(None),
                sa_func.date(ProductionOrder.shipped_at) >= month_start,
                sa_func.date(ProductionOrder.shipped_at) <= month_end,
            )
            if factory_id:
                q = q.filter(ProductionOrder.factory_id == factory_id)
            point["value"] = float(q.scalar() or 0)

        else:
            point["value"] = 0

        result.append(point)

    return result


def get_activity_feed(
    db: Session,
    factory_id: Optional[UUID] = None,
    limit: int = 20,
) -> list[dict]:
    """Recent activity events for CEO dashboard."""
    from api.models import Notification

    q = db.query(Notification).order_by(Notification.created_at.desc())
    if factory_id:
        q = q.filter(Notification.factory_id == factory_id)

    notifications = q.limit(limit).all()

    return [
        {
            "id": str(n.id),
            "type": n.type if isinstance(n.type, str) else n.type.value,
            "title": n.title,
            "message": n.message,
            "created_at": n.created_at.isoformat() if n.created_at else None,
            "is_read": n.is_read,
            "related_entity_type": (
                n.related_entity_type
                if isinstance(n.related_entity_type, str)
                else n.related_entity_type.value
            ) if n.related_entity_type else None,
            "related_entity_id": str(n.related_entity_id) if n.related_entity_id else None,
        }
        for n in notifications
    ]
