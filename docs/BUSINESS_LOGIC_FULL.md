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
- `check_and_unblock_positions_after_receive(db, factory_id, material_id)` — After material receipt, checks if any INSUFFICIENT_MATERIALS positions can now be unblocked.

### Business Rules
1. Consumption rate lookup: ConsumptionRule > recipe.consumption_spray/brush > recipe_material rates.
2. Application method (spray/brush/splash/silk_screen) determines which rate to use.
3. Engobe is consumed separately from glaze (needs_engobe flag on ApplicationMethod).
4. Area calculation uses `glazeable_sqm` from position or recalculates via surface_area service.
5. Defect margin pieces are included in reservation.

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

---

## 4. Backward Scheduling (TOC/DBR)

**File:** `production_scheduler.py` (~568 lines)
**Called by:** `order_intake.py`, `schedule.router`, `kilns.router`

### Purpose
Backward-schedules positions from deadline to today using TOC/DBR (Drum-Buffer-Rope). Kiln is the constraint (drum).

### Key Functions

- `schedule_position(db, position)` — Backward from deadline: completion -> sorting -> kiln -> glazing. Skips weekends. Finds best kiln.
- `find_best_kiln(db, factory_id, target_date, position)` — Selects kiln: filters by temperature compatibility, checks maintenance windows, balances load.
- `schedule_order(db, order)` — Schedules all positions in an order.
- `reschedule_position(db, position)` — Re-run scheduling for a single position.
- `reschedule_affected_by_kiln(db, kiln_id)` — Reschedule all positions assigned to a kiln (e.g., after breakdown).
- `reschedule_factory(db, factory_id)` — Full factory reschedule.
- `get_kiln_maintenance_windows(db, factory_id)` — Returns maintenance windows that block kiln availability.

### Business Rules
1. Working days only (Monday-Saturday by default, per factory_calendar).
2. Buffer days added between glazing and kiln based on `buffer_target_hours`.
3. Rope limit: max positions released per day (prevents overload before constraint).
4. Kiln assignment considers: temperature group compatibility, maintenance windows, current load balance.

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
