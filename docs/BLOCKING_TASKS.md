# Blocking Tasks — Complete Analysis

> Generated 2026-04-06. Covers every TaskType that can be created with `blocking=True`,
> the trigger conditions, the PositionStatus it blocks, auto-resolution paths,
> and Smart Force Unblock options.

---

## Overview

Blocking tasks are the system's mechanism for pausing position progress when
a prerequisite is missing. A blocking task:

1. Sets the position to a **blocking PositionStatus** (e.g. `awaiting_recipe`).
2. Creates a **Task** record with `blocking=True` linked to the position.
3. Prevents the position from transitioning forward until the task is resolved.

Resolution happens in three ways:
- **Auto-resolve**: system detects the prerequisite is satisfied (e.g. materials arrive).
- **Manual resolve**: PM/admin marks the task as DONE and transitions the position.
- **Force unblock**: PM uses Smart Force Unblock with 3 context-aware options per type.

---

## Blocking Task Types

### 1. RECIPE_CONFIGURATION

| Field | Value |
|-------|-------|
| **TaskType** | `recipe_configuration` |
| **Created by** | `business/services/order_intake.py` — `process_order_item()` |
| **Trigger** | No matching recipe found for position's collection/color/size during order intake |
| **Blocks position to** | `PositionStatus.AWAITING_RECIPE` |
| **Assigned to** | Production Manager (implicit, no explicit role set) |
| **Auto-resolves** | No. PM must create/assign a recipe, then reprocess the order (`POST /orders/{id}/reprocess`) |
| **Force Unblock options** | Via `awaiting_recipe` options: |
| | 1. **Create new recipe** — opens recipe creation with pre-filled position data |
| | 2. **Use existing recipe** — select and assign from existing recipe list |
| | 3. **Proceed without recipe** (danger) — force to PLANNED, PM takes responsibility |

---

### 2. STENCIL_ORDER

| Field | Value |
|-------|-------|
| **TaskType** | `stencil_order` |
| **Created by** | `business/services/order_intake.py` — `check_blocking_tasks()` |
| **Trigger** | Position collection or application_type contains "stencil" |
| **Blocks position to** | `PositionStatus.AWAITING_STENCIL_SILKSCREEN` (only if timing-urgent per `service_blocking.should_block_for_service`) |
| **Assigned to** | `UserRole.PRODUCTION_MANAGER` |
| **Timing logic** | Task always created. Position blocked only when `service_lead_time >= days_until_planned_glazing`. If no glazing date yet, blocking is deferred; APScheduler's `check_pending_service_blocks` re-evaluates daily. |
| **Auto-resolves** | No. PM marks stencil as received and closes the task. |
| **Force Unblock options** | Via `awaiting_stencil_silkscreen` options: |
| | 1. **Stencil ready** — mark as available, close blocking task |
| | 2. **Use alternative stencil** — select substitute |
| | 3. **Skip stencil step** (danger) — proceed without stencil |

Also created by `business/services/service_blocking.py` — `block_position_for_service()` with service_type='stencil', which includes deadline calculation (`due_at = planned_glazing - lead_time`).

---

### 3. SILK_SCREEN_ORDER

| Field | Value |
|-------|-------|
| **TaskType** | `silk_screen_order` |
| **Created by** | `business/services/order_intake.py` — `check_blocking_tasks()` |
| **Trigger** | Position collection contains "silkscreen" or "silk screen", or application_type contains "silkscreen" |
| **Blocks position to** | `PositionStatus.AWAITING_STENCIL_SILKSCREEN` (same status as stencil, timing-gated) |
| **Assigned to** | `UserRole.PRODUCTION_MANAGER` |
| **Timing logic** | Same as STENCIL_ORDER — service_lead_time default 5 days |
| **Auto-resolves** | No. PM marks silkscreen as received. |
| **Force Unblock options** | Same as STENCIL_ORDER (`awaiting_stencil_silkscreen` options) |

---

### 4. COLOR_MATCHING

| Field | Value |
|-------|-------|
| **TaskType** | `color_matching` |
| **Created by** | `business/services/order_intake.py` — `check_blocking_tasks()` |
| **Trigger** | Position collection contains "custom" OR `color_2` is set (multi-color product) |
| **Blocks position to** | `PositionStatus.AWAITING_COLOR_MATCHING` (timing-gated, only if no other blocking already applied) |
| **Assigned to** | `UserRole.PRODUCTION_MANAGER` |
| **Timing logic** | Default lead time: 2 days. Same should_block_for_service logic. |
| **Auto-resolves** | No. PM confirms color match. |
| **Force Unblock options** | Via `awaiting_color_matching` options: |
| | 1. **Color approved** — PM confirms match is acceptable |
| | 2. **Adjust color** — create recipe adjustment task |
| | 3. **Proceed as-is** (danger) — force to PLANNED |

---

### 5. CONSUMPTION_MEASUREMENT

| Field | Value |
|-------|-------|
| **TaskType** | `consumption_measurement` |
| **Created by** | `business/services/order_intake.py` — `_check_consumption_rates()` |
| **Trigger** | Recipe exists but is missing consumption rate data for the required application method (spray/brush rates). E.g., method BS requires brush_rate for engobe and spray_rate for glaze — if either is NULL, this task is created. |
| **Blocks position to** | `PositionStatus.AWAITING_CONSUMPTION_DATA` |
| **Assigned to** | `UserRole.PRODUCTION_MANAGER` |
| **Auto-resolves** | No. PM must physically measure consumption rates and enter them in the recipe, then reprocess. |
| **Force Unblock options** | Via `awaiting_consumption_data` options: |
| | 1. **Enter rates now** — PM provides spray/brush rates inline |
| | 2. **Use default rates** — apply factory default consumption rates |
| | 3. **Skip consumption check** (danger) — proceed without rates |

Metadata includes: `recipe_id`, `recipe_name`, `application_method`, `missing_rates[]`.

---

### 6. SIZE_RESOLUTION

| Field | Value |
|-------|-------|
| **TaskType** | `size_resolution` |
| **Created by** | `business/services/size_resolution.py` — `create_size_resolution_task()` |
| **Trigger** | Position dimensions don't match any Size record (`no_match`), match multiple sizes (`multiple_matches`), or dimensions can't be extracted (`missing_dimensions`) |
| **Blocks position to** | `PositionStatus.AWAITING_SIZE_CONFIRMATION` |
| **Assigned to** | `UserRole.ADMINISTRATOR` |
| **Auto-resolves** | No. Admin must confirm/create the correct size. |
| **Force Unblock options** | Via `awaiting_size_confirmation` options: |
| | 1. **Size confirmed** — PM confirms dimensions are correct |
| | 2. **Adjust dimensions** — PM provides correct dimensions |
| | 3. **Custom size** — create custom size entry |

Metadata includes: `reason`, `candidates[]`, `position_size_string`, `position_shape`, dimensions.

Note: When a size is auto-created, a non-blocking SIZE_RESOLUTION task is created for PM approval.

---

### 7. MATERIAL_ORDER (non-stone shortage)

| Field | Value |
|-------|-------|
| **TaskType** | `material_order` |
| **Created by** | `business/services/material_reservation.py` — `sync_material_procurement_task()`, called at the tail of `reserve_materials_for_position()` (and therefore on every order intake AND every scheduler recalc / reserve attempt). |
| **Trigger** | `reserve_materials_for_position` returns shortages for any material that is **not** stone (stone goes to `STONE_PROCUREMENT`). |
| **Blocks position to** | `PositionStatus.INSUFFICIENT_MATERIALS` (set elsewhere — this task is purely the purchaser-facing counterpart). |
| **Assigned to** | `UserRole.PURCHASER`, `blocking=True` |
| **Granularity** | **One task per position**, aggregating ALL non-stone shortages for that position (pigment + frit + bulk + …). Re-runs update the same task in place. |
| **Auto-resolves** | **Yes.** When shortage clears (stock received, recipe changed, position split), the next call to `reserve_materials_for_position` detects empty non-stone shortage list → flips `status = DONE`. |
| **due_at (ETA)** | `today + max(lead_days)` across all shortages in the task. Per-material lead days resolved in order: `Material.supplier.default_lead_time_days` → per-type default (`pigment=7`, `frit/oxide/other_bulk/other=14`, `consumable/packaging=7`) → fallback `14`. |
| **ETA is monotone forward** | If the task already has a later `due_at` (e.g. purchaser manually set a confirmed delivery date), auto-recalc **does not** push it back. Only extends. |
| **Scheduler integration** | `production_scheduler._get_blocking_task_ready_date` reads `Task.due_at` → becomes `material_ready_date` for the position → planner doesn't start glazing before that date. |
| **Force Unblock options** | Via `insufficient_materials` options (unchanged): 1) proceed with available stock, 2) wait for delivery, 3) substitute material. |
| **Untracked utilities** | Materials in `_UNTRACKED_UTILITY_NAMES` (water / вода) never generate this task — they're skipped in reservation entirely. |

Metadata includes: `materials[]` (name, type, required/available/deficit), `lead_days_max`, `lead_days_by_material`.

The force-reserve path calls `force_reserve_materials()` which creates RESERVE transactions regardless of balance, tracking negative balances in the `negative_balances` table.

---

### 8. STONE_PROCUREMENT

| Field | Value |
|-------|-------|
| **TaskType** | `stone_procurement` |
| **Created by** | `business/services/stone_reservation.py` — `_check_stone_stock_and_create_task()` (invoked during `reserve_stone_for_position`, runs on order intake and on every reserve/recalc). |
| **Trigger** | Position reserves stone but matched stone material at this factory has `effective_available < reserved_sqm` (after subtracting other active stone reservations for the same size). |
| **Blocks position to** | `PositionStatus.INSUFFICIENT_MATERIALS` when current status is in the blockable set (`planned`, `awaiting_recipe`, `awaiting_stencil_silkscreen`, `awaiting_color_matching`, `awaiting_consumption_data`). |
| **Assigned to** | `UserRole.PURCHASER`, `blocking=True` |
| **Granularity** | One task per position. Dedup via `(related_position_id, type, status ∈ {pending, in_progress})`. Re-runs update description + `due_at` in place. |
| **Auto-resolves** | Not automatically — purchaser must procure stone and receive into warehouse. Warehouse receipt triggers `check_and_unblock_positions_after_receive`. |
| **due_at (ETA)** | `today + lead_days`. `lead_days = matching_stone.supplier.default_lead_time_days` if supplier linked, else **35 days** (Bali stone default, `STONE_DEFAULT_LEAD_DAYS`). |
| **ETA is monotone forward** | Same as MATERIAL_ORDER — existing later `due_at` is never pushed back by auto-recalc. |
| **Scheduler integration** | Same — `production_scheduler` reads `Task.due_at` and anchors `material_ready_date` to it. |
| **Force Unblock options** | No specific Smart Unblock options (covered under `insufficient_materials` if position gets blocked). |

Metadata includes: `reserved_sqm`, `available_sqm`, `deficit_sqm`, `quantity`, `stone_defect_pct`, `lead_days`, `lead_source` (supplier name or "default lead time").

---

### 9. QUALITY_CHECK

| Field | Value |
|-------|-------|
| **TaskType** | `quality_check` |
| **Created by** | `business/services/quality_control.py` — three scenarios: |
| | a) `create_qc_tasks()` — batch QC after firing (positions entering TRANSFERRED_TO_SORTING) |
| | b) `report_critical_defect()` — critical defect found during inspection, blocks position |
| | c) `qm_block_position()` — QM manually blocks a position for quality investigation |
| **Blocks position to** | `PositionStatus.BLOCKED_BY_QM` (for critical defects and manual blocks) |
| **Assigned to** | `UserRole.QUALITY_MANAGER` (scenario a) or `UserRole.PRODUCTION_MANAGER` (scenarios b, c — PM notification) |
| **Auto-resolves** | No. QM must inspect, make a disposition decision (pass/fail/rework). |
| **Force Unblock options** | Via `blocked_by_qm` options: |
| | 1. **QM approved** — override QM block, quality manager approved |
| | 2. **Rework** — send back to previous stage for rework |
| | 3. **Scrap** (danger) — mark as defective, cancel position, and write off |

The "scrap" option triggers `position.status = CANCELLED` and creates a write-off audit trail.

---

### 10. KILN_MAINTENANCE

| Field | Value |
|-------|-------|
| **TaskType** | `kiln_maintenance` |
| **Created by** | `business/services/kiln_breakdown.py` — kiln emergency breakdown handler |
| **Trigger** | Kiln status changes to `MAINTENANCE_EMERGENCY`. All positions assigned to that kiln's batches need reassignment. |
| **Blocks position to** | Does not change position status directly. Blocks batch progression — positions in LOADED_IN_KILN remain stuck until kiln is repaired or positions are reassigned to another kiln. |
| **Assigned to** | `UserRole.PRODUCTION_MANAGER` |
| **Priority** | 10 (highest) |
| **Auto-resolves** | No. PM must either repair kiln or manually reassign positions to other kilns. |
| **Force Unblock options** | No specific Smart Unblock options (not a PositionStatus-level block) |

Metadata includes: affected kiln_id, batch IDs, position count, estimated downtime.

---

### 11. PACKING_MATERIALS_NEEDED

| Field | Value |
|-------|-------|
| **TaskType** | `packing_materials_needed` |
| **Created by** | `business/services/packaging_consumption.py` — `check_packing_materials()` (called via `on_sorting_start()`) |
| **Trigger** | Position enters TRANSFERRED_TO_SORTING and packaging material check finds shortages (boxes, spacers insufficient in stock) |
| **Blocks position to** | Does NOT change position status — task is a warning so warehouse restocks before packing begins |
| **Assigned to** | `warehouse` role |
| **Priority** | 2 |
| **Auto-resolves** | Yes! `auto_resolve_packing_tasks()` is called after material receive transactions. It checks all open PACKING_MATERIALS_NEEDED tasks and marks them DONE when stock is sufficient. |
| **Force Unblock options** | No specific Smart Unblock options (warning task, not position-level block) |

Metadata includes: `shortages[]` (material_name, needed, available, deficit), `boxes_needed`, `box_type`.

---

### 12. FIRING_PROFILE_NEEDED

| Field | Value |
|-------|-------|
| **TaskType** | `firing_profile_needed` |
| **Created by** | `business/services/production_scheduler.py` — `_check_firing_profile_data()` |
| **Trigger** | During scheduling, no `StageTypologySpeed` record found for stage='firing' for the position's typology. The scheduler uses a 1-day fallback but creates this task. |
| **Blocks position to** | `blocking=False` initially — not immediately blocking. Can escalate to blocking if position reaches kiln date without resolution. |
| **Assigned to** | `UserRole.PRODUCTION_MANAGER` |
| **Priority** | 7 |
| **Due date** | `planned_kiln_date - 1 day` |
| **Auto-resolves** | No. PM must configure StageTypologySpeed records for the 'firing' stage. |
| **Force Unblock options** | N/A (not blocking by default) |

Metadata includes: `typology_id`, `typology_name`, `planned_kiln_date`, `reason`.

---

### 13. TYPOLOGY_SPEEDS_NEEDED

| Field | Value |
|-------|-------|
| **TaskType** | `typology_speeds_needed` |
| **Created by** | `business/services/production_scheduler.py` — auto-created when a new typology is auto-generated for a position with no matching existing typology |
| **Trigger** | `find_matching_typology()` creates a new `KilnLoadingTypology` auto-entry, and no `StageTypologySpeed` records exist for it |
| **Blocks position to** | `blocking=False` — informational task, not blocking |
| **Assigned to** | `UserRole.PRODUCTION_MANAGER` |
| **Priority** | 6 |
| **Auto-resolves** | No. PM must configure stage speeds for the new typology. |
| **Force Unblock options** | N/A (not blocking) |

Metadata includes: `typology_id`, `typology_name`, `nearest_typologies[]` for reference.

---

### 14. BOARD_ORDER_NEEDED

| Field | Value |
|-------|-------|
| **TaskType** | `board_order_needed` |
| **Created by** | `business/services/production_scheduler.py` — `_create_board_order_task()` |
| **Trigger** | Glazing board capacity check during scheduling finds a deficit (more boards needed than available) |
| **Blocks position to** | `blocking=False` — non-blocking advisory task |
| **Assigned to** | `UserRole.PRODUCTION_MANAGER` |
| **Priority** | 6 |
| **Auto-resolves** | No. PM must order or prepare additional glazing boards. |
| **Force Unblock options** | N/A (not blocking) |

Deduplication: skips creation if a PENDING task already exists for the same factory.

---

### 15. SHELF_REPLACEMENT_NEEDED

| Field | Value |
|-------|-------|
| **TaskType** | `shelf_replacement_needed` |
| **Created by** | Kiln shelf write-off flow (when shelf is written off and factory stock drops critically low) |
| **Blocks position to** | Non-blocking — advisory for PM |
| **Assigned to** | Production Manager |
| **Auto-resolves** | No |
| **Force Unblock options** | N/A |

---

## Non-Blocking Task Types (for completeness)

These TaskType values create tasks but are NOT typically blocking:

| TaskType | Purpose | Created by |
|----------|---------|------------|
| `showroom_transfer` | Transfer items to showroom | Surplus handling |
| `photographing` | Product photography needed | Order workflow |
| `mana_confirmation` | Mana (Bali) confirmation | Order workflow |
| `packing_photo` | Packing photo documentation | Packing workflow |
| `repair_sla_alert` | Repair exceeds SLA | Repair monitoring |
| `reconciliation_alert` | Stock reconciliation discrepancy | Reconciliation |
| `stock_shortage` | General stock shortage alert | Min balance check |
| `stock_transfer` | Inter-factory stock transfer | Warehouse ops |
| `material_receiving` | Material delivery expected | Purchase lifecycle |
| `glazing_board_needed` | Glazing board procurement | Production line |
| `deadline_exceeded` | Position missed its deadline | Scheduling |

---

## Status Machine — Blocking Transitions

The `_TRANSITIONS` dict in `status_machine.py` defines which blocking statuses
can transition back to `PLANNED` (the only forward path from a block):

```
INSUFFICIENT_MATERIALS  --> PLANNED
AWAITING_RECIPE         --> PLANNED
AWAITING_STENCIL_SILKSCREEN --> PLANNED
AWAITING_COLOR_MATCHING --> PLANNED
AWAITING_SIZE_CONFIRMATION --> PLANNED
AWAITING_CONSUMPTION_DATA --> PLANNED
BLOCKED_BY_QM           --> (any status, returns to status_before_block)
```

All blocking statuses trigger rescheduling via `reschedule_position()` in the status machine.

---

## Smart Force Unblock — Flow Summary

1. PM clicks "Force Unblock" on a blocked position
2. Frontend calls `GET /positions/{id}/force-unblock-options` to get 3 context-aware options
3. PM selects an option and provides mandatory notes (audit trail)
4. Frontend calls `POST /positions/{id}/force-unblock` with `{option, notes}`
5. Backend:
   - Closes all open blocking tasks for this position (status -> DONE)
   - If `insufficient_materials` + `proceed_with_available`: calls `force_reserve_materials()` (can create negative balances)
   - If `blocked_by_qm` + `scrap`: cancels position, creates write-off
   - Otherwise: transitions position to PLANNED
   - Creates audit Task with `mana_confirmation` type
   - Sends Telegram notification to CEO/Owner with full details
   - Triggers `reschedule_position()` to recalculate dates
6. Priority boost: `priority_order += 10` on unblocked position

Every force unblock is audited with: who, when, which option, notes, and CEO is always notified via Telegram.
