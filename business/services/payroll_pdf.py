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


def generate_payslip_pdf(item: dict, year: int, month: int, factory_name: str = "") -> BytesIO:
    """Generate a single-employee payslip (portrait A4)."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("t", parent=styles["Heading1"], fontSize=14, alignment=TA_CENTER, spaceAfter=2)
    sub_style = ParagraphStyle("s", parent=styles["Normal"], fontSize=9, alignment=TA_CENTER, textColor=colors.grey, spaceAfter=10)
    label_style = ParagraphStyle("lbl", parent=styles["Normal"], fontSize=8, textColor=colors.grey)
    value_style = ParagraphStyle("val", parent=styles["Normal"], fontSize=9, fontName="Helvetica-Bold")
    section_style = ParagraphStyle("sec", parent=styles["Normal"], fontSize=8, fontName="Helvetica-Bold",
                                   textColor=colors.HexColor("#1e3a5f"), spaceBefore=8, spaceAfter=4)

    period_label = MONTH_NAMES[month - 1] if 1 <= month <= 12 else str(month)
    generated_at = datetime.now().strftime("%d %b %Y %H:%M")
    is_probation = item.get("is_on_probation", False)
    category = item.get("employment_category", "formal")

    elements = [
        Paragraph("PAYSLIP", title_style),
        Paragraph(f"{period_label} {year}{' — ' + factory_name if factory_name else ''}", sub_style),
    ]

    # ── Employee info block ─────────────────────────────────────
    def _row(label, value, bold=False):
        lbl = Paragraph(label, label_style)
        val_s = ParagraphStyle("v2", parent=value_style if bold else styles["Normal"], fontSize=9)
        val = Paragraph(str(value), val_s)
        return [lbl, val]

    info_data = [
        _row("Employee", item.get("full_name", "")),
        _row("Position", item.get("position", "")),
        _row("Department", item.get("department", "").title()),
        _row("Category", ("Formal" if category == "formal" else "Contractor") +
             (" — PROBATION" if is_probation else "")),
        _row("Work Schedule", "6-day (Mon–Sat)" if item.get("work_schedule") == "six_day" else "5-day (Mon–Fri)"),
        _row("PTKP Status", "TK/0"),
    ]
    info_table = Table(info_data, colWidths=[45 * mm, 120 * mm])
    info_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    elements.append(info_table)
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e5e7eb"), spaceAfter=4))

    # ── Helper to build a two-column detail table ───────────────
    def _section(title, rows):
        elements.append(Paragraph(title, section_style))
        tdata = [[Paragraph(r[0], label_style), Paragraph(_fmt_idr(r[1]) + " IDR", value_style)] for r in rows]
        t = Table(tdata, colWidths=[100 * mm, 65 * mm])
        t.setStyle(TableStyle([
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LINEBELOW", (0, -1), (-1, -1), 0.3, colors.HexColor("#e5e7eb")),
        ]))
        elements.append(t)

    # Attendance
    elements.append(Paragraph("ATTENDANCE", section_style))
    att_data = [
        [Paragraph("Working Days in Month", label_style), Paragraph(str(item.get("working_days_in_month", 0)), value_style)],
        [Paragraph("Present Days", label_style), Paragraph(str(item.get("present_days", 0)), value_style)],
        [Paragraph("Absent Days", label_style), Paragraph(str(item.get("absent_days", 0)), value_style)],
        [Paragraph("Sick / Leave", label_style), Paragraph(f"{item.get('sick_days',0)} / {item.get('leave_days',0)}", value_style)],
        [Paragraph("Overtime Hours", label_style), Paragraph(f"{item.get('overtime_hours', 0):.1f} hrs", value_style)],
    ]
    if item.get("saturday_auto_overtime_hours", 0) > 0:
        att_data.append([
            Paragraph("  incl. Saturday Auto-OT", label_style),
            Paragraph(f"{item.get('saturday_auto_overtime_hours', 0):.1f} hrs", value_style),
        ])
    att_t = Table(att_data, colWidths=[100 * mm, 65 * mm])
    att_t.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    elements.append(att_t)

    # Earnings
    earn_rows = [
        ("Base Salary (prorated)", item.get("prorated_salary", 0)),
        ("Allowances (prorated)", item.get("prorated_allowances", 0)),
    ]
    if item.get("overtime_pay", 0) > 0:
        earn_rows.append(("Overtime Pay", item.get("overtime_pay", 0)))
    if item.get("commission", 0) > 0:
        earn_rows.append(("Commission", item.get("commission", 0)))
    _section("EARNINGS", earn_rows)

    # Gross
    gross_data = [[
        Paragraph("GROSS SALARY", ParagraphStyle("g", parent=value_style, fontSize=10)),
        Paragraph(_fmt_idr(item.get("gross_salary", 0)) + " IDR",
                  ParagraphStyle("g2", parent=value_style, fontSize=10, alignment=2)),
    ]]
    gross_t = Table(gross_data, colWidths=[100 * mm, 65 * mm])
    gross_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0f4f8")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(gross_t)

    # Company contributions (not deducted from employee)
    if category == "formal":
        company_rows = []
        if item.get("bpjs_employer", 0) > 0:
            company_rows.append(("BPJS Employer Contribution", item.get("bpjs_employer", 0)))
        if item.get("company_bpjs_for_employee", 0) > 0:
            company_rows.append(("BPJS Employee Share (paid by company)", item.get("company_bpjs_for_employee", 0)))
        if item.get("pph21", 0) > 0:
            company_rows.append((f"PPh 21 TER (gross-up, paid by company)", item.get("pph21", 0)))
        if is_probation:
            company_rows.append(("⚠ Probation period — BPJS not registered", 0))
        if company_rows:
            _section("COMPANY CONTRIBUTIONS (not deducted from salary)", company_rows)

    # Deductions from employee
    ded_rows = []
    if item.get("absence_deduction", 0) > 0:
        ded_rows.append(("Absence Deduction", item.get("absence_deduction", 0)))
    if item.get("contractor_tax", 0) > 0:
        ded_rows.append(("PPh 23 (2.5%)", item.get("contractor_tax", 0)))
    if ded_rows:
        _section("DEDUCTIONS", ded_rows)

    # Net
    elements.append(Spacer(1, 3 * mm))
    net_green = colors.HexColor("#166534")
    net_data = [[
        Paragraph("NET SALARY (TAKE HOME)", ParagraphStyle("n", parent=value_style, fontSize=11, textColor=net_green)),
        Paragraph(_fmt_idr(item.get("net_salary", 0)) + " IDR",
                  ParagraphStyle("n2", parent=value_style, fontSize=11, textColor=net_green, alignment=2)),
    ]]
    net_t = Table(net_data, colWidths=[100 * mm, 65 * mm])
    net_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0fdf4")),
        ("LINEABOVE", (0, 0), (-1, 0), 1, net_green),
        ("LINEBELOW", (0, 0), (-1, 0), 1, net_green),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(net_t)

    # Total cost to company
    elements.append(Spacer(1, 4 * mm))
    cost_data = [[
        Paragraph("Total Cost to Company", label_style),
        Paragraph(_fmt_idr(item.get("total_cost_to_company", 0)) + " IDR",
                  ParagraphStyle("c", parent=value_style, fontSize=8, alignment=2)),
    ]]
    cost_t = Table(cost_data, colWidths=[100 * mm, 65 * mm])
    cost_t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    elements.append(cost_t)

    elements.append(Spacer(1, 8 * mm))
    elements.append(Paragraph(
        f"Generated: {generated_at} | This payslip is confidential.",
        ParagraphStyle("foot", parent=styles["Normal"], fontSize=7, textColor=colors.grey, alignment=TA_CENTER)
    ))

    doc.build(elements)
    buf.seek(0)
    return buf
