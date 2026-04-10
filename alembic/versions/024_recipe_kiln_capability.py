"""Recipe × kiln capability matrix — Layer 4 of the firing model redesign.

Which recipes (colors/glazes) can actually be fired on which kiln?

Example: "Lagoon Spark" can only be fired on "New Kiln" with its
current equipment — on other kilns we don't even know the correct
temperature. The scheduler MUST route Lagoon Spark orders to New
Kiln and refuse to put them anywhere else.

This table answers two questions:
    1. Can this recipe physically be fired on this kiln? (is_qualified)
    2. If yes, what's our historical success/quality there?
       (quality_rating, success_count, failure_count)

When a kiln's equipment changes (Layer 1 — new thermocouple, new
cable), all capabilities for that kiln get `needs_requalification = true`
so production knows to run a test batch before trusting it.

Revision ID: 024
Revises: 023
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recipe_kiln_capabilities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("recipe_id", UUID(as_uuid=True),
                  sa.ForeignKey("recipes.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("kiln_id", UUID(as_uuid=True),
                  sa.ForeignKey("resources.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("is_qualified", sa.Boolean, nullable=False,
                  server_default=sa.text("false")),
        sa.Column("quality_rating", sa.Integer, nullable=True),  # 1-5
        sa.Column("success_count", sa.Integer, nullable=False,
                  server_default=sa.text("0")),
        sa.Column("failure_count", sa.Integer, nullable=False,
                  server_default=sa.text("0")),
        sa.Column("last_fired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_qualified_equipment_config_id", UUID(as_uuid=True),
                  sa.ForeignKey("kiln_equipment_configs.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("needs_requalification", sa.Boolean, nullable=False,
                  server_default=sa.text("false")),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("qualified_by", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.UniqueConstraint("recipe_id", "kiln_id", name="uq_recipe_kiln_capability"),
        sa.CheckConstraint(
            "quality_rating IS NULL OR (quality_rating BETWEEN 1 AND 5)",
            name="ck_rkc_quality_rating_range",
        ),
    )
    op.create_index("ix_rkc_recipe", "recipe_kiln_capabilities", ["recipe_id"])
    op.create_index("ix_rkc_kiln", "recipe_kiln_capabilities", ["kiln_id"])
    op.create_index(
        "ix_rkc_qualified",
        "recipe_kiln_capabilities",
        ["recipe_id", "is_qualified"],
    )


def downgrade() -> None:
    op.drop_index("ix_rkc_qualified", table_name="recipe_kiln_capabilities")
    op.drop_index("ix_rkc_kiln", table_name="recipe_kiln_capabilities")
    op.drop_index("ix_rkc_recipe", table_name="recipe_kiln_capabilities")
    op.drop_table("recipe_kiln_capabilities")
