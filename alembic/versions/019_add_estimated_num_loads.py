"""Add estimated_num_loads and schedule_metadata to order_positions.

estimated_num_loads: stores how many kiln firings the scheduler calculated
for this position, enabling the batch planner to split multi-load positions.

schedule_metadata: JSONB for scheduler/batch planner metadata such as
original_kiln_date (tracks deferrals for batch accumulation).

Revision ID: 019
Revises: 018
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "order_positions",
        sa.Column("estimated_num_loads", sa.Integer(), nullable=True),
    )
    op.add_column(
        "order_positions",
        sa.Column("schedule_metadata", JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("order_positions", "schedule_metadata")
    op.drop_column("order_positions", "estimated_num_loads")
