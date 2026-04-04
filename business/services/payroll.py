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


# ── TER (Tarif Efektif Rata-rata) — PMK 168/2023, effective Jan 2024 ────────
# Category A: TK/0
# Category B: TK/1, TK/2, TK/3, K/0
# Category C: K/1, K/2, K/3
# Each entry: (upper_limit_inclusive, rate_decimal)
# Last entry has upper_limit = None (open-ended)

_TER_A = [
    (5_400_000, Decimal("0.0000")),
    (5_650_000, Decimal("0.0025")),
    (5_950_000, Decimal("0.0050")),
    (6_300_000, Decimal("0.0075")),
    (6_750_000, Decimal("0.0100")),
    (7_500_000, Decimal("0.0125")),
    (8_550_000, Decimal("0.0150")),
    (9_650_000, Decimal("0.0200")),
    (10_050_000, Decimal("0.0250")),
    (10_350_000, Decimal("0.0300")),
    (10_700_000, Decimal("0.0350")),
    (11_050_000, Decimal("0.0400")),
    (11_600_000, Decimal("0.0450")),
    (12_500_000, Decimal("0.0500")),
    (13_750_000, Decimal("0.0550")),
    (15_100_000, Decimal("0.0600")),
    (16_950_000, Decimal("0.0650")),
    (19_750_000, Decimal("0.0700")),
    (24_150_000, Decimal("0.0750")),
    (26_450_000, Decimal("0.0800")),
    (28_000_000, Decimal("0.0850")),
    (30_050_000, Decimal("0.0900")),
    (32_400_000, Decimal("0.0950")),
    (35_400_000, Decimal("0.1000")),
    (39_100_000, Decimal("0.1050")),
    (43_850_000, Decimal("0.1100")),
    (47_800_000, Decimal("0.1150")),
    (51_400_000, Decimal("0.1200")),
    (56_300_000, Decimal("0.1250")),
    (62_200_000, Decimal("0.1300")),
    (69_200_000, Decimal("0.1350")),
    (79_000_000, Decimal("0.1400")),
    (93_200_000, Decimal("0.1450")),
    (None, Decimal("0.1500")),
]

_TER_B = [
    (6_200_000, Decimal("0.0000")),
    (6_500_000, Decimal("0.0025")),
    (6_850_000, Decimal("0.0050")),
    (7_300_000, Decimal("0.0075")),
    (9_200_000, Decimal("0.0100")),
    (10_750_000, Decimal("0.0150")),
    (11_250_000, Decimal("0.0200")),
    (11_600_000, Decimal("0.0250")),
    (12_600_000, Decimal("0.0300")),
    (13_600_000, Decimal("0.0350")),
    (14_950_000, Decimal("0.0400")),
    (16_400_000, Decimal("0.0450")),
    (18_450_000, Decimal("0.0500")),
    (21_850_000, Decimal("0.0550")),
    (26_000_000, Decimal("0.0600")),
    (27_700_000, Decimal("0.0650")),
    (29_350_000, Decimal("0.0700")),
    (31_450_000, Decimal("0.0750")),
    (33_950_000, Decimal("0.0800")),
    (37_100_000, Decimal("0.0850")),
    (41_100_000, Decimal("0.0900")),
    (45_800_000, Decimal("0.0950")),
    (49_500_000, Decimal("0.1000")),
    (53_800_000, Decimal("0.1050")),
    (58_500_000, Decimal("0.1100")),
    (64_000_000, Decimal("0.1150")),
    (71_000_000, Decimal("0.1200")),
    (80_000_000, Decimal("0.1250")),
    (93_000_000, Decimal("0.1300")),
    (107_000_000, Decimal("0.1400")),
    (None, Decimal("0.1500")),
]

_TER_C = [
    (7_050_000, Decimal("0.0000")),
    (7_450_000, Decimal("0.0025")),
    (7_800_000, Decimal("0.0050")),
    (8_250_000, Decimal("0.0075")),
    (8_850_000, Decimal("0.0100")),
    (9_800_000, Decimal("0.0125")),
    (10_950_000, Decimal("0.0150")),
    (11_200_000, Decimal("0.0175")),
    (12_050_000, Decimal("0.0200")),
    (12_950_000, Decimal("0.0250")),
    (14_150_000, Decimal("0.0300")),
    (15_550_000, Decimal("0.0350")),
    (17_050_000, Decimal("0.0400")),
    (19_500_000, Decimal("0.0450")),
    (22_700_000, Decimal("0.0500")),
    (26_600_000, Decimal("0.0550")),
    (28_100_000, Decimal("0.0600")),
    (30_100_000, Decimal("0.0650")),
    (32_600_000, Decimal("0.0700")),
    (35_400_000, Decimal("0.0750")),
    (38_900_000, Decimal("0.0800")),
    (43_000_000, Decimal("0.0850")),
    (47_400_000, Decimal("0.0900")),
    (51_200_000, Decimal("0.0950")),
    (55_800_000, Decimal("0.1000")),
    (60_400_000, Decimal("0.1050")),
    (66_700_000, Decimal("0.1100")),
    (74_500_000, Decimal("0.1150")),
    (83_200_000, Decimal("0.1200")),
    (95_600_000, Decimal("0.1250")),
    (110_000_000, Decimal("0.1300")),
    (134_000_000, Decimal("0.1400")),
    (None, Decimal("0.1500")),
]

_TER_CATEGORY_MAP = {
    "TK/0": _TER_A,
    "TK/1": _TER_B, "TK/2": _TER_B, "TK/3": _TER_B, "K/0": _TER_B,
    "K/1": _TER_C, "K/2": _TER_C, "K/3": _TER_C,
}


def _ter_rate(monthly_gross: Decimal, ptkp_status: str) -> Decimal:
    """Look up TER rate for given monthly gross and PTKP status."""
    table = _TER_CATEGORY_MAP.get(ptkp_status, _TER_A)
    gross_int = int(monthly_gross)
    for upper, rate in table:
        if upper is None or gross_int <= upper:
            return rate
    return _TER_A[-1][1]  # fallback


def calculate_pph21_ter(monthly_gross: Decimal, ptkp_status: str = "TK/0") -> Decimal:
    """Calculate monthly PPh 21 using TER method (PMK 168/2023).

    TER rate is applied to monthly bruto (gross before BPJS deduction).
    Company bears the tax (gross-up): not deducted from employee's take-home.
    """
    if monthly_gross <= ZERO:
        return ZERO
    rate = _ter_rate(monthly_gross, ptkp_status)
    return _round(monthly_gross * rate)


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
    payroll_year: int = 0,
    payroll_month: int = 0,
    holiday_dates: set | None = None,
) -> dict:
    """Calculate full monthly payroll for one employee.

    Rules:
    - Probation (<90 days from hire_date): no BPJS, PPh21 gross-up by company
    - After probation, has_own_bpjs=False: company pays both BPJS employer+employee, PPh21 gross-up
    - After probation, has_own_bpjs=True: company compensates allowance_bpjs (already in gross), PPh21 gross-up
    - PPh21 calculated via TER method (PMK 168/2023) — always borne by company
    - Contractor: PPh 23 still deducted from payment

    Args:
        employee: Employee ORM object or dict-like with salary/allowance fields
        attendance_records: List of Attendance ORM objects for the month
        working_days_in_month: Total working days in the month (from factory calendar)
        ptkp_status: Tax status for PPh 21 (default TK/0)
        sales_revenue: Revenue for commission calculation (sales department)
        payroll_year: Year of payroll period (for probation check)
        payroll_month: Month of payroll period (for probation check)

    Returns:
        Comprehensive payroll breakdown dict.
    """
    # ── Extract employee fields ──────────────────────────────────────────
    base_salary = _d(getattr(employee, 'base_salary', 0) or 0)
    employment_category = getattr(employee, 'employment_category', 'formal') or 'formal'
    department = getattr(employee, 'department', 'production') or 'production'
    work_schedule = getattr(employee, 'work_schedule', 'six_day') or 'six_day'
    commission_rate = _d(getattr(employee, 'commission_rate', None))
    has_own_bpjs = bool(getattr(employee, 'has_own_bpjs', False))

    # ── Probation detection (first 90 days from hire_date) ──────────────
    is_on_probation = False
    hire_date = getattr(employee, 'hire_date', None)
    if hire_date and payroll_year and payroll_month:
        from datetime import date as _date, timedelta as _td
        payroll_period_start = _date(payroll_year, payroll_month, 1)
        probation_end = hire_date + _td(days=90)
        is_on_probation = probation_end > payroll_period_start

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
    # hours_worked proration: accumulate fractional days from hours_worked field
    _partial_day_total = Decimal("0")  # sum of (hours_worked / standard_hours) for partial days

    # Standard hours per day by schedule
    # 6-day: Mon-Fri = 7h, Saturday = 5h. 5-day: Mon-Fri = 8h.
    _std_hours_default = Decimal("7") if work_schedule == 'six_day' else Decimal("8")
    _std_hours_sat = Decimal("5")  # Saturday for 6-day schedule

    def _get_std_hours_for_date(att_date_val) -> Decimal:
        """Return standard working hours for a given date."""
        if work_schedule == 'six_day' and att_date_val is not None:
            wd = getattr(att_date_val, 'weekday', lambda: -1)()
            if wd == 5:  # Saturday
                return _std_hours_sat
        return _std_hours_default

    def _is_non_working_day(d) -> bool:
        """Check if date is a holiday or rest day (not a scheduled working day).
        Work on these days is compensated via OT pay, NOT via proration."""
        if d is None:
            return False
        if d in _holidays:
            return True
        wd = getattr(d, 'weekday', lambda: -1)()
        if work_schedule == 'five_day' and wd >= 5:
            return True
        if work_schedule == 'six_day' and wd == 6:
            return True
        return False

    for att in attendance_records:
        status = getattr(att, 'status', '') or ''
        ot = _d(getattr(att, 'overtime_hours', 0) or 0)
        hw = getattr(att, 'hours_worked', None)
        att_date_val = getattr(att, 'date', None)

        # Days that are holidays/rest days don't count toward present_days for proration.
        # Their work is compensated via overtime pay instead.
        is_non_working = _is_non_working_day(att_date_val)

        if status == 'present':
            if is_non_working:
                pass  # Don't count — OT pay covers this
            elif hw is not None:
                # Partial day: prorate by hours_worked / standard_hours (capped at 1.0)
                std_h = _get_std_hours_for_date(att_date_val)
                fraction = min(_d(hw) / std_h, Decimal("1"))
                _partial_day_total += fraction
            else:
                present_days += 1
        elif status == 'absent':
            absent_days += 1
        elif status == 'sick':
            sick_days += 1
        elif status == 'leave':
            leave_days += 1
        elif status == 'half_day':
            if is_non_working:
                pass  # Don't count — OT pay covers this
            elif hw is not None:
                std_h = _get_std_hours_for_date(att_date_val)
                fraction = min(_d(hw) / std_h, Decimal("1"))
                _partial_day_total += fraction
            else:
                half_days += 1
        total_overtime_hours += ot

    # Effective working days: full present + leave + sick + half_day*0.5 + partial days
    effective_days = (Decimal(str(present_days + leave_days + sick_days))
                      + Decimal(str(half_days)) * Decimal("0.5")
                      + _partial_day_total)

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
    # For 6-day schedule: Saturdays where status=present and no manual OT entered
    # automatically get 2 hours OT (1st hour 1.5x, 2nd hour 2x) per Indonesian law.
    # Holiday OT uses higher multipliers (2x from first hour) per PP 35/2021.
    _holidays = holiday_dates or set()
    overtime_pay = ZERO
    holiday_overtime_hours = Decimal("0")
    weekday_overtime_hours = Decimal("0")
    saturday_auto_overtime_hours = Decimal("0")
    for att in attendance_records:
        ot = float(getattr(att, 'overtime_hours', 0) or 0)
        att_date = getattr(att, 'date', None)
        att_status = getattr(att, 'status', '') or ''

        # Auto-OT for 6-day Saturday: only if no manual OT already recorded
        if (work_schedule == 'six_day'
                and att_date is not None
                and getattr(att_date, 'weekday', lambda: -1)() == 5  # Saturday
                and att_status == 'present'
                and ot == 0):
            ot = 2.0
            saturday_auto_overtime_hours += Decimal("2")

        if ot > 0:
            # Check if this day is a holiday/non-working day from factory calendar
            # OR a rest day (weekend) for the employee's work schedule
            is_holiday = False
            if att_date is not None:
                if att_date in _holidays:
                    is_holiday = True
                else:
                    wd = getattr(att_date, 'weekday', lambda: -1)()
                    # 5-day schedule: Saturday(5) and Sunday(6) are rest days
                    # 6-day schedule: Sunday(6) is the only rest day
                    if work_schedule == 'five_day' and wd >= 5:
                        is_holiday = True
                    elif work_schedule == 'six_day' and wd == 6:
                        is_holiday = True
            overtime_pay += calculate_overtime_pay(hourly_rate, ot, work_schedule, is_holiday=is_holiday)
            if is_holiday:
                holiday_overtime_hours += _d(ot)
            else:
                weekday_overtime_hours += _d(ot)

    # ── Commission (sales department only) ───────────────────────────────
    commission = ZERO
    if department == 'sales' and commission_rate > ZERO and sales_revenue > 0:
        commission = _round(_d(sales_revenue) * commission_rate / Decimal("100"))

    # ── Gross salary ─────────────────────────────────────────────────────
    prorated_allowances = _round(total_allowances * proration_factor)
    gross_salary = prorated_salary + prorated_allowances + overtime_pay + commission

    # ── BPJS + PPh21 ─────────────────────────────────────────────────────
    bpjs_employee_total = ZERO
    bpjs_employer_total = ZERO
    bpjs_breakdown = {}
    pph21 = ZERO
    contractor_tax = ZERO
    # company_bpjs_for_employee: BPJS employee share borne by company (not from employee net)
    company_bpjs_for_employee = ZERO

    if employment_category == 'formal':
        if not is_on_probation:
            # BPJS on contractual base salary (not prorated)
            bpjs = calculate_bpjs(base_salary)
            bpjs_breakdown = bpjs
            bpjs_employer_total = _d(bpjs["employer_total"])

            if has_own_bpjs:
                # Employee has own BPJS — company compensates via allowance_bpjs (already in gross)
                # No additional BPJS employee deduction needed
                bpjs_employee_total = ZERO
                company_bpjs_for_employee = ZERO
            else:
                # Company pays employee's BPJS share too → not deducted from net
                bpjs_employee_total = _d(bpjs["employee_total"])
                company_bpjs_for_employee = bpjs_employee_total
                bpjs_employee_total = ZERO  # not charged to employee net

        # PPh21 via TER — always gross-up (company bears, not deducted from employee)
        pph21 = calculate_pph21_ter(gross_salary, ptkp_status)

    elif employment_category == 'contractor':
        # PPh 23: 2.5% deducted from contractor payment
        contractor_tax = _round(gross_salary * CONTRACTOR_TAX_RATE)

    # ── Absence deduction ────────────────────────────────────────────────
    absence_deduction = _round(daily_rate * Decimal(str(absent_days)))

    # ── Deductions from employee (take-home perspective) ─────────────────
    # Formal: company pays PPh21 + BPJS employee → only absence reduces net
    # Contractor: PPh23 still deducted from payment
    total_deductions = bpjs_employee_total + contractor_tax + absence_deduction

    # ── Net salary (take home pay) ───────────────────────────────────────
    net_salary = _round(gross_salary - total_deductions)

    # ── Total cost to company ────────────────────────────────────────────
    if employment_category == 'formal':
        # Gross + BPJS employer + BPJS employee (if company pays it) + PPh21 (gross-up)
        total_cost = _round(gross_salary + bpjs_employer_total + company_bpjs_for_employee + pph21)
    else:
        total_cost = _round(gross_salary)  # contractor: company pays gross, PPh23 is withheld

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
        "partial_day_fraction": float(_partial_day_total),  # fractional days from hours_worked
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
        "holiday_overtime_hours": float(holiday_overtime_hours),
        "weekday_overtime_hours": float(weekday_overtime_hours),
        "saturday_auto_overtime_hours": float(saturday_auto_overtime_hours),

        # Commission
        "commission_rate": float(commission_rate),
        "commission": float(commission),

        # Gross
        "gross_salary": float(gross_salary),

        # Probation / BPJS flags
        "is_on_probation": is_on_probation,
        "has_own_bpjs": has_own_bpjs,

        # BPJS (formal only; bpjs_employee=0 since company covers it)
        "bpjs_employee": float(bpjs_employee_total),
        "bpjs_employer": float(bpjs_employer_total),
        "company_bpjs_for_employee": float(company_bpjs_for_employee),
        "bpjs_breakdown": bpjs_breakdown,

        # Tax (PPh21 gross-up: borne by company, not deducted from employee)
        "pph21": float(pph21),
        "pph21_borne_by_company": float(pph21) if employment_category == 'formal' else 0.0,
        "contractor_tax": float(contractor_tax),

        # Deductions (from employee net — formal: only absences; contractor: PPh23+absences)
        "absence_deduction": float(absence_deduction),
        "total_deductions": float(total_deductions),

        # Net
        "net_salary": float(net_salary),

        # Total cost to company
        "total_cost_to_company": float(total_cost),
    }
