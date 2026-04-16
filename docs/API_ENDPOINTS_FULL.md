# Moonjar PMS -- Complete API Endpoints

> Auto-extracted from 67 router files in `api/routers/`
> Total: **667** endpoints across 67 router files
> Generated: 2026-04-17
> Script: `scripts/generate_api_docs.py`

## Authentication Levels

| Level | Dependency | Who |
|-------|-----------|-----|
| **public** | None | No auth required |
| **any_auth** | `get_current_user` | Any authenticated user |
| **management** | `require_management` | owner, administrator, ceo, production_manager |
| **admin** | `require_admin` | owner, administrator |
| **admin_or_pm** | `require_admin_or_pm` | owner, administrator, production_manager |
| **owner** | `require_owner` | owner only |
| **finance** | `require_finance` | owner, administrator, ceo |
| **qm_or_admin** | `require_quality` | owner, administrator, quality_manager |
| **warehouse** | `require_warehouse` | owner, administrator, warehouse |
| **sorting** | `require_sorting` | sorter_packer + management roles |
| **purchaser** | `require_purchaser` | owner, administrator, purchaser |
| **role(...)** | `require_role(...)` | Custom role combination |

---

## Table of Contents

1. [Auth](#1-auth-apiauth) (9 endpoints)
2. [Orders](#2-orders-apiorders) (18 endpoints)
3. [Positions](#3-positions-apipositions) (20 endpoints)
4. [Schedule](#4-schedule-apischedule) (23 endpoints)
5. [Materials](#5-materials-apimaterials) (29 endpoints)
6. [Recipes](#6-recipes-apirecipes) (15 endpoints)
7. [Quality](#7-quality-apiquality) (15 endpoints)
8. [Defects](#8-defects-apidefects) (15 endpoints)
9. [Tasks](#9-tasks-apitasks) (8 endpoints)
10. [Suppliers](#10-suppliers-apisuppliers) (6 endpoints)
11. [Integration](#11-integration-apiintegration) (9 endpoints)
12. [Users](#12-users-apiusers) (6 endpoints)
13. [Factories](#13-factories-apifactories) (9 endpoints)
14. [Kilns](#14-kilns-apikilns) (18 endpoints)
15. [Kiln Equipment](#15-kiln-equipment-api) (8 endpoints)
16. [Recipe Kiln Capability](#16-recipe-kiln-capability-api) (5 endpoints)
17. [Kiln Maintenance](#17-kiln-maintenance-apikiln-maintenance) (14 endpoints)
18. [Kiln Inspections](#18-kiln-inspections-apikiln-inspections) (10 endpoints)
19. [Kiln Constants](#19-kiln-constants-apikiln-constants) (5 endpoints)
20. [Reference](#20-reference-apireference) (43 endpoints)
21. [Toc](#21-toc-apitoc) (6 endpoints)
22. [Tps](#22-tps-apitps) (67 endpoints)
23. [Notifications](#23-notifications-apinotifications) (4 endpoints)
24. [Analytics](#24-analytics-apianalytics) (12 endpoints)
25. [Ai Chat](#25-ai-chat-apiai-chat) (3 endpoints)
26. [Export](#26-export-apiexport) (9 endpoints)
27. [Reports](#27-reports-apireports) (3 endpoints)
28. [Stages](#28-stages-apistages) (5 endpoints)
29. [Transcription](#29-transcription-apitranscription) (2 endpoints)
30. [Telegram](#30-telegram-apitelegram) (11 endpoints)
31. [Health](#31-health-api) (6 endpoints)
32. [Purchaser](#32-purchaser-apipurchaser) (12 endpoints)
33. [Kiln Loading Rules](#33-kiln-loading-rules-apikiln-loading-rules) (5 endpoints)
34. [Kiln Firing Schedules](#34-kiln-firing-schedules-apikiln-firing-schedules) (5 endpoints)
35. [Dashboard Access](#35-dashboard-access-apidashboard-access) (6 endpoints)
36. [Notification Preferences](#36-notification-preferences-apinotification-preferences) (5 endpoints)
37. [Financials](#37-financials-apifinancials) (6 endpoints)
38. [Warehouse Sections](#38-warehouse-sections-apiwarehouse-sections) (6 endpoints)
39. [Reconciliations](#39-reconciliations-apireconciliations) (8 endpoints)
40. [Qm Blocks](#40-qm-blocks-apiqm-blocks) (5 endpoints)
41. [Problem Cards](#41-problem-cards-apiproblem-cards) (5 endpoints)
42. [Security](#42-security-apisecurity) (15 endpoints)
43. [Websocket](#43-websocket-apiws) (1 endpoints)
44. [Packing Photos](#44-packing-photos-apipacking-photos) (4 endpoints)
45. [Finished Goods](#45-finished-goods-apifinished-goods) (5 endpoints)
46. [Firing Profiles](#46-firing-profiles-apifiring-profiles) (6 endpoints)
47. [Batches](#47-batches-apibatches) (12 endpoints)
48. [Firing Logs](#48-firing-logs-apibatches) (4 endpoints)
49. [Cleanup](#49-cleanup-apicleanup) (5 endpoints)
50. [Material Groups](#50-material-groups-apimaterial-groups) (9 endpoints)
51. [Packaging](#51-packaging-apipackaging) (8 endpoints)
52. [Sizes](#52-sizes-apisizes) (8 endpoints)
53. [Consumption Rules](#53-consumption-rules-apiconsumption-rules) (5 endpoints)
54. [Grinding Stock](#54-grinding-stock-apigrinding-stock) (6 endpoints)
55. [Factory Calendar](#55-factory-calendar-apifactory-calendar) (5 endpoints)
56. [Stone Reservations](#56-stone-reservations-apistone-reservations) (7 endpoints)
57. [Settings](#57-settings-apisettings) (3 endpoints)
58. [Admin Settings](#58-admin-settings-apiadmin-settings) (11 endpoints)
59. [Guides](#59-guides-apiguides) (2 endpoints)
60. [Delivery](#60-delivery-apidelivery) (1 endpoints)
61. [Employees](#61-employees-apiemployees) (14 endpoints)
62. [Mana Shipments](#62-mana-shipments-apimana-shipments) (6 endpoints)
63. [Gamification](#63-gamification-apigamification) (26 endpoints)
64. [Workforce](#64-workforce-apiworkforce) (14 endpoints)
65. [Onboarding](#65-onboarding-apionboarding) (5 endpoints)
66. [Shipments](#66-shipments-apishipments) (7 endpoints)
67. [Pdf Templates](#67-pdf-templates-apipdftemplates) (2 endpoints)

---

## 1. Auth (`/api/auth`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/auth/login` | public | Login |
| POST | `/api/auth/google` | public | Google login |
| POST | `/api/auth/refresh` | public | Refresh token |
| POST | `/api/auth/logout` | any_auth | Logout |
| GET | `/api/auth/me` | any_auth | Get me |
| POST | `/api/auth/logout-all` | any_auth | Revoke ALL active sessions for the current user. |
| POST | `/api/auth/verify-owner-key` | public | First-time owner setup: verify the OWNER_KEY to claim the owner account. |
| POST | `/api/auth/totp-verify` | public | Complete login by verifying a TOTP code (or backup code) after password auth. |
| POST | `/api/auth/change-password` | any_auth | Change password for the authenticated user. |

## 2. Orders (`/api/orders`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/orders` | management | List orders |
| GET | `/api/orders/cancellation-requests` | management | List orders with pending (or all) cancellation requests. PM dashboard uses this. |
| GET | `/api/orders/change-requests` | management | List orders with pending change requests from Sales. PM dashboard uses this. |
| POST | `/api/orders/upload-pdf` | management | Upload a PDF order document for parsing. |
| POST | `/api/orders/confirm-pdf` | management | Confirm a parsed PDF order — creates the actual order and positions. |
| POST | `/api/orders/{order_id}/reprocess` | management | Re-run the intake pipeline for all positions of an existing order. |
| GET | `/api/orders/{order_id}/debug-sqm` | management | Debug endpoint: read glazeable_sqm directly via raw SQL. |
| POST | `/api/orders/{order_id}/reschedule` | management | Reschedule an order: recalculate planned dates, assign kilns, reserve materials. |
| GET | `/api/orders/{order_id}` | management | Get order |
| POST | `/api/orders` | management | Create an order manually (PM form or future PDF upload). |
| PATCH | `/api/orders/{order_id}` | management | Update order |
| DELETE | `/api/orders/{order_id}` | management | Cancel order |
| PATCH | `/api/orders/{order_id}/ship` | management | Mark order as shipped. All READY_FOR_SHIPMENT positions → SHIPPED. |
| POST | `/api/orders/{order_id}/accept-cancellation` | management | PM accepts the cancellation request → order status → CANCELLED. |
| POST | `/api/orders/{order_id}/reject-cancellation` | management | PM rejects the cancellation request → order continues as-is. |
| GET | `/api/orders/{order_id}/change-requests` | management | List all change requests for a specific order (history + pending). |
| POST | `/api/orders/{order_id}/approve-change` | management | PM approves the change request → apply stored payload changes to the order. |
| POST | `/api/orders/{order_id}/reject-change` | management | PM rejects the change request → discard stored changes. |

## 3. Positions (`/api/positions`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/positions` | any_auth | List positions |
| GET | `/api/positions/blocking-summary` | any_auth | Return a summary of all blocked positions with related tasks and shortages. |
| GET | `/api/positions/{position_id}` | any_auth | Get position |
| PATCH | `/api/positions/{position_id}` | management | Update position |
| POST | `/api/positions/batch-transitions` | any_auth | Return allowed transitions for multiple positions in a single request. |
| GET | `/api/positions/{position_id}/allowed-transitions` | any_auth | Return list of allowed next statuses for a position. |
| POST | `/api/positions/{position_id}/status` | any_auth | Change position status |
| POST | `/api/positions/{position_id}/split` | sorting | Sort a fired position: split into good/refire/repair/color_mismatch/grinding/write-off. |
| POST | `/api/positions/{position_id}/resolve-color-mismatch` | management | PM resolves a color-mismatch sub-position by directing tiles into up to 3 paths: |
| GET | `/api/positions/{position_id}/stock-availability` | any_auth | Check finished goods availability for a stock position (informational, shown before sorting). |
| GET | `/api/positions/{position_id}/force-unblock-options` | management | Return context-aware unblock options based on position's current blocking status. |
| POST | `/api/positions/{position_id}/force-unblock` | management | PM force-unblock: override any blocking status with context-aware action. |
| GET | `/api/positions/{position_id}/material-reservations` | any_auth | Return material reservation details for a position. |
| POST | `/api/positions/reorder` | management | Batch update priority_order for multiple positions. |
| POST | `/api/positions/{position_id}/reassign-batch` | management | Move a position to a different batch (or remove from batch). |
| POST | `/api/positions/{position_id}/split-production` | management | PM splits a position during production. |
| GET | `/api/positions/{position_id}/split-tree` | management | Get full split tree (parent + all descendants) for a position. |
| GET | `/api/positions/{position_id}/mergeable-children` | any_auth | Get list of children that can be merged back into this parent. |
| POST | `/api/positions/{position_id}/merge` | management | Merge a child sub-position back into parent position. |
| GET | `/api/positions/{position_id}/materials` | any_auth | Get material requirements for a position with reservation status. |

## 4. Schedule (`/api/schedule`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/schedule/resources` | any_auth | List resources |
| GET | `/api/schedule/batches` | any_auth | List batches |
| POST | `/api/schedule/batches` | management | Create batch |
| GET | `/api/schedule/glazing-schedule` | any_auth | Get glazing schedule |
| GET | `/api/schedule/firing-schedule` | any_auth | Get firing schedule |
| GET | `/api/schedule/sorting-schedule` | any_auth | Get sorting schedule |
| GET | `/api/schedule/qc-schedule` | any_auth | Positions currently in QC pipeline. |
| GET | `/api/schedule/kiln-schedule` | any_auth | Batches grouped by kiln. |
| PATCH | `/api/schedule/positions/reorder` | management | Bulk reorder positions — assigns sequential priority_order values. |
| POST | `/api/schedule/batches/{batch_id}/positions` | management | Assign positions to an existing batch. |
| GET | `/api/schedule/orders/{order_id}/schedule` | any_auth | Full production schedule for an order — visible to Sales for |
| POST | `/api/schedule/orders/{order_id}/reschedule` | management | Manually trigger a full reschedule of all positions in an order. |
| POST | `/api/schedule/orders/{order_id}/reschedule-debug` | management | Debug: reschedule order and return errors. |
| POST | `/api/schedule/factory/{factory_id}/reschedule` | management | Reschedule all active positions across all orders in a factory. |
| POST | `/api/schedule/factory/{factory_id}/reschedule-overdue` | management | Replan all overdue positions using the full scheduling engine. |
| GET | `/api/schedule/positions/{position_id}/schedule` | any_auth | Schedule details for a single position — planned dates, kiln |
| POST | `/api/schedule/optimize-batch/{batch_id}` | management | Find candidate positions to fill remaining capacity in a batch. |
| GET | `/api/schedule/kiln-utilization` | any_auth | Kiln utilization metrics for a factory over the past N days. |
| GET | `/api/schedule/production-schedule` | any_auth | Forward-looking daily production schedule view for N days. |
| POST | `/api/schedule/recalculate` | management | Full factory schedule recalculation orchestrator. |
| GET | `/api/schedule/config/{factory_id}` | management | Get scheduler configuration for a factory (buffer days, auto-buffer settings). |
| PUT | `/api/schedule/config/{factory_id}` | management | Update scheduler configuration for a factory. PM/CEO only. |
| POST | `/api/schedule/factory/{factory_id}/check-readiness` | management | Re-check readiness for ALL active positions: stone, materials, |

## 5. Materials (`/api/materials`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/materials` | any_auth | List materials |
| GET | `/api/materials/low-stock` | any_auth | Low stock alerts — accessible to warehouse + purchaser. |
| GET | `/api/materials/effective-balance` | any_auth | Effective balance = current balance minus reserved for active orders. |
| GET | `/api/materials/consumption-adjustments` | any_auth | List consumption adjustments — pending corrections for PM review. |
| POST | `/api/materials/consumption-adjustments/{adj_id}/approve` | management | Approve a consumption adjustment — updates shape coefficient. |
| POST | `/api/materials/consumption-adjustments/{adj_id}/reject` | management | Reject a consumption adjustment — no coefficient change. |
| GET | `/api/materials/duplicates` | admin | Find potential duplicate materials by similar names. |
| POST | `/api/materials/merge` | admin | Merge multiple materials into one. Moves all references, sums stock balances, |
| POST | `/api/materials/cleanup-duplicates` | admin | Auto-detect and merge duplicate materials. |
| POST | `/api/materials/ensure-all-stocks` | admin | Backfill: create missing MaterialStock rows for all active factories. |
| GET | `/api/materials/substitutions` | any_auth | List all active material substitution pairs. |
| POST | `/api/materials/substitutions` | management | Create a new material substitution pair. |
| DELETE | `/api/materials/substitutions/{sub_id}` | management | Soft-delete a substitution pair. |
| GET | `/api/materials/substitutions/check/{material_id}` | any_auth | Check available substitutes for a material at a factory. |
| GET | `/api/materials/{material_id}` | any_auth | Get material |
| POST | `/api/materials` | any_auth | Create material |
| PATCH | `/api/materials/{material_id}` | any_auth | Update material |
| PUT | `/api/materials/{material_id}/min-balance` | management | PM manually overrides min_balance for a material. Disables auto-calculation. |
| DELETE | `/api/materials/{material_id}` | admin | Delete a material and all its related records. Owner/Admin only. |
| GET | `/api/materials/{material_id}/transactions` | any_auth | List material transactions |
| POST | `/api/materials/transactions` | any_auth | Manual receive, write-off, or inventory adjustment transaction. |
| POST | `/api/materials/transactions/{transaction_id}/approve` | management | PM approves/rejects/partially accepts a pending material receipt. |
| DELETE | `/api/materials/transactions/{transaction_id}` | any_auth | Delete a material transaction and reverse its stock effect. |
| POST | `/api/materials/purchase-requests` | any_auth | Create purchase request |
| POST | `/api/materials/purchase-requests/{pr_id}/approve` | management | PM approves auto-reorder purchase request. |
| POST | `/api/materials/purchase-requests/{pr_id}/edit-approve` | management | PM edits quantities and approves. CEO gets notification about changes. |
| POST | `/api/materials/purchase-requests/{pr_id}/reject` | management | PM rejects auto-reorder with reason. CEO gets notification. |
| POST | `/api/materials/purchase-requests/{pr_id}/receive-partial` | management | Record a partial delivery for a purchase request. |
| POST | `/api/materials/purchase-requests/{pr_id}/resolve-deficit` | management | PM resolves a partial delivery deficit. |

## 6. Recipes (`/api/recipes`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/recipes/engobe/shelf-coating` | any_auth | List shelf coating engobe recipes. |
| GET | `/api/recipes` | any_auth | List recipes |
| GET | `/api/recipes/lookup` | any_auth | Look up recipe by up to 7 fields.  Returns best match + alternatives. |
| POST | `/api/recipes/import-csv` | admin | Import recipes from a CSV file. |
| GET | `/api/recipes/temperature-groups` | management | List all firing temperature groups. Management role required. |
| GET | `/api/recipes/temperature-groups/{group_id}/recipes` | management | Get all recipes linked to a temperature group. Management role required. |
| GET | `/api/recipes/{item_id}` | any_auth | Get recipes item |
| POST | `/api/recipes` | any_auth | Create recipes item |
| PATCH | `/api/recipes/{item_id}` | any_auth | Update recipes item |
| DELETE | `/api/recipes/{item_id}` | any_auth | Delete recipes item |
| POST | `/api/recipes/bulk-delete` | any_auth | Delete multiple recipes by IDs. |
| GET | `/api/recipes/{recipe_id}/materials` | any_auth | Get all ingredients for a recipe, with material name/type. |
| PUT | `/api/recipes/{recipe_id}/materials` | any_auth | Replace all ingredients of a recipe (bulk upsert). |
| GET | `/api/recipes/{recipe_id}/firing-stages` | any_auth | Get all firing stages for a recipe, ordered by stage_number. |
| PUT | `/api/recipes/{recipe_id}/firing-stages` | any_auth | Replace all firing stages for a recipe (bulk upsert). |

## 7. Quality (`/api/quality`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/quality/calendar-matrix` | any_auth | QC calendar matrix -- for each day in a date range, returns: |
| GET | `/api/quality/defect-causes` | any_auth | List all defect causes, optional filter by category. |
| POST | `/api/quality/defect-causes` | role(owner,administrator,quality_manager) | Create a new defect cause (admin or quality_manager only). |
| GET | `/api/quality/inspections` | any_auth | List inspections |
| POST | `/api/quality/inspections` | any_auth | Create QC inspection. OK → quality_check_done. Defect → blocked_by_qm + QmBlock. |
| PATCH | `/api/quality/inspections/{inspection_id}` | any_auth | Update inspection |
| POST | `/api/quality/inspections/{inspection_id}/photo` | any_auth | Upload a photo for a QC inspection. Stores as base64 data URL in DB. |
| GET | `/api/quality/positions-for-qc` | any_auth | Positions awaiting quality check. |
| GET | `/api/quality/stats` | any_auth | Dashboard KPI stats. |
| POST | `/api/quality/analyze-photo` | any_auth | Analyze a production photo using LLM vision (Claude). |
| GET | `/api/quality/checklist-items` | any_auth | Return the list of checklist items for a given check type. |
| POST | `/api/quality/pre-kiln-check` | any_auth | Create a pre-kiln quality checklist. |
| GET | `/api/quality/pre-kiln-checks` | any_auth | Get pre-kiln checklist records, optionally filtered by position or factory. |
| POST | `/api/quality/final-check` | any_auth | Create a final quality checklist for packed goods. |
| GET | `/api/quality/final-checks` | any_auth | Get final checklist records, optionally filtered by position or factory. |

## 8. Defects (`/api/defects`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/defects` | any_auth | List defects |
| GET | `/api/defects/repair-queue` | any_auth | Return positions currently in repair status with SLA info. |
| GET | `/api/defects/coefficients` | management | Get current effective defect coefficients for a factory. |
| POST | `/api/defects/positions/{position_id}/override` | role(owner,ceo) | Override defect coefficient for a specific position (Owner / CEO only). |
| POST | `/api/defects/record` | management | Record actual defect percentage after firing and check vs target threshold. |
| GET | `/api/defects/surplus-dispositions` | any_auth | List surplus disposition records — positions routed to showroom, casters, or mana. |
| GET | `/api/defects/surplus-summary` | any_auth | Surplus summary for a factory: total quantities, breakdown by disposition type, |
| POST | `/api/defects/surplus-dispositions/auto-assign` | management | Preview or execute auto-disposition for a surplus position. |
| POST | `/api/defects/surplus-dispositions/batch` | management | Process multiple surplus positions at once — assigns dispositions, |
| GET | `/api/defects/supplier-reports` | management | List supplier defect reports — aggregated on-the-fly from production_defects. |
| POST | `/api/defects/supplier-reports/generate` | management | Generate a detailed supplier defect report for a date range and supplier (glaze_type). |
| GET | `/api/defects/{item_id}` | any_auth | Get defects item |
| POST | `/api/defects` | any_auth | Create defects item |
| PATCH | `/api/defects/{item_id}` | any_auth | Update defects item |
| DELETE | `/api/defects/{item_id}` | any_auth | Delete defects item |

## 9. Tasks (`/api/tasks`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/tasks` | any_auth | List tasks |
| GET | `/api/tasks/{task_id}` | any_auth | Get task |
| POST | `/api/tasks` | management | Create task |
| PATCH | `/api/tasks/{task_id}` | management | Update task |
| POST | `/api/tasks/{task_id}/complete` | any_auth | Complete task |
| POST | `/api/tasks/{task_id}/resolve-shortage` | management | PM resolves a stock shortage: manufacture or decline. |
| POST | `/api/tasks/{task_id}/resolve-size` | management | Admin/PM resolves a size ambiguity: pick existing size or create new. |
| POST | `/api/tasks/{task_id}/resolve-consumption` | management | PM resolves consumption measurement: enters measured rate(s) for recipe. |

## 10. Suppliers (`/api/suppliers`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/suppliers` | any_auth | List suppliers |
| GET | `/api/suppliers/{item_id}/lead-times` | any_auth | Get lead time history and stats for a supplier. |
| GET | `/api/suppliers/{item_id}` | any_auth | Get suppliers item |
| POST | `/api/suppliers` | any_auth | Create suppliers item |
| PATCH | `/api/suppliers/{item_id}` | any_auth | Update suppliers item |
| DELETE | `/api/suppliers/{item_id}` | any_auth | Delete suppliers item |

## 11. Integration (`/api/integration`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/integration/health` | admin | Admin-only diagnostic: check if Sales integration keys are configured (no secrets leaked). |
| GET | `/api/integration/db-check` | admin | Admin-only diagnostic: check actual database state — alembic version, key tables, row counts. |
| GET | `/api/integration/orders/{external_id}/production-status` | public | Public endpoint for Sales app to query order production status. |
| GET | `/api/integration/orders/status-updates` | public | Bulk status endpoint for Sales polling (every 30 min). |
| POST | `/api/integration/orders/{external_id}/request-cancellation` | public | Sales App calls this to request PM review an order cancellation. |
| POST | `/api/integration/webhook/sales-order` | public | Receive order from Sales app. |
| GET | `/api/integration/webhooks` | admin | Admin-only: list Sales webhook events history (for diagnostics). |
| GET | `/api/integration/stubs` | any_auth | Get current state of integration stubs. |
| POST | `/api/integration/stubs` | any_auth | Toggle integration stubs on/off. |

## 12. Users (`/api/users`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/users` | management | List users |
| GET | `/api/users/{user_id}` | admin | Get user |
| POST | `/api/users` | admin | Create user |
| PATCH | `/api/users/{user_id}` | admin | Update user |
| POST | `/api/users/{user_id}/toggle-active` | admin | Toggle user active |
| POST | `/api/users/{user_id}/reset-password` | admin | Admin resets another user's password. |

## 13. Factories (`/api/factories`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/factories` | any_auth | List factories |
| PATCH | `/api/factories/{item_id}/kiln-mode` | admin | Toggle factory kiln constants mode between 'manual' and 'production'. |
| GET | `/api/factories/{factory_id}/estimate` | any_auth | Estimate factory workload: count open positions by stage, |
| GET | `/api/factories/{item_id}` | any_auth | Get factories item |
| POST | `/api/factories` | admin | Create factories item |
| PATCH | `/api/factories/{item_id}` | admin | Update factories item |
| DELETE | `/api/factories/{item_id}` | admin | Delete factories item |
| GET | `/api/factories/{factory_id}/rotation-rules` | any_auth | Get factory-wide default rotation rules (kiln_id IS NULL). |
| PUT | `/api/factories/{factory_id}/rotation-rules` | admin | Create or update factory-wide default rotation rule. |

## 14. Kilns (`/api/kilns`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/kilns/collections` | any_auth | List all collections (for kiln loading rules configuration). |
| GET | `/api/kilns` | any_auth | List kilns |
| GET | `/api/kilns/maintenance/upcoming` | management | List upcoming maintenance across all kilns in a factory. |
| GET | `/api/kilns/{kiln_id}` | any_auth | Get kiln |
| POST | `/api/kilns` | management | Create kiln |
| PATCH | `/api/kilns/{kiln_id}` | management | Update kiln |
| PATCH | `/api/kilns/{kiln_id}/status` | management | Update kiln status |
| DELETE | `/api/kilns/{kiln_id}` | management | Delete a kiln. Removes associated loading rules via CASCADE. |
| GET | `/api/kilns/{kiln_id}/maintenance` | any_auth | List maintenance schedule for a specific kiln. |
| POST | `/api/kilns/{kiln_id}/maintenance` | management | Schedule new maintenance for a kiln. |
| PUT | `/api/kilns/{kiln_id}/maintenance/{schedule_id}` | management | Update a maintenance schedule entry for a kiln. |
| POST | `/api/kilns/{kiln_id}/maintenance/{schedule_id}/complete` | management | Mark maintenance as completed. If recurring, auto-create next occurrence. |
| DELETE | `/api/kilns/{kiln_id}/maintenance/{schedule_id}` | management | Cancel (delete) a scheduled maintenance entry for a kiln. |
| POST | `/api/kilns/{kiln_id}/breakdown` | management | Report kiln breakdown — triggers emergency reschedule. |
| POST | `/api/kilns/{kiln_id}/restore` | management | Mark kiln as operational again after repair. |
| GET | `/api/kilns/{kiln_id}/rotation-rules` | any_auth | Get rotation rules for a specific kiln (falls back to factory default). |
| PUT | `/api/kilns/{kiln_id}/rotation-rules` | management | Create or update rotation rule for a specific kiln. |
| GET | `/api/kilns/{kiln_id}/rotation-check` | any_auth | Check if proposed glaze type complies with rotation rules for this kiln. |

## 15. Kiln Equipment (`/api`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/kilns/{kiln_id}/equipment` | any_auth | Full history of equipment configurations for a kiln (newest first). |
| GET | `/api/kilns/{kiln_id}/equipment/current` | any_auth | Currently installed equipment config (the one with effective_to IS NULL). |
| POST | `/api/kilns/{kiln_id}/equipment` | management | Install a new equipment config. |
| PATCH | `/api/kilns/{kiln_id}/equipment/{config_id}` | management | Patch fields on an existing config. |
| DELETE | `/api/kilns/{kiln_id}/equipment/{config_id}` | management | Delete an equipment config. |
| GET | `/api/temperature-groups/{group_id}/setpoints` | any_auth | Return a calibration row for every kiln, optionally scoped to a factory. |
| PUT | `/api/temperature-groups/{group_id}/setpoints` | management | Create or update the set-point for (temperature_group × current config of kiln). |
| DELETE | `/api/temperature-groups/{group_id}/setpoints/{setpoint_id}` | management | Clear a set-point (e.g. if it was entered by mistake). |

## 16. Recipe Kiln Capability (`/api`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/recipes/{recipe_id}/kiln-capabilities` | any_auth | Returns one row per active kiln in the system (across factories). |
| PUT | `/api/recipes/{recipe_id}/kiln-capabilities/{kiln_id}` | any_auth | Upsert capability |
| DELETE | `/api/recipes/{recipe_id}/kiln-capabilities/{kiln_id}` | any_auth | Delete capability |
| GET | `/api/kilns/{kiln_id}/recipe-capabilities` | any_auth | List kiln recipes |
| POST | `/api/kilns/{kiln_id}/recipe-capabilities/mark-requalification` | any_auth | Flip needs_requalification=true on all capabilities for this kiln. |

## 17. Kiln Maintenance (`/api/kiln-maintenance`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/kiln-maintenance/types` | any_auth | List all maintenance types (any authenticated user). |
| POST | `/api/kiln-maintenance/types` | management | Create a new maintenance type (management only). |
| PUT | `/api/kiln-maintenance/types/{type_id}` | management | Update a maintenance type (management only). |
| GET | `/api/kiln-maintenance/kilns/{kiln_id}` | any_auth | List scheduled maintenance for a specific kiln (any authenticated user). |
| POST | `/api/kiln-maintenance/kilns/{kiln_id}` | management | Schedule new maintenance for a kiln (management only). |
| PUT | `/api/kiln-maintenance/kilns/{kiln_id}/{schedule_id}` | management | Update a maintenance schedule entry (management only). |
| POST | `/api/kiln-maintenance/kilns/{kiln_id}/{schedule_id}/complete` | management | Mark maintenance as completed. If recurring, auto-create the next occurrence. |
| DELETE | `/api/kiln-maintenance/kilns/{kiln_id}/{schedule_id}` | management | Cancel (delete) a scheduled maintenance entry (management only). |
| GET | `/api/kiln-maintenance/upcoming` | management | List upcoming maintenance across all kilns in a factory. |
| GET | `/api/kiln-maintenance` | any_auth | List all maintenance schedules (backward-compatible). |
| GET | `/api/kiln-maintenance/{item_id}` | any_auth | Get a single maintenance schedule entry. |
| POST | `/api/kiln-maintenance` | management | Create a maintenance schedule entry (management only, backward-compatible). |
| PATCH | `/api/kiln-maintenance/{item_id}` | management | Update a maintenance schedule entry (management only). |
| DELETE | `/api/kiln-maintenance/{item_id}` | management | Delete a maintenance schedule entry (management only). |

## 18. Kiln Inspections (`/api/kiln-inspections`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/kiln-inspections/items` | any_auth | List all active inspection checklist items grouped by category. |
| GET | `/api/kiln-inspections` | any_auth | List inspections with optional filters. |
| GET | `/api/kiln-inspections/{inspection_id}` | any_auth | Get inspection |
| DELETE | `/api/kiln-inspections/{inspection_id}` | management | Delete a kiln inspection and its results. |
| POST | `/api/kiln-inspections` | management | Create a new kiln inspection with all checklist results. |
| GET | `/api/kiln-inspections/repairs` | any_auth | List repair log entries. |
| POST | `/api/kiln-inspections/repairs` | management | Create a new repair log entry. |
| PATCH | `/api/kiln-inspections/repairs/{repair_id}` | management | Update repair log entry. |
| DELETE | `/api/kiln-inspections/repairs/{repair_id}` | management | Delete repair |
| GET | `/api/kiln-inspections/matrix` | any_auth | Return inspection data in matrix format: dates × kilns × items. |

## 19. Kiln Constants (`/api/kiln-constants`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/kiln-constants` | any_auth | List kiln constants |
| GET | `/api/kiln-constants/{item_id}` | any_auth | Get kiln constants item |
| POST | `/api/kiln-constants` | admin | Create kiln constants item |
| PATCH | `/api/kiln-constants/{item_id}` | admin | Update kiln constants item |
| DELETE | `/api/kiln-constants/{item_id}` | admin | Delete kiln constants item |

## 20. Reference (`/api/reference`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/reference/product-types` | any_auth | Return all product types (enum values). |
| GET | `/api/reference/stone-types` | any_auth | Return distinct stone material names from the materials table. |
| GET | `/api/reference/glaze-types` | any_auth | Return distinct glaze material names from the materials table. |
| GET | `/api/reference/finish-types` | any_auth | Return distinct finishing values from existing order positions. |
| GET | `/api/reference/shape-types` | any_auth | Return all shape types (enum values). |
| GET | `/api/reference/material-types` | any_auth | Return material types from subgroups (dynamic) with enum fallback. |
| GET | `/api/reference/position-statuses` | any_auth | Return all position statuses (enum values). |
| GET | `/api/reference/collections` | any_auth | Return all collections from the collections table. |
| GET | `/api/reference/application-methods` | any_auth | List all application methods (SS, S, BS, etc.). |
| GET | `/api/reference/application-collections` | any_auth | List all application collections (Authentic, Creative, Exclusive, etc.). |
| GET | `/api/reference/all` | any_auth | Return all reference data in a single payload (for initial frontend load). |
| GET | `/api/reference/shape-coefficients` | any_auth | List all shape consumption coefficients. |
| PUT | `/api/reference/shape-coefficients/{shape}/{product_type}` | management | Update (or create) shape consumption coefficient. PM/Admin only. |
| GET | `/api/reference/bowl-shapes` | any_auth | Return all bowl shape types (for sink configuration). |
| GET | `/api/reference/temperature-groups` | any_auth | List all firing temperature groups with their attached recipes. |
| POST | `/api/reference/temperature-groups` | management | Create a new firing temperature group. PM/Admin only. |
| PUT | `/api/reference/temperature-groups/{group_id}` | management | Update a firing temperature group. PM/Admin only. |
| POST | `/api/reference/temperature-groups/{group_id}/recipes` | management | Attach a recipe to a temperature group. PM/Admin only. |
| DELETE | `/api/reference/temperature-groups/{group_id}/recipes/{recipe_id}` | management | Detach a recipe from a temperature group. PM/Admin only. |
| POST | `/api/reference/collections` | management | Create collection |
| PUT | `/api/reference/collections/{item_id}` | management | Update collection |
| DELETE | `/api/reference/collections/{item_id}` | management | Delete collection |
| GET | `/api/reference/color-collections` | any_auth | Return all color collections (for glaze recipes). |
| POST | `/api/reference/color-collections` | management | Create color collection |
| PUT | `/api/reference/color-collections/{item_id}` | management | Update color collection |
| DELETE | `/api/reference/color-collections/{item_id}` | management | Delete color collection |
| GET | `/api/reference/colors` | any_auth | List colors |
| POST | `/api/reference/colors` | management | Create color |
| PUT | `/api/reference/colors/{item_id}` | management | Update color |
| DELETE | `/api/reference/colors/{item_id}` | management | Delete color |
| GET | `/api/reference/application-types` | any_auth | List application types |
| POST | `/api/reference/application-types` | management | Create application type |
| PUT | `/api/reference/application-types/{item_id}` | management | Update application type |
| DELETE | `/api/reference/application-types/{item_id}` | management | Delete application type |
| GET | `/api/reference/places-of-application` | any_auth | List places of application |
| POST | `/api/reference/places-of-application` | management | Create place of application |
| PUT | `/api/reference/places-of-application/{item_id}` | management | Update place of application |
| DELETE | `/api/reference/places-of-application/{item_id}` | management | Delete place of application |
| GET | `/api/reference/finishing-types` | any_auth | List finishing types |
| POST | `/api/reference/finishing-types` | management | Create finishing type |
| PUT | `/api/reference/finishing-types/{item_id}` | management | Update finishing type |
| DELETE | `/api/reference/finishing-types/{item_id}` | management | Delete finishing type |
| POST | `/api/reference/bulk-import` | management | Generic bulk import for any reference entity. PM/Admin only. |

## 21. Toc (`/api/toc`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/toc/constraints` | any_auth | List TOC constraints (bottleneck config per factory). |
| PATCH | `/api/toc/constraints/{constraint_id}` | management | Update TOC constraint parameters. |
| PATCH | `/api/toc/bottleneck/batch-mode` | management | Toggle constraint batch processing mode. |
| PATCH | `/api/toc/bottleneck/buffer-target` | management | Set buffer target hours for a factory's constraint. |
| GET | `/api/toc/buffer-health` | any_auth | Buffer health metrics — glazed items before kiln constraint. |
| GET | `/api/toc/buffer-zones` | any_auth | TOC buffer zones for active orders. |

## 22. Tps (`/api/tps`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/tps/parameters` | any_auth | List TPS parameters (targets & tolerances per stage). |
| POST | `/api/tps/parameters` | management | Create a TPS parameter target. |
| PATCH | `/api/tps/parameters/{param_id}` | management | Update a TPS parameter. |
| GET | `/api/tps` | any_auth | List TPS shift metrics. |
| POST | `/api/tps` | management | Record a shift metric using the TPS metrics service. |
| GET | `/api/tps/{metric_id}` | any_auth | Get a single TPS shift metric by ID. |
| PATCH | `/api/tps/{metric_id}` | management | Update a TPS shift metric (partial update). |
| DELETE | `/api/tps/{metric_id}` | management | Delete a TPS shift metric. |
| GET | `/api/tps/dashboard-summary` | management | Aggregated TPS dashboard summary. |
| GET | `/api/tps/shift-summary` | any_auth | Collect and return all shift metrics for a factory on a given date. |
| GET | `/api/tps/signal` | any_auth | Evaluate the TPS signal (green/yellow/red) for a factory today. |
| GET | `/api/tps/deviations` | any_auth | List TPS deviations. |
| POST | `/api/tps/deviations` | management | Report a TPS deviation. |
| PATCH | `/api/tps/deviations/{deviation_id}` | management | Update/resolve a TPS deviation. |
| POST | `/api/tps/record` | any_auth | Record operation start/end time for a position. |
| GET | `/api/tps/position/{position_id}/timeline` | any_auth | Get full operation timeline for a position. |
| GET | `/api/tps/throughput` | management | Get stage throughput statistics per factory and date range. |
| GET | `/api/tps/deviations/operations` | management | Get positions with abnormal operation times. |
| GET | `/api/tps/operations` | management | List all operations for a factory. |
| GET | `/api/tps/master-permissions/check/{user_id}/{operation_id}` | any_auth | Check if a user has permission for a specific operation. |
| GET | `/api/tps/master-permissions/{user_id}` | management | List all operation permissions for a master/senior_master. |
| POST | `/api/tps/master-permissions` | management | Grant an operation permission to a master/senior_master. |
| DELETE | `/api/tps/master-permissions/{permission_id}` | management | Revoke an operation permission from a master/senior_master. |
| GET | `/api/tps/achievements/{user_id}` | any_auth | Get achievements for a user with level, progress, next milestone. |
| POST | `/api/tps/achievements/{user_id}/recalculate` | management | Force recalculate all achievements for a user. |
| GET | `/api/tps/process-steps` | any_auth | List process steps with filtering. |
| POST | `/api/tps/process-steps` | management | Create a new process step. |
| PATCH | `/api/tps/process-steps/reorder` | management | Reorder process steps. Sets sequence = index for each step. |
| GET | `/api/tps/process-steps/pipeline` | any_auth | Return filtered pipeline for a specific collection+method combo. |
| PATCH | `/api/tps/process-steps/{step_id}` | management | Partial update of a process step. |
| DELETE | `/api/tps/process-steps/{step_id}` | management | Soft-delete: set is_active=false. |
| GET | `/api/tps/process-steps/{step_id}/standard-work` | any_auth | List all standard work items for a process step. |
| POST | `/api/tps/process-steps/{step_id}/standard-work` | management | Create a standard work item for a process step. |
| POST | `/api/tps/process-steps/{step_id}/standard-work/reorder` | management | Reorder standard work items. Sets sequence = index for each item. |
| PATCH | `/api/tps/process-steps/{step_id}/standard-work/{work_id}` | management | Partial update of a standard work item. |
| DELETE | `/api/tps/process-steps/{step_id}/standard-work/{work_id}` | management | Delete a standard work item. |
| GET | `/api/tps/calibration/log` | any_auth | List calibration log entries with step and factory names. |
| GET | `/api/tps/calibration/status` | management | Current calibration status for all steps in a factory. |
| POST | `/api/tps/calibration/run` | management | Manually trigger calibration analysis for a factory. |
| POST | `/api/tps/calibration/apply` | management | Apply a calibration suggestion. |
| PATCH | `/api/tps/calibration/toggle/{step_id}` | management | Toggle auto_calibrate on/off for a ProcessStep. PM only. |
| PATCH | `/api/tps/calibration/typology-toggle/{speed_id}` | management | Toggle auto_calibrate on/off for a StageTypologySpeed. PM only. |
| POST | `/api/tps/calibration/apply/{step_id}` | management | Manually apply the current EMA-suggested rate for a specific step. PM only. |
| GET | `/api/tps/typologies` | management | List all active typologies. If factory_id omitted — returns cross-factory |
| POST | `/api/tps/typologies/calculate-all` | management | Recalculate capacities for ALL typologies in a factory. |
| POST | `/api/tps/typologies` | management | Create a new kiln loading typology. |
| GET | `/api/tps/typologies/match` | management | Find matching typology for given product parameters. |
| GET | `/api/tps/typologies/{typology_id}` | management | Get a single typology with capacities. |
| PATCH | `/api/tps/typologies/{typology_id}` | management | Partially update a typology. |
| DELETE | `/api/tps/typologies/{typology_id}` | management | Soft-delete a typology (set is_active=False). |
| POST | `/api/tps/typologies/{typology_id}/calculate` | management | Recalculate capacities for a single typology across all kilns. |
| GET | `/api/tps/typologies/{typology_id}/capacities` | management | Get per-kiln capacities for a typology. |
| GET | `/api/tps/stage-speeds` | any_auth | List stage typology speeds with optional filters. |
| POST | `/api/tps/stage-speeds` | management | Create a new stage typology speed entry. |
| PATCH | `/api/tps/stage-speeds/{speed_id}` | management | Partially update a stage typology speed. |
| DELETE | `/api/tps/stage-speeds/{speed_id}` | management | Delete a stage typology speed entry. |
| GET | `/api/tps/stage-speeds/matrix` | any_auth | Return all speeds grouped by typology then stage, for a frontend matrix view. |
| GET | `/api/tps/line-resources` | any_auth | List production line resources (work tables, drying racks, boards). |
| POST | `/api/tps/line-resources` | management | Create a production line resource. |
| PATCH | `/api/tps/line-resources/{resource_id}` | management | Update a production line resource. |
| DELETE | `/api/tps/line-resources/{resource_id}` | management | Soft-delete a production line resource. |
| GET | `/api/tps/kiln-shelves` | any_auth | List kiln shelves, optionally filtered by kiln. |
| POST | `/api/tps/kiln-shelves` | management | Create a kiln shelf linked to a specific kiln. |
| PATCH | `/api/tps/kiln-shelves/{shelf_id}` | management | Update a kiln shelf. |
| POST | `/api/tps/kiln-shelves/{shelf_id}/write-off` | management | Write off a kiln shelf with reason and optional photo. |
| POST | `/api/tps/kiln-shelves/{shelf_id}/increment-cycles` | any_auth | Increment firing cycles counter. Auto-warns when approaching max. |
| GET | `/api/tps/kiln-shelves/analytics` | any_auth | Lifecycle analytics for kiln shelves — OPEX impact, projected replacements. |

## 23. Notifications (`/api/notifications`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/notifications/unread-count` | any_auth | Return count of unread notifications for current user. |
| GET | `/api/notifications` | any_auth | List notifications for the current user, newest first. |
| PATCH | `/api/notifications/{notification_id}/read` | any_auth | Mark a single notification as read. |
| POST | `/api/notifications/read-all` | any_auth | Mark all notifications as read for the current user. |

## 24. Analytics (`/api/analytics`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/analytics/dashboard-summary` | management | Summary metrics for Owner/CEO dashboard. |
| GET | `/api/analytics/production-metrics` | management | Production metrics: daily output, pipeline funnel, critical positions. |
| GET | `/api/analytics/material-metrics` | management | Material usage metrics: deficit items. |
| GET | `/api/analytics/factory-comparison` | owner | Owner only: per-factory KPI comparison cards. |
| GET | `/api/analytics/buffer-health` | management | CEO: per-kiln buffer health status. |
| GET | `/api/analytics/trend-data` | management | Time series data for trend charts. |
| GET | `/api/analytics/activity-feed` | management | CEO: recent activity events feed. |
| GET | `/api/analytics/inventory-report` | management | Monthly inventory adjustment report for CEO/Owner. |
| GET | `/api/analytics/anomalies` | management | Get detected anomalies for a factory (or all factories). |
| GET | `/api/analytics/factory-leaderboard` | management | Factory leaderboard: compare factories across key metrics. |
| GET | `/api/analytics/lead-time/{factory_id}` | management | Factory lead time estimate: active positions, avg cycle, queue days. |
| GET | `/api/analytics/streaks` | management | Streaks + daily challenge for the logged-in PM user. |

## 25. Ai Chat (`/api/ai-chat`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/ai-chat/chat` | any_auth | Send a message to the AI assistant. |
| GET | `/api/ai-chat/sessions` | any_auth | List user's chat sessions, most recent first. |
| GET | `/api/ai-chat/sessions/{session_id}/messages` | any_auth | Get all messages in a chat session. |

## 26. Export (`/api/export`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/export/materials/excel` | management | Export materials data to Excel (XLSX). |
| GET | `/api/export/quality/excel` | management | Export quality inspection data to Excel (XLSX). |
| GET | `/api/export/orders/excel` | management | Export orders to Excel (XLSX). |
| GET | `/api/export/orders/pdf` | management | Export orders to PDF. |
| GET | `/api/export/positions/pdf` | management | Export positions to PDF. |
| POST | `/api/export/owner-monthly` | owner | Owner monthly report with KPIs + financial summary. |
| POST | `/api/export/ceo-daily` | management | CEO daily summary report. |
| GET | `/api/export/ceo-daily/excel` | management | CEO daily report as a multi-sheet Excel workbook. |
| GET | `/api/export/owner-monthly/excel` | owner | Owner monthly report as a multi-sheet Excel workbook. |

## 27. Reports (`/api/reports`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/reports` | management | Available report types. |
| GET | `/api/reports/orders-summary` | management | Orders summary report: totals, completion stats, on-time %. |
| GET | `/api/reports/kiln-load` | management | Per-kiln utilization report. |

## 28. Stages (`/api/stages`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/stages` | any_auth | List stages |
| GET | `/api/stages/{item_id}` | any_auth | Get stages item |
| POST | `/api/stages` | any_auth | Create stages item |
| PATCH | `/api/stages/{item_id}` | any_auth | Update stages item |
| DELETE | `/api/stages/{item_id}` | any_auth | Delete stages item |

## 29. Transcription (`/api/transcription`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/transcription` | management | List transcription logs with pagination and optional filters. |
| GET | `/api/transcription/{log_id}` | management | Get a single transcription log by ID. |

## 30. Telegram (`/api/telegram`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/telegram/bot-status` | admin | Check Telegram bot connection status. |
| GET | `/api/telegram/owner-chat` | admin | Get the current owner/admin Telegram chat ID. |
| PUT | `/api/telegram/owner-chat` | admin | Set the owner/admin Telegram chat ID (stored in database). |
| POST | `/api/telegram/test-chat` | admin | Send a test message to a Telegram chat to verify the chat ID is correct. |
| POST | `/api/telegram/send-message` | admin | Send a custom message via the Telegram bot. Admin only. |
| POST | `/api/telegram/trigger-summary` | admin | Manually trigger evening summary or morning briefing for a factory. |
| GET | `/api/telegram/recent-chats` | admin | Return chats the bot has seen via webhook since last server restart. |
| POST | `/api/telegram/webhook` | public | Telegram webhook endpoint. |
| POST | `/api/telegram/subscribe` | any_auth | Link a Telegram user ID to the authenticated PMS user. |
| DELETE | `/api/telegram/unsubscribe` | any_auth | Unlink Telegram from the authenticated PMS user. |
| GET | `/api/telegram/invite-link/{user_id}` | admin | Generate a Telegram deep link URL for a PMS user. |

## 31. Health (`/api`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/health` | public | Health check |
| GET | `/api/health/env-check` | public | Public diagnostic: which integration keys are configured (values hidden). |
| GET | `/api/health/seed-status` | admin | Admin-only diagnostic: count rows in key reference tables. |
| GET | `/api/health/backup` | admin | Return backup monitoring data from the backup_logs table. |
| POST | `/api/admin/backup` | admin | Trigger a database backup immediately (runs in background). |
| GET | `/api/internal/poll-pms-status` | public | Cloud Scheduler keep-alive / status polling endpoint. |

## 32. Purchaser (`/api/purchaser`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/purchaser` | any_auth | List purchaser |
| GET | `/api/purchaser/stats` | any_auth | Dashboard KPI stats with lead-time analytics. |
| GET | `/api/purchaser/deliveries` | any_auth | Completed or partially received deliveries. |
| GET | `/api/purchaser/deficits` | any_auth | Material deficits — materials where current balance < min_balance. |
| GET | `/api/purchaser/consolidation-suggestions` | any_auth | Return suggestions for consolidating approved PRs by supplier. |
| POST | `/api/purchaser/consolidate` | any_auth | Execute consolidation of specified PR IDs into a single PR. |
| GET | `/api/purchaser/lead-times` | any_auth | Supplier lead times from supplier_lead_times table. |
| GET | `/api/purchaser/{item_id}` | any_auth | Get purchaser item |
| POST | `/api/purchaser` | any_auth | Create purchaser item |
| PATCH | `/api/purchaser/{item_id}` | any_auth | Update purchaser item |
| PATCH | `/api/purchaser/{item_id}/status` | any_auth | Full status workflow: |
| DELETE | `/api/purchaser/{item_id}` | any_auth | Delete purchaser item |

## 33. Kiln Loading Rules (`/api/kiln-loading-rules`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/kiln-loading-rules` | any_auth | List kiln loading rules |
| GET | `/api/kiln-loading-rules/{item_id}` | any_auth | Get kiln loading rules item |
| POST | `/api/kiln-loading-rules` | management | Create kiln loading rules item |
| PATCH | `/api/kiln-loading-rules/{item_id}` | management | Update kiln loading rules item |
| DELETE | `/api/kiln-loading-rules/{item_id}` | management | Delete kiln loading rules item |

## 34. Kiln Firing Schedules (`/api/kiln-firing-schedules`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/kiln-firing-schedules` | any_auth | List kiln firing schedules |
| GET | `/api/kiln-firing-schedules/{item_id}` | any_auth | Get kiln firing schedules item |
| POST | `/api/kiln-firing-schedules` | any_auth | Create kiln firing schedules item |
| PATCH | `/api/kiln-firing-schedules/{item_id}` | any_auth | Update kiln firing schedules item |
| DELETE | `/api/kiln-firing-schedules/{item_id}` | any_auth | Delete kiln firing schedules item |

## 35. Dashboard Access (`/api/dashboard-access`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/dashboard-access` | admin | List dashboard access |
| GET | `/api/dashboard-access/my` | any_auth | Return current user's accessible dashboards. |
| GET | `/api/dashboard-access/{item_id}` | admin | Get dashboard access item |
| POST | `/api/dashboard-access` | admin | Create dashboard access item |
| PATCH | `/api/dashboard-access/{item_id}` | admin | Update dashboard access item |
| DELETE | `/api/dashboard-access/{item_id}` | admin | Delete dashboard access item |

## 36. Notification Preferences (`/api/notification-preferences`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/notification-preferences` | any_auth | List notification preferences |
| GET | `/api/notification-preferences/{item_id}` | any_auth | Get notification preferences item |
| POST | `/api/notification-preferences` | any_auth | Create notification preferences item |
| PATCH | `/api/notification-preferences/{item_id}` | any_auth | Update notification preferences item |
| DELETE | `/api/notification-preferences/{item_id}` | any_auth | Delete notification preferences item |

## 37. Financials (`/api/financials`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/financials/summary` | role(owner,ceo) | Financial summary: OPEX/CAPEX totals, revenue, margin, cost per sqm. |
| GET | `/api/financials` | role(owner,ceo) | List financials |
| GET | `/api/financials/{item_id}` | role(owner,ceo) | Get financials item |
| POST | `/api/financials` | role(owner) | Create financials item |
| PATCH | `/api/financials/{item_id}` | role(owner) | Update financials item |
| DELETE | `/api/financials/{item_id}` | role(owner) | Delete financials item |

## 38. Warehouse Sections (`/api/warehouse-sections`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/warehouse-sections` | any_auth | List warehouse sections with optional filters. |
| GET | `/api/warehouse-sections/all` | admin_or_pm | List ALL warehouse sections (admin view, including inactive). |
| GET | `/api/warehouse-sections/{item_id}` | any_auth | Get warehouse section |
| POST | `/api/warehouse-sections` | admin_or_pm | Create a new warehouse section. Owner/Admin only. |
| PATCH | `/api/warehouse-sections/{item_id}` | admin_or_pm | Update a warehouse section. Owner/Admin only. |
| DELETE | `/api/warehouse-sections/{item_id}` | admin_or_pm | Delete a warehouse section. Owner/Admin only. |

## 39. Reconciliations (`/api/reconciliations`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/reconciliations` | any_auth | List reconciliations |
| GET | `/api/reconciliations/{reconciliation_id}/items` | any_auth | Return all items for a reconciliation, with material name. |
| POST | `/api/reconciliations/{reconciliation_id}/items` | any_auth | Add items to an in-progress reconciliation. |
| POST | `/api/reconciliations/{reconciliation_id}/complete` | management | Finalize a reconciliation: mark as completed and create adjustment |
| GET | `/api/reconciliations/{item_id}` | any_auth | Get reconciliations item |
| POST | `/api/reconciliations` | any_auth | Create reconciliations item |
| PATCH | `/api/reconciliations/{item_id}` | any_auth | Update reconciliations item |
| DELETE | `/api/reconciliations/{item_id}` | any_auth | Delete reconciliations item |

## 40. Qm Blocks (`/api/qm-blocks`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/qm-blocks` | any_auth | List qm blocks |
| GET | `/api/qm-blocks/{item_id}` | any_auth | Get qm blocks item |
| POST | `/api/qm-blocks` | any_auth | Create qm blocks item |
| PATCH | `/api/qm-blocks/{item_id}` | any_auth | Update qm blocks item |
| DELETE | `/api/qm-blocks/{item_id}` | any_auth | Delete qm blocks item |

## 41. Problem Cards (`/api/problem-cards`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/problem-cards` | any_auth | List problem cards |
| GET | `/api/problem-cards/{item_id}` | any_auth | Get problem cards item |
| POST | `/api/problem-cards` | any_auth | Create problem cards item |
| PATCH | `/api/problem-cards/{item_id}` | any_auth | Update problem cards item |
| DELETE | `/api/problem-cards/{item_id}` | any_auth | Delete problem cards item |

## 42. Security (`/api/security`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/security/audit-log` | admin | Paginated, filterable audit log. |
| GET | `/api/security/audit-log/summary` | admin | Audit log summary: failed logins, unique IPs, anomalies. |
| GET | `/api/security/sessions` | any_auth | List active sessions. Admins see all, users see own. |
| DELETE | `/api/security/sessions/{session_id}` | any_auth | Revoke a specific session. |
| DELETE | `/api/security/sessions` | any_auth | Revoke all other sessions for the current user. |
| GET | `/api/security/ip-allowlist` | admin | List IP allowlist entries. |
| POST | `/api/security/ip-allowlist` | admin | Add IP to allowlist. |
| DELETE | `/api/security/ip-allowlist/{entry_id}` | admin | Remove IP from allowlist (soft delete). |
| POST | `/api/security/totp/setup` | any_auth | Begin TOTP setup: generate secret, provisioning URI, and backup codes. |
| POST | `/api/security/totp/verify` | any_auth | Verify a TOTP code to confirm setup and enable 2FA. |
| POST | `/api/security/totp/disable` | any_auth | Disable TOTP 2FA. Requires a valid TOTP code or backup code. |
| GET | `/api/security/totp/status` | any_auth | Check whether TOTP 2FA is enabled for the current user. |
| POST | `/api/security/totp/backup-codes/regenerate` | any_auth | Regenerate backup codes. Requires a valid TOTP code. Old codes are invalidated. |
| GET | `/api/security/rate-limit-events` | admin | List recent rate limit violation events (admin only). |
| DELETE | `/api/security/rate-limit-events/clear` | admin | Clear rate limit events older than N days (default: 30). Admin only. |

## 43. Websocket (`/api/ws`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| WS | `/api/ws/notifications` | public | Websocket endpoint |

## 44. Packing Photos (`/api/packing-photos`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/packing-photos` | any_auth | List packing photos |
| POST | `/api/packing-photos` | sorting | Create packing photo |
| DELETE | `/api/packing-photos/{photo_id}` | sorting | Delete packing photo |
| POST | `/api/packing-photos/upload` | sorting | Upload a packing photo file directly (multipart form). |

## 45. Finished Goods (`/api/finished-goods`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/finished-goods` | any_auth | List finished goods |
| POST | `/api/finished-goods` | management | Create or update finished goods stock (upsert by unique constraint). |
| PATCH | `/api/finished-goods/{stock_id}` | management | Update finished goods |
| DELETE | `/api/finished-goods/{stock_id}` | management | Delete / write-off a finished goods stock record. Audit-logged. |
| GET | `/api/finished-goods/availability` | any_auth | Check finished goods availability across all factories. |

## 46. Firing Profiles (`/api/firing-profiles`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/firing-profiles` | any_auth | List firing profiles |
| GET | `/api/firing-profiles/{item_id}` | any_auth | Get firing profile |
| POST | `/api/firing-profiles` | any_auth | Create firing profile |
| PATCH | `/api/firing-profiles/{item_id}` | any_auth | Update firing profile |
| DELETE | `/api/firing-profiles/{item_id}` | any_auth | Soft-delete: sets is_active=False. |
| POST | `/api/firing-profiles/match` | any_auth | Test endpoint: find best matching profile for given product_type + collection + thickness. |

## 47. Batches (`/api/batches`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/batches/auto-form` | management | Automatically form batches for a factory. |
| POST | `/api/batches/capacity-preview` | any_auth | Preview how a position would load in a specific kiln. |
| GET | `/api/batches` | any_auth | List batches with optional filters. |
| GET | `/api/batches/{batch_id}` | any_auth | Get batch detail with all assigned positions. |
| POST | `/api/batches/{batch_id}/start` | management | Mark batch as in_progress (kiln loaded, firing started). |
| POST | `/api/batches/{batch_id}/complete` | management | Mark batch as completed (firing done). |
| POST | `/api/batches/{batch_id}/confirm` | management | PM confirms a suggested batch (with optional adjustments). |
| POST | `/api/batches/{batch_id}/reject` | management | PM rejects a suggested batch. Positions are unassigned, batch deleted. |
| POST | `/api/batches` | management | Manually create a batch. |
| PATCH | `/api/batches/{batch_id}` | management | Update batch fields. |
| POST | `/api/batches/{batch_id}/photos` | any_auth | Upload a firing photo for a batch (after kiln unloading). |
| GET | `/api/batches/{batch_id}/photos` | any_auth | Get all photos for a batch. |

## 48. Firing Logs (`/api/batches`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/batches/{batch_id}/firing-log` | any_auth | Create/start a firing log for a batch. |
| PATCH | `/api/batches/{batch_id}/firing-log/{log_id}` | any_auth | Update firing log — set end time, peak temp, result. |
| POST | `/api/batches/{batch_id}/firing-log/{log_id}/reading` | any_auth | Add a temperature reading to the firing log. |
| GET | `/api/batches/{batch_id}/firing-log` | any_auth | Get all firing logs for a batch. |

## 49. Cleanup (`/api/cleanup`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/cleanup/permissions` | role(owner,administrator,ceo,production_manager) | Get current PM cleanup toggles for a factory. |
| PATCH | `/api/cleanup/permissions` | role(owner,administrator,ceo) | Admin/CEO/Owner: toggle PM cleanup permissions for a factory. |
| DELETE | `/api/cleanup/tasks/{task_id}` | role(owner,administrator,ceo,production_manager) | Hard-delete a task. PM requires pm_can_delete_tasks toggle. |
| DELETE | `/api/cleanup/positions/{position_id}` | role(owner,administrator,ceo,production_manager) | Hard-delete a position, its split children and all linked tasks. |
| DELETE | `/api/cleanup/orders/{order_id}` | role(owner,administrator,ceo,production_manager) | Hard-delete an order + all positions, split children, tasks, and order items. |

## 50. Material Groups (`/api/material-groups`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/material-groups/hierarchy` | any_auth | Full nested hierarchy: groups → subgroups with material counts. |
| GET | `/api/material-groups/groups` | any_auth | List all material groups (flat, no subgroups). |
| POST | `/api/material-groups/groups` | admin | Create a new material group. Admin only. |
| PUT | `/api/material-groups/groups/{group_id}` | admin | Update a material group. Admin only. |
| DELETE | `/api/material-groups/groups/{group_id}` | admin | Delete a material group. Admin only. Fails if group has materials. |
| GET | `/api/material-groups/subgroups` | any_auth | List subgroups, optionally filtered by group. |
| POST | `/api/material-groups/subgroups` | admin | Create a new material subgroup. Admin only. |
| PUT | `/api/material-groups/subgroups/{subgroup_id}` | admin | Update a material subgroup. Admin only. |
| DELETE | `/api/material-groups/subgroups/{subgroup_id}` | admin | Delete a material subgroup. Admin only. Fails if subgroup has materials. |

## 51. Packaging (`/api/packaging`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/packaging` | admin_or_pm | List all packaging box types with capacities and spacer rules. |
| GET | `/api/packaging/sizes` | admin_or_pm | List all tile sizes for dropdown. |
| GET | `/api/packaging/{box_type_id}` | admin_or_pm | Get box type |
| POST | `/api/packaging` | admin_or_pm | Create box type |
| PATCH | `/api/packaging/{box_type_id}` | admin_or_pm | Update box type |
| DELETE | `/api/packaging/{box_type_id}` | admin_or_pm | Delete box type |
| PUT | `/api/packaging/{box_type_id}/capacities` | admin_or_pm | Bulk-replace all capacity entries for a box type. |
| PUT | `/api/packaging/{box_type_id}/spacers` | admin_or_pm | Bulk-replace all spacer rules for a box type. |

## 52. Sizes (`/api/sizes`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/sizes/search` | any_auth | Search sizes by dimensions, name, or shape. Used by size resolution UI. |
| GET | `/api/sizes` | any_auth | List all sizes ordered by name. |
| POST | `/api/sizes/recalculate-all-boards` | admin_or_pm | Recalculate glazing board specs for ALL sizes. Use after formula changes. |
| GET | `/api/sizes/{size_id}/glazing-board` | any_auth | Get (or recalculate) glazing board spec for a size. |
| GET | `/api/sizes/{size_id}` | any_auth | Get size |
| POST | `/api/sizes` | admin_or_pm | Create size |
| PATCH | `/api/sizes/{size_id}` | admin_or_pm | Update size |
| DELETE | `/api/sizes/{size_id}` | admin_or_pm | Delete size |

## 53. Consumption Rules (`/api/consumption-rules`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/consumption-rules` | any_auth | List all consumption rules, ordered by rule_number. |
| GET | `/api/consumption-rules/{rule_id}` | any_auth | Get consumption rule |
| POST | `/api/consumption-rules` | admin_or_pm | Create consumption rule |
| PATCH | `/api/consumption-rules/{rule_id}` | admin_or_pm | Update consumption rule |
| DELETE | `/api/consumption-rules/{rule_id}` | admin_or_pm | Delete consumption rule |

## 54. Grinding Stock (`/api/grinding-stock`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/grinding-stock` | any_auth | List grinding stock items, optionally filtered by factory and status. |
| GET | `/api/grinding-stock/stats` | any_auth | Count grinding stock items by status per factory. |
| GET | `/api/grinding-stock/{item_id}` | any_auth | Get a single grinding stock item by ID. |
| POST | `/api/grinding-stock` | management | Create a new grinding stock entry (PM/management only). |
| DELETE | `/api/grinding-stock/{item_id}` | management | Delete a grinding stock item (management only). |
| POST | `/api/grinding-stock/{item_id}/decide` | management | PM decision on a grinding stock item: grind, wait (pending), or send to Mana. |

## 55. Factory Calendar (`/api/factory-calendar`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/factory-calendar/working-days` | any_auth | Count working days between two dates for a factory. |
| GET | `/api/factory-calendar` | any_auth | List calendar entries (non-working days / overrides) for a factory. |
| POST | `/api/factory-calendar` | management | Add a non-working day (or working-day override) to factory calendar. |
| POST | `/api/factory-calendar/bulk` | management | Add multiple holidays / non-working days at once (e.g., Balinese holidays). |
| DELETE | `/api/factory-calendar/{entry_id}` | management | Remove a non-working day from factory calendar. |

## 56. Stone Reservations (`/api/stone-reservations`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/stone-reservations` | management | List stone reservations with optional filters. |
| GET | `/api/stone-reservations/{reservation_id}` | management | Get a single stone reservation with its adjustment log. |
| GET | `/api/stone-reservations/weekly-report` | management | Weekly stone waste report. |
| GET | `/api/stone-reservations/defect-rates` | management | Get stone defect rates configuration. |
| PUT | `/api/stone-reservations/defect-rates` | management | Upsert stone defect rate for a size_category × product_type combination. |
| POST | `/api/stone-reservations/{reservation_id}/adjustments` | management | Create a stone reservation adjustment (writeoff or return). |
| GET | `/api/stone-reservations/{reservation_id}/adjustments` | management | List all adjustments for a stone reservation. |

## 57. Settings (`/api/settings`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/settings/service-lead-times` | management | Returns configured lead times for all service types at the given factory. |
| PUT | `/api/settings/service-lead-times/{factory_id}` | admin | Upsert service lead times for the given factory. |
| POST | `/api/settings/service-lead-times/{factory_id}/reset-defaults` | admin | Delete all custom lead times for the factory, reverting to system defaults. |

## 58. Admin Settings (`/api/admin-settings`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/admin-settings/escalation-rules` | admin | List escalation rules |
| POST | `/api/admin-settings/escalation-rules` | admin | Create escalation rule |
| PATCH | `/api/admin-settings/escalation-rules/{rule_id}` | admin | Update escalation rule |
| DELETE | `/api/admin-settings/escalation-rules/{rule_id}` | admin | Delete escalation rule |
| GET | `/api/admin-settings/receiving-settings` | admin | Get receiving settings |
| PUT | `/api/admin-settings/receiving-settings/{factory_id}` | admin | Upsert receiving settings |
| GET | `/api/admin-settings/defect-thresholds` | admin | List defect thresholds |
| PUT | `/api/admin-settings/defect-thresholds/{material_id}` | admin | Upsert defect threshold |
| DELETE | `/api/admin-settings/defect-thresholds/{material_id}` | admin | Delete defect threshold |
| GET | `/api/admin-settings/consolidation-settings` | admin | Get consolidation settings |
| PUT | `/api/admin-settings/consolidation-settings/{factory_id}` | admin | Upsert consolidation settings |

## 59. Guides (`/api/guides`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/guides/{role}/{language}` | any_auth | Get a user guide in markdown format for a specific role and language. |
| GET | `/api/guides` | any_auth | List available guides and languages. |

## 60. Delivery (`/api/delivery`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/delivery/process-photo` | public | Process a delivery note photo end-to-end: |

## 61. Employees (`/api/employees`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/employees` | any_auth | List employees, optionally filtered by factory, active status, department, and category. |
| GET | `/api/employees/payroll-summary` | management | Calculate full payroll summary with Indonesian tax/BPJS for a given month. |
| GET | `/api/employees/hr-costs/yearly` | finance | Yearly HR costs breakdown by month — for owner/ceo visibility. |
| GET | `/api/employees/hr-costs/employee/{employee_id}/history` | finance | Per-employee monthly payroll history for a year — for owner/ceo drill-down. |
| GET | `/api/employees/payroll-pdf` | management | Generate and return payroll summary as PDF. |
| GET | `/api/employees/payroll-pdf-employee` | management | Generate and return individual employee payslip as PDF. |
| GET | `/api/employees/{employee_id}` | any_auth | Get a single employee by ID. |
| POST | `/api/employees` | management | Create a new employee. |
| PATCH | `/api/employees/{employee_id}` | management | Update an employee. Partial update. |
| DELETE | `/api/employees/{employee_id}` | management | Soft-delete: set is_active=False. |
| GET | `/api/employees/{employee_id}/attendance` | any_auth | Get attendance records for an employee, filtered by date range or year/month. |
| POST | `/api/employees/{employee_id}/attendance` | management | Record attendance for an employee on a date. |
| PATCH | `/api/employees/attendance/{attendance_id}` | management | Update an attendance record. |
| DELETE | `/api/employees/attendance/{attendance_id}` | management | Delete (reset) an attendance record for a specific day. |

## 62. Mana Shipments (`/api/mana-shipments`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/mana-shipments` | any_auth | List mana shipments |
| GET | `/api/mana-shipments/{item_id}` | any_auth | Get mana shipment |
| PATCH | `/api/mana-shipments/{item_id}` | any_auth | Update mana shipment |
| POST | `/api/mana-shipments/{item_id}/confirm` | any_auth | Confirm mana shipment |
| POST | `/api/mana-shipments/{item_id}/ship` | any_auth | Ship mana shipment |
| DELETE | `/api/mana-shipments/{item_id}` | any_auth | Delete mana shipment |

## 63. Gamification (`/api/gamification`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/gamification/skills/badges` | any_auth | List all skill badges for a factory. |
| POST | `/api/gamification/skills/badges/seed` | management | Seed default skill badges for a factory. |
| GET | `/api/gamification/skills/user/{user_id}` | any_auth | Get all skills and progress for a user. |
| POST | `/api/gamification/skills/start` | any_auth | Start learning a new skill. |
| POST | `/api/gamification/skills/request-certification` | any_auth | Worker requests certification after meeting all requirements. |
| POST | `/api/gamification/skills/certify` | management | PM/CEO approves skill certification. |
| POST | `/api/gamification/skills/revoke` | management | PM/CEO revokes a certification. |
| GET | `/api/gamification/leaderboard` | any_auth | Top-20 workers by points for a given period (year/month/week). |
| GET | `/api/gamification/points/my` | any_auth | Current user's points summary and rank. |
| GET | `/api/gamification/competitions` | any_auth | List competitions for a factory. |
| GET | `/api/gamification/competitions/{competition_id}/standings` | any_auth | Get competition standings/leaderboard. |
| POST | `/api/gamification/competitions` | management | PM/CEO creates a new individual competition. |
| POST | `/api/gamification/competitions/team` | management | PM/CEO creates a team competition. |
| POST | `/api/gamification/competitions/propose` | any_auth | Worker proposes a challenge (needs PM approval). |
| POST | `/api/gamification/competitions/{competition_id}/approve` | management | PM/CEO approves a proposed challenge. |
| POST | `/api/gamification/competitions/update-scores` | management | Manually trigger score update for active competitions. |
| GET | `/api/gamification/prizes` | management | List prize recommendations. |
| POST | `/api/gamification/prizes/generate-monthly` | owner | Generate monthly prize recommendations. |
| POST | `/api/gamification/prizes/generate-quarterly` | owner | Generate quarterly prize recommendations (budget = 2.5x monthly). |
| POST | `/api/gamification/prizes/{prize_id}/approve` | owner | CEO/Owner approves a prize recommendation. |
| POST | `/api/gamification/prizes/{prize_id}/reject` | owner | CEO/Owner rejects a prize recommendation. |
| POST | `/api/gamification/prizes/{prize_id}/award` | owner | Mark a prize as awarded. |
| GET | `/api/gamification/ceo-dashboard` | owner | Get CEO gamification dashboard data. |
| GET | `/api/gamification/ceo-dashboard/impact` | owner | Get productivity impact analysis. |
| POST | `/api/gamification/ceo-dashboard/send-report` | owner | Manually trigger CEO weekly gamification report. |
| GET | `/api/gamification/seasons` | any_auth | List gamification seasons. |

## 64. Workforce (`/api/workforce`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/workforce/skills` | any_auth | List all worker-stage skills for a factory. |
| GET | `/api/workforce/skills/user/{user_id}` | any_auth | Get all stage skills for a specific user. |
| POST | `/api/workforce/skills` | management | Assign a stage skill to a worker. |
| PUT | `/api/workforce/skills/{skill_id}` | management | Update proficiency level for a worker-stage skill. |
| DELETE | `/api/workforce/skills/{skill_id}` | management | Remove a skill assignment from a worker. |
| GET | `/api/workforce/shifts` | any_auth | List shift definitions for a factory. |
| POST | `/api/workforce/shifts` | management | Create a new shift definition. |
| PUT | `/api/workforce/shifts/{shift_id}` | management | Update a shift definition. |
| DELETE | `/api/workforce/shifts/{shift_id}` | management | Delete a shift definition (only if no assignments reference it). |
| GET | `/api/workforce/assignments` | any_auth | Get shift assignments for a specific date. |
| POST | `/api/workforce/assignments` | management | Assign a worker to a shift on a specific date. |
| DELETE | `/api/workforce/assignments/{assignment_id}` | management | Remove a shift assignment. |
| GET | `/api/workforce/daily-capacity` | any_auth | Get aggregated worker count per stage for a date (from shift assignments). |
| GET | `/api/workforce/optimization/{factory_id}` | management | AI-driven optimal worker distribution suggestions. |

## 65. Onboarding (`/api/onboarding`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/onboarding/progress` | any_auth | Get full onboarding progress for the current user and role. |
| POST | `/api/onboarding/complete-section` | any_auth | Mark a section as read (awards XP_SECTION_READ). |
| POST | `/api/onboarding/submit-quiz` | any_auth | Submit quiz answers, calculate score, award XP if passing. |
| GET | `/api/onboarding/content/{lang}` | any_auth | Get all onboarding content for a specific role. |
| GET | `/api/onboarding/roles` | any_auth | List all roles that have onboarding content. |

## 66. Shipments (`/api/shipments`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/shipments` | any_auth | List shipments, optionally filtered by order_id, factory_id, status. |
| GET | `/api/shipments/{shipment_id}` | any_auth | Get a single shipment with all items. |
| POST | `/api/shipments` | management | Create a new shipment with selected positions (partial shipment support). |
| PATCH | `/api/shipments/{shipment_id}` | management | Update shipment details (tracking, carrier, weight, etc.). |
| POST | `/api/shipments/{shipment_id}/ship` | management | Mark shipment as shipped. Transitions positions to SHIPPED, notifies Sales webhook. |
| POST | `/api/shipments/{shipment_id}/deliver` | management | Mark shipment as delivered. |
| DELETE | `/api/shipments/{shipment_id}` | management | Cancel (delete) a shipment. Only allowed when status is 'prepared'. |

## 67. Pdf Templates (`/api/pdf/templates`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/pdf/templates/` | any_auth | List all registered PDF templates with metadata. |
| GET | `/api/pdf/templates/{template_id}` | any_auth | Get a specific PDF template by ID. |
