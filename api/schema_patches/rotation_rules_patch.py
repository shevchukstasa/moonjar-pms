"""Schema patch — kiln rotation rules table.
Decision 2026-03-19: Configurable rotation rules per factory/kiln
to control glaze type sequencing and avoid contamination.
"""

ROTATION_RULES_SQL = [
    # kiln_rotation_rules — configurable glaze rotation per factory/kiln
    """CREATE TABLE IF NOT EXISTS kiln_rotation_rules (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        factory_id UUID NOT NULL REFERENCES factories(id),
        kiln_id UUID REFERENCES resources(id),
        rule_name VARCHAR(100) NOT NULL,
        glaze_sequence JSONB NOT NULL,
        cooldown_minutes INTEGER DEFAULT 0,
        incompatible_pairs JSONB DEFAULT '[]',
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE(factory_id, kiln_id, rule_name)
    )""",

    # Indexes
    "CREATE INDEX IF NOT EXISTS idx_rotation_rules_factory ON kiln_rotation_rules(factory_id)",
    "CREATE INDEX IF NOT EXISTS idx_rotation_rules_kiln ON kiln_rotation_rules(kiln_id)",
    "CREATE INDEX IF NOT EXISTS idx_rotation_rules_active ON kiln_rotation_rules(factory_id, is_active)",
]


def apply_patch(db_connection):
    """Apply kiln rotation rules schema patch. Safe to run multiple times (IF NOT EXISTS).

    Accepts a SQLAlchemy Connection from engine.begin() -- caller manages transaction.
    Do NOT call commit/rollback here.
    """
    import sqlalchemy as sa
    for sql in ROTATION_RULES_SQL:
        try:
            db_connection.execute(sa.text(sql))
        except Exception:
            pass  # table/index already exists -- ignore
