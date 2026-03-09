"""Add columns that may be missing from databases created before schema was finalized.

Uses PostgreSQL ADD COLUMN IF NOT EXISTS — safe to run multiple times.
Covers all columns from migration batches 007–015 in DATABASE_SCHEMA.sql.

Revision ID: 002_missing_cols
Revises: 001_initial
Create Date: 2026-03-09
"""
from alembic import op

revision = "002_missing_cols"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # --- Migration 007: tasks.metadata_json ---
    conn.execute(
        "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS metadata_json JSONB"
    )

    # --- Migration 008: colors.is_basic ---
    conn.execute(
        "ALTER TABLE colors ADD COLUMN IF NOT EXISTS is_basic BOOLEAN NOT NULL DEFAULT FALSE"
    )

    # --- Migration 009: production_orders.shipped_at ---
    conn.execute(
        "ALTER TABLE production_orders ADD COLUMN IF NOT EXISTS shipped_at TIMESTAMPTZ"
    )

    # --- Migration 011: order_positions.quantity_sqm ---
    conn.execute(
        "ALTER TABLE order_positions ADD COLUMN IF NOT EXISTS quantity_sqm NUMERIC(10,3)"
    )

    # --- Migration 012: production_orders.sales_manager_contact ---
    conn.execute(
        "ALTER TABLE production_orders ADD COLUMN IF NOT EXISTS sales_manager_contact VARCHAR(300)"
    )

    # --- Migration 013: color_2 ---
    conn.execute(
        "ALTER TABLE production_order_items ADD COLUMN IF NOT EXISTS color_2 VARCHAR(100)"
    )
    conn.execute(
        "ALTER TABLE order_positions ADD COLUMN IF NOT EXISTS color_2 VARCHAR(200)"
    )

    # --- Migration 014: factories.served_locations ---
    conn.execute(
        "ALTER TABLE factories ADD COLUMN IF NOT EXISTS served_locations JSONB"
    )

    # --- Migration 015: firing_round, firing profiles ---
    conn.execute(
        "ALTER TABLE order_positions ADD COLUMN IF NOT EXISTS firing_round INTEGER NOT NULL DEFAULT 1"
    )
    conn.execute(
        "ALTER TABLE batches ADD COLUMN IF NOT EXISTS firing_profile_id UUID"
    )
    conn.execute(
        "ALTER TABLE batches ADD COLUMN IF NOT EXISTS target_temperature INTEGER"
    )

    # --- Table: firing_profiles (Migration 015) ---
    conn.execute("""
        CREATE TABLE IF NOT EXISTS firing_profiles (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            factory_id UUID NOT NULL REFERENCES factories(id),
            name VARCHAR(200) NOT NULL,
            description TEXT,
            max_temperature INTEGER NOT NULL,
            min_temperature INTEGER NOT NULL DEFAULT 0,
            duration_hours NUMERIC(6,2) NOT NULL DEFAULT 24,
            cooling_hours NUMERIC(6,2) NOT NULL DEFAULT 12,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            metadata_json JSONB DEFAULT '{}',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # --- Table: recipe_firing_stages (Migration 015) ---
    conn.execute("""
        CREATE TABLE IF NOT EXISTS recipe_firing_stages (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            recipe_id UUID NOT NULL,
            stage_order INTEGER NOT NULL DEFAULT 1,
            target_temperature INTEGER NOT NULL,
            hold_minutes INTEGER NOT NULL DEFAULT 60,
            ramp_rate NUMERIC(5,1),
            atmosphere VARCHAR(50),
            notes TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # --- Table: finished_goods_stock (Migration 007) ---
    conn.execute("""
        CREATE TABLE IF NOT EXISTS finished_goods_stock (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            factory_id UUID NOT NULL REFERENCES factories(id),
            position_id UUID REFERENCES order_positions(id),
            color VARCHAR(200),
            size VARCHAR(100),
            collection VARCHAR(200),
            quantity INTEGER NOT NULL DEFAULT 0,
            quantity_sqm NUMERIC(10,3),
            location VARCHAR(200),
            notes TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # --- Table: rag_embeddings (Migration 010) ---
    conn.execute("""
        CREATE TABLE IF NOT EXISTS rag_embeddings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            content_type VARCHAR(50) NOT NULL,
            content_id UUID,
            content_text TEXT NOT NULL,
            embedding BYTEA,
            metadata_json JSONB DEFAULT '{}',
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # --- FK: batches.firing_profile_id → firing_profiles(id) ---
    # Only add if not already present
    conn.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_name = 'fk_batches_firing_profile'
                  AND table_name = 'batches'
            ) THEN
                ALTER TABLE batches ADD CONSTRAINT fk_batches_firing_profile
                    FOREIGN KEY (firing_profile_id) REFERENCES firing_profiles(id);
            END IF;
        END $$
    """)

    print("INFO: Migration 002 — all missing columns/tables added (IF NOT EXISTS).")


def downgrade() -> None:
    # Not reversible — these columns/tables should stay
    pass
