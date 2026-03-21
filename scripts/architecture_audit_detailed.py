#!/usr/bin/env python3
"""
Architecture Audit — Detailed Report (русский язык)

Генерирует понятный отчёт о пробелах в системе:
- Что построено, но не используется
- Что используется в бизнес-логике, но не имеет интерфейса
- Какие функции запланированы, но не реализованы
- Приоритеты по важности

Запуск: python scripts/architecture_audit_detailed.py
"""

import os
import re
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
API_DIR = ROOT / "api"
ROUTERS_DIR = API_DIR / "routers"
MODELS_FILE = API_DIR / "models.py"
MAIN_FILE = API_DIR / "main.py"
DASHBOARD_DIR = ROOT / "presentation" / "dashboard" / "src"
PAGES_DIR = DASHBOARD_DIR / "pages"
APP_TSX = DASHBOARD_DIR / "App.tsx"
SIDEBAR_FILE = DASHBOARD_DIR / "components" / "layout" / "Sidebar.tsx"

# ── Colors ────────────────────────────────────────────────────────────
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"
BG_RED = "\033[41m"
BG_YELLOW = "\033[43m"
BG_GREEN = "\033[42m"

# ── Helpers ───────────────────────────────────────────────────────────

def count_lines(path: Path) -> int:
    try:
        return len(path.read_text().splitlines())
    except:
        return 0


def has_frontend_page(api_prefix: str) -> bool:
    """Check if a frontend page exists that references this API prefix."""
    # Map API prefix to known page files
    page_map = {
        "/api/kiln-maintenance": "KilnMaintenancePage.tsx",
        "/api/factory-calendar": "FactoryCalendarPage.tsx",
        "/api/reconciliations": "ReconciliationsPage.tsx",
        "/api/finished-goods": "FinishedGoodsPage.tsx",
        "/api/reports": "ReportsPage.tsx",
        "/api/dashboard-access": "DashboardAccessPage.tsx",
        "/api/grinding-stock": "GrindingPage.tsx",
        "/api/settings": "SettingsPage.tsx",
        "/api/kiln-firing-schedules": "KilnFiringSchedulesPage.tsx",
        "/api/stages": "StagesPage.tsx",
    }
    page_file = page_map.get(api_prefix)
    if page_file and (PAGES_DIR / page_file).exists():
        return True
    # Also check API client files
    api_dir = DASHBOARD_DIR / "api"
    for f in api_dir.glob("*.ts"):
        try:
            if api_prefix.replace("/api/", "") in f.read_text():
                return True
        except:
            pass
    return False


def has_delete_endpoint(router_name: str) -> bool:
    """Check if a router file has DELETE endpoint."""
    rfile = ROUTERS_DIR / f"{router_name}.py"
    if not rfile.exists():
        return False
    return "@router.delete(" in rfile.read_text()

def count_endpoints(router_path: Path) -> dict:
    """Count HTTP methods in a router file."""
    text = router_path.read_text()
    methods = defaultdict(int)
    for m in re.finditer(r'@router\.(get|post|put|patch|delete)\(', text):
        methods[m.group(1).upper()] += 1
    return dict(methods)

def search_in_codebase(pattern: str, dirs: list[Path]) -> int:
    """Count how many files reference a pattern."""
    count = 0
    for d in dirs:
        if not d.exists():
            continue
        for f in d.rglob("*.py"):
            if pattern in f.read_text():
                count += 1
        for f in d.rglob("*.tsx"):
            if pattern in f.read_text():
                count += 1
        for f in d.rglob("*.ts"):
            if f.suffix == ".ts" and pattern in f.read_text():
                count += 1
    return count


# ═══════════════════════════════════════════════════════════════════════
# MAIN REPORT
# ═══════════════════════════════════════════════════════════════════════

def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    print(f"""
{BOLD}{CYAN}╔══════════════════════════════════════════════════════════════╗
║          MOONJAR PMS — ПОЛНЫЙ АУДИТ АРХИТЕКТУРЫ             ║
║                    {now}                      ║
╚══════════════════════════════════════════════════════════════╝{RESET}
""")

    # ── Statistics ─────────────────────────────────────────────────────
    router_count = len([f for f in ROUTERS_DIR.glob("*.py") if f.stem != "__init__"])
    model_count = len(re.findall(r"class \w+\(Base\):", MODELS_FILE.read_text()))
    page_count = len(list(PAGES_DIR.glob("*.tsx")))

    print(f"{BOLD}📊 Общая статистика:{RESET}")
    print(f"   Backend роутеров:  {CYAN}{router_count}{RESET}")
    print(f"   Моделей БД:       {CYAN}{model_count}{RESET}")
    print(f"   Frontend страниц: {CYAN}{page_count}{RESET}")
    print()

    # ═══════════════════════════════════════════════════════════════════
    # SECTION A: Бэкенд построен, но нет интерфейса
    # ═══════════════════════════════════════════════════════════════════

    print(f"""{BOLD}{RED}
╔══════════════════════════════════════════════════════════════╗
║  A. BACKEND ЕСТЬ — FRONTEND НЕТ                            ║
║  API эндпоинты построены, но пользователь не может          ║
║  ими воспользоваться через интерфейс                        ║
╚══════════════════════════════════════════════════════════════╝{RESET}
""")

    backend_no_frontend = [
        {
            "api": "/api/kiln-maintenance",
            "name": "🔧 Обслуживание печей (Kiln Maintenance)",
            "priority": "ВЫСОКИЙ",
            "description": (
                "Полная система планирования ТО печей: типы обслуживания,\n"
                "   расписание на каждую печь, повторяющиеся задачи,\n"
                "   отметки о выполнении. 9 эндпоинтов готовы.\n"
                "   Связано с новым модулем Kiln Inspections."
            ),
            "who_needs": "Production Manager",
            "endpoints": "GET/POST/PUT/DELETE × types, schedules, completions",
            "status": "Backend 100% → Frontend 0%",
        },
        {
            "api": "/api/factory-calendar",
            "name": "📅 Календарь фабрики (Factory Calendar)",
            "priority": "ВЫСОКИЙ",
            "description": (
                "Рабочие/нерабочие дни фабрики. Праздники Бали,\n"
                "   выходные. Используется для расчёта сроков производства.\n"
                "   Без UI менеджер не может отметить нерабочие дни."
            ),
            "who_needs": "Admin / Production Manager",
            "endpoints": "GET working-days, GET/POST/POST-bulk/DELETE entries",
            "status": "Backend 100% → Frontend 0%",
        },
        {
            "api": "/api/reconciliations",
            "name": "📦 Инвентаризация (Reconciliations)",
            "priority": "ВЫСОКИЙ",
            "description": (
                "Сверка физических остатков с системой.\n"
                "   Создать сверку → внести факт по позициям →\n"
                "   завершить → автоматически создаются корректировки.\n"
                "   Критично для точности остатков материалов."
            ),
            "who_needs": "Warehouse / Production Manager",
            "endpoints": "GET/POST/PATCH/DELETE + items + complete",
            "status": "Backend 100% → Frontend 0%",
        },
        {
            "api": "/api/finished-goods",
            "name": "📊 Склад готовой продукции (Finished Goods)",
            "priority": "ВЫСОКИЙ",
            "description": (
                "Учёт готовых изделий: цвет, размер, коллекция, количество.\n"
                "   Проверка наличия по всем фабрикам.\n"
                "   Нужно для отгрузки заказов из существующих запасов."
            ),
            "who_needs": "Warehouse / PM / Owner",
            "endpoints": "GET list + availability, POST upsert, PATCH update",
            "status": "Backend 100% → Frontend 0%",
        },
        {
            "api": "/api/reports",
            "name": "📈 Аналитические отчёты (Reports)",
            "priority": "СРЕДНИЙ",
            "description": (
                "Бизнес-отчёты: сводка по заказам (кол-во, % вовремя,\n"
                "   средний срок), загрузка печей (утилизация в %).\n"
                "   Есть analytics API, но reports — отдельный блок."
            ),
            "who_needs": "Owner / CEO / PM",
            "endpoints": "GET list, GET orders-summary, GET kiln-load",
            "status": "Backend 100% → Frontend 0%",
        },
        {
            "api": "/api/dashboard-access",
            "name": "🔐 Конструктор дашбордов (Dashboard Access)",
            "priority": "СРЕДНИЙ",
            "description": (
                "Админ может дать пользователю доступ к дополнительным\n"
                "   дашбордам сверх его роли. Например, PM видит CEO-дашборд.\n"
                "   Без UI — только через API вручную."
            ),
            "who_needs": "Admin",
            "endpoints": "GET/POST/PATCH/DELETE + my-dashboards",
            "status": "Backend 100% → Frontend 0%",
        },
        {
            "api": "/api/grinding-stock",
            "name": "⚙️ Решения по перешлифовке (Grinding Decisions)",
            "priority": "СРЕДНИЙ",
            "description": (
                "Очередь позиций на перешлифовку. PM решает:\n"
                "   шлифовать / ждать / отправить в Mana.\n"
                "   Sorter видит список, но PM не может принять решение через UI."
            ),
            "who_needs": "Production Manager",
            "endpoints": "GET list/stats/item, POST create/decide",
            "status": "Backend 100% → Frontend ~30% (только просмотр)",
        },
        {
            "api": "/api/settings/service-lead-times",
            "name": "⏱ Сроки сервисов (Service Lead Times)",
            "priority": "НИЗКИЙ",
            "description": (
                "Настройка сроков для трафарета, шелкографии и т.д.\n"
                "   По фабрикам. Есть SettingsPage, но без этого раздела."
            ),
            "who_needs": "Admin",
            "endpoints": "GET/PUT/POST-reset per factory",
            "status": "Backend 100% → Frontend 0% (страница Settings существует)",
        },
        {
            "api": "/api/kiln-firing-schedules",
            "name": "🔥 Расписание обжигов (Kiln Firing Schedules)",
            "priority": "НИЗКИЙ",
            "description": (
                "CRUD для расписания обжигов. Базовый функционал,\n"
                "   пересекается с модулем Schedule."
            ),
            "who_needs": "PM",
            "endpoints": "GET/POST/PATCH/DELETE",
            "status": "Backend 100% → Frontend 0%",
        },
        {
            "api": "/api/stages",
            "name": "📋 Производственные этапы (Stages)",
            "priority": "НИЗКИЙ",
            "description": (
                "Справочник этапов производства (резка, глазуровка, обжиг...).\n"
                "   Справочные данные, можно управлять через Admin."
            ),
            "who_needs": "Admin",
            "endpoints": "GET/POST/PATCH/DELETE",
            "status": "Backend 100% → Frontend 0%",
        },
    ]

    resolved_count = 0
    for item in backend_no_frontend:
        has_fe = has_frontend_page(item["api"])
        if has_fe:
            resolved_count += 1
            print(f"  {GREEN}✅ {item['name']}{RESET}  {DIM}— РЕАЛИЗОВАНО{RESET}")
            print()
            continue
        priority_color = RED if item["priority"] == "ВЫСОКИЙ" else (YELLOW if item["priority"] == "СРЕДНИЙ" else DIM)
        print(f"  {BOLD}{item['name']}{RESET}")
        print(f"  {priority_color}Приоритет: {item['priority']}{RESET}  |  Кому нужно: {item['who_needs']}")
        print(f"  {DIM}{item['description']}{RESET}")
        print(f"  API: {CYAN}{item['api']}{RESET}  →  {item['endpoints']}")
        print(f"  Статус: {YELLOW}{item['status']}{RESET}")
        print()
    if resolved_count:
        print(f"  {GREEN}{BOLD}→ {resolved_count} из {len(backend_no_frontend)} задач закрыты!{RESET}")
        print()

    # ═══════════════════════════════════════════════════════════════════
    # SECTION B: Модели БД без API
    # ═══════════════════════════════════════════════════════════════════

    print(f"""{BOLD}{YELLOW}
╔══════════════════════════════════════════════════════════════╗
║  B. МОДЕЛИ БД БЕЗ API                                      ║
║  Таблицы созданы в базе, но к ним нет доступа               ║
║  ни через API, ни через интерфейс                           ║
╚══════════════════════════════════════════════════════════════╝{RESET}
""")

    models_no_api = [
        {
            "name": "DailyTaskDistribution",
            "table": "daily_task_distributions",
            "category": "ИСПОЛЬЗУЕТСЯ ВНУТРЕННЕ",
            "description": (
                "Ежедневная рассылка задач в Telegram.\n"
                "   Генерируется автоматически планировщиком.\n"
                "   → API не нужен (внутренний сервис).\n"
                "   → Но может быть полезен GET для просмотра истории рассылок."
            ),
            "action": "Опционально: GET-эндпоинт для просмотра истории",
        },
        {
            "name": "EscalationRule",
            "table": "escalation_rules",
            "category": "ИСПОЛЬЗУЕТСЯ ВНУТРЕННЕ, НУЖЕН UI",
            "description": (
                "Правила эскалации задач: PM не решил за N часов → CEO → Owner.\n"
                "   Движок эскалации работает, но правила нельзя настроить через UI.\n"
                "   Сейчас: таймауты зашиты, менять можно только в БД."
            ),
            "action": "НУЖЕН: Страница настройки эскалации в Admin",
        },
        {
            "name": "ManaShipment",
            "table": "mana_shipments",
            "category": "ИСПОЛЬЗУЕТСЯ ВНУТРЕННЕ, НУЖЕН UI",
            "description": (
                "Отгрузки дефектных плиток в Mana (внешний глазуровщик).\n"
                "   Сервис sorting_split.py маршрутизирует туда дефекты.\n"
                "   Но нет UI для просмотра/подтверждения отгрузок."
            ),
            "action": "НУЖЕН: Раздел в Warehouse для управления отгрузками Mana",
        },
        {
            "name": "MaterialDefectThreshold",
            "table": "material_defect_thresholds",
            "category": "ИСПОЛЬЗУЕТСЯ ВНУТРЕННЕ, НУЖЕН UI",
            "description": (
                "Пороги допустимого % дефектов при приёмке материалов.\n"
                "   Warehouse автоматически одобряет, если дефекты < порога.\n"
                "   Но пороги нельзя настроить через UI."
            ),
            "action": "НУЖЕН: Настройка порогов в Admin → Materials",
        },
        {
            "name": "PurchaseConsolidationSetting",
            "table": "purchase_consolidation_settings",
            "category": "ИСПОЛЬЗУЕТСЯ ВНУТРЕННЕ, НУЖЕН UI",
            "description": (
                "Настройки консолидации закупок: окно объединения (дни),\n"
                "   порог срочности, горизонт планирования.\n"
                "   Purchaser-сервис использует, но настройки не редактируемы."
            ),
            "action": "НУЖЕН: Раздел настроек в Purchaser или Admin",
        },
        {
            "name": "ReceivingSetting",
            "table": "receiving_settings",
            "category": "ИСПОЛЬЗУЕТСЯ ВНУТРЕННЕ, НУЖЕН UI",
            "description": (
                "Режим приёмки материалов на фабрике: 'all' (ручная) или 'auto'.\n"
                "   Влияет на Warehouse workflow. Нельзя переключить через UI."
            ),
            "action": "НУЖЕН: Переключатель в Admin → Settings (per factory)",
        },
        {
            "name": "StageReconciliationLog",
            "table": "stage_reconciliation_logs",
            "category": "ИСПОЛЬЗУЕТСЯ ВНУТРЕННЕ",
            "description": (
                "Логи сверки количества плиток при переходе между этапами.\n"
                "   Reconciliation-сервис автоматически записывает.\n"
                "   Алерт PM при расхождениях."
            ),
            "action": "Опционально: GET-эндпоинт для просмотра логов",
        },
        {
            "name": "RagEmbedding",
            "table": "rag_embeddings",
            "category": "ВНУТРЕННИЙ СЕРВИС",
            "description": (
                "Векторные эмбеддинги для AI-чата (RAG).\n"
                "   Полностью внутренний — индексирует данные для поиска."
            ),
            "action": "API не нужен",
        },
        {
            "name": "KilnCalculationLog",
            "table": "kiln_calculation_logs",
            "category": "НЕ ИСПОЛЬЗУЕТСЯ",
            "description": (
                "Логи расчётов вместимости печей.\n"
                "   Модель и схемы созданы, но нигде не записываются."
            ),
            "action": "Удалить или реализовать запись логов",
        },
        {
            "name": "ProcessStep + StandardWork",
            "table": "process_steps / standard_work",
            "category": "НЕ ИСПОЛЬЗУЕТСЯ",
            "description": (
                "Стандартные операции и нормы времени.\n"
                "   Модели созданы, схемы есть, но нет ни сервисов, ни API.\n"
                "   Возможно, будущая фича для нормирования."
            ),
            "action": "Отложить (фича v2) или удалить",
        },
        {
            "name": "EdgeHeightRule",
            "table": "edge_height_rules",
            "category": "НЕ ИСПОЛЬЗУЕТСЯ",
            "description": (
                "Правила максимальной высоты кромки в зависимости от толщины.\n"
                "   Создана в миграции, но нигде не используется."
            ),
            "action": "Отложить (фича v2) или удалить",
        },
    ]

    for item in models_no_api:
        cat_color = RED if "НУЖЕН UI" in item["category"] else (YELLOW if "ВНУТРЕННЕ" in item["category"] else DIM)
        print(f"  {BOLD}{item['name']}{RESET}  {DIM}({item['table']}){RESET}")
        print(f"  {cat_color}{item['category']}{RESET}")
        print(f"  {DIM}{item['description']}{RESET}")
        print(f"  → {CYAN}{item['action']}{RESET}")
        print()

    # ═══════════════════════════════════════════════════════════════════
    # SECTION C: CRUD не полный
    # ═══════════════════════════════════════════════════════════════════

    print(f"""{BOLD}{MAGENTA}
╔══════════════════════════════════════════════════════════════╗
║  C. НЕПОЛНЫЙ CRUD                                           ║
║  Можно создать, но нельзя удалить                           ║
╚══════════════════════════════════════════════════════════════╝{RESET}
""")

    crud_issues = [
        {
            "router": "batches",
            "issue": "Батчи (загрузки в печь) нельзя удалить",
            "reason": "Батч — критическая запись. Удаление может нарушить историю. Возможно, нужен soft-delete или 'cancel'.",
            "verdict": "⚠️ Возможно ОК — батчи не должны удаляться",
        },
        {
            "router": "finished_goods",
            "issue": "Готовую продукцию нельзя удалить из учёта",
            "reason": "Только создание и обновление. Нет возможности списать.",
            "verdict": "❌ Нужен DELETE или PATCH для списания",
        },
        {
            "router": "material_groups",
            "issue": "Группы материалов нельзя удалить",
            "reason": "Справочник. Если группа больше не нужна — нельзя убрать.",
            "verdict": "❌ Нужен DELETE (с проверкой зависимостей)",
        },
        {
            "router": "positions",
            "issue": "Позиции заказа нельзя удалить",
            "reason": "Можно создать, изменить статус, но не удалить ошибочную.",
            "verdict": "⚠️ Возможно ОК — позиции отменяются, не удаляются",
        },
        {
            "router": "quality",
            "issue": "Проверки качества нельзя удалить",
            "reason": "Записи QC — аудиторский след. Удаление может быть нежелательно.",
            "verdict": "⚠️ Возможно ОК — QC записи не должны удаляться",
        },
        {
            "router": "tasks",
            "issue": "Задачи нельзя удалить",
            "reason": "Можно создать, назначить, закрыть, но не удалить.",
            "verdict": "⚠️ Возможно ОК — задачи закрываются, не удаляются",
        },
        {
            "router": "tps",
            "issue": "TPS метрики нельзя удалить",
            "reason": "Toyota Production System — метрики и отклонения.",
            "verdict": "⚠️ Возможно ОК — метрики архивные",
        },
        {
            "router": "users",
            "issue": "Пользователей нельзя удалить",
            "reason": "Есть toggle-active (деактивация), но нет полного DELETE.",
            "verdict": "⚠️ Возможно ОК — есть toggle-active для деактивации",
        },
    ]

    for item in crud_issues:
        # Dynamic check: does the router now have DELETE?
        has_del = has_delete_endpoint(item["router"])
        if "❌" in item["verdict"] and has_del:
            print(f"  {GREEN}✅ {item['router']}{RESET}: {item['issue']} {DIM}— ИСПРАВЛЕНО{RESET}")
            print()
            continue
        verdict_color = RED if "❌" in item["verdict"] else YELLOW
        print(f"  {BOLD}{item['router']}{RESET}: {item['issue']}")
        print(f"  {DIM}{item['reason']}{RESET}")
        print(f"  {verdict_color}{item['verdict']}{RESET}")
        print()

    # ═══════════════════════════════════════════════════════════════════
    # SECTION D: Env config
    # ═══════════════════════════════════════════════════════════════════

    print(f"""{BOLD}{DIM}
╔══════════════════════════════════════════════════════════════╗
║  D. ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ                                    ║
║  Используются в коде, но не в централизованном Settings     ║
╚══════════════════════════════════════════════════════════════╝{RESET}
""")

    env_issues = [
        ("TELEGRAM_WEBHOOK_SECRET", "Секрет для webhook Telegram бота", "Перенести в Settings"),
        ("INTERNAL_API_KEY", "Ключ для внутренних API-вызовов", "Перенести в Settings"),
        ("UPLOADS_DIR", "Директория для загрузки файлов", "Перенести в Settings"),
        ("RAILWAY_ENVIRONMENT", "Определение среды Railway", "ОК — платформенная переменная"),
        ("RAILWAY_PUBLIC_DOMAIN", "Публичный домен Railway", "ОК — платформенная переменная"),
        ("ENV", "Общая переменная среды", "ОК — стандартная"),
    ]

    for var, desc, action in env_issues:
        color = YELLOW if "Перенести" in action else DIM
        print(f"  {color}{var}{RESET}: {desc}")
        print(f"  → {action}")
        print()

    # ═══════════════════════════════════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════════════════════════════════

    print(f"""{BOLD}{GREEN}
╔══════════════════════════════════════════════════════════════╗
║                    ИТОГО: ПЛАН ДЕЙСТВИЙ                     ║
╚══════════════════════════════════════════════════════════════╝{RESET}
""")

    print(f"""  {RED}{BOLD}🔴 ВЫСОКИЙ ПРИОРИТЕТ (бизнес-критичные функции без UI):{RESET}
  1. Обслуживание печей (kiln-maintenance) — 9 эндпоинтов без интерфейса
  2. Календарь фабрики (factory-calendar) — влияет на расчёт сроков
  3. Инвентаризация (reconciliations) — точность остатков
  4. Склад готовой продукции (finished-goods) — учёт и отгрузка

  {YELLOW}{BOLD}🟡 СРЕДНИЙ ПРИОРИТЕТ (улучшения):{RESET}
  5. Аналитические отчёты (reports) — KPI для Owner/CEO
  6. Конструктор дашбордов (dashboard-access) — гибкость ролей
  7. Решения по перешлифовке (grinding) — PM decision UI
  8. Настройка эскалации (escalation rules) — Admin UI
  9. Настройка приёмки (receiving/defect thresholds) — Admin UI
  10. Настройка консолидации закупок — Purchaser/Admin UI

  {DIM}{BOLD}⚪ НИЗКИЙ ПРИОРИТЕТ (справочники/отложить):{RESET}
  11. Сроки сервисов (service lead times) — в Settings
  12. Расписание обжигов (kiln-firing-schedules) — дублирует Schedule
  13. Этапы производства (stages) — справочные данные
  14. ProcessStep/StandardWork — фича v2
  15. EdgeHeightRule — фича v2

  {RED}{BOLD}❌ ИСПРАВИТЬ:{RESET}
  16. Нет DELETE для users — нельзя деактивировать пользователей
  17. Нет DELETE для finished_goods — нельзя списать продукцию
  18. Нет DELETE для material_groups — нельзя удалить группу
""")

    # Write report to file
    report_path = ROOT / "docs" / "AUDIT_REPORT.md"
    write_markdown_report(report_path, backend_no_frontend, models_no_api, crud_issues, env_issues)
    print(f"  {GREEN}📄 Отчёт также сохранён в: {report_path}{RESET}")
    print()


def write_markdown_report(path, backend_items, model_items, crud_items, env_items):
    """Write the same report as Markdown file."""
    lines = [
        "# Moonjar PMS — Architecture Audit Report",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## A. Backend есть — Frontend нет",
        "",
        "| # | API | Название | Приоритет | Кому нужно | Статус |",
        "|---|-----|----------|-----------|------------|--------|",
    ]
    for i, item in enumerate(backend_items, 1):
        name = item["name"].split(" ", 1)[1] if " " in item["name"] else item["name"]
        lines.append(
            f"| {i} | `{item['api']}` | {name} | {item['priority']} | {item['who_needs']} | {item['status']} |"
        )

    lines += [
        "",
        "## B. Модели БД без API",
        "",
        "| Модель | Таблица | Категория | Действие |",
        "|--------|---------|-----------|----------|",
    ]
    for item in model_items:
        lines.append(
            f"| `{item['name']}` | `{item['table']}` | {item['category']} | {item['action']} |"
        )

    lines += [
        "",
        "## C. Неполный CRUD",
        "",
        "| Роутер | Проблема | Вердикт |",
        "|--------|----------|---------|",
    ]
    for item in crud_items:
        lines.append(f"| `{item['router']}` | {item['issue']} | {item['verdict']} |")

    lines += [
        "",
        "## D. Переменные окружения",
        "",
        "| Переменная | Описание | Действие |",
        "|-----------|----------|----------|",
    ]
    for var, desc, action in env_items:
        lines.append(f"| `{var}` | {desc} | {action} |")

    lines += [
        "",
        "## План действий",
        "",
        "### 🔴 Высокий приоритет",
        "1. Обслуживание печей (kiln-maintenance) — 9 эндпоинтов без интерфейса",
        "2. Календарь фабрики (factory-calendar) — влияет на расчёт сроков",
        "3. Инвентаризация (reconciliations) — точность остатков материалов",
        "4. Склад готовой продукции (finished-goods) — учёт и отгрузка",
        "",
        "### 🟡 Средний приоритет",
        "5. Аналитические отчёты (reports) — KPI для руководства",
        "6. Конструктор дашбордов (dashboard-access) — гибкость ролей",
        "7. Решения по перешлифовке (grinding) — PM decision UI",
        "8. Настройки эскалации, приёмки, консолидации — Admin UI",
        "",
        "### ⚪ Низкий приоритет",
        "9. Service lead times, kiln-firing-schedules, stages — справочники",
        "10. ProcessStep/StandardWork/EdgeHeightRule — v2 features",
        "",
        "### ❌ Исправить",
        "- Нет DELETE для users (деактивация)",
        "- Нет DELETE для finished_goods (списание)",
        "- Нет DELETE для material_groups",
    ]

    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
