"""
TEMPORARY cleanup router — lets PM hard-delete test data.
Controlled by per-factory toggles set by admin/ceo/owner.
All deletions are written to Python logger (WARNING level).
Remove this file once test data is cleaned up.
"""

import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.database import get_db
from api.roles import require_role
from api.models import (
    Factory,
    ProductionOrder,
    ProductionOrderItem,
    OrderPosition,
    Task,
    # ── FK-blocking models (no CASCADE on order/position refs) ──
    MaterialTransaction,
    QualityCheck,
    DefectRecord,
    GrindingStock,
    RepairQueue,
    SurplusDisposition,
    CastersBox,
    OrderPackingPhoto,
    WorkerMedia,
    OrderFinancial,
    QmBlock,
)

logger = logging.getLogger("moonjar.cleanup")

router = APIRouter()


def _sql_safe(db, stmt: str):
    """Execute SQL in savepoint — skip on error without corrupting transaction."""
    from sqlalchemy import text as sa_text
    try:
        nested = db.begin_nested()
        db.execute(sa_text(stmt))
        nested.commit()
    except Exception as e:
        try:
            nested.rollback()
        except Exception:
            pass
        logger.debug("Cleanup SQL skip: %s", str(e)[:100])


# ── Role dependencies ──────────────────────────────────────────────────────
_require_management_roles = require_role(
    "owner", "administrator", "ceo", "production_manager"
)
_require_admin_roles = require_role("owner", "administrator", "ceo")


# ── Helpers ────────────────────────────────────────────────────────────────

def _ev(val):
    return val.value if hasattr(val, "value") else str(val) if val else None


def _get_factory_settings(db: Session, factory_id: UUID) -> dict:
    factory = db.query(Factory).filter(Factory.id == factory_id).first()
    if not factory:
        raise HTTPException(404, "Factory not found")
    return factory.settings or {}


def _check_pm_permission(db: Session, factory_id: UUID, flag: str, current_user) -> None:
    """For PM role: check factory toggle. Owner/admin/ceo always allowed."""
    role = _ev(current_user.role)
    if role in ("owner", "administrator", "ceo"):
        return
    settings = _get_factory_settings(db, factory_id)
    if not settings.get(flag, False):
        raise HTTPException(
            403,
            f"Cleanup not enabled for this factory. Ask admin/CEO to enable '{flag}'.",
        )


def _delete_tasks_for_position(db: Session, position_id: UUID) -> int:
    """Hard-delete all tasks linked to a position. Returns count deleted."""
    tasks = db.query(Task).filter(Task.related_position_id == position_id).all()
    for t in tasks:
        db.delete(t)
    return len(tasks)


def _delete_position_tree(db: Session, position: OrderPosition) -> tuple[int, int]:
    """
    Delete position + all split children + their tasks.
    Returns (positions_deleted, tasks_deleted).
    """
    positions_deleted = 0
    tasks_deleted = 0

    # 1. Delete tasks for the root position
    tasks_deleted += _delete_tasks_for_position(db, position.id)

    # 2. Find and delete split children recursively
    children = (
        db.query(OrderPosition)
        .filter(OrderPosition.parent_position_id == position.id)
        .all()
    )
    for child in children:
        tasks_deleted += _delete_tasks_for_position(db, child.id)
        db.delete(child)
        positions_deleted += 1

    # 3. Delete the root position itself
    db.delete(position)
    positions_deleted += 1

    return positions_deleted, tasks_deleted


# ── Tables with FK refs to order_positions (no CASCADE) ──
_POSITION_FK_MODELS = [
    (MaterialTransaction, MaterialTransaction.related_position_id),
    (QualityCheck,        QualityCheck.position_id),
    (DefectRecord,        DefectRecord.position_id),
    (GrindingStock,       GrindingStock.source_position_id),
    (RepairQueue,         RepairQueue.source_position_id),
    (SurplusDisposition,  SurplusDisposition.position_id),
    (OrderPackingPhoto,   OrderPackingPhoto.position_id),
    (WorkerMedia,         WorkerMedia.related_position_id),
    (QmBlock,             QmBlock.position_id),
]

# ── Tables with FK refs to production_orders (no CASCADE) ──
_ORDER_FK_MODELS = [
    (MaterialTransaction, MaterialTransaction.related_order_id),
    (GrindingStock,       GrindingStock.source_order_id),
    (RepairQueue,         RepairQueue.source_order_id),
    (SurplusDisposition,  SurplusDisposition.order_id),
    (CastersBox,          CastersBox.source_order_id),
    (OrderPackingPhoto,   OrderPackingPhoto.order_id),
    (WorkerMedia,         WorkerMedia.related_order_id),
    (OrderFinancial,      OrderFinancial.order_id),
]


def _purge_position_refs(db: Session, position_ids: list[UUID]) -> int:
    """Hard-delete all FK references to given positions from non-CASCADE tables."""
    total = 0
    if not position_ids:
        return total
    for Model, fk_col in _POSITION_FK_MODELS:
        try:
            total += db.query(Model).filter(fk_col.in_(position_ids)).delete(
                synchronize_session="fetch"
            )
        except Exception as e:
            logger.warning("Cleanup: failed to purge %s: %s", Model.__tablename__, e)
            db.rollback()
    # Clear batch_id on positions before CASCADE (avoid FK conflict)
    try:
        from api.models import Notification, PositionPhoto, KilnCalculationLog, OperationLog, StoneReservation, Shipment, ShipmentItem
        for M, col in [
            (Notification, Notification.related_entity_id),
            (KilnCalculationLog, KilnCalculationLog.position_id),
            (OperationLog, OperationLog.position_id),
        ]:
            try:
                db.query(M).filter(col.in_(position_ids)).delete(synchronize_session="fetch")
            except Exception:
                db.rollback()
        # Nullify batch references for positions
        for pid in position_ids:
            try:
                db.query(OrderPosition).filter(OrderPosition.id == pid).update(
                    {"batch_id": None, "resource_id": None}, synchronize_session="fetch"
                )
            except Exception:
                db.rollback()
    except ImportError:
        pass
    return total


def _purge_order_refs(db: Session, order_id: UUID, position_ids: list[UUID]) -> dict:
    """
    Hard-delete all FK references to this order and its positions
    from tables that lack CASCADE. Returns summary for logging.
    """
    counts: dict[str, int] = {}

    # Position-linked refs
    if position_ids:
        n = _purge_position_refs(db, position_ids)
        if n:
            counts["position_refs"] = n

    # Order-linked refs
    for Model, fk_col in _ORDER_FK_MODELS:
        n = db.query(Model).filter(fk_col == order_id).delete(
            synchronize_session="fetch"
        )
        if n:
            counts[Model.__tablename__] = n

    return counts


# ══════════════════════════════════════════════════════════════════════════════
# §1  Permissions — read / update factory flags
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/permissions")
async def get_cleanup_permissions(
    factory_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(_require_management_roles),
):
    """Get current PM cleanup toggles for a factory."""
    settings = _get_factory_settings(db, factory_id)
    return {
        "factory_id": str(factory_id),
        "pm_can_delete_tasks": bool(settings.get("pm_can_delete_tasks", False)),
        "pm_can_delete_positions": bool(settings.get("pm_can_delete_positions", False)),
        "pm_can_delete_orders": bool(settings.get("pm_can_delete_orders", False)),
    }


class CleanupPermissionsUpdate(BaseModel):
    factory_id: UUID
    pm_can_delete_tasks: bool | None = None
    pm_can_delete_positions: bool | None = None
    pm_can_delete_orders: bool | None = None


@router.patch("/permissions")
async def update_cleanup_permissions(
    body: CleanupPermissionsUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(_require_admin_roles),
):
    """Admin/CEO/Owner: toggle PM cleanup permissions for a factory."""
    factory = db.query(Factory).filter(Factory.id == body.factory_id).first()
    if not factory:
        raise HTTPException(404, "Factory not found")

    settings = dict(factory.settings or {})
    changed = []

    if body.pm_can_delete_tasks is not None:
        settings["pm_can_delete_tasks"] = body.pm_can_delete_tasks
        changed.append(f"pm_can_delete_tasks={body.pm_can_delete_tasks}")

    if body.pm_can_delete_positions is not None:
        settings["pm_can_delete_positions"] = body.pm_can_delete_positions
        changed.append(f"pm_can_delete_positions={body.pm_can_delete_positions}")

    if body.pm_can_delete_orders is not None:
        settings["pm_can_delete_orders"] = body.pm_can_delete_orders
        changed.append(f"pm_can_delete_orders={body.pm_can_delete_orders}")

    factory.settings = settings
    db.commit()

    logger.warning(
        "CLEANUP PERMISSIONS updated | factory=%s | changes=%s | by %s",
        factory.name,
        ", ".join(changed),
        current_user.email,
    )

    return {
        "factory_id": str(body.factory_id),
        "pm_can_delete_tasks": bool(settings.get("pm_can_delete_tasks", False)),
        "pm_can_delete_positions": bool(settings.get("pm_can_delete_positions", False)),
        "pm_can_delete_orders": bool(settings.get("pm_can_delete_orders", False)),
    }


# ══════════════════════════════════════════════════════════════════════════════
# §2  Delete task
# ══════════════════════════════════════════════════════════════════════════════

@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: UUID,
    factory_id: UUID = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(_require_management_roles),
):
    """
    Hard-delete a task. PM requires pm_can_delete_tasks toggle.
    Admin/CEO/Owner can always delete.
    """
    _check_pm_permission(db, factory_id, "pm_can_delete_tasks", current_user)

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "Task not found")

    logger.warning(
        "CLEANUP DELETE task | id=%s type=%s status=%s order=%s | by %s",
        task_id,
        _ev(task.type),
        _ev(task.status),
        task.related_order_id,
        current_user.email,
    )

    db.delete(task)
    db.commit()
    return {"deleted": "task", "id": str(task_id)}


# ══════════════════════════════════════════════════════════════════════════════
# §3  Delete position (+ split children + linked tasks)
# ══════════════════════════════════════════════════════════════════════════════

@router.delete("/positions/{position_id}")
async def delete_position(
    position_id: UUID,
    factory_id: UUID = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(_require_management_roles),
):
    """
    Hard-delete a position, its split children and all linked tasks.
    PM requires pm_can_delete_positions toggle.
    """
    _check_pm_permission(db, factory_id, "pm_can_delete_positions", current_user)

    position = db.query(OrderPosition).filter(OrderPosition.id == position_id).first()
    if not position:
        raise HTTPException(404, "Position not found")

    # If this is a split child, auto-escalate to the parent
    if position.parent_position_id is not None:
        parent = db.query(OrderPosition).filter(OrderPosition.id == position.parent_position_id).first()
        if parent:
            position = parent

    # Gather all position IDs in the tree (root + split children)
    child_ids = [
        c.id for c in db.query(OrderPosition)
        .filter(OrderPosition.parent_position_id == position.id).all()
    ]
    all_pos_ids = [position.id] + child_ids

    # Purge FK refs from non-CASCADE tables before deleting positions
    refs_purged = _purge_position_refs(db, all_pos_ids)

    logger.warning(
        "CLEANUP DELETE position | id=%s order=%s color=%s size=%s qty=%s refs_purged=%d | by %s",
        position.id,
        position.order_id,
        position.color,
        position.size,
        position.quantity,
        refs_purged,
        current_user.email,
    )

    pos_deleted, tasks_deleted = _delete_position_tree(db, position)
    db.commit()

    return {
        "deleted": "position",
        "id": str(position_id),
        "positions_deleted": pos_deleted,
        "tasks_deleted": tasks_deleted,
    }


# ══════════════════════════════════════════════════════════════════════════════
# §4  Delete order (admin/ceo/owner always; PM with toggle)
# ══════════════════════════════════════════════════════════════════════════════

@router.delete("/orders/{order_id}")
async def delete_order(
    order_id: UUID,
    factory_id: UUID = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(_require_management_roles),
):
    """
    Hard-delete an order + all positions, split children, tasks, and order items.
    PM requires pm_can_delete_orders toggle. Admin/CEO/Owner can always delete.
    DB CASCADE handles: positions, items, status_logs.
    Manual pre-delete: tasks linked to order or positions (no CASCADE in DB).
    """
    _check_pm_permission(db, factory_id, "pm_can_delete_orders", current_user)

    order = db.query(ProductionOrder).filter(ProductionOrder.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")

    # Cache order info BEFORE deletion (object becomes detached after raw SQL delete)
    order_number = order.order_number
    order_client = order.client

    # Gather all position IDs (to purge FK refs before CASCADE removes positions)
    position_ids = [
        row[0]
        for row in db.query(OrderPosition.id)
        .filter(OrderPosition.order_id == order_id)
        .all()
    ]

    # ── Aggressive FK cleanup via raw SQL ──
    from sqlalchemy import text as sa_text
    pos_count = len(position_ids)
    tasks_deleted = 0

    # Include ALL positions: root + split children (parent_position_id)
    all_pos_ids = list(position_ids)
    if position_ids:
        child_rows = db.execute(sa_text(
            f"SELECT id FROM order_positions WHERE parent_position_id IN "
            f"({','.join(repr(str(p)) for p in position_ids)})"
        )).fetchall()
        for row in child_rows:
            cid = row[0]
            if cid not in all_pos_ids:
                all_pos_ids.append(cid)

    try:
        if all_pos_ids:
            pids_str = ",".join(f"'{p}'" for p in all_pos_ids)

            # 1. Nullify self-referencing FK (parent_position_id) to break circular deps
            _sql_safe(db, f"UPDATE order_positions SET parent_position_id = NULL WHERE parent_position_id IN ({pids_str})")
            _sql_safe(db, f"UPDATE order_positions SET batch_id = NULL, resource_id = NULL, estimated_kiln_id = NULL, recipe_id = NULL WHERE id IN ({pids_str})")

            # 2. Delete from ALL FK tables
            # Delete ONLY consume/reserve/unreserve transactions (NOT audit/receive/inventory!)
            _sql_safe(db, f"DELETE FROM material_transactions WHERE related_position_id IN ({pids_str}) AND type IN ('consume', 'reserve', 'unreserve')")

            fk_tables = [
                # material_transactions handled above with type filter
                ("quality_checks", "position_id"),
                ("defect_records", "position_id"),
                ("grinding_stock", "source_position_id"),
                ("repair_queue", "source_position_id"),
                ("surplus_dispositions", "position_id"),
                ("order_packing_photos", "position_id"),
                ("worker_media", "related_position_id"),
                ("qm_blocks", "position_id"),
                ("notifications", "related_entity_id"),
                ("kiln_calculation_logs", "position_id"),
                ("operation_logs", "position_id"),
                ("stone_reservations", "position_id"),
                ("position_photos", "position_id"),
                ("shipment_items", "position_id"),
                ("order_stage_history", "position_id"),
                ("consumption_adjustments", "position_id"),
                ("tasks", "related_position_id"),
            ]
            for table, col in fk_tables:
                _sql_safe(db, f"DELETE FROM {table} WHERE {col} IN ({pids_str})")

        # Order-level FK refs (ONLY consume/reserve/unreserve — preserve audit/receive/inventory!)
        _sql_safe(db, f"DELETE FROM material_transactions WHERE related_order_id = '{order_id}' AND type IN ('consume', 'reserve', 'unreserve')")
        _sql_safe(db, f"DELETE FROM grinding_stock WHERE source_order_id = '{order_id}'")
        _sql_safe(db, f"DELETE FROM repair_queue WHERE source_order_id = '{order_id}'")
        _sql_safe(db, f"DELETE FROM surplus_dispositions WHERE order_id = '{order_id}'")
        _sql_safe(db, f"DELETE FROM casters_boxes WHERE source_order_id = '{order_id}'")
        _sql_safe(db, f"DELETE FROM order_packing_photos WHERE order_id = '{order_id}'")
        _sql_safe(db, f"DELETE FROM worker_media WHERE related_order_id = '{order_id}'")
        _sql_safe(db, f"DELETE FROM order_financials WHERE order_id = '{order_id}'")
        r = db.execute(sa_text(f"DELETE FROM tasks WHERE related_order_id = '{order_id}'"))
        tasks_deleted = r.rowcount

        # Shipments
        _sql_safe(db, f"DELETE FROM shipment_items WHERE shipment_id IN (SELECT id FROM shipments WHERE order_id = '{order_id}')")
        _sql_safe(db, f"DELETE FROM shipments WHERE order_id = '{order_id}'")

        # Status logs (may not CASCADE)
        _sql_safe(db, f"DELETE FROM production_order_status_logs WHERE order_id = '{order_id}'")

        # Finally delete order (CASCADE removes positions + items)
        db.execute(sa_text(f"DELETE FROM production_orders WHERE id = '{order_id}'"))
        db.commit()

    except Exception as e:
        db.rollback()
        logger.error("CLEANUP DELETE order FAILED | id=%s: %s", order_id, e)
        raise HTTPException(500, f"Cleanup failed: {str(e)[:200]}")

    logger.warning(
        "CLEANUP DELETE order | id=%s number=%s client=%s "
        "positions=%d tasks=%d | by %s",
        order_id,
        order_number,
        order_client,
        pos_count,
        tasks_deleted,
        current_user.email,
    )

    return {
        "deleted": "order",
        "id": str(order_id),
        "order_number": order_number,
        "positions_deleted": pos_count,
        "tasks_deleted": tasks_deleted,
    }
