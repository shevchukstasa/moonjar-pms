"""Factory Calendar router — manage non-working days per factory."""

from uuid import UUID
from typing import Optional, List
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.roles import require_management
from api.models import FactoryCalendar, Factory

router = APIRouter()


# ── Pydantic schemas ──────────────────────────────────────────

class CalendarEntryOut(BaseModel):
    id: str
    factory_id: str
    factory_name: Optional[str] = None
    date: str
    is_working_day: bool
    num_shifts: int
    holiday_name: Optional[str] = None
    holiday_source: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None


class CalendarCreateInput(BaseModel):
    factory_id: str
    date: str  # ISO format YYYY-MM-DD
    is_working_day: bool = False
    num_shifts: int = 2
    holiday_name: Optional[str] = None
    holiday_source: Optional[str] = None  # 'government', 'balinese', 'manual'
    notes: Optional[str] = None


class CalendarBulkInput(BaseModel):
    factory_id: str
    entries: List[CalendarCreateInput]


# ── Helpers ───────────────────────────────────────────────────

def _serialize(entry: FactoryCalendar, db: Session) -> dict:
    factory = db.query(Factory).filter(Factory.id == entry.factory_id).first()
    return {
        "id": str(entry.id),
        "factory_id": str(entry.factory_id),
        "factory_name": factory.name if factory else None,
        "date": str(entry.date),
        "is_working_day": entry.is_working_day,
        "num_shifts": entry.num_shifts or 2,
        "holiday_name": entry.holiday_name,
        "holiday_source": entry.holiday_source,
        "approved_by": str(entry.approved_by) if entry.approved_by else None,
        "approved_at": entry.approved_at.isoformat() if entry.approved_at else None,
        "notes": entry.notes,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
    }


# ── Endpoints ─────────────────────────────────────────────────

@router.get("/working-days")
async def count_working_days(
    factory_id: str = Query(..., description="Factory UUID"),
    start_date: str = Query(..., description="Start date YYYY-MM-DD"),
    end_date: str = Query(..., description="End date YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Count working days between two dates for a factory.

    Logic:
    - Default work week is 6 days (Mon-Sat), Sunday off.
    - Any date in factory_calendar with is_working_day=False is a non-working day.
    - Any date in factory_calendar with is_working_day=True overrides
      the default (e.g., a Sunday marked as working).
    """
    try:
        d_start = date.fromisoformat(start_date)
        d_end = date.fromisoformat(end_date)
    except (ValueError, TypeError):
        raise HTTPException(422, "Invalid date format. Use YYYY-MM-DD.")

    if d_start > d_end:
        raise HTTPException(422, "start_date must be <= end_date")

    fid = UUID(factory_id)

    # Fetch all calendar overrides in the range
    overrides = (
        db.query(FactoryCalendar)
        .filter(
            FactoryCalendar.factory_id == fid,
            FactoryCalendar.date >= d_start,
            FactoryCalendar.date <= d_end,
        )
        .all()
    )
    override_map = {entry.date: entry.is_working_day for entry in overrides}

    working = 0
    holidays = 0
    current = d_start
    while current <= d_end:
        if current in override_map:
            if override_map[current]:
                working += 1
            else:
                holidays += 1
        else:
            # Default: Mon-Sat working, Sunday off
            if current.weekday() < 6:  # 0=Mon … 5=Sat
                working += 1
        current += timedelta(days=1)

    total_days = (d_end - d_start).days + 1
    return {
        "factory_id": factory_id,
        "start_date": start_date,
        "end_date": end_date,
        "total_days": total_days,
        "working_days": working,
        "holidays": holidays,
        "sundays": total_days - working - holidays,
    }


@router.get("")
async def list_calendar(
    factory_id: str = Query(..., description="Factory UUID"),
    year: Optional[int] = Query(None, description="Filter by year"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Filter by month (1-12)"),
    page: int = Query(1, ge=1),
    per_page: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List calendar entries (non-working days / overrides) for a factory."""
    fid = UUID(factory_id)
    query = db.query(FactoryCalendar).filter(FactoryCalendar.factory_id == fid)

    if year is not None:
        from sqlalchemy import extract
        query = query.filter(extract("year", FactoryCalendar.date) == year)
    if month is not None:
        from sqlalchemy import extract
        query = query.filter(extract("month", FactoryCalendar.date) == month)

    total = query.count()
    items = (
        query.order_by(FactoryCalendar.date)
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return {
        "items": [_serialize(e, db) for e in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.post("", status_code=201)
async def create_calendar_entry(
    data: CalendarCreateInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Add a non-working day (or working-day override) to factory calendar."""
    fid = UUID(data.factory_id)

    # Validate factory exists
    factory = db.query(Factory).filter(Factory.id == fid).first()
    if not factory:
        raise HTTPException(404, "Factory not found")

    try:
        entry_date = date.fromisoformat(data.date)
    except (ValueError, TypeError):
        raise HTTPException(422, f"Invalid date: {data.date}")

    # Check for duplicate
    existing = (
        db.query(FactoryCalendar)
        .filter(FactoryCalendar.factory_id == fid, FactoryCalendar.date == entry_date)
        .first()
    )
    if existing:
        raise HTTPException(
            409,
            f"Calendar entry already exists for {data.date} at this factory. "
            "Delete it first or use a different date.",
        )

    entry = FactoryCalendar(
        factory_id=fid,
        date=entry_date,
        is_working_day=data.is_working_day,
        num_shifts=data.num_shifts,
        holiday_name=data.holiday_name,
        holiday_source=data.holiday_source or "manual",
        approved_by=current_user.id,
        approved_at=datetime.now(timezone.utc),
        notes=data.notes,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _serialize(entry, db)


@router.post("/bulk", status_code=201)
async def bulk_create_calendar_entries(
    data: CalendarBulkInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Add multiple holidays / non-working days at once (e.g., Balinese holidays)."""
    fid = UUID(data.factory_id)

    factory = db.query(Factory).filter(Factory.id == fid).first()
    if not factory:
        raise HTTPException(404, "Factory not found")

    if not data.entries:
        raise HTTPException(422, "No entries provided")

    created = []
    skipped = []

    for item in data.entries:
        try:
            entry_date = date.fromisoformat(item.date)
        except (ValueError, TypeError):
            skipped.append({"date": item.date, "reason": "invalid date format"})
            continue

        existing = (
            db.query(FactoryCalendar)
            .filter(FactoryCalendar.factory_id == fid, FactoryCalendar.date == entry_date)
            .first()
        )
        if existing:
            skipped.append({"date": item.date, "reason": "already exists"})
            continue

        entry = FactoryCalendar(
            factory_id=fid,
            date=entry_date,
            is_working_day=item.is_working_day,
            num_shifts=item.num_shifts,
            holiday_name=item.holiday_name,
            holiday_source=item.holiday_source or "manual",
            approved_by=current_user.id,
            approved_at=datetime.now(timezone.utc),
            notes=item.notes,
        )
        db.add(entry)
        created.append(entry)

    db.commit()
    for e in created:
        db.refresh(e)

    return {
        "created": [_serialize(e, db) for e in created],
        "skipped": skipped,
        "total_created": len(created),
        "total_skipped": len(skipped),
    }


@router.delete("/{entry_id}", status_code=204)
async def delete_calendar_entry(
    entry_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Remove a non-working day from factory calendar."""
    entry = db.query(FactoryCalendar).filter(FactoryCalendar.id == entry_id).first()
    if not entry:
        raise HTTPException(404, "Calendar entry not found")
    db.delete(entry)
    db.commit()
