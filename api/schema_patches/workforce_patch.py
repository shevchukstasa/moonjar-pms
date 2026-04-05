"""Workforce management: worker skills, shift definitions, shift assignments."""
import logging
from sqlalchemy import text

logger = logging.getLogger("moonjar.patches.workforce")


def apply(conn):
    """Apply workforce schema patch.

    Receives a SQLAlchemy Connection (not engine) from main.py patch runner.
    """
    # WorkerStageSkill
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS worker_stage_skills (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            factory_id UUID NOT NULL REFERENCES factories(id) ON DELETE CASCADE,
            stage VARCHAR(50) NOT NULL,
            proficiency VARCHAR(20) NOT NULL DEFAULT 'capable',
            certified_at DATE,
            certified_by UUID REFERENCES users(id) ON DELETE SET NULL,
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_worker_stage_skill UNIQUE (user_id, factory_id, stage)
        )
    """))

    # ShiftDefinition
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS shift_definitions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            factory_id UUID NOT NULL REFERENCES factories(id) ON DELETE CASCADE,
            name VARCHAR(50) NOT NULL,
            name_id VARCHAR(50),
            start_time TIME NOT NULL,
            end_time TIME NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_shift_def_name UNIQUE (factory_id, name)
        )
    """))

    # ShiftAssignment
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS shift_assignments (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            factory_id UUID NOT NULL REFERENCES factories(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            shift_definition_id UUID NOT NULL REFERENCES shift_definitions(id) ON DELETE CASCADE,
            date DATE NOT NULL,
            stage VARCHAR(50) NOT NULL,
            is_lead BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            assigned_by UUID REFERENCES users(id) ON DELETE SET NULL,
            CONSTRAINT uq_shift_assignment_user_date_shift UNIQUE (user_id, date, shift_definition_id)
        )
    """))

    # Indexes for common queries
    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_worker_skills_factory_stage "
        "ON worker_stage_skills(factory_id, stage)"
    ))
    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_shift_assign_factory_date "
        "ON shift_assignments(factory_id, date)"
    ))
    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_shift_assign_date_stage "
        "ON shift_assignments(factory_id, date, stage)"
    ))

    logger.info("Workforce tables created/verified")
