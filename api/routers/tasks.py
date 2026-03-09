"""Tasks router — list, create, complete, resolve-shortage."""

import uuid as uuid_mod
from datetime import datetime, timezone
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user, apply_factory_filter
from api.roles import require_management
from api.models import Task, User, ProductionOrder, OrderPosition, ProductionOrderItem, Factory
from api.enums import TaskStatus, TaskType, PositionStatus, UserRole

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
        "metadata_json": t.metadata_json,
    }


@router.get("")
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


# --- Get single task ---
@router.get("/{task_id}")
async def get_task(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "Task not found")
    return _serialize_task(task, db)


# --- Create task ---
class TaskCreateInput(BaseModel):
    factory_id: str
    type: str
    assigned_to: str | None = None
    assigned_role: str | None = None
    related_order_id: str | None = None
    related_position_id: str | None = None
    blocking: bool = False
    description: str | None = None
    priority: int = 0
    metadata_json: dict | None = None


@router.post("", status_code=201)
async def create_task(
    data: TaskCreateInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    now = datetime.now(timezone.utc)
    task = Task(
        id=uuid_mod.uuid4(),
        factory_id=UUID(data.factory_id),
        type=data.type,
        status=TaskStatus.PENDING,
        assigned_to=UUID(data.assigned_to) if data.assigned_to else None,
        assigned_role=data.assigned_role,
        related_order_id=UUID(data.related_order_id) if data.related_order_id else None,
        related_position_id=UUID(data.related_position_id) if data.related_position_id else None,
        blocking=data.blocking,
        description=data.description,
        priority=data.priority,
        metadata_json=data.metadata_json,
        created_at=now,
        updated_at=now,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return _serialize_task(task, db)


# --- Update task ---
class TaskUpdateInput(BaseModel):
    status: str | None = None
    assigned_to: str | None = None
    description: str | None = None
    priority: int | None = None


@router.patch("/{task_id}")
async def update_task(
    task_id: UUID,
    data: TaskUpdateInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "Task not found")

    if data.status:
        task.status = data.status
    if data.assigned_to:
        task.assigned_to = UUID(data.assigned_to)
    if data.description is not None:
        task.description = data.description
    if data.priority is not None:
        task.priority = data.priority
    task.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(task)
    return _serialize_task(task, db)


# --- Complete task ---
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
    task.completed_at = datetime.now(timezone.utc)
    task.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(task)
    return _serialize_task(task, db)


# ---------- Shortage Resolution ----------

class ShortageResolutionInput(BaseModel):
    decision: str  # "manufacture" | "decline"
    target_factory_id: str | None = None  # factory for manufacturing
    manufacture_quantity: int | None = None
    notes: str | None = None


@router.post("/{task_id}/resolve-shortage")
async def resolve_shortage(
    task_id: UUID,
    data: ShortageResolutionInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """PM resolves a stock shortage: manufacture or decline."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "Task not found")

    if _ev(task.type) != "stock_shortage":
        raise HTTPException(400, "Task is not a stock shortage task")

    if _ev(task.status) == "done":
        raise HTTPException(400, "Task is already resolved")

    now = datetime.now(timezone.utc)
    meta = task.metadata_json or {}

    if data.decision == "manufacture":
        qty = data.manufacture_quantity or meta.get("shortage", 0)
        if qty <= 0:
            raise HTTPException(400, "Manufacture quantity must be > 0")

        # Determine target factory
        target_factory_id = UUID(data.target_factory_id) if data.target_factory_id else task.factory_id

        # Get parent position for copying attributes
        parent_position = db.query(OrderPosition).filter(
            OrderPosition.id == task.related_position_id
        ).first()
        if not parent_position:
            raise HTTPException(400, "Related position not found")

        # Create new manufacturing position
        new_position = OrderPosition(
            id=uuid_mod.uuid4(),
            order_id=parent_position.order_id,
            order_item_id=parent_position.order_item_id,
            parent_position_id=parent_position.id,
            factory_id=target_factory_id,
            status=PositionStatus.PLANNED,  # Goes through full production cycle
            quantity=qty,
            color=meta.get("color", parent_position.color),
            size=meta.get("size", parent_position.size),
            collection=None,  # NOT stock — needs manufacturing
            product_type=parent_position.product_type,
            shape=parent_position.shape,
            thickness_mm=parent_position.thickness_mm,
            mandatory_qc=parent_position.mandatory_qc,
            priority_order=parent_position.priority_order,
            created_at=now,
            updated_at=now,
        )
        db.add(new_position)

        # Close task
        task.status = TaskStatus.DONE
        task.completed_at = now
        task.updated_at = now
        task.metadata_json = {
            **meta,
            "resolution": "manufacture",
            "manufacture_quantity": qty,
            "target_factory_id": str(target_factory_id),
            "new_position_id": str(new_position.id),
            "resolved_by": str(current_user.id),
            "resolved_at": now.isoformat(),
        }

        db.commit()
        db.refresh(new_position)

        return {
            "decision": "manufacture",
            "new_position_id": str(new_position.id),
            "quantity": qty,
            "factory_id": str(target_factory_id),
            "task_status": "done",
        }

    elif data.decision == "decline":
        # Close task, log decline
        task.status = TaskStatus.DONE
        task.completed_at = now
        task.updated_at = now
        task.metadata_json = {
            **meta,
            "resolution": "decline",
            "declined_reason": data.notes,
            "resolved_by": str(current_user.id),
            "resolved_at": now.isoformat(),
        }

        db.commit()

        # TODO: Notify sales manager when notifications are implemented
        return {
            "decision": "decline",
            "notes": data.notes,
            "task_status": "done",
        }

    else:
        raise HTTPException(400, f"Invalid decision: {data.decision}. Must be 'manufacture' or 'decline'")
