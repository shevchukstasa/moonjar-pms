"""
Staffing Optimizer — AI-driven optimal worker distribution suggestions.

Analyzes production throughput data (TpsShiftMetric, last 7 days) against
scheduled demand (OrderPosition, next 7 days) and current worker assignments
(ShiftAssignment) to recommend rebalancing across production stages.

Algorithm:
  1. Per stage: calculate actual daily throughput, required throughput, current workers
  2. Derive workers_needed = ceil(required_throughput / throughput_per_worker)
  3. Identify bottlenecks (understaffed >110% capacity) and excess (overstaffed <50%)
  4. Generate actionable suggestions: move workers, add overtime, hire temp
"""
import logging
import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func

logger = logging.getLogger("moonjar.staffing_optimizer")

# ────────────────────────────────────────────────────────────────
# Production stages in order (maps to TpsShiftMetric.stage values
# and ShiftAssignment.stage values)
# ────────────────────────────────────────────────────────────────

PRODUCTION_STAGES = [
    "incoming_inspection",
    "engobe",
    "glazing",
    "pre_kiln_inspection",
    "kiln_loading",
    "firing",
    "sorting",
    "packing",
    "quality_check",
]

# Status → stage mapping for demand calculation (positions scheduled in next N days)
_STATUS_STAGE_MAP = {
    "planned": "incoming_inspection",
    "engobe_applied": "engobe",
    "engobe_check": "engobe",
    "glazed": "glazing",
    "sent_to_glazing": "glazing",
    "pre_kiln_check": "pre_kiln_inspection",
    "loaded_in_kiln": "kiln_loading",
    "fired": "firing",
    "refire": "firing",
    "transferred_to_sorting": "sorting",
    "packed": "packing",
    "sent_to_quality_check": "quality_check",
    "quality_check_done": "quality_check",
}

# Default throughput per worker per day (pcs) — fallback when no TpsShiftMetric data
_DEFAULT_THROUGHPUT_PER_WORKER = {
    "incoming_inspection": 200,
    "engobe": 120,
    "glazing": 80,
    "pre_kiln_inspection": 150,
    "kiln_loading": 100,
    "firing": 50,  # firing is kiln-constrained, not labor-constrained
    "sorting": 150,
    "packing": 100,
    "quality_check": 200,
}


# ────────────────────────────────────────────────────────────────
# Data structures
# ────────────────────────────────────────────────────────────────

@dataclass
class StageAnalysis:
    """Per-stage staffing analysis."""
    stage: str
    current_workers: int = 0
    avg_daily_throughput: float = 0.0  # actual avg from TpsShiftMetric (pcs/day)
    throughput_per_worker: float = 0.0  # derived: throughput / workers (or default)
    required_daily_throughput: float = 0.0  # demand from scheduled positions
    workers_needed: int = 0  # ceil(required / per_worker)
    worker_delta: int = 0  # needed - current (positive = understaffed)
    utilization_pct: float = 0.0  # required / capacity
    status: str = "balanced"  # "understaffed" | "overstaffed" | "balanced"


@dataclass
class StaffingSuggestion:
    """Single actionable staffing recommendation."""
    priority: int  # 1 = highest
    type: str  # "move_workers" | "add_workers" | "overtime" | "reduce"
    message: str  # human-readable recommendation
    from_stage: Optional[str] = None
    to_stage: Optional[str] = None
    worker_count: int = 0
    reason: str = ""


@dataclass
class StaffingOptimizationResult:
    """Complete staffing optimization output."""
    factory_id: str
    analysis_date: str
    horizon_days: int
    stages: list[StageAnalysis] = field(default_factory=list)
    suggestions: list[StaffingSuggestion] = field(default_factory=list)
    bottleneck_stage: Optional[str] = None
    excess_capacity_stages: list = field(default_factory=list)
    total_workers: int = 0
    total_workers_needed: int = 0


# ────────────────────────────────────────────────────────────────
# Core algorithm
# ────────────────────────────────────────────────────────────────

def suggest_optimal_staffing(
    db: Session,
    factory_id: UUID,
    horizon_days: int = 7,
) -> dict:
    """
    Analyze staffing across all production stages and generate optimization suggestions.

    Returns a dict with:
      - stages: per-stage analysis with throughput, workers, utilization
      - suggestions: ordered list of actionable recommendations
      - bottleneck_stage: the most constrained stage (highest understaffing)
      - excess_capacity_stages: stages with significant overcapacity
    """
    today = date.today()
    lookback_start = today - timedelta(days=horizon_days)
    horizon_end = today + timedelta(days=horizon_days)

    # 1. Get actual throughput per stage from TpsShiftMetric (last N days)
    throughput_by_stage = _get_actual_throughput(db, factory_id, lookback_start, today)

    # 2. Get current worker assignments per stage
    workers_by_stage = _get_current_workers(db, factory_id, today)

    # 3. Get required throughput per stage from scheduled positions (next N days)
    demand_by_stage = _get_demand_by_stage(db, factory_id, today, horizon_end)

    # 4. Build per-stage analysis
    stages: list[StageAnalysis] = []
    worst_delta = 0
    bottleneck = None
    excess_stages = []

    for stage_name in PRODUCTION_STAGES:
        analysis = _analyze_stage(
            stage_name,
            throughput_data=throughput_by_stage.get(stage_name),
            current_workers=workers_by_stage.get(stage_name, 0),
            required_throughput=demand_by_stage.get(stage_name, 0),
            horizon_days=horizon_days,
        )
        stages.append(analysis)

        if analysis.worker_delta > worst_delta:
            worst_delta = analysis.worker_delta
            bottleneck = stage_name

        if analysis.status == "overstaffed":
            excess_stages.append(stage_name)

    # 5. Generate suggestions
    suggestions = _generate_suggestions(stages, horizon_days)

    total_workers = sum(s.current_workers for s in stages)
    total_needed = sum(s.workers_needed for s in stages)

    result = StaffingOptimizationResult(
        factory_id=str(factory_id),
        analysis_date=today.isoformat(),
        horizon_days=horizon_days,
        stages=stages,
        suggestions=suggestions,
        bottleneck_stage=bottleneck,
        excess_capacity_stages=excess_stages,
        total_workers=total_workers,
        total_workers_needed=total_needed,
    )

    logger.info(
        "STAFFING_OPT | factory=%s | workers=%d needed=%d bottleneck=%s excess=%s suggestions=%d",
        factory_id, total_workers, total_needed, bottleneck, excess_stages, len(suggestions),
    )

    return _to_dict(result)


# ────────────────────────────────────────────────────────────────
# Data retrieval helpers
# ────────────────────────────────────────────────────────────────

def _get_actual_throughput(
    db: Session,
    factory_id: UUID,
    start_date: date,
    end_date: date,
) -> dict[str, dict]:
    """Get average daily throughput per stage from TpsShiftMetric.

    Returns {stage: {"avg_output": float, "avg_output_pcs": float, "days_with_data": int}}
    """
    from api.models import TpsShiftMetric

    rows = (
        db.query(
            TpsShiftMetric.stage,
            sa_func.avg(TpsShiftMetric.actual_output_pcs).label("avg_pcs"),
            sa_func.avg(TpsShiftMetric.actual_output).label("avg_sqm"),
            sa_func.count(sa_func.distinct(TpsShiftMetric.date)).label("days"),
        )
        .filter(
            TpsShiftMetric.factory_id == factory_id,
            TpsShiftMetric.date >= start_date,
            TpsShiftMetric.date <= end_date,
        )
        .group_by(TpsShiftMetric.stage)
        .all()
    )

    result = {}
    for row in rows:
        result[row.stage] = {
            "avg_output_pcs": float(row.avg_pcs or 0),
            "avg_output_sqm": float(row.avg_sqm or 0),
            "days_with_data": int(row.days or 0),
        }
    return result


def _get_current_workers(
    db: Session,
    factory_id: UUID,
    ref_date: date,
) -> dict[str, int]:
    """Get worker count per stage from ShiftAssignment.

    Uses the most recent assignment date <= ref_date for each stage.
    Falls back to ref_date if no historical data.
    """
    from api.models import ShiftAssignment
    import sqlalchemy as sa

    # Find the most recent date with any assignments at this factory
    latest_date = (
        db.query(sa_func.max(ShiftAssignment.date))
        .filter(
            ShiftAssignment.factory_id == factory_id,
            ShiftAssignment.date <= ref_date,
        )
        .scalar()
    )

    if not latest_date:
        return {}

    rows = (
        db.query(
            ShiftAssignment.stage,
            sa_func.count(sa.distinct(ShiftAssignment.user_id)).label("workers"),
        )
        .filter(
            ShiftAssignment.factory_id == factory_id,
            ShiftAssignment.date == latest_date,
        )
        .group_by(ShiftAssignment.stage)
        .all()
    )

    return {row.stage: int(row.workers) for row in rows}


def _get_demand_by_stage(
    db: Session,
    factory_id: UUID,
    start_date: date,
    end_date: date,
) -> dict[str, float]:
    """Calculate required daily throughput per stage from scheduled positions.

    Looks at positions with planned dates falling within the horizon window.
    Returns total pieces needed per stage (aggregated across horizon).
    """
    from api.models import OrderPosition
    from api.enums import PositionStatus

    # Active (non-terminal) positions at this factory
    active_statuses = [
        PositionStatus.PLANNED,
        PositionStatus.INSUFFICIENT_MATERIALS,
        PositionStatus.AWAITING_RECIPE,
        PositionStatus.AWAITING_STENCIL_SILKSCREEN,
        PositionStatus.AWAITING_COLOR_MATCHING,
        PositionStatus.AWAITING_SIZE_CONFIRMATION,
        PositionStatus.AWAITING_CONSUMPTION_DATA,
        PositionStatus.ENGOBE_APPLIED,
        PositionStatus.ENGOBE_CHECK,
        PositionStatus.GLAZED,
        PositionStatus.PRE_KILN_CHECK,
        PositionStatus.SENT_TO_GLAZING,
        PositionStatus.LOADED_IN_KILN,
        PositionStatus.FIRED,
        PositionStatus.TRANSFERRED_TO_SORTING,
        PositionStatus.REFIRE,
        PositionStatus.AWAITING_REGLAZE,
        PositionStatus.PACKED,
        PositionStatus.SENT_TO_QUALITY_CHECK,
    ]

    positions = (
        db.query(OrderPosition)
        .filter(
            OrderPosition.factory_id == factory_id,
            OrderPosition.status.in_(active_statuses),
        )
        .all()
    )

    demand: dict[str, float] = {}
    for pos in positions:
        # Determine which stage this position needs to go through next
        status_val = pos.status.value if hasattr(pos.status, "value") else str(pos.status)

        # For positions with planned dates in the horizon, count their demand
        # at the stage they're currently in AND subsequent stages
        in_horizon = _is_in_horizon(pos, start_date, end_date)
        if not in_horizon:
            continue

        qty = int(pos.quantity_with_defect_margin or pos.quantity or 0)
        if qty <= 0:
            continue

        # Map current status to stage and count demand at that stage
        current_stage = _STATUS_STAGE_MAP.get(status_val)
        if current_stage:
            demand[current_stage] = demand.get(current_stage, 0) + qty

        # Also count demand at subsequent stages (positions will flow through)
        if current_stage:
            stage_idx = PRODUCTION_STAGES.index(current_stage) if current_stage in PRODUCTION_STAGES else -1
            for next_stage in PRODUCTION_STAGES[stage_idx + 1:]:
                demand[next_stage] = demand.get(next_stage, 0) + qty

    return demand


def _is_in_horizon(pos, start_date: date, end_date: date) -> bool:
    """Check if a position has any planned date within the analysis horizon."""
    for date_attr in ("planned_glazing_date", "planned_kiln_date", "planned_sorting_date", "planned_completion_date"):
        d = getattr(pos, date_attr, None)
        if d and start_date <= d <= end_date:
            return True
    # If no planned dates, include positions that are actively in production
    status_val = pos.status.value if hasattr(pos.status, "value") else str(pos.status)
    active_in_progress = {
        "engobe_applied", "engobe_check", "glazed", "pre_kiln_check",
        "loaded_in_kiln", "fired", "transferred_to_sorting", "packed",
        "sent_to_quality_check", "refire", "sent_to_glazing",
    }
    return status_val in active_in_progress


# ────────────────────────────────────────────────────────────────
# Stage analysis
# ────────────────────────────────────────────────────────────────

def _analyze_stage(
    stage_name: str,
    throughput_data: Optional[dict],
    current_workers: int,
    required_throughput: float,
    horizon_days: int,
) -> StageAnalysis:
    """Analyze a single stage's staffing adequacy."""
    analysis = StageAnalysis(stage=stage_name, current_workers=current_workers)

    # Daily required throughput (total demand / horizon days)
    daily_required = required_throughput / max(horizon_days, 1)
    analysis.required_daily_throughput = round(daily_required, 1)

    # Actual throughput from metrics
    if throughput_data and throughput_data["days_with_data"] > 0:
        analysis.avg_daily_throughput = round(throughput_data["avg_output_pcs"], 1)
        if current_workers > 0:
            analysis.throughput_per_worker = round(
                throughput_data["avg_output_pcs"] / current_workers, 1
            )
        else:
            analysis.throughput_per_worker = _DEFAULT_THROUGHPUT_PER_WORKER.get(stage_name, 100)
    else:
        # No metrics data — use defaults
        default_rate = _DEFAULT_THROUGHPUT_PER_WORKER.get(stage_name, 100)
        analysis.throughput_per_worker = default_rate
        analysis.avg_daily_throughput = default_rate * max(current_workers, 1)

    # Workers needed
    if analysis.throughput_per_worker > 0 and daily_required > 0:
        analysis.workers_needed = math.ceil(daily_required / analysis.throughput_per_worker)
    else:
        analysis.workers_needed = current_workers  # no demand = keep current

    analysis.worker_delta = analysis.workers_needed - current_workers

    # Utilization and status
    capacity = analysis.throughput_per_worker * max(current_workers, 1)
    if capacity > 0:
        analysis.utilization_pct = round((daily_required / capacity) * 100, 1)
    else:
        analysis.utilization_pct = 0.0

    # Classify status
    if daily_required > capacity * 1.1:
        analysis.status = "understaffed"
    elif daily_required < capacity * 0.5 and current_workers > 1:
        analysis.status = "overstaffed"
    else:
        analysis.status = "balanced"

    return analysis


# ────────────────────────────────────────────────────────────────
# Suggestion generation
# ────────────────────────────────────────────────────────────────

def _generate_suggestions(
    stages: list[StageAnalysis],
    horizon_days: int,
) -> list[StaffingSuggestion]:
    """Generate actionable staffing suggestions based on stage analyses."""
    suggestions: list[StaffingSuggestion] = []
    priority_counter = 0

    understaffed = [s for s in stages if s.status == "understaffed"]
    overstaffed = [s for s in stages if s.status == "overstaffed"]

    # Sort: most understaffed first (highest delta)
    understaffed.sort(key=lambda s: s.worker_delta, reverse=True)
    # Sort: most overstaffed first (lowest delta, most negative)
    overstaffed.sort(key=lambda s: s.worker_delta)

    # 1. Move workers from overstaffed to understaffed stages
    available_pool: list[tuple[StageAnalysis, int]] = []
    for ov in overstaffed:
        excess = abs(ov.worker_delta)
        if excess > 0:
            available_pool.append((ov, excess))

    for us in understaffed:
        deficit = us.worker_delta
        if deficit <= 0:
            continue

        # Try to cover deficit from overstaffed stages
        for i, (ov, excess) in enumerate(available_pool):
            if deficit <= 0:
                break
            if excess <= 0:
                continue

            move_count = min(deficit, excess)
            priority_counter += 1
            suggestions.append(StaffingSuggestion(
                priority=priority_counter,
                type="move_workers",
                message=(
                    f"Move {move_count} worker{'s' if move_count > 1 else ''} "
                    f"from {_stage_label(ov.stage)} (overstaffed at {ov.utilization_pct}%) "
                    f"to {_stage_label(us.stage)} (understaffed at {us.utilization_pct}%)"
                ),
                from_stage=ov.stage,
                to_stage=us.stage,
                worker_count=move_count,
                reason=f"{_stage_label(us.stage)} needs {us.workers_needed} workers but has {us.current_workers}",
            ))
            deficit -= move_count
            available_pool[i] = (ov, excess - move_count)

        # If still understaffed after moves — suggest adding workers
        if deficit > 0:
            priority_counter += 1
            suggestions.append(StaffingSuggestion(
                priority=priority_counter,
                type="add_workers",
                message=(
                    f"Add {deficit} worker{'s' if deficit > 1 else ''} "
                    f"to {_stage_label(us.stage)} to meet demand "
                    f"({us.required_daily_throughput:.0f} pcs/day required, "
                    f"current capacity {us.avg_daily_throughput:.0f} pcs/day)"
                ),
                to_stage=us.stage,
                worker_count=deficit,
                reason=f"No available workers to redistribute from other stages",
            ))

    # 2. Overtime suggestions for critical understaffing (>150% utilization)
    for us in understaffed:
        if us.utilization_pct > 150:
            priority_counter += 1
            suggestions.append(StaffingSuggestion(
                priority=priority_counter,
                type="overtime",
                message=(
                    f"Consider overtime or weekend shifts for {_stage_label(us.stage)} "
                    f"— utilization at {us.utilization_pct}% indicates significant backlog risk"
                ),
                to_stage=us.stage,
                reason=f"Stage at {us.utilization_pct}% capacity with {us.worker_delta} worker deficit",
            ))

    # 3. If no suggestions needed — report healthy state
    if not suggestions:
        suggestions.append(StaffingSuggestion(
            priority=1,
            type="balanced",
            message="Staffing is well-balanced across all stages. No redistribution needed.",
            reason="All stages operating within 50-110% capacity utilization",
        ))

    return suggestions


def _stage_label(stage: str) -> str:
    """Convert stage key to human-readable label."""
    return stage.replace("_", " ").title()


# ────────────────────────────────────────────────────────────────
# Serialization
# ────────────────────────────────────────────────────────────────

def _to_dict(result: StaffingOptimizationResult) -> dict:
    """Convert result to JSON-serializable dict."""
    return {
        "factory_id": result.factory_id,
        "analysis_date": result.analysis_date,
        "horizon_days": result.horizon_days,
        "total_workers": result.total_workers,
        "total_workers_needed": result.total_workers_needed,
        "bottleneck_stage": result.bottleneck_stage,
        "excess_capacity_stages": result.excess_capacity_stages,
        "stages": [
            {
                "stage": s.stage,
                "stage_label": _stage_label(s.stage),
                "current_workers": s.current_workers,
                "workers_needed": s.workers_needed,
                "worker_delta": s.worker_delta,
                "avg_daily_throughput": s.avg_daily_throughput,
                "throughput_per_worker": s.throughput_per_worker,
                "required_daily_throughput": s.required_daily_throughput,
                "utilization_pct": s.utilization_pct,
                "status": s.status,
            }
            for s in result.stages
        ],
        "suggestions": [
            {
                "priority": sg.priority,
                "type": sg.type,
                "message": sg.message,
                "from_stage": sg.from_stage,
                "to_stage": sg.to_stage,
                "worker_count": sg.worker_count,
                "reason": sg.reason,
            }
            for sg in result.suggestions
        ],
    }
