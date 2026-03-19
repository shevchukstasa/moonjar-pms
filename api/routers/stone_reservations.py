"""
Stone Reservations router.
Stone is tracked separately from BOM materials (Decision 2026-03-19).
"""
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import text, func, case

from api.database import get_db
from api.models import StoneReservation, StoneReservationAdjustment, StoneDefectRate
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
    query = db.query(StoneReservation)

    if factory_id:
        query = query.filter(StoneReservation.factory_id == factory_id)
    if position_id:
        query = query.filter(StoneReservation.position_id == position_id)
    if status:
        query = query.filter(StoneReservation.status == status)

    total = query.count()
    offset = (page - 1) * per_page

    try:
        reservations = (
            query
            .order_by(StoneReservation.created_at.desc())
            .offset(offset)
            .limit(per_page)
            .all()
        )
    except Exception as e:
        logger.error("list_stone_reservations query failed: %s", e)
        raise HTTPException(status_code=500, detail="Database error listing stone reservations")

    items = []
    for r in reservations:
        # Calculate adjustment totals from loaded relationship
        writeoff_sqm = 0.0
        return_sqm = 0.0
        for adj in (r.adjustments or []):
            val = float(adj.qty_sqm) if adj.qty_sqm else 0.0
            if adj.type == 'writeoff':
                writeoff_sqm += val
            elif adj.type == 'return':
                return_sqm += val

        items.append({
            "id": str(r.id),
            "position_id": str(r.position_id),
            "factory_id": str(r.factory_id),
            "size_category": r.size_category,
            "product_type": r.product_type,
            "reserved_qty": r.reserved_qty,
            "reserved_sqm": float(r.reserved_sqm),
            "stone_defect_pct": float(r.stone_defect_pct),
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "reconciled_at": r.reconciled_at.isoformat() if r.reconciled_at else None,
            "total_writeoff_sqm": round(writeoff_sqm, 3),
            "total_return_sqm": round(return_sqm, 3),
        })

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
    r = db.query(StoneReservation).filter(StoneReservation.id == reservation_id).first()

    if not r:
        raise HTTPException(status_code=404, detail="Stone reservation not found")

    adj_list = [
        {
            "id": str(a.id),
            "type": a.type,
            "qty_sqm": float(a.qty_sqm),
            "reason": a.reason,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "created_by": str(a.created_by) if a.created_by else None,
        }
        for a in sorted(r.adjustments or [], key=lambda x: x.created_at or datetime.min.replace(tzinfo=timezone.utc))
    ]

    return {
        "id": str(r.id),
        "position_id": str(r.position_id),
        "factory_id": str(r.factory_id),
        "size_category": r.size_category,
        "product_type": r.product_type,
        "reserved_qty": r.reserved_qty,
        "reserved_sqm": float(r.reserved_sqm),
        "stone_defect_pct": float(r.stone_defect_pct),
        "status": r.status,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "reconciled_at": r.reconciled_at.isoformat() if r.reconciled_at else None,
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
        query = db.query(StoneDefectRate)
        if factory_id:
            query = query.filter(
                (StoneDefectRate.factory_id == factory_id) | (StoneDefectRate.factory_id.is_(None))
            ).order_by(
                case((StoneDefectRate.factory_id.isnot(None), 0), else_=1),
                StoneDefectRate.size_category,
                StoneDefectRate.product_type,
            )
        else:
            query = query.filter(
                StoneDefectRate.factory_id.is_(None)
            ).order_by(
                StoneDefectRate.size_category,
                StoneDefectRate.product_type,
            )
        rows = query.all()
    except Exception as e:
        logger.error("get_defect_rates failed: %s", e)
        raise HTTPException(status_code=500, detail="Database error fetching defect rates")

    return [
        {
            "id": str(r.id),
            "factory_id": str(r.factory_id) if r.factory_id else None,
            "size_category": r.size_category,
            "product_type": r.product_type,
            "defect_pct": float(r.defect_pct),
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            "updated_by": str(r.updated_by) if r.updated_by else None,
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

    by_id = current_user.id if hasattr(current_user, "id") else None

    try:
        if factory_id:
            # Factory-specific: use ORM upsert approach
            existing = db.query(StoneDefectRate).filter(
                StoneDefectRate.factory_id == factory_id,
                StoneDefectRate.size_category == size_category,
                StoneDefectRate.product_type == product_type,
            ).first()

            if existing:
                existing.defect_pct = defect_pct
                existing.updated_at = datetime.now(timezone.utc)
                existing.updated_by = by_id
            else:
                db.add(StoneDefectRate(
                    factory_id=factory_id,
                    size_category=size_category,
                    product_type=product_type,
                    defect_pct=defect_pct,
                    updated_by=by_id,
                ))
        else:
            # Global row — factory_id IS NULL (PostgreSQL UNIQUE treats NULLs as distinct)
            existing = db.query(StoneDefectRate).filter(
                StoneDefectRate.factory_id.is_(None),
                StoneDefectRate.size_category == size_category,
                StoneDefectRate.product_type == product_type,
            ).first()

            if existing:
                existing.defect_pct = defect_pct
                existing.updated_at = datetime.now(timezone.utc)
                existing.updated_by = by_id
            else:
                db.add(StoneDefectRate(
                    factory_id=None,
                    size_category=size_category,
                    product_type=product_type,
                    defect_pct=defect_pct,
                    updated_by=by_id,
                ))

        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("update_defect_rate failed: %s", e)
        raise HTTPException(status_code=500, detail="Database error updating defect rate")

    fid_str = str(factory_id) if factory_id else None
    by_id_str = str(by_id) if by_id else None

    logger.info(
        "DEFECT_RATE_UPDATED | factory=%s | %s/%s | pct=%.4f | by=%s",
        fid_str, size_category, product_type, defect_pct, by_id_str,
    )

    return {
        "ok": True,
        "factory_id": fid_str,
        "size_category": size_category,
        "product_type": product_type,
        "defect_pct": defect_pct,
    }
