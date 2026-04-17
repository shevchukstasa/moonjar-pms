"""
Production schedule generation & recalculation orchestrator.
Business Logic: §5 (TOC/DBR), §17 (scheduling), §20 (replanning)

- generate_production_schedule: read-only aggregation of the next N days
- recalculate_schedule: orchestrator for full factory reschedule
"""
from uuid import UUID
from datetime import date, datetime, timedelta, timezone
from typing import Optional
import logging

from sqlalchemy.orm import Session

from api.models import (
    OrderPosition,
    ProductionOrder,
    Batch,
    Resource,
    FactoryCalendar,
)
from api.enums import (
    PositionStatus,
    BatchStatus,
    OrderStatus,
    ResourceType,
)

logger = logging.getLogger("moonjar.planning_scheduler")

# Terminal statuses — positions done or cancelled, not in daily production plan.
# PACKED is included: once a position is packed, it's out of production stages
# even if its historical stage_plan has future dates from when it was in flight.
_TERMINAL_STATUSES = {
    PositionStatus.SHIPPED.value,
    PositionStatus.CANCELLED.value,
    PositionStatus.MERGED.value,
    PositionStatus.PACKED.value,
    PositionStatus.READY_FOR_SHIPMENT.value,
}

# Status groups for schedule sections
_GLAZING_STATUSES = {
    PositionStatus.SENT_TO_GLAZING.value,
    PositionStatus.ENGOBE_APPLIED.value,
    PositionStatus.ENGOBE_CHECK.value,
    PositionStatus.GLAZED.value,
}

_PRE_KILN_STATUSES = {
    PositionStatus.PRE_KILN_CHECK.value,
    PositionStatus.GLAZED.value,
}

_FIRING_STATUSES = {
    PositionStatus.LOADED_IN_KILN.value,
}

_POST_KILN_STATUSES = {
    PositionStatus.FIRED.value,
    PositionStatus.TRANSFERRED_TO_SORTING.value,
}

_QC_STATUSES = {
    PositionStatus.SENT_TO_QUALITY_CHECK.value,
    PositionStatus.QUALITY_CHECK_DONE.value,
    PositionStatus.PACKED.value,
}


# ────────────────────────────────────────────────────────────────
# §1  Production schedule generation
# ────────────────────────────────────────────────────────────────

def _serialize_position(
    pos: OrderPosition,
    order: Optional[ProductionOrder] = None,
    day_slice: Optional[dict] = None,
) -> dict:
    """Minimal serialization for schedule view.

    If `day_slice` is given (from stage_plan), the serialization shows
    only that day's slice of the position (qty_per_day, sqm_per_day)
    plus a label like "day 2/5" so the UI can render partial progress.
    """
    base = {
        "id": str(pos.id),
        "order_id": str(pos.order_id),
        "order_number": order.order_number if order else None,
        "status": pos.status if isinstance(pos.status, str) else pos.status.value,
        "color": pos.color,
        "size": pos.size,
        "quantity": pos.quantity,
        "area_sqm": round(float(pos.quantity_sqm), 3) if pos.quantity_sqm else None,
        "product_type": pos.product_type if isinstance(pos.product_type, str) else (pos.product_type.value if pos.product_type else None),
        "priority": pos.priority_order or 0,
        "estimated_kiln": str(pos.estimated_kiln_id) if pos.estimated_kiln_id else None,
    }
    if day_slice:
        base["stage_slice"] = day_slice  # {stage, day_index, total_days, qty_per_day, sqm_per_day}
    return base


def _serialize_batch(batch: Batch, kiln: Optional[Resource] = None) -> dict:
    """Minimal serialization for schedule view."""
    meta = batch.metadata_json or {}
    return {
        "id": str(batch.id),
        "kiln_id": str(batch.resource_id),
        "kiln_name": kiln.name if kiln else None,
        "status": batch.status if isinstance(batch.status, str) else batch.status.value,
        "positions_count": meta.get("positions_count", 0),
        "utilization_pct": meta.get("kiln_utilization_pct", 0),
        "target_temperature": batch.target_temperature,
    }


def generate_production_schedule(
    db: Session,
    factory_id: UUID,
    horizon_days: int = 14,
) -> dict:
    """
    Generate a forward-looking daily production schedule view.

    Read-only aggregation: for each day in the horizon, shows what's
    scheduled in each production section (glazing, kiln loading, firing,
    cooling, sorting, QC).

    Integrates with FactoryCalendar for holidays and working days.

    Returns:
        {
            factory_id, generated_at, horizon_days,
            days: [{date, is_working_day, holiday_name,
                    sections: {glazing, kiln_loading, firing, cooling, sorting, qc},
                    metrics: {total_positions, total_sqm, batches_count}}],
            warnings: [str],
            summary: {total_positions_scheduled, total_batches, days_with_work}
        }
    """
    start = date.today()
    end = start + timedelta(days=horizon_days)

    # ── Factory calendar ──
    calendar_entries = db.query(FactoryCalendar).filter(
        FactoryCalendar.factory_id == factory_id,
        FactoryCalendar.date >= start,
        FactoryCalendar.date <= end,
    ).all()
    calendar_map = {c.date: c for c in calendar_entries}

    # ── Active positions ──
    active_statuses = [
        s.value for s in PositionStatus
        if s.value not in _TERMINAL_STATUSES
    ]
    positions = db.query(OrderPosition).join(
        ProductionOrder, OrderPosition.order_id == ProductionOrder.id,
    ).filter(
        OrderPosition.factory_id == factory_id,
        OrderPosition.status.in_(active_statuses),
        ProductionOrder.status.in_([
            OrderStatus.NEW.value,
            OrderStatus.IN_PRODUCTION.value,
            OrderStatus.PARTIALLY_READY.value,
        ]),
    ).all()

    # Pre-load orders for display
    order_ids = {p.order_id for p in positions}
    orders = {
        o.id: o
        for o in db.query(ProductionOrder).filter(
            ProductionOrder.id.in_(list(order_ids)),
        ).all()
    } if order_ids else {}

    # Index positions by planned dates.
    #
    # For each section we store tuples of (position, day_slice_dict_or_None).
    # day_slice is None when the position has no stage_plan metadata
    # (single-day fallback, legacy behaviour), or a dict describing which
    # slice of the multi-day stage lands on this particular day.
    glazing_by_date: dict[date, list] = {}
    kiln_by_date: dict[date, list] = {}
    sorting_by_date: dict[date, list] = {}
    completion_by_date: dict[date, list] = {}

    # Stages that belong to each UI section
    _GLAZING_STAGES = (
        "unpacking_sorting",
        "engobe",
        "drying_engobe",
        "glazing",
        "drying_glaze",
        "edge_cleaning_loading",
    )
    _SORTING_STAGES = ("sorting",)
    _PACKING_STAGES = ("packing",)

    def _expand_stage(
        stage_name: str,
        stage_info: dict,
        target_dict: dict,
        pos,
    ):
        """Add one position to target_dict for every day in [start, end]."""
        try:
            _start = date.fromisoformat(stage_info["start"])
            _end = date.fromisoformat(stage_info["end"])
        except Exception:
            return
        _days = max(int(stage_info.get("days") or 1), 1)
        _qty = stage_info.get("qty_per_day")
        _sqm = stage_info.get("sqm_per_day")
        _idx = 0
        _cur = _start
        while _cur <= _end:
            _idx += 1
            if start <= _cur <= end:
                target_dict.setdefault(_cur, []).append((
                    pos,
                    {
                        "stage": stage_name,
                        "day_index": _idx,
                        "total_days": _days,
                        "qty_per_day": _qty,
                        "sqm_per_day": _sqm,
                    },
                ))
            _cur = _cur + timedelta(days=1)

    for pos in positions:
        _meta = pos.schedule_metadata or {}
        _plan = _meta.get("stage_plan") if isinstance(_meta, dict) else None

        if _plan and isinstance(_plan, dict):
            # New path: distribute across full stage durations.
            for _sname in _GLAZING_STAGES:
                _sinfo = _plan.get(_sname)
                if _sinfo:
                    _expand_stage(_sname, _sinfo, glazing_by_date, pos)
            # kiln_loading is a single-day event on planned_kiln_date
            if pos.planned_kiln_date:
                kiln_by_date.setdefault(pos.planned_kiln_date, []).append((pos, None))
            for _sname in _SORTING_STAGES:
                _sinfo = _plan.get(_sname)
                if _sinfo:
                    _expand_stage(_sname, _sinfo, sorting_by_date, pos)
            for _sname in _PACKING_STAGES:
                _sinfo = _plan.get(_sname)
                if _sinfo:
                    _expand_stage(_sname, _sinfo, completion_by_date, pos)
        else:
            # Legacy path — single-day buckets (no stage_plan yet).
            if pos.planned_glazing_date:
                glazing_by_date.setdefault(pos.planned_glazing_date, []).append((pos, None))
            if pos.planned_kiln_date:
                kiln_by_date.setdefault(pos.planned_kiln_date, []).append((pos, None))
            if pos.planned_sorting_date:
                sorting_by_date.setdefault(pos.planned_sorting_date, []).append((pos, None))
            if pos.planned_completion_date:
                completion_by_date.setdefault(pos.planned_completion_date, []).append((pos, None))

    # ── Batches in date range ──
    batches = db.query(Batch).filter(
        Batch.factory_id == factory_id,
        Batch.batch_date >= start,
        Batch.batch_date <= end,
        Batch.status.in_([
            BatchStatus.PLANNED.value,
            BatchStatus.IN_PROGRESS.value,
            BatchStatus.SUGGESTED.value,
        ]),
    ).all()

    batch_by_date: dict[date, list] = {}
    for b in batches:
        batch_by_date.setdefault(b.batch_date, []).append(b)

    # Pre-load kilns for batch display
    kiln_ids = {b.resource_id for b in batches}
    kilns_map = {
        k.id: k
        for k in db.query(Resource).filter(
            Resource.id.in_(list(kiln_ids)),
        ).all()
    } if kiln_ids else {}

    # ── Build daily schedule ──
    warnings = []
    days = []
    total_pos_scheduled = 0
    total_batches_count = 0
    days_with_work = 0

    for i in range(horizon_days + 1):
        day = start + timedelta(days=i)
        cal = calendar_map.get(day)

        # Working day determination: calendar entry or default (Sunday = off)
        if cal is not None:
            is_working = bool(cal.is_working_day)
            holiday_name = cal.holiday_name
        else:
            is_working = day.weekday() != 6  # Sunday = 6
            holiday_name = None

        # Sections — each list now holds (position, day_slice_dict|None) tuples
        glazing_entries = glazing_by_date.get(day, [])
        kiln_loading_entries = kiln_by_date.get(day, [])
        firing_batches = batch_by_date.get(day, [])
        # Cooling: batches from yesterday (1-day cooling)
        cooling_batches = batch_by_date.get(day - timedelta(days=1), [])
        sorting_entries = sorting_by_date.get(day, [])
        qc_entries = completion_by_date.get(day, [])

        def _daily_sqm(entries):
            total = 0.0
            for _p, _slice in entries:
                if _slice and _slice.get("sqm_per_day") is not None:
                    total += float(_slice["sqm_per_day"] or 0)
                elif _p.quantity_sqm:
                    total += float(_p.quantity_sqm)
            return total

        # Metrics
        day_positions = len(glazing_entries) + len(kiln_loading_entries) + len(sorting_entries) + len(qc_entries)
        day_sqm = (
            _daily_sqm(glazing_entries)
            + _daily_sqm(kiln_loading_entries)
            + _daily_sqm(sorting_entries)
            + _daily_sqm(qc_entries)
        )

        if day_positions > 0 or firing_batches:
            days_with_work += 1
        total_pos_scheduled += day_positions
        total_batches_count += len(firing_batches)

        # Warnings
        if not is_working and (day_positions > 0 or firing_batches):
            label = f"holiday: {holiday_name}" if holiday_name else "non-working day"
            warnings.append(f"{day}: work scheduled on {label}")

        # Check for behind-schedule positions at kiln loading
        for _p, _slice in kiln_loading_entries:
            if _p.status in (PositionStatus.PLANNED.value, PositionStatus.INSUFFICIENT_MATERIALS.value):
                order = orders.get(_p.order_id)
                warnings.append(
                    f"{day}: position {_p.id} not ready for kiln "
                    f"(status={_p.status}, order={order.order_number if order else '?'})"
                )

        # No kiln activity warning
        if is_working and not firing_batches and not cooling_batches and day > start:
            warnings.append(f"{day}: no kiln activity (idle constraint)")

        days.append({
            "date": str(day),
            "weekday": day.strftime("%A"),
            "is_working_day": is_working,
            "holiday_name": holiday_name,
            "sections": {
                "glazing": [
                    _serialize_position(p, orders.get(p.order_id), day_slice=s)
                    for (p, s) in glazing_entries
                ],
                "kiln_loading": [
                    _serialize_position(p, orders.get(p.order_id), day_slice=s)
                    for (p, s) in kiln_loading_entries
                ],
                "firing": [_serialize_batch(b, kilns_map.get(b.resource_id)) for b in firing_batches],
                "cooling": [_serialize_batch(b, kilns_map.get(b.resource_id)) for b in cooling_batches],
                "sorting": [
                    _serialize_position(p, orders.get(p.order_id), day_slice=s)
                    for (p, s) in sorting_entries
                ],
                "qc": [
                    _serialize_position(p, orders.get(p.order_id), day_slice=s)
                    for (p, s) in qc_entries
                ],
            },
            "metrics": {
                "total_positions": day_positions,
                "total_sqm": round(day_sqm, 2),
                "batches_count": len(firing_batches),
            },
        })

    return {
        "factory_id": str(factory_id),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "horizon_days": horizon_days,
        "days": days,
        "warnings": warnings,
        "summary": {
            "total_positions_scheduled": total_pos_scheduled,
            "total_batches": total_batches_count,
            "days_with_work": days_with_work,
        },
    }


# ────────────────────────────────────────────────────────────────
# §2  Schedule recalculation orchestrator
# ────────────────────────────────────────────────────────────────

def recalculate_schedule(db: Session, factory_id: UUID) -> dict:
    """
    Full factory schedule recalculation.

    Orchestrates existing services in correct order:
    1. Recalculate material availability + deadline estimates
    2. Reschedule all active positions (backward scheduling)
    3. Suggest batches for unbatched positions
    4. Calculate kiln utilization summary

    Returns:
        {
            positions_rescheduled, batches_suggested,
            utilization_summary, warnings
        }
    """
    warnings = []

    # Step 1: Recalculate estimates
    try:
        from business.services.schedule_estimation import recalculate_all_estimates
        recalculate_all_estimates(db, factory_id)
        db.flush()
        logger.info("Estimates recalculated for factory %s", factory_id)
    except Exception as e:
        logger.error("recalculate_all_estimates failed: %s", e, exc_info=True)
        db.rollback()
        warnings.append(f"Estimate recalculation error: {e}")

    # Step 2: Reschedule all positions
    positions_rescheduled = 0
    try:
        from business.services.production_scheduler import reschedule_factory
        positions_rescheduled = reschedule_factory(db, factory_id)
        db.flush()
        logger.info("Rescheduled %d positions for factory %s", positions_rescheduled, factory_id)
    except Exception as e:
        logger.error("reschedule_factory failed: %s", e, exc_info=True)
        db.rollback()
        warnings.append(f"Reschedule error: {e}")

    # Step 3: Suggest batches for unbatched positions
    batches_suggested = 0
    try:
        from business.services.batch_formation import suggest_or_create_batches
        batch_results = suggest_or_create_batches(db, factory_id, mode="suggest")
        batches_suggested = len(batch_results)
        db.flush()
        logger.info("Suggested %d batches for factory %s", batches_suggested, factory_id)
    except Exception as e:
        logger.error("suggest_or_create_batches failed: %s", e, exc_info=True)
        db.rollback()
        warnings.append(f"Batch suggestion error: {e}")

    # Step 4: Utilization summary (short window — last 7 days)
    utilization = None
    try:
        from business.planning_engine.optimizer import calculate_kiln_utilization
        utilization = calculate_kiln_utilization(db, factory_id, period_days=7)
    except Exception as e:
        logger.warning("Utilization calculation failed: %s", e)
        try:
            db.rollback()
        except Exception:
            pass

    # Commit all changes
    try:
        db.commit()
    except Exception as e:
        logger.error("Commit failed during recalculate_schedule: %s", e)
        db.rollback()
        warnings.append(f"Commit error: {e}")

    return {
        "factory_id": str(factory_id),
        "positions_rescheduled": positions_rescheduled,
        "batches_suggested": batches_suggested,
        "utilization_summary": utilization,
        "warnings": warnings,
    }
