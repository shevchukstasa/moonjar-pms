"""Add role column to onboarding_progress for multi-role onboarding.

Each role has its own set of sections, so progress is now scoped by
(user_id, section_id, role) instead of just (user_id, section_id).

Revision ID: 020
Revises: 019
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # Add role column if not exists
    col_exists = conn.execute(text("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'onboarding_progress' AND column_name = 'role'
    """)).scalar()

    if not col_exists:
        op.add_column(
            "onboarding_progress",
            sa.Column("role", sa.String(50), nullable=False, server_default="production_manager"),
        )

    # Drop old unique constraint if exists, create new one
    old_exists = conn.execute(text("""
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'uq_onboarding_user_section'
          AND table_name = 'onboarding_progress'
    """)).scalar()

    if old_exists:
        op.drop_constraint("uq_onboarding_user_section", "onboarding_progress", type_="unique")

    new_exists = conn.execute(text("""
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'uq_onboarding_user_section_role'
          AND table_name = 'onboarding_progress'
    """)).scalar()

    if not new_exists:
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
