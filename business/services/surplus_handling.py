"""
Surplus Handling Service.

After sorting, surplus items need disposition:
1. Check color — if base color (white, ivory, cream, beige, grey, black) -> showroom
2. Check quantity — if small batch (< 5 sqm) -> casters/mana
3. Check quality — if minor defects -> seconds outlet
4. Otherwise -> warehouse stock for future orders

Rules from ARCHITECTURE.md:
- Base colors: White, Ivory, Cream, Beige, Grey, Black -> showroom priority
- Custom colors -> warehouse first, if no demand in 30 days -> casters

Integration with existing code:
- sorting_split.py already has handle_surplus() with size-based routing (10x10 logic)
- This service provides the enhanced auto-disposition logic referenced in the spec
- defects.py surplus-dispositions endpoint uses this for summary/batch processing
"""

import logging
from uuid import UUID
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from api.models import (
    OrderPosition, SurplusDisposition, CastersBox, ManaShipment,
    Task, Color, ProductionOrder,
)
from api.enums import (
    SurplusDispositionType, TaskType, UserRole,
    ManaShipmentStatus, PositionStatus,
)

logger = logging.getLogger("moonjar.surplus_handling")

# Well-known base colors (fallback if DB lookup fails)
BASE_COLORS = {"White", "Ivory", "Cream", "Beige", "Grey", "Black"}

# Threshold for "small batch" in sqm — goes to casters
SMALL_BATCH_SQM_THRESHOLD = 5.0

# Days without demand before custom-color warehouse stock -> casters
NO_DEMAND_DAYS = 30

# Accumulation threshold for PM decision task
_ACCUMULATION_TASK_THRESHOLD = 100


def _check_is_base_color(db: Session, color_name: str) -> bool:
    """
    Check if a color is a base color by looking up colors.is_basic in DB.
    Falls back to the hardcoded BASE_COLORS set if not found.
    """
    color = db.query(Color).filter(Color.name == color_name).first()
    if color is not None:
        return bool(color.is_basic)
    # Fallback: check against known base colors (case-insensitive)
    return color_name.strip().title() in BASE_COLORS


def _get_position_sqm(position: OrderPosition) -> float:
    """Get the area in sqm for a position, with fallback calculation."""
    if position.quantity_sqm:
        return float(position.quantity_sqm)
    # Fallback: try to calculate from size string (e.g. "10x10", "5×21,5" -> sqm per piece)
    try:
        from business.services.size_normalizer import normalize_size_str
        parts = normalize_size_str(position.size).split("x")
        if len(parts) >= 2:
            w_cm, h_cm = float(parts[0]), float(parts[1])
            sqm_per_piece = (w_cm * h_cm) / 10000.0
            return sqm_per_piece * position.quantity
    except (ValueError, AttributeError):
        pass
    return 0.0


def auto_assign_surplus_disposition(
    db: Session,
    position: OrderPosition,
    surplus_quantity: Optional[int] = None,
) -> dict:
    """
    Automatically determine disposition for a surplus position.

    Decision tree:
    1. Size == 10x10 AND base color -> SHOWROOM (display board)
    2. Size == 10x10 AND non-base color -> CASTERS (coaster box)
    3. Non-10x10 AND base color AND quantity >= threshold -> SHOWROOM
    4. Non-10x10 AND small batch (< 5 sqm) -> CASTERS
    5. Non-10x10 -> MANA (general surplus shipment)

    Args:
        db: Database session
        position: The OrderPosition with surplus
        surplus_quantity: Override quantity (defaults to position.quantity)

    Returns:
        {"disposition": "showroom"|"casters"|"mana"|"warehouse",
         "reason": str,
         "surplus_disposition_id": str|None}
    """
    qty = surplus_quantity if surplus_quantity is not None else position.quantity
    color = position.color or ""
    size = position.size or ""
    is_base = _check_is_base_color(db, color)
    sqm = _get_position_sqm(position)

    disposition_type = None
    reason = ""

    if size == "10x10":
        if is_base:
            disposition_type = SurplusDispositionType.SHOWROOM
            reason = f"Base color ({color}) 10x10 -> showroom display board"
        else:
            disposition_type = SurplusDispositionType.CASTERS
            reason = f"Non-base color ({color}) 10x10 -> coaster box"
    else:
        # Non-10x10 tiles
        if is_base and qty >= 10:
            disposition_type = SurplusDispositionType.SHOWROOM
            reason = f"Base color ({color}) {size}, {qty} pcs -> showroom priority"
        elif sqm < SMALL_BATCH_SQM_THRESHOLD:
            disposition_type = SurplusDispositionType.CASTERS
            reason = f"Small batch ({sqm:.2f} sqm < {SMALL_BATCH_SQM_THRESHOLD}) -> casters"
        else:
            disposition_type = SurplusDispositionType.MANA
            reason = f"Non-base color ({color}) {size}, {sqm:.2f} sqm -> mana shipment"

    logger.info(
        f"Surplus disposition for position {position.id}: "
        f"{disposition_type.value} — {reason}"
    )

    return {
        "disposition": disposition_type.value,
        "reason": reason,
        "is_base_color": is_base,
        "quantity": qty,
        "sqm": round(sqm, 4),
    }


def process_surplus_batch(
    db: Session,
    positions: list[OrderPosition],
    factory_id: UUID,
) -> dict:
    """
    Process a batch of surplus positions and assign dispositions.

    For each position, runs auto_assign_surplus_disposition() and creates
    the appropriate SurplusDisposition record + routing tasks.

    Args:
        db: Database session
        positions: List of OrderPosition objects with surplus
        factory_id: Factory UUID

    Returns:
        {
            "processed": int,
            "by_disposition": {"showroom": N, "casters": N, "mana": N},
            "details": [{"position_id": ..., "disposition": ..., "reason": ...}, ...]
        }
    """
    from business.services.sorting_split import handle_surplus as _handle_surplus

    results = []
    by_disposition = {"showroom": 0, "casters": 0, "mana": 0}

    for position in positions:
        try:
            # Use auto_assign to determine the disposition
            decision = auto_assign_surplus_disposition(db, position)
            disposition_type = decision["disposition"]

            # Delegate to the existing handle_surplus() which creates DB records,
            # tasks, and accumulation entries
            surplus_record = _handle_surplus(db, position, position.quantity)

            by_disposition[disposition_type] = by_disposition.get(disposition_type, 0) + 1

            results.append({
                "position_id": str(position.id),
                "disposition": disposition_type,
                "reason": decision["reason"],
                "surplus_disposition_id": str(surplus_record.id) if surplus_record else None,
            })

        except Exception as e:
            logger.error(f"Failed to process surplus for position {position.id}: {e}")
            results.append({
                "position_id": str(position.id),
                "disposition": "error",
                "reason": str(e),
                "surplus_disposition_id": None,
            })

    db.flush()

    return {
        "processed": len(positions),
        "by_disposition": by_disposition,
        "details": results,
    }


def get_surplus_summary(db: Session, factory_id: UUID) -> dict:
    """
    Summary of surplus inventory for a factory.

    Returns:
        {
            "factory_id": str,
            "total_surplus_quantity": int,
            "total_surplus_sqm": float,
            "by_disposition": {
                "showroom": {"count": N, "total_qty": N},
                "casters": {"count": N, "total_qty": N},
                "mana": {"count": N, "total_qty": N},
            },
            "pending_decisions": int,
            "recent_surplus": [...last 10 entries...],
        }
    """
    # Aggregate surplus dispositions by type
    disposition_stats = (
        db.query(
            SurplusDisposition.disposition_type,
            func.count(SurplusDisposition.id).label("count"),
            func.sum(SurplusDisposition.surplus_quantity).label("total_qty"),
        )
        .filter(SurplusDisposition.factory_id == factory_id)
        .group_by(SurplusDisposition.disposition_type)
        .all()
    )

    by_disposition = {}
    total_qty = 0
    for row in disposition_stats:
        dtype = row.disposition_type.value if hasattr(row.disposition_type, "value") else str(row.disposition_type)
        qty = int(row.total_qty or 0)
        by_disposition[dtype] = {
            "count": row.count,
            "total_qty": qty,
        }
        total_qty += qty

    # Count pending PM decision tasks related to surplus
    pending_decisions = db.query(func.count(Task.id)).filter(
        Task.factory_id == factory_id,
        Task.type.in_([TaskType.SHOWROOM_TRANSFER, TaskType.MANA_CONFIRMATION]),
        Task.status.notin_(["done", "cancelled"]),
    ).scalar() or 0

    # Pending casters boxes
    casters_total = db.query(func.sum(CastersBox.quantity)).filter(
        CastersBox.factory_id == factory_id,
        CastersBox.removed_at.is_(None),
    ).scalar() or 0

    # Pending mana shipment items
    pending_mana = db.query(ManaShipment).filter(
        ManaShipment.factory_id == factory_id,
        ManaShipment.status == ManaShipmentStatus.PENDING,
    ).first()
    mana_pending_qty = 0
    if pending_mana and pending_mana.items_json:
        mana_pending_qty = sum(
            item.get("quantity", 0)
            for item in pending_mana.items_json
            if isinstance(item, dict)
        )

    # Recent surplus entries (last 10)
    recent = (
        db.query(SurplusDisposition)
        .filter(SurplusDisposition.factory_id == factory_id)
        .order_by(SurplusDisposition.created_at.desc())
        .limit(10)
        .all()
    )
    recent_items = []
    for sd in recent:
        recent_items.append({
            "id": str(sd.id),
            "color": sd.color,
            "size": sd.size,
            "surplus_quantity": sd.surplus_quantity,
            "disposition_type": sd.disposition_type.value if sd.disposition_type else None,
            "is_base_color": sd.is_base_color,
            "created_at": sd.created_at.isoformat() if sd.created_at else None,
        })

    return {
        "factory_id": str(factory_id),
        "total_surplus_quantity": total_qty,
        "by_disposition": by_disposition,
        "pending_decisions": pending_decisions,
        "casters_box_total": int(casters_total),
        "mana_pending_quantity": mana_pending_qty,
        "recent_surplus": recent_items,
    }
