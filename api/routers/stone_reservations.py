"""
Stone Reservations router.
Stone is tracked separately from BOM materials (Decision 2026-03-19).
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from api.database import get_db
from api.roles import require_management
from business.services.stone_reservation import (
    get_stone_defect_rate,
    get_weekly_stone_waste_report,
)

logger = logging.getLogger("moonjar.routers.stone_reservations")

router = APIRouter(tags=["stone-reservations"])


# ──────────────────────────────────────────────────────────────────
# GET /stone-reservations
# ──────────────────────────────────────────────────────────────────

@router.get("")
def list_stone_reservations(
    factory_id: Optional[UUID] = Query(None, description="Filter by factory"),
    position_id: Optional[UUID] = Query(None, description="Filter by order position"),
    status: Optional[str] = Query(None, description="Filter by status: active|reconciled|cancelled"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """List stone reservations with optional filters.

    Returns paginated list of stone_reservations rows enriched with
    total adjustment sums.
    """
    conditions = []
    params: dict = {}

    if factory_id:
        conditions.append("r.factory_id = :factory_id")
        params["factory_id"] = str(factory_id)

    if position_id:
        conditions.append("r.position_id = :position_id")
        params["position_id"] = str(position_id)

    if status:
        conditions.append("r.status = :status")
        params["status"] = status

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    count_sql = text(f"""
        SELECT COUNT(*) FROM stone_reservations r
        {where_clause}
    """)
    total = db.execute(count_sql, params).scalar() or 0

    offset = (page - 1) * per_page
    params["limit"] = per_page
    params["offset"] = offset

    rows_sql = text(f"""
        SELECT
            r.id,
            r.position_id,
            r.factory_id,
            r.size_category,
            r.product_type,
            r.reserved_qty,
            r.reserved_sqm,
            r.stone_defect_pct,
            r.status,
            r.created_at,
            r.reconciled_at,
            COALESCE(wo.writeoff_sqm, 0)  AS total_writeoff_sqm,
            COALESCE(ret.return_sqm,  0)  AS total_return_sqm
        FROM stone_reservations r
        LEFT JOIN LATERAL (
            SELECT COALESCE(SUM(qty_sqm), 0) AS writeoff_sqm
            FROM stone_reservation_adjustments
            WHERE reservation_id = r.id AND type = 'writeoff'
        ) wo ON true
        LEFT JOIN LATERAL (
            SELECT COALESCE(SUM(qty_sqm), 0) AS return_sqm
            FROM stone_reservation_adjustments
            WHERE reservation_id = r.id AND type = 'return'
        ) ret ON true
        {where_clause}
        ORDER BY r.created_at DESC
        LIMIT :limit OFFSET :offset
    """)

    try:
        results = db.execute(rows_sql, params).fetchall()
    except Exception as e:
        logger.error("list_stone_reservations query failed: %s", e)
        raise HTTPException(status_code=500, detail="Database error listing stone reservations")

    items = [
        {
            "id": str(row[0]),
            "position_id": str(row[1]),
            "factory_id": str(row[2]),
            "size_category": row[3],
            "product_type": row[4],
            "reserved_qty": row[5],
            "reserved_sqm": float(row[6]),
            "stone_defect_pct": float(row[7]),
            "status": row[8],
            "created_at": row[9].isoformat() if row[9] else None,
            "reconciled_at": row[10].isoformat() if row[10] else None,
            "total_writeoff_sqm": float(row[11]),
            "total_return_sqm": float(row[12]),
        }
        for row in results
    ]

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": max(1, -(-int(total) // per_page)),  # ceil division
        "items": items,
    }


# ──────────────────────────────────────────────────────────────────
# GET /stone-reservations/{reservation_id}
# ──────────────────────────────────────────────────────────────────

@router.get("/{reservation_id}")
def get_stone_reservation(
    reservation_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Get a single stone reservation with its adjustment log."""
    rid = str(reservation_id)

    row = db.execute(text("""
        SELECT
            r.id, r.position_id, r.factory_id, r.size_category, r.product_type,
            r.reserved_qty, r.reserved_sqm, r.stone_defect_pct,
            r.status, r.created_at, r.reconciled_at
        FROM stone_reservations r
        WHERE r.id = :rid
        LIMIT 1
    """), {"rid": rid}).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Stone reservation not found")

    adjustments = db.execute(text("""
        SELECT id, type, qty_sqm, reason, created_at, created_by
        FROM stone_reservation_adjustments
        WHERE reservation_id = :rid
        ORDER BY created_at ASC
    """), {"rid": rid}).fetchall()

    adj_list = [
        {
            "id": str(a[0]),
            "type": a[1],
            "qty_sqm": float(a[2]),
            "reason": a[3],
            "created_at": a[4].isoformat() if a[4] else None,
            "created_by": str(a[5]) if a[5] else None,
        }
        for a in adjustments
    ]

    return {
        "id": str(row[0]),
        "position_id": str(row[1]),
        "factory_id": str(row[2]),
        "size_category": row[3],
        "product_type": row[4],
        "reserved_qty": row[5],
        "reserved_sqm": float(row[6]),
        "stone_defect_pct": float(row[7]),
        "status": row[8],
        "created_at": row[9].isoformat() if row[9] else None,
        "reconciled_at": row[10].isoformat() if row[10] else None,
        "adjustments": adj_list,
    }


# ──────────────────────────────────────────────────────────────────
# GET /stone-reservations/weekly-report
# ──────────────────────────────────────────────────────────────────

@router.get("/weekly-report")
def get_weekly_report(
    factory_id: UUID = Query(..., description="Factory UUID"),
    week_offset: int = Query(0, ge=0, le=52, description="0=current week, 1=last week, etc."),
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Weekly stone waste report.

    Returns reserved vs actual stone consumption summary for the given week,
    broken down by product type.
    """
    return get_weekly_stone_waste_report(db, factory_id, week_offset)


# ──────────────────────────────────────────────────────────────────
# GET /stone-reservations/defect-rates
# ──────────────────────────────────────────────────────────────────

@router.get("/defect-rates")
def get_defect_rates(
    factory_id: Optional[UUID] = Query(None, description="Factory UUID; omit for global rates"),
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Get stone defect rates configuration.

    Returns all defect rate rows visible to this factory:
    - factory-specific rows (if factory_id provided)
    - global rows (factory_id IS NULL)

    Factory-specific rows take precedence over global in the service layer.
    """
    try:
        if factory_id:
            rows = db.execute(text("""
                SELECT id, factory_id, size_category, product_type, defect_pct, updated_at, updated_by
                FROM stone_defect_rates
                WHERE factory_id = :fid OR factory_id IS NULL
                ORDER BY
                    CASE WHEN factory_id IS NOT NULL THEN 0 ELSE 1 END,
                    size_category, product_type
            """), {"fid": str(factory_id)}).fetchall()
        else:
            rows = db.execute(text("""
                SELECT id, factory_id, size_category, product_type, defect_pct, updated_at, updated_by
                FROM stone_defect_rates
                WHERE factory_id IS NULL
                ORDER BY size_category, product_type
            """)).fetchall()
    except Exception as e:
        logger.error("get_defect_rates failed: %s", e)
        raise HTTPException(status_code=500, detail="Database error fetching defect rates")

    return [
        {
            "id": str(r[0]),
            "factory_id": str(r[1]) if r[1] else None,
            "size_category": r[2],
            "product_type": r[3],
            "defect_pct": float(r[4]),
            "updated_at": r[5].isoformat() if r[5] else None,
            "updated_by": str(r[6]) if r[6] else None,
        }
        for r in rows
    ]


# ──────────────────────────────────────────────────────────────────
# PUT /stone-reservations/defect-rates
# ──────────────────────────────────────────────────────────────────

@router.put("/defect-rates")
def update_defect_rate(
    factory_id: Optional[UUID] = Body(None, description="Factory UUID; null = global default"),
    size_category: str = Body(..., description="small | medium | large | any"),
    product_type: str = Body(..., description="tile | countertop | sink | 3d"),
    defect_pct: float = Body(..., ge=0.0, le=1.0, description="Defect rate as fraction (0.0–1.0)"),
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Upsert stone defect rate for a size_category × product_type combination.

    Performs INSERT ... ON CONFLICT DO UPDATE (upsert) so it's safe to call
    multiple times. factory_id=null sets the global default.
    """
    valid_size_categories = {"small", "medium", "large", "any"}
    if size_category not in valid_size_categories:
        raise HTTPException(
            status_code=400,
            detail=f"size_category must be one of {sorted(valid_size_categories)}",
        )

    valid_product_types = {"tile", "countertop", "sink", "3d"}
    if product_type not in valid_product_types:
        raise HTTPException(
            status_code=400,
            detail=f"product_type must be one of {sorted(valid_product_types)}",
        )

    fid = str(factory_id) if factory_id else None
    by_id = str(current_user.id) if hasattr(current_user, "id") else None

    try:
        if fid:
            # Factory-specific upsert
            db.execute(text("""
                INSERT INTO stone_defect_rates
                    (factory_id, size_category, product_type, defect_pct, updated_at, updated_by)
                VALUES (:fid, :sc, :pt, :pct, NOW(), :by_id)
                ON CONFLICT (factory_id, size_category, product_type)
                DO UPDATE SET
                    defect_pct = EXCLUDED.defect_pct,
                    updated_at = NOW(),
                    updated_by = EXCLUDED.updated_by
            """), {"fid": fid, "sc": size_category, "pt": product_type, "pct": defect_pct, "by_id": by_id})
        else:
            # Global row — unique constraint on (factory_id IS NULL, sc, pt)
            # PostgreSQL UNIQUE treats NULLs as distinct, so use manual approach:
            existing = db.execute(text("""
                SELECT id FROM stone_defect_rates
                WHERE factory_id IS NULL AND size_category = :sc AND product_type = :pt
                LIMIT 1
            """), {"sc": size_category, "pt": product_type}).fetchone()

            if existing:
                db.execute(text("""
                    UPDATE stone_defect_rates
                    SET defect_pct = :pct, updated_at = NOW(), updated_by = :by_id
                    WHERE id = :rid
                """), {"pct": defect_pct, "by_id": by_id, "rid": str(existing[0])})
            else:
                db.execute(text("""
                    INSERT INTO stone_defect_rates
                        (factory_id, size_category, product_type, defect_pct, updated_at, updated_by)
                    VALUES (NULL, :sc, :pt, :pct, NOW(), :by_id)
                """), {"sc": size_category, "pt": product_type, "pct": defect_pct, "by_id": by_id})

        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("update_defect_rate failed: %s", e)
        raise HTTPException(status_code=500, detail="Database error updating defect rate")

    logger.info(
        "DEFECT_RATE_UPDATED | factory=%s | %s/%s | pct=%.4f | by=%s",
        fid, size_category, product_type, defect_pct, by_id,
    )

    return {
        "ok": True,
        "factory_id": fid,
        "size_category": size_category,
        "product_type": product_type,
        "defect_pct": defect_pct,
    }
