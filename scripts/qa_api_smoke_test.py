#!/usr/bin/env python3
"""
Moonjar PMS — API Smoke Test
=============================
Logs in as owner and hits every GET endpoint.
Reports status codes: 200, 401, 403, 404, 500, etc.

Usage:
    python scripts/qa_api_smoke_test.py
    python scripts/qa_api_smoke_test.py --base-url http://localhost:8000
    python scripts/qa_api_smoke_test.py --email owner@moonjar.com --password secret
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from typing import Optional

import requests

# ── Default configuration ──────────────────────────────────────────

DEFAULT_BASE_URL = "https://moonjar-pms-production.up.railway.app"
DEFAULT_EMAIL = "owner@moonjar.com"
DEFAULT_PASSWORD = "owner123"

# ── All GET endpoints to test ──────────────────────────────────────

# Each tuple: (method, path, description)
# Paths with {id} use placeholder UUIDs (expect 404 or 422, which is fine)
PLACEHOLDER_UUID = "00000000-0000-0000-0000-000000000000"

ENDPOINTS = [
    # Health (no auth required)
    ("GET", "/api/health", "Health check"),
    ("GET", "/api/health/seed-status", "Seed status"),

    # Auth
    ("GET", "/api/auth/me", "Current user"),

    # Orders
    ("GET", "/api/orders", "List orders"),
    ("GET", "/api/orders/cancellation-requests", "Cancellation requests"),
    ("GET", "/api/orders/change-requests", "Change requests"),

    # Positions
    ("GET", "/api/positions", "List positions"),
    ("GET", "/api/positions/blocking-summary", "Blocking summary"),

    # Schedule
    ("GET", "/api/schedule/resources", "Schedule resources"),
    ("GET", "/api/schedule/batches", "Scheduled batches"),
    ("GET", "/api/schedule/glazing-schedule", "Glazing schedule"),
    ("GET", "/api/schedule/firing-schedule", "Firing schedule"),
    ("GET", "/api/schedule/sorting-schedule", "Sorting schedule"),
    ("GET", "/api/schedule/qc-schedule", "QC schedule"),
    ("GET", "/api/schedule/kiln-schedule", "Kiln schedule"),

    # Materials
    ("GET", "/api/materials", "List materials"),
    ("GET", "/api/materials/low-stock", "Low stock materials"),
    ("GET", "/api/materials/effective-balance", "Effective balance"),
    ("GET", "/api/materials/consumption-adjustments", "Consumption adjustments"),
    ("GET", "/api/materials/duplicates", "Duplicate materials"),

    # Recipes
    ("GET", "/api/recipes", "List recipes"),
    ("GET", "/api/recipes/lookup", "Recipe lookup"),

    # Quality
    ("GET", "/api/quality/calendar-matrix", "QC calendar matrix"),
    ("GET", "/api/quality/defect-causes", "Defect causes"),
    ("GET", "/api/quality/inspections", "QC inspections"),
    ("GET", "/api/quality/positions-for-qc", "Positions for QC"),
    ("GET", "/api/quality/stats", "Quality stats"),

    # Defects
    ("GET", "/api/defects", "Defect causes list"),
    ("GET", "/api/defects/repair-queue", "Repair queue"),
    ("GET", "/api/defects/coefficients", "Defect coefficients"),
    ("GET", "/api/defects/surplus-dispositions", "Surplus dispositions"),
    ("GET", "/api/defects/surplus-summary", "Surplus summary"),
    ("GET", "/api/defects/supplier-reports", "Supplier reports"),

    # Tasks
    ("GET", "/api/tasks", "List tasks"),

    # Suppliers
    ("GET", "/api/suppliers", "List suppliers"),

    # Integration
    ("GET", "/api/integration/health", "Integration health"),
    ("GET", "/api/integration/db-check", "DB check"),
    ("GET", "/api/integration/orders/status-updates", "Order status updates"),
    ("GET", "/api/integration/webhooks", "Webhooks list"),
    ("GET", "/api/integration/stubs", "Integration stubs"),

    # Users
    ("GET", "/api/users", "List users"),

    # Factories
    ("GET", "/api/factories", "List factories"),

    # Kilns
    ("GET", "/api/kilns", "List kilns"),
    ("GET", "/api/kilns/collections", "Kiln collections"),
    ("GET", "/api/kilns/maintenance/upcoming", "Upcoming maintenance"),

    # Kiln Maintenance
    ("GET", "/api/kiln-maintenance", "Maintenance list"),
    ("GET", "/api/kiln-maintenance/types", "Maintenance types"),
    ("GET", "/api/kiln-maintenance/upcoming", "Upcoming maintenance"),

    # Kiln Inspections
    ("GET", "/api/kiln-inspections", "Inspection list"),
    ("GET", "/api/kiln-inspections/items", "Inspection items"),
    ("GET", "/api/kiln-inspections/repairs", "Inspection repairs"),
    ("GET", "/api/kiln-inspections/matrix", "Inspection matrix"),

    # Kiln Constants
    ("GET", "/api/kiln-constants", "Kiln constants"),

    # Kiln Loading Rules
    ("GET", "/api/kiln-loading-rules", "Loading rules"),

    # Kiln Firing Schedules
    ("GET", "/api/kiln-firing-schedules", "Firing schedules"),

    # Reference Data
    ("GET", "/api/reference/all", "All reference data"),
    ("GET", "/api/reference/product-types", "Product types"),
    ("GET", "/api/reference/stone-types", "Stone types"),
    ("GET", "/api/reference/glaze-types", "Glaze types"),
    ("GET", "/api/reference/finish-types", "Finish types"),
    ("GET", "/api/reference/shape-types", "Shape types"),
    ("GET", "/api/reference/material-types", "Material types"),
    ("GET", "/api/reference/position-statuses", "Position statuses"),
    ("GET", "/api/reference/collections", "Collections"),
    ("GET", "/api/reference/application-methods", "Application methods"),
    ("GET", "/api/reference/application-collections", "Application collections"),
    ("GET", "/api/reference/shape-coefficients", "Shape coefficients"),
    ("GET", "/api/reference/bowl-shapes", "Bowl shapes"),
    ("GET", "/api/reference/temperature-groups", "Temperature groups"),
    ("GET", "/api/reference/color-collections", "Color collections"),
    ("GET", "/api/reference/colors", "Colors"),
    ("GET", "/api/reference/application-types", "Application types"),
    ("GET", "/api/reference/places-of-application", "Places of application"),
    ("GET", "/api/reference/finishing-types", "Finishing types"),

    # TOC
    ("GET", "/api/toc/constraints", "TOC constraints"),
    ("GET", "/api/toc/buffer-health", "Buffer health"),
    ("GET", "/api/toc/buffer-zones", "Buffer zones"),

    # TPS
    ("GET", "/api/tps/parameters", "TPS parameters"),
    ("GET", "/api/tps", "TPS entries"),
    ("GET", "/api/tps/dashboard-summary", "TPS dashboard"),
    ("GET", "/api/tps/shift-summary", "TPS shift summary"),
    ("GET", "/api/tps/signal", "TPS signal"),
    ("GET", "/api/tps/deviations", "TPS deviations"),
    ("GET", "/api/tps/throughput", "TPS throughput"),
    ("GET", "/api/tps/deviations/operations", "TPS deviation operations"),

    # Notifications
    ("GET", "/api/notifications", "Notifications"),
    ("GET", "/api/notifications/unread-count", "Unread count"),

    # Analytics
    ("GET", "/api/analytics/dashboard-summary", "Analytics summary"),
    ("GET", "/api/analytics/production-metrics", "Production metrics"),
    ("GET", "/api/analytics/material-metrics", "Material metrics"),
    ("GET", "/api/analytics/factory-comparison", "Factory comparison"),
    ("GET", "/api/analytics/buffer-health", "Analytics buffer health"),
    ("GET", "/api/analytics/trend-data", "Trend data"),
    ("GET", "/api/analytics/activity-feed", "Activity feed"),
    ("GET", "/api/analytics/inventory-report", "Inventory report"),
    ("GET", "/api/analytics/anomalies", "Anomalies"),

    # Reports
    ("GET", "/api/reports", "Reports"),
    ("GET", "/api/reports/orders-summary", "Orders summary report"),
    ("GET", "/api/reports/kiln-load", "Kiln load report"),

    # Export
    ("GET", "/api/export/materials/excel", "Export materials Excel"),
    ("GET", "/api/export/quality/excel", "Export quality Excel"),
    ("GET", "/api/export/orders/excel", "Export orders Excel"),

    # Stages
    ("GET", "/api/stages", "Production stages"),

    # Telegram
    ("GET", "/api/telegram/bot-status", "Telegram bot status"),
    ("GET", "/api/telegram/owner-chat", "Telegram owner chat"),
    ("GET", "/api/telegram/recent-chats", "Telegram recent chats"),

    # Purchaser
    ("GET", "/api/purchaser", "Purchase orders"),
    ("GET", "/api/purchaser/stats", "Purchaser stats"),
    ("GET", "/api/purchaser/deliveries", "Deliveries"),
    ("GET", "/api/purchaser/deficits", "Deficits"),
    ("GET", "/api/purchaser/consolidation-suggestions", "Consolidation suggestions"),
    ("GET", "/api/purchaser/lead-times", "Lead times"),

    # Dashboard Access
    ("GET", "/api/dashboard-access", "Dashboard access list"),
    ("GET", "/api/dashboard-access/my", "My dashboard access"),

    # Notification Preferences
    ("GET", "/api/notification-preferences", "Notification preferences"),

    # Financials
    ("GET", "/api/financials", "Financial entries"),
    ("GET", "/api/financials/summary", "Financial summary"),

    # Warehouse Sections
    ("GET", "/api/warehouse-sections", "Warehouse sections"),
    ("GET", "/api/warehouse-sections/all", "All warehouse sections"),

    # Reconciliations
    ("GET", "/api/reconciliations", "Reconciliations"),

    # QM Blocks
    ("GET", "/api/qm-blocks", "QM blocks"),

    # Problem Cards
    ("GET", "/api/problem-cards", "Problem cards"),

    # Security
    ("GET", "/api/security/audit-log", "Audit log"),
    ("GET", "/api/security/audit-log/summary", "Audit log summary"),
    ("GET", "/api/security/sessions", "Active sessions"),
    ("GET", "/api/security/ip-allowlist", "IP allowlist"),
    ("GET", "/api/security/totp/status", "TOTP status"),
    ("GET", "/api/security/rate-limit-events", "Rate limit events"),

    # Packing Photos
    ("GET", "/api/packing-photos", "Packing photos"),

    # Finished Goods
    ("GET", "/api/finished-goods", "Finished goods"),
    ("GET", "/api/finished-goods/availability", "Finished goods availability"),

    # Firing Profiles
    ("GET", "/api/firing-profiles", "Firing profiles"),

    # Batches
    ("GET", "/api/batches", "Batches"),

    # Cleanup
    ("GET", "/api/cleanup/permissions", "Cleanup permissions"),

    # Material Groups
    ("GET", "/api/material-groups/hierarchy", "Material group hierarchy"),
    ("GET", "/api/material-groups/groups", "Material groups"),
    ("GET", "/api/material-groups/subgroups", "Material subgroups"),

    # Packaging
    ("GET", "/api/packaging", "Packaging box types"),
    ("GET", "/api/packaging/sizes", "Packaging sizes"),

    # Sizes
    ("GET", "/api/sizes", "Sizes"),
    ("GET", "/api/sizes/search", "Size search"),

    # Consumption Rules
    ("GET", "/api/consumption-rules", "Consumption rules"),

    # Grinding Stock
    ("GET", "/api/grinding-stock", "Grinding stock"),
    ("GET", "/api/grinding-stock/stats", "Grinding stats"),

    # Stone Reservations
    ("GET", "/api/stone-reservations", "Stone reservations"),
    ("GET", "/api/stone-reservations/weekly-report", "Weekly report"),
    ("GET", "/api/stone-reservations/defect-rates", "Defect rates"),

    # Factory Calendar
    ("GET", "/api/factory-calendar", "Factory calendar"),
    ("GET", "/api/factory-calendar/working-days", "Working days"),

    # Settings
    ("GET", "/api/settings", "User settings"),

    # Admin Settings
    ("GET", "/api/admin-settings", "Admin settings"),

    # Guides
    ("GET", "/api/guides", "Guides list"),

    # Transcription
    ("GET", "/api/transcription", "Transcription status"),

    # AI Chat
    ("GET", "/api/ai-chat/sessions", "AI Chat sessions"),
]


@dataclass
class TestResult:
    method: str
    path: str
    description: str
    status_code: int
    response_time_ms: float
    error: Optional[str] = None


@dataclass
class TestSummary:
    total: int = 0
    passed: int = 0  # 200-299
    auth_errors: int = 0  # 401
    forbidden: int = 0  # 403
    not_found: int = 0  # 404
    client_errors: int = 0  # other 4xx
    server_errors: int = 0  # 5xx
    connection_errors: int = 0
    results: list = field(default_factory=list)


def login(session: requests.Session, base_url: str, email: str, password: str) -> bool:
    """Login and store JWT cookies in session."""
    url = f"{base_url}/api/auth/login"
    try:
        resp = session.post(url, json={"email": email, "password": password}, timeout=15)
        if resp.status_code == 200:
            print(f"  Login successful as {email}")
            return True
        else:
            print(f"  Login FAILED: {resp.status_code} — {resp.text[:200]}")
            return False
    except requests.exceptions.ConnectionError as e:
        print(f"  Login FAILED: Connection error — {e}")
        return False


def run_test(
    session: requests.Session, base_url: str, method: str, path: str, description: str
) -> TestResult:
    """Execute a single API test."""
    url = f"{base_url}{path}"
    start = time.monotonic()
    try:
        resp = session.request(method, url, timeout=30)
        elapsed = (time.monotonic() - start) * 1000
        return TestResult(
            method=method,
            path=path,
            description=description,
            status_code=resp.status_code,
            response_time_ms=round(elapsed, 1),
        )
    except requests.exceptions.ConnectionError as e:
        elapsed = (time.monotonic() - start) * 1000
        return TestResult(
            method=method,
            path=path,
            description=description,
            status_code=0,
            response_time_ms=round(elapsed, 1),
            error=f"Connection error: {e}",
        )
    except requests.exceptions.Timeout:
        elapsed = (time.monotonic() - start) * 1000
        return TestResult(
            method=method,
            path=path,
            description=description,
            status_code=0,
            response_time_ms=round(elapsed, 1),
            error="Timeout (30s)",
        )


def status_icon(code: int) -> str:
    if code == 0:
        return "CONN_ERR"
    elif 200 <= code < 300:
        return "OK"
    elif code == 401:
        return "UNAUTH"
    elif code == 403:
        return "FORBID"
    elif code == 404:
        return "NOT_FOUND"
    elif code == 422:
        return "VALIDATION"
    elif 400 <= code < 500:
        return f"CLI_{code}"
    elif 500 <= code < 600:
        return f"SRV_{code}"
    else:
        return f"???_{code}"


def classify(summary: TestSummary, result: TestResult):
    summary.total += 1
    summary.results.append(result)
    code = result.status_code
    if code == 0:
        summary.connection_errors += 1
    elif 200 <= code < 300:
        summary.passed += 1
    elif code == 401:
        summary.auth_errors += 1
    elif code == 403:
        summary.forbidden += 1
    elif code == 404:
        summary.not_found += 1
    elif 400 <= code < 500:
        summary.client_errors += 1
    elif 500 <= code < 600:
        summary.server_errors += 1


def main():
    parser = argparse.ArgumentParser(description="Moonjar PMS API Smoke Test")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Base URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument("--email", default=DEFAULT_EMAIL, help="Owner email")
    parser.add_argument("--password", default=DEFAULT_PASSWORD, help="Owner password")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show all results (not just failures)"
    )
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    print("=" * 70)
    print("  MOONJAR PMS — API SMOKE TEST")
    print("=" * 70)
    print(f"  Base URL:   {base_url}")
    print(f"  Endpoints:  {len(ENDPOINTS)}")
    print(f"  Login as:   {args.email}")
    print("=" * 70)

    # ── Login ──────────────────────────────────────────────────────
    session = requests.Session()
    print("\n[1/3] Logging in...")
    if not login(session, base_url, args.email, args.password):
        print("\nFATAL: Cannot login. Aborting.")
        sys.exit(1)

    # ── Run tests ──────────────────────────────────────────────────
    print(f"\n[2/3] Running {len(ENDPOINTS)} endpoint tests...\n")
    summary = TestSummary()

    for i, (method, path, desc) in enumerate(ENDPOINTS, 1):
        result = run_test(session, base_url, method, path, desc)
        classify(summary, result)

        icon = status_icon(result.status_code)
        line = f"  [{i:3d}/{len(ENDPOINTS)}] {icon:10s} {result.status_code:3d}  {result.response_time_ms:7.0f}ms  {method} {path}"

        # Always show failures, optionally show successes
        if result.status_code >= 400 or result.status_code == 0:
            print(f"\033[91m{line}\033[0m")  # Red
            if result.error:
                print(f"           ERROR: {result.error}")
        elif args.verbose:
            print(f"\033[92m{line}\033[0m")  # Green
        else:
            # Progress dot for passing tests
            print(f"\033[92m{line}\033[0m")

    # ── Summary ────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    print(f"  Total endpoints tested:  {summary.total}")
    print(f"  \033[92mPassed (2xx):            {summary.passed}\033[0m")
    if summary.auth_errors:
        print(f"  \033[93mUnauthorized (401):      {summary.auth_errors}\033[0m")
    if summary.forbidden:
        print(f"  \033[93mForbidden (403):         {summary.forbidden}\033[0m")
    if summary.not_found:
        print(f"  \033[93mNot Found (404):         {summary.not_found}\033[0m")
    if summary.client_errors:
        print(f"  \033[91mOther Client Errors:     {summary.client_errors}\033[0m")
    if summary.server_errors:
        print(f"  \033[91mServer Errors (5xx):     {summary.server_errors}\033[0m")
    if summary.connection_errors:
        print(f"  \033[91mConnection Errors:       {summary.connection_errors}\033[0m")

    pass_rate = (summary.passed / summary.total * 100) if summary.total else 0
    print(f"\n  Pass rate: {pass_rate:.1f}%")

    # ── List failures ──────────────────────────────────────────────
    failures = [r for r in summary.results if r.status_code >= 500 or r.status_code == 0]
    if failures:
        print(f"\n  CRITICAL FAILURES ({len(failures)}):")
        for r in failures:
            print(f"    {r.status_code:3d}  {r.method} {r.path}  — {r.description}")
            if r.error:
                print(f"         {r.error}")

    warnings = [r for r in summary.results if 400 <= r.status_code < 500]
    if warnings:
        print(f"\n  WARNINGS ({len(warnings)}):")
        for r in warnings:
            print(f"    {r.status_code:3d}  {r.method} {r.path}  — {r.description}")

    print("\n" + "=" * 70)

    # Exit code: 1 if any 5xx or connection errors
    if summary.server_errors or summary.connection_errors:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
