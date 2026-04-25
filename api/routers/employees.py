"""Employees & Attendance router — HR module CRUD."""

from uuid import UUID
from typing import Optional, List
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import extract

from api.database import get_db
from api.auth import get_current_user
from api.roles import require_management, require_finance
from api.models import Employee, Attendance, Factory, UserFactory, SalaryAdvance

router = APIRouter()


# ── Pydantic schemas ──────────────────────────────────────────

class EmployeeOut(BaseModel):
    id: str
    factory_id: str
    factory_name: Optional[str] = None
    full_name: str
    short_name: Optional[str] = None
    position: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    birth_date: Optional[str] = None
    has_own_bpjs: Optional[bool] = False
    hire_date: Optional[str] = None
    is_active: bool
    employment_type: Optional[str] = None
    department: Optional[str] = None
    work_schedule: Optional[str] = None
    bpjs_mode: Optional[str] = None
    employment_category: Optional[str] = None
    commission_rate: Optional[float] = None
    pay_period: Optional[str] = None
    base_salary: Optional[float] = None
    allowance_bike: Optional[float] = None
    allowance_housing: Optional[float] = None
    allowance_food: Optional[float] = None
    allowance_bpjs: Optional[float] = None
    allowance_other: Optional[float] = None
    allowance_other_note: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class EmployeeCreateInput(BaseModel):
    factory_id: str
    full_name: str
    short_name: Optional[str] = None
    position: str
    phone: Optional[str] = None
    email: Optional[str] = None
    birth_date: Optional[str] = None
    has_own_bpjs: bool = False
    hire_date: Optional[str] = None
    termination_date: Optional[str] = None
    is_active: bool = True
    employment_type: str = "full_time"
    department: str = "production"
    work_schedule: str = "six_day"
    bpjs_mode: str = "company_pays"
    employment_category: str = "formal"
    commission_rate: Optional[float] = None
    pay_period: str = "calendar_month"
    base_salary: float = 0
    allowance_bike: float = 0
    allowance_housing: float = 0
    allowance_food: float = 0
    allowance_bpjs: float = 0
    allowance_other: float = 0
    allowance_other_note: Optional[str] = None


class EmployeeUpdateInput(BaseModel):
    full_name: Optional[str] = None
    short_name: Optional[str] = None
    position: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    birth_date: Optional[str] = None
    has_own_bpjs: Optional[bool] = None
    hire_date: Optional[str] = None
    termination_date: Optional[str] = None
    is_active: Optional[bool] = None
    employment_type: Optional[str] = None
    department: Optional[str] = None
    work_schedule: Optional[str] = None
    bpjs_mode: Optional[str] = None
    employment_category: Optional[str] = None
    commission_rate: Optional[float] = None
    pay_period: Optional[str] = None
    base_salary: Optional[float] = None
    allowance_bike: Optional[float] = None
    allowance_housing: Optional[float] = None
    allowance_food: Optional[float] = None
    allowance_bpjs: Optional[float] = None
    allowance_other: Optional[float] = None
    allowance_other_note: Optional[str] = None


class AttendanceOut(BaseModel):
    id: str
    employee_id: str
    employee_name: Optional[str] = None
    date: str
    status: str
    overtime_hours: float
    hours_worked: Optional[float] = None  # NULL = full day; e.g. 5.0 = came late
    notes: Optional[str] = None
    recorded_by: Optional[str] = None
    created_at: Optional[str] = None


class AttendanceListResponse(BaseModel):
    items: List[AttendanceOut]


class AttendanceCreateInput(BaseModel):
    date: str  # YYYY-MM-DD
    status: str  # present, absent, sick, leave, half_day
    overtime_hours: float = 0
    hours_worked: Optional[float] = None  # NULL = full day; e.g. 5.0 = came late
    notes: Optional[str] = None


class AttendanceUpdateInput(BaseModel):
    status: Optional[str] = None
    overtime_hours: Optional[float] = None
    hours_worked: Optional[float] = None  # NULL = full day; e.g. 5.0 = came late
    notes: Optional[str] = None


class AdvanceCreateInput(BaseModel):
    date: str
    amount: float
    deduct_year: Optional[int] = None   # defaults to date year
    deduct_month: Optional[int] = None  # defaults to date month
    carry_amount: Optional[float] = None  # if set: deduct (amount-carry_amount) this month, carry_amount next month
    notes: Optional[str] = None


class AdvanceUpdateInput(BaseModel):
    date: Optional[str] = None
    amount: Optional[float] = None
    deduct_year: Optional[int] = None
    deduct_month: Optional[int] = None
    notes: Optional[str] = None


class PayrollTotals(BaseModel):
    total_employees: int = 0
    formal_count: int = 0
    contractor_count: int = 0
    total_gross: float = 0.0
    total_bpjs_employer: float = 0.0
    total_bpjs_employee: float = 0.0
    total_pph21: float = 0.0
    total_contractor_tax: float = 0.0
    total_net: float = 0.0
    total_cost: float = 0.0
    total_overtime_pay: float = 0.0
    total_commission: float = 0.0


class PayrollSummaryItem(BaseModel):
    employee_id: str
    full_name: str
    position: str
    department: str
    employment_category: str
    work_schedule: str
    working_days_in_month: int
    present_days: int
    absent_days: int
    sick_days: int
    leave_days: int
    half_days: int
    effective_days: float
    overtime_hours: float
    base_salary: float
    daily_rate: float
    hourly_rate: float
    prorated_salary: float
    allowance_bike: float
    allowance_housing: float
    allowance_food: float
    allowance_bpjs: float
    allowance_other: float
    total_allowances: float
    prorated_allowances: float
    overtime_pay: float
    commission_rate: float
    commission: float
    gross_salary: float
    bpjs_employee: float
    bpjs_employer: float
    pph21: float
    contractor_tax: float
    absence_deduction: float
    total_deductions: float
    net_salary: float
    total_cost_to_company: float
    advances_total: float = 0.0
    net_salary_after_advances: float = 0.0


class PayrollSummaryResponse(BaseModel):
    items: list[PayrollSummaryItem]
    totals: PayrollTotals
    factory_id: Optional[str] = None
    year: int
    month: int


# ── Helpers ───────────────────────────────────────────────────

# Roles that can see salary/financial data
_SALARY_VISIBLE_ROLES = {"owner", "administrator", "ceo", "production_manager"}


def _serialize_employee(emp: Employee, db: Session) -> dict:
    """Full serializer including salary fields — used by management roles."""
    factory = db.query(Factory).filter(Factory.id == emp.factory_id).first()
    return {
        "id": str(emp.id),
        "factory_id": str(emp.factory_id),
        "factory_name": factory.name if factory else None,
        "full_name": emp.full_name,
        "short_name": emp.short_name,
        "position": emp.position,
        "phone": emp.phone,
        "email": emp.email,
        "birth_date": str(emp.birth_date) if emp.birth_date else None,
        "has_own_bpjs": bool(emp.has_own_bpjs) if hasattr(emp, 'has_own_bpjs') else False,
        "hire_date": str(emp.hire_date) if emp.hire_date else None,
        "termination_date": str(emp.termination_date) if emp.termination_date else None,
        "is_active": emp.is_active,
        "employment_type": emp.employment_type or "full_time",
        "department": emp.department or "production",
        "work_schedule": emp.work_schedule or "six_day",
        "bpjs_mode": emp.bpjs_mode or "company_pays",
        "employment_category": emp.employment_category or "formal",
        "commission_rate": float(emp.commission_rate) if emp.commission_rate is not None else None,
        "pay_period": emp.pay_period or "calendar_month",
        "base_salary": float(emp.base_salary or 0),
        "allowance_bike": float(emp.allowance_bike or 0),
        "allowance_housing": float(emp.allowance_housing or 0),
        "allowance_food": float(emp.allowance_food or 0),
        "allowance_bpjs": float(emp.allowance_bpjs or 0),
        "allowance_other": float(emp.allowance_other or 0),
        "allowance_other_note": emp.allowance_other_note,
        "created_at": emp.created_at.isoformat() if emp.created_at else None,
        "updated_at": emp.updated_at.isoformat() if emp.updated_at else None,
    }


def _serialize_employee_public(emp: Employee, db: Session) -> dict:
    """Public serializer — NO salary, allowance, or BPJS fields."""
    factory = db.query(Factory).filter(Factory.id == emp.factory_id).first()
    return {
        "id": str(emp.id),
        "factory_id": str(emp.factory_id),
        "factory_name": factory.name if factory else None,
        "full_name": emp.full_name,
        "short_name": emp.short_name,
        "position": emp.position,
        "department": emp.department or "production",
        "phone": emp.phone,
        "email": emp.email,
        "is_active": emp.is_active,
    }


def _get_user_factory_ids(user, db: Session) -> set:
    """Return set of factory UUIDs the user is assigned to."""
    rows = db.query(UserFactory.factory_id).filter(UserFactory.user_id == user.id).all()
    return {r.factory_id for r in rows}


def _serialize_attendance(att: Attendance, db: Session) -> dict:
    emp = db.query(Employee).filter(Employee.id == att.employee_id).first()
    return {
        "id": str(att.id),
        "employee_id": str(att.employee_id),
        "employee_name": emp.full_name if emp else None,
        "date": str(att.date),
        "status": att.status,
        "overtime_hours": float(att.overtime_hours or 0),
        "hours_worked": float(att.hours_worked) if att.hours_worked is not None else None,
        "notes": att.notes,
        "recorded_by": str(att.recorded_by) if att.recorded_by else None,
        "created_at": att.created_at.isoformat() if att.created_at else None,
    }


# ── Employee endpoints ────────────────────────────────────────

@router.get("")
async def list_employees(
    factory_id: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    department: Optional[str] = Query(None),
    employment_category: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List employees, optionally filtered by factory, active status, department, and category."""
    role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)

    query = db.query(Employee)

    # MEDIUM #7: Factory scoping — non-global roles only see employees from their factories
    if role not in ("owner", "administrator"):
        user_factory_ids = _get_user_factory_ids(current_user, db)
        if user_factory_ids:
            query = query.filter(Employee.factory_id.in_(user_factory_ids))
        else:
            # User has no factory assignments → empty result
            return {"items": [], "total": 0, "page": page, "per_page": per_page}

    if factory_id:
        query = query.filter(Employee.factory_id == UUID(factory_id))
    if is_active is not None:
        query = query.filter(Employee.is_active == is_active)
    if department:
        query = query.filter(Employee.department == department)
    if employment_category:
        query = query.filter(Employee.employment_category == employment_category)

    total = query.count()
    items = (
        query.order_by(Employee.full_name)
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    # HIGH #1: Only management roles see salary data
    serializer = _serialize_employee if role in _SALARY_VISIBLE_ROLES else _serialize_employee_public

    return {
        "items": [serializer(e, db) for e in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/payroll-summary", response_model=PayrollSummaryResponse)
async def payroll_summary(
    factory_id: Optional[str] = Query(None, description="Factory UUID (omit for all factories)"),
    year: int = Query(..., description="Year"),
    month: int = Query(..., ge=1, le=12, description="Month 1-12"),
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Calculate full payroll summary with Indonesian tax/BPJS for a given month."""
    from business.services.payroll import calculate_monthly_payroll
    from api.models import FactoryCalendar
    import calendar
    from datetime import date as _date

    # Include active employees + terminated employees whose termination_date falls in this month
    from sqlalchemy import or_
    query = db.query(Employee).filter(
        or_(
            Employee.is_active == True,
            # Include terminated employees for their final payroll month
            (Employee.termination_date.isnot(None))
            & (extract("year", Employee.termination_date) == year)
            & (extract("month", Employee.termination_date) == month),
        )
    )
    if factory_id:
        fid = UUID(factory_id)
        query = query.filter(Employee.factory_id == fid)

    employees = query.order_by(Employee.full_name).all()

    # Load holiday dates from factory calendar for OT multiplier calculation
    holiday_query = db.query(FactoryCalendar.date, FactoryCalendar.factory_id).filter(
        FactoryCalendar.is_working_day == False,
        extract("year", FactoryCalendar.date) == year,
        extract("month", FactoryCalendar.date) == month,
    )
    # Group holidays by factory_id for multi-factory payroll
    _factory_holidays: dict[str, set] = {}
    for row in holiday_query.all():
        fid_str = str(row.factory_id)
        _factory_holidays.setdefault(fid_str, set()).add(row.date)

    # Pre-compute working days for calendar month
    # Must subtract holidays from factory calendar (not just raw weekday count)
    cal = calendar.Calendar()
    month_days_list = list(cal.itermonthdays2(year, month))

    # Collect ALL holiday dates across all factories for this month
    all_holiday_dates: set = set()
    for dates_set in _factory_holidays.values():
        all_holiday_dates.update(dates_set)

    # Per-factory working day counts (holidays differ per factory)
    def _working_days_for_factory(fid_str: str, six_day: bool) -> int:
        fac_holidays = _factory_holidays.get(fid_str, set())
        count = 0
        for day_num, wd in month_days_list:
            if day_num == 0:
                continue
            d = _date(year, month, day_num)
            if d in fac_holidays:
                continue  # holiday — not a working day
            if six_day and wd < 6:
                count += 1
            elif not six_day and wd < 5:
                count += 1
        return count

    # Fallback: raw weekday count (used only if no factory calendar)
    weekdays_in_month = sum(1 for day, wd in month_days_list if day != 0 and wd < 5)
    six_day_working = sum(1 for day, wd in month_days_list if day != 0 and wd < 6)

    # Pre-compute working days for 25-to-24 period
    def _working_days_in_range(start: _date, end: _date, six_day: bool, fid_str: str = "") -> int:
        fac_holidays = _factory_holidays.get(fid_str, set())
        count = 0
        cur = start
        while cur <= end:
            if cur not in fac_holidays:
                wd = cur.weekday()
                if six_day and wd < 6:
                    count += 1
                elif not six_day and wd < 5:
                    count += 1
            from datetime import timedelta
            cur += timedelta(days=1)
        return count

    result = []
    totals = {
        "total_employees": 0,
        "formal_count": 0,
        "contractor_count": 0,
        "total_gross": 0.0,
        "total_bpjs_employer": 0.0,
        "total_bpjs_employee": 0.0,
        "total_company_bpjs_for_employee": 0.0,
        "total_pph21": 0.0,
        "total_pph21_borne_by_company": 0.0,
        "total_contractor_tax": 0.0,
        "total_net": 0.0,
        "total_cost": 0.0,
        "total_overtime_pay": 0.0,
        "total_commission": 0.0,
    }

    for emp in employees:
        pay_period = getattr(emp, 'pay_period', 'calendar_month') or 'calendar_month'
        ws = getattr(emp, 'work_schedule', 'six_day') or 'six_day'

        if pay_period == '25_to_24':
            # Period: 25th of previous month to 24th of current month
            prev_month = month - 1 if month > 1 else 12
            prev_year = year if month > 1 else year - 1
            period_start = _date(prev_year, prev_month, 25)
            period_end = _date(year, month, 24)
            attendance_records = (
                db.query(Attendance)
                .filter(
                    Attendance.employee_id == emp.id,
                    Attendance.date >= period_start,
                    Attendance.date <= period_end,
                )
                .all()
            )
            emp_fid = str(emp.factory_id) if emp.factory_id else ""
            working_days = _working_days_in_range(period_start, period_end, ws == 'six_day', emp_fid)
        else:
            # Calendar month
            attendance_records = (
                db.query(Attendance)
                .filter(
                    Attendance.employee_id == emp.id,
                    extract("year", Attendance.date) == year,
                    extract("month", Attendance.date) == month,
                )
                .all()
            )
            emp_fid = str(emp.factory_id) if emp.factory_id else ""
            # Use factory-specific working days (subtracting holidays)
            if _factory_holidays.get(emp_fid):
                working_days = _working_days_for_factory(emp_fid, ws == 'six_day')
            else:
                working_days = six_day_working if ws == 'six_day' else weekdays_in_month

        # Get holiday dates for this employee's factory (already resolved emp_fid above)
        emp_holidays = _factory_holidays.get(emp_fid, set())

        payroll = calculate_monthly_payroll(
            employee=emp,
            attendance_records=attendance_records,
            working_days_in_month=working_days,
            payroll_year=year,
            payroll_month=month,
            holiday_dates=emp_holidays,
        )

        # Load advances deductible in this pay period (by deduct_year/month, fallback to date)
        from sqlalchemy import or_ as _or_, and_ as _and_
        if pay_period == '25_to_24':
            # For 25-to-24 period we use the deduction month matching this calendar month
            advances_q = db.query(SalaryAdvance).filter(
                SalaryAdvance.employee_id == emp.id,
                _or_(
                    _and_(SalaryAdvance.deduct_year == year, SalaryAdvance.deduct_month == month),
                    _and_(SalaryAdvance.deduct_year.is_(None),
                          SalaryAdvance.date >= period_start,
                          SalaryAdvance.date <= period_end),
                ),
            )
        else:
            advances_q = db.query(SalaryAdvance).filter(
                SalaryAdvance.employee_id == emp.id,
                _or_(
                    _and_(SalaryAdvance.deduct_year == year, SalaryAdvance.deduct_month == month),
                    _and_(SalaryAdvance.deduct_year.is_(None),
                          extract("year", SalaryAdvance.date) == year,
                          extract("month", SalaryAdvance.date) == month),
                ),
            )
        advances_total = float(sum(float(a.amount) for a in advances_q.all()))
        payroll["advances_total"] = advances_total
        payroll["net_salary_after_advances"] = round(payroll["net_salary"] - advances_total, 2)

        result.append(payroll)

        # Accumulate totals
        totals["total_employees"] += 1
        cat = payroll.get("employment_category", "formal")
        if cat == "formal":
            totals["formal_count"] += 1
        else:
            totals["contractor_count"] += 1
        totals["total_gross"] += payroll["gross_salary"]
        totals["total_bpjs_employer"] += payroll["bpjs_employer"]
        totals["total_bpjs_employee"] += payroll["bpjs_employee"]
        totals["total_company_bpjs_for_employee"] += payroll.get("company_bpjs_for_employee", 0)
        totals["total_pph21"] += payroll["pph21"]
        totals["total_pph21_borne_by_company"] += payroll.get("pph21_borne_by_company", 0)
        totals["total_contractor_tax"] += payroll["contractor_tax"]
        totals["total_net"] += payroll["net_salary"]
        totals["total_cost"] += payroll["total_cost_to_company"]
        totals["total_overtime_pay"] += payroll["overtime_pay"]
        totals["total_commission"] += payroll["commission"]

    return {
        "items": result,
        "totals": totals,
        "factory_id": factory_id,
        "year": year,
        "month": month,
    }


@router.get("/hr-costs/yearly")
async def hr_costs_yearly(
    year: int = Query(..., description="Calendar year"),
    factory_id: Optional[str] = Query(None, description="Factory UUID (omit for all factories)"),
    db: Session = Depends(get_db),
    current_user=Depends(require_finance),
):
    """Yearly HR costs breakdown by month — for owner/ceo visibility.

    Returns 12 months of payroll totals including terminated employees,
    leave compensation, BPJS, PPh21, and total cost to company.
    """
    from datetime import date as _date

    months_data = []
    year_totals = {
        "total_employees": 0,  # max across months
        "total_gross": 0.0,
        "total_bpjs_employer": 0.0,
        "total_company_bpjs_for_employee": 0.0,
        "total_pph21": 0.0,
        "total_contractor_tax": 0.0,
        "total_net": 0.0,
        "total_cost": 0.0,
        "total_overtime_pay": 0.0,
        "total_commission": 0.0,
        "total_leave_compensation": 0.0,
        "terminations_count": 0,
    }
    year_by_department: dict[str, dict] = {}

    # Only iterate through months up to current month (no future data)
    today = _date.today()
    max_month = 12
    if year == today.year:
        max_month = today.month
    elif year > today.year:
        max_month = 0

    for m in range(1, max_month + 1):
        try:
            summary = await payroll_summary(
                factory_id=factory_id,
                year=year,
                month=m,
                db=db,
                current_user=current_user,
            )
        except Exception as e:
            # Skip months that fail to compute
            months_data.append({
                "month": m,
                "error": str(e),
                "total_employees": 0,
                "total_gross": 0,
                "total_cost": 0,
            })
            continue

        totals = summary.get("totals", {})
        items = summary.get("items", [])

        # Count leave compensation + terminations for this month
        leave_comp_total = sum(item.get("leave_compensation", 0) or 0 for item in items)
        terminations = sum(1 for item in items if item.get("is_termination_month"))

        # Breakdown by department (production / sales / administration / ...)
        by_department: dict[str, dict] = {}
        for item in items:
            dept = (item.get("department") or "production").lower()
            bucket = by_department.setdefault(dept, {
                "department": dept,
                "employees": 0,
                "total_gross": 0.0,
                "total_bpjs_employer": 0.0,
                "total_pph21": 0.0,
                "total_contractor_tax": 0.0,
                "total_net": 0.0,
                "total_cost": 0.0,
                "total_overtime_pay": 0.0,
                "total_commission": 0.0,
                "leave_compensation": 0.0,
            })
            bucket["employees"] += 1
            bucket["total_gross"] += float(item.get("gross_salary", 0) or 0)
            bucket["total_bpjs_employer"] += float(item.get("bpjs_employer", 0) or 0)
            bucket["total_pph21"] += float(item.get("pph21", 0) or 0)
            bucket["total_contractor_tax"] += float(item.get("contractor_tax", 0) or 0)
            bucket["total_net"] += float(item.get("net_salary", 0) or 0)
            bucket["total_cost"] += float(item.get("total_cost_to_company", 0) or 0)
            bucket["total_overtime_pay"] += float(item.get("overtime_pay", 0) or 0)
            bucket["total_commission"] += float(item.get("commission", 0) or 0)
            bucket["leave_compensation"] += float(item.get("leave_compensation", 0) or 0)

        month_entry = {
            "month": m,
            "month_name": _date(year, m, 1).strftime("%B"),
            "total_employees": totals.get("total_employees", 0),
            "formal_count": totals.get("formal_count", 0),
            "contractor_count": totals.get("contractor_count", 0),
            "total_gross": totals.get("total_gross", 0),
            "total_bpjs_employer": totals.get("total_bpjs_employer", 0),
            "total_company_bpjs_for_employee": totals.get("total_company_bpjs_for_employee", 0),
            "total_pph21": totals.get("total_pph21", 0),
            "total_pph21_borne_by_company": totals.get("total_pph21_borne_by_company", 0),
            "total_contractor_tax": totals.get("total_contractor_tax", 0),
            "total_net": totals.get("total_net", 0),
            "total_cost": totals.get("total_cost", 0),
            "total_overtime_pay": totals.get("total_overtime_pay", 0),
            "total_commission": totals.get("total_commission", 0),
            "leave_compensation": leave_comp_total,
            "terminations": terminations,
            "by_department": list(by_department.values()),
        }
        months_data.append(month_entry)

        # Accumulate year totals
        year_totals["total_employees"] = max(year_totals["total_employees"], month_entry["total_employees"])
        year_totals["total_gross"] += month_entry["total_gross"]
        year_totals["total_bpjs_employer"] += month_entry["total_bpjs_employer"]
        year_totals["total_company_bpjs_for_employee"] += month_entry["total_company_bpjs_for_employee"]
        year_totals["total_pph21"] += month_entry["total_pph21"]
        year_totals["total_contractor_tax"] += month_entry["total_contractor_tax"]
        year_totals["total_net"] += month_entry["total_net"]
        year_totals["total_cost"] += month_entry["total_cost"]
        year_totals["total_overtime_pay"] += month_entry["total_overtime_pay"]
        year_totals["total_commission"] += month_entry["total_commission"]
        year_totals["total_leave_compensation"] += leave_comp_total
        year_totals["terminations_count"] += terminations

        # Accumulate by-department year totals
        for dept_entry in by_department.values():
            d = dept_entry["department"]
            ybucket = year_by_department.setdefault(d, {
                "department": d,
                "peak_employees": 0,
                "total_gross": 0.0,
                "total_bpjs_employer": 0.0,
                "total_pph21": 0.0,
                "total_contractor_tax": 0.0,
                "total_net": 0.0,
                "total_cost": 0.0,
                "total_overtime_pay": 0.0,
                "total_commission": 0.0,
                "leave_compensation": 0.0,
            })
            ybucket["peak_employees"] = max(ybucket["peak_employees"], dept_entry["employees"])
            ybucket["total_gross"] += dept_entry["total_gross"]
            ybucket["total_bpjs_employer"] += dept_entry["total_bpjs_employer"]
            ybucket["total_pph21"] += dept_entry["total_pph21"]
            ybucket["total_contractor_tax"] += dept_entry["total_contractor_tax"]
            ybucket["total_net"] += dept_entry["total_net"]
            ybucket["total_cost"] += dept_entry["total_cost"]
            ybucket["total_overtime_pay"] += dept_entry["total_overtime_pay"]
            ybucket["total_commission"] += dept_entry["total_commission"]
            ybucket["leave_compensation"] += dept_entry["leave_compensation"]

    return {
        "year": year,
        "factory_id": factory_id,
        "months": months_data,
        "year_totals": year_totals,
        "by_department": list(year_by_department.values()),
    }


@router.get("/hr-costs/employee/{employee_id}/history")
async def hr_costs_employee_history(
    employee_id: UUID,
    year: int = Query(..., description="Calendar year"),
    db: Session = Depends(get_db),
    current_user=Depends(require_finance),
):
    """Per-employee monthly payroll history for a year — for owner/ceo drill-down."""
    from business.services.payroll import calculate_monthly_payroll
    from api.models import FactoryCalendar
    import calendar as _cal
    from datetime import date as _date

    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    ws = getattr(emp, 'work_schedule', 'six_day') or 'six_day'
    emp_fid = str(emp.factory_id) if emp.factory_id else ""

    # Limit to months when employee was employed
    hire_month = 1
    if emp.hire_date and emp.hire_date.year == year:
        hire_month = emp.hire_date.month
    elif emp.hire_date and emp.hire_date.year > year:
        return {"employee_id": str(emp.id), "full_name": emp.full_name, "year": year, "months": []}

    term_month = 12
    if emp.termination_date and emp.termination_date.year == year:
        term_month = emp.termination_date.month
    elif emp.termination_date and emp.termination_date.year < year:
        return {"employee_id": str(emp.id), "full_name": emp.full_name, "year": year, "months": []}

    today = _date.today()
    if year == today.year:
        term_month = min(term_month, today.month)
    elif year > today.year:
        return {"employee_id": str(emp.id), "full_name": emp.full_name, "year": year, "months": []}

    months_data = []
    for m in range(hire_month, term_month + 1):
        attendance_records = (
            db.query(Attendance)
            .filter(
                Attendance.employee_id == emp.id,
                extract("year", Attendance.date) == year,
                extract("month", Attendance.date) == m,
            )
            .all()
        )

        # Working days in month
        cal = _cal.Calendar()
        month_days = list(cal.itermonthdays2(year, m))
        if ws == 'six_day':
            working_days = sum(1 for _, wd in month_days if 0 <= wd <= 5)
        else:
            working_days = sum(1 for _, wd in month_days if 0 <= wd <= 4)

        # Holidays for this factory
        holiday_rows = db.query(FactoryCalendar.date).filter(
            FactoryCalendar.factory_id == emp.factory_id,
            FactoryCalendar.is_working_day == False,
            extract("year", FactoryCalendar.date) == year,
            extract("month", FactoryCalendar.date) == m,
        ).all()
        emp_holidays = {row.date for row in holiday_rows}
        working_days = max(working_days - len(emp_holidays), 1)

        payroll = calculate_monthly_payroll(
            employee=emp,
            attendance_records=attendance_records,
            working_days_in_month=working_days,
            payroll_year=year,
            payroll_month=m,
            holiday_dates=emp_holidays,
        )

        months_data.append({
            "month": m,
            "month_name": _date(year, m, 1).strftime("%B"),
            **{k: payroll.get(k) for k in [
                "present_days", "absent_days", "sick_days", "leave_days",
                "gross_salary", "net_salary", "total_cost_to_company",
                "bpjs_employer", "pph21", "overtime_pay", "commission",
                "leave_compensation", "is_termination_month",
            ]},
        })

    return {
        "employee_id": str(emp.id),
        "full_name": emp.full_name,
        "position": emp.position,
        "hire_date": str(emp.hire_date) if emp.hire_date else None,
        "termination_date": str(emp.termination_date) if emp.termination_date else None,
        "year": year,
        "months": months_data,
    }


@router.get("/payroll-pdf")
async def payroll_pdf(
    factory_id: Optional[str] = Query(None),
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Generate and return payroll summary as PDF."""
    from fastapi.responses import StreamingResponse
    from business.services.payroll_pdf import generate_payroll_summary_pdf

    # Reuse payroll_summary logic — call the existing endpoint function
    summary = await payroll_summary(
        factory_id=factory_id,
        year=year,
        month=month,
        db=db,
        current_user=current_user,
    )

    factory_name = ""
    if factory_id:
        from api.models import Factory
        fac = db.query(Factory).filter(Factory.id == UUID(factory_id)).first()
        factory_name = fac.name if fac else ""

    buf = generate_payroll_summary_pdf(
        payroll_items=summary["items"],
        totals=summary["totals"],
        year=year,
        month=month,
        factory_name=factory_name,
    )

    month_str = str(month).zfill(2)
    filename = f"payroll_{year}_{month_str}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/payroll-pdf-employee")
async def payroll_pdf_employee(
    employee_id: str = Query(...),
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Generate and return individual employee payslip as PDF."""
    from fastapi.responses import StreamingResponse
    from business.services.payroll_pdf import generate_payslip_pdf
    from api.models import Employee as EmployeeModel, Factory

    emp = db.query(EmployeeModel).filter(EmployeeModel.id == UUID(employee_id)).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    factory_name = ""
    if emp.factory_id:
        fac = db.query(Factory).filter(Factory.id == emp.factory_id).first()
        factory_name = fac.name if fac else ""

    # Calculate payroll for this employee
    from business.services.payroll import calculate_monthly_payroll
    from api.models import FactoryCalendar
    import calendar as _cal

    ws = getattr(emp, 'work_schedule', 'six_day') or 'six_day'
    pay_period = getattr(emp, "pay_period", "calendar_month") or "calendar_month"

    # Load attendance records
    if pay_period == "25_to_24":
        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        period_start = date(prev_year, prev_month, 25)
        period_end = date(year, month, 24)
        attendance_records = db.query(Attendance).filter(
            Attendance.employee_id == emp.id,
            Attendance.date >= period_start,
            Attendance.date <= period_end,
        ).all()
        working_days = sum(
            1 for d in range((period_end - period_start).days + 1)
            if (period_start + timedelta(days=d)).weekday() < (6 if ws == 'six_day' else 5)
        )
    else:
        attendance_records = db.query(Attendance).filter(
            Attendance.employee_id == emp.id,
            extract("year", Attendance.date) == year,
            extract("month", Attendance.date) == month,
        ).all()
        month_days_list = list(_cal.Calendar().itermonthdays2(year, month))
        if ws == 'six_day':
            working_days = sum(1 for day, wd in month_days_list if day != 0 and wd < 6)
        else:
            working_days = sum(1 for day, wd in month_days_list if day != 0 and wd < 5)

    # Load holiday dates and subtract from working days
    emp_holidays = set()
    if emp.factory_id:
        for row in db.query(FactoryCalendar.date).filter(
            FactoryCalendar.factory_id == emp.factory_id,
            FactoryCalendar.is_working_day == False,
            extract("year", FactoryCalendar.date) == year,
            extract("month", FactoryCalendar.date) == month,
        ).all():
            emp_holidays.add(row[0])

    # Subtract factory holidays from working days count
    if emp_holidays and pay_period == "calendar_month":
        month_days_list2 = list(_cal.Calendar().itermonthdays2(year, month))
        count = 0
        for day_num, wd in month_days_list2:
            if day_num == 0:
                continue
            d = date(year, month, day_num)
            if d in emp_holidays:
                continue
            if ws == 'six_day' and wd < 6:
                count += 1
            elif ws != 'six_day' and wd < 5:
                count += 1
        working_days = count

    payroll = calculate_monthly_payroll(
        employee=emp,
        attendance_records=attendance_records,
        working_days_in_month=working_days,
        payroll_year=year,
        payroll_month=month,
        holiday_dates=emp_holidays,
    )

    buf = generate_payslip_pdf(
        item=payroll,
        year=year,
        month=month,
        factory_name=factory_name,
    )

    emp_name = (emp.full_name or "employee").replace(" ", "_")
    month_str = str(month).zfill(2)
    filename = f"payslip_{emp_name}_{year}_{month_str}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{employee_id}", response_model=EmployeeOut)
async def get_employee(
    employee_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get a single employee by ID."""
    role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)

    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(404, "Employee not found")

    # MEDIUM #7: Factory scoping — non-admin users can only view employees in their factories
    if role not in ("owner", "administrator"):
        user_factory_ids = _get_user_factory_ids(current_user, db)
        if emp.factory_id not in user_factory_ids:
            raise HTTPException(404, "Employee not found")

    # HIGH #1: Only management roles see salary data
    serializer = _serialize_employee if role in _SALARY_VISIBLE_ROLES else _serialize_employee_public
    return serializer(emp, db)


@router.post("", status_code=201)
async def create_employee(
    data: EmployeeCreateInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Create a new employee."""
    fid = UUID(data.factory_id)
    factory = db.query(Factory).filter(Factory.id == fid).first()
    if not factory:
        raise HTTPException(404, "Factory not found")

    emp = Employee(
        factory_id=fid,
        full_name=data.full_name,
        short_name=data.short_name,
        position=data.position,
        phone=data.phone,
        email=data.email,
        birth_date=date.fromisoformat(data.birth_date) if data.birth_date else None,
        has_own_bpjs=data.has_own_bpjs,
        hire_date=date.fromisoformat(data.hire_date) if data.hire_date else None,
        termination_date=date.fromisoformat(data.termination_date) if data.termination_date else None,
        is_active=data.is_active,
        employment_type=data.employment_type,
        department=data.department,
        work_schedule=data.work_schedule,
        bpjs_mode=data.bpjs_mode,
        employment_category=data.employment_category,
        commission_rate=data.commission_rate,
        pay_period=data.pay_period,
        base_salary=data.base_salary,
        allowance_bike=data.allowance_bike,
        allowance_housing=data.allowance_housing,
        allowance_food=data.allowance_food,
        allowance_bpjs=data.allowance_bpjs,
        allowance_other=data.allowance_other,
        allowance_other_note=data.allowance_other_note,
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return _serialize_employee(emp, db)


@router.patch("/{employee_id}")
async def update_employee(
    employee_id: UUID,
    data: EmployeeUpdateInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Update an employee. Partial update."""
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(404, "Employee not found")

    update_data = data.model_dump(exclude_unset=True)
    # Convert date strings to date objects, empty strings to None
    for date_field in ("hire_date", "birth_date", "termination_date"):
        if date_field in update_data:
            val = update_data[date_field]
            if val and isinstance(val, str):
                update_data[date_field] = date.fromisoformat(val)
            elif not val:
                update_data[date_field] = None

    for key, value in update_data.items():
        setattr(emp, key, value)

    db.commit()
    db.refresh(emp)
    return _serialize_employee(emp, db)


@router.delete("/{employee_id}")
async def deactivate_employee(
    employee_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Soft-delete: set is_active=False."""
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(404, "Employee not found")
    emp.is_active = False
    db.commit()
    return {"status": "deactivated", "id": str(emp.id)}


# ── Attendance endpoints ──────────────────────────────────────

@router.get("/{employee_id}/attendance", response_model=AttendanceListResponse)
async def get_attendance(
    employee_id: UUID,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None, ge=1, le=12),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get attendance records for an employee, filtered by date range or year/month."""
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(404, "Employee not found")

    query = db.query(Attendance).filter(Attendance.employee_id == employee_id)

    if start_date:
        query = query.filter(Attendance.date >= date.fromisoformat(start_date))
    if end_date:
        query = query.filter(Attendance.date <= date.fromisoformat(end_date))
    if year:
        query = query.filter(extract("year", Attendance.date) == year)
    if month:
        query = query.filter(extract("month", Attendance.date) == month)

    items = query.order_by(Attendance.date).all()
    return {"items": [_serialize_attendance(a, db) for a in items]}


@router.post("/{employee_id}/attendance", status_code=201)
async def record_attendance(
    employee_id: UUID,
    data: AttendanceCreateInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Record attendance for an employee on a date."""
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(404, "Employee not found")

    VALID_STATUSES = {"present", "absent", "sick", "leave", "half_day"}
    if data.status not in VALID_STATUSES:
        raise HTTPException(422, f"Invalid status. Must be one of: {', '.join(VALID_STATUSES)}")

    try:
        att_date = date.fromisoformat(data.date)
    except (ValueError, TypeError):
        raise HTTPException(422, f"Invalid date: {data.date}")

    # Check for duplicate
    existing = (
        db.query(Attendance)
        .filter(Attendance.employee_id == employee_id, Attendance.date == att_date)
        .first()
    )
    if existing:
        raise HTTPException(409, f"Attendance already recorded for {data.date}. Use PATCH to update.")

    att = Attendance(
        employee_id=employee_id,
        date=att_date,
        status=data.status,
        overtime_hours=data.overtime_hours,
        hours_worked=data.hours_worked,
        notes=data.notes,
        recorded_by=current_user.id,
    )
    db.add(att)
    db.commit()
    db.refresh(att)
    return _serialize_attendance(att, db)


@router.patch("/attendance/{attendance_id}")
async def update_attendance(
    attendance_id: UUID,
    data: AttendanceUpdateInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Update an attendance record."""
    att = db.query(Attendance).filter(Attendance.id == attendance_id).first()
    if not att:
        raise HTTPException(404, "Attendance record not found")

    VALID_STATUSES = {"present", "absent", "sick", "leave", "half_day"}
    update_data = data.model_dump(exclude_unset=True)

    if "status" in update_data and update_data["status"] not in VALID_STATUSES:
        raise HTTPException(422, f"Invalid status. Must be one of: {', '.join(VALID_STATUSES)}")

    for key, value in update_data.items():
        setattr(att, key, value)

    db.commit()
    db.refresh(att)
    return _serialize_attendance(att, db)


@router.delete("/attendance/{attendance_id}")
async def delete_attendance(
    attendance_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Delete (reset) an attendance record for a specific day."""
    att = db.query(Attendance).filter(Attendance.id == attendance_id).first()
    if not att:
        raise HTTPException(404, "Attendance record not found")

    db.delete(att)
    db.commit()
    return {"status": "deleted", "id": str(attendance_id)}


# ── Salary Advance endpoints ──────────────────────────────────

def _serialize_advance(adv: SalaryAdvance) -> dict:
    # Effective deduction month — fallback to advance date if not explicitly set
    eff_year = adv.deduct_year if adv.deduct_year else adv.date.year
    eff_month = adv.deduct_month if adv.deduct_month else adv.date.month
    return {
        "id": str(adv.id),
        "employee_id": str(adv.employee_id),
        "date": str(adv.date),
        "amount": float(adv.amount),
        "deduct_year": eff_year,
        "deduct_month": eff_month,
        "notes": adv.notes,
        "recorded_by": str(adv.recorded_by) if adv.recorded_by else None,
        "created_at": adv.created_at.isoformat() if adv.created_at else None,
    }


@router.get("/{employee_id}/advances")
async def get_advances(
    employee_id: UUID,
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None, ge=1, le=12),
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """List salary advances for an employee.

    Filters by the effective deduction month (deduct_year/deduct_month if set,
    otherwise falls back to the advance date's year/month).
    """
    from sqlalchemy import or_, and_
    query = db.query(SalaryAdvance).filter(SalaryAdvance.employee_id == employee_id)
    if year and month:
        query = query.filter(
            or_(
                and_(SalaryAdvance.deduct_year == year, SalaryAdvance.deduct_month == month),
                and_(SalaryAdvance.deduct_year.is_(None),
                     extract("year", SalaryAdvance.date) == year,
                     extract("month", SalaryAdvance.date) == month),
            )
        )
    elif year:
        query = query.filter(
            or_(
                SalaryAdvance.deduct_year == year,
                and_(SalaryAdvance.deduct_year.is_(None), extract("year", SalaryAdvance.date) == year),
            )
        )
    items = query.order_by(SalaryAdvance.date).all()
    return {"items": [_serialize_advance(a) for a in items]}


@router.post("/{employee_id}/advances", status_code=201)
async def create_advance(
    employee_id: UUID,
    data: AdvanceCreateInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Record a salary advance payment for an employee."""
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(404, "Employee not found")
    try:
        adv_date = date.fromisoformat(data.date)
    except (ValueError, TypeError):
        raise HTTPException(422, f"Invalid date: {data.date}")
    if data.amount <= 0:
        raise HTTPException(422, "Amount must be positive")

    # Resolve effective deduction month
    ded_year = data.deduct_year or adv_date.year
    ded_month = data.deduct_month or adv_date.month

    # Handle carry-over split: deduct (amount - carry_amount) this month, carry_amount next month
    carry = data.carry_amount
    if carry is not None:
        if carry <= 0 or carry >= data.amount:
            raise HTTPException(422, "carry_amount must be between 0 and amount (exclusive)")
        this_month_amount = round(data.amount - carry, 2)
        # Next deduction month
        if ded_month == 12:
            next_year, next_month = ded_year + 1, 1
        else:
            next_year, next_month = ded_year, ded_month + 1

        adv_this = SalaryAdvance(
            employee_id=employee_id, date=adv_date,
            amount=this_month_amount, deduct_year=ded_year, deduct_month=ded_month,
            notes=data.notes, recorded_by=current_user.id,
        )
        adv_next = SalaryAdvance(
            employee_id=employee_id, date=adv_date,
            amount=carry, deduct_year=next_year, deduct_month=next_month,
            notes=f"[carry-over] {data.notes or ''}".strip(),
            recorded_by=current_user.id,
        )
        db.add_all([adv_this, adv_next])
        db.commit()
        db.refresh(adv_this)
        db.refresh(adv_next)
        return {"items": [_serialize_advance(adv_this), _serialize_advance(adv_next)]}

    adv = SalaryAdvance(
        employee_id=employee_id, date=adv_date,
        amount=data.amount, deduct_year=ded_year, deduct_month=ded_month,
        notes=data.notes, recorded_by=current_user.id,
    )
    db.add(adv)
    db.commit()
    db.refresh(adv)
    return _serialize_advance(adv)


@router.patch("/advances/{advance_id}")
async def update_advance(
    advance_id: UUID,
    data: AdvanceUpdateInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Update a salary advance record."""
    adv = db.query(SalaryAdvance).filter(SalaryAdvance.id == advance_id).first()
    if not adv:
        raise HTTPException(404, "Advance not found")
    update_data = data.model_dump(exclude_unset=True)
    if "date" in update_data:
        try:
            update_data["date"] = date.fromisoformat(update_data["date"])
        except (ValueError, TypeError):
            raise HTTPException(422, f"Invalid date: {update_data['date']}")
    if "amount" in update_data and update_data["amount"] <= 0:
        raise HTTPException(422, "Amount must be positive")
    for key, value in update_data.items():
        setattr(adv, key, value)
    db.commit()
    db.refresh(adv)
    return _serialize_advance(adv)


@router.delete("/advances/{advance_id}")
async def delete_advance(
    advance_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Delete a salary advance record."""
    adv = db.query(SalaryAdvance).filter(SalaryAdvance.id == advance_id).first()
    if not adv:
        raise HTTPException(404, "Advance not found")
    db.delete(adv)
    db.commit()
    return {"status": "deleted", "id": str(advance_id)}
