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

    from reportlab.platypus import HRFlowable
    company_style = ParagraphStyle(
        "co", parent=styles["Normal"], fontSize=11, fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=1
    )
    address_style = ParagraphStyle(
        "addr", parent=styles["Normal"], fontSize=7.5, alignment=TA_CENTER,
        textColor=colors.grey, spaceAfter=6
    )

    elements = [
        Paragraph("PT MOONJAR DESIGN BALI", company_style),
        Paragraph("Jl. Sunset Road 900B, Seminyak, Kuta, Kab. Badung, Bali", address_style),
        HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#1e3a5f"), spaceAfter=4),
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
    """Generate a premium single-page payslip in Moonjar brand style."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    from reportlab.graphics.shapes import Drawing, Rect, Circle, String
    from reportlab.graphics import renderPDF

    # ── Moonjar brand palette ──────────────────────────────────
    CHARCOAL = colors.HexColor("#2D2926")       # primary dark (lava stone)
    WARM_CLAY = colors.HexColor("#8B6F47")       # warm brown (craft)
    EMBER = colors.HexColor("#C4713B")           # terracotta accent
    SAND = colors.HexColor("#F5F0EB")            # warm paper bg
    CREAM = colors.HexColor("#FAF8F5")           # lighter bg
    GOLD_DARK = colors.HexColor("#A68B5B")       # gold accent
    SAGE = colors.HexColor("#4A6741")            # green for net salary
    SAGE_BG = colors.HexColor("#F0F4ED")         # light sage bg
    DIVIDER = colors.HexColor("#D4C5B0")         # warm divider
    MUTED = colors.HexColor("#8C8078")           # muted text

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=14 * mm, bottomMargin=12 * mm,
    )

    styles = getSampleStyleSheet()
    W = 174 * mm  # usable width

    # ── Style definitions ──────────────────────────────────────
    lbl = ParagraphStyle("lbl", parent=styles["Normal"], fontSize=7, textColor=MUTED)
    val = ParagraphStyle("val", parent=styles["Normal"], fontSize=7.5, fontName="Helvetica-Bold", textColor=CHARCOAL)
    sec = ParagraphStyle("sec", parent=styles["Normal"], fontSize=7, fontName="Helvetica-Bold",
                         textColor=WARM_CLAY, spaceBefore=5, spaceAfter=2,
                         borderPadding=(0, 0, 1, 0))
    note = ParagraphStyle("note", parent=styles["Normal"], fontSize=6, textColor=MUTED)
    COL_L = 100 * mm
    COL_R = 74 * mm

    period_label = MONTH_NAMES[month - 1] if 1 <= month <= 12 else str(month)
    is_probation = item.get("is_on_probation", False)
    category = item.get("employment_category", "formal")

    elements = []

    # ══════════════════════════════════════════════════════════
    # HEADER — Moonjar brand block
    # ══════════════════════════════════════════════════════════
    logo_text = ParagraphStyle("logo", parent=styles["Normal"], fontSize=13, fontName="Helvetica-Bold",
                                textColor=CHARCOAL, alignment=TA_LEFT, leading=16)
    tagline = ParagraphStyle("tag", parent=styles["Normal"], fontSize=6.5, textColor=GOLD_DARK,
                              alignment=TA_LEFT, fontName="Helvetica-Oblique")
    addr = ParagraphStyle("addr", parent=styles["Normal"], fontSize=6.5, textColor=MUTED, alignment=TA_RIGHT)
    slip_title = ParagraphStyle("slip", parent=styles["Normal"], fontSize=8, textColor=EMBER,
                                 fontName="Helvetica-Bold", alignment=TA_RIGHT)

    header_data = [[
        [Paragraph("MOONJAR", logo_text),
         Paragraph("Poetic craftsmanship in lava stone", tagline)],
        [Paragraph("PAYSLIP", slip_title),
         Paragraph(f"{period_label} {year}" + (f"  \u2022  {factory_name}" if factory_name else ""), addr),
         Paragraph("Jl. Sunset Road 900B, Seminyak, Bali", addr)],
    ]]
    header_t = Table(header_data, colWidths=[90 * mm, 84 * mm])
    header_t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(header_t)

    # Warm accent line
    elements.append(Spacer(1, 2 * mm))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=EMBER, spaceAfter=1 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.3, color=DIVIDER, spaceAfter=4 * mm))

    # ══════════════════════════════════════════════════════════
    # EMPLOYEE INFO — compact two-column
    # ══════════════════════════════════════════════════════════
    sched = "6-day (Mon\u2013Sat)" if item.get("work_schedule") == "six_day" else "5-day (Mon\u2013Fri)"
    cat_text = ("Formal" if category == "formal" else "Contractor") + (" \u2022 PROBATION" if is_probation else "")

    info = [
        [Paragraph("Employee", lbl), Paragraph(item.get("full_name", ""), val),
         Paragraph("Schedule", lbl), Paragraph(sched, val)],
        [Paragraph("Position", lbl), Paragraph(item.get("position", ""), val),
         Paragraph("Category", lbl), Paragraph(cat_text, val)],
    ]
    info_t = Table(info, colWidths=[22 * mm, 65 * mm, 22 * mm, 65 * mm])
    info_t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
        ("BACKGROUND", (0, 0), (-1, -1), SAND),
        ("BOX", (0, 0), (-1, -1), 0.3, DIVIDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(info_t)
    elements.append(Spacer(1, 3 * mm))

    # ── Helper ─────────────────────────────────────────────────
    def _tbl(rows, total_row=False):
        t = Table(rows, colWidths=[COL_L, COL_R])
        style_cmds = [
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 1.2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1.2),
        ]
        if total_row:
            style_cmds.append(("LINEABOVE", (0, -1), (-1, -1), 0.3, DIVIDER))
        t.setStyle(TableStyle(style_cmds))
        return t

    # ══════════════════════════════════════════════════════════
    # ATTENDANCE + EARNINGS side by side — compact
    # ══════════════════════════════════════════════════════════
    elements.append(Paragraph("ATTENDANCE", sec))
    att_rows = [
        [Paragraph(f"Working Days", lbl), Paragraph(f"{item.get('present_days', 0)} / {item.get('working_days_in_month', 0)}", val)],
        [Paragraph(f"Absent / Sick / Leave", lbl), Paragraph(f"{item.get('absent_days', 0)} / {item.get('sick_days',0)} / {item.get('leave_days',0)}", val)],
        [Paragraph(f"Overtime", lbl), Paragraph(f"{item.get('overtime_hours', 0):.1f} hrs" +
            (f"  (incl. {item.get('saturday_auto_overtime_hours', 0):.0f}h Sat auto-OT)" if item.get("saturday_auto_overtime_hours", 0) > 0 else ""), val)],
    ]
    elements.append(_tbl(att_rows))

    # ── EARNINGS ───────────────────────────────────────────────
    elements.append(Paragraph("EARNINGS", sec))
    earn = [
        [Paragraph("Base Salary (prorated)", lbl), Paragraph(f"{_fmt_idr(item.get('prorated_salary', 0))} IDR", val)],
        [Paragraph("Allowances (prorated)", lbl), Paragraph(f"{_fmt_idr(item.get('prorated_allowances', 0))} IDR", val)],
    ]
    if item.get("commission", 0) > 0:
        earn.append([Paragraph("Commission", lbl), Paragraph(f"{_fmt_idr(item.get('commission', 0))} IDR", val)])
    elements.append(_tbl(earn))

    # ── OVERTIME BREAKDOWN ─────────────────────────────────────
    if item.get("overtime_pay", 0) > 0:
        hr = item.get("hourly_rate", 0)
        elements.append(Paragraph(f"OVERTIME  \u2022  Hourly rate: Rp {_fmt_idr(hr)} (base / 173)", sec))
        ot_rows = []
        for mult_key, mult_val, mult_label in [("ot_hours_at_1_5x", 1.5, "1.5\u00d7"), ("ot_hours_at_2x", 2, "2\u00d7"),
                                                  ("ot_hours_at_3x", 3, "3\u00d7"), ("ot_hours_at_4x", 4, "4\u00d7")]:
            h = item.get(mult_key, 0)
            if h > 0:
                pay = round(h * hr * mult_val)
                ot_rows.append([
                    Paragraph(f"{mult_label}  {h:.1f} hrs \u00d7 Rp {_fmt_idr(hr)} \u00d7 {mult_val:.1f}", lbl),
                    Paragraph(f"{_fmt_idr(pay)} IDR", val),
                ])
        ot_rows.append([
            Paragraph("Total Overtime", ParagraphStyle("otb", parent=val, fontSize=7)),
            Paragraph(f"{_fmt_idr(item.get('overtime_pay', 0))} IDR", val),
        ])
        elements.append(_tbl(ot_rows, total_row=True))

    # ══════════════════════════════════════════════════════════
    # GROSS — highlighted bar
    # ══════════════════════════════════════════════════════════
    elements.append(Spacer(1, 2 * mm))
    gross_row = [[
        Paragraph("GROSS SALARY", ParagraphStyle("g", parent=val, fontSize=8.5, textColor=CHARCOAL)),
        Paragraph(f"Rp {_fmt_idr(item.get('gross_salary', 0))}", ParagraphStyle("g2", parent=val, fontSize=9, textColor=CHARCOAL, alignment=TA_RIGHT)),
    ]]
    gross_t = Table(gross_row, colWidths=[COL_L, COL_R])
    gross_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SAND),
        ("BOX", (0, 0), (-1, -1), 0.5, DIVIDER),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(gross_t)

    # ══════════════════════════════════════════════════════════
    # TAX & CONTRIBUTIONS — compact
    # ══════════════════════════════════════════════════════════
    if category == "formal":
        # PPh 21
        pph21_val = item.get("pph21", 0)
        ter_rate = item.get("pph21_ter_rate_pct", 0)
        ter_s = f"{ter_rate:.2f}".rstrip('0').rstrip('.')
        elements.append(Paragraph(f"PPh 21  \u2022  TER {ter_s}% \u2022  paid by employer", sec))
        elements.append(_tbl([
            [Paragraph(f"PPh 21 (TER {ter_s}% \u00d7 gross)", lbl), Paragraph(f"{_fmt_idr(pph21_val)} IDR", val)],
        ]))

        # BPJS
        bd = item.get("bpjs_breakdown", {})
        if item.get("bpjs_employer", 0) > 0 or item.get("company_bpjs_for_employee", 0) > 0:
            elements.append(Paragraph("BPJS \u2014 EMPLOYER (10.89%)", sec))
            er_rows = [
                [Paragraph("JKN 4% + JKK 0.89% + JKM 0.3%", lbl),
                 Paragraph(f"{_fmt_idr(bd.get('jkn_employer', 0) + bd.get('jkk_employer', 0) + bd.get('jkm_employer', 0))} IDR", val)],
                [Paragraph("JHT 3.7% + JP 2%", lbl),
                 Paragraph(f"{_fmt_idr(bd.get('jht_employer', 0) + bd.get('jp_employer', 0))} IDR", val)],
                [Paragraph("Total Employer", ParagraphStyle("b", parent=val, fontSize=7)),
                 Paragraph(f"{_fmt_idr(item.get('bpjs_employer', 0))} IDR", val)],
            ]
            elements.append(_tbl(er_rows, total_row=True))

            elements.append(Paragraph("BPJS \u2014 EMPLOYEE (4%)  \u2022  paid by company", sec))
            ee_rows = [
                [Paragraph("JKN 1% + JHT 2% + JP 1%", lbl),
                 Paragraph(f"{_fmt_idr(bd.get('jkn_employee', 0) + bd.get('jht_employee', 0) + bd.get('jp_employee', 0))} IDR", val)],
            ]
            elements.append(_tbl(ee_rows))
            elements.append(Paragraph("Employee BPJS is fully paid by the company \u2014 not deducted from salary", note))

        elif is_probation:
            elements.append(Paragraph("BPJS \u2014 Probation period, not yet registered", note))

    # Deductions
    if item.get("absence_deduction", 0) > 0 or item.get("contractor_tax", 0) > 0:
        elements.append(Paragraph("DEDUCTIONS", sec))
        ded = []
        if item.get("absence_deduction", 0) > 0:
            ded.append([Paragraph("Absence Deduction", lbl), Paragraph(f"{_fmt_idr(item.get('absence_deduction', 0))} IDR", val)])
        if item.get("contractor_tax", 0) > 0:
            ded.append([Paragraph("PPh 23 (2.5%)", lbl), Paragraph(f"{_fmt_idr(item.get('contractor_tax', 0))} IDR", val)])
        elements.append(_tbl(ded))

    # ══════════════════════════════════════════════════════════
    # NET SALARY — premium green bar
    # ══════════════════════════════════════════════════════════
    elements.append(Spacer(1, 3 * mm))
    net_row = [[
        Paragraph("NET SALARY", ParagraphStyle("n", parent=val, fontSize=9, textColor=SAGE)),
        Paragraph(f"Rp {_fmt_idr(item.get('net_salary', 0))}", ParagraphStyle("n2", parent=val, fontSize=10, textColor=SAGE, alignment=TA_RIGHT)),
    ]]
    net_t = Table(net_row, colWidths=[COL_L, COL_R])
    net_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SAGE_BG),
        ("BOX", (0, 0), (-1, -1), 0.8, SAGE),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(net_t)

    # Cost to company (small)
    elements.append(Spacer(1, 2 * mm))
    elements.append(_tbl([
        [Paragraph("Total Cost to Company", lbl), Paragraph(f"Rp {_fmt_idr(item.get('total_cost_to_company', 0))}", val)],
    ]))

    # ══════════════════════════════════════════════════════════
    # SIGNATURE — right-aligned, compact
    # ══════════════════════════════════════════════════════════
    elements.append(Spacer(1, 8 * mm))
    sig_lbl = ParagraphStyle("sl", parent=styles["Normal"], fontSize=7, textColor=MUTED, alignment=TA_CENTER)
    sig_name = ParagraphStyle("sn", parent=styles["Normal"], fontSize=8, fontName="Helvetica-Bold",
                               textColor=CHARCOAL, alignment=TA_CENTER)
    sig_title = ParagraphStyle("st", parent=styles["Normal"], fontSize=7, textColor=MUTED, alignment=TA_CENTER)

    sig_data = [
        [Paragraph("", sig_lbl), Paragraph("Approved by", sig_lbl)],
        [Paragraph("", sig_lbl), Paragraph("", sig_lbl)],
        [Paragraph("", sig_lbl), Paragraph("____________________", sig_lbl)],
        [Paragraph("", sig_lbl), Paragraph("Stanislav Shevchuk", sig_name)],
        [Paragraph("", sig_lbl), Paragraph("Direktur", sig_title)],
    ]
    sig_t = Table(sig_data, colWidths=[W * 0.55, W * 0.45])
    sig_t.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("TOPPADDING", (0, 2), (-1, 2), 10 * mm),
    ]))
    elements.append(sig_t)

    # ── Footer accent ──────────────────────────────────────────
    elements.append(Spacer(1, 4 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.3, color=DIVIDER, spaceAfter=1))
    elements.append(Paragraph(
        "PT Moonjar Design Bali  \u2022  This document is confidential",
        ParagraphStyle("ft", parent=styles["Normal"], fontSize=6, textColor=MUTED, alignment=TA_CENTER)
    ))

    doc.build(elements)
    buf.seek(0)
    return buf
