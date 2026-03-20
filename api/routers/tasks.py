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
from api.models import Task, User, ProductionOrder, OrderPosition, ProductionOrderItem, Factory, Size, GlazingBoardSpec, Recipe
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


# ── Size Resolution ──────────────────────────────────────────────

class SizeResolutionInput(BaseModel):
    size_id: str | None = None            # existing size to assign
    create_new_size: bool = False          # create a new size entry
    new_size_name: str | None = None
    new_size_width_mm: int | None = None
    new_size_height_mm: int | None = None
    new_size_thickness_mm: int | None = None
    new_size_shape: str = "rectangle"


VALID_SIZE_SHAPES = {"rectangle", "square", "round", "freeform", "triangle", "octagon"}


@router.post("/{task_id}/resolve-size")
async def resolve_size(
    task_id: UUID,
    data: SizeResolutionInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Admin/PM resolves a size ambiguity: pick existing size or create new."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "Task not found")

    if _ev(task.type) != "size_resolution":
        raise HTTPException(400, "Task is not a size_resolution task")

    if _ev(task.status) == "done":
        raise HTTPException(400, "Task is already resolved")

    now = datetime.now(timezone.utc)
    meta = task.metadata_json or {}

    position = db.query(OrderPosition).filter(
        OrderPosition.id == task.related_position_id
    ).first()
    if not position:
        raise HTTPException(400, "Related position not found")

    chosen_size_id: UUID | None = None

    if data.create_new_size:
        # Validate required fields
        if not data.new_size_name:
            raise HTTPException(400, "new_size_name is required when creating a new size")
        if not data.new_size_width_mm or not data.new_size_height_mm:
            raise HTTPException(400, "new_size_width_mm and new_size_height_mm are required")
        if data.new_size_shape and data.new_size_shape not in VALID_SIZE_SHAPES:
            raise HTTPException(400, f"Invalid shape: {data.new_size_shape}")

        # Check uniqueness
        existing = db.query(Size).filter(Size.name == data.new_size_name).first()
        if existing:
            raise HTTPException(409, f"Size '{data.new_size_name}' already exists. Use its ID instead.")

        new_size = Size(
            name=data.new_size_name,
            width_mm=data.new_size_width_mm,
            height_mm=data.new_size_height_mm,
            thickness_mm=data.new_size_thickness_mm,
            shape=data.new_size_shape or "rectangle",
            is_custom=True,
        )
        db.add(new_size)
        db.flush()
        chosen_size_id = new_size.id

    elif data.size_id:
        size = db.query(Size).filter(Size.id == UUID(data.size_id)).first()
        if not size:
            raise HTTPException(404, f"Size '{data.size_id}' not found")
        chosen_size_id = size.id

    else:
        raise HTTPException(400, "Either size_id or create_new_size=true is required")

    # Assign size to position
    position.size_id = chosen_size_id
    position.updated_at = now

    # Transition position back to PLANNED if it was awaiting size
    if _ev(position.status) == "awaiting_size_confirmation":
        position.status = PositionStatus.PLANNED

    # Close task
    task.status = TaskStatus.DONE
    task.completed_at = now
    task.updated_at = now
    task.metadata_json = {
        **meta,
        "resolution": "new_size_created" if data.create_new_size else "existing_size_selected",
        "chosen_size_id": str(chosen_size_id),
        "resolved_by": str(current_user.id),
        "resolved_at": now.isoformat(),
    }

    db.flush()

    # ── Glazing board calculation ──────────────────────────────
    # After size is determined, calculate how tiles fit on glazing boards.
    # If a custom board width is needed, create a task for PM.
    glazing_board_result = None
    try:
        chosen_size = db.query(Size).filter(Size.id == chosen_size_id).first()
        if chosen_size:
            from business.services.glazing_board import calculate_glazing_board
            board_calc = calculate_glazing_board(chosen_size.width_mm, chosen_size.height_mm)

            # Upsert glazing board spec
            spec = db.query(GlazingBoardSpec).filter(GlazingBoardSpec.size_id == chosen_size_id).first()
            if spec is None:
                spec = GlazingBoardSpec(size_id=chosen_size_id)
                db.add(spec)
            spec.board_length_cm = board_calc.board_length_cm
            spec.board_width_cm = board_calc.board_width_cm
            spec.tiles_per_board = board_calc.tiles_per_board
            spec.area_per_board_m2 = board_calc.area_per_board_m2
            spec.tiles_along_length = board_calc.tiles_along_length
            spec.tiles_across_width = board_calc.tiles_across_width
            spec.tile_orientation_cm = board_calc.tile_orientation_cm
            spec.is_custom_board = not board_calc.is_standard_board
            spec.notes = board_calc.notes
            db.flush()

            glazing_board_result = {
                "board_length_cm": board_calc.board_length_cm,
                "board_width_cm": board_calc.board_width_cm,
                "tiles_per_board": board_calc.tiles_per_board,
                "area_per_board_m2": board_calc.area_per_board_m2,
                "is_custom_board": not board_calc.is_standard_board,
            }

            # Create PM task if custom board is needed
            if not board_calc.is_standard_board:
                import json
                board_task = Task(
                    factory_id=position.factory_id,
                    type=TaskType.GLAZING_BOARD_NEEDED,
                    status=TaskStatus.PENDING,
                    assigned_role=UserRole.PRODUCTION_MANAGER,
                    related_order_id=task.related_order_id,
                    related_position_id=position.id,
                    blocking=False,
                    priority=5,
                    description=(
                        f"Custom glazing board needed for size '{chosen_size.name}' "
                        f"({chosen_size.width_mm}×{chosen_size.height_mm} mm): "
                        f"cut board to {board_calc.board_width_cm:.1f} cm wide "
                        f"(standard 20cm doesn't fit neatly). "
                        f"{board_calc.tiles_per_board} tiles/board = "
                        f"{board_calc.area_per_board_m2:.4f} m²"
                    ),
                    metadata_json=json.dumps({
                        "size_id": str(chosen_size_id),
                        "size_name": chosen_size.name,
                        "width_mm": chosen_size.width_mm,
                        "height_mm": chosen_size.height_mm,
                        "board_length_cm": float(board_calc.board_length_cm),
                        "board_width_cm": float(board_calc.board_width_cm),
                        "tiles_per_board": board_calc.tiles_per_board,
                        "tiles_per_two_boards": board_calc.tiles_per_board * 2,
                        "area_per_board_m2": float(board_calc.area_per_board_m2),
                        "tiles_along_length": board_calc.tiles_along_length,
                        "tiles_across_width": board_calc.tiles_across_width,
                        "tile_orientation_cm": board_calc.tile_orientation_cm,
                    }),
                )
                db.add(board_task)
                db.flush()
                glazing_board_result["task_created"] = True
                glazing_board_result["task_id"] = str(board_task.id)
    except Exception as exc:
        import logging
        logging.getLogger("moonjar.tasks").warning(
            "Glazing board calc failed for size %s: %s", chosen_size_id, exc
        )

    # Trigger material reservation for the unblocked position
    # (only if position is now PLANNED and has a recipe)
    reservation_result = None
    if _ev(position.status) == "planned" and position.recipe_id:
        try:
            from api.models import Recipe
            recipe = db.query(Recipe).filter(Recipe.id == position.recipe_id).first()
            if recipe:
                from business.services.material_reservation import (
                    reserve_materials_for_position,
                )
                result = reserve_materials_for_position(db, position, recipe, position.factory_id)
                if result.shortages:
                    position.status = PositionStatus.INSUFFICIENT_MATERIALS
                    reservation_result = {
                        "status": "insufficient_materials",
                        "shortages": len(result.shortages),
                    }
                else:
                    reservation_result = {"status": "reserved"}
        except Exception as e:
            import logging
            logging.getLogger("moonjar.tasks").warning(
                "Material reservation after size resolution failed: %s", e
            )

    db.commit()

    return {
        "task_status": "done",
        "chosen_size_id": str(chosen_size_id),
        "position_status": _ev(position.status),
        "created_new_size": data.create_new_size,
        "reservation": reservation_result,
        "glazing_board": glazing_board_result,
    }


# ── Resolve Consumption Measurement Task ────────────────────

class ConsumptionResolutionInput(BaseModel):
    spray_ml_per_sqm: Optional[float] = None
    brush_ml_per_sqm: Optional[float] = None


@router.post("/{task_id}/resolve-consumption")
async def resolve_consumption(
    task_id: UUID,
    data: ConsumptionResolutionInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """PM resolves consumption measurement: enters measured rate(s) for recipe."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "Task not found")

    if _ev(task.type) != "consumption_measurement":
        raise HTTPException(400, "Task is not a consumption_measurement task")

    if _ev(task.status) == "done":
        raise HTTPException(400, "Task is already resolved")

    now = datetime.now(timezone.utc)
    meta = task.metadata_json if isinstance(task.metadata_json, dict) else {}
    if isinstance(task.metadata_json, str):
        import json as _json
        try:
            meta = _json.loads(task.metadata_json)
        except Exception:
            meta = {}

    missing_rates = meta.get("missing_rates", [])

    # Validate that at least one required rate is provided
    if "spray" in missing_rates and not data.spray_ml_per_sqm:
        raise HTTPException(400, "spray_ml_per_sqm is required (was missing)")
    if "brush" in missing_rates and not data.brush_ml_per_sqm:
        raise HTTPException(400, "brush_ml_per_sqm is required (was missing)")

    # Find and update recipe
    recipe_id = meta.get("recipe_id")
    if not recipe_id:
        raise HTTPException(400, "No recipe_id in task metadata")

    recipe = db.query(Recipe).filter(Recipe.id == UUID(recipe_id)).first()
    if not recipe:
        raise HTTPException(404, f"Recipe {recipe_id} not found")

    updated_fields = []
    if data.spray_ml_per_sqm:
        from decimal import Decimal
        recipe.consumption_spray_ml_per_sqm = Decimal(str(data.spray_ml_per_sqm))
        updated_fields.append(f"spray={data.spray_ml_per_sqm}")
    if data.brush_ml_per_sqm:
        from decimal import Decimal
        recipe.consumption_brush_ml_per_sqm = Decimal(str(data.brush_ml_per_sqm))
        updated_fields.append(f"brush={data.brush_ml_per_sqm}")

    # Find related position and unblock
    position = db.query(OrderPosition).filter(
        OrderPosition.id == task.related_position_id
    ).first()

    if position and _ev(position.status) == "awaiting_consumption_data":
        position.status = PositionStatus.PLANNED
        position.updated_at = now

    # Close task
    task.status = TaskStatus.DONE
    task.completed_at = now
    task.updated_at = now
    task.metadata_json = {
        **meta,
        "resolution": "consumption_measured",
        "spray_ml_per_sqm": data.spray_ml_per_sqm,
        "brush_ml_per_sqm": data.brush_ml_per_sqm,
        "resolved_by": str(current_user.id),
        "resolved_at": now.isoformat(),
    }

    # Trigger material reservation for the unblocked position
    reservation_result = None
    if position and _ev(position.status) == "planned" and position.recipe_id:
        try:
            from business.services.material_reservation import (
                reserve_materials_for_position,
            )
            result = reserve_materials_for_position(db, position, recipe, position.factory_id)
            if result.shortages:
                position.status = PositionStatus.INSUFFICIENT_MATERIALS
                reservation_result = {
                    "status": "insufficient_materials",
                    "shortages": len(result.shortages),
                }
            else:
                reservation_result = {"status": "reserved"}
        except Exception as e:
            import logging
            logging.getLogger("moonjar.tasks").warning(
                "Material reservation after consumption resolution failed: %s", e
            )

    db.commit()

    return {
        "task_status": "done",
        "recipe_id": recipe_id,
        "updated_fields": updated_fields,
        "position_status": _ev(position.status) if position else None,
        "reservation": reservation_result,
    }
