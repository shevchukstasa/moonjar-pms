#!/usr/bin/env python3
"""
Stone data integrity audit — проверка связности характеристик камня
по всей системе: unit (pcs/m²), size, shape, typology (product_subtype),
collection, short_name, supplier, recipes.

Цель: найти все места, где данные у stone-материала/позиции неполные
или расходятся между сущностями (Material ↔ Size ↔ OrderPosition ↔ Recipe).

Запуск:
    # Локально (нужен DATABASE_URL в env или .env)
    DATABASE_URL=postgresql://... python3 scripts/audit_stone_data.py

    # На Railway (с production-БД)
    railway run --service <backend-service-id> python3 scripts/audit_stone_data.py

    # JSON-режим (для дальнейшей обработки)
    python3 scripts/audit_stone_data.py --json > audit.json

Read-only: ничего не меняет в БД.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from decimal import Decimal
from pathlib import Path
from typing import Any

# ── Bootstrap DB connection ─────────────────────────────────────────────

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from sqlalchemy import create_engine, text
except ImportError:
    print("ERROR: SQLAlchemy not installed. Run: pip install sqlalchemy", file=sys.stderr)
    sys.exit(2)


def _get_db_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    try:
        from api.config import settings
        return settings.DATABASE_URL
    except Exception:
        env_file = Path(__file__).resolve().parent.parent / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("DATABASE_URL="):
                    return line.split("=", 1)[1].strip().strip('"\'')
    print("ERROR: DATABASE_URL not found (env, api.config.settings, .env)", file=sys.stderr)
    sys.exit(2)


# ── Stone detection rules ───────────────────────────────────────────────
# Material считается "stone" если его subgroup.code или material_type
# совпадает с одним из stone-типов. См. §29 BUSINESS_LOGIC_FULL.

STONE_MATERIAL_TYPES = {"stone", "tile", "sink", "custom_product"}
VALID_TYPOLOGIES = {"tiles", "3d", "sink", "countertop", "freeform"}
VALID_UNITS_FOR_STONE = {"pcs", "m2"}


# ── Severity levels ─────────────────────────────────────────────────────
SEV_HIGH = "HIGH"
SEV_MED = "MED"
SEV_LOW = "LOW"


@dataclass
class Issue:
    severity: str
    entity: str          # "material" | "size" | "position" | "recipe" | "cross"
    entity_id: str
    entity_name: str
    field: str
    problem: str
    hint: str = ""

    def to_row(self) -> list[str]:
        return [self.severity, self.entity, self.entity_name[:50],
                self.field, self.problem, self.hint]


@dataclass
class Report:
    db_url_host: str
    materials_total: int = 0
    stone_materials: list[dict] = field(default_factory=list)
    sizes: list[dict] = field(default_factory=list)
    positions_total: int = 0
    stone_positions_sampled: int = 0
    issues: list[Issue] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)
    unit_breakdown: dict[str, int] = field(default_factory=dict)
    typology_breakdown: dict[str, int] = field(default_factory=dict)
    shape_breakdown: dict[str, int] = field(default_factory=dict)

    def add(self, issue: Issue) -> None:
        self.issues.append(issue)

    def by_severity(self) -> dict[str, int]:
        c = Counter(i.severity for i in self.issues)
        return {k: c.get(k, 0) for k in (SEV_HIGH, SEV_MED, SEV_LOW)}


# ── Helpers ─────────────────────────────────────────────────────────────

def _safe_host(url: str) -> str:
    """Strip credentials from DB URL for display."""
    import re
    return re.sub(r"://[^@]+@", "://***@", url)


def _compute_piece_area_sqm(w_mm: Any, h_mm: Any, d_mm: Any, shape: str | None) -> float | None:
    """Compute single-piece area from Size fields. Returns None if impossible."""
    try:
        if shape == "round" and d_mm:
            r = float(d_mm) / 2.0 / 1000.0
            return 3.14159265 * r * r
        if w_mm and h_mm:
            return float(w_mm) * float(h_mm) / 1_000_000.0
    except Exception:
        return None
    return None


# ── Section 1: Materials ────────────────────────────────────────────────

def audit_materials(conn, report: Report) -> dict[str, dict]:
    """
    Проверка материалов-камней: unit, size_id, product_subtype, short_name, supplier_id.
    Возвращает dict[material_id → material_row] для дальнейших перекрёстных проверок.
    """
    rows = conn.execute(text("""
        SELECT
            m.id, m.material_code, m.name, m.short_name, m.full_name,
            m.unit, m.material_type, m.product_subtype,
            m.subgroup_id, m.supplier_id, m.size_id,
            sg.code AS subgroup_code, sg.name AS subgroup_name,
            s.name AS size_name, s.width_mm, s.height_mm,
            s.thickness_mm, s.diameter_mm, s.shape AS size_shape,
            sup.name AS supplier_name
        FROM materials m
        LEFT JOIN material_subgroups sg ON sg.id = m.subgroup_id
        LEFT JOIN sizes s ON s.id = m.size_id
        LEFT JOIN suppliers sup ON sup.id = m.supplier_id
        ORDER BY m.material_code NULLS LAST, m.name
    """)).mappings().all()

    report.materials_total = len(rows)
    mat_by_id: dict[str, dict] = {}

    for m in rows:
        mat_by_id[str(m["id"])] = dict(m)
        is_stone = (
            (m["material_type"] or "").lower() in STONE_MATERIAL_TYPES
            or (m["subgroup_code"] or "").lower() in STONE_MATERIAL_TYPES
        )
        if not is_stone:
            continue

        report.stone_materials.append({
            "id": str(m["id"]),
            "code": m["material_code"],
            "name": m["name"],
            "short_name": m["short_name"],
            "unit": m["unit"],
            "typology": m["product_subtype"],
            "material_type": m["material_type"],
            "subgroup": m["subgroup_code"],
            "size": m["size_name"],
            "size_id": str(m["size_id"]) if m["size_id"] else None,
            "supplier": m["supplier_name"],
        })

        unit = (m["unit"] or "").lower()
        report.unit_breakdown[unit] = report.unit_breakdown.get(unit, 0) + 1
        report.typology_breakdown[m["product_subtype"] or "—"] = \
            report.typology_breakdown.get(m["product_subtype"] or "—", 0) + 1

        label = f"{m['material_code']} / {m['name']}"

        # HIGH: unit не in {pcs, m2}
        if unit not in VALID_UNITS_FOR_STONE:
            report.add(Issue(SEV_HIGH, "material", str(m["id"]), label,
                             "unit",
                             f"unit={m['unit']!r} — не pcs/m²",
                             "Stone должен быть в pcs или m²"))

        # HIGH: no size_id — конверсия pcs↔m² невозможна
        if not m["size_id"]:
            report.add(Issue(SEV_HIGH, "material", str(m["id"]), label,
                             "size_id",
                             "не привязан size_id",
                             "Без size нельзя пересчитать pcs → m²"))

        # HIGH: unit=pcs + no size → 100% сломано в резерве
        if unit == "pcs" and not m["size_id"]:
            report.add(Issue(SEV_HIGH, "material", str(m["id"]), label,
                             "unit+size",
                             "unit=pcs, size=NULL — stone_reservation вернёт 0",
                             "Привязать size или сменить unit"))

        # MED: no product_subtype (typology)
        if not m["product_subtype"]:
            report.add(Issue(SEV_MED, "material", str(m["id"]), label,
                             "product_subtype",
                             "нет типологии (tiles/3d/sink/countertop/freeform)",
                             "Влияет на kiln zone classification"))
        elif m["product_subtype"] not in VALID_TYPOLOGIES:
            report.add(Issue(SEV_HIGH, "material", str(m["id"]), label,
                             "product_subtype",
                             f"invalid typology={m['product_subtype']!r}",
                             f"Допустимо: {sorted(VALID_TYPOLOGIES)}"))

        # MED: нет short_name — ломается canonical match (§29)
        if not m["short_name"]:
            report.add(Issue(SEV_MED, "material", str(m["id"]), label,
                             "short_name",
                             "нет short_name (canonical match key)",
                             "Delivery/webhook не найдёт дубли"))

        # MED: нет supplier
        if not m["supplier_id"]:
            report.add(Issue(SEV_MED, "material", str(m["id"]), label,
                             "supplier_id",
                             "нет поставщика",
                             "Не сможем создать PurchaseRequest"))

        # LOW: size dimensions consistency
        if m["size_id"]:
            sh = (m["size_shape"] or "").lower()
            if sh == "round" and not m["diameter_mm"]:
                report.add(Issue(SEV_HIGH, "material", str(m["id"]), label,
                                 "size.diameter",
                                 "shape=round, но diameter_mm=NULL",
                                 "Площадь посчитать невозможно"))
            elif sh != "round" and (not m["width_mm"] or not m["height_mm"]):
                report.add(Issue(SEV_HIGH, "material", str(m["id"]), label,
                                 "size.w/h",
                                 "shape=rectangular, но width/height пусты",
                                 "Площадь посчитать невозможно"))

    return mat_by_id


# ── Section 2: Sizes ────────────────────────────────────────────────────

def audit_sizes(conn, report: Report) -> dict[str, dict]:
    rows = conn.execute(text("""
        SELECT id, name, width_mm, height_mm, thickness_mm, diameter_mm,
               shape, is_custom
        FROM sizes
        ORDER BY name
    """)).mappings().all()

    sizes_by_id: dict[str, dict] = {}
    mat_count_by_size = dict(conn.execute(text("""
        SELECT size_id::text, COUNT(*) FROM materials
        WHERE size_id IS NOT NULL GROUP BY size_id
    """)).all())
    pos_count_by_size = dict(conn.execute(text("""
        SELECT size_id::text, COUNT(*) FROM order_positions
        WHERE size_id IS NOT NULL GROUP BY size_id
    """)).all())

    for s in rows:
        sid = str(s["id"])
        sizes_by_id[sid] = dict(s)
        n_mat = mat_count_by_size.get(sid, 0)
        n_pos = pos_count_by_size.get(sid, 0)
        label = f"{s['name']}"
        sh = (s["shape"] or "").lower()

        report.shape_breakdown[sh or "—"] = report.shape_breakdown.get(sh or "—", 0) + 1
        report.sizes.append({
            "id": sid, "name": s["name"],
            "w_mm": s["width_mm"], "h_mm": s["height_mm"],
            "t_mm": s["thickness_mm"], "d_mm": s["diameter_mm"],
            "shape": sh,
            "used_by_materials": n_mat,
            "used_by_positions": n_pos,
        })

        # HIGH: zero dimensions
        if sh == "round":
            if not s["diameter_mm"] or s["diameter_mm"] <= 0:
                report.add(Issue(SEV_HIGH, "size", sid, label,
                                 "diameter_mm",
                                 f"shape=round, diameter_mm={s['diameter_mm']}",
                                 "Площадь = 0"))
        else:
            if not s["width_mm"] or not s["height_mm"]:
                report.add(Issue(SEV_HIGH, "size", sid, label,
                                 "w/h",
                                 f"w={s['width_mm']}, h={s['height_mm']}",
                                 "Площадь = 0"))

        # LOW: orphaned size
        if n_mat == 0 and n_pos == 0:
            report.add(Issue(SEV_LOW, "size", sid, label,
                             "usage",
                             "размер не используется ни материалом, ни позицией",
                             "Можно почистить"))

    return sizes_by_id


# ── Section 3: Order Positions (stone) ──────────────────────────────────

def audit_positions(conn, report: Report, sizes_by_id: dict) -> None:
    total = conn.execute(text("SELECT COUNT(*) FROM order_positions")).scalar() or 0
    report.positions_total = int(total)

    # Смотрим ТОЛЬКО активные/недавние, чтобы не гонять исторические.
    rows = conn.execute(text("""
        SELECT
            p.id, p.quantity, p.quantity_sqm, p.glazeable_sqm,
            p.color, p.collection, p.size AS size_str, p.size_id,
            p.shape, p.length_cm, p.width_cm, p.depth_cm,
            p.thickness_mm, p.product_type,
            p.application_collection_code, p.application_method_code,
            p.place_of_application,
            o.order_number,
            s.width_mm AS sz_w, s.height_mm AS sz_h,
            s.diameter_mm AS sz_d, s.shape AS sz_shape
        FROM order_positions p
        JOIN production_orders o ON o.id = p.order_id
        LEFT JOIN sizes s ON s.id = p.size_id
        WHERE o.status NOT IN ('cancelled', 'shipped')
        ORDER BY o.created_at DESC
        LIMIT 500
    """)).mappings().all()

    report.stone_positions_sampled = len(rows)

    for p in rows:
        pid = str(p["id"])
        label = f"{p['order_number']}:{p['color']} {p['size_str']}"
        qty = float(p["quantity"] or 0)
        qty_sqm = float(p["quantity_sqm"] or 0)
        glaz = float(p["glazeable_sqm"] or 0)

        # HIGH: ни quantity, ни quantity_sqm
        if qty <= 0 and qty_sqm <= 0:
            report.add(Issue(SEV_HIGH, "position", pid, label,
                             "quantity",
                             f"qty=0, qty_sqm=0 — позиция пустая",
                             "Scheduler проигнорирует"))

        # HIGH: no size_id
        if not p["size_id"]:
            report.add(Issue(SEV_MED, "position", pid, label,
                             "size_id",
                             f"нет size_id (size_str={p['size_str']!r})",
                             "Fallback на length×width в см"))

        # HIGH: glazeable_sqm не совпадает с вычисленным
        if p["size_id"] and glaz > 0:
            piece = _compute_piece_area_sqm(
                p["sz_w"], p["sz_h"], p["sz_d"], p["sz_shape"])
            if piece and piece > 0:
                drift = abs(glaz - piece) / piece
                if drift > 0.15:  # >15% расхождение
                    report.add(Issue(SEV_MED, "position", pid, label,
                                     "glazeable_sqm",
                                     f"glazeable={glaz:.4f} m², size даёт {piece:.4f} m² (drift {drift*100:.0f}%)",
                                     "Проверить, правильно ли насчитана кромка/профиль"))

        # MED: quantity_sqm vs quantity×piece_area mismatch
        if p["size_id"] and qty > 0 and qty_sqm > 0:
            piece = _compute_piece_area_sqm(
                p["sz_w"], p["sz_h"], p["sz_d"], p["sz_shape"])
            if piece:
                expected = qty * piece
                if expected > 0 and abs(qty_sqm - expected) / expected > 0.1:
                    report.add(Issue(SEV_HIGH, "position", pid, label,
                                     "quantity_sqm",
                                     f"qty_sqm={qty_sqm:.2f}, но {qty}×{piece:.4f}={expected:.2f}",
                                     "Одно из значений врёт — расходы и планирование будут неверны"))

        # LOW: shape в позиции не совпадает с shape в size
        if p["size_id"] and p["shape"] and p["sz_shape"]:
            ps = (p["shape"] or "").lower()
            ss = (p["sz_shape"] or "").lower()
            if ps != ss and not (ps == "rectangle" and ss == "square"):
                report.add(Issue(SEV_LOW, "position", pid, label,
                                 "shape",
                                 f"position.shape={ps}, size.shape={ss}",
                                 "Скорее всего ошибка импорта"))

        # MED: нет collection для финальных продуктов
        if not p["collection"]:
            report.add(Issue(SEV_LOW, "position", pid, label,
                             "collection",
                             "нет collection (Authentic/Creative/Stencil/...)",
                             "Влияет на сортировку/упаковку"))

        # MED: нет application_collection_code
        if not p["application_collection_code"]:
            report.add(Issue(SEV_LOW, "position", pid, label,
                             "application_collection_code",
                             "нет кода коллекции нанесения",
                             "Scheduler может неправильно выбрать стадии"))


# ── Section 4: Cross-entity (Material ↔ Position matching) ──────────────

def audit_cross(conn, report: Report, mat_by_id: dict, sizes_by_id: dict) -> None:
    """
    Для каждого stone-материала с одной стороны, и для каждой активной
    позиции с другой — проверить, есть ли материал того же size+shape,
    и совпадают ли unit/характеристики.
    """
    # Мапим material по (short_name, size_id) и (size_id) для быстрого lookup
    stone_mats_by_size: dict[str, list[dict]] = defaultdict(list)
    for m in mat_by_id.values():
        mt = (m["material_type"] or "").lower()
        sg = (m["subgroup_code"] or "").lower()
        if mt in STONE_MATERIAL_TYPES or sg in STONE_MATERIAL_TYPES:
            if m["size_id"]:
                stone_mats_by_size[str(m["size_id"])].append(m)

    # Берём активные позиции
    rows = conn.execute(text("""
        SELECT DISTINCT p.size_id, p.size AS size_str,
               MIN(o.order_number) AS sample_order
        FROM order_positions p
        JOIN production_orders o ON o.id = p.order_id
        WHERE o.status NOT IN ('cancelled', 'shipped')
          AND p.size_id IS NOT NULL
        GROUP BY p.size_id, p.size
    """)).mappings().all()

    seen_mismatches = set()
    for p in rows:
        sid = str(p["size_id"])
        mats = stone_mats_by_size.get(sid, [])
        if not mats:
            report.add(Issue(SEV_MED, "cross", sid, p["size_str"] or "?",
                             "material-lookup",
                             f"нет ни одного stone-материала с size_id={sid}",
                             f"Позиции в ордерах (пример: {p['sample_order']}) не смогут зарезервировать"))
            continue
        # Если несколько материалов того же size — unit должен совпадать
        units = {(m["unit"] or "").lower() for m in mats}
        if len(units) > 1 and "+".join(sorted(units)) not in seen_mismatches:
            seen_mismatches.add("+".join(sorted(units)))
            sample = ", ".join(m["material_code"] or m["name"] for m in mats[:5])
            report.add(Issue(SEV_HIGH, "cross", sid, p["size_str"] or "?",
                             "unit-mismatch",
                             f"материалы с size={p['size_str']} имеют разные unit: {units}",
                             f"Резерв нестабилен. Материалы: {sample}"))


# ── Section 5: Recipes using stone materials ────────────────────────────

def audit_recipes(conn, report: Report, mat_by_id: dict) -> None:
    """
    Recipes сами по себе не используют stone-материал, но RecipeMaterial
    может ссылаться на stone. Это странно, помечаем.
    Также: recipes с consumption_*_ml_per_sqm требуют, чтобы позиция имела
    area в m² — если material в pcs и size нет, это сломается.
    """
    # Stone-materials в RecipeMaterial
    rows = conn.execute(text("""
        SELECT rm.id AS rm_id, rm.recipe_id, r.name AS recipe_name,
               rm.material_id, m.name AS material_name, m.material_code,
               m.unit, m.material_type, rm.quantity_per_unit, rm.unit AS rm_unit,
               sg.code AS subgroup_code
        FROM recipe_materials rm
        JOIN recipes r ON r.id = rm.recipe_id
        JOIN materials m ON m.id = rm.material_id
        LEFT JOIN material_subgroups sg ON sg.id = m.subgroup_id
    """)).mappings().all()

    for rm in rows:
        mt = (rm["material_type"] or "").lower()
        sg = (rm["subgroup_code"] or "").lower()
        is_stone = mt in STONE_MATERIAL_TYPES or sg in STONE_MATERIAL_TYPES
        if not is_stone:
            continue
        label = f"{rm['recipe_name']} ← {rm['material_name']}"
        report.add(Issue(SEV_MED, "recipe", str(rm["rm_id"]), label,
                         "stone-in-recipe",
                         f"stone-материал в рецепте (unit={rm['unit']}, rm.unit={rm['rm_unit']})",
                         "Обычно stone — это продукт, а не ингредиент"))

    # Recipes с ml/m² rate + связанные позиции в pcs-материалах без size
    # (это уже покрыто в audit_positions косвенно через qty_sqm checks)


# ── Section 6: Recent transactions (unit anomalies) ─────────────────────

def audit_transactions(conn, report: Report) -> None:
    """
    За последние 30 дней — приход/расход stone-материалов с quantity,
    которое не похоже на unit. Например, material в pcs, но quantity=0.25
    (скорее всего это m² введены как pcs).
    """
    rows = conn.execute(text("""
        SELECT t.id, t.type, t.quantity, t.created_at, t.notes,
               m.material_code, m.name AS material_name, m.unit,
               m.material_type, sg.code AS subgroup_code
        FROM material_transactions t
        JOIN materials m ON m.id = t.material_id
        LEFT JOIN material_subgroups sg ON sg.id = m.subgroup_id
        WHERE t.created_at > NOW() - INTERVAL '30 days'
          AND (m.material_type IN ('stone','tile','sink','custom_product')
               OR sg.code IN ('stone','tile','sink','custom_product'))
        ORDER BY t.created_at DESC
        LIMIT 200
    """)).mappings().all()

    for t in rows:
        qty = float(t["quantity"] or 0)
        unit = (t["unit"] or "").lower()
        label = f"{t['material_code']} / {t['material_name']}"

        # HIGH: pcs with fractional quantity
        if unit == "pcs" and qty != int(qty):
            report.add(Issue(SEV_HIGH, "transaction", str(t["id"]), label,
                             "quantity",
                             f"type={t['type']}, qty={qty} (дробное) при unit=pcs",
                             f"created_at={t['created_at']}; скорее всего введено в m²"))

        # LOW: m2 with integer large quantity (может быть pcs)
        if unit == "m2" and qty == int(qty) and qty > 100:
            report.add(Issue(SEV_LOW, "transaction", str(t["id"]), label,
                             "quantity",
                             f"type={t['type']}, qty={qty} (целое, >100) при unit=m²",
                             "Возможно введено как pcs"))


# ── Summary ─────────────────────────────────────────────────────────────

def print_report(report: Report) -> None:
    print("=" * 78)
    print("STONE DATA INTEGRITY AUDIT")
    print("=" * 78)
    print(f"DB:           {report.db_url_host}")
    print(f"Materials:    {report.materials_total} total / {len(report.stone_materials)} stone")
    print(f"Sizes:        {len(report.sizes)}")
    print(f"Positions:    {report.positions_total} total / {report.stone_positions_sampled} active sampled")
    print()

    print("─── UNIT BREAKDOWN (stone materials) ───")
    for u, c in sorted(report.unit_breakdown.items(), key=lambda x: -x[1]):
        print(f"  {u or '(empty)':<10} {c}")
    print()

    print("─── TYPOLOGY BREAKDOWN (product_subtype) ───")
    for t, c in sorted(report.typology_breakdown.items(), key=lambda x: -x[1]):
        print(f"  {t or '(empty)':<12} {c}")
    print()

    print("─── SIZE SHAPE BREAKDOWN ───")
    for s, c in sorted(report.shape_breakdown.items(), key=lambda x: -x[1]):
        print(f"  {s or '(empty)':<12} {c}")
    print()

    sev = report.by_severity()
    print("─── ISSUES BY SEVERITY ───")
    print(f"  HIGH: {sev['HIGH']}")
    print(f"  MED:  {sev['MED']}")
    print(f"  LOW:  {sev['LOW']}")
    print()

    # Group by severity+entity
    by_group: dict[tuple, list[Issue]] = defaultdict(list)
    for i in report.issues:
        by_group[(i.severity, i.entity, i.field)].append(i)

    print("─── ISSUES (grouped) ───")
    for sev_level in (SEV_HIGH, SEV_MED, SEV_LOW):
        matching = [(k, v) for k, v in by_group.items() if k[0] == sev_level]
        if not matching:
            continue
        print(f"\n  [{sev_level}]")
        for (_, entity, fld), issues in sorted(matching, key=lambda x: -len(x[1])):
            print(f"    {entity}.{fld}: {len(issues)} cases")
            for i in issues[:3]:
                print(f"      • {i.entity_name[:60]}: {i.problem}")
                if i.hint:
                    print(f"        hint: {i.hint}")
            if len(issues) > 3:
                print(f"      ... +{len(issues) - 3} more")

    print()
    print("=" * 78)
    print(f"TOTAL: {len(report.issues)} issues found")
    print("=" * 78)
    print()

    # Top table — all stone materials with key fields
    print("─── STONE MATERIALS TABLE ───")
    print(f"  {'CODE':<8} {'NAME':<28} {'UNIT':<5} {'TYPOLOGY':<11} {'SIZE':<14} {'SHORT_NAME':<22}")
    for sm in report.stone_materials:
        print(
            f"  {(sm['code'] or '—'):<8} "
            f"{(sm['name'] or '—')[:27]:<28} "
            f"{(sm['unit'] or '—'):<5} "
            f"{(sm['typology'] or '—'):<11} "
            f"{(sm['size'] or '—')[:13]:<14} "
            f"{(sm['short_name'] or '—')[:21]:<22}"
        )


def _to_json_safe(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return float(obj)
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_json_safe(v) for v in obj]
    return obj


def print_json(report: Report) -> None:
    payload = {
        "db": report.db_url_host,
        "summary": {
            "materials_total": report.materials_total,
            "stone_materials": len(report.stone_materials),
            "sizes": len(report.sizes),
            "positions_total": report.positions_total,
            "positions_sampled": report.stone_positions_sampled,
            "by_severity": report.by_severity(),
        },
        "unit_breakdown": report.unit_breakdown,
        "typology_breakdown": report.typology_breakdown,
        "shape_breakdown": report.shape_breakdown,
        "stone_materials": report.stone_materials,
        "sizes": report.sizes,
        "issues": [asdict(i) for i in report.issues],
    }
    print(json.dumps(_to_json_safe(payload), ensure_ascii=False, indent=2))


# ── Main ────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Stone data integrity audit (read-only)")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of text")
    parser.add_argument("--sample", type=int, default=500,
                        help="Max active positions to sample (default 500)")
    args = parser.parse_args()

    db_url = _get_db_url()
    report = Report(db_url_host=_safe_host(db_url))
    engine = create_engine(db_url)

    try:
        with engine.connect() as conn:
            mat_by_id = audit_materials(conn, report)
            sizes_by_id = audit_sizes(conn, report)
            audit_positions(conn, report, sizes_by_id)
            audit_cross(conn, report, mat_by_id, sizes_by_id)
            audit_recipes(conn, report, mat_by_id)
            audit_transactions(conn, report)
    except Exception as e:
        print(f"ERROR connecting/querying DB: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    finally:
        engine.dispose()

    if args.json:
        print_json(report)
    else:
        print_report(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
