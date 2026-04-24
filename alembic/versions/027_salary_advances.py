"""Add salary_advances table for employee prepayment tracking.

Revision ID: 027
Revises: 026_material_short_name_typology
Create Date: 2026-04-24
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
import sqlalchemy.dialects.postgresql as pg

revision = '027'
down_revision = '026'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'salary_advances',
        sa.Column('id', pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('employee_id', pg.UUID(as_uuid=True), sa.ForeignKey('employees.id'), nullable=False),
        sa.Column('date', sa.Date, nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('recorded_by', pg.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_salary_advances_employee_id', 'salary_advances', ['employee_id'])
    op.create_index('ix_salary_advances_date', 'salary_advances', ['date'])


def downgrade() -> None:
    op.drop_index('ix_salary_advances_date', 'salary_advances')
    op.drop_index('ix_salary_advances_employee_id', 'salary_advances')
    op.drop_table('salary_advances')
