#!/usr/bin/env python3
"""
Moonjar PMS — Backend ↔ Frontend Reconciliation Tool
Автоматически сравнивает API-эндпоинты бэкенда с вызовами фронтенда.
"""

import os
import re
from pathlib import Path
from collections import defaultdict

# === Paths ===
BASE = Path(__file__).resolve().parent.parent
BACKEND_ROUTERS = BASE / "api" / "routers"
FRONTEND_API = BASE / "presentation" / "dashboard" / "src" / "api"
FRONTEND_HOOKS = BASE / "presentation" / "dashboard" / "src" / "hooks"
FRONTEND_PAGES = BASE / "presentation" / "dashboard" / "src" / "pages"
FRONTEND_COMPONENTS = BASE / "presentation" / "dashboard" / "src" / "components"
MAIN_PY = BASE / "api" / "main.py"
APP_TSX = BASE / "presentation" / "dashboard" / "src" / "App.tsx"


def parse_backend_routes():
    """Parse all backend router files and extract endpoints."""
    # First, parse main.py to get prefix mappings
    prefixes = {}
    main_content = MAIN_PY.read_text()
    # Match: app.include_router(module.router, prefix="/api/xxx", ...)
    for match in re.finditer(
        r'app\.include_router\(\s*(\w+)\.router\s*,\s*prefix="([^"]+)"', main_content
    ):
        module_name = match.group(1)
        prefix = match.group(2)
        prefixes[module_name] = prefix

    endpoints = []
    stubs = []

    for py_file in sorted(BACKEND_ROUTERS.glob("*.py")):
        if py_file.name == "__init__.py":
            continue

        module_name = py_file.stem
        content = py_file.read_text()
        prefix = prefixes.get(module_name, f"/api/{module_name}")

        # Find all route decorators
        for match in re.finditer(
            r'@router\.(get|post|put|patch|delete|websocket)\("([^"]*)"(?:,\s*[^)]*)?(?:\))',
            content,
        ):
            method = match.group(1).upper()
            path = match.group(2)
            full_path = prefix + path

            # Check if it's a stub (501 or NotImplementedError nearby)
            line_start = match.start()
            # Get next 500 chars after decorator to check function body
            body_snippet = content[line_start : line_start + 800]
            is_stub = bool(
                re.search(r'status_code=501|NotImplementedError|"Not implemented"', body_snippet)
            )

            # Get function name
            func_match = re.search(r'(?:async\s+)?def\s+(\w+)', body_snippet)
            func_name = func_match.group(1) if func_match else "unknown"

            entry = {
                "module": module_name,
                "method": method,
                "path": full_path,
                "function": func_name,
                "is_stub": is_stub,
                "file": py_file.name,
            }
            endpoints.append(entry)
            if is_stub:
                stubs.append(entry)

    return endpoints, stubs


def parse_frontend_api_calls():
    """Parse all frontend API client files and extract API calls."""
    calls = []

    for ts_file in sorted(FRONTEND_API.glob("*.ts")):
        if ts_file.name == "client.ts":
            continue

        content = ts_file.read_text()
        module_name = ts_file.stem

        # Match: apiClient.get('/path', ...) or apiClient.post('/path', ...)
        for match in re.finditer(
            r"apiClient\.(get|post|put|patch|delete)\(\s*[`']([^`']+)[`']", content
        ):
            method = match.group(1).upper()
            path_template = match.group(2)
            # Normalize template literals: ${id} → {id}
            path_template = re.sub(r"\$\{[^}]+\}", "{id}", path_template)
            full_path = "/api" + path_template

            calls.append(
                {
                    "module": module_name,
                    "method": method,
                    "path": full_path,
                    "file": ts_file.name,
                }
            )

    return calls


def parse_frontend_hooks():
    """Parse all frontend hooks and list them."""
    hooks = []
    for ts_file in sorted(FRONTEND_HOOKS.glob("*.ts")):
        content = ts_file.read_text()
        # Find exported hook functions
        for match in re.finditer(r"export\s+(?:function|const)\s+(use\w+)", content):
            hook_name = match.group(1)

            # Check what API it calls
            api_calls = re.findall(r"(\w+Api)\.\w+", content)
            unique_apis = list(set(api_calls))

            hooks.append(
                {
                    "file": ts_file.name,
                    "hook": hook_name,
                    "apis": unique_apis,
                }
            )
    return hooks


def parse_frontend_pages():
    """Parse all frontend pages and their dependencies."""
    pages = []
    for tsx_file in sorted(FRONTEND_PAGES.glob("*.tsx")):
        content = tsx_file.read_text()

        # Find hooks used
        hooks_used = re.findall(r"(use\w+)\s*\(", content)
        hooks_used = list(set(hooks_used))

        # Find API imports
        api_imports = re.findall(r"from\s+['\"]@/api/(\w+)['\"]", content)
        hook_imports = re.findall(r"from\s+['\"]@/hooks/(\w+)['\"]", content)

        # Check for isError handling
        has_error_handling = bool(re.search(r"isError|error\s*&&|\.error|catch\(", content))
        has_loading = bool(re.search(r"isLoading|isPending", content))

        # Check for empty state messages
        empty_messages = re.findall(r'"No\s+\w+[^"]*"', content)

        pages.append(
            {
                "file": tsx_file.name,
                "hooks_used": sorted(hooks_used),
                "api_imports": api_imports,
                "hook_imports": hook_imports,
                "has_error_handling": has_error_handling,
                "has_loading": has_loading,
                "empty_state_messages": empty_messages,
            }
        )
    return pages


def parse_routes():
    """Parse App.tsx routes."""
    content = APP_TSX.read_text()
    routes = []
    for match in re.finditer(r'<Route\s+path="([^"]+)"\s+element=\{<(\w+)', content):
        routes.append({"path": match.group(1), "component": match.group(2)})
    return routes


def normalize_path(path):
    """Normalize API path for comparison: replace {id}/{item_id}/etc with {id}."""
    return re.sub(r"\{[^}]+\}", "{id}", path)


def reconcile():
    """Main reconciliation logic."""
    backend_endpoints, stubs = parse_backend_routes()
    frontend_calls = parse_frontend_api_calls()
    frontend_hooks = parse_frontend_hooks()
    frontend_pages = parse_frontend_pages()
    routes = parse_routes()

    # Normalize paths for comparison
    backend_set = {}
    for ep in backend_endpoints:
        key = (ep["method"], normalize_path(ep["path"]))
        backend_set[key] = ep

    frontend_set = {}
    for call in frontend_calls:
        key = (call["method"], normalize_path(call["path"]))
        frontend_set[key] = call

    # Find mismatches
    backend_only = []
    for key, ep in backend_set.items():
        if key not in frontend_set:
            backend_only.append(ep)

    frontend_only = []
    for key, call in frontend_set.items():
        if key not in backend_set:
            frontend_only.append(call)

    matched = []
    for key in backend_set:
        if key in frontend_set:
            matched.append((backend_set[key], frontend_set[key]))

    # === REPORT ===
    print("=" * 80)
    print("  MOONJAR PMS — BACKEND ↔ FRONTEND RECONCILIATION REPORT")
    print("=" * 80)

    # Summary
    print(f"\n📊 СВОДКА:")
    print(f"  Backend эндпоинтов:  {len(backend_endpoints)}")
    print(f"  Frontend API-вызовов: {len(frontend_calls)}")
    print(f"  Совпадений:          {len(matched)}")
    print(f"  Только в Backend:    {len(backend_only)}")
    print(f"  Только в Frontend:   {len(frontend_only)}")
    print(f"  Backend stubs (501): {len(stubs)}")

    # Stubs
    if stubs:
        print(f"\n{'='*80}")
        print("🚧 BACKEND STUBS (501 / NotImplementedError):")
        print(f"{'='*80}")
        for ep in stubs:
            print(f"  {ep['method']:7} {ep['path']:<55} [{ep['file']}]")

    # Backend only (no frontend caller)
    if backend_only:
        print(f"\n{'='*80}")
        print("⚠️  BACKEND-ONLY — Эндпоинты БЕЗ фронтенд-вызовов:")
        print(f"{'='*80}")
        by_module = defaultdict(list)
        for ep in backend_only:
            by_module[ep["module"]].append(ep)
        for module in sorted(by_module):
            print(f"\n  [{module}]")
            for ep in by_module[module]:
                stub_mark = " 🚧 STUB" if ep["is_stub"] else ""
                print(f"    {ep['method']:7} {ep['path']:<55}{stub_mark}")

    # Frontend only (calling non-existent backend)
    if frontend_only:
        print(f"\n{'='*80}")
        print("❌ FRONTEND-ONLY — Вызовы НЕСУЩЕСТВУЮЩИХ backend-эндпоинтов:")
        print(f"{'='*80}")
        for call in frontend_only:
            print(f"  {call['method']:7} {call['path']:<55} [{call['file']}]")

    # Routes
    print(f"\n{'='*80}")
    print("🗺️  FRONTEND ROUTES (App.tsx):")
    print(f"{'='*80}")
    for r in routes:
        print(f"  {r['path']:<40} → {r['component']}")

    # Pages without error handling
    print(f"\n{'='*80}")
    print("🔴 СТРАНИЦЫ БЕЗ ОБРАБОТКИ ОШИБОК (isError):")
    print(f"{'='*80}")
    pages_no_error = [p for p in frontend_pages if not p["has_error_handling"] and p["hook_imports"]]
    for p in pages_no_error:
        hooks = ", ".join(p["hook_imports"])
        print(f"  {p['file']:<45} hooks: [{hooks}]")

    if not pages_no_error:
        print("  ✅ Все страницы с хуками обрабатывают ошибки")

    # Pages with empty states
    print(f"\n{'='*80}")
    print("📋 СТРАНИЦЫ С ПУСТЫМИ СОСТОЯНИЯМИ:")
    print(f"{'='*80}")
    for p in frontend_pages:
        if p["empty_state_messages"]:
            msgs = "; ".join(p["empty_state_messages"][:3])
            print(f"  {p['file']:<45} {msgs}")

    # Frontend hooks summary
    print(f"\n{'='*80}")
    print("🪝 FRONTEND HOOKS:")
    print(f"{'='*80}")
    for h in frontend_hooks:
        apis = ", ".join(h["apis"]) if h["apis"] else "no API calls"
        print(f"  {h['hook']:<40} [{apis}]  ({h['file']})")

    # Missing frontend API files (backend modules without frontend client)
    backend_modules = set(ep["module"] for ep in backend_endpoints)
    frontend_modules = set(call["module"] for call in frontend_calls)
    # Map frontend file stems to rough backend modules
    missing_fe_files = []
    for bm in sorted(backend_modules):
        # Check if any frontend file roughly corresponds
        found = False
        for fm in frontend_modules:
            if bm.replace("_", "") in fm.replace("_", "").replace("-", "").lower():
                found = True
                break
        if not found:
            missing_fe_files.append(bm)

    if missing_fe_files:
        print(f"\n{'='*80}")
        print("📁 BACKEND-МОДУЛИ БЕЗ FRONTEND API-КЛИЕНТА:")
        print(f"{'='*80}")
        for m in missing_fe_files:
            prefix = ""
            for ep in backend_endpoints:
                if ep["module"] == m:
                    prefix = ep["path"].rsplit("/", 1)[0]
                    break
            print(f"  {m:<35} (prefix: {prefix})")

    print(f"\n{'='*80}")
    print("  КОНЕЦ ОТЧЁТА")
    print(f"{'='*80}")


if __name__ == "__main__":
    reconcile()
