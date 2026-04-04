"""Gamification Engine v2 — REST API for skills, competitions, prizes, CEO dashboard."""

import logging
from uuid import UUID
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.roles import require_management, require_owner, require_any

logger = logging.getLogger("moonjar.gamification")
router = APIRouter()


# ── Pydantic schemas ────────────────────────────────────────────


class SkillBadgeCreate(BaseModel):
    code: str
    name: str
    name_id: str | None = None
    category: str = "production"
    icon: str | None = None
    description: str | None = None
    required_operations: int = 50
    required_zero_defect_pct: float = 90.0
    required_mentor_approval: bool = False
    points_on_earn: int = 100
    operation_id: UUID | None = None


class StartSkillRequest(BaseModel):
    skill_badge_id: UUID


class CertifySkillRequest(BaseModel):
    user_skill_id: UUID


class CompetitionCreate(BaseModel):
    title: str
    title_id: str | None = None
    competition_type: str = "individual"
    metric: str = "combined"
    scoring_formula: str = "combined"
    quality_weight: float = 1.0
    start_date: date
    end_date: date
    prize_description: str | None = None
    prize_budget_idr: float | None = None


class TeamCompetitionCreate(CompetitionCreate):
    team_type: str = "section"
    teams: list[dict] | None = None


class ProposeChallenge(BaseModel):
    title: str
    title_id: str | None = None
    metric: str = "combined"
    start_date: date
    end_date: date


class ApprovePrize(BaseModel):
    prize_id: UUID


# ── Skills endpoints ────────────────────────────────────────────


@router.get("/skills/badges")
async def list_skill_badges(
    factory_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_any),
):
    """List all skill badges for a factory."""
    from business.services.skill_system import get_factory_skills
    return get_factory_skills(db, factory_id)


@router.post("/skills/badges/seed")
async def seed_skill_badges(
    factory_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Seed default skill badges for a factory."""
    from business.services.skill_system import seed_factory_skills
    count = seed_factory_skills(db, factory_id)
    db.commit()
    return {"seeded": count}


@router.get("/skills/user/{user_id}")
async def get_user_skills(
    user_id: UUID,
    factory_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_any),
):
    """Get all skills and progress for a user."""
    from business.services.skill_system import get_user_skills
    return get_user_skills(db, user_id, factory_id)


@router.post("/skills/start")
async def start_learning_skill(
    body: StartSkillRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_any),
):
    """Start learning a new skill."""
    from business.services.skill_system import start_skill_learning
    result = start_skill_learning(db, current_user.id, body.skill_badge_id)
    db.commit()
    return result


@router.post("/skills/certify")
async def certify_skill(
    body: CertifySkillRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """PM/CEO approves skill certification."""
    from business.services.skill_system import approve_certification
    result = approve_certification(db, body.user_skill_id, current_user.id)
    db.commit()
    return result


@router.post("/skills/revoke")
async def revoke_skill(
    body: CertifySkillRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """PM/CEO revokes a certification."""
    from business.services.skill_system import revoke_certification
    result = revoke_certification(db, body.user_skill_id, current_user.id)
    db.commit()
    return result


# ── Competitions endpoints ──────────────────────────────────────


@router.get("/competitions")
async def list_competitions(
    factory_id: UUID,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_any),
):
    """List competitions for a factory."""
    from business.services.competitions import get_active_competitions
    return get_active_competitions(db, factory_id, status)


@router.get("/competitions/{competition_id}/standings")
async def competition_standings(
    competition_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_any),
):
    """Get competition standings/leaderboard."""
    from business.services.competitions import get_competition_standings
    return get_competition_standings(db, competition_id)


@router.post("/competitions")
async def create_competition(
    body: CompetitionCreate,
    factory_id: UUID = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """PM/CEO creates a new individual competition."""
    from business.services.competitions import create_competition as _create
    comp = _create(
        db, factory_id,
        title=body.title,
        title_id=body.title_id,
        competition_type=body.competition_type,
        metric=body.metric,
        scoring_formula=body.scoring_formula,
        quality_weight=body.quality_weight,
        start_date=body.start_date,
        end_date=body.end_date,
        prize_description=body.prize_description,
        prize_budget_idr=body.prize_budget_idr,
        created_by=current_user.id,
    )
    db.commit()
    return {"id": str(comp.id), "title": comp.title, "status": comp.status}


@router.post("/competitions/team")
async def create_team_competition(
    body: TeamCompetitionCreate,
    factory_id: UUID = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """PM/CEO creates a team competition."""
    from business.services.competitions import create_team_competition as _create
    comp = _create(
        db, factory_id,
        title=body.title,
        title_id=body.title_id,
        competition_type="team",
        metric=body.metric,
        scoring_formula=body.scoring_formula,
        quality_weight=body.quality_weight,
        start_date=body.start_date,
        end_date=body.end_date,
        prize_description=body.prize_description,
        prize_budget_idr=body.prize_budget_idr,
        created_by=current_user.id,
        team_type=body.team_type,
        teams=body.teams,
    )
    db.commit()
    return {"id": str(comp.id), "title": comp.title, "status": comp.status}


@router.post("/competitions/propose")
async def propose_challenge(
    body: ProposeChallenge,
    factory_id: UUID = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_any),
):
    """Worker proposes a challenge (needs PM approval)."""
    from business.services.competitions import propose_challenge as _propose
    comp = _propose(
        db, factory_id,
        proposed_by=current_user.id,
        title=body.title,
        title_id=body.title_id,
        metric=body.metric,
        start_date=body.start_date,
        end_date=body.end_date,
    )
    db.commit()
    return {"id": str(comp.id), "title": comp.title, "status": comp.status}


@router.post("/competitions/{competition_id}/approve")
async def approve_competition(
    competition_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """PM/CEO approves a proposed challenge."""
    from api.models import Competition
    comp = db.query(Competition).filter(Competition.id == competition_id).first()
    if not comp:
        raise HTTPException(404, "Competition not found")
    if comp.status != "proposed":
        raise HTTPException(400, "Competition is not in proposed status")
    comp.status = "upcoming"
    comp.created_by = current_user.id
    db.commit()
    return {"id": str(comp.id), "status": comp.status}


@router.post("/competitions/update-scores")
async def trigger_score_update(
    factory_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Manually trigger score update for active competitions."""
    from business.services.competitions import update_all_active_competitions
    updated = update_all_active_competitions(db, factory_id)
    db.commit()
    return {"updated_competitions": updated}


# ── Prizes endpoints ────────────────────────────────────────────


@router.get("/prizes")
async def list_prizes(
    factory_id: UUID,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """List prize recommendations."""
    from business.services.prize_advisor import get_pending_prizes
    return get_pending_prizes(db, factory_id, status)


@router.post("/prizes/generate-monthly")
async def generate_monthly_prizes(
    factory_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_owner),
):
    """Generate monthly prize recommendations."""
    from business.services.prize_advisor import generate_monthly_prizes
    prizes = generate_monthly_prizes(db, factory_id)
    db.commit()
    return {"generated": len(prizes)}


@router.post("/prizes/{prize_id}/approve")
async def approve_prize(
    prize_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_owner),
):
    """CEO/Owner approves a prize recommendation."""
    from business.services.prize_advisor import approve_prize as _approve
    result = _approve(db, prize_id, current_user.id)
    db.commit()
    return result


@router.post("/prizes/{prize_id}/reject")
async def reject_prize(
    prize_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_owner),
):
    """CEO/Owner rejects a prize recommendation."""
    from business.services.prize_advisor import reject_prize as _reject
    result = _reject(db, prize_id)
    db.commit()
    return result


@router.post("/prizes/{prize_id}/award")
async def award_prize(
    prize_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_owner),
):
    """Mark a prize as awarded."""
    from business.services.prize_advisor import award_prize as _award
    result = _award(db, prize_id)
    db.commit()
    return result


# ── CEO Dashboard endpoints ─────────────────────────────────────


@router.get("/ceo-dashboard")
async def ceo_dashboard_data(
    factory_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_owner),
):
    """Get CEO gamification dashboard data."""
    from business.services.ceo_reports import get_ceo_dashboard_data
    return get_ceo_dashboard_data(db, factory_id)


@router.get("/ceo-dashboard/impact")
async def productivity_impact(
    factory_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_owner),
):
    """Get productivity impact analysis."""
    from business.services.ceo_reports import generate_productivity_impact
    return generate_productivity_impact(db, factory_id)


@router.post("/ceo-dashboard/send-report")
async def send_ceo_report(
    factory_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_owner),
):
    """Manually trigger CEO weekly gamification report."""
    from business.services.ceo_reports import generate_weekly_gamification_report
    report = generate_weekly_gamification_report(db, factory_id)
    return {"report": report}


# ── Seasons endpoints ───────────────────────────────────────────


@router.get("/seasons")
async def list_seasons(
    factory_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_any),
):
    """List gamification seasons."""
    from api.models import GamificationSeason
    seasons = db.query(GamificationSeason).filter(
        GamificationSeason.factory_id == factory_id,
    ).order_by(GamificationSeason.start_date.desc()).all()
    return [
        {
            "id": str(s.id),
            "name": s.name,
            "start_date": str(s.start_date),
            "end_date": str(s.end_date),
            "status": s.status,
            "final_standings": s.final_standings,
            "prizes_awarded": s.prizes_awarded,
        }
        for s in seasons
    ]
