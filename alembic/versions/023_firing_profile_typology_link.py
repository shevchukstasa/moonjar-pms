"""Firing profile typology link — Layer 3 of the firing model redesign.

Max-temperature comes from the temperature group (Layer 1), actual
controller set-point per kiln comes from Layer 2. Layer 3 — the
ramp/hold/cool curve — depends on WHAT we're firing: tile vs
countertop vs sink, 20x20 vs 60x60, 8mm vs 20mm. All of that is
already captured by `kiln_loading_typologies` (product_types,
place_of_application, size range). So we just link firing_profiles
to a typology instead of re-encoding the same filter criteria.

When scheduling a batch, the matcher now picks:
    firing_profile WHERE typology_id == batch.typology_id
                     AND temperature_group_id == batch.temp_group_id

Existing rows stay valid: typology_id is nullable, old profiles
match via the legacy product_type/collection/thickness columns.
Over time those rows should be re-assigned to typologies.

Revision ID: 023
Revises: 022
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "firing_profiles",
        sa.Column("typology_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_firing_profiles_typology",
        "firing_profiles",
        "kiln_loading_typologies",
        ["typology_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_firing_profiles_typology",
        "firing_profiles",
        ["typology_id"],
    )
    op.create_index(
        "ix_firing_profiles_group_typology",
        "firing_profiles",
        ["temperature_group_id", "typology_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_firing_profiles_group_typology", table_name="firing_profiles")
    op.drop_index("ix_firing_profiles_typology", table_name="firing_profiles")
    op.drop_constraint("fk_firing_profiles_typology", "firing_profiles", type_="foreignkey")
    op.drop_column("firing_profiles", "typology_id")
