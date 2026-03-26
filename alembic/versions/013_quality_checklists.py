"""Add quality_checklists table for structured pre-kiln and final QC inspections.

New table: quality_checklists
- Stores structured checklist results as JSONB
- check_type: 'pre_kiln' or 'final'
- overall_result: 'pass', 'fail', 'needs_rework'
- Links to order_positions, factories, users

Revision ID: 013_quality_checklists
Revises: 012_glazing_boards_and_factory_columns
Create Date: 2026-03-26
"""
from alembic import op
from sqlalchemy import text

revision = "013_quality_checklists"
down_revision = "012_glazing_boards_and_factory_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(text("""
        CREATE TABLE IF NOT EXISTS quality_checklists (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            position_id UUID NOT NULL REFERENCES order_positions(id) ON DELETE CASCADE,
            factory_id UUID NOT NULL REFERENCES factories(id),
            check_type VARCHAR(30) NOT NULL,
            checklist_results JSONB NOT NULL,
            overall_result VARCHAR(20) NOT NULL,
            checked_by UUID REFERENCES users(id),
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))

    # Indexes for common queries
    op.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_quality_checklists_position_id "
        "ON quality_checklists(position_id)"
    ))
    op.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_quality_checklists_check_type "
        "ON quality_checklists(check_type)"
    ))
    op.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_quality_checklists_factory_id "
        "ON quality_checklists(factory_id)"
    ))


def downgrade() -> None:
    op.execute(text("DROP TABLE IF EXISTS quality_checklists"))
