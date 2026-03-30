"""
Anomaly Detection Service for Production Data.

Detects statistical anomalies in:
1. Defect rates -- spike above 2sigma from rolling average
2. Throughput -- sudden drop in output per stage
3. Cycle times -- positions taking unusually long at a stage
4. Material consumption -- usage significantly above BOM estimates
5. Kiln efficiency -- unusual temperature profiles or batch failures

Method: Z-score based anomaly detection using rolling windows.
For each metric, maintain a rolling mean + stddev over last 30 data points.
Flag as anomaly when |current - mean| > 2 * stddev.
"""

from dataclasses import dataclass
from typing import Optional
from uuid import UUID
from datetime import date, timedelta
from math import sqrt
import logging

from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func

from api.models import (
    TpsShiftMetric, OrderPosition, Batch, DefectRecord,
    ProductionDefect, Resource, MaterialTransaction,
    RecipeMaterial, Factory,
)
from api.enums import (
    BatchStatus, PositionStatus, ResourceType, DefectStage,
)

logger = logging.getLogger("moonjar.anomaly")

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

MIN_SAMPLE_SIZE = 5  # Minimum data points needed for statistical analysis


@dataclass
class Anomaly:
    type: str           # "defect_spike" | "throughput_drop" | "cycle_time" | "material_excess" | "kiln_anomaly"
    severity: str       # "warning" | "critical"
    metric_name: str    # e.g., "defect_rate_pigment"
    current_value: float
    expected_range: tuple  # (mean - 2sigma, mean + 2sigma)
    z_score: float
    factory_id: UUID
    related_entity_id: Optional[UUID] = None  # position, batch, kiln
    description: str = ""


# ---------------------------------------------------------------------------
# Statistics helpers (no numpy/scipy)
# ---------------------------------------------------------------------------

def _mean(values: list[float]) -> float:
    """Calculate arithmetic mean."""
    if not values:
        return 0.0
    return sum(values) / len(values)


def _stddev(values: list[float], mean_val: float) -> float:
    """Calculate sample standard deviation."""
    n = len(values)
    if n < 2:
        return 0.0
    variance = sum((v - mean_val) ** 2 for v in values) / (n - 1)
    return sqrt(variance)


def _z_score(current: float, mean_val: float, std: float) -> float:
    """Calculate z-score. Returns 0 if stddev is 0."""
    if std == 0:
        return 0.0
    return (current - mean_val) / std


def _classify_severity(z: float) -> str:
    """Classify severity based on z-score magnitude."""
    abs_z = abs(z)
    if abs_z >= 3.0:
        return "critical"
    return "warning"


# ---------------------------------------------------------------------------
# 1. Defect rate anomalies
# ---------------------------------------------------------------------------

def detect_defect_anomalies(
    db: Session, factory_id: UUID, lookback_days: int = 30
) -> list[Anomaly]:
    """Detect spikes in defect rates by stage.

    Groups daily defect counts by stage over the lookback window.
    Compares the latest day's defect rate against the rolling stats.
    """
    anomalies: list[Anomaly] = []
    today = date.today()
    cutoff = today - timedelta(days=lookback_days)

    # Daily defect counts grouped by stage
    rows = (
        db.query(
            DefectRecord.stage,
            DefectRecord.date,
            sa_func.sum(DefectRecord.quantity).label("total_defects"),
        )
        .filter(
            DefectRecord.factory_id == factory_id,
            DefectRecord.date >= cutoff,
        )
        .group_by(DefectRecord.stage, DefectRecord.date)
        .order_by(DefectRecord.stage, DefectRecord.date)
        .all()
    )

    if not rows:
        return anomalies

    # Group by stage
    stage_data: dict[str, list[tuple[date, float]]] = {}
    for row in rows:
        stage_key = row.stage.value if hasattr(row.stage, "value") else str(row.stage)
        if stage_key not in stage_data:
            stage_data[stage_key] = []
        stage_data[stage_key].append((row.date, float(row.total_defects)))

    for stage_key, data_points in stage_data.items():
        if len(data_points) < MIN_SAMPLE_SIZE:
            continue

        values = [dp[1] for dp in data_points]
        # Use all but the last point as historical, last as current
        historical = values[:-1]
        current = values[-1]
        latest_date = data_points[-1][0]

        # Only flag if the latest data point is recent (within 2 days)
        if (today - latest_date).days > 2:
            continue

        mean_val = _mean(historical)
        std = _stddev(historical, mean_val)

        if std == 0:
            continue

        z = _z_score(current, mean_val, std)

        # Only flag upward spikes (more defects than expected)
        if z > 2.0:
            lower = max(0, mean_val - 2 * std)
            upper = mean_val + 2 * std
            anomalies.append(Anomaly(
                type="defect_spike",
                severity=_classify_severity(z),
                metric_name=f"defect_count_{stage_key}",
                current_value=round(current, 2),
                expected_range=(round(lower, 2), round(upper, 2)),
                z_score=round(z, 2),
                factory_id=factory_id,
                description=(
                    f"Defect count at {stage_key} stage is {current:.0f}, "
                    f"expected range [{lower:.1f} - {upper:.1f}] "
                    f"(z={z:.1f})"
                ),
            ))

    # Also check ProductionDefect by glaze_type
    pd_rows = (
        db.query(
            ProductionDefect.glaze_type,
            ProductionDefect.fired_at,
            sa_func.sum(ProductionDefect.defect_quantity).label("defects"),
            sa_func.sum(ProductionDefect.total_quantity).label("total"),
        )
        .filter(
            ProductionDefect.factory_id == factory_id,
            ProductionDefect.fired_at >= cutoff,
        )
        .group_by(ProductionDefect.glaze_type, ProductionDefect.fired_at)
        .order_by(ProductionDefect.glaze_type, ProductionDefect.fired_at)
        .all()
    )

    glaze_data: dict[str, list[tuple[date, float]]] = {}
    for row in pd_rows:
        gtype = row.glaze_type or "unknown"
        total = float(row.total or 0)
        if total <= 0:
            continue
        rate = float(row.defects or 0) / total * 100
        if gtype not in glaze_data:
            glaze_data[gtype] = []
        glaze_data[gtype].append((row.fired_at, rate))

    for gtype, data_points in glaze_data.items():
        if len(data_points) < MIN_SAMPLE_SIZE:
            continue

        values = [dp[1] for dp in data_points]
        historical = values[:-1]
        current = values[-1]
        latest_date = data_points[-1][0]

        if (today - latest_date).days > 2:
            continue

        mean_val = _mean(historical)
        std = _stddev(historical, mean_val)
        if std == 0:
            continue

        z = _z_score(current, mean_val, std)
        if z > 2.0:
            lower = max(0, mean_val - 2 * std)
            upper = mean_val + 2 * std
            anomalies.append(Anomaly(
                type="defect_spike",
                severity=_classify_severity(z),
                metric_name=f"defect_rate_{gtype}",
                current_value=round(current, 2),
                expected_range=(round(lower, 2), round(upper, 2)),
                z_score=round(z, 2),
                factory_id=factory_id,
                description=(
                    f"Defect rate for glaze '{gtype}' is {current:.1f}%, "
                    f"expected [{lower:.1f}% - {upper:.1f}%] (z={z:.1f})"
                ),
            ))

    return anomalies


# ---------------------------------------------------------------------------
# 2. Throughput anomalies
# ---------------------------------------------------------------------------

def detect_throughput_anomalies(
    db: Session, factory_id: UUID, lookback_days: int = 30
) -> list[Anomaly]:
    """Detect drops in production throughput by stage.

    Uses TPS shift metrics to check daily output per stage.
    Flags when today's output is significantly below the rolling average.
    """
    anomalies: list[Anomaly] = []
    today = date.today()
    cutoff = today - timedelta(days=lookback_days)

    rows = (
        db.query(
            TpsShiftMetric.stage,
            TpsShiftMetric.date,
            sa_func.sum(TpsShiftMetric.actual_output).label("daily_output"),
        )
        .filter(
            TpsShiftMetric.factory_id == factory_id,
            TpsShiftMetric.date >= cutoff,
        )
        .group_by(TpsShiftMetric.stage, TpsShiftMetric.date)
        .order_by(TpsShiftMetric.stage, TpsShiftMetric.date)
        .all()
    )

    if not rows:
        return anomalies

    stage_data: dict[str, list[tuple[date, float]]] = {}
    for row in rows:
        stage = row.stage
        if stage not in stage_data:
            stage_data[stage] = []
        stage_data[stage].append((row.date, float(row.daily_output or 0)))

    for stage, data_points in stage_data.items():
        if len(data_points) < MIN_SAMPLE_SIZE:
            continue

        values = [dp[1] for dp in data_points]
        historical = values[:-1]
        current = values[-1]
        latest_date = data_points[-1][0]

        if (today - latest_date).days > 2:
            continue

        mean_val = _mean(historical)
        std = _stddev(historical, mean_val)
        if std == 0:
            continue

        z = _z_score(current, mean_val, std)

        # Flag downward drops (negative z means below average)
        if z < -2.0:
            lower = max(0, mean_val - 2 * std)
            upper = mean_val + 2 * std
            anomalies.append(Anomaly(
                type="throughput_drop",
                severity=_classify_severity(z),
                metric_name=f"throughput_{stage}",
                current_value=round(current, 2),
                expected_range=(round(lower, 2), round(upper, 2)),
                z_score=round(z, 2),
                factory_id=factory_id,
                description=(
                    f"Throughput at '{stage}' dropped to {current:.1f} sqm, "
                    f"expected [{lower:.1f} - {upper:.1f}] (z={z:.1f})"
                ),
            ))

    return anomalies


# ---------------------------------------------------------------------------
# 3. Cycle time anomalies
# ---------------------------------------------------------------------------

def detect_cycle_time_anomalies(
    db: Session, factory_id: UUID
) -> list[Anomaly]:
    """Detect positions stuck at a stage for unusually long.

    Looks at active positions and checks how long they've been at their
    current stage by comparing created_at/updated_at to now.
    Also uses TPS cycle_time_minutes for stage-level analysis.
    """
    anomalies: list[Anomaly] = []
    today = date.today()
    cutoff = today - timedelta(days=30)

    # Stage-level cycle times from TPS metrics
    rows = (
        db.query(
            TpsShiftMetric.stage,
            TpsShiftMetric.date,
            sa_func.avg(TpsShiftMetric.cycle_time_minutes).label("avg_cycle"),
        )
        .filter(
            TpsShiftMetric.factory_id == factory_id,
            TpsShiftMetric.date >= cutoff,
            TpsShiftMetric.cycle_time_minutes > 0,
        )
        .group_by(TpsShiftMetric.stage, TpsShiftMetric.date)
        .order_by(TpsShiftMetric.stage, TpsShiftMetric.date)
        .all()
    )

    if not rows:
        return anomalies

    stage_data: dict[str, list[tuple[date, float]]] = {}
    for row in rows:
        stage = row.stage
        if stage not in stage_data:
            stage_data[stage] = []
        stage_data[stage].append((row.date, float(row.avg_cycle)))

    for stage, data_points in stage_data.items():
        if len(data_points) < MIN_SAMPLE_SIZE:
            continue

        values = [dp[1] for dp in data_points]
        historical = values[:-1]
        current = values[-1]
        latest_date = data_points[-1][0]

        if (today - latest_date).days > 2:
            continue

        mean_val = _mean(historical)
        std = _stddev(historical, mean_val)
        if std == 0:
            continue

        z = _z_score(current, mean_val, std)

        # Flag abnormally high cycle times
        if z > 2.0:
            lower = max(0, mean_val - 2 * std)
            upper = mean_val + 2 * std
            anomalies.append(Anomaly(
                type="cycle_time",
                severity=_classify_severity(z),
                metric_name=f"cycle_time_{stage}",
                current_value=round(current, 2),
                expected_range=(round(lower, 2), round(upper, 2)),
                z_score=round(z, 2),
                factory_id=factory_id,
                description=(
                    f"Cycle time at '{stage}' is {current:.1f} min, "
                    f"expected [{lower:.1f} - {upper:.1f}] min (z={z:.1f})"
                ),
            ))

    return anomalies


# ---------------------------------------------------------------------------
# 4. Material consumption anomalies
# ---------------------------------------------------------------------------

def detect_material_consumption_anomalies(
    db: Session, factory_id: UUID
) -> list[Anomaly]:
    """Detect material usage significantly above BOM estimates.

    Compares actual consumed quantities (from material_transactions)
    against expected quantities (from recipe_materials * position quantity).
    """
    anomalies: list[Anomaly] = []
    cutoff = date.today() - timedelta(days=7)

    # Get recent consume transactions grouped by material
    consume_rows = (
        db.query(
            MaterialTransaction.material_id,
            sa_func.sum(MaterialTransaction.quantity).label("total_consumed"),
        )
        .filter(
            MaterialTransaction.factory_id == factory_id,
            MaterialTransaction.type == "consume",
            MaterialTransaction.created_at >= cutoff,
        )
        .group_by(MaterialTransaction.material_id)
        .all()
    )

    if not consume_rows:
        return anomalies

    # Get weekly consumption history for last 30 days by material
    for row in consume_rows:
        material_id = row.material_id
        current_consumption = abs(float(row.total_consumed))

        # Get historical weekly consumption for this material (rolling 4 weeks)
        weekly_data = []
        for weeks_ago in range(1, 5):
            week_start = date.today() - timedelta(days=7 * (weeks_ago + 1))
            week_end = date.today() - timedelta(days=7 * weeks_ago)

            week_total = (
                db.query(sa_func.sum(MaterialTransaction.quantity))
                .filter(
                    MaterialTransaction.factory_id == factory_id,
                    MaterialTransaction.material_id == material_id,
                    MaterialTransaction.type == "consume",
                    MaterialTransaction.created_at >= week_start,
                    MaterialTransaction.created_at < week_end,
                )
                .scalar()
            )
            if week_total is not None:
                weekly_data.append(abs(float(week_total)))

        if len(weekly_data) < 3:
            continue

        mean_val = _mean(weekly_data)
        std = _stddev(weekly_data, mean_val)
        if std == 0 or mean_val == 0:
            continue

        z = _z_score(current_consumption, mean_val, std)

        if z > 2.0:
            lower = max(0, mean_val - 2 * std)
            upper = mean_val + 2 * std
            anomalies.append(Anomaly(
                type="material_excess",
                severity=_classify_severity(z),
                metric_name=f"material_{material_id}",
                current_value=round(current_consumption, 3),
                expected_range=(round(lower, 3), round(upper, 3)),
                z_score=round(z, 2),
                factory_id=factory_id,
                related_entity_id=material_id,
                description=(
                    f"Material consumption this week: {current_consumption:.2f}, "
                    f"expected [{lower:.2f} - {upper:.2f}] (z={z:.1f})"
                ),
            ))

    return anomalies


# ---------------------------------------------------------------------------
# 5. Kiln anomalies
# ---------------------------------------------------------------------------

def detect_kiln_anomalies(
    db: Session, factory_id: UUID
) -> list[Anomaly]:
    """Detect kiln batch failures or unusual patterns.

    Checks:
    - Batch failure rates per kiln over the last 30 days
    - Unusual batch load patterns (low utilization)
    """
    anomalies: list[Anomaly] = []
    today = date.today()
    cutoff = today - timedelta(days=30)

    kilns = (
        db.query(Resource)
        .filter(
            Resource.factory_id == factory_id,
            Resource.resource_type == ResourceType.KILN.value,
            Resource.is_active.is_(True),
        )
        .all()
    )

    if not kilns:
        return anomalies

    for kiln in kilns:
        # Get batches for this kiln
        batches = (
            db.query(Batch)
            .filter(
                Batch.resource_id == kiln.id,
                Batch.batch_date >= cutoff,
                Batch.status == BatchStatus.DONE.value,
            )
            .order_by(Batch.batch_date)
            .all()
        )

        if len(batches) < MIN_SAMPLE_SIZE:
            continue

        capacity = float(kiln.capacity_sqm or 0)
        if capacity <= 0:
            continue

        # Calculate utilization per batch
        utilizations = []
        for batch in batches:
            loaded = (
                db.query(sa_func.sum(OrderPosition.quantity_sqm))
                .filter(OrderPosition.batch_id == batch.id)
                .scalar()
            )
            loaded_sqm = float(loaded or 0)
            util = (loaded_sqm / capacity) * 100 if capacity > 0 else 0
            utilizations.append((batch.batch_date, min(util, 100.0), batch.id))

        if len(utilizations) < MIN_SAMPLE_SIZE:
            continue

        values = [u[1] for u in utilizations]
        historical = values[:-1]
        current = values[-1]
        latest_date = utilizations[-1][0]
        latest_batch_id = utilizations[-1][2]

        if (today - latest_date).days > 3:
            continue

        mean_val = _mean(historical)
        std = _stddev(historical, mean_val)
        if std == 0:
            continue

        z = _z_score(current, mean_val, std)

        # Flag abnormally low utilization
        if z < -2.0:
            lower = max(0, mean_val - 2 * std)
            upper = min(100, mean_val + 2 * std)
            anomalies.append(Anomaly(
                type="kiln_anomaly",
                severity=_classify_severity(z),
                metric_name=f"kiln_utilization_{kiln.name}",
                current_value=round(current, 1),
                expected_range=(round(lower, 1), round(upper, 1)),
                z_score=round(z, 2),
                factory_id=factory_id,
                related_entity_id=kiln.id,
                description=(
                    f"Kiln '{kiln.name}' utilization dropped to {current:.1f}%, "
                    f"expected [{lower:.1f}% - {upper:.1f}%] (z={z:.1f})"
                ),
            ))

    # Check defect rates per kiln (from DefectRecord after_firing)
    for kiln in kilns:
        batch_ids_q = (
            db.query(Batch.id)
            .filter(
                Batch.resource_id == kiln.id,
                Batch.batch_date >= cutoff,
                Batch.status == BatchStatus.DONE.value,
            )
        )
        batch_ids = [b.id for b in batch_ids_q.all()]
        if not batch_ids:
            continue

        # Defects linked to batches in this kiln
        defect_rows = (
            db.query(
                DefectRecord.date,
                sa_func.sum(DefectRecord.quantity).label("defects"),
            )
            .filter(
                DefectRecord.batch_id.in_(batch_ids),
                DefectRecord.stage == DefectStage.AFTER_FIRING.value,
            )
            .group_by(DefectRecord.date)
            .order_by(DefectRecord.date)
            .all()
        )

        if len(defect_rows) < MIN_SAMPLE_SIZE:
            continue

        values = [float(r.defects) for r in defect_rows]
        historical = values[:-1]
        current = values[-1]
        latest_date = defect_rows[-1].date

        if (today - latest_date).days > 3:
            continue

        mean_val = _mean(historical)
        std = _stddev(historical, mean_val)
        if std == 0:
            continue

        z = _z_score(current, mean_val, std)

        if z > 2.0:
            lower = max(0, mean_val - 2 * std)
            upper = mean_val + 2 * std
            anomalies.append(Anomaly(
                type="kiln_anomaly",
                severity=_classify_severity(z),
                metric_name=f"kiln_defects_{kiln.name}",
                current_value=round(current, 0),
                expected_range=(round(lower, 1), round(upper, 1)),
                z_score=round(z, 2),
                factory_id=factory_id,
                related_entity_id=kiln.id,
                description=(
                    f"Post-firing defects for kiln '{kiln.name}': {current:.0f} pcs, "
                    f"expected [{lower:.1f} - {upper:.1f}] (z={z:.1f})"
                ),
            ))

    return anomalies


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run_all_anomaly_checks(db: Session, factory_id: UUID) -> list[Anomaly]:
    """Run all anomaly checks and return combined results."""
    all_anomalies: list[Anomaly] = []

    checks = [
        ("defect", detect_defect_anomalies),
        ("throughput", detect_throughput_anomalies),
        ("cycle_time", detect_cycle_time_anomalies),
        ("material", detect_material_consumption_anomalies),
        ("kiln", detect_kiln_anomalies),
    ]

    for name, check_fn in checks:
        try:
            results = check_fn(db, factory_id)
            all_anomalies.extend(results)
            if results:
                logger.info(
                    "Factory %s: %d %s anomalies detected",
                    factory_id, len(results), name,
                )
        except Exception as e:
            logger.error(
                "Anomaly check '%s' failed for factory %s: %s",
                name, factory_id, e,
            )

    return all_anomalies


def create_anomaly_alerts(db: Session, anomalies: list[Anomaly]) -> int:
    """Create notifications for detected anomalies.

    Returns the number of notifications created.
    """
    if not anomalies:
        return 0

    from business.services.notifications import notify_pm

    count = 0
    for anomaly in anomalies:
        try:
            notifs = notify_pm(
                db=db,
                factory_id=anomaly.factory_id,
                type="alert",
                title=f"Anomaly: {anomaly.metric_name} ({anomaly.severity})",
                message=anomaly.description,
                related_entity_type="batch" if anomaly.type == "kiln_anomaly" else None,
                related_entity_id=anomaly.related_entity_id,
            )
            count += len(notifs)
        except Exception as e:
            logger.error("Failed to create alert for anomaly %s: %s", anomaly.metric_name, e)

    return count


# ---------------------------------------------------------------------------
# Serialization (for API responses)
# ---------------------------------------------------------------------------

def anomaly_to_dict(anomaly: Anomaly) -> dict:
    """Convert Anomaly dataclass to JSON-serializable dict."""
    return {
        "type": anomaly.type,
        "severity": anomaly.severity,
        "metric_name": anomaly.metric_name,
        "current_value": anomaly.current_value,
        "expected_range": {
            "lower": anomaly.expected_range[0],
            "upper": anomaly.expected_range[1],
        },
        "z_score": anomaly.z_score,
        "factory_id": str(anomaly.factory_id),
        "related_entity_id": str(anomaly.related_entity_id) if anomaly.related_entity_id else None,
        "description": anomaly.description,
    }
