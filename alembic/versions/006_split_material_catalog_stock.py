"""Split materials into shared catalog + per-factory material_stock.

Materials table becomes a shared catalog (name, type, unit, supplier).
Stock data (balance, min_balance, consumption) moves to material_stock (per factory).
MaterialTransaction gains factory_id column.
Deduplicates materials that existed per-factory into single catalog entries.

Revision ID: 006_split_material_stock
Revises: 005_kiln_constants_complete
Create Date: 2026-03-12
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

revision = "006_split_material_stock"
down_revision = "005_kiln_constants_complete"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # ── Step 1: Create material_stock table ──────────────────────────────
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS material_stock (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            material_id     UUID NOT NULL REFERENCES materials(id) ON DELETE CASCADE,
            factory_id      UUID NOT NULL REFERENCES factories(id),
            balance                 DECIMAL(12,3) NOT NULL DEFAULT 0,
            min_balance             DECIMAL(12,3) NOT NULL DEFAULT 0,
            min_balance_recommended DECIMAL(12,3),
            min_balance_auto        BOOLEAN NOT NULL DEFAULT TRUE,
            avg_daily_consumption   DECIMAL(12,3) DEFAULT 0,
            avg_monthly_consumption DECIMAL(12,3) DEFAULT 0,
            warehouse_section       VARCHAR(50) DEFAULT 'raw_materials',
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (material_id, factory_id)
        )
    """))

    # ── Step 2: Add factory_id to material_transactions ──────────────────
    conn.execute(text("""
        ALTER TABLE material_transactions
        ADD COLUMN IF NOT EXISTS factory_id UUID REFERENCES factories(id)
    """))

    # Populate factory_id from materials.factory_id
    conn.execute(text("""
        UPDATE material_transactions mt
        SET factory_id = m.factory_id
        FROM materials m
        WHERE mt.material_id = m.id AND mt.factory_id IS NULL
    """))

    # ── Step 3: Copy stock data from materials → material_stock ──────────
    conn.execute(text("""
        INSERT INTO material_stock
            (material_id, factory_id, balance, min_balance,
             min_balance_recommended, min_balance_auto,
             avg_daily_consumption, avg_monthly_consumption,
             warehouse_section, created_at, updated_at)
        SELECT id, factory_id, balance, min_balance,
               min_balance_recommended, min_balance_auto,
               avg_daily_consumption, avg_monthly_consumption,
               warehouse_section, created_at, updated_at
        FROM materials
        ON CONFLICT (material_id, factory_id) DO NOTHING
    """))

    # ── Step 4: Deduplicate materials (same name across factories) ───────
    # Build mapping: duplicate_id → canonical_id (canonical = MIN(id) per name)
    conn.execute(text("""
        CREATE TEMP TABLE _material_dedup AS
        SELECT m.id AS dup_id, canonical.canonical_id
        FROM materials m
        JOIN (
            SELECT lower(name) AS lname, MIN(id::text)::uuid AS canonical_id
            FROM materials
            GROUP BY lower(name)
        ) canonical ON lower(m.name) = canonical.lname
        WHERE m.id != canonical.canonical_id
    """))

    # Check if there are duplicates to process
    dup_count = conn.execute(text("SELECT count(*) FROM _material_dedup")).scalar()

    if dup_count > 0:
        # Delete duplicate material_stock rows (canonical already has stock for same factory)
        conn.execute(text("""
            DELETE FROM material_stock ms
            USING _material_dedup d
            WHERE ms.material_id = d.dup_id
        """))

        # Delete all recipe_materials for duplicate materials
        # (canonical materials already have correct recipe_materials links)
        conn.execute(text("""
            DELETE FROM recipe_materials rm
            USING _material_dedup d
            WHERE rm.material_id = d.dup_id
        """))

        # Re-point material_transactions to canonical material
        conn.execute(text("""
            UPDATE material_transactions mt
            SET material_id = d.canonical_id
            FROM _material_dedup d
            WHERE mt.material_id = d.dup_id
        """))

        # Delete duplicate material rows
        conn.execute(text("""
            DELETE FROM materials WHERE id IN (SELECT dup_id FROM _material_dedup)
        """))

    conn.execute(text("DROP TABLE IF EXISTS _material_dedup"))

    # ── Step 5: Drop stock columns from materials ────────────────────────
    # Drop the old unique constraint first
    conn.execute(text("""
        ALTER TABLE materials DROP CONSTRAINT IF EXISTS materials_name_factory_id_key
    """))
    # Also try the alternative constraint name
    conn.execute(text("""
        DO $$ BEGIN
            ALTER TABLE materials DROP CONSTRAINT IF EXISTS uq_materials_name_factory_id;
        EXCEPTION WHEN undefined_object THEN NULL;
        END $$
    """))

    # Drop foreign key on factory_id
    conn.execute(text("""
        ALTER TABLE materials DROP CONSTRAINT IF EXISTS materials_factory_id_fkey
    """))

    # Drop columns
    for col in [
        'factory_id', 'balance', 'min_balance', 'min_balance_recommended',
        'min_balance_auto', 'avg_daily_consumption', 'avg_monthly_consumption',
        'warehouse_section',
    ]:
        conn.execute(text(f"ALTER TABLE materials DROP COLUMN IF EXISTS {col}"))

    # ── Step 6: Add unique constraint on name only ───────────────────────
    conn.execute(text("""
        ALTER TABLE materials ADD CONSTRAINT materials_name_key UNIQUE (name)
    """))

    # ── Step 7: Create indexes ───────────────────────────────────────────
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_material_stock_material_id
        ON material_stock (material_id)
    """))
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_material_stock_factory_id
        ON material_stock (factory_id)
    """))
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_material_transactions_factory_id
        ON material_transactions (factory_id)
    """))


def downgrade() -> None:
    conn = op.get_bind()

    # Restore columns on materials
    conn.execute(text("""
        ALTER TABLE materials
        ADD COLUMN IF NOT EXISTS factory_id UUID REFERENCES factories(id),
        ADD COLUMN IF NOT EXISTS balance DECIMAL(12,3) NOT NULL DEFAULT 0,
        ADD COLUMN IF NOT EXISTS min_balance DECIMAL(12,3) NOT NULL DEFAULT 0,
        ADD COLUMN IF NOT EXISTS min_balance_recommended DECIMAL(12,3),
        ADD COLUMN IF NOT EXISTS min_balance_auto BOOLEAN NOT NULL DEFAULT TRUE,
        ADD COLUMN IF NOT EXISTS avg_daily_consumption DECIMAL(12,3) DEFAULT 0,
        ADD COLUMN IF NOT EXISTS avg_monthly_consumption DECIMAL(12,3) DEFAULT 0,
        ADD COLUMN IF NOT EXISTS warehouse_section VARCHAR(50) DEFAULT 'raw_materials'
    """))

    # Copy stock data back: for each material_stock row, create a material row per factory
    # This is a lossy reverse — we duplicate materials per factory again
    conn.execute(text("""
        UPDATE materials m
        SET factory_id = ms.factory_id,
            balance = ms.balance,
            min_balance = ms.min_balance,
            min_balance_recommended = ms.min_balance_recommended,
            min_balance_auto = ms.min_balance_auto,
            avg_daily_consumption = ms.avg_daily_consumption,
            avg_monthly_consumption = ms.avg_monthly_consumption,
            warehouse_section = ms.warehouse_section
        FROM material_stock ms
        WHERE ms.material_id = m.id
        AND ms.factory_id = (
            SELECT factory_id FROM material_stock
            WHERE material_id = m.id ORDER BY created_at LIMIT 1
        )
    """))

    # Drop unique name-only constraint, restore (name, factory_id)
    conn.execute(text("ALTER TABLE materials DROP CONSTRAINT IF EXISTS materials_name_key"))
    conn.execute(text("""
        ALTER TABLE materials
        ADD CONSTRAINT materials_name_factory_id_key UNIQUE (name, factory_id)
    """))

    # Drop material_stock table
    conn.execute(text("DROP INDEX IF EXISTS ix_material_stock_material_id"))
    conn.execute(text("DROP INDEX IF EXISTS ix_material_stock_factory_id"))
    conn.execute(text("DROP TABLE IF EXISTS material_stock"))

    # Remove factory_id from material_transactions
    conn.execute(text("DROP INDEX IF EXISTS ix_material_transactions_factory_id"))
    conn.execute(text("ALTER TABLE material_transactions DROP COLUMN IF EXISTS factory_id"))
