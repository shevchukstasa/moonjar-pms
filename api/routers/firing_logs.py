"""
Firing logs router — temperature logging during kiln firing.

Endpoints:
  POST   /api/batches/{batch_id}/firing-log          — create/start firing log
  PATCH  /api/batches/{batch_id}/firing-log/{id}      — update firing log
  POST   /api/batches/{batch_id}/firing-log/{id}/reading — add a temperature reading
  GET    /api/batches/{batch_id}/firing-log            — get firing log(s) for batch
"""

from datetime import datetime, timezone
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.models import FiringLog, Batch, Resource

router = APIRouter()


# ── Pydantic schemas ──────────────────────────────────────────

class FiringLogCreate(BaseModel):
    target_temperature: Optional[float] = None
    firing_profile_id: Optional[UUID] = None
    notes: Optional[str] = None


class FiringLogUpdate(BaseModel):
    ended_at: Optional[str] = None  # ISO datetime
    peak_temperature: Optional[float] = None
    target_temperature: Optional[float] = None
    result: Optional[str] = None  # success, partial_failure, abort
    notes: Optional[str] = None


class TemperatureReading(BaseModel):
    temp: float
    time: Optional[str] = None  # HH:MM, auto-filled if omitted
    notes: Optional[str] = None


def _serialize_log(log: FiringLog) -> dict:
    return {
        "id": str(log.id),
        "batch_id": str(log.batch_id),
        "kiln_id": str(log.kiln_id),
        "started_at": log.started_at.isoformat() if log.started_at else None,
        "ended_at": log.ended_at.isoformat() if log.ended_at else None,
        "peak_temperature": float(log.peak_temperature) if log.peak_temperature else None,
        "target_temperature": float(log.target_temperature) if log.target_temperature else None,
        "temperature_readings": log.temperature_readings or [],
        "firing_profile_id": str(log.firing_profile_id) if log.firing_profile_id else None,
        "result": log.result,
        "notes": log.notes,
        "recorded_by": str(log.recorded_by) if log.recorded_by else None,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


# ── POST /api/batches/{batch_id}/firing-log ───────────────────

@router.post("/{batch_id}/firing-log", status_code=201)
async def create_firing_log(
    batch_id: UUID,
    data: FiringLogCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create/start a firing log for a batch."""
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(404, "Batch not found")

    # Get kiln from batch
    kiln = db.query(Resource).filter(Resource.id == batch.resource_id).first()
    if not kiln:
        raise HTTPException(400, "Batch has no assigned kiln")

    log = FiringLog(
        batch_id=batch.id,
        kiln_id=batch.resource_id,
        started_at=datetime.now(timezone.utc),
        target_temperature=data.target_temperature,
        firing_profile_id=data.firing_profile_id or batch.firing_profile_id,
        notes=data.notes,
        recorded_by=current_user.id,
        temperature_readings=[],
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    return _serialize_log(log)


# ── PATCH /api/batches/{batch_id}/firing-log/{id} ─────────────

@router.patch("/{batch_id}/firing-log/{log_id}")
async def update_firing_log(
    batch_id: UUID,
    log_id: UUID,
    data: FiringLogUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Update firing log — set end time, peak temp, result."""
    log = db.query(FiringLog).filter(
        FiringLog.id == log_id,
        FiringLog.batch_id == batch_id,
    ).first()
    if not log:
        raise HTTPException(404, "Firing log not found")

    if data.ended_at is not None:
        try:
            log.ended_at = datetime.fromisoformat(data.ended_at)
        except ValueError:
            log.ended_at = datetime.now(timezone.utc)

    if data.peak_temperature is not None:
        log.peak_temperature = data.peak_temperature

    if data.target_temperature is not None:
        log.target_temperature = data.target_temperature

    if data.result is not None:
        if data.result not in ("success", "partial_failure", "abort"):
            raise HTTPException(400, "Invalid result. Must be: success, partial_failure, abort")
        log.result = data.result

    if data.notes is not None:
        log.notes = data.notes

    db.commit()
    db.refresh(log)

    return _serialize_log(log)


# ── POST /api/batches/{batch_id}/firing-log/{id}/reading ──────

@router.post("/{batch_id}/firing-log/{log_id}/reading")
async def add_temperature_reading(
    batch_id: UUID,
    log_id: UUID,
    data: TemperatureReading,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Add a temperature reading to the firing log."""
    log = db.query(FiringLog).filter(
        FiringLog.id == log_id,
        FiringLog.batch_id == batch_id,
    ).first()
    if not log:
        raise HTTPException(404, "Firing log not found")

    # Build the reading entry
    now = datetime.now(timezone.utc)
    reading = {
        "temp": data.temp,
        "time": data.time or now.strftime("%H:%M"),
        "timestamp": now.isoformat(),
    }
    if data.notes:
        reading["notes"] = data.notes

    # Append to readings list
    readings = list(log.temperature_readings or [])
    readings.append(reading)

    # Update peak temperature if this reading is higher
    current_peak = float(log.peak_temperature) if log.peak_temperature else 0
    if data.temp > current_peak:
        log.peak_temperature = data.temp

    # Force JSONB update (SQLAlchemy needs a new reference)
    log.temperature_readings = readings

    db.commit()
    db.refresh(log)

    return _serialize_log(log)


# ── GET /api/batches/{batch_id}/firing-log ─────────────────────

@router.get("/{batch_id}/firing-log")
async def get_firing_logs(
    batch_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get all firing logs for a batch."""
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(404, "Batch not found")

    logs = db.query(FiringLog).filter(
        FiringLog.batch_id == batch_id,
    ).order_by(FiringLog.created_at.desc()).all()

    return {
        "items": [_serialize_log(log) for log in logs],
        "total": len(logs),
    }
