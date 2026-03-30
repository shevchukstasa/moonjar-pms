def apply(conn):
    from sqlalchemy import text
    conn.execute(text("""
        DO $$ BEGIN
            ALTER TABLE problem_cards ADD COLUMN mode VARCHAR(20) DEFAULT 'simple';
        EXCEPTION WHEN duplicate_column THEN NULL;
        END $$;
    """))
