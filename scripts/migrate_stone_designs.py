#!/usr/bin/env python3
"""
One-off data migration: assign stone_designs to M-0053 / M-0054 and
regenerate short_name for all stone materials.

What it does (dry-run by default; --apply to commit):

  1. Creates (if missing) three default designs: design-1, design-2, design-3
     with Russian names "Дизайн 1 / 2 / 3", typology=3d.
     Photos intentionally not set — UI renders placeholders.

  2. For M-0053 (Lavastone 5x20x1.2, typology=3d): assigns design-1,
     product_subtype='3d', name kept as-is.

  3. For M-0054 (Grey Lava 5x20x1.2, typology=—): assigns design-2,
     sets product_subtype='3d', name kept as-is.

  4. Recomputes short_name for every stone material via
     build_short_name_from_raw(name, design_name), writing "Lava Stone
     5×20×1.2 · Дизайн 1" etc. Also fixes M-0055 / M-0058 which had
     stale short_names (M-0055: "Lava Stone 8×21.5×1.2" → "5×21.5×1.2";
     M-0058: "Lava Stone 5×20×1" → "10×20×1").

  5. Checks no two stone materials end up with the same short_name
     (the partial UNIQUE index on (size_id, product_subtype, design_id)
     now enforces this at DB level too, but we pre-check for a clearer
     error message).

Safe to re-run. If designs already exist, they are reused.
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text

from business.services.material_naming import build_short_name_from_raw


DEFAULT_DESIGNS = [
    {"code": "design-1", "name": "Дизайн 1", "name_id": "Desain 1", "typology": "3d",
     "description": "Первый 3D-узор"},
    {"code": "design-2", "name": "Дизайн 2", "name_id": "Desain 2", "typology": "3d",
     "description": "Второй 3D-узор"},
    {"code": "design-3", "name": "Дизайн 3", "name_id": "Desain 3", "typology": "3d",
     "description": "Третий 3D-узор"},
]

# Explicit material → design code mapping. Anything not listed keeps its
# current design_id (likely NULL — the owner assigns via UI later).
MATERIAL_ASSIGNMENTS = {
    "M-0053": "design-1",
    "M-0054": "design-2",
}

# Materials that need explicit typology correction (audit flagged these
# as having NULL product_subtype while clearly being 3d/tile).
TYPOLOGY_CORRECTIONS = {
    "M-0054": "3d",  # Grey Lava 5x20x1.2 — same geometry as M-0053 (3d)
    # M-0049 Lavastone 8x15 — left alone (unit=m², typology unclear, user decides)
}


def _get_db_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    print("ERROR: DATABASE_URL not set", file=sys.stderr)
    sys.exit(2)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write changes (default: dry-run)")
    args = parser.parse_args()

    engine = create_engine(_get_db_url())
    with engine.begin() as conn:
        print("=" * 78)
        print(f"STONE DESIGN MIGRATION — {'APPLY' if args.apply else 'DRY-RUN'}")
        print("=" * 78)

        # ── Step 1: ensure designs exist ───────────────────────────
        existing_designs = {
            row["code"]: row["id"]
            for row in conn.execute(text(
                "SELECT id::text AS id, code FROM stone_designs WHERE code = ANY(:codes)"
            ), {"codes": [d["code"] for d in DEFAULT_DESIGNS]}).mappings().all()
        }

        design_id_by_code: dict[str, str] = dict(existing_designs)
        designs_to_create = [d for d in DEFAULT_DESIGNS if d["code"] not in existing_designs]

        print(f"\nDesigns: {len(existing_designs)} existing, {len(designs_to_create)} to create")
        for d in designs_to_create:
            print(f"  + {d['code']} / {d['name']}")

        if args.apply:
            for d in designs_to_create:
                new_id = conn.execute(text("""
                    INSERT INTO stone_designs (code, name, name_id, typology, description)
                    VALUES (:code, :name, :name_id, :typology, :description)
                    RETURNING id::text
                """), d).scalar()
                design_id_by_code[d["code"]] = new_id
        else:
            # Fake UUIDs for dry-run planning
            for d in designs_to_create:
                design_id_by_code[d["code"]] = f"(new:{d['code']})"

        # ── Step 2: load all stone materials ───────────────────────
        mats = conn.execute(text("""
            SELECT m.id::text AS id, m.material_code, m.name, m.short_name,
                   m.product_subtype, m.design_id::text AS design_id,
                   sg.code AS subgroup_code, m.material_type
            FROM materials m
            LEFT JOIN material_subgroups sg ON sg.id = m.subgroup_id
            WHERE m.material_type IN ('stone', 'tile', 'sink', 'custom_product')
               OR sg.code IN ('stone', 'tile', 'sink', 'custom_product')
            ORDER BY m.material_code
        """)).mappings().all()

        print(f"\nStone materials: {len(mats)}")

        # ── Step 3: plan updates ───────────────────────────────────
        planned = []
        for m in mats:
            code = m["material_code"]
            current_design_id = m["design_id"]
            current_typology = m["product_subtype"]
            current_short = m["short_name"] or ""

            # Target design_id
            target_design_code = MATERIAL_ASSIGNMENTS.get(code)
            target_design_id = (
                design_id_by_code.get(target_design_code)
                if target_design_code else current_design_id
            )

            # Target typology
            target_typology = TYPOLOGY_CORRECTIONS.get(code, current_typology)

            # Target short_name (always recompute from name)
            design_name = None
            if target_design_code:
                design_name = next(
                    (d["name"] for d in DEFAULT_DESIGNS if d["code"] == target_design_code),
                    None,
                )
            elif target_design_id:
                # Look up existing design name
                design_name = conn.execute(
                    text("SELECT name FROM stone_designs WHERE id::text = :id"),
                    {"id": target_design_id},
                ).scalar()
            target_short = build_short_name_from_raw(m["name"] or "", design_name=design_name)

            changes = []
            if target_design_id and target_design_id != current_design_id:
                changes.append(("design_id", current_design_id, target_design_id))
            if target_typology and target_typology != current_typology:
                changes.append(("product_subtype", current_typology, target_typology))
            if target_short and target_short != current_short:
                changes.append(("short_name", current_short, target_short))

            if changes:
                planned.append({
                    "id": m["id"],
                    "code": code,
                    "name": m["name"],
                    "changes": changes,
                    "target_design_id": target_design_id if target_design_code else current_design_id,
                    "target_typology": target_typology,
                    "target_short": target_short,
                })

        print(f"\nMaterials to update: {len(planned)}\n")
        for p in planned:
            print(f"  {p['code']} / {p['name']}")
            for field, old, new in p["changes"]:
                print(f"    {field}: {old!r} → {new!r}")

        if not planned:
            print("\nNothing to update. Exit.")
            return 0

        # ── Step 4: collision check on short_name ──────────────────
        all_shorts = {}
        for m in mats:
            planned_for_this = next((p for p in planned if p["id"] == m["id"]), None)
            final_short = planned_for_this["target_short"] if planned_for_this else (m["short_name"] or "")
            all_shorts[m["id"]] = final_short

        counts = Counter(all_shorts.values())
        collisions = {s: c for s, c in counts.items() if c > 1 and s}
        if collisions:
            print("\n⚠️  COLLISION — after migration these short_names would repeat:")
            for s, c in collisions.items():
                print(f"  {s!r} ×{c}")
                for mid, sh in all_shorts.items():
                    if sh == s:
                        code = next((m["material_code"] for m in mats if m["id"] == mid), "?")
                        print(f"      • {code}")
            print("\nAborting. Fix material.name or assignments.")
            return 3

        print("\n✓ No short_name collisions.")

        if not args.apply:
            print("\nDry-run — no changes. Rerun with --apply.")
            return 0

        # ── Step 5: apply ──────────────────────────────────────────
        print("\nApplying…")
        for p in planned:
            conn.execute(text("""
                UPDATE materials
                SET design_id = CAST(:design_id AS uuid),
                    product_subtype = :typology,
                    short_name = :short,
                    updated_at = NOW()
                WHERE id::text = :id
            """), {
                "design_id": p["target_design_id"],
                "typology": p["target_typology"],
                "short": p["target_short"],
                "id": p["id"],
            })
        print(f"\n✓ Updated {len(planned)} stone materials.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
