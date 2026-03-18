"""
Quality Control service.
Business Logic: §10, §25

Functions:
  - assign_qc_checks      — after kiln exit, assign QC tasks for positions in a batch
  - on_qc_defect_found     — record defect, block if critical, notify PM
  - qm_block_production    — QM blocks a position with evidence photos
  - qm_unblock_production  — QM resolves a block, position returns to previous status
"""
import uuid as uuid_mod
import logging
from uuid import UUID
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from api.models import (
    OrderPosition, Task, QualityCheck, QualityAssignmentConfig,
    DefectRecord, QmBlock, Notification, User, UserFactory, Batch,
)
from api.enums import (
    TaskType, TaskStatus, PositionStatus, UserRole,
    QcResult, QcStage, DefectStage, DefectOutcome,
    QmBlockType, NotificationType, RelatedEntityType,
)

logger = logging.getLogger("moonjar.quality_control")


# ────────────────────────────────────────────────────────────────
# 1. assign_qc_checks
# ────────────────────────────────────────────────────────────────

def assign_qc_checks(
    db: Session,
    batch_id: UUID,
    factory_id: UUID,
) -> list[Task]:
    """
    After a batch exits the kiln, assign QC check tasks.

    - Fetches all positions in the batch
    - Determines sample size from QualityAssignmentConfig (minimum 2%)
    - Positions with mandatory_qc are always included
    - Creates a QUALITY_CHECK task per selected position (blocking)
    - Transitions selected positions to SENT_TO_QUALITY_CHECK
    - Returns list of created tasks
    """
    positions = (
        db.query(OrderPosition)
        .filter(
            OrderPosition.batch_id == batch_id,
            OrderPosition.factory_id == factory_id,
            OrderPosition.status == PositionStatus.FIRED,
        )
        .all()
    )

    if not positions:
        logger.info("assign_qc_checks: no FIRED positions in batch %s", batch_id)
        return []

    # Load QC config for the FIRING stage at this factory
    config = (
        db.query(QualityAssignmentConfig)
        .filter(
            QualityAssignmentConfig.factory_id == factory_id,
            QualityAssignmentConfig.stage == QcStage.FIRING,
        )
        .first()
    )
    current_pct = float(config.current_percentage) if config else 2.0

    # Determine which positions to check:
    #   - all mandatory_qc positions
    #   - random sample of the rest up to current_pct %
    mandatory = [p for p in positions if p.mandatory_qc]
    non_mandatory = [p for p in positions if not p.mandatory_qc]

    sample_count = max(1, round(len(non_mandatory) * current_pct / 100))
    # Take the first N non-mandatory (in production a random shuffle would be better,
    # but deterministic selection is acceptable for now).
    sampled = non_mandatory[:sample_count]

    selected = mandatory + sampled
    if not selected:
        logger.info("assign_qc_checks: sample is empty for batch %s", batch_id)
        return []

    created_tasks: list[Task] = []
    now = datetime.now(timezone.utc)

    for pos in selected:
        task = Task(
            id=uuid_mod.uuid4(),
            factory_id=factory_id,
            type=TaskType.QUALITY_CHECK,
            status=TaskStatus.PENDING,
            assigned_role=UserRole.QUALITY_MANAGER,
            related_order_id=pos.order_id,
            related_position_id=pos.id,
            blocking=True,
            description=(
                f"QC check after firing — position {pos.color} {pos.size} "
                f"(qty {pos.quantity})"
            ),
            priority=2,
            metadata_json={
                "batch_id": str(batch_id),
                "stage": QcStage.FIRING.value,
                "mandatory_qc": pos.mandatory_qc,
            },
            created_at=now,
            updated_at=now,
        )
        db.add(task)
        created_tasks.append(task)

        # Transition position so it is blocked until QC completes
        pos.status = PositionStatus.SENT_TO_QUALITY_CHECK
        pos.updated_at = now

    db.flush()
    logger.info(
        "assign_qc_checks: created %d QC tasks for batch %s (%d mandatory, %d sampled)",
        len(created_tasks), batch_id, len(mandatory), len(sampled),
    )
    return created_tasks


# ────────────────────────────────────────────────────────────────
# 2. on_qc_defect_found
# ────────────────────────────────────────────────────────────────

def on_qc_defect_found(
    db: Session,
    position_id: UUID,
    defect_type: str,
    severity: str,
    notes: Optional[str],
    inspector_id: UUID,
) -> OrderPosition:
    """
    When QC inspector finds a defect:

    - Creates a QualityCheck record with result=DEFECT
    - Creates a DefectRecord
    - If severity is 'critical' → blocks position (BLOCKED_BY_QM) and creates PM task
    - If severity is 'minor' → adds note, position can continue
    - Increases the factory/stage QC inspection percentage
    - Returns the updated position
    """
    position = db.query(OrderPosition).filter(OrderPosition.id == position_id).first()
    if not position:
        raise ValueError(f"Position {position_id} not found")

    now = datetime.now(timezone.utc)

    # 1. Create QualityCheck record
    qc_check = QualityCheck(
        id=uuid_mod.uuid4(),
        position_id=position.id,
        factory_id=position.factory_id,
        stage=QcStage.FIRING,
        result=QcResult.DEFECT,
        notes=notes,
        checked_by=inspector_id,
        created_at=now,
    )
    db.add(qc_check)

    # 2. Map severity to DefectOutcome
    if severity == "critical":
        outcome = DefectOutcome.WRITE_OFF
    else:
        outcome = DefectOutcome.RETURN_TO_WORK

    # 3. Create DefectRecord
    defect_record = DefectRecord(
        id=uuid_mod.uuid4(),
        factory_id=position.factory_id,
        stage=DefectStage.AFTER_FIRING,
        position_id=position.id,
        batch_id=position.batch_id,
        defect_type=defect_type,
        quantity=position.quantity,
        outcome=outcome,
        reported_by=inspector_id,
        reported_via="dashboard",
        notes=notes,
        date=now.date(),
        created_at=now,
    )
    db.add(defect_record)

    # 4. Handle severity
    if severity == "critical":
        # Block position
        position.status = PositionStatus.BLOCKED_BY_QM
        position.updated_at = now

        # Create QmBlock record
        qm_block = QmBlock(
            id=uuid_mod.uuid4(),
            factory_id=position.factory_id,
            block_type=QmBlockType.POSITION,
            position_id=position.id,
            batch_id=position.batch_id,
            reason=f"Critical defect: {defect_type}",
            severity="critical",
            blocked_by=inspector_id,
            created_at=now,
        )
        db.add(qm_block)

        # Create PM notification task
        pm_task = Task(
            id=uuid_mod.uuid4(),
            factory_id=position.factory_id,
            type=TaskType.QUALITY_CHECK,
            status=TaskStatus.PENDING,
            assigned_role=UserRole.PRODUCTION_MANAGER,
            related_order_id=position.order_id,
            related_position_id=position.id,
            blocking=True,
            description=(
                f"CRITICAL defect found: {defect_type} — "
                f"position {position.color} {position.size} blocked by QM"
            ),
            priority=4,
            metadata_json={
                "defect_type": defect_type,
                "severity": severity,
                "qc_check_id": str(qc_check.id),
                "defect_record_id": str(defect_record.id),
                "qm_block_id": str(qm_block.id),
            },
            created_at=now,
            updated_at=now,
        )
        db.add(pm_task)

        # Notify PM via notification service
        try:
            from business.services.notifications import notify_pm
            notify_pm(
                db=db,
                factory_id=position.factory_id,
                type=NotificationType.ALERT.value,
                title=f"Critical QC defect: {defect_type}",
                message=(
                    f"Position {position.color} {position.size} (qty {position.quantity}) "
                    f"has been blocked due to a critical defect."
                ),
                related_entity_type=RelatedEntityType.POSITION.value,
                related_entity_id=position.id,
            )
        except Exception as e:
            logger.warning("Failed to notify PM about critical defect: %s", e)

        logger.warning(
            "on_qc_defect_found: CRITICAL defect '%s' on position %s — blocked",
            defect_type, position_id,
        )
    else:
        # Minor defect — position can continue, just log it
        position.updated_at = now
        logger.info(
            "on_qc_defect_found: minor defect '%s' on position %s — noted",
            defect_type, position_id,
        )

    # 5. Increase QC inspection percentage for this factory/stage
    _increase_inspection_percentage(db, position.factory_id, QcStage.FIRING)

    db.flush()
    return position


def _increase_inspection_percentage(
    db: Session,
    factory_id: UUID,
    stage: QcStage,
) -> None:
    """Increase the QC inspection percentage for a factory/stage after a defect is found."""
    config = (
        db.query(QualityAssignmentConfig)
        .filter(
            QualityAssignmentConfig.factory_id == factory_id,
            QualityAssignmentConfig.stage == stage,
        )
        .first()
    )
    now = datetime.now(timezone.utc)
    if config:
        increase = float(config.increase_on_defect_percentage)
        new_pct = float(config.current_percentage) + increase
        # Cap at 100%
        config.current_percentage = min(new_pct, 100.0)
        config.updated_at = now
        logger.info(
            "QC inspection %% for factory %s stage %s increased to %.1f%%",
            factory_id, stage.value, float(config.current_percentage),
        )
    else:
        # Create a default config with increased percentage
        config = QualityAssignmentConfig(
            id=uuid_mod.uuid4(),
            factory_id=factory_id,
            stage=stage,
            base_percentage=2.0,
            increase_on_defect_percentage=2.0,
            current_percentage=4.0,  # base 2% + first increase 2%
            updated_at=now,
        )
        db.add(config)
        logger.info(
            "Created QC config for factory %s stage %s with initial 4%%",
            factory_id, stage.value,
        )


# ────────────────────────────────────────────────────────────────
# 3. qm_block_production
# ────────────────────────────────────────────────────────────────

def qm_block_production(
    db: Session,
    position_id: UUID,
    qm_user_id: UUID,
    reason: str,
    evidence_urls: list[str],
) -> QmBlock:
    """
    QM blocks a position with evidence photos.

    - Creates a QmBlock record
    - Sets position status to BLOCKED_BY_QM (saves previous status in metadata)
    - Notifies PM and CEO
    - Returns the QmBlock record
    """
    position = db.query(OrderPosition).filter(OrderPosition.id == position_id).first()
    if not position:
        raise ValueError(f"Position {position_id} not found")

    now = datetime.now(timezone.utc)
    previous_status = position.status.value if hasattr(position.status, "value") else str(position.status)

    # Create QmBlock record
    block = QmBlock(
        id=uuid_mod.uuid4(),
        factory_id=position.factory_id,
        block_type=QmBlockType.POSITION,
        position_id=position.id,
        batch_id=position.batch_id,
        reason=reason,
        severity="critical",
        photo_urls=evidence_urls,
        blocked_by=qm_user_id,
        created_at=now,
    )
    db.add(block)

    # Transition position to blocked
    position.status = PositionStatus.BLOCKED_BY_QM
    position.updated_at = now

    # Create a blocking task for PM
    task = Task(
        id=uuid_mod.uuid4(),
        factory_id=position.factory_id,
        type=TaskType.QUALITY_CHECK,
        status=TaskStatus.PENDING,
        assigned_role=UserRole.PRODUCTION_MANAGER,
        related_order_id=position.order_id,
        related_position_id=position.id,
        blocking=True,
        description=f"QM blocked position: {reason}",
        priority=4,
        metadata_json={
            "qm_block_id": str(block.id),
            "previous_status": previous_status,
            "evidence_urls": evidence_urls,
        },
        created_at=now,
        updated_at=now,
    )
    db.add(task)

    # Notify PM and CEO
    try:
        from business.services.notifications import notify_pm, notify_role
        notify_pm(
            db=db,
            factory_id=position.factory_id,
            type=NotificationType.ALERT.value,
            title=f"QM blocked position: {position.color} {position.size}",
            message=reason,
            related_entity_type=RelatedEntityType.POSITION.value,
            related_entity_id=position.id,
        )
        notify_role(
            db=db,
            factory_id=position.factory_id,
            role=UserRole.CEO,
            type=NotificationType.ALERT.value,
            title=f"QM blocked position: {position.color} {position.size}",
            message=reason,
            related_entity_type=RelatedEntityType.POSITION.value,
            related_entity_id=position.id,
        )
    except Exception as e:
        logger.warning("Failed to send QM block notifications: %s", e)

    db.flush()

    logger.info(
        "qm_block_production: position %s blocked by QM user %s — reason: %s",
        position_id, qm_user_id, reason,
    )
    return block


# ────────────────────────────────────────────────────────────────
# 4. qm_unblock_production
# ────────────────────────────────────────────────────────────────

def qm_unblock_production(
    db: Session,
    block_id: UUID,
    qm_user_id: UUID,
    resolution: str,
) -> QmBlock:
    """
    QM resolves a block — position returns to previous status.

    - Marks the QmBlock as resolved
    - Restores position status from the associated task metadata (previous_status)
    - Closes associated blocking tasks
    - Notifies PM
    - Returns the updated QmBlock record
    """
    block = db.query(QmBlock).filter(QmBlock.id == block_id).first()
    if not block:
        raise ValueError(f"QmBlock {block_id} not found")

    if block.resolved_at is not None:
        raise ValueError(f"QmBlock {block_id} is already resolved")

    now = datetime.now(timezone.utc)

    # Resolve the block
    block.resolved_by = qm_user_id
    block.resolved_at = now
    block.resolution_note = resolution

    # Find the associated blocking task to retrieve previous_status
    related_task = (
        db.query(Task)
        .filter(
            Task.related_position_id == block.position_id,
            Task.type == TaskType.QUALITY_CHECK,
            Task.status.notin_([TaskStatus.DONE, TaskStatus.CANCELLED]),
            Task.blocking.is_(True),
        )
        .first()
    )

    # Determine the status to restore
    previous_status = None
    if related_task and related_task.metadata_json:
        previous_status = related_task.metadata_json.get("previous_status")

    # Default to FIRED if we can't determine the previous status
    restore_status = PositionStatus.FIRED
    if previous_status:
        try:
            restore_status = PositionStatus(previous_status)
        except ValueError:
            logger.warning(
                "qm_unblock_production: unknown previous_status '%s', defaulting to FIRED",
                previous_status,
            )

    # Restore position status
    if block.position_id:
        position = db.query(OrderPosition).filter(OrderPosition.id == block.position_id).first()
        if position and (
            position.status == PositionStatus.BLOCKED_BY_QM
            or (hasattr(position.status, "value") and position.status.value == "blocked_by_qm")
        ):
            position.status = restore_status
            position.updated_at = now
            logger.info(
                "qm_unblock_production: position %s restored to %s",
                block.position_id, restore_status.value,
            )

    # Close all related blocking QC tasks for this position
    related_tasks = (
        db.query(Task)
        .filter(
            Task.related_position_id == block.position_id,
            Task.type == TaskType.QUALITY_CHECK,
            Task.status.notin_([TaskStatus.DONE, TaskStatus.CANCELLED]),
        )
        .all()
    )
    for t in related_tasks:
        t.status = TaskStatus.DONE
        t.completed_at = now
        t.updated_at = now

    # Notify PM
    try:
        from business.services.notifications import notify_pm
        position = db.query(OrderPosition).filter(OrderPosition.id == block.position_id).first()
        title = "QM unblocked position"
        if position:
            title = f"QM unblocked position: {position.color} {position.size}"
        notify_pm(
            db=db,
            factory_id=block.factory_id,
            type=NotificationType.STATUS_CHANGE.value,
            title=title,
            message=f"Resolution: {resolution}",
            related_entity_type=RelatedEntityType.POSITION.value,
            related_entity_id=block.position_id,
        )
    except Exception as e:
        logger.warning("Failed to send QM unblock notification: %s", e)

    db.flush()

    logger.info(
        "qm_unblock_production: block %s resolved by QM user %s — %s",
        block_id, qm_user_id, resolution,
    )
    return block
