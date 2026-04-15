"""Backfill missing values in task_type PostgreSQL enum.

Between 009_add_missing_enums (16 values) and now, the TaskType Python
enum grew by 11 entries. Those were added to api/enums.py but never
mirrored to the database. When scheduler tried to create a Task with
one of the missing types (e.g. ``deadline_exceeded``), psycopg2 raised
``invalid input value for enum task_type`` and the transaction entered
an aborted state, cascading ``InFailedSqlTransaction`` failures through
the rest of the reschedule flow.

This migration uses ``ADD VALUE IF NOT EXISTS`` — idempotent and safe
to run on every environment.

Revision ID: 025_backfill_task_type_enum
Revises: 024
Create Date: 2026-04-15
"""
from alembic import op
from sqlalchemy import text


revision = "025_backfill_task_type_enum"
down_revision = "024"
branch_labels = None
depends_on = None


# Full current list from api/enums.py::TaskType (26 values).
TASK_TYPE_VALUES = [
    "stencil_order",
    "silk_screen_order",
    "color_matching",
    "material_order",
    "quality_check",
    "kiln_maintenance",
    "showroom_transfer",
    "photographing",
    "mana_confirmation",
    "packing_photo",
    "recipe_configuration",
    "repair_sla_alert",
    "reconciliation_alert",
    "stock_shortage",
    "stock_transfer",
    "size_resolution",
    "material_receiving",
    "glazing_board_needed",
    "consumption_measurement",
    "stone_procurement",
    "board_order_needed",
    "shelf_replacement_needed",
    "firing_profile_needed",
    "deadline_exceeded",
    "typology_speeds_needed",
    "packing_materials_needed",
]


def upgrade() -> None:
    conn = op.get_bind()
    # ALTER TYPE ADD VALUE cannot run inside a transaction block in
    # older PostgreSQL, but alembic's default migration context already
    # runs each statement on its own connection when isolation is set
    # to autocommit. We use the IF NOT EXISTS clause which makes the
    # statement idempotent on PG 9.6+.
    for val in TASK_TYPE_VALUES:
        conn.execute(text(
            f"ALTER TYPE task_type ADD VALUE IF NOT EXISTS '{val}'"
        ))


def downgrade() -> None:
    # PostgreSQL cannot remove values from an enum type.
    pass
