"""Add material_tracking_disabled flag to production_orders (Express mode).

See docs/BUSINESS_LOGIC_FULL.md §2.6 — owner-level override that lets a single
order proceed without material reservation/consumption (custom one-off stones,
trial batches, warranty repair, customer-supplied raw material).

Revision ID: 030
Revises: 029
Create Date: 2026-04-25
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
import sqlalchemy.dialects.postgresql as pg


revision = '030'
down_revision = '029'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'production_orders',
        sa.Column(
            'material_tracking_disabled',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
        ),
    )
    op.add_column(
        'production_orders',
        sa.Column('material_tracking_disabled_reason', sa.Text(), nullable=True),
    )
    op.add_column(
        'production_orders',
        sa.Column(
            'material_tracking_disabled_at',
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        'production_orders',
        sa.Column(
            'material_tracking_disabled_by',
            pg.UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='SET NULL'),
            nullable=True,
        ),
    )

    op.execute("""
        CREATE INDEX ix_production_orders_material_tracking_disabled
        ON production_orders (material_tracking_disabled)
        WHERE material_tracking_disabled = true
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_production_orders_material_tracking_disabled")
    op.drop_column('production_orders', 'material_tracking_disabled_by')
    op.drop_column('production_orders', 'material_tracking_disabled_at')
    op.drop_column('production_orders', 'material_tracking_disabled_reason')
    op.drop_column('production_orders', 'material_tracking_disabled')
