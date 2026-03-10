#!/usr/bin/env python3
"""
diff_migration.py — Compare models.py against migration 003 state and suggest migration 004.

Usage:
    python3 scripts/diff_migration.py               # live DB mode (requires running DB)
    python3 scripts/diff_migration.py --static       # static mode: parse migrations, no DB needed
    python3 scripts/diff_migration.py --write        # also write alembic/versions/004_schema_sync.py
    python3 scripts/diff_migration.py --db URL       # override DATABASE_URL
    python3 scripts/diff_migration.py --json         # machine-readable output

Modes:
    Live DB mode (default):
        Connects to DATABASE_URL, introspects real schema, finds exact missing columns.
        Requires: docker compose up -d db  OR  --db "postgresql://..."

    Static mode (--static):
        No DB needed. Parses migration files + api/main.py _add_columns to build
        the "migration 003 schema state", then diffs against current models.py.
        Less precise (assumes migration 001 created all initial tables).
"""

import sys
import os
import argparse
import json
from pathlib import Path

# --- Path setup ---
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# --- Load .env ---
def _load_env():
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

_load_env()


# ════════════════════════════════════════════════════════════════════
# 1. Load models metadata
# ════════════════════════════════════════════════════════════════════

def load_metadata():
    """Import api.models and return Base.metadata."""
    # Must set DATABASE_URL before importing (api.database reads it at import time)
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        print("ERROR: DATABASE_URL not set. Add it to .env or pass --db URL.", file=sys.stderr)
        sys.exit(1)

    import api.models  # noqa — loads all model classes into Base
    from api.database import Base
    return Base.metadata


# ════════════════════════════════════════════════════════════════════
# 2. Introspect the live DB
# ════════════════════════════════════════════════════════════════════

def introspect_db(db_url: str):
    """Return {table_name: {col_name: col_info}} from the live database."""
    from sqlalchemy import create_engine, inspect as sa_inspect

    engine = create_engine(db_url)
    inspector = sa_inspect(engine)

    db_tables = {}
    for table_name in inspector.get_table_names():
        cols = {}
        for col in inspector.get_columns(table_name):
            cols[col["name"]] = col  # keep full info
        db_tables[table_name] = cols

    engine.dispose()
    return db_tables


# ════════════════════════════════════════════════════════════════════
# 3. SQLAlchemy type → PostgreSQL DDL string
# ════════════════════════════════════════════════════════════════════

def _col_to_ddl(col) -> str:
    """Convert a SQLAlchemy Column to a PostgreSQL DDL fragment."""
    import sqlalchemy as sa
    from sqlalchemy.dialects.postgresql import UUID, JSONB, INET, ARRAY, TSVECTOR
    from sqlalchemy.sql.sqltypes import NullType

    t = col.type

    # Resolve type string
    if isinstance(t, (sa.String, sa.VARCHAR)):
        length = getattr(t, "length", None)
        type_str = f"VARCHAR({length})" if length else "TEXT"
    elif isinstance(t, sa.Text):
        type_str = "TEXT"
    elif isinstance(t, sa.Integer):
        type_str = "INTEGER"
    elif isinstance(t, sa.BigInteger):
        type_str = "BIGINT"
    elif isinstance(t, sa.SmallInteger):
        type_str = "SMALLINT"
    elif isinstance(t, sa.Boolean):
        type_str = "BOOLEAN"
    elif isinstance(t, sa.Numeric):
        p = getattr(t, "precision", None)
        s = getattr(t, "scale", None)
        type_str = f"NUMERIC({p},{s})" if p is not None else "NUMERIC"
    elif isinstance(t, sa.Float):
        type_str = "FLOAT"
    elif isinstance(t, sa.DateTime):
        tz = getattr(t, "timezone", False)
        type_str = "TIMESTAMPTZ" if tz else "TIMESTAMP"
    elif isinstance(t, sa.Date):
        type_str = "DATE"
    elif isinstance(t, sa.Time):
        type_str = "TIME"
    elif isinstance(t, UUID):
        type_str = "UUID"
    elif isinstance(t, JSONB):
        type_str = "JSONB"
    elif isinstance(t, INET):
        type_str = "INET"
    elif isinstance(t, TSVECTOR):
        type_str = "TSVECTOR"
    elif isinstance(t, sa.Enum):
        # Use the enum name or TEXT fallback
        enum_name = getattr(t, "name", None) or getattr(t, "enum_class", None)
        if enum_name and hasattr(enum_name, "__name__"):
            enum_name = enum_name.__name__.lower()
        type_str = str(enum_name) if enum_name else "TEXT"
    elif isinstance(t, ARRAY):
        item_type = _resolve_item_type(t.item_type)
        type_str = f"{item_type}[]"
    elif isinstance(t, NullType):
        type_str = "TEXT"  # fallback
    else:
        type_str = str(t).upper()

    # Nullable / NOT NULL
    nullable_str = "" if col.nullable else " NOT NULL"

    # Default
    default_str = ""
    if col.server_default is not None:
        raw = str(col.server_default.arg) if hasattr(col.server_default, "arg") else str(col.server_default)
        default_str = f" DEFAULT {raw}"
    elif col.default is not None and hasattr(col.default, "arg"):
        arg = col.default.arg
        if callable(arg):
            pass  # Python-side default, skip
        elif isinstance(arg, bool):
            default_str = f" DEFAULT {'TRUE' if arg else 'FALSE'}"
        elif isinstance(arg, (int, float)):
            default_str = f" DEFAULT {arg}"
        elif isinstance(arg, str):
            default_str = f" DEFAULT '{arg}'"

    return f"{type_str}{nullable_str}{default_str}"


def _resolve_item_type(t) -> str:
    import sqlalchemy as sa
    if isinstance(t, sa.String):
        return f"VARCHAR({t.length})" if t.length else "TEXT"
    if isinstance(t, sa.Integer):
        return "INTEGER"
    return "TEXT"


# ════════════════════════════════════════════════════════════════════
# 4. Diff engine
# ════════════════════════════════════════════════════════════════════

SKIP_TABLES = {
    # Alembic internal, spatial extensions, etc.
    "alembic_version", "spatial_ref_sys",
}


def diff(metadata, db_tables: dict) -> dict:
    """
    Returns:
        {
          "missing_tables": [table_name, ...],
          "missing_columns": [(table, col_name, ddl), ...],
          "new_in_db_only": [(table, col_name), ...],   # informational
        }
    """
    missing_tables = []
    missing_columns = []
    extra_in_db = []

    for table in metadata.sorted_tables:
        tname = table.name
        if tname in SKIP_TABLES:
            continue

        if tname not in db_tables:
            missing_tables.append(tname)
            continue

        db_cols = db_tables[tname]
        for col in table.columns:
            if col.name not in db_cols:
                ddl = _col_to_ddl(col)
                missing_columns.append((tname, col.name, ddl))

    # Check for tables in DB not in models (informational)
    model_table_names = {t.name for t in metadata.sorted_tables}
    for tname in db_tables:
        if tname in SKIP_TABLES or tname.startswith("alembic"):
            continue
        if tname not in model_table_names:
            extra_in_db.append(tname)

    return {
        "missing_tables": missing_tables,
        "missing_columns": missing_columns,
        "extra_in_db": extra_in_db,
    }


# ════════════════════════════════════════════════════════════════════
# 5. Generate migration 004 code
# ════════════════════════════════════════════════════════════════════

MIGRATION_TEMPLATE = '''\
"""Sync schema to models.py state after migration 003.

Auto-generated by scripts/diff_migration.py — review before applying.
Safe to run multiple times (ADD COLUMN IF NOT EXISTS, CREATE TABLE IF NOT EXISTS).

Revision ID: 004_schema_sync
Revises: 003_seed_data
Create Date: {date}
"""
from alembic import op
from sqlalchemy import text

revision = "004_schema_sync"
down_revision = "003_seed_data"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
{body}
    print("INFO: Migration 004 — schema sync complete.")


def downgrade() -> None:
    pass  # columns are additive — not reversing
'''


def _safe_col_block(table: str, col: str, ddl: str, indent: str = "    ") -> str:
    return (
        f"{indent}conn.execute(text(\"\"\"\n"
        f"{indent}    DO $$ BEGIN\n"
        f"{indent}        IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}') THEN\n"
        f"{indent}            ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {ddl};\n"
        f"{indent}        END IF;\n"
        f"{indent}    END $$\n"
        f"{indent}\"\"\"))\n"
    )


def _create_table_block(metadata, table_name: str, indent: str = "    ") -> str:
    table = metadata.tables[table_name]
    col_defs = []
    for col in table.columns:
        if col.primary_key:
            col_defs.append(f"        {col.name} UUID PRIMARY KEY DEFAULT gen_random_uuid()")
        else:
            ddl = _col_to_ddl(col)
            col_defs.append(f"        {col.name} {ddl}")
    cols_str = ",\n".join(col_defs)
    return (
        f"{indent}conn.execute(text(\"\"\"\n"
        f"{indent}    CREATE TABLE IF NOT EXISTS {table_name} (\n"
        f"{cols_str}\n"
        f"{indent}    )\n"
        f"{indent}\"\"\"))\n"
    )


def generate_migration(diff_result: dict, metadata) -> str:
    from datetime import date as dt_date
    today = dt_date.today().isoformat()

    body_lines = []

    # 1. Missing tables (live mode)
    if diff_result.get("missing_tables"):
        body_lines.append("    # ── New tables ──────────────────────────────────────")
        for tname in diff_result["missing_tables"]:
            if tname in metadata.tables:
                body_lines.append(_create_table_block(metadata, tname))
            else:
                body_lines.append(f"    # WARNING: table '{tname}' not found in metadata")

    # 2. Missing columns (live mode) grouped by table
    if diff_result.get("missing_columns"):
        body_lines.append("    # ── Missing columns ─────────────────────────────────")
        current_table = None
        for tname, col, ddl in sorted(diff_result["missing_columns"], key=lambda x: x[0]):
            if tname != current_table:
                body_lines.append(f"    # --- {tname} ---")
                current_table = tname
            body_lines.append(_safe_col_block(tname, col, ddl))

    # 3. Runtime-only columns (static mode) — formalize _add_columns into migration
    if diff_result.get("runtime_only"):
        body_lines.append("    # ── Formalizing runtime-only columns (from main.py _add_columns) ─")
        current_table = None
        for tname, col, ddl in sorted(diff_result["runtime_only"], key=lambda x: x[0]):
            if tname != current_table:
                body_lines.append(f"    # --- {tname} ---")
                current_table = tname
            # ddl from _extract_add_columns_ddl starts with col name — strip it
            # e.g. "firing_profile_id UUID" → type_part = "UUID"
            parts = ddl.split(None, 1)
            type_part = parts[1] if len(parts) > 1 else ddl
            body_lines.append(_safe_col_block(tname, col, type_part))

    if not body_lines:
        body_lines.append("    pass  # No schema changes needed — DB matches models.py")

    body = "\n".join(body_lines)
    return MIGRATION_TEMPLATE.format(date=today, body=body)


# ════════════════════════════════════════════════════════════════════
# 6. Pretty-print report
# ════════════════════════════════════════════════════════════════════

RESET  = "\033[0m"
RED    = "\033[31m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
CYAN   = "\033[36m"
BOLD   = "\033[1m"
DIM    = "\033[2m"


def print_report(diff_result: dict):
    mt = diff_result["missing_tables"]
    mc = diff_result["missing_columns"]
    ex = diff_result["extra_in_db"]

    print(f"\n{BOLD}{'═'*60}{RESET}")
    print(f"{BOLD}  diff_migration — Models vs Live DB{RESET}")
    print(f"{BOLD}{'═'*60}{RESET}\n")

    if not mt and not mc:
        print(f"{GREEN}{BOLD}  ✓ DB is in sync with models.py — nothing to migrate{RESET}\n")
    else:
        # Missing tables
        if mt:
            print(f"{RED}{BOLD}  MISSING TABLES ({len(mt)}):{RESET}")
            for t in mt:
                print(f"    {RED}+ CREATE TABLE {t}{RESET}")
            print()

        # Missing columns grouped by table
        if mc:
            print(f"{YELLOW}{BOLD}  MISSING COLUMNS ({len(mc)}):{RESET}")
            current = None
            for tname, col, ddl in sorted(mc, key=lambda x: x[0]):
                if tname != current:
                    print(f"\n    {CYAN}{tname}{RESET}")
                    current = tname
                print(f"      {YELLOW}+ {col}  {DIM}{ddl}{RESET}")
            print()

    # Extra tables (informational)
    if ex:
        print(f"{DIM}  Tables in DB not in models (informational):{RESET}")
        for t in sorted(ex):
            print(f"    {DIM}? {t}{RESET}")
        print()

    # Summary
    issues = len(mt) + len(mc)
    color = RED if issues > 0 else GREEN
    print(f"{color}{BOLD}  SUMMARY: {len(mt)} missing tables | {len(mc)} missing columns{RESET}")
    if issues > 0:
        print(f"{YELLOW}  → Run with --write to generate alembic/versions/004_schema_sync.py{RESET}")
    print()


# ════════════════════════════════════════════════════════════════════
# 6b. Static mode — parse migrations, no DB needed
# ════════════════════════════════════════════════════════════════════

import re as _re


def _parse_migration_add_columns(migration_path: Path) -> set:
    """Extract (table, col_name) from ALTER TABLE ... ADD COLUMN IF NOT EXISTS."""
    src = migration_path.read_text()
    found = set()
    # Pattern: ALTER TABLE <table> ADD COLUMN IF NOT EXISTS <col>
    for m in _re.finditer(
        r"ALTER\s+TABLE\s+(\w+)\s+ADD\s+COLUMN\s+IF\s+NOT\s+EXISTS\s+(\w+)",
        src, _re.IGNORECASE
    ):
        found.add((m.group(1).lower(), m.group(2).lower()))
    # Also catch plain ALTER TABLE ... ADD COLUMN <col>  (no IF NOT EXISTS)
    for m in _re.finditer(
        r"ALTER\s+TABLE\s+(\w+)\s+ADD\s+COLUMN\s+(?!IF)(\w+)",
        src, _re.IGNORECASE
    ):
        found.add((m.group(1).lower(), m.group(2).lower()))
    return found


def _parse_main_add_columns(main_path: Path) -> set:
    """Extract (table, col_name) from _add_columns list in main.py."""
    src = main_path.read_text()
    found = set()
    # Match tuples: ("table_name", "col_name TYPE ..."),
    for m in _re.finditer(r'\(\s*["\'](\w+)["\']\s*,\s*["\'](\w+)\s+[^"\']+["\']\s*\)', src):
        found.add((m.group(1).lower(), m.group(2).lower()))
    return found


def _parse_migration_create_tables(migration_path: Path) -> set:
    """Extract table names from CREATE TABLE IF NOT EXISTS statements."""
    src = migration_path.read_text()
    found = set()
    for m in _re.finditer(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)", src, _re.IGNORECASE):
        found.add(m.group(1).lower())
    return found


def _extract_add_columns_ddl(main_path: Path) -> list:
    """
    Parse only the add_cols = [...] list inside _add_columns() in main.py.
    Returns [(table, col_name, full_ddl), ...].
    """
    src = main_path.read_text()

    # Find the add_cols = [...] block (between the list brackets)
    start = src.find("add_cols = [")
    if start == -1:
        return []
    # Find matching closing bracket
    bracket_start = src.index("[", start)
    depth = 0
    end = bracket_start
    for i, ch in enumerate(src[bracket_start:], start=bracket_start):
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                end = i
                break

    block = src[bracket_start:end + 1]

    results = []
    # Match tuples: ("table_name", "COL_NAME TYPE ..."),
    for m in _re.finditer(
        r'\(\s*["\'](\w+)["\']\s*,\s*["\'](\w+(?:\s+[^"\']+)?)["\']\s*\)',
        block
    ):
        table = m.group(1).strip()
        col_ddl = m.group(2).strip()
        # Must look like a DDL definition: first word is col name, second is a SQL type keyword
        parts = col_ddl.split()
        if len(parts) < 2:
            continue
        sql_types = {"boolean", "integer", "bigint", "varchar", "text", "uuid",
                     "jsonb", "timestamptz", "timestamp", "numeric", "inet", "smallint"}
        if parts[1].lower().split("(")[0] not in sql_types:
            continue
        col_name = parts[0]
        results.append((table, col_name, col_ddl))
    return results


def static_diff(metadata, root: Path) -> dict:
    """
    Precise static diff without a live DB:

    Key insight:
      - migration 001: creates all tables via Base.metadata.create_all()
      - migration 002: adds specific columns (ADD COLUMN IF NOT EXISTS)
      - main.py _add_columns: runtime additions for columns missing from migrations
        These reach the DB every startup but are NOT in formal Alembic migrations.

    Goal: find which _add_columns are NOT covered by migration 002,
    and which models.py columns exist in NEITHER — these need migration 004.

    For tables: check if models.py has tables not mentioned in any migration.
    """
    versions_dir = root / "alembic" / "versions"
    main_py = root / "api" / "main.py"

    # --- Step 1: columns covered by formal migrations (002) ---
    migration_cols: set = set()  # (table, col)
    for mig_file in sorted(versions_dir.glob("0*.py")):
        migration_cols |= _parse_migration_add_columns(mig_file)

    # --- Step 2: columns covered by main.py _add_columns (runtime) ---
    main_col_items = _extract_add_columns_ddl(main_py) if main_py.exists() else []
    main_add_set = {(t.lower(), c.lower()) for t, c, _ in main_col_items}

    # --- Step 3: tables created in migrations 002+ ---
    explicitly_created: set = set()
    for mig_file in sorted(versions_dir.glob("0*.py")):
        explicitly_created |= _parse_migration_create_tables(mig_file)
    if main_py.exists():
        for t in _parse_migration_create_tables(main_py):
            explicitly_created.add(t)

    # --- Step 4: runtime columns not in formal migrations ---
    # These are "OK at runtime" but should be in migration 004 for clean Alembic history
    runtime_only = []  # (table, col, ddl) — in _add_columns but not in 002
    for table, col, ddl in main_col_items:
        pair = (table.lower(), col.lower())
        if pair not in migration_cols:
            runtime_only.append((table, col, ddl))

    # --- Step 5: new tables since migration 001 ---
    # Migration 001 runs Base.metadata.create_all() — all tables in models.py at that
    # time were created. Tables added to models.py AFTER 001 need their own CREATE TABLE.
    # We detect these by checking migration 002+ for CREATE TABLE statements.
    # Tables in models.py that appear in explicitly_created (migration 002+) are "new tables
    # added after 001 with their own migration" → OK.
    # But we can't know what was in models.py at migration 001 time.
    #
    # Practical heuristic: tables in models.py NOT mentioned in migration 002+ CREATE TABLE
    # but KNOWN to be added after a certain point can be flagged. Since we lack git history,
    # we skip this check — the live DB mode covers it precisely.
    missing_tables = []  # static mode can't reliably detect new tables

    return {
        "mode": "static",
        "missing_tables": missing_tables,
        "missing_columns": [],  # can't reliably detect without DB
        "runtime_only": runtime_only,   # in _add_columns but not in formal migration
        "extra_in_db": [],
        "note": (
            "Static mode: shows (1) runtime-only columns that need formal migration, "
            "(2) potentially new tables. For exact column diff use live DB mode."
        ),
    }


def print_static_report(result: dict):
    ro = result.get("runtime_only", [])
    mt = result.get("missing_tables", [])

    print(f"\n{BOLD}{'═'*60}{RESET}")
    print(f"{BOLD}  diff_migration — STATIC MODE (no DB required){RESET}")
    print(f"{BOLD}{'═'*60}{RESET}")
    print(f"{DIM}  {result['note']}{RESET}\n")

    # Runtime-only columns → main.py _add_columns but NOT in any migration
    if ro:
        print(f"{YELLOW}{BOLD}  Runtime-only columns ({len(ro)}) — need formal migration 004:{RESET}")
        print(f"  {DIM}(Present in main.py _add_columns but not in Alembic migrations 001–003){RESET}")
        current = None
        for tname, col, ddl in sorted(ro, key=lambda x: x[0]):
            if tname != current:
                print(f"\n    {CYAN}{tname}{RESET}")
                current = tname
            print(f"      {YELLOW}+ {col}  {DIM}{ddl}{RESET}")
        print()
    else:
        print(f"{GREEN}  ✓ All _add_columns are covered by formal migrations{RESET}\n")

    # Possibly new tables
    if mt:
        print(f"{RED}{BOLD}  Possibly new tables ({len(mt)}) — may need migration:{RESET}")
        print(f"  {DIM}(Not mentioned in any migration file — verify manually){RESET}")
        for t in sorted(mt):
            print(f"    {RED}? {t}{RESET}")
        print()

    total = len(ro) + len(mt)
    color = YELLOW if total > 0 else GREEN
    print(f"{color}{BOLD}  SUMMARY: {len(ro)} runtime-only columns | {len(mt)} possibly new tables{RESET}")
    if total > 0:
        print(f"{YELLOW}  → Run with --write to generate alembic/versions/004_schema_sync.py{RESET}")
    print(f"\n{DIM}  For exact column diff: docker compose up -d db && python3 scripts/diff_migration.py{RESET}")
    print(f"{DIM}  Or: python3 scripts/diff_migration.py --db 'postgresql://user:pass@host/db'{RESET}\n")


# ════════════════════════════════════════════════════════════════════
# 7. Main
# ════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Compare models.py against migration 003 and suggest migration 004."
    )
    parser.add_argument("--db", metavar="URL", help="Override DATABASE_URL")
    parser.add_argument("--static", action="store_true",
                        help="Static mode: parse migration files only, no DB connection needed")
    parser.add_argument("--write", action="store_true",
                        help="Write proposed migration to alembic/versions/004_schema_sync.py")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="Output machine-readable JSON")
    parser.add_argument("--migration-only", action="store_true",
                        help="Print only the migration code (live mode only)")
    args = parser.parse_args()

    # Load metadata (always needed)
    print(f"{DIM}Loading models...{RESET}", end=" ", flush=True)
    try:
        metadata = load_metadata()
        print(f"OK ({len(metadata.tables)} tables){RESET}")
    except Exception as e:
        print(f"\nERROR: Could not import api.models: {e}", file=sys.stderr)
        sys.exit(1)

    # ── Static mode (no DB) ──────────────────────────────────────────
    if args.static:
        result = static_diff(metadata, ROOT)

        if args.as_json:
            out = {k: v for k, v in result.items() if k != "mode"}
            print(json.dumps(out, indent=2))
            sys.exit(0)

        print_static_report(result)

        if (result.get("runtime_only") or result.get("missing_tables")) and args.write:
            migration_code = generate_migration(result, metadata)
            out_path = ROOT / "alembic" / "versions" / "004_schema_sync.py"
            if out_path.exists():
                print(f"{YELLOW}WARNING: {out_path} already exists — overwriting.{RESET}")
            out_path.write_text(migration_code)
            print(f"{GREEN}✓ Written: {out_path}{RESET}")

        return

    # ── Live DB mode ─────────────────────────────────────────────────
    db_url = args.db or os.environ.get("DATABASE_URL", "")
    if not db_url:
        print("ERROR: DATABASE_URL not set. Add to .env or pass --db URL.", file=sys.stderr)
        sys.exit(1)

    print(f"{DIM}Connecting to DB...{RESET}", end=" ", flush=True)
    try:
        db_tables = introspect_db(db_url)
        print(f"OK ({len(db_tables)} tables in DB){RESET}")
    except Exception as e:
        print(f"\n{RED}ERROR: Could not connect to DB:{RESET}", file=sys.stderr)
        print(f"  {e}", file=sys.stderr)
        print(file=sys.stderr)
        print(f"{YELLOW}Options to fix:{RESET}", file=sys.stderr)
        print(f"  1. Start local DB:   docker compose up -d db", file=sys.stderr)
        print(f"  2. Use Railway URL:  python3 scripts/diff_migration.py --db 'postgresql://...'", file=sys.stderr)
        print(f"  3. Static mode:      python3 scripts/diff_migration.py --static", file=sys.stderr)
        sys.exit(1)

    result = diff(metadata, db_tables)

    if args.as_json:
        print(json.dumps(result, indent=2, default=str))
        sys.exit(0 if not result["missing_tables"] and not result["missing_columns"] else 1)

    if not args.migration_only:
        print_report(result)

    migration_code = generate_migration(result, metadata)

    if args.migration_only:
        print(migration_code)
        return

    if result["missing_tables"] or result["missing_columns"]:
        print(f"{BOLD}{'─'*60}{RESET}")
        print(f"{BOLD}  Proposed migration 004:{RESET}")
        print(f"{'─'*60}")
        print(migration_code)

    if args.write:
        out_path = ROOT / "alembic" / "versions" / "004_schema_sync.py"
        if out_path.exists():
            print(f"{YELLOW}WARNING: {out_path} already exists — overwriting.{RESET}")
        out_path.write_text(migration_code)
        print(f"{GREEN}✓ Written: {out_path}{RESET}")

    sys.exit(0 if not result["missing_tables"] and not result["missing_columns"] else 1)


if __name__ == "__main__":
    main()
