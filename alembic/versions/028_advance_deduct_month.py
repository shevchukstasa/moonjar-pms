"""Add deduct_year/deduct_month to salary_advances for carry-over support.

Revision ID: 028
Revises: 027
Create Date: 2026-04-25
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = '028'
down_revision = '027'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('salary_advances', sa.Column('deduct_year', sa.Integer, nullable=True))
    op.add_column('salary_advances', sa.Column('deduct_month', sa.Integer, nullable=True))


def downgrade() -> None:
    op.drop_column('salary_advances', 'deduct_month')
    op.drop_column('salary_advances', 'deduct_year')
