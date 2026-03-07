"""Tasks router — list, complete. Create/update are PM/system actions (501 for now)."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user, apply_factory_filter
from api.models import Task, User, ProductionOrder
from api.enums import TaskStatus

router = APIRouter()


def _ev(val):
    return val.value if hasattr(val, "value") else str(val) if val else None


def _serialize_task(t, db) -> dict:
    assignee_name = None
    if t.assigned_to:
        user = db.query(User).filter(User.id == t.assigned_to).first()
        assignee_name = user.name if user else None

    order_number = None
    if t.related_order_id:
        order = db.query(ProductionOrder).filter(ProductionOrder.id == t.related_order_id).first()
        order_number = order.order_number if order else None

    return {
        "id": str(t.id),
        "factory_id": str(t.factory_id),
        "type": _ev(t.type),
        "status": _ev(t.status),
        "assigned_to": str(t.assigned_to) if t.assigned_to else None,
        "assigned_to_name": assignee_name,
        "assigned_role": _ev(t.assigned_role),
        "related_order_id": str(t.related_order_id) if t.related_order_id else None,
        "related_order_number": order_number,
        "related_position_id": str(t.related_position_id) if t.related_position_id else None,
        "blocking": t.blocking,
        "description": t.description,
        "priority": t.priority,
        "due_at": t.due_at.isoformat() if t.due_at else None,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


@router.get("/")
async def list_tasks(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    factory_id: UUID | None = None,
    assigned_to: UUID | None = None,
    assigned_role: str | None = None,
    status: str | None = None,
    task_type: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(Task)
    query = apply_factory_filter(query, current_user, factory_id, Task)

    if assigned_to:
        query = query.filter(Task.assigned_to == assigned_to)
    if assigned_role:
        query = query.filter(Task.assigned_role == assigned_role)
    if status:
        statuses = [s.strip() for s in status.split(",")]
        query = query.filter(Task.status.in_(statuses))
    if task_type:
        types = [t.strip() for t in task_type.split(",")]
        query = query.filter(Task.type.in_(types))

    total = query.count()
    items = query.order_by(
        Task.priority.desc(), Task.created_at
    ).offset((page - 1) * per_page).limit(per_page).all()

    return {
        "items": [_serialize_task(t, db) for t in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.post("/", status_code=201)
async def create_task(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # TODO: Create task — PM/system action
    raise HTTPException(501, "Not implemented")


@router.patch("/{task_id}")
async def update_task(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # TODO: Update task — PM/system action
    raise HTTPException(501, "Not implemented")


@router.post("/{task_id}/complete")
async def complete_task(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "Task not found")

    if _ev(task.status) == "done":
        raise HTTPException(400, "Task is already completed")

    task.status = TaskStatus.DONE
    db.commit()
    db.refresh(task)
    return _serialize_task(task, db)
