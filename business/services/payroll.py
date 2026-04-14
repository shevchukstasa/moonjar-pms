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

# Full 44-row table per PMK 168/2023 Lampiran — verified against official gazette
_TER_A = [
    (5_400_000, Decimal("0.0000")),      # 0%
    (5_650_000, Decimal("0.0025")),      # 0.25%
    (5_950_000, Decimal("0.0050")),      # 0.5%
    (6_300_000, Decimal("0.0075")),      # 0.75%
    (6_750_000, Decimal("0.0100")),      # 1%
    (7_500_000, Decimal("0.0125")),      # 1.25%
    (8_550_000, Decimal("0.0150")),      # 1.5%
    (9_650_000, Decimal("0.0175")),      # 1.75%
    (10_050_000, Decimal("0.0200")),     # 2%
    (10_350_000, Decimal("0.0225")),     # 2.25%
    (10_700_000, Decimal("0.0250")),     # 2.5%
    (11_050_000, Decimal("0.0300")),     # 3%
    (11_600_000, Decimal("0.0350")),     # 3.5%
    (12_500_000, Decimal("0.0400")),     # 4%
    (13_750_000, Decimal("0.0500")),     # 5%
    (15_100_000, Decimal("0.0600")),     # 6%
    (16_950_000, Decimal("0.0700")),     # 7%
    (19_750_000, Decimal("0.0800")),     # 8%
    (24_150_000, Decimal("0.0900")),     # 9%
    (26_450_000, Decimal("0.1000")),     # 10%
    (28_000_000, Decimal("0.1100")),     # 11%
    (30_050_000, Decimal("0.1200")),     # 12%
    (32_400_000, Decimal("0.1300")),     # 13%
    (35_400_000, Decimal("0.1400")),     # 14%
    (39_100_000, Decimal("0.1500")),     # 15%
    (43_850_000, Decimal("0.1600")),     # 16%
    (47_800_000, Decimal("0.1700")),     # 17%
    (51_400_000, Decimal("0.1800")),     # 18%
    (56_300_000, Decimal("0.1900")),     # 19%
    (62_200_000, Decimal("0.2000")),     # 20%
    (68_600_000, Decimal("0.2100")),     # 21%
    (77_500_000, Decimal("0.2200")),     # 22%
    (89_000_000, Decimal("0.2300")),     # 23%
    (103_000_000, Decimal("0.2400")),    # 24%
    (125_000_000, Decimal("0.2500")),    # 25%
    (157_000_000, Decimal("0.2600")),    # 26%
    (206_000_000, Decimal("0.2700")),    # 27%
    (337_000_000, Decimal("0.2800")),    # 28%
    (454_000_000, Decimal("0.2900")),    # 29%
    (550_000_000, Decimal("0.3000")),    # 30%
    (695_000_000, Decimal("0.3100")),    # 31%
    (910_000_000, Decimal("0.3200")),    # 32%
    (1_400_000_000, Decimal("0.3300")),  # 33%
    (None, Decimal("0.3400")),           # 34%
]

_TER_B = [
    (6_200_000, Decimal("0.0000")),      # 0%
    (6_500_000, Decimal("0.0025")),      # 0.25%
    (6_850_000, Decimal("0.0050")),      # 0.5%
    (7_300_000, Decimal("0.0075")),      # 0.75%
    (9_200_000, Decimal("0.0100")),      # 1%
    (10_750_000, Decimal("0.0150")),     # 1.5%
    (11_250_000, Decimal("0.0200")),     # 2%
    (11_600_000, Decimal("0.0250")),     # 2.5%
    (12_600_000, Decimal("0.0300")),     # 3%
    (13_600_000, Decimal("0.0400")),     # 4%
    (14_950_000, Decimal("0.0500")),     # 5%
    (16_400_000, Decimal("0.0600")),     # 6%
    (18_450_000, Decimal("0.0700")),     # 7%
    (21_850_000, Decimal("0.0800")),     # 8%
    (26_000_000, Decimal("0.0900")),     # 9%
    (27_700_000, Decimal("0.1000")),     # 10%
    (29_350_000, Decimal("0.1100")),     # 11%
    (31_450_000, Decimal("0.1200")),     # 12%
    (33_950_000, Decimal("0.1300")),     # 13%
    (37_100_000, Decimal("0.1400")),     # 14%
    (41_100_000, Decimal("0.1500")),     # 15%
    (45_800_000, Decimal("0.1600")),     # 16%
    (49_500_000, Decimal("0.1700")),     # 17%
    (53_800_000, Decimal("0.1800")),     # 18%
    (58_500_000, Decimal("0.1900")),     # 19%
    (64_000_000, Decimal("0.2000")),     # 20%
    (71_000_000, Decimal("0.2100")),     # 21%
    (80_000_000, Decimal("0.2200")),     # 22%
    (93_000_000, Decimal("0.2300")),     # 23%
    (109_000_000, Decimal("0.2400")),    # 24%
    (129_000_000, Decimal("0.2500")),    # 25%
    (163_000_000, Decimal("0.2600")),    # 26%
    (211_000_000, Decimal("0.2700")),    # 27%
    (374_000_000, Decimal("0.2800")),    # 28%
    (459_000_000, Decimal("0.2900")),    # 29%
    (555_000_000, Decimal("0.3000")),    # 30%
    (704_000_000, Decimal("0.3100")),    # 31%
    (957_000_000, Decimal("0.3200")),    # 32%
    (1_405_000_000, Decimal("0.3300")),  # 33%
    (None, Decimal("0.3400")),           # 34%
]

_TER_C = [
    (6_600_000, Decimal("0.0000")),      # 0%
    (6_950_000, Decimal("0.0025")),      # 0.25%
    (7_350_000, Decimal("0.0050")),      # 0.5%
    (7_800_000, Decimal("0.0075")),      # 0.75%
    (8_850_000, Decimal("0.0100")),      # 1%
    (9_800_000, Decimal("0.0150")),      # 1.5%
    (10_950_000, Decimal("0.0200")),     # 2%
    (11_200_000, Decimal("0.0250")),     # 2.5%
    (12_050_000, Decimal("0.0300")),     # 3%
    (12_950_000, Decimal("0.0400")),     # 4%
    (14_150_000, Decimal("0.0500")),     # 5%
    (15_550_000, Decimal("0.0600")),     # 6%
    (17_050_000, Decimal("0.0700")),     # 7%
    (19_500_000, Decimal("0.0800")),     # 8%
    (22_700_000, Decimal("0.0900")),     # 9%
    (26_600_000, Decimal("0.1000")),     # 10%
    (28_100_000, Decimal("0.1100")),     # 11%
    (30_100_000, Decimal("0.1200")),     # 12%
    (32_600_000, Decimal("0.1300")),     # 13%
    (35_400_000, Decimal("0.1400")),     # 14%
    (38_900_000, Decimal("0.1500")),     # 15%
    (43_000_000, Decimal("0.1600")),     # 16%
    (47_400_000, Decimal("0.1700")),     # 17%
    (51_200_000, Decimal("0.1800")),     # 18%
    (55_800_000, Decimal("0.1900")),     # 19%
    (60_400_000, Decimal("0.2000")),     # 20%
    (66_700_000, Decimal("0.2100")),     # 21%
    (74_500_000, Decimal("0.2200")),     # 22%
    (83_200_000, Decimal("0.2300")),     # 23%
    (95_600_000, Decimal("0.2400")),     # 24%
    (110_000_000, Decimal("0.2500")),    # 25%
    (134_000_000, Decimal("0.2600")),    # 26%
    (169_000_000, Decimal("0.2700")),    # 27%
    (221_000_000, Decimal("0.2800")),    # 28%
    (390_000_000, Decimal("0.2900")),    # 29%
    (463_000_000, Decimal("0.3000")),    # 30%
    (561_000_000, Decimal("0.3100")),    # 31%
    (709_000_000, Decimal("0.3200")),    # 32%
    (965_000_000, Decimal("0.3300")),    # 33%
    (None, Decimal("0.3400")),           # 34%
]

# PMK 168/2023 Pasal 2:
# A = TK/0, TK/1  |  B = TK/2, TK/3, K/0, K/1  |  C = K/2, K/3
_TER_CATEGORY_MAP = {
    "TK/0": _TER_A, "TK/1": _TER_A,
    "TK/2": _TER_B, "TK/3": _TER_B, "K/0": _TER_B, "K/1": _TER_B,
    "K/2": _TER_C, "K/3": _TER_C,
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
    result = calculate_overtime_pay_detailed(hourly_rate, overtime_hours, work_schedule, is_holiday)
    return result["total"]


def calculate_overtime_pay_detailed(
    hourly_rate: Decimal,
    overtime_hours: float,
    work_schedule: str = "six_day",
    is_holiday: bool = False,
) -> dict:
    """Calculate overtime pay with per-multiplier breakdown.

    Returns dict with: total, and hours/pay per multiplier (1.5x, 2x, 3x, 4x).
    """
    hours = Decimal(str(overtime_hours))
    breakdown = {"1.5": Decimal("0"), "2": Decimal("0"), "3": Decimal("0"), "4": Decimal("0")}

    if hours <= ZERO:
        return {"total": ZERO, "breakdown": breakdown}

    total = ZERO

    if not is_holiday:
        # Weekday overtime: 1st hour 1.5x, 2nd+ 2x
        if hours >= Decimal("1"):
            total += hourly_rate * Decimal("1.5")
            breakdown["1.5"] += Decimal("1")
            remaining = hours - Decimal("1")
            if remaining > ZERO:
                total += hourly_rate * Decimal("2") * remaining
                breakdown["2"] += remaining
        else:
            total += hourly_rate * Decimal("1.5") * hours
            breakdown["1.5"] += hours
    else:
        # Holiday / Rest day overtime
        limit = Decimal("8") if work_schedule == "five_day" else Decimal("7")
        # 1-limit: 2x
        h2 = min(hours, limit)
        total += hourly_rate * Decimal("2") * h2
        breakdown["2"] += h2
        # next 1 hour: 3x
        if hours > limit:
            h3 = min(hours - limit, Decimal("1"))
            total += hourly_rate * Decimal("3") * h3
            breakdown["3"] += h3
        # remaining: 4x
        if hours > limit + Decimal("1"):
            h4 = hours - limit - Decimal("1")
            total += hourly_rate * Decimal("4") * h4
            breakdown["4"] += h4

    return {"total": _round(total), "breakdown": breakdown}


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

    # ── Holiday set (used by both attendance analysis and overtime calc) ─
    _holidays = holiday_dates or set()

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
    overtime_pay = ZERO
    holiday_overtime_hours = Decimal("0")
    weekday_overtime_hours = Decimal("0")
    saturday_auto_overtime_hours = Decimal("0")
    # Accumulate hours per multiplier across all days
    ot_hours_at_1_5x = Decimal("0")
    ot_hours_at_2x = Decimal("0")
    ot_hours_at_3x = Decimal("0")
    ot_hours_at_4x = Decimal("0")

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
                    if work_schedule == 'five_day' and wd >= 5:
                        is_holiday = True
                    elif work_schedule == 'six_day' and wd == 6:
                        is_holiday = True
            detail = calculate_overtime_pay_detailed(hourly_rate, ot, work_schedule, is_holiday=is_holiday)
            overtime_pay += detail["total"]
            bd = detail["breakdown"]
            ot_hours_at_1_5x += bd["1.5"]
            ot_hours_at_2x += bd["2"]
            ot_hours_at_3x += bd["3"]
            ot_hours_at_4x += bd["4"]
            if is_holiday:
                holiday_overtime_hours += _d(ot)
            else:
                weekday_overtime_hours += _d(ot)

    # Add auto-OT to total (it's not in the DB records, only computed above)
    total_overtime_hours += saturday_auto_overtime_hours

    # ── Commission (sales department only) ───────────────────────────────
    commission = ZERO
    if department == 'sales' and commission_rate > ZERO and sales_revenue > 0:
        commission = _round(_d(sales_revenue) * commission_rate / Decimal("100"))

    # ── Gross salary ─────────────────────────────────────────────────────
    prorated_allowances = _round(total_allowances * proration_factor)
    gross_salary = prorated_salary + prorated_allowances + overtime_pay + commission + leave_compensation

    # ── BPJS + PPh21 ─────────────────────────────────────────────────────
    bpjs_employee_total = ZERO
    bpjs_employer_total = ZERO
    bpjs_breakdown = {}
    pph21 = ZERO
    pph21_ter_rate_pct = 0.0
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
        pph21_ter_rate_pct = float(_ter_rate(gross_salary, ptkp_status) * Decimal("100"))

    elif employment_category == 'contractor':
        # PPh 23: 2.5% deducted from contractor payment
        contractor_tax = _round(gross_salary * CONTRACTOR_TAX_RATE)

    # ── Absence deduction ────────────────────────────────────────────────
    absence_deduction = Decimal('0')

    # ── Leave compensation on termination ────────────────────────────────
    # Indonesian law (UU 13/2003 art. 79, PP 35/2021 art. 15):
    # - Annual leave (cuti tahunan): 12 days/year, earned ONLY after 12 months continuous service
    # - On probation or < 12 months service: NO leave compensation
    # - Daily rate for compensation: monthly salary / 30 (calendar days, not working days)
    # - Only unused days from current leave period are compensated
    leave_compensation = ZERO
    leave_days_entitled = Decimal("0")
    is_termination_month = False
    termination_date_val = getattr(employee, 'termination_date', None)

    if termination_date_val and payroll_year and payroll_month:
        from datetime import date as _date
        term_year = termination_date_val.year
        term_month = termination_date_val.month
        if term_year == payroll_year and term_month == payroll_month:
            is_termination_month = True

            # Check eligibility: must have completed 12+ months AND not on probation
            if hire_date and not is_on_probation:
                months_of_service = (term_year - hire_date.year) * 12 + (term_month - hire_date.month)
                if months_of_service >= 12:
                    # Proportional leave for current year period
                    # Leave period starts on hire anniversary month each year
                    anniversary_month = hire_date.month
                    if term_month >= anniversary_month:
                        months_in_period = term_month - anniversary_month
                    else:
                        months_in_period = 12 - anniversary_month + term_month
                    leave_days_entitled = _round(Decimal(str(months_in_period)) / Decimal("12") * Decimal("12"))
                    # Subtract leave days already taken this period (from attendance)
                    leave_taken = Decimal(str(leave_days))
                    unused_leave = max(leave_days_entitled - leave_taken, ZERO)
                    # PP 35/2021: daily rate = salary / 30 (calendar days)
                    leave_daily_rate = _round(base_salary / Decimal("30"))
                    leave_compensation = _round(unused_leave * leave_daily_rate)

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
        "ot_hours_at_1_5x": float(ot_hours_at_1_5x),
        "ot_hours_at_2x": float(ot_hours_at_2x),
        "ot_hours_at_3x": float(ot_hours_at_3x),
        "ot_hours_at_4x": float(ot_hours_at_4x),

        # Commission
        "commission_rate": float(commission_rate),
        "commission": float(commission),

        # Leave compensation (termination only)
        "is_termination_month": is_termination_month,
        "leave_days_entitled": float(leave_days_entitled),
        "leave_compensation": float(leave_compensation),

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
        "pph21_ter_rate_pct": pph21_ter_rate_pct if employment_category == 'formal' else 0.0,
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
