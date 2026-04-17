"""Reports router — order summaries, kiln load reports, daily production.
See API_CONTRACTS.md for full specification.
"""

from collections import defaultdict
from uuid import UUID
from datetime import date, timedelta
from typing import Optional
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func as sa_func, cast, Date

from api.database import get_db
from api.roles import require_management
from api.models import (
    ProductionOrder, OrderPosition, Resource, Batch,
    DefectRecord, Factory,
)
from api.enums import (
    OrderStatus, PositionStatus, ResourceType, BatchStatus,
    DefectOutcome,
)

logger = logging.getLogger("moonjar.reports")

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
            {"id": "daily-production", "name": "Daily Production", "description": "Daily sorting, defects, packing per order"},
        ],
        "total": 3,
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


# ---------------------------------------------------------------------------
# Daily Production Report
# ---------------------------------------------------------------------------

@router.get("/daily-production")
async def daily_production_report(
    factory_id: UUID,
    report_date: Optional[str] = Query(None, alias="date", description="YYYY-MM-DD, defaults to today"),
    order_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Daily production report: sorted, defects by outcome, packed — grouped by order+color+method+size.

    The owner's spreadsheet tracks per-day production activity:
      Sorted | Refire | Repair | Grinding | ColorMismatch | WriteOff | TotalReject | Packed | DefectRate%

    Data sources:
      - **Sorted**: positions that transitioned to TRANSFERRED_TO_SORTING on this date
        (tracked via updated_at) PLUS good_quantity from parent positions whose
        sub-positions (split_category != null) were created on this date.
      - **Defects**: DefectRecord rows for the given date+factory, grouped by outcome.
      - **Packed**: positions that moved to PACKED status on this date (updated_at).
    """
    d = date.fromisoformat(report_date) if report_date else date.today()

    factory = db.query(Factory).filter(Factory.id == factory_id).first()
    factory_name = factory.name if factory else str(factory_id)

    # ── 1. Defects by position, grouped by outcome ──────────────────────
    defect_q = db.query(
        DefectRecord.position_id,
        DefectRecord.outcome,
        sa_func.sum(DefectRecord.quantity).label("qty"),
    ).filter(
        DefectRecord.factory_id == factory_id,
        DefectRecord.date == d,
    )
    if order_id:
        # Filter defects to only those linked to positions of the given order
        defect_q = defect_q.join(
            OrderPosition, DefectRecord.position_id == OrderPosition.id
        ).filter(OrderPosition.order_id == order_id)
    defect_q = defect_q.group_by(DefectRecord.position_id, DefectRecord.outcome)

    # Build {position_id: {outcome: qty}} map
    defect_map: dict[str, dict[str, int]] = {}
    position_ids_with_defects: set[str] = set()
    for row in defect_q.all():
        pid = str(row.position_id) if row.position_id else "__no_position__"
        position_ids_with_defects.add(pid)
        outcome_val = row.outcome if isinstance(row.outcome, str) else row.outcome.value
        defect_map.setdefault(pid, {})[outcome_val] = int(row.qty or 0)

    # ── 2. Sorted positions on this date ────────────────────────────────
    # Approach: positions that entered TRANSFERRED_TO_SORTING (or are sub-positions
    # created on this date with split_category set — i.e. sorting results).
    # We also count positions that moved to PACKED on the same day.
    #
    # "Sorted" = parent positions whose status became TRANSFERRED_TO_SORTING on this date
    #          + the total quantity from those positions (before split).
    #
    # For simplicity and reliability, we query:
    #   a) Positions with status in (TRANSFERRED_TO_SORTING, PACKED, READY_FOR_SHIPMENT, SHIPPED)
    #      where updated_at is on the given date AND parent_position_id IS NULL (root positions)
    #      → these are the ones sorted on that day.
    #   b) Sub-positions (split_category != null) created on this date → defect splits from sorting.
    #   c) Positions that are sub-positions created on this date also contribute to "sorted" count
    #      of the parent.

    # Query sub-positions created on this date (sorting splits)
    sub_pos_q = db.query(OrderPosition).filter(
        OrderPosition.factory_id == factory_id,
        OrderPosition.split_category.isnot(None),
        cast(OrderPosition.created_at, Date) == d,
    )
    if order_id:
        sub_pos_q = sub_pos_q.filter(OrderPosition.order_id == order_id)
    sub_positions = sub_pos_q.all()

    # Collect parent_position_ids that had sorting activity
    parent_ids_from_splits = set()
    for sp in sub_positions:
        if sp.parent_position_id:
            parent_ids_from_splits.add(sp.parent_position_id)

    # Query positions that moved to sorting-related statuses on this date
    sorted_statuses = [
        PositionStatus.TRANSFERRED_TO_SORTING.value,
        PositionStatus.PACKED.value,
        PositionStatus.READY_FOR_SHIPMENT.value,
        PositionStatus.SHIPPED.value,
    ]
    sorted_pos_q = db.query(OrderPosition).filter(
        OrderPosition.factory_id == factory_id,
        OrderPosition.parent_position_id.is_(None),  # root positions only
        OrderPosition.status.in_(sorted_statuses),
        cast(OrderPosition.updated_at, Date) == d,
    )
    if order_id:
        sorted_pos_q = sorted_pos_q.filter(OrderPosition.order_id == order_id)
    sorted_positions = sorted_pos_q.all()

    # Also load parent positions from splits (they may have been sorted earlier
    # but splits created today — the sorted count is the parent quantity)
    extra_parent_ids = parent_ids_from_splits - {p.id for p in sorted_positions}
    extra_parents = []
    if extra_parent_ids:
        extra_parents = db.query(OrderPosition).filter(
            OrderPosition.id.in_(list(extra_parent_ids))
        ).all()

    all_sorted = {p.id: p for p in sorted_positions}
    for p in extra_parents:
        all_sorted[p.id] = p

    # ── 3. Packed positions on this date ────────────────────────────────
    packed_q = db.query(OrderPosition).filter(
        OrderPosition.factory_id == factory_id,
        OrderPosition.status == PositionStatus.PACKED.value,
        cast(OrderPosition.updated_at, Date) == d,
    )
    if order_id:
        packed_q = packed_q.filter(OrderPosition.order_id == order_id)
    packed_positions = packed_q.all()
    packed_map: dict[str, int] = {}  # position_id -> packed qty
    for p in packed_positions:
        packed_map[str(p.id)] = p.quantity

    # ── 4. Collect all position IDs we need order info for ──────────────
    all_position_ids = set()
    for pid in position_ids_with_defects:
        if pid != "__no_position__":
            all_position_ids.add(pid)
    for pid in all_sorted:
        all_position_ids.add(str(pid))
    for sp in sub_positions:
        all_position_ids.add(str(sp.id))
        if sp.parent_position_id:
            all_position_ids.add(str(sp.parent_position_id))
    for pid in packed_map:
        all_position_ids.add(pid)

    # Load all relevant positions with their orders in one query
    positions_by_id: dict[str, OrderPosition] = {}
    if all_position_ids:
        pos_rows = db.query(OrderPosition).options(
            joinedload(OrderPosition.order)
        ).filter(
            OrderPosition.id.in_([UUID(pid) for pid in all_position_ids if pid != "__no_position__"])
        ).all()
        for p in pos_rows:
            positions_by_id[str(p.id)] = p

    # ── 5. Aggregate into report rows ───────────────────────────────────
    # Group key: (order_number, color, method, size)
    row_data: dict[tuple, dict] = defaultdict(lambda: {
        "sorted": 0, "refire": 0, "repair": 0, "grinding": 0,
        "color_mismatch": 0, "write_off": 0, "packed": 0,
        "order_number": "", "color": "", "method": "", "size": "",
    })

    def _group_key(pos: OrderPosition) -> tuple:
        order_num = pos.order.order_number if pos.order else "Unknown"
        color = pos.color or ""
        method = (pos.application_method_code or pos.application or "").upper()
        size = pos.size or ""
        return (order_num, color, method, size)

    # Add sorted quantities
    for pid, pos in all_sorted.items():
        key = _group_key(pos)
        row_data[key]["order_number"] = key[0]
        row_data[key]["color"] = key[1]
        row_data[key]["method"] = key[2]
        row_data[key]["size"] = key[3]
        row_data[key]["sorted"] += pos.quantity

    # Add defect quantities from DefectRecord
    for pid, outcomes in defect_map.items():
        if pid == "__no_position__":
            continue
        pos = positions_by_id.get(pid)
        if not pos:
            continue
        # Use the parent position for grouping if this is a sub-position
        group_pos = pos
        if pos.parent_position_id and str(pos.parent_position_id) in positions_by_id:
            group_pos = positions_by_id[str(pos.parent_position_id)]
        key = _group_key(group_pos)
        row_data[key]["order_number"] = key[0]
        row_data[key]["color"] = key[1]
        row_data[key]["method"] = key[2]
        row_data[key]["size"] = key[3]

        for outcome, qty in outcomes.items():
            if outcome == DefectOutcome.REFIRE.value:
                row_data[key]["refire"] += qty
            elif outcome == DefectOutcome.REPAIR.value:
                row_data[key]["repair"] += qty
            elif outcome == DefectOutcome.GRINDING.value:
                row_data[key]["grinding"] += qty
            elif outcome == DefectOutcome.WRITE_OFF.value:
                row_data[key]["write_off"] += qty
            elif outcome == DefectOutcome.TO_MANA.value:
                row_data[key]["write_off"] += qty  # to_mana counts as write-off in report
            elif outcome == DefectOutcome.REGLAZE.value:
                row_data[key]["repair"] += qty  # reglaze = repair
            elif outcome == DefectOutcome.RETURN_TO_WORK.value:
                pass  # return_to_work is not a reject
            elif outcome == DefectOutcome.TO_STOCK.value:
                pass  # to_stock is not a reject

    # Add color_mismatch from sub-positions with split_category = color_mismatch
    for sp in sub_positions:
        group_pos = sp
        if sp.parent_position_id and str(sp.parent_position_id) in positions_by_id:
            group_pos = positions_by_id[str(sp.parent_position_id)]
        key = _group_key(group_pos)
        row_data[key]["order_number"] = key[0]
        row_data[key]["color"] = key[1]
        row_data[key]["method"] = key[2]
        row_data[key]["size"] = key[3]

        cat = sp.split_category if isinstance(sp.split_category, str) else sp.split_category.value
        if cat == "color_mismatch":
            row_data[key]["color_mismatch"] += sp.quantity

    # Add packed quantities
    for pid, qty in packed_map.items():
        pos = positions_by_id.get(pid)
        if not pos:
            continue
        key = _group_key(pos)
        row_data[key]["order_number"] = key[0]
        row_data[key]["color"] = key[1]
        row_data[key]["method"] = key[2]
        row_data[key]["size"] = key[3]
        row_data[key]["packed"] += qty

    # ── 6. Build response rows with totals ──────────────────────────────
    rows = []
    total_sorted = 0
    total_refire = 0
    total_repair = 0
    total_grinding = 0
    total_color_mismatch = 0
    total_write_off = 0
    total_packed = 0

    for key, data in sorted(row_data.items()):
        reject = data["refire"] + data["repair"] + data["grinding"] + data["color_mismatch"] + data["write_off"]
        defect_pct = round((reject / data["sorted"]) * 100, 2) if data["sorted"] > 0 else 0.0

        rows.append({
            "order_number": data["order_number"],
            "color": data["color"],
            "method": data["method"],
            "size": data["size"],
            "sorted": data["sorted"],
            "refire": data["refire"],
            "repair": data["repair"],
            "grinding": data["grinding"],
            "color_mismatch": data["color_mismatch"],
            "write_off": data["write_off"],
            "total_reject": reject,
            "packed": data["packed"],
            "defect_rate_pct": defect_pct,
        })

        total_sorted += data["sorted"]
        total_refire += data["refire"]
        total_repair += data["repair"]
        total_grinding += data["grinding"]
        total_color_mismatch += data["color_mismatch"]
        total_write_off += data["write_off"]
        total_packed += data["packed"]

    total_reject = total_refire + total_repair + total_grinding + total_color_mismatch + total_write_off
    overall_defect_pct = round((total_reject / total_sorted) * 100, 2) if total_sorted > 0 else 0.0

    return {
        "date": str(d),
        "factory": factory_name,
        "factory_id": str(factory_id),
        "summary": {
            "total_sorted": total_sorted,
            "total_refire": total_refire,
            "total_repair": total_repair,
            "total_grinding": total_grinding,
            "total_color_mismatch": total_color_mismatch,
            "total_write_off": total_write_off,
            "total_reject": total_reject,
            "total_packed": total_packed,
            "defect_rate_pct": overall_defect_pct,
        },
        "rows": rows,
    }
