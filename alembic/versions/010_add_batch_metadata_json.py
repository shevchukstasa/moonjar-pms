"""Add metadata_json JSONB column to batches table.

Stores loading plan details (geometry-based capacity calculations,
per-position loading method, utilization metrics).

Revision ID: 010_add_batch_metadata_json
Revises: 009_add_missing_enums
Create Date: 2026-03-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "010_add_batch_metadata_json"
down_revision = "009_add_missing_enums"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("batches", sa.Column("metadata_json", JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column("batches", "metadata_json")
