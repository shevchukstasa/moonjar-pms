#!/usr/bin/env python3
"""
Moonjar PMS — Dead Code Scanner
================================
Сканирует весь кодовой базы и находит мёртвый код:
  1. Неиспользуемые Python-импорты
  2. Неиспользуемые Python-функции/методы
  3. Неиспользуемые Python-классы
  4. Неиспользуемые SQLAlchemy-модели
  5. Неиспользуемые API-эндпоинты (роутеры без фронтенд-вызовов)
  6. Неиспользуемые фронтенд-компоненты (.tsx)
  7. Неиспользуемые фронтенд-страницы (нет роута в App.tsx)
  8. Неиспользуемые TypeScript/JS-экспорты
  9. Мёртвая бизнес-логика (файлы business/)
 10. Осиротевшие Pydantic-схемы
 11. Неиспользуемые переменные окружения (config)
 12. Неиспользуемые CSS-классы (custom CSS)

Запуск: python3 scripts/dead_code_scanner.py
"""

import ast
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Optional

# ─── Цвета терминала ───
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

# ─── Пути ───
PROJECT_ROOT = Path(__file__).resolve().parent.parent
API_DIR = PROJECT_ROOT / "api"
BUSINESS_DIR = PROJECT_ROOT / "business"
FRONTEND_DIR = PROJECT_ROOT / "presentation" / "dashboard" / "src"
DOCS_DIR = PROJECT_ROOT / "docs"

SKIP_DIRS = {"__pycache__", "node_modules", ".git", "dist", "build", ".venv", "venv", "env", ".mypy_cache", ".pytest_cache", "Icon"}


# ─── Утилиты ───

def should_skip(path: Path) -> bool:
    parts = path.parts
    return any(p in SKIP_DIRS for p in parts)


def collect_files(root: Path, extensions: tuple) -> list[Path]:
    results = []
    if not root.exists():
        return results
    for p in root.rglob("*"):
        if p.is_file() and p.suffix in extensions and not should_skip(p):
            results.append(p)
    return results


def read_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


class Finding:
    """Одна находка мёртвого кода."""
    def __init__(self, category: str, level: str, path: str, line: int, name: str, detail: str = ""):
        self.category = category
        self.level = level       # "red", "yellow", "green"
        self.path = path
        self.line = line
        self.name = name
        self.detail = detail

    def color(self) -> str:
        return {"red": RED, "yellow": YELLOW, "green": GREEN}.get(self.level, "")

    def level_ru(self) -> str:
        return {"red": "МЁРТВЫЙ", "yellow": "ВОЗМОЖНО", "green": "ЖИВОЙ"}.get(self.level, "?")


findings: list[Finding] = []


# ════════════════════════════════════════════
# 1. Неиспользуемые Python-импорты (AST)
# ════════════════════════════════════════════

def scan_unused_imports():
    py_files = collect_files(API_DIR, (".py",)) + collect_files(BUSINESS_DIR, (".py",))
    # Also scripts and root-level .py
    py_files += collect_files(PROJECT_ROOT / "scripts", (".py",))
    py_files += [f for f in PROJECT_ROOT.glob("*.py") if not should_skip(f)]

    for fpath in py_files:
        source = read_file(fpath)
        if not source.strip():
            continue
        try:
            tree = ast.parse(source, filename=str(fpath))
        except SyntaxError:
            continue

        # Collect all imported names
        imported_names: list[tuple[str, int]] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name.split(".")[0]
                    imported_names.append((name, node.lineno))
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    name = alias.asname or alias.name
                    imported_names.append((name, node.lineno))

        # Collect all used names (excluding import statements themselves)
        used_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            if isinstance(node, ast.Name):
                used_names.add(node.id)
            elif isinstance(node, ast.Attribute):
                # Walk to the root Name
                n = node
                while isinstance(n, ast.Attribute):
                    n = n.value
                if isinstance(n, ast.Name):
                    used_names.add(n.id)
            # Decorators, annotations as strings
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                for d in node.decorator_list:
                    if isinstance(d, ast.Name):
                        used_names.add(d.id)
            if isinstance(node, ast.ClassDef):
                for b in node.bases:
                    if isinstance(b, ast.Name):
                        used_names.add(b.id)
                for d in node.decorator_list:
                    if isinstance(d, ast.Name):
                        used_names.add(d.id)

        # Also check for string references (type annotations as strings, __all__, etc.)
        for name_str, _ in imported_names:
            if name_str in source.replace(f"import {name_str}", "").replace(f"from ", ""):
                # crude double check — if name appears as a substring beyond imports
                pass

        for name, lineno in imported_names:
            # Skip _ imports (convention for side effects)
            if name == "_" or name.startswith("__"):
                continue
            if name not in used_names:
                # Double check: maybe used in string annotations or comments
                # Count occurrences in source (excluding import lines)
                lines = source.split("\n")
                count = 0
                for i, line in enumerate(lines):
                    if i + 1 == lineno:
                        continue
                    if name in line:
                        count += 1
                if count == 0:
                    findings.append(Finding(
                        "Неиспользуемые импорты",
                        "red",
                        rel(fpath), lineno, name,
                        f"Импортирован, но не используется в файле"
                    ))


# ════════════════════════════════════════════
# 2. Неиспользуемые Python-функции/методы
# ════════════════════════════════════════════

def scan_unused_functions():
    py_files = collect_files(API_DIR, (".py",)) + collect_files(BUSINESS_DIR, (".py",))
    py_files += collect_files(PROJECT_ROOT / "scripts", (".py",))

    # Phase 1: collect all defined functions
    all_funcs: list[tuple[str, str, int, bool]] = []  # (name, file, line, is_method)
    for fpath in py_files:
        source = read_file(fpath)
        if not source.strip():
            continue
        try:
            tree = ast.parse(source, filename=str(fpath))
        except SyntaxError:
            continue

        # Build a set of class-level function nodes for is_method detection
        class_body_nodes: set[int] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    class_body_nodes.add(id(item))

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("__") and node.name.endswith("__"):
                    continue
                is_method = id(node) in class_body_nodes

                # Skip decorated functions (likely endpoints or event handlers)
                has_route_decorator = False
                for d in node.decorator_list:
                    if isinstance(d, ast.Attribute):
                        if d.attr in ("get", "post", "put", "patch", "delete", "websocket", "on_event"):
                            has_route_decorator = True
                    elif isinstance(d, ast.Name):
                        if d.id in ("property", "staticmethod", "classmethod", "abstractmethod", "validator", "field_validator", "model_validator"):
                            has_route_decorator = True
                    elif isinstance(d, ast.Call):
                        if isinstance(d.func, ast.Attribute):
                            if d.func.attr in ("get", "post", "put", "patch", "delete", "websocket"):
                                has_route_decorator = True

                if has_route_decorator:
                    continue

                all_funcs.append((node.name, rel(fpath), node.lineno, is_method))

    # Phase 2: build a word-frequency index from all .py files (fast)
    _WORD_RE = re.compile(r'\b\w+\b')
    global_word_counts: dict[str, int] = defaultdict(int)
    file_word_counts: dict[str, dict[str, int]] = {}
    for fpath in py_files:
        text = read_file(fpath)
        local: dict[str, int] = defaultdict(int)
        for w in _WORD_RE.findall(text):
            global_word_counts[w] += 1
            local[w] += 1
        file_word_counts[rel(fpath)] = local

    # Phase 3: check usage via word counts (O(1) per function)
    for name, filepath, lineno, is_method in all_funcs:
        if name.startswith("_") and not name.startswith("__"):
            local = file_word_counts.get(filepath, {})
            if local.get(name, 0) <= 1:
                findings.append(Finding(
                    "Неиспользуемые функции",
                    "yellow",
                    filepath, lineno, name,
                    "Приватная функция — найдено <=1 упоминание в файле"
                ))
            continue

        if global_word_counts.get(name, 0) <= 1:
            findings.append(Finding(
                "Неиспользуемые функции",
                "red" if not is_method else "yellow",
                filepath, lineno, name,
                "Определена, но нигде не вызывается" if not is_method else "Метод определён, но возможно не вызывается"
            ))


# ════════════════════════════════════════════
# 3. Неиспользуемые Python-классы
# ════════════════════════════════════════════

def scan_unused_classes():
    py_files = collect_files(API_DIR, (".py",)) + collect_files(BUSINESS_DIR, (".py",))
    py_files += collect_files(PROJECT_ROOT / "scripts", (".py",))
    alembic_files = collect_files(PROJECT_ROOT / "alembic", (".py",))

    all_classes: list[tuple[str, str, int]] = []
    for fpath in py_files:
        source = read_file(fpath)
        if not source.strip():
            continue
        try:
            tree = ast.parse(source, filename=str(fpath))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if node.name in ("Base", "Config", "Settings"):
                    continue
                all_classes.append((node.name, rel(fpath), node.lineno))

    # Build word-frequency index (fast)
    _WORD_RE = re.compile(r'\b\w+\b')
    word_counts: dict[str, int] = defaultdict(int)
    for fpath in py_files + alembic_files:
        for w in _WORD_RE.findall(read_file(fpath)):
            word_counts[w] += 1

    for name, filepath, lineno in all_classes:
        if word_counts.get(name, 0) <= 1:
            if filepath == rel(API_DIR / "models.py"):
                continue
            if filepath == rel(API_DIR / "schemas.py"):
                continue
            findings.append(Finding(
                "Неиспользуемые классы",
                "red",
                filepath, lineno, name,
                "Определён, но нигде не используется"
            ))


# ════════════════════════════════════════════
# 4. Неиспользуемые SQLAlchemy-модели
# ════════════════════════════════════════════

def scan_unused_models():
    models_file = API_DIR / "models.py"
    if not models_file.exists():
        return

    source = read_file(models_file)
    try:
        tree = ast.parse(source, filename=str(models_file))
    except SyntaxError:
        return

    model_names: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            # Check if it inherits from Base
            for base in node.bases:
                if isinstance(base, ast.Name) and base.id == "Base":
                    model_names.append((node.name, node.lineno))

    # Build text index of all files EXCEPT models.py itself
    py_files = collect_files(API_DIR, (".py",)) + collect_files(BUSINESS_DIR, (".py",))
    py_files += collect_files(PROJECT_ROOT / "alembic", (".py",))
    full_text = ""
    for fpath in py_files:
        if fpath.name == "models.py" and fpath.parent == API_DIR:
            continue
        full_text += read_file(fpath) + "\n"

    for name, lineno in model_names:
        pattern = re.compile(r'(?<!\w)' + re.escape(name) + r'(?!\w)')
        if not pattern.search(full_text):
            findings.append(Finding(
                "Неиспользуемые SQLAlchemy-модели",
                "red",
                rel(models_file), lineno, name,
                "Модель определена, но не импортируется ни в одном роутере/сервисе"
            ))


# ════════════════════════════════════════════
# 5. Неиспользуемые API-эндпоинты (роутеры без фронтенд-вызовов)
# ════════════════════════════════════════════

def scan_unused_endpoints():
    # Collect router files registered in main.py
    main_file = API_DIR / "main.py"
    if not main_file.exists():
        return
    main_text = read_file(main_file)

    # Find all router module names included via app.include_router
    router_imports = re.findall(r'from api\.routers import (\w+)', main_text)
    included_routers = set(router_imports)

    # Also find routers in routers/ that are NOT included
    router_dir = API_DIR / "routers"
    if router_dir.exists():
        for f in router_dir.iterdir():
            if f.suffix == ".py" and f.name != "__init__.py" and f.name != "Icon":
                mod_name = f.stem
                if mod_name not in included_routers:
                    findings.append(Finding(
                        "Неиспользуемые API-эндпоинты",
                        "red",
                        rel(f), 1, mod_name,
                        "Роутер существует, но НЕ подключён в main.py"
                    ))

    # Now check which registered router prefixes are actually called from frontend
    frontend_api_dir = FRONTEND_DIR / "api"
    if not frontend_api_dir.exists():
        return

    frontend_api_text = ""
    for f in frontend_api_dir.iterdir():
        if f.suffix in (".ts", ".tsx"):
            frontend_api_text += read_file(f) + "\n"

    # Extract API paths from frontend (e.g., '/orders', '/materials')
    frontend_paths = set(re.findall(r"['\"`](/[a-z_-]+(?:/[a-z_-]+)*)", frontend_api_text))
    # Normalize
    frontend_prefixes = set()
    for p in frontend_paths:
        parts = p.strip("/").split("/")
        if parts:
            frontend_prefixes.add(parts[0])

    # For each router, extract the prefix from main.py
    prefix_pattern = re.compile(r'app\.include_router\(\s*(\w+)\.router\s*,\s*prefix\s*=\s*["\']([^"\']+)["\']')
    for match in prefix_pattern.finditer(main_text):
        mod_name = match.group(1)
        prefix = match.group(2).strip("/")
        prefix_first = prefix.split("/")[0] if prefix else ""
        if prefix_first and prefix_first not in frontend_prefixes:
            findings.append(Finding(
                "Неиспользуемые API-эндпоинты",
                "yellow",
                rel(main_file), 0, f"{mod_name} (/{prefix})",
                "Роутер подключён, но префикс не найден в frontend API-вызовах"
            ))


# ════════════════════════════════════════════
# 6. Неиспользуемые фронтенд-компоненты (.tsx)
# ════════════════════════════════════════════

def scan_unused_components():
    components_dir = FRONTEND_DIR / "components"
    if not components_dir.exists():
        return

    # Collect all .tsx files in components/
    component_files = collect_files(components_dir, (".tsx",))

    # Build import text of ALL frontend files
    all_ts_files = collect_files(FRONTEND_DIR, (".ts", ".tsx"))
    full_text = ""
    for f in all_ts_files:
        full_text += read_file(f) + "\n"

    for comp_file in component_files:
        comp_name = comp_file.stem
        if comp_name == "index":
            continue

        # Check if component name appears in imports anywhere (except itself)
        # Look for: import ... from '.../<CompName>'  or  import <CompName>
        pattern = re.compile(r'(?:import\s+.*?' + re.escape(comp_name) + r'|from\s+[\'"].*?/' + re.escape(comp_name) + r'[\'"])')
        file_text = read_file(comp_file)

        # Count in all files except itself
        other_text = full_text.replace(file_text, "")
        if not pattern.search(other_text):
            # Also try simple name reference
            simple_pattern = re.compile(r'(?<!\w)' + re.escape(comp_name) + r'(?!\w)')
            if not simple_pattern.search(other_text):
                findings.append(Finding(
                    "Неиспользуемые компоненты",
                    "red",
                    rel(comp_file), 1, comp_name,
                    "Компонент нигде не импортируется"
                ))


# ════════════════════════════════════════════
# 7. Неиспользуемые фронтенд-страницы
# ════════════════════════════════════════════

def scan_unused_pages():
    pages_dir = FRONTEND_DIR / "pages"
    if not pages_dir.exists():
        return

    app_tsx = FRONTEND_DIR / "App.tsx"
    if not app_tsx.exists():
        return
    app_text = read_file(app_tsx)

    # Also check all frontend files for lazy imports
    all_ts_files = collect_files(FRONTEND_DIR, (".ts", ".tsx"))
    full_text = ""
    for f in all_ts_files:
        if f != app_tsx:
            full_text += read_file(f) + "\n"

    for page_file in pages_dir.iterdir():
        if page_file.suffix != ".tsx":
            continue
        page_name = page_file.stem
        if page_name == "index":
            continue

        # Check if imported in App.tsx
        if page_name not in app_text and page_name not in full_text:
            findings.append(Finding(
                "Неиспользуемые страницы",
                "red",
                rel(page_file), 1, page_name,
                "Страница существует, но не импортируется в App.tsx или другом файле"
            ))


# ════════════════════════════════════════════
# 8. Неиспользуемые TypeScript/JS-экспорты
# ════════════════════════════════════════════

def scan_unused_ts_exports():
    all_ts_files = collect_files(FRONTEND_DIR, (".ts", ".tsx"))

    # Build per-file word sets and global word counts
    _WORD_RE = re.compile(r'\b\w+\b')
    file_texts: dict[str, str] = {}
    file_words: dict[str, set[str]] = {}
    global_word_counts: dict[str, int] = defaultdict(int)
    for f in all_ts_files:
        text = read_file(f)
        file_texts[str(f)] = text
        words = set(_WORD_RE.findall(text))
        file_words[str(f)] = words
        for w in words:
            global_word_counts[w] += 1

    export_pattern = re.compile(r'export\s+(?:const|function|class|type|interface|enum)\s+(\w+)')

    for fpath in all_ts_files:
        text = file_texts[str(fpath)]
        local_words = file_words[str(fpath)]
        for match in export_pattern.finditer(text):
            name = match.group(1)
            lineno = text[:match.start()].count("\n") + 1

            if name in ("default", "Props", "FC"):
                continue

            # If the word appears in only 1 file (this one), it's unused elsewhere
            if global_word_counts.get(name, 0) <= 1:
                findings.append(Finding(
                    "Неиспользуемые TS-экспорты",
                    "yellow",
                    rel(fpath), lineno, name,
                    "Экспортируется, но не импортируется в других файлах"
                ))


# ════════════════════════════════════════════
# 9. Неиспользуемые CSS-классы (custom)
# ════════════════════════════════════════════

def scan_unused_css():
    css_files = collect_files(FRONTEND_DIR, (".css",))
    if not css_files:
        return

    all_ts_files = collect_files(FRONTEND_DIR, (".ts", ".tsx"))
    full_text = ""
    for f in all_ts_files:
        full_text += read_file(f) + "\n"

    class_pattern = re.compile(r'\.([a-zA-Z_][\w-]+)\s*\{')

    for css_file in css_files:
        css_text = read_file(css_file)
        for match in class_pattern.finditer(css_text):
            cls_name = match.group(1)
            lineno = css_text[:match.start()].count("\n") + 1

            # Skip Tailwind base/utility classes
            if cls_name.startswith("tw-") or cls_name in ("root", "body", "html", "app"):
                continue

            if cls_name not in full_text:
                findings.append(Finding(
                    "Неиспользуемые CSS-классы",
                    "yellow",
                    rel(css_file), lineno, f".{cls_name}",
                    "CSS-класс определён, но не найден в TSX/TS"
                ))


# ════════════════════════════════════════════
# 10. Мёртвая бизнес-логика
# ════════════════════════════════════════════

def scan_dead_business_logic():
    if not BUSINESS_DIR.exists():
        return

    business_files = collect_files(BUSINESS_DIR, (".py",))

    # Build text of all non-business Python files
    api_files = collect_files(API_DIR, (".py",))
    other_text = ""
    for f in api_files:
        other_text += read_file(f) + "\n"
    # Also check alembic
    alembic_files = collect_files(PROJECT_ROOT / "alembic", (".py",))
    for f in alembic_files:
        other_text += read_file(f) + "\n"
    # Also check within business (cross-references)
    business_text = ""
    for f in business_files:
        business_text += read_file(f) + "\n"

    for fpath in business_files:
        if fpath.name == "__init__.py":
            continue

        module_name = fpath.stem  # e.g., "capacity"
        # Build import patterns
        # business.kiln.capacity → from business.kiln.capacity import ... or from business.kiln import capacity
        rel_path = fpath.relative_to(PROJECT_ROOT)
        module_path = ".".join(rel_path.with_suffix("").parts)  # business.kiln.capacity

        # Check if this module is imported anywhere outside itself
        found = False

        # Pattern 1: from business.X.Y import ...
        if module_path in other_text:
            found = True
        # Pattern 2: import business.X.Y
        if not found and module_path in other_text:
            found = True
        # Pattern 3: from business.X import Y (where Y is module_name)
        if not found:
            parent_path = ".".join(rel_path.parent.parts)
            pattern = f"from {parent_path} import"
            if pattern in other_text and module_name in other_text:
                found = True
        # Pattern 4: cross-business import
        if not found:
            file_text = read_file(fpath)
            other_business = business_text.replace(file_text, "")
            if module_path in other_business:
                found = True
            if not found:
                parent_path = ".".join(rel_path.parent.parts)
                pattern = f"from {parent_path} import"
                if pattern in other_business and module_name in other_business:
                    found = True

        if not found:
            findings.append(Finding(
                "Мёртвая бизнес-логика",
                "red",
                rel(fpath), 1, module_name,
                f"Модуль {module_path} нигде не импортируется"
            ))


# ════════════════════════════════════════════
# 11. Осиротевшие Pydantic-схемы
# ════════════════════════════════════════════

def scan_orphan_schemas():
    schemas_file = API_DIR / "schemas.py"
    if not schemas_file.exists():
        # Check for schema_patches dir
        schemas_dir = API_DIR / "schema_patches"
        if schemas_dir.exists():
            schema_files = collect_files(schemas_dir, (".py",))
        else:
            return
        schema_files.append(schemas_file) if schemas_file.exists() else None
    else:
        schema_files = [schemas_file]
        schemas_dir = API_DIR / "schema_patches"
        if schemas_dir.exists():
            schema_files += collect_files(schemas_dir, (".py",))

    # Collect schema class names
    schema_names: list[tuple[str, str, int]] = []
    for sf in schema_files:
        if not sf.exists():
            continue
        source = read_file(sf)
        try:
            tree = ast.parse(source, filename=str(sf))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if node.name in ("Config",):
                    continue
                schema_names.append((node.name, rel(sf), node.lineno))

    # Build word sets for routers + business
    _WORD_RE = re.compile(r'\b\w+\b')
    router_files = collect_files(API_DIR / "routers", (".py",))
    business_files = collect_files(BUSINESS_DIR, (".py",))
    usage_words: set[str] = set()
    for f in router_files + business_files:
        usage_words.update(_WORD_RE.findall(read_file(f)))

    # Schema internal word counts
    schema_word_counts: dict[str, int] = defaultdict(int)
    for sf in schema_files:
        if sf.exists():
            for w in _WORD_RE.findall(read_file(sf)):
                schema_word_counts[w] += 1

    for name, filepath, lineno in schema_names:
        if name in usage_words:
            continue  # used in routers or business
        # Maybe it's only used internally by other schemas
        if schema_word_counts.get(name, 0) <= 1:
            findings.append(Finding(
                "Осиротевшие схемы",
                "red",
                filepath, lineno, name,
                "Pydantic-схема не используется ни в одном роутере/сервисе"
            ))
        else:
            findings.append(Finding(
                "Осиротевшие схемы",
                "yellow",
                filepath, lineno, name,
                "Используется только внутри schemas.py (как под-схема)"
            ))


# ════════════════════════════════════════════
# 12. Неиспользуемые переменные окружения
# ════════════════════════════════════════════

def scan_unused_env_vars():
    config_file = API_DIR / "config.py"
    if not config_file.exists():
        return

    source = read_file(config_file)
    try:
        tree = ast.parse(source, filename=str(config_file))
    except SyntaxError:
        return

    # Find Settings class and its fields
    env_vars: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "Settings":
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    var_name = item.target.id
                    env_vars.append((var_name, item.lineno))

    # Build text of all Python files EXCEPT config.py
    py_files = collect_files(API_DIR, (".py",)) + collect_files(BUSINESS_DIR, (".py",))
    usage_text = ""
    for f in py_files:
        if f.name == "config.py" and f.parent == API_DIR:
            continue
        usage_text += read_file(f) + "\n"

    for var_name, lineno in env_vars:
        # Check for settings.VAR_NAME or settings.var_name
        pattern_upper = re.compile(r'settings\.' + re.escape(var_name), re.IGNORECASE)
        pattern_lower = re.compile(r'settings\.' + re.escape(var_name.lower()), re.IGNORECASE)
        # Also check os.getenv("VAR_NAME") and os.environ["VAR_NAME"]
        env_pattern = re.compile(r'(?:getenv|environ).*?' + re.escape(var_name))

        if not pattern_upper.search(usage_text) and not pattern_lower.search(usage_text) and not env_pattern.search(usage_text):
            findings.append(Finding(
                "Неиспользуемые env-переменные",
                "yellow",
                rel(config_file), lineno, var_name,
                "Определена в Settings, но не используется за пределами config.py"
            ))


# ════════════════════════════════════════════
# Вывод результатов
# ════════════════════════════════════════════

def print_results():
    if not findings:
        print(f"\n{GREEN}{BOLD}Мёртвый код не найден! Кодовая база чистая.{RESET}\n")
        return

    # Group by category
    by_category: dict[str, list[Finding]] = defaultdict(list)
    for f in findings:
        by_category[f.category].append(f)

    # Counters
    total_red = sum(1 for f in findings if f.level == "red")
    total_yellow = sum(1 for f in findings if f.level == "yellow")
    total = len(findings)

    print(f"\n{'═' * 80}")
    print(f"{BOLD}{CYAN}  MOONJAR PMS — ОТЧЁТ ПО МЁРТВОМУ КОДУ{RESET}")
    print(f"{'═' * 80}\n")

    category_order = [
        "Неиспользуемые импорты",
        "Неиспользуемые функции",
        "Неиспользуемые классы",
        "Неиспользуемые SQLAlchemy-модели",
        "Неиспользуемые API-эндпоинты",
        "Неиспользуемые компоненты",
        "Неиспользуемые страницы",
        "Неиспользуемые TS-экспорты",
        "Неиспользуемые CSS-классы",
        "Мёртвая бизнес-логика",
        "Осиротевшие схемы",
        "Неиспользуемые env-переменные",
    ]

    for cat in category_order:
        items = by_category.get(cat, [])
        if not items:
            continue

        red_count = sum(1 for i in items if i.level == "red")
        yellow_count = sum(1 for i in items if i.level == "yellow")

        print(f"{BOLD}{'─' * 70}{RESET}")
        label = f"  {cat}"
        if red_count:
            label += f"  {RED}[{red_count} мёртвых]{RESET}"
        if yellow_count:
            label += f"  {YELLOW}[{yellow_count} подозрительных]{RESET}"
        print(f"{BOLD}{label}{RESET}")
        print(f"{'─' * 70}")

        for item in sorted(items, key=lambda x: (x.level != "red", x.path, x.line)):
            color = item.color()
            tag = item.level_ru()
            print(f"  {color}[{tag}]{RESET} {DIM}{item.path}:{item.line}{RESET}  {BOLD}{item.name}{RESET}")
            if item.detail:
                print(f"           {DIM}{item.detail}{RESET}")

        print()

    # Summary
    print(f"{'═' * 80}")
    print(f"{BOLD}  ИТОГО:{RESET}")
    print(f"    {RED}Точно мёртвый код:{RESET}  {total_red}")
    print(f"    {YELLOW}Возможно мёртвый:{RESET}   {total_yellow}")
    print(f"    {BOLD}Всего находок:{RESET}       {total}")
    print(f"{'═' * 80}\n")


def save_report():
    """Сохранить отчёт в docs/DEAD_CODE_REPORT.md"""
    DOCS_DIR.mkdir(exist_ok=True)
    report_path = DOCS_DIR / "DEAD_CODE_REPORT.md"

    by_category: dict[str, list[Finding]] = defaultdict(list)
    for f in findings:
        by_category[f.category].append(f)

    total_red = sum(1 for f in findings if f.level == "red")
    total_yellow = sum(1 for f in findings if f.level == "yellow")

    lines = [
        "# Moonjar PMS — Отчёт по мёртвому коду",
        "",
        f"Дата сканирования: {time.strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Сводка",
        "",
        f"| Категория | Точно мёртвый | Возможно мёртвый |",
        f"|-----------|:---:|:---:|",
    ]

    category_order = [
        "Неиспользуемые импорты",
        "Неиспользуемые функции",
        "Неиспользуемые классы",
        "Неиспользуемые SQLAlchemy-модели",
        "Неиспользуемые API-эндпоинты",
        "Неиспользуемые компоненты",
        "Неиспользуемые страницы",
        "Неиспользуемые TS-экспорты",
        "Неиспользуемые CSS-классы",
        "Мёртвая бизнес-логика",
        "Осиротевшие схемы",
        "Неиспользуемые env-переменные",
    ]

    for cat in category_order:
        items = by_category.get(cat, [])
        red = sum(1 for i in items if i.level == "red")
        yellow = sum(1 for i in items if i.level == "yellow")
        if items:
            lines.append(f"| {cat} | {red} | {yellow} |")

    lines.append(f"| **ИТОГО** | **{total_red}** | **{total_yellow}** |")
    lines.append("")

    for cat in category_order:
        items = by_category.get(cat, [])
        if not items:
            continue

        lines.append(f"## {cat}")
        lines.append("")

        for item in sorted(items, key=lambda x: (x.level != "red", x.path, x.line)):
            tag = "DEAD" if item.level == "red" else "MAYBE"
            lines.append(f"- **[{tag}]** `{item.path}:{item.line}` — `{item.name}`")
            if item.detail:
                lines.append(f"  - {item.detail}")

        lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"{GREEN}Отчёт сохранён: {rel(report_path)}{RESET}\n")


# ════════════════════════════════════════════
# Main
# ════════════════════════════════════════════

def main():
    print(f"\n{BOLD}{CYAN}Moonjar PMS — Сканер мёртвого кода{RESET}")
    print(f"{DIM}Корень проекта: {PROJECT_ROOT}{RESET}\n")

    start = time.time()

    scanners = [
        ("1/12 Неиспользуемые импорты...", scan_unused_imports),
        ("2/12 Неиспользуемые функции...", scan_unused_functions),
        ("3/12 Неиспользуемые классы...", scan_unused_classes),
        ("4/12 Неиспользуемые модели...", scan_unused_models),
        ("5/12 Неиспользуемые эндпоинты...", scan_unused_endpoints),
        ("6/12 Неиспользуемые компоненты...", scan_unused_components),
        ("7/12 Неиспользуемые страницы...", scan_unused_pages),
        ("8/12 Неиспользуемые TS-экспорты...", scan_unused_ts_exports),
        ("9/12 Неиспользуемые CSS-классы...", scan_unused_css),
        ("10/12 Мёртвая бизнес-логика...", scan_dead_business_logic),
        ("11/12 Осиротевшие схемы...", scan_orphan_schemas),
        ("12/12 Неиспользуемые env-переменные...", scan_unused_env_vars),
    ]

    for label, scanner in scanners:
        print(f"  {DIM}{label}{RESET}", end="", flush=True)
        t = time.time()
        scanner()
        elapsed = time.time() - t
        print(f"  {DIM}({elapsed:.1f}с){RESET}")

    total_time = time.time() - start
    print(f"\n{DIM}Сканирование завершено за {total_time:.1f}с{RESET}")

    print_results()
    save_report()


if __name__ == "__main__":
    main()
