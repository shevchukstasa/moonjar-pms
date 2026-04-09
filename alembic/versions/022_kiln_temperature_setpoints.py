"""Kiln temperature set-points — Layer 2 of the firing model redesign.

For a given temperature group (e.g. "Low Temperature" → 1012 °C target),
every kiln with that group in its capability list has its own actual
controller set-point depending on its current equipment config. Example:
    "Low Temperature" on Kiln-A (chinese thermocouple)  → 1018 °C
    "Low Temperature" on Kiln-B (indonesian thermocouple) → 1005 °C

Ключ: (temperature_group_id, kiln_equipment_config_id). На каждую связку —
одно действующее значение set-point, плюс аудит (кто калибровал, когда,
по какой причине).

Когда оборудование печи меняется, новый kiln_equipment_config получает
новый id, и существующие записи здесь остаются привязанными к старому
config — они не применяются автоматически к новой конфигурации, пока PM
не перекалибрует.

Revision ID: 022
Revises: 021
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "kiln_temperature_setpoints",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("temperature_group_id", UUID(as_uuid=True),
                  sa.ForeignKey("firing_temperature_groups.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("kiln_equipment_config_id", UUID(as_uuid=True),
                  sa.ForeignKey("kiln_equipment_configs.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("setpoint_c", sa.Integer(), nullable=False),
        # Actual controller value in °C. May differ from group.temperature
        # (the abstract target) because of thermocouple drift, cable length,
        # controller calibration, etc.

        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("calibrated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("calibrated_by", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("needs_recalibration", sa.Boolean(), nullable=False,
                  server_default=sa.text("false")),
        # Flipped to true when the underlying kiln_equipment_config is
        # superseded (Stage 6 wiring).

        sa.Column("created_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),

        sa.UniqueConstraint(
            "temperature_group_id", "kiln_equipment_config_id",
            name="uq_setpoint_group_config",
        ),
    )

    op.create_index(
        "ix_setpoints_group",
        "kiln_temperature_setpoints",
        ["temperature_group_id"],
    )
    op.create_index(
        "ix_setpoints_config",
        "kiln_temperature_setpoints",
        ["kiln_equipment_config_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_setpoints_config", table_name="kiln_temperature_setpoints")
    op.drop_index("ix_setpoints_group", table_name="kiln_temperature_setpoints")
    op.drop_table("kiln_temperature_setpoints")
