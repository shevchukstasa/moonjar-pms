"""Extend finished_goods_stock with manager-facing metadata fields.

Adds:
  - description       — color description shown to PM/sales (e.g. "Light Blue")
  - application       — surface type used by sorting (SS, BS, S, SB, Raku, Stencil, Crawl, ...)
  - location_note     — sub-location within the factory warehouse (e.g. "Moonjar", "Mana")
  - price_per_m2      — wholesale price snapshot, hidden from default API view
  - received_at       — physical receipt date (distinct from updated_at)

Unique constraint widened to include `application` and `location_note` so that
the same color+size can co-exist as separate stock rows when stored in different
sub-locations or finished with different surface treatments.

Revision ID: 032
Revises: 031
Create Date: 2026-04-26
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = '032'
down_revision = '031'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('finished_goods_stock', sa.Column('description', sa.String(200), nullable=True))
    op.add_column('finished_goods_stock', sa.Column('application', sa.String(50), nullable=True))
    op.add_column('finished_goods_stock', sa.Column('location_note', sa.String(50), nullable=True))
    op.add_column('finished_goods_stock', sa.Column('price_per_m2', sa.Numeric(15, 2), nullable=True))
    op.add_column('finished_goods_stock', sa.Column('received_at', sa.Date(), nullable=True))

    op.drop_constraint('uq_finished_goods_stock', 'finished_goods_stock', type_='unique')
    op.create_unique_constraint(
        'uq_finished_goods_stock',
        'finished_goods_stock',
        ['factory_id', 'color', 'size', 'collection', 'product_type', 'application', 'location_note'],
    )


def downgrade() -> None:
    op.drop_constraint('uq_finished_goods_stock', 'finished_goods_stock', type_='unique')
    op.create_unique_constraint(
        'uq_finished_goods_stock',
        'finished_goods_stock',
        ['factory_id', 'color', 'size', 'collection', 'product_type'],
    )
    op.drop_column('finished_goods_stock', 'received_at')
    op.drop_column('finished_goods_stock', 'price_per_m2')
    op.drop_column('finished_goods_stock', 'location_note')
    op.drop_column('finished_goods_stock', 'application')
    op.drop_column('finished_goods_stock', 'description')
