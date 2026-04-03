"""Set capacity_sqm on kilns from working-area dimensions.

All 6 kilns were seeded with kiln_working_area_cm but capacity_sqm=NULL.
The scheduler and batch-formation code need capacity_sqm to distribute
positions across days and pick the best-fit kiln.

Formula: width_cm × depth_cm / 10000 × kiln_coefficient = capacity in m².
"""

from alembic import op
from sqlalchemy import text

revision = "016"
down_revision = "015_cleanup_test_transactions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    # Check if resources table exists
    exists = conn.execute(text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'resources')"
    )).scalar()
    if not exists:
        return

    # Set capacity_sqm = working_area(width×depth) / 10000 × coefficient
    # for all kilns that have dimensions but no capacity_sqm yet.
    conn.execute(text("""
        UPDATE resources
        SET capacity_sqm = ROUND(
            (kiln_working_area_cm->>'width_cm')::numeric
            * (kiln_working_area_cm->>'depth_cm')::numeric
            / 10000.0
            * COALESCE(kiln_coefficient, 1.0),
            3
        )
        WHERE resource_type = 'kiln'
          AND capacity_sqm IS NULL
          AND kiln_working_area_cm IS NOT NULL
          AND kiln_working_area_cm->>'width_cm' IS NOT NULL
          AND kiln_working_area_cm->>'depth_cm' IS NOT NULL
    """))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(text("""
        UPDATE resources
        SET capacity_sqm = NULL
        WHERE resource_type = 'kiln'
    """))
