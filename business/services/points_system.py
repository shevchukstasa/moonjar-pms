"""
Points System — gamified recipe verification scoring.

Accuracy thresholds:
  +/- 1%  = 10 pts (perfect!)
  +/- 3%  = 7 pts
  +/- 5%  = 5 pts
  +/- 10% = 3 pts
  > 10%   = 1 pt (participation)

Bonus sources:
  streak_bonus         = +5 pts/day
  challenge_complete   = +20 pts
  achievement_unlock   = +50 pts
  skill_certification  = +100 pts (per skill badge earned)
  competition_win_1st  = +50 pts
  competition_win_2nd  = +30 pts
  competition_win_3rd  = +20 pts
  team_win_bonus       = +30 pts (all team members)
  speed_bonus_glazing  = +3/5/10 pts (20%/50%/100%+ above avg)
  speed_bonus_firing   = +3/5/10 pts
  speed_bonus_sorting  = +3/5/10 pts
"""

import logging
from datetime import datetime, date, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import func, extract
from sqlalchemy.orm import Session

from api.models import (
    UserPoints, PointTransaction, RecipeVerification,
    User, UserFactory,
)

logger = logging.getLogger("moonjar.points_system")

# ── Accuracy scoring table ──────────────────────────────────────

ACCURACY_POINTS = {
    1: 10,    # +/- 1% -> 10 points (perfect!)
    3: 7,     # +/- 3% -> 7 points
    5: 5,     # +/- 5% -> 5 points
    10: 3,    # +/- 10% -> 3 points
    100: 1,   # > 10% -> 1 point (participation)
}


def calculate_accuracy_points(target_g: float, actual_g: float) -> tuple[int, float]:
    """Calculate points based on weighing accuracy.

    Returns (points, deviation_pct).
    """
    if target_g <= 0:
        return 1, 0.0
    deviation_pct = abs(actual_g - target_g) / target_g * 100
    for threshold, pts in sorted(ACCURACY_POINTS.items()):
        if deviation_pct <= threshold:
            return pts, round(deviation_pct, 2)
    return 1, round(deviation_pct, 2)


def accuracy_emoji(points: int) -> str:
    """Emoji indicator based on points awarded."""
    if points >= 10:
        return "\U0001F3AF"  # direct hit
    elif points >= 7:
        return "\U0001F44D"  # thumbs up
    elif points >= 5:
        return "\U0001F44C"  # ok hand
    elif points >= 3:
        return "\U0001F914"  # thinking
    else:
        return "\U0001F4AA"  # flex (participation)


# ── Point operations ────────────────────────────────────────────


def award_points(
    db: Session,
    user_id: UUID,
    factory_id: UUID,
    points: int,
    reason: str,
    details: dict | None = None,
    position_id: UUID | None = None,
) -> PointTransaction:
    """Award points: create transaction + update totals (upsert)."""
    now = datetime.now(timezone.utc)
    current_year = now.year

    # 1. Create transaction record
    txn = PointTransaction(
        user_id=user_id,
        factory_id=factory_id,
        points=points,
        reason=reason,
        details=details,
        position_id=position_id,
    )
    db.add(txn)

    # 2. Upsert UserPoints for current year
    user_pts = db.query(UserPoints).filter(
        UserPoints.user_id == user_id,
        UserPoints.factory_id == factory_id,
        UserPoints.year == current_year,
    ).first()

    if not user_pts:
        user_pts = UserPoints(
            user_id=user_id,
            factory_id=factory_id,
            year=current_year,
            points_total=0,
            points_this_month=0,
            points_this_week=0,
        )
        db.add(user_pts)
        db.flush()

    user_pts.points_total += points
    user_pts.points_this_month += points
    user_pts.points_this_week += points
    user_pts.updated_at = now

    db.flush()
    logger.info(
        "Points awarded: user=%s, factory=%s, +%d pts (%s), total=%d",
        user_id, factory_id, points, reason, user_pts.points_total,
    )
    return txn


def get_user_points(db: Session, user_id: UUID, factory_id: UUID) -> dict:
    """Get user's point summary for current year."""
    current_year = datetime.now(timezone.utc).year
    user_pts = db.query(UserPoints).filter(
        UserPoints.user_id == user_id,
        UserPoints.factory_id == factory_id,
        UserPoints.year == current_year,
    ).first()

    if not user_pts:
        return {
            "points_total": 0,
            "points_this_month": 0,
            "points_this_week": 0,
            "year": current_year,
        }

    return {
        "points_total": user_pts.points_total,
        "points_this_month": user_pts.points_this_month,
        "points_this_week": user_pts.points_this_week,
        "year": user_pts.year,
    }


def get_recent_transactions(
    db: Session, user_id: UUID, factory_id: UUID, limit: int = 5
) -> list[dict]:
    """Get recent point transactions for a user."""
    txns = (
        db.query(PointTransaction)
        .filter(
            PointTransaction.user_id == user_id,
            PointTransaction.factory_id == factory_id,
        )
        .order_by(PointTransaction.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "points": t.points,
            "reason": t.reason,
            "details": t.details,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in txns
    ]


def get_points_leaderboard(
    db: Session, factory_id: UUID, period: str = "year"
) -> list[dict]:
    """Top performers by points.

    period: 'year', 'month', 'week'
    """
    current_year = datetime.now(timezone.utc).year

    if period == "month":
        order_col = UserPoints.points_this_month
    elif period == "week":
        order_col = UserPoints.points_this_week
    else:
        order_col = UserPoints.points_total

    rows = (
        db.query(UserPoints, User.name)
        .join(User, User.id == UserPoints.user_id)
        .filter(
            UserPoints.factory_id == factory_id,
            UserPoints.year == current_year,
        )
        .order_by(order_col.desc())
        .limit(20)
        .all()
    )

    result = []
    for pts, user_name in rows:
        if period == "month":
            score = pts.points_this_month
        elif period == "week":
            score = pts.points_this_week
        else:
            score = pts.points_total
        if score > 0:
            result.append({
                "user_id": str(pts.user_id),
                "name": user_name,
                "points": score,
            })
    return result


def get_user_rank(db: Session, user_id: UUID, factory_id: UUID) -> tuple[int, int]:
    """Get user's rank and total participants.

    Returns (rank, total). Rank is 1-based; 0 means not ranked.
    """
    current_year = datetime.now(timezone.utc).year
    all_pts = (
        db.query(UserPoints.user_id, UserPoints.points_total)
        .filter(
            UserPoints.factory_id == factory_id,
            UserPoints.year == current_year,
            UserPoints.points_total > 0,
        )
        .order_by(UserPoints.points_total.desc())
        .all()
    )

    total = len(all_pts)
    rank = 0
    for i, (uid, _) in enumerate(all_pts, 1):
        if uid == user_id:
            rank = i
            break
    return rank, total


# ── Weekly / Monthly resets ─────────────────────────────────────


def reset_weekly_points(db: Session) -> int:
    """Reset points_this_week for all users. Returns count updated."""
    current_year = datetime.now(timezone.utc).year
    count = (
        db.query(UserPoints)
        .filter(
            UserPoints.year == current_year,
            UserPoints.points_this_week > 0,
        )
        .update({"points_this_week": 0, "updated_at": datetime.now(timezone.utc)})
    )
    logger.info("Weekly points reset: %d records", count)
    return count


def reset_monthly_points(db: Session) -> int:
    """Reset points_this_month for all users. Returns count updated."""
    current_year = datetime.now(timezone.utc).year
    count = (
        db.query(UserPoints)
        .filter(
            UserPoints.year == current_year,
            UserPoints.points_this_month > 0,
        )
        .update({"points_this_month": 0, "updated_at": datetime.now(timezone.utc)})
    )
    logger.info("Monthly points reset: %d records", count)
    return count
