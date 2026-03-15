"""
008 — Add upfront scheduling fields to order_positions.

New columns:
  planned_glazing_date     DATE   — when glazing should start
  planned_kiln_date        DATE   — when kiln firing should happen
  planned_sorting_date     DATE   — when sorting should happen
  planned_completion_date  DATE   — when position should be complete
  estimated_kiln_id        UUID   — preliminary kiln assignment (FK → resources)
  schedule_version         INT    — increment on each reschedule

These support TOC/DBR backward scheduling: when an order comes in,
the entire production path is planned immediately from deadline.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "008_add_position_schedule_fields"
down_revision = "007_recipe_redesign"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add schedule date columns
    op.add_column(
        'order_positions',
        sa.Column('planned_glazing_date', sa.Date, nullable=True),
    )
    op.add_column(
        'order_positions',
        sa.Column('planned_kiln_date', sa.Date, nullable=True),
    )
    op.add_column(
        'order_positions',
        sa.Column('planned_sorting_date', sa.Date, nullable=True),
    )
    op.add_column(
        'order_positions',
        sa.Column('planned_completion_date', sa.Date, nullable=True),
    )

    # Add estimated kiln FK
    op.add_column(
        'order_positions',
        sa.Column('estimated_kiln_id', UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        'fk_order_positions_estimated_kiln',
        'order_positions',
        'resources',
        ['estimated_kiln_id'],
        ['id'],
    )

    # Add schedule version counter
    op.add_column(
        'order_positions',
        sa.Column('schedule_version', sa.Integer, nullable=False, server_default='1'),
    )

    # Create indexes for schedule queries
    op.create_index(
        'ix_order_positions_planned_kiln_date',
        'order_positions',
        ['planned_kiln_date'],
    )
    op.create_index(
        'ix_order_positions_estimated_kiln_id',
        'order_positions',
        ['estimated_kiln_id'],
    )
    op.create_index(
        'ix_order_positions_planned_completion_date',
        'order_positions',
        ['planned_completion_date'],
    )


def downgrade() -> None:
    op.drop_index('ix_order_positions_planned_completion_date', 'order_positions')
    op.drop_index('ix_order_positions_estimated_kiln_id', 'order_positions')
    op.drop_index('ix_order_positions_planned_kiln_date', 'order_positions')
    op.drop_constraint('fk_order_positions_estimated_kiln', 'order_positions', type_='foreignkey')
    op.drop_column('order_positions', 'schedule_version')
    op.drop_column('order_positions', 'estimated_kiln_id')
    op.drop_column('order_positions', 'planned_completion_date')
    op.drop_column('order_positions', 'planned_sorting_date')
    op.drop_column('order_positions', 'planned_kiln_date')
    op.drop_column('order_positions', 'planned_glazing_date')
