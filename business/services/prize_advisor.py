"""
Prize Advisor — AI Prize Recommendation Engine.

Анализирует данные продуктивности работников и предлагает призы с ROI.
Использует rule-based логику (не LLM) — быстро, надёжно, предсказуемо.

Prize types:
  individual_mvp  — MVP месяца, Rp 300k Gopay
  most_improved   — Самый прогрессирующий, Rp 200k
  team_winner     — Лучшая секция, Rp 500k командный обед
  skill_champion  — Больше всего сертификаций, Rp 150k
  zero_defect     — Самая длинная серия без дефектов, Rp 100k
"""

import logging
from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import func as sa_func, and_, extract
from sqlalchemy.orm import Session

from api.models import (
    PrizeRecommendation, UserPoints, PointTransaction,
    OperationLog, UserSkill, SkillBadge, Competition,
    CompetitionEntry, GamificationSeason, User, UserFactory, Factory,
)
from api.enums import UserRole

logger = logging.getLogger("moonjar.prize_advisor")

# ── Бюджеты призов (IDR) ──────────────────────────────────────

MONTHLY_PRIZES = {
    "individual_mvp": {
        "title": "MVP Bulan Ini",
        "description": "Pekerja dengan poin tertinggi bulan ini. Hadiah: Gopay Rp 300.000",
        "cost": Decimal("300000"),
    },
    "most_improved": {
        "title": "Paling Berkembang",
        "description": "Peningkatan poin terbesar dibandingkan bulan sebelumnya. Hadiah: Gopay Rp 200.000",
        "cost": Decimal("200000"),
    },
    "team_winner": {
        "title": "Tim Terbaik",
        "description": "Seksi dengan performa terbaik. Hadiah: Makan bersama Rp 500.000",
        "cost": Decimal("500000"),
    },
    "skill_champion": {
        "title": "Juara Sertifikasi",
        "description": "Paling banyak sertifikasi bulan ini. Hadiah: Gopay Rp 150.000",
        "cost": Decimal("150000"),
    },
    "zero_defect": {
        "title": "Zero Defect Champion",
        "description": "Streak tanpa cacat terpanjang. Hadiah: Gopay Rp 100.000",
        "cost": Decimal("100000"),
    },
}

QUARTERLY_MULTIPLIER = Decimal("2.5")  # Quarterly prizes 2.5x monthly


# ── Main generation functions ──────────────────────────────────


def generate_monthly_prizes(
    db: Session,
    factory_id: UUID,
    year: int,
    month: int,
) -> list[PrizeRecommendation]:
    """
    Анализирует данные за месяц и создаёт PrizeRecommendation записи.

    Returns: список созданных рекомендаций.
    """
    _, last_day = monthrange(year, month)
    date_from = date(year, month, 1)
    date_to = date(year, month, last_day)
    period_label = f"{year}-{month:02d}"

    # Удалить старые suggested-рекомендации за этот период (перегенерация)
    db.query(PrizeRecommendation).filter(
        PrizeRecommendation.factory_id == factory_id,
        PrizeRecommendation.period == "monthly",
        PrizeRecommendation.period_label == period_label,
        PrizeRecommendation.status == "suggested",
    ).delete(synchronize_session="fetch")

    productivity = _analyze_productivity(db, factory_id, date_from, date_to)
    recommendations = []

    # 1. Individual MVP — top points earner
    mvp = _find_mvp(db, factory_id, year, month)
    if mvp:
        prize = _create_prize(
            db, factory_id, "monthly", period_label, "individual_mvp",
            recipient_user_id=mvp["user_id"],
            productivity_gain_pct=productivity.get("throughput_delta_pct"),
            reasoning=f"Poin tertinggi: {mvp['points']} pts. "
                      f"Throughput delta: {productivity.get('throughput_delta_pct', 0):.1f}%",
        )
        recommendations.append(prize)

    # 2. Most improved — biggest delta vs previous month
    improved = _find_most_improved(db, factory_id, year, month)
    if improved:
        prize = _create_prize(
            db, factory_id, "monthly", period_label, "most_improved",
            recipient_user_id=improved["user_id"],
            productivity_gain_pct=Decimal(str(improved["improvement_pct"])),
            reasoning=f"Peningkatan: +{improved['improvement_pct']:.0f}% poin "
                      f"({improved['prev_points']} → {improved['curr_points']})",
        )
        recommendations.append(prize)

    # 3. Team winner — best performing section (by average points)
    team = _find_best_team(db, factory_id, date_from, date_to)
    if team:
        prize = _create_prize(
            db, factory_id, "monthly", period_label, "team_winner",
            recipient_team_name=team["team_name"],
            productivity_gain_pct=productivity.get("throughput_delta_pct"),
            reasoning=f"Seksi terbaik: {team['team_name']}. "
                      f"Rata-rata poin: {team['avg_points']:.0f}. "
                      f"Kualitas: {team.get('quality_avg', 0):.1f}%",
        )
        recommendations.append(prize)

    # 4. Skill champion — most certifications this month
    skill_champ = _find_skill_champion(db, factory_id, date_from, date_to)
    if skill_champ:
        prize = _create_prize(
            db, factory_id, "monthly", period_label, "skill_champion",
            recipient_user_id=skill_champ["user_id"],
            reasoning=f"Sertifikasi baru: {skill_champ['cert_count']} skill "
                      f"({', '.join(skill_champ['skill_names'])})",
        )
        recommendations.append(prize)

    # 5. Zero defect champion — longest streak
    zd_champ = _find_zero_defect_champion(db, factory_id, date_from, date_to)
    if zd_champ:
        prize = _create_prize(
            db, factory_id, "monthly", period_label, "zero_defect",
            recipient_user_id=zd_champ["user_id"],
            reasoning=f"Streak tanpa cacat: {zd_champ['streak_days']} hari berturut-turut",
        )
        recommendations.append(prize)

    db.commit()
    logger.info(
        "Generated %d monthly prize recommendations for factory %s, period %s",
        len(recommendations), factory_id, period_label,
    )
    return recommendations


def generate_quarterly_prizes(
    db: Session,
    factory_id: UUID,
    year: int,
    quarter: int,
) -> list[PrizeRecommendation]:
    """
    Квартальные призы — бюджет 2.5x от месячных.
    Quarter: 1=Jan-Mar, 2=Apr-Jun, 3=Jul-Sep, 4=Oct-Dec.
    """
    start_month = (quarter - 1) * 3 + 1
    end_month = start_month + 2
    date_from = date(year, start_month, 1)
    _, last_day = monthrange(year, end_month)
    date_to = date(year, end_month, last_day)
    period_label = f"{year}-Q{quarter}"

    # Удалить старые suggested за этот квартал
    db.query(PrizeRecommendation).filter(
        PrizeRecommendation.factory_id == factory_id,
        PrizeRecommendation.period == "quarterly",
        PrizeRecommendation.period_label == period_label,
        PrizeRecommendation.status == "suggested",
    ).delete(synchronize_session="fetch")

    productivity = _analyze_productivity(db, factory_id, date_from, date_to)
    recommendations = []

    # Quarterly MVP
    mvp = _find_mvp_range(db, factory_id, date_from, date_to)
    if mvp:
        prize = _create_prize(
            db, factory_id, "quarterly", period_label, "individual_mvp",
            recipient_user_id=mvp["user_id"],
            productivity_gain_pct=productivity.get("throughput_delta_pct"),
            cost_multiplier=QUARTERLY_MULTIPLIER,
            reasoning=f"MVP Kuartal: {mvp['points']} pts total. "
                      f"Throughput delta: {productivity.get('throughput_delta_pct', 0):.1f}%",
        )
        recommendations.append(prize)

    # Quarterly Most Improved
    improved = _find_most_improved_range(db, factory_id, date_from, date_to)
    if improved:
        prize = _create_prize(
            db, factory_id, "quarterly", period_label, "most_improved",
            recipient_user_id=improved["user_id"],
            productivity_gain_pct=Decimal(str(improved["improvement_pct"])),
            cost_multiplier=QUARTERLY_MULTIPLIER,
            reasoning=f"Peningkatan kuartal: +{improved['improvement_pct']:.0f}%",
        )
        recommendations.append(prize)

    # Quarterly Team Winner
    team = _find_best_team(db, factory_id, date_from, date_to)
    if team:
        prize = _create_prize(
            db, factory_id, "quarterly", period_label, "team_winner",
            recipient_team_name=team["team_name"],
            productivity_gain_pct=productivity.get("throughput_delta_pct"),
            cost_multiplier=QUARTERLY_MULTIPLIER,
            reasoning=f"Tim terbaik kuartal: {team['team_name']}. "
                      f"Rata-rata: {team['avg_points']:.0f} pts",
        )
        recommendations.append(prize)

    db.commit()
    logger.info(
        "Generated %d quarterly prize recommendations for factory %s, %s",
        len(recommendations), factory_id, period_label,
    )
    return recommendations


# ── Productivity analysis ──────────────────────────────────────


def _analyze_productivity(
    db: Session,
    factory_id: UUID,
    date_from: date,
    date_to: date,
) -> dict:
    """
    Метрики продуктивности за период.

    Returns dict with:
      throughput_total, quality_avg, throughput_delta_pct,
      top_performers (list of dicts).
    """
    period_days = (date_to - date_from).days + 1

    # Current period throughput
    current_throughput = db.query(
        sa_func.coalesce(sa_func.sum(OperationLog.quantity_processed), 0)
    ).filter(
        OperationLog.factory_id == factory_id,
        OperationLog.shift_date >= date_from,
        OperationLog.shift_date <= date_to,
    ).scalar() or 0

    # Current period quality (avg defect rate → quality%)
    total_ops = db.query(
        sa_func.coalesce(sa_func.sum(OperationLog.quantity_processed), 0)
    ).filter(
        OperationLog.factory_id == factory_id,
        OperationLog.shift_date >= date_from,
        OperationLog.shift_date <= date_to,
    ).scalar() or 0

    total_defects = db.query(
        sa_func.coalesce(sa_func.sum(OperationLog.defect_count), 0)
    ).filter(
        OperationLog.factory_id == factory_id,
        OperationLog.shift_date >= date_from,
        OperationLog.shift_date <= date_to,
    ).scalar() or 0

    quality_avg = (
        round((1 - total_defects / total_ops) * 100, 1)
        if total_ops > 0 else 100.0
    )

    # Previous period (same length) for delta
    prev_from = date_from - timedelta(days=period_days)
    prev_to = date_from - timedelta(days=1)

    prev_throughput = db.query(
        sa_func.coalesce(sa_func.sum(OperationLog.quantity_processed), 0)
    ).filter(
        OperationLog.factory_id == factory_id,
        OperationLog.shift_date >= prev_from,
        OperationLog.shift_date <= prev_to,
    ).scalar() or 0

    throughput_delta_pct = (
        round((current_throughput - prev_throughput) / prev_throughput * 100, 1)
        if prev_throughput > 0 else 0.0
    )

    # Top 5 performers by points in period
    top_rows = (
        db.query(
            PointTransaction.user_id,
            sa_func.sum(PointTransaction.points).label("total_pts"),
        )
        .filter(
            PointTransaction.factory_id == factory_id,
            sa_func.cast(PointTransaction.created_at, sa_func.date()) >= date_from,  # type: ignore[attr-defined]
            sa_func.cast(PointTransaction.created_at, sa_func.date()) <= date_to,
        )
        .group_by(PointTransaction.user_id)
        .order_by(sa_func.sum(PointTransaction.points).desc())
        .limit(5)
        .all()
    )

    top_performers = []
    for row in top_rows:
        user = db.query(User).get(row.user_id)
        top_performers.append({
            "user_id": str(row.user_id),
            "name": user.name if user else "Unknown",
            "points": int(row.total_pts),
        })

    return {
        "throughput_total": int(current_throughput),
        "quality_avg": quality_avg,
        "throughput_delta_pct": Decimal(str(throughput_delta_pct)),
        "top_performers": top_performers,
    }


def _calculate_roi(
    productivity_gain_pct: float,
    prize_cost_idr: Decimal,
    monthly_revenue_estimate: int = 50_000_000,
) -> float:
    """
    Простой ROI multiplier.

    ROI = (revenue_gain - prize_cost) / prize_cost
    Где revenue_gain = monthly_revenue * productivity_gain_pct / 100
    """
    if prize_cost_idr <= 0:
        return 0.0
    revenue_gain = monthly_revenue_estimate * float(productivity_gain_pct) / 100
    roi = (revenue_gain - float(prize_cost_idr)) / float(prize_cost_idr)
    return round(max(roi, 0.0), 2)


# ── Prize CRUD ─────────────────────────────────────────────────


def approve_prize(db: Session, prize_id: UUID, approver_id: UUID) -> PrizeRecommendation:
    """CEO одобряет приз. Меняет статус на 'approved'."""
    prize = db.query(PrizeRecommendation).filter(
        PrizeRecommendation.id == prize_id,
    ).one_or_none()
    if not prize:
        raise ValueError(f"Prize {prize_id} tidak ditemukan")
    if prize.status != "suggested":
        raise ValueError(f"Prize status '{prize.status}' — hanya 'suggested' yang bisa disetujui")

    prize.status = "approved"
    prize.approved_by = approver_id
    prize.approved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(prize)

    logger.info("Prize %s approved by %s", prize_id, approver_id)
    return prize


def reject_prize(
    db: Session,
    prize_id: UUID,
    approver_id: UUID,
    reason: Optional[str] = None,
) -> PrizeRecommendation:
    """CEO отклоняет приз."""
    prize = db.query(PrizeRecommendation).filter(
        PrizeRecommendation.id == prize_id,
    ).one_or_none()
    if not prize:
        raise ValueError(f"Prize {prize_id} tidak ditemukan")
    if prize.status != "suggested":
        raise ValueError(f"Prize status '{prize.status}' — hanya 'suggested' yang bisa ditolak")

    prize.status = "rejected"
    prize.approved_by = approver_id
    prize.approved_at = datetime.now(timezone.utc)
    if reason:
        prize.ai_reasoning = f"{prize.ai_reasoning}\n\nDitolak: {reason}"
    db.commit()
    db.refresh(prize)

    logger.info("Prize %s rejected by %s: %s", prize_id, approver_id, reason or "no reason")
    return prize


def get_pending_prizes(db: Session, factory_id: UUID) -> list[dict]:
    """Все suggested-призы, ожидающие одобрения CEO."""
    prizes = (
        db.query(PrizeRecommendation)
        .filter(
            PrizeRecommendation.factory_id == factory_id,
            PrizeRecommendation.status == "suggested",
        )
        .order_by(PrizeRecommendation.created_at.desc())
        .all()
    )
    result = []
    for p in prizes:
        recipient_name = None
        if p.recipient_user_id:
            user = db.query(User).get(p.recipient_user_id)
            recipient_name = user.name if user else None

        result.append({
            "id": str(p.id),
            "period": p.period,
            "period_label": p.period_label,
            "prize_type": p.prize_type,
            "prize_title": p.prize_title,
            "prize_description": p.prize_description,
            "recipient_name": recipient_name or p.recipient_team_name or "—",
            "estimated_cost_idr": float(p.estimated_cost_idr),
            "productivity_gain_pct": float(p.productivity_gain_pct) if p.productivity_gain_pct else None,
            "roi_estimate": float(p.roi_estimate) if p.roi_estimate else None,
            "ai_reasoning": p.ai_reasoning,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        })
    return result


def award_prize(db: Session, prize_id: UUID) -> PrizeRecommendation:
    """Отмечает приз как фактически выданный."""
    prize = db.query(PrizeRecommendation).filter(
        PrizeRecommendation.id == prize_id,
    ).one_or_none()
    if not prize:
        raise ValueError(f"Prize {prize_id} tidak ditemukan")
    if prize.status != "approved":
        raise ValueError(f"Prize status '{prize.status}' — hanya 'approved' yang bisa dibagikan")

    prize.status = "awarded"
    db.commit()
    db.refresh(prize)

    logger.info("Prize %s marked as awarded", prize_id)
    return prize


# ── Internal helpers ───────────────────────────────────────────


def _create_prize(
    db: Session,
    factory_id: UUID,
    period: str,
    period_label: str,
    prize_type: str,
    recipient_user_id: Optional[UUID] = None,
    recipient_team_name: Optional[str] = None,
    productivity_gain_pct: Optional[Decimal] = None,
    cost_multiplier: Decimal = Decimal("1"),
    reasoning: str = "",
) -> PrizeRecommendation:
    """Создаёт PrizeRecommendation с расчётом ROI."""
    config = MONTHLY_PRIZES.get(prize_type, MONTHLY_PRIZES["individual_mvp"])
    cost = config["cost"] * cost_multiplier

    gain_pct = float(productivity_gain_pct) if productivity_gain_pct else 0.0
    roi = _calculate_roi(gain_pct, cost)

    prize = PrizeRecommendation(
        factory_id=factory_id,
        period=period,
        period_label=period_label,
        prize_type=prize_type,
        recipient_user_id=recipient_user_id,
        recipient_team_name=recipient_team_name,
        prize_title=config["title"],
        prize_description=config["description"],
        estimated_cost_idr=cost,
        productivity_gain_pct=productivity_gain_pct,
        roi_estimate=Decimal(str(roi)),
        ai_reasoning=reasoning,
        status="suggested",
    )
    db.add(prize)
    return prize


def _find_mvp(
    db: Session,
    factory_id: UUID,
    year: int,
    month: int,
) -> Optional[dict]:
    """Находит работника с максимальным количеством очков за месяц."""
    row = (
        db.query(
            UserPoints.user_id,
            UserPoints.points_this_month,
        )
        .filter(
            UserPoints.factory_id == factory_id,
            UserPoints.year == year,
            UserPoints.points_this_month > 0,
        )
        .order_by(UserPoints.points_this_month.desc())
        .first()
    )
    if not row:
        return None
    return {"user_id": row.user_id, "points": row.points_this_month}


def _find_mvp_range(
    db: Session,
    factory_id: UUID,
    date_from: date,
    date_to: date,
) -> Optional[dict]:
    """MVP по сумме транзакций за произвольный диапазон дат."""
    row = (
        db.query(
            PointTransaction.user_id,
            sa_func.sum(PointTransaction.points).label("total"),
        )
        .filter(
            PointTransaction.factory_id == factory_id,
            sa_func.cast(PointTransaction.created_at, sa_func.date()) >= date_from,
            sa_func.cast(PointTransaction.created_at, sa_func.date()) <= date_to,
        )
        .group_by(PointTransaction.user_id)
        .order_by(sa_func.sum(PointTransaction.points).desc())
        .first()
    )
    if not row or (row.total or 0) <= 0:
        return None
    return {"user_id": row.user_id, "points": int(row.total)}


def _find_most_improved(
    db: Session,
    factory_id: UUID,
    year: int,
    month: int,
) -> Optional[dict]:
    """
    Работник с наибольшим ростом очков по сравнению с предыдущим месяцем.
    """
    # Current month points
    current_rows = (
        db.query(UserPoints.user_id, UserPoints.points_this_month)
        .filter(
            UserPoints.factory_id == factory_id,
            UserPoints.year == year,
            UserPoints.points_this_month > 0,
        )
        .all()
    )
    if not current_rows:
        return None

    # Previous month — get from transactions
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1

    _, prev_last_day = monthrange(prev_year, prev_month)
    prev_from = date(prev_year, prev_month, 1)
    prev_to = date(prev_year, prev_month, prev_last_day)

    prev_points = {}
    prev_rows = (
        db.query(
            PointTransaction.user_id,
            sa_func.sum(PointTransaction.points).label("total"),
        )
        .filter(
            PointTransaction.factory_id == factory_id,
            sa_func.cast(PointTransaction.created_at, sa_func.date()) >= prev_from,
            sa_func.cast(PointTransaction.created_at, sa_func.date()) <= prev_to,
        )
        .group_by(PointTransaction.user_id)
        .all()
    )
    for r in prev_rows:
        prev_points[r.user_id] = int(r.total)

    best = None
    for row in current_rows:
        prev = prev_points.get(row.user_id, 0)
        curr = row.points_this_month
        if prev > 0:
            improvement = (curr - prev) / prev * 100
        elif curr > 0:
            improvement = 100.0  # from zero to something
        else:
            continue

        if best is None or improvement > best["improvement_pct"]:
            best = {
                "user_id": row.user_id,
                "curr_points": curr,
                "prev_points": prev,
                "improvement_pct": improvement,
            }

    return best


def _find_most_improved_range(
    db: Session,
    factory_id: UUID,
    date_from: date,
    date_to: date,
) -> Optional[dict]:
    """Most improved за произвольный период vs предыдущий период той же длины."""
    period_days = (date_to - date_from).days + 1
    prev_from = date_from - timedelta(days=period_days)
    prev_to = date_from - timedelta(days=1)

    def _points_by_user(d_from, d_to):
        rows = (
            db.query(
                PointTransaction.user_id,
                sa_func.sum(PointTransaction.points).label("total"),
            )
            .filter(
                PointTransaction.factory_id == factory_id,
                sa_func.cast(PointTransaction.created_at, sa_func.date()) >= d_from,
                sa_func.cast(PointTransaction.created_at, sa_func.date()) <= d_to,
            )
            .group_by(PointTransaction.user_id)
            .all()
        )
        return {r.user_id: int(r.total) for r in rows}

    curr_map = _points_by_user(date_from, date_to)
    prev_map = _points_by_user(prev_from, prev_to)

    best = None
    for uid, curr in curr_map.items():
        prev = prev_map.get(uid, 0)
        if prev > 0:
            improvement = (curr - prev) / prev * 100
        elif curr > 0:
            improvement = 100.0
        else:
            continue
        if best is None or improvement > best["improvement_pct"]:
            best = {
                "user_id": uid,
                "curr_points": curr,
                "prev_points": prev,
                "improvement_pct": improvement,
            }
    return best


def _find_best_team(
    db: Session,
    factory_id: UUID,
    date_from: date,
    date_to: date,
) -> Optional[dict]:
    """
    Лучшая «команда» = группа по операции (секция).
    Средние очки на человека + средняя качество.
    """
    # Group operation logs by operation_id (=section), calc avg throughput & defect rate
    section_stats = (
        db.query(
            OperationLog.operation_id,
            sa_func.count(sa_func.distinct(OperationLog.user_id)).label("workers"),
            sa_func.sum(OperationLog.quantity_processed).label("throughput"),
            sa_func.sum(OperationLog.defect_count).label("defects"),
        )
        .filter(
            OperationLog.factory_id == factory_id,
            OperationLog.shift_date >= date_from,
            OperationLog.shift_date <= date_to,
        )
        .group_by(OperationLog.operation_id)
        .all()
    )

    if not section_stats:
        return None

    # Also get point averages by section users
    best_section = None
    best_score = -1

    for s in section_stats:
        if not s.operation_id or (s.throughput or 0) == 0:
            continue

        workers = s.workers or 1
        throughput = int(s.throughput or 0)
        defects = int(s.defects or 0)
        quality = round((1 - defects / throughput) * 100, 1) if throughput > 0 else 100.0

        # Get avg points for workers in this section
        section_users = (
            db.query(sa_func.distinct(OperationLog.user_id))
            .filter(
                OperationLog.factory_id == factory_id,
                OperationLog.operation_id == s.operation_id,
                OperationLog.shift_date >= date_from,
                OperationLog.shift_date <= date_to,
            )
            .all()
        )
        user_ids = [r[0] for r in section_users]

        avg_pts = 0
        if user_ids:
            pts_sum = (
                db.query(sa_func.coalesce(sa_func.sum(PointTransaction.points), 0))
                .filter(
                    PointTransaction.factory_id == factory_id,
                    PointTransaction.user_id.in_(user_ids),
                    sa_func.cast(PointTransaction.created_at, sa_func.date()) >= date_from,
                    sa_func.cast(PointTransaction.created_at, sa_func.date()) <= date_to,
                )
                .scalar() or 0
            )
            avg_pts = pts_sum / len(user_ids)

        # Combined score: 60% points + 40% quality
        score = avg_pts * 0.6 + quality * 0.4

        if score > best_score:
            best_score = score
            # Get operation name for team label
            from api.models import Operation
            op = db.query(Operation).get(s.operation_id)
            best_section = {
                "operation_id": str(s.operation_id),
                "team_name": op.name if op else f"Seksi #{str(s.operation_id)[:8]}",
                "avg_points": avg_pts,
                "quality_avg": quality,
                "workers": workers,
            }

    return best_section


def _find_skill_champion(
    db: Session,
    factory_id: UUID,
    date_from: date,
    date_to: date,
) -> Optional[dict]:
    """Работник с наибольшим количеством новых сертификаций за период."""
    rows = (
        db.query(
            UserSkill.user_id,
            sa_func.count(UserSkill.id).label("cert_count"),
            sa_func.array_agg(SkillBadge.name).label("skill_names"),
        )
        .join(SkillBadge, SkillBadge.id == UserSkill.skill_badge_id)
        .filter(
            SkillBadge.factory_id == factory_id,
            UserSkill.status == "certified",
            UserSkill.certified_at >= datetime.combine(date_from, datetime.min.time()).replace(tzinfo=timezone.utc),
            UserSkill.certified_at <= datetime.combine(date_to, datetime.max.time()).replace(tzinfo=timezone.utc),
        )
        .group_by(UserSkill.user_id)
        .order_by(sa_func.count(UserSkill.id).desc())
        .first()
    )

    if not rows or rows.cert_count == 0:
        return None

    return {
        "user_id": rows.user_id,
        "cert_count": rows.cert_count,
        "skill_names": rows.skill_names or [],
    }


def _find_zero_defect_champion(
    db: Session,
    factory_id: UUID,
    date_from: date,
    date_to: date,
) -> Optional[dict]:
    """
    Работник с самой длинной серией дней без дефектов.
    Считаем по shift_date: если defect_count=0 за все ops в день — день засчитан.
    """
    # Get all users who worked in this period
    user_days = (
        db.query(
            OperationLog.user_id,
            OperationLog.shift_date,
            sa_func.sum(OperationLog.defect_count).label("day_defects"),
        )
        .filter(
            OperationLog.factory_id == factory_id,
            OperationLog.shift_date >= date_from,
            OperationLog.shift_date <= date_to,
        )
        .group_by(OperationLog.user_id, OperationLog.shift_date)
        .order_by(OperationLog.user_id, OperationLog.shift_date)
        .all()
    )

    if not user_days:
        return None

    # Calculate longest streak per user
    best_user = None
    best_streak = 0

    current_user = None
    current_streak = 0
    last_date = None

    for row in user_days:
        if row.user_id != current_user:
            # Save previous user's streak
            if current_streak > best_streak and current_user is not None:
                best_streak = current_streak
                best_user = current_user
            current_user = row.user_id
            current_streak = 0
            last_date = None

        if (row.day_defects or 0) == 0:
            if last_date and (row.shift_date - last_date).days == 1:
                current_streak += 1
            else:
                current_streak = 1
            last_date = row.shift_date
        else:
            if current_streak > best_streak:
                best_streak = current_streak
                best_user = current_user
            current_streak = 0
            last_date = None

    # Check last user
    if current_streak > best_streak and current_user is not None:
        best_streak = current_streak
        best_user = current_user

    if best_user is None or best_streak < 2:
        return None

    return {
        "user_id": best_user,
        "streak_days": best_streak,
    }
