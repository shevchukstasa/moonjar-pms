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


_BULAN = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]

# Motivational quotes — rotated by month
_QUOTES = [
    "Setiap batu punya cerita. Terima kasih sudah menjadi bagian dari cerita kami.",
    "Tangan-tangan hebat menciptakan karya luar biasa. Terima kasih atas dedikasi Anda!",
    "Bersama kita mengubah batu menjadi seni. Kerja keras Anda sangat berarti.",
    "Api dan semangat Anda membentuk karya indah. Terima kasih!",
    "Kreativitas Anda adalah kekuatan Moonjar. Terus berkarya!",
    "Setiap detail adalah kebanggaan. Terima kasih atas ketelitian Anda.",
    "Dari batu kasar menjadi keindahan — berkat tangan-tangan terampil Anda.",
    "Moonjar bersinar karena tim yang luar biasa. Anda salah satunya!",
    "Karya terbaik lahir dari hati yang tulus. Terima kasih atas semangatnya.",
    "Setiap hari, Anda membangun keindahan dari batu lava. Luar biasa!",
    "Dedikasi Anda mengubah batu menjadi mahakarya. Bangga memiliki Anda!",
    "Tahun baru, semangat baru! Terima kasih sudah bersama Moonjar.",
]


def generate_payslip_pdf(item: dict, year: int, month: int, factory_name: str = "") -> BytesIO:
    """Generate a vibrant single-page payslip in Moonjar brand style (Bahasa Indonesia)."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

    # ── Moonjar brand palette — VIBRANT ───────────────────────
    CHARCOAL = colors.HexColor("#1A1714")       # deep dark
    WARM_CLAY = colors.HexColor("#7A5C34")       # rich brown
    EMBER = colors.HexColor("#C4713B")           # terracotta accent
    EMBER_BG = colors.HexColor("#FFF3EC")        # warm peach bg
    SAND = colors.HexColor("#F5EDE4")            # warm card bg
    GOLD = colors.HexColor("#B8860B")            # rich gold
    SAGE = colors.HexColor("#2E7D32")            # vivid green for money
    SAGE_BG = colors.HexColor("#E8F5E9")         # light green bg
    DIVIDER = colors.HexColor("#C9B99A")         # warm divider
    BODY = colors.HexColor("#3E3832")            # body text (readable)
    MUTED = colors.HexColor("#6B6159")           # secondary text

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=16 * mm, rightMargin=16 * mm,
        topMargin=12 * mm, bottomMargin=10 * mm,
    )

    styles = getSampleStyleSheet()
    W = 178 * mm  # usable width

    # ── Style definitions — LARGER, BOLDER ────────────────────
    lbl = ParagraphStyle("lbl", parent=styles["Normal"], fontSize=8.5, textColor=MUTED)
    val = ParagraphStyle("val", parent=styles["Normal"], fontSize=9, fontName="Helvetica-Bold", textColor=CHARCOAL)
    sec = ParagraphStyle("sec", parent=styles["Normal"], fontSize=8.5, fontName="Helvetica-Bold",
                         textColor=EMBER, spaceBefore=5, spaceAfter=2)
    note = ParagraphStyle("note", parent=styles["Normal"], fontSize=7, textColor=MUTED,
                          fontName="Helvetica-Oblique")
    COL_L = 104 * mm
    COL_R = 74 * mm

    bulan = _BULAN[month - 1] if 1 <= month <= 12 else str(month)
    is_probation = item.get("is_on_probation", False)
    category = item.get("employment_category", "formal")
    quote = _QUOTES[(month - 1) % len(_QUOTES)]

    elements = []

    # ══════════════════════════════════════════════════════════
    # HEADER — bold Moonjar brand
    # ══════════════════════════════════════════════════════════
    logo_text = ParagraphStyle("logo", parent=styles["Normal"], fontSize=18, fontName="Helvetica-Bold",
                                textColor=CHARCOAL, alignment=TA_LEFT, leading=20)
    tagline = ParagraphStyle("tag", parent=styles["Normal"], fontSize=7.5, textColor=GOLD,
                              alignment=TA_LEFT, fontName="Helvetica-Oblique")
    addr = ParagraphStyle("addr", parent=styles["Normal"], fontSize=7.5, textColor=MUTED, alignment=TA_RIGHT)
    slip_title = ParagraphStyle("slip", parent=styles["Normal"], fontSize=11, textColor=EMBER,
                                 fontName="Helvetica-Bold", alignment=TA_RIGHT)

    header_data = [[
        [Paragraph("MOONJAR", logo_text),
         Paragraph("Poetic craftsmanship in lava stone", tagline)],
        [Paragraph("SLIP GAJI", slip_title),
         Paragraph(f"{bulan} {year}" + (f"  \u2022  {factory_name}" if factory_name else ""), addr),
         Paragraph("Jl. Sunset Road 900B, Seminyak, Bali", addr)],
    ]]
    header_t = Table(header_data, colWidths=[90 * mm, 88 * mm])
    header_t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(header_t)

    # Bold ember accent line
    elements.append(Spacer(1, 2.5 * mm))
    elements.append(HRFlowable(width="100%", thickness=2, color=EMBER, spaceAfter=1.5 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=GOLD, spaceAfter=4 * mm))

    # ══════════════════════════════════════════════════════════
    # EMPLOYEE INFO — warm card
    # ══════════════════════════════════════════════════════════
    sched = "6 hari (Sen\u2013Sab)" if item.get("work_schedule") == "six_day" else "5 hari (Sen\u2013Jum)"
    cat_text = ("Tetap" if category == "formal" else "Kontrak") + (" \u2022 PERCOBAAN" if is_probation else "")

    info = [
        [Paragraph("Nama", lbl), Paragraph(item.get("full_name", ""), val),
         Paragraph("Jadwal", lbl), Paragraph(sched, val)],
        [Paragraph("Jabatan", lbl), Paragraph(item.get("position", ""), val),
         Paragraph("Kategori", lbl), Paragraph(cat_text, val)],
    ]
    info_t = Table(info, colWidths=[20 * mm, 70 * mm, 18 * mm, 70 * mm])
    info_t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("BACKGROUND", (0, 0), (-1, -1), SAND),
        ("BOX", (0, 0), (-1, -1), 0.5, DIVIDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("ROUNDRECT", (0, 0), (-1, -1), 2),
    ]))
    elements.append(info_t)
    elements.append(Spacer(1, 3.5 * mm))

    # ── Helper ─────────────────────────────────────────────────
    def _tbl(rows, total_row=False):
        t = Table(rows, colWidths=[COL_L, COL_R])
        style_cmds = [
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]
        if total_row:
            style_cmds.append(("LINEABOVE", (0, -1), (-1, -1), 0.5, DIVIDER))
        t.setStyle(TableStyle(style_cmds))
        return t

    # ══════════════════════════════════════════════════════════
    # KEHADIRAN (Attendance)
    # ══════════════════════════════════════════════════════════
    elements.append(Paragraph("KEHADIRAN", sec))
    att_rows = [
        [Paragraph("Hari Kerja", lbl), Paragraph(f"{item.get('present_days', 0)} / {item.get('working_days_in_month', 0)} hari", val)],
        [Paragraph("Absen / Sakit / Cuti", lbl), Paragraph(f"{item.get('absent_days', 0)} / {item.get('sick_days',0)} / {item.get('leave_days',0)}", val)],
        [Paragraph("Lembur", lbl), Paragraph(f"{item.get('overtime_hours', 0):.1f} jam" +
            (f"  (termasuk {item.get('saturday_auto_overtime_hours', 0):.0f}j lembur Sabtu)" if item.get("saturday_auto_overtime_hours", 0) > 0 else ""), val)],
    ]
    elements.append(_tbl(att_rows))

    # ── PENDAPATAN (Earnings) ─────────────────────────────────
    elements.append(Paragraph("PENDAPATAN", sec))
    earn = [
        [Paragraph("Gaji Pokok (prorata)", lbl), Paragraph(f"Rp {_fmt_idr(item.get('prorated_salary', 0))}", val)],
        [Paragraph("Tunjangan (prorata)", lbl), Paragraph(f"Rp {_fmt_idr(item.get('prorated_allowances', 0))}", val)],
    ]
    if item.get("commission", 0) > 0:
        earn.append([Paragraph("Komisi", lbl), Paragraph(f"Rp {_fmt_idr(item.get('commission', 0))}", val)])
    elements.append(_tbl(earn))

    # ── LEMBUR (Overtime breakdown) ───────────────────────────
    if item.get("overtime_pay", 0) > 0:
        hr = item.get("hourly_rate", 0)
        elements.append(Paragraph(f"LEMBUR  \u2022  Tarif per jam: Rp {_fmt_idr(hr)} (gaji pokok / 173)", sec))
        ot_rows = []
        for mult_key, mult_val, mult_label in [("ot_hours_at_1_5x", 1.5, "1,5\u00d7"), ("ot_hours_at_2x", 2, "2\u00d7")]:
            h = item.get(mult_key, 0)
            if h > 0:
                pay = round(h * hr * mult_val)
                ot_rows.append([
                    Paragraph(f"{mult_label}  {h:.1f} jam \u00d7 Rp {_fmt_idr(hr)} \u00d7 {mult_val:.1f}", lbl),
                    Paragraph(f"Rp {_fmt_idr(pay)}", val),
                ])
        ot_rows.append([
            Paragraph("Total Lembur", ParagraphStyle("otb", parent=val, fontSize=8.5)),
            Paragraph(f"Rp {_fmt_idr(item.get('overtime_pay', 0))}", val),
        ])
        elements.append(_tbl(ot_rows, total_row=True))

    # ══════════════════════════════════════════════════════════
    # GAJI KOTOR (Gross) — warm accent bar
    # ══════════════════════════════════════════════════════════
    elements.append(Spacer(1, 2.5 * mm))
    gross_row = [[
        Paragraph("GAJI KOTOR", ParagraphStyle("g", parent=val, fontSize=10, textColor=CHARCOAL)),
        Paragraph(f"Rp {_fmt_idr(item.get('gross_salary', 0))}", ParagraphStyle("g2", parent=val, fontSize=11, textColor=CHARCOAL, alignment=TA_RIGHT)),
    ]]
    gross_t = Table(gross_row, colWidths=[COL_L, COL_R])
    gross_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), EMBER_BG),
        ("BOX", (0, 0), (-1, -1), 0.8, EMBER),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(gross_t)

    # ══════════════════════════════════════════════════════════
    # PAJAK & IURAN (Tax & Contributions)
    # ══════════════════════════════════════════════════════════
    if category == "formal":
        # PPh 21
        pph21_val = item.get("pph21", 0)
        ter_rate = item.get("pph21_ter_rate_pct", 0)
        ter_s = f"{ter_rate:.2f}".rstrip('0').rstrip('.')
        elements.append(Paragraph(f"PPh 21  \u2022  TER {ter_s}%  \u2022  dibayar perusahaan", sec))
        elements.append(_tbl([
            [Paragraph(f"PPh 21 (TER {ter_s}% \u00d7 gaji kotor)", lbl), Paragraph(f"Rp {_fmt_idr(pph21_val)}", val)],
        ]))

        # BPJS section hidden — calculations under review

    # Potongan (Deductions)
    if item.get("absence_deduction", 0) > 0 or item.get("contractor_tax", 0) > 0:
        elements.append(Paragraph("POTONGAN", sec))
        ded = []
        if item.get("absence_deduction", 0) > 0:
            ded.append([Paragraph("Potongan Absen", lbl), Paragraph(f"Rp {_fmt_idr(item.get('absence_deduction', 0))}", val)])
        if item.get("contractor_tax", 0) > 0:
            ded.append([Paragraph("PPh 23 (2,5%)", lbl), Paragraph(f"Rp {_fmt_idr(item.get('contractor_tax', 0))}", val)])
        elements.append(_tbl(ded))

    # ══════════════════════════════════════════════════════════
    # GAJI BERSIH (Net) — bold green bar
    # ══════════════════════════════════════════════════════════
    elements.append(Spacer(1, 3 * mm))
    net_row = [[
        Paragraph("GAJI BERSIH", ParagraphStyle("n", parent=val, fontSize=11, textColor=SAGE)),
        Paragraph(f"Rp {_fmt_idr(item.get('net_salary', 0))}", ParagraphStyle("n2", parent=val, fontSize=13, textColor=SAGE, alignment=TA_RIGHT)),
    ]]
    net_t = Table(net_row, colWidths=[COL_L, COL_R])
    net_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SAGE_BG),
        ("BOX", (0, 0), (-1, -1), 1, SAGE),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(net_t)


    # ══════════════════════════════════════════════════════════
    # MOTIVATIONAL QUOTE — dopamine element
    # ══════════════════════════════════════════════════════════
    elements.append(Spacer(1, 4 * mm))
    quote_style = ParagraphStyle("q", parent=styles["Normal"], fontSize=8, textColor=GOLD,
                                  fontName="Helvetica-Oblique", alignment=TA_CENTER,
                                  leading=11)
    quote_t = Table([[Paragraph(f"\u201c{quote}\u201d", quote_style)]], colWidths=[W])
    quote_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SAND),
        ("BOX", (0, 0), (-1, -1), 0.5, GOLD),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    elements.append(quote_t)

    # ══════════════════════════════════════════════════════════
    # TANDA TANGAN (Signature)
    # ══════════════════════════════════════════════════════════
    elements.append(Spacer(1, 6 * mm))
    sig_lbl = ParagraphStyle("sl", parent=styles["Normal"], fontSize=8, textColor=MUTED, alignment=TA_CENTER)
    sig_name = ParagraphStyle("sn", parent=styles["Normal"], fontSize=9, fontName="Helvetica-Bold",
                               textColor=CHARCOAL, alignment=TA_CENTER)
    sig_title = ParagraphStyle("st", parent=styles["Normal"], fontSize=8, textColor=MUTED, alignment=TA_CENTER)

    sig_data = [
        [Paragraph("", sig_lbl), Paragraph("Disetujui oleh", sig_lbl)],
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
        ("TOPPADDING", (0, 2), (-1, 2), 8 * mm),
    ]))
    elements.append(sig_t)

    # ── Footer ─────────────────────────────────────────────────
    elements.append(Spacer(1, 3 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=DIVIDER, spaceAfter=1.5))
    elements.append(Paragraph(
        "PT Moonjar Design Bali  \u2022  Dokumen ini bersifat rahasia",
        ParagraphStyle("ft", parent=styles["Normal"], fontSize=7, textColor=MUTED, alignment=TA_CENTER)
    ))

    doc.build(elements)
    buf.seek(0)
    return buf
