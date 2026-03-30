"""
Escalation Engine.
Business Logic: §36 (Notifications & Escalation)

Handles task escalation chains: PM → CEO → Owner.
Night alerts only for kiln events (temperature deviation, kiln shutdown).
Escalation levels: 1=morning message, 2=repeat every 30min, 3=voice call.
"""
import logging
from datetime import datetime, timezone, timedelta
from uuid import UUID
from typing import Optional

from sqlalchemy.orm import Session

from api.models import (
    Task, EscalationRule, User, UserFactory, Notification,
)
from api.enums import TaskStatus, UserRole, NotificationType, NightAlertLevel

logger = logging.getLogger("moonjar.escalation")

# Night hours (factory local time, Bali = WITA = UTC+8)
NIGHT_START_HOUR = 21  # 9 PM
NIGHT_END_HOUR = 6     # 6 AM
BALI_UTC_OFFSET = 8

# Task types that trigger night alerts (kiln-related only)
NIGHT_ALERT_TASK_TYPES = frozenset({
    "kiln_breakdown",
    "kiln_temperature_deviation",
    "kiln_power_failure",
    "kiln_emergency",
})


def is_night_time(utc_now: Optional[datetime] = None) -> bool:
    """Check if current time is night in Bali (WITA, UTC+8)."""
    if utc_now is None:
        utc_now = datetime.now(timezone.utc)
    local_hour = (utc_now.hour + BALI_UTC_OFFSET) % 24
    return local_hour >= NIGHT_START_HOUR or local_hour < NIGHT_END_HOUR


def check_and_escalate(db: Session, factory_id: UUID) -> list[dict]:
    """
    Check all active tasks for escalation needs.

    Escalation chain:
    1. Task assigned to PM → if not resolved in pm_timeout_hours → escalate to CEO
    2. CEO notified → if not resolved in ceo_timeout_hours → escalate to Owner
    3. Owner notified → if not resolved in owner_timeout_hours → voice call

    Night mode (21:00-06:00 Bali time):
    - Only kiln-related alerts are sent at night
    - All other escalations are deferred to morning (06:00)
    - Kiln alerts: level 1=telegram, level 2=repeat every 30min, level 3=voice call

    Returns list of escalation actions taken.
    """
    now = datetime.now(timezone.utc)
    night = is_night_time(now)
    actions = []

    # Get all pending/in-progress tasks for this factory
    active_tasks = db.query(Task).filter(
        Task.factory_id == factory_id,
        Task.status.in_([TaskStatus.PENDING.value, TaskStatus.IN_PROGRESS.value]),
    ).all()

    if not active_tasks:
        return actions

    # Load escalation rules for this factory
    rules = {}
    for rule in db.query(EscalationRule).filter(
        EscalationRule.factory_id == factory_id,
        EscalationRule.is_active == True,  # noqa: E712
    ).all():
        rules[rule.task_type] = rule

    # Get role → user mapping for this factory
    pm_users = _get_users_by_role(db, factory_id, UserRole.PRODUCTION_MANAGER)
    ceo_users = _get_users_by_role(db, factory_id, UserRole.CEO)
    owner_users = _get_users_by_role(db, factory_id, UserRole.OWNER)

    for task in active_tasks:
        task_type = task.type.value if hasattr(task.type, "value") else str(task.type)
        rule = rules.get(task_type)
        if not rule:
            # Use defaults
            rule = _default_rule()

        age_hours = (now - task.created_at).total_seconds() / 3600

        # Night check: only kiln alerts proceed at night
        if night and task_type not in NIGHT_ALERT_TASK_TYPES:
            # Defer non-kiln escalation to morning
            continue

        # Determine current escalation level
        current_level = _get_escalation_level(task)

        # Level 0 → PM (already assigned, check if timeout exceeded)
        if current_level == 0 and age_hours >= float(rule.pm_timeout_hours):
            # Escalate to CEO
            for user in ceo_users:
                _send_escalation(
                    db, task, user, "ceo",
                    f"Escalated: {task_type} not resolved by PM in {rule.pm_timeout_hours}h",
                    night=night,
                )
            _set_escalation_level(task, 1, night=night)
            actions.append({
                "task_id": str(task.id),
                "task_type": task_type,
                "escalated_to": "ceo",
                "age_hours": round(age_hours, 1),
            })

        # Level 1 → CEO timeout → escalate to Owner
        elif current_level == 1 and age_hours >= float(rule.ceo_timeout_hours):
            for user in owner_users:
                _send_escalation(
                    db, task, user, "owner",
                    f"URGENT: {task_type} not resolved by CEO in {rule.ceo_timeout_hours}h",
                    night=night,
                )
            _set_escalation_level(task, 2, night=night)
            actions.append({
                "task_id": str(task.id),
                "task_type": task_type,
                "escalated_to": "owner",
                "age_hours": round(age_hours, 1),
            })

        # Level 2 → Owner timeout → voice call attempt
        elif current_level == 2 and age_hours >= float(rule.owner_timeout_hours):
            for user in owner_users:
                _request_voice_call(db, task, user)
            _set_escalation_level(task, 3, night=night)
            actions.append({
                "task_id": str(task.id),
                "task_type": task_type,
                "escalated_to": "voice_call",
                "age_hours": round(age_hours, 1),
            })

        # Night kiln alerts: repeat every 30 min at level 2+
        if night and task_type in NIGHT_ALERT_TASK_TYPES and current_level >= 1:
            last_notif_at = _get_last_notification_time(task)
            if last_notif_at and (now - last_notif_at).total_seconds() >= 1800:
                target_users = ceo_users + owner_users
                for user in target_users:
                    _send_escalation(
                        db, task, user, "night_repeat",
                        f"NIGHT ALERT (repeat): {task_type} still unresolved",
                        night=True,
                    )
                # Mark night alert mode as REPEAT for kiln night repeats
                if not task.metadata_json or not isinstance(task.metadata_json, dict):
                    task.metadata_json = {}
                task.metadata_json["night_alert_mode"] = NightAlertLevel.REPEAT.value
                actions.append({
                    "task_id": str(task.id),
                    "task_type": task_type,
                    "escalated_to": "night_repeat",
                    "age_hours": round(age_hours, 1),
                })

    db.flush()
    return actions


def get_deferred_morning_alerts(db: Session, factory_id: UUID) -> list[dict]:
    """
    Get non-kiln tasks that were deferred during night.
    Should be called at 06:00 Bali time by scheduler.
    """
    now = datetime.now(timezone.utc)
    morning_cutoff = now - timedelta(hours=12)  # Tasks created in last 12h

    tasks = db.query(Task).filter(
        Task.factory_id == factory_id,
        Task.status.in_([TaskStatus.PENDING.value, TaskStatus.IN_PROGRESS.value]),
        Task.created_at >= morning_cutoff,
    ).all()

    deferred = []
    for task in tasks:
        task_type = task.type.value if hasattr(task.type, "value") else str(task.type)
        if task_type not in NIGHT_ALERT_TASK_TYPES:
            deferred.append({
                "task_id": str(task.id),
                "task_type": task_type,
                "created_at": task.created_at.isoformat(),
                "description": task.description,
            })

    return deferred


# ── Helpers ──────────────────────────────────────────────────

def _get_users_by_role(db: Session, factory_id: UUID, role: UserRole) -> list[User]:
    """Get active users with a specific role for a factory."""
    return db.query(User).join(
        UserFactory, UserFactory.user_id == User.id,
    ).filter(
        UserFactory.factory_id == factory_id,
        User.role == role.value,
        User.is_active == True,  # noqa: E712
    ).all()


def _default_rule():
    """Return a default escalation rule when none is configured."""
    class _Default:
        pm_timeout_hours = 4
        ceo_timeout_hours = 8
        owner_timeout_hours = 24
        night_level = 1
    return _Default()


def _get_escalation_level(task: Task) -> int:
    """Get current escalation level from task metadata."""
    if task.metadata_json and isinstance(task.metadata_json, dict):
        return task.metadata_json.get("escalation_level", 0)
    return 0


def _level_to_night_alert(level: int, is_kiln: bool, night: bool) -> Optional[str]:
    """Map escalation level to NightAlertLevel value for night escalations."""
    if not night:
        return None
    if not is_kiln:
        return NightAlertLevel.MORNING.value
    # Kiln tasks at night: level 2+ repeat, level 3 = call
    if level >= 3:
        return NightAlertLevel.CALL.value
    if level >= 2:
        return NightAlertLevel.REPEAT.value
    return NightAlertLevel.MORNING.value


def _set_escalation_level(task: Task, level: int, night: bool = False):
    """Set escalation level in task metadata."""
    if not task.metadata_json or not isinstance(task.metadata_json, dict):
        task.metadata_json = {}
    task.metadata_json["escalation_level"] = level
    task.metadata_json["escalated_at"] = datetime.now(timezone.utc).isoformat()
    task_type = task.type.value if hasattr(task.type, "value") else str(task.type)
    is_kiln = task_type in NIGHT_ALERT_TASK_TYPES
    alert_mode = _level_to_night_alert(level, is_kiln, night)
    if alert_mode:
        task.metadata_json["night_alert_mode"] = alert_mode


def _get_last_notification_time(task: Task) -> Optional[datetime]:
    """Get time of last escalation notification from metadata."""
    if task.metadata_json and isinstance(task.metadata_json, dict):
        ts = task.metadata_json.get("last_notification_at")
        if ts:
            try:
                return datetime.fromisoformat(ts)
            except (ValueError, TypeError):
                pass
    return None


def _send_escalation(
    db: Session,
    task: Task,
    user: User,
    level: str,
    message: str,
    night: bool = False,
):
    """Send escalation notification (in-app + telegram)."""
    import uuid as uuid_mod

    notif = Notification(
        id=uuid_mod.uuid4(),
        user_id=user.id,
        factory_id=task.factory_id,
        type=NotificationType.ALERT.value,
        title=f"Escalation ({level}): {task.type if isinstance(task.type, str) else task.type.value}",
        message=message,
        related_entity_type="task",
        related_entity_id=task.id,
    )
    db.add(notif)

    # Update task metadata
    if not task.metadata_json or not isinstance(task.metadata_json, dict):
        task.metadata_json = {}
    task.metadata_json["last_notification_at"] = datetime.now(timezone.utc).isoformat()
    task.metadata_json[f"escalated_to_{level}"] = user.id.hex if hasattr(user.id, "hex") else str(user.id)

    # Try Telegram notification
    try:
        if hasattr(user, "telegram_chat_id") and user.telegram_chat_id:
            from business.services.telegram_bot import send_message
            emoji = "🔴" if night else "⚠️"
            send_message(
                user.telegram_chat_id,
                f"{emoji} {message}\n\nTask: {task.description or task.type}",
            )
    except Exception as e:
        logger.warning(f"Telegram escalation failed for user {user.id}: {e}")

    logger.info(f"Escalation sent: task={task.id} level={level} user={user.id} night={night}")


def _request_voice_call(db: Session, task: Task, user: User):
    """
    Request a voice call for critical escalation (kiln emergencies).
    Currently logs + creates high-priority notification.
    Actual voice call integration (Twilio/etc) is v2.
    """
    import uuid as uuid_mod

    logger.critical(
        f"VOICE CALL REQUESTED: task={task.id} type={task.type} user={user.id} name={user.name}"
    )

    notif = Notification(
        id=uuid_mod.uuid4(),
        user_id=user.id,
        factory_id=task.factory_id,
        type=NotificationType.ALERT.value,
        title=f"🚨 VOICE CALL: {task.type if isinstance(task.type, str) else task.type.value}",
        message=f"Critical escalation — attempted voice call. Task: {task.description or 'N/A'}",
        related_entity_type="task",
        related_entity_id=task.id,
    )
    db.add(notif)

    # Update metadata
    if not task.metadata_json or not isinstance(task.metadata_json, dict):
        task.metadata_json = {}
    task.metadata_json["voice_call_requested"] = True
    task.metadata_json["voice_call_at"] = datetime.now(timezone.utc).isoformat()

    # Try Telegram as backup
    try:
        if hasattr(user, "telegram_chat_id") and user.telegram_chat_id:
            from business.services.telegram_bot import send_message
            send_message(
                user.telegram_chat_id,
                f"🚨🚨🚨 CRITICAL: {task.description or task.type}\n\n"
                f"Voice call attempted. Please respond immediately!",
            )
    except Exception as e:
        logger.warning("Failed to send escalation call notification: %s", e)
