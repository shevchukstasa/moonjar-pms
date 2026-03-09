"""001 initial schema — stamp existing database.

If tables already exist (production), this is a no-op.
If tables don't exist (fresh database), creates all tables from models.

Revision ID: 001_initial
Revises:
Create Date: 2026-03-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all tables if they don't exist (stamp existing DBs)."""
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    existing_tables = inspector.get_table_names()

    # If 'factories' table exists, the schema is already in place.
    # Just stamp this migration as done.
    if 'factories' in existing_tables:
        print("INFO: Schema already exists — stamping migration as applied.")
        return

    # Fresh database — create all tables from metadata.
    from api.database import Base
    import api.models  # noqa: F401 — load all models
    Base.metadata.create_all(bind=bind)
    print("INFO: Created all tables from models.")


def downgrade() -> None:
    """Drop all tables (DANGEROUS — only for dev)."""
    from api.database import Base
    import api.models  # noqa: F401
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
