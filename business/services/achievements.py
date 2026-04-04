"""
Master Achievement System — gamification Phase 6.

Achievement types and level thresholds:
- glazing_master:    100 / 500 / 1000 / 5000 / 10000 positions glazed
- zero_defect_hero:  10 / 30 / 90 / 180 / 365 consecutive zero-defect days
- speed_champion:    7 / 14 / 30 / 60 / 90 days avg cycle < factory avg
- kiln_expert:       50 / 200 / 500 / 1500 / 5000 firings managed
- quality_star:      50 / 200 / 500 / 1500 / 5000 QC checks passed

Level names: Apprentice (1), Craftsman (2), Expert (3), Master (4), Grand Master (5)
"""

import logging
from datetime import datetime, timezone, date, timedelta
from uuid import UUID
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func, cast, Date

from api.models import (
    MasterAchievement, User, UserFactory,
    OrderPosition, Batch, QualityCheck, DefectRecord,
    OperationLog,
)
from api.enums import (
    PositionStatus, BatchStatus, QcResult, UserRole,
)
from business.services.notifications import send_telegram_message, get_forum_topic

logger = logging.getLogger("moonjar.achievements")

# ── Achievement definitions ────────────────────────────────────

ACHIEVEMENT_TYPES = {
    "glazing_master": {
        "label": "Glazing Master",
        "icon": "\U0001F3A8",
        "thresholds": [100, 500, 1000, 5000, 10000],
    },
    "zero_defect_hero": {
        "label": "Zero Defect Hero",
        "icon": "\u2728",
        "thresholds": [10, 30, 90, 180, 365],
    },
    "speed_champion": {
        "label": "Speed Champion",
        "icon": "\u26A1",
        "thresholds": [7, 14, 30, 60, 90],
    },
    "kiln_expert": {
        "label": "Kiln Expert",
        "icon": "\U0001F525",
        "thresholds": [50, 200, 500, 1500, 5000],
    },
    "quality_star": {
        "label": "Quality Star",
        "icon": "\u2B50",
        "thresholds": [50, 200, 500, 1500, 5000],
    },
    "skill_collector": {
        "label": "Skill Collector",
        "icon": "\U0001F393",
        "thresholds": [2, 5, 10, 15, 20],
    },
    "competition_winner": {
        "label": "Competition Winner",
        "icon": "\U0001F3C6",
        "thresholds": [1, 5, 10, 25, 50],
    },
}

LEVEL_NAMES = {
    0: "Locked",
    1: "Apprentice",
    2: "Craftsman",
    3: "Expert",
    4: "Master",
    5: "Grand Master",
}


def get_level_name(level: int) -> str:
    return LEVEL_NAMES.get(level, "Unknown")


def _get_threshold_for_level(achievement_type: str, level: int) -> int:
    """Return the threshold needed for the given level (1-5). Returns 0 for level 0."""
    if level <= 0:
        return 0
    thresholds = ACHIEVEMENT_TYPES[achievement_type]["thresholds"]
    idx = min(level - 1, len(thresholds) - 1)
    return thresholds[idx]


def _get_next_threshold(achievement_type: str, current_level: int) -> Optional[int]:
    """Return the threshold for the next level, or None if maxed."""
    if current_level >= 5:
        return None
    thresholds = ACHIEVEMENT_TYPES[achievement_type]["thresholds"]
    idx = current_level  # level 0 -> thresholds[0] for next
    if idx < len(thresholds):
        return thresholds[idx]
    return None


# ── Get or create achievement record ──────────────────────────


def _get_or_create(db: Session, user_id: UUID, achievement_type: str) -> MasterAchievement:
    """Get or create an achievement record."""
    ach = db.query(MasterAchievement).filter(
        MasterAchievement.user_id == user_id,
        MasterAchievement.achievement_type == achievement_type,
    ).first()
    if not ach:
        next_target = _get_next_threshold(achievement_type, 0)
        ach = MasterAchievement(
            user_id=user_id,
            achievement_type=achievement_type,
            level=0,
            progress_current=0,
            progress_target=next_target or 100,
        )
        db.add(ach)
        db.flush()
    return ach


def _check_level_up(
    db: Session,
    ach: MasterAchievement,
    current_progress: int,
) -> bool:
    """Update progress and check for level up. Returns True if leveled up."""
    ach.progress_current = current_progress
    ach.updated_at = datetime.now(timezone.utc)

    old_level = ach.level
    thresholds = ACHIEVEMENT_TYPES[ach.achievement_type]["thresholds"]

    # Determine new level
    new_level = 0
    for i, threshold in enumerate(thresholds):
        if current_progress >= threshold:
            new_level = i + 1
        else:
            break

    new_level = min(new_level, 5)

    if new_level > old_level:
        ach.level = new_level
        ach.unlocked_at = datetime.now(timezone.utc)
        # Set next target
        next_t = _get_next_threshold(ach.achievement_type, new_level)
        if next_t:
            ach.progress_target = next_t
        else:
            ach.progress_target = thresholds[-1]  # Max

        # Send Telegram notification
        _notify_achievement(db, ach)
        return True

    # Update target for current level progress
    next_t = _get_next_threshold(ach.achievement_type, ach.level)
    if next_t:
        ach.progress_target = next_t

    return False


def _notify_achievement(db: Session, ach: MasterAchievement):
    """Send Telegram notification for achievement unlock."""
    user = db.query(User).filter(User.id == ach.user_id).first()
    if not user or not user.telegram_user_id:
        return

    cfg = ACHIEVEMENT_TYPES.get(ach.achievement_type, {})
    label = cfg.get("label", ach.achievement_type)
    icon = cfg.get("icon", "\U0001F3C6")
    level_name = get_level_name(ach.level)

    text = (
        f"\U0001F3C6 Achievement Unlocked: {label} {level_name} (Level {ach.level})!\n"
        f"{icon} {ach.progress_current} total. Keep going!"
    )
    try:
        send_telegram_message(str(user.telegram_user_id), text)
    except Exception as e:
        logger.warning("Achievement notification failed for user %s: %s", user.id, e)

    # Also send to forum #achievements topic
    try:
        forum_group, achievements_topic = get_forum_topic("achievements")
        if forum_group:
            forum_text = (
                f"\U0001F3C6 *{user.full_name}* unlocked: {label} {level_name} (Level {ach.level})!\n"
                f"{icon} {ach.progress_current} total."
            )
            send_telegram_message(
                str(forum_group), forum_text,
                message_thread_id=achievements_topic,
            )
    except Exception as e:
        logger.warning("Achievement forum notification failed: %s", e)


# ── Progress measurement functions ─────────────────────────────


def _measure_glazing_master(db: Session, user_id: UUID) -> int:
    """Count positions glazed by this user via operation logs.

    Uses OperationLog entries where the user worked on glazing-related operations.
    Falls back to quantity_processed sum if available.
    """
    # Count distinct positions from operation logs for this user
    count = db.query(sa_func.count(sa_func.distinct(OperationLog.position_id))).filter(
        OperationLog.user_id == user_id,
        OperationLog.position_id.isnot(None),
    ).scalar() or 0
    return count


def _measure_zero_defect_hero(db: Session, user_id: UUID) -> int:
    """Count consecutive zero-defect days for user's factory.

    Uses the user's primary factory and counts backwards from today.
    """
    uf = db.query(UserFactory).filter(UserFactory.user_id == user_id).first()
    if not uf:
        return 0

    today = date.today()
    consecutive = 0

    for i in range(365):  # max 1 year lookback
        day = today - timedelta(days=i)
        defect_count = db.query(sa_func.count(DefectRecord.id)).filter(
            DefectRecord.factory_id == uf.factory_id,
            DefectRecord.date == day,
        ).scalar() or 0

        if defect_count == 0:
            consecutive += 1
        else:
            break

    return consecutive


def _measure_speed_champion(db: Session, user_id: UUID) -> int:
    """Count consecutive days where user's positions had below-avg cycle time.

    Simplified: count days where at least 1 position was completed faster
    than the rolling factory average.
    """
    uf = db.query(UserFactory).filter(UserFactory.user_id == user_id).first()
    if not uf:
        return 0

    # Get factory avg cycle time (last 30 days)
    today = date.today()
    d_from = today - timedelta(days=30)

    shipped_positions = db.query(OrderPosition).filter(
        OrderPosition.factory_id == uf.factory_id,
        OrderPosition.status == PositionStatus.SHIPPED.value,
        cast(OrderPosition.updated_at, Date) >= d_from,
    ).all()

    if not shipped_positions:
        return 0

    # Avg cycle = avg days from created to shipped
    cycles = []
    for p in shipped_positions:
        if p.created_at and p.updated_at:
            delta = (p.updated_at.date() if hasattr(p.updated_at, 'date') else p.updated_at) - (
                p.created_at.date() if hasattr(p.created_at, 'date') else p.created_at
            )
            if delta.days > 0:
                cycles.append(delta.days)

    if not cycles:
        return 0

    factory_avg = sum(cycles) / len(cycles)

    # Count consecutive days where user's positions were faster
    consecutive = 0
    for i in range(90):
        day = today - timedelta(days=i)
        # Get position IDs the user worked on that day via operation logs
        user_position_ids = [
            r[0] for r in db.query(OperationLog.position_id).filter(
                OperationLog.user_id == user_id,
                OperationLog.shift_date == day,
                OperationLog.position_id.isnot(None),
            ).distinct().all()
        ]
        if not user_position_ids:
            if i == 0:
                continue
            break

        user_positions = db.query(OrderPosition).filter(
            OrderPosition.id.in_(user_position_ids),
            OrderPosition.status == PositionStatus.SHIPPED.value,
        ).all()

        if not user_positions:
            if i == 0:
                continue  # Skip today if no data
            break

        user_cycles = []
        for p in user_positions:
            if p.created_at and p.updated_at:
                delta = (p.updated_at.date() if hasattr(p.updated_at, 'date') else p.updated_at) - (
                    p.created_at.date() if hasattr(p.created_at, 'date') else p.created_at
                )
                if delta.days > 0:
                    user_cycles.append(delta.days)

        if user_cycles and (sum(user_cycles) / len(user_cycles)) < factory_avg:
            consecutive += 1
        else:
            break

    return consecutive


def _measure_kiln_expert(db: Session, user_id: UUID) -> int:
    """Count firings managed by this user via operation logs with batch_id."""
    count = db.query(sa_func.count(sa_func.distinct(OperationLog.batch_id))).filter(
        OperationLog.user_id == user_id,
        OperationLog.batch_id.isnot(None),
    ).scalar() or 0
    return count


def _measure_quality_star(db: Session, user_id: UUID) -> int:
    """Count QC checks passed by this user."""
    count = db.query(sa_func.count(QualityCheck.id)).filter(
        QualityCheck.checked_by == user_id,
        QualityCheck.result == QcResult.OK.value,
    ).scalar() or 0
    return count


# ── Main update function ──────────────────────────────────────

def _measure_skill_collector(db: Session, user_id: UUID) -> int:
    """Count certified skills for this user."""
    from api.models import UserSkill
    count = db.query(sa_func.count(UserSkill.id)).filter(
        UserSkill.user_id == user_id,
        UserSkill.status == "certified",
    ).scalar() or 0
    return count


def _measure_competition_winner(db: Session, user_id: UUID) -> int:
    """Count competition wins (rank=1) for this user."""
    from api.models import CompetitionEntry
    count = db.query(sa_func.count(CompetitionEntry.id)).filter(
        CompetitionEntry.user_id == user_id,
        CompetitionEntry.rank == 1,
    ).scalar() or 0
    return count


MEASURERS = {
    "glazing_master": _measure_glazing_master,
    "zero_defect_hero": _measure_zero_defect_hero,
    "speed_champion": _measure_speed_champion,
    "kiln_expert": _measure_kiln_expert,
    "quality_star": _measure_quality_star,
    "skill_collector": _measure_skill_collector,
    "competition_winner": _measure_competition_winner,
}


def update_achievements_for_user(db: Session, user_id: UUID) -> list[dict]:
    """Update all achievements for a user. Returns list of newly unlocked ones."""
    newly_unlocked = []

    for atype, measurer in MEASURERS.items():
        try:
            ach = _get_or_create(db, user_id, atype)
            progress = measurer(db, user_id)
            leveled_up = _check_level_up(db, ach, progress)
            if leveled_up:
                newly_unlocked.append({
                    "type": atype,
                    "level": ach.level,
                    "level_name": get_level_name(ach.level),
                    "progress": progress,
                })
        except Exception as e:
            logger.warning("Achievement update failed for user %s type %s: %s", user_id, atype, e)

    return newly_unlocked


def get_user_achievements(db: Session, user_id: UUID) -> list[dict]:
    """Get all achievements for a user (with progress info)."""
    results = []

    for atype in ACHIEVEMENT_TYPES:
        ach = _get_or_create(db, user_id, atype)
        cfg = ACHIEVEMENT_TYPES[atype]
        next_target = _get_next_threshold(atype, ach.level)

        results.append({
            "id": str(ach.id),
            "achievement_type": atype,
            "label": cfg["label"],
            "icon": cfg["icon"],
            "level": ach.level,
            "level_name": get_level_name(ach.level),
            "unlocked_at": ach.unlocked_at.isoformat() if ach.unlocked_at else None,
            "progress_current": ach.progress_current,
            "progress_target": ach.progress_target,
            "next_target": next_target,
            "thresholds": cfg["thresholds"],
        })

    db.flush()
    return results
