"""Add short_name + delivery history + diameter; backfill stone typologies.

See docs/BUSINESS_LOGIC_FULL.md §29 for the canonical model.

Adds:
  - materials.short_name      VARCHAR(100)  — canonical "Lava Stone {size}" for stone
  - sizes.diameter_mm         INTEGER NULL  — for round shapes (sinks, round countertops)
  - material_transactions.delivery_name  VARCHAR(300) NULL — raw OCR text per receipt

Backfills:
  - For material_type='stone': derive short_name from existing name via regex parser.
  - For non-stone: short_name = name.
  - Legacy product_subtype values map: sinks→sink, table_top→countertop, custom→freeform.

Revision ID: 026
Revises: 025_backfill_task_type_enum
Create Date: 2026-04-18
"""
from __future__ import annotations

import re

from alembic import op
from sqlalchemy import text


revision = "026"
down_revision = "025_backfill_task_type_enum"
branch_labels = None
depends_on = None


# ── Helpers (kept inline so migration is self-contained) ───────────

# Match "5x20", "5×20", "5/20", "5 × 20" → groups (w, h)
_RECT_RE = re.compile(
    r'(\d+(?:[.,]\d+)?)\s*[/xX×]\s*(\d+(?:[.,]\d+)?)'
    r'(?:\s*[/xX×]\s*(\d+(?:[.,/\-]\d+)?))?'
)
# Round: Ø29, dia30, etc.
_DIA_RE = re.compile(r'[øØ]\s*(\d+(?:\.\d+)?)|dia\w*\s*(\d+(?:\.\d+)?)', re.IGNORECASE)


def _build_size_label(name: str) -> str | None:
    """Extract canonical size label from a stone material name.

    "Grey Lava 5×20×1.2" → "5×20×1.2"
    "Lava Sink Ø35×3"    → "Ø35×3"
    Returns None if no size found.
    """
    dia = _DIA_RE.search(name)
    if dia:
        d = dia.group(1) or dia.group(2)
        # Look for thickness after the diameter
        rest = name[dia.end():]
        thick_match = re.search(r'[xX×]\s*(\d+(?:[.,/\-]\d+)?)', rest)
        if thick_match:
            return f"Ø{d}×{thick_match.group(1).replace(',', '.')}"
        return f"Ø{d}"

    rect = _RECT_RE.search(name)
    if rect:
        w = rect.group(1).replace(",", ".")
        h = rect.group(2).replace(",", ".")
        t = rect.group(3)
        if t:
            t = t.replace(",", ".")
            return f"{w}×{h}×{t}"
        return f"{w}×{h}"

    return None


def _build_stone_short_name(name: str) -> str:
    """Build canonical short_name for a stone material.

    Always prefixes "Lava Stone " + size label (or just "Lava Stone Freeform" if no size).
    """
    size_label = _build_size_label(name)
    if size_label:
        return f"Lava Stone {size_label}"
    return "Lava Stone Freeform"


# ── Migration ──────────────────────────────────────────────────────

def upgrade() -> None:
    conn = op.get_bind()

    # 1. materials.short_name
    has_short = conn.execute(text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
        "WHERE table_name='materials' AND column_name='short_name')"
    )).scalar()
    if not has_short:
        conn.execute(text(
            "ALTER TABLE materials ADD COLUMN short_name VARCHAR(100)"
        ))

    # 2. sizes.diameter_mm
    has_dia = conn.execute(text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
        "WHERE table_name='sizes' AND column_name='diameter_mm')"
    )).scalar()
    if not has_dia:
        conn.execute(text(
            "ALTER TABLE sizes ADD COLUMN diameter_mm INTEGER"
        ))

    # 3. material_transactions.delivery_name
    has_dn = conn.execute(text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
        "WHERE table_name='material_transactions' AND column_name='delivery_name')"
    )).scalar()
    if not has_dn:
        conn.execute(text(
            "ALTER TABLE material_transactions ADD COLUMN delivery_name VARCHAR(300)"
        ))

    # 4. Migrate legacy product_subtype values for stone materials
    #    sinks → sink, table_top → countertop, custom → freeform
    conn.execute(text("""
        UPDATE materials SET product_subtype = 'sink'
        WHERE material_type = 'stone' AND product_subtype = 'sinks'
    """))
    conn.execute(text("""
        UPDATE materials SET product_subtype = 'countertop'
        WHERE material_type = 'stone' AND product_subtype = 'table_top'
    """))
    conn.execute(text("""
        UPDATE materials SET product_subtype = 'freeform'
        WHERE material_type = 'stone' AND product_subtype = 'custom'
    """))

    # 5. Backfill short_name
    #    - Non-stone: short_name = name (only if NULL)
    conn.execute(text("""
        UPDATE materials
        SET short_name = name
        WHERE short_name IS NULL AND material_type <> 'stone'
    """))

    #    - Stone: parse name → "Lava Stone {size}"
    rows = conn.execute(text(
        "SELECT id, name FROM materials "
        "WHERE material_type='stone' AND short_name IS NULL"
    )).fetchall()
    for row in rows:
        short = _build_stone_short_name(row[1] or "")
        # Truncate to column limit
        short = short[:100]
        conn.execute(
            text("UPDATE materials SET short_name = :s WHERE id = :id"),
            {"s": short, "id": row[0]},
        )

    # 6. Index on short_name (for matcher lookups)
    has_idx = conn.execute(text(
        "SELECT EXISTS (SELECT 1 FROM pg_indexes "
        "WHERE indexname='ix_materials_short_name')"
    )).scalar()
    if not has_idx:
        conn.execute(text(
            "CREATE INDEX ix_materials_short_name ON materials (short_name)"
        ))


def downgrade() -> None:
    conn = op.get_bind()

    # Drop index, then columns
    conn.execute(text("DROP INDEX IF EXISTS ix_materials_short_name"))
    conn.execute(text("ALTER TABLE materials DROP COLUMN IF EXISTS short_name"))
    conn.execute(text("ALTER TABLE sizes DROP COLUMN IF EXISTS diameter_mm"))
    conn.execute(text(
        "ALTER TABLE material_transactions DROP COLUMN IF EXISTS delivery_name"
    ))
    # Note: legacy product_subtype value migration is NOT reverted —
    # rolling back the value remap would lose information. Left as-is.
