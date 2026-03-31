"""Cleanup test material transactions (NULL created_by) and fix material balances.

This migration:
1. Finds all material_transactions with created_by IS NULL
2. Calculates net balance correction per (material_id, factory_id):
   - receive/inventory adds to balance (removing = subtract)
   - consume/manual_write_off subtracts from balance (removing = add back)
3. Applies corrections to material_stocks
4. Deletes the test transactions

Revision ID: 015_cleanup_test_transactions
Revises: 014_add_employee_pay_period
Create Date: 2026-04-01
"""
from alembic import op
from sqlalchemy import text

revision = "015_cleanup_test_transactions"
down_revision = "014_add_employee_pay_period"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Step 1: Calculate balance corrections needed
    # For each test transaction:
    #   receive/inventory: balance was INCREASED, removing = DECREASE
    #   consume/manual_write_off: balance was DECREASED, removing = INCREASE
    # correction = SUM of reverse effects
    op.execute(text("""
        -- Temporary table with corrections
        CREATE TEMP TABLE _balance_corrections AS
        SELECT
            ms.id AS stock_id,
            SUM(
                CASE
                    WHEN mt.type IN ('receive', 'inventory') THEN -mt.quantity
                    WHEN mt.type IN ('consume', 'manual_write_off') THEN mt.quantity
                    ELSE 0
                END
            ) AS correction
        FROM material_transactions mt
        JOIN material_stocks ms
            ON ms.material_id = mt.material_id
            AND ms.factory_id = mt.factory_id
        WHERE mt.created_by IS NULL
          AND mt.type IN ('receive', 'consume', 'manual_write_off', 'inventory')
        GROUP BY ms.id
        HAVING SUM(
            CASE
                WHEN mt.type IN ('receive', 'inventory') THEN -mt.quantity
                WHEN mt.type IN ('consume', 'manual_write_off') THEN mt.quantity
                ELSE 0
            END
        ) != 0;
    """))

    # Step 2: Apply balance corrections
    op.execute(text("""
        UPDATE material_stocks ms
        SET balance = GREATEST(0, ms.balance + bc.correction)
        FROM _balance_corrections bc
        WHERE ms.id = bc.stock_id;
    """))

    # Step 3: Delete all test transactions (NULL created_by)
    op.execute(text("""
        DELETE FROM material_transactions
        WHERE created_by IS NULL;
    """))

    # Step 4: Also fix any stocks that have negative balance (safety net)
    op.execute(text("""
        UPDATE material_stocks
        SET balance = 0
        WHERE balance < 0;
    """))

    # Cleanup
    op.execute(text("DROP TABLE IF EXISTS _balance_corrections;"))


def downgrade() -> None:
    # Cannot restore deleted transactions
    pass
