#!/usr/bin/env python3
"""
Architecture Audit Script — сравнивает документацию с реальным кодом.

Находит:
1. Backend роутеры без фронтенд-страниц
2. Фронтенд-страницы без маршрутов в App.tsx
3. Модели БД без API роутеров
4. API эндпоинты без фронтенд-вызовов
5. Sidebar-ссылки на несуществующие маршруты
6. Роутеры зарегистрированные в main.py vs файлы в api/routers/
7. Импорты в main.py vs реальные файлы

Запуск: python scripts/architecture_audit.py
"""

import os
import re
import sys
from pathlib import Path
from collections import defaultdict

# ── Paths ─────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
API_DIR = ROOT / "api"
ROUTERS_DIR = API_DIR / "routers"
MODELS_FILE = API_DIR / "models.py"
MAIN_FILE = API_DIR / "main.py"
DASHBOARD_DIR = ROOT / "presentation" / "dashboard" / "src"
PAGES_DIR = DASHBOARD_DIR / "pages"
APP_TSX = DASHBOARD_DIR / "App.tsx"
SIDEBAR_FILE = DASHBOARD_DIR / "components" / "layout" / "Sidebar.tsx"
API_CLIENT_DIR = DASHBOARD_DIR / "api"

# ── Colors ────────────────────────────────────────────────────────────
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def header(title: str):
    print(f"\n{BOLD}{CYAN}{'═' * 60}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'═' * 60}{RESET}")


def ok(msg: str):
    print(f"  {GREEN}✓{RESET} {msg}")


def warn(msg: str):
    print(f"  {YELLOW}⚠{RESET} {msg}")


def err(msg: str):
    print(f"  {RED}✗{RESET} {msg}")


def dim(msg: str):
    print(f"  {DIM}{msg}{RESET}")


# ── 1. Router files vs main.py registrations ─────────────────────────
def audit_routers():
    header("1. Backend Routers: файлы vs регистрация в main.py")

    # Get all .py files in routers dir (excluding __init__)
    router_files = {
        f.stem for f in ROUTERS_DIR.glob("*.py")
        if f.stem != "__init__" and not f.stem.startswith("_")
    }

    # Parse main.py for registered routers
    main_text = MAIN_FILE.read_text()
    # Pattern: import X from routers or include_router(X.router, ...)
    registered_imports = set()
    for m in re.finditer(r"from\s+api\.routers\s+import\s+(.+)", main_text):
        names = [n.strip() for n in m.group(1).split(",")]
        registered_imports.update(names)
    for m in re.finditer(r"from\s+api\.routers\.(\w+)\s+import", main_text):
        registered_imports.add(m.group(1))

    # Also find include_router calls
    registered_routers = set()
    for m in re.finditer(r"include_router\(\s*(\w+)\.router", main_text):
        registered_routers.add(m.group(1))
    # Handle aliased imports like "settings_router"
    for m in re.finditer(r"(\w+)\s+as\s+(\w+)", main_text):
        if m.group(2) in registered_routers:
            registered_routers.discard(m.group(2))
            registered_routers.add(m.group(1))

    # Extract prefixes
    prefix_map = {}
    for m in re.finditer(
        r'include_router\(\s*(\w+)\.router.*?prefix="(/api/[^"]+)"', main_text
    ):
        prefix_map[m.group(1)] = m.group(2)

    unregistered = router_files - registered_routers - registered_imports
    unused_imports = registered_imports - router_files

    issues = 0
    if unregistered:
        for r in sorted(unregistered):
            err(f"Router FILE exists but NOT registered in main.py: {r}.py")
            issues += 1
    if unused_imports:
        for r in sorted(unused_imports):
            warn(f"Imported in main.py but no router file: {r}")
            issues += 1

    if issues == 0:
        ok(f"All {len(router_files)} router files registered in main.py")

    return prefix_map


# ── 2. Frontend pages vs App.tsx routes ───────────────────────────────
def audit_frontend_routes():
    header("2. Frontend: страницы vs маршруты в App.tsx")

    # Get all page files
    page_files = {f.stem for f in PAGES_DIR.glob("*.tsx")}

    # Parse App.tsx for imported pages and route paths
    app_text = APP_TSX.read_text()

    # Find imports
    imported_pages = set()
    for m in re.finditer(r"import\s+(\w+)\s+from\s+['\"].*?pages/(\w+)['\"]", app_text):
        imported_pages.add(m.group(2))

    # Find lazy imports
    for m in re.finditer(r"lazy\(\(\)\s*=>\s*import\(['\"].*?pages/(\w+)['\"]\)", app_text):
        imported_pages.add(m.group(1))

    # Find all <Route ... element={<ComponentName ...} />
    route_components = set()
    for m in re.finditer(r"element=\{<(\w+)", app_text):
        route_components.add(m.group(1))

    # Find route paths
    route_paths = []
    for m in re.finditer(r'path="([^"]+)"', app_text):
        route_paths.append(m.group(1))

    # Pages without routes
    issues = 0
    for page in sorted(page_files):
        if page in ("NotFoundPage",):
            continue
        if page not in route_components and page not in imported_pages:
            # Check if it's used as a component name inside App.tsx at all
            if page not in app_text:
                warn(f"Page FILE exists but NOT used in App.tsx: {page}.tsx")
                issues += 1

    if issues == 0:
        ok(f"All {len(page_files)} page files referenced in App.tsx")

    return route_paths, route_components


# ── 3. Sidebar links vs actual routes ─────────────────────────────────
def audit_sidebar(route_paths: list):
    header("3. Sidebar: ссылки vs реальные маршруты")

    if not SIDEBAR_FILE.exists():
        warn("Sidebar.tsx not found")
        return

    sidebar_text = SIDEBAR_FILE.read_text()

    # Extract all `to: '/...'` links
    sidebar_links = []
    for m in re.finditer(r"to:\s*['\"]([^'\"]+)['\"]", sidebar_text):
        sidebar_links.append(m.group(1))

    issues = 0
    for link in sidebar_links:
        # Normalize: remove trailing slashes, handle dynamic segments
        clean = link.rstrip("/")
        if clean not in route_paths and not any(
            clean.startswith(rp.split(":")[0].rstrip("/")) for rp in route_paths
        ):
            err(f"Sidebar link '{link}' → no matching route in App.tsx")
            issues += 1

    if issues == 0:
        ok(f"All {len(sidebar_links)} sidebar links match routes in App.tsx")


# ── 4. Models without API endpoints ──────────────────────────────────
def audit_models_vs_api(prefix_map: dict):
    header("4. Models: таблицы БД vs API coverage")

    models_text = MODELS_FILE.read_text()

    # Extract model class names and their __tablename__
    model_tables = {}
    current_class = None
    for line in models_text.splitlines():
        m = re.match(r"class\s+(\w+)\(Base\):", line)
        if m:
            current_class = m.group(1)
        m2 = re.match(r'\s+__tablename__\s*=\s*["\'](\w+)["\']', line)
        if m2 and current_class:
            model_tables[current_class] = m2.group(1)

    # Models that are "utility" / join tables — don't need direct CRUD
    UTILITY_MODELS = {
        "UserFactory", "RecipeMaterial", "RecipeKilnConfig", "ReferenceAuditLog",
        "SalesWebhookEvent", "ProductionOrderStatusLog", "OrderStageHistory",
        "SecurityAuditLog", "ActiveSession", "IpAllowlist", "TotpBackupCode",
        "RateLimitEvent", "RecipeFiringStage", "KilnMaintenanceMaterial",
        "KilnActualLoad", "FiringTemperatureGroupRecipe", "OperationLog",
        "BackupLog", "KilnInspectionResult", "StoneReservationAdjustment",
        "MasterPermission",
    }

    # Check which models have corresponding routers
    # Heuristic: model name → table name → look for it in router files
    router_contents = {}
    for f in ROUTERS_DIR.glob("*.py"):
        if f.stem != "__init__":
            router_contents[f.stem] = f.read_text()

    all_router_text = "\n".join(router_contents.values())

    issues = 0
    for model_name, table_name in sorted(model_tables.items()):
        if model_name in UTILITY_MODELS:
            continue
        # Check if model class is referenced in any router
        if model_name not in all_router_text and table_name not in all_router_text:
            warn(f"Model '{model_name}' (table: {table_name}) — not referenced in any API router")
            issues += 1

    if issues == 0:
        ok(f"All {len(model_tables)} models have API coverage")
    else:
        dim(f"({len(model_tables) - issues} models have coverage, {issues} may be missing)")


# ── 5. Backend API endpoints without frontend API client calls ────────
def audit_api_clients():
    header("5. Frontend API clients vs backend endpoints")

    if not API_CLIENT_DIR.exists():
        warn("Frontend api/ directory not found")
        return

    # Collect ALL frontend source files (api clients + pages + components)
    all_frontend_text = ""
    for ext in ("*.ts", "*.tsx"):
        for f in DASHBOARD_DIR.rglob(ext):
            all_frontend_text += f.read_text() + "\n"

    # Find all API paths referenced in frontend:
    # 1. Full paths: '/api/orders', "/api/kilns"
    # 2. Relative paths used with apiClient: '/orders', '/kilns', `/orders/${id}`
    frontend_path_segments = set()

    # Direct /api/ paths
    for m in re.finditer(r"['\"`](/api/[\w-]+)", all_frontend_text):
        segment = m.group(1).replace("/api/", "")
        frontend_path_segments.add(segment)

    # Relative paths via apiClient.get/post/patch/delete/put('/path')
    for m in re.finditer(r"(?:apiClient|api|client|axios)\.\w+\(\s*['\"`]/?(\w[\w-]*)", all_frontend_text):
        frontend_path_segments.add(m.group(1))

    # Template literals: `/orders/${id}`, '/kilns/${..}'
    for m in re.finditer(r"[`'\"]/?(\w[\w-]*)(?:/\$\{|/\w)", all_frontend_text):
        frontend_path_segments.add(m.group(1))

    # Also catch fetch('/something') patterns
    for m in re.finditer(r"fetch\(['\"`]/?(\w[\w-]*)", all_frontend_text):
        frontend_path_segments.add(m.group(1))

    # Parse main.py for registered prefixes
    main_text = MAIN_FILE.read_text()
    registered_prefixes = {}
    for m in re.finditer(r'include_router\(\s*\w+\.router.*?prefix="(/api/([\w-]+))"', main_text):
        registered_prefixes[m.group(1)] = m.group(2)

    # Internal-only endpoints that don't need frontend
    INTERNAL_ONLY = {
        "cleanup", "ws", "telegram", "integration", "transcription",
        "health", "security", "guides",
    }

    # Check which backend prefixes have NO frontend reference
    issues = 0
    for full_prefix, segment in sorted(registered_prefixes.items()):
        if segment in INTERNAL_ONLY:
            continue
        # Check if segment or any variant matches
        has_client = (
            segment in frontend_path_segments
            or segment.replace("-", "_") in frontend_path_segments
            or segment.replace("-", "") in frontend_path_segments
            or any(segment in fp for fp in frontend_path_segments)
        )
        if not has_client:
            warn(f"Backend '{full_prefix}' — no frontend references found")
            issues += 1

    if issues == 0:
        ok(f"All {len(registered_prefixes)} backend endpoints have frontend coverage")
    else:
        dim(f"({len(registered_prefixes) - len(INTERNAL_ONLY) - issues} covered, {issues} without frontend)")


# ── 6. Orphan frontend pages (no sidebar link) ───────────────────────
def audit_page_accessibility():
    header("6. Page accessibility: страницы без ссылок в Sidebar")

    if not SIDEBAR_FILE.exists():
        warn("Sidebar.tsx not found")
        return

    sidebar_text = SIDEBAR_FILE.read_text()
    app_text = APP_TSX.read_text()

    # Get route path → component mapping
    route_map = {}
    for m in re.finditer(r'path="([^"]+)".*?element=\{<(\w+)', app_text):
        route_map[m.group(1)] = m.group(2)

    # Get sidebar links
    sidebar_paths = set()
    for m in re.finditer(r"to:\s*['\"]([^'\"]+)['\"]", sidebar_text):
        sidebar_paths.add(m.group(1))

    # Pages that are accessed via navigation, not sidebar
    NAVIGATED_PAGES = {
        "/login", "/", "/settings", "*",
        # Detail/sub-pages accessed via click
        "/manager/orders/:orderId", "/manager/shortage/:taskId",
        "/manager/size-resolution/:taskId", "/admin/size-resolution/:taskId",
    }

    issues = 0
    for path, component in sorted(route_map.items()):
        if path in NAVIGATED_PAGES:
            continue
        # Check if path or any prefix matches sidebar
        if path not in sidebar_paths and not any(
            sp.rstrip("/") == path.rstrip("/") for sp in sidebar_paths
        ):
            warn(f"Route '{path}' ({component}) — not linked in Sidebar")
            issues += 1

    if issues == 0:
        ok("All routed pages are accessible from Sidebar")


# ── 7. Роутер-эндпоинты: HTTP methods ────────────────────────────────
def audit_endpoint_methods():
    header("7. API endpoint coverage: GET/POST/PATCH/DELETE per router")

    METHOD_PATTERN = re.compile(
        r'@router\.(get|post|put|patch|delete)\(\s*["\']([^"\']*)["\']'
    )

    stats = {}
    for f in sorted(ROUTERS_DIR.glob("*.py")):
        if f.stem == "__init__":
            continue
        text = f.read_text()
        methods = defaultdict(list)
        for m in METHOD_PATTERN.finditer(text):
            methods[m.group(1).upper()].append(m.group(2))
        if methods:
            stats[f.stem] = dict(methods)

    # Routers where POST without DELETE is expected (not CRUD entities)
    NO_DELETE_OK = {
        "ai_chat", "auth", "export", "health", "integration",
        "schedule", "settings", "notifications", "grinding",
    }

    # Find routers with no DELETE (potential issue for CRUD)
    crud_issues = []
    for name, methods in sorted(stats.items()):
        has_post = "POST" in methods
        has_delete = "DELETE" in methods

        if has_post and not has_delete and name not in NO_DELETE_OK:
            crud_issues.append(name)
            warn(f"Router '{name}': has POST but no DELETE")

        # Summary line
        method_str = " ".join(
            f"{m}:{len(eps)}" for m, eps in sorted(methods.items())
        )
        dim(f"{name}: {method_str}")

    if not crud_issues:
        ok("All CRUD routers have matching DELETE endpoints")


# ── 8. Schema patches vs models consistency ───────────────────────────
def audit_schema_patches():
    header("8. Schema patches: файлы vs регистрация в main.py")

    patches_dir = API_DIR / "schema_patches"
    if not patches_dir.exists():
        warn("No schema_patches directory found")
        return

    patch_files = {f.stem for f in patches_dir.glob("*.py") if f.stem != "__init__"}

    main_text = MAIN_FILE.read_text()

    issues = 0
    for patch in sorted(patch_files):
        if patch not in main_text:
            err(f"Schema patch '{patch}.py' exists but NOT called in main.py")
            issues += 1

    if issues == 0:
        ok(f"All {len(patch_files)} schema patches registered in main.py")


# ── 9. Missing env vars / config references ───────────────────────────
def audit_config():
    header("9. Environment config: referenced vs defined")

    config_file = API_DIR / "config.py"
    if not config_file.exists():
        warn("config.py not found")
        return

    config_text = config_file.read_text()

    # Find all Settings class attributes
    config_vars = set()
    for m in re.finditer(r"(\w+):\s*(?:str|int|bool|float|Optional)", config_text):
        config_vars.add(m.group(1))

    # Find os.getenv() calls across the project
    env_refs = set()
    for py_file in API_DIR.rglob("*.py"):
        text = py_file.read_text()
        for m in re.finditer(r'os\.(?:getenv|environ(?:\.get)?)\(\s*["\'](\w+)["\']', text):
            env_refs.add(m.group(1))

    # Also check business/ directory
    business_dir = ROOT / "business"
    if business_dir.exists():
        for py_file in business_dir.rglob("*.py"):
            text = py_file.read_text()
            for m in re.finditer(r'os\.(?:getenv|environ(?:\.get)?)\(\s*["\'](\w+)["\']', text):
                env_refs.add(m.group(1))

    # Common env vars that don't need to be in Settings
    SYSTEM_VARS = {"PATH", "HOME", "USER", "LANG", "TZ", "PORT", "HOST"}

    issues = 0
    for var in sorted(env_refs - SYSTEM_VARS):
        if var.upper() not in {v.upper() for v in config_vars}:
            # Not critical, but worth noting
            dim(f"os.getenv('{var}') used but not in Settings class")
            issues += 1

    if issues == 0:
        ok("All env vars used are defined in Settings")


# ── MAIN ──────────────────────────────────────────────────────────────
def main():
    print(f"\n{BOLD}🔍 Moonjar PMS — Architecture Audit{RESET}")
    print(f"{DIM}Root: {ROOT}{RESET}")

    if not ROUTERS_DIR.exists():
        print(f"{RED}ERROR: routers directory not found at {ROUTERS_DIR}{RESET}")
        sys.exit(1)

    total_issues = 0

    # Run all audits
    prefix_map = audit_routers()
    route_paths, route_components = audit_frontend_routes()
    audit_sidebar(route_paths)
    audit_models_vs_api(prefix_map)
    audit_api_clients()
    audit_page_accessibility()
    audit_endpoint_methods()
    audit_schema_patches()
    audit_config()

    print(f"\n{BOLD}{'═' * 60}{RESET}")
    print(f"{BOLD}  Audit complete. Review warnings above.{RESET}")
    print(f"{BOLD}{'═' * 60}{RESET}\n")


if __name__ == "__main__":
    main()
