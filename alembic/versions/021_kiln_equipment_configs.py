"""Kiln equipment configurations — history of installed thermocouples/controllers/cables.

Layer 1 of the firing model redesign. Each record is a snapshot of what
equipment was physically installed on a kiln during a time window. When
equipment changes (thermocouple burns out, controller replaced), the
current config gets effective_to=now and a new one is created.

Only ONE config per kiln may have effective_to=NULL at any time (enforced
by partial unique index).

Downstream layers (set-points, firing profiles, recipe capability) reference
the specific kiln_equipment_config_id so that equipment changes invalidate
the quality assertions built on top of them.

Revision ID: 021
Revises: 020
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "kiln_equipment_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("kiln_id", UUID(as_uuid=True),
                  sa.ForeignKey("resources.id", ondelete="CASCADE"),
                  nullable=False),

        # Equipment specification
        sa.Column("typology", sa.String(30), nullable=True),
        # "horizontal" | "vertical" | "raku" — free-form for now,
        # can become enum later.

        sa.Column("thermocouple_brand", sa.String(100), nullable=True),
        sa.Column("thermocouple_model", sa.String(100), nullable=True),
        sa.Column("thermocouple_length_cm", sa.Integer(), nullable=True),
        sa.Column("thermocouple_position", sa.String(100), nullable=True),
        # where on the kiln it's installed — "top-center", "side-rear", etc.

        sa.Column("controller_brand", sa.String(100), nullable=True),
        sa.Column("controller_model", sa.String(100), nullable=True),

        sa.Column("cable_brand", sa.String(100), nullable=True),
        sa.Column("cable_length_cm", sa.Integer(), nullable=True),
        sa.Column("cable_type", sa.String(100), nullable=True),

        # Free-form notes + structured extras
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("extras", JSONB(), nullable=True),
        # Escape hatch: any additional fields we don't know about yet
        # (e.g. insulation type, refractory lining rev, gas burner brand).

        # Validity window
        sa.Column("effective_from", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        # NULL = current config

        # Audit
        sa.Column("installed_by", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reason", sa.String(200), nullable=True),
        # "burned out" / "preventive replacement" / "initial setup"
        sa.Column("created_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
    )

    op.create_index(
        "ix_kiln_equipment_configs_kiln_id",
        "kiln_equipment_configs",
        ["kiln_id"],
    )

    # Only one "current" (effective_to IS NULL) config per kiln at a time.
    op.create_index(
        "uq_kiln_equipment_configs_one_current",
        "kiln_equipment_configs",
        ["kiln_id"],
        unique=True,
        postgresql_where=sa.text("effective_to IS NULL"),
    )

    # Seed: create an initial config for every existing kiln, carrying
    # over the legacy thermocouple/control_cable/control_device fields
    # from resources. This way existing kilns immediately have a "current"
    # config and nothing downstream breaks.
    op.execute("""
        INSERT INTO kiln_equipment_configs (
            kiln_id,
            thermocouple_brand,
            controller_brand,
            cable_brand,
            effective_from,
            reason
        )
        SELECT
            id,
            thermocouple,
            control_device,
            control_cable,
            created_at,
            'initial import from resources table'
        FROM resources
        WHERE resource_type = 'kiln'
    """)


def downgrade() -> None:
    op.drop_index(
        "uq_kiln_equipment_configs_one_current",
        table_name="kiln_equipment_configs",
    )
    op.drop_index(
        "ix_kiln_equipment_configs_kiln_id",
        table_name="kiln_equipment_configs",
    )
    op.drop_table("kiln_equipment_configs")
