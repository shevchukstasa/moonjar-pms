"""Add retry_count and permanently_failed columns to sales_webhook_events.

Supports automatic webhook retry with max attempts tracking.

Revision ID: 014_webhook_retry_columns
Revises: 013_quality_checklists
Create Date: 2026-03-28
"""
from alembic import op
from sqlalchemy import text


revision = "014_webhook_retry_columns"
down_revision = "013_quality_checklists"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_bind().connect() as conn:
        conn.execute(text("""
            ALTER TABLE sales_webhook_events
            ADD COLUMN IF NOT EXISTS retry_count INTEGER NOT NULL DEFAULT 0;
        """))
        conn.execute(text("""
            ALTER TABLE sales_webhook_events
            ADD COLUMN IF NOT EXISTS permanently_failed BOOLEAN NOT NULL DEFAULT FALSE;
        """))
        conn.commit()


def downgrade() -> None:
    with op.get_bind().connect() as conn:
        conn.execute(text("ALTER TABLE sales_webhook_events DROP COLUMN IF EXISTS permanently_failed;"))
        conn.execute(text("ALTER TABLE sales_webhook_events DROP COLUMN IF EXISTS retry_count;"))
        conn.commit()
