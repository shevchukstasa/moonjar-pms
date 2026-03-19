#!/usr/bin/env python3
"""
Moonjar PMS — Stage 1 & Stage 2 Integration Test Suite
=======================================================
Тестирует ВСЕ основные API endpoints этапов 1 и 2.
По одному запросу на каждую функцию/группу.

Использование:
  EMAIL=admin@example.com PASSWORD=secret python3 scripts/test_stages_1_2.py
  BASE_URL=https://... EMAIL=... PASSWORD=... python3 scripts/test_stages_1_2.py

Exit codes: 0 = all passed, 1 = failures
"""

import os
import sys
import json
import time
import uuid
import requests
from datetime import datetime, date, timedelta

# ── Config ────────────────────────────────────────────────
BASE = os.getenv("BASE_URL", "https://moonjar-pms-production.up.railway.app/api").rstrip("/")
EMAIL = os.getenv("EMAIL", "")
PASSWORD = os.getenv("PASSWORD", "")

if not EMAIL or not PASSWORD:
    print("ERROR: Set EMAIL and PASSWORD environment variables")
    print("  EMAIL=admin@example.com PASSWORD=secret python3 scripts/test_stages_1_2.py")
    sys.exit(1)

# ── State ─────────────────────────────────────────────────
session = requests.Session()
session.headers.update({"Content-Type": "application/json"})

passed = 0
failed = 0
skipped = 0
failures = []

# IDs created during testing (for chained tests)
ctx = {}

# ── Helpers ───────────────────────────────────────────────
RESET = "\033[0m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
CYAN = "\033[96m"


def section(title):
    time.sleep(0.5)  # pause between sections to avoid rate-limiting (429)
    print(f"\n{BOLD}{CYAN}{'─'*60}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'─'*60}{RESET}")


def ok(name):
    global passed
    passed += 1
    print(f"  {GREEN}✓{RESET} {name}")


def fail(name, reason):
    global failed
    failed += 1
    short = str(reason)[:120]
    print(f"  {RED}✗{RESET} {name}: {short}")
    failures.append(f"{name}: {reason}")


def skip(name, reason=""):
    global skipped
    skipped += 1
    print(f"  {YELLOW}○{RESET} {name}" + (f" ({reason})" if reason else ""))


def _sync_csrf(r):
    """Keep CSRF token in sync — server echoes it in every response."""
    new_csrf = r.headers.get("X-CSRF-Token")
    if new_csrf:
        session.headers["X-CSRF-Token"] = new_csrf


def check(r, expected=200, name="", save_as=None, save_key=None):
    """Asserts status code and optionally saves response data to ctx."""
    _sync_csrf(r)
    if r.status_code == expected:
        ok(name)
        if save_as:
            try:
                data = r.json()
                if save_key and isinstance(data, dict):
                    ctx[save_as] = data.get(save_key) or data.get("id")
                elif save_key and isinstance(data, list):
                    ctx[save_as] = data[0].get(save_key) if data else None
                else:
                    ctx[save_as] = data.get("id") if isinstance(data, dict) else None
            except Exception:
                pass
        return True
    else:
        try:
            detail = r.json().get("detail", r.text[:120])
        except Exception:
            detail = r.text[:120]
        fail(name, f"Expected {expected}, got {r.status_code}: {detail}")
        return False


def get(path, params=None, name=""):
    return session.get(f"{BASE}{path}", params=params, timeout=15)


def post(path, body=None, name=""):
    return session.post(f"{BASE}{path}", json=body, timeout=15)


def patch(path, body=None, name=""):
    return session.patch(f"{BASE}{path}", json=body, timeout=15)


def delete(path, name=""):
    return session.delete(f"{BASE}{path}", timeout=15)


def put(path, body=None, name=""):
    return session.put(f"{BASE}{path}", json=body, timeout=15)


# ─────────────────────────────────────────────────────────
# STAGE 1 — FOUNDATION
# ─────────────────────────────────────────────────────────

section("STAGE 1 · Health & Auth")

# Health
r = get("/health")
check(r, 200, "GET /health")

# Anonymous access returns 401/403
r = get("/orders")
name = "GET /orders (no auth) → 401"
if r.status_code in (401, 403):
    ok(name)
else:
    fail(name, f"Expected 401/403, got {r.status_code}")

# Login
r = post("/auth/login", {"email": EMAIL, "password": PASSWORD})
if check(r, 200, f"POST /auth/login ({EMAIL})"):
    data = r.json()
    ctx["access_token"] = data.get("access_token")
    ctx["user_id"] = data.get("user", {}).get("id")
    ctx["user_role"] = data.get("user", {}).get("role")
    ctx["factory_id"] = (data.get("user", {}).get("factories") or [{}])[0].get("id")
    if ctx.get("access_token"):
        session.headers["Authorization"] = f"Bearer {ctx['access_token']}"
        ok("  → Token received & set")
    else:
        fail("  → Token received", "No access_token in response")
    # CSRF token — required for all mutating requests (POST/PATCH/DELETE)
    csrf = r.headers.get("X-CSRF-Token") or r.cookies.get("csrf_token")
    if csrf:
        session.headers["X-CSRF-Token"] = csrf
        ok("  → CSRF token set")
else:
    print(f"\n{RED}FATAL: Cannot login. Check EMAIL and PASSWORD.{RESET}")
    sys.exit(1)

# GET /auth/me
r = get("/auth/me")
check(r, 200, "GET /auth/me")

# POST /auth/refresh
r = post("/auth/refresh")
if r.status_code == 200:
    new_token = r.json().get("access_token")
    if new_token:
        session.headers["Authorization"] = f"Bearer {new_token}"
    # Update CSRF token — refresh generates new jti, so csrf_token changes
    new_csrf = r.headers.get("X-CSRF-Token") or session.cookies.get("csrf_token")
    if new_csrf:
        session.headers["X-CSRF-Token"] = new_csrf
    ok("POST /auth/refresh")
elif r.status_code in (401, 422):
    skip("POST /auth/refresh", "refresh token not in cookie (expected in browser flow)")
else:
    fail("POST /auth/refresh", f"Unexpected {r.status_code}: {r.text[:80]}")

section("STAGE 1 · Users")

r = get("/users")
if r.status_code == 200:
    check(r, 200, "GET /users")
elif r.status_code == 403:
    skip("GET /users", "admin-only endpoint (current role has no access — expected)")
else:
    check(r, 200, "GET /users")

if ctx.get("user_id"):
    r = get(f"/users/{ctx['user_id']}")
    if r.status_code == 200:
        check(r, 200, "GET /users/{id}")
    elif r.status_code == 403:
        skip("GET /users/{id}", "admin-only endpoint")
    else:
        check(r, 200, "GET /users/{id}")

# Create test user (admin-only; accept 403 gracefully)
test_email = f"test_{uuid.uuid4().hex[:8]}@moonjar-test.com"
r = post("/users", {
    "email": test_email,
    "name": "Test User Stage1",
    "role": "warehouse",
    "password": "TestPass123!",
})
if r.status_code == 403:
    skip("POST /users (create warehouse user)", "admin-only endpoint")
elif check(r, 201, "POST /users (create warehouse user)", save_as="test_user_id"):
    uid = ctx.get("test_user_id")
    if uid:
        r = patch(f"/users/{uid}", {"name": "Test User Updated"})
        check(r, 200, "PATCH /users/{id}")

        r = post(f"/users/{uid}/toggle-active")
        check(r, 200, "POST /users/{id}/toggle-active")

section("STAGE 1 · Factories")

r = get("/factories")
if check(r, 200, "GET /factories", save_as="factory_id", save_key="id"):
    items = r.json()
    if isinstance(items, list) and items:
        ctx["factory_id"] = ctx.get("factory_id") or items[0].get("id")
    elif isinstance(items, dict) and items.get("items"):
        ctx["factory_id"] = items["items"][0].get("id") if items["items"] else ctx.get("factory_id")

if ctx.get("factory_id"):
    r = get(f"/factories/{ctx['factory_id']}")
    check(r, 200, "GET /factories/{id}")

section("STAGE 1 · Reference: Colors, Collections, Finishings")

r = get("/reference/colors")
check(r, 200, "GET /reference/colors")

r = get("/reference/collections")
check(r, 200, "GET /reference/collections")

r = get("/reference/finishing-types")
check(r, 200, "GET /reference/finishing-types")

section("STAGE 1 · Sizes & Glazing Boards")

r = get("/sizes")
if check(r, 200, "GET /sizes"):
    items = r.json().get("items", [])
    ctx["size_id_existing"] = items[0].get("id") if items else None

r = get("/sizes/search", params={"q": "10x10"})
check(r, 200, "GET /sizes/search?q=10x10")

r = get("/sizes/search", params={"width_mm": 100, "height_mm": 100})
check(r, 200, "GET /sizes/search?width_mm=100&height_mm=100")

# Create size + auto glazing board calculation
test_size_name = f"TestSize_{uuid.uuid4().hex[:6]}"
r = post("/sizes", {
    "name": test_size_name,
    "width_mm": 120,
    "height_mm": 240,
    "shape": "rectangle",
    "is_custom": True,
})
if check(r, 201, "POST /sizes (create, auto-glazing-board)", save_as="test_size_id"):
    sid = ctx.get("test_size_id")
    data = r.json()
    has_board = data.get("glazing_board") is not None
    if has_board:
        ok(f"  → glazing_board auto-calculated: {data['glazing_board']['tiles_per_board']} pcs/board")
    else:
        fail("  → glazing_board auto-calculated", "glazing_board is null in response")

    r = get(f"/sizes/{sid}")
    check(r, 200, "GET /sizes/{id}")

    r = get(f"/sizes/{sid}/glazing-board")
    if check(r, 200, "GET /sizes/{id}/glazing-board"):
        gb = r.json()
        ok(f"  → {gb['tiles_per_board']} tiles/board, {gb['board_width_cm']}cm wide, {'CUSTOM' if gb['is_custom_board'] else 'standard'}")

    r = get(f"/sizes/{sid}/glazing-board", params={"recalculate": "true"})
    check(r, 200, "GET /sizes/{id}/glazing-board?recalculate=true")

    r = patch(f"/sizes/{sid}", {"name": test_size_name + "_upd"})
    check(r, 200, "PATCH /sizes/{id}")

    r = delete(f"/sizes/{sid}")
    check(r, 200, "DELETE /sizes/{id}")

section("STAGE 1 · Materials")

r = get("/materials")
if check(r, 200, "GET /materials"):
    items = r.json()
    if isinstance(items, dict):
        items = items.get("items", [])
    ctx["material_id"] = items[0].get("id") if items else None

r = get("/materials/low-stock", params={"factory_id": ctx.get("factory_id", "")})
check(r, 200, "GET /materials/low-stock")

r = get("/materials/effective-balance", params={"factory_id": ctx.get("factory_id", "")})
check(r, 200, "GET /materials/effective-balance")

if ctx.get("material_id"):
    r = get(f"/materials/{ctx['material_id']}")
    check(r, 200, "GET /materials/{id}")

    r = get(f"/materials/{ctx['material_id']}/transactions")
    check(r, 200, "GET /materials/{id}/transactions")

section("STAGE 1 · Recipes")

r = get("/recipes")
if check(r, 200, "GET /recipes"):
    items = r.json()
    if isinstance(items, dict):
        items = items.get("items", [])
    ctx["recipe_id"] = items[0].get("id") if items else None

if ctx.get("recipe_id"):
    r = get(f"/recipes/{ctx['recipe_id']}")
    check(r, 200, "GET /recipes/{id}")

    r = get(f"/recipes/{ctx['recipe_id']}/materials")
    check(r, 200, "GET /recipes/{id}/materials")

    r = get(f"/recipes/{ctx['recipe_id']}/firing-stages")
    check(r, 200, "GET /recipes/{id}/firing-stages")

section("STAGE 1 · Kilns")

r = get("/kilns", params={"factory_id": ctx.get("factory_id", "")})
if check(r, 200, "GET /kilns"):
    items = r.json()
    if isinstance(items, dict):
        items = items.get("items", [])
    ctx["kiln_id"] = items[0].get("id") if items else None

if ctx.get("kiln_id"):
    r = get(f"/kilns/{ctx['kiln_id']}")
    check(r, 200, "GET /kilns/{id}")

r = get("/kilns/collections")
check(r, 200, "GET /kilns/collections")

section("STAGE 1 · Orders")

r = get("/orders", params={"factory_id": ctx.get("factory_id", ""), "per_page": 5})
if check(r, 200, "GET /orders"):
    data = r.json()
    items = data.get("items", []) if isinstance(data, dict) else data
    ctx["order_id"] = items[0].get("id") if items else None

if ctx.get("order_id"):
    r = get(f"/orders/{ctx['order_id']}")
    check(r, 200, "GET /orders/{id}")

r = get("/orders/cancellation-requests", params={"factory_id": ctx.get("factory_id", "")})
check(r, 200, "GET /orders/cancellation-requests")

r = get("/orders/change-requests", params={"factory_id": ctx.get("factory_id", "")})
check(r, 200, "GET /orders/change-requests")

section("STAGE 1 · Positions")

params = {"per_page": 5}
if ctx.get("factory_id"):
    params["factory_id"] = ctx["factory_id"]
r = get("/positions", params=params)
if check(r, 200, "GET /positions"):
    data = r.json()
    items = data.get("items", []) if isinstance(data, dict) else data
    ctx["position_id"] = items[0].get("id") if items else None

r = get("/positions/blocking-summary", params={"factory_id": ctx.get("factory_id", "")})
check(r, 200, "GET /positions/blocking-summary")

if ctx.get("position_id"):
    r = get(f"/positions/{ctx['position_id']}")
    check(r, 200, "GET /positions/{id}")

    r = get(f"/positions/{ctx['position_id']}/allowed-transitions")
    check(r, 200, "GET /positions/{id}/allowed-transitions")

    r = get(f"/positions/{ctx['position_id']}/stock-availability")
    check(r, 200, "GET /positions/{id}/stock-availability")

    r = get(f"/positions/{ctx['position_id']}/material-reservations")
    check(r, 200, "GET /positions/{id}/material-reservations")

section("STAGE 1 · Tasks")

r = get("/tasks", params={"per_page": 10})
if check(r, 200, "GET /tasks"):
    data = r.json()
    items = data.get("items", []) if isinstance(data, dict) else data
    ctx["task_id"] = items[0].get("id") if items else None

if ctx.get("task_id"):
    r = get(f"/tasks/{ctx['task_id']}")
    check(r, 200, "GET /tasks/{id}")

section("STAGE 1 · Suppliers")

r = get("/suppliers")
if check(r, 200, "GET /suppliers"):
    items = r.json()
    if isinstance(items, dict):
        items = items.get("items", [])
    ctx["supplier_id"] = items[0].get("id") if items else None

if ctx.get("supplier_id"):
    r = get(f"/suppliers/{ctx['supplier_id']}")
    check(r, 200, "GET /suppliers/{id}")

section("STAGE 1 · Warehouse Sections")

r = get("/warehouse-sections", params={"factory_id": ctx.get("factory_id", "")})
check(r, 200, "GET /warehouse-sections")

section("STAGE 1 · Firing Profiles")

r = get("/firing-profiles", params={"factory_id": ctx.get("factory_id", "")})
check(r, 200, "GET /firing-profiles")

section("STAGE 1 · Packaging")

r = get("/packaging")
check(r, 200, "GET /packaging")

r = get("/packaging/sizes")
check(r, 200, "GET /packaging/sizes")

section("STAGE 1 · Consumption Rules")

r = get("/consumption-rules")
check(r, 200, "GET /consumption-rules")

section("STAGE 1 · Notifications")

r = get("/notifications")
check(r, 200, "GET /notifications")

# ─────────────────────────────────────────────────────────
# STAGE 2 — PRODUCTION PIPELINE
# ─────────────────────────────────────────────────────────

section("STAGE 2 · Batches")

r = get("/batches", params={"factory_id": ctx.get("factory_id", ""), "per_page": 5})
if check(r, 200, "GET /batches"):
    data = r.json()
    items = data.get("items", []) if isinstance(data, dict) else data
    ctx["batch_id"] = items[0].get("id") if items else None

if ctx.get("batch_id"):
    r = get(f"/batches/{ctx['batch_id']}")
    check(r, 200, "GET /batches/{id}")

    r = get(f"/batches/{ctx['batch_id']}/photos")
    check(r, 200, "GET /batches/{id}/photos")

# Capacity preview (doesn't create anything)
if ctx.get("factory_id"):
    r = post("/batches/capacity-preview", {
        "factory_id": ctx["factory_id"],
        "position_ids": [],
    })
    if r.status_code in (200, 422):
        ok("POST /batches/capacity-preview")
    else:
        fail("POST /batches/capacity-preview", f"{r.status_code}: {r.text[:80]}")

section("STAGE 2 · Quality Inspections")

r = get("/quality/inspections", params={"factory_id": ctx.get("factory_id", "")})
check(r, 200, "GET /quality/inspections")

r = get("/quality/stats", params={"factory_id": ctx.get("factory_id", "")})
check(r, 200, "GET /quality/stats")

r = get("/quality/positions-for-qc", params={"factory_id": ctx.get("factory_id", "")})
check(r, 200, "GET /quality/positions-for-qc")

section("STAGE 2 · Defects")

r = get("/defects", params={"factory_id": ctx.get("factory_id", "")})
if check(r, 200, "GET /defects"):
    data = r.json()
    items = data.get("items", []) if isinstance(data, dict) else data
    ctx["defect_id"] = items[0].get("id") if items else None

if ctx.get("defect_id"):
    r = get(f"/defects/{ctx['defect_id']}")
    check(r, 200, "GET /defects/{id}")

section("STAGE 2 · Grinding Stock")

r = get("/grinding-stock", params={"factory_id": ctx.get("factory_id", "")})
if check(r, 200, "GET /grinding-stock"):
    data = r.json()
    items = data.get("items", []) if isinstance(data, dict) else data
    ctx["grind_id"] = items[0].get("id") if items else None

r = get("/grinding-stock/stats", params={"factory_id": ctx.get("factory_id", "")})
check(r, 200, "GET /grinding-stock/stats")

if ctx.get("grind_id"):
    r = get(f"/grinding-stock/{ctx['grind_id']}")
    check(r, 200, "GET /grinding-stock/{id}")

section("STAGE 2 · TPS Metrics")

r = get("/tps/parameters", params={"factory_id": ctx.get("factory_id", "")})
check(r, 200, "GET /tps/parameters")

r = get("/tps", params={"factory_id": ctx.get("factory_id", "")})
check(r, 200, "GET /tps (entries)")

r = get("/tps/deviations", params={"factory_id": ctx.get("factory_id", "")})
check(r, 200, "GET /tps/deviations")

r = get("/tps/throughput", params={"factory_id": ctx.get("factory_id", "")})
check(r, 200, "GET /tps/throughput")

r = get("/tps/deviations/operations", params={"factory_id": ctx.get("factory_id", "")})
check(r, 200, "GET /tps/deviations/operations")

if ctx.get("position_id"):
    r = get(f"/tps/position/{ctx['position_id']}/timeline")
    check(r, 200, "GET /tps/position/{id}/timeline")

section("STAGE 2 · Analytics")

params = {"factory_id": ctx.get("factory_id", "")}
r = get("/analytics/dashboard-summary", params=params)
check(r, 200, "GET /analytics/dashboard-summary")

r = get("/analytics/production-metrics", params=params)
check(r, 200, "GET /analytics/production-metrics")

r = get("/analytics/material-metrics", params=params)
check(r, 200, "GET /analytics/material-metrics")

r = get("/analytics/buffer-health", params=params)
check(r, 200, "GET /analytics/buffer-health")

r = get("/analytics/trend-data", params={**params, "metric": "output"})
check(r, 200, "GET /analytics/trend-data")

r = get("/analytics/activity-feed", params=params)
check(r, 200, "GET /analytics/activity-feed")

today = date.today()
r = get("/analytics/inventory-report", params={**params, "month": today.month, "year": today.year})
check(r, 200, "GET /analytics/inventory-report")

section("STAGE 2 · Schedule")

params = {"factory_id": ctx.get("factory_id", "")}
r = get("/schedule/resources", params=params)
check(r, 200, "GET /schedule/resources")

r = get("/schedule/glazing-schedule", params=params)
check(r, 200, "GET /schedule/glazing-schedule")

r = get("/schedule/firing-schedule", params=params)
check(r, 200, "GET /schedule/firing-schedule")

r = get("/schedule/sorting-schedule", params=params)
check(r, 200, "GET /schedule/sorting-schedule")

r = get("/schedule/qc-schedule", params=params)
check(r, 200, "GET /schedule/qc-schedule")

r = get("/schedule/kiln-schedule", params=params)
check(r, 200, "GET /schedule/kiln-schedule")

r = get("/schedule/batches", params=params)
check(r, 200, "GET /schedule/batches")

if ctx.get("order_id"):
    r = get(f"/schedule/orders/{ctx['order_id']}/schedule")
    check(r, 200, "GET /schedule/orders/{id}/schedule")

if ctx.get("position_id"):
    r = get(f"/schedule/positions/{ctx['position_id']}/schedule")
    check(r, 200, "GET /schedule/positions/{id}/schedule")

section("STAGE 2 · Factory Calendar")

if ctx.get("factory_id"):
    today = date.today().isoformat()
    r = get("/factory-calendar", params={"factory_id": ctx["factory_id"]})
    check(r, 200, "GET /factory-calendar")

    r = get("/factory-calendar/working-days", params={
        "factory_id": ctx["factory_id"],
        "start_date": today,
        "end_date": (date.today() + timedelta(days=30)).isoformat(),
    })
    check(r, 200, "GET /factory-calendar/working-days")

    # Add a holiday
    future_date = (date.today() + timedelta(days=90)).isoformat()
    r = post("/factory-calendar", {
        "factory_id": ctx["factory_id"],
        "date": future_date,
        "is_working_day": False,
        "holiday_name": "Test Holiday (Stage 2 Test)",
        "num_shifts": 0,
    })
    if check(r, 201, "POST /factory-calendar (add holiday)", save_as="calendar_id"):
        cal_id = ctx.get("calendar_id")
        if cal_id:
            r = delete(f"/factory-calendar/{cal_id}")
            if r.status_code in (200, 204):
                ok("DELETE /factory-calendar/{id} (cleanup)")
            else:
                fail("DELETE /factory-calendar/{id} (cleanup)", f"{r.status_code}: {r.text[:80]}")

section("STAGE 2 · Problem Cards")

r = get("/problem-cards", params={"factory_id": ctx.get("factory_id", "")})
if check(r, 200, "GET /problem-cards"):
    data = r.json()
    items = data.get("items", []) if isinstance(data, dict) else data
    ctx["problem_card_id"] = items[0].get("id") if items else None

if ctx.get("problem_card_id"):
    r = get(f"/problem-cards/{ctx['problem_card_id']}")
    check(r, 200, "GET /problem-cards/{id}")

section("STAGE 2 · QM Blocks")

r = get("/qm-blocks", params={"factory_id": ctx.get("factory_id", "")})
if check(r, 200, "GET /qm-blocks"):
    data = r.json()
    items = data.get("items", []) if isinstance(data, dict) else data
    ctx["qm_block_id"] = items[0].get("id") if items else None

if ctx.get("qm_block_id"):
    r = get(f"/qm-blocks/{ctx['qm_block_id']}")
    check(r, 200, "GET /qm-blocks/{id}")

section("STAGE 2 · Finished Goods")

r = get("/finished-goods", params={"factory_id": ctx.get("factory_id", "")})
check(r, 200, "GET /finished-goods")

r = get("/finished-goods/availability", params={"factory_id": ctx.get("factory_id", ""), "color": "White", "size": "30x60", "needed": 100})
check(r, 200, "GET /finished-goods/availability")

section("STAGE 2 · Kiln Maintenance")

r = get("/kiln-maintenance/types")
check(r, 200, "GET /kiln-maintenance/types")

r = get("/kiln-maintenance/upcoming", params={"factory_id": ctx.get("factory_id", "")})
check(r, 200, "GET /kiln-maintenance/upcoming")

r = get("/kiln-maintenance", params={"factory_id": ctx.get("factory_id", "")})
check(r, 200, "GET /kiln-maintenance")

if ctx.get("kiln_id"):
    r = get(f"/kiln-maintenance/kilns/{ctx['kiln_id']}")
    check(r, 200, "GET /kiln-maintenance/kilns/{kiln_id}")

section("STAGE 2 · Firing Profiles")

r = get("/firing-profiles", params={"factory_id": ctx.get("factory_id", "")})
if check(r, 200, "GET /firing-profiles"):
    data = r.json()
    items = data.get("items", []) if isinstance(data, dict) else data
    ctx["firing_profile_id"] = items[0].get("id") if items else None

if ctx.get("firing_profile_id"):
    r = get(f"/firing-profiles/{ctx['firing_profile_id']}")
    check(r, 200, "GET /firing-profiles/{id}")

section("STAGE 2 · Material Consumption Adjustments")

r = get("/materials/consumption-adjustments", params={"factory_id": ctx.get("factory_id", "")})
check(r, 200, "GET /materials/consumption-adjustments")

section("STAGE 2 · Material Transactions")

if ctx.get("material_id") and ctx.get("factory_id"):
    r = post("/materials/transactions", {
        "material_id": ctx["material_id"],
        "factory_id": ctx["factory_id"],
        "transaction_type": "inventory",
        "quantity": 0,
        "notes": "Stage 2 test — inventory check (0 delta)",
    })
    # Inventory adjustment with 0 delta should succeed or 422 (validation)
    if r.status_code in (200, 201, 422):
        ok("POST /materials/transactions (inventory)")
    else:
        fail("POST /materials/transactions", f"{r.status_code}: {r.text[:80]}")

section("STAGE 2 · Reconciliation")

r = get("/reconciliations", params={"factory_id": ctx.get("factory_id", "")})
check(r, 200, "GET /reconciliations")

section("STAGE 2 · TOC / Buffer Health")

r = get("/toc/buffer-zones", params={"factory_id": ctx.get("factory_id", "")})
if check(r, 200, "GET /toc/buffer-zones"):
    data = r.json()
    summary = data.get("summary", {})
    total = data.get("total", 0)
    ok(f"  → {total} orders: green={summary.get('green',0)} yellow={summary.get('yellow',0)} red={summary.get('red',0)}")

section("STAGE 2 · Material Groups")

r = get("/material-groups/groups")
check(r, 200, "GET /material-groups/groups")

section("STAGE 2 · Webhook / Integration")

# GET /integration/webhooks — admin-only, PM gets 403 (expected)
r = get("/integration/webhooks")
if r.status_code in (403, 429):
    skip("GET /integration/webhooks", "admin-only endpoint" if r.status_code == 403 else "rate limited")
else:
    check(r, 200, "GET /integration/webhooks")

# POST /integration/webhook/sales-order — requires X-API-Key from Sales app
# Without the key we expect 401 (not 404) — confirms endpoint exists and is active
r = session.post(f"{BASE}/integration/webhook/sales-order", json={
    "event_id": "test-probe-001",
    "event_type": "new_order",
    "order_data": {},
})
_sync_csrf(r)
if r.status_code == 503:
    skip("POST /integration/webhook/sales-order", "webhook disabled (PRODUCTION_WEBHOOK_ENABLED=false)")
elif r.status_code in (401, 403):
    ok("POST /integration/webhook/sales-order (endpoint active, no Sales API key — expected 401)")
elif r.status_code == 200:
    ok("POST /integration/webhook/sales-order (processed)")
else:
    fail("POST /integration/webhook/sales-order", f"{r.status_code}: {r.text[:120]}")

# Rate limit reset: 100 req/min limit — pause 65s to guarantee the 60s window fully resets
print(f"\n  {YELLOW}[rate-limit guard] sleeping 65s to reset API rate limit window (100 req/min limit)...{RESET}")
time.sleep(65)

section("STAGE 2 · Security")

r = get("/security/audit-log", params={"per_page": 5})
if r.status_code == 403:
    skip("GET /security/audit-log", "admin-only endpoint")
else:
    check(r, 200, "GET /security/audit-log")

r = get("/security/sessions")
check(r, 200, "GET /security/sessions")

section("STAGE 2 · Stages (production stages)")

r = get("/stages", params={"factory_id": ctx.get("factory_id", "")})
check(r, 200, "GET /stages")

section("STAGE 2 · Dashboard Access")

r = get("/dashboard-access")
if r.status_code in (200, 403, 404):
    ok("GET /dashboard-access") if r.status_code == 200 else skip("GET /dashboard-access", f"HTTP {r.status_code}")
else:
    fail("GET /dashboard-access", f"{r.status_code}")

section("STAGE 2 · Kiln Constants & Loading Rules")

r = get("/kiln-constants", params={"factory_id": ctx.get("factory_id", "")})
if r.status_code in (200, 404):
    ok("GET /kiln-constants") if r.status_code == 200 else skip("GET /kiln-constants", "not mounted")

r = get("/kiln-loading-rules")
if r.status_code in (200, 404):
    ok("GET /kiln-loading-rules") if r.status_code == 200 else skip("GET /kiln-loading-rules", "not mounted")

section("STAGE 2 · Kiln Firing Schedules")

if ctx.get("kiln_id"):
    r = get("/kiln-firing-schedules", params={"kiln_id": ctx["kiln_id"]})
    if r.status_code in (200, 404):
        ok("GET /kiln-firing-schedules") if r.status_code == 200 else skip("GET /kiln-firing-schedules", "not mounted")

section("STAGE 2 · Packing Photos")

r = get("/packing-photos", params={"factory_id": ctx.get("factory_id", "")})
if r.status_code in (200, 404):
    ok("GET /packing-photos") if r.status_code == 200 else skip("GET /packing-photos", "not mounted")

# ── Auth logout ────────────────────────────────────────────
section("Cleanup: Logout")
r = post("/auth/logout")
if r.status_code in (200, 204):
    ok("POST /auth/logout")
else:
    fail("POST /auth/logout", f"{r.status_code}")

# ── Summary ───────────────────────────────────────────────
total = passed + failed + skipped
print(f"\n{'='*60}")
print(f"{BOLD}  RESULTS: Stage 1 & 2 Integration Test{RESET}")
print(f"{'='*60}")
print(f"  {GREEN}Passed:  {passed}{RESET}")
print(f"  {RED}Failed:  {failed}{RESET}")
print(f"  {YELLOW}Skipped: {skipped}{RESET}")
print(f"  Total:   {total}")

if failures:
    print(f"\n{RED}{BOLD}  FAILURES:{RESET}")
    for f in failures:
        print(f"  {RED}✗{RESET} {f}")

print(f"\n{'='*60}")
pct = round(passed / max(passed + failed, 1) * 100)
status = f"{GREEN}ALL GOOD{RESET}" if failed == 0 else f"{RED}{failed} FAILED{RESET}"
print(f"  Result: {status} ({pct}% pass rate)")
print(f"{'='*60}\n")

sys.exit(0 if failed == 0 else 1)
