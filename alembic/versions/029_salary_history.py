"""Add salary_history table for tracking salary changes over time.

Revision ID: 029
Revises: 028
Create Date: 2026-04-25
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
import sqlalchemy.dialects.postgresql as pg

revision = '029'
down_revision = '028'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'salary_history',
        sa.Column('id', pg.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('employee_id', pg.UUID(as_uuid=True),
                  sa.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False),
        sa.Column('effective_date', sa.Date, nullable=False),
        sa.Column('base_salary', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('allowance_bike', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('allowance_housing', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('allowance_food', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('allowance_bpjs', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('allowance_other', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('recorded_by', pg.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.execute("""
        CREATE INDEX ix_salary_history_employee_date
        ON salary_history (employee_id, effective_date DESC)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_salary_history_employee_date")
    op.drop_table('salary_history')
