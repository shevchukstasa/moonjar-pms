"""Add pay_period field to employees table.

Revision ID: 014_add_employee_pay_period
Revises: 013_quality_checklists
Create Date: 2026-03-31
"""
from alembic import op
from sqlalchemy import text

revision = "014_add_employee_pay_period"
down_revision = "013_quality_checklists"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(text("""
        ALTER TABLE employees
        ADD COLUMN IF NOT EXISTS pay_period VARCHAR(20) NOT NULL DEFAULT 'calendar_month';
    """))


def downgrade():
    op.execute(text("""
        ALTER TABLE employees DROP COLUMN IF EXISTS pay_period;
    """))
