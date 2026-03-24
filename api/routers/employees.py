"""Employees & Attendance router — HR module CRUD."""

from uuid import UUID
from typing import Optional, List
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import extract

from api.database import get_db
from api.auth import get_current_user
from api.roles import require_management
from api.models import Employee, Attendance, Factory

router = APIRouter()


# ── Pydantic schemas ──────────────────────────────────────────

class EmployeeOut(BaseModel):
    id: str
    factory_id: str
    factory_name: Optional[str] = None
    full_name: str
    position: str
    phone: Optional[str] = None
    hire_date: Optional[str] = None
    is_active: bool
    employment_type: str
    base_salary: float
    allowance_bike: float
    allowance_housing: float
    allowance_food: float
    allowance_bpjs: float
    allowance_other: float
    allowance_other_note: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class EmployeeCreateInput(BaseModel):
    factory_id: str
    full_name: str
    position: str
    phone: Optional[str] = None
    hire_date: Optional[str] = None
    is_active: bool = True
    employment_type: str = "full_time"
    base_salary: float = 0
    allowance_bike: float = 0
    allowance_housing: float = 0
    allowance_food: float = 0
    allowance_bpjs: float = 0
    allowance_other: float = 0
    allowance_other_note: Optional[str] = None


class EmployeeUpdateInput(BaseModel):
    full_name: Optional[str] = None
    position: Optional[str] = None
    phone: Optional[str] = None
    hire_date: Optional[str] = None
    is_active: Optional[bool] = None
    employment_type: Optional[str] = None
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
    notes: Optional[str] = None
    recorded_by: Optional[str] = None
    created_at: Optional[str] = None


class AttendanceCreateInput(BaseModel):
    date: str  # YYYY-MM-DD
    status: str  # present, absent, sick, leave, half_day
    overtime_hours: float = 0
    notes: Optional[str] = None


class AttendanceUpdateInput(BaseModel):
    status: Optional[str] = None
    overtime_hours: Optional[float] = None
    notes: Optional[str] = None


class PayrollSummaryItem(BaseModel):
    employee_id: str
    full_name: str
    position: str
    base_salary: float
    allowance_bike: float
    allowance_housing: float
    allowance_food: float
    allowance_bpjs: float
    allowance_other: float
    total_allowances: float
    working_days: int
    absent_days: int
    sick_days: int
    leave_days: int
    half_days: int
    overtime_hours: float
    gross_total: float


# ── Helpers ───────────────────────────────────────────────────

def _serialize_employee(emp: Employee, db: Session) -> dict:
    factory = db.query(Factory).filter(Factory.id == emp.factory_id).first()
    return {
        "id": str(emp.id),
        "factory_id": str(emp.factory_id),
        "factory_name": factory.name if factory else None,
        "full_name": emp.full_name,
        "position": emp.position,
        "phone": emp.phone,
        "hire_date": str(emp.hire_date) if emp.hire_date else None,
        "is_active": emp.is_active,
        "employment_type": emp.employment_type or "full_time",
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


def _serialize_attendance(att: Attendance, db: Session) -> dict:
    emp = db.query(Employee).filter(Employee.id == att.employee_id).first()
    return {
        "id": str(att.id),
        "employee_id": str(att.employee_id),
        "employee_name": emp.full_name if emp else None,
        "date": str(att.date),
        "status": att.status,
        "overtime_hours": float(att.overtime_hours or 0),
        "notes": att.notes,
        "recorded_by": str(att.recorded_by) if att.recorded_by else None,
        "created_at": att.created_at.isoformat() if att.created_at else None,
    }


# ── Employee endpoints ────────────────────────────────────────

@router.get("")
async def list_employees(
    factory_id: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List employees, optionally filtered by factory and active status."""
    query = db.query(Employee)
    if factory_id:
        query = query.filter(Employee.factory_id == UUID(factory_id))
    if is_active is not None:
        query = query.filter(Employee.is_active == is_active)

    total = query.count()
    items = (
        query.order_by(Employee.full_name)
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return {
        "items": [_serialize_employee(e, db) for e in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/payroll-summary")
async def payroll_summary(
    factory_id: str = Query(..., description="Factory UUID"),
    year: int = Query(..., description="Year"),
    month: int = Query(..., ge=1, le=12, description="Month 1-12"),
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Calculate payroll summary for a factory for a given month."""
    fid = UUID(factory_id)
    employees = (
        db.query(Employee)
        .filter(Employee.factory_id == fid, Employee.is_active == True)
        .order_by(Employee.full_name)
        .all()
    )

    result = []
    for emp in employees:
        attendance_records = (
            db.query(Attendance)
            .filter(
                Attendance.employee_id == emp.id,
                extract("year", Attendance.date) == year,
                extract("month", Attendance.date) == month,
            )
            .all()
        )

        working_days = sum(1 for a in attendance_records if a.status == "present")
        half_days = sum(1 for a in attendance_records if a.status == "half_day")
        absent_days = sum(1 for a in attendance_records if a.status == "absent")
        sick_days = sum(1 for a in attendance_records if a.status == "sick")
        leave_days = sum(1 for a in attendance_records if a.status == "leave")
        overtime_hours = sum(float(a.overtime_hours or 0) for a in attendance_records)

        total_allowances = float(
            (emp.allowance_bike or 0)
            + (emp.allowance_housing or 0)
            + (emp.allowance_food or 0)
            + (emp.allowance_bpjs or 0)
            + (emp.allowance_other or 0)
        )

        gross_total = float(emp.base_salary or 0) + total_allowances

        result.append({
            "employee_id": str(emp.id),
            "full_name": emp.full_name,
            "position": emp.position,
            "base_salary": float(emp.base_salary or 0),
            "allowance_bike": float(emp.allowance_bike or 0),
            "allowance_housing": float(emp.allowance_housing or 0),
            "allowance_food": float(emp.allowance_food or 0),
            "allowance_bpjs": float(emp.allowance_bpjs or 0),
            "allowance_other": float(emp.allowance_other or 0),
            "total_allowances": total_allowances,
            "working_days": working_days,
            "absent_days": absent_days,
            "sick_days": sick_days,
            "leave_days": leave_days,
            "half_days": half_days,
            "overtime_hours": overtime_hours,
            "gross_total": gross_total,
        })

    return {"items": result, "factory_id": factory_id, "year": year, "month": month}


@router.get("/{employee_id}")
async def get_employee(
    employee_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get a single employee by ID."""
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(404, "Employee not found")
    return _serialize_employee(emp, db)


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
        position=data.position,
        phone=data.phone,
        hire_date=date.fromisoformat(data.hire_date) if data.hire_date else None,
        is_active=data.is_active,
        employment_type=data.employment_type,
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
    if "hire_date" in update_data and update_data["hire_date"]:
        update_data["hire_date"] = date.fromisoformat(update_data["hire_date"])

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

@router.get("/{employee_id}/attendance")
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
