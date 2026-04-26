# Moonjar PMS — Complete Business Logic

> Auto-extracted from 50 service files in `business/services/`
> Generated: 2026-03-26

---

## Table of Contents

1. [Order Intake Pipeline](#1-order-intake-pipeline)
2. [Material Reservation & Consumption](#2-material-reservation--consumption)
3. [Stone Reservation System](#3-stone-reservation-system)
4. [Backward Scheduling (TOC/DBR)](#4-backward-scheduling-tocdbr)
5. [Batch Formation & Kiln Assignment](#5-batch-formation--kiln-assignment)
6. [Firing Profiles & Temperature Groups](#6-firing-profiles--temperature-groups)
7. [Status Machine & Transitions](#7-status-machine--transitions)
8. [Quality Control](#8-quality-control)
9. [Sorting / Splitting / Defect Routing](#9-sorting--splitting--defect-routing)
10. [Surplus Handling](#10-surplus-handling)
11. [Packaging Consumption](#11-packaging-consumption)
12. [Shipment Workflow](#12-shipment-workflow)
13. [Defect Coefficients](#13-defect-coefficients)
14. [Repair Monitoring](#14-repair-monitoring)
15. [Buffer Health (TOC)](#15-buffer-health-toc)
16. [Rotation Rules](#16-rotation-rules)
17. [Purchaser Lifecycle](#17-purchaser-lifecycle)
18. [Purchase Consolidation](#18-purchase-consolidation)
19. [Min Balance Auto-Calculation](#19-min-balance-auto-calculation)
20. [Service Blocking](#20-service-blocking)
21. [Escalation System](#21-escalation-system)
22. [Notifications](#22-notifications)
23. [Daily Task Distribution](#23-daily-task-distribution)
24. [Daily KPI & Analytics](#24-daily-kpi--analytics)
25. [TPS Metrics](#25-tps-metrics)
26. [Anomaly Detection](#26-anomaly-detection)
27. [Payroll Calculation](#27-payroll-calculation)
28. [Telegram Bot](#28-telegram-bot)
29. [Telegram AI](#29-telegram-ai)
30. [Telegram Callbacks](#30-telegram-callbacks)
31. [AI Chat Service](#31-ai-chat-service)
32. [Photo Analysis (AI Vision)](#32-photo-analysis-ai-vision)
33. [Photo Storage](#33-photo-storage)
34. [PDF Parser](#34-pdf-parser)
35. [Material Matcher (AI)](#35-material-matcher-ai)
36. [Surface Area Calculation](#36-surface-area-calculation)
37. [Glazing Board Calculator](#37-glazing-board-calculator)
38. [Size Resolution](#38-size-resolution)
39. [Kiln Breakdown Handling](#39-kiln-breakdown-handling)
40. [Order Cancellation](#40-order-cancellation)
41. [Change Request Processing](#41-change-request-processing)
42. [Schedule Estimation](#42-schedule-estimation)
43. [Reconciliation](#43-reconciliation)
44. [Warehouse Operations](#44-warehouse-operations)
45. [Webhook Sender](#45-webhook-sender)
46. [Partial Delivery](#46-partial-delivery)
47. [Defect Alert (5-Why)](#47-defect-alert-5-why)
48. [Master Achievement System](#48-master-achievement-system)
49. [Attendance Monitor](#49-attendance-monitor)
50. [Auto-Reorder](#50-auto-reorder)
51. [CEO Reports (Gamification)](#51-ceo-reports-gamification)
52. [Mini-Competitions Engine](#52-mini-competitions-engine)
53. [Factory Leaderboard](#53-factory-leaderboard)
54. [Material Substitution](#54-material-substitution)
55. [Payroll PDF Generator](#55-payroll-pdf-generator)
56. [Points System](#56-points-system)
57. [Prize Advisor](#57-prize-advisor)
58. [Production Split (Mid-Production)](#58-production-split-mid-production)
59. [Skill Badge System](#59-skill-badge-system)
60. [Staffing Optimizer](#60-staffing-optimizer)
61. [Streaks & Daily Challenges](#61-streaks--daily-challenges)
62. [TPS Auto-Calibration](#62-tps-auto-calibration)
63. [Transcription Logger](#63-transcription-logger)
64. [Typology Matcher](#64-typology-matcher)
65. [Weekly Summary](#65-weekly-summary)

---

## 1. Order Intake Pipeline

**File:** `order_intake.py` (~1210 lines)
**Called by:** `orders.router` (POST, confirm-pdf, reprocess), `integration.router` (webhook)

### Purpose
Processes incoming orders from 3 sources (Sales webhook, PDF upload, manual) into production-ready positions with scheduling.

### Key Functions

- `process_incoming_order(db, payload, source)` — Main entry point. Creates ProductionOrder + Items, then processes each item into OrderPosition.
- `assign_factory(db, client_location)` — Auto-assigns factory based on client location (served_locations JSONB).
- `process_order_item(db, order, item, factory_id)` — For each item: resolves recipe, size, shape; calculates surface area; applies defect coefficient; checks material availability; creates blocking tasks if needed; runs scheduling.
- `_find_recipe(db, item)` — Recipe matching: color_collection + color name match. Falls back to color_type='base' if custom not found. Handles exclusive/stencil/silk_screen variants.
- `check_blocking_tasks(db, position, item)` — Creates blocking tasks: STENCIL_ORDER, SILK_SCREEN_ORDER, COLOR_MATCHING, SIZE_RESOLUTION, CONSUMPTION_MEASUREMENT.
- `_check_consumption_rates(db, position, recipe)` — Verifies consumption rates exist for glaze/engobe. Creates task if missing.
- `_auto_detect_exclusive(db, position, item)` — Detects Exclusive collection (custom colors, no base restrictions).
- `_generate_order_number(db)` — Auto-generates sequential order number (MJ-00001).

### Business Rules
1. Webhook deduplication via `external_id` + `source` unique constraint.
2. Stock collection ("Сток") orders skip manufacturing — go straight to READY_FOR_SHIPMENT.
3. Defect coefficient adds extra pieces to `quantity_with_defect_margin`.
4. Position gets `planned_glazing_date`, `planned_kiln_date`, `planned_sorting_date`, `planned_completion_date` from scheduler.
5. Positions start in PLANNED status, or blocking status if recipe/materials/stencil/size missing.

---

## 2. Material Reservation & Consumption

**File:** `material_reservation.py` (~945 lines)
**Called by:** `positions.router` (status transition to SENT_TO_GLAZING), `status_machine.py`

### Purpose
Calculates material needs per position (from recipe BOM), reserves stock, and writes off on consumption. Handles smart availability checking with substitution suggestions.

### Key Functions

- `find_best_consumption_rule(db, position, recipe_type)` — Finds most specific matching ConsumptionRule by priority (more non-null match fields = higher priority).
- `reserve_materials_for_position(db, position_id)` — Reserves all BOM materials. Creates RESERVE transactions. Sets `reservation_at`. Blocks if insufficient.
- `force_reserve_materials(db, position_id)` — Force-reserve even if stock insufficient (for PM override).
- `unreserve_materials_for_position(db, position_id)` — Reverse all reservations (e.g., on cancellation).
- `check_material_availability_smart(db, position)` — Smart check: returns needs, availability, substitution suggestions, and purchase request recommendations.
- `create_auto_purchase_request(db, factory_id, missing_materials)` — Auto-creates purchase request for missing materials.
- `sync_material_procurement_task(db, position, shortages)` — Creates/updates/closes a blocking `MATERIAL_ORDER` task (non-stone). Called at the tail of `reserve_materials_for_position` on every reserve attempt. One task per position, covers all non-stone shortages. Closes itself (status=DONE) when stock catches up.
- `check_and_unblock_positions_after_receive(db, factory_id, material_id)` — After material receipt, checks if any INSUFFICIENT_MATERIALS positions can now be unblocked.

### Business Rules
1. Consumption rate lookup: ConsumptionRule > recipe.consumption_spray/brush > recipe_material rates.
2. Application method (spray/brush/splash/silk_screen) determines which rate to use.
3. Engobe is consumed separately from glaze (needs_engobe flag on ApplicationMethod).
4. Area calculation uses `glazeable_sqm` from position or recalculates via surface_area service.
5. Defect margin pieces are included in reservation.
6. **Untracked utilities** (`water`, `вода`) never count as deficit — they're infrastructure, always assumed unlimited. Skipped in reserve / deficit checks / UI requirements list. Match is case-insensitive on exact material name. See `_UNTRACKED_UTILITY_NAMES` in `material_reservation.py`.
7. **Blocking task lifecycle (single rule for all materials):**
   - Stone deficit → `STONE_PROCUREMENT` blocking task (one per position), created/updated in `stone_reservation.py`.
   - Any other material deficit (pigment, frit, bulk, etc.) → `MATERIAL_ORDER` blocking task (one per position, covers all non-stone items), created/updated in `material_reservation.py:sync_material_procurement_task`.
   - Both tasks get `due_at = today + lead_days` set automatically:
     - Stone: `supplier.default_lead_time_days` or **35 days** default.
     - Non-stone: `max(supplier.default_lead_time_days)` across shortages, per-type fallback (pigment=7, frit/oxide/other_bulk=14, …), ultimate fallback **14 days**.
   - `due_at` is **only pushed forward** by auto-recalc, never backwards — so a purchaser-entered precise ETA always wins.
   - When shortage disappears (materials received), the matching task auto-closes (`status=DONE`) on the next reserve attempt / recalc.
   - The scheduler reads `Task.due_at` via `_get_blocking_task_ready_date` → this becomes `material_ready_date` for that position, i.e. the planner won't start glazing before the deficit is expected to clear.

### Reservation: required side-effects (2026-04-25)

**`reserve_materials_for_position()` ОБЯЗАН**, в порядке:
1. Для каждого RecipeMaterial: `MaterialTransaction(type=RESERVE, qty=expected, position_id, material_id)`
2. Уменьшать "available" (через сумму активных RESERVE), НО `MaterialStock.balance` не трогать (balance = физический склад)
3. После полного успеха — выставить **`OrderPosition.reservation_at = now()`** (это маркер «зарезервировано»). Если хоть один материал упал — НЕ сетить, оставить `reservation_at = NULL`.
4. Идемпотентность: перед reserve вызвать `_release_existing_reserves(position)` — иначе повторные вызовы плодят фантомные резервы (см. commit `6aada32`).

### Consumption: required side-effects (2026-04-25)

**Триггер:** переход позиции в `ENGOBE_APPLIED` (камень физически взят, энгоб нанесён) — см. также §3 для stone consumption.

**`on_glazing_start()` ОБЯЗАН**, для каждого RecipeMaterial:
1. **Per-material try/except** — exception на одном материале НЕ должен убить весь loop. Failed materials логируются как ERROR с traceback'ом, остальные обрабатываются.
2. `MaterialTransaction(type=CONSUME, qty=actual, position_id, material_id)` — запись о фактическом расходе.
3. `MaterialTransaction(type=UNRESERVE, qty=expected, position_id, material_id)` — закрыть исходный резерв.
4. `MaterialStock.balance -= actual` — реальное уменьшение склада.
5. Если `actual ≠ expected` (отчёт мастера) — создать `ConsumptionAdjustment` для PM-ревью.
6. После цикла **обязательно**: `position.materials_written_off_at = now()` — даже если часть материалов failed (с полным error log'ом). Это маркер «consumption attempted».

**Если функция падает совсем** (catastrophic) — status_machine ловит exception но НЕ должен глотать как WARNING. Это ERROR с traceback'ом + позиция помечается флагом `consumption_failed_at` для последующего ручного backfill'а.

### Side-effects checklist для каждого статуса

Это чек-лист для проверки «формально или реально прошло»:

| Статус | Обязательные side-effects |
|---|---|
| `planned` | `reservation_at` set + RESERVE-транзакции для всех материалов рецепта + active StoneReservation |
| `engobe_applied` | `materials_written_off_at` set + CONSUME+UNRESERVE-транзакции + `MaterialStock.balance` уменьшен + StoneReservation.status='consumed' + CONSUME stone transaction |
| `glazed` | (если ещё не было consume на engobe — то же что для engobe_applied) + `glazed_at` timestamp |
| `loaded_in_kiln` | привязка к Batch (`batch_id` set) |
| `fired` | `fired_at` set; route_after_firing вызван |
| `transferred_to_sorting` | `transferred_at` set |
| `sorted` | `sorted_at` set; SortingResult записан |
| `packed` | **обязательно** через `/positions/{id}/pack` endpoint: PackingPhoto загружено, packaging materials consumed, packed_at set |
| `ready_for_shipment` | в составе ShipmentItem или alone-флаг |
| `shipped` | **обязательно** через `/shipments/{id}/ship` endpoint: ShipmentItem существует, материалы в shipped_at |

Прямой переход через `/positions/{id}/status` без сайд-эффектов = **формально прошло, содержательно НЕТ**. Это разрешено только в override-режиме (см. §X Status Machine vs Business Endpoints).

---

## 3. Stone Reservation System

**File:** `stone_reservation.py` (~438 lines)
**Called by:** `order_intake.py`, `positions.router`

### Purpose
Reserves raw stone (bisque) for positions based on size category and product type, applying stone defect rates.

### Key Functions

- `reserve_stone_for_position(db, position)` — Creates StoneReservation record. Calculates reserved_sqm with defect margin.
- `get_stone_defect_rate(db, factory_id, size_category, product_type)` — Gets defect rate from stone_defect_rates table. Default fallback.
- `reconcile_stone_after_firing(db, position)` — After firing, compares actual output vs reserved. Records adjustment.
- `get_weekly_stone_waste_report(db, factory_id)` — Weekly report: actual vs expected stone usage per size category.

### Business Rules
1. Size categories: "small" (<20x20), "medium" (20x30 to 30x30), "large" (>30x30).
2. Defect rate varies by size_category + product_type (tiles vs sinks).
3. Reserved qty = ordered_qty / (1 - defect_pct).

### Stone Consumption — required side-effects (2026-04-25)

**Триггер:** переход позиции в `ENGOBE_APPLIED` (камень физически взят со склада, на него нанесён энгоб — после этого он уже не вернётся в каталог).

**`consume_stone_for_position(position_id)` ОБЯЗАН:**
1. Найти `matching_stone` Material для этой позиции — через тот же matcher что в `_check_stone_stock_and_create_task` (size_id с shape guard, потом name substring).
2. Создать `MaterialTransaction(type=CONSUME, material_id=matching_stone.id, qty=position.quantity, position_id, factory_id)`.
3. Уменьшить `MaterialStock.balance` на `position.quantity` (для unit='pcs') или на `reserved_sqm` (для unit='m2').
4. Перевести **активный** `StoneReservation` для этой позиции в `status='consumed'`.
5. Если `matching_stone` не найден → НЕ падать, логировать ERROR + создать manual-task PM «не смогли списать камень для позиции X — проверь каталог».
6. Идемпотентность: если для позиции уже есть `MaterialTransaction(type=CONSUME)` для stone — не дублировать.

**Где вызывается:** `business/services/status_machine.py` при переходе в `ENGOBE_APPLIED` (рядом с уже существующим вызовом `on_glazing_start` для glaze materials).

**Почему именно `engobe_applied`, а не `loaded_in_kiln`:** камень физически взят и обработан энгобом — даже если потом обжиг не получится, камень уже потрачен. Списываем по факту физической работы, не по логистическому событию (загрузка в печь).

**Откат:** если позиция отменена ПОСЛЕ engobe_applied — `MaterialTransaction(type=CONSUME)` НЕ откатывается (камень реально потрачен). Это списание брака.

---

## 4. Forward / Left-Shift Scheduling with Stage Capacity

**File:** `business/services/production_scheduler.py`
**Called by:** `order_intake.py`, `api/routers/schedule.py`, `api/routers/kilns.py`, `business/services/pull_system.py`, нижний крон в `api/scheduler.py`

### Философия (обязательная, источник истины)

Расписание строится **вперёд во времени (forward / left-shift packing), а не назад от дедлайна**. Принцип:

> «Всё, что можно делать сегодня — делается сегодня. Всё, что завтра — завтра. И так далее.
>  При этом на каждый день ставим ровно столько работы, сколько смогут переварить бригады этого дня по каждой стадии, с учётом производительности и смен.»

Дедлайн — **только триггер алерта** (`_create_deadline_exceeded_alert`), **не** анкор расписания. Если по forward-пакингу позиция вылезает за дедлайн — выбрасываем алерт, но дату не подгоняем назад.

### Что сдвигает позицию вправо (hard-блокеры)

Для каждой позиции считается `earliest_start = max(...)` из:
1. `date.today()` — нельзя планировать в прошлое.
2. **Materials availability** — `_get_material_ready_date(pos)` (см. §2). Если материал не в наличии, берётся `expected_arrival_date` партии поставщика.
3. **Blocking tasks** — `_get_blocking_tasks_ready_date(pos)` для `AWAITING_RECIPE`, `AWAITING_STENCIL`, `COLOR_MATCHING`, `CONSUMPTION_DATA` и др. (см. §20 и `docs/BLOCKING_TASKS.md`). Берётся ETA поставщика.
4. **FIFO min_start_date** — предыдущие ордера (`ProductionOrder.created_at ASC` → `OrderPosition.priority_order` → `position_number`) должны быть уже распакованы в текущем проходе. Это даёт нижнюю границу.
5. **Factory calendar** — `_next_working_day_cal(db, factory_id, d)` пропускает воскресенья **и** записи `FactoryCalendar.is_working_day = false` (национальные, балийские, manual holidays).

После этого `earliest_start` — это «самый ранний день, когда позицию вообще можно начать». Дальше включается capacity packing.

### Daily capacity cap per stage

Для каждой стадии (`engobe`, `glazing`, `sorting`, `packing`, `edge_cleaning`, `qc_pre_kiln`, `qc_final`, `drying`, `unpacking`, …) — считается **пропускная способность дня** по формуле:

```
daily_cap = brigade_size × shift_count × shift_duration_hours × productivity_rate
```

Источники данных:
- `StageTypologySpeed` (`api/models.py::StageTypologySpeed`) — per (`factory_id`, `typology_id`, `stage`): `productivity_rate`, `rate_unit` (`pcs` / `sqm`), `rate_basis` (`per_person` / `per_brigade` / `fixed_duration`), `time_unit` (`min` / `hour` / `shift`), `shift_count`, `shift_duration_hours`, `brigade_size`. **Это первичный источник.**
- `ShiftAssignment` — если на день назначено другое число людей в бригаде (больничные, ротации), эффективная `brigade_size` берётся оттуда (`_get_effective_brigade_size`).
- `ProcessStep.duration_hours` — fallback, если по стадии нет `StageTypologySpeed`.
- Если и этого нет — стадия считается «1 рабочий день» (защитный fallback).

**Два режима работы стадии:**

| `rate_basis`      | Смысл                                                  | Как учитывается в packing                                                            |
|-------------------|--------------------------------------------------------|--------------------------------------------------------------------------------------|
| `per_person`      | Штук/м² в час/смену **на одного рабочего**             | `daily_cap = brigade × shifts × hours × rate` → capacity mode                        |
| `per_brigade`     | Штук/м² в час/смену **на всю бригаду**                 | `daily_cap = shifts × hours × rate` → capacity mode                                  |
| `fixed_duration`  | Стадия занимает N часов **блоком** (сушка, остывание) | Не ест capacity, просто блокирует `duration_days` дней                               |

### Алгоритм forward packing

`forward_pack_factory(db, factory_id)` — **единственный источник истины** для полного пересчёта. Шаги:

1. **Снимок загрузки**: для каждой стадии и каждой даты держим словарь `loaded[(stage, date)] = used_pcs_or_sqm`.
2. **Очередь позиций**: все активные (`PLANNED`, `IN_PRODUCTION`, `BLOCKED`) позиции сортируются по FIFO (`order.created_at` → `position.priority_order` NULLS LAST → `position_number`).
3. **Packing loop** по одной позиции:
   - `earliest = max(today, material_ready, blocking_ready, fifo_prev_end)`, пропустить до ближайшего рабочего дня (`_next_working_day_cal`).
   - Идём по стадиям в порядке `_PIPELINE_STAGES` (unpacking → engobe → drying → glazing → qc_pre_kiln → kiln → cooling → qc_final → edge_cleaning → sorting → packing).
   - Для каждой стадии — `CapInfo = _get_stage_daily_capacity_info(stage, typology)`. Если `mode='fixed_duration'` — занимаем `duration_days` подряд рабочих дней от `stage_start`. Если `mode='capacity'` — распределяем `total_qty` по дням, беря на каждый день `min(remaining, daily_cap - loaded[(stage, day)])`, переходя на следующий рабочий день пока `remaining > 0`. В `loaded` пишем занятую часть.
   - Между стадиями учитываются resource-constraint (`drying_rack`, `glazing_board`, `work_table` — через `_STAGE_RESOURCE_MAP`) и буферные часы.
   - **Kiln** — **отдельный constraint (drum)**, НЕ пакуется capacity-режимом. Для kiln вызывается `find_best_kiln_and_date(...)`, который подбирает печь по зонам (`get_zone_capacity`), temperature group, maintenance windows. `plan_kiln_batches(..., allow_deferral=False)` не откладывает kiln-дату ради наполнения батча, если мы в forward-режиме (иначе кэскадно сдвинет всё вниз).
4. **Запись**: для каждой позиции заполняется `stage_plan` (JSONB, 12-стадийная схема) с `start`, `end`, `days`, `qty_per_day`, `sqm_per_day` — visual spread по дням рендерится фронтом.
5. **Дедлайн-алерты**: если `planned_completion_date > deadline` — `_create_deadline_exceeded_alert(pos)`, но расписание НЕ меняем.
6. **Commit per order** (SAVEPOINT) — чтобы падение одной позиции не роняло всю пачку.

### Точки входа (все три должны идти через forward_pack_factory)

1. **Automatic** — `api/scheduler.py` ночной крон (2:00 WITA), + `business/services/pull_system.py` на `StageCompletedEvent`.
2. **Tablo drag-drop** — `api/routers/schedule.py::reorder_queue` пересчитывает `priority_order` и вызывает `forward_pack_factory`.
3. **Manual "Recalculate" button** — `POST /api/schedule/recalculate` → `forward_pack_factory`.

`schedule_position(db, pos)` остаётся для **единичной** позиции (создание ордера, split), но это приблизительное размещение без глобального capacity snapshot — полный пересчёт всё равно приходит ночью или по кнопке.

### Ключевые функции

- `forward_pack_factory(db, factory_id)` — полный пересчёт (**единственный источник истины**).
- `_next_working_day_cal(db, factory_id, d)` — пропускает воскресенья + `FactoryCalendar.is_working_day=false`.
- `_get_stage_daily_capacity_info(db, factory_id, stage, typology_id, pos)` — возвращает `CapInfo(mode, daily_cap, duration_days)`.
- `_get_effective_brigade_size(db, factory_id, stage, static)` — с учётом `ShiftAssignment`.
- `_get_stage_duration_days(db, factory_id, stage, sqm, pcs, pos)` — fallback через `ProcessStep`.
- `find_best_kiln_and_date(db, factory_id, target_date, pos, max_shift_days=14)` — подбор kiln по зонам.
- `plan_kiln_batches(db, factory_id, allow_deferral=True)` — группировка в батчи. **Forward scheduler вызывает с `allow_deferral=False`** — не откладываем kiln ради наполнения, сдвиг `≥60%` fill делает только ночной batch-former.
- `schedule_position(db, pos)` — приблизительное размещение одной позиции (создание/split).
- `reschedule_factory(db, factory_id)` — тонкий wrapper над `forward_pack_factory`.
- `reschedule_affected_by_kiln(db, kiln_id)` — при breakdown: zeroes out positions, calls `forward_pack_factory`.

### Инварианты (ломать запрещено)

1. `stage_plan` остаётся 12-стадийной схемой JSONB; мутация только через `dict(existing) + flag_modified(pos, 'stage_plan')` — см. commit `0f5b496`.
2. `priority_order`: `NULL` = FIFO-eligible, non-NULL = manual pin. FIFO chain = `order.created_at ASC → priority_order NULLS LAST → position_number`.
3. Material status на позиции (`reserved` / `insufficient` / `consumed` / `not_reserved`) не переписывается scheduler-ом — только §2/§3.
4. Kiln всегда проходит через `find_best_kiln_and_date` — никакого прямого присваивания.
5. Blocking tasks (§20) — scheduler читает, но не создаёт и не закрывает их.
6. Дедлайн → только алерт, **никогда** не сдвигает дату назад.
7. FactoryCalendar holidays — уважаем всегда, через `_next_working_day_cal`.
8. SAVEPOINT per order — падение одной позиции не роняет остальные.
9. `schedule_metadata` — логируем `left_shift_trace`, `capacity_trace`, `shifted_reason` для debug.
10. Никаких «быстро поправлю backward на forward без чтения §4» — см. project CLAUDE.md.

### Отображение графика: скрытие уже выполненных стадий (bug-fix 2026-04-25, commits 7bfeef6 + later sync)

**Правило:** **любой** UI view расписания (календарь Daily Production View, Plan vs Fact, любые будущие views) **не показывает** позицию на стадиях, которые она уже прошла по своему текущему статусу.

**Почему это важно.** `schedule_position` записывает в `stage_plan` даты для ВСЕХ 12 стадий, даже если позиция уже в `GLAZED` или `FIRED`. Если эти исторические записи разложить по UI 1:1 — пользователь видит «сегодня Unpack, завтра Engobe», хотя физически мастер уже прошёл эти этапы часы назад. Хуже того: разные views (календарь vs Plan vs Fact) могут показывать **противоречивые данные про одну и ту же позицию** на одну и ту же дату, если фильтр применён только в одном месте.

**Single source of truth:** маппинг и helper-функции живут в `business/services/stage_progress.py` (`STAGE_INDEX`, `STATUS_COMPLETED_STAGE_INDEX`, `position_completed_index()`, `stage_already_done()`). Любой views должен импортировать и применять `stage_already_done(pos, stage_key)` перед тем как класть позицию в выдачу.

**Применяется в:**
- `business/planning_engine/scheduler.py::generate_production_schedule` — Daily Production View calendar
- `api/routers/schedule.py::get_daily_plan` — Plan vs Fact daily tracking

**Маппинг status → пройденных стадий** (живёт в `stage_progress.py`):

Маппинг «какая стадия уже в прошлом для данного статуса» — `_STATUS_COMPLETED_STAGE_INDEX`:

| Статус позиции | Пройдено стадий (индекс) |
|---|---|
| `planned`, `insufficient_materials`, `awaiting_*` | 0 (ничего) |
| `engobe_applied` | 2 (unpacking + engobe) |
| `engobe_check`, `sent_to_glazing`, `awaiting_reglaze` | 3 |
| `glazed` | 4 (до glazing включительно) |
| `pre_kiln_check` | 6 (через edge_cleaning_loading) |
| `loaded_in_kiln`, `refire` | 7 |
| `fired` | 8 |
| `transferred_to_sorting` | 10 (через cooling + unloading) |
| `sorted`, `sent_to_quality_check`, `quality_check_done`, `blocked_by_qm` | 11 |
| `packed`, `ready_for_shipment`, `shipped`, `merged`, `cancelled` | 12 (всё) |

`_STAGE_INDEX` — каноничный порядок стадий: `unpacking_sorting=1, engobe=2, drying_engobe=3, glazing=4, drying_glaze=5, edge_cleaning_loading=6, kiln_loading=7, firing=8, cooling=9, unloading=10, sorting=11, packing=12`.

**Правило скрытия:** если `_STAGE_INDEX[stage] <= _STATUS_COMPLETED_STAGE_INDEX[position.status]` — позицию не добавляем в ячейку этого дня. Применяется и к `stage_plan` пути, и к legacy path (`planned_*_date` buckets), и к single-day событию `kiln_loading`.

**Что НЕ делает это правило:** оно не переписывает `stage_plan` в БД и не перепланирует даты. Это чисто UI-фильтр. Если позиция в `glazed` — `stage_plan['unpacking_sorting']` в БД всё ещё содержит историческую дату, но в календаре она не показывается.

**Идейная проверка:** когда позиция становится `shipped` (=12) — она в любом случае уже в `_TERMINAL_STATUSES` и отфильтровывается на входе `generate_production_schedule`, поэтому индекс 12 в маппинге — для симметрии, а не для боевой логики.

### Триггеры пересчёта расписания

Помимо ночного крон-задания и ручной кнопки, расписание фабрики обязано пересчитываться **в реальном времени** в ответ на следующие события — иначе календарь рассинхронизируется с фактом:

| Триггер | Когда срабатывает | Реализация |
|---|---|---|
| **Position status change** | мастер отметил «нанесён ангоб», «загружена в печь» и т. д. | `api/schedule_triggers.py::_collect_status_changes` слушает `OrderPosition.status` через SQLAlchemy `after_flush`, дебаунсит по `factory_id` и зовёт `reschedule_factory(fid)` через `after_commit` в фоновом потоке. |
| **Cron** | каждую ночь в 02:00 WITA | `api/scheduler.py` — APScheduler. Ловит drift, который не попал в event-driven путь. |
| **Manual recalc** | кнопка PM, drag-n-drop в Tablo, force-unblock | `POST /api/schedule/recalculate`, `POST /api/schedule/reorder-queue`, `POST /api/schedule/backfill-procurement-tasks`. |
| **Material received** | приход партии материала на склад → `MaterialTransaction(type=RECEIVE)` | `api/schedule_triggers.py::_collect_material_receipts` — тот же паттерн, что и для статусов. Важно: позиции, висящие в `INSUFFICIENT_MATERIALS`, могут разблокироваться сразу после прихода — без триггера они оставались бы заблокированными до утреннего крона. |

**Инвариант:** все триггеры должны проходить через единственную точку — `_trigger_reschedule(session)`, привязанную к `after_commit`, чтобы пересчёт фабрики происходил **один раз** на коммит независимо от того, сколько событий накопилось (статусы + приходы материалов в одной транзакции — один пересчёт).

### Параллельные стадии (pipeline overlap) — ТРЕБУЕТ РЕАЛИЗАЦИИ

**Статус:** задокументировано как правило, реализация идёт отдельным коммитом (bug #2).

**Проблема.** Текущий `_add_stage()` в `production_scheduler.py:2316` ставит каждую следующую стадию строго после окончания предыдущей:
```python
cursor = _add_stage("unpacking_sorting", cursor, 1)  # Apr 24
cursor = _add_stage("engobe",           cursor, 1)  # Apr 25
cursor = _add_stage("drying_engobe",    cursor, 1)  # Apr 27 (26 — Вс)
cursor = _add_stage("glazing",          cursor, 1)  # Apr 28
```

Итого для партии 162 шт — **4 рабочих дня**. На реальном производстве команда из 3 человек делает все эти стадии **внахлёст**:
- Worker 1 распаковывает и выкладывает на доски.
- Как только 1-2 доски готовы (~15 минут) — Worker 2 начинает наносить энгоб.
- Worker 3 подключает компрессор, готовит линию, работает параллельно с Worker 2.
- Пока один ангобит, другой уже выкладывает следующую партию, третий сушит/глазурит первые.

Итоговая длительность цепочки 4 стадий = **0.5–1 день**, не 4.

**Правило:** стадии выполняются **pipeline-стилем с перекрытием**. Стадия N+1 может начинаться, когда стадия N выполнена на `(1 − overlap_ratio) × 100%`.

**Коэффициенты перекрытия по умолчанию:**

| Переход между стадиями | `overlap_ratio` | Обоснование |
|---|---|---|
| `unpacking_sorting → engobe` | **0.8** | Параллельная работа разных workers по партии |
| `engobe → drying_engobe` | **0.0** (full serial) | Сушка — естественный процесс, идёт от таймера, не от работы |
| `drying_engobe → glazing` | **0.8** | Как только часть высохла — можно глазурить |
| `glazing → drying_glaze` | **0.0** (full serial) | Та же физика сушки |
| `drying_glaze → edge_cleaning_loading` | **0.8** | Обработка кромок — параллельно по мере сушки |
| `edge_cleaning_loading → kiln_loading` | **0.0** (full serial) | Печь — дискретное событие, ждёт полной партии |
| `firing → cooling` | **0.0** (full serial) | Остывание — физический процесс |
| `cooling → unloading` | **0.0** (full serial) | Разгрузка — после остывания |
| `unloading → sorting` | **0.8** | Параллельная сортировка по мере разгрузки |
| `sorting → packing` | **0.8** | Параллельная упаковка |

**Правило перекрытия описано в таблице `StageOverlapRule` (создаётся миграцией)**, настраивается на уровне фабрики. Если записи нет — используются дефолты из таблицы выше.

**Формула:**
```
stage_N+1_start = stage_N_start + stage_N_duration × (1 − overlap_ratio)
```
С округлением вверх до рабочего дня (минимум +0 дней если перекрытие высокое).

**Важные инварианты:**
- **Drying-стадии остаются полностью последовательными** (`overlap = 0`) — мы не можем физически начать glazing пока ангоб не высох.
- **Kiln — всегда serial** — печь как drum (§5, §6), не pipeline.
- **Firing/Cooling — full serial** — физическая невозможность.
- **При `overlap = 0`** поведение полностью совпадает со старым (backward compat).

**Где реализовать:**
- `business/services/production_scheduler.py` — изменить сигнатуру `_add_stage` или обёртку поверх.
- Конфиг overlap — прочитать `StageOverlapRule` или таблицу-дефолт в коде.
- `stage_plan` в БД — сохраняем `start/end` с учётом пересечения (чтобы UI показывал корректно).
- UI `DailyProductionView` — уже работает корректно с пересекающимися диапазонами (позиция появится в двух stage-бейджах на один день — это правильно).

---

## 5. Batch Formation & Kiln Assignment

**File:** `batch_formation.py` (~1446 lines) — LARGEST service file
**Called by:** `batches.router` (auto-form, capacity-preview, confirm, reject)

### Purpose
Groups ready-for-kiln positions into batches, assigns kilns, calculates loading plans, handles co-firing restrictions.

### Key Functions

- `suggest_or_create_batches(db, factory_id)` — Main batch formation. Groups positions by temperature group, finds best kilns, creates Batch + assigns positions.
- `_find_best_kiln_for_batch(db, positions, factory_id)` — Selects kiln: matches temperature group, checks rotation compliance, calculates fill percentage.
- `_calculate_position_loading(db, position, kiln)` — Calculates how many pieces of this position fit on each level.
- `_build_loading_plan(db, batch)` — Builds multi-level loading plan (which positions go on which level, how many pieces per level).
- `preview_position_in_kiln(db, positions, kiln_id)` — Preview how positions would load into a specific kiln (without creating batch).
- `pm_confirm_batch(db, batch_id, pm_user_id)` — PM confirms suggested batch. Transitions SUGGESTED -> PLANNED. Assigns firing profile.
- `pm_reject_batch(db, batch_id, pm_user_id)` — PM rejects batch. Releases positions.
- `start_batch(db, batch_id)` — Start firing. Batch -> IN_PROGRESS.
- `complete_batch(db, batch_id)` — Complete firing. Batch -> DONE. Positions -> FIRED.
- `assign_batch_firing_profile(db, batch_id)` — Auto-matches firing profile from temperature group + product attributes.

### Business Rules
1. Co-firing: positions with different temperatures/glazes can share a kiln only if temperature group allows.
2. Two-stage firing (Gold): first batch fires base, second batch fires gold layer.
3. Raku kiln: separate handling, smaller capacity (60x100 cm).
4. Loading levels: multi-level kilns (shelves). Thicker tiles on bottom, thinner on top.
5. Filler tiles: if kiln not 100% full, system suggests filler positions from PLANNED pool.
6. Batch modes: AUTO (system decides everything), HYBRID (system suggests, PM confirms).

---

## 6. Firing Profiles & Temperature Groups

**File:** `firing_profiles.py` (~188 lines)
**Called by:** `batch_formation.py`, `firing_profiles.router`

### Purpose
Matches positions to firing profiles (temperature curves) based on product attributes. Manages temperature group -> recipe associations.

### Key Functions

- `match_firing_profile(db, product_type, collection, thickness_mm, temperature_group_id)` — Finds best firing profile by match_priority.
- `get_batch_firing_profile(db, batch)` — Auto-select firing profile for a batch based on majority temperature group.
- `get_total_firing_rounds(db, recipe_id)` — Returns number of firing rounds (1 for normal, 2 for gold).
- `group_positions_by_temperature(db, positions)` — Groups positions into temperature-compatible groups.

---

## 7. Status Machine & Transitions

**File:** `status_machine.py` (~519 lines)
**Called by:** `positions.router` (status transitions)

### Purpose
Validates and executes position status transitions. Each transition triggers specific business logic.

### Key Functions

- `validate_status_transition(current, new)` — Checks if transition is allowed per state machine.
- `get_allowed_transitions(current)` — Returns list of valid next statuses.
- `transition_position_status(db, position, new_status, user_id, extra_data)` — Executes transition with side effects:
  - PLANNED -> SENT_TO_GLAZING: reserves materials (glaze + engobe + stone).
  - SENT_TO_GLAZING -> GLAZED: consumes glaze materials.
  - GLAZED -> PRE_KILN_CHECK: triggers pre-kiln QC.
  - PRE_KILN_CHECK -> LOADED_IN_KILN: position enters kiln batch.
  - LOADED_IN_KILN -> FIRED: batch completion.
  - FIRED -> TRANSFERRED_TO_SORTING: moves to sorting area.
  - TRANSFERRED_TO_SORTING -> PACKED: packing completed.
  - PACKED -> READY_FOR_SHIPMENT: ready for pickup.
  - Various -> BLOCKED_BY_QM: QM blocks production.
- `route_after_firing(db, position)` — Determines next status after firing: TRANSFERRED_TO_SORTING (normal), REFIRE, or AWAITING_REGLAZE.

### Status Transitions (26 statuses)
```
PLANNED -> INSUFFICIENT_MATERIALS | AWAITING_* | SENT_TO_GLAZING
SENT_TO_GLAZING -> ENGOBE_APPLIED -> GLAZED
GLAZED -> PRE_KILN_CHECK -> LOADED_IN_KILN
LOADED_IN_KILN -> FIRED
FIRED -> TRANSFERRED_TO_SORTING | REFIRE | AWAITING_REGLAZE
TRANSFERRED_TO_SORTING -> PACKED | SENT_TO_QUALITY_CHECK
PACKED -> READY_FOR_SHIPMENT
READY_FOR_SHIPMENT -> SHIPPED
Any -> BLOCKED_BY_QM | CANCELLED
```

---

## 8. Quality Control

**File:** `quality_control.py` (~430 lines)
**Called by:** `quality.router`, `status_machine.py`

### Purpose
Manages QC assignment percentages, defect detection responses, and QM production blocks.

### Key Functions

- `assign_qc_checks(db, factory_id, positions, stage)` — Randomly selects positions for QC based on `current_percentage` from quality_assignment_config.
- `on_qc_defect_found(db, check, defect_count)` — When defect found: increases inspection %, creates 5-why task, notifies QM.
- `_increase_inspection_percentage(db, factory_id, stage)` — Increases QC sampling rate after defect. Caps at 100%.
- `qm_block_production(db, block_data)` — QM blocks position/batch. Creates QmBlock record, sets position to BLOCKED_BY_QM.
- `qm_unblock_production(db, block_id, resolution)` — QM unblocks. Restores previous status.

### Business Rules
1. Base QC percentage: 2% of positions per stage.
2. On defect: percentage increases by `increase_on_defect_percentage` (default 2%).
3. Percentage decreases back to base after 7 consecutive defect-free shifts.

---

## 9. Sorting / Splitting / Defect Routing

**File:** `sorting_split.py` (~742 lines)
**Called by:** `positions.router` (split endpoint)

### Purpose
Handles post-firing sorting: splits positions into sub-positions based on outcome (good, defect, write-off, repair, refire, reglaze, grinding, mana).

### Key Functions

- `process_sorting_split(db, position_id, split_data)` — Main sorting entry point. Creates sub-positions for each outcome bucket.
- `create_sub_position(db, parent, category, quantity, ...)` — Creates child OrderPosition linked to parent via parent_position_id.
- `route_to_mana(db, position, quantity)` — Routes defective tiles to Mana showroom. Creates ManaShipment.
- `add_to_grinding_stock(db, position, count)` — Adds defective tiles to grinding stock for re-use.
- `handle_surplus(db, position, surplus_quantity)` — Handles surplus production (more good tiles than ordered).
- `merge_position_back(db, child_position_id)` — Merges child back into parent (e.g., after repair completes).

### Defect Outcome Routing
| Outcome | Action |
|---------|--------|
| GOOD | Sub-position -> PACKED |
| WRITE_OFF | Sub-position -> CANCELLED, stock adjustment |
| REPAIR | Sub-position -> repair_queue, REPAIR status |
| REFIRE | Sub-position -> batch queue for 2nd firing |
| REGLAZE | Sub-position -> AWAITING_REGLAZE |
| GRINDING | -> grinding_stock |
| TO_MANA | -> ManaShipment |
| TO_STOCK | -> finished_goods_stock |

### Sort → Pack separation (SORTED status)

Sorting and packing are distinct steps; the post-fire lifecycle runs:

```
TRANSFERRED_TO_SORTING → (Split wizard) → SORTED → (Pack action) → PACKED → (Send to QC) → SENT_TO_QUALITY_CHECK
```

- **Split** only distributes tiles into categories (good / refire / repair / color_mismatch / grinding / write_off). Parent becomes `SORTED`. **Packaging is NOT consumed at this step.**
- **Pack** (`POST /positions/{id}/pack`) is the point where packaging materials are deducted and the position becomes `PACKED`. The endpoint enforces three hard gates — fail any of them and the position stays `SORTED`:
  1. **Photo required** — at least one `OrderPackingPhoto` must be attached. Returns 400 with "Photo required before packing".
  2. **Packaging rules configured** — `calculate_packaging_needs()` must return a non-empty materials list for the position's size. If absent, the `on_sorting_start` hook already filed a `PACKING_MATERIALS_NEEDED` blocking task for PM; the endpoint returns 400 referencing the size that needs rules.
  3. **Packaging stock sufficient** — `consume_packaging()` must succeed. Propagates the underlying exception as 400 so sorter sees why.
- **Send to QC** (`changeStatus → sent_to_quality_check`) is only reachable from `PACKED`.

**UI consequences:** the Sorter dashboard's Pak tile lists both `SORTED` and `PACKED` positions. Each card renders differently:
- `SORTED` → photo uploader + amber "📦 Pak sekarang" button (disabled until photo uploaded). On failure the backend's error is shown in-card as a red blocker banner referring the sorter to PM.
- `PACKED` → green "✨ Kirim ke QC" button.

**Why this matters:** packaging rule / stock problems used to be warning-logged at Split time and silently swallowed — the position moved to `PACKED` regardless. Now they are real blockers: sorter can't mark a box "packed" if the system has no way to account for its boxes or spacers.

---

### Split Quantity Validation (partial sort & surplus tolerance)

The split endpoint (`POST /positions/{id}/split`) accepts `total = good + refire + repair + color_mismatch + grinding + write_off` and compares to `position.quantity` (tiles physically loaded into kiln):

| Case | Rule | Behavior |
|------|------|----------|
| `total == qty` | Normal | Parent → PACKED with good qty; defect sub-positions created per category. |
| `total < qty` | **Partial sort** | Create a residual sub-position with `status=TRANSFERRED_TO_SORTING, quantity=qty-total`. Sorter can finish the remainder later (next day). Frontend shows a confirmation dialog explaining the carry-over. |
| `total > qty`, overflow `≤ 10%` | **Surplus production** | Kiln overages are valid (≤10% of loaded qty). Accept the split as-is; log at INFO level. Surplus vs *ordered* qty still gets routed downstream by `handle_surplus()` (showroom / coaster box / mana). |
| `total > qty`, overflow `> 10%` | **Reject** | Return 400: physically impossible or miscounted. Sorter must recount. |

**Why 10% ceiling:** production margin buffer is typically 3% of ordered qty, capped at +30 tiles (see manager task generation). Sorter-observed overages above 10% signal either a counting error or a process problem that needs investigation — system refuses to silently absorb them.

**UI alignment (sorter dashboard):** the same rules are mirrored in `SorterPackerDashboard.tsx` as four distinct submit modes (`ok` / `partial` / `surplus` / `block_overflow`) with matching status banner colors (emerald / amber / orange / red) and a confirmation dialog for non-OK modes. Manual input is never silently capped — if the user types a number that makes the total invalid, the UI shows the error and blocks submit until they fix it.

---

## 10. Surplus Handling

**File:** `surplus_handling.py` (~211 lines)
**Called by:** `sorting_split.py`, `defects.router`

### Purpose
Handles surplus tiles (production > ordered quantity). Auto-assigns surplus to matching pending orders or sends to stock/mana.

### Key Functions

- `auto_assign_surplus_disposition(db, factory_id)` — Scans surplus, tries to match with pending orders of same color+size.
- `process_surplus_batch(db, dispositions)` — Processes batch of surplus assignments.
- `get_surplus_summary(db, factory_id)` — Dashboard summary of surplus by color/size.

### Business Rules
1. Base colors -> stock (ready for any future order).
2. Custom colors -> check for matching pending orders. If none, -> Mana showroom.
3. Auto-assignment prioritizes orders with earliest deadline.

---

## 11. Packaging Consumption

**File:** `packaging_consumption.py` (~182 lines)
**Called by:** `status_machine.py` (transition to PACKED)

### Purpose
Calculates and reserves/consumes packaging materials (boxes + spacers) per position.

### Key Functions

- `calculate_packaging_needs(db, position)` — Returns box count, spacer count per material.
- `reserve_packaging(db, position)` — Reserves packaging materials.
- `consume_packaging(db, position)` — Writes off packaging materials on packing.

### Business Rules
1. Box type selected by tile size (from packaging_box_capacities).
2. Spacers per box from packaging_spacer_rules.
3. Boxes = ceil(quantity / pieces_per_box).

---

## 12. Shipment Workflow

**File:** (handled in `shipments.router` + `status_machine.py`)

Shipment creation -> add items (positions) -> ship (update tracking) -> deliver.
Each shipped position transitions to SHIPPED status. Order status auto-updates when all positions shipped.

---

## 13. Defect Coefficients

**File:** `defect_coefficient.py` (~237 lines)
**Called by:** `order_intake.py`, `positions.router`

### Purpose
Maintains rolling defect coefficients per stone type/supplier/factory. Used to add margin pieces to production orders.

### Key Functions

- `update_stone_defect_coefficient(db, factory_id)` — Recalculates coefficient from recent defect_records (rolling 30-day window).
- `get_stone_defect_coefficient(db, factory_id, stone_type)` — Returns coefficient (0.0 - 1.0). Default 0 if insufficient data.
- `calculate_production_quantity_with_defects(db, position)` — Returns `quantity_with_defect_margin = quantity / (1 - defect_coeff)`.
- `record_actual_defect_and_check_threshold(db, record)` — Records defect, checks if coefficient exceeds threshold, alerts PM.

---

## 14. Repair Monitoring

**File:** `repair_monitoring.py` (~498 lines)
**Called by:** `sorting_split.py`, background scheduler

### Purpose
Tracks repair SLA (turnaround time), escalates overdue repairs, maintains repair queue.

### Key Functions

- `check_repair_sla(db, factory_id)` — Checks all in-repair items against SLA thresholds. Creates escalation tasks.
- `create_repair_queue_entry(db, position, defect_type, quantity)` — Adds to repair queue with calculated priority.
- `get_repair_queue(db, factory_id)` — Returns prioritized repair queue.

### Business Rules
1. SLA: 3 working days for standard repairs, 1 day for rush.
2. Escalation: PM at SLA breach, CEO at 2x SLA, owner at 3x SLA.

---

## 15. Buffer Health (TOC)

**File:** `buffer_health.py` (~161 lines)
**Called by:** `analytics.router`, `toc.router`

### Purpose
Monitors TOC buffer zone before the constraint (kiln). Green/Yellow/Red health indicators.

### Key Functions

- `calculate_buffer_health(db, factory_id)` — Returns buffer metrics: positions waiting, sqm waiting, health color.
- `apply_rope_limit(db, factory_id, positions)` — Enforces rope limit (max positions released per day).

### Business Rules
1. Green: buffer 67-100% of target. Yellow: 33-67%. Red: 0-33%.
2. Red buffer triggers alert to PM.
3. Rope limit prevents WIP explosion before constraint.

---

## 16. Rotation Rules

**File:** `rotation_rules.py` (~239 lines)
**Called by:** `batch_formation.py`, `kilns.router`

### Purpose
Ensures kiln fires glazes in correct sequence (prevent cross-contamination between incompatible glazes).

### Key Functions

- `check_rotation_compliance(db, kiln_id, glaze_type)` — Checks if firing this glaze type after the last batch complies with rotation rules.
- `get_next_recommended_glaze(db, kiln_id)` — Returns next recommended glaze type based on rotation sequence.
- `validate_batch_rotation(db, batch)` — Validates batch composition against kiln rotation rules.

---

## 17. Purchaser Lifecycle

**File:** `purchaser_lifecycle.py` (~431 lines)
**Called by:** `purchaser.router`, `warehouse.py`

### Purpose
Full purchase request lifecycle: approve -> send to supplier -> track -> receive -> update lead times.

### Key Functions

- `on_material_received(db, pr, received_data)` — Processes material receipt. Updates stock, calculates actual lead time, notifies PM.
- `update_supplier_lead_time(db, supplier_id, material_type, actual_days)` — Rolling average of actual vs expected lead time.
- `check_and_notify_overdue(db)` — Background job: finds overdue PRs, sends alerts.
- `compute_enhanced_stats(db, factory_id)` — Dashboard stats: pending count, overdue count, avg lead time, spend.

### Business Rules
1. PR status flow: PENDING -> APPROVED -> SENT -> IN_TRANSIT -> RECEIVED -> CLOSED.
2. Partial receipt: updates remaining quantity, keeps PR in PARTIALLY_RECEIVED.
3. Lead time tracking: maintains rolling average over last 10 deliveries per supplier+material_type.

---

## 18. Purchase Consolidation

**File:** `purchase_consolidation.py` (~296 lines)
**Called by:** `purchaser.router`, background scheduler

### Purpose
Groups small purchase requests to same supplier into consolidated orders for better pricing.

### Key Functions

- `find_consolidation_candidates(db, factory_id)` — Finds PRs within consolidation window that can be merged.
- `consolidate_purchase_requests(db, pr_ids)` — Merges multiple PRs into one. Sums quantities.
- `auto_consolidate_on_schedule(db, factory_id)` — Background job: runs consolidation weekly.

### Business Rules
1. Consolidation window: 7 days (configurable per factory).
2. Only PENDING/APPROVED PRs can be consolidated.
3. Same supplier required.

---

## 19. Min Balance Auto-Calculation

**File:** `min_balance.py` (~175 lines)

### Purpose
Auto-calculates recommended minimum balance for materials based on consumption rate + lead time.

### Key Functions

- `get_effective_lead_time(db, material_id, factory_id)` — Returns actual lead time (from supplier_lead_times) or default.
- `recalculate_min_balance_recommendations(db, factory_id)` — For each material: min_balance_recommended = avg_daily_consumption * lead_time_days * safety_factor.
- `pm_override_min_balance(db, material_id, factory_id, new_value)` — PM manually overrides min_balance (disables auto-mode).

---

## 20. Service Blocking

**File:** `service_blocking.py` (~351 lines)
**Called by:** `order_intake.py`, `status_machine.py`

### Purpose
Blocks positions that require external services (stencil making, silk screen ordering, color matching) before production can start.

### Key Functions

- `should_block_for_service(db, position)` — Determines if position needs service blocking.
- `block_position_for_service(db, position, service_type)` — Creates blocking task, sets appropriate AWAITING_* status.
- `unblock_position_service(db, position)` — When task completed, transitions position to next status.
- `check_pending_service_blocks(db, factory_id)` — Background: checks if any blocked positions can be unblocked.

### Service Types
| Service | Blocking Status | Task Type |
|---------|----------------|-----------|
| Stencil | AWAITING_STENCIL_SILKSCREEN | STENCIL_ORDER |
| Silk Screen | AWAITING_STENCIL_SILKSCREEN | SILK_SCREEN_ORDER |
| Color Match | AWAITING_COLOR_MATCHING | COLOR_MATCHING |
| Size | AWAITING_SIZE_CONFIRMATION | SIZE_RESOLUTION |
| Consumption | AWAITING_CONSUMPTION_DATA | CONSUMPTION_MEASUREMENT |

---

## 21. Escalation System

**File:** `escalation.py` (~293 lines)
**Called by:** background scheduler

### Purpose
Time-based escalation of unresolved tasks: PM -> CEO -> Owner, with night-time deferral.

### Key Functions

- `check_and_escalate(db, factory_id)` — Main escalation loop. For each open task, checks timeout thresholds, sends escalation notifications.
- `is_night_time(utc_now)` — 21:00 - 06:00 local time is "night". Level 1 = defer to morning.
- `get_deferred_morning_alerts(db, factory_id)` — Returns tasks deferred from overnight for morning push.

### Business Rules
1. Escalation levels: 1 = PM, 2 = CEO, 3 = Owner.
2. Timeouts configurable per task_type per factory (escalation_rules table).
3. Night alerts: Level 1 = defer, Level 2 = repeat, Level 3 = phone call.

---

## 22. Notifications

**File:** `notifications.py` (~332 lines)
**Called by:** all services that need to notify users

### Purpose
Multi-channel notification system: in-app, WebSocket push, Telegram.

### Key Functions

- `create_notification(db, user_id, type, title, message, ...)` — Creates in-app notification, pushes via WebSocket and Telegram.
- `notify_pm(db, factory_id, type, title, message)` — Notifies all PMs for a factory.
- `notify_role(db, factory_id, role, type, title, message)` — Notifies all users with specific role.
- `send_telegram_message(chat_id, text)` — Sends Telegram message via Bot API.
- `send_telegram_message_with_buttons(chat_id, text, buttons)` — Sends message with inline keyboard buttons.

---

## 23. Daily Task Distribution

**File:** `daily_distribution.py` (~1021 lines)
**Called by:** background scheduler (21:00 daily), `telegram.router`

### Purpose
Generates daily task distribution for factory masters: glazing tasks, kiln loading plan, glaze recipes, KPI summary. Sent to Telegram group.

### Key Functions

- `daily_task_distribution(db, factory_id)` — Master function: collects all data for tomorrow.
- `_collect_glazing_tasks(db, factory_id, target_date)` — Positions scheduled for glazing tomorrow with recipe details + board specs.
- `_collect_kiln_loading(db, factory_id, target_date)` — Batches scheduled for loading tomorrow.
- `_collect_urgent_alerts(db, factory_id)` — Low stock, overdue tasks, SLA breaches.
- `_compute_kpi_yesterday(db, factory_id)` — Yesterday's metrics: fired count, defect rate, on-time rate.
- `format_daily_message(distribution, language)` — Formats as Telegram message in ID/EN/RU.

### Message Content
- Glazing tasks with positions, recipe, glaze quantity (kg), board count
- Kiln loading plan per kiln
- Glaze recipes needed (materials list)
- Urgent alerts
- Yesterday's KPI

---

## 24. Daily KPI & Analytics

**File:** `daily_kpi.py` (~477 lines)
**Called by:** `analytics.router`

### Purpose
Dashboard KPI calculations: on-time rate, defect rate, kiln utilization, production metrics.

### Key Functions

- `calculate_dashboard_summary(db, factory_id)` — Top-level KPI: orders count, on-time %, defect %, kiln utilization.
- `calculate_on_time_rate(db, factory_id)` — Positions completed on or before planned_completion_date.
- `calculate_defect_rate(db, factory_id)` — Defective pieces / total pieces over period.
- `calculate_kiln_utilization(db, factory_id)` — Actual loaded sqm / capacity sqm per kiln.
- `calculate_production_metrics(db, factory_id)` — Detailed metrics by production stage.
- `calculate_factory_comparison(db)` — Cross-factory comparison (owner dashboard).
- `calculate_trend_data(db, factory_id, metric, period)` — Time-series for trend charts.
- `get_activity_feed(db, factory_id)` — Recent events (order created, batch fired, defect found).

---

## 25. TPS Metrics

**File:** `tps_metrics.py` (~258 lines)
**Called by:** `tps.router`

### Purpose
Toyota Production System metrics: OEE, takt time, cycle time, throughput per shift/stage.

### Key Functions

- `collect_shift_metrics(db, factory_id, shift_date)` — Collects actual output per stage per shift.
- `record_shift_metric(db, data)` — Records TpsShiftMetric with deviation analysis.
- `evaluate_signal(db, factory_id)` — Returns current production signal (GREEN/YELLOW/RED) based on deviation from targets.

---

## 26. Anomaly Detection

**File:** `anomaly_detection.py` (~731 lines)
**Called by:** `analytics.router`, background scheduler

### Purpose
Statistical anomaly detection using Z-score on rolling windows.

### Key Functions

- `detect_defect_anomalies(db, factory_id)` — Spike in defect rates above 2-sigma.
- `detect_throughput_anomalies(db, factory_id)` — Sudden drops in stage output.
- `detect_cycle_time_anomalies(db, factory_id)` — Positions taking unusually long.
- `detect_material_consumption_anomalies(db, factory_id)` — Usage significantly above BOM.
- `detect_kiln_anomalies(db, factory_id)` — Unusual temperature profiles, batch failures.
- `run_all_anomaly_checks(db, factory_id)` — Runs all 5 checks, returns list of Anomaly objects.

---

## 27. Payroll Calculation

**File:** `payroll.py` (~229 lines)
**Called by:** `employees.router` (payroll-summary)

### Purpose
Indonesian payroll calculation: base salary, allowances, BPJS contributions, PPh21 tax, overtime.

### Key Functions

- `calculate_bpjs(base_salary)` — BPJS Ketenagakerjaan (JKK 0.24%, JKM 0.3%, JHT 3.7%+2%) + BPJS Kesehatan (4%+1%).
- `calculate_pph21_annual(annual_taxable_income)` — Progressive tax: 5% up to 60M, 15% up to 250M, 25% up to 500M, 30% up to 5B, 35% above.
- `calculate_overtime_pay(base_salary, overtime_hours, work_schedule)` — Indonesian labor law overtime rates.
- `calculate_monthly_payroll(db, employee, month, year)` — Full payroll: gross = base + allowances + overtime. Net = gross - BPJS employee share - PPh21.

---

## 28. Telegram Bot

**File:** `telegram_bot.py` (~2271 lines) — SECOND LARGEST
**Called by:** `telegram.router` (webhook)

### Purpose
Telegram bot for factory masters: report defects, log actual production, split positions, view recipes, upload photos. Full command handler.

### Commands
| Command | Description |
|---------|-------------|
| `/start` | Register user, link Telegram to PMS account |
| `/status` | View today's production status for factory |
| `/help` | Show available commands |
| `/defect <pos> <qty>` | Report defect for position |
| `/actual <pos> <qty>` | Report actual production quantity |
| `/split <pos>` | Start sorting split for position |
| `/glaze <pos>` | View glaze recipe and consumption for position |
| `/recipe <name>` | Lookup recipe details |
| `/plan` | View tomorrow's plan (daily distribution) |
| `/photo` | Upload production photo |

### Photo Handling
- Photos auto-detect position number from caption.
- Delivery photos trigger AI material matching (GPT-4 Vision).
- Photos stored via photo_storage service (Supabase or local).

---

## 29. Telegram AI

**File:** `telegram_ai.py` (~582 lines)
**Called by:** `telegram_bot.py`

### Purpose
AI-powered features for Telegram bot: natural language parsing, smart daily messages, defect diagnosis, task prioritization, material matching.

### Key Functions

- `parse_natural_language(text, user_context)` — Parses free-text messages into structured commands (e.g., "10 defective tiles on position 3" -> defect report).
- `generate_smart_daily_message(db, factory_id)` — AI-enhanced daily message with context-aware insights.
- `diagnose_defect(photo_base64, context)` — AI diagnosis of defect from photo.
- `prioritize_tasks(tasks, factory_context)` — AI-powered task prioritization.
- `ai_match_material(name, existing_materials)` — AI matching of delivery item names to catalog materials.

### LLM Priority
1. Anthropic Claude (primary)
2. OpenAI GPT-4 (fallback)
3. Context-only response (no LLM)

---

## 30. Telegram Callbacks

**File:** `telegram_callbacks.py` (~414 lines)
**Called by:** `telegram_bot.py`

### Purpose
Handles inline button callbacks from Telegram messages (daily plan acknowledgment, alert responses, task quick-actions).

---

## 31. AI Chat Service

**File:** `ai_chat_service.py` (~166 lines)
**Called by:** `ai_chat.router`

### Purpose
RAG-grounded AI assistant using production data context. Multi-provider (Claude + OpenAI fallback).

---

## 32. Photo Analysis (AI Vision)

**File:** `photo_analysis.py` (~382 lines)
**Called by:** `quality.router` (analyze-photo), `telegram_bot.py`

### Purpose
AI-powered photo analysis for defect detection and delivery verification.

### Key Functions

- `analyze_photo(image_bytes, analysis_type, context)` — Routes to OpenAI Vision or Claude Vision for analysis.
- `format_analysis_message(result)` — Formats AI analysis result as human-readable message.
- `format_delivery_message(result)` — Formats delivery photo analysis (material identification, quantity estimation).

---

## 33. Photo Storage

**File:** `photo_storage.py` (~250 lines)

### Purpose
Photo upload/storage abstraction: Supabase Storage (production) or local filesystem (development).

---

## 34. PDF Parser

**File:** `pdf_parser_service.py` (~850 lines)
**Called by:** `orders.router` (upload-pdf)

### Purpose
Parses order PDF documents into structured data using tabular extraction + pattern matching.

### Key Functions

- `parse_order_pdf(file_bytes)` — Main parser. Extracts text + tables from PDF. Maps columns to fields. Returns ParsedOrder with confidence scores.
- `validate_pdf_file(file_bytes, filename)` — Validates PDF format and size.
- `_identify_columns(headers, template)` — Maps table headers to order item fields.

### Supports
- Multiple PDF templates (auto-detected via `pdf_templates.py`).
- Date parsing in multiple formats (DMY, MDY, YYYY-MM-DD).
- Product type detection from text patterns.

---

## 35. Material Matcher (AI)

**File:** `material_matcher.py` (~1169 lines) — AI-heavy
**Called by:** `delivery.router`, `telegram_bot.py`

### Purpose
AI-powered matching of delivery item names (often in Indonesian) to existing material catalog. Handles fuzzy matching, translation, and smart suggestions.

### Key Functions

- `find_best_match(db, delivery_name)` — Main matcher. Translates from Indonesian, tokenizes, calculates similarity score against all materials.
- `smart_match_stone_item(db, delivery_data)` — Specialized matching for stone deliveries. Parses stone name for size/type/supplier hints.
- `match_delivery_items(db, items)` — Batch match delivery items.
- `translate_material_name(indo_name)` — Indonesian -> English material name translation.
- `normalize_size(text)` — Normalizes size strings ("10x10" -> "10x10", "10 cm x 10 cm" -> "10x10").

---

## 36. Surface Area Calculation

**File:** `surface_area.py` (~354 lines)
**Called by:** `order_intake.py`, `material_reservation.py`

### Purpose
Calculates glazeable surface area for various shapes and product types.

### Key Functions

- `calculate_glazeable_surface(shape, dimensions, product_type, edge_profile, ...)` — Main calculation. Handles rectangles, circles, triangles, octagons, freeform shapes.
- `calculate_edge_surface(length_cm, width_cm, height_cm, edge_profile, sides)` — Edge profiling adds extra surface area.
- `_calculate_bowl_surface(depth_cm, ...)` — Bowl surface for sinks (parallelepiped or half-oval).
- `get_shape_coefficient(db, shape, product_type)` — Lookup coefficient from shape_consumption_coefficients table.
- `calculate_glazeable_sqm_for_position(db, position)` — Convenience: calculates and caches glazeable_sqm on position.

---

## 37. Glazing Board Calculator

**File:** `glazing_board.py` (~73 lines)
**Called by:** `sizes.router`, `daily_distribution.py`

### Purpose
Calculates how many tiles fit on a standard glazing board (122 cm length, variable width). Masters glaze 2 boards at a time.

### Key Functions

- `calculate_glazing_board(width_mm, height_mm)` — Returns: tiles_per_board, board_width_cm, area_per_board_m2, tiles_along_length, tiles_across_width.

---

## 38. Size Resolution

**File:** `size_resolution.py` (~279 lines)
**Called by:** `tasks.router`, `order_intake.py`

### Purpose
Resolves ambiguous or new tile sizes from orders. Matches to existing catalog or creates new Size record.

### Key Functions

- `resolve_size_for_position(db, position)` — Matches position size string to sizes table. Creates SIZE_RESOLUTION task if no match.
- `create_size_resolution_task(db, position)` — Creates blocking task for PM to confirm size.

---

## 39. Kiln Breakdown Handling

**File:** `kiln_breakdown.py` (~461 lines)
**Called by:** `kilns.router`

### Purpose
Emergency handling when kiln breaks down: reassigns batches, reschedules, creates maintenance records, notifies stakeholders.

### Key Functions

- `handle_kiln_breakdown(db, kiln_id, description)` — Main entry: marks kiln as emergency maintenance, finds alternatives, reassigns batches.
- `find_alternative_kilns(db, broken_kiln, factory_id)` — Finds compatible alternative kilns.
- `reassign_batch_to_kiln(db, batch, alternatives)` — Moves batch to alternative kiln.
- `handle_kiln_restore(db, kiln_id)` — Restores kiln to active. Triggers rescheduling.

---

## 40. Order Cancellation

**File:** `order_cancellation.py` (~21 lines, delegated)
**Called by:** `orders.router`

Processes order cancellation: unreserves materials, cancels positions, updates order status, notifies Sales App via webhook.

---

## 41. Change Request Processing

**File:** `change_request_service.py` (~270 lines)
**Called by:** `integration.router` (webhook), `orders.router`

### Purpose
Handles order modification requests from Sales App: diff calculation, PM review, apply changes.

### Key Functions

- `create_change_request_from_webhook(db, order_id, new_payload)` — Calculates diff between current and new order data. Creates ChangeRequest for PM review.
- `approve_change_request(db, cr_id, user_id)` — Applies changes: updates items, recalculates positions, reschedules.
- `reject_change_request(db, cr_id, user_id)` — Rejects change, notifies Sales.

---

## 42. Schedule Estimation

**File:** `schedule_estimation.py` (~221 lines)
**Called by:** `factories.router`, `orders.router`

### Purpose
Estimates production timelines: how many days for an order, when will positions be available.

### Key Functions

- `calculate_position_availability(db, position)` — Estimated completion date for a position.
- `calculate_production_days(db, order)` — Total production days estimate.
- `calculate_schedule_deadline(db, order)` — Deadline = received_date + production_days + buffer.
- `recalculate_all_estimates(db, factory_id)` — Bulk recalculation for all active orders.

---

## 43. Reconciliation

**File:** `reconciliation.py` (~109 lines)
**Called by:** `reconciliations.router`, `status_machine.py`

### Purpose
Stage-to-stage quantity reconciliation: verifies piece counts between production stages match.

### Key Functions

- `reconcile_stage_transition(db, batch_id, stage_from, stage_to)` — Compares input count vs output (good + defect + write-off). Flags discrepancy.
- `inventory_reconciliation(db, reconciliation_id)` — Physical count vs system balance reconciliation.

---

## 44. Warehouse Operations

**File:** `warehouse.py` (~290 lines)
**Called by:** `materials.router`

### Purpose
Material receiving with approval workflow.

### Key Functions

- `receive_material(db, transaction_data)` — Creates RECEIVE transaction. If approval_mode='all', sets pending approval.
- `pm_approve_receipt(db, transaction_id, accepted_qty)` — PM approves receipt. Updates stock balance.
- `_update_stock_balance(db, material_id, factory_id, qty)` — Atomically updates material_stock.balance.

---

## 45. Webhook Sender

**File:** `webhook_sender.py` (~91 lines)
**Called by:** `status_machine.py`, `order_cancellation.py`

### Purpose
Sends production status updates back to Sales App via HTTP webhook.

---

## 46. Partial Delivery

**File:** `partial_delivery.py` (~395 lines)
**Called by:** `purchaser.router`

### Purpose
Handles partial material deliveries: records what was received, creates deficit task for remainder.

### Key Functions

- `handle_partial_delivery(db, pr_id, received_items)` — Records partial receipt, updates PR to PARTIALLY_RECEIVED, creates deficit resolution task.
- `pm_resolve_partial_delivery(db, task_id, decision)` — PM decides: wait for rest, find alternative supplier, or accept shortage.

---

## 47. Defect Alert (5-Why)

**File:** `defect_alert.py` (~30 lines)
**Called by:** `quality_control.py`

Creates 5-Why analysis task for quality manager when defect found during QC.

---

## 48. Master Achievement System

**File:** `achievements.py` (~449 lines)
**Called by:** gamification cron, Telegram bot

### Purpose
Tracks and awards 7 achievement types across 5 levels (Apprentice → Grand Master) for factory workers. Measures progress from OperationLog, QualityCheck, DefectRecord, UserSkill, and CompetitionEntry.

### Key Functions

- `update_achievements_for_user(db, user_id)` — Recalculates all 7 achievement types for a user. Returns list of newly unlocked achievements.
- `get_user_achievements(db, user_id)` — Returns all achievements with progress info (current, target, thresholds).
- `_check_level_up(db, ach, current_progress)` — Compares progress against thresholds, bumps level if crossed. Sends Telegram notification on level-up.
- `_measure_glazing_master(db, user_id)` — Counts distinct positions worked via OperationLog.
- `_measure_zero_defect_hero(db, user_id)` — Counts consecutive zero-defect production days (skips non-production days).
- `_measure_speed_champion(db, user_id)` — Counts consecutive days where user's cycle time was below factory average.
- `_measure_kiln_expert(db, user_id)` — Counts distinct batches managed via OperationLog.
- `_measure_quality_star(db, user_id)` — Counts QC checks with OK result.
- `_measure_skill_collector(db, user_id)` — Counts certified UserSkill records.
- `_measure_competition_winner(db, user_id)` — Counts competition entries with rank=1.

### Business Rules
1. **7 achievement types:** glazing_master, zero_defect_hero, speed_champion, kiln_expert, quality_star, skill_collector, competition_winner.
2. **5 levels per achievement:** Apprentice (1), Craftsman (2), Expert (3), Master (4), Grand Master (5).
3. **Thresholds vary by type:** e.g. glazing_master = 100/500/1000/5000/10000 positions.
4. Level-up triggers Telegram notification to user + forum #achievements topic.
5. Zero-defect hero skips days with no production activity (weekends/holidays) — absence != zero defects.

### Dependencies
`OperationLog`, `QualityCheck`, `DefectRecord`, `UserSkill`, `CompetitionEntry`, `notifications`

---

## 49. Attendance Monitor

**File:** `attendance_monitor.py` (~221 lines)
**Called by:** scheduler (daily 7:30 AM Bali / 23:30 UTC)

### Purpose
Detects working days in the current month where no attendance records exist for a factory. Alerts PM (in-app) and CEO/Owner (Telegram) when gaps accumulate.

### Key Functions

- `check_attendance_gaps(db, factory_id)` — Scans from 1st of month to yesterday. Returns list of unfilled dates (excludes Sundays and FactoryCalendar holidays). Skips factories with no active employees.
- `process_attendance_gaps(db, factory_id)` — Calls check, sends PM in-app notification, and Telegram alert to CEO/Owner if 3+ days unfilled.

### Business Rules
1. A day is "unfilled" if ZERO attendance records exist for that factory+date.
2. Sundays (weekday=6) and FactoryCalendar holidays are excluded.
3. PM always gets in-app notification when any gaps exist.
4. CEO/Owner gets Telegram alert only when 3+ working days are unfilled.
5. If factory has no active employees, monitoring is skipped.

### Dependencies
`Attendance`, `Employee`, `Factory`, `FactoryCalendar`, `notifications`

---

## 50. Auto-Reorder

**File:** `auto_reorder.py` (~465 lines)
**Called by:** daily scheduler (after min_balance recalculation)

### Purpose
Detects low stock (balance < min_balance), creates MaterialPurchaseRequest (PENDING) + mandatory PM Task, and sends Telegram notification with approve/edit/reject buttons.

### Key Functions

- `check_and_create_reorders(db, factory_id)` — Finds low-stock materials, groups by supplier, creates purchase requests and MATERIAL_ORDER tasks. Skips materials already covered by substitutes or with existing pending auto_reorder PRs.
- `approve_purchase_request(db, pr_id, pm_user_id)` — PM approves, sets status=APPROVED, closes linked task.
- `edit_purchase_request(db, pr_id, pm_user_id, updated_materials, notes)` — PM edits quantities, approves, notifies CEO of changes.
- `reject_purchase_request(db, pr_id, pm_user_id, reason)` — PM rejects, closes PR, notifies CEO with reason.

### Business Rules
1. Deduplication: skips materials that already have a PENDING auto_reorder purchase request.
2. Substitution check: if a substitute material covers the full deficit, the original is skipped (via `material_substitution.check_substitution_available`).
3. For stone/frit materials: order quantity = max(deficit, avg_monthly_consumption).
4. Purchase requests are grouped by supplier.
5. PM task has priority=7 (high). Telegram buttons: Approve / Edit / Reject.
6. CEO/Owner notified on edit or reject actions.

### Dependencies
`MaterialStock`, `Material`, `Supplier`, `MaterialPurchaseRequest`, `Task`, `material_substitution`, `notifications`

---

## 51. CEO Reports (Gamification)

**File:** `ceo_reports.py` (~688 lines)
**Called by:** scheduler (Sunday 20:00 WITA), API endpoint

### Purpose
Generates weekly gamification dashboard reports for CEO/Owner. Includes leaderboard, competitions, certifications, attention alerts, and prize recommendations. All user-facing text in Indonesian (Bahasa Indonesia).

### Key Functions

- `generate_weekly_gamification_report(db, factory_id)` — Telegram-formatted report with 5 sections: leaderboard, active competitions, new certifications, workers needing attention, pending prizes.
- `generate_productivity_impact(db, factory_id, days)` — Before/after comparison: throughput, quality, active workers, avg points per worker.
- `get_who_needs_encouragement(db, factory_id)` — Finds workers with 3+ weeks of declining points (compares last 4 weekly totals).
- `get_ceo_dashboard_data(db, factory_id)` — Full JSON for frontend CEO dashboard: leaderboard (top 10), competitions, certifications, attention, prizes, productivity impact, season info.
- `send_weekly_report_all_factories(db)` — Sends reports to all CEO/Owner users across all active factories.

### Business Rules
1. Weekly point delta shown per worker (current vs previous week).
2. Workers flagged for attention only if declining 3+ consecutive weeks.
3. IDR amounts formatted as "Rp 300rb" or "Rp 1.5jt".
4. Report sent as in-app notification (gamification_weekly_report type).

### Dependencies
`PointTransaction`, `UserPoints`, `Competition`, `CompetitionEntry`, `UserSkill`, `SkillBadge`, `GamificationSeason`, `prize_advisor`, `notifications`

---

## 52. Mini-Competitions Engine

**File:** `competitions.py` (~774 lines)
**Called by:** scheduler (daily cron), API endpoints

### Purpose
Speed + quality gamification competitions for factory workers. Supports individual and team competitions with combined scoring formula.

### Key Functions

- `create_competition(db, ...)` — Creates individual or team competition with date range, quality_weight, and optional prize budget.
- `create_team_competition(db, ...)` — Creates team competition with pre-defined teams (sections filtered by operation name).
- `update_competition_scores(db, competition_id)` — Recalculates all entries from OperationLog data. Assigns ranks.
- `finalize_competition(db, competition_id)` — Final score recalc, sets status=completed, awards points (1st=50, 2nd=30, 3rd=20, participation=10).
- `update_all_active_competitions(db)` — Cron: activates upcoming competitions, recalculates scores for all active ones.
- `finalize_ended_competitions(db)` — Cron: auto-finalizes competitions past end_date.
- `auto_create_weekly_competition(db, factory_id)` — Creates "Minggu Kecepatan #N" (Speed Week) individual competition, Mon-Sun.
- `start_new_season(db, factory_id)` — Creates monthly GamificationSeason. Closes previous season with final_standings snapshot.
- `propose_challenge(db, ...)` — Worker-proposed challenge (status=upcoming until PM approves).

### Business Rules
1. **Scoring formula:** `combined = throughput * (quality_pct / 100) ^ quality_weight`.
2. **Prize tiers:** 1st=50pts, 2nd=30pts, 3rd=20pts, participation=10pts.
3. Team members resolved from OperationLog by matching team.filter_key against operation names.
4. Weekly competitions prevent duplicates via start_date + title check.
5. Seasons are monthly, with previous season auto-closed and final standings snapshotted.

### Dependencies
`Competition`, `CompetitionEntry`, `CompetitionTeam`, `GamificationSeason`, `OperationLog`, `points_system`

---

## 53. Factory Leaderboard

**File:** `factory_leaderboard.py` (~210 lines)
**Called by:** CEO/Owner dashboard API

### Purpose
Compares all active factories across 6 key metrics for CEO multi-factory view.

### Key Functions

- `calculate_factory_leaderboard(db, period)` — Ranks factories by: avg_cycle_days, defect_rate, on_time_pct, kiln_utilization, output_sqm, positions_completed. Period: "week" or "month".

### Business Rules
1. Each metric gets a per-factory rank. Overall rank = sum of all metric ranks (lower = better).
2. Current vs previous period delta shown for each metric.
3. Metrics marked as `lower_is_better` or not (affects ranking direction).
4. Kiln utilization obtained from `daily_kpi.calculate_kiln_utilization`.
5. Output sqm from TpsShiftMetric.actual_output.

### Dependencies
`Factory`, `ProductionOrder`, `OrderPosition`, `DefectRecord`, `QualityCheck`, `TpsShiftMetric`, `daily_kpi`

---

## 54. Material Substitution

**File:** `material_substitution.py` (~221 lines)
**Called by:** `auto_reorder`, `material_reservation`

### Purpose
Handles interchangeable materials (e.g. 0.2g CMC = 1g Bentonite). When one material is insufficient, checks if a substitute has enough stock to cover the deficit.

### Key Functions

- `find_substitutes(db, material_id)` — Finds all active substitutes from MaterialSubstitution table. Handles bidirectional lookup (material_a↔material_b) with automatic ratio inversion.
- `check_substitution_available(db, material_id, factory_id, needed_qty)` — Checks if any substitute has sufficient stock. Returns best match even if insufficient (for info).
- `get_combined_availability(db, material_id, factory_id)` — Total available quantity: original material balance + all substitutes converted to original-material equivalent.

### Business Rules
1. Substitution is bidirectional: if A→B has ratio 5.0, then B→A has ratio 0.2.
2. `check_substitution_available` returns the first sufficient substitute, or the first insufficient one if none are sufficient.
3. Conversion uses the ratio from MaterialSubstitution table (e.g. 1 unit CMC → 5 units Bentonite).

### Dependencies
`MaterialSubstitution`, `MaterialStock`, `Material`

---

## 55. Payroll PDF Generator

**File:** `payroll_pdf.py` (~545 lines)
**Called by:** payroll API endpoint

### Purpose
Generates payroll PDFs using ReportLab: landscape A4 summary table (all employees) and individual portrait A4 payslips in Moonjar brand style (Bahasa Indonesia).

### Key Functions

- `generate_payroll_summary_pdf(payroll_items, totals, year, month, factory_name)` — Landscape A4 table with all employees: base, allowances, overtime, gross, BPJS, tax, net. Company header "PT MOONJAR DESIGN BALI".
- `generate_payslip_pdf(item, year, month, factory_name)` — Individual payslip: employee info, attendance (present/absent/sick/leave), earnings breakdown, overtime by multiplier tier, BPJS employer+employee, PPh 21 TER, deductions, net salary. Includes motivational Indonesian quote rotated by month.

### Business Rules
1. Summary includes formal/contractor counts and total cost-to-company.
2. Payslip sections: KEHADIRAN, PENDAPATAN, LEMBUR, GAJI KOTOR, PPh 21, BPJS, POTONGAN, GAJI BERSIH.
3. BPJS employee portion explicitly noted as "paid by company, not deducted from salary".
4. Overtime breakdown by multiplier tiers: 1.5x, 2x, 3x, 4x.
5. Signature block: "Stanislav Shevchuk, Direktur".
6. Footer: "Dokumen ini bersifat rahasia" (confidential).

### Dependencies
`reportlab` (external)

---

## 56. Points System

**File:** `points_system.py` (~290 lines)
**Called by:** recipe verification, competitions, skill_system, streaks, Telegram bot

### Purpose
Central gamification points engine. Awards points, tracks totals (year/month/week), provides leaderboards and rankings.

### Key Functions

- `calculate_accuracy_points(target_g, actual_g)` — Scoring by weighing deviation: +/-1%=10pts, +/-3%=7pts, +/-5%=5pts, +/-10%=3pts, >10%=1pt.
- `award_points(db, user_id, factory_id, points, reason, details, position_id)` — Creates PointTransaction + upserts UserPoints totals (year/month/week).
- `get_user_points(db, user_id, factory_id)` — Current year point summary.
- `get_recent_transactions(db, user_id, factory_id, limit)` — Last N point transactions.
- `get_points_leaderboard(db, factory_id, period)` — Top 20 by year/month/week.
- `get_user_rank(db, user_id, factory_id)` — User's rank and total participants.
- `reset_weekly_points(db)` — Cron: resets points_this_week for all users.
- `reset_monthly_points(db)` — Cron: resets points_this_month for all users.

### Business Rules
1. Points accumulate yearly with Jan 1 reset (via year column in UserPoints).
2. Weekly and monthly counters reset independently via cron jobs.
3. Bonus point sources: streak (+5/day), challenge (+20), achievement (+50), skill certification (+100), competition win (+50/+30/+20), team win (+30), speed bonus (+3/5/10 by stage).

### Dependencies
`UserPoints`, `PointTransaction`, `RecipeVerification`

---

## 57. Prize Advisor

**File:** `prize_advisor.py` (~867 lines)
**Called by:** scheduler (monthly/quarterly), CEO dashboard API

### Purpose
Rule-based prize recommendation engine. Analyzes worker productivity and suggests prizes with ROI estimate. No LLM — fast, reliable, predictable.

### Key Functions

- `generate_monthly_prizes(db, factory_id, year, month)` — Creates up to 5 PrizeRecommendation records: individual_mvp, most_improved, team_winner, skill_champion, zero_defect.
- `generate_quarterly_prizes(db, factory_id, year, quarter)` — Quarterly prizes with 2.5x budget multiplier.
- `approve_prize(db, prize_id, approver_id)` — CEO approves (status: suggested→approved).
- `reject_prize(db, prize_id, approver_id, reason)` — CEO rejects.
- `award_prize(db, prize_id)` — Marks prize as actually awarded (approved→awarded).
- `get_pending_prizes(db, factory_id)` — All suggested prizes awaiting CEO approval.

### Business Rules
1. **5 prize types:** individual_mvp (Rp 300k), most_improved (Rp 200k), team_winner (Rp 500k), skill_champion (Rp 150k), zero_defect (Rp 100k).
2. **ROI formula:** `(revenue_gain - prize_cost) / prize_cost`, where `revenue_gain = monthly_revenue_estimate * productivity_gain_pct / 100`. Default monthly_revenue_estimate = Rp 50M.
3. Quarterly budget = 2.5x monthly.
4. Regeneration: old `suggested` recommendations for the same period are deleted before creating new ones.
5. Most improved: calculated as % increase in points vs previous month/period.
6. Best team: scored 60% avg points + 40% quality (by operation section).

### Dependencies
`PrizeRecommendation`, `UserPoints`, `PointTransaction`, `OperationLog`, `UserSkill`, `SkillBadge`

---

## 58. Production Split (Mid-Production)

**File:** `production_split.py` (~242 lines)
**Called by:** positions API

### Purpose
Splits a position during production. Parent position is frozen (is_parent=True); children inherit parent's state and run the full remaining cycle independently.

### Key Functions

- `can_split_position(position)` — Validates: cannot split if loaded_in_kiln, already a parent, or a sorting sub-position.
- `split_position_mid_production(db, position, splits, reason, created_by_id)` — Creates child positions from split specs. Freezes parent via raw SQL (is_parent, split_type, split_stage, split_at, split_reason).
- `get_split_tree(db, position_id)` — Returns full nested tree of parent + all descendants with split metadata.

### Business Rules
1. Split quantities must sum exactly to parent quantity.
2. Children inherit all parent attributes (recipe, size, factory, planned dates, firing_round, etc.).
3. quantity_sqm and quantity_with_defect_margin are scaled proportionally.
4. Children continue from the same status the parent had at time of split.
5. Cannot split: loaded_in_kiln, already-split parents, sorting sub-positions.
6. Parent is frozen via `is_parent=True` and retains historical data.

### Dependencies
`OrderPosition`

---

## 59. Skill Badge System

**File:** `skill_system.py` (~1017 lines)
**Called by:** scheduler (nightly), API endpoints, OperationLog creation

### Purpose
Learnable skills and certifications for factory workers. Workers progress by completing operations with low defect rates. Skills auto-certify or require mentor approval.

### Key Functions

- `seed_factory_skills(db, factory_id)` — Creates 20 default skill badges (10 production, 4 specialized, 2 quality, 1 safety, 1 leadership, 2 cross-training).
- `get_factory_skills(db, factory_id)` — All skills with certified/learning counts.
- `get_user_skills(db, user_id)` — User's skill progress across all badges.
- `start_skill_learning(db, user_id, skill_badge_id)` — Begin tracking a skill (idempotent).
- `update_skill_progress(db, user_id, operation_id, quantity, defects)` — Called after OperationLog creation. Updates matching skills, checks for certification.
- `batch_update_all_skills(db)` — Nightly cron: recalculates all learners from OperationLog + awards cross-training badges.
- `request_certification(db, user_id, skill_badge_id)` — Worker requests PM approval (validates requirements first).
- `approve_certification(db, approver_id, user_skill_id)` — PM approves. Awards points, sends Telegram congratulation.
- `revoke_certification(db, revoker_id, user_skill_id, reason)` — PM revokes (reason required). Notifies PM channel.

### Business Rules
1. **20 skills total:** 6 categories with varying requirements (30-60 operations, 85-95% defect-free).
2. **Defect-free %** calculated from last 50 operations (`_DEFECT_WINDOW = 50`).
3. Skills with `required_mentor_approval=True` go to `pending_approval` status; others auto-certify.
4. **Cross-training badges** (2-stage, 4-stage) auto-awarded based on certified production skill count.
5. Points on certification: 80-300 pts depending on skill category.
6. Only PM/admin/owner/CEO can approve or revoke certifications.
7. Revocation sends notification to PM channel.

### Dependencies
`SkillBadge`, `UserSkill`, `OperationLog`, `points_system`, `notifications`

---

## 60. Staffing Optimizer

**File:** `staffing_optimizer.py` (~581 lines)
**Called by:** API endpoint, Telegram bot

### Purpose
AI-driven optimal worker distribution suggestions. Analyzes actual throughput (TpsShiftMetric), current assignments (ShiftAssignment), and scheduled demand (OrderPosition) to recommend rebalancing across 9 production stages.

### Key Functions

- `suggest_optimal_staffing(db, factory_id, horizon_days)` — Full analysis: per-stage throughput, workers, utilization, bottleneck detection, actionable suggestions.

### Business Rules
1. **9 production stages analyzed:** incoming_inspection, engobe, glazing, pre_kiln_inspection, kiln_loading, firing, sorting, packing, quality_check.
2. `workers_needed = ceil(required_daily_throughput / throughput_per_worker)`.
3. **Understaffed:** demand > 110% capacity. **Overstaffed:** demand < 50% capacity.
4. **Suggestion priority:** (a) move workers from overstaffed to understaffed, (b) add workers if no surplus available, (c) overtime if utilization >150%.
5. Uses actual TpsShiftMetric data for throughput; falls back to hardcoded defaults per stage.
6. Demand calculated from OrderPosition with planned dates within the horizon window.

### Dependencies
`TpsShiftMetric`, `ShiftAssignment`, `OrderPosition`

---

## 61. Streaks & Daily Challenges

**File:** `streaks.py` (~379 lines)
**Called by:** scheduler (daily), Telegram bot

### Purpose
Tracks consecutive-day streaks for PM users and generates deterministic daily challenges per factory.

### Key Functions

- `update_streaks_for_factory(db, factory_id, today)` — Updates all 4 streak types for all PM/admin/owner users.
- `check_on_time_delivery(db, factory_id, today)` — True if all orders shipped today met deadline (vacuous true if no shipments).
- `check_zero_defects(db, factory_id, today)` — True if no defect records logged today.
- `check_daily_login(db, user_id, today)` — True if user had an active session today.
- `check_batch_utilization(db, factory_id, today)` — True if avg kiln utilization >= 80%.
- `get_daily_challenge(db, factory_id, today)` — Returns deterministic daily challenge (from 7 templates, selected via SHA-256 hash of factory_id + date).
- `evaluate_challenge(db, factory_id, today)` — Measures actual progress against challenge target.
- `get_user_streaks(db, user_id, factory_id)` — Returns all streaks with current/best/last_date.

### Business Rules
1. **4 streak types:** on_time_delivery, zero_defects, daily_login, batch_utilization.
2. Streak increments if last activity was yesterday; resets to 1 if gap.
3. Best streak tracked separately from current streak.
4. **7 challenge templates:** pre_kiln_checks, kiln_utilization, ship_orders, zero_defects, batch_completion, position_progress, all_checks_pass.
5. Challenge selection is deterministic per factory+date (SHA-256 hash mod 7).

### Dependencies
`UserStreak`, `DailyChallenge`, `ProductionOrder`, `DefectRecord`, `Batch`, `QualityCheck`, `OrderPosition`, `ActiveSession`, `daily_kpi`

---

## 62. TPS Auto-Calibration

**File:** `tps_calibration.py` (~471 lines)
**Called by:** scheduler (daily cron), API endpoint

### Purpose
Auto-calibrates production rates using Exponential Moving Average (EMA) of actual output. Detects drift between planned and actual rates and adjusts ProcessStep and StageTypologySpeed records.

### Key Functions

- `calculate_ema_rate(db, factory_id, step, lookback_days, alpha)` — EMA of actual production rate from TpsShiftMetric over last 30 days.
- `check_calibration_needed(db, factory_id, step, threshold, min_data_points)` — Checks if drift exceeds threshold (15%). Returns suggestion or None.
- `run_calibration(db, factory_id, auto_apply)` — Runs calibration for all active ProcessSteps. Auto-applies if step.auto_calibrate=True.
- `apply_calibration(db, step_id, new_rate, ...)` — Updates ProcessStep rate + creates CalibrationLog entry.
- `get_calibration_status(db, factory_id)` — Current status for all steps with drift info.
- `calibrate_typology_speeds(db, factory_id, auto_apply, ...)` — Same EMA calibration for StageTypologySpeed records, filtered by typology_id.

### Business Rules
1. **EMA alpha=0.3** (30% weight to newest data point).
2. **Drift threshold=15%:** calibration triggers only when |EMA - planned| / planned > 0.15.
3. **Minimum 7 data points** required before calibration is considered.
4. Auto-calibration enabled by default (ProcessStep.auto_calibrate=True).
5. PM can toggle auto-calibration per step via API.
6. CalibrationLog records: previous_rate, new_rate, ema_value, data_points, trigger (auto/manual/auto_typology).
7. Typology speeds calibrated independently per typology_id (each typology gets its own EMA).

### Dependencies
`ProcessStep`, `StageTypologySpeed`, `TpsShiftMetric`, `CalibrationLog`

---

## 63. Transcription Logger

**File:** `transcription_logger.py` (~85 lines)
**Called by:** Telegram bot (voice/audio messages)

### Purpose
Transcribes voice messages via OpenAI Whisper API and persists transcription logs to the database.

### Key Functions

- `transcribe_audio(audio_bytes, filename)` — Async. Sends audio to OpenAI Whisper API (`whisper-1` model, `verbose_json` format). Returns text, language, and duration.
- `save_transcription_log(db, ...)` — Persists TranscriptionLog with user_id, telegram IDs, audio duration, transcribed text, AI response summary, detected language.

### Business Rules
1. Requires OPENAI_API_KEY in settings.
2. Default audio format: OGG (Telegram voice messages).
3. Transcription timeout: 60 seconds.
4. Language auto-detected by Whisper (returned in response).

### Dependencies
`TranscriptionLog`, `httpx`, OpenAI Whisper API

---

## 64. Typology Matcher

**File:** `typology_matcher.py` (~422 lines)
**Called by:** production_scheduler, batch formation, kiln assignment

### Purpose
Matches positions to kiln loading typologies and calculates capacity per kiln per typology using the geometry engine.

### Key Functions

- `find_matching_typology(db, position)` — Matches position against KilnLoadingTypology criteria (product_types, place_of_application, collections, methods, size range). Returns highest-priority match.
- `classify_loading_zone(position)` — Returns "edge" or "flat" based on place_of_application and tile size (<=15cm max side = edge).
- `get_effective_capacity(db, position, kiln)` — Resolution: ai_adjusted_sqm → capacity_sqm → kiln.capacity_sqm → 1.0 fallback.
- `get_zone_capacity(db, position, kiln, zone)` — Zone-specific capacity from KilnTypologyCapacity. Falls back to proportional split (85% edge / 15% flat).
- `calculate_typology_for_kiln(db, typology, kiln)` — Calculates capacity using geometry engine (business/kiln/capacity.py). Creates/updates KilnTypologyCapacity record.
- `calculate_all_typology_capacities(db, factory_id, typology_id)` — Batch: all active kilns x typologies.

### Business Rules
1. Typology matching criteria: product_types, place_of_application, collections, methods (all JSONB arrays; empty = match all), plus size range.
2. If position.place_of_application is NULL and product_type is "tile", defaults to "face_only" (prevents silent scheduler fallback).
3. Capacity resolution order: ai_adjusted_sqm > capacity_sqm > kiln.capacity_sqm > 1.0.
4. Edge/flat zone classification: face_only/edges_1/edges_2 with max_dim <=15cm = edge; everything else = flat.
5. Default fallback for zone capacity: edge=85%, flat=15% of total.

### Dependencies
`KilnLoadingTypology`, `KilnTypologyCapacity`, `OrderPosition`, `Resource`, `business/kiln/capacity.py`

---

## 65. Weekly Summary

**File:** `weekly_summary.py` (~256 lines)
**Called by:** scheduler (Sunday 20:00 UTC / Monday 04:00 Bali)

### Purpose
Generates and sends a rich weekly production summary via Telegram to PM, CEO, and Owner users.

### Key Functions

- `generate_weekly_summary(db, factory_id)` — Builds summary for last 7 days: orders shipped (with delta vs previous week), positions completed, firings + kiln utilization, defect rate, on-time %, best master.
- `send_weekly_summary(db, factory_id)` — Sends generated summary to all PM/CEO/Owner users with Telegram.

### Business Rules
1. Covers Mon-Sun (last 7 days).
2. Delta comparison vs previous 7-day period for shipped orders.
3. Best master determined by most positions moved to READY_FOR_SHIPMENT/SHIPPED (via updated_by field).
4. Mood indicator: defect_rate <3% + on_time >=95% = "Excellent"; <5% + >=85% = "Good"; else = "Room for improvement".
5. Message language: Russian (for CEO), with metrics in universal format.

### Dependencies
`ProductionOrder`, `OrderPosition`, `Batch`, `DefectRecord`, `QualityCheck`, `Factory`, `notifications`, `daily_kpi`

---

## §28 Plan vs Fact — Daily Production Tracking

### Purpose
Compare planned vs actual daily production per stage, track carryover, and show cumulative progress for each position.

### Data Sources
- **PLAN**: `OrderPosition.schedule_metadata.stage_plan[<stage>]` — contains `{start, end, days, qty_per_day}` for each stage. When target date falls within `[start, end]`, the position has `qty_per_day` planned work.
- **FACT**: `OperationLog` entries for the given `shift_date` — `quantity_processed` summed per position per stage. Stage is resolved by mapping `Operation.name` (freeform) to stage keys via `_OP_NAME_TO_STAGE` lookup.
- **CARRYOVER**: `max(0, planned - actual)` — what didn't get done today, expected to add to tomorrow's workload.
- **CUMULATIVE**: Sum of all `OperationLog.quantity_processed` up to and including the target date per position per stage.

### Tracked Stages (in production order)
1. `engobe` — Engobe application
2. `glazing` — Glaze application
3. `edge_cleaning_loading` — Edge cleaning and board loading
4. `kiln_loading` — Loading into kiln (special case: if no stage_plan entry, falls back to `planned_kiln_date == target_date`)

### Daily Capacity
Computed via `_get_stage_daily_capacity()` from `StageTypologySpeed` — `effective_rate_per_hour * shift_hours * shift_count`. Used for informational display only.

### Color Coding (Frontend)
- Green: actual >= plan (100%+)
- Yellow: actual = 80-99% of plan
- Red: actual < 80% of plan

### Endpoint
`GET /api/schedule/daily-plan?factory_id=<uuid>&date=<YYYY-MM-DD>`

### Frontend
"Plan vs Fact" tab on ManagerSchedulePage. Component: `PlanVsFactView.tsx`. Date picker with prev/next day navigation.

---

## §29 Material Naming, Stone Typology & Delivery Matching

### Purpose
Single source of truth for how stone materials are named, classified, matched against the catalog on delivery, and which units are valid per material type. Drives matcher (`business/services/material_matcher.py`), delivery flow (`api/routers/delivery.py`), naming service (`business/services/material_naming.py`), Telegram bot, and the web "Scan Delivery Note" dialog.

### Size string normalisation (2026-04-26)

Size strings come from many typists in many shapes: `"5×21,5"`, `"5x21.5"`, `"5 x 21.5"`, `"5х21,5"` (cyrillic ха), `"5*21.5"`. Without normalisation, `"5x21,5" in "5x21.5"` returns `False` and stone matching silently misses the stock — that's the bug behind the prod incident on 25 Apr 2026.

**Single canonical form** — lowercase, comma → dot, all of `×`/`х`/`Х`/`✕`/`*` → ASCII `x`, every whitespace removed.

```
"5×21,5"      → "5x21.5"
" 5 x 21.5 "  → "5x21.5"
"5х21,5"      → "5x21.5"     (cyrillic)
"10 X 10"     → "10x10"
"5*20"        → "5x20"
```

**Helper:** `business/services/size_normalizer.py::normalize_size_str()`. **Mandatory** at every comparison site (matcher) and every parse site (size→dimensions). No ad-hoc `.lower().replace()` chains anywhere — they always end up incomplete.

Active call sites: `stone_reservation.py` (both matching strategies), `typology_matcher.py`, `production_scheduler.py`, `surplus_handling.py`, `kiln/capacity.py::parse_size`, `api/routers/positions.py`, `api/routers/orders.py`.

### Naming model

Every `Material` has two name fields:

- **`Material.name`** — long name (≤300 chars, unique). For stone, this is the human-readable name as it first arrived on a delivery note (e.g. `"Grey Lava 5×20×1.2"`, `"Bali Lava Stone 5×20×1.2"`). Preserves the original wording. Editable.
- **`Material.short_name`** — canonical short name (≤100 chars). For stone, ALWAYS `"Lava Stone {size}"` (two words, exact case). For non-stone, defaults to `name`. Used as the matching key.

**One material per `short_name`.** If "Grey Lava 5×20×1.2" arrives and "Lava Stone 5×20×1.2" already exists with `short_name == "Lava Stone 5×20×1.2"`, matcher reuses that material — the receipt adds to the existing balance. The exact wording from this delivery note is preserved in `MaterialTransaction.delivery_name` so history is not lost.

Color of stone is NOT stored as a structured field on `Material`. Reasoning: stock is tracked at the `short_name` level — color variants of the same size collapse into one balance.

### Stone typologies (5 values)

`Material.product_subtype` for stone uses one of:

| Value | Meaning | Auto-detect rule |
|---|---|---|
| `tiles` | Flat tile | Single thickness (e.g. `1.2`), max dim ≤ 40 cm |
| `3d` | Relief / 3D-formed tile | Thickness expressed as range (e.g. `1-2`, `1/2`) |
| `sink` | Wash-basin / sink | Round Ø > 40 cm, OR explicit "sink"/"wastafel" keyword |
| `countertop` | Worktop / counter | Rectangular with any dim > 40 cm, OR round Ø > 40 cm with explicit "countertop"/"top" keyword |
| `freeform` | Arbitrary sculptural form, no standard size grid | Explicit selection only (matcher never auto-assigns) |

Ambiguous round Ø 29-40 cm → `needs_user_choice=true` returned to UI; user picks `tiles` / `sink` / `countertop`.

### Size schema (per typology)

`Size` table fields:
- `width_mm`, `height_mm`, `thickness_mm` — for rectangular shapes
- `diameter_mm` (NEW, nullable) — for round shapes
- `shape` — `'rectangle'` | `'square'` | `'round'` | `'oval'` | `'right_triangle'` | `'triangle'` | `'octagon'` | `'trapezoid'` | `'trapezoid_truncated'` | `'rhombus'` | `'parallelogram'` | `'semicircle'` | `'freeform'`
- `shape_dimensions` (JSONB) — authoritative per-shape inputs (in cm). Preferred over `width_mm/height_mm` for display (`formatSizeLabel`). Keys depend on the shape.

#### Triangle types

Triangles are split into **two distinct shapes** because their loading on shelves differs and operator input is different:

- `right_triangle` — operator enters two legs `side_a`, `side_b`; hypotenuse `side_c = √(a²+b²)` is auto-derived and read-only. Bounding box for display = `a × b` (the legs of the right angle), NOT a square. Area = `a*b/2`.
- `triangle` — general triangle. Operator enters all three sides `side_a`, `side_b`, `side_c`. Validated by triangle inequality. Area = Heron's formula. Display lists all three sides (`a × b × c`).

Existing rows whose three sides satisfy `a²+b²≈c²` (within 1% tolerance) are auto-classified as `right_triangle` by Alembic migration `031`.

For kiln packing, both triangle types are loaded **as pairs** (two pieces fit into a single rectangular footprint with a small gap) — see `business/kiln/capacity.py::_effective_dims`.

Size lookup uses `(shape, dimensions)` tuple; orientation-insensitive for rectangles (`5×20` matches `20×5`).

For `freeform` materials, `Size` is optional — short_name becomes just `"Lava Stone Freeform"` and additional descriptor lives in `name`.

### Unit constraints per material type

Hard-validated at API boundary (`material_naming.validate_unit_for_type`) — the UI MUST hide invalid options:

| material_type | Allowed units |
|---|---|
| `stone` | `pcs`, `m²` |
| `pigment`, `frit`, `oxide_carbonate`, `other_bulk` | `kg`, `g` |
| `packaging`, `consumable`, `other` | `pcs`, `m`, `kg` |

Reject delivery transactions where unit is not allowed for the material's type.

### Supplier → material_type mapping

Static map in `material_matcher.SUPPLIER_MATERIAL_TYPE`. When a delivery's supplier is recognized, `material_type` is forced — matcher never proposes a material of a different type. Current entries: `bestone*` → `stone`. Extend by adding rows; no code change beyond the dict.

### Delivery matching algorithm (stone path)

For each item from OCR:

1. **Parse** raw name → `{color_word, base="Lava Stone", size_raw, thickness_raw, is_round, diameter}`. (Stripping is informational; color is discarded.)
2. **Determine typology** by typology rules above.
3. **Resolve size** in `Size` table by dimensions; create new `Size` row if none.
4. **Build canonical `short_name`** = `"Lava Stone {size_label}"` (e.g. `"Lava Stone 5×20×1.2"`).
5. **Lookup Material** by exact `short_name` match (filtered to `material_type='stone'`). Match if found.
6. **No match** → return `suggested_short_name`, `suggested_typology`, `suggested_size_id` so user can confirm/create with one click.

Token-fuzzy matching is reserved for non-stone (legacy `find_best_match` path). Stone uses direct `short_name` equality after canonicalization — no fuzzy scoring, no thresholds.

### Endpoints
- `POST /delivery/process-photo` — OCR + matching, returns items with `parsed_*` fields and `suggested_short_name`.
- `POST /delivery/create-material-from-scan` — creates `Material` + `Size` from scan-parsed payload, returns `material_id` ready for receipt transaction.
- `POST /materials/transactions` — accepts the receipt; stores `delivery_name` (raw OCR text) for history.

### Frontend
- `presentation/dashboard/src/components/material/TypologySelector.tsx` — 5-button picker.
- `.../SizeInput.tsx` — dimensions input with shape-aware fields.
- `.../NamePreview.tsx` — live `short_name` preview.
- "Scan Delivery Note" dialog: each row is inline-editable (name / typology / size), with "Create & match" button per row.
- Telegram bot: same rules, kg-button hidden for stone, pcs-button hidden for pigment/frit.

### Migration & backfill
Alembic `026_material_short_name_typology.py`:
- ADD `materials.short_name`, `sizes.diameter_mm`, `material_transactions.delivery_name`.
- Backfill: for `material_type='stone'`, derive `short_name` from existing `name` via parser; default to `name` for non-stone.
- Map legacy `product_subtype` values: `tiles→tiles`, `sinks→sink`, `table_top→countertop`, `custom→freeform`.

### 3D design picker (addendum)

3D tiles of identical geometry can still differ by **design** (e.g. "Дизайн 1"
and "Дизайн 2" sharing `5×20×1-2`). Materials are therefore discriminated on
`(size_id, product_subtype='3d', design_id)` — enforced by the partial unique
index `uq_materials_size_typology_design` (see `stone_designs_patch`).

**Delivery matching rule for 3D:** the matcher refuses auto-match — delivery
notes rarely name the design, and picking "the first material with this
short_name" would silently corrupt the wrong balance. Instead the matcher
returns `needs_design_choice=true`; the UI/bot presents a design picker and
only after a choice (existing design / new design / no design) does it
find-or-create the Material for `(size_id, '3d', design_id)` and record the
receipt transaction against it.

Where implemented:
- `business/services/material_matcher.py` — `needs_design_choice` flag; `matched=false` forced for 3D.
- `business/services/telegram_bot.py` — `_send_design_picker` + `ddesign:*` callback + `_resolve_material_for_design` find-or-create.
- Web "Scan Delivery Note" uses the existing `DesignPicker` component — see `presentation/dashboard/src/components/material/DesignPicker.tsx`.

---

## §30 Status Machine vs Business Endpoints (2026-04-25)

### Зачем эта глава

Запросы на смену статуса позиции идут двумя путями, и **их нельзя путать**:

1. **`POST /positions/{id}/status`** — это **enum-bypass endpoint для администрирования**. Он просто переключает поле `status` через `transition_position_status()` + вызывает `on_glazing_start` для consumption-стадий. Никаких других side-effects.
2. **Бизнес-endpoints** (`/pack`, `/ship`, `/qc`, `/sort`, `/process-firing`) — выполняют **полную бизнес-операцию** со всеми побочными эффектами: загрузка фото, создание `Shipment` / `BoxAssignment` / `QualityCheck` записей, списание упаковки, валидация правил и т.д.

**Без этого правила** возникает «фантомное прохождение»: позиция помечена как `packed`, но коробок не списано, фото нет, packaging rules не проверены. Это и нашли на проде 25 апреля 2026 — все 12 столов «отгружены», камень и коробки на месте, никаких записей.

### Правила доступа к `/positions/{id}/status`

| Роль | Может прыгнуть напрямую в `packed` / `ready_for_shipment` / `shipped` / `quality_check_done` ? |
|---|---|
| `owner` | ✅ Да, без подтверждения. Override mode для исправления данных. |
| `administrator` | ✅ Да, без подтверждения. То же самое. |
| `production_manager` | ⚠️ Да, но **система требует confirm-флаг** в payload (`override=true`) И обязательно пишет audit-log с указанием PM, before/after status, timestamp, опциональной причиной. |
| `quality_manager`, `warehouse`, `sorter_packer`, `purchaser`, прочие | ❌ Нет. Прямой переход в эти статусы запрещён, должны идти через бизнес-endpoint. |

Промежуточные статусы (`engobe_applied`, `glazed`, `loaded_in_kiln`, `fired`, `transferred_to_sorting`, `sorted`) можно ставить через `/status` всем management-ролям без override-флага — это нормальный workflow для мастеров (нет отдельного `/glaze` endpoint, все эти переходы идут через master button «Я сделал»).

**Реализация:**
- `business/services/status_machine.py` — добавить проверку `_BYPASS_PROTECTED_STATUSES = {PACKED, READY_FOR_SHIPMENT, SHIPPED, QUALITY_CHECK_DONE}` + role-aware gate с обязательным `override` для PM.
- `api/routers/positions.py:change_position_status` — пробрасывать `override` flag из payload.
- `api/middleware/audit.py` (или новая) — логировать каждый override в `AuditLog` (already exists в проекте).

### Reference на бизнес-endpoints (когда что использовать)

| Целевой статус | Бизнес-endpoint | Что обязан сделать |
|---|---|---|
| `packed` | `POST /positions/{id}/pack` | photo upload + check `PackagingBoxCapacity` + `MaterialTransaction(consume)` для боксов + `packed_at` |
| `ready_for_shipment` | автоматически после `packed` (логика в /pack) | флаг готовности |
| `shipped` | `POST /shipments/{id}/ship` (через Shipment агрегат) | `ShipmentItem` строка + `shipped_at` + (для нескольких pos одной перевозки — единая Shipment запись) |
| `quality_check_done` | `POST /positions/{id}/quality-check` (или эквивалент в QC модуле) | `QualityCheck` запись + photo + результат (good/defect/refire) |

---

## §31 Packing Rules (2026-04-25)

### Бизнес-правило

Каждый активный `Size` в каталоге обязан иметь хотя бы одну запись `PackagingBoxCapacity` (= для какой коробки сколько штук этого размера помещается). Без этой записи **физически нельзя упаковать** позицию — мы не знаем какие коробки и сколько брать со склада.

### Что должно происходить при `POST /positions/{id}/pack`

1. **Проверка наличия rule:** найти `PackagingBoxCapacity` для `position.size_id`. Если нет → **HTTP 400** + создать blocking task `PACKAGING_RULES_NEEDED` для PM с описанием «Заведи packaging rules для размера X». Позиция **остаётся в `sorted`**, не переходит в `packed`.
2. **Проверка наличия фото:** `position.packing_photos` должен иметь минимум 1 файл (uploaded через UI). Если нет → HTTP 400 «Загрузи фото упаковки».
3. **Проверка остатка боксов:** для каждого box-материала из правила — проверить `MaterialStock.balance ≥ required_qty`. Если нет — blocking task `BOX_INSUFFICIENT` для PM, позиция остаётся в `sorted`.
4. **Side-effects при успехе:**
   - `MaterialTransaction(type=CONSUME)` для каждого box-материала по правилу.
   - `MaterialStock.balance -= consumed_qty`.
   - `position.packed_at = now()`.
   - `position.status = PACKED`.
   - `BoxAssignment` запись (какие коробки, сколько штук).

### Что должно происходить при `POST /shipments/{id}/ship`

1. **Минимум 1 ShipmentItem** — иначе HTTP 400.
2. **Все позиции в Shipment должны быть в `packed`** — иначе HTTP 400.
3. **Side-effects при успехе:**
   - `Shipment.shipped_at = now()`.
   - Для каждого ShipmentItem: `position.shipped_at = now()`, `position.status = SHIPPED`.
   - Создать carrier-документ (PDF), сохранить в Shipment.

### Audit для существующих positions

Скрипт `scripts/audit_packing_rules_coverage.py` (создать) проходит по всем активным `Size`'ам и для каждого проверяет наличие `PackagingBoxCapacity`. Возвращает список Size'ов без правил. Для каждого автоматически создаёт blocking task PM (одна задача на size, не на каждую позицию).

### Side-effects checklist для статуса `packed` / `shipped` (расширение §2)

Контрольный список «формально или реально прошло» — для последующих audit-проходов:

| Хочешь убедиться, что позиция реально `packed` | Проверь что |
|---|---|
| `position.packed_at IS NOT NULL` | ✓ |
| `position.packing_photos.count() ≥ 1` | ✓ |
| `MaterialTransaction WHERE position_id=X AND type='consume' AND material.material_type='packaging'` существует | ✓ |
| `BoxAssignment WHERE position_id=X` существует | ✓ |

| Хочешь убедиться, что позиция реально `shipped` | Проверь что |
|---|---|
| `position.shipped_at IS NOT NULL` | ✓ |
| `ShipmentItem WHERE position_id=X` существует | ✓ |
| `Shipment.shipped_at IS NOT NULL` | ✓ |

Если хоть одна строка не выполняется — позиция **формально в статусе, реально процесс не пройден**. Owner / Admin override должен явно фиксироваться в `AuditLog` с указанием причины.

---

## §2.6 Express Mode — Material Tracking Disabled (owner override)

**Назначение.** Иногда заказ невозможно или невыгодно проводить через стандартный материальный учёт: уникальный камень индивидуального размера (не повторится), пробная партия, ремонт по гарантии, давальческое сырьё клиента. Для таких случаев есть «Express mode» — заказ ведётся по статусам, но **без резервирования и списания материалов**. Это owner-level override: владелец берёт ответственность за инвентарь вне системы.

### Поля на `production_orders`

| Колонка | Тип | Назначение |
|---|---|---|
| `material_tracking_disabled` | `boolean NOT NULL DEFAULT false` | Флаг "express". Write-once: после `true` — обратно `false` нельзя без миграции. |
| `material_tracking_disabled_reason` | `text` | Обязательная причина. Хранится для аудита и отчётов OPEX. |
| `material_tracking_disabled_at` | `timestamptz` | Когда включили. |
| `material_tracking_disabled_by` | `uuid → users.id` | Кто включил. |

### Поведение при `material_tracking_disabled = true`

1. **`reserve_materials_for_position`** — early return. Не создаёт `MaterialTransaction(type=RESERVE)`. Не выставляет `INSUFFICIENT_MATERIALS`. Если резервы уже были — снимаются (через `unreserve_materials_for_position`).
2. **`on_glazing_start` / `consume_refire_materials`** — early return. Не создаёт `MaterialTransaction(type=CONSUME)`. Stock balances не двигаются.
3. **`materials_written_off_at`** ставится в момент включения флага (для всех уже созданных позиций), чтобы статус-машина никогда не пыталась повторно вызвать consume.
4. **Position status** — owner может через тот же fast-track перевести позиции сразу в любой целевой статус (типично `loaded_in_kiln` или `fired`), state-machine validation пропускается (override).
5. **Audit** — security_event + Task с `metadata_json.action = "fast_track"` создаются на каждое включение. Telegram CEO/Owner.
6. **UI** — на карточке заказа крупный бейдж `📦🚫 EXPRESS — без учёта материалов` + причина. В отчётах OPEX и материальном расходе такие заказы выделяются отдельной строкой.

### Что НЕ затрагивает Express mode

- Все остальные стадии работают как обычно: planning, kiln assignment, QC, sorting, packing, shipping. Списываются только packaging-материалы (на этапе `packed`), потому что без коробок физически отгрузить нельзя — и клиенту это видно.
- Финансовые проводки (если есть) — работают штатно.
- Telegram-уведомления и role-based access — работают штатно.

### Проверки целостности (audit)

Аналог §2 «формально vs реально». Для express-заказов:

| Хочешь убедиться, что заказ реально проведён без учёта | Проверь что |
|---|---|
| `production_orders.material_tracking_disabled = true` | ✓ |
| `production_orders.material_tracking_disabled_reason IS NOT NULL` | ✓ |
| Для каждой `OrderPosition`: `materials_written_off_at IS NOT NULL` | ✓ |
| Нет `MaterialTransaction(type IN ('reserve','consume')) WHERE related_order_id = X` (кроме packaging) | ✓ |
| В `Task` есть запись `metadata_json.action = 'fast_track' AND related_order_id = X` | ✓ |

Если хоть одна строка не выполняется — express был включён криво. Чинить вручную.

### Endpoint

`POST /api/orders/{id}/fast-track`

Body:
```json
{ "reason": "string (required)", "target_status": "loaded_in_kiln | fired | planned | ..." (optional) }
```

Roles: `owner | administrator | ceo` (CEO — временно, см. `docs/TEMPORARY_DELEGATIONS.md`).

Returns: `{ order_id, positions_updated, reservations_released, target_status }`.

### Когда НЕ использовать

- Серийный продукт со стандартными размерами — нужен нормальный учёт.
- Когда не хватает материала на складе и хочется «обойти» — это путь `Force Unblock → proceed_with_available` (с уходом баланса в минус), а не Express. Express значит «учёт по этому заказу не нужен в принципе», а не «закрыть глаза на дефицит».
- Если непонятно «почему именно express, а не нормальный путь» — значит надо нормальный путь.
