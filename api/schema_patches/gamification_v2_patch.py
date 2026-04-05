"""Gamification Engine v2 — schema patch for skill badges, competitions, prizes, seasons."""

import logging
from sqlalchemy import text

logger = logging.getLogger("moonjar.schema_patches.gamification_v2")

STATEMENTS = [
    # ── Skill Badges ──
    """
    CREATE TABLE IF NOT EXISTS skill_badges (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        factory_id UUID NOT NULL REFERENCES factories(id) ON DELETE CASCADE,
        code VARCHAR(50) NOT NULL,
        name VARCHAR(200) NOT NULL,
        name_id VARCHAR(200),
        category VARCHAR(50) NOT NULL,
        icon VARCHAR(10),
        description TEXT,
        required_operations INTEGER NOT NULL DEFAULT 50,
        required_zero_defect_pct NUMERIC(5,2) DEFAULT 90,
        required_mentor_approval BOOLEAN NOT NULL DEFAULT FALSE,
        points_on_earn INTEGER NOT NULL DEFAULT 100,
        operation_id UUID REFERENCES operations(id) ON DELETE SET NULL,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE(factory_id, code)
    )
    """,
    # ── User Skills ──
    """
    CREATE TABLE IF NOT EXISTS user_skills (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        skill_badge_id UUID NOT NULL REFERENCES skill_badges(id) ON DELETE CASCADE,
        status VARCHAR(20) NOT NULL DEFAULT 'learning',
        operations_completed INTEGER NOT NULL DEFAULT 0,
        defect_free_pct NUMERIC(5,2) NOT NULL DEFAULT 0,
        certified_at TIMESTAMPTZ,
        certified_by UUID REFERENCES users(id) ON DELETE SET NULL,
        started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE(user_id, skill_badge_id)
    )
    """,
    # ── Competitions ──
    """
    CREATE TABLE IF NOT EXISTS competitions (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        factory_id UUID NOT NULL REFERENCES factories(id) ON DELETE CASCADE,
        title VARCHAR(300) NOT NULL,
        title_id VARCHAR(300),
        competition_type VARCHAR(20) NOT NULL,
        metric VARCHAR(50) NOT NULL DEFAULT 'combined',
        scoring_formula VARCHAR(20) NOT NULL DEFAULT 'combined',
        quality_weight NUMERIC(3,1) NOT NULL DEFAULT 1.0,
        start_date DATE NOT NULL,
        end_date DATE NOT NULL,
        status VARCHAR(20) NOT NULL DEFAULT 'upcoming',
        season_tag VARCHAR(50),
        prize_description TEXT,
        prize_budget_idr NUMERIC(12,2),
        created_by UUID REFERENCES users(id) ON DELETE SET NULL,
        proposed_by UUID REFERENCES users(id) ON DELETE SET NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    # ── Competition Teams ──
    """
    CREATE TABLE IF NOT EXISTS competition_teams (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        competition_id UUID NOT NULL REFERENCES competitions(id) ON DELETE CASCADE,
        name VARCHAR(200) NOT NULL,
        team_type VARCHAR(30) NOT NULL,
        filter_key VARCHAR(100),
        icon VARCHAR(10),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    # ── Competition Entries ──
    """
    CREATE TABLE IF NOT EXISTS competition_entries (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        competition_id UUID NOT NULL REFERENCES competitions(id) ON DELETE CASCADE,
        user_id UUID REFERENCES users(id) ON DELETE CASCADE,
        team_id UUID REFERENCES competition_teams(id) ON DELETE CASCADE,
        throughput_score NUMERIC(10,2) NOT NULL DEFAULT 0,
        quality_score NUMERIC(5,2) NOT NULL DEFAULT 100,
        combined_score NUMERIC(10,2) NOT NULL DEFAULT 0,
        bonus_points INTEGER NOT NULL DEFAULT 0,
        rank INTEGER,
        entries_count INTEGER NOT NULL DEFAULT 0,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE(competition_id, user_id),
        UNIQUE(competition_id, team_id)
    )
    """,
    # ── Prize Recommendations ──
    """
    CREATE TABLE IF NOT EXISTS prize_recommendations (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        factory_id UUID NOT NULL REFERENCES factories(id) ON DELETE CASCADE,
        period VARCHAR(20) NOT NULL,
        period_label VARCHAR(50) NOT NULL,
        prize_type VARCHAR(30) NOT NULL,
        recipient_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
        recipient_team_name VARCHAR(200),
        prize_title VARCHAR(300) NOT NULL,
        prize_description TEXT,
        estimated_cost_idr NUMERIC(12,2) NOT NULL,
        productivity_gain_pct NUMERIC(5,2),
        roi_estimate NUMERIC(8,2),
        ai_reasoning TEXT,
        status VARCHAR(20) NOT NULL DEFAULT 'suggested',
        approved_by UUID REFERENCES users(id) ON DELETE SET NULL,
        approved_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    # ── Gamification Seasons ──
    """
    CREATE TABLE IF NOT EXISTS gamification_seasons (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        factory_id UUID NOT NULL REFERENCES factories(id) ON DELETE CASCADE,
        name VARCHAR(100) NOT NULL,
        start_date DATE NOT NULL,
        end_date DATE NOT NULL,
        status VARCHAR(20) NOT NULL DEFAULT 'active',
        final_standings JSONB,
        prizes_awarded JSONB,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE(factory_id, start_date)
    )
    """,
]


def apply(conn):
    """Apply gamification v2 schema patch.

    Receives a SQLAlchemy Connection (not engine) from main.py patch runner.
    """
    for stmt in STATEMENTS:
        try:
            conn.execute(text(stmt))
        except Exception as e:
            logger.warning("Gamification v2 patch statement skipped: %s", e)
    logger.info("Gamification v2 schema patch applied (7 tables)")
