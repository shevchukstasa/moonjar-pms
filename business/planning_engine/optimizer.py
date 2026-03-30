"""
Batch optimization & kiln utilization analytics.
Business Logic: §7 (batch fill), §19 (kiln metrics)

TOC principle: the constraint (kiln) must never be idle.
- optimize_batch_fill: post-creation advisory — find positions to fill spare capacity
- calculate_kiln_utilization: analytics for kiln usage over a period
"""
from uuid import UUID
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional
import logging

from sqlalchemy.orm import Session

from api.models import (
    Batch,
    OrderPosition,
    ProductionOrder,
    Resource,
    RecipeKilnConfig,
)
from api.enums import (
    BatchStatus,
    PositionStatus,
    OrderStatus,
    ResourceType,
)
from business.kiln.constants import get_kiln_constants
from business.kiln.assignment_rules import validate_cofiring, get_loading_rules
from business.kiln.capacity import calculate_kiln_capacity

logger = logging.getLogger("moonjar.optimizer")

# Ready-for-kiln statuses
_READY_STATUSES = [PositionStatus.PRE_KILN_CHECK.value, PositionStatus.GLAZED.value]

# Max cofiring temperature range (°C)
_COFIRING_TEMP_RANGE = 50


# ────────────────────────────────────────────────────────────────
# §1  Batch fill optimization
# ────────────────────────────────────────────────────────────────

def _get_position_area(pos: OrderPosition) -> Decimal:
    """Position area in sqm — mirrors batch_formation._get_position_area_sqm."""
    if pos.glazeable_sqm:
        return Decimal(str(pos.glazeable_sqm)) * Decimal(str(pos.quantity))
    if pos.quantity_sqm:
        return Decimal(str(pos.quantity_sqm))
    if pos.length_cm and pos.width_cm:
        piece = (Decimal(str(pos.length_cm)) * Decimal(str(pos.width_cm))) / Decimal("10000")
        return piece * Decimal(str(pos.quantity))
    return Decimal("0.04") * Decimal(str(pos.quantity))


def _get_kiln_capacity(kiln: Resource) -> Decimal:
    """Kiln capacity in sqm — mirrors batch_formation._get_kiln_capacity_sqm."""
    if kiln.capacity_sqm:
        return Decimal(str(kiln.capacity_sqm))
    if kiln.kiln_working_area_cm:
        dims = kiln.kiln_working_area_cm
        w = dims.get("width", 0)
        h = dims.get("height", 0)
        if w and h:
            return Decimal(str(w * h)) / Decimal("10000")
    return Decimal("1.0")


def _get_batch_temperature(db: Session, batch: Batch) -> Optional[int]:
    """Get the target temperature for a batch."""
    if batch.target_temperature:
        return int(batch.target_temperature)
    # Infer from first position's recipe
    first_pos = db.query(OrderPosition).filter(
        OrderPosition.batch_id == batch.id,
    ).first()
    if first_pos and first_pos.recipe_id:
        cfg = db.query(RecipeKilnConfig).filter(
            RecipeKilnConfig.recipe_id == first_pos.recipe_id,
        ).first()
        if cfg and cfg.firing_temperature:
            return int(cfg.firing_temperature)
    return None


def _is_temp_compatible(
    candidate: OrderPosition,
    batch_temp: Optional[int],
    db: Session,
) -> bool:
    """Check if candidate's firing temperature is within ±COFIRING range."""
    if batch_temp is None:
        return True  # no temperature constraint
    if not candidate.recipe_id:
        return True  # no recipe — allow (will be checked by co-firing)
    cfg = db.query(RecipeKilnConfig).filter(
        RecipeKilnConfig.recipe_id == candidate.recipe_id,
    ).first()
    if not cfg or not cfg.firing_temperature:
        return True
    return abs(int(cfg.firing_temperature) - batch_temp) <= _COFIRING_TEMP_RANGE


def _score_candidate(
    pos: OrderPosition,
    order: Optional[ProductionOrder],
    area: Decimal,
    remaining: Decimal,
    kiln: Resource,
    constants: dict,
    loading_rules: dict,
) -> tuple[float, str]:
    """
    Score a candidate position for batch fill (0-100).
    Returns (score, primary_reason).
    """
    score = 0.0
    reason = "compatible"

    # 1. Deadline urgency (0-40): closer deadline = higher score
    if order and order.final_deadline:
        days_left = (order.final_deadline - date.today()).days
        urgency = max(0.0, 40.0 - days_left)
        score += min(urgency, 40.0)
        if urgency >= 30:
            reason = "urgent deadline"

    # 2. Size fit (0-30): how well it fills remaining space
    if remaining > 0:
        fit_ratio = float(area) / float(remaining)
        if fit_ratio <= 1.0:
            size_score = 30.0 * fit_ratio
            score += size_score
            if fit_ratio > 0.7:
                reason = "excellent size fit"
        # Oversized → penalize but don't exclude (partial loading possible)

    # 3. Priority (0-20)
    priority = getattr(pos, "priority_order", 0) or 0
    score += min(float(priority) * 5.0, 20.0)
    if priority >= 4:
        reason = "high priority"

    # 4. Loading method bonus (0-10)
    try:
        cap = calculate_kiln_capacity(pos, kiln, constants, loading_rules)
        if cap and cap.get("optimal", {}).get("total_pieces", 0) > 0:
            score += 10.0
    except Exception:
        pass  # geometry not available — no bonus

    return round(score, 1), reason


def optimize_batch_fill(db: Session, batch_id: UUID) -> dict:
    """
    Find additional positions that can fill remaining batch capacity.

    For a PLANNED or SUGGESTED batch, analyzes spare kiln capacity and
    returns ranked suggestions of compatible positions — without modifying
    any records.

    Returns:
        {
            batch_id, kiln_id, kiln_name,
            current_utilization_pct, remaining_capacity_sqm,
            suggestions: [{position_id, order_id, order_number, area_sqm,
                          score, loading_method, reason}]
        }
    """
    # ── Load batch ──
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        return {"error": "batch_not_found", "batch_id": str(batch_id)}

    if batch.status not in (BatchStatus.PLANNED.value, BatchStatus.SUGGESTED.value):
        return {
            "error": "invalid_status",
            "batch_id": str(batch_id),
            "status": batch.status,
            "message": "Only PLANNED or SUGGESTED batches can be optimized",
        }

    # ── Load kiln + constants ──
    kiln = db.query(Resource).filter(Resource.id == batch.resource_id).first()
    if not kiln:
        return {"error": "kiln_not_found", "batch_id": str(batch_id)}

    constants = get_kiln_constants(db, batch.factory_id)
    loading_rules = get_loading_rules(db, kiln.id)

    # ── Current positions + utilization ──
    current_positions = db.query(OrderPosition).filter(
        OrderPosition.batch_id == batch_id,
    ).all()

    current_area = sum(_get_position_area(p) for p in current_positions)
    kiln_cap = _get_kiln_capacity(kiln)
    remaining = kiln_cap - current_area

    current_pct = round(float(current_area) / float(kiln_cap) * 100, 1) if kiln_cap > 0 else 0.0

    if remaining <= Decimal("0.01"):
        return {
            "batch_id": str(batch_id),
            "kiln_id": str(kiln.id),
            "kiln_name": kiln.name,
            "current_utilization_pct": current_pct,
            "remaining_capacity_sqm": 0.0,
            "suggestions": [],
        }

    # ── Batch temperature ──
    batch_temp = _get_batch_temperature(db, batch)

    # ── Candidate positions ──
    current_ids = [p.id for p in current_positions]
    candidates = db.query(OrderPosition).filter(
        OrderPosition.factory_id == batch.factory_id,
        OrderPosition.status.in_(_READY_STATUSES),
        OrderPosition.batch_id.is_(None),
    ).all()

    # Exclude positions already in this batch (safety)
    candidates = [c for c in candidates if c.id not in current_ids]

    # ── Filter + score ──
    suggestions = []
    # Pre-load orders for deadline scoring
    order_ids = {c.order_id for c in candidates}
    orders = {
        o.id: o
        for o in db.query(ProductionOrder).filter(
            ProductionOrder.id.in_(list(order_ids)),
        ).all()
    } if order_ids else {}

    for cand in candidates:
        # Temperature check (fast filter)
        if not _is_temp_compatible(cand, batch_temp, db):
            continue

        # Co-firing check (full validation)
        cofiring = validate_cofiring(db, current_positions + [cand], kiln.id, constants)
        if not cofiring.get("ok", False):
            continue

        area = _get_position_area(cand)
        if area > remaining * Decimal("1.5"):
            continue  # too large even for partial

        order = orders.get(cand.order_id)
        score, reason = _score_candidate(
            cand, order, area, remaining, kiln, constants, loading_rules,
        )

        # Determine loading method
        loading_method = "area_based"
        try:
            cap = calculate_kiln_capacity(cand, kiln, constants, loading_rules)
            if cap and cap.get("optimal", {}).get("method"):
                loading_method = cap["optimal"]["method"]
        except Exception:
            pass

        suggestions.append({
            "position_id": str(cand.id),
            "order_id": str(cand.order_id),
            "order_number": order.order_number if order else None,
            "area_sqm": round(float(area), 3),
            "score": score,
            "loading_method": loading_method,
            "reason": reason,
        })

    # Sort by score descending, take top 20
    suggestions.sort(key=lambda s: s["score"], reverse=True)
    suggestions = suggestions[:20]

    return {
        "batch_id": str(batch_id),
        "kiln_id": str(kiln.id),
        "kiln_name": kiln.name,
        "current_utilization_pct": current_pct,
        "remaining_capacity_sqm": round(float(remaining), 3),
        "suggestions": suggestions,
    }


# ────────────────────────────────────────────────────────────────
# §2  Kiln utilization analytics
# ────────────────────────────────────────────────────────────────

def calculate_kiln_utilization(
    db: Session,
    factory_id: UUID,
    period_days: int = 30,
) -> dict:
    """
    Calculate kiln utilization metrics for the past N days.

    For each kiln: firings count, average fill %, idle days, total area.
    Plus factory-level summary.

    Returns:
        {
            factory_id, period_days,
            kilns: {kiln_id: {name, firings, avg_fill_pct, idle_days,
                              total_area_sqm, batches_count}},
            summary: {total_firings, avg_utilization_pct,
                      busiest_kiln, least_busy_kiln}
        }
    """
    cutoff = date.today() - timedelta(days=period_days)

    # All active kilns for factory
    kilns = db.query(Resource).filter(
        Resource.factory_id == factory_id,
        Resource.resource_type == ResourceType.KILN.value,
        Resource.is_active.is_(True),
    ).all()

    if not kilns:
        return {
            "factory_id": str(factory_id),
            "period_days": period_days,
            "kilns": {},
            "summary": {
                "total_firings": 0,
                "avg_utilization_pct": 0.0,
                "busiest_kiln": None,
                "least_busy_kiln": None,
            },
        }

    kiln_metrics = {}

    for kiln in kilns:
        batches = db.query(Batch).filter(
            Batch.resource_id == kiln.id,
            Batch.batch_date >= cutoff,
            Batch.batch_date <= date.today(),
        ).all()

        # Only count completed/in-progress firings for metrics
        fired_batches = [
            b for b in batches
            if b.status in (BatchStatus.DONE.value, BatchStatus.IN_PROGRESS.value)
        ]

        firings = len(fired_batches)

        # Average fill from metadata
        fill_values = []
        total_area = Decimal("0")
        for b in fired_batches:
            meta = b.metadata_json or {}
            util_pct = meta.get("kiln_utilization_pct")
            if util_pct is not None:
                fill_values.append(float(util_pct))
            area = meta.get("total_area_sqm")
            if area is not None:
                total_area += Decimal(str(area))

        avg_fill = round(sum(fill_values) / len(fill_values), 1) if fill_values else 0.0

        # Idle days = days in period without any batch firing
        firing_dates = {b.batch_date for b in batches}
        total_days = min(period_days, (date.today() - cutoff).days + 1)
        idle_days = total_days - len(firing_dates)

        kiln_metrics[str(kiln.id)] = {
            "name": kiln.name,
            "firings": firings,
            "avg_fill_pct": avg_fill,
            "idle_days": max(0, idle_days),
            "total_area_sqm": round(float(total_area), 2),
            "batches_count": len(batches),
        }

    # Factory summary
    total_firings = sum(m["firings"] for m in kiln_metrics.values())

    all_fills = [m["avg_fill_pct"] for m in kiln_metrics.values() if m["firings"] > 0]
    avg_util = round(sum(all_fills) / len(all_fills), 1) if all_fills else 0.0

    busiest = max(kiln_metrics.items(), key=lambda x: x[1]["firings"])
    least_busy = min(kiln_metrics.items(), key=lambda x: x[1]["firings"])

    return {
        "factory_id": str(factory_id),
        "period_days": period_days,
        "kilns": kiln_metrics,
        "summary": {
            "total_firings": total_firings,
            "avg_utilization_pct": avg_util,
            "busiest_kiln": {"id": busiest[0], "name": busiest[1]["name"]},
            "least_busy_kiln": {"id": least_busy[0], "name": least_busy[1]["name"]},
        },
    }
