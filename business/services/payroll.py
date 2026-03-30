"""Payroll calculation engine — Indonesian labor law compliant.

Based on PP 35/2021, UU Cipta Kerja, and current BPJS regulations (2025-2026).
Supports both formal employees and contractors.
"""

from decimal import Decimal, ROUND_HALF_UP


# ── Constants ────────────────────────────────────────────────────────────────

HOURS_DIVISOR = Decimal("173")  # PP 35/2021 legal standard

# BPJS rates (percentage of base salary)
BPJS_JKN_EMPLOYER = Decimal("0.04")       # 4%
BPJS_JKN_EMPLOYEE = Decimal("0.01")       # 1%
BPJS_JKK_EMPLOYER = Decimal("0.0089")     # 0.89% (medium risk — manufacturing)
BPJS_JKM_EMPLOYER = Decimal("0.0030")     # 0.30%
BPJS_JHT_EMPLOYER = Decimal("0.0370")     # 3.70%
BPJS_JHT_EMPLOYEE = Decimal("0.0200")     # 2.00%
BPJS_JP_EMPLOYER = Decimal("0.0200")      # 2.00%
BPJS_JP_EMPLOYEE = Decimal("0.0100")      # 1.00%

# BPJS caps
BPJS_JKN_WAGE_CAP = Decimal("12000000")   # Max wage base for JKN
BPJS_JP_WAGE_CAP = Decimal("10547400")    # Max wage base for JP

# PPh 21 progressive tax brackets (annual taxable income)
PPH21_BRACKETS = [
    (Decimal("60000000"), Decimal("0.05")),     # 0 - 60M: 5%
    (Decimal("250000000"), Decimal("0.15")),    # 60M - 250M: 15%
    (Decimal("500000000"), Decimal("0.25")),    # 250M - 500M: 25%
    (Decimal("5000000000"), Decimal("0.30")),   # 500M - 5B: 30%
    (None, Decimal("0.35")),                     # Above 5B: 35%
]

# PTKP (Non-Taxable Income) — annual
PTKP_TABLE = {
    "TK/0": Decimal("54000000"),
    "K/0": Decimal("58500000"),
    "TK/1": Decimal("58500000"),
    "K/1": Decimal("63000000"),
    "TK/2": Decimal("63000000"),
    "K/2": Decimal("67500000"),
    "TK/3": Decimal("67500000"),
    "K/3": Decimal("72000000"),
}

# Contractor tax rate (PPh 23)
CONTRACTOR_TAX_RATE = Decimal("0.025")  # 2.5%

ZERO = Decimal("0")
TWO_PLACES = Decimal("0.01")


def _d(val) -> Decimal:
    """Safely convert any numeric value to Decimal."""
    if val is None:
        return ZERO
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


def _round(val: Decimal) -> Decimal:
    """Round to 2 decimal places."""
    return val.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


# ── BPJS Calculation ────────────────────────────────────────────────────────

def calculate_bpjs(base_salary: Decimal) -> dict:
    """Calculate BPJS contributions for a formal employee.

    Returns dict with employee_total, employer_total, and per-program breakdown.
    """
    salary = _d(base_salary)

    # JKN — capped at wage base
    jkn_base = min(salary, BPJS_JKN_WAGE_CAP)
    jkn_employer = _round(jkn_base * BPJS_JKN_EMPLOYER)
    jkn_employee = _round(jkn_base * BPJS_JKN_EMPLOYEE)

    # JKK — employer only, no cap
    jkk_employer = _round(salary * BPJS_JKK_EMPLOYER)

    # JKM — employer only, no cap
    jkm_employer = _round(salary * BPJS_JKM_EMPLOYER)

    # JHT — no cap
    jht_employer = _round(salary * BPJS_JHT_EMPLOYER)
    jht_employee = _round(salary * BPJS_JHT_EMPLOYEE)

    # JP — capped at wage base
    jp_base = min(salary, BPJS_JP_WAGE_CAP)
    jp_employer = _round(jp_base * BPJS_JP_EMPLOYER)
    jp_employee = _round(jp_base * BPJS_JP_EMPLOYEE)

    employee_total = jkn_employee + jht_employee + jp_employee
    employer_total = jkn_employer + jkk_employer + jkm_employer + jht_employer + jp_employer

    return {
        "jkn_employer": float(jkn_employer),
        "jkn_employee": float(jkn_employee),
        "jkk_employer": float(jkk_employer),
        "jkm_employer": float(jkm_employer),
        "jht_employer": float(jht_employer),
        "jht_employee": float(jht_employee),
        "jp_employer": float(jp_employer),
        "jp_employee": float(jp_employee),
        "employee_total": float(employee_total),
        "employer_total": float(employer_total),
    }


# ── PPh 21 Calculation ──────────────────────────────────────────────────────

def calculate_pph21_annual(annual_taxable_income: Decimal) -> Decimal:
    """Calculate annual PPh 21 using progressive brackets."""
    if annual_taxable_income <= ZERO:
        return ZERO

    remaining = annual_taxable_income
    total_tax = ZERO
    prev_limit = ZERO

    for limit, rate in PPH21_BRACKETS:
        if limit is None:
            # Top bracket — no upper limit
            total_tax += _round(remaining * rate)
            break

        bracket_size = limit - prev_limit
        if remaining <= bracket_size:
            total_tax += _round(remaining * rate)
            break
        else:
            total_tax += _round(bracket_size * rate)
            remaining -= bracket_size
            prev_limit = limit

    return total_tax


def calculate_pph21_monthly(
    monthly_gross: Decimal,
    bpjs_employee: Decimal,
    ptkp_status: str = "TK/0",
) -> Decimal:
    """Calculate monthly PPh 21 for a formal employee.

    Uses the annual method: annualize gross, subtract BPJS employee share,
    subtract PTKP, apply progressive rates, then divide by 12.
    """
    ptkp = PTKP_TABLE.get(ptkp_status, PTKP_TABLE["TK/0"])

    annual_gross = monthly_gross * Decimal("12")
    annual_bpjs = bpjs_employee * Decimal("12")
    annual_net = annual_gross - annual_bpjs
    annual_taxable = annual_net - ptkp

    if annual_taxable <= ZERO:
        return ZERO

    annual_tax = calculate_pph21_annual(annual_taxable)
    monthly_tax = _round(annual_tax / Decimal("12"))
    return monthly_tax


# ── Overtime Calculation ─────────────────────────────────────────────────────

def calculate_overtime_pay(
    hourly_rate: Decimal,
    overtime_hours: float,
    work_schedule: str = "six_day",
    is_holiday: bool = False,
) -> Decimal:
    """Calculate overtime pay for a single day's overtime hours.

    Multipliers reset daily (not cumulative across days).
    """
    hours = Decimal(str(overtime_hours))
    if hours <= ZERO:
        return ZERO

    total = ZERO

    if not is_holiday:
        # Weekday overtime
        # 1st hour: 1.5x, 2nd+ hour: 2x
        if hours >= Decimal("1"):
            total += hourly_rate * Decimal("1.5")
            remaining = hours - Decimal("1")
            if remaining > ZERO:
                total += hourly_rate * Decimal("2") * remaining
        else:
            total += hourly_rate * Decimal("1.5") * hours
    else:
        # Holiday / Rest day overtime
        if work_schedule == "five_day":
            # 1-8h: 2x, 9th: 3x, 10+: 4x
            if hours <= Decimal("8"):
                total += hourly_rate * Decimal("2") * hours
            elif hours <= Decimal("9"):
                total += hourly_rate * Decimal("2") * Decimal("8")
                total += hourly_rate * Decimal("3") * (hours - Decimal("8"))
            else:
                total += hourly_rate * Decimal("2") * Decimal("8")
                total += hourly_rate * Decimal("3") * Decimal("1")
                total += hourly_rate * Decimal("4") * (hours - Decimal("9"))
        else:
            # 6-day schedule: 1-7h: 2x, 8th: 3x, 9+: 4x
            if hours <= Decimal("7"):
                total += hourly_rate * Decimal("2") * hours
            elif hours <= Decimal("8"):
                total += hourly_rate * Decimal("2") * Decimal("7")
                total += hourly_rate * Decimal("3") * (hours - Decimal("7"))
            else:
                total += hourly_rate * Decimal("2") * Decimal("7")
                total += hourly_rate * Decimal("3") * Decimal("1")
                total += hourly_rate * Decimal("4") * (hours - Decimal("8"))

    return _round(total)


# ── Main Payroll Calculation ─────────────────────────────────────────────────

def calculate_monthly_payroll(
    employee,
    attendance_records: list,
    working_days_in_month: int,
    ptkp_status: str = "TK/0",
    sales_revenue: float = 0,
) -> dict:
    """Calculate full monthly payroll for one employee.

    Args:
        employee: Employee ORM object or dict-like with salary/allowance fields
        attendance_records: List of Attendance ORM objects for the month
        working_days_in_month: Total working days in the month (from factory calendar)
        ptkp_status: Tax status for PPh 21 (default TK/0)
        sales_revenue: Revenue for commission calculation (sales department)

    Returns:
        Comprehensive payroll breakdown dict.
    """
    # ── Extract employee fields ──────────────────────────────────────────
    base_salary = _d(getattr(employee, 'base_salary', 0) or 0)
    employment_category = getattr(employee, 'employment_category', 'formal') or 'formal'
    department = getattr(employee, 'department', 'production') or 'production'
    work_schedule = getattr(employee, 'work_schedule', 'six_day') or 'six_day'
    commission_rate = _d(getattr(employee, 'commission_rate', None))

    allowance_bike = _d(getattr(employee, 'allowance_bike', 0) or 0)
    allowance_housing = _d(getattr(employee, 'allowance_housing', 0) or 0)
    allowance_food = _d(getattr(employee, 'allowance_food', 0) or 0)
    allowance_bpjs = _d(getattr(employee, 'allowance_bpjs', 0) or 0)
    allowance_other = _d(getattr(employee, 'allowance_other', 0) or 0)

    total_allowances = allowance_bike + allowance_housing + allowance_food + allowance_bpjs + allowance_other

    # ── Attendance analysis ──────────────────────────────────────────────
    present_days = 0
    absent_days = 0
    sick_days = 0
    leave_days = 0
    half_days = 0
    total_overtime_hours = Decimal("0")

    for att in attendance_records:
        status = getattr(att, 'status', '') or ''
        ot = _d(getattr(att, 'overtime_hours', 0) or 0)
        if status == 'present':
            present_days += 1
        elif status == 'absent':
            absent_days += 1
        elif status == 'sick':
            sick_days += 1
        elif status == 'leave':
            leave_days += 1
        elif status == 'half_day':
            half_days += 1
        total_overtime_hours += ot

    # Effective working days: present + leave + sick + half_day*0.5
    effective_days = Decimal(str(present_days + leave_days + sick_days)) + Decimal(str(half_days)) * Decimal("0.5")

    # ── Proration ────────────────────────────────────────────────────────
    if working_days_in_month <= 0:
        proration_factor = ZERO
    else:
        proration_factor = min(effective_days / Decimal(str(working_days_in_month)), Decimal("1"))

    prorated_salary = _round(base_salary * proration_factor)
    daily_rate = _round(base_salary / Decimal(str(max(working_days_in_month, 1))))

    # ── Hourly rate for overtime ─────────────────────────────────────────
    hourly_rate = _round(base_salary / HOURS_DIVISOR)

    # ── Overtime pay ─────────────────────────────────────────────────────
    # Simplified: treat all OT as weekday OT (per-day records)
    # For a more accurate implementation, each attendance record could flag is_holiday
    overtime_pay = ZERO
    for att in attendance_records:
        ot = float(getattr(att, 'overtime_hours', 0) or 0)
        if ot > 0:
            # Check if day is a holiday/rest day (simplified: not tracked per record yet)
            overtime_pay += calculate_overtime_pay(hourly_rate, ot, work_schedule, is_holiday=False)

    # ── Commission (sales department only) ───────────────────────────────
    commission = ZERO
    if department == 'sales' and commission_rate > ZERO and sales_revenue > 0:
        commission = _round(_d(sales_revenue) * commission_rate / Decimal("100"))

    # ── Gross salary ─────────────────────────────────────────────────────
    prorated_allowances = _round(total_allowances * proration_factor)
    gross_salary = prorated_salary + prorated_allowances + overtime_pay + commission

    # ── Category-specific calculations ───────────────────────────────────
    bpjs_employee_total = ZERO
    bpjs_employer_total = ZERO
    bpjs_breakdown = {}
    pph21 = ZERO
    contractor_tax = ZERO

    if employment_category == 'formal':
        # BPJS calculations on base salary (not prorated — BPJS is on contractual salary)
        bpjs = calculate_bpjs(base_salary)
        bpjs_breakdown = bpjs
        bpjs_employee_total = _d(bpjs["employee_total"])
        bpjs_employer_total = _d(bpjs["employer_total"])

        # PPh 21
        pph21 = calculate_pph21_monthly(gross_salary, bpjs_employee_total, ptkp_status)

    elif employment_category == 'contractor':
        # Contractor: 2.5% PPh 23 on total payment
        contractor_tax = _round(gross_salary * CONTRACTOR_TAX_RATE)

    # ── Absence deduction ────────────────────────────────────────────────
    absence_deduction = _round(daily_rate * Decimal(str(absent_days)))

    # ── Deductions ───────────────────────────────────────────────────────
    total_deductions = bpjs_employee_total + pph21 + contractor_tax + absence_deduction

    # ── Net salary (take home pay) ───────────────────────────────────────
    net_salary = _round(gross_salary - total_deductions)

    # ── Total cost to company ────────────────────────────────────────────
    if employment_category == 'formal':
        total_cost = _round(gross_salary + bpjs_employer_total + pph21)
    else:
        total_cost = _round(gross_salary)  # contractor: company pays gross amount

    return {
        # Employee info
        "employee_id": str(getattr(employee, 'id', '')),
        "full_name": getattr(employee, 'full_name', ''),
        "position": getattr(employee, 'position', ''),
        "department": department,
        "employment_category": employment_category,
        "work_schedule": work_schedule,

        # Attendance
        "working_days_in_month": working_days_in_month,
        "present_days": present_days,
        "absent_days": absent_days,
        "sick_days": sick_days,
        "leave_days": leave_days,
        "half_days": half_days,
        "effective_days": float(effective_days),
        "overtime_hours": float(total_overtime_hours),

        # Salary components
        "base_salary": float(base_salary),
        "daily_rate": float(daily_rate),
        "hourly_rate": float(hourly_rate),
        "prorated_salary": float(prorated_salary),
        "proration_factor": float(_round(proration_factor)),

        # Allowances
        "allowance_bike": float(allowance_bike),
        "allowance_housing": float(allowance_housing),
        "allowance_food": float(allowance_food),
        "allowance_bpjs": float(allowance_bpjs),
        "allowance_other": float(allowance_other),
        "total_allowances": float(total_allowances),
        "prorated_allowances": float(prorated_allowances),

        # Overtime
        "overtime_pay": float(overtime_pay),

        # Commission
        "commission_rate": float(commission_rate),
        "commission": float(commission),

        # Gross
        "gross_salary": float(gross_salary),

        # BPJS (formal only)
        "bpjs_employee": float(bpjs_employee_total),
        "bpjs_employer": float(bpjs_employer_total),
        "bpjs_breakdown": bpjs_breakdown,

        # Tax
        "pph21": float(pph21),
        "contractor_tax": float(contractor_tax),

        # Deductions
        "absence_deduction": float(absence_deduction),
        "total_deductions": float(total_deductions),

        # Net
        "net_salary": float(net_salary),

        # Total cost to company
        "total_cost_to_company": float(total_cost),
    }
