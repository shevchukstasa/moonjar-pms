#!/usr/bin/env python3
"""
Скрипт проверки: все создаваемые сущности должны быть удаляемы (owner)
с обязательным логированием (AuditLog).

Проверяет:
1. Frontend: есть Create → должен быть Delete
2. Backend: есть POST → должен быть DELETE
3. DELETE endpoint → должен писать в AuditLog
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROUTERS_DIR = ROOT / "api" / "routers"
PAGES_DIR = ROOT / "presentation" / "dashboard" / "src" / "pages"

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def check_backend_routers():
    """Check all routers: POST exists → DELETE should exist → AuditLog should be used."""
    print(f"\n{BOLD}═══ BACKEND: POST → DELETE → AuditLog ═══{RESET}\n")

    results = []
    for rfile in sorted(ROUTERS_DIR.glob("*.py")):
        if rfile.stem.startswith("__"):
            continue
        text = rfile.read_text()

        has_post = bool(re.search(r'@router\.post\(', text))
        has_delete = bool(re.search(r'@router\.delete\(', text))
        has_audit = "AuditLog" in text

        if not has_post:
            continue  # Skip read-only routers

        status = "✅" if has_delete else "❌"
        audit_status = "✅" if has_audit else "⚠️"

        if not has_delete:
            results.append(("MISSING_DELETE", rfile.stem))
            print(f"  {RED}❌ {rfile.stem}{RESET}: POST есть, DELETE — НЕТ")
        elif not has_audit:
            results.append(("MISSING_AUDIT", rfile.stem))
            print(f"  {YELLOW}⚠️  {rfile.stem}{RESET}: DELETE есть, но AuditLog — НЕТ")
        else:
            print(f"  {GREEN}✅ {rfile.stem}{RESET}: POST + DELETE + AuditLog")

    return results


def check_frontend_pages():
    """Check all pages: Create button → Delete button should exist."""
    print(f"\n{BOLD}═══ FRONTEND: Create → Delete ═══{RESET}\n")

    results = []
    for pfile in sorted(PAGES_DIR.glob("*.tsx")):
        text = pfile.read_text()

        # Detect create functionality
        has_create = bool(re.search(
            r'(Add\s|Create\s|\+\s*Add|\+\s*New|upsert|createMut|useCreate)',
            text
        ))
        if not has_create:
            continue

        has_delete = bool(re.search(
            r'(deleteMut|deleteMutation|onDelete|handleDelete|\.delete\(|Delete<|Delete\b.*button|variant="danger")',
            text, re.IGNORECASE
        ))

        if not has_delete:
            results.append(pfile.stem)
            print(f"  {RED}❌ {pfile.stem}{RESET}: Create есть, Delete — НЕТ")
        else:
            print(f"  {GREEN}✅ {pfile.stem}{RESET}: Create + Delete")

    return results


def main():
    print(f"""
{BOLD}╔══════════════════════════════════════════════════════════════╗
║  ПРОВЕРКА: CREATE → DELETE + AUDIT LOG                      ║
║  Всё, что создаётся Owner, должно удаляться с логированием  ║
╚══════════════════════════════════════════════════════════════╝{RESET}
""")

    backend_issues = check_backend_routers()
    frontend_issues = check_frontend_pages()

    print(f"\n{BOLD}═══ ИТОГО ═══{RESET}\n")

    missing_delete = [r for t, r in backend_issues if t == "MISSING_DELETE"]
    missing_audit = [r for t, r in backend_issues if t == "MISSING_AUDIT"]

    if missing_delete:
        print(f"  {RED}Backend без DELETE ({len(missing_delete)}):{RESET}")
        for r in missing_delete:
            print(f"    - {r}")

    if missing_audit:
        print(f"  {YELLOW}Backend DELETE без AuditLog ({len(missing_audit)}):{RESET}")
        for r in missing_audit:
            print(f"    - {r}")

    if frontend_issues:
        print(f"  {RED}Frontend без Delete кнопки ({len(frontend_issues)}):{RESET}")
        for p in frontend_issues:
            print(f"    - {p}")

    if not missing_delete and not missing_audit and not frontend_issues:
        print(f"  {GREEN}✅ Все сущности удаляемы с аудит-логом!{RESET}")

    print()


if __name__ == "__main__":
    main()
