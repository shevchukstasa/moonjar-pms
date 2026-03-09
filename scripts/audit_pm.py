#!/usr/bin/env python3
"""
audit_pm.py — Full PM (Production Manager) role audit.

Checks that backend architecture, business logic, and frontend
are consistent for the Production Manager role.

Usage:
    python3 scripts/audit_pm.py [--json]

Exit code:
    0 — all checks passed
    1 — critical issues found
"""

import ast
import os
import re
import sys
import json
from pathlib import Path
from typing import NamedTuple, Optional

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
BACKEND_ROUTERS   = ROOT / "api" / "routers"
BACKEND_SERVICES  = ROOT / "business" / "services"
BACKEND_MAIN_PY   = ROOT / "api" / "main.py"
BACKEND_MODELS    = ROOT / "api" / "models.py"
BACKEND_ENUMS     = ROOT / "api" / "enums.py"
BACKEND_ROLES     = ROOT / "api" / "roles.py"
BACKEND_AUTH      = ROOT / "api" / "auth.py"
FRONTEND_PAGES    = ROOT / "presentation" / "dashboard" / "src" / "pages"
FRONTEND_HOOKS    = ROOT / "presentation" / "dashboard" / "src" / "hooks"
FRONTEND_API      = ROOT / "presentation" / "dashboard" / "src" / "api"
FRONTEND_COMPS    = ROOT / "presentation" / "dashboard" / "src" / "components"
FRONTEND_APP      = ROOT / "presentation" / "dashboard" / "src" / "App.tsx"

# ── Role groups (mirrors api/roles.py) ────────────────────────────────────────
REQUIRE_MANAGEMENT = {"owner", "administrator", "ceo", "production_manager"}
REQUIRE_SORTING    = {"owner", "administrator", "production_manager", "sorter_packer"}
REQUIRE_PURCHASER  = {"owner", "administrator", "purchaser"}
REQUIRE_WAREHOUSE  = {"owner", "administrator", "warehouse"}
REQUIRE_QUALITY    = {"owner", "administrator", "quality_manager"}
REQUIRE_ADMIN      = {"owner", "administrator"}
REQUIRE_OWNER      = {"owner"}
REQUIRE_ANY        = {"owner","administrator","ceo","production_manager",
                      "quality_manager","warehouse","sorter_packer","purchaser"}
REQUIRE_AUTH_ONLY  = set()  # just get_current_user — any role

PM_ACCESSIBLE_GROUPS = {
    "require_management": REQUIRE_MANAGEMENT,
    "require_sorting":    REQUIRE_SORTING,
    "require_any":        REQUIRE_ANY,
    "get_current_user":   REQUIRE_AUTH_ONLY,  # read-only public to any auth user
}

PM_INACCESSIBLE_GROUPS = {
    "require_owner":    REQUIRE_OWNER,
    "require_admin":    REQUIRE_ADMIN,
    "require_quality":  REQUIRE_QUALITY,
    "require_warehouse":REQUIRE_WAREHOUSE,
    "require_purchaser":REQUIRE_PURCHASER,
}

# ── PM pages in frontend ──────────────────────────────────────────────────────
PM_PAGES = [
    "ManagerDashboard.tsx",
    "ManagerKilnsPage.tsx",
    "ManagerSchedulePage.tsx",
    "OrderDetailPage.tsx",
    "ShortageDecisionPage.tsx",
    "TabloDashboard.tsx",       # no auth guard — accessible to all
    "SorterPackerDashboard.tsx",# PM has access
    "WarehouseDashboard.tsx",   # PM has access
    "PurchaserDashboard.tsx",   # PM has access
]

# ── Expected backend services (key ones) ──────────────────────────────────────
EXPECTED_SERVICES = {
    "schedule_estimation.py": [
        "calculate_buffer",
        "calculate_position_availability",
        "calculate_production_days",
        "calculate_schedule_deadline",
        "recalculate_all_estimates",
    ],
    "buffer_health.py": [
        "calculate_buffer_health",
        "apply_rope_limit",
    ],
    "defect_coefficient.py": [
        "update_stone_defect_coefficient",
        "get_stone_defect_coefficient",
    ],
    "daily_kpi.py": [
        "calculate_dashboard_summary",
        "calculate_on_time_rate",
        "calculate_defect_rate",
        "calculate_kiln_utilization",
        "calculate_production_metrics",
        "calculate_material_metrics",
        "calculate_factory_comparison",
    ],
    "reconciliation.py": [
        "reconcile_stage_transition",
        "inventory_reconciliation",
    ],
}

# ── Data structures ────────────────────────────────────────────────────────────
class Endpoint(NamedTuple):
    method:     str   # GET/POST/PATCH/DELETE
    path:       str   # e.g. /orders/{order_id}
    router_prefix: str  # e.g. /orders
    full_path:  str   # e.g. /orders/{order_id}
    auth:       str   # require_management / require_owner / get_current_user / public / etc.
    pm_access:  bool
    is_stub:    bool
    file:       str

class ApiCall(NamedTuple):
    method:   str   # get/post/patch/delete
    path:     str   # raw string e.g. '/orders' or f-string pattern
    page:     str   # source file
    line:     int

class Issue(NamedTuple):
    severity: str  # CRITICAL / WARNING / INFO
    category: str
    message:  str
    detail:   Optional[str] = None

# ── Helpers ────────────────────────────────────────────────────────────────────
def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except FileNotFoundError:
        return ""

def _py_files(directory: Path):
    return sorted(directory.glob("*.py")) if directory.exists() else []

def _ts_files(directory: Path):
    return sorted(directory.glob("*.tsx")) + sorted(directory.glob("*.ts")) \
           if directory.exists() else []

# ── 1. Parse backend router files ─────────────────────────────────────────────
ROUTER_PREFIX_RE = re.compile(
    r'prefix\s*=\s*["\']([^"\']+)["\']'
)
# Match @router.get("", ...) or @router.get("/path", ...) then the function def
ENDPOINT_RE = re.compile(
    r'@router\.(get|post|patch|put|delete)\(\s*["\']([^"\']*)["\']',
    re.IGNORECASE,
)
# Auth decorator patterns in function body
AUTH_DEPENDS_RE = re.compile(
    r'Depends\((require_management|require_owner|require_admin|require_quality'
    r'|require_warehouse|require_purchaser|require_sorting|require_any'
    r'|get_current_user|_require_read|_require_write)\)'
)
STUB_RE = re.compile(r'raise\s+NotImplementedError|# ?TODO.*stub|pass\s*#\s*stub', re.IGNORECASE)

def _get_router_prefix(content: str) -> str:
    m = ROUTER_PREFIX_RE.search(content)
    return m.group(1) if m else ""

def _classify_auth(auth_token: str) -> tuple[str, bool]:
    """Returns (canonical_auth_name, pm_has_access)."""
    if auth_token in ("require_management", "require_sorting", "require_any", "get_current_user"):
        return auth_token, True
    if auth_token in ("require_owner", "require_admin", "_require_write"):
        return auth_token, False
    if auth_token in ("require_quality", "require_warehouse", "require_purchaser", "_require_read"):
        return auth_token, False
    return auth_token, False

def parse_endpoints() -> list[Endpoint]:
    """Parse all backend router files and extract endpoints with auth info."""
    endpoints = []

    # Map router file → API prefix from main.py
    main_content = _read(BACKEND_MAIN_PY)
    # e.g. app.include_router(orders.router, prefix="/api/orders", ...)
    include_re = re.compile(
        r'include_router\([^,]+,\s*prefix=["\']([^"\']+)["\']'
    )
    prefix_map: dict[str, str] = {}
    for m in include_re.finditer(main_content):
        prefix = m.group(1)
        # extract just the last segment for mapping to file name
        last = prefix.rsplit("/", 1)[-1]
        prefix_map[last] = prefix

    for router_file in _py_files(BACKEND_ROUTERS):
        fname = router_file.name
        if fname.startswith("__"):
            continue
        content = _read(router_file)
        stem = fname.replace(".py", "")

        # Determine prefix
        api_prefix = prefix_map.get(stem, f"/api/{stem.replace('_', '-')}")
        # Normalize hyphens/underscores
        for k, v in prefix_map.items():
            if k.replace("-","_") == stem.replace("-","_"):
                api_prefix = v
                break

        # Walk through lines, capture endpoint then next Depends
        lines = content.split("\n")
        for i, line in enumerate(lines):
            em = ENDPOINT_RE.search(line)
            if not em:
                continue
            method = em.group(1).upper()
            sub_path = em.group(2)  # e.g. "" or "/{id}" or "/cancellation-requests"
            full_path = (api_prefix + sub_path).rstrip("/") or "/"

            # Scan next ~15 lines for Depends(...)
            snippet = "\n".join(lines[i:i+20])
            is_stub = bool(STUB_RE.search(snippet))

            am = AUTH_DEPENDS_RE.search(snippet)
            if am:
                raw_auth = am.group(1)
            else:
                # Check if it's a public/integration endpoint
                if "x_api_key" in snippet.lower() or "x-api-key" in snippet.lower():
                    raw_auth = "x_api_key"
                else:
                    raw_auth = "public"

            auth_name, pm_access = _classify_auth(raw_auth)

            endpoints.append(Endpoint(
                method=method,
                path=sub_path,
                router_prefix=api_prefix,
                full_path=full_path,
                auth=auth_name,
                pm_access=pm_access,
                is_stub=is_stub,
                file=fname,
            ))

    return endpoints


# ── 2. Parse frontend PM pages for API calls ──────────────────────────────────
API_CALL_RE = re.compile(
    r'apiClient\.(get|post|patch|put|delete)\(\s*[`\'"]([^`\'"]+)[`\'"]'
    r'|axios\.(get|post|patch|put|delete)\(\s*[`\'"]([^`\'"]+)[`\'"]'
)
HOOK_USE_RE = re.compile(r'(use\w+)\(')
IMPORT_API_RE = re.compile(r"from\s+['\"]@/api/(\w+)['\"]")
IS_ERROR_RE = re.compile(r'isError')

def parse_pm_api_calls() -> list[ApiCall]:
    calls = []
    for page_name in PM_PAGES:
        page_path = FRONTEND_PAGES / page_name
        content = _read(page_path)
        if not content:
            continue
        for m in API_CALL_RE.finditer(content):
            method = (m.group(1) or m.group(3) or "").lower()
            path   = (m.group(2) or m.group(4) or "")
            line_no = content[:m.start()].count("\n") + 1
            calls.append(ApiCall(method=method, path=path, page=page_name, line=line_no))
    return calls

def parse_hook_calls_in_pm_pages() -> dict[str, list[str]]:
    """For each PM page, find which hooks are used."""
    result: dict[str, list[str]] = {}
    for page_name in PM_PAGES:
        content = _read(FRONTEND_PAGES / page_name)
        hooks = sorted(set(HOOK_USE_RE.findall(content)))
        result[page_name] = [h for h in hooks if h.startswith("use")]
    return result

def parse_api_module_calls() -> dict[str, list[str]]:
    """
    For each hook file referenced from PM pages, extract what API paths it calls.
    Returns: {hook_file: ["/path1", "/path2", ...]}
    """
    result: dict[str, list[str]] = {}
    for hf in _ts_files(FRONTEND_HOOKS):
        content = _read(hf)
        paths = []
        for m in API_CALL_RE.finditer(content):
            p = m.group(2) or m.group(4) or ""
            if p:
                paths.append(p)
        if paths:
            result[hf.name] = paths
    return result


# ── 3. Parse business services for stubs ──────────────────────────────────────
def check_services() -> list[Issue]:
    issues = []
    for svc_file, expected_funcs in EXPECTED_SERVICES.items():
        svc_path = BACKEND_SERVICES / svc_file
        content = _read(svc_path)
        if not content:
            issues.append(Issue("CRITICAL", "service_missing",
                                f"Service file not found: {svc_file}"))
            continue

        for fn in expected_funcs:
            if fn not in content:
                issues.append(Issue("CRITICAL", "service_function_missing",
                                    f"{svc_file}: function '{fn}' not found"))
                continue
            # Check if the function is a stub (raise NotImplementedError or just `pass`)
            fn_re = re.compile(
                rf"def {fn}\([^)]*\)[^:]*:.*?(?=\ndef |\Z)",
                re.DOTALL,
            )
            m = fn_re.search(content)
            if m:
                body = m.group(0)
                if "raise NotImplementedError" in body or (
                    re.search(r"def \w+\([^)]*\)[^:]*:\s*\n\s*pass\s*\n", body)
                ):
                    issues.append(Issue("CRITICAL", "service_stub",
                                        f"{svc_file}: function '{fn}' is a stub"))
    return issues


# ── 4. Check PM frontend pages for isError handling ──────────────────────────
def check_error_handling() -> list[Issue]:
    issues = []
    for page_name in PM_PAGES:
        content = _read(FRONTEND_PAGES / page_name)
        if not content:
            continue
        # Check if page has any isLoading usage but no isError
        has_loading = bool(re.search(r'isLoading', content))
        has_error   = bool(IS_ERROR_RE.search(content))
        if has_loading and not has_error:
            issues.append(Issue(
                "WARNING", "no_error_handling",
                f"{page_name}: uses isLoading but has no isError handling",
                "API failures will silently show empty content",
            ))
    return issues


# ── 5. Check frontend route guards ───────────────────────────────────────────
def check_route_guards() -> list[Issue]:
    issues = []
    app_content = _read(FRONTEND_APP)
    if not app_content:
        issues.append(Issue("CRITICAL", "app_tsx_missing", "App.tsx not found"))
        return issues

    # PM pages must be inside RequireRole with production_manager
    pm_required_routes = {
        "/manager":          "production_manager",
        "/manager/schedule": "production_manager",
        "/manager/kilns":    "production_manager",
        "/manager/shortage": "production_manager",
    }
    for route, role in pm_required_routes.items():
        route_escaped = route.replace("/", r"\/?")
        # Find if route has RequireRole guard containing the role
        pattern = re.compile(
            rf'RequireRole[^>]+roles[^>]+{role}[^>]*>.*?path=["\'][^"\']*{re.escape(route)}',
            re.DOTALL,
        )
        if not pattern.search(app_content):
            # Fallback: just check role appears near the route path
            idx = app_content.find(f'"{route}"')
            if idx == -1:
                idx = app_content.find(f"'{route}'")
            if idx >= 0:
                # Check if production_manager is within 500 chars before
                context = app_content[max(0, idx-500):idx+200]
                if "production_manager" not in context:
                    issues.append(Issue(
                        "WARNING", "route_guard_missing_role",
                        f"Route '{route}' may not have production_manager in RequireRole guard",
                        "Check App.tsx manually",
                    ))

    # /tablo should be accessible (no role guard or all-roles guard)
    tablo_idx = app_content.find('"/tablo"')
    if tablo_idx >= 0:
        context = app_content[max(0, tablo_idx-200):tablo_idx+100]
        if "RequireRole" in context:
            issues.append(Issue(
                "INFO", "tablo_route_guard",
                "/tablo route appears to have a role guard (expected: open to all authenticated users)",
            ))

    return issues


# ── 6. Cross-reference: frontend hooks → backend endpoints ───────────────────
def cross_reference(endpoints: list[Endpoint]) -> list[Issue]:
    """
    Check that every API path called from PM hooks/pages
    has a corresponding backend endpoint accessible to PM.
    """
    issues = []

    # Build backend endpoint lookup: normalized_path → list[Endpoint]
    be_lookup: dict[str, list[Endpoint]] = {}
    for ep in endpoints:
        norm = _normalize_path(ep.full_path)
        be_lookup.setdefault(norm, []).append(ep)

    # Collect all paths from PM hook files
    pm_hooks = set()
    hook_pages = parse_hook_calls_in_pm_pages()
    for page_hooks in hook_pages.values():
        pm_hooks.update(page_hooks)

    # Check every hook file that might be used by PM pages
    for hf in _ts_files(FRONTEND_HOOKS):
        content = _read(hf)
        # Only process hooks that appear in PM pages
        hook_fns = re.findall(r'export function (use\w+)', content)
        if not any(fn in pm_hooks for fn in hook_fns):
            continue

        for m in API_CALL_RE.finditer(content):
            raw_path = m.group(2) or m.group(4) or ""
            if not raw_path:
                continue
            # Skip template literal paths with complex expressions
            if "${" in raw_path and raw_path.count("${") > 1:
                continue

            norm = _normalize_path(raw_path)
            matched = be_lookup.get(norm)

            if not matched:
                # Try partial match (template literals like /orders/${id})
                matched = _fuzzy_match(norm, be_lookup)

            if not matched:
                issues.append(Issue(
                    "WARNING", "frontend_path_no_backend",
                    f"{hf.name}: calls '{raw_path}' — no matching backend endpoint found",
                    "Endpoint may use different path or may not exist",
                ))
                continue

            # Check PM can actually access the matched endpoint
            pm_accessible = any(ep.pm_access for ep in matched)
            if not pm_accessible:
                issues.append(Issue(
                    "CRITICAL", "pm_access_denied",
                    f"{hf.name}: calls '{raw_path}' but PM role cannot access "
                    f"(auth: {matched[0].auth})",
                ))

            # Check if endpoint is a stub
            for ep in matched:
                if ep.is_stub and ep.pm_access:
                    issues.append(Issue(
                        "WARNING", "backend_stub",
                        f"{hf.name}: calls '{raw_path}' → {ep.file} is a stub (NotImplementedError)",
                    ))

    return issues


def _normalize_path(path: str) -> str:
    """Normalize path for comparison: strip /api prefix, replace {param} with *."""
    p = path.strip()
    p = re.sub(r"^\$\{[^}]+\}", "", p)   # strip leading template expressions
    p = re.sub(r"/api", "", p, count=1)
    p = re.sub(r"\$\{[^}]+\}", "*", p)   # ${id} → *
    p = re.sub(r"\{[^}]+\}", "*", p)     # {id} → *
    p = p.rstrip("/").lower()
    return p


def _fuzzy_match(norm: str, lookup: dict[str, list]) -> list:
    """Try to match with wildcard segments."""
    # e.g. /orders/* should match /orders/{order_id}
    norm_parts = norm.split("/")
    for key, val in lookup.items():
        key_parts = key.split("/")
        if len(norm_parts) != len(key_parts):
            continue
        if all(a == b or b == "*" or a == "*" for a, b in zip(norm_parts, key_parts)):
            return val
    return []


# ── 7. Check PM-accessible backend endpoints for stubs ───────────────────────
def check_pm_endpoint_stubs(endpoints: list[Endpoint]) -> list[Issue]:
    issues = []
    for ep in endpoints:
        if ep.pm_access and ep.is_stub:
            issues.append(Issue(
                "CRITICAL", "pm_endpoint_stub",
                f"{ep.file}: {ep.method} {ep.full_path} is a stub (PM can access but it's not implemented)",
            ))
    return issues


# ── 8. Check DB columns exist for cancellation flow ──────────────────────────
def check_model_fields() -> list[Issue]:
    issues = []
    models_content = _read(BACKEND_MODELS)
    required_fields = {
        "cancellation_requested":    "ProductionOrder",
        "cancellation_requested_at": "ProductionOrder",
        "cancellation_decision":     "ProductionOrder",
        "cancellation_decided_at":   "ProductionOrder",
        "cancellation_decided_by":   "ProductionOrder",
        "shipped_at":                "ProductionOrder",
        "external_id":               "ProductionOrder",
    }
    for field, model in required_fields.items():
        if field not in models_content:
            issues.append(Issue(
                "CRITICAL", "model_field_missing",
                f"{model}: field '{field}' not found in models.py",
            ))
    return issues


# ── 9. Check notification types cover PM needs ───────────────────────────────
def check_enums() -> list[Issue]:
    issues = []
    enums_content = _read(BACKEND_ENUMS)
    required_enum_values = [
        "cancellation_request",
        "task_assigned",
        "stock_shortage",
        "reconciliation_discrepancy",
        "alert",
    ]
    for val in required_enum_values:
        if val not in enums_content:
            issues.append(Issue(
                "WARNING", "enum_value_missing",
                f"NotificationType missing value: '{val}'",
            ))
    return issues


# ── 10. Check frontend components exist ──────────────────────────────────────
def check_frontend_components() -> list[Issue]:
    issues = []
    required_components = {
        "components/dashboard/CancellationRequestsPanel.tsx": "PM cancellation panel",
        "components/dashboard/BufferHealthTable.tsx":         "TOC buffer health",
        "components/dashboard/CriticalPositionsTable.tsx":    "Critical positions",
        "components/dashboard/MaterialDeficitsTable.tsx":     "Material deficits",
        "components/dashboard/ActivityFeed.tsx":              "Activity feed",
        "components/tablo/SectionTable.tsx":                  "Tablo section table",
        "components/tablo/KilnCard.tsx":                      "Kiln card",
    }
    src = ROOT / "presentation" / "dashboard" / "src"
    for rel_path, description in required_components.items():
        full = src / rel_path
        if not full.exists():
            issues.append(Issue(
                "CRITICAL", "component_missing",
                f"Missing component: {rel_path} ({description})",
            ))
        else:
            content = _read(full)
            if len(content.strip()) < 50:
                issues.append(Issue(
                    "WARNING", "component_empty",
                    f"Component appears empty or minimal: {rel_path}",
                ))
    return issues


# ── 11. Check integration endpoint format ─────────────────────────────────────
def check_integration_endpoints(endpoints: list[Endpoint]) -> list[Issue]:
    issues = []
    integration_paths = [ep.full_path for ep in endpoints if "integration" in ep.file]

    required_integration = [
        "/api/integration/orders/{external_id}/production-status",
        "/api/integration/orders/status-updates",
        "/api/integration/webhook/sales-order",
        "/api/integration/orders/{external_id}/request-cancellation",
    ]
    for req in required_integration:
        norm = _normalize_path(req)
        found = any(_normalize_path(p) == norm or _fuzzy_match(norm, {_normalize_path(p): [p] for p in integration_paths}) for p in integration_paths)
        if not found:
            # Try fuzzy
            found2 = bool(_fuzzy_match(norm, {_normalize_path(p): [p] for p in integration_paths}))
            if not found2:
                issues.append(Issue(
                    "CRITICAL", "integration_endpoint_missing",
                    f"Integration endpoint not found: {req}",
                ))
    return issues


# ── 12. Summarise all PM-accessible endpoints ──────────────────────────────────
def summarize_pm_endpoints(endpoints: list[Endpoint]) -> dict:
    pm_eps = [ep for ep in endpoints if ep.pm_access]
    by_router: dict[str, list[str]] = {}
    for ep in pm_eps:
        router = ep.file.replace(".py", "")
        by_router.setdefault(router, []).append(f"{ep.method:7} {ep.full_path}")
    return by_router


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    use_json = "--json" in sys.argv

    print("=" * 70)
    print("PM ROLE AUDIT — Moonjar PMS")
    print("=" * 70)

    all_issues: list[Issue] = []

    # 1. Parse endpoints
    print("\n[1/9] Parsing backend endpoints...")
    endpoints = parse_endpoints()
    pm_eps = [ep for ep in endpoints if ep.pm_access]
    print(f"      Total endpoints: {len(endpoints)}")
    print(f"      PM-accessible:   {len(pm_eps)}")
    pm_by_router = summarize_pm_endpoints(endpoints)

    # 2. Check business services
    print("[2/9] Checking business services...")
    svc_issues = check_services()
    all_issues.extend(svc_issues)
    print(f"      Issues: {len(svc_issues)}")

    # 3. Check PM-accessible endpoint stubs
    print("[3/9] Checking for stubs in PM-accessible endpoints...")
    stub_issues = check_pm_endpoint_stubs(endpoints)
    all_issues.extend(stub_issues)
    print(f"      Issues: {len(stub_issues)}")

    # 4. Cross-reference frontend hooks → backend
    print("[4/9] Cross-referencing frontend API calls → backend...")
    xref_issues = cross_reference(endpoints)
    all_issues.extend(xref_issues)
    print(f"      Issues: {len(xref_issues)}")

    # 5. Error handling
    print("[5/9] Checking error handling in PM pages...")
    err_issues = check_error_handling()
    all_issues.extend(err_issues)
    print(f"      Issues: {len(err_issues)}")

    # 6. Route guards
    print("[6/9] Checking frontend route guards...")
    guard_issues = check_route_guards()
    all_issues.extend(guard_issues)
    print(f"      Issues: {len(guard_issues)}")

    # 7. Model fields
    print("[7/9] Checking DB model fields...")
    model_issues = check_model_fields()
    all_issues.extend(model_issues)
    print(f"      Issues: {len(model_issues)}")

    # 8. Enums
    print("[8/9] Checking enums...")
    enum_issues = check_enums()
    all_issues.extend(enum_issues)
    print(f"      Issues: {len(enum_issues)}")

    # 9. Frontend components
    print("[9/9] Checking frontend components...")
    comp_issues = check_frontend_components()
    all_issues.extend(comp_issues)
    print(f"      Issues: {len(comp_issues)}")

    # Integration endpoints
    int_issues = check_integration_endpoints(endpoints)
    all_issues.extend(int_issues)

    # ── Report ────────────────────────────────────────────────────────────────
    if use_json:
        out = {
            "total_endpoints": len(endpoints),
            "pm_accessible_endpoints": len(pm_eps),
            "pm_endpoints_by_router": pm_by_router,
            "issues": [
                {"severity": i.severity, "category": i.category,
                 "message": i.message, "detail": i.detail}
                for i in all_issues
            ],
            "summary": {
                "CRITICAL": sum(1 for i in all_issues if i.severity == "CRITICAL"),
                "WARNING":  sum(1 for i in all_issues if i.severity == "WARNING"),
                "INFO":     sum(1 for i in all_issues if i.severity == "INFO"),
            }
        }
        print(json.dumps(out, indent=2))
        return

    # ── Human-readable output ─────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("PM-ACCESSIBLE ENDPOINTS (by router)")
    print("=" * 70)
    for router, eps in sorted(pm_by_router.items()):
        print(f"\n  [{router}]")
        for ep in eps:
            print(f"    {ep}")

    print("\n" + "=" * 70)
    print("ISSUES")
    print("=" * 70)

    criticals = [i for i in all_issues if i.severity == "CRITICAL"]
    warnings  = [i for i in all_issues if i.severity == "WARNING"]
    infos     = [i for i in all_issues if i.severity == "INFO"]

    if criticals:
        print(f"\n  ❌  CRITICAL ({len(criticals)})")
        for i in criticals:
            print(f"    [{i.category}] {i.message}")
            if i.detail:
                print(f"      → {i.detail}")
    else:
        print("\n  ✅  No CRITICAL issues")

    if warnings:
        print(f"\n  ⚠   WARNING ({len(warnings)})")
        for i in warnings:
            print(f"    [{i.category}] {i.message}")
            if i.detail:
                print(f"      → {i.detail}")
    else:
        print("  ✅  No WARNING issues")

    if infos:
        print(f"\n  ℹ   INFO ({len(infos)})")
        for i in infos:
            print(f"    [{i.category}] {i.message}")

    print("\n" + "=" * 70)
    total = len(all_issues)
    crit  = len(criticals)
    print(f"SUMMARY: {len(endpoints)} backend endpoints | {len(pm_eps)} PM-accessible "
          f"| {total} issues ({crit} critical, {len(warnings)} warnings)")

    if crit > 0:
        print("STATUS: ❌  CRITICAL issues found — check items above")
        sys.exit(1)
    elif warnings:
        print("STATUS: ⚠   Passed with warnings")
        sys.exit(0)
    else:
        print("STATUS: ✅  All checks passed")
        sys.exit(0)


if __name__ == "__main__":
    main()
