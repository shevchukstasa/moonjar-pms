# Moonjar PMS — Complete API Endpoints

> Auto-extracted from 62 router files in `api/routers/`
> Total: 511 endpoints across 62 router files
> Generated: 2026-03-26

## Authentication Levels

| Level | Dependency | Who |
|-------|-----------|-----|
| **public** | None | No auth required |
| **any_auth** | `get_current_user` | Any authenticated user |
| **management** | `require_management` | owner, administrator, production_manager |
| **admin** | `require_admin` | owner, administrator |
| **admin_or_pm** | `require_admin_or_pm` | owner, administrator, production_manager |
| **owner** | `require_owner` | owner only |
| **owner_or_ceo** | `require_role("owner","ceo")` | owner, ceo |
| **qm_or_admin** | `require_role(...)` | owner, administrator, quality_manager |
| **sorting** | `require_sorting` | sorter_packer + management roles |

---

## Table of Contents

1. [Auth](#1-auth-apiauth) (9 endpoints)
2. [Orders](#2-orders-apiorders) (18 endpoints)
3. [Positions](#3-positions-apipositions) (20 endpoints)
4. [Materials](#4-materials-apimaterials) (21 endpoints)
5. [Material Groups](#5-material-groups-apimaterial-groups) (9 endpoints)
6. [Recipes](#6-recipes-apirecipes) (12 endpoints)
7. [Quality](#7-quality-apiquality) (15 endpoints)
8. [Defects](#8-defects-apidefects) (14 endpoints)
9. [Batches](#9-batches-apibatches) (12 endpoints)
10. [Schedule](#10-schedule-apischedule) (13 endpoints)
11. [Kilns](#11-kilns-apikilns) (19 endpoints)
12. [Kiln Maintenance](#12-kiln-maintenance-apikiln-maintenance) (13 endpoints)
13. [Kiln Inspections](#13-kiln-inspections-apikiln-inspections) (9 endpoints)
14. [Tasks](#14-tasks-apitasks) (8 endpoints)
15. [Materials Purchase / Purchaser](#15-purchaser-apipurchaser) (12 endpoints)
16. [Suppliers](#16-suppliers-apisuppliers) (6 endpoints)
17. [Integration / Webhook](#17-integration-apiintegration) (8 endpoints)
18. [Users](#18-users-apiusers) (5 endpoints)
19. [Factories](#19-factories-apifactories) (8 endpoints)
20. [Analytics](#20-analytics-apianalytics) (9 endpoints)
21. [TOC / DBR](#21-toc-apitoc) (5 endpoints)
22. [TPS Metrics](#22-tps-apitps) (15 endpoints)
23. [Notifications](#23-notifications-apinotifications) (4 endpoints)
24. [Notification Preferences](#24-notification-preferences-apinotification-preferences) (5 endpoints)
25. [AI Chat](#25-ai-chat-apiai-chat) (3 endpoints)
26. [Export](#26-export-apiexport) (7 endpoints)
27. [Reports](#27-reports-apireports) (3 endpoints)
28. [Telegram](#28-telegram-apitelegram) (7 endpoints)
29. [Security](#29-security-apisecurity) (15 endpoints)
30. [Health](#30-health-api) (5 endpoints)
31. [Settings](#31-settings-apisettings) (3 endpoints)
32. [Admin Settings](#32-admin-settings-apiadmin-settings) (11 endpoints)
33. [Reference Data](#33-reference-data-apireference) (44 endpoints)
34. [Financials](#34-financials-apifinancials) (6 endpoints)
35. [Warehouse Sections](#35-warehouse-sections-apiwarehouse-sections) (6 endpoints)
36. [Reconciliations](#36-reconciliations-apireconciliations) (7 endpoints)
37. [Finished Goods](#37-finished-goods-apifinished-goods) (5 endpoints)
38. [Shipments](#38-shipments-apishipments) (7 endpoints)
39. [Packaging](#39-packaging-apipackaging) (8 endpoints)
40. [Packing Photos](#40-packing-photos-apipacking-photos) (4 endpoints)
41. [Grinding Stock](#41-grinding-stock-apigrinding-stock) (5 endpoints)
42. [Mana Shipments](#42-mana-shipments-apimana-shipments) (6 endpoints)
43. [Other Routers](#43-other-routers) (remaining)

---

## 1. Auth (`/api/auth`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/login` | public | Email+password login. Returns JWT access+refresh tokens. Handles account lockout. |
| POST | `/google` | public | Google OAuth login. Creates user if first login. Returns JWT tokens. |
| POST | `/refresh` | public | Refresh expired access token using refresh token. |
| POST | `/logout` | any_auth | Revoke current session's refresh token. |
| GET | `/me` | any_auth | Get current user profile with factory assignments. |
| POST | `/logout-all` | any_auth | Revoke all sessions for current user except current. |
| POST | `/verify-owner-key` | public | Verify owner secret key for initial setup. |
| POST | `/totp-verify` | public | Verify TOTP code during 2FA login flow. |
| POST | `/change-password` | any_auth | Change password for current user. Requires old password. |

## 2. Orders (`/api/orders`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `` | management | List orders with pagination, filters (status, factory, search). |
| GET | `/cancellation-requests` | management | List orders with pending cancellation requests from Sales. |
| GET | `/change-requests` | management | List orders with pending modification change requests. |
| POST | `/upload-pdf` | management | Upload PDF order document for AI parsing. Returns parsed data preview. |
| POST | `/confirm-pdf` | management | Confirm parsed PDF data and create order + positions + schedule. |
| POST | `/{order_id}/reprocess` | management | Re-run order intake pipeline (re-resolve recipes, sizes, schedule). |
| POST | `/{order_id}/reschedule` | management | Recalculate schedule for all positions in order. |
| GET | `/{order_id}` | management | Get order details with positions and items. |
| POST | `` | management | Create order manually with items. Runs full intake pipeline. |
| PATCH | `/{order_id}` | management | Update order fields (client, dates, notes). |
| DELETE | `/{order_id}` | management | Delete order and cascade to positions/reservations. |
| PATCH | `/{order_id}/ship` | management | Mark order as shipped. Updates all positions to SHIPPED status. |
| POST | `/{order_id}/accept-cancellation` | management | Accept cancellation request from Sales. Runs cancellation pipeline. |
| POST | `/{order_id}/reject-cancellation` | management | Reject cancellation request. Notifies Sales via webhook. |
| GET | `/{order_id}/change-requests` | management | Get change request history for a specific order. |
| POST | `/{order_id}/approve-change` | management | Approve change request. Applies diff to order/positions. |
| POST | `/{order_id}/reject-change` | management | Reject change request. Notifies Sales. |

## 3. Positions (`/api/positions`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `` | any_auth | List positions with filters (order, status, factory, batch, search). |
| GET | `/blocking-summary` | any_auth | Summary of blocked positions by blocking reason (materials, recipe, etc). |
| GET | `/{position_id}` | any_auth | Get position details with recipe, batch, schedule info. |
| PATCH | `/{position_id}` | any_auth | Update position fields (recipe, size, quantity, etc). |
| GET | `/{position_id}/allowed-transitions` | any_auth | Get valid status transitions from current status. |
| POST | `/{position_id}/status` | any_auth | Transition position status. Triggers business logic (reservation, consumption, QC). |
| POST | `/{position_id}/split` | any_auth | Split position after sorting (good/defect/write-off/repair/refire/etc). |
| POST | `/{position_id}/resolve-color-mismatch` | management | Resolve color mismatch: create new recipe or assign existing. |
| GET | `/{position_id}/stock-availability` | any_auth | Check stone stock availability for position. |
| POST | `/{position_id}/force-unblock` | management | Force unblock a position stuck in blocking status. |
| GET | `/{position_id}/material-reservations` | any_auth | Get material reservation details (expected vs actual consumption). |
| POST | `/reorder` | management | Reorder positions within an order (change priority). |
| POST | `/{position_id}/reassign-batch` | management | Move position to a different batch. |
| POST | `/{position_id}/split-production` | management | Split position mid-production into two sub-positions. |
| GET | `/{position_id}/split-tree` | any_auth | Get tree of parent + all child split positions. |
| GET | `/{position_id}/mergeable-children` | any_auth | Get list of child positions eligible for merge-back. |
| POST | `/{position_id}/merge` | management | Merge child position back into parent. |
| GET | `/{position_id}/materials` | any_auth | Get calculated material needs for position (BOM). |

## 4. Materials (`/api/materials`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `` | any_auth | List materials with stock per factory, filters, search, pagination. |
| GET | `/low-stock` | any_auth | Materials below min_balance threshold. |
| GET | `/effective-balance` | any_auth | Effective balance = stock - reserved for each material. |
| GET | `/consumption-adjustments` | any_auth | List consumption variance records (actual vs expected). |
| POST | `/consumption-adjustments/{adj_id}/approve` | management | Approve consumption adjustment, update shape coefficient. |
| POST | `/consumption-adjustments/{adj_id}/reject` | management | Reject consumption adjustment. |
| GET | `/duplicates` | admin | Find potential duplicate materials by fuzzy name matching. |
| POST | `/merge` | admin | Merge two duplicate materials. Transfers all references. |
| POST | `/cleanup-duplicates` | admin | Batch cleanup of duplicate materials. |
| POST | `/ensure-all-stocks` | admin | Create missing MaterialStock records for all factory/material combos. |
| GET | `/{material_id}` | any_auth | Get material details with stock per factory. |
| POST | `` | management | Create new material with auto-generated code (M-0001). |
| PATCH | `/{material_id}` | management | Update material fields. |
| DELETE | `/{material_id}` | admin | Soft-delete material (checks for active references). |
| GET | `/{material_id}/transactions` | any_auth | Transaction history for a material (receive, consume, reserve). |
| POST | `/transactions` | any_auth | Create material transaction (receive, write-off, adjustment). Triggers approval flow. |
| POST | `/transactions/{transaction_id}/approve` | management | Approve pending receipt. Updates stock balance. |
| DELETE | `/transactions/{transaction_id}` | management | Delete/cancel pending transaction. |
| POST | `/purchase-requests` | any_auth | Create manual purchase request. |
| POST | `/purchase-requests/{pr_id}/receive-partial` | any_auth | Record partial delivery against purchase request. |
| POST | `/purchase-requests/{pr_id}/resolve-deficit` | management | Resolve material deficit (accept shortage or find alternative). |

## 5. Material Groups (`/api/material-groups`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/hierarchy` | any_auth | Full group > subgroup > materials hierarchy tree. |
| GET | `/groups` | any_auth | List top-level material groups. |
| POST | `/groups` | admin | Create material group. |
| PUT | `/groups/{group_id}` | admin | Update material group. |
| DELETE | `/groups/{group_id}` | admin | Delete group (fails if has subgroups). |
| GET | `/subgroups` | any_auth | List subgroups (optional group filter). |
| POST | `/subgroups` | admin | Create subgroup under a group. |
| PUT | `/subgroups/{subgroup_id}` | admin | Update subgroup. |
| DELETE | `/subgroups/{subgroup_id}` | admin | Delete subgroup (fails if has materials). |

## 6. Recipes (`/api/recipes`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `` | any_auth | List recipes with filters (type, color_collection, search). |
| GET | `/lookup` | any_auth | Smart recipe lookup by color + collection + application method. |
| POST | `/import-csv` | admin | Bulk import recipes from CSV file. |
| GET | `/{item_id}` | any_auth | Get recipe with materials and kiln config. |
| POST | `` | admin | Create recipe with materials and kiln config. |
| PATCH | `/{item_id}` | any_auth | Update recipe fields. |
| DELETE | `/{item_id}` | admin | Delete recipe (checks for active position references). |
| POST | `/bulk-delete` | admin | Bulk delete multiple recipes. |
| GET | `/{recipe_id}/materials` | any_auth | Get BOM (bill of materials) for recipe. |
| PUT | `/{recipe_id}/materials` | any_auth | Replace all materials in recipe BOM. |
| GET | `/{recipe_id}/firing-stages` | any_auth | Get multi-firing stage definitions (e.g., Gold = 2 stages). |
| PUT | `/{recipe_id}/firing-stages` | any_auth | Replace firing stage definitions. |

## 7. Quality (`/api/quality`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/calendar-matrix` | any_auth | Quality check calendar: matrix of dates x kilns with defect counts. |
| GET | `/defect-causes` | any_auth | List defect cause dictionary. |
| POST | `/defect-causes` | qm_or_admin | Create new defect cause entry. |
| GET | `/inspections` | any_auth | List quality inspections with filters. |
| POST | `/inspections` | any_auth | Create quality inspection record for a position. |
| PATCH | `/inspections/{inspection_id}` | any_auth | Update inspection (result, notes, photos). |
| POST | `/inspections/{inspection_id}/photo` | any_auth | Upload photo to inspection record. |
| GET | `/positions-for-qc` | any_auth | Positions currently eligible for quality check. |
| GET | `/stats` | any_auth | Quality statistics (defect rates by stage, time period). |
| POST | `/analyze-photo` | any_auth | AI-powered defect photo analysis (OpenAI Vision / Claude). |
| GET | `/checklist-items` | any_auth | Get QC checklist template items. |
| POST | `/pre-kiln-check` | any_auth | Submit pre-kiln QC checklist for a position. |
| GET | `/pre-kiln-checks` | any_auth | List pre-kiln checks. |
| POST | `/final-check` | any_auth | Submit final QC checklist for a position. |
| GET | `/final-checks` | any_auth | List final QC checks. |

## 8. Defects (`/api/defects`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `` | any_auth | List defect records with filters. |
| GET | `/repair-queue` | any_auth | List items in repair queue. |
| GET | `/coefficients` | any_auth | Get stone defect coefficients per factory/stone type. |
| POST | `/positions/{position_id}/override` | management | Override defect coefficient for a position. |
| POST | `/record` | any_auth | Record defect during production (with outcome routing). |
| GET | `/surplus-dispositions` | any_auth | List surplus disposition decisions. |
| GET | `/surplus-summary` | any_auth | Summary of surplus by factory. |
| POST | `/surplus-dispositions/auto-assign` | management | Auto-assign surplus to matching orders or stock. |
| GET | `/supplier-reports` | any_auth | List supplier defect reports. |
| POST | `/supplier-reports/generate` | management | Generate defect report for supplier (period). |
| GET | `/{item_id}` | any_auth | Get defect cause by ID. |
| POST | `` | any_auth | Create defect cause. |
| PATCH | `/{item_id}` | any_auth | Update defect cause. |
| DELETE | `/{item_id}` | any_auth | Delete defect cause. |

## 9. Batches (`/api/batches`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auto-form` | management | Auto-form batches for a factory. Groups positions by temperature/kiln. |
| POST | `/capacity-preview` | any_auth | Preview kiln loading capacity for a set of positions. |
| GET | `` | any_auth | List batches with filters (status, kiln, date range). |
| GET | `/{batch_id}` | any_auth | Get batch details with positions and loading plan. |
| POST | `/{batch_id}/start` | management | Start firing (batch -> IN_PROGRESS, positions -> LOADED_IN_KILN). |
| POST | `/{batch_id}/complete` | management | Complete firing (batch -> DONE, positions -> FIRED). |
| POST | `/{batch_id}/confirm` | management | PM confirms suggested batch (SUGGESTED -> PLANNED). |
| POST | `/{batch_id}/reject` | management | PM rejects suggested batch. Positions released. |
| POST | `` | management | Create batch manually, assign positions. |
| PATCH | `/{batch_id}` | management | Update batch (notes, date, firing profile). |
| POST | `/{batch_id}/photos` | any_auth | Upload batch photo (kiln loading documentation). |
| GET | `/{batch_id}/photos` | any_auth | Get batch photos. |

### Firing Logs (also under `/api/batches`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/{batch_id}/firing-log` | any_auth | Create firing log entry for batch. |
| PATCH | `/{batch_id}/firing-log/{log_id}` | any_auth | Update firing log (temperatures, result). |
| POST | `/{batch_id}/firing-log/{log_id}/reading` | any_auth | Add temperature reading to firing log. |
| GET | `/{batch_id}/firing-log` | any_auth | Get firing logs for batch. |

## 10. Schedule (`/api/schedule`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/resources` | any_auth | List kiln resources with status. |
| GET | `/batches` | any_auth | List schedule batches (calendar view). |
| POST | `/batches` | management | Create schedule batch. |
| GET | `/glazing-schedule` | any_auth | Glazing work schedule (positions planned for glazing). |
| GET | `/firing-schedule` | any_auth | Firing schedule (batches by kiln and date). |
| GET | `/sorting-schedule` | any_auth | Sorting schedule (positions needing sorting). |
| GET | `/qc-schedule` | any_auth | QC schedule (positions requiring quality check). |
| GET | `/kiln-schedule` | any_auth | Kiln timeline (slots, maintenance windows). |
| PATCH | `/positions/reorder` | management | Reorder positions in schedule (change planned dates). |
| POST | `/batches/{batch_id}/positions` | management | Add/remove positions from a batch. |
| GET | `/orders/{order_id}/schedule` | any_auth | Get full schedule summary for an order. |
| POST | `/orders/{order_id}/reschedule` | management | Reschedule order (recalculate all dates). |
| POST | `/factory/{factory_id}/reschedule` | management | Reschedule all orders in factory. |
| GET | `/positions/{position_id}/schedule` | any_auth | Get schedule details for a single position. |

## 11. Kilns (`/api/kilns`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/collections` | any_auth | Get all collection names (for filters). |
| GET | `` | any_auth | List kilns with status, capacity, factory filter. |
| GET | `/maintenance/upcoming` | management | Upcoming maintenance across all kilns. |
| GET | `/{kiln_id}` | any_auth | Get kiln details with equipment specs. |
| POST | `` | management | Create new kiln (resource type=kiln). |
| PATCH | `/{kiln_id}` | management | Update kiln (dimensions, equipment, coefficient). |
| PATCH | `/{kiln_id}/status` | management | Change kiln status (active/maintenance/inactive). |
| DELETE | `/{kiln_id}` | management | Delete kiln (must have no active batches). |
| GET | `/{kiln_id}/maintenance` | management | Maintenance schedule for specific kiln. |
| POST | `/{kiln_id}/maintenance` | management | Schedule maintenance for kiln. |
| PUT | `/{kiln_id}/maintenance/{schedule_id}` | management | Update maintenance entry. |
| POST | `/{kiln_id}/maintenance/{schedule_id}/complete` | management | Mark maintenance as completed. |
| DELETE | `/{kiln_id}/maintenance/{schedule_id}` | management | Cancel scheduled maintenance. |
| POST | `/{kiln_id}/breakdown` | management | Report kiln breakdown. Triggers emergency reassignment. |
| POST | `/{kiln_id}/restore` | management | Restore kiln after breakdown. |
| GET | `/{kiln_id}/rotation-rules` | any_auth | Get glaze rotation rules for kiln. |
| PUT | `/{kiln_id}/rotation-rules` | management | Set glaze rotation rules. |
| GET | `/{kiln_id}/rotation-check` | any_auth | Check if next batch complies with rotation rules. |

## 12. Kiln Maintenance (`/api/kiln-maintenance`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/types` | any_auth | List maintenance types. |
| POST | `/types` | management | Create maintenance type. |
| PUT | `/types/{type_id}` | management | Update maintenance type. |
| GET | `/kilns/{kiln_id}` | any_auth | Maintenance history for specific kiln. |
| POST | `/kilns/{kiln_id}` | management | Schedule maintenance for kiln. |
| PUT | `/kilns/{kiln_id}/{schedule_id}` | management | Update scheduled maintenance. |
| POST | `/kilns/{kiln_id}/{schedule_id}/complete` | management | Complete maintenance entry. |
| DELETE | `/kilns/{kiln_id}/{schedule_id}` | management | Delete maintenance entry. |
| GET | `/upcoming` | any_auth | Upcoming maintenance across all kilns. |
| GET | `` | any_auth | List all maintenance with materials. |
| GET | `/{item_id}` | any_auth | Get maintenance detail. |
| POST | `` | management | Create maintenance entry with materials. |
| PATCH | `/{item_id}` | management | Update maintenance. |
| DELETE | `/{item_id}` | management | Delete maintenance entry. |

## 13. Kiln Inspections (`/api/kiln-inspections`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/items` | any_auth | List inspection checklist template items. |
| GET | `` | any_auth | List inspections with filters. |
| GET | `/{inspection_id}` | any_auth | Get inspection with results. |
| POST | `` | any_auth | Create inspection (submit checklist results for a kiln). |
| GET | `/repairs` | any_auth | List kiln repair logs. |
| POST | `/repairs` | any_auth | Create repair log entry (from inspection finding). |
| PATCH | `/repairs/{repair_id}` | any_auth | Update repair log (diagnosis, actions, completion). |
| DELETE | `/repairs/{repair_id}` | management | Delete repair log. |
| GET | `/matrix` | any_auth | Inspection matrix: kilns x dates with status indicators. |

## 14. Tasks (`/api/tasks`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `` | any_auth | List tasks with filters (type, status, assigned_to). |
| GET | `/{task_id}` | any_auth | Get task details with related order/position. |
| POST | `` | management | Create task manually. |
| PATCH | `/{task_id}` | management | Update task (assign, priority, description). |
| POST | `/{task_id}/complete` | management | Complete task. May trigger downstream actions. |
| POST | `/{task_id}/resolve-shortage` | management | Resolve material shortage task (accept/substitute/wait). |
| POST | `/{task_id}/resolve-size` | management | Resolve size confirmation task (match or create new size). |
| POST | `/{task_id}/resolve-consumption` | management | Resolve consumption measurement task (enter actual data). |

## 15. Purchaser (`/api/purchaser`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `` | any_auth | List purchase requests with filters and pagination. |
| GET | `/stats` | any_auth | Purchaser dashboard stats (pending, overdue, spend). |
| GET | `/deliveries` | any_auth | Upcoming and recent deliveries. |
| GET | `/deficits` | any_auth | Current material deficits requiring purchase. |
| GET | `/consolidation-suggestions` | any_auth | Suggested PR consolidations (group by supplier/window). |
| POST | `/consolidate` | any_auth | Execute purchase request consolidation. |
| GET | `/lead-times` | any_auth | Supplier lead times with actual vs default comparison. |
| GET | `/{item_id}` | any_auth | Get purchase request details. |
| POST | `` | any_auth | Create purchase request. |
| PATCH | `/{item_id}` | any_auth | Update purchase request fields. |
| PATCH | `/{item_id}/status` | any_auth | Transition PR status (approve -> send -> receive). Full lifecycle. |
| DELETE | `/{item_id}` | any_auth | Delete purchase request (pending only). |

## 16. Suppliers (`/api/suppliers`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `` | any_auth | List suppliers with search. |
| GET | `/{item_id}/lead-times` | any_auth | Lead times per material type for supplier. |
| GET | `/{item_id}` | any_auth | Get supplier details. |
| POST | `` | any_auth | Create supplier. |
| PATCH | `/{item_id}` | any_auth | Update supplier. |
| DELETE | `/{item_id}` | any_auth | Delete supplier (soft). |

## 17. Integration (`/api/integration`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | admin | Integration health check. |
| GET | `/db-check` | admin | Database connectivity check with table counts. |
| GET | `/orders/{external_id}/production-status` | public (API key) | Get production status by external order ID. For Sales App. |
| GET | `/orders/status-updates` | public (API key) | Batch poll for status updates since timestamp. For Sales App. |
| POST | `/orders/{external_id}/request-cancellation` | public (API key) | Request order cancellation from Sales App. |
| POST | `/webhook/sales-order` | public (API key) | Receive new/updated order from Sales App webhook. Full intake pipeline. |
| GET | `/webhooks` | admin | List webhook events. |
| GET | `/stubs` | admin | List test stub orders. |
| POST | `/stubs` | admin | Create test stub order. |

## 18. Users (`/api/users`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `` | admin | List users with factory assignments. |
| GET | `/{user_id}` | admin | Get user details. |
| POST | `` | admin | Create user with role and factory assignment. |
| PATCH | `/{user_id}` | admin | Update user (name, email, role, factories). |
| POST | `/{user_id}/toggle-active` | admin | Activate/deactivate user. |

## 19. Factories (`/api/factories`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `` | any_auth | List factories. |
| PATCH | `/{item_id}/kiln-mode` | admin | Switch kiln constants mode (manual/production). |
| GET | `/{factory_id}/estimate` | any_auth | Production lead time estimate for factory. |
| GET | `/{item_id}` | any_auth | Get factory details. |
| POST | `` | admin | Create factory. |
| PATCH | `/{item_id}` | admin | Update factory. |
| DELETE | `/{item_id}` | admin | Delete factory. |
| GET | `/{factory_id}/rotation-rules` | any_auth | Get factory-level rotation rules. |
| PUT | `/{factory_id}/rotation-rules` | management | Set factory rotation rules. |

## 20. Analytics (`/api/analytics`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/dashboard-summary` | management | KPI summary (orders, on-time rate, defect rate, kiln utilization). |
| GET | `/production-metrics` | management | Detailed production metrics by stage. |
| GET | `/material-metrics` | management | Material consumption and stock metrics. |
| GET | `/factory-comparison` | owner | Compare metrics across factories. |
| GET | `/buffer-health` | any_auth | TOC buffer health status per kiln. |
| GET | `/trend-data` | management | Time-series data for trend charts. |
| GET | `/activity-feed` | management | Recent activity events. |
| GET | `/inventory-report` | management | Full inventory report with stock levels. |
| GET | `/anomalies` | management | Detected anomalies (defects, throughput, consumption). |

## 21. TOC (`/api/toc`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/constraints` | any_auth | Get bottleneck configuration (constraint resource, buffer, rope). |
| PATCH | `/constraints/{constraint_id}` | management | Update constraint config. |
| PATCH | `/bottleneck/batch-mode` | management | Switch batch formation mode (auto/hybrid). |
| PATCH | `/bottleneck/buffer-target` | management | Set buffer target hours. |
| GET | `/buffer-health` | any_auth | Buffer health indicators per kiln. |
| GET | `/buffer-zones` | any_auth | Buffer zone breakdown (green/yellow/red). |

## 22. TPS (`/api/tps`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/parameters` | any_auth | TPS target parameters per stage. |
| POST | `/parameters` | management | Create TPS parameter. |
| PATCH | `/parameters/{param_id}` | management | Update TPS parameter. |
| GET | `` | any_auth | List shift metrics with date range. |
| POST | `` | management | Record shift metric manually. |
| GET | `/dashboard-summary` | any_auth | TPS dashboard (OEE, defect rate, takt time, throughput). |
| GET | `/shift-summary` | any_auth | Summary for a specific shift. |
| GET | `/signal` | any_auth | Current production signal (green/yellow/red). |
| GET | `/deviations` | any_auth | List deviations. |
| POST | `/deviations` | management | Report deviation. |
| PATCH | `/deviations/{deviation_id}` | management | Update/resolve deviation. |
| POST | `/record` | management | Record shift production data (output, defects, downtime). |
| GET | `/position/{position_id}/timeline` | any_auth | Position production timeline (stages with timestamps). |
| GET | `/throughput` | any_auth | Throughput metrics by stage. |
| GET | `/deviations/operations` | any_auth | Operations with deviation history. |

## 23. Notifications (`/api/notifications`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/unread-count` | any_auth | Count of unread notifications for current user. |
| GET | `` | any_auth | List notifications for current user with pagination. |
| PATCH | `/{notification_id}/read` | any_auth | Mark notification as read. |
| POST | `/read-all` | any_auth | Mark all notifications as read. |

## 24. Notification Preferences (`/api/notification-preferences`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `` | any_auth | List current user's notification preferences. |
| GET | `/{item_id}` | any_auth | Get preference by ID. |
| POST | `` | any_auth | Create notification preference. |
| PATCH | `/{item_id}` | any_auth | Update preference. |
| DELETE | `/{item_id}` | any_auth | Delete preference. |

## 25. AI Chat (`/api/ai-chat`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/chat` | any_auth | Send message to AI assistant. RAG-grounded response. |
| GET | `/sessions` | any_auth | List chat sessions for current user. |
| GET | `/sessions/{session_id}/messages` | any_auth | Get message history for a session. |

## 26. Export (`/api/export`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/materials/excel` | management | Export materials inventory to Excel. |
| GET | `/quality/excel` | management | Export quality data to Excel. |
| GET | `/orders/excel` | management | Export orders list to Excel. |
| GET | `/orders/pdf` | management | Generate order PDF (production spec sheet). |
| GET | `/positions/pdf` | management | Generate position detail PDF. |
| POST | `/owner-monthly` | owner | Generate monthly owner report PDF. |
| POST | `/ceo-daily` | management | Generate CEO daily report PDF. |

## 27. Reports (`/api/reports`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `` | management | Available reports list. |
| GET | `/orders-summary` | management | Orders summary report (by status, factory, period). |
| GET | `/kiln-load` | management | Kiln loading report (utilization, capacity). |

## 28. Telegram (`/api/telegram`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/bot-status` | admin | Telegram bot connection status. |
| GET | `/owner-chat` | admin | Get owner Telegram chat ID. |
| PUT | `/owner-chat` | admin | Set owner Telegram chat ID. |
| POST | `/test-chat` | admin | Send test message to a Telegram chat. |
| GET | `/recent-chats` | admin | List recent Telegram chat interactions. |
| POST | `/webhook` | public | Telegram webhook endpoint (receives updates from Telegram). |
| POST | `/subscribe` | any_auth | Subscribe user to Telegram notifications. |
| DELETE | `/unsubscribe` | any_auth | Unsubscribe from Telegram. |

## 29. Security (`/api/security`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/audit-log` | admin | Security audit log with filters. |
| GET | `/audit-log/summary` | admin | Audit log summary statistics. |
| GET | `/sessions` | any_auth | List active sessions for current user. |
| DELETE | `/sessions/{session_id}` | any_auth | Revoke specific session. |
| DELETE | `/sessions` | any_auth | Revoke all sessions except current. |
| GET | `/ip-allowlist` | admin | List IP allowlist entries. |
| POST | `/ip-allowlist` | admin | Add IP to allowlist. |
| DELETE | `/ip-allowlist/{entry_id}` | admin | Remove IP from allowlist. |
| POST | `/totp/setup` | any_auth | Initialize TOTP 2FA setup (returns QR code). |
| POST | `/totp/verify` | any_auth | Verify and activate TOTP. |
| POST | `/totp/disable` | any_auth | Disable TOTP 2FA. |
| GET | `/totp/status` | any_auth | Check TOTP status for current user. |
| POST | `/totp/backup-codes/regenerate` | any_auth | Regenerate TOTP backup codes. |
| GET | `/rate-limit-events` | admin | View rate limit events. |
| DELETE | `/rate-limit-events/clear` | admin | Clear rate limit events. |

## 30. Health (`/api`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | public | Basic health check. Returns {"status":"ok"}. |
| GET | `/health/seed-status` | admin | Check seed data status (reference tables populated). |
| GET | `/health/backup` | admin | Last backup status and schedule. |
| POST | `/admin/backup` | admin | Trigger manual database backup. |
| GET | `/internal/poll-pms-status` | public | Internal polling endpoint for Sales App. |

## 31. Settings (`/api/settings`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `` | management | Get system settings. |
| PUT | `` | admin | Update system settings. |
| POST | `` | admin | Bulk update settings. |

## 32. Admin Settings (`/api/admin-settings`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/escalation-rules` | admin | List escalation rules. |
| POST | `/escalation-rules` | admin | Create escalation rule. |
| PATCH | `/escalation-rules/{id}` | admin | Update escalation rule. |
| DELETE | `/escalation-rules/{id}` | admin | Delete escalation rule. |
| GET | `/receiving-settings` | admin | Get receiving approval settings. |
| PUT | `/receiving-settings` | admin | Update receiving settings. |
| GET | `/defect-thresholds` | admin | List material defect thresholds. |
| PUT | `/defect-thresholds` | admin | Update defect threshold. |
| DELETE | `/defect-thresholds/{id}` | admin | Delete defect threshold. |
| GET | `/consolidation-settings` | admin | Get purchase consolidation settings. |
| PUT | `/consolidation-settings` | admin | Update consolidation settings. |

## 33. Reference Data (`/api/reference`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/product-types` | any_auth | Product type enum values. |
| GET | `/stone-types` | any_auth | Stone type values. |
| GET | `/glaze-types` | any_auth | Glaze type values. |
| GET | `/finish-types` | any_auth | Finish type values. |
| GET | `/shape-types` | any_auth | Shape type enum values. |
| GET | `/material-types` | any_auth | Material type enum values. |
| GET | `/position-statuses` | any_auth | Position status enum values. |
| GET | `/collections` | any_auth | Product collections. |
| GET | `/application-methods` | any_auth | Application methods (SS, BS, etc). |
| GET | `/application-collections` | any_auth | Application collections (Authentic, Exclusive, etc). |
| GET | `/all` | any_auth | All reference data in one response (for frontend caching). |
| GET | `/shape-coefficients` | any_auth | Shape consumption coefficients. |
| PUT | `/shape-coefficients/{shape}/{product_type}` | management | Update shape coefficient. |
| GET | `/bowl-shapes` | any_auth | Bowl shape options for sinks. |
| GET | `/temperature-groups` | any_auth | Firing temperature groups. |
| POST | `/temperature-groups` | management | Create temperature group. |
| PUT | `/temperature-groups/{group_id}` | management | Update temperature group. |
| POST | `/temperature-groups/{group_id}/recipes` | management | Link recipe to temperature group. |
| DELETE | `/temperature-groups/{group_id}/recipes/{recipe_id}` | management | Unlink recipe from group. |
| POST | `/collections` | management | Create collection. |
| PUT | `/collections/{item_id}` | management | Update collection. |
| DELETE | `/collections/{item_id}` | management | Delete collection. |
| GET | `/color-collections` | any_auth | Color collections. |
| POST | `/color-collections` | management | Create color collection. |
| PUT | `/color-collections/{item_id}` | management | Update color collection. |
| DELETE | `/color-collections/{item_id}` | management | Delete color collection. |
| GET | `/colors` | any_auth | Colors. |
| POST | `/colors` | management | Create color. |
| PUT | `/colors/{item_id}` | management | Update color. |
| DELETE | `/colors/{item_id}` | management | Delete color. |
| GET | `/application-types` | any_auth | Application types. |
| POST | `/application-types` | management | Create application type. |
| PUT | `/application-types/{item_id}` | management | Update application type. |
| DELETE | `/application-types/{item_id}` | management | Delete application type. |
| GET | `/places-of-application` | any_auth | Places of application (face_only, face_and_sides, etc). |
| POST | `/places-of-application` | management | Create place of application. |
| PUT | `/places-of-application/{item_id}` | management | Update place of application. |
| DELETE | `/places-of-application/{item_id}` | management | Delete place of application. |
| GET | `/finishing-types` | any_auth | Finishing types. |
| POST | `/finishing-types` | management | Create finishing type. |
| PUT | `/finishing-types/{item_id}` | management | Update finishing type. |
| DELETE | `/finishing-types/{item_id}` | management | Delete finishing type. |
| POST | `/bulk-import` | admin | Bulk import reference data from JSON. |

## 34-43. Remaining Routers

### Financials (`/api/financials`) — 6 endpoints
Owner/CEO read, owner write. Summary with P&L, CRUD for financial entries.

### Warehouse Sections (`/api/warehouse-sections`) — 6 endpoints
CRUD for warehouse sections. Admin/PM can create, any auth can read.

### Reconciliations (`/api/reconciliations`) — 7 endpoints
Inventory reconciliation workflow: create session, add items (actual vs system), complete with adjustments.

### Finished Goods (`/api/finished-goods`) — 5 endpoints
CRUD for finished goods stock + availability check by color/size.

### Shipments (`/api/shipments`) — 7 endpoints
Create shipment, add items, ship, deliver, cancel. Management role.

### Packaging (`/api/packaging`) — 8 endpoints
Box types, size capacities, spacer rules. Admin/PM manage.

### Packing Photos (`/api/packing-photos`) — 4 endpoints
Upload/list/delete packing photos for orders. Sorting role.

### Grinding Stock (`/api/grinding-stock`) — 5 endpoints
List grinding stock, stats, CRUD, decide disposition (grind/discard/reuse).

### Mana Shipments (`/api/mana-shipments`) — 6 endpoints
Internal transfers to Mana showroom. Confirm and ship workflow.

### Other small routers

| Router | Prefix | Endpoints | Auth | Description |
|--------|--------|-----------|------|-------------|
| Dashboard Access | `/api/dashboard-access` | 6 | admin/any | Grant users access to additional dashboards |
| Cleanup | `/api/cleanup` | 4 | management/admin | Delete test data (tasks, positions, orders) |
| Consumption Rules | `/api/consumption-rules` | 5 | any/admin_or_pm | Glaze consumption rules per product config |
| Factory Calendar | `/api/factory-calendar` | 5 | any/management | Working days, holidays, bulk create |
| Sizes | `/api/sizes` | 7 | any/admin_or_pm | Tile sizes with glazing board spec auto-calc |
| Stages | `/api/stages` | 5 | any | Production stages reference |
| Stone Reservations | `/api/stone-reservations` | 5 | management | Stone reservations, defect rates, weekly report |
| Kiln Constants | `/api/kiln-constants` | 5 | any/admin | Kiln calculation constants |
| Kiln Firing Schedules | `/api/kiln-firing-schedules` | 5 | any | Per-kiln firing schedules (temperature curves) |
| Kiln Loading Rules | `/api/kiln-loading-rules` | 5 | any/management | Per-kiln loading rules (JSONB) |
| Firing Profiles | `/api/firing-profiles` | 6 | any | Universal firing profiles + auto-match |
| QM Blocks | `/api/qm-blocks` | 5 | any | Quality manager production blocks |
| Problem Cards | `/api/problem-cards` | 5 | any | Problem cards for production issues |
| Employees | `/api/employees` | 9 | any | HR: employees, payroll summary, attendance |
| Delivery | `/api/delivery` | 1 | any/apikey | Process delivery photo via AI |
| Transcription | `/api/transcription` | 1 | any | Audio transcription (placeholder) |
| Guides | `/api/guides` | 2 | any | PM guide content by role/language |
| WebSocket | `/api/ws` | 1 | ws | Real-time notifications WebSocket |
