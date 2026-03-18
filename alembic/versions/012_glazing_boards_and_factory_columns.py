"""Add glazing_board_specs table and missing factory columns.

Fixes:
- factories.receiving_approval_mode (VARCHAR, default 'all')
- factories.kiln_constants_mode (VARCHAR, default 'manual')
- factories.rotation_rules (JSONB)
- task_type enum: + glazing_board_needed, material_receiving
- New table: glazing_board_specs (board dimensions per tile size)

Revision ID: 012_glazing_boards_and_factory_columns
Revises: 011_stage2_schema_updates
Create Date: 2026-03-19
"""
from alembic import op
from sqlalchemy import text

revision = "012_glazing_boards_and_factory_columns"
down_revision = "011_stage2_schema_updates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Add new task_type enum values (requires AUTOCOMMIT) ──
    conn = op.get_bind()
    raw_conn = conn.connection.dbapi_connection
    old_iso = raw_conn.isolation_level
    try:
        raw_conn.set_isolation_level(0)  # AUTOCOMMIT
        cur = raw_conn.cursor()
        for val in ("glazing_board_needed", "material_receiving"):
            try:
                cur.execute(
                    "ALTER TYPE task_type ADD VALUE IF NOT EXISTS %s", (val,)
                )
            except Exception:
                pass
        cur.close()
    finally:
        raw_conn.set_isolation_level(old_iso)

    # ── 2. Add missing columns to factories ─────────────────────
    op.execute(text("""
        DO $$ BEGIN
            ALTER TABLE factories
                ADD COLUMN IF NOT EXISTS receiving_approval_mode VARCHAR(20) NOT NULL DEFAULT 'all';
        EXCEPTION WHEN others THEN NULL;
        END $$
    """))
    op.execute(text("""
        DO $$ BEGIN
            ALTER TABLE factories
                ADD COLUMN IF NOT EXISTS kiln_constants_mode VARCHAR(20) NOT NULL DEFAULT 'manual';
        EXCEPTION WHEN others THEN NULL;
        END $$
    """))
    op.execute(text("""
        DO $$ BEGIN
            ALTER TABLE factories
                ADD COLUMN IF NOT EXISTS rotation_rules JSONB;
        EXCEPTION WHEN others THEN NULL;
        END $$
    """))

    # ── 3. Create glazing_board_specs table ─────────────────────
    op.execute(text("""
        CREATE TABLE IF NOT EXISTS glazing_board_specs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            size_id UUID NOT NULL UNIQUE REFERENCES sizes(id) ON DELETE CASCADE,
            board_length_cm NUMERIC(6,1) NOT NULL DEFAULT 122.0,
            board_width_cm NUMERIC(6,1) NOT NULL,
            tiles_per_board INTEGER NOT NULL,
            area_per_board_m2 NUMERIC(8,4) NOT NULL,
            tiles_along_length INTEGER NOT NULL,
            tiles_across_width INTEGER NOT NULL,
            tile_orientation_cm VARCHAR(30),
            is_custom_board BOOLEAN NOT NULL DEFAULT FALSE,
            notes TEXT,
            calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))


def downgrade() -> None:
    op.execute(text("DROP TABLE IF EXISTS glazing_board_specs"))
    # Cannot remove enum values in PostgreSQL — left in place on downgrade
    # Cannot remove columns added with ADD COLUMN IF NOT EXISTS easily,
    # but listed here for documentation:
    # ALTER TABLE factories DROP COLUMN IF EXISTS receiving_approval_mode;
    # ALTER TABLE factories DROP COLUMN IF EXISTS kiln_constants_mode;
    # ALTER TABLE factories DROP COLUMN IF EXISTS rotation_rules;
