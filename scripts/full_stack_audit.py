#!/usr/bin/env python3
"""
Moonjar PMS — Full-Stack Architecture Audit
============================================

Auto-discovers and cross-references ALL layers:
  1. Backend API endpoints (routers)
  2. Frontend API clients + hooks + pages
  3. ORM models
  4. Docs: API_CONTRACTS, API_ENDPOINTS_FULL, BUSINESS_LOGIC_FULL
  5. Role guides (docs/guides/)
  6. Business services

Outputs a Markdown report with:
  A. Backend endpoints WITHOUT frontend consumer
  B. Frontend API calls to NON-EXISTENT backend endpoints
  C. ORM models without any router/API exposure
  D. Documented endpoints (API_CONTRACTS) missing from code
  E. Code endpoints missing from API_CONTRACTS docs
  F. Business logic sections (§) referencing missing files/functions
  G. Guide references to features that don't exist
  H. Services without any doc coverage
  I. Summary stats

Usage:
    python scripts/full_stack_audit.py
    python scripts/full_stack_audit.py --json   # machine-readable output
"""

import os
import re
import sys
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# ── Paths ────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
API_ROUTERS = ROOT / "api" / "routers"
API_MODELS = ROOT / "api" / "models.py"
API_MAIN = ROOT / "api" / "main.py"
BIZ_SERVICES = ROOT / "business" / "services"
FRONTEND = ROOT / "presentation" / "dashboard" / "src"
FE_API = FRONTEND / "api"
FE_HOOKS = FRONTEND / "hooks"
FE_PAGES = FRONTEND / "pages"
FE_COMPONENTS = FRONTEND / "components"
DOCS = ROOT / "docs"
GUIDES = DOCS / "guides"
REPORT_PATH = DOCS / "FULL_STACK_AUDIT.md"

# ── Colors ───────────────────────────────────────────────────────
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

# ────────────────────────────────────────────────────────────────
# §1  Auto-discover backend endpoints
# ────────────────────────────────────────────────────────────────

def discover_router_prefixes() -> dict[str, str]:
    """Parse api/main.py for include_router calls → {module_name: prefix}."""
    prefixes = {}
    if not API_MAIN.exists():
        return prefixes
    text = API_MAIN.read_text()
    # Pattern: app.include_router(xxx.router, prefix="/api/yyy", ...)
    for m in re.finditer(
        r'include_router\(\s*(\w+)\.router\s*,\s*prefix\s*=\s*"([^"]+)"',
        text,
    ):
        module_name = m.group(1)
        prefix = m.group(2)
        prefixes[module_name] = prefix
    return prefixes


def discover_endpoints() -> list[dict]:
    """Scan all router files for @router.{method}("path") decorators."""
    endpoints = []
    prefixes = discover_router_prefixes()

    for py_file in sorted(API_ROUTERS.glob("*.py")):
        if py_file.name.startswith("__"):
            continue
        module_name = py_file.stem
        prefix = prefixes.get(module_name, f"/api/{module_name}")
        text = py_file.read_text()

        for m in re.finditer(
            r'@router\.(get|post|put|patch|delete)\(\s*"([^"]*)"',
            text,
        ):
            method = m.group(1).upper()
            path = m.group(2)
            full_path = prefix.rstrip("/") + "/" + path.lstrip("/") if path else prefix
            full_path = re.sub(r"//+", "/", full_path)  # normalize
            endpoints.append({
                "method": method,
                "path": full_path,
                "file": str(py_file.relative_to(ROOT)),
                "module": module_name,
                "prefix": prefix,
            })

    return endpoints


# ────────────────────────────────────────────────────────────────
# §2  Auto-discover frontend API calls
# ────────────────────────────────────────────────────────────────

def discover_frontend_api_calls() -> list[dict]:
    """Scan frontend api/ dir for apiClient.{method}('path') calls."""
    calls = []
    if not FE_API.exists():
        return calls

    for ts_file in sorted(FE_API.glob("*.ts")):
        if ts_file.name == "client.ts":
            continue
        text = ts_file.read_text()
        module = ts_file.stem

        # apiClient.get('/path') or apiClient.get<Type>('/path') or
        # apiClient.post(`/path/${id}`)
        for m in re.finditer(
            r"apiClient\.(get|post|put|patch|delete)\s*(?:<[^>]*>)?\s*\(\s*['\"`]([^'\"`]+)['\"`]",
            text,
        ):
            method = m.group(1).upper()
            path = m.group(2)
            # Normalize template literals: /orders/${id} → /orders/{id}
            path = re.sub(r"\$\{[^}]+\}", "{id}", path)
            calls.append({
                "method": method,
                "path": "/api" + path if not path.startswith("/api") else path,
                "file": str(ts_file.relative_to(ROOT)),
                "module": module,
            })

    return calls


def discover_frontend_pages() -> list[str]:
    """List all page component files."""
    if not FE_PAGES.exists():
        return []
    return sorted(
        str(f.relative_to(ROOT))
        for f in FE_PAGES.glob("*.tsx")
    )


def discover_frontend_hooks() -> list[str]:
    """List all hook files."""
    if not FE_HOOKS.exists():
        return []
    return sorted(
        str(f.relative_to(ROOT))
        for f in FE_HOOKS.glob("*.ts")
    )


# ────────────────────────────────────────────────────────────────
# §3  Auto-discover ORM models
# ────────────────────────────────────────────────────────────────

def discover_models() -> list[str]:
    """Extract class names that inherit from Base in api/models.py."""
    if not API_MODELS.exists():
        return []
    text = API_MODELS.read_text()
    models = []
    for m in re.finditer(r"^class\s+(\w+)\s*\(", text, re.MULTILINE):
        name = m.group(1)
        if name not in ("Base", "BaseModel"):
            models.append(name)
    return sorted(models)


def find_model_in_routers(model_name: str) -> list[str]:
    """Check which router files reference a model."""
    found = []
    for py_file in API_ROUTERS.glob("*.py"):
        if py_file.name.startswith("__"):
            continue
        text = py_file.read_text()
        if model_name in text:
            found.append(py_file.stem)
    return found


# ────────────────────────────────────────────────────────────────
# §4  Business services
# ────────────────────────────────────────────────────────────────

def discover_services() -> list[str]:
    """List all business service files."""
    if not BIZ_SERVICES.exists():
        return []
    return sorted(
        f.stem for f in BIZ_SERVICES.glob("*.py")
        if not f.name.startswith("__")
    )


# ────────────────────────────────────────────────────────────────
# §5  Docs parsing
# ────────────────────────────────────────────────────────────────

def _parse_api_doc_with_sections(filepath: Path) -> list[dict]:
    """Parse an API doc that uses section headers with prefixes and relative paths.

    Handles two formats:
      - API_CONTRACTS.md:  ## Orders (`/api/orders`)  + | GET | / | ...
      - API_ENDPOINTS_FULL.md:  ## 2. Orders (`/api/orders`)  + | GET | `/path` | ...

    Paths in table rows are RELATIVE to the section prefix.
    """
    if not filepath.exists():
        return []
    text = filepath.read_text()
    endpoints = []
    current_prefix = "/api"

    for line in text.splitlines():
        # Section header with prefix: ## Title (`/api/something`)
        sec_match = re.match(r"^#{2,4}\s+.+?\(\s*`?(/api[^)`]*)`?\s*\)", line)
        if sec_match:
            current_prefix = sec_match.group(1).rstrip("/")
            continue

        # Table row: | METHOD | path | ...
        row_match = re.match(
            r"\|\s*(GET|POST|PUT|PATCH|DELETE)\s*\|\s*`?([^|`]*)`?\s*\|",
            line,
            re.IGNORECASE,
        )
        if row_match:
            method = row_match.group(1).upper()
            rel_path = row_match.group(2).strip()
            # Build full path from section prefix + relative path
            if rel_path.startswith("/api"):
                full = rel_path  # already absolute
            elif rel_path in ("", "/"):
                full = current_prefix
            else:
                # Check if rel_path is already the suffix of current_prefix
                # e.g. prefix="/api/tps/kiln-shelves", rel="/kiln-shelves/{id}"
                # → should NOT produce /api/tps/kiln-shelves/kiln-shelves/{id}
                prefix_last = current_prefix.rstrip("/").rsplit("/", 1)[-1]
                rel_first = rel_path.lstrip("/").split("/", 1)[0]
                if prefix_last == rel_first:
                    # Strip the duplicate segment — use parent prefix
                    parent = current_prefix.rstrip("/").rsplit("/", 1)[0]
                    full = parent + "/" + rel_path.lstrip("/")
                else:
                    full = current_prefix + "/" + rel_path.lstrip("/")
            full = re.sub(r"//+", "/", full)
            endpoints.append({"method": method, "path": full})

    return endpoints


def parse_api_contracts() -> list[dict]:
    """Parse docs/API_CONTRACTS.md for documented endpoints."""
    return _parse_api_doc_with_sections(DOCS / "API_CONTRACTS.md")


def parse_api_endpoints_full() -> list[dict]:
    """Parse docs/API_ENDPOINTS_FULL.md for documented endpoints."""
    return _parse_api_doc_with_sections(DOCS / "API_ENDPOINTS_FULL.md")


def parse_business_logic_sections() -> list[dict]:
    """Parse BUSINESS_LOGIC_FULL.md for sections and file/function references."""
    path = DOCS / "BUSINESS_LOGIC_FULL.md"
    if not path.exists():
        return []
    text = path.read_text()
    sections = []
    current_section = None

    for line in text.splitlines():
        # Match both formats:
        #   ## §1 Title           (old §-style)
        #   ## 1. Title           (numbered list style)
        #   ### 1.2 Sub-section
        sec_match = re.match(
            r"^#{2,4}\s*(?:§)?(\d+(?:\.\d+)?)[.\s]+(.+)", line
        )
        if sec_match:
            current_section = {
                "number": sec_match.group(1),
                "title": sec_match.group(2).strip(),
                "files": [],
                "functions": [],
            }
            sections.append(current_section)
            continue

        if current_section:
            # File references: `business/services/xxx.py` or `api/routers/xxx.py`
            for fm in re.finditer(r"`((?:business|api)/[^`]+\.py)`", line):
                current_section["files"].append(fm.group(1))
            # Function references: `function_name()`
            for fm in re.finditer(r"`(\w+)\(\)`", line):
                current_section["functions"].append(fm.group(1))

    return sections


def parse_guides() -> list[dict]:
    """Parse guide files for endpoint/feature references."""
    if not GUIDES.exists():
        return []
    guides = []
    for gf in sorted(GUIDES.glob("*.md")):
        text = gf.read_text()
        api_refs = set()
        page_refs = set()

        # API endpoint references: /api/xxx or `GET /api/xxx`
        for m in re.finditer(r"(/api/[\w/\-{}]+)", text):
            api_refs.add(m.group(1))

        # Page/route references: /dashboard/xxx or /schedule or /orders
        for m in re.finditer(r"(?:route|page|navigate|url)[:\s]+[`\"']?(/[\w/\-]+)", text, re.IGNORECASE):
            page_refs.add(m.group(1))

        # Feature keywords: button/tab/section names
        feature_refs = set()
        for m in re.finditer(
            r'(?:click|tab|button|section|panel|card|modal|dialog)[:\s]+["\']([^"\']+)["\']',
            text,
            re.IGNORECASE,
        ):
            feature_refs.add(m.group(1))

        guides.append({
            "file": gf.name,
            "role": gf.stem.replace("GUIDE_", "").replace("_EN", "").replace("_ID", ""),
            "lang": "ID" if "_ID" in gf.stem else "EN",
            "api_refs": sorted(api_refs),
            "page_refs": sorted(page_refs),
            "feature_refs": sorted(feature_refs),
        })

    return guides


# ────────────────────────────────────────────────────────────────
# §6  Cross-reference analysis
# ────────────────────────────────────────────────────────────────

def normalize_path(path: str) -> str:
    """Normalize endpoint path for comparison."""
    # Strip query string (?foo=bar)
    p = p if "?" not in (p := path) else p.split("?")[0]
    p = p.rstrip("/")
    # Normalize {order_id} vs {id} vs {xxx_id} → {id}
    p = re.sub(r"\{[^}]+\}", "{id}", p)
    return p


def analyze_backend_without_frontend(
    backend_endpoints: list[dict],
    frontend_calls: list[dict],
) -> list[dict]:
    """Find backend endpoints that no frontend API client calls."""
    fe_paths = set()
    for c in frontend_calls:
        fe_paths.add(normalize_path(c["path"]))

    # Also scan all TS/TSX files for path fragments
    fe_text = ""
    for ext in ("*.ts", "*.tsx"):
        for f in FRONTEND.rglob(ext):
            try:
                fe_text += f.read_text()
            except Exception:
                pass

    orphans = []
    for ep in backend_endpoints:
        norm = normalize_path(ep["path"])
        # Skip health/docs/internal endpoints
        if any(x in norm for x in ("/health", "/openapi", "/docs", "/redoc", "/seed")):
            continue
        if norm in fe_paths:
            continue
        # Fuzzy: check if the path fragment appears anywhere in frontend
        path_fragment = norm.split("/api/")[-1].split("/")[0] if "/api/" in norm else ""
        if path_fragment and path_fragment in fe_text:
            continue
        orphans.append(ep)

    return orphans


def analyze_frontend_without_backend(
    backend_endpoints: list[dict],
    frontend_calls: list[dict],
) -> list[dict]:
    """Find frontend API calls to paths that don't exist in backend."""
    be_paths = set()
    for ep in backend_endpoints:
        be_paths.add(normalize_path(ep["path"]))

    # Also build prefix set for fuzzy matching
    be_prefixes = set()
    for ep in backend_endpoints:
        parts = normalize_path(ep["path"]).split("/")
        for i in range(2, len(parts)):
            be_prefixes.add("/".join(parts[:i]))

    phantoms = []
    for call in frontend_calls:
        norm = normalize_path(call["path"])
        if norm in be_paths:
            continue
        # Check if any backend path starts with this prefix
        # (handles /orders/{id}/positions where we have /orders/{id})
        prefix = "/".join(norm.split("/")[:4])
        if prefix in be_prefixes:
            continue
        # Check path without trailing {id} — maybe the list endpoint matches
        without_id = re.sub(r"/\{id\}$", "", norm)
        if without_id != norm and without_id in be_paths:
            continue
        phantoms.append(call)

    return phantoms


def analyze_models_without_api(
    models: list[str],
    backend_endpoints: list[dict],
) -> list[dict]:
    """Find ORM models not referenced in any router."""
    # Internal/support models that don't need API exposure
    INTERNAL = {
        "Base", "AuditLog", "AuditLogEntry", "SessionLocal",
        "TaskCommentLink", "UserFactory", "CeleryTaskMeta",
    }
    orphans = []
    for model in models:
        if model in INTERNAL:
            continue
        routers = find_model_in_routers(model)
        if not routers:
            orphans.append({"model": model, "routers": []})

    return orphans


def analyze_docs_vs_code(
    documented: list[dict],
    actual: list[dict],
    doc_name: str,
) -> tuple[list[dict], list[dict]]:
    """Compare documented endpoints vs actual code endpoints.

    Returns (in_docs_not_code, in_code_not_docs).
    """
    doc_set = {(d["method"], normalize_path(d["path"])) for d in documented}
    code_set = {(e["method"], normalize_path(e["path"])) for e in actual}

    in_docs_not_code = [
        {"method": m, "path": p, "source": doc_name}
        for m, p in sorted(doc_set - code_set)
    ]
    in_code_not_docs = [
        {"method": m, "path": p, "source": doc_name}
        for m, p in sorted(code_set - doc_set)
        if not any(x in p for x in ("/health", "/openapi", "/docs"))
    ]

    return in_docs_not_code, in_code_not_docs


def analyze_business_logic_refs(sections: list[dict]) -> list[dict]:
    """Check if files/functions referenced in BUSINESS_LOGIC_FULL.md exist."""
    issues = []
    for sec in sections:
        for f in sec["files"]:
            full_path = ROOT / f
            if not full_path.exists():
                issues.append({
                    "section": f"§{sec['number']} {sec['title']}",
                    "type": "missing_file",
                    "ref": f,
                })
        for func in sec["functions"]:
            # Search in services and routers
            found = False
            for d in (BIZ_SERVICES, API_ROUTERS):
                if not d.exists():
                    continue
                for py in d.glob("*.py"):
                    try:
                        if re.search(rf"def {func}\s*\(", py.read_text()):
                            found = True
                            break
                    except Exception:
                        pass
                if found:
                    break
            if not found:
                issues.append({
                    "section": f"§{sec['number']} {sec['title']}",
                    "type": "missing_function",
                    "ref": f"{func}()",
                })

    return issues


def analyze_services_without_docs(
    services: list[str],
    bl_sections: list[dict],
) -> list[str]:
    """Find services not mentioned in BUSINESS_LOGIC_FULL.md."""
    # Flatten all file references
    documented_files = set()
    bl_text = ""
    bl_path = DOCS / "BUSINESS_LOGIC_FULL.md"
    if bl_path.exists():
        bl_text = bl_path.read_text()
    for sec in bl_sections:
        for f in sec["files"]:
            documented_files.add(Path(f).stem)

    undocumented = []
    SKIP = {"__init__", "__pycache__"}
    for svc in services:
        if svc in SKIP:
            continue
        if svc in documented_files:
            continue
        # Also check if service name appears anywhere in the doc
        if svc in bl_text or svc.replace("_", " ") in bl_text:
            continue
        undocumented.append(svc)

    return undocumented


# ────────────────────────────────────────────────────────────────
# §7  Report generation
# ────────────────────────────────────────────────────────────────

def print_section(title: str, items: list, color: str = YELLOW):
    """Print a colored section header with count."""
    count = len(items) if isinstance(items, list) else items
    status = f"{GREEN}OK{RESET}" if count == 0 else f"{color}{count} issues{RESET}"
    print(f"\n{BOLD}{title}{RESET}  [{status}]")


def generate_markdown_report(results: dict) -> str:
    """Generate the full Markdown audit report."""
    lines = [
        f"# Full-Stack Architecture Audit",
        f"",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"",
        f"## Summary",
        f"",
        f"| Layer | Count |",
        f"|-------|-------|",
        f"| Backend endpoints | {results['stats']['backend_endpoints']} |",
        f"| Frontend API calls | {results['stats']['frontend_api_calls']} |",
        f"| Frontend pages | {results['stats']['frontend_pages']} |",
        f"| Frontend hooks | {results['stats']['frontend_hooks']} |",
        f"| ORM models | {results['stats']['orm_models']} |",
        f"| Business services | {results['stats']['business_services']} |",
        f"| Role guides | {results['stats']['guides']} |",
        f"",
        f"## Issues Found",
        f"",
    ]

    # A. Backend without frontend
    items = results["backend_no_frontend"]
    lines.append(f"### A. Backend endpoints without frontend consumer ({len(items)})")
    lines.append("")
    if items:
        lines.append("| Method | Path | Router |")
        lines.append("|--------|------|--------|")
        for ep in items[:50]:  # cap at 50
            lines.append(f"| {ep['method']} | `{ep['path']}` | {ep['module']} |")
        if len(items) > 50:
            lines.append(f"| ... | *{len(items) - 50} more* | |")
    else:
        lines.append("*None — all backend endpoints have frontend consumers.*")
    lines.append("")

    # B. Frontend calling non-existent backend
    items = results["frontend_no_backend"]
    lines.append(f"### B. Frontend API calls to non-existent backend ({len(items)})")
    lines.append("")
    if items:
        lines.append("| Method | Path | Frontend module |")
        lines.append("|--------|------|----------------|")
        for c in items:
            lines.append(f"| {c['method']} | `{c['path']}` | {c['module']} |")
    else:
        lines.append("*None — all frontend calls resolve to existing endpoints.*")
    lines.append("")

    # C. Models without API
    items = results["models_no_api"]
    lines.append(f"### C. ORM models without API exposure ({len(items)})")
    lines.append("")
    if items:
        lines.append("| Model | Notes |")
        lines.append("|-------|-------|")
        for m in items:
            lines.append(f"| `{m['model']}` | Not referenced in any router |")
    else:
        lines.append("*None — all models have router references.*")
    lines.append("")

    # D. Documented but missing from code
    items = results["docs_not_in_code"]
    lines.append(f"### D. Documented endpoints missing from code ({len(items)})")
    lines.append("")
    if items:
        lines.append("| Method | Path | Doc source |")
        lines.append("|--------|------|-----------|")
        for d in items[:50]:
            lines.append(f"| {d['method']} | `{d['path']}` | {d['source']} |")
    else:
        lines.append("*None — all documented endpoints exist in code.*")
    lines.append("")

    # E. Code endpoints missing from docs
    items = results["code_not_in_docs"]
    lines.append(f"### E. Code endpoints missing from API docs ({len(items)})")
    lines.append("")
    if items:
        lines.append("| Method | Path | Doc source |")
        lines.append("|--------|------|-----------|")
        for d in items[:80]:
            lines.append(f"| {d['method']} | `{d['path']}` | {d['source']} |")
        if len(items) > 80:
            lines.append(f"| ... | *{len(items) - 80} more* | |")
    else:
        lines.append("*None — all code endpoints are documented.*")
    lines.append("")

    # F. Business logic referencing missing files/functions
    items = results["bl_broken_refs"]
    lines.append(f"### F. Business logic docs referencing missing code ({len(items)})")
    lines.append("")
    if items:
        lines.append("| Section | Type | Reference |")
        lines.append("|---------|------|-----------|")
        for i in items:
            lines.append(f"| {i['section']} | {i['type']} | `{i['ref']}` |")
    else:
        lines.append("*None — all doc references resolve to existing code.*")
    lines.append("")

    # G. Services without doc coverage
    items = results["services_no_docs"]
    lines.append(f"### G. Business services without doc coverage ({len(items)})")
    lines.append("")
    if items:
        for s in items:
            lines.append(f"- `business/services/{s}.py`")
    else:
        lines.append("*None — all services are documented.*")
    lines.append("")

    # H. Guide analysis
    guides = results.get("guides_analysis", [])
    lines.append(f"### H. Guide coverage ({len(guides)} guides)")
    lines.append("")
    if guides:
        lines.append("| Guide | Role | Lang | API refs | Page refs |")
        lines.append("|-------|------|------|----------|-----------|")
        for g in guides:
            lines.append(
                f"| {g['file']} | {g['role']} | {g['lang']} | "
                f"{len(g['api_refs'])} | {len(g['page_refs'])} |"
            )
    lines.append("")

    # Totals
    total_issues = (
        len(results["backend_no_frontend"])
        + len(results["frontend_no_backend"])
        + len(results["models_no_api"])
        + len(results["docs_not_in_code"])
        + len(results["code_not_in_docs"])
        + len(results["bl_broken_refs"])
        + len(results["services_no_docs"])
    )
    lines.append("---")
    lines.append(f"**Total issues: {total_issues}**")
    lines.append("")

    return "\n".join(lines)


# ────────────────────────────────────────────────────────────────
# §8  Main
# ────────────────────────────────────────────────────────────────

def main():
    json_mode = "--json" in sys.argv

    print(f"{BOLD}{CYAN}Moonjar PMS — Full-Stack Architecture Audit{RESET}")
    print(f"{'=' * 50}")

    # ── Discover ──
    print(f"\n{CYAN}Discovering...{RESET}")

    backend_endpoints = discover_endpoints()
    print(f"  Backend endpoints: {len(backend_endpoints)}")

    frontend_calls = discover_frontend_api_calls()
    print(f"  Frontend API calls: {len(frontend_calls)}")

    frontend_pages = discover_frontend_pages()
    print(f"  Frontend pages: {len(frontend_pages)}")

    frontend_hooks = discover_frontend_hooks()
    print(f"  Frontend hooks: {len(frontend_hooks)}")

    models = discover_models()
    print(f"  ORM models: {len(models)}")

    services = discover_services()
    print(f"  Business services: {len(services)}")

    api_contracts = parse_api_contracts()
    print(f"  API_CONTRACTS entries: {len(api_contracts)}")

    api_full = parse_api_endpoints_full()
    print(f"  API_ENDPOINTS_FULL entries: {len(api_full)}")

    bl_sections = parse_business_logic_sections()
    print(f"  BUSINESS_LOGIC sections: {len(bl_sections)}")

    guides = parse_guides()
    print(f"  Role guides: {len(guides)}")

    # ── Analyze ──
    print(f"\n{CYAN}Cross-referencing...{RESET}")

    backend_no_frontend = analyze_backend_without_frontend(backend_endpoints, frontend_calls)
    print_section("A. Backend without frontend", backend_no_frontend, RED)
    for ep in backend_no_frontend[:10]:
        print(f"     {ep['method']:6s} {ep['path']}  ({ep['module']})")
    if len(backend_no_frontend) > 10:
        print(f"     ... +{len(backend_no_frontend) - 10} more")

    frontend_no_backend = analyze_frontend_without_backend(backend_endpoints, frontend_calls)
    print_section("B. Frontend → missing backend", frontend_no_backend, RED)
    for c in frontend_no_backend[:10]:
        print(f"     {c['method']:6s} {c['path']}  ({c['module']})")

    models_no_api = analyze_models_without_api(models, backend_endpoints)
    print_section("C. Models without API", models_no_api)
    for m in models_no_api[:10]:
        print(f"     {m['model']}")
    if len(models_no_api) > 10:
        print(f"     ... +{len(models_no_api) - 10} more")

    docs_not_in_code_contracts, code_not_in_docs_contracts = analyze_docs_vs_code(
        api_contracts, backend_endpoints, "API_CONTRACTS.md",
    )
    docs_not_in_code_full, code_not_in_docs_full = analyze_docs_vs_code(
        api_full, backend_endpoints, "API_ENDPOINTS_FULL.md",
    )
    docs_not_in_code = docs_not_in_code_contracts + docs_not_in_code_full
    code_not_in_docs = code_not_in_docs_contracts + code_not_in_docs_full
    # Deduplicate
    seen = set()
    deduped = []
    for d in code_not_in_docs:
        key = (d["method"], d["path"])
        if key not in seen:
            seen.add(key)
            deduped.append(d)
    code_not_in_docs = deduped

    print_section("D. Documented but missing from code", docs_not_in_code)
    for d in docs_not_in_code[:10]:
        print(f"     {d['method']:6s} {d['path']}  ({d['source']})")

    print_section("E. Code but missing from docs", code_not_in_docs)
    for d in code_not_in_docs[:10]:
        print(f"     {d['method']:6s} {d['path']}")
    if len(code_not_in_docs) > 10:
        print(f"     ... +{len(code_not_in_docs) - 10} more")

    bl_broken_refs = analyze_business_logic_refs(bl_sections)
    print_section("F. Business logic broken refs", bl_broken_refs)
    for i in bl_broken_refs[:10]:
        print(f"     {i['section']}: {i['type']} → {i['ref']}")

    services_no_docs = analyze_services_without_docs(services, bl_sections)
    print_section("G. Services without docs", services_no_docs)
    for s in services_no_docs[:10]:
        print(f"     {s}.py")
    if len(services_no_docs) > 10:
        print(f"     ... +{len(services_no_docs) - 10} more")

    # ── Build results ──
    results = {
        "stats": {
            "backend_endpoints": len(backend_endpoints),
            "frontend_api_calls": len(frontend_calls),
            "frontend_pages": len(frontend_pages),
            "frontend_hooks": len(frontend_hooks),
            "orm_models": len(models),
            "business_services": len(services),
            "guides": len(guides),
        },
        "backend_no_frontend": backend_no_frontend,
        "frontend_no_backend": frontend_no_backend,
        "models_no_api": models_no_api,
        "docs_not_in_code": docs_not_in_code,
        "code_not_in_docs": code_not_in_docs,
        "bl_broken_refs": bl_broken_refs,
        "services_no_docs": services_no_docs,
        "guides_analysis": guides,
    }

    total_issues = (
        len(backend_no_frontend)
        + len(frontend_no_backend)
        + len(models_no_api)
        + len(docs_not_in_code)
        + len(code_not_in_docs)
        + len(bl_broken_refs)
        + len(services_no_docs)
    )

    # ── Output ──
    print(f"\n{'=' * 50}")
    print(f"{BOLD}TOTAL: {total_issues} issues found{RESET}")

    if json_mode:
        print(json.dumps(results, indent=2, default=str))
    else:
        report = generate_markdown_report(results)
        REPORT_PATH.write_text(report)
        print(f"\nReport saved to: {REPORT_PATH.relative_to(ROOT)}")

    return total_issues


if __name__ == "__main__":
    main()
