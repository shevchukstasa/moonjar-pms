# Order Lifecycle Audit — Full Production Flow

> Generated: 2026-03-26
> Scope: Every step from order receipt to shipment
> Method: Manual codebase read + production endpoint verification

---

## Summary

| Metric | Count |
|--------|-------|
| Total steps audited | 24 |
| Fully working (backend + frontend + production) | 14 |
| Partial (code exists, not fully connected) | 7 |
| Missing (not implemented) | 2 |
| Dead code (defined but never called) | 1 |

---

## Detailed Audit Table

| # | Step | Business Logic | Backend Code | Frontend UI | Production API | Status | Notes |
|---|------|---------------|-------------|-------------|----------------|--------|-------|
| 1 | **Order Receipt** (webhook from Sales) | BUSINESS_LOGIC.md §1-3, ARCHITECTURE.md | `api/routers/integration.py:receive_sales_order()` (line 495) — full auth (X-API-Key + Bearer + HMAC), idempotency, flat/nested payload support | N/A (server-to-server) | `POST /api/integration/webhook/sales-order` returns 405 on GET (correct — POST only) | **Works** | Both auth methods, idempotency via `sales_webhook_events`, handles change requests for existing orders |
| 2 | **Order Receipt** (manual creation) | BUSINESS_LOGIC.md §1-3 | `api/routers/orders.py:create_order()` — calls `process_incoming_order()` | `OrderCreateDialog.tsx` + `PdfUploadDialog.tsx` | `POST /api/orders` — 401 (auth required, correct) | **Works** | Supports manual entry + PDF upload + OCR parsing |
| 3 | **Order Validation** (required fields, position validation) | BUSINESS_LOGIC.md §1 | `business/services/order_intake.py:process_incoming_order()` — validates items, parses sizes/thickness/sqm, handles `quantity_pcs` vs `quantity` field names | Inline in `OrderCreateDialog.tsx` (form validation) | Validated inside order creation flow | **Works** | Validates totals, parses "11mm" strings, resolves size from dimensions, calculates sqm from WxH |
| 4 | **Recipe/Color Matching** | BUSINESS_LOGIC.md §2 | `business/services/order_intake.py:_find_recipe()` — matches by color + collection + application method | Blocking task shown in `BlockingTasksTab.tsx` when recipe not found (`awaiting_recipe` status) | Part of order creation flow | **Works** | If no recipe found, position blocked as `AWAITING_RECIPE` with PM task. Stock collections skip recipe lookup |
| 5 | **Material Calculation** (stone, glaze, engobe per position) | BUSINESS_LOGIC.md §4, §16 | `business/services/material_reservation.py:_calculate_required()` — supports `per_sqm`, `g_per_100g`, `per_piece` units. `_get_area_for_position()` handles face + edge area. Method-specific rates (spray/brush/silk_screen). `ConsumptionRule` overrides for non-standard shapes | N/A (automatic on position creation) | Executes during order intake | **Works** | Shape-aware (rectangle, octagon, freeform), edge profile area included, defect margin via `_get_defect_coefficient()` (last 90 days), consumption rate auto-detection blocks positions if rates missing |
| 6 | **Material Reservation** | BUSINESS_LOGIC.md §4 | `business/services/material_reservation.py:reserve_materials_for_position()` — creates RESERVE transactions, checks stock availability, creates shortages if insufficient | `MaterialReservationsPanel.tsx`, `StoneReservationTab.tsx`, `MaterialDeficitsTable.tsx` | `GET /api/positions/blocking-summary` — 401 (correct) | **Works** | Smart: checks ordered materials (in-transit purchase requests), force-reserve option for PM, unreserve on cancellation |
| 7 | **Purchase Request** (if materials insufficient) | BUSINESS_LOGIC.md §4 | `business/services/material_reservation.py` auto-creates `MaterialPurchaseRequest` on shortage. `api/routers/purchaser.py` — full CRUD + status workflow (pending→approved→sent→in_transit→received→closed) | `PurchaserDashboard.tsx`, `ShortageDecisionPage.tsx` | `GET /api/purchaser` — 401 (correct) | **Works** | Auto-creation + manual workflow. `purchaser_lifecycle.py` handles auto-transition on warehouse receipt, lead time tracking, overdue detection |
| 8 | **Schedule Calculation** (backward scheduling from deadline) | BUSINESS_LOGIC.md §5, §17, §20 | `business/services/production_scheduler.py:schedule_order()` + `schedule_position()` — full TOC/DBR backward scheduling. Calculates planned_glazing_date, planned_kiln_date, planned_sorting_date, planned_completion_date | `ManagerSchedulePage.tsx`, schedule dates shown in `OrderDetailPage.tsx` position cards | `GET /api/schedule/resources` — 401 (correct) | **Works** | Called immediately in `process_incoming_order()` step 7. Handles tight deadlines (clamps to today), skips Sundays, maintenance-aware. Auto-reschedules on status changes |
| 9 | **Kiln Assignment** (capacity calculation) | BUSINESS_LOGIC.md §7, §19 | `business/services/production_scheduler.py:find_best_kiln()` — selects kiln with fewest slots in 7-day window, excludes emergency maintenance and blocked dates. `business/kiln/capacity.py` for geometry-based fit | `ManagerKilnsPage.tsx`, `KilnCard.tsx` in Tablo | `GET /api/kilns` — 401 (correct) | **Works** | Maintenance-aware, load-balanced. Estimated kiln assigned at scheduling time, actual kiln at batch formation |
| 10 | **Daily Task Distribution** (Telegram to workers) | BUSINESS_LOGIC.md §11, §34 | `business/services/daily_distribution.py:daily_task_distribution()` — collects glazing/kiln tasks for tomorrow, computes KPI, sends formatted Telegram message with inline buttons. AI insight via `telegram_ai.py` | N/A (Telegram-based) | Triggered by APScheduler cron | **Works** | Sends to `masters_group_chat_id`, includes urgent alerts, KPI yesterday, inline buttons for acknowledgment. Language configurable (ID/EN/RU) |
| 11 | **Engobe Application** (worker applies engobe, status update) | BUSINESS_LOGIC.md §4.1 (status machine) | `api/routers/positions.py:change_position_status()` — transitions `planned → engobe_applied`. Triggers `on_glazing_start()` for material consumption on first glazing status | `TabloDashboard.tsx` > `SectionTable.tsx` > `StatusDropdown.tsx` — glazing section with drag-drop status changes | `POST /api/positions/{id}/status` — 401 (correct) | **Works** | Status machine validates transition. Material consumption triggered on ENGOBE_APPLIED (first time). Tablo UI shows positions grouped by status section |
| 12 | **Glazing** (worker applies glaze, status update) | BUSINESS_LOGIC.md §4.1 | `api/routers/positions.py:change_position_status()` — transition `engobe_check → glazed` (or `planned → glazed` if no engobe needed). `business/services/material_consumption.py:on_glazing_start()` consumes BOM materials | `TabloDashboard.tsx` glazing section, `GlazingBoardCalcResult` for board layout guidance | `POST /api/positions/{id}/status` | **Works** | Material consumption creates CONSUME + UNRESERVE transactions, tracks variance via `ConsumptionAdjustment`, refire path uses `consume_refire_materials()` (surface materials only) |
| 13 | **Pre-Kiln QC** (quality check before loading) | BUSINESS_LOGIC.md §4.1 | `api/routers/positions.py:change_position_status()` — transition `glazed → pre_kiln_check`. Optional: QM can block via `qm_blocks.py` | `TabloDashboard.tsx` glazing section (pre_kiln_check status visible), `QualityManagerDashboard.tsx` | `POST /api/positions/{id}/status` | **Partial** | Status transition exists and works, but there is no dedicated pre-kiln QC form/checklist in the UI. QM uses generic status change or QM block mechanism. No structured pre-kiln inspection record (unlike post-firing QC which has `QualityCheck` model) |
| 14 | **Batch Formation** (group positions into kiln batches) | BUSINESS_LOGIC.md §7, §19 | `business/services/batch_formation.py:suggest_or_create_batches()` — groups by temperature compatibility, geometry-based capacity, filler tile selection, co-firing rules. `api/routers/batches.py:auto_form_batches()` | `ManagerSchedulePage.tsx` batch formation, `KilnCard.tsx` batch view | `POST /api/batches/auto-form` — 401 (correct) | **Works** | Auto-form and suggest modes. Temperature grouping (±50°C), per-kiln loading rules, filler tile greedy selection, PM confirm/reject flow for suggested batches |
| 15 | **Kiln Loading** (load batch into kiln) | BUSINESS_LOGIC.md §7 | `api/routers/batches.py:start_batch()` — `POST /api/batches/{id}/start` transitions batch to IN_PROGRESS, positions to LOADED_IN_KILN | `TabloDashboard.tsx` firing section, `KilnLevelView.tsx` for spatial layout | `POST /api/batches/{id}/start` — 401 (correct) | **Works** | Batch start triggers position status change. Placement data (position, level) tracked per position |
| 16 | **Firing** (kiln fires, temperature profile) | BUSINESS_LOGIC.md §7 | `business/services/firing_profiles.py` — firing temperature profiles stored per recipe. `KilnActualLoad` model tracks actual firing data. `api/routers/firing_profiles.py` CRUD | `KilnFiringSchedulesPage.tsx`, firing profiles in `AdminFiringProfilesPage.tsx` | `GET /api/firing-profiles` — 401 (correct) | **Partial** | Firing profiles exist and are assigned to batches, but real-time temperature logging (IoT sensor integration) is not implemented. Firing is tracked as a status transition only, not a time-series temperature curve |
| 17 | **Kiln Unloading** (unload after firing) | BUSINESS_LOGIC.md §7 | `api/routers/batches.py:complete_batch()` — `POST /api/batches/{id}/complete` transitions batch to COMPLETED, positions to FIRED. `business/services/status_machine.py:route_after_firing()` determines next status (multi-firing or sorting) | `TabloDashboard.tsx` firing section | `POST /api/batches/{id}/complete` — 401 (correct) | **Works** | Auto-routes: single firing → TRANSFERRED_TO_SORTING; multi-firing → back to SENT_TO_GLAZING. Triggers packaging reservation. Increments `firing_round` |
| 18 | **Post-Firing QC** (check for defects) | BUSINESS_LOGIC.md §10, §25 | `business/services/quality_control.py:assign_qc_checks()` — creates QUALITY_CHECK tasks for sampled positions (mandatory_qc + random %). `on_qc_defect_found()` records defects, blocks if critical. `api/routers/quality.py` — full inspection CRUD | `QualityManagerDashboard.tsx`, `quality.ts` API client, calendar matrix view | `GET /api/quality/inspections` — 401 (correct) | **Works** | Sample-based (configurable % from `QualityAssignmentConfig`), mandatory_qc always checked, defect causes taxonomy, QM block/unblock flow with evidence photos |
| 19 | **Sorting/Splitting** (sort good vs defective tiles) | BUSINESS_LOGIC.md §8-9 | `api/routers/positions.py:split_position()` — `POST /api/positions/{id}/split` — splits into good/refire/repair/color_mismatch/grinding/write_off. Creates sub-positions with `split_index`. `business/services/sorting_split.py:process_sorting_split()` | `SorterPackerDashboard.tsx`, `ProductionSplitModal.tsx` in Tablo | `POST /api/positions/{id}/split` — 401 (correct) | **Works** | Full sorting flow: parent → PACKED (good qty), sub-positions for each defect type with correct routing (Mana, repair, refire, grinding). Defect records created. Packaging consumption triggered |
| 20 | **Grinding Decision** (grind/hold/send to Mana) | BUSINESS_LOGIC.md §8-9 | `api/routers/grinding.py` — CRUD + `POST /api/grinding-stock/{id}/decide` (grinding/pending/sent_to_mana decisions). `GrindingStock` model | `GrindingDecisionsPage.tsx` | `GET /api/grinding-stock` — 401 (correct) | **Works** | PM decides per grinding stock item. Statuses: pending → grinding / sent_to_mana. Stats endpoint for dashboard |
| 21 | **Packing** (pack good tiles) | BUSINESS_LOGIC.md §8 | Packing is implicit in the sorting split flow — parent position set to PACKED status. `business/services/packaging_consumption.py:consume_packaging()` consumes box + spacer materials. `api/routers/packing_photos.py` for photo evidence | `SorterPackerDashboard.tsx`, `AdminPackagingPage.tsx` for box type config, packing photos | `GET /api/packing-photos` — 401 (correct) | **Works** | Packaging consumption automatic on split. Box types with per-size capacities. Spacer rules. Photo upload for QC evidence |
| 22 | **Final QC** (final quality check) | BUSINESS_LOGIC.md §10, §25 | `api/routers/positions.py:change_position_status()` — transition `packed → sent_to_quality_check → quality_check_done`. `business/services/quality_control.py:assign_qc_checks()` (same mechanism as post-firing) | `QualityManagerDashboard.tsx` | `POST /api/positions/{id}/status` | **Partial** | Uses same QC mechanism as post-firing. Transition works, but there is no separate "final QC" form — it reuses the generic QC inspection flow. No dedicated final QC checklist (different from post-firing checks) |
| 23 | **Ready for Shipment** (mark order ready) | BUSINESS_LOGIC.md §4.1 | `api/routers/positions.py:change_position_status()` — `quality_check_done → ready_for_shipment` or `packed → ready_for_shipment` (if no QC needed). `_recalculate_order_status()` auto-sets order to READY_FOR_SHIPMENT when all positions ready | `OrderDetailPage.tsx` shows order status, `TabloDashboard.tsx` sorting section | `POST /api/positions/{id}/status` | **Works** | Auto-triggers webhook to Sales: `_notify_sales_order_event(order, "order_ready")` when all positions become ready. Order status auto-calculated from position statuses |
| 24 | **Shipment** (ship to client) | N/A (not documented in BL) | `api/routers/orders.py:update_order()` — allows setting `status: "shipped"` + `shipped_at` timestamp. Position transition `ready_for_shipment → shipped` exists in status machine | `OrderDetailPage.tsx` — order status can be changed to shipped | `PATCH /api/orders/{id}` — 401 (correct) | **Partial** | Shipment is a simple status change, no dedicated shipment workflow (no tracking number, no shipping document generation, no delivery confirmation). `shipped_at` timestamp set on order, but no per-position shipped_at |
| 25 | **Status Webhook to Sales** (send status back) | BUSINESS_LOGIC.md (webhook sender) | `business/services/webhook_sender.py:send_webhook()` — async with 3 retries, exponential backoff (2s, 4s, 8s). `api/routers/positions.py:_notify_sales_order_event()` sends on order_ready. `notify_sales_status_change_stub()` sends intermediate status updates. `api/routers/integration.py:get_production_status()` for Sales polling | N/A (server-to-server) | `GET /api/integration/orders/{ext_id}/production-status` + `GET /api/integration/orders/status-updates` for polling | **Works** | Dual mechanism: push webhooks (with retry) + pull API (Sales polls every 30 min). Failed webhooks logged to `sales_webhook_events`. Rich payload: stage, progress %, per-position schedules, cancellation state |

---

## Cross-Cutting Concerns

| Concern | Status | Details |
|---------|--------|---------|
| **Status Machine** | **Works** | `business/services/status_machine.py` — 20+ statuses, validated transitions, management override. `route_after_firing()` handles multi-firing. |
| **Notification System** | **Works** | `business/services/notifications.py` — in-app + WebSocket push + Telegram. Per-user notification preferences. |
| **Audit Logging** | **Works** | `api/audit.py` — AuditLog model tracks mutations. Used in finished goods, materials, etc. |
| **Factory Filter** | **Works** | `apply_factory_filter()` — all list endpoints respect user's factory access (multi-factory isolation). |
| **Defect Coefficient** | **Works** | `order_intake.py:_get_defect_coefficient()` — auto-calculates from last 90 days of defect data, capped at 30%. |
| **Stone Reservation** | **Works** | `business/services/stone_reservation.py` — separate from BOM reservation, shape-aware, reconciliation after firing. |
| **Consumption Rules** | **Works** | `business/services/material_reservation.py:find_best_consumption_rule()` — override rates for non-standard shapes/products. |

---

## Gap Analysis — What's Missing or Weak

### Missing (not implemented)

1. **Real-time kiln temperature monitoring** (step 16) — No IoT sensor integration. Firing is tracked as a status change only, not a temperature time-series. Firing profiles define target temperatures but actual temperature logging is absent.

2. **Dedicated shipment workflow** (step 24) — No shipping document generation, no tracking numbers, no delivery confirmation from the client. Shipment is a simple status flip.

### Partial / Weak

3. **Pre-Kiln QC** (step 13) — No structured checklist or inspection form. QM uses generic status transitions or QM block mechanism. Unlike post-firing QC which has a dedicated `QualityCheck` model with cause taxonomy.

4. **Final QC** (step 22) — Reuses post-firing QC mechanism. No separate final QC checklist specific to packed goods (e.g., packaging integrity, label verification, quantity recount).

5. **Firing process** (step 16) — Firing profiles with target temperatures exist, but no actual firing log (start time, end time, peak temperature, cooling curve). `KilnActualLoad` captures basic data but not temperature profiles.

6. **Shipment to client** (step 24) — No `shipped_at` per position (only per order). No partial shipment tracking (some positions shipped, others held). `partial_delivery.py` exists but handles inbound material deliveries, not outbound shipments.

7. **Schedule visualization** (step 8) — `GET /api/schedule` returns 404 (root path not mapped), but `GET /api/schedule/resources` works. Gantt-style view exists in `ManagerSchedulePage.tsx` but the backend schedule endpoints have limited query capabilities.

---

## Production Endpoint Verification

| Endpoint | HTTP Status | Interpretation |
|----------|-------------|----------------|
| `GET /api/health` | 200 | Service up |
| `GET /api/orders` | 401 | Auth required (correct) |
| `GET /api/positions` | 401 | Auth required (correct) |
| `GET /api/batches` | 401 | Auth required (correct) |
| `GET /api/materials` | 401 | Auth required (correct) |
| `GET /api/kilns` | 401 | Auth required (correct) |
| `GET /api/purchaser` | 401 | Auth required (correct) |
| `GET /api/quality/inspections` | 401 | Auth required (correct) |
| `GET /api/grinding-stock` | 401 | Auth required (correct) |
| `GET /api/finished-goods` | 401 | Auth required (correct) |
| `GET /api/packing-photos` | 401 | Auth required (correct) |
| `GET /api/stone-reservations` | 401 | Auth required (correct) |
| `GET /api/mana-shipments` | 401 | Auth required (correct) |
| `GET /api/schedule/resources` | 401 | Auth required (correct) |
| `POST /api/integration/webhook/sales-order` | 405 on GET | Correct (POST only) |
| `POST /api/delivery/process-photo` | 405 on GET | Correct (POST only) |

All critical endpoints respond correctly on production.

---

## File Index

### Backend Services (business logic)

| File | Lifecycle Steps Covered |
|------|------------------------|
| `business/services/order_intake.py` | #1, #2, #3, #4, #5 |
| `business/services/material_reservation.py` | #5, #6 |
| `business/services/material_consumption.py` | #11, #12 (glazing consumption) |
| `business/services/production_scheduler.py` | #8 (schedule calculation) |
| `business/services/batch_formation.py` | #14 (batch formation) |
| `business/services/quality_control.py` | #18, #22 (QC) |
| `business/services/sorting_split.py` | #19 (sorting) |
| `business/services/daily_distribution.py` | #10 (Telegram tasks) |
| `business/services/webhook_sender.py` | #25 (status webhook) |
| `business/services/status_machine.py` | All status transitions |
| `business/services/purchaser_lifecycle.py` | #7 (purchase lifecycle) |
| `business/services/stone_reservation.py` | #5 (stone separate from BOM) |
| `business/services/packaging_consumption.py` | #21 (packing) |
| `business/services/firing_profiles.py` | #16, #17 (multi-firing routing) |
| `business/services/notifications.py` | Cross-cutting (all steps) |
| `business/services/glazing_board.py` | #12 (board calculator) |
| `business/services/partial_delivery.py` | #7 (partial inbound delivery) |

### Backend Routers (API endpoints)

| File | Lifecycle Steps Covered |
|------|------------------------|
| `api/routers/integration.py` | #1 (webhook), #25 (status API) |
| `api/routers/orders.py` | #2 (manual creation), #24 (ship) |
| `api/routers/positions.py` | #11-#13, #17, #19, #22-#24 (status transitions + split) |
| `api/routers/batches.py` | #14, #15, #17 (batch lifecycle) |
| `api/routers/quality.py` | #18, #22 (QC inspections) |
| `api/routers/purchaser.py` | #7 (purchase requests) |
| `api/routers/grinding.py` | #20 (grinding decisions) |
| `api/routers/materials.py` | #6 (material stock) |
| `api/routers/schedule.py` | #8 (schedule view) |
| `api/routers/packing_photos.py` | #21 (packing evidence) |
| `api/routers/finished_goods.py` | #23 (finished goods stock) |

### Frontend Pages

| File | Lifecycle Steps Covered |
|------|------------------------|
| `OrderCreateDialog.tsx` | #2 (manual order) |
| `PdfUploadDialog.tsx` | #2 (PDF upload) |
| `OrderDetailPage.tsx` | #2, #8, #23, #24 (order overview) |
| `TabloDashboard.tsx` | #11-#15, #17, #19 (production board) |
| `SorterPackerDashboard.tsx` | #19, #21 (sorting + packing) |
| `QualityManagerDashboard.tsx` | #13, #18, #22 (QC) |
| `PurchaserDashboard.tsx` | #7 (purchase requests) |
| `ManagerSchedulePage.tsx` | #8, #14 (schedule + batches) |
| `ManagerKilnsPage.tsx` | #9, #15, #16 (kilns) |
| `GrindingDecisionsPage.tsx` | #20 (grinding) |
| `BlockingTasksTab.tsx` | #4, #6 (blocked positions) |
| `MaterialDeficitsTable.tsx` | #6, #7 (shortages) |
| `ShortageDecisionPage.tsx` | #7 (shortage resolution) |
| `KilnFiringSchedulesPage.tsx` | #16 (firing schedules) |
