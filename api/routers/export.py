"""Export router — PDF and Excel generation.
See API_CONTRACTS.md for full specification.

Uses openpyxl for Excel, reportlab for PDF.
Falls back to CSV/text if libraries not available.
"""

from uuid import UUID
from datetime import date, timedelta
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func

from api.database import get_db
from api.auth import get_current_user
from api.roles import require_management, require_owner
from api.models import (
    ProductionOrder, OrderPosition, ProductionOrderItem,
    FinancialEntry, OrderFinancial,
)
from api.enums import OrderStatus, PositionStatus, ExpenseType

router = APIRouter()


def _get_orders(db: Session, factory_id: UUID | None = None) -> list:
    """Get orders for export."""
    q = db.query(ProductionOrder).order_by(ProductionOrder.created_at.desc())
    if factory_id:
        q = q.filter(ProductionOrder.factory_id == factory_id)
    return q.limit(500).all()


@router.get("/orders/excel")
async def export_orders_excel(
    factory_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Export orders to Excel (XLSX)."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    except ImportError:
        raise HTTPException(500, "openpyxl not installed. Run: pip install openpyxl")

    orders = _get_orders(db, factory_id)

    wb = Workbook()
    ws = wb.active
    ws.title = "Orders"

    # Header styling
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="2B5797", end_color="2B5797", fill_type="solid")
    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    headers = [
        "Order #", "Client", "Factory", "Status",
        "Created", "Deadline", "Schedule Deadline",
        "Shipped", "Source",
    ]

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
        cell.border = thin_border

    for row, order in enumerate(orders, 2):
        ws.cell(row=row, column=1, value=order.order_number).border = thin_border
        ws.cell(row=row, column=2, value=order.client).border = thin_border
        ws.cell(row=row, column=3, value=order.factory.name if order.factory else "").border = thin_border
        status_val = order.status if isinstance(order.status, str) else order.status.value
        ws.cell(row=row, column=4, value=status_val).border = thin_border
        ws.cell(row=row, column=5, value=str(order.created_at.date()) if order.created_at else "").border = thin_border
        ws.cell(row=row, column=6, value=str(order.final_deadline) if order.final_deadline else "").border = thin_border
        ws.cell(row=row, column=7, value=str(order.schedule_deadline) if order.schedule_deadline else "").border = thin_border
        ws.cell(row=row, column=8, value=str(order.shipped_at.date()) if order.shipped_at else "").border = thin_border
        source_val = order.source if isinstance(order.source, str) else order.source.value
        ws.cell(row=row, column=9, value=source_val).border = thin_border

    # Auto-width
    for col in ws.columns:
        max_length = max(len(str(cell.value or "")) for cell in col)
        ws.column_dimensions[col[0].column_letter].width = min(max_length + 2, 40)

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=orders_{date.today()}.xlsx"},
    )


@router.get("/orders/pdf")
async def export_orders_pdf(
    factory_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Export orders to PDF."""
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    except ImportError:
        raise HTTPException(500, "reportlab not installed. Run: pip install reportlab")

    orders = _get_orders(db, factory_id)

    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph(f"Orders Report — {date.today()}", styles["Title"]))
    elements.append(Spacer(1, 12))

    # Table data
    data = [["Order #", "Client", "Status", "Deadline", "Shipped"]]
    for order in orders:
        status_val = order.status if isinstance(order.status, str) else order.status.value
        data.append([
            order.order_number,
            (order.client or "")[:30],
            status_val,
            str(order.final_deadline) if order.final_deadline else "",
            str(order.shipped_at.date()) if order.shipped_at else "",
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2B5797")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F2F2")]),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(table)
    doc.build(elements)

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=orders_{date.today()}.pdf"},
    )


@router.get("/positions/pdf")
async def export_positions_pdf(
    order_id: UUID | None = None,
    factory_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Export positions to PDF."""
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    except ImportError:
        raise HTTPException(500, "reportlab not installed. Run: pip install reportlab")

    q = db.query(OrderPosition).join(ProductionOrder)
    if order_id:
        q = q.filter(OrderPosition.order_id == order_id)
    if factory_id:
        q = q.filter(OrderPosition.factory_id == factory_id)
    positions = q.order_by(OrderPosition.created_at.desc()).limit(500).all()

    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    elements = []

    title = f"Positions Report — {date.today()}"
    if order_id:
        order = db.query(ProductionOrder).get(order_id)
        if order:
            title = f"Positions for Order {order.order_number}"

    elements.append(Paragraph(title, styles["Title"]))
    elements.append(Spacer(1, 12))

    data = [["Order #", "Color", "Size", "Qty", "SQM", "Status", "Batch"]]
    for p in positions:
        status_val = p.status if isinstance(p.status, str) else p.status.value
        data.append([
            p.order.order_number if p.order else "",
            p.color,
            p.size,
            str(p.quantity),
            f"{float(p.quantity_sqm or 0):.2f}",
            status_val,
            str(p.batch_id)[:8] if p.batch_id else "",
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2B5797")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F2F2")]),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(table)
    doc.build(elements)

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=positions_{date.today()}.pdf"},
    )


@router.post("/owner-monthly")
async def owner_monthly_report(
    factory_id: UUID | None = None,
    month: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_owner),
):
    """Owner monthly report with KPIs + financial summary."""
    from business.services.daily_kpi import calculate_dashboard_summary

    if month:
        year, m = int(month[:4]), int(month[5:7])
        d_from = date(year, m, 1)
        if m == 12:
            d_to = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            d_to = date(year, m + 1, 1) - timedelta(days=1)
    else:
        d_to = date.today()
        d_from = d_to.replace(day=1)

    summary = calculate_dashboard_summary(db, factory_id, d_from, d_to)

    # Financial breakdown
    financial_q = db.query(
        FinancialEntry.entry_type,
        FinancialEntry.category,
        sa_func.sum(FinancialEntry.amount).label("total"),
    ).filter(
        FinancialEntry.entry_date >= d_from,
        FinancialEntry.entry_date <= d_to,
    )
    if factory_id:
        financial_q = financial_q.filter(FinancialEntry.factory_id == factory_id)
    financial_q = financial_q.group_by(FinancialEntry.entry_type, FinancialEntry.category)

    financials = {}
    for row in financial_q.all():
        entry_type = row.entry_type if isinstance(row.entry_type, str) else row.entry_type.value
        category = row.category if isinstance(row.category, str) else row.category.value
        if entry_type not in financials:
            financials[entry_type] = {}
        financials[entry_type][category] = float(row.total or 0)

    # Revenue from shipped orders
    revenue_q = db.query(
        sa_func.sum(OrderFinancial.total_price)
    ).join(ProductionOrder).filter(
        ProductionOrder.shipped_at.isnot(None),
        sa_func.date(ProductionOrder.shipped_at) >= d_from,
        sa_func.date(ProductionOrder.shipped_at) <= d_to,
    )
    if factory_id:
        revenue_q = revenue_q.filter(ProductionOrder.factory_id == factory_id)
    revenue = float(revenue_q.scalar() or 0)

    return {
        "period": {"from": str(d_from), "to": str(d_to)},
        "kpi": summary,
        "financial_breakdown": financials,
        "revenue": revenue,
    }


@router.post("/ceo-daily")
async def ceo_daily_report(
    factory_id: UUID | None = None,
    report_date: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """CEO daily summary report."""
    from business.services.daily_kpi import (
        calculate_dashboard_summary,
        calculate_production_metrics,
        calculate_material_metrics,
        get_activity_feed,
    )

    d = date.fromisoformat(report_date) if report_date else date.today()
    d_from = d
    d_to = d

    summary = calculate_dashboard_summary(db, factory_id, d_from, d_to)
    production = calculate_production_metrics(db, factory_id, d_from, d_to)
    materials = calculate_material_metrics(db, factory_id)
    activity = get_activity_feed(db, factory_id, limit=20)

    return {
        "date": str(d),
        "kpi": summary,
        "production": production,
        "material_deficits": materials,
        "recent_activity": activity,
    }
