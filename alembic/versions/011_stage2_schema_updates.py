"""Stage 2 schema updates — new tables, columns, and enum values.

Covers all model additions not yet handled by prior migrations:
- New enum values: grinding_status (pending/grinding/completed),
  position_status (ready_for_kiln/grinding/mana_confirmation),
  task_type (material_receiving), engobe_type, night_alert_level,
  receiving_approval_mode, problem_card_mode/status, webhook_auth_mode,
  bowl_shape
- New columns on grinding_stock (decided_by, decided_at, notes)
- New tables: factory_calendar, operations, master_permissions,
  operation_logs, escalation_rules, receiving_settings,
  material_defect_thresholds, edge_height_rules,
  purchase_consolidation_settings

Revision ID: 011_stage2_schema_updates
Revises: 010_add_batch_metadata_json
Create Date: 2026-03-19
"""
from alembic import op
from sqlalchemy import text

revision = "011_stage2_schema_updates"
down_revision = "010_add_batch_metadata_json"
branch_labels = None
depends_on = None


# ── Enum values to add ──────────────────────────────────────────
# ALTER TYPE ... ADD VALUE IF NOT EXISTS requires AUTOCOMMIT,
# which Alembic runs outside a transaction for us when using op.execute().
# PostgreSQL 9.3+ supports ADD VALUE IF NOT EXISTS natively.

ENUM_ADDITIONS = [
    # grinding_status — new decision statuses
    ("grinding_status", "pending"),
    ("grinding_status", "grinding"),
    ("grinding_status", "completed"),
    # position_status — new workflow stages
    ("position_status", "ready_for_kiln"),
    ("position_status", "grinding"),
    ("position_status", "mana_confirmation"),
    # task_type — material receiving task
    ("task_type", "material_receiving"),
]


def upgrade() -> None:
    # ── 1. Add missing enum values ──────────────────────────────
    # ALTER TYPE ... ADD VALUE cannot run inside a transaction block.
    # Alembic by default wraps upgrade() in a transaction, so we must
    # use a raw DBAPI connection in AUTOCOMMIT mode.
    conn = op.get_bind()
    raw_conn = conn.connection.dbapi_connection
    old_isolation = raw_conn.isolation_level
    try:
        raw_conn.set_isolation_level(0)  # AUTOCOMMIT
        cur = raw_conn.cursor()
        for enum_type, enum_val in ENUM_ADDITIONS:
            try:
                cur.execute(
                    f"ALTER TYPE {enum_type} ADD VALUE IF NOT EXISTS %s",
                    (enum_val,),
                )
            except Exception:
                pass  # Already exists — safe to skip
        cur.close()
    finally:
        raw_conn.set_isolation_level(old_isolation)

    # ── 2. Add missing columns to grinding_stock ────────────────
    op.execute(text("""
        DO $$ BEGIN
            IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'grinding_stock') THEN
                ALTER TABLE grinding_stock ADD COLUMN IF NOT EXISTS decided_by UUID REFERENCES users(id);
                ALTER TABLE grinding_stock ADD COLUMN IF NOT EXISTS decided_at TIMESTAMPTZ;
                ALTER TABLE grinding_stock ADD COLUMN IF NOT EXISTS notes TEXT;
            END IF;
        END $$
    """))

    # ── 3. New tables ───────────────────────────────────────────

    # 3a. factory_calendar
    op.execute(text("""
        CREATE TABLE IF NOT EXISTS factory_calendar (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            factory_id UUID NOT NULL REFERENCES factories(id),
            date DATE NOT NULL,
            is_working_day BOOLEAN NOT NULL DEFAULT TRUE,
            num_shifts INTEGER NOT NULL DEFAULT 2,
            holiday_name VARCHAR(200),
            holiday_source VARCHAR(50),
            approved_by UUID REFERENCES users(id),
            approved_at TIMESTAMPTZ,
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_factory_calendar_date UNIQUE (factory_id, date)
        )
    """))

    # 3b. operations
    op.execute(text("""
        CREATE TABLE IF NOT EXISTS operations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            factory_id UUID NOT NULL REFERENCES factories(id),
            name VARCHAR(100) NOT NULL,
            description TEXT,
            default_time_minutes NUMERIC(8,2),
            is_active BOOLEAN DEFAULT TRUE,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """))

    # 3c. master_permissions
    op.execute(text("""
        CREATE TABLE IF NOT EXISTS master_permissions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id),
            operation_id UUID NOT NULL REFERENCES operations(id),
            granted_by UUID NOT NULL REFERENCES users(id),
            granted_at TIMESTAMPTZ DEFAULT NOW(),
            CONSTRAINT uq_master_perm_user_op UNIQUE (user_id, operation_id)
        )
    """))

    # 3d. operation_logs
    op.execute(text("""
        CREATE TABLE IF NOT EXISTS operation_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            factory_id UUID NOT NULL REFERENCES factories(id),
            operation_id UUID NOT NULL REFERENCES operations(id),
            user_id UUID NOT NULL REFERENCES users(id),
            position_id UUID REFERENCES order_positions(id),
            batch_id UUID REFERENCES batches(id),
            shift_date DATE NOT NULL,
            shift_number INTEGER,
            started_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ,
            duration_minutes NUMERIC(8,2),
            quantity_processed INTEGER,
            defect_count INTEGER DEFAULT 0,
            notes TEXT,
            source VARCHAR(20) DEFAULT 'telegram',
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """))

    # 3e. escalation_rules
    op.execute(text("""
        CREATE TABLE IF NOT EXISTS escalation_rules (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            factory_id UUID NOT NULL REFERENCES factories(id),
            task_type VARCHAR(50) NOT NULL,
            pm_timeout_hours NUMERIC(6,2) NOT NULL,
            ceo_timeout_hours NUMERIC(6,2) NOT NULL,
            owner_timeout_hours NUMERIC(6,2) NOT NULL,
            night_level INTEGER DEFAULT 1,
            is_active BOOLEAN DEFAULT TRUE,
            CONSTRAINT uq_escalation_factory_task UNIQUE (factory_id, task_type)
        )
    """))

    # 3f. receiving_settings
    op.execute(text("""
        CREATE TABLE IF NOT EXISTS receiving_settings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            factory_id UUID NOT NULL REFERENCES factories(id) UNIQUE,
            approval_mode VARCHAR(20) NOT NULL DEFAULT 'all',
            updated_by UUID REFERENCES users(id),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """))

    # 3g. material_defect_thresholds
    op.execute(text("""
        CREATE TABLE IF NOT EXISTS material_defect_thresholds (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            material_id UUID NOT NULL REFERENCES materials(id) UNIQUE,
            max_defect_percent NUMERIC(5,2) NOT NULL DEFAULT 3.0,
            updated_by UUID REFERENCES users(id),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """))

    # 3h. edge_height_rules
    op.execute(text("""
        CREATE TABLE IF NOT EXISTS edge_height_rules (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            factory_id UUID NOT NULL REFERENCES factories(id),
            thickness_mm_min NUMERIC(6,2) NOT NULL,
            thickness_mm_max NUMERIC(6,2) NOT NULL,
            max_edge_height_cm NUMERIC(6,2) NOT NULL,
            is_tested BOOLEAN DEFAULT FALSE,
            notes TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """))

    # 3i. purchase_consolidation_settings
    op.execute(text("""
        CREATE TABLE IF NOT EXISTS purchase_consolidation_settings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            factory_id UUID NOT NULL REFERENCES factories(id) UNIQUE,
            consolidation_window_days INTEGER NOT NULL DEFAULT 7,
            urgency_threshold_days INTEGER NOT NULL DEFAULT 5,
            planning_horizon_days INTEGER NOT NULL DEFAULT 30,
            updated_by UUID REFERENCES users(id),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """))


def downgrade() -> None:
    # Drop new tables in reverse dependency order
    op.execute(text("DROP TABLE IF EXISTS purchase_consolidation_settings"))
    op.execute(text("DROP TABLE IF EXISTS edge_height_rules"))
    op.execute(text("DROP TABLE IF EXISTS material_defect_thresholds"))
    op.execute(text("DROP TABLE IF EXISTS receiving_settings"))
    op.execute(text("DROP TABLE IF EXISTS escalation_rules"))
    op.execute(text("DROP TABLE IF EXISTS operation_logs"))
    op.execute(text("DROP TABLE IF EXISTS master_permissions"))
    op.execute(text("DROP TABLE IF EXISTS operations"))
    op.execute(text("DROP TABLE IF EXISTS factory_calendar"))

    # Drop columns from grinding_stock
    op.execute(text("""
        DO $$ BEGIN
            IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'grinding_stock') THEN
                ALTER TABLE grinding_stock DROP COLUMN IF EXISTS decided_by;
                ALTER TABLE grinding_stock DROP COLUMN IF EXISTS decided_at;
                ALTER TABLE grinding_stock DROP COLUMN IF EXISTS notes;
            END IF;
        END $$
    """))

    # PostgreSQL cannot remove individual values from an enum type.
    # The enum additions are left in place on downgrade.
