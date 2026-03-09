"""Financial entries router — CRUD + summary endpoint.
See API_CONTRACTS.md for full specification.
"""

from uuid import UUID
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func

from api.database import get_db
from api.auth import get_current_user
from api.roles import require_role
from api.models import FinancialEntry, OrderFinancial, ProductionOrder
from api.schemas import FinancialEntryCreate, FinancialEntryUpdate, FinancialEntryResponse
from api.enums import ExpenseType, ExpenseCategory, OrderStatus

router = APIRouter()

# Role guards
_require_read = require_role("owner", "ceo")
_require_write = require_role("owner")


@router.get("/summary")
async def financial_summary(
    factory_id: UUID | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(_require_read),
):
    """Financial summary: OPEX/CAPEX totals, revenue, margin, cost per sqm."""
    d_from = date.fromisoformat(date_from) if date_from else date.today() - timedelta(days=30)
    d_to = date.fromisoformat(date_to) if date_to else date.today()

    # OPEX total
    opex_q = db.query(sa_func.sum(FinancialEntry.amount)).filter(
        FinancialEntry.entry_type == ExpenseType.OPEX.value,
        FinancialEntry.entry_date >= d_from,
        FinancialEntry.entry_date <= d_to,
    )
    if factory_id:
        opex_q = opex_q.filter(FinancialEntry.factory_id == factory_id)
    opex_total = float(opex_q.scalar() or 0)

    # CAPEX total
    capex_q = db.query(sa_func.sum(FinancialEntry.amount)).filter(
        FinancialEntry.entry_type == ExpenseType.CAPEX.value,
        FinancialEntry.entry_date >= d_from,
        FinancialEntry.entry_date <= d_to,
    )
    if factory_id:
        capex_q = capex_q.filter(FinancialEntry.factory_id == factory_id)
    capex_total = float(capex_q.scalar() or 0)

    # Breakdown by category
    breakdown_q = db.query(
        FinancialEntry.entry_type,
        FinancialEntry.category,
        sa_func.sum(FinancialEntry.amount).label("total"),
    ).filter(
        FinancialEntry.entry_date >= d_from,
        FinancialEntry.entry_date <= d_to,
    )
    if factory_id:
        breakdown_q = breakdown_q.filter(FinancialEntry.factory_id == factory_id)
    breakdown_q = breakdown_q.group_by(FinancialEntry.entry_type, FinancialEntry.category)

    breakdown = []
    for row in breakdown_q.all():
        breakdown.append({
            "entry_type": row.entry_type if isinstance(row.entry_type, str) else row.entry_type.value,
            "category": row.category if isinstance(row.category, str) else row.category.value,
            "total": float(row.total or 0),
        })

    # Revenue from shipped orders
    revenue_q = db.query(sa_func.sum(OrderFinancial.total_price)).join(
        ProductionOrder
    ).filter(
        ProductionOrder.shipped_at.isnot(None),
        sa_func.date(ProductionOrder.shipped_at) >= d_from,
        sa_func.date(ProductionOrder.shipped_at) <= d_to,
    )
    if factory_id:
        revenue_q = revenue_q.filter(ProductionOrder.factory_id == factory_id)
    revenue = float(revenue_q.scalar() or 0)

    # Margin
    total_expenses = opex_total + capex_total
    margin = revenue - total_expenses
    margin_percent = (margin / revenue * 100) if revenue > 0 else 0

    # Cost per sqm
    from api.models import TpsShiftMetric
    output_q = db.query(sa_func.sum(TpsShiftMetric.actual_output)).filter(
        TpsShiftMetric.date >= d_from,
        TpsShiftMetric.date <= d_to,
    )
    if factory_id:
        output_q = output_q.filter(TpsShiftMetric.factory_id == factory_id)
    output_sqm = float(output_q.scalar() or 0)
    cost_per_sqm = round(opex_total / output_sqm, 2) if output_sqm > 0 else 0

    return {
        "period": {"from": str(d_from), "to": str(d_to)},
        "opex_total": round(opex_total, 2),
        "capex_total": round(capex_total, 2),
        "revenue": round(revenue, 2),
        "margin": round(margin, 2),
        "margin_percent": round(margin_percent, 1),
        "cost_per_sqm": cost_per_sqm,
        "output_sqm": round(output_sqm, 2),
        "breakdown": breakdown,
    }


@router.get("", response_model=dict)
async def list_financials(
    factory_id: UUID | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(_require_read),
):
    query = db.query(FinancialEntry).order_by(FinancialEntry.entry_date.desc())
    if factory_id:
        query = query.filter(FinancialEntry.factory_id == factory_id)
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return {"items": items, "total": total, "page": page, "per_page": per_page}


@router.get("/{item_id}", response_model=FinancialEntryResponse)
async def get_financials_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(_require_read),
):
    item = db.query(FinancialEntry).filter(FinancialEntry.id == item_id).first()
    if not item:
        raise HTTPException(404, "FinancialEntry not found")
    return item


@router.post("", response_model=FinancialEntryResponse, status_code=201)
async def create_financials_item(
    data: FinancialEntryCreate,
    db: Session = Depends(get_db),
    current_user=Depends(_require_write),
):
    item = FinancialEntry(**data.model_dump(), created_by=current_user.id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=FinancialEntryResponse)
async def update_financials_item(
    item_id: UUID,
    data: FinancialEntryUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(_require_write),
):
    item = db.query(FinancialEntry).filter(FinancialEntry.id == item_id).first()
    if not item:
        raise HTTPException(404, "FinancialEntry not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
async def delete_financials_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(_require_write),
):
    item = db.query(FinancialEntry).filter(FinancialEntry.id == item_id).first()
    if not item:
        raise HTTPException(404, "FinancialEntry not found")
    db.delete(item)
    db.commit()
