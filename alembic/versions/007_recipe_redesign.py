"""
007 — Recipe redesign: drop unused fields, add specific_gravity.

Remove: size, thickness_mm, place_of_application, finishing_type
Add:    specific_gravity (Numeric 5,3)
Update: unique constraint on recipes
Update: recipe_materials.unit from 'fraction' → 'g_per_100g'
"""

from alembic import op
import sqlalchemy as sa

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Drop the old composite unique constraint
    #    Constraint name from 004_schema_sync / initial: recipes_collection_color_size_application_type_place_of_ap_key
    op.execute("""
        DO $$
        BEGIN
            -- Try both possible constraint names
            BEGIN
                ALTER TABLE recipes DROP CONSTRAINT IF EXISTS recipes_collection_color_size_application_type_place_of_ap_key;
            EXCEPTION WHEN undefined_object THEN NULL;
            END;
            BEGIN
                ALTER TABLE recipes DROP CONSTRAINT IF EXISTS recipes_collection_color_size_application_type_place_of_appli;
            EXCEPTION WHEN undefined_object THEN NULL;
            END;
        END $$;
    """)

    # Also try to drop by scanning pg_constraint
    op.execute("""
        DO $$
        DECLARE
            cname text;
        BEGIN
            SELECT conname INTO cname
            FROM pg_constraint
            WHERE conrelid = 'recipes'::regclass
              AND contype = 'u'
              AND array_length(conkey, 1) > 3;
            IF cname IS NOT NULL THEN
                EXECUTE 'ALTER TABLE recipes DROP CONSTRAINT ' || quote_ident(cname);
            END IF;
        END $$;
    """)

    # 2. Add specific_gravity column
    op.add_column('recipes', sa.Column('specific_gravity', sa.Numeric(5, 3), nullable=True))

    # 3. Drop removed columns (if they exist)
    for col in ['size', 'thickness_mm', 'place_of_application', 'finishing_type']:
        op.execute(f"""
            DO $$
            BEGIN
                ALTER TABLE recipes DROP COLUMN IF EXISTS {col};
            EXCEPTION WHEN undefined_column THEN NULL;
            END $$;
        """)

    # 4. Create new unique constraint (without the dropped fields)
    op.create_unique_constraint(
        'uq_recipes_collection_color_apptype',
        'recipes',
        ['collection', 'color', 'application_type'],
    )

    # 5. Update recipe_materials.unit for existing seed data
    op.execute("""
        UPDATE recipe_materials
        SET unit = 'g_per_100g'
        WHERE unit = 'fraction'
    """)


def downgrade() -> None:
    # Reverse: drop new constraint, re-add columns, restore old constraint
    op.drop_constraint('uq_recipes_collection_color_apptype', 'recipes', type_='unique')

    op.add_column('recipes', sa.Column('size', sa.String(50)))
    op.add_column('recipes', sa.Column('thickness_mm', sa.Numeric(5, 1), nullable=False, server_default='11.0'))
    op.add_column('recipes', sa.Column('place_of_application', sa.String(50)))
    op.add_column('recipes', sa.Column('finishing_type', sa.String(100)))

    op.drop_column('recipes', 'specific_gravity')

    op.execute("""
        UPDATE recipe_materials
        SET unit = 'fraction'
        WHERE unit = 'g_per_100g'
    """)
