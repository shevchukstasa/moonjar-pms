"""
CEO Reports — Gamification dashboard reports formatted for Telegram.

Weekly reports, productivity impact analysis, encouragement tracking.
All user-facing text in Russian.
"""

import logging
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func as sa_func, cast, Date
from sqlalchemy.orm import Session

from api.models import (
    PrizeRecommendation, UserPoints, PointTransaction,
    OperationLog, UserSkill, SkillBadge, Competition,
    CompetitionEntry, GamificationSeason, User, UserFactory, Factory,
)
from api.enums import UserRole

logger = logging.getLogger("moonjar.ceo_reports")

# ── Medals for leaderboard ─────────────────────────────────────
_RANK_MEDALS = {1: "\U0001F947", 2: "\U0001F948", 3: "\U0001F949"}  # gold, silver, bronze


# ── Weekly gamification report ─────────────────────────────────


def generate_weekly_gamification_report(db: Session, factory_id: UUID) -> str:
    """
    Еженедельный отчёт по геймификации — форматирован для Telegram (MarkdownV2-safe).

    Секции:
      1. PAPAN PERINGKAT (Leaderboard) — top-5 с дельтой
      2. KOMPETISI AKTIF — текущие соревнования с лидерами
      3. SERTIFIKASI BARU — новые сертификации за неделю
      4. PERLU PERHATIAN — работники со снижением 3+ недели
      5. REKOMENDASI HADIAH — pending prize recommendations с ROI
    """
    factory = db.query(Factory).get(factory_id)
    factory_name = factory.name if factory else "Unknown"

    today = date.today()
    week_start = today - timedelta(days=7)
    week_end = today

    sections = []

    # Header
    header = (
        f"\U0001F4CA ОТЧЁТ ПО ГЕЙМИФИКАЦИИ — {factory_name}\n"
        f"Неделя: {week_start.strftime('%d/%m')} - {week_end.strftime('%d/%m/%Y')}"
    )
    sections.append(header)

    # 1. Leaderboard
    sections.append(_build_leaderboard_section(db, factory_id, week_start, week_end))

    # 2. Active competitions
    sections.append(_build_competitions_section(db, factory_id, today))

    # 3. New certifications
    sections.append(_build_certifications_section(db, factory_id, week_start, week_end))

    # 4. Workers needing attention
    sections.append(_build_attention_section(db, factory_id))

    # 5. Prize recommendations
    sections.append(_build_prizes_section(db, factory_id))

    return "\n\n".join(s for s in sections if s)


def _build_leaderboard_section(
    db: Session,
    factory_id: UUID,
    week_start: date,
    week_end: date,
) -> str:
    """Top-5 leaderboard with weekly point delta."""
    # Current week points
    current_rows = (
        db.query(
            PointTransaction.user_id,
            sa_func.sum(PointTransaction.points).label("week_pts"),
        )
        .filter(
            PointTransaction.factory_id == factory_id,
            cast(PointTransaction.created_at, Date) >= week_start,
            cast(PointTransaction.created_at, Date) <= week_end,
        )
        .group_by(PointTransaction.user_id)
        .order_by(sa_func.sum(PointTransaction.points).desc())
        .limit(5)
        .all()
    )

    if not current_rows:
        return "\U0001F3C6 ЛИДЕРБОРД\n  Нет данных за эту неделю."

    # Previous week for delta
    prev_start = week_start - timedelta(days=7)
    prev_end = week_start - timedelta(days=1)
    prev_map = _get_points_map(db, factory_id, prev_start, prev_end)

    lines = ["\U0001F3C6 ЛИДЕРБОРД"]
    for i, row in enumerate(current_rows, 1):
        user = db.query(User).get(row.user_id)
        name = user.name if user else "?"
        pts = int(row.week_pts)
        prev_pts = prev_map.get(row.user_id, 0)
        delta = pts - prev_pts

        medal = _RANK_MEDALS.get(i, f"{i}.")
        delta_str = f"+{delta}" if delta >= 0 else str(delta)
        lines.append(f"{medal} {name} — {pts} очк. ({delta_str})")

    return "\n".join(lines)


def _build_competitions_section(
    db: Session,
    factory_id: UUID,
    today: date,
) -> str:
    """Active competitions with current leaders."""
    active = (
        db.query(Competition)
        .filter(
            Competition.factory_id == factory_id,
            Competition.status == "active",
            Competition.start_date <= today,
            Competition.end_date >= today,
        )
        .all()
    )

    if not active:
        return "\u2694\uFE0F АКТИВНЫЕ СОРЕВНОВАНИЯ\n  Нет активных соревнований."

    lines = ["\u2694\uFE0F АКТИВНЫЕ СОРЕВНОВАНИЯ"]
    for comp in active:
        days_left = (comp.end_date - today).days
        title = comp.title_id or comp.title
        lines.append(f'"{title}" (осталось {days_left} дн.)')

        # Get leader
        leader_entry = (
            db.query(CompetitionEntry)
            .filter(
                CompetitionEntry.competition_id == comp.id,
                CompetitionEntry.user_id.isnot(None),
            )
            .order_by(CompetitionEntry.combined_score.desc())
            .first()
        )
        if leader_entry and leader_entry.user_id:
            user = db.query(User).get(leader_entry.user_id)
            leader_name = user.name if user else "?"
            lines.append(
                f"  Лидер: {leader_name} "
                f"({float(leader_entry.throughput_score):.1f} м\u00B2, "
                f"качество {float(leader_entry.quality_score):.0f}%)"
            )

    return "\n".join(lines)


def _build_certifications_section(
    db: Session,
    factory_id: UUID,
    week_start: date,
    week_end: date,
) -> str:
    """New skill certifications this week."""
    certs = (
        db.query(UserSkill, SkillBadge, User)
        .join(SkillBadge, SkillBadge.id == UserSkill.skill_badge_id)
        .join(User, User.id == UserSkill.user_id)
        .filter(
            SkillBadge.factory_id == factory_id,
            UserSkill.status == "certified",
            UserSkill.certified_at >= datetime.combine(week_start, datetime.min.time()).replace(tzinfo=timezone.utc),
            UserSkill.certified_at <= datetime.combine(week_end, datetime.max.time()).replace(tzinfo=timezone.utc),
        )
        .all()
    )

    if not certs:
        return "\U0001F393 НОВЫЕ СЕРТИФИКАЦИИ\n  Нет новых сертификаций за эту неделю."

    lines = ["\U0001F393 НОВЫЕ СЕРТИФИКАЦИИ"]
    for skill, badge, user in certs:
        badge_name = badge.name_id or badge.name
        lines.append(f"  {user.name}: {badge_name} \u2705")

    return "\n".join(lines)


def _build_attention_section(db: Session, factory_id: UUID) -> str:
    """Workers with 3+ week declining performance."""
    declining = get_who_needs_encouragement(db, factory_id)

    if not declining:
        return "\u26A0\uFE0F ТРЕБУЮТ ВНИМАНИЯ\n  Все работники стабильны. \U0001F44D"

    lines = ["\u26A0\uFE0F ТРЕБУЮТ ВНИМАНИЯ"]
    for w in declining:
        lines.append(
            f"  {w['name']} — снижение баллов {w['decline_weeks']} нед. "
            f"({w['decline_pct']:+.0f}%)"
        )

    return "\n".join(lines)


def _build_prizes_section(db: Session, factory_id: UUID) -> str:
    """Pending prize recommendations with costs and ROI."""
    from business.services.prize_advisor import get_pending_prizes

    pending = get_pending_prizes(db, factory_id)
    if not pending:
        return "\U0001F381 РЕКОМЕНДАЦИИ ПО ПРИЗАМ\n  Нет новых рекомендаций."

    lines = ["\U0001F381 РЕКОМЕНДАЦИИ ПО ПРИЗАМ"]
    total_cost = 0
    total_gain = 0

    for p in pending:
        cost = p["estimated_cost_idr"]
        roi = p.get("roi_estimate") or 0
        cost_str = _format_idr(cost)
        recipient = p["recipient_name"]

        # Map prize_type to short label
        type_labels = {
            "individual_mvp": "MVP",
            "most_improved": "Прогресс",
            "team_winner": "Команда",
            "skill_champion": "Сертификация",
            "zero_defect": "Ноль дефектов",
        }
        label = type_labels.get(p["prize_type"], p["prize_type"])
        lines.append(f"  {label}: {recipient} — {cost_str} (ROI: {roi:.1f}\u00D7)")

        total_cost += cost
        if roi > 0:
            total_gain += cost * roi

    lines.append(f"  Итого: {_format_idr(total_cost)} | Ожид. выгода: {_format_idr(total_gain)}")
    return "\n".join(lines)


# ── Productivity impact ────────────────────────────────────────


def generate_productivity_impact(
    db: Session,
    factory_id: UUID,
    days: int = 30,
) -> dict:
    """
    Before/after gamification metrics.

    Compares last `days` period with the `days` period before that.
    Returns: throughput_change, quality_change, on_time_change (all in %).
    """
    today = date.today()
    current_start = today - timedelta(days=days)
    current_end = today
    prev_start = current_start - timedelta(days=days)
    prev_end = current_start - timedelta(days=1)

    current = _period_metrics(db, factory_id, current_start, current_end)
    previous = _period_metrics(db, factory_id, prev_start, prev_end)

    def _delta(curr_val, prev_val):
        if prev_val and prev_val > 0:
            return round((curr_val - prev_val) / prev_val * 100, 1)
        return 0.0

    return {
        "period_days": days,
        "current_period": f"{current_start} — {current_end}",
        "previous_period": f"{prev_start} — {prev_end}",
        "throughput": {
            "current": current["throughput"],
            "previous": previous["throughput"],
            "change_pct": _delta(current["throughput"], previous["throughput"]),
        },
        "quality": {
            "current": current["quality_pct"],
            "previous": previous["quality_pct"],
            "change_pct": round(current["quality_pct"] - previous["quality_pct"], 1),
        },
        "active_workers": {
            "current": current["active_workers"],
            "previous": previous["active_workers"],
        },
        "avg_points_per_worker": {
            "current": current["avg_points"],
            "previous": previous["avg_points"],
            "change_pct": _delta(current["avg_points"], previous["avg_points"]),
        },
    }


def _period_metrics(
    db: Session,
    factory_id: UUID,
    date_from: date,
    date_to: date,
) -> dict:
    """Базовые метрики за период."""
    throughput = db.query(
        sa_func.coalesce(sa_func.sum(OperationLog.quantity_processed), 0)
    ).filter(
        OperationLog.factory_id == factory_id,
        OperationLog.shift_date >= date_from,
        OperationLog.shift_date <= date_to,
    ).scalar() or 0

    defects = db.query(
        sa_func.coalesce(sa_func.sum(OperationLog.defect_count), 0)
    ).filter(
        OperationLog.factory_id == factory_id,
        OperationLog.shift_date >= date_from,
        OperationLog.shift_date <= date_to,
    ).scalar() or 0

    quality_pct = round((1 - defects / throughput) * 100, 1) if throughput > 0 else 100.0

    active_workers = db.query(
        sa_func.count(sa_func.distinct(OperationLog.user_id))
    ).filter(
        OperationLog.factory_id == factory_id,
        OperationLog.shift_date >= date_from,
        OperationLog.shift_date <= date_to,
    ).scalar() or 0

    total_points = db.query(
        sa_func.coalesce(sa_func.sum(PointTransaction.points), 0)
    ).filter(
        PointTransaction.factory_id == factory_id,
        cast(PointTransaction.created_at, Date) >= date_from,
        cast(PointTransaction.created_at, Date) <= date_to,
    ).scalar() or 0

    avg_points = round(total_points / active_workers, 1) if active_workers > 0 else 0.0

    return {
        "throughput": int(throughput),
        "quality_pct": quality_pct,
        "active_workers": int(active_workers),
        "avg_points": avg_points,
    }


# ── Weekly report sender ───────────────────────────────────────


def send_weekly_report_all_factories(db: Session) -> None:
    """
    Отправляет еженедельный отчёт всем CEO/Owner.
    Вызывается по cron: Sunday 20:00 WITA.
    """
    from business.services.notifications import create_notification

    factories = db.query(Factory).filter(Factory.is_active.is_(True)).all()

    for factory in factories:
        try:
            report_text = generate_weekly_gamification_report(db, factory.id)

            # Find CEO/Owner users linked to this factory
            ceo_users = (
                db.query(User)
                .join(UserFactory, UserFactory.user_id == User.id)
                .filter(
                    UserFactory.factory_id == factory.id,
                    User.role.in_([UserRole.CEO, UserRole.OWNER]),
                    User.is_active.is_(True),
                )
                .all()
            )

            for user in ceo_users:
                create_notification(
                    db=db,
                    user_id=user.id,
                    type="gamification_weekly_report",
                    title=f"Отчёт по геймификации — {factory.name}",
                    message=report_text,
                    factory_id=factory.id,
                )

            logger.info(
                "Weekly gamification report sent for factory %s to %d users",
                factory.name, len(ceo_users),
            )
        except Exception as e:
            logger.error(
                "Failed to send weekly report for factory %s: %s",
                factory.id, e, exc_info=True,
            )


# ── Who needs encouragement ───────────────────────────────────


def get_who_needs_encouragement(db: Session, factory_id: UUID) -> list[dict]:
    """
    Работники со снижением очков 3+ недели подряд или сломанными стриками.

    Returns list of dicts: name, user_id, decline_weeks, decline_pct, last_week_points.
    """
    today = date.today()
    results = []

    # Get all factory workers
    workers = (
        db.query(User)
        .join(UserFactory, UserFactory.user_id == User.id)
        .filter(
            UserFactory.factory_id == factory_id,
            User.is_active.is_(True),
            User.role.in_([
                UserRole.MASTER, UserRole.SENIOR_MASTER,
                UserRole.SORTER_PACKER, UserRole.WAREHOUSE,
            ]),
        )
        .all()
    )

    for worker in workers:
        # Get last 4 weeks of points
        weekly_points = []
        for w in range(4):
            w_end = today - timedelta(days=w * 7)
            w_start = w_end - timedelta(days=6)
            pts = db.query(
                sa_func.coalesce(sa_func.sum(PointTransaction.points), 0)
            ).filter(
                PointTransaction.user_id == worker.id,
                PointTransaction.factory_id == factory_id,
                cast(PointTransaction.created_at, Date) >= w_start,
                cast(PointTransaction.created_at, Date) <= w_end,
            ).scalar() or 0
            weekly_points.append(int(pts))

        # weekly_points[0] = most recent week, [3] = 4 weeks ago
        # Check for 3+ consecutive declining weeks
        decline_weeks = 0
        for i in range(len(weekly_points) - 1):
            if weekly_points[i] < weekly_points[i + 1]:
                decline_weeks += 1
            else:
                break

        if decline_weeks >= 3:
            # Calculate total decline percentage
            oldest_pts = weekly_points[decline_weeks] if decline_weeks < len(weekly_points) else weekly_points[-1]
            newest_pts = weekly_points[0]
            decline_pct = (
                (newest_pts - oldest_pts) / oldest_pts * 100
                if oldest_pts > 0 else -100.0
            )

            results.append({
                "user_id": str(worker.id),
                "name": worker.name,
                "decline_weeks": decline_weeks,
                "decline_pct": decline_pct,
                "last_week_points": weekly_points[0],
                "weekly_trend": weekly_points,
            })

    # Sort by severity (most decline first)
    results.sort(key=lambda x: x["decline_pct"])
    return results


# ── CEO Dashboard JSON data ───────────────────────────────────


def get_ceo_dashboard_data(db: Session, factory_id: UUID) -> dict:
    """
    JSON для API endpoint — все KPI геймификации.

    Sections:
      leaderboard, active_competitions, recent_certifications,
      needs_attention, pending_prizes, productivity_impact, season_info.
    """
    today = date.today()
    week_start = today - timedelta(days=7)
    week_end = today

    # Leaderboard: top 10 this week
    leaderboard_rows = (
        db.query(
            PointTransaction.user_id,
            sa_func.sum(PointTransaction.points).label("week_pts"),
        )
        .filter(
            PointTransaction.factory_id == factory_id,
            cast(PointTransaction.created_at, Date) >= week_start,
            cast(PointTransaction.created_at, Date) <= week_end,
        )
        .group_by(PointTransaction.user_id)
        .order_by(sa_func.sum(PointTransaction.points).desc())
        .limit(10)
        .all()
    )

    prev_map = _get_points_map(db, factory_id, week_start - timedelta(days=7), week_start - timedelta(days=1))

    leaderboard = []
    for i, row in enumerate(leaderboard_rows, 1):
        user = db.query(User).get(row.user_id)
        pts = int(row.week_pts)
        prev_pts = prev_map.get(row.user_id, 0)
        leaderboard.append({
            "rank": i,
            "user_id": str(row.user_id),
            "name": user.name if user else "?",
            "points": pts,
            "delta": pts - prev_pts,
        })

    # Active competitions
    active_comps = (
        db.query(Competition)
        .filter(
            Competition.factory_id == factory_id,
            Competition.status == "active",
            Competition.start_date <= today,
            Competition.end_date >= today,
        )
        .all()
    )
    competitions = []
    for comp in active_comps:
        days_left = (comp.end_date - today).days
        leader = (
            db.query(CompetitionEntry)
            .filter(
                CompetitionEntry.competition_id == comp.id,
                CompetitionEntry.user_id.isnot(None),
            )
            .order_by(CompetitionEntry.combined_score.desc())
            .first()
        )
        leader_name = None
        if leader and leader.user_id:
            u = db.query(User).get(leader.user_id)
            leader_name = u.name if u else None

        competitions.append({
            "id": str(comp.id),
            "title": comp.title_id or comp.title,
            "days_left": days_left,
            "leader_name": leader_name,
            "leader_score": float(leader.combined_score) if leader else 0,
            "entries_count": (
                db.query(sa_func.count(CompetitionEntry.id))
                .filter(CompetitionEntry.competition_id == comp.id)
                .scalar() or 0
            ),
        })

    # Recent certifications (last 7 days)
    certs = (
        db.query(UserSkill, SkillBadge, User)
        .join(SkillBadge, SkillBadge.id == UserSkill.skill_badge_id)
        .join(User, User.id == UserSkill.user_id)
        .filter(
            SkillBadge.factory_id == factory_id,
            UserSkill.status == "certified",
            UserSkill.certified_at >= datetime.combine(week_start, datetime.min.time()).replace(tzinfo=timezone.utc),
        )
        .all()
    )
    certifications = [
        {
            "user_name": user.name,
            "skill_name": badge.name_id or badge.name,
            "certified_at": skill.certified_at.isoformat() if skill.certified_at else None,
        }
        for skill, badge, user in certs
    ]

    # Needs attention
    needs_attention = get_who_needs_encouragement(db, factory_id)

    # Pending prizes
    from business.services.prize_advisor import get_pending_prizes
    pending_prizes = get_pending_prizes(db, factory_id)

    # Productivity impact (30 days)
    impact = generate_productivity_impact(db, factory_id, days=30)

    # Current season
    season = (
        db.query(GamificationSeason)
        .filter(
            GamificationSeason.factory_id == factory_id,
            GamificationSeason.status == "active",
        )
        .first()
    )
    season_info = None
    if season:
        season_info = {
            "name": season.name,
            "start_date": season.start_date.isoformat(),
            "end_date": season.end_date.isoformat(),
            "days_remaining": (season.end_date - today).days,
        }

    # Summary stats
    total_points_this_week = sum(r.week_pts for r in leaderboard_rows) if leaderboard_rows else 0
    total_workers = len(leaderboard_rows)

    return {
        "factory_id": str(factory_id),
        "factory_name": (db.query(Factory).get(factory_id) or Factory()).name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_points_this_week": int(total_points_this_week),
            "active_workers": total_workers,
            "active_competitions": len(competitions),
            "pending_prizes": len(pending_prizes),
            "workers_needing_attention": len(needs_attention),
        },
        "leaderboard": leaderboard,
        "competitions": competitions,
        "certifications": certifications,
        "needs_attention": needs_attention,
        "pending_prizes": pending_prizes,
        "productivity_impact": impact,
        "season": season_info,
    }


# ── Helpers ────────────────────────────────────────────────────


def _get_points_map(
    db: Session,
    factory_id: UUID,
    date_from: date,
    date_to: date,
) -> dict:
    """User ID -> total points for a date range."""
    rows = (
        db.query(
            PointTransaction.user_id,
            sa_func.sum(PointTransaction.points).label("total"),
        )
        .filter(
            PointTransaction.factory_id == factory_id,
            cast(PointTransaction.created_at, Date) >= date_from,
            cast(PointTransaction.created_at, Date) <= date_to,
        )
        .group_by(PointTransaction.user_id)
        .all()
    )
    return {r.user_id: int(r.total) for r in rows}


def _format_idr(amount: float) -> str:
    """Format IDR amount: 300000 -> 'Rp 300rb', 1500000 -> 'Rp 1.5jt'."""
    if amount >= 1_000_000:
        val = amount / 1_000_000
        if val == int(val):
            return f"Rp {int(val)}jt"
        return f"Rp {val:.1f}jt"
    elif amount >= 1_000:
        val = amount / 1_000
        if val == int(val):
            return f"Rp {int(val)}rb"
        return f"Rp {val:.0f}rb"
    return f"Rp {int(amount)}"
