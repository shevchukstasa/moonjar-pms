#!/usr/bin/env python3
"""
Generate docs/API_CONTRACTS.md from actual FastAPI router files.

Reuses endpoint discovery logic from generate_api_docs.py, adds:
  - Frontend column: checks if endpoint path appears in frontend .ts/.tsx files
  - Preserves detailed endpoint specs (#### sections) from existing file
  - Groups endpoints by router/tag with proper section headers

Usage:
    python3 scripts/generate_api_contracts.py
    python3 scripts/generate_api_contracts.py --dry-run   # print to stdout
"""

import ast
import os
import re
import sys
from datetime import date
from pathlib import Path
from typing import NamedTuple

# ── Project paths ──────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
API_DIR = PROJECT_ROOT / "api"
ROUTERS_DIR = API_DIR / "routers"
MAIN_PY = API_DIR / "main.py"
FRONTEND_SRC = PROJECT_ROOT / "presentation" / "dashboard" / "src"
OUTPUT = PROJECT_ROOT / "docs" / "API_CONTRACTS.md"

# ── Auth labels ────────────────────────────────────────────────────
AUTH_LABELS = {
    "require_owner": "owner",
    "require_admin": "admin",
    "require_admin_or_pm": "admin_or_pm",
    "require_management": "management",
    "require_finance": "finance",
    "require_quality": "qm_or_admin",
    "require_warehouse": "warehouse",
    "require_sorting": "sorting+",
    "require_purchaser": "purchaser",
    "require_any": "any_auth",
    "get_current_user": "any_auth",
}


class Endpoint(NamedTuple):
    method: str
    path: str          # path within router (e.g. "/{id}")
    auth: str
    description: str
    func_name: str


class RouterInfo(NamedTuple):
    module_name: str
    prefix: str
    tag: str
    file_path: Path


# ══════════════════════════════════════════════════════════════════════
# 1) Router & endpoint discovery (mirrors generate_api_docs.py)
# ══════════════════════════════════════════════════════════════════════

def parse_include_routers() -> list[RouterInfo]:
    source = MAIN_PY.read_text()
    results = []
    pattern = re.compile(r'app\.include_router\s*\((.*?)\)', re.DOTALL)

    for m in pattern.finditer(source):
        body = re.sub(r'\s+', ' ', m.group(1).strip())
        router_match = re.match(r'(\w+)\.router', body)
        if not router_match:
            continue
        module_name = router_match.group(1)
        prefix_match = re.search(r'prefix\s*=\s*"([^"]+)"', body)
        prefix = prefix_match.group(1) if prefix_match else ""
        tag_match = re.search(r'tags\s*=\s*\["([^"]+)"', body)
        tag = tag_match.group(1) if tag_match else module_name

        file_module = module_name
        if module_name == "settings_router":
            file_module = "settings"
        file_path = ROUTERS_DIR / f"{file_module}.py"
        if not file_path.exists():
            print(f"  WARNING: {file_path} not found for '{module_name}'", file=sys.stderr)
            continue

        results.append(RouterInfo(module_name=module_name, prefix=prefix, tag=tag, file_path=file_path))
    return results


def _resolve_auth_from_depends(call_node: ast.Call) -> str | None:
    if not call_node.args:
        return None
    arg = call_node.args[0]
    if isinstance(arg, ast.Name):
        return AUTH_LABELS.get(arg.id)
    if isinstance(arg, ast.Attribute):
        return AUTH_LABELS.get(arg.attr)
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
        if func_name and func_name in AUTH_LABELS:
            return AUTH_LABELS[func_name]
    return None


def _get_auth_from_function(func_node, local_aliases: dict[str, str]) -> str:
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
        if not default.args:
            continue
        dep_arg = default.args[0]
        if isinstance(dep_arg, ast.Name):
            name = dep_arg.id
            if name in local_aliases:
                return local_aliases[name]
            if name in AUTH_LABELS:
                return AUTH_LABELS[name]
        if isinstance(dep_arg, ast.Attribute):
            if dep_arg.attr in AUTH_LABELS:
                return AUTH_LABELS[dep_arg.attr]
        if isinstance(dep_arg, ast.Call):
            fn = None
            if isinstance(dep_arg.func, ast.Name):
                fn = dep_arg.func.id
            elif isinstance(dep_arg.func, ast.Attribute):
                fn = dep_arg.func.attr
            if fn == "require_role":
                roles = [a.value for a in dep_arg.args if isinstance(a, ast.Constant) and isinstance(a.value, str)]
                return "role(" + ",".join(roles) + ")" if roles else "role(...)"
            if fn and fn in AUTH_LABELS:
                return AUTH_LABELS[fn]
    return "public"


def _docstring_first_line(func_node) -> str:
    ds = ast.get_docstring(func_node)
    if ds:
        for line in ds.strip().splitlines():
            line = line.strip()
            if line:
                return line[:120] if len(line) <= 120 else line[:117] + "..."
    return ""


def _clean_func_name(name: str) -> str:
    return name.replace("_", " ").strip().capitalize()


def parse_router_file(file_path: Path) -> list[Endpoint]:
    source = file_path.read_text()
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        print(f"  WARNING: Syntax error in {file_path}: {e}", file=sys.stderr)
        return []

    # Collect local auth aliases
    local_auth_aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and isinstance(node.value, ast.Call):
                call = node.value
                fn = None
                if isinstance(call.func, ast.Name):
                    fn = call.func.id
                elif isinstance(call.func, ast.Attribute):
                    fn = call.func.attr
                if fn == "require_role":
                    roles = [a.value for a in call.args if isinstance(a, ast.Constant) and isinstance(a.value, str)]
                    if roles:
                        local_auth_aliases[target.id] = "role(" + ",".join(roles) + ")"
                elif fn and fn in AUTH_LABELS:
                    local_auth_aliases[target.id] = AUTH_LABELS[fn]

    endpoints = []
    HTTP_METHODS = {"get", "post", "put", "patch", "delete", "websocket"}

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
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
                        if dec.args and isinstance(dec.args[0], ast.Constant):
                            path = dec.args[0].value
                        else:
                            for kw in dec.keywords:
                                if kw.arg == "path" and isinstance(kw.value, ast.Constant):
                                    path = kw.value.value
                            if path is None:
                                path = ""
            if method is None:
                continue
            auth = _get_auth_from_function(node, local_auth_aliases)
            desc = _docstring_first_line(node)
            if not desc:
                desc = _clean_func_name(node.name)
            endpoints.append(Endpoint(method=method, path=path, auth=auth, description=desc, func_name=node.name))
    return endpoints


# ══════════════════════════════════════════════════════════════════════
# 2) Frontend usage detection
# ══════════════════════════════════════════════════════════════════════

def build_frontend_index() -> str:
    """Read all .ts/.tsx files from frontend src into one big string for searching."""
    if not FRONTEND_SRC.exists():
        print("  WARNING: Frontend src not found, all endpoints marked [API-only]", file=sys.stderr)
        return ""
    parts = []
    for ext in ("*.ts", "*.tsx"):
        for f in FRONTEND_SRC.rglob(ext):
            try:
                parts.append(f.read_text(errors="ignore"))
            except Exception:
                pass
    return "\n".join(parts)


def _normalize_path_for_search(full_path: str) -> list[str]:
    """Generate search patterns for a full API path.

    Returns multiple patterns to check:
    - The full path with params replaced by patterns
    - Path segments that would appear in axios/fetch calls
    """
    patterns = []

    # Remove /api prefix for frontend (they use baseURL)
    no_api = full_path
    if no_api.startswith("/api"):
        no_api = no_api[4:]

    # Pattern 1: exact path (minus /api)
    patterns.append(no_api)

    # Pattern 2: path with params replaced by ${...} template literals
    # e.g. /orders/{order_id}/ship -> /orders/${...}/ship
    param_replaced = re.sub(r'\{[^}]+\}', '${', no_api)
    if param_replaced != no_api:
        # Just check the static parts around params
        static_parts = re.split(r'\{[^}]+\}', no_api)
        for part in static_parts:
            if part and len(part) > 3:
                patterns.append(part.rstrip("/"))

    # Pattern 3: the last meaningful segment
    # e.g. /orders/upload-pdf -> "upload-pdf"
    segments = [s for s in no_api.split("/") if s and not s.startswith("{")]
    if segments:
        last = segments[-1]
        if len(last) > 3 and last not in ("all", "stats", "list"):
            patterns.append(last)

    return patterns


def check_frontend_usage(full_path: str, frontend_text: str, tag: str) -> str:
    """Determine frontend status for an endpoint."""
    if not frontend_text:
        return "`[API-only]`"

    # Known API-only / telegram-only patterns
    if "/webhook" in full_path and "telegram" in full_path.lower():
        return "`[Telegram-only]`"
    if "/webhook/sales-order" in full_path:
        return "`[API-only]`"
    if full_path.endswith("/production-status") and "/integration/" in full_path:
        return "`[API-only]`"
    if full_path.endswith("/status-updates") and "/integration/" in full_path:
        return "`[API-only]`"
    if "/request-cancellation" in full_path and "/integration/" in full_path:
        return "`[API-only]`"

    patterns = _normalize_path_for_search(full_path)

    for pattern in patterns:
        if pattern in frontend_text:
            return "✓"

    # Check with quotes (API path strings in code)
    no_api = full_path[4:] if full_path.startswith("/api") else full_path
    # Check for the path in backtick template literals, quoted strings
    # Convert {param} to regex-like patterns
    search_path = re.sub(r'\{[^}]+\}', r'\\$\\{', no_api)
    if re.search(re.escape(no_api.split("{")[0].rstrip("/")), frontend_text):
        return "✓"

    return "`[API-only]`"


# ══════════════════════════════════════════════════════════════════════
# 3) Preserve existing detailed specs from API_CONTRACTS.md
# ══════════════════════════════════════════════════════════════════════

def extract_detailed_specs(existing_content: str) -> dict[str, str]:
    """Extract #### sections (detailed endpoint specs) keyed by section header prefix.

    Returns dict mapping section_prefix (e.g. "/api/tps") to the detail text block.
    """
    lines = existing_content.split("\n")
    detail_blocks: dict[str, list[str]] = {}

    # Track which ## / ### section we're inside
    section_prefix = ""
    i = 0
    while i < len(lines):
        line = lines[i]

        # Track current section header
        sec_match = re.match(r'^##\s+.*?\(\`(/api[^`]*)\`\)', line)
        subsec_match = re.match(r'^###\s+.*?\(\`(/api[^`]*)\`\)', line)
        if sec_match:
            section_prefix = sec_match.group(1)
            i += 1
            continue
        elif subsec_match:
            section_prefix = subsec_match.group(1)
            i += 1
            continue

        # Detect #### detail block start
        if line.startswith("#### "):
            if section_prefix not in detail_blocks:
                detail_blocks[section_prefix] = []
            # Collect this #### block and everything until next ##/### or section-ending ---
            detail_blocks[section_prefix].append(line)
            i += 1
            while i < len(lines):
                l = lines[i]
                # Stop at next major section header
                if re.match(r'^##\s+.*?\(\`/api', l) or re.match(r'^###\s+.*?\(\`/api', l):
                    break
                # Stop at --- that separates sections (followed by ## or end)
                if l.strip() == "---":
                    # Peek ahead: if next non-empty line is ## or end, this is a separator
                    j = i + 1
                    while j < len(lines) and lines[j].strip() == "":
                        j += 1
                    if j >= len(lines) or lines[j].startswith("## "):
                        break
                # Another #### is fine — keep collecting
                detail_blocks[section_prefix].append(l)
                i += 1
            continue
        i += 1

    specs: dict[str, str] = {}
    for prefix, block_lines in detail_blocks.items():
        # Strip trailing empty lines
        while block_lines and block_lines[-1].strip() == "":
            block_lines.pop()
        if block_lines:
            specs[prefix] = "\n".join(block_lines)

    return specs


# ══════════════════════════════════════════════════════════════════════
# 4) Section naming and ordering
# ══════════════════════════════════════════════════════════════════════

# Manual section title overrides for nicer display
SECTION_TITLES = {
    "auth": "Auth",
    "orders": "Orders",
    "positions": "Positions",
    "schedule": "Schedule",
    "materials": "Materials",
    "recipes": "Recipes",
    "quality": "Quality",
    "defects": "Defects",
    "tasks": "Tasks",
    "suppliers": "Suppliers",
    "integration": "Integration",
    "users": "Users",
    "factories": "Factories",
    "kilns": "Kilns",
    "kiln-equipment": "Kiln Equipment",
    "recipe-kiln-capability": "Recipe-Kiln Capability",
    "kiln-maintenance": "Kiln Maintenance",
    "kiln-inspections": "Kiln Inspections",
    "kiln-constants": "Kiln Constants",
    "kiln-loading-rules": "Kiln Loading Rules",
    "kiln-firing-schedules": "Kiln Firing Schedules",
    "reference": "Reference Data",
    "toc": "TOC (Theory of Constraints)",
    "tps": "TPS (Toyota Production System)",
    "notifications": "Notifications",
    "analytics": "Analytics",
    "ai-chat": "AI Chat",
    "export": "Export",
    "reports": "Reports",
    "stages": "Stages",
    "transcription": "Transcription",
    "telegram": "Telegram",
    "health": "Health",
    "purchaser": "Purchaser",
    "dashboard-access": "Dashboard Access",
    "notification-preferences": "Notification Preferences",
    "financials": "Financials",
    "warehouse-sections": "Warehouse Sections",
    "reconciliations": "Reconciliations",
    "qm-blocks": "QM Blocks",
    "problem-cards": "Problem Cards",
    "security": "Security",
    "websocket": "WebSocket",
    "packing-photos": "Packing Photos",
    "finished-goods": "Finished Goods",
    "firing-profiles": "Firing Profiles",
    "batches": "Batches",
    "firing-logs": "Firing Logs",
    "cleanup": "Cleanup",
    "material-groups": "Material Groups",
    "packaging": "Packaging",
    "sizes": "Sizes",
    "consumption-rules": "Consumption Rules",
    "grinding-stock": "Grinding Stock",
    "factory-calendar": "Factory Calendar",
    "stone-reservations": "Stone Reservations",
    "settings": "Settings",
    "admin-settings": "Admin Settings",
    "guides": "Guides",
    "delivery": "Delivery",
    "employees": "Employees",
    "mana-shipments": "Mana Shipments",
    "gamification": "Gamification",
    "workforce": "Workforce",
    "onboarding": "Onboarding",
    "shipments": "Shipments",
    "pdf-templates": "PDF Templates",
}


def section_title(tag: str) -> str:
    return SECTION_TITLES.get(tag, tag.replace("-", " ").title())


# Routers that share a prefix with another router need subsection treatment
# e.g. firing_logs shares /api/batches prefix with batches
SUBSECTION_TAGS = {"firing-logs"}  # rendered as ### under Batches


# ══════════════════════════════════════════════════════════════════════
# 5) Build the document
# ══════════════════════════════════════════════════════════════════════

def build_full_path(prefix: str, ep_path: str) -> str:
    if ep_path:
        full = prefix.rstrip("/") + "/" + ep_path.lstrip("/")
    else:
        full = prefix
    return full.replace("//", "/")


def build_relative_path(prefix: str, ep_path: str) -> str:
    """Path relative to the section prefix, for display in table."""
    full = build_full_path(prefix, ep_path)
    # Remove the section prefix to get relative path
    if full.startswith(prefix):
        rel = full[len(prefix):]
        if not rel:
            rel = "/"
        elif not rel.startswith("/"):
            rel = "/" + rel
        return rel
    return full


def generate_contracts_md(router_infos: list[RouterInfo], frontend_text: str, existing_specs: dict[str, str]) -> str:
    lines = []

    # Header
    lines.append("# Moonjar PMS — API Contracts")
    lines.append("")
    lines.append("> Complete endpoint reference. Base path: `/api`")
    lines.append(">")
    lines.append("> **Auth levels:** `public` = no auth, `any_auth` = any JWT user, `management` = PM/Admin/Owner,")
    lines.append("> `admin` = Admin/Owner, `owner` = Owner only, `owner/ceo` = Owner or CEO.")
    lines.append(">")
    lines.append("> **Frontend column:** ✓ = wired to frontend, `[API-only]` = backend only,")
    lines.append("> `[Telegram-only]` = used by Telegram bot, `[Frontend planned]` = not yet wired,")
    lines.append("> `[Admin-only]` = admin panel / CLI.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Group routers by their effective display section
    # Firing logs shares prefix /api/batches with batches — handle as subsection
    sections = []
    total_count = 0

    for info in router_infos:
        endpoints = parse_router_file(info.file_path)
        if not endpoints:
            continue
        total_count += len(endpoints)
        sections.append((info, endpoints))

    # Build output
    for info, endpoints in sections:
        title = section_title(info.tag)
        is_subsection = info.tag in SUBSECTION_TAGS
        header_prefix = "###" if is_subsection else "##"

        lines.append(f"{header_prefix} {title} (`{info.prefix}`)")
        lines.append("")
        lines.append("| Method | Path | Auth | Frontend | Description |")
        lines.append("|--------|------|------|----------|-------------|")

        for ep in endpoints:
            rel_path = build_relative_path(info.prefix, ep.path)
            full_path = build_full_path(info.prefix, ep.path)
            frontend_status = check_frontend_usage(full_path, frontend_text, info.tag)
            desc = ep.description.replace("|", "\\|")
            lines.append(f"| {ep.method} | {rel_path} | {ep.auth} | {frontend_status} | {desc} |")

        lines.append("")

        # Append detailed specs: match sub-prefixes of this router's actual endpoints
        # Build set of all full paths for this router to find matching specs
        all_full_paths = set()
        for ep in endpoints:
            fp = build_full_path(info.prefix, ep.path)
            all_full_paths.add(fp)
            # Also add path prefixes for sub-resources
            parts = fp.split("/")
            for k in range(3, len(parts) + 1):
                all_full_paths.add("/".join(parts[:k]))

        matched_specs = []
        for spec_key, spec_text in existing_specs.items():
            # Match if spec_key exactly equals a path or is a prefix of an endpoint path
            if spec_key in all_full_paths:
                matched_specs.append((spec_key, spec_text))

        if matched_specs:
            matched_specs.sort(key=lambda x: x[0])
            for spec_key, spec_text in matched_specs:
                lines.append(spec_text)
                lines.append("")

        lines.append("---")
        lines.append("")

    # Telegram Bot Commands section (static)
    lines.append("## Telegram Bot Commands")
    lines.append("")
    lines.append("| Command | Description |")
    lines.append("|---------|-------------|")
    lines.append("| `/mystats` | Personal points breakdown and statistics |")
    lines.append("| `/leaderboard` | Top performers ranking |")
    lines.append("| `/stock` | Low stock materials summary |")
    lines.append("| `/challenge` | Current daily challenge details |")
    lines.append("| `/achievements` | Earned badges and milestones |")
    lines.append("| `/points` | Current points balance |")
    lines.append("| `/cancel_verify` | Cancel an in-progress recipe verification |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"*Generated {date.today().isoformat()} by `scripts/generate_api_contracts.py`. Total: ~{len(sections)} routers, ~{total_count} endpoints.*")
    lines.append("")

    return "\n".join(lines)


def main():
    dry_run = "--dry-run" in sys.argv

    print(f"Parsing {MAIN_PY} for router registrations...", file=sys.stderr)
    router_infos = parse_include_routers()
    print(f"Found {len(router_infos)} routers.", file=sys.stderr)

    print("Building frontend usage index...", file=sys.stderr)
    frontend_text = build_frontend_index()
    frontend_size = len(frontend_text)
    print(f"Frontend index: {frontend_size:,} chars from {FRONTEND_SRC}", file=sys.stderr)

    # Load existing specs — prefer git HEAD version to avoid reading our own output
    existing_specs: dict[str, str] = {}
    old_content = ""
    import subprocess
    try:
        result = subprocess.run(
            ["git", "show", "HEAD:docs/API_CONTRACTS.md"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        if result.returncode == 0:
            old_content = result.stdout
            print("Loading detailed specs from git HEAD...", file=sys.stderr)
    except Exception:
        pass
    if not old_content and OUTPUT.exists():
        old_content = OUTPUT.read_text()
        print("Loading detailed specs from current file...", file=sys.stderr)
    if old_content:
        existing_specs = extract_detailed_specs(old_content)
        print(f"Found {len(existing_specs)} sections with detailed specs: {list(existing_specs.keys())}", file=sys.stderr)

    print("Generating markdown...", file=sys.stderr)
    md = generate_contracts_md(router_infos, frontend_text, existing_specs)

    ep_count = sum(1 for line in md.split("\n") if re.match(r'\| (GET|POST|PUT|PATCH|DELETE|WS) \|', line))

    if dry_run:
        print(md)
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(md)
        print(f"Written {OUTPUT} with {ep_count} endpoints.", file=sys.stderr)


if __name__ == "__main__":
    main()
