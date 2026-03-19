"""
Kiln Breakdown Emergency Reschedule Service.
Business Logic: kiln emergency handling.

When a kiln breaks down mid-production:
1. Mark kiln as MAINTENANCE_EMERGENCY
2. Find all active/planned batches in that kiln
3. For each batch, find alternative kilns that:
   - Are operational (status = active)
   - Have capacity for the batch
   - Are at the same factory
4. Reassign batches to best available kiln
5. If no kiln available -> create escalation task for PM
6. Create maintenance record
7. Notify PM + CEO via notifications
8. Recalculate schedule for affected positions
"""
import logging
from datetime import datetime, date, timedelta, timezone
from uuid import UUID
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func

from api.models import (
    Resource,
    Batch,
    OrderPosition,
    ScheduleSlot,
    KilnMaintenanceSchedule,
    Task,
    Notification,
    User,
    UserFactory,
)
from api.enums import (
    ResourceType,
    ResourceStatus,
    BatchStatus,
    ScheduleSlotStatus,
    MaintenanceStatus,
    TaskType,
    TaskStatus,
    NotificationType,
    UserRole,
    RelatedEntityType,
)

logger = logging.getLogger("moonjar.kiln_breakdown")


# ────────────────────────────────────────────────────────────────
# Main entry point
# ────────────────────────────────────────────────────────────────

async def handle_kiln_breakdown(
    db: Session,
    kiln_id: UUID,
    reason: str,
    estimated_repair_hours: Optional[int],
    reported_by_id: UUID,
) -> dict:
    """
    Main entry point for kiln breakdown emergency.

    Returns a summary dict with:
      - kiln_id, kiln_name
      - maintenance_id
      - affected_batches: count of batches in the broken kiln
      - reassigned_batches: count successfully moved
      - failed_batches: count that could not be reassigned (escalated)
      - affected_positions: count of positions rescheduled
      - escalation_created: bool
    """
    # 1. Validate kiln exists
    kiln = db.query(Resource).filter(
        Resource.id == kiln_id,
        Resource.resource_type == ResourceType.KILN,
    ).first()
    if not kiln:
        raise ValueError(f"Kiln {kiln_id} not found")

    factory_id = kiln.factory_id
    kiln_name = kiln.name

    # 2. Mark kiln as MAINTENANCE_EMERGENCY
    old_status = kiln.status.value if hasattr(kiln.status, "value") else str(kiln.status)
    kiln.status = ResourceStatus.MAINTENANCE_EMERGENCY
    kiln.is_active = False
    kiln.updated_at = datetime.now(timezone.utc)

    # 3. Create emergency maintenance record
    maintenance = create_breakdown_maintenance(
        db, kiln_id, reason, estimated_repair_hours, reported_by_id, factory_id,
    )

    # 4. Find all active/planned batches in this kiln
    non_done_statuses = [BatchStatus.SUGGESTED, BatchStatus.PLANNED, BatchStatus.IN_PROGRESS]
    affected_batches = db.query(Batch).filter(
        Batch.resource_id == kiln_id,
        Batch.status.in_(non_done_statuses),
    ).all()

    # 5. Find alternative kilns at the same factory
    alternative_kilns = find_alternative_kilns(db, kiln, factory_id)

    # 6. Attempt to reassign each batch
    reassigned_count = 0
    failed_batches = []

    for batch in affected_batches:
        success = reassign_batch_to_kiln(db, batch, alternative_kilns)
        if success:
            reassigned_count += 1
        else:
            failed_batches.append(batch)

    # 7. If any batch could not be reassigned, create escalation task
    escalation_created = False
    if failed_batches:
        _create_escalation_task(
            db, factory_id, kiln_id, kiln_name, failed_batches, reported_by_id,
        )
        escalation_created = True

    # 8. Reschedule affected positions (positions with estimated_kiln_id == broken kiln)
    positions_rescheduled = _reschedule_affected_positions(db, kiln_id)

    # 9. Notify PM + CEO
    _notify_breakdown(
        db, factory_id, kiln_id, kiln_name, reason,
        len(affected_batches), reassigned_count, len(failed_batches),
        positions_rescheduled,
    )

    db.commit()

    result = {
        "kiln_id": str(kiln_id),
        "kiln_name": kiln_name,
        "old_status": old_status,
        "new_status": "maintenance_emergency",
        "maintenance_id": str(maintenance.id),
        "affected_batches": len(affected_batches),
        "reassigned_batches": reassigned_count,
        "failed_batches": len(failed_batches),
        "affected_positions": positions_rescheduled,
        "escalation_created": escalation_created,
        "estimated_repair_hours": estimated_repair_hours,
        "reason": reason,
    }

    logger.info(
        "KILN_BREAKDOWN | kiln=%s name=%s | batches: %d affected, %d reassigned, %d failed | positions: %d",
        kiln_id, kiln_name, len(affected_batches), reassigned_count,
        len(failed_batches), positions_rescheduled,
    )

    return result


# ────────────────────────────────────────────────────────────────
# Find alternative kilns
# ────────────────────────────────────────────────────────────────

def find_alternative_kilns(db: Session, broken_kiln: Resource, factory_id: UUID) -> list[Resource]:
    """
    Find operational kilns at the same factory that can handle
    the broken kiln's batches.

    Returns kilns sorted by current load (least loaded first).
    """
    kilns = db.query(Resource).filter(
        Resource.factory_id == factory_id,
        Resource.resource_type == ResourceType.KILN,
        Resource.is_active.is_(True),
        Resource.status == ResourceStatus.ACTIVE,
        Resource.id != broken_kiln.id,
    ).all()

    if not kilns:
        return []

    # Sort by current batch load (ascending — least loaded first)
    kiln_loads = []
    today = date.today()
    window_start = today - timedelta(days=1)
    window_end = today + timedelta(days=14)

    for kiln in kilns:
        batch_count = db.query(sa_func.count(Batch.id)).filter(
            Batch.resource_id == kiln.id,
            Batch.batch_date >= window_start,
            Batch.batch_date <= window_end,
            Batch.status.in_([BatchStatus.PLANNED.value, BatchStatus.IN_PROGRESS.value]),
        ).scalar() or 0
        kiln_loads.append((kiln, batch_count))

    kiln_loads.sort(key=lambda x: x[1])
    return [k for k, _ in kiln_loads]


# ────────────────────────────────────────────────────────────────
# Reassign batch
# ────────────────────────────────────────────────────────────────

def reassign_batch_to_kiln(db: Session, batch: Batch, alternative_kilns: list[Resource]) -> bool:
    """
    Move a batch from the broken kiln to the best available alternative kiln.

    Returns True if reassignment was successful, False if no kiln could accept it.
    """
    if not alternative_kilns:
        return False

    # Pick the first (least loaded) kiln
    target_kiln = alternative_kilns[0]

    old_kiln_id = batch.resource_id
    batch.resource_id = target_kiln.id
    batch.updated_at = datetime.now(timezone.utc)

    # Update batch notes
    note = f"[EMERGENCY] Reassigned from kiln breakdown. Original kiln: {old_kiln_id}"
    if batch.notes:
        batch.notes = f"{batch.notes}\n{note}"
    else:
        batch.notes = note

    # Also update any positions in this batch to point to new kiln
    positions = db.query(OrderPosition).filter(
        OrderPosition.batch_id == batch.id,
    ).all()
    for pos in positions:
        if pos.resource_id == old_kiln_id:
            pos.resource_id = target_kiln.id
            pos.updated_at = datetime.now(timezone.utc)
        if pos.estimated_kiln_id == old_kiln_id:
            pos.estimated_kiln_id = target_kiln.id

    # Also update schedule slots for this batch
    slots = db.query(ScheduleSlot).filter(
        ScheduleSlot.batch_id == batch.id,
        ScheduleSlot.status.in_([
            ScheduleSlotStatus.PLANNED,
            ScheduleSlotStatus.IN_PROGRESS,
        ]),
    ).all()
    for slot in slots:
        slot.resource_id = target_kiln.id

    logger.info(
        "BATCH_REASSIGNED | batch=%s | from_kiln=%s to_kiln=%s (%s) | %d positions updated",
        batch.id, old_kiln_id, target_kiln.id, target_kiln.name, len(positions),
    )

    return True


# ────────────────────────────────────────────────────────────────
# Create maintenance record
# ────────────────────────────────────────────────────────────────

def create_breakdown_maintenance(
    db: Session,
    kiln_id: UUID,
    reason: str,
    estimated_hours: Optional[int],
    reported_by: UUID,
    factory_id: UUID,
) -> KilnMaintenanceSchedule:
    """Create emergency maintenance record for the broken kiln."""
    maintenance = KilnMaintenanceSchedule(
        resource_id=kiln_id,
        maintenance_type=f"Emergency Breakdown: {reason}",
        scheduled_date=date.today(),
        estimated_duration_hours=estimated_hours,
        status=MaintenanceStatus.IN_PROGRESS,
        notes=f"Emergency breakdown reported. Reason: {reason}",
        created_by=reported_by,
        factory_id=factory_id,
        is_recurring=False,
        requires_empty_kiln=True,
        requires_cooled_kiln=True,
        requires_power_off=True,
    )
    db.add(maintenance)
    db.flush()  # Get the ID without committing
    return maintenance


# ────────────────────────────────────────────────────────────────
# Get affected positions
# ────────────────────────────────────────────────────────────────

def get_affected_positions(db: Session, kiln_id: UUID) -> list[OrderPosition]:
    """Get all non-terminal positions estimated to use the broken kiln."""
    from api.enums import PositionStatus

    terminal_statuses = {
        PositionStatus.SHIPPED.value,
        PositionStatus.CANCELLED.value,
        PositionStatus.READY_FOR_SHIPMENT.value,
        PositionStatus.PACKED.value,
    }

    return db.query(OrderPosition).filter(
        OrderPosition.estimated_kiln_id == kiln_id,
        OrderPosition.status.notin_(list(terminal_statuses)),
    ).all()


# ────────────────────────────────────────────────────────────────
# Reschedule affected positions
# ────────────────────────────────────────────────────────────────

def _reschedule_affected_positions(db: Session, kiln_id: UUID) -> int:
    """
    Reschedule all positions that were estimated to use the broken kiln.
    Delegates to the production_scheduler's reschedule_affected_by_kiln.
    """
    try:
        from business.services.production_scheduler import reschedule_affected_by_kiln
        count = reschedule_affected_by_kiln(db, kiln_id)
        return count
    except Exception as e:
        logger.error("Failed to reschedule positions for kiln %s: %s", kiln_id, e)
        return 0


# ────────────────────────────────────────────────────────────────
# Escalation task
# ────────────────────────────────────────────────────────────────

def _create_escalation_task(
    db: Session,
    factory_id: UUID,
    kiln_id: UUID,
    kiln_name: str,
    failed_batches: list[Batch],
    reported_by_id: UUID,
) -> Task:
    """Create an escalation task for PM when batches cannot be auto-reassigned."""
    batch_ids = ", ".join(str(b.id)[:8] for b in failed_batches)
    description = (
        f"URGENT: Kiln '{kiln_name}' breakdown — {len(failed_batches)} batch(es) "
        f"could not be automatically reassigned. No alternative kilns available.\n"
        f"Batch IDs: {batch_ids}\n"
        f"Manual reassignment or production delay decision required."
    )

    task = Task(
        factory_id=factory_id,
        type=TaskType.KILN_MAINTENANCE,
        status=TaskStatus.PENDING,
        assigned_role=UserRole.PRODUCTION_MANAGER,
        blocking=True,
        description=description,
        priority=10,  # Highest priority
        metadata_json={
            "kiln_id": str(kiln_id),
            "kiln_name": kiln_name,
            "failed_batch_ids": [str(b.id) for b in failed_batches],
            "type": "kiln_breakdown_escalation",
        },
    )
    db.add(task)
    db.flush()

    logger.warning(
        "ESCALATION_CREATED | kiln=%s | %d batches need manual reassignment",
        kiln_id, len(failed_batches),
    )
    return task


# ────────────────────────────────────────────────────────────────
# Notifications
# ────────────────────────────────────────────────────────────────

def _notify_breakdown(
    db: Session,
    factory_id: UUID,
    kiln_id: UUID,
    kiln_name: str,
    reason: str,
    affected_batches: int,
    reassigned_batches: int,
    failed_batches: int,
    positions_rescheduled: int,
) -> None:
    """Notify PM + CEO about the kiln breakdown."""
    title = f"KILN BREAKDOWN: {kiln_name}"
    message = (
        f"Kiln '{kiln_name}' has broken down.\n"
        f"Reason: {reason}\n"
        f"Affected batches: {affected_batches}\n"
        f"Auto-reassigned: {reassigned_batches}\n"
        f"Failed (need manual): {failed_batches}\n"
        f"Positions rescheduled: {positions_rescheduled}"
    )

    try:
        from business.services.notifications import notify_pm, notify_role
        # Notify PMs
        notify_pm(
            db=db,
            factory_id=factory_id,
            type=NotificationType.KILN_BREAKDOWN.value,
            title=title,
            message=message,
            related_entity_type=RelatedEntityType.KILN.value,
            related_entity_id=kiln_id,
        )
        # Notify CEOs
        notify_role(
            db=db,
            factory_id=factory_id,
            role=UserRole.CEO,
            type=NotificationType.KILN_BREAKDOWN.value,
            title=title,
            message=message,
            related_entity_type=RelatedEntityType.KILN.value,
            related_entity_id=kiln_id,
        )
    except Exception as e:
        logger.error("Failed to send breakdown notifications: %s", e)

    # Try Telegram notification to masters group
    try:
        from api.models import Factory
        factory = db.query(Factory).get(factory_id)
        if factory and hasattr(factory, "masters_group_chat_id") and factory.masters_group_chat_id:
            from business.services.notifications import send_telegram_message_with_buttons
            kid_short = str(kiln_id)[:8]
            tg_message = (
                f"*PERINGATAN KILN RUSAK*\n"
                f"Kiln: {kiln_name}\n"
                f"Alasan: {reason}\n"
                f"Batch terdampak: {affected_batches}\n"
                f"Otomatis dipindah: {reassigned_batches}\n"
                f"Perlu manual: {failed_batches}"
            )
            buttons = [
                [{"text": "Jadwal ulang", "callback_data": f"a:r:{kid_short}"}],
            ]
            send_telegram_message_with_buttons(
                str(factory.masters_group_chat_id),
                tg_message,
                buttons,
            )
    except Exception as e:
        logger.warning("Failed to send Telegram breakdown alert: %s", e)


# ────────────────────────────────────────────────────────────────
# Kiln restore
# ────────────────────────────────────────────────────────────────

async def handle_kiln_restore(
    db: Session,
    kiln_id: UUID,
    restored_by_id: UUID,
    notes: Optional[str] = None,
) -> dict:
    """
    Restore a kiln to active status after repair.

    1. Set kiln status back to ACTIVE
    2. Complete any in-progress emergency maintenance records
    3. Notify PM
    """
    kiln = db.query(Resource).filter(
        Resource.id == kiln_id,
        Resource.resource_type == ResourceType.KILN,
    ).first()
    if not kiln:
        raise ValueError(f"Kiln {kiln_id} not found")

    old_status = kiln.status.value if hasattr(kiln.status, "value") else str(kiln.status)
    kiln_name = kiln.name
    factory_id = kiln.factory_id

    # Set to active
    kiln.status = ResourceStatus.ACTIVE
    kiln.is_active = True
    kiln.updated_at = datetime.now(timezone.utc)

    # Complete in-progress emergency maintenance records for this kiln
    open_maintenances = db.query(KilnMaintenanceSchedule).filter(
        KilnMaintenanceSchedule.resource_id == kiln_id,
        KilnMaintenanceSchedule.status == MaintenanceStatus.IN_PROGRESS,
    ).all()

    for m in open_maintenances:
        m.status = MaintenanceStatus.DONE
        m.completed_at = datetime.now(timezone.utc)
        m.completed_by_id = restored_by_id
        if notes:
            m.notes = (m.notes or "") + f"\nRepair completed: {notes}"
        m.updated_at = datetime.now(timezone.utc)

    # Notify PM about restoration
    try:
        from business.services.notifications import notify_pm
        notify_pm(
            db=db,
            factory_id=factory_id,
            type=NotificationType.KILN_BREAKDOWN.value,
            title=f"Kiln RESTORED: {kiln_name}",
            message=f"Kiln '{kiln_name}' is back online and active.{(' Notes: ' + notes) if notes else ''}",
            related_entity_type=RelatedEntityType.KILN.value,
            related_entity_id=kiln_id,
        )
    except Exception as e:
        logger.warning("Failed to send kiln restore notification: %s", e)

    db.commit()

    result = {
        "kiln_id": str(kiln_id),
        "kiln_name": kiln_name,
        "old_status": old_status,
        "new_status": "active",
        "maintenance_records_completed": len(open_maintenances),
        "notes": notes,
    }

    logger.info(
        "KILN_RESTORED | kiln=%s name=%s | %d maintenance records completed",
        kiln_id, kiln_name, len(open_maintenances),
    )

    return result
