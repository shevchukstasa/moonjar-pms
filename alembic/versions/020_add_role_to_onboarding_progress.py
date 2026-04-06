"""Add role column to onboarding_progress for multi-role onboarding.

Each role has its own set of sections, so progress is now scoped by
(user_id, section_id, role) instead of just (user_id, section_id).

Revision ID: 020
Revises: 019
"""
from alembic import op
import sqlalchemy as sa

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade():
    # Add role column with default for existing rows
    op.add_column(
        "onboarding_progress",
        sa.Column("role", sa.String(50), nullable=False, server_default="production_manager"),
    )

    # Drop old unique constraint and create new one including role
    op.drop_constraint("uq_onboarding_user_section", "onboarding_progress", type_="unique")
    op.create_unique_constraint(
        "uq_onboarding_user_section_role",
        "onboarding_progress",
        ["user_id", "section_id", "role"],
    )


def downgrade():
    op.drop_constraint("uq_onboarding_user_section_role", "onboarding_progress", type_="unique")
    op.drop_column("onboarding_progress", "role")
    op.create_unique_constraint(
        "uq_onboarding_user_section",
        "onboarding_progress",
        ["user_id", "section_id"],
    )
