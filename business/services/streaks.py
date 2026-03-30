"""
Streak tracking + daily challenge generation for PM gamification.

Streak types:
- on_time_delivery: consecutive days where all shipped orders met deadline
- zero_defects: consecutive days with 0 defect records
- daily_login: consecutive days user logged in (via session/audit)
- batch_utilization: consecutive days with avg kiln utilization >= 80%

Daily challenges: deterministic per factory+date using hash.
"""

import hashlib
import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, and_, cast, Date
from sqlalchemy.orm import Session

from api.models import (
    UserStreak, DailyChallenge, ProductionOrder, DefectRecord,
    Batch, QualityCheck, Shipment, ShipmentItem,
    User, UserFactory, Factory, OrderPosition, ActiveSession,
)
from api.enums import (
    OrderStatus, QcResult, BatchStatus, UserRole, PositionStatus,
)

logger = logging.getLogger("moonjar.streaks")

# ── Streak types ────────────────────────────────────────────────

STREAK_TYPES = ["on_time_delivery", "zero_defects", "daily_login", "batch_utilization"]


def _get_or_create_streak(db: Session, user_id, factory_id, streak_type) -> UserStreak:
    """Get or create a streak record."""
    streak = db.query(UserStreak).filter(
        UserStreak.user_id == user_id,
        UserStreak.factory_id == factory_id,
        UserStreak.streak_type == streak_type,
    ).first()
    if not streak:
        streak = UserStreak(
            user_id=user_id,
            factory_id=factory_id,
            streak_type=streak_type,
            current_streak=0,
            best_streak=0,
        )
        db.add(streak)
        db.flush()
    return streak


def _increment_streak(streak: UserStreak, today: date):
    """Increment streak if last activity was yesterday or today, else reset to 1."""
    if streak.last_activity_date == today:
        return  # Already counted today
    if streak.last_activity_date == today - timedelta(days=1):
        streak.current_streak += 1
    else:
        streak.current_streak = 1
    streak.last_activity_date = today
    if streak.current_streak > streak.best_streak:
        streak.best_streak = streak.current_streak
    streak.updated_at = datetime.now(timezone.utc)


def _reset_streak(streak: UserStreak, today: date):
    """Reset streak to 0 (condition not met today)."""
    if streak.last_activity_date and streak.last_activity_date < today - timedelta(days=1):
        # Already broken — was not yesterday
        streak.current_streak = 0
    elif streak.last_activity_date == today - timedelta(days=1):
        # Today is the break day
        streak.current_streak = 0
    streak.updated_at = datetime.now(timezone.utc)


# ── Check functions (return bool: did the factory meet the condition today?) ─


def check_on_time_delivery(db: Session, factory_id, today: date) -> bool:
    """True if all orders shipped today had shipped_at <= final_deadline (or no shipments = vacuous true)."""
    shipped_today = db.query(ProductionOrder).filter(
        ProductionOrder.factory_id == factory_id,
        ProductionOrder.status == OrderStatus.SHIPPED.value,
        cast(ProductionOrder.shipped_at, Date) == today,
    ).all()
    if not shipped_today:
        return True  # No shipments today — streak continues
    for order in shipped_today:
        if order.final_deadline and order.shipped_at:
            if order.shipped_at.date() > order.final_deadline:
                return False
    return True


def check_zero_defects(db: Session, factory_id, today: date) -> bool:
    """True if no defect records logged today for this factory."""
    defect_count = db.query(func.count(DefectRecord.id)).filter(
        DefectRecord.factory_id == factory_id,
        DefectRecord.date == today,
    ).scalar()
    return defect_count == 0


def check_daily_login(db: Session, user_id, today: date) -> bool:
    """True if user had an active session today."""
    session_today = db.query(ActiveSession).filter(
        ActiveSession.user_id == user_id,
        cast(ActiveSession.last_activity, Date) == today,
    ).first()
    return session_today is not None


def check_batch_utilization(db: Session, factory_id, today: date) -> bool:
    """True if avg kiln utilization today >= 80% (batches done today with >= 80% fill)."""
    from business.services.daily_kpi import calculate_dashboard_summary
    try:
        summary = calculate_dashboard_summary(db, factory_id, today, today)
        util = summary.get("kiln_utilization", 0) if isinstance(summary, dict) else 0
        return util >= 80
    except Exception:
        return False  # Can't calculate — don't award


# ── Main daily job ──────────────────────────────────────────────


def update_streaks_for_factory(db: Session, factory_id, today: date):
    """Update all streak types for all PM users in a factory."""
    pm_users = db.query(User).join(UserFactory).filter(
        UserFactory.factory_id == factory_id,
        User.role.in_([UserRole.PRODUCTION_MANAGER.value, UserRole.ADMINISTRATOR.value, UserRole.OWNER.value]),
        User.is_active.is_(True),
    ).all()

    if not pm_users:
        return

    # Pre-check factory-level conditions
    on_time_ok = check_on_time_delivery(db, factory_id, today)
    zero_defects_ok = check_zero_defects(db, factory_id, today)
    batch_util_ok = check_batch_utilization(db, factory_id, today)

    for user in pm_users:
        # on_time_delivery
        streak = _get_or_create_streak(db, user.id, factory_id, "on_time_delivery")
        if on_time_ok:
            _increment_streak(streak, today)
        else:
            _reset_streak(streak, today)

        # zero_defects
        streak = _get_or_create_streak(db, user.id, factory_id, "zero_defects")
        if zero_defects_ok:
            _increment_streak(streak, today)
        else:
            _reset_streak(streak, today)

        # daily_login
        streak = _get_or_create_streak(db, user.id, factory_id, "daily_login")
        if check_daily_login(db, user.id, today):
            _increment_streak(streak, today)
        else:
            _reset_streak(streak, today)

        # batch_utilization
        streak = _get_or_create_streak(db, user.id, factory_id, "batch_utilization")
        if batch_util_ok:
            _increment_streak(streak, today)
        else:
            _reset_streak(streak, today)


# ── Daily challenge ─────────────────────────────────────────────

CHALLENGE_TEMPLATES = [
    {
        "type": "pre_kiln_checks",
        "title": "Complete 3 pre-kiln checks before 14:00",
        "description": "Run quality checks on 3 positions before they enter the kiln today.",
        "target": 3,
    },
    {
        "type": "kiln_utilization",
        "title": "Achieve 85%+ kiln utilization today",
        "description": "Fill kilns to at least 85% capacity across all firings today.",
        "target": 85,
    },
    {
        "type": "ship_orders",
        "title": "Ship 2 orders today",
        "description": "Complete and ship at least 2 production orders today.",
        "target": 2,
    },
    {
        "type": "zero_defects",
        "title": "Zero defects in QC today",
        "description": "Achieve a perfect quality day with no defect records.",
        "target": 0,
    },
    {
        "type": "batch_completion",
        "title": "Complete 2 kiln batches today",
        "description": "Finish firing and unload at least 2 batches today.",
        "target": 2,
    },
    {
        "type": "position_progress",
        "title": "Move 10 positions forward today",
        "description": "Advance at least 10 positions to their next production stage.",
        "target": 10,
    },
    {
        "type": "all_checks_pass",
        "title": "100% QC pass rate today",
        "description": "Every quality check performed today should pass.",
        "target": 100,
    },
]


def get_daily_challenge(db: Session, factory_id, today: date) -> dict:
    """Get or create today's challenge for a factory. Deterministic from date hash."""
    existing = db.query(DailyChallenge).filter(
        DailyChallenge.factory_id == factory_id,
        DailyChallenge.challenge_date == today,
    ).first()
    if existing:
        return _challenge_to_dict(existing)

    # Deterministic selection: hash(factory_id + date) mod len(templates)
    seed = hashlib.sha256(f"{factory_id}:{today.isoformat()}".encode()).hexdigest()
    idx = int(seed, 16) % len(CHALLENGE_TEMPLATES)
    template = CHALLENGE_TEMPLATES[idx]

    challenge = DailyChallenge(
        factory_id=factory_id,
        challenge_date=today,
        challenge_type=template["type"],
        title=template["title"],
        description=template["description"],
        target_value=template["target"],
    )
    db.add(challenge)
    db.flush()
    return _challenge_to_dict(challenge)


def evaluate_challenge(db: Session, factory_id, today: date):
    """Evaluate today's challenge completion based on actual data."""
    challenge = db.query(DailyChallenge).filter(
        DailyChallenge.factory_id == factory_id,
        DailyChallenge.challenge_date == today,
    ).first()
    if not challenge or challenge.completed:
        return

    actual = _measure_challenge(db, factory_id, today, challenge.challenge_type, challenge.target_value)
    challenge.actual_value = actual

    if challenge.challenge_type == "zero_defects":
        challenge.completed = actual == 0
    elif challenge.challenge_type == "kiln_utilization":
        challenge.completed = actual >= challenge.target_value
    elif challenge.challenge_type == "all_checks_pass":
        challenge.completed = actual >= 100
    else:
        challenge.completed = actual >= challenge.target_value


def _measure_challenge(db: Session, factory_id, today: date, ctype: str, target: int) -> int:
    """Measure actual progress for a challenge type."""
    if ctype == "pre_kiln_checks":
        from api.models import QualityChecklist
        count = db.query(func.count(QualityChecklist.id)).filter(
            QualityChecklist.factory_id == factory_id,
            QualityChecklist.check_type == 'pre_kiln',
            cast(QualityChecklist.created_at, Date) == today,
        ).scalar() or 0
        return count

    elif ctype == "kiln_utilization":
        from business.services.daily_kpi import calculate_dashboard_summary
        try:
            summary = calculate_dashboard_summary(db, factory_id, today, today)
            return int(summary.get("kiln_utilization", 0)) if isinstance(summary, dict) else 0
        except Exception:
            return 0

    elif ctype == "ship_orders":
        count = db.query(func.count(ProductionOrder.id)).filter(
            ProductionOrder.factory_id == factory_id,
            ProductionOrder.status == OrderStatus.SHIPPED.value,
            cast(ProductionOrder.shipped_at, Date) == today,
        ).scalar() or 0
        return count

    elif ctype == "zero_defects":
        count = db.query(func.count(DefectRecord.id)).filter(
            DefectRecord.factory_id == factory_id,
            DefectRecord.date == today,
        ).scalar() or 0
        return count

    elif ctype == "batch_completion":
        count = db.query(func.count(Batch.id)).filter(
            Batch.factory_id == factory_id,
            Batch.status == BatchStatus.DONE.value,
            cast(Batch.updated_at, Date) == today,
        ).scalar() or 0
        return count

    elif ctype == "position_progress":
        # Count positions that changed status today (approximation via updated_at)
        count = db.query(func.count(OrderPosition.id)).filter(
            OrderPosition.factory_id == factory_id,
            cast(OrderPosition.updated_at, Date) == today,
            OrderPosition.status != PositionStatus.PLANNED.value,
        ).scalar() or 0
        return count

    elif ctype == "all_checks_pass":
        total = db.query(func.count(QualityCheck.id)).filter(
            QualityCheck.factory_id == factory_id,
            cast(QualityCheck.created_at, Date) == today,
        ).scalar() or 0
        if total == 0:
            return 0  # No checks = not met
        passed = db.query(func.count(QualityCheck.id)).filter(
            QualityCheck.factory_id == factory_id,
            cast(QualityCheck.created_at, Date) == today,
            QualityCheck.result == QcResult.OK.value,
        ).scalar() or 0
        return int((passed / total) * 100) if total > 0 else 0

    return 0


def _challenge_to_dict(c: DailyChallenge) -> dict:
    return {
        "type": c.challenge_type,
        "title": c.title,
        "description": c.description,
        "target_value": c.target_value,
        "actual_value": c.actual_value,
        "completed": c.completed,
        "date": c.challenge_date.isoformat() if c.challenge_date else None,
    }


def get_user_streaks(db: Session, user_id, factory_id) -> list[dict]:
    """Get all streaks for a user+factory."""
    streaks = db.query(UserStreak).filter(
        UserStreak.user_id == user_id,
        UserStreak.factory_id == factory_id,
    ).all()

    # Ensure all streak types exist
    existing_types = {s.streak_type for s in streaks}
    for stype in STREAK_TYPES:
        if stype not in existing_types:
            s = _get_or_create_streak(db, user_id, factory_id, stype)
            streaks.append(s)
    db.flush()

    return [
        {
            "type": s.streak_type,
            "current": s.current_streak,
            "best": s.best_streak,
            "last_date": s.last_activity_date.isoformat() if s.last_activity_date else None,
        }
        for s in streaks
    ]
