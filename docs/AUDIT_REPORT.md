# Moonjar PMS — Architecture Audit Report
Generated: 2026-03-21 09:44

## A. Backend есть — Frontend нет

| # | API | Название | Приоритет | Кому нужно | Статус |
|---|-----|----------|-----------|------------|--------|
| 1 | `/api/kiln-maintenance` | Обслуживание печей (Kiln Maintenance) | ВЫСОКИЙ | Production Manager | Backend 100% → Frontend 0% |
| 2 | `/api/factory-calendar` | Календарь фабрики (Factory Calendar) | ВЫСОКИЙ | Admin / Production Manager | Backend 100% → Frontend 0% |
| 3 | `/api/reconciliations` | Инвентаризация (Reconciliations) | ВЫСОКИЙ | Warehouse / Production Manager | Backend 100% → Frontend 0% |
| 4 | `/api/finished-goods` | Склад готовой продукции (Finished Goods) | ВЫСОКИЙ | Warehouse / PM / Owner | Backend 100% → Frontend 0% |
| 5 | `/api/reports` | Аналитические отчёты (Reports) | СРЕДНИЙ | Owner / CEO / PM | Backend 100% → Frontend 0% |
| 6 | `/api/dashboard-access` | Конструктор дашбордов (Dashboard Access) | СРЕДНИЙ | Admin | Backend 100% → Frontend 0% |
| 7 | `/api/grinding-stock` | Решения по перешлифовке (Grinding Decisions) | СРЕДНИЙ | Production Manager | Backend 100% → Frontend ~30% (только просмотр) |
| 8 | `/api/settings/service-lead-times` | Сроки сервисов (Service Lead Times) | НИЗКИЙ | Admin | Backend 100% → Frontend 0% (страница Settings существует) |
| 9 | `/api/kiln-firing-schedules` | Расписание обжигов (Kiln Firing Schedules) | НИЗКИЙ | PM | Backend 100% → Frontend 0% |
| 10 | `/api/stages` | Производственные этапы (Stages) | НИЗКИЙ | Admin | Backend 100% → Frontend 0% |

## B. Модели БД без API

| Модель | Таблица | Категория | Действие |
|--------|---------|-----------|----------|
| `DailyTaskDistribution` | `daily_task_distributions` | ИСПОЛЬЗУЕТСЯ ВНУТРЕННЕ | Опционально: GET-эндпоинт для просмотра истории |
| `EscalationRule` | `escalation_rules` | ИСПОЛЬЗУЕТСЯ ВНУТРЕННЕ, НУЖЕН UI | НУЖЕН: Страница настройки эскалации в Admin |
| `ManaShipment` | `mana_shipments` | ИСПОЛЬЗУЕТСЯ ВНУТРЕННЕ, НУЖЕН UI | НУЖЕН: Раздел в Warehouse для управления отгрузками Mana |
| `MaterialDefectThreshold` | `material_defect_thresholds` | ИСПОЛЬЗУЕТСЯ ВНУТРЕННЕ, НУЖЕН UI | НУЖЕН: Настройка порогов в Admin → Materials |
| `PurchaseConsolidationSetting` | `purchase_consolidation_settings` | ИСПОЛЬЗУЕТСЯ ВНУТРЕННЕ, НУЖЕН UI | НУЖЕН: Раздел настроек в Purchaser или Admin |
| `ReceivingSetting` | `receiving_settings` | ИСПОЛЬЗУЕТСЯ ВНУТРЕННЕ, НУЖЕН UI | НУЖЕН: Переключатель в Admin → Settings (per factory) |
| `StageReconciliationLog` | `stage_reconciliation_logs` | ИСПОЛЬЗУЕТСЯ ВНУТРЕННЕ | Опционально: GET-эндпоинт для просмотра логов |
| `RagEmbedding` | `rag_embeddings` | ВНУТРЕННИЙ СЕРВИС | API не нужен |
| `KilnCalculationLog` | `kiln_calculation_logs` | НЕ ИСПОЛЬЗУЕТСЯ | Удалить или реализовать запись логов |
| `ProcessStep + StandardWork` | `process_steps / standard_work` | НЕ ИСПОЛЬЗУЕТСЯ | Отложить (фича v2) или удалить |
| `EdgeHeightRule` | `edge_height_rules` | НЕ ИСПОЛЬЗУЕТСЯ | Отложить (фича v2) или удалить |

## C. Неполный CRUD

| Роутер | Проблема | Вердикт |
|--------|----------|---------|
| `batches` | Батчи (загрузки в печь) нельзя удалить | ⚠️ Возможно ОК — батчи не должны удаляться |
| `finished_goods` | Готовую продукцию нельзя удалить из учёта | ❌ Нужен DELETE или PATCH для списания |
| `material_groups` | Группы материалов нельзя удалить | ❌ Нужен DELETE (с проверкой зависимостей) |
| `positions` | Позиции заказа нельзя удалить | ⚠️ Возможно ОК — позиции отменяются, не удаляются |
| `quality` | Проверки качества нельзя удалить | ⚠️ Возможно ОК — QC записи не должны удаляться |
| `tasks` | Задачи нельзя удалить | ⚠️ Возможно ОК — задачи закрываются, не удаляются |
| `tps` | TPS метрики нельзя удалить | ⚠️ Возможно ОК — метрики архивные |
| `users` | Пользователей нельзя удалить | ❌ Нужен DELETE или деактивация |

## D. Переменные окружения

| Переменная | Описание | Действие |
|-----------|----------|----------|
| `TELEGRAM_WEBHOOK_SECRET` | Секрет для webhook Telegram бота | Перенести в Settings |
| `INTERNAL_API_KEY` | Ключ для внутренних API-вызовов | Перенести в Settings |
| `UPLOADS_DIR` | Директория для загрузки файлов | Перенести в Settings |
| `RAILWAY_ENVIRONMENT` | Определение среды Railway | ОК — платформенная переменная |
| `RAILWAY_PUBLIC_DOMAIN` | Публичный домен Railway | ОК — платформенная переменная |
| `ENV` | Общая переменная среды | ОК — стандартная |

## План действий

### 🔴 Высокий приоритет
1. Обслуживание печей (kiln-maintenance) — 9 эндпоинтов без интерфейса
2. Календарь фабрики (factory-calendar) — влияет на расчёт сроков
3. Инвентаризация (reconciliations) — точность остатков материалов
4. Склад готовой продукции (finished-goods) — учёт и отгрузка

### 🟡 Средний приоритет
5. Аналитические отчёты (reports) — KPI для руководства
6. Конструктор дашбордов (dashboard-access) — гибкость ролей
7. Решения по перешлифовке (grinding) — PM decision UI
8. Настройки эскалации, приёмки, консолидации — Admin UI

### ⚪ Низкий приоритет
9. Service lead times, kiln-firing-schedules, stages — справочники
10. ProcessStep/StandardWork/EdgeHeightRule — v2 features

### ❌ Исправить
- Нет DELETE для users (деактивация)
- Нет DELETE для finished_goods (списание)
- Нет DELETE для material_groups