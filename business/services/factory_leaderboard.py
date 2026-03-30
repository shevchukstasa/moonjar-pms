"""
Factory Leaderboard — compare factories across key metrics.

Used by CEO/Owner dashboard to rank factories.
"""

import logging
from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func, cast, Date

from api.models import (
    Factory, ProductionOrder, OrderPosition, DefectRecord,
    QualityCheck, TpsShiftMetric,
)
from api.enums import (
    OrderStatus, PositionStatus, QcResult,
)

logger = logging.getLogger("moonjar.factory_leaderboard")


def calculate_factory_leaderboard(db: Session, period: str = "week") -> dict:
    """Compare all active factories across key metrics.

    Returns ranked factories with current + previous period values for delta.
    """
    if period == "week":
        today = date.today()
        current_start = today - timedelta(days=7)
        current_end = today
        prev_start = current_start - timedelta(days=7)
        prev_end = current_start - timedelta(days=1)
    else:  # month
        today = date.today()
        current_start = today - timedelta(days=30)
        current_end = today
        prev_start = current_start - timedelta(days=30)
        prev_end = current_start - timedelta(days=1)

    factories = db.query(Factory).filter(Factory.is_active.is_(True)).all()
    items = []

    for factory in factories:
        fid = factory.id
        current = _factory_metrics(db, fid, current_start, current_end)
        previous = _factory_metrics(db, fid, prev_start, prev_end)

        item = {
            "factory_id": str(fid),
            "factory_name": factory.name,
            "factory_location": factory.location,
            "metrics": {
                "avg_cycle_days": {
                    "value": current["avg_cycle_days"],
                    "prev": previous["avg_cycle_days"],
                    "delta": round(current["avg_cycle_days"] - previous["avg_cycle_days"], 1),
                    "lower_is_better": True,
                },
                "defect_rate": {
                    "value": current["defect_rate"],
                    "prev": previous["defect_rate"],
                    "delta": round(current["defect_rate"] - previous["defect_rate"], 1),
                    "lower_is_better": True,
                },
                "on_time_pct": {
                    "value": current["on_time_pct"],
                    "prev": previous["on_time_pct"],
                    "delta": round(current["on_time_pct"] - previous["on_time_pct"], 1),
                    "lower_is_better": False,
                },
                "kiln_utilization": {
                    "value": current["kiln_utilization"],
                    "prev": previous["kiln_utilization"],
                    "delta": round(current["kiln_utilization"] - previous["kiln_utilization"], 1),
                    "lower_is_better": False,
                },
                "output_sqm": {
                    "value": current["output_sqm"],
                    "prev": previous["output_sqm"],
                    "delta": round(current["output_sqm"] - previous["output_sqm"], 1),
                    "lower_is_better": False,
                },
                "positions_completed": {
                    "value": current["positions_completed"],
                    "prev": previous["positions_completed"],
                    "delta": current["positions_completed"] - previous["positions_completed"],
                    "lower_is_better": False,
                },
            },
        }
        items.append(item)

    # Compute ranks for each metric
    metric_keys = ["avg_cycle_days", "defect_rate", "on_time_pct",
                    "kiln_utilization", "output_sqm", "positions_completed"]

    for key in metric_keys:
        lower_is_better = items[0]["metrics"][key]["lower_is_better"] if items else False
        sorted_items = sorted(
            items,
            key=lambda x: x["metrics"][key]["value"],
            reverse=not lower_is_better,
        )
        for rank, item in enumerate(sorted_items, 1):
            item["metrics"][key]["rank"] = rank

    # Overall score: sum of ranks (lower = better)
    for item in items:
        total_rank = sum(item["metrics"][k]["rank"] for k in metric_keys)
        item["overall_rank_score"] = total_rank

    items.sort(key=lambda x: x["overall_rank_score"])
    for rank, item in enumerate(items, 1):
        item["overall_rank"] = rank

    return {
        "items": items,
        "period": period,
        "date_from": str(current_start),
        "date_to": str(current_end),
    }


def _factory_metrics(db: Session, factory_id, d_from: date, d_to: date) -> dict:
    """Calculate key metrics for a factory in a date range."""

    # Avg cycle time (days from created_at to shipped_at for shipped orders)
    shipped = db.query(ProductionOrder).filter(
        ProductionOrder.factory_id == factory_id,
        ProductionOrder.status == OrderStatus.SHIPPED.value,
        ProductionOrder.shipped_at.isnot(None),
        cast(ProductionOrder.shipped_at, Date) >= d_from,
        cast(ProductionOrder.shipped_at, Date) <= d_to,
    ).all()

    if shipped:
        cycle_days = []
        for o in shipped:
            if o.created_at and o.shipped_at:
                delta = (o.shipped_at.date() if hasattr(o.shipped_at, 'date') else o.shipped_at) - (
                    o.created_at.date() if hasattr(o.created_at, 'date') else o.created_at
                )
                cycle_days.append(delta.days)
        avg_cycle = sum(cycle_days) / len(cycle_days) if cycle_days else 0
    else:
        avg_cycle = 0

    # On-time %
    if shipped:
        on_time = sum(
            1 for o in shipped
            if o.final_deadline and o.shipped_at
            and (o.shipped_at.date() if hasattr(o.shipped_at, 'date') else o.shipped_at) <= o.final_deadline
        )
        on_time_pct = (on_time / len(shipped)) * 100
    else:
        on_time_pct = 100.0

    # Defect rate
    defect_qty = db.query(sa_func.sum(DefectRecord.quantity)).filter(
        DefectRecord.factory_id == factory_id,
        DefectRecord.date >= d_from,
        DefectRecord.date <= d_to,
    ).scalar() or 0

    total_checked = db.query(sa_func.count(QualityCheck.id)).filter(
        QualityCheck.factory_id == factory_id,
        cast(QualityCheck.created_at, Date) >= d_from,
        cast(QualityCheck.created_at, Date) <= d_to,
    ).scalar() or 0

    defect_rate = (float(defect_qty) / float(total_checked) * 100) if total_checked > 0 else 0.0

    # Kiln utilization via planning engine
    try:
        from business.services.daily_kpi import calculate_kiln_utilization
        kiln_util = calculate_kiln_utilization(db, factory_id, d_from, d_to)
    except Exception:
        kiln_util = 0.0

    # Output sqm (from TPS shift metrics)
    output = db.query(sa_func.sum(TpsShiftMetric.actual_output)).filter(
        TpsShiftMetric.factory_id == factory_id,
        TpsShiftMetric.date >= d_from,
        TpsShiftMetric.date <= d_to,
    ).scalar() or 0

    # Positions completed
    positions_done = db.query(sa_func.count(OrderPosition.id)).filter(
        OrderPosition.factory_id == factory_id,
        OrderPosition.status.in_([
            PositionStatus.READY_FOR_SHIPMENT.value,
            PositionStatus.SHIPPED.value,
        ]),
        cast(OrderPosition.updated_at, Date) >= d_from,
        cast(OrderPosition.updated_at, Date) <= d_to,
    ).scalar() or 0

    return {
        "avg_cycle_days": round(avg_cycle, 1),
        "defect_rate": round(defect_rate, 1),
        "on_time_pct": round(on_time_pct, 1),
        "kiln_utilization": round(kiln_util, 1),
        "output_sqm": round(float(output), 1),
        "positions_completed": positions_done,
    }
