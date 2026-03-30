"""Kiln maintenance scheduling — types CRUD + schedule management.

Provides:
  - Maintenance Types CRUD (GET/POST/PUT)
  - Kiln-specific maintenance schedule (GET/POST/PUT/DELETE/complete)
  - Factory-wide upcoming maintenance view
"""

from uuid import UUID
from datetime import datetime, date, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.roles import require_management
from api.models import (
    KilnMaintenanceSchedule,
    KilnMaintenanceType,
    Resource,
    Factory,
)
from api.enums import ResourceType, MaintenanceStatus

router = APIRouter()


# ────────────────────────────────────────────────────────────
# Serialization helpers
# ────────────────────────────────────────────────────────────

def _serialize_maintenance_type(mt: KilnMaintenanceType) -> dict:
    return {
        "id": str(mt.id),
        "name": mt.name,
        "description": mt.description,
        "duration_hours": float(mt.duration_hours) if mt.duration_hours else None,
        "requires_empty_kiln": mt.requires_empty_kiln,
        "requires_cooled_kiln": mt.requires_cooled_kiln,
        "requires_power_off": mt.requires_power_off,
        "default_interval_days": mt.default_interval_days,
        "is_active": mt.is_active,
        "created_at": mt.created_at.isoformat() if mt.created_at else None,
        "updated_at": mt.updated_at.isoformat() if mt.updated_at else None,
    }


def _serialize_schedule(s: KilnMaintenanceSchedule, db: Session) -> dict:
    kiln = db.query(Resource).filter(Resource.id == s.resource_id).first()
    factory = db.query(Factory).filter(Factory.id == s.factory_id).first() if s.factory_id else None
    mt = db.query(KilnMaintenanceType).filter(KilnMaintenanceType.id == s.maintenance_type_id).first() if s.maintenance_type_id else None
    status_val = s.status.value if hasattr(s.status, 'value') else str(s.status) if s.status else 'planned'
    return {
        "id": str(s.id),
        "resource_id": str(s.resource_id),
        "kiln_name": kiln.name if kiln else None,
        "maintenance_type": s.maintenance_type,
        "maintenance_type_id": str(s.maintenance_type_id) if s.maintenance_type_id else None,
        "maintenance_type_details": _serialize_maintenance_type(mt) if mt else None,
        "scheduled_date": str(s.scheduled_date),
        "scheduled_time": s.scheduled_time.isoformat() if s.scheduled_time else None,
        "estimated_duration_hours": float(s.estimated_duration_hours) if s.estimated_duration_hours else None,
        "status": status_val,
        "notes": s.notes,
        "completed_at": s.completed_at.isoformat() if s.completed_at else None,
        "completed_by_id": str(s.completed_by_id) if s.completed_by_id else None,
        "created_by": str(s.created_by) if s.created_by else None,
        "factory_id": str(s.factory_id) if s.factory_id else None,
        "factory_name": factory.name if factory else None,
        "is_recurring": s.is_recurring,
        "recurrence_interval_days": s.recurrence_interval_days,
        "requires_empty_kiln": s.requires_empty_kiln,
        "requires_cooled_kiln": s.requires_cooled_kiln,
        "requires_power_off": s.requires_power_off,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


# ────────────────────────────────────────────────────────────
# Pydantic input models
# ────────────────────────────────────────────────────────────

class MaintenanceTypeInput(BaseModel):
    name: str
    description: Optional[str] = None
    duration_hours: float = 2
    requires_empty_kiln: bool = False
    requires_cooled_kiln: bool = False
    requires_power_off: bool = False
    default_interval_days: Optional[int] = None
    is_active: bool = True


class MaintenanceTypeUpdateInput(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    duration_hours: Optional[float] = None
    requires_empty_kiln: Optional[bool] = None
    requires_cooled_kiln: Optional[bool] = None
    requires_power_off: Optional[bool] = None
    default_interval_days: Optional[int] = None
    is_active: Optional[bool] = None


class MaintenanceScheduleInput(BaseModel):
    maintenance_type: Optional[str] = None
    maintenance_type_id: Optional[str] = None
    scheduled_date: str  # ISO date string
    scheduled_time: Optional[str] = None  # HH:MM format
    estimated_duration_hours: Optional[float] = None
    notes: Optional[str] = None
    factory_id: Optional[str] = None
    is_recurring: bool = False
    recurrence_interval_days: Optional[int] = None


class MaintenanceScheduleUpdateInput(BaseModel):
    maintenance_type: Optional[str] = None
    maintenance_type_id: Optional[str] = None
    scheduled_date: Optional[str] = None
    scheduled_time: Optional[str] = None
    estimated_duration_hours: Optional[float] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    is_recurring: Optional[bool] = None
    recurrence_interval_days: Optional[int] = None


class CompleteMaintenanceInput(BaseModel):
    notes: Optional[str] = None


# ────────────────────────────────────────────────────────────
# Maintenance Types CRUD
# ────────────────────────────────────────────────────────────

@router.get("/types")
async def list_maintenance_types(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List all maintenance types (any authenticated user)."""
    items = db.query(KilnMaintenanceType).filter(
        KilnMaintenanceType.is_active.is_(True),
    ).order_by(KilnMaintenanceType.name).all()
    return {"items": [_serialize_maintenance_type(mt) for mt in items]}


@router.post("/types", status_code=201)
async def create_maintenance_type(
    data: MaintenanceTypeInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Create a new maintenance type (management only)."""
    mt = KilnMaintenanceType(
        name=data.name,
        description=data.description,
        duration_hours=data.duration_hours,
        requires_empty_kiln=data.requires_empty_kiln,
        requires_cooled_kiln=data.requires_cooled_kiln,
        requires_power_off=data.requires_power_off,
        default_interval_days=data.default_interval_days,
        is_active=data.is_active,
    )
    db.add(mt)
    db.commit()
    db.refresh(mt)
    return _serialize_maintenance_type(mt)


@router.put("/types/{type_id}")
async def update_maintenance_type(
    type_id: UUID,
    data: MaintenanceTypeUpdateInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Update a maintenance type (management only)."""
    mt = db.query(KilnMaintenanceType).filter(KilnMaintenanceType.id == type_id).first()
    if not mt:
        raise HTTPException(404, "Maintenance type not found")

    if data.name is not None:
        mt.name = data.name
    if data.description is not None:
        mt.description = data.description
    if data.duration_hours is not None:
        mt.duration_hours = data.duration_hours
    if data.requires_empty_kiln is not None:
        mt.requires_empty_kiln = data.requires_empty_kiln
    if data.requires_cooled_kiln is not None:
        mt.requires_cooled_kiln = data.requires_cooled_kiln
    if data.requires_power_off is not None:
        mt.requires_power_off = data.requires_power_off
    if data.default_interval_days is not None:
        mt.default_interval_days = data.default_interval_days
    if data.is_active is not None:
        mt.is_active = data.is_active

    mt.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(mt)
    return _serialize_maintenance_type(mt)


# ────────────────────────────────────────────────────────────
# Kiln-specific maintenance schedule
# ────────────────────────────────────────────────────────────

@router.get("/kilns/{kiln_id}")
async def list_kiln_maintenance(
    kiln_id: UUID,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List scheduled maintenance for a specific kiln (any authenticated user)."""
    kiln = db.query(Resource).filter(
        Resource.id == kiln_id,
        Resource.resource_type == ResourceType.KILN.value,
    ).first()
    if not kiln:
        raise HTTPException(404, "Kiln not found")

    query = db.query(KilnMaintenanceSchedule).filter(
        KilnMaintenanceSchedule.resource_id == kiln_id,
    )
    if status:
        query = query.filter(KilnMaintenanceSchedule.status == status)

    total = query.count()
    items = query.order_by(
        KilnMaintenanceSchedule.scheduled_date.desc(),
    ).offset((page - 1) * per_page).limit(per_page).all()

    return {
        "items": [_serialize_schedule(s, db) for s in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.post("/kilns/{kiln_id}", status_code=201)
async def schedule_maintenance(
    kiln_id: UUID,
    data: MaintenanceScheduleInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Schedule new maintenance for a kiln (management only)."""
    kiln = db.query(Resource).filter(
        Resource.id == kiln_id,
        Resource.resource_type == ResourceType.KILN.value,
    ).first()
    if not kiln:
        raise HTTPException(404, "Kiln not found")

    # Resolve maintenance type details
    maintenance_type_name = data.maintenance_type or "General Maintenance"
    maintenance_type_id = None
    estimated_duration = data.estimated_duration_hours
    requires_empty = False
    requires_cooled = False
    requires_power = False

    if data.maintenance_type_id:
        mt = db.query(KilnMaintenanceType).filter(
            KilnMaintenanceType.id == UUID(data.maintenance_type_id),
        ).first()
        if not mt:
            raise HTTPException(404, "Maintenance type not found")
        maintenance_type_id = mt.id
        maintenance_type_name = data.maintenance_type or mt.name
        if estimated_duration is None:
            estimated_duration = float(mt.duration_hours)
        requires_empty = mt.requires_empty_kiln
        requires_cooled = mt.requires_cooled_kiln
        requires_power = mt.requires_power_off

    # Parse date
    try:
        sched_date = date.fromisoformat(data.scheduled_date)
    except (ValueError, TypeError):
        raise HTTPException(422, f"Invalid scheduled_date: {data.scheduled_date}")

    # Parse time (optional)
    from datetime import time as time_type
    sched_time = None
    if data.scheduled_time:
        try:
            parts = data.scheduled_time.split(":")
            sched_time = time_type(int(parts[0]), int(parts[1]))
        except (ValueError, IndexError):
            raise HTTPException(422, f"Invalid scheduled_time: {data.scheduled_time}")

    # Resolve factory_id
    factory_id = UUID(data.factory_id) if data.factory_id else kiln.factory_id

    schedule = KilnMaintenanceSchedule(
        resource_id=kiln_id,
        maintenance_type=maintenance_type_name,
        maintenance_type_id=maintenance_type_id,
        scheduled_date=sched_date,
        scheduled_time=sched_time,
        estimated_duration_hours=estimated_duration,
        status=MaintenanceStatus.PLANNED,
        notes=data.notes,
        created_by=current_user.id,
        factory_id=factory_id,
        is_recurring=data.is_recurring,
        recurrence_interval_days=data.recurrence_interval_days,
        requires_empty_kiln=requires_empty,
        requires_cooled_kiln=requires_cooled,
        requires_power_off=requires_power,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return _serialize_schedule(schedule, db)


@router.put("/kilns/{kiln_id}/{schedule_id}")
async def update_maintenance_schedule(
    kiln_id: UUID,
    schedule_id: UUID,
    data: MaintenanceScheduleUpdateInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Update a maintenance schedule entry (management only)."""
    schedule = db.query(KilnMaintenanceSchedule).filter(
        KilnMaintenanceSchedule.id == schedule_id,
        KilnMaintenanceSchedule.resource_id == kiln_id,
    ).first()
    if not schedule:
        raise HTTPException(404, "Maintenance schedule not found")

    if data.maintenance_type is not None:
        schedule.maintenance_type = data.maintenance_type
    if data.maintenance_type_id is not None:
        mt = db.query(KilnMaintenanceType).filter(
            KilnMaintenanceType.id == UUID(data.maintenance_type_id),
        ).first()
        if not mt:
            raise HTTPException(404, "Maintenance type not found")
        schedule.maintenance_type_id = mt.id
        schedule.requires_empty_kiln = mt.requires_empty_kiln
        schedule.requires_cooled_kiln = mt.requires_cooled_kiln
        schedule.requires_power_off = mt.requires_power_off
    if data.scheduled_date is not None:
        try:
            schedule.scheduled_date = date.fromisoformat(data.scheduled_date)
        except (ValueError, TypeError):
            raise HTTPException(422, f"Invalid scheduled_date: {data.scheduled_date}")
    if data.scheduled_time is not None:
        from datetime import time as time_type
        try:
            parts = data.scheduled_time.split(":")
            schedule.scheduled_time = time_type(int(parts[0]), int(parts[1]))
        except (ValueError, IndexError):
            raise HTTPException(422, f"Invalid scheduled_time: {data.scheduled_time}")
    if data.estimated_duration_hours is not None:
        schedule.estimated_duration_hours = data.estimated_duration_hours
    if data.notes is not None:
        schedule.notes = data.notes
    if data.status is not None:
        schedule.status = data.status
    if data.is_recurring is not None:
        schedule.is_recurring = data.is_recurring
    if data.recurrence_interval_days is not None:
        schedule.recurrence_interval_days = data.recurrence_interval_days

    schedule.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(schedule)
    return _serialize_schedule(schedule, db)


@router.post("/kilns/{kiln_id}/{schedule_id}/complete")
async def complete_maintenance(
    kiln_id: UUID,
    schedule_id: UUID,
    data: CompleteMaintenanceInput = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Mark maintenance as completed. If recurring, auto-create the next occurrence."""
    schedule = db.query(KilnMaintenanceSchedule).filter(
        KilnMaintenanceSchedule.id == schedule_id,
        KilnMaintenanceSchedule.resource_id == kiln_id,
    ).first()
    if not schedule:
        raise HTTPException(404, "Maintenance schedule not found")

    status_val = schedule.status.value if hasattr(schedule.status, 'value') else str(schedule.status)
    if status_val == 'done':
        raise HTTPException(400, "Maintenance already completed")

    schedule.status = MaintenanceStatus.DONE
    schedule.completed_at = datetime.now(timezone.utc)
    schedule.completed_by_id = current_user.id
    if data and data.notes:
        schedule.notes = (schedule.notes or "") + ("\n" if schedule.notes else "") + data.notes
    schedule.updated_at = datetime.now(timezone.utc)

    # If recurring, auto-create the next occurrence
    next_schedule = None
    if schedule.is_recurring and schedule.recurrence_interval_days:
        next_date = schedule.scheduled_date + timedelta(days=schedule.recurrence_interval_days)
        next_schedule = KilnMaintenanceSchedule(
            resource_id=schedule.resource_id,
            maintenance_type=schedule.maintenance_type,
            maintenance_type_id=schedule.maintenance_type_id,
            scheduled_date=next_date,
            scheduled_time=schedule.scheduled_time,
            estimated_duration_hours=schedule.estimated_duration_hours,
            status=MaintenanceStatus.PLANNED,
            notes=None,
            created_by=current_user.id,
            factory_id=schedule.factory_id,
            is_recurring=True,
            recurrence_interval_days=schedule.recurrence_interval_days,
            requires_empty_kiln=schedule.requires_empty_kiln,
            requires_cooled_kiln=schedule.requires_cooled_kiln,
            requires_power_off=schedule.requires_power_off,
        )
        db.add(next_schedule)

    db.commit()
    db.refresh(schedule)

    result = _serialize_schedule(schedule, db)
    if next_schedule:
        db.refresh(next_schedule)
        result["next_occurrence"] = _serialize_schedule(next_schedule, db)

    return result


@router.delete("/kilns/{kiln_id}/{schedule_id}", status_code=204)
async def cancel_maintenance(
    kiln_id: UUID,
    schedule_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Cancel (delete) a scheduled maintenance entry (management only)."""
    schedule = db.query(KilnMaintenanceSchedule).filter(
        KilnMaintenanceSchedule.id == schedule_id,
        KilnMaintenanceSchedule.resource_id == kiln_id,
    ).first()
    if not schedule:
        raise HTTPException(404, "Maintenance schedule not found")

    db.delete(schedule)
    db.commit()


# ────────────────────────────────────────────────────────────
# Factory-wide upcoming maintenance
# ────────────────────────────────────────────────────────────

@router.get("/upcoming")
async def upcoming_maintenance(
    factory_id: Optional[str] = None,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """
    List upcoming maintenance across all kilns in a factory.
    Returns planned + in_progress maintenance within the next N days.
    """
    today = date.today()
    end_date = today + timedelta(days=days)

    query = db.query(KilnMaintenanceSchedule).filter(
        KilnMaintenanceSchedule.scheduled_date >= today,
        KilnMaintenanceSchedule.scheduled_date <= end_date,
        KilnMaintenanceSchedule.status.in_([
            MaintenanceStatus.PLANNED,
            MaintenanceStatus.IN_PROGRESS,
        ]),
    )

    if factory_id:
        query = query.filter(KilnMaintenanceSchedule.factory_id == UUID(factory_id))

    items = query.order_by(KilnMaintenanceSchedule.scheduled_date).all()

    return {
        "items": [_serialize_schedule(s, db) for s in items],
        "total": len(items),
        "date_range": {"start": str(today), "end": str(end_date)},
    }


# ────────────────────────────────────────────────────────────
# Legacy CRUD endpoints (backward-compatible with existing router)
# ────────────────────────────────────────────────────────────

@router.get("")
async def list_all_maintenance(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    factory_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List all maintenance schedules (backward-compatible)."""
    query = db.query(KilnMaintenanceSchedule)
    if factory_id:
        query = query.filter(KilnMaintenanceSchedule.factory_id == UUID(factory_id))
    if status:
        query = query.filter(KilnMaintenanceSchedule.status == status)

    total = query.count()
    items = query.order_by(
        KilnMaintenanceSchedule.scheduled_date.desc(),
    ).offset((page - 1) * per_page).limit(per_page).all()

    return {
        "items": [_serialize_schedule(s, db) for s in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/{item_id}")
async def get_kiln_maintenance_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get a single maintenance schedule entry."""
    item = db.query(KilnMaintenanceSchedule).filter(KilnMaintenanceSchedule.id == item_id).first()
    if not item:
        raise HTTPException(404, "KilnMaintenanceSchedule not found")
    return _serialize_schedule(item, db)


@router.post("", status_code=201)
async def create_kiln_maintenance_item(
    data: MaintenanceScheduleInput,
    resource_id: str = Query(..., description="Kiln resource ID"),
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Create a maintenance schedule entry (management only, backward-compatible)."""
    kiln = db.query(Resource).filter(
        Resource.id == UUID(resource_id),
        Resource.resource_type == ResourceType.KILN.value,
    ).first()
    if not kiln:
        raise HTTPException(404, "Kiln not found")

    # Delegate to the kiln-specific endpoint logic
    maintenance_type_name = data.maintenance_type or "General Maintenance"
    maintenance_type_id = None
    estimated_duration = data.estimated_duration_hours
    requires_empty = False
    requires_cooled = False
    requires_power = False

    if data.maintenance_type_id:
        mt = db.query(KilnMaintenanceType).filter(
            KilnMaintenanceType.id == UUID(data.maintenance_type_id),
        ).first()
        if mt:
            maintenance_type_id = mt.id
            maintenance_type_name = data.maintenance_type or mt.name
            if estimated_duration is None:
                estimated_duration = float(mt.duration_hours)
            requires_empty = mt.requires_empty_kiln
            requires_cooled = mt.requires_cooled_kiln
            requires_power = mt.requires_power_off

    try:
        sched_date = date.fromisoformat(data.scheduled_date)
    except (ValueError, TypeError):
        raise HTTPException(422, f"Invalid scheduled_date: {data.scheduled_date}")

    from datetime import time as time_type
    sched_time = None
    if data.scheduled_time:
        try:
            parts = data.scheduled_time.split(":")
            sched_time = time_type(int(parts[0]), int(parts[1]))
        except (ValueError, IndexError):
            pass

    factory_id = UUID(data.factory_id) if data.factory_id else kiln.factory_id

    item = KilnMaintenanceSchedule(
        resource_id=UUID(resource_id),
        maintenance_type=maintenance_type_name,
        maintenance_type_id=maintenance_type_id,
        scheduled_date=sched_date,
        scheduled_time=sched_time,
        estimated_duration_hours=estimated_duration,
        status=MaintenanceStatus.PLANNED,
        notes=data.notes,
        created_by=current_user.id,
        factory_id=factory_id,
        is_recurring=data.is_recurring,
        recurrence_interval_days=data.recurrence_interval_days,
        requires_empty_kiln=requires_empty,
        requires_cooled_kiln=requires_cooled,
        requires_power_off=requires_power,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_schedule(item, db)


@router.patch("/{item_id}")
async def update_kiln_maintenance_item(
    item_id: UUID,
    data: MaintenanceScheduleUpdateInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Update a maintenance schedule entry (management only)."""
    item = db.query(KilnMaintenanceSchedule).filter(KilnMaintenanceSchedule.id == item_id).first()
    if not item:
        raise HTTPException(404, "KilnMaintenanceSchedule not found")

    if data.maintenance_type is not None:
        item.maintenance_type = data.maintenance_type
    if data.maintenance_type_id is not None:
        mt = db.query(KilnMaintenanceType).filter(
            KilnMaintenanceType.id == UUID(data.maintenance_type_id),
        ).first()
        if mt:
            item.maintenance_type_id = mt.id
            item.requires_empty_kiln = mt.requires_empty_kiln
            item.requires_cooled_kiln = mt.requires_cooled_kiln
            item.requires_power_off = mt.requires_power_off
    if data.scheduled_date is not None:
        try:
            item.scheduled_date = date.fromisoformat(data.scheduled_date)
        except (ValueError, TypeError):
            raise HTTPException(422, f"Invalid scheduled_date: {data.scheduled_date}")
    if data.scheduled_time is not None:
        from datetime import time as time_type
        try:
            parts = data.scheduled_time.split(":")
            item.scheduled_time = time_type(int(parts[0]), int(parts[1]))
        except (ValueError, IndexError):
            pass
    if data.estimated_duration_hours is not None:
        item.estimated_duration_hours = data.estimated_duration_hours
    if data.notes is not None:
        item.notes = data.notes
    if data.status is not None:
        item.status = data.status
    if data.is_recurring is not None:
        item.is_recurring = data.is_recurring
    if data.recurrence_interval_days is not None:
        item.recurrence_interval_days = data.recurrence_interval_days

    item.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)
    return _serialize_schedule(item, db)


@router.delete("/{item_id}", status_code=204)
async def delete_kiln_maintenance_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Delete a maintenance schedule entry (management only)."""
    item = db.query(KilnMaintenanceSchedule).filter(KilnMaintenanceSchedule.id == item_id).first()
    if not item:
        raise HTTPException(404, "KilnMaintenanceSchedule not found")
    db.delete(item)
    db.commit()
