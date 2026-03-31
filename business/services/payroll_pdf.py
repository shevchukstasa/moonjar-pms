"""Payroll PDF generator — uses reportlab to produce landscape A4 payroll summary."""

from io import BytesIO
from datetime import datetime

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def _fmt_idr(value: float) -> str:
    """Format number as IDR without symbol."""
    try:
        v = int(round(value))
        return f"{v:,}".replace(",", ".")
    except Exception:
        return "0"


def generate_payroll_summary_pdf(
    payroll_items: list,
    totals: dict,
    year: int,
    month: int,
    factory_name: str = "",
) -> BytesIO:
    """Generate a landscape A4 payroll summary PDF.

    Returns a BytesIO buffer ready for streaming.
    """
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT

    buf = BytesIO()
    page = landscape(A4)
    doc = SimpleDocTemplate(
        buf,
        pagesize=page,
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "title", parent=styles["Heading1"], fontSize=13, alignment=TA_CENTER, spaceAfter=4
    )
    sub_style = ParagraphStyle(
        "sub", parent=styles["Normal"], fontSize=9, alignment=TA_CENTER, spaceAfter=8, textColor=colors.grey
    )
    small_right = ParagraphStyle(
        "small_right", parent=styles["Normal"], fontSize=7, alignment=TA_RIGHT
    )

    period_label = MONTH_NAMES[month - 1] if 1 <= month <= 12 else str(month)
    factory_label = f" — {factory_name}" if factory_name else ""
    generated_at = datetime.now().strftime("%d %b %Y %H:%M")

    elements = [
        Paragraph(f"Payroll Report{factory_label}", title_style),
        Paragraph(f"{period_label} {year}", sub_style),
        Paragraph(f"Generated: {generated_at}", small_right),
        Spacer(1, 4 * mm),
    ]

    # ── Table data ──────────────────────────────────────────────
    header = [
        "#", "Name", "Position", "Category", "Schedule",
        "Days\nPresent", "Days\nAbsent", "OT\nhrs",
        "Base\n(IDR)", "Allowances\n(IDR)", "OT Pay\n(IDR)",
        "Gross\n(IDR)", "BPJS\n(IDR)", "Tax\n(IDR)",
        "Net\n(IDR)",
    ]

    rows = [header]
    for idx, item in enumerate(payroll_items, 1):
        rows.append([
            str(idx),
            item.get("full_name", ""),
            item.get("position", ""),
            "F" if item.get("employment_category") == "formal" else "C",
            "6d" if item.get("work_schedule") == "six_day" else "5d",
            str(item.get("present_days", 0)),
            str(item.get("absent_days", 0)) if item.get("absent_days") else "-",
            str(round(item.get("overtime_hours", 0), 1)) if item.get("overtime_hours") else "-",
            _fmt_idr(item.get("prorated_salary", item.get("base_salary", 0))),
            _fmt_idr(item.get("prorated_allowances", item.get("total_allowances", 0))),
            _fmt_idr(item.get("overtime_pay", 0)) if item.get("overtime_pay") else "-",
            _fmt_idr(item.get("gross_salary", 0)),
            _fmt_idr(item.get("bpjs_employee", 0)) if item.get("bpjs_employee") else "-",
            _fmt_idr(item.get("pph21", 0) + item.get("contractor_tax", 0)) if (item.get("pph21") or item.get("contractor_tax")) else "-",
            _fmt_idr(item.get("net_salary", 0)),
        ])

    # Totals row
    rows.append([
        "", "TOTAL", "", "", "",
        str(totals.get("total_employees", 0)),
        "",
        "",
        "",
        "",
        _fmt_idr(totals.get("total_overtime_pay", 0)),
        _fmt_idr(totals.get("total_gross", 0)),
        _fmt_idr(totals.get("total_bpjs_employee", 0)),
        _fmt_idr(totals.get("total_pph21", 0) + totals.get("total_contractor_tax", 0)),
        _fmt_idr(totals.get("total_net", 0)),
    ])

    # Column widths (landscape A4 = ~277mm usable)
    col_widths = [
        8 * mm,   # #
        38 * mm,  # Name
        28 * mm,  # Position
        14 * mm,  # Category
        14 * mm,  # Schedule
        12 * mm,  # Days Present
        12 * mm,  # Days Absent
        10 * mm,  # OT hrs
        24 * mm,  # Base
        24 * mm,  # Allowances
        22 * mm,  # OT Pay
        24 * mm,  # Gross
        20 * mm,  # BPJS
        18 * mm,  # Tax
        24 * mm,  # Net
    ]

    table = Table(rows, colWidths=col_widths, repeatRows=1)

    # Styles
    header_bg = colors.HexColor("#1e3a5f")
    total_bg = colors.HexColor("#f0f4f8")
    alt_bg = colors.HexColor("#f9fafb")
    net_col = colors.HexColor("#166534")  # dark green

    ts = TableStyle([
        # Header
        ("BACKGROUND", (0, 0), (-1, 0), header_bg),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 7),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, alt_bg]),
        # Data alignment
        ("FONTSIZE", (0, 1), (-1, -1), 7),
        ("ALIGN", (0, 1), (1, -1), "LEFT"),   # # and Name left
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),  # rest right
        ("ALIGN", (3, 1), (4, -1), "CENTER"),  # Category, Schedule center
        ("ALIGN", (5, 1), (7, -1), "CENTER"),  # day counts center
        # Totals row
        ("BACKGROUND", (0, -1), (-1, -1), total_bg),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, -1), (-1, -1), 7),
        # Net column highlight
        ("TEXTCOLOR", (-1, 1), (-1, -1), net_col),
        ("FONTNAME", (-1, 1), (-1, -1), "Helvetica-Bold"),
        # Grid
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d1d5db")),
        ("LINEBELOW", (0, 0), (-1, 0), 1, colors.white),
        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#9ca3af")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ])
    table.setStyle(ts)
    elements.append(table)

    # ── Summary footer ──────────────────────────────────────────
    elements.append(Spacer(1, 6 * mm))
    summary_data = [
        ["", "Formal", str(totals.get("formal_count", 0)), "employees"],
        ["", "Contractors", str(totals.get("contractor_count", 0)), "employees"],
        ["", "Total Gross", _fmt_idr(totals.get("total_gross", 0)), "IDR"],
        ["", "BPJS (Employer)", _fmt_idr(totals.get("total_bpjs_employer", 0)), "IDR"],
        ["", "BPJS (Employee)", _fmt_idr(totals.get("total_bpjs_employee", 0)), "IDR"],
        ["", "Total Tax", _fmt_idr(totals.get("total_pph21", 0) + totals.get("total_contractor_tax", 0)), "IDR"],
        ["", "Total Net", _fmt_idr(totals.get("total_net", 0)), "IDR"],
        ["", "Total Cost to Company", _fmt_idr(totals.get("total_cost", 0)), "IDR"],
    ]
    summary_table = Table(summary_data, colWidths=[10 * mm, 50 * mm, 40 * mm, 20 * mm])
    summary_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (2, 0), (2, -1), "RIGHT"),
        ("FONTNAME", (1, -2), (2, -2), "Helvetica-Bold"),  # Total Net bold
        ("TEXTCOLOR", (2, -2), (2, -2), net_col),
        ("NOSPLIT", (0, 0), (-1, -1)),
    ]))
    elements.append(summary_table)

    doc.build(elements)
    buf.seek(0)
    return buf
