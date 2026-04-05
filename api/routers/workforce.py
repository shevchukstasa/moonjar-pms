"""Workforce Management — worker skills, shift definitions, shift assignments."""

import logging
from uuid import UUID
from datetime import date, time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.roles import require_management, require_any

logger = logging.getLogger("moonjar.workforce")
router = APIRouter()


# ── Pydantic schemas ────────────────────────────────────────────


class WorkerSkillCreate(BaseModel):
    user_id: UUID
    factory_id: UUID
    stage: str
    proficiency: str = Field(default="capable", description="trainee / capable / expert")
    notes: str | None = None


class WorkerSkillUpdate(BaseModel):
    proficiency: str = Field(..., description="trainee / capable / expert")
    notes: str | None = None


class ShiftDefinitionCreate(BaseModel):
    factory_id: UUID
    name: str
    name_id: str | None = None
    start_time: time
    end_time: time


class ShiftDefinitionUpdate(BaseModel):
    name: str | None = None
    name_id: str | None = None
    start_time: time | None = None
    end_time: time | None = None
    is_active: bool | None = None


class ShiftAssignmentCreate(BaseModel):
    factory_id: UUID
    user_id: UUID
    shift_definition_id: UUID
    date: date
    stage: str
    is_lead: bool = False


# ── Worker Stage Skills ─────────────────────────────────────────


@router.get("/skills")
async def list_worker_skills(
    factory_id: UUID = Query(...),
    stage: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_any),
):
    """List all worker-stage skills for a factory."""
    from api.models import WorkerStageSkill
    q = db.query(WorkerStageSkill).filter(WorkerStageSkill.factory_id == factory_id)
    if stage:
        q = q.filter(WorkerStageSkill.stage == stage)
    rows = q.order_by(WorkerStageSkill.stage, WorkerStageSkill.created_at).all()
    return [
        {
            "id": str(r.id),
            "user_id": str(r.user_id),
            "factory_id": str(r.factory_id),
            "stage": r.stage,
            "proficiency": r.proficiency,
            "certified_at": str(r.certified_at) if r.certified_at else None,
            "certified_by": str(r.certified_by) if r.certified_by else None,
            "notes": r.notes,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/skills/user/{user_id}")
async def get_user_skills(
    user_id: UUID,
    factory_id: UUID = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_any),
):
    """Get all stage skills for a specific user."""
    from api.models import WorkerStageSkill
    rows = (
        db.query(WorkerStageSkill)
        .filter(
            WorkerStageSkill.user_id == user_id,
            WorkerStageSkill.factory_id == factory_id,
        )
        .order_by(WorkerStageSkill.stage)
        .all()
    )
    return [
        {
            "id": str(r.id),
            "user_id": str(r.user_id),
            "factory_id": str(r.factory_id),
            "stage": r.stage,
            "proficiency": r.proficiency,
            "certified_at": str(r.certified_at) if r.certified_at else None,
            "certified_by": str(r.certified_by) if r.certified_by else None,
            "notes": r.notes,
        }
        for r in rows
    ]


@router.post("/skills", status_code=201)
async def create_worker_skill(
    body: WorkerSkillCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Assign a stage skill to a worker."""
    from api.models import WorkerStageSkill
    if body.proficiency not in ("trainee", "capable", "expert"):
        raise HTTPException(400, "proficiency must be one of: trainee, capable, expert")
    existing = (
        db.query(WorkerStageSkill)
        .filter(
            WorkerStageSkill.user_id == body.user_id,
            WorkerStageSkill.factory_id == body.factory_id,
            WorkerStageSkill.stage == body.stage,
        )
        .first()
    )
    if existing:
        raise HTTPException(409, f"Worker already has skill for stage '{body.stage}' in this factory")
    skill = WorkerStageSkill(
        user_id=body.user_id,
        factory_id=body.factory_id,
        stage=body.stage,
        proficiency=body.proficiency,
        certified_by=current_user.id,
        notes=body.notes,
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return {
        "id": str(skill.id),
        "user_id": str(skill.user_id),
        "factory_id": str(skill.factory_id),
        "stage": skill.stage,
        "proficiency": skill.proficiency,
    }


@router.put("/skills/{skill_id}")
async def update_worker_skill(
    skill_id: UUID,
    body: WorkerSkillUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Update proficiency level for a worker-stage skill."""
    from api.models import WorkerStageSkill
    if body.proficiency not in ("trainee", "capable", "expert"):
        raise HTTPException(400, "proficiency must be one of: trainee, capable, expert")
    skill = db.query(WorkerStageSkill).filter(WorkerStageSkill.id == skill_id).first()
    if not skill:
        raise HTTPException(404, "Skill assignment not found")
    skill.proficiency = body.proficiency
    if body.notes is not None:
        skill.notes = body.notes
    skill.certified_by = current_user.id
    db.commit()
    db.refresh(skill)
    return {
        "id": str(skill.id),
        "user_id": str(skill.user_id),
        "stage": skill.stage,
        "proficiency": skill.proficiency,
    }


@router.delete("/skills/{skill_id}")
async def delete_worker_skill(
    skill_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Remove a skill assignment from a worker."""
    from api.models import WorkerStageSkill
    skill = db.query(WorkerStageSkill).filter(WorkerStageSkill.id == skill_id).first()
    if not skill:
        raise HTTPException(404, "Skill assignment not found")
    db.delete(skill)
    db.commit()
    return {"deleted": True, "id": str(skill_id)}


# ── Shift Definitions ───────────────────────────────────────────


@router.get("/shifts")
async def list_shifts(
    factory_id: UUID = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_any),
):
    """List shift definitions for a factory."""
    from api.models import ShiftDefinition
    rows = (
        db.query(ShiftDefinition)
        .filter(ShiftDefinition.factory_id == factory_id)
        .order_by(ShiftDefinition.start_time)
        .all()
    )
    return [
        {
            "id": str(r.id),
            "factory_id": str(r.factory_id),
            "name": r.name,
            "name_id": r.name_id,
            "start_time": r.start_time.isoformat() if r.start_time else None,
            "end_time": r.end_time.isoformat() if r.end_time else None,
            "is_active": r.is_active,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.post("/shifts", status_code=201)
async def create_shift(
    body: ShiftDefinitionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Create a new shift definition."""
    from api.models import ShiftDefinition
    existing = (
        db.query(ShiftDefinition)
        .filter(
            ShiftDefinition.factory_id == body.factory_id,
            ShiftDefinition.name == body.name,
        )
        .first()
    )
    if existing:
        raise HTTPException(409, f"Shift '{body.name}' already exists for this factory")
    shift = ShiftDefinition(
        factory_id=body.factory_id,
        name=body.name,
        name_id=body.name_id,
        start_time=body.start_time,
        end_time=body.end_time,
    )
    db.add(shift)
    db.commit()
    db.refresh(shift)
    return {
        "id": str(shift.id),
        "factory_id": str(shift.factory_id),
        "name": shift.name,
        "start_time": shift.start_time.isoformat(),
        "end_time": shift.end_time.isoformat(),
    }


@router.put("/shifts/{shift_id}")
async def update_shift(
    shift_id: UUID,
    body: ShiftDefinitionUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Update a shift definition."""
    from api.models import ShiftDefinition
    shift = db.query(ShiftDefinition).filter(ShiftDefinition.id == shift_id).first()
    if not shift:
        raise HTTPException(404, "Shift definition not found")
    if body.name is not None:
        shift.name = body.name
    if body.name_id is not None:
        shift.name_id = body.name_id
    if body.start_time is not None:
        shift.start_time = body.start_time
    if body.end_time is not None:
        shift.end_time = body.end_time
    if body.is_active is not None:
        shift.is_active = body.is_active
    db.commit()
    db.refresh(shift)
    return {
        "id": str(shift.id),
        "name": shift.name,
        "start_time": shift.start_time.isoformat(),
        "end_time": shift.end_time.isoformat(),
        "is_active": shift.is_active,
    }


@router.delete("/shifts/{shift_id}")
async def delete_shift(
    shift_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Delete a shift definition (only if no assignments reference it)."""
    from api.models import ShiftDefinition, ShiftAssignment
    shift = db.query(ShiftDefinition).filter(ShiftDefinition.id == shift_id).first()
    if not shift:
        raise HTTPException(404, "Shift definition not found")
    active_assignments = (
        db.query(ShiftAssignment)
        .filter(ShiftAssignment.shift_definition_id == shift_id)
        .count()
    )
    if active_assignments > 0:
        raise HTTPException(
            409,
            f"Cannot delete shift with {active_assignments} existing assignments. "
            "Remove assignments first or deactivate the shift instead.",
        )
    db.delete(shift)
    db.commit()
    return {"deleted": True, "id": str(shift_id)}


# ── Shift Assignments ───────────────────────────────────────────


@router.get("/assignments")
async def list_assignments(
    factory_id: UUID = Query(...),
    date_: date = Query(..., alias="date"),
    db: Session = Depends(get_db),
    current_user=Depends(require_any),
):
    """Get shift assignments for a specific date."""
    from api.models import ShiftAssignment
    rows = (
        db.query(ShiftAssignment)
        .filter(
            ShiftAssignment.factory_id == factory_id,
            ShiftAssignment.date == date_,
        )
        .order_by(ShiftAssignment.shift_definition_id, ShiftAssignment.stage)
        .all()
    )
    return [
        {
            "id": str(r.id),
            "factory_id": str(r.factory_id),
            "user_id": str(r.user_id),
            "shift_definition_id": str(r.shift_definition_id),
            "date": str(r.date),
            "stage": r.stage,
            "is_lead": r.is_lead,
            "assigned_by": str(r.assigned_by) if r.assigned_by else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.post("/assignments", status_code=201)
async def create_assignment(
    body: ShiftAssignmentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Assign a worker to a shift on a specific date."""
    from api.models import ShiftAssignment, ShiftDefinition, WorkerStageSkill
    # Verify shift exists
    shift = db.query(ShiftDefinition).filter(ShiftDefinition.id == body.shift_definition_id).first()
    if not shift:
        raise HTTPException(404, "Shift definition not found")
    if not shift.is_active:
        raise HTTPException(400, "Cannot assign to inactive shift")
    # Verify worker has the skill for this stage (warn, don't block)
    has_skill = (
        db.query(WorkerStageSkill)
        .filter(
            WorkerStageSkill.user_id == body.user_id,
            WorkerStageSkill.factory_id == body.factory_id,
            WorkerStageSkill.stage == body.stage,
        )
        .first()
    )
    assignment = ShiftAssignment(
        factory_id=body.factory_id,
        user_id=body.user_id,
        shift_definition_id=body.shift_definition_id,
        date=body.date,
        stage=body.stage,
        is_lead=body.is_lead,
        assigned_by=current_user.id,
    )
    db.add(assignment)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        if "uq_shift_assignment_user_date_shift" in str(exc):
            raise HTTPException(409, "Worker already assigned to this shift on this date")
        raise
    db.refresh(assignment)
    result = {
        "id": str(assignment.id),
        "user_id": str(assignment.user_id),
        "shift_definition_id": str(assignment.shift_definition_id),
        "date": str(assignment.date),
        "stage": assignment.stage,
        "is_lead": assignment.is_lead,
    }
    if not has_skill:
        result["warning"] = f"Worker has no registered skill for stage '{body.stage}'"
    return result


@router.delete("/assignments/{assignment_id}")
async def delete_assignment(
    assignment_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Remove a shift assignment."""
    from api.models import ShiftAssignment
    assignment = db.query(ShiftAssignment).filter(ShiftAssignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(404, "Shift assignment not found")
    db.delete(assignment)
    db.commit()
    return {"deleted": True, "id": str(assignment_id)}


# ── Daily Capacity ──────────────────────────────────────────────


@router.get("/daily-capacity")
async def get_daily_capacity(
    factory_id: UUID = Query(...),
    date_: date = Query(..., alias="date"),
    db: Session = Depends(get_db),
    current_user=Depends(require_any),
):
    """Get aggregated worker count per stage for a date (from shift assignments)."""
    from api.models import ShiftAssignment
    rows = (
        db.query(ShiftAssignment)
        .filter(
            ShiftAssignment.factory_id == factory_id,
            ShiftAssignment.date == date_,
        )
        .all()
    )
    capacity: dict[str, dict] = defaultdict(lambda: {"workers": 0, "leads": 0, "user_ids": []})
    for r in rows:
        entry = capacity[r.stage]
        entry["workers"] += 1
        if r.is_lead:
            entry["leads"] += 1
        entry["user_ids"].append(str(r.user_id))

    return {
        "factory_id": str(factory_id),
        "date": str(date_),
        "total_workers": len({str(r.user_id) for r in rows}),
        "stages": {
            stage: {
                "workers": data["workers"],
                "leads": data["leads"],
                "user_ids": data["user_ids"],
            }
            for stage, data in sorted(capacity.items())
        },
    }
