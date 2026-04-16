#!/usr/bin/env python3
"""
Generate docs/API_ENDPOINTS_FULL.md from actual FastAPI router files.

Usage:
    python3 scripts/generate_api_docs.py

Parses api/main.py for include_router() calls, then reads each router
file to extract @router.{method}("path") endpoints with auth levels
and docstrings.
"""

import ast
import os
import re
import sys
from datetime import date
from pathlib import Path
from typing import NamedTuple

# Resolve project root (one level up from scripts/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
API_DIR = PROJECT_ROOT / "api"
ROUTERS_DIR = API_DIR / "routers"
MAIN_PY = API_DIR / "main.py"
OUTPUT = PROJECT_ROOT / "docs" / "API_ENDPOINTS_FULL.md"

# ── Known auth dependency → label mapping ──────────────────────
# Order matters: more specific first
AUTH_LABELS = {
    "require_owner": "owner",
    "require_admin": "admin",
    "require_admin_or_pm": "admin_or_pm",
    "require_management": "management",
    "require_finance": "finance",
    "require_quality": "qm_or_admin",
    "require_warehouse": "warehouse",
    "require_sorting": "sorting",
    "require_purchaser": "purchaser",
    "require_any": "any_auth",
    "get_current_user": "any_auth",
}


class Endpoint(NamedTuple):
    method: str
    path: str
    auth: str
    description: str
    func_name: str


class RouterInfo(NamedTuple):
    module_name: str      # e.g. "auth"
    prefix: str           # e.g. "/api/auth"
    tag: str              # e.g. "auth"
    file_path: Path


def parse_include_routers() -> list[RouterInfo]:
    """Parse api/main.py to find all include_router() calls and their prefixes."""
    source = MAIN_PY.read_text()

    # We need to handle both single-line and multi-line include_router calls.
    # Strategy: use regex to find all include_router blocks.
    results = []

    # Match patterns like:
    #   app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
    #   app.include_router(\n    recipe_kiln_capability.router,\n    prefix="/api",\n    tags=[...]\n)
    # Collapse the source to make multi-line calls single-line for easier parsing
    # Find all include_router blocks by matching balanced parens
    pattern = re.compile(
        r'app\.include_router\s*\((.*?)\)',
        re.DOTALL
    )

    for m in pattern.finditer(source):
        body = m.group(1).strip()
        # Remove newlines and extra spaces
        body = re.sub(r'\s+', ' ', body)

        # Extract module.router
        router_match = re.match(r'(\w+)\.router', body)
        if not router_match:
            continue
        module_name = router_match.group(1)

        # Extract prefix
        prefix_match = re.search(r'prefix\s*=\s*"([^"]+)"', body)
        prefix = prefix_match.group(1) if prefix_match else ""

        # Extract first tag
        tag_match = re.search(r'tags\s*=\s*\["([^"]+)"', body)
        tag = tag_match.group(1) if tag_match else module_name

        # Handle aliased imports (settings_router → settings)
        file_module = module_name
        if module_name == "settings_router":
            file_module = "settings"

        file_path = ROUTERS_DIR / f"{file_module}.py"
        if not file_path.exists():
            print(f"  WARNING: {file_path} not found for module '{module_name}'", file=sys.stderr)
            continue

        results.append(RouterInfo(
            module_name=module_name,
            prefix=prefix,
            tag=tag,
            file_path=file_path,
        ))

    return results


def _resolve_auth_from_depends(call_node: ast.Call) -> str | None:
    """Given a Depends(...) call AST node, resolve the auth label."""
    if not call_node.args:
        return None
    arg = call_node.args[0]

    # Direct name: Depends(get_current_user) or Depends(require_admin)
    if isinstance(arg, ast.Name):
        return AUTH_LABELS.get(arg.id)

    # Attribute: Depends(roles.require_admin) — rare but possible
    if isinstance(arg, ast.Attribute):
        return AUTH_LABELS.get(arg.attr)

    # Call: Depends(require_role("owner", "ceo"))
    if isinstance(arg, ast.Call):
        func_name = None
        if isinstance(arg.func, ast.Name):
            func_name = arg.func.id
        elif isinstance(arg.func, ast.Attribute):
            func_name = arg.func.attr

        if func_name == "require_role":
            roles = []
            for a in arg.args:
                if isinstance(a, ast.Constant) and isinstance(a.value, str):
                    roles.append(a.value)
            if roles:
                return "role(" + ",".join(roles) + ")"
            return "role(...)"

        # Other callable in AUTH_LABELS
        if func_name and func_name in AUTH_LABELS:
            return AUTH_LABELS[func_name]

    return None


def _get_auth_from_function(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Determine auth level from function parameters' Depends() calls."""
    for arg in func_node.args.args:
        # Check default values
        pass
    # Merge args + defaults
    # In FastAPI, Depends are typically in keyword defaults or positional defaults
    all_defaults = []

    # Positional defaults: last N args have defaults
    n_defaults = len(func_node.args.defaults)
    n_args = len(func_node.args.args)
    for i, default in enumerate(func_node.args.defaults):
        arg_index = n_args - n_defaults + i
        arg_name = func_node.args.args[arg_index].arg if arg_index < n_args else None
        all_defaults.append((arg_name, default))

    # Keyword-only args with defaults
    for kw_arg, kw_default in zip(func_node.args.kwonlyargs, func_node.args.kw_defaults):
        if kw_default is not None:
            all_defaults.append((kw_arg.arg, kw_default))

    for arg_name, default in all_defaults:
        if not isinstance(default, ast.Call):
            continue
        # Check if it's Depends(...)
        func = default.func
        is_depends = False
        if isinstance(func, ast.Name) and func.id == "Depends":
            is_depends = True
        elif isinstance(func, ast.Attribute) and func.attr == "Depends":
            is_depends = True

        if is_depends:
            label = _resolve_auth_from_depends(default)
            if label:
                return label

    return "public"


def _get_docstring_first_line(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Extract first meaningful line of a function's docstring."""
    ds = ast.get_docstring(func_node)
    if ds:
        # Take first non-empty line
        for line in ds.strip().splitlines():
            line = line.strip()
            if line:
                # Truncate if too long
                if len(line) > 120:
                    line = line[:117] + "..."
                return line
    return ""


def _clean_func_name(name: str) -> str:
    """Convert function name to human-readable description."""
    # Remove common prefixes
    for prefix in ("get_", "create_", "update_", "delete_", "list_", "do_"):
        if name.startswith(prefix):
            break
    # Replace underscores with spaces, capitalize
    return name.replace("_", " ").strip().capitalize()


def parse_router_file(file_path: Path) -> list[Endpoint]:
    """Parse a router .py file and extract all endpoint definitions."""
    source = file_path.read_text()
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        print(f"  WARNING: Syntax error in {file_path}: {e}", file=sys.stderr)
        return []

    # First pass: collect module-level variable assignments that are
    # require_role(...) calls. E.g.:
    #   require_qm_or_admin = require_role("owner", "administrator", "quality_manager")
    #   _require_read = require_role("owner", "ceo")
    local_auth_aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and isinstance(node.value, ast.Call):
                call = node.value
                func_name = None
                if isinstance(call.func, ast.Name):
                    func_name = call.func.id
                elif isinstance(call.func, ast.Attribute):
                    func_name = call.func.attr
                if func_name == "require_role":
                    roles = []
                    for a in call.args:
                        if isinstance(a, ast.Constant) and isinstance(a.value, str):
                            roles.append(a.value)
                    if roles:
                        label = "role(" + ",".join(roles) + ")"
                        local_auth_aliases[target.id] = label
                elif func_name and func_name in AUTH_LABELS:
                    local_auth_aliases[target.id] = AUTH_LABELS[func_name]

    endpoints = []
    HTTP_METHODS = {"get", "post", "put", "patch", "delete", "websocket"}

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        # Check decorators for @router.{method}("path")
        for dec in node.decorator_list:
            method = None
            path = None

            if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                attr = dec.func
                if isinstance(attr.value, ast.Name) and attr.value.id == "router":
                    if attr.attr in HTTP_METHODS:
                        method = attr.attr.upper()
                        if method == "WEBSOCKET":
                            method = "WS"
                        # First positional arg is path
                        if dec.args and isinstance(dec.args[0], ast.Constant):
                            path = dec.args[0].value
                        else:
                            # Check path keyword
                            for kw in dec.keywords:
                                if kw.arg == "path" and isinstance(kw.value, ast.Constant):
                                    path = kw.value.value
                            if path is None:
                                path = ""

            if method is None:
                continue

            # Determine auth
            auth = _get_auth_from_function_with_aliases(node, local_auth_aliases)

            # Description
            desc = _get_docstring_first_line(node)
            if not desc:
                desc = _clean_func_name(node.name)

            endpoints.append(Endpoint(
                method=method,
                path=path,
                auth=auth,
                description=desc,
                func_name=node.name,
            ))

    return endpoints


def _get_auth_from_function_with_aliases(
    func_node: ast.FunctionDef | ast.AsyncFunctionDef,
    local_aliases: dict[str, str],
) -> str:
    """Like _get_auth_from_function but also checks local aliases."""
    all_defaults = []

    n_defaults = len(func_node.args.defaults)
    n_args = len(func_node.args.args)
    for i, default in enumerate(func_node.args.defaults):
        arg_index = n_args - n_defaults + i
        arg_name = func_node.args.args[arg_index].arg if arg_index < n_args else None
        all_defaults.append((arg_name, default))

    for kw_arg, kw_default in zip(func_node.args.kwonlyargs, func_node.args.kw_defaults):
        if kw_default is not None:
            all_defaults.append((kw_arg.arg, kw_default))

    for arg_name, default in all_defaults:
        if not isinstance(default, ast.Call):
            continue
        func = default.func
        is_depends = False
        if isinstance(func, ast.Name) and func.id == "Depends":
            is_depends = True
        elif isinstance(func, ast.Attribute) and func.attr == "Depends":
            is_depends = True

        if not is_depends:
            continue

        # Check what's inside Depends()
        if not default.args:
            continue
        dep_arg = default.args[0]

        # Direct name reference
        if isinstance(dep_arg, ast.Name):
            name = dep_arg.id
            # Check local aliases first
            if name in local_aliases:
                return local_aliases[name]
            if name in AUTH_LABELS:
                return AUTH_LABELS[name]

        # Attribute access
        if isinstance(dep_arg, ast.Attribute):
            if dep_arg.attr in AUTH_LABELS:
                return AUTH_LABELS[dep_arg.attr]

        # Inline call: Depends(require_role("owner", "ceo"))
        if isinstance(dep_arg, ast.Call):
            func_name = None
            if isinstance(dep_arg.func, ast.Name):
                func_name = dep_arg.func.id
            elif isinstance(dep_arg.func, ast.Attribute):
                func_name = dep_arg.func.attr

            if func_name == "require_role":
                roles = []
                for a in dep_arg.args:
                    if isinstance(a, ast.Constant) and isinstance(a.value, str):
                        roles.append(a.value)
                if roles:
                    return "role(" + ",".join(roles) + ")"
                return "role(...)"

            if func_name and func_name in AUTH_LABELS:
                return AUTH_LABELS[func_name]

    return "public"


def _section_title(tag: str) -> str:
    """Convert tag like 'kiln-maintenance' to 'Kiln Maintenance'."""
    return tag.replace("-", " ").title()


def generate_markdown(router_infos: list[RouterInfo]) -> str:
    """Generate the full markdown document."""
    sections = []
    total_count = 0

    for info in router_infos:
        endpoints = parse_router_file(info.file_path)
        if not endpoints:
            continue

        total_count += len(endpoints)
        sections.append((info, endpoints))

    # ── Build document ──
    lines = []

    # Header
    lines.append("# Moonjar PMS -- Complete API Endpoints")
    lines.append("")
    lines.append(f"> Auto-extracted from {len(sections)} router files in `api/routers/`")
    lines.append(f"> Total: **{total_count}** endpoints across {len(sections)} router files")
    lines.append(f"> Generated: {date.today().isoformat()}")
    lines.append(f"> Script: `scripts/generate_api_docs.py`")
    lines.append("")

    # Auth levels reference
    lines.append("## Authentication Levels")
    lines.append("")
    lines.append("| Level | Dependency | Who |")
    lines.append("|-------|-----------|-----|")
    lines.append("| **public** | None | No auth required |")
    lines.append("| **any_auth** | `get_current_user` | Any authenticated user |")
    lines.append("| **management** | `require_management` | owner, administrator, ceo, production_manager |")
    lines.append("| **admin** | `require_admin` | owner, administrator |")
    lines.append("| **admin_or_pm** | `require_admin_or_pm` | owner, administrator, production_manager |")
    lines.append("| **owner** | `require_owner` | owner only |")
    lines.append("| **finance** | `require_finance` | owner, administrator, ceo |")
    lines.append("| **qm_or_admin** | `require_quality` | owner, administrator, quality_manager |")
    lines.append("| **warehouse** | `require_warehouse` | owner, administrator, warehouse |")
    lines.append("| **sorting** | `require_sorting` | sorter_packer + management roles |")
    lines.append("| **purchaser** | `require_purchaser` | owner, administrator, purchaser |")
    lines.append("| **role(...)** | `require_role(...)` | Custom role combination |")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Table of contents
    lines.append("## Table of Contents")
    lines.append("")
    for i, (info, endpoints) in enumerate(sections, 1):
        title = _section_title(info.tag)
        anchor = f"{i}-{info.tag.replace(' ', '-').lower()}-{info.prefix.replace('/', '').replace('-', '-')}"
        lines.append(f"{i}. [{title}](#{anchor}) ({len(endpoints)} endpoints)")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Sections
    for i, (info, endpoints) in enumerate(sections, 1):
        title = _section_title(info.tag)
        lines.append(f"## {i}. {title} (`{info.prefix}`)")
        lines.append("")
        lines.append("| Method | Path | Auth | Description |")
        lines.append("|--------|------|------|-------------|")

        for ep in endpoints:
            full_path = info.prefix.rstrip("/") + "/" + ep.path.lstrip("/") if ep.path else info.prefix
            # Normalize double slashes
            full_path = full_path.replace("//", "/")
            # Escape pipe characters in description
            desc = ep.description.replace("|", "\\|")
            lines.append(f"| {ep.method} | `{full_path}` | {ep.auth} | {desc} |")

        lines.append("")

    return "\n".join(lines)


def main():
    print(f"Parsing {MAIN_PY} for router registrations...")
    router_infos = parse_include_routers()
    print(f"Found {len(router_infos)} routers.")

    print("Extracting endpoints from router files...")
    md = generate_markdown(router_infos)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(md)

    # Count endpoints in output
    endpoint_count = md.count("| GET ") + md.count("| POST ") + md.count("| PUT ") + md.count("| PATCH ") + md.count("| DELETE ") + md.count("| WS ")
    print(f"Written {OUTPUT} with {endpoint_count} endpoints.")


if __name__ == "__main__":
    main()
