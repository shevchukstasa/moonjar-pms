"""Moonjar PMS — Role-based onboarding system with gamified progress tracking."""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import and_

from api.database import get_db
from api.auth import get_current_user
from api.models import OnboardingProgress, User
from api.onboarding_content import get_role_content, get_all_roles

logger = logging.getLogger("moonjar.onboarding")
router = APIRouter()

# ── Constants ──────────────────────────────────────────────────────

XP_SECTION_READ = 50
XP_QUIZ_PASS = 100  # awarded when quiz_score >= 80
QUIZ_PASS_THRESHOLD = 80

DEFAULT_ROLE = "production_manager"


# ── Helpers ──────────────────────────────────────────────────────

def _resolve_role(role: Optional[str], user_role: str) -> str:
    """Resolve which role's onboarding to show.

    Owner/admin can view any role's onboarding. Others see their own.
    """
    if role and role in get_all_roles():
        # Owner and admin can view any role
        if user_role in ("owner", "administrator") or role == user_role:
            return role
    return user_role if user_role in get_all_roles() else DEFAULT_ROLE


def _get_sections_for_role(role: str) -> list[str]:
    content = get_role_content(role)
    if not content:
        return []
    return content["SECTIONS"]


def _get_quiz_answers_for_role(role: str) -> dict:
    content = get_role_content(role)
    if not content:
        return {}
    return content["QUIZ_ANSWERS"]


def _get_content_for_role(role: str) -> dict:
    content = get_role_content(role)
    if not content:
        return {}
    return content["ONBOARDING_CONTENT"]


# ── Pydantic schemas ──────────────────────────────────────────────

class SectionProgress(BaseModel):
    section_id: str
    completed: bool
    quiz_score: int | None
    quiz_attempts: int
    xp_earned: int
    completed_at: str | None

class OnboardingOverview(BaseModel):
    sections: list[SectionProgress]
    total_xp: int
    completed_count: int
    total_sections: int
    pct_complete: int
    role: str

class CompleteSectionRequest(BaseModel):
    section_id: str
    role: str | None = None

class SubmitQuizRequest(BaseModel):
    section_id: str
    answers: dict[str, str]
    role: str | None = None

class QuizResult(BaseModel):
    score: int
    passed: bool
    xp_awarded: int
    correct_answers: dict[str, str]


# ── Endpoints ─────────────────────────────────────────────────────

@router.get("/progress", response_model=OnboardingOverview)
async def get_progress(
    role: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get full onboarding progress for the current user and role."""
    resolved_role = _resolve_role(role, current_user.role)
    sections_list = _get_sections_for_role(resolved_role)

    rows = db.query(OnboardingProgress).filter(
        and_(
            OnboardingProgress.user_id == current_user.id,
            OnboardingProgress.role == resolved_role,
        )
    ).all()

    progress_map = {r.section_id: r for r in rows}
    sections = []
    total_xp = 0
    completed = 0

    for sid in sections_list:
        row = progress_map.get(sid)
        if row:
            sections.append(SectionProgress(
                section_id=sid,
                completed=row.completed,
                quiz_score=row.quiz_score,
                quiz_attempts=row.quiz_attempts,
                xp_earned=row.xp_earned,
                completed_at=row.completed_at.isoformat() if row.completed_at else None,
            ))
            total_xp += row.xp_earned
            if row.completed:
                completed += 1
        else:
            sections.append(SectionProgress(
                section_id=sid,
                completed=False,
                quiz_score=None,
                quiz_attempts=0,
                xp_earned=0,
                completed_at=None,
            ))

    return OnboardingOverview(
        sections=sections,
        total_xp=total_xp,
        completed_count=completed,
        total_sections=len(sections_list),
        pct_complete=int((completed / len(sections_list)) * 100) if sections_list else 0,
        role=resolved_role,
    )


@router.post("/complete-section", response_model=SectionProgress)
async def complete_section(
    body: CompleteSectionRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a section as read (awards XP_SECTION_READ)."""
    resolved_role = _resolve_role(body.role, current_user.role)
    sections_list = _get_sections_for_role(resolved_role)

    if body.section_id not in sections_list:
        raise HTTPException(400, f"Unknown section: {body.section_id}")

    row = db.query(OnboardingProgress).filter(
        and_(
            OnboardingProgress.user_id == current_user.id,
            OnboardingProgress.section_id == body.section_id,
            OnboardingProgress.role == resolved_role,
        )
    ).first()

    if not row:
        row = OnboardingProgress(
            user_id=current_user.id,
            section_id=body.section_id,
            role=resolved_role,
            completed=False,
            xp_earned=0,
        )
        db.add(row)

    if not row.completed:
        row.completed = True
        row.completed_at = datetime.now(timezone.utc)
        row.xp_earned += XP_SECTION_READ
        db.commit()
        db.refresh(row)
        logger.info(f"Onboarding: user {current_user.id} completed section {body.section_id} (role={resolved_role})")

    return SectionProgress(
        section_id=row.section_id,
        completed=row.completed,
        quiz_score=row.quiz_score,
        quiz_attempts=row.quiz_attempts,
        xp_earned=row.xp_earned,
        completed_at=row.completed_at.isoformat() if row.completed_at else None,
    )


@router.post("/submit-quiz", response_model=QuizResult)
async def submit_quiz(
    body: SubmitQuizRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submit quiz answers, calculate score, award XP if passing."""
    resolved_role = _resolve_role(body.role, current_user.role)
    sections_list = _get_sections_for_role(resolved_role)
    quiz_answers = _get_quiz_answers_for_role(resolved_role)

    if body.section_id not in sections_list:
        raise HTTPException(400, f"Unknown section: {body.section_id}")

    answer_key = quiz_answers.get(body.section_id, {})
    if not answer_key:
        raise HTTPException(400, f"No quiz for section: {body.section_id}")

    # Calculate score
    correct = 0
    total = len(answer_key)
    for qid, correct_answer in answer_key.items():
        if body.answers.get(qid) == correct_answer:
            correct += 1

    score = int((correct / total) * 100) if total else 0
    passed = score >= QUIZ_PASS_THRESHOLD

    # Update DB
    row = db.query(OnboardingProgress).filter(
        and_(
            OnboardingProgress.user_id == current_user.id,
            OnboardingProgress.section_id == body.section_id,
            OnboardingProgress.role == resolved_role,
        )
    ).first()

    if not row:
        row = OnboardingProgress(
            user_id=current_user.id,
            section_id=body.section_id,
            role=resolved_role,
            completed=False,
            xp_earned=0,
        )
        db.add(row)

    row.quiz_attempts += 1
    xp_awarded = 0

    # Only award quiz XP if this is the first passing attempt
    if passed and (row.quiz_score is None or row.quiz_score < QUIZ_PASS_THRESHOLD):
        xp_awarded = XP_QUIZ_PASS
        row.xp_earned += XP_QUIZ_PASS

    # Keep the best score
    if row.quiz_score is None or score > row.quiz_score:
        row.quiz_score = score

    db.commit()
    db.refresh(row)

    return QuizResult(
        score=score,
        passed=passed,
        xp_awarded=xp_awarded,
        correct_answers=answer_key,
    )


# ── Content endpoint ─────────────────────────────────────────────

@router.get("/content/{lang}")
async def get_content(
    lang: str,
    role: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
):
    """Get all onboarding content for a specific role."""
    if lang not in ("en", "id", "ru"):
        lang = "en"

    resolved_role = _resolve_role(role, current_user.role)
    sections_list = _get_sections_for_role(resolved_role)
    content = _get_content_for_role(resolved_role)

    if not sections_list:
        raise HTTPException(404, f"No onboarding content for role: {resolved_role}")

    return {
        "sections": sections_list,
        "content": content,
        "xp_section_read": XP_SECTION_READ,
        "xp_quiz_pass": XP_QUIZ_PASS,
        "quiz_pass_threshold": QUIZ_PASS_THRESHOLD,
        "role": resolved_role,
    }


@router.get("/roles")
async def list_onboarding_roles(current_user=Depends(get_current_user)):
    """List all roles that have onboarding content."""
    return {"roles": get_all_roles()}
