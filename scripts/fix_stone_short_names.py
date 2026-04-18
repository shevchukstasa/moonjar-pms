#!/usr/bin/env python3
"""
Fix canonical short_name for stone materials.

Re-derives each stone material's short_name from material.name using the
single source of truth in business/services/material_naming.py
(build_short_name_from_raw — see BUSINESS_LOGIC_FULL §29).

Default mode: dry-run — prints the diff, changes nothing.
With --apply: writes the new short_name in-place.

Safety:
  * Before applying, verifies no two materials would end up with the same
    short_name (which would break canonical dedup). If collision is detected,
    aborts without touching the DB.
  * Skips materials that are not stone (material_type/subgroup not in the
    stone set) — only stone has the "Lava Stone {size}" rule.
  * Writes an audit log entry per update (audit_logs), using action='update'
    with old_value / new_value for traceability.

Usage:
    DATABASE_URL=... python3 scripts/fix_stone_short_names.py            # dry-run
    DATABASE_URL=... python3 scripts/fix_stone_short_names.py --apply    # commit
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from sqlalchemy import create_engine, text
except ImportError:
    print("ERROR: SQLAlchemy not installed", file=sys.stderr)
    sys.exit(2)

from business.services.material_naming import build_short_name_from_raw


STONE_TYPES = {"stone", "tile", "sink", "custom_product"}


def _get_db_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("DATABASE_URL="):
                return line.split("=", 1)[1].strip().strip('"\'')
    print("ERROR: DATABASE_URL not set", file=sys.stderr)
    sys.exit(2)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true",
                        help="Actually write changes (default: dry-run)")
    args = parser.parse_args()

    engine = create_engine(_get_db_url())

    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT m.id, m.material_code, m.name, m.short_name,
                   m.material_type, sg.code AS subgroup_code
            FROM materials m
            LEFT JOIN material_subgroups sg ON sg.id = m.subgroup_id
            ORDER BY m.material_code NULLS LAST, m.name
        """)).mappings().all()

        planned: list[dict] = []
        for m in rows:
            mt = (m["material_type"] or "").lower()
            sg = (m["subgroup_code"] or "").lower()
            if mt not in STONE_TYPES and sg not in STONE_TYPES:
                continue
            expected = build_short_name_from_raw(m["name"] or "")
            current = m["short_name"] or ""
            if expected and expected != current:
                planned.append({
                    "id": str(m["id"]),
                    "code": m["material_code"],
                    "name": m["name"],
                    "old": current,
                    "new": expected,
                })

        print("=" * 78)
        print(f"STONE SHORT_NAME FIX — {'APPLY' if args.apply else 'DRY-RUN'}")
        print("=" * 78)
        print(f"Stone materials scanned: {sum(1 for m in rows if (m['material_type'] or '').lower() in STONE_TYPES or (m['subgroup_code'] or '').lower() in STONE_TYPES)}")
        print(f"Need fix:                {len(planned)}")
        print()

        if not planned:
            print("Nothing to do.")
            return 0

        print(f"{'CODE':<8} {'NAME':<32} {'OLD':<32} → NEW")
        for p in planned:
            print(
                f"{(p['code'] or '—'):<8} "
                f"{(p['name'] or '—')[:31]:<32} "
                f"{p['old'][:31]:<32} → {p['new']}"
            )
        print()

        # Collision check: compute the final short_name for EVERY stone material
        # (both those we plan to change and those we don't), then ensure uniqueness.
        final_by_id: dict[str, str] = {}
        for m in rows:
            mt = (m["material_type"] or "").lower()
            sg = (m["subgroup_code"] or "").lower()
            if mt not in STONE_TYPES and sg not in STONE_TYPES:
                continue
            expected = build_short_name_from_raw(m["name"] or "")
            final = expected or (m["short_name"] or "")
            final_by_id[str(m["id"])] = final

        from collections import Counter
        name_count = Counter(final_by_id.values())
        collisions = {n: c for n, c in name_count.items() if c > 1 and n}
        if collisions:
            print("⚠️  COLLISION DETECTED — after fix these short_names would repeat:")
            for n, c in collisions.items():
                ids = [mid for mid, fn in final_by_id.items() if fn == n]
                codes = conn.execute(
                    text("SELECT material_code, name FROM materials WHERE id::text = ANY(:ids)"),
                    {"ids": ids},
                ).all()
                print(f"  {n!r}  ×{c}")
                for code, raw in codes:
                    print(f"      • {code} / {raw}")
            print()
            print("Aborting — fix material.name first, then rerun.")
            return 3

        if not args.apply:
            print("Dry-run — no changes. Rerun with --apply to commit.")
            return 0

        # Apply
        print("Applying…")
        with conn.begin():
            for p in planned:
                conn.execute(
                    text("""
                        UPDATE materials
                        SET short_name = :new, updated_at = NOW()
                        WHERE id = :id
                    """),
                    {"new": p["new"], "id": p["id"]},
                )
                # Audit log (best-effort; skip silently if audit_logs shape differs)
                try:
                    conn.execute(
                        text("""
                            INSERT INTO audit_logs
                              (id, entity_type, entity_id, action, old_value, new_value, created_at)
                            VALUES
                              (gen_random_uuid(), 'material', :id, 'update',
                               :old, :new, NOW())
                        """),
                        {
                            "id": p["id"],
                            "old": f'{{"short_name": "{p["old"]}"}}',
                            "new": f'{{"short_name": "{p["new"]}"}}',
                        },
                    )
                except Exception:
                    pass

        print(f"✓ Updated {len(planned)} stone materials.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
