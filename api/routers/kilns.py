"""Kilns router — kiln management (CRUD on resources table with type='kiln')."""

from uuid import UUID
from typing import Optional
from datetime import datetime, date, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.roles import require_management
from api.models import Resource, KilnLoadingRule, Factory, Collection, KilnMaintenanceSchedule, KilnMaintenanceType
from api.enums import ResourceType, MaintenanceStatus

router = APIRouter()

VALID_KILN_TYPES = ["big", "small", "raku"]
VALID_STATUSES = ["active", "maintenance_planned", "maintenance_emergency", "inactive"]


def _ev(val):
    return val.value if hasattr(val, "value") else str(val) if val else None


def _norm_dims(d: Optional[dict]) -> Optional[dict]:
    """
    Normalise kiln dimension dict to plain {width, depth, height?} keys.
    Accepts both {width_cm, depth_cm, height_cm} (seed format) and
    {width, depth, height} (frontend format).  height is optional.
    """
    if not d:
        return d
    w = d.get("width") if d.get("width") is not None else d.get("width_cm")
    dp = d.get("depth") if d.get("depth") is not None else d.get("depth_cm")
    h = d.get("height") if d.get("height") is not None else d.get("height_cm")
    result = {}
    if w is not None:
        result["width"] = float(w)
    if dp is not None:
        result["depth"] = float(dp)
    if h is not None:
        result["height"] = float(h)
    return result if result else None


def _serialize_kiln(resource: Resource, db: Session) -> dict:
    """Serialize a kiln resource with loading rules and factory name."""
    rules = db.query(KilnLoadingRule).filter(KilnLoadingRule.kiln_id == resource.id).first()
    factory = db.query(Factory).filter(Factory.id == resource.factory_id).first()
    return {
        "id": str(resource.id),
        "name": resource.name,
        "factory_id": str(resource.factory_id),
        "factory_name": factory.name if factory else None,
        "kiln_type": resource.kiln_type,
        "status": _ev(resource.status),
        "kiln_dimensions_cm": _norm_dims(resource.kiln_dimensions_cm),
        "kiln_working_area_cm": _norm_dims(resource.kiln_working_area_cm),
        "kiln_multi_level": resource.kiln_multi_level,
        "kiln_coefficient": float(resource.kiln_coefficient) if resource.kiln_coefficient else None,
        "num_levels": resource.num_levels,
        "capacity_sqm": float(resource.capacity_sqm) if resource.capacity_sqm else None,
        "capacity_pcs": resource.capacity_pcs,
        "thermocouple": resource.thermocouple,
        "control_cable": resource.control_cable,
        "control_device": resource.control_device,
        "is_active": resource.is_active,
        "loading_rules": rules.rules if rules else None,
        "loading_rules_id": str(rules.id) if rules else None,
        "created_at": resource.created_at.isoformat() if resource.created_at else None,
        "updated_at": resource.updated_at.isoformat() if resource.updated_at else None,
    }


VALID_THERMOCOUPLES = ["chinese", "indonesia_manufacture"]
VALID_CONTROL_CABLES = ["indonesia_manufacture"]
VALID_CONTROL_DEVICES = ["oven", "moonjar"]


class KilnCreateInput(BaseModel):
    name: str
    factory_id: str
    kiln_type: str
    kiln_dimensions_cm: Optional[dict] = None
    kiln_working_area_cm: Optional[dict] = None
    kiln_multi_level: bool = False
    kiln_coefficient: float = 0.8
    capacity_sqm: Optional[float] = None
    capacity_pcs: Optional[int] = None
    thermocouple: Optional[str] = None
    control_cable: Optional[str] = None
    control_device: Optional[str] = None


class KilnUpdateInput(BaseModel):
    name: Optional[str] = None
    factory_id: Optional[str] = None
    kiln_dimensions_cm: Optional[dict] = None
    kiln_working_area_cm: Optional[dict] = None
    kiln_multi_level: Optional[bool] = None
    kiln_coefficient: Optional[float] = None
    capacity_sqm: Optional[float] = None
    capacity_pcs: Optional[int] = None
    thermocouple: Optional[str] = None
    control_cable: Optional[str] = None
    control_device: Optional[str] = None


# --- Endpoints ---

@router.get("/collections")
async def list_collections(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List all collections (for kiln loading rules configuration)."""
    items = db.query(Collection).order_by(Collection.name).all()
    return {"items": [{"id": str(c.id), "name": c.name} for c in items]}


@router.get("")
async def list_kilns(
    factory_id: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(Resource).filter(Resource.resource_type == ResourceType.KILN)

    if factory_id:
        query = query.filter(Resource.factory_id == UUID(factory_id))
    if status:
        query = query.filter(Resource.status == status)

    total = query.count()
    kilns = query.order_by(Resource.name).offset((page - 1) * per_page).limit(per_page).all()

    return {
        "items": [_serialize_kiln(k, db) for k in kilns],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/maintenance/upcoming")
async def upcoming_kiln_maintenance(
    factory_id: Optional[str] = None,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """List upcoming maintenance across all kilns in a factory."""
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
        "items": [_serialize_maintenance(s, db) for s in items],
        "total": len(items),
        "date_range": {"start": str(today), "end": str(end_date)},
    }


@router.get("/{kiln_id}")
async def get_kiln(
    kiln_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    kiln = db.query(Resource).filter(Resource.id == kiln_id, Resource.resource_type == ResourceType.KILN).first()
    if not kiln:
        raise HTTPException(404, "Kiln not found")
    return _serialize_kiln(kiln, db)


@router.post("", status_code=201)
async def create_kiln(
    data: KilnCreateInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    if data.kiln_type not in VALID_KILN_TYPES:
        raise HTTPException(422, f"Invalid kiln_type '{data.kiln_type}'. Valid: {', '.join(VALID_KILN_TYPES)}")

    kiln = Resource(
        name=data.name,
        resource_type="kiln",
        factory_id=UUID(data.factory_id),
        kiln_type=data.kiln_type,
        kiln_dimensions_cm=_norm_dims(data.kiln_dimensions_cm),
        kiln_working_area_cm=_norm_dims(data.kiln_working_area_cm),
        kiln_multi_level=data.kiln_multi_level,
        kiln_coefficient=data.kiln_coefficient,
        capacity_sqm=data.capacity_sqm,
        capacity_pcs=data.capacity_pcs,
        thermocouple=data.thermocouple or None,
        control_cable=data.control_cable or None,
        control_device=data.control_device or None,
        status="active",
        is_active=True,
    )
    db.add(kiln)
    db.commit()
    db.refresh(kiln)
    return _serialize_kiln(kiln, db)


@router.patch("/{kiln_id}")
async def update_kiln(
    kiln_id: UUID,
    data: KilnUpdateInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    kiln = db.query(Resource).filter(Resource.id == kiln_id, Resource.resource_type == ResourceType.KILN).first()
    if not kiln:
        raise HTTPException(404, "Kiln not found")

    if data.name is not None:
        kiln.name = data.name
    if data.factory_id is not None:
        # Validate factory exists
        factory = db.query(Factory).filter(Factory.id == UUID(data.factory_id)).first()
        if not factory:
            raise HTTPException(404, "Factory not found")
        kiln.factory_id = UUID(data.factory_id)
    if data.kiln_dimensions_cm is not None:
        kiln.kiln_dimensions_cm = _norm_dims(data.kiln_dimensions_cm)
    if data.kiln_working_area_cm is not None:
        kiln.kiln_working_area_cm = _norm_dims(data.kiln_working_area_cm)
    if data.kiln_multi_level is not None:
        kiln.kiln_multi_level = data.kiln_multi_level
    if data.kiln_coefficient is not None:
        kiln.kiln_coefficient = data.kiln_coefficient
    if data.capacity_sqm is not None:
        kiln.capacity_sqm = data.capacity_sqm
    if data.capacity_pcs is not None:
        kiln.capacity_pcs = data.capacity_pcs
    if data.thermocouple is not None:
        kiln.thermocouple = data.thermocouple or None
    if data.control_cable is not None:
        kiln.control_cable = data.control_cable or None
    if data.control_device is not None:
        kiln.control_device = data.control_device or None

    kiln.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(kiln)
    return _serialize_kiln(kiln, db)


@router.patch("/{kiln_id}/status")
async def update_kiln_status(
    kiln_id: UUID,
    status: str = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    if status not in VALID_STATUSES:
        raise HTTPException(422, f"Invalid status '{status}'. Valid: {', '.join(VALID_STATUSES)}")

    kiln = db.query(Resource).filter(Resource.id == kiln_id, Resource.resource_type == ResourceType.KILN).first()
    if not kiln:
        raise HTTPException(404, "Kiln not found")

    old_status = _ev(kiln.status)
    kiln.status = status
    kiln.is_active = status == "active"
    kiln.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(kiln)

    # ── Reschedule positions when kiln status changes ──────────
    # If kiln goes to maintenance_emergency or inactive, all positions
    # estimated to use this kiln need to be reassigned.
    if status in ("maintenance_emergency", "inactive") and old_status == "active":
        try:
            from business.services.production_scheduler import reschedule_affected_by_kiln
            count = reschedule_affected_by_kiln(db, kiln_id)
            if count > 0:
                db.commit()
        except Exception as e:
            import logging
            logging.getLogger("moonjar.kilns").warning(
                "Failed to reschedule after kiln %s status change: %s", kiln_id, e,
            )

        # ── Real-time alert: kiln breakdown ──────────────────────
        try:
            from business.services.notifications import notify_pm
            factory_id = kiln.factory_id
            if factory_id:
                alert_title = f"🔥 KILN BREAKDOWN: {kiln.name}"
                alert_msg = (
                    f"Kiln {kiln.name} → status: {status}\n"
                    f"Status sebelumnya: {old_status}\n"
                    f"Posisi terdampak: {count if 'count' in dir() else '?'} — dijadwalkan ulang"
                )
                notify_pm(db, factory_id, "kiln_breakdown", alert_title, alert_msg,
                          related_entity_type="resource",
                          related_entity_id=kiln_id)
                # Also send to masters chat with reschedule button
                from api.models import Factory
                factory = db.query(Factory).get(factory_id)
                if factory and factory.masters_group_chat_id:
                    kid_short = str(kiln_id)[:8]
                    kiln_buttons = [
                        [{"text": "\U0001f4c5 Jadwal ulang", "callback_data": f"a:r:{kid_short}"}],
                    ]
                    from business.services.notifications import send_telegram_message_with_buttons
                    send_telegram_message_with_buttons(
                        str(factory.masters_group_chat_id),
                        f"🔥 *PERINGATAN KILN*\n{alert_msg}",
                        kiln_buttons,
                    )
        except Exception as e:
            import logging
            logging.getLogger("moonjar.kilns").warning(
                "Failed to send kiln breakdown alert: %s", e
            )

    return _serialize_kiln(kiln, db)


@router.delete("/{kiln_id}", status_code=204)
async def delete_kiln(
    kiln_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Delete a kiln. Removes associated loading rules via CASCADE."""
    kiln = db.query(Resource).filter(Resource.id == kiln_id, Resource.resource_type == ResourceType.KILN).first()
    if not kiln:
        raise HTTPException(404, "Kiln not found")

    from api.models import Batch
    from api.enums import BatchStatus

    # BatchStatus values: suggested | planned | in_progress | done  (no "completed"/"cancelled")
    # Non-terminal = anything that is NOT done
    non_done_statuses = [BatchStatus.SUGGESTED, BatchStatus.PLANNED, BatchStatus.IN_PROGRESS]
    active_batches = db.query(Batch).filter(
        Batch.resource_id == kiln_id,
        Batch.status.in_(non_done_statuses),
    ).count()
    if active_batches > 0:
        raise HTTPException(
            409,
            f"Cannot delete kiln: {active_batches} active batch(es) are in progress. "
            "Complete or reassign them first.",
        )

    # Even done batches reference the kiln via FK — deleting the kiln would
    # violate the constraint.  Prefer setting status to 'inactive' for kilns
    # with historical data.
    historical_batches = db.query(Batch).filter(Batch.resource_id == kiln_id).count()
    if historical_batches > 0:
        raise HTTPException(
            409,
            f"Cannot delete kiln: {historical_batches} historical batch record(s) still reference it. "
            "Set the kiln status to 'inactive' instead of deleting.",
        )

    try:
        db.delete(kiln)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            409,
            "Cannot delete kiln: other records still reference it. "
            "Set the kiln status to 'inactive' instead of deleting.",
        )


# ────────────────────────────────────────────────────────────
# Kiln Maintenance Schedule — convenience endpoints on kilns router
# ────────────────────────────────────────────────────────────

def _serialize_maintenance(s: KilnMaintenanceSchedule, db: Session) -> dict:
    """Serialize a maintenance schedule entry."""
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
        "maintenance_type_name": mt.name if mt else None,
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


@router.get("/{kiln_id}/maintenance")
async def list_kiln_maintenance(
    kiln_id: UUID,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List maintenance schedule for a specific kiln."""
    kiln = db.query(Resource).filter(
        Resource.id == kiln_id,
        Resource.resource_type == ResourceType.KILN,
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
        "items": [_serialize_maintenance(s, db) for s in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


class MaintenanceCreateInput(BaseModel):
    maintenance_type: Optional[str] = None
    maintenance_type_id: Optional[str] = None
    scheduled_date: str
    scheduled_time: Optional[str] = None
    estimated_duration_hours: Optional[float] = None
    notes: Optional[str] = None
    factory_id: Optional[str] = None
    is_recurring: bool = False
    recurrence_interval_days: Optional[int] = None


class MaintenanceUpdateInput(BaseModel):
    maintenance_type: Optional[str] = None
    maintenance_type_id: Optional[str] = None
    scheduled_date: Optional[str] = None
    scheduled_time: Optional[str] = None
    estimated_duration_hours: Optional[float] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    is_recurring: Optional[bool] = None
    recurrence_interval_days: Optional[int] = None


@router.post("/{kiln_id}/maintenance", status_code=201)
async def create_kiln_maintenance(
    kiln_id: UUID,
    data: MaintenanceCreateInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Schedule new maintenance for a kiln."""
    kiln = db.query(Resource).filter(
        Resource.id == kiln_id,
        Resource.resource_type == ResourceType.KILN,
    ).first()
    if not kiln:
        raise HTTPException(404, "Kiln not found")

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
            raise HTTPException(422, f"Invalid scheduled_time: {data.scheduled_time}")

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
    return _serialize_maintenance(schedule, db)


@router.put("/{kiln_id}/maintenance/{schedule_id}")
async def update_kiln_maintenance(
    kiln_id: UUID,
    schedule_id: UUID,
    data: MaintenanceUpdateInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Update a maintenance schedule entry for a kiln."""
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
    return _serialize_maintenance(schedule, db)


@router.post("/{kiln_id}/maintenance/{schedule_id}/complete")
async def complete_kiln_maintenance(
    kiln_id: UUID,
    schedule_id: UUID,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Mark maintenance as completed. If recurring, auto-create next occurrence."""
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
    if notes:
        schedule.notes = (schedule.notes or "") + ("\n" if schedule.notes else "") + notes
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

    result = _serialize_maintenance(schedule, db)
    if next_schedule:
        db.refresh(next_schedule)
        result["next_occurrence"] = _serialize_maintenance(next_schedule, db)
    return result


@router.delete("/{kiln_id}/maintenance/{schedule_id}", status_code=204)
async def delete_kiln_maintenance(
    kiln_id: UUID,
    schedule_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Cancel (delete) a scheduled maintenance entry for a kiln."""
    schedule = db.query(KilnMaintenanceSchedule).filter(
        KilnMaintenanceSchedule.id == schedule_id,
        KilnMaintenanceSchedule.resource_id == kiln_id,
    ).first()
    if not schedule:
        raise HTTPException(404, "Maintenance schedule not found")
    db.delete(schedule)
    db.commit()


