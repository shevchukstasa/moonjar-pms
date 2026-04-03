"""Add zone column to kiln_typology_capacities for mixed kiln loading.

Zone-based capacity allows the scheduler to distinguish between
edge-loaded tiles (high density, vertical) and flat-loaded tiles
(lower density, horizontal).  Each typology+kiln combination can
now have separate capacity records per zone.

Values: 'edge', 'flat', 'filler', 'primary' (backward compat default).
"""

from alembic import op
from sqlalchemy import text

revision = "017"
down_revision = "016_set_kiln_capacity_sqm"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Check if table exists
    exists = conn.execute(text(
        "SELECT EXISTS ("
        "  SELECT 1 FROM information_schema.tables"
        "  WHERE table_name = 'kiln_typology_capacities'"
        ")"
    )).scalar()
    if not exists:
        return

    # Add zone column if it doesn't exist yet
    col_exists = conn.execute(text(
        "SELECT EXISTS ("
        "  SELECT 1 FROM information_schema.columns"
        "  WHERE table_name = 'kiln_typology_capacities'"
        "    AND column_name = 'zone'"
        ")"
    )).scalar()
    if not col_exists:
        conn.execute(text(
            "ALTER TABLE kiln_typology_capacities "
            "ADD COLUMN zone VARCHAR(20) NOT NULL DEFAULT 'primary'"
        ))

    # Update unique constraint: drop old (typology_id, resource_id)
    # and create new (typology_id, resource_id, zone)
    # so we can store separate capacity records per zone.
    #
    # First, check if the old constraint exists and drop it.
    old_constraint = conn.execute(text("""
        SELECT constraint_name
        FROM information_schema.table_constraints
        WHERE table_name = 'kiln_typology_capacities'
          AND constraint_type = 'UNIQUE'
        LIMIT 1
    """)).scalar()

    if old_constraint:
        # Check if it already includes 'zone'
        cols = conn.execute(text(f"""
            SELECT column_name
            FROM information_schema.constraint_column_usage
            WHERE constraint_name = '{old_constraint}'
            ORDER BY column_name
        """)).fetchall()
        col_names = [r[0] for r in cols]

        if 'zone' not in col_names:
            conn.execute(text(
                f"ALTER TABLE kiln_typology_capacities DROP CONSTRAINT {old_constraint}"
            ))
            conn.execute(text(
                "ALTER TABLE kiln_typology_capacities "
                "ADD CONSTRAINT uq_kiln_typology_capacities_typology_resource_zone "
                "UNIQUE (typology_id, resource_id, zone)"
            ))

    # Create index on zone for fast filtering
    idx_exists = conn.execute(text(
        "SELECT EXISTS ("
        "  SELECT 1 FROM pg_indexes"
        "  WHERE indexname = 'ix_kiln_typology_capacities_zone'"
        ")"
    )).scalar()
    if not idx_exists:
        conn.execute(text(
            "CREATE INDEX ix_kiln_typology_capacities_zone "
            "ON kiln_typology_capacities (zone)"
        ))


def downgrade() -> None:
    conn = op.get_bind()

    exists = conn.execute(text(
        "SELECT EXISTS ("
        "  SELECT 1 FROM information_schema.tables"
        "  WHERE table_name = 'kiln_typology_capacities'"
        ")"
    )).scalar()
    if not exists:
        return

    # Drop the zone-aware unique constraint and restore the old one
    conn.execute(text("""
        ALTER TABLE kiln_typology_capacities
        DROP CONSTRAINT IF EXISTS uq_kiln_typology_capacities_typology_resource_zone
    """))
    conn.execute(text("""
        ALTER TABLE kiln_typology_capacities
        ADD CONSTRAINT uq_kiln_typology_capacities_typology_resource
        UNIQUE (typology_id, resource_id)
    """))

    # Drop index
    conn.execute(text(
        "DROP INDEX IF EXISTS ix_kiln_typology_capacities_zone"
    ))

    # Drop column
    conn.execute(text(
        "ALTER TABLE kiln_typology_capacities DROP COLUMN IF EXISTS zone"
    ))
