"""
Defect Alert service — creates 5 Why tasks and alerts when defect % exceeds target.
Decision 2026-03-19.
"""
import logging
from typing import Optional

from sqlalchemy.orm import Session

from api.models import Task, User
from api.enums import TaskType, TaskStatus, UserRole

logger = logging.getLogger("moonjar.defect_alert")


def _find_quality_manager(db: Session, factory_id) -> Optional[User]:
    """Return an active QM for the factory, or None."""
    return (
        db.query(User)
        .filter(
            User.role == UserRole.QUALITY_MANAGER,
            User.is_active.is_(True),
        )
        .first()
    )


def create_five_why_task(
    db: Session,
    position,
    actual_defect_pct: float,
    target_defect_pct: float,
    glaze_type: str,
    product_type: str,
) -> Optional[Task]:
    """
    Create a Quality Check (5 Why / root-cause analysis) task for the Quality Manager
    when actual defect % exceeds the target threshold.

    TaskType.FIVE_WHY does not exist in enums → we use TaskType.QUALITY_CHECK.
    The task description and metadata_json carry the 5 Why context.

    Returns the created Task (not yet committed — caller flushes/commits).
    """
    try:
        actual_pct_display = round(actual_defect_pct * 100, 1)
        target_pct_display = round(target_defect_pct * 100, 1)
        excess_pct = round((actual_defect_pct - target_defect_pct) * 100, 1)

        description = (
            f"[5 WHY ANALYSIS REQUIRED] Defect rate exceeded threshold.\n"
            f"Position: {position.id}\n"
            f"Color: {getattr(position, 'color', '—')} | Size: {getattr(position, 'size', '—')}\n"
            f"Glaze type: {glaze_type} | Product type: {product_type}\n"
            f"Actual defect: {actual_pct_display}% | Target: {target_pct_display}% "
            f"(+{excess_pct}% above threshold)\n\n"
            f"Please conduct 5 Why root cause analysis and document findings."
        )

        metadata = {
            "alert_type": "five_why",
            "position_id": str(position.id),
            "order_id": str(getattr(position, 'order_id', None)),
            "actual_defect_pct": actual_pct_display,
            "target_defect_pct": target_pct_display,
            "excess_pct": excess_pct,
            "glaze_type": glaze_type,
            "product_type": product_type,
            "color": getattr(position, 'color', None),
            "size": getattr(position, 'size', None),
        }

        # Try to assign directly to a QM user; otherwise assign by role
        qm_user = _find_quality_manager(db, position.factory_id)

        task = Task(
            factory_id=position.factory_id,
            type=TaskType.QUALITY_CHECK,
            status=TaskStatus.PENDING,
            assigned_to=qm_user.id if qm_user else None,
            assigned_role=UserRole.QUALITY_MANAGER,
            related_position_id=position.id,
            related_order_id=getattr(position, 'order_id', None),
            blocking=False,
            priority=10,  # high priority — defect alert
            description=description,
            metadata_json=metadata,
        )

        db.add(task)
        db.flush()  # get task.id without full commit

        logger.info(
            "Created 5 Why task %s for position %s (actual=%.1f%% target=%.1f%%)",
            task.id, position.id, actual_pct_display, target_pct_display,
        )
        return task

    except Exception as exc:
        logger.error("Failed to create 5 Why task for position %s: %s", position.id, exc)
        return None
