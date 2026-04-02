"""
Stone Reservation service.
Stone is tracked separately from BOM materials.
Decision 2026-03-19.

Stone is a raw material (slabs/blocks) consumed per position.
The amount reserved accounts for:
  - geometry (sqm based on shape / size)
  - defect margin (stone_defect_pct) → extra stone needed beyond the net area
  - quantity (number of pieces)

Lifecycle:
  1. reserve_stone_for_position()   — called on position creation / re-reservation
  2. reconcile_stone_after_firing() — called after firing result is known
  3. get_weekly_stone_waste_report() — reporting
"""
import logging
from datetime import date, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger("moonjar.stone_reservation")


# ──────────────────────────────────────────────────────────────────
# Size category helper
# ──────────────────────────────────────────────────────────────────

def get_size_category(width_mm: float, height_mm: float) -> str:
    """Classify tile/product size into small/medium/large based on max dimension (mm)."""
    max_dim = max(width_mm or 0, height_mm or 0)
    if max_dim <= 300:
        return "small"
    elif max_dim <= 600:
        return "medium"
    else:
        return "large"


def _size_category_from_position(position) -> str:
    """Derive size_category from a position's dimensions.

    Priority:
    1. length_cm / width_cm (stored in cm → convert to mm)
    2. size string "WxH" parsing (cm)
    3. fallback to 'medium'
    """
    length_cm = getattr(position, "length_cm", None)
    width_cm = getattr(position, "width_cm", None)

    if length_cm and width_cm and float(length_cm) > 0 and float(width_cm) > 0:
        return get_size_category(float(width_cm) * 10, float(length_cm) * 10)

    size = getattr(position, "size", None)
    if size:
        import re
        m = re.match(r"(\d+)\s*[x×X]\s*(\d+)", str(size))
        if m:
            w_cm = float(m.group(1))
            h_cm = float(m.group(2))
            return get_size_category(w_cm * 10, h_cm * 10)

    return "medium"


def _product_type_str(position) -> str:
    """Get product_type as a plain string (handles both Enum and str)."""
    pt = getattr(position, "product_type", None)
    if pt is None:
        return "tile"
    return pt.value if hasattr(pt, "value") else str(pt)


# ──────────────────────────────────────────────────────────────────
# Hardcoded defaults (used when DB has no matching row)
# ──────────────────────────────────────────────────────────────────

STONE_DEFECT_DEFAULTS: dict[tuple[str, str], float] = {
    ("small",  "tile"):        0.02,
    ("medium", "tile"):        0.03,
    ("large",  "tile"):        0.05,
    ("any",    "countertop"):  0.04,
    ("any",    "sink"):        0.06,
    ("any",    "3d"):          0.08,
}


# ──────────────────────────────────────────────────────────────────
# §1  Defect rate lookup
# ──────────────────────────────────────────────────────────────────

def get_stone_defect_rate(
    db: Session,
    factory_id: UUID,
    size_category: str,
    product_type: str,
) -> float:
    """Get stone defect rate for size_category + product_type.

    Lookup priority:
    1. factory-specific exact match (factory_id + size_category + product_type)
    2. factory-specific 'any' size_category match
    3. global (factory_id IS NULL) exact match
    4. global 'any' size_category match
    5. hardcoded STONE_DEFECT_DEFAULTS

    Returns defect rate as a fraction (e.g. 0.05 = 5%).
    """
    from api.models import StoneDefectRate

    pt = product_type.lower().strip()
    sc = size_category.lower().strip()

    try:
        # 1. Factory-specific exact
        row = db.query(StoneDefectRate).filter(
            StoneDefectRate.factory_id == factory_id,
            StoneDefectRate.size_category == sc,
            StoneDefectRate.product_type == pt,
        ).first()
        if row:
            return float(row.defect_pct)

        # 2. Factory-specific 'any' size_category
        row = db.query(StoneDefectRate).filter(
            StoneDefectRate.factory_id == factory_id,
            StoneDefectRate.size_category == 'any',
            StoneDefectRate.product_type == pt,
        ).first()
        if row:
            return float(row.defect_pct)

        # 3. Global (factory_id IS NULL) exact
        row = db.query(StoneDefectRate).filter(
            StoneDefectRate.factory_id.is_(None),
            StoneDefectRate.size_category == sc,
            StoneDefectRate.product_type == pt,
        ).first()
        if row:
            return float(row.defect_pct)

        # 4. Global 'any' size_category
        row = db.query(StoneDefectRate).filter(
            StoneDefectRate.factory_id.is_(None),
            StoneDefectRate.size_category == 'any',
            StoneDefectRate.product_type == pt,
        ).first()
        if row:
            return float(row.defect_pct)

    except Exception as e:
        logger.warning("stone_defect_rate DB lookup failed: %s", e)

    # 5. Hardcoded fallback
    return STONE_DEFECT_DEFAULTS.get(
        (sc, pt),
        STONE_DEFECT_DEFAULTS.get(("any", pt), 0.04),
    )


# ──────────────────────────────────────────────────────────────────
# §2  Area helpers
# ──────────────────────────────────────────────────────────────────

def _get_net_sqm_per_piece(position) -> float:
    """Return net stone area required per piece (m²), no defect margin.

    Priority:
    1. glazeable_sqm (exact, shape-aware, already calculated)
    2. quantity_sqm / quantity (bounding-box total ÷ pieces)
    3. Parse size string "WxH cm" → bounding box
    4. fallback 0.0
    """
    glazeable = getattr(position, "glazeable_sqm", None)
    if glazeable and float(glazeable) > 0:
        return float(glazeable)

    qty_sqm = getattr(position, "quantity_sqm", None)
    qty = getattr(position, "quantity", None) or 1
    if qty_sqm and float(qty_sqm) > 0:
        return float(qty_sqm) / int(qty)

    size = getattr(position, "size", None)
    if size:
        import re
        m = re.match(r"(\d+)\s*[x×X]\s*(\d+)", str(size))
        if m:
            w_cm = float(m.group(1))
            h_cm = float(m.group(2))
            return (w_cm * h_cm) / 10000.0

    return 0.0


def _calculate_reserved_sqm(position, defect_pct: float) -> float:
    """Calculate total stone area to reserve (m²) including defect margin.

    Formula: reserved_sqm = net_sqm_per_piece × quantity × (1 + defect_pct)
    """
    net_per_piece = _get_net_sqm_per_piece(position)
    qty = int(getattr(position, "quantity", 1) or 1)
    return round(net_per_piece * qty * (1 + defect_pct), 3)


# ──────────────────────────────────────────────────────────────────
# §3  Reserve stone for a position
# ──────────────────────────────────────────────────────────────────

def reserve_stone_for_position(
    db: Session,
    position,
    auto_commit: bool = True,
) -> Optional[dict]:
    """Create (or replace) stone reservation for a position.

    - Cancels any existing 'active' reservation for this position first.
    - Creates a new stone_reservations row.
    - Returns dict with reservation details, or None if net area is 0.

    Args:
        db:          SQLAlchemy session
        position:    OrderPosition ORM object (must have id, factory_id, quantity, etc.)
        auto_commit: If True (default), commit within this function.
                     Set to False when called from a pipeline that manages
                     its own transaction (e.g. order_intake).

    Returns:
        {
            "reservation_id": str,
            "size_category": str,
            "product_type": str,
            "reserved_qty": int,
            "reserved_sqm": float,
            "stone_defect_pct": float,
        }
        or None if calculation yields 0 sqm (no dimensions available).
    """
    position_id = str(position.id)
    factory_id = str(position.factory_id)
    size_category = _size_category_from_position(position)
    product_type = _product_type_str(position)
    quantity = int(getattr(position, "quantity", 1) or 1)

    defect_pct = get_stone_defect_rate(
        db,
        factory_id=position.factory_id,
        size_category=size_category,
        product_type=product_type,
    )

    reserved_sqm = _calculate_reserved_sqm(position, defect_pct)

    if reserved_sqm <= 0:
        logger.warning(
            "reserve_stone | position=%s | reserved_sqm=0 — no dimensions, skipping",
            position_id,
        )
        return None

    # Cancel existing active reservations for this position
    try:
        db.execute(text("""
            UPDATE stone_reservations
            SET status = 'cancelled'
            WHERE position_id = :pid AND status = 'active'
        """), {"pid": position_id})
    except Exception as e:
        logger.warning("reserve_stone | cancel existing failed: %s", e)

    # Insert new reservation
    row = db.execute(text("""
        INSERT INTO stone_reservations
            (position_id, factory_id, size_category, product_type,
             reserved_qty, reserved_sqm, stone_defect_pct, status)
        VALUES
            (:pid, :fid, :sc, :pt, :qty, :sqm, :pct, 'active')
        RETURNING id
    """), {
        "pid": position_id,
        "fid": factory_id,
        "sc": size_category,
        "pt": product_type,
        "qty": quantity,
        "sqm": reserved_sqm,
        "pct": defect_pct,
    }).fetchone()

    if auto_commit:
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise
    else:
        db.flush()

    reservation_id = str(row[0])

    logger.info(
        "STONE_RESERVED | position=%s | reservation=%s | %s/%s | qty=%d | sqm=%.3f | defect=%.2f%%",
        position_id, reservation_id, size_category, product_type,
        quantity, reserved_sqm, defect_pct * 100,
    )

    return {
        "reservation_id": reservation_id,
        "size_category": size_category,
        "product_type": product_type,
        "reserved_qty": quantity,
        "reserved_sqm": reserved_sqm,
        "stone_defect_pct": defect_pct,
    }


# ──────────────────────────────────────────────────────────────────
# §4  Reconcile after firing
# ──────────────────────────────────────────────────────────────────

def reconcile_stone_after_firing(
    db: Session,
    position,
    actual_good_qty: int,
    reconciled_by_id: Optional[UUID] = None,
) -> dict:
    """Called after firing result is known. Compare actual vs reserved stone.

    Logic:
    - actual_sqm = actual_good_qty × net_sqm_per_piece
    - If actual_sqm < reserved_sqm → excess stone → log as 'return'
    - If actual_sqm > reserved_sqm → overage → log as 'writeoff'
    - If equal → 'exact'

    Note: no physical stock update for now — only adjustment log entries.

    Args:
        db:                 SQLAlchemy session
        position:           OrderPosition ORM object
        actual_good_qty:    number of good pieces after firing
        reconciled_by_id:   UUID of user performing reconciliation (optional)

    Returns:
        {
            "action": "return" | "writeoff" | "exact",
            "qty_sqm": float,          # absolute delta (always positive)
            "reservation_id": str,
            "reserved_sqm": float,
            "actual_sqm": float,
        }
    """
    position_id = str(position.id)
    by_id = str(reconciled_by_id) if reconciled_by_id else None

    # Find active reservation
    res_row = db.execute(text("""
        SELECT id, reserved_sqm, stone_defect_pct
        FROM stone_reservations
        WHERE position_id = :pid AND status = 'active'
        ORDER BY created_at DESC
        LIMIT 1
    """), {"pid": position_id}).fetchone()

    if not res_row:
        logger.warning("reconcile_stone | no active reservation for position=%s", position_id)
        return {
            "action": "exact",
            "qty_sqm": 0.0,
            "reservation_id": None,
            "reserved_sqm": 0.0,
            "actual_sqm": 0.0,
        }

    reservation_id = str(res_row[0])
    reserved_sqm = float(res_row[1])

    net_per_piece = _get_net_sqm_per_piece(position)
    actual_sqm = round(net_per_piece * int(actual_good_qty), 3)

    delta = round(reserved_sqm - actual_sqm, 3)

    if abs(delta) < 0.001:
        action = "exact"
        adj_sqm = 0.0
    elif delta > 0:
        # Reserved more than used → return
        action = "return"
        adj_sqm = delta
    else:
        # Used more than reserved → writeoff
        action = "writeoff"
        adj_sqm = abs(delta)

    # Log adjustment if there's a real difference
    if action != "exact":
        reason = (
            f"Post-firing reconciliation: actual_good_qty={actual_good_qty}, "
            f"actual_sqm={actual_sqm:.3f}, reserved_sqm={reserved_sqm:.3f}"
        )
        try:
            db.execute(text("""
                INSERT INTO stone_reservation_adjustments
                    (reservation_id, type, qty_sqm, reason, created_by)
                VALUES (:rid, :atype, :sqm, :reason, :by_id)
            """), {
                "rid": reservation_id,
                "atype": action,
                "sqm": adj_sqm,
                "reason": reason,
                "by_id": by_id,
            })
        except Exception as e:
            logger.error("reconcile_stone | adjustment insert failed: %s", e)

    # Mark reservation as reconciled
    try:
        db.execute(text("""
            UPDATE stone_reservations
            SET status = 'reconciled', reconciled_at = NOW()
            WHERE id = :rid
        """), {"rid": reservation_id})
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("reconcile_stone | update reservation failed: %s", e)

    logger.info(
        "STONE_RECONCILED | position=%s | reservation=%s | action=%s | delta_sqm=%.3f",
        position_id, reservation_id, action, adj_sqm,
    )

    return {
        "action": action,
        "qty_sqm": adj_sqm,
        "reservation_id": reservation_id,
        "reserved_sqm": reserved_sqm,
        "actual_sqm": actual_sqm,
    }


# ──────────────────────────────────────────────────────────────────
# §5  Weekly stone waste report
# ──────────────────────────────────────────────────────────────────

def get_weekly_stone_waste_report(
    db: Session,
    factory_id: UUID,
    week_offset: int = 0,
) -> dict:
    """Generate weekly stone waste summary.

    week_offset=0 → current ISO week, 1 → last week, etc.

    Returns:
        {
            "factory_id": str,
            "week_start": str (ISO date),
            "week_end": str (ISO date),
            "total_reserved_sqm": float,
            "total_actual_sqm": float,
            "total_writeoff_sqm": float,
            "total_return_sqm": float,
            "net_waste_sqm": float,          # writeoff - return (positive = wasted extra)
            "waste_pct": float,              # net_waste / total_reserved * 100
            "reservations_count": int,
            "reconciled_count": int,
            "by_product_type": [
                {
                    "product_type": str,
                    "reserved_sqm": float,
                    "writeoff_sqm": float,
                    "return_sqm": float,
                    "net_waste_sqm": float,
                }
            ],
        }
    """
    today = date.today()
    # ISO week: Monday = start
    week_start = today - timedelta(days=today.weekday()) - timedelta(weeks=week_offset)
    week_end = week_start + timedelta(days=6)

    fid = str(factory_id)
    ws = week_start.isoformat()
    we = (week_end + timedelta(days=1)).isoformat()  # exclusive upper bound

    # Overall stats from stone_reservations created in this week
    try:
        summary = db.execute(text("""
            SELECT
                COUNT(*)                           AS reservations_count,
                COALESCE(SUM(reserved_sqm), 0)    AS total_reserved_sqm,
                COUNT(*) FILTER (WHERE status = 'reconciled') AS reconciled_count
            FROM stone_reservations
            WHERE factory_id = :fid
              AND created_at >= :ws
              AND created_at < :we
        """), {"fid": fid, "ws": ws, "we": we}).fetchone()
    except Exception as e:
        logger.error("weekly_stone_report | summary query failed: %s", e)
        summary = None

    reservations_count = int(summary[0]) if summary else 0
    total_reserved_sqm = float(summary[1]) if summary else 0.0
    reconciled_count = int(summary[2]) if summary else 0

    # Adjustment totals from this week's reservations
    try:
        adj = db.execute(text("""
            SELECT
                COALESCE(SUM(a.qty_sqm) FILTER (WHERE a.type = 'writeoff'), 0) AS writeoff_sqm,
                COALESCE(SUM(a.qty_sqm) FILTER (WHERE a.type = 'return'),   0) AS return_sqm
            FROM stone_reservation_adjustments a
            JOIN stone_reservations r ON r.id = a.reservation_id
            WHERE r.factory_id = :fid
              AND r.created_at >= :ws
              AND r.created_at < :we
        """), {"fid": fid, "ws": ws, "we": we}).fetchone()
    except Exception as e:
        logger.error("weekly_stone_report | adjustment query failed: %s", e)
        adj = None

    total_writeoff_sqm = float(adj[0]) if adj else 0.0
    total_return_sqm = float(adj[1]) if adj else 0.0

    # Derive actual consumed sqm:
    # total_actual = total_reserved - total_return + total_writeoff
    # But simpler: total_actual = total_reserved - net_return_delta
    # net_waste = writeoff - return  (positive = wasted more than the defect margin)
    net_waste_sqm = round(total_writeoff_sqm - total_return_sqm, 3)
    total_actual_sqm = round(total_reserved_sqm - total_return_sqm + total_writeoff_sqm, 3)
    waste_pct = (
        round(net_waste_sqm / total_reserved_sqm * 100, 2)
        if total_reserved_sqm > 0
        else 0.0
    )

    # Per-product-type breakdown
    try:
        pt_rows = db.execute(text("""
            SELECT
                r.product_type,
                COALESCE(SUM(r.reserved_sqm), 0)                                        AS reserved_sqm,
                COALESCE(SUM(a_wo.wo_sqm), 0)                                           AS writeoff_sqm,
                COALESCE(SUM(a_ret.ret_sqm), 0)                                         AS return_sqm
            FROM stone_reservations r
            LEFT JOIN LATERAL (
                SELECT COALESCE(SUM(qty_sqm), 0) AS wo_sqm
                FROM stone_reservation_adjustments
                WHERE reservation_id = r.id AND type = 'writeoff'
            ) a_wo ON true
            LEFT JOIN LATERAL (
                SELECT COALESCE(SUM(qty_sqm), 0) AS ret_sqm
                FROM stone_reservation_adjustments
                WHERE reservation_id = r.id AND type = 'return'
            ) a_ret ON true
            WHERE r.factory_id = :fid
              AND r.created_at >= :ws
              AND r.created_at < :we
            GROUP BY r.product_type
            ORDER BY reserved_sqm DESC
        """), {"fid": fid, "ws": ws, "we": we}).fetchall()
    except Exception as e:
        logger.error("weekly_stone_report | by_product_type query failed: %s", e)
        pt_rows = []

    by_product_type = []
    for row in pt_rows:
        pt_reserved = float(row[1])
        pt_writeoff = float(row[2])
        pt_return = float(row[3])
        by_product_type.append({
            "product_type": row[0],
            "reserved_sqm": pt_reserved,
            "writeoff_sqm": pt_writeoff,
            "return_sqm": pt_return,
            "net_waste_sqm": round(pt_writeoff - pt_return, 3),
        })

    return {
        "factory_id": fid,
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "total_reserved_sqm": total_reserved_sqm,
        "total_actual_sqm": total_actual_sqm,
        "total_writeoff_sqm": total_writeoff_sqm,
        "total_return_sqm": total_return_sqm,
        "net_waste_sqm": net_waste_sqm,
        "waste_pct": waste_pct,
        "reservations_count": reservations_count,
        "reconciled_count": reconciled_count,
        "by_product_type": by_product_type,
    }
