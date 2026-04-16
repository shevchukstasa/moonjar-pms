"""
Mini-Competitions Engine -- speed + quality gamification for factory workers.

Scoring formula:
  throughput_score = SUM(quantity_processed)          from OperationLog
  quality_score    = (1 - SUM(defects)/SUM(qty))*100  from OperationLog
  combined_score   = throughput * (quality_pct/100) ^ quality_weight

Prize distribution on finalize:
  1st = 50 pts, 2nd = 30 pts, 3rd = 20 pts, participation = 10 pts
"""

import logging
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from api.models import (
    Competition,
    CompetitionEntry,
    CompetitionTeam,
    GamificationSeason,
    OperationLog,
    User,
)
from business.services.points_system import award_points

logger = logging.getLogger("moonjar.competitions")

# ── Prize tiers ───────────────────────────────────────────────────

PRIZE_POINTS = {1: 50, 2: 30, 3: 20}
PARTICIPATION_POINTS = 10

# Indonesian month names for auto-generated titles
_BULAN_ID = {
    1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
    5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
    9: "September", 10: "Oktober", 11: "November", 12: "Desember",
}


# ── 1. create_competition ─────────────────────────────────────────

def create_competition(
    db: Session,
    factory_id: UUID,
    title: str,
    competition_type: str,
    metric: str,
    start_date: date,
    end_date: date,
    quality_weight: float = 1.0,
    title_id: str | None = None,
    prize_description: str | None = None,
    prize_budget_idr: float | None = None,
    created_by: UUID | None = None,
    proposed_by: UUID | None = None,
    season_tag: str | None = None,
    scoring_formula: str = "combined",
) -> Competition:
    """Create a single competition (individual or team)."""
    if end_date < start_date:
        raise ValueError("end_date must be >= start_date")
    if competition_type not in ("individual", "team"):
        raise ValueError("competition_type must be 'individual' or 'team'")

    status = "upcoming" if start_date > date.today() else "active"

    comp = Competition(
        factory_id=factory_id,
        title=title,
        title_id=title_id,
        competition_type=competition_type,
        metric=metric,
        scoring_formula=scoring_formula,
        quality_weight=Decimal(str(quality_weight)),
        start_date=start_date,
        end_date=end_date,
        status=status,
        season_tag=season_tag,
        prize_description=prize_description,
        prize_budget_idr=Decimal(str(prize_budget_idr)) if prize_budget_idr else None,
        created_by=created_by,
        proposed_by=proposed_by,
    )
    db.add(comp)
    db.flush()
    logger.info(
        "Competition created: %s [%s] factory=%s %s..%s",
        title, competition_type, factory_id, start_date, end_date,
    )
    return comp


# ── 2. create_team_competition ────────────────────────────────────

def create_team_competition(
    db: Session,
    factory_id: UUID,
    title: str,
    teams_config: list[dict],
    metric: str = "combined",
    start_date: date | None = None,
    end_date: date | None = None,
    quality_weight: float = 1.0,
    title_id: str | None = None,
    prize_description: str | None = None,
    prize_budget_idr: float | None = None,
    created_by: UUID | None = None,
) -> Competition:
    """Create a team competition with pre-defined teams.

    teams_config example:
        [{"name": "Tim Glazing", "type": "section",
          "filter_key": "glazing", "icon": "..."}]
    """
    if not teams_config:
        raise ValueError("teams_config must contain at least 2 teams")

    today = date.today()
    sd = start_date or today
    ed = end_date or (sd + timedelta(days=6))

    comp = create_competition(
        db, factory_id, title, "team", metric, sd, ed,
        quality_weight=quality_weight,
        title_id=title_id,
        prize_description=prize_description,
        prize_budget_idr=prize_budget_idr,
        created_by=created_by,
    )

    for tc in teams_config:
        team = CompetitionTeam(
            competition_id=comp.id,
            name=tc["name"],
            team_type=tc.get("type", "custom"),
            filter_key=tc.get("filter_key"),
            icon=tc.get("icon"),
        )
        db.add(team)

    db.flush()
    logger.info(
        "Team competition created: %s with %d teams", title, len(teams_config),
    )
    return comp


# ── 3. get_active_competitions ────────────────────────────────────

def get_active_competitions(db: Session, factory_id: UUID) -> list[dict]:
    """Return active + upcoming competitions with standings summary."""
    comps = (
        db.query(Competition)
        .filter(
            Competition.factory_id == factory_id,
            Competition.status.in_(["active", "upcoming"]),
        )
        .order_by(Competition.start_date)
        .all()
    )

    result = []
    for c in comps:
        top_entries = (
            db.query(CompetitionEntry)
            .filter(CompetitionEntry.competition_id == c.id)
            .order_by(CompetitionEntry.combined_score.desc())
            .limit(3)
            .all()
        )

        result.append({
            "id": str(c.id),
            "title": c.title,
            "title_id": c.title_id,
            "competition_type": c.competition_type,
            "metric": c.metric,
            "status": c.status,
            "start_date": c.start_date.isoformat(),
            "end_date": c.end_date.isoformat(),
            "quality_weight": float(c.quality_weight),
            "prize_description": c.prize_description,
            "prize_budget_idr": float(c.prize_budget_idr) if c.prize_budget_idr else None,
            "top_3": [_entry_to_dict(db, e) for e in top_entries],
            "participants_count": (
                db.query(sa_func.count(CompetitionEntry.id))
                .filter(CompetitionEntry.competition_id == c.id)
                .scalar()
            ),
        })

    return result


# ── 4. get_competition_standings ──────────────────────────────────

def get_competition_standings(db: Session, competition_id: UUID) -> list[dict]:
    """Full ranked standings for a competition."""
    entries = (
        db.query(CompetitionEntry)
        .filter(CompetitionEntry.competition_id == competition_id)
        .order_by(CompetitionEntry.combined_score.desc())
        .all()
    )

    standings = []
    for i, e in enumerate(entries, start=1):
        d = _entry_to_dict(db, e)
        d["rank"] = i
        standings.append(d)

    return standings


# ── 5. update_competition_scores ──────────────────────────────────

def update_competition_scores(db: Session, competition_id: UUID) -> None:
    """Recalculate all entries for a competition from OperationLog data."""
    comp = db.query(Competition).get(competition_id)
    if not comp:
        logger.warning("Competition %s not found", competition_id)
        return
    if comp.status not in ("active",):
        logger.debug("Skipping score update for %s (status=%s)", comp.title, comp.status)
        return

    qw = float(comp.quality_weight)

    if comp.competition_type == "individual":
        _update_individual_scores(db, comp, qw)
    else:
        _update_team_scores(db, comp, qw)

    # Assign ranks
    entries = (
        db.query(CompetitionEntry)
        .filter(CompetitionEntry.competition_id == comp.id)
        .order_by(CompetitionEntry.combined_score.desc())
        .all()
    )
    for i, entry in enumerate(entries, start=1):
        entry.rank = i

    db.flush()
    logger.info(
        "Scores updated for competition '%s': %d entries", comp.title, len(entries),
    )


def _update_individual_scores(
    db: Session, comp: Competition, qw: float,
) -> None:
    """Aggregate OperationLog per user for the competition date range."""
    aggregates = (
        db.query(
            OperationLog.user_id,
            sa_func.sum(OperationLog.quantity_processed).label("total_qty"),
            sa_func.sum(OperationLog.defect_count).label("total_defects"),
            sa_func.count(OperationLog.id).label("log_count"),
        )
        .filter(
            OperationLog.factory_id == comp.factory_id,
            OperationLog.shift_date >= comp.start_date,
            OperationLog.shift_date <= comp.end_date,
            OperationLog.quantity_processed > 0,
        )
        .group_by(OperationLog.user_id)
        .all()
    )

    for row in aggregates:
        throughput = float(row.total_qty or 0)
        defects = float(row.total_defects or 0)
        quality_pct = ((1 - defects / throughput) * 100) if throughput > 0 else 100.0
        quality_pct = max(quality_pct, 0.0)
        combined = _calc_combined(throughput, quality_pct, qw)

        entry = (
            db.query(CompetitionEntry)
            .filter(
                CompetitionEntry.competition_id == comp.id,
                CompetitionEntry.user_id == row.user_id,
            )
            .first()
        )
        if not entry:
            entry = CompetitionEntry(
                competition_id=comp.id,
                user_id=row.user_id,
            )
            db.add(entry)

        entry.throughput_score = Decimal(str(round(throughput, 2)))
        entry.quality_score = Decimal(str(round(quality_pct, 2)))
        entry.combined_score = Decimal(str(round(combined, 2)))
        entry.entries_count = int(row.log_count or 0)

    db.flush()


def _update_team_scores(
    db: Session, comp: Competition, qw: float,
) -> None:
    """Aggregate OperationLog per team (via filter_key on operation name)."""
    teams = (
        db.query(CompetitionTeam)
        .filter(CompetitionTeam.competition_id == comp.id)
        .all()
    )

    for team in teams:
        # Build filter: team.filter_key matches operation name pattern
        # Workers are grouped by their operation section matching filter_key
        log_query = (
            db.query(
                sa_func.sum(OperationLog.quantity_processed).label("total_qty"),
                sa_func.sum(OperationLog.defect_count).label("total_defects"),
                sa_func.count(OperationLog.id).label("log_count"),
            )
            .filter(
                OperationLog.factory_id == comp.factory_id,
                OperationLog.shift_date >= comp.start_date,
                OperationLog.shift_date <= comp.end_date,
                OperationLog.quantity_processed > 0,
            )
        )

        if team.filter_key:
            # Join operations to match by section/name
            from api.models import Operation
            log_query = log_query.join(
                Operation, Operation.id == OperationLog.operation_id,
            ).filter(
                sa_func.lower(Operation.name).contains(team.filter_key.lower()),
            )

        row = log_query.one()
        throughput = float(row.total_qty or 0)
        defects = float(row.total_defects or 0)
        quality_pct = ((1 - defects / throughput) * 100) if throughput > 0 else 100.0
        quality_pct = max(quality_pct, 0.0)
        combined = _calc_combined(throughput, quality_pct, qw)

        entry = (
            db.query(CompetitionEntry)
            .filter(
                CompetitionEntry.competition_id == comp.id,
                CompetitionEntry.team_id == team.id,
            )
            .first()
        )
        if not entry:
            entry = CompetitionEntry(
                competition_id=comp.id,
                team_id=team.id,
            )
            db.add(entry)

        entry.throughput_score = Decimal(str(round(throughput, 2)))
        entry.quality_score = Decimal(str(round(quality_pct, 2)))
        entry.combined_score = Decimal(str(round(combined, 2)))
        entry.entries_count = int(row.log_count or 0)

    db.flush()


def _calc_combined(throughput: float, quality_pct: float, qw: float) -> float:
    """combined = throughput * (quality_pct / 100) ^ quality_weight"""
    if throughput <= 0:
        return 0.0
    q_factor = max(quality_pct / 100.0, 0.0)
    return throughput * (q_factor ** qw)


# ── 6. update_all_active_competitions ─────────────────────────────

def update_all_active_competitions(db: Session) -> int:
    """Cron job: recalculate scores for all active competitions.

    Also activates upcoming competitions whose start_date <= today.
    Returns count of competitions processed.
    """
    today = date.today()

    # Activate upcoming competitions that should have started
    upcoming = (
        db.query(Competition)
        .filter(
            Competition.status == "upcoming",
            Competition.start_date <= today,
        )
        .all()
    )
    for comp in upcoming:
        comp.status = "active"
        logger.info("Competition activated: %s", comp.title)

    db.flush()

    # Update scores for all active
    active = (
        db.query(Competition)
        .filter(Competition.status == "active")
        .all()
    )
    for comp in active:
        try:
            update_competition_scores(db, comp.id)
        except Exception:
            logger.exception("Failed to update scores for competition %s", comp.id)

    db.flush()
    count = len(upcoming) + len(active)
    logger.info(
        "Competition cron: activated %d, scored %d", len(upcoming), len(active),
    )
    return count


# ── 7. finalize_competition ───────────────────────────────────────

def finalize_competition(db: Session, competition_id: UUID) -> None:
    """Set status=completed, assign final ranks, award points."""
    comp = db.query(Competition).get(competition_id)
    if not comp:
        raise ValueError(f"Competition {competition_id} not found")
    if comp.status == "completed":
        logger.warning("Competition %s already completed", comp.title)
        return

    # Final score recalc
    if comp.status == "active":
        update_competition_scores(db, comp.id)

    comp.status = "completed"

    entries = (
        db.query(CompetitionEntry)
        .filter(CompetitionEntry.competition_id == comp.id)
        .order_by(CompetitionEntry.combined_score.desc())
        .all()
    )

    for i, entry in enumerate(entries, start=1):
        entry.rank = i
        points = PRIZE_POINTS.get(i, PARTICIPATION_POINTS)
        entry.bonus_points = points

        if comp.competition_type == "individual" and entry.user_id:
            _award_competition_points(
                db, entry.user_id, comp.factory_id, points,
                f"Kompetisi '{comp.title}' - Peringkat #{i}",
                competition_id=comp.id,
            )
        elif comp.competition_type == "team" and entry.team_id:
            _award_team_points(db, comp, entry.team_id, points, i)

    db.flush()
    logger.info(
        "Competition finalized: '%s' — %d participants", comp.title, len(entries),
    )


def _award_competition_points(
    db: Session,
    user_id: UUID,
    factory_id: UUID,
    points: int,
    reason: str,
    competition_id: UUID | None = None,
) -> None:
    """Award points via the central points system."""
    try:
        award_points(
            db, user_id, factory_id, points, reason,
            details={"source": "competition", "competition_id": str(competition_id)},
        )
    except Exception:
        logger.exception("Failed to award %d pts to user %s", points, user_id)


def _award_team_points(
    db: Session,
    comp: Competition,
    team_id: UUID,
    points: int,
    rank: int,
) -> None:
    """Award points to every member of a team.

    Members are resolved by matching OperationLog users whose operations
    match the team's filter_key in the competition date range.
    """
    team = db.query(CompetitionTeam).get(team_id)
    if not team:
        return

    user_ids_query = (
        db.query(OperationLog.user_id)
        .filter(
            OperationLog.factory_id == comp.factory_id,
            OperationLog.shift_date >= comp.start_date,
            OperationLog.shift_date <= comp.end_date,
            OperationLog.quantity_processed > 0,
        )
    )

    if team.filter_key:
        from api.models import Operation
        user_ids_query = user_ids_query.join(
            Operation, Operation.id == OperationLog.operation_id,
        ).filter(
            sa_func.lower(Operation.name).contains(team.filter_key.lower()),
        )

    member_ids = [row[0] for row in user_ids_query.distinct().all()]

    for uid in member_ids:
        _award_competition_points(
            db, uid, comp.factory_id, points,
            f"Kompetisi Tim '{comp.title}' ({team.name}) - Peringkat #{rank}",
            competition_id=comp.id,
        )

    logger.info(
        "Team '%s' — %d members awarded %d pts each", team.name, len(member_ids), points,
    )


# ── 8. finalize_ended_competitions ────────────────────────────────

def finalize_ended_competitions(db: Session) -> int:
    """Cron: finds active competitions past their end_date, finalizes them."""
    today = date.today()
    ended = (
        db.query(Competition)
        .filter(
            Competition.status == "active",
            Competition.end_date < today,
        )
        .all()
    )

    count = 0
    for comp in ended:
        try:
            finalize_competition(db, comp.id)
            count += 1
        except Exception:
            logger.exception("Failed to finalize competition %s", comp.id)

    if count:
        logger.info("Auto-finalized %d competitions", count)
    return count


# ── 9. auto_create_weekly_competition ─────────────────────────────

def auto_create_weekly_competition(db: Session, factory_id: UUID) -> Competition:
    """Create 'Minggu Kecepatan #N' individual competition, Mon-Sun.

    Week number is ISO week of the start date.
    """
    today = date.today()
    # Next Monday (or today if already Monday)
    days_to_monday = (7 - today.weekday()) % 7
    if days_to_monday == 0 and today.weekday() != 0:
        days_to_monday = 7
    monday = today + timedelta(days=days_to_monday) if days_to_monday else today
    sunday = monday + timedelta(days=6)

    week_num = monday.isocalendar()[1]
    bulan = _BULAN_ID.get(monday.month, "")

    title = f"Minggu Kecepatan #{week_num}"
    title_id = f"Speed Week #{week_num} — {bulan} {monday.year}"

    # Prevent duplicate for same week
    existing = (
        db.query(Competition)
        .filter(
            Competition.factory_id == factory_id,
            Competition.start_date == monday,
            Competition.title == title,
        )
        .first()
    )
    if existing:
        logger.info("Weekly competition already exists for week %d", week_num)
        return existing

    comp = create_competition(
        db, factory_id,
        title=title,
        competition_type="individual",
        metric="combined",
        start_date=monday,
        end_date=sunday,
        quality_weight=1.0,
        title_id=title_id,
        season_tag=f"{monday.year}-W{week_num:02d}",
    )
    logger.info("Auto-created weekly competition: %s (%s..%s)", title, monday, sunday)
    return comp


# ── 10. start_new_season ──────────────────────────────────────────

def start_new_season(db: Session, factory_id: UUID) -> GamificationSeason:
    """Create a GamificationSeason for the current month.

    Closes previous active season with final_standings snapshot.
    """
    today = date.today()
    month_start = today.replace(day=1)
    _, last_day = monthrange(today.year, today.month)
    month_end = today.replace(day=last_day)
    bulan = _BULAN_ID.get(today.month, "")

    season_name = f"Musim {bulan} {today.year}"

    # Close previous active season
    prev_season = (
        db.query(GamificationSeason)
        .filter(
            GamificationSeason.factory_id == factory_id,
            GamificationSeason.status == "active",
        )
        .order_by(GamificationSeason.start_date.desc())
        .first()
    )

    if prev_season:
        # Snapshot final standings from completed competitions in that season
        completed = (
            db.query(Competition)
            .filter(
                Competition.factory_id == factory_id,
                Competition.status == "completed",
                Competition.start_date >= prev_season.start_date,
                Competition.end_date <= prev_season.end_date,
            )
            .all()
        )

        standings_snapshot = []
        for c in completed:
            entries = (
                db.query(CompetitionEntry)
                .filter(CompetitionEntry.competition_id == c.id)
                .order_by(CompetitionEntry.rank)
                .limit(10)
                .all()
            )
            standings_snapshot.append({
                "competition_id": str(c.id),
                "title": c.title,
                "top": [
                    {
                        "rank": e.rank,
                        "user_id": str(e.user_id) if e.user_id else None,
                        "team_id": str(e.team_id) if e.team_id else None,
                        "combined_score": float(e.combined_score),
                    }
                    for e in entries
                ],
            })

        prev_season.status = "completed"
        prev_season.final_standings = standings_snapshot
        logger.info("Season closed: %s", prev_season.name)

    # Prevent duplicate
    existing = (
        db.query(GamificationSeason)
        .filter(
            GamificationSeason.factory_id == factory_id,
            GamificationSeason.start_date == month_start,
        )
        .first()
    )
    if existing:
        logger.info("Season already exists: %s", existing.name)
        return existing

    season = GamificationSeason(
        factory_id=factory_id,
        name=season_name,
        start_date=month_start,
        end_date=month_end,
        status="active",
    )
    db.add(season)
    db.flush()
    logger.info("New season started: %s (%s..%s)", season_name, month_start, month_end)
    return season


# ── 11. propose_challenge ─────────────────────────────────────────

def propose_challenge(
    db: Session,
    factory_id: UUID,
    proposed_by: UUID,
    title: str,
    metric: str = "combined",
    days: int = 7,
) -> Competition:
    """Worker-proposed challenge. Status='upcoming' until PM approves.

    PM approves by setting status to 'active'.
    """
    today = date.today()
    start = today + timedelta(days=1)
    end = start + timedelta(days=days - 1)

    comp = Competition(
        factory_id=factory_id,
        title=title,
        title_id=None,
        competition_type="individual",
        metric=metric,
        scoring_formula="combined",
        quality_weight=Decimal("1.0"),
        start_date=start,
        end_date=end,
        status="upcoming",
        proposed_by=proposed_by,
    )
    db.add(comp)
    db.flush()

    user = db.query(User).get(proposed_by)
    proposer_name = user.full_name if user else str(proposed_by)
    logger.info(
        "Challenge proposed by %s: '%s' (%s, %d hari)",
        proposer_name, title, metric, days,
    )
    return comp


# ── Helpers ───────────────────────────────────────────────────────

def _entry_to_dict(db: Session, entry: CompetitionEntry) -> dict:
    """Serialize a CompetitionEntry to dict with user/team name."""
    name = None
    if entry.user_id:
        user = db.query(User).get(entry.user_id)
        name = user.full_name if user else str(entry.user_id)
    elif entry.team_id:
        team = db.query(CompetitionTeam).get(entry.team_id)
        name = team.name if team else str(entry.team_id)

    return {
        "id": str(entry.id),
        "user_id": str(entry.user_id) if entry.user_id else None,
        "team_id": str(entry.team_id) if entry.team_id else None,
        "name": name,
        "throughput_score": float(entry.throughput_score),
        "quality_score": float(entry.quality_score),
        "combined_score": float(entry.combined_score),
        "bonus_points": entry.bonus_points,
        "rank": entry.rank,
        "entries_count": entry.entries_count,
    }
