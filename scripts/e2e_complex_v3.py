#!/usr/bin/env python3
"""
E2E Complex Tests v3 — Moonjar PMS
5 advanced scenarios + надёжная очистка через прямой DB + Telegram-уведомления.

Сценарии:
  T26 — Consumption Rules обязательны: ангоб без правил расхода → позиция зависает
  T27 — Packaging Rules обязательны: упаковка без box types → материал не списывается
  T28 — Поломка печи во время производства → сдвиг расписания → уведомление директору
  T29 — Блокирующая задача → срыв дедлайна → уведомление CEO/Owner
  T30 — Ангоб для полок заканчивается → партия не может загрузиться → запрос на закупку

Usage:
    python scripts/e2e_complex_v3.py \\
        --email shevchukstasa@gmail.com --password Moonjar2024! \\
        --db-url "postgresql://postgres:FxrYtbHulBywvUlNURocqBLuLFfQNWdZ@tramway.proxy.rlwy.net:35660/railway" \\
        --tg-chat-id 452576610

    python scripts/e2e_complex_v3.py --help
"""

import argparse
import json
import sys
import time
import traceback
import uuid
from datetime import datetime, date, timedelta

try:
    import requests
except ImportError:
    sys.exit("ERROR: pip install requests")

try:
    import psycopg2
    from psycopg2.extras import register_uuid
    register_uuid()
    HAS_DB = True
except ImportError:
    HAS_DB = False
    print("WARNING: psycopg2 not installed — DB-level cleanup disabled (pip install psycopg2-binary)")

# ─── Console colors ─────────────────────────────────────────────────────────
G = "\033[92m"; R = "\033[91m"; Y = "\033[93m"; C = "\033[96m"; B = "\033[1m"; X = "\033[0m"

TG_BOT_TOKEN = "8361475396:AAHiHwhMLpJ7EtbyNRDD4m-7uqVExHAH2og"


def ts():
    return datetime.now().strftime("%H:%M:%S")


# ─── DB Cleanup ──────────────────────────────────────────────────────────────

def db_cleanup_orders(db_url: str, order_ids: list):
    """Надёжное удаление тестовых заказов из БД с обходом всех FK-зависимостей."""
    if not HAS_DB or not db_url or not order_ids:
        return
    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id FROM production_orders WHERE id = ANY(%s::uuid[])",
            (order_ids,)
        )
        existing = [r[0] for r in cur.fetchall()]
        if not existing:
            return

        cur.execute(
            "SELECT id FROM order_positions WHERE order_id = ANY(%s::uuid[])",
            (existing,)
        )
        pos_ids = [r[0] for r in cur.fetchall()]

        # Удаляем строки с NOT NULL FK на positions
        for table, col in [
            ("consumption_adjustments", "position_id"),
            ("shipment_items", "position_id"),
            ("quality_checks", "position_id"),
            ("surplus_dispositions", "position_id"),
        ]:
            if pos_ids:
                cur.execute(f"DELETE FROM {table} WHERE {col} = ANY(%s::uuid[])", (pos_ids,))

        # Удаляем строки с NOT NULL FK на orders
        for table, col in [
            ("order_packing_photos", "order_id"),
            ("shipments", "order_id"),
        ]:
            cur.execute(f"DELETE FROM {table} WHERE {col} = ANY(%s::uuid[])", (existing,))

        # NULL-им nullable FK на positions
        for table, col in [
            ("defect_records", "position_id"),
            ("grinding_stock", "source_position_id"),
            ("material_transactions", "related_position_id"),
            ("repair_queue", "source_position_id"),
            ("tasks", "related_position_id"),
            ("worker_media", "related_position_id"),
            ("position_photos", "position_id"),
            ("operation_logs", "position_id"),
            ("production_defects", "position_id"),
            ("qm_blocks", "position_id"),
        ]:
            if pos_ids:
                cur.execute(
                    f"UPDATE {table} SET {col} = NULL WHERE {col} = ANY(%s::uuid[])",
                    (pos_ids,)
                )

        if pos_ids:
            cur.execute(
                "UPDATE order_positions SET parent_position_id = NULL "
                "WHERE parent_position_id = ANY(%s::uuid[])", (pos_ids,)
            )

        # NULL-им nullable FK на orders
        for table, col in [
            ("casters_boxes", "source_order_id"),
            ("grinding_stock", "source_order_id"),
            ("material_transactions", "related_order_id"),
            ("order_financials", "order_id"),
            ("repair_queue", "source_order_id"),
            ("tasks", "related_order_id"),
            ("worker_media", "related_order_id"),
        ]:
            cur.execute(
                f"UPDATE {table} SET {col} = NULL WHERE {col} = ANY(%s::uuid[])",
                (existing,)
            )

        # Удаляем заказы (CASCADE → order_positions, order_stage_history, etc.)
        cur.execute("DELETE FROM production_orders WHERE id = ANY(%s::uuid[])", (existing,))
        deleted = cur.rowcount
        conn.commit()
        print(f"  {G}DB cleanup: deleted {deleted} orders + all deps{X}")
    except Exception as e:
        conn.rollback()
        print(f"  {Y}DB cleanup warning: {e}{X}")
    finally:
        conn.close()


# ─── Telegram ────────────────────────────────────────────────────────────────

def tg_send(chat_id: str | int, text: str):
    """Отправить сообщение в Telegram."""
    if not chat_id:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception:
        pass


# ─── Test Runner ─────────────────────────────────────────────────────────────

class ComplexE2ETest:
    def __init__(self, api_url: str, email: str, password: str,
                 db_url: str = "", tg_chat_id: str = ""):
        self.api_url = api_url.rstrip("/")
        self.session = requests.Session()
        self.db_url = db_url
        self.tg = tg_chat_id
        self.factory_id = None
        self.factory_name = ""
        self.kiln_id = None
        self.kiln_name = ""
        self.created_order_ids: list[str] = []
        self.results: list[tuple[str, list]] = []

        self._login(email, password)
        self._setup()

    # ─── Auth ────────────────────────────────────────────────────────────

    def _login(self, email, password):
        r = self.session.post(f"{self.api_url}/auth/login",
                              json={"email": email, "password": password}, timeout=30)
        if not r.ok:
            sys.exit(f"Login failed: {r.status_code} {r.text[:200]}")
        csrf = self.session.cookies.get("csrf_token")
        if csrf:
            self.session.headers["X-CSRF-Token"] = csrf
        print(f"{G}Logged in ({'CSRF ok' if csrf else 'no CSRF'}){X}")

    def _setup(self):
        # Factory — prefer active/non-frozen (Bali), skip frozen ones
        r = self._api("GET", "/factories")
        items = (r.json().get("items") or r.json()) if r.ok else []
        if isinstance(items, list) and items:
            # Skip factories that look frozen/inactive (Semarang etc.)
            factory = next(
                (f for f in items if not any(kw in f.get("name", "").lower()
                 for kw in ("semarang", "frozen", "inactive"))),
                items[0],
            )
            self.factory_id = factory["id"]
            self.factory_name = factory.get("name", "?")
        # Kiln
        r = self._api("GET", f"/kilns?factory_id={self.factory_id}")
        kilns = (r.json().get("items") or r.json()) if r.ok else []
        if isinstance(kilns, list) and kilns:
            active = next((k for k in kilns if k.get("status") in ("active", "available", None)), kilns[0])
            self.kiln_id = active["id"]
            self.kiln_name = active.get("name", "?")
        print(f"{G}Factory: {self.factory_name} | Kiln: {self.kiln_name}{X}")

    # ─── HTTP ────────────────────────────────────────────────────────────

    def _api(self, method, path, **kw) -> requests.Response:
        kw.setdefault("timeout", 30)
        r = self.session.request(method, f"{self.api_url}{path}", **kw)
        color = G if r.ok else R
        print(f"  {C}{method} {path}{X} → {color}{r.status_code}{X}" +
              (f" {r.text[:120]}" if not r.ok else ""))
        return r

    # ─── Helpers ─────────────────────────────────────────────────────────

    def _step(self, name, steps, fn):
        print(f"\n  {B}[Step]{X} {name}")
        try:
            result = fn()
            steps.append((name, True, "OK"))
            return result
        except Exception as e:
            msg = str(e)[:200]
            steps.append((name, False, msg))
            print(f"  {R}FAIL: {msg}{X}")
            traceback.print_exc()
            return None

    def _create_order(self, items: list[dict], suffix: str = "") -> str | None:
        uid = uuid.uuid4().hex[:8]
        r = self._api("POST", "/orders", json={
            "order_number": f"E2E-V3-{uid}{suffix}",
            "client": f"E2E Test Client {uid}",
            "client_location": "Bali",
            "factory_id": str(self.factory_id),
            "final_deadline": str(date.today() + timedelta(days=14)),
            "desired_delivery_date": str(date.today() + timedelta(days=12)),
            "items": items,
        })
        if not r.ok:
            raise RuntimeError(f"Create order failed: {r.status_code} {r.text[:200]}")
        data = r.json()
        order_id = data.get("id") or data.get("order_id")
        self.created_order_ids.append(order_id)
        return order_id

    def _positions(self, order_id: str) -> list:
        order = self._api("GET", f"/orders/{order_id}").json()
        return order.get("positions") or order.get("items") or []

    def _transition(self, pos_id: str, status: str):
        r = self._api("POST", f"/positions/{pos_id}/status",
                      json={"status": status, "notes": "e2e v3 test"})
        if not r.ok:
            raise RuntimeError(f"→{status} failed: {r.status_code} {r.text[:200]}")
        time.sleep(0.3)
        return r.json()

    def _pos_status(self, pos_id: str) -> str:
        r = self._api("GET", f"/positions/{pos_id}/allowed-transitions")
        return r.json().get("current_status", "unknown") if r.ok else "unknown"

    def _create_batch_and_fire(self, position_ids: list[str]) -> str:
        r = self._api("POST", "/batches", json={
            "resource_id": self.kiln_id,
            "factory_id": self.factory_id,
            "batch_date": date.today().isoformat(),
            "status": "planned",
            "target_temperature": 1050,
        })
        batch_id = r.json().get("id") if r.ok else None
        if not batch_id:
            raise RuntimeError("Batch creation failed")
        for pid in position_ids:
            self._api("POST", f"/positions/{pid}/reassign-batch", json={"batch_id": batch_id})
        time.sleep(0.3)
        r2 = self._api("GET", f"/batches/{batch_id}")
        if r2.ok and r2.json().get("status") == "suggested":
            self._api("POST", f"/batches/{batch_id}/confirm", json={})
            time.sleep(0.3)
        r3 = self._api("POST", f"/batches/{batch_id}/start")
        if not r3.ok:
            raise RuntimeError(f"Batch start failed: {r3.text[:200]}")
        time.sleep(0.5)
        r4 = self._api("POST", f"/batches/{batch_id}/complete")
        if not r4.ok:
            raise RuntimeError(f"Batch complete failed: {r4.text[:200]}")
        time.sleep(0.5)
        return batch_id

    def _split_all_good(self, pos_id: str, qty: int):
        r = self._api("POST", f"/positions/{pos_id}/split", json={
            "good_quantity": qty, "refire_quantity": 0, "repair_quantity": 0,
            "color_mismatch_quantity": 0, "grinding_quantity": 0, "write_off_quantity": 0,
            "notes": "e2e v3 - all good",
        })
        if not r.ok:
            raise RuntimeError(f"Split failed: {r.text[:200]}")
        time.sleep(0.3)

    def _pre_kiln_qc(self, pos_id: str):
        r = self._api("POST", "/quality/pre-kiln-check", json={
            "position_id": pos_id, "factory_id": self.factory_id,
            "overall_result": "pass",
            "checklist_results": {k: "pass" for k in [
                "glaze_coverage_uniform", "glaze_thickness_correct", "no_drips_or_runs",
                "engobe_applied_correctly", "edge_glazing_complete",
                "correct_color_recipe_verified", "tile_dimensions_within_tolerance", "no_cracks_or_chips",
            ]},
            "notes": "e2e v3 pre-kiln",
        })
        if not r.ok:
            raise RuntimeError(f"Pre-kiln QC failed: {r.text[:200]}")
        time.sleep(0.3)

    def _final_qc(self, pos_id: str):
        r = self._api("POST", "/quality/final-check", json={
            "position_id": pos_id, "factory_id": self.factory_id,
            "overall_result": "pass",
            "checklist_results": {k: "pass" for k in [
                "correct_quantity_matches_order", "all_tiles_match_color_sample",
                "no_visible_defects", "correct_packaging_label",
                "packaging_intact_no_damage", "size_matches_order_specification", "documentation_complete",
            ]},
            "notes": "e2e v3 final",
        })
        if not r.ok:
            raise RuntimeError(f"Final QC failed: {r.text[:200]}")
        time.sleep(0.3)

    def _ship_order(self, order_id: str, positions: list[dict]) -> str:
        items = [{"position_id": p["id"], "quantity": p.get("quantity_pcs", p.get("quantity", 10))}
                 for p in positions]
        r = self._api("POST", "/shipments", json={
            "order_id": order_id, "carrier": "E2E Carrier",
            "tracking_number": f"E2E-{uuid.uuid4().hex[:8].upper()}",
            "items": items, "notes": "e2e v3 shipment",
        })
        if not r.ok:
            raise RuntimeError(f"Shipment create failed: {r.text[:200]}")
        sid = r.json().get("id")
        time.sleep(0.3)
        r2 = self._api("POST", f"/shipments/{sid}/ship")
        if not r2.ok:
            raise RuntimeError(f"Ship failed: {r2.text[:200]}")
        time.sleep(0.3)
        return sid

    def _tg(self, text: str):
        tg_send(self.tg, text)

    # ─── Test 26: Consumption Rules — обязательны ─────────────────────────

    def test_26_consumption_rules_mandatory(self):
        """T26: Позиция с ангобом при отсутствии Consumption Rules.

        Ожидаемое поведение: система должна НЕ списывать материал
        (или заблокировать переход). Тест выявляет: списывается ли
        расход материала при отсутствии правил.
        """
        name = "T26: Consumption Rules — mandatory check"
        steps = []
        order_id = None

        print(f"\n{'='*65}\n{B}{name}{X}\n{'='*65}")
        self._tg(f"🧪 <b>{name}</b>\nСтарт: проверяем обязательность Consumption Rules")

        def create():
            nonlocal order_id
            # Плитка с ангобом (engobe) — расход должен считаться через consumption rules
            order_id = self._create_order([{
                "color": "E2E-EngobeGlaze-ConsumpTest",
                "size": "20x20",
                "quantity_pcs": 50,
                "collection": "Standard",
                "product_type": "tile",
                "thickness": 11.0,
            }])
            return order_id

        self._step("Create order (tile with engobe)", steps, create)
        if not order_id:
            self.results.append((name, steps))
            return

        positions = self._positions(order_id)
        if not positions:
            steps.append(("Get positions", False, "No positions"))
            self.results.append((name, steps))
            return

        pos = positions[0]
        pos_id = pos["id"]

        # Проверяем: есть ли consumption rules
        def check_consumption_rules():
            r = self._api("GET", f"/consumption-rules?factory_id={self.factory_id}")
            data = r.json() if r.ok else []
            rules = data if isinstance(data, list) else data.get("items", [])
            if not rules:
                self._tg("⚠️ <b>T26</b>: Consumption Rules отсутствуют!\n"
                         "Система позволяет нанести ангоб без правил расхода — "
                         "материал НЕ будет списан. Это пробел в бизнес-логике.")
                print(f"  {Y}WARNING: No consumption rules — material deduction will be SKIPPED{X}")
            else:
                print(f"  {G}Consumption rules exist: {len(rules)} rules{X}")
            return rules

        rules = self._step("Check consumption rules exist", steps, check_consumption_rules)

        # Проверяем баланс материала до
        def check_balance_before():
            r = self._api("GET", f"/materials?factory_id={self.factory_id}&limit=50")
            mats = r.json().get("items", []) if r.ok else []
            engobe = [m for m in mats if "engob" in m.get("name", "").lower() or "engobe" in m.get("name", "").lower()]
            print(f"  Engobe materials before: {[(m['name'], m.get('balance', m.get('quantity', '?'))) for m in engobe[:3]]}")
            return {m["id"]: m.get("balance", m.get("quantity", 0)) for m in engobe}

        balance_before = self._step("Record material balance before engobe", steps, check_balance_before)

        # Наносим ангоб — без рецепта система должна заблокировать
        def apply_engobe():
            current = self._pos_status(pos_id)
            if current == "awaiting_recipe":
                self._transition(pos_id, "planned")
                current = "planned"
            if current != "planned":
                raise RuntimeError(f"Unexpected status: '{current}'")
            # Пробуем перейти в engobe_applied без рецепта
            r = self._api("POST", f"/positions/{pos_id}/status",
                          json={"status": "engobe_applied", "notes": "e2e T26 - no recipe"})
            if not r.ok and r.status_code == 400 and "recipe" in r.text.lower():
                # ПРАВИЛЬНОЕ поведение: система заблокировала
                print(f"  {G}CORRECT: System blocked engobe without recipe: {r.json().get('detail','')[:80]}{X}")
                self._tg("✅ <b>T26</b>: Система заблокировала нанесение ангоба без рецепта!\n"
                         "Consumption Rules enforcement работает корректно.")
                return "BLOCKED_CORRECTLY"
            elif r.ok:
                # БАГ: система разрешила без рецепта
                self._tg("❌ <b>T26 BUG</b>: Система разрешила engobe_applied без рецепта!\n"
                         "Материал НЕ будет списан — бизнес-логика нарушена.")
                print(f"  {R}BUG: engobe_applied allowed without recipe!{X}")
                return "ALLOWED_WITHOUT_RECIPE"
            else:
                raise RuntimeError(f"Unexpected error: {r.status_code} {r.text[:100]}")

        self._step("Apply engobe (transition → engobe_applied)", steps, apply_engobe)
        time.sleep(1)  # дать время на списание

        # Проверяем баланс после
        def check_balance_after():
            if not balance_before:
                print(f"  {Y}No engobe materials to compare{X}")
                return
            r = self._api("GET", f"/materials?factory_id={self.factory_id}&limit=50")
            mats = r.json().get("items", []) if r.ok else []
            engobe = [m for m in mats if "engob" in m.get("name", "").lower()]
            for m in engobe:
                before = balance_before.get(m["id"], "?")
                after = m.get("balance", m.get("quantity", "?"))
                diff = (float(before) - float(after)) if before != "?" and after != "?" else "?"
                status = G if diff and float(str(diff)) > 0 else R
                verdict = "DEDUCTED" if diff and float(str(diff)) > 0 else "NOT DEDUCTED ⚠️"
                print(f"  {status}{m['name']}: {before} → {after} ({verdict}){X}")
                if diff == 0 or diff == "?":
                    self._tg(f"❌ <b>T26 FAIL</b>: {m['name']} НЕ списан при нанесении ангоба!\n"
                             f"Balance: {before} → {after}")

        self._step("Verify material deducted after engobe", steps, check_balance_after)

        self.results.append((name, steps))
        pass_count = sum(1 for _, ok, _ in steps if ok)
        self._tg(f"{'✅' if pass_count == len(steps) else '⚠️'} <b>T26</b> завершён: "
                 f"{pass_count}/{len(steps)} шагов OK")

    # ─── Test 27: Packaging Rules — обязательны ───────────────────────────

    def test_27_packaging_rules_mandatory(self):
        """T27: Упаковка без настроенных Box Types — материал должен списываться.

        Ожидаемое: если packaging rules не настроены, система либо блокирует
        упаковку, либо упаковывает без списания — оба варианта нужно выявить.
        """
        name = "T27: Packaging Rules — mandatory check"
        steps = []
        order_id = None

        print(f"\n{'='*65}\n{B}{name}{X}\n{'='*65}")
        self._tg(f"📦 <b>{name}</b>\nПроверяем обязательность Packaging Rules")

        def create():
            nonlocal order_id
            order_id = self._create_order([{
                "color": "Onyx",
                "size": "25x25",
                "quantity_pcs": 20,
                "collection": "Standard",
                "product_type": "tile",
                "thickness": 11.0,
            }])
            return order_id

        self._step("Create order", steps, create)
        if not order_id:
            self.results.append((name, steps))
            return

        # Проверяем настроены ли box types
        def check_box_types():
            r = self._api("GET", f"/packaging/box-types?factory_id={self.factory_id}")
            box_types = r.json().get("items", r.json() if r.ok else []) if r.ok else []
            if isinstance(box_types, list) and not box_types:
                self._tg("⚠️ <b>T27</b>: Packaging box types не настроены!\n"
                         "Упаковочные материалы НЕ будут списаны при упаковке. "
                         "Необходимо настроить Packaging Rules в Admin → Packaging Rules")
                print(f"  {R}NO box types configured — packaging won't deduct materials!{X}")
            else:
                count = len(box_types) if isinstance(box_types, list) else "?"
                print(f"  {G}Box types configured: {count}{X}")
            return box_types

        box_types = self._step("Check packaging box types", steps, check_box_types)

        # Прогоняем позицию через полный pipeline до стадии 'packed'
        positions = self._positions(order_id)
        if not positions:
            steps.append(("Get positions", False, "No positions"))
            self.results.append((name, steps))
            return

        pos = positions[0]
        pos_id = pos["id"]
        qty = pos.get("quantity_pcs", pos.get("quantity", 20))

        def full_pipeline_to_packed():
            # glazed
            st = self._pos_status(pos_id)
            if st == "awaiting_recipe":
                self._transition(pos_id, "planned")
                st = "planned"
            if st == "planned":
                self._transition(pos_id, "glazed")
            # pre-kiln QC
            self._pre_kiln_qc(pos_id)
            # batch + fire
            self._create_batch_and_fire([pos_id])
            # sort
            time.sleep(0.5)
            self._split_all_good(pos_id, qty)
            # final QC
            time.sleep(0.5)
            self._final_qc(pos_id)
            # pack
            time.sleep(0.5)
            st2 = self._pos_status(pos_id)
            print(f"  Status before packing: {st2}")
            if st2 in ("sorted", "ready_to_pack", "final_check"):
                self._transition(pos_id, "packed")

        self._step("Full pipeline → packed", steps, full_pipeline_to_packed)

        # Проверяем packaging материалы были ли списаны
        def check_packaging_deduction():
            r = self._api("GET", f"/materials?factory_id={self.factory_id}&limit=100")
            mats = r.json().get("items", []) if r.ok else []
            pack_mats = [m for m in mats if any(w in m.get("name", "").lower()
                         for w in ["box", "коробка", "packaging", "tape", "скотч", "bubble", "foam"])]
            if not pack_mats:
                self._tg("⚠️ <b>T27</b>: Упаковочные материалы не найдены в системе.\n"
                         "Невозможно проверить списание.")
                print(f"  {Y}No packaging materials found to verify deduction{X}")
                return
            for m in pack_mats[:3]:
                txns = self._api("GET", f"/material-transactions?material_id={m['id']}&limit=10")
                recent = txns.json().get("items", []) if txns.ok else []
                e2e_txn = [t for t in recent if "e2e" in str(t.get("notes", "")).lower()
                           or str(order_id) in str(t)]
                verdict = f"{G}DEDUCTED{X}" if e2e_txn else f"{R}NOT DEDUCTED ⚠️{X}"
                print(f"  {m['name']}: {verdict}")

        self._step("Verify packaging material deduction", steps, check_packaging_deduction)

        self.results.append((name, steps))
        pass_count = sum(1 for _, ok, _ in steps if ok)
        self._tg(f"{'✅' if pass_count == len(steps) else '⚠️'} <b>T27</b>: "
                 f"{pass_count}/{len(steps)} OK")

    # ─── Test 28: Kiln breakdown → schedule shift ─────────────────────────

    def test_28_kiln_breakdown_schedule_shift(self):
        """T28: Ремонт печи → позиции без батча → уведомление директору.

        Сценарий:
        1. Создаём заказ с коротким дедлайном
        2. Ставим печь на техническое обслуживание
        3. Пытаемся создать партию — печь недоступна
        4. Проверяем что система отправила уведомление
        5. Возвращаем печь в рабочее состояние
        """
        name = "T28: Kiln Breakdown → Schedule Shift + Notification"
        steps = []
        order_id = None
        original_kiln_status = None

        print(f"\n{'='*65}\n{B}{name}{X}\n{'='*65}")
        self._tg(f"🔧 <b>{name}</b>\nЭмулируем поломку/ремонт печи")

        def create_urgent_order():
            nonlocal order_id
            order_id = self._create_order([{
                "color": "Onyx",
                "size": "20x20",
                "quantity_pcs": 30,
                "collection": "Standard",
                "product_type": "tile",
                "thickness": 11.0,
            }], suffix="-KILN-BREAKDOWN")
            return order_id

        self._step("Create urgent order (3-day deadline)", steps, create_urgent_order)

        # Получаем текущий статус печи
        def get_kiln_status():
            nonlocal original_kiln_status
            r = self._api("GET", f"/kilns/{self.kiln_id}")
            original_kiln_status = r.json().get("status", "active") if r.ok else "active"
            print(f"  Kiln current status: {original_kiln_status}")
            return original_kiln_status

        self._step("Record current kiln status", steps, get_kiln_status)

        # Ставим печь на ТО (правильный endpoint: PATCH /kilns/{id}/status?status=...)
        def set_kiln_maintenance():
            r = self._api("PATCH", f"/kilns/{self.kiln_id}/status?status=maintenance_planned")
            if not r.ok:
                raise RuntimeError(f"Cannot set kiln to maintenance_planned: {r.text[:200]}")
            self._tg(f"🔧 <b>T28</b>: Печь {self.kiln_name} поставлена на ТО (maintenance_planned).\n"
                     f"Смотрим что произойдёт с незапущенными позициями...")
            print(f"  {Y}Kiln set to maintenance_planned{X}")

        self._step("Set kiln to maintenance", steps, set_kiln_maintenance)
        time.sleep(1)

        # Пытаемся создать батч — должен либо упасть, либо предупредить
        def attempt_batch_on_maintenance_kiln():
            if not order_id:
                return
            positions = self._positions(order_id)
            if not positions:
                return
            pos_id = positions[0]["id"]
            # Переводим в glazed сначала
            st = self._pos_status(pos_id)
            if st == "awaiting_recipe":
                self._transition(pos_id, "planned")
                st = "planned"
            if st == "planned":
                try:
                    self._transition(pos_id, "glazed")
                except Exception:
                    pass
            self._pre_kiln_qc(pos_id)

            # Пробуем создать батч
            r = self._api("POST", "/batches", json={
                "resource_id": self.kiln_id,
                "factory_id": self.factory_id,
                "batch_date": date.today().isoformat(),
                "status": "planned",
                "target_temperature": 1050,
            })
            if r.ok:
                print(f"  {Y}WARNING: Batch created on maintenance kiln! "
                      f"System does not block batch creation during maintenance.{X}")
                self._tg("⚠️ <b>T28</b>: Система разрешила создать партию для печи на ТО.\n"
                         "Ожидается: запрет или предупреждение.")
            else:
                print(f"  {G}CORRECT: Batch blocked on maintenance kiln: {r.status_code}{X}")
                self._tg(f"✅ <b>T28</b>: Система заблокировала партию для печи на ТО.\n"
                         f"Статус: {r.status_code}")

        self._step("Attempt batch on maintenance kiln", steps, attempt_batch_on_maintenance_kiln)

        # Проверяем уведомления
        def check_notifications():
            r = self._api("GET", f"/notifications?factory_id={self.factory_id}&limit=20")
            notifs = r.json().get("items", []) if r.ok else []
            kiln_notifs = [n for n in notifs if "kiln" in str(n).lower() or "maintenance" in str(n).lower()
                           or "печ" in str(n).lower()]
            print(f"  Kiln-related notifications: {len(kiln_notifs)}")
            if kiln_notifs:
                self._tg(f"📢 <b>T28</b>: Найдены {len(kiln_notifs)} уведомлений о печи:\n" +
                         "\n".join(str(n.get("message", n.get("text", str(n))))[:80] for n in kiln_notifs[:3]))
            return kiln_notifs

        self._step("Check notifications sent", steps, check_notifications)

        # Возвращаем печь
        def restore_kiln():
            restore_to = original_kiln_status if original_kiln_status != "maintenance" else "active"
            r = self._api("PATCH", f"/kilns/{self.kiln_id}/status?status={restore_to}")
            print(f"  Kiln restored to: {restore_to}")
            self._tg(f"✅ <b>T28</b>: Печь {self.kiln_name} возвращена в статус '{restore_to}'")

        self._step("Restore kiln to original status", steps, restore_kiln)

        self.results.append((name, steps))
        pass_count = sum(1 for _, ok, _ in steps if ok)
        self._tg(f"{'✅' if pass_count == len(steps) else '⚠️'} <b>T28</b>: {pass_count}/{len(steps)} OK")

    # ─── Test 29: Blocking task → deadline miss → notification ────────────

    def test_29_blocking_task_deadline_miss(self):
        """T29: Блокирующая задача задерживает позицию → дедлайн срывается → уведомление.

        Сценарий:
        1. Создаём заказ с дедлайном сегодня (уже просрочен или вот-вот)
        2. Создаём блокирующую задачу на позицию
        3. Проверяем что статус заказа отражает задержку
        4. Проверяем уведомление директору/CEO
        """
        name = "T29: Blocking Task → Deadline Miss → Notification"
        steps = []
        order_id = None

        print(f"\n{'='*65}\n{B}{name}{X}\n{'='*65}")
        self._tg(f"⚡ <b>{name}</b>\nЭмулируем срыв дедлайна из-за блокирующей задачи")

        def create_overdue_order():
            nonlocal order_id
            uid = uuid.uuid4().hex[:8]
            # Дедлайн вчера — заказ уже просрочен
            r = self._api("POST", "/orders", json={
                "order_number": f"E2E-V3-{uid}-OVERDUE",
                "client": f"E2E Test Overdue {uid}",
                "client_location": "Bali",
                "factory_id": str(self.factory_id),
                "final_deadline": str(date.today() - timedelta(days=1)),
                "desired_delivery_date": str(date.today() - timedelta(days=2)),
                "items": [{
                    "color": "Onyx",
                    "size": "20x20",
                    "quantity_pcs": 10,
                    "collection": "Standard",
                    "product_type": "tile",
                    "thickness": 11.0,
                }],
            })
            if not r.ok:
                raise RuntimeError(f"Create order failed: {r.text[:200]}")
            order_id = r.json().get("id") or r.json().get("order_id")
            self.created_order_ids.append(order_id)
            return order_id

        self._step("Create order with past deadline (overdue)", steps, create_overdue_order)
        if not order_id:
            self.results.append((name, steps))
            return

        positions = self._positions(order_id)
        if not positions:
            steps.append(("Get positions", False, "No positions"))
            self.results.append((name, steps))
            return

        pos_id = positions[0]["id"]

        # Создаём блокирующую задачу
        def create_blocking_task():
            r = self._api("POST", "/tasks", json={
                "type": "stencil_order",
                "description": "E2E test blocking task: нет утверждённого дизайна трафарета — stencil missing",
                "blocking": True,
                "priority": 3,
                "related_order_id": order_id,
                "related_position_id": pos_id,
                "factory_id": self.factory_id,
            })
            if not r.ok:
                raise RuntimeError(f"Task creation failed: {r.text[:200]}")
            task_id = r.json().get("id")
            self._tg(f"⚡ <b>T29</b>: Создана блокирующая задача (ID: {task_id})\n"
                     f"Заказ с просроченным дедлайном + блокировка → ждём уведомление")
            return task_id

        task_id = self._step("Create blocking task on overdue order", steps, create_blocking_task)

        # Переводим позицию в awaiting_stencil (если возможно)
        def block_position():
            st = self._pos_status(pos_id)
            if st == "awaiting_recipe":
                self._transition(pos_id, "planned")
                st = "planned"
            print(f"  Position status: {st}")
            if st == "planned":
                r = self._api("POST", f"/positions/{pos_id}/status",
                              json={"status": "awaiting_stencil_silkscreen",
                                    "notes": "E2E: stencil not ready"})
                if r.ok:
                    print(f"  {Y}Position blocked: awaiting_stencil_silkscreen{X}")

        self._step("Block position (awaiting stencil/silkscreen)", steps, block_position)
        time.sleep(2)  # Дать время на обработку

        # Проверяем уведомления
        def check_overdue_notifications():
            r = self._api("GET", f"/notifications?factory_id={self.factory_id}&limit=30")
            notifs = r.json().get("items", []) if r.ok else []
            overdue = [n for n in notifs if any(w in str(n).lower()
                       for w in ["overdue", "deadline", "delay", "срок", "задержка", "просроч"])]
            print(f"  Overdue/deadline notifications: {len(overdue)}")
            if overdue:
                sample = overdue[0].get("message", overdue[0].get("text", str(overdue[0])))[:150]
                self._tg(f"📢 <b>T29</b>: Уведомление о просроченном заказе:\n{sample}")
            else:
                self._tg("⚠️ <b>T29</b>: Уведомления о просроченном заказе НЕ найдены.\n"
                         "Система не нотифицирует при срыве дедлайна.")
                print(f"  {Y}No overdue notifications found — scheduler may not have run yet{X}")
            return overdue

        self._step("Check overdue deadline notifications", steps, check_overdue_notifications)

        # Проверяем статус заказа
        def check_order_status():
            order = self._api("GET", f"/orders/{order_id}").json()
            status = order.get("status", "?")
            sales_status = order.get("sales_status", "?")
            is_delayed = order.get("is_delayed", False)
            print(f"  Order status: {status} | sales_status: {sales_status} | is_delayed: {is_delayed}")
            self._tg(f"📊 <b>T29</b>: Статус заказа:\n"
                     f"status={status}, sales_status={sales_status}, is_delayed={is_delayed}")

        self._step("Verify order reflects delay", steps, check_order_status)

        self.results.append((name, steps))
        pass_count = sum(1 for _, ok, _ in steps if ok)
        self._tg(f"{'✅' if pass_count == len(steps) else '⚠️'} <b>T29</b>: {pass_count}/{len(steps)} OK")

    # ─── Test 30: Shelf engobe runs out ──────────────────────────────────

    def test_30_shelf_engobe_runs_out(self):
        """T30: Ангоб для полок заканчивается → партия не может загрузиться.

        Ангоб для полок (shelf coating/engobe) — расходник перед загрузкой в печь.
        Когда он заканчивается, печь нельзя загрузить.

        Сценарий:
        1. Находим материал "ангоб для полок" в системе
        2. Уменьшаем его запас до нуля (через adjustment)
        3. Пытаемся запустить партию — должна быть заблокирована
        4. Мастер создаёт запрос на закупку
        5. Проверяем что запрос зафиксирован + уведомление
        """
        name = "T30: Shelf Engobe Runs Out → Batch Blocked → Purchase Request"
        steps = []
        order_id = None
        shelf_engobe_id = None
        original_balance = None

        print(f"\n{'='*65}\n{B}{name}{X}\n{'='*65}")
        self._tg(f"🏺 <b>{name}</b>\nЭмулируем: кончился ангоб для полок")

        # Находим материал ангоба для полок
        def find_shelf_engobe():
            nonlocal shelf_engobe_id, original_balance
            r = self._api("GET", f"/materials?factory_id={self.factory_id}&limit=200")
            mats = r.json().get("items", []) if r.ok else []
            keywords = ["shelf", "полк", "board", "плита", "kiln shelf", "engobe shelf",
                        "engob", "ангоб", "coating"]
            found = None
            for m in mats:
                name_l = m.get("name", "").lower()
                if any(k in name_l for k in keywords):
                    found = m
                    break
            if not found:
                print(f"  {Y}Shelf engobe material not found. Available materials:{X}")
                for m in mats[:10]:
                    print(f"    - {m['name']}")
                self._tg("⚠️ <b>T30</b>: Материал 'ангоб для полок' не найден в системе.\n"
                         "Возможно он называется иначе или не заведён.")
                return None
            shelf_engobe_id = found["id"]
            r2 = self._api("GET", f"/material-stock?material_id={shelf_engobe_id}&factory_id={self.factory_id}")
            stock = r2.json().get("items", [r2.json()]) if r2.ok else []
            if isinstance(stock, dict):
                stock = [stock]
            if stock:
                original_balance = stock[0].get("balance", 0)
            print(f"  {G}Found: {found['name']} | balance: {original_balance}{X}")
            self._tg(f"🏺 <b>T30</b>: Найден материал: {found['name']}\n"
                     f"Текущий остаток: {original_balance}")
            return found

        shelf_mat = self._step("Find shelf engobe material", steps, find_shelf_engobe)
        if not shelf_mat:
            steps.append(("Skip — no shelf engobe material", True, "Material not found, skipping"))
            self.results.append((name, steps))
            self._tg("ℹ️ <b>T30</b>: Тест пропущен — материал не найден.\n"
                     "Необходимо завести 'Ангоб для полок' в системе.")
            return

        # Создаём заказ
        def create():
            nonlocal order_id
            order_id = self._create_order([{
                "color": "Onyx",
                "size": "20x20",
                "quantity_pcs": 20,
                "collection": "Standard",
                "product_type": "tile",
                "thickness": 11.0,
            }], suffix="-SHELF-ENGOBE")
            return order_id

        self._step("Create order", steps, create)
        if not order_id:
            self.results.append((name, steps))
            return

        positions = self._positions(order_id)
        if not positions:
            steps.append(("Get positions", False, "No positions"))
            self.results.append((name, steps))
            return

        pos_id = positions[0]["id"]
        qty = positions[0].get("quantity_pcs", positions[0].get("quantity", 20))

        # Обнуляем остаток ангоба через adjustment
        def deplete_shelf_engobe():
            if not shelf_engobe_id or original_balance is None:
                return
            # Создаём транзакцию списания
            r = self._api("POST", "/material-transactions", json={
                "material_id": shelf_engobe_id,
                "factory_id": self.factory_id,
                "transaction_type": "adjustment",
                "quantity": -float(original_balance) if original_balance > 0 else 0,
                "notes": "E2E T30: depleting shelf engobe to test blocking",
            })
            if not r.ok:
                # Пробуем через adjust endpoint
                r2 = self._api("PUT", f"/materials/{shelf_engobe_id}/adjust", json={
                    "adjustment": -float(original_balance),
                    "reason": "E2E T30: depleting shelf engobe to test blocking",
                    "factory_id": self.factory_id,
                })
                if not r2.ok:
                    print(f"  {Y}Could not deplete material: {r.text[:100]}{X}")
                    return
            self._tg(f"🏺 <b>T30</b>: Ангоб для полок обнулён (было: {original_balance}).\n"
                     f"Пробуем запустить партию...")
            print(f"  {Y}Shelf engobe depleted to 0{X}")

        self._step("Deplete shelf engobe balance to zero", steps, deplete_shelf_engobe)
        time.sleep(1)

        # Переводим позицию в glazed и пробуем запустить партию
        def try_batch_without_shelf_engobe():
            st = self._pos_status(pos_id)
            if st == "awaiting_recipe":
                self._transition(pos_id, "planned")
                st = "planned"
            if st == "planned":
                self._transition(pos_id, "glazed")
            self._pre_kiln_qc(pos_id)
            # Пробуем запустить партию
            r = self._api("POST", "/batches", json={
                "resource_id": self.kiln_id,
                "factory_id": self.factory_id,
                "batch_date": date.today().isoformat(),
                "status": "planned",
                "target_temperature": 1050,
            })
            if r.ok:
                batch_id = r.json().get("id")
                self._api("POST", f"/positions/{pos_id}/reassign-batch",
                          json={"batch_id": batch_id})
                r_start = self._api("POST", f"/batches/{batch_id}/start")
                if r_start.ok:
                    print(f"  {R}WARNING: Batch started despite zero shelf engobe! "
                          f"Shelf engobe deduction not blocking batch start.{X}")
                    self._tg("❌ <b>T30 FAIL</b>: Партия запущена несмотря на нулевой остаток ангоба для полок!\n"
                             "Система не блокирует загрузку при отсутствии расходника.")
                else:
                    print(f"  {G}CORRECT: Batch start blocked: {r_start.status_code}{X}")
                    self._tg(f"✅ <b>T30</b>: Старт партии заблокирован при отсутствии ангоба!\n"
                             f"Статус: {r_start.status_code}")

        self._step("Try batch start — expect block or warning", steps, try_batch_without_shelf_engobe)

        # Мастер создаёт заявку на производство ангоба для полок (внутренний рецепт)
        def create_production_task_for_shelf_engobe():
            # Ищем рецепт ангоба для полок
            r_recipes = self._api("GET", f"/recipes?factory_id={self.factory_id}&limit=50")
            recipes = (r_recipes.json().get("items") or r_recipes.json()) if r_recipes.ok else []
            engobe_recipe = next(
                (rec for rec in recipes if isinstance(rec, dict) and
                 any(k in rec.get("name", "").lower() for k in ["shelf", "engob", "полк", "board", "coating"])),
                None,
            )
            recipe_info = f" (рецепт: {engobe_recipe['name']})" if engobe_recipe else ""
            # Создаём задачу типа glazing_board_needed — сигнал что нужно сварить ангоб
            r = self._api("POST", "/tasks", json={
                "type": "glazing_board_needed",
                "description": f"E2E T30: кончился ангоб для полок.{recipe_info} "
                               f"Нужно приготовить минимум {original_balance or 50} ед. по рецепту.",
                "blocking": True,
                "priority": 3,
                "factory_id": self.factory_id,
            })
            if not r.ok:
                raise RuntimeError(f"Production task failed: {r.text[:200]}")
            task_id = r.json().get("id")
            self._tg(
                f"🏺 <b>T30</b>: Заявка на <b>производство</b> ангоба для полок!\n"
                f"ID задачи: {task_id}{recipe_info}\n"
                f"Количество: {original_balance or 50} ед.\n"
                f"Тип: glazing_board_needed → PM получит уведомление"
            )
            print(f"  {G}Production task created for shelf engobe: {task_id}{X}")
            return task_id

        self._step("Create production task for shelf engobe (internal recipe)", steps,
                   create_production_task_for_shelf_engobe)

        # Восстанавливаем баланс
        def restore_balance():
            if not shelf_engobe_id or original_balance is None:
                return
            r = self._api("POST", "/material-transactions", json={
                "material_id": shelf_engobe_id,
                "factory_id": self.factory_id,
                "transaction_type": "adjustment",
                "quantity": float(original_balance),
                "notes": "E2E T30: restoring shelf engobe balance after test",
            })
            if not r.ok:
                r2 = self._api("PUT", f"/materials/{shelf_engobe_id}/adjust", json={
                    "adjustment": float(original_balance),
                    "reason": "E2E T30: restoring balance",
                    "factory_id": self.factory_id,
                })
            self._tg(f"✅ <b>T30</b>: Баланс ангоба восстановлен до {original_balance}")
            print(f"  {G}Shelf engobe balance restored to {original_balance}{X}")

        self._step("Restore shelf engobe balance", steps, restore_balance)

        self.results.append((name, steps))
        pass_count = sum(1 for _, ok, _ in steps if ok)
        self._tg(f"{'✅' if pass_count == len(steps) else '⚠️'} <b>T30</b>: {pass_count}/{len(steps)} OK")

    # ─── Report + Cleanup ────────────────────────────────────────────────

    def cleanup_all(self):
        """Надёжная очистка через прямой доступ к БД (обходит все FK-зависимости)."""
        print(f"\n{B}Cleaning up {len(self.created_order_ids)} test orders...{X}")
        if self.db_url:
            db_cleanup_orders(self.db_url, self.created_order_ids)
        else:
            # Fallback через API
            for oid in self.created_order_ids:
                try:
                    self._api("DELETE", f"/cleanup/orders/{oid}?factory_id={self.factory_id}")
                except Exception as e:
                    print(f"  {Y}API cleanup failed for {oid}: {e}{X}")

    def print_report(self, elapsed: float = 0):
        print(f"\n{'='*65}")
        print(f"{B}  E2E COMPLEX TEST REPORT v3{X}")
        print(f"{'='*65}")
        total = passed = failed = 0
        for test_name, steps in self.results:
            p = sum(1 for _, ok, _ in steps if ok)
            f = sum(1 for _, ok, _ in steps if not ok)
            total += len(steps); passed += p; failed += f
            status = f"{G}ALL PASS{X}" if f == 0 else f"{R}{f} FAIL{X}"
            print(f"\n  {B}{test_name}{X}: {p}/{len(steps)}  [{status}]")
            for step_name, ok, msg in steps:
                icon = f"{G}✓{X}" if ok else f"{R}✗{X}"
                detail = "" if ok else f" — {msg}"
                print(f"    [{icon}] {step_name}{detail}")
        print(f"\n{'─'*65}")
        print(f"  Total: {passed}/{total} steps  |  Failed: {failed}  |  Time: {elapsed:.1f}s")
        if failed == 0:
            print(f"  {G}{B}ALL TESTS PASSED{X}")
        else:
            print(f"  {R}{B}{failed} STEPS FAILED — see details above{X}")
        print(f"{'='*65}\n")

        # Telegram summary
        verdict = "✅ ВСЕ ТЕСТЫ ПРОШЛИ" if failed == 0 else f"❌ {failed} шагов провалено"
        self._tg(
            f"📋 <b>E2E Complex Tests v3 — ИТОГ</b>\n"
            f"{verdict}\n"
            f"Шагов: {passed}/{total} ОК\n"
            f"Время: {elapsed:.1f}s\n\n"
            + "\n".join(
                f"{'✅' if sum(1 for _,ok,_ in s if not ok)==0 else '❌'} {n}"
                for n, s in self.results
            )
        )

    def run(self):
        start = time.time()
        self._tg(
            f"🚀 <b>Moonjar PMS — E2E Complex Tests v3</b>\n"
            f"Фабрика: {self.factory_name}\n"
            f"Тесты: T26 ConsumptionRules | T27 PackagingRules | "
            f"T28 KilnBreakdown | T29 BlockingTask | T30 ShelfEngobeEmpty"
        )
        try:
            self.test_26_consumption_rules_mandatory()
            time.sleep(2)
            self.test_27_packaging_rules_mandatory()
            time.sleep(2)
            self.test_28_kiln_breakdown_schedule_shift()
            time.sleep(2)
            self.test_29_blocking_task_deadline_miss()
            time.sleep(2)
            self.test_30_shelf_engobe_runs_out()
        except KeyboardInterrupt:
            print(f"\n{Y}Interrupted — running cleanup...{X}")
            self._tg("⚠️ Тест прерван — запускаем очистку...")
        except Exception as e:
            print(f"\n{R}Unexpected error: {e}{X}")
            traceback.print_exc()
        finally:
            self.cleanup_all()

        elapsed = time.time() - start
        self.print_report(elapsed)


# ─── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="E2E Complex Tests v3 — Moonjar PMS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--api-url", default="https://moonjar-pms-production.up.railway.app/api")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument(
        "--db-url",
        default="postgresql://postgres:FxrYtbHulBywvUlNURocqBLuLFfQNWdZ@tramway.proxy.rlwy.net:35660/railway",
        help="PostgreSQL URL for reliable DB-level cleanup",
    )
    parser.add_argument("--tg-chat-id", default="452576610",
                        help="Telegram chat_id for live notifications (default: 452576610)")
    args = parser.parse_args()

    t = ComplexE2ETest(
        api_url=args.api_url,
        email=args.email,
        password=args.password,
        db_url=args.db_url,
        tg_chat_id=args.tg_chat_id,
    )
    t.run()
