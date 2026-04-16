# Moonjar PMS — API Contracts

> Complete endpoint reference. Base path: `/api`
>
> **Auth levels:** `public` = no auth, `any_auth` = any JWT user, `management` = PM/Admin/Owner,
> `admin` = Admin/Owner, `owner` = Owner only, `owner/ceo` = Owner or CEO.
>
> **Frontend column:** ✓ = wired to frontend, `[API-only]` = backend only,
> `[Telegram-only]` = used by Telegram bot, `[Frontend planned]` = not yet wired,
> `[Admin-only]` = admin panel / CLI.

---

## Auth (`/api/auth`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| POST | /login | public | ✓ | Login |
| POST | /google | public | ✓ | Google login |
| POST | /refresh | public | ✓ | Refresh token |
| POST | /logout | any_auth | ✓ | Logout |
| GET | /me | any_auth | ✓ | Get me |
| POST | /logout-all | any_auth | ✓ | Revoke ALL active sessions for the current user. |
| POST | /verify-owner-key | public | ✓ | First-time owner setup: verify the OWNER_KEY to claim the owner account. |
| POST | /totp-verify | public | ✓ | Complete login by verifying a TOTP code (or backup code) after password auth. |
| POST | /change-password | any_auth | `[API-only]` | Change password for the authenticated user. |

---

## Orders (`/api/orders`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | management | ✓ | List orders |
| GET | /cancellation-requests | management | ✓ | List orders with pending (or all) cancellation requests. PM dashboard uses this. |
| GET | /change-requests | management | ✓ | List orders with pending change requests from Sales. PM dashboard uses this. |
| POST | /upload-pdf | management | ✓ | Upload a PDF order document for parsing. |
| POST | /confirm-pdf | management | ✓ | Confirm a parsed PDF order — creates the actual order and positions. |
| POST | /{order_id}/reprocess | management | ✓ | Re-run the intake pipeline for all positions of an existing order. |
| GET | /{order_id}/debug-sqm | management | ✓ | Debug endpoint: read glazeable_sqm directly via raw SQL. |
| POST | /{order_id}/reschedule | management | ✓ | Reschedule an order: recalculate planned dates, assign kilns, reserve materials. |
| GET | /{order_id} | management | ✓ | Get order |
| POST | / | management | ✓ | Create an order manually (PM form or future PDF upload). |
| PATCH | /{order_id} | management | ✓ | Update order |
| DELETE | /{order_id} | management | ✓ | Cancel order |
| PATCH | /{order_id}/ship | management | ✓ | Mark order as shipped. All READY_FOR_SHIPMENT positions → SHIPPED. |
| POST | /{order_id}/accept-cancellation | management | ✓ | PM accepts the cancellation request → order status → CANCELLED. |
| POST | /{order_id}/reject-cancellation | management | ✓ | PM rejects the cancellation request → order continues as-is. |
| GET | /{order_id}/change-requests | management | ✓ | List all change requests for a specific order (history + pending). |
| POST | /{order_id}/approve-change | management | ✓ | PM approves the change request → apply stored payload changes to the order. |
| POST | /{order_id}/reject-change | management | ✓ | PM rejects the change request → discard stored changes. |

---

## Positions (`/api/positions`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | ✓ | List positions |
| GET | /blocking-summary | any_auth | ✓ | Return a summary of all blocked positions with related tasks and shortages. |
| GET | /{position_id} | any_auth | ✓ | Get position |
| PATCH | /{position_id} | management | ✓ | Update position |
| POST | /batch-transitions | any_auth | ✓ | Return allowed transitions for multiple positions in a single request. |
| GET | /{position_id}/allowed-transitions | any_auth | ✓ | Return list of allowed next statuses for a position. |
| POST | /{position_id}/status | any_auth | ✓ | Change position status |
| POST | /{position_id}/split | sorting+ | ✓ | Sort a fired position: split into good/refire/repair/color_mismatch/grinding/write-off. |
| POST | /{position_id}/resolve-color-mismatch | management | ✓ | PM resolves a color-mismatch sub-position by directing tiles into up to 3 paths: |
| GET | /{position_id}/stock-availability | any_auth | ✓ | Check finished goods availability for a stock position (informational, shown before sorting). |
| GET | /{position_id}/force-unblock-options | management | ✓ | Return context-aware unblock options based on position's current blocking status. |
| POST | /{position_id}/force-unblock | management | ✓ | PM force-unblock: override any blocking status with context-aware action. |
| GET | /{position_id}/material-reservations | any_auth | ✓ | Return material reservation details for a position. |
| POST | /reorder | management | ✓ | Batch update priority_order for multiple positions. |
| POST | /{position_id}/reassign-batch | management | ✓ | Move a position to a different batch (or remove from batch). |
| POST | /{position_id}/split-production | management | ✓ | PM splits a position during production. |
| GET | /{position_id}/split-tree | management | ✓ | Get full split tree (parent + all descendants) for a position. |
| GET | /{position_id}/mergeable-children | any_auth | ✓ | Get list of children that can be merged back into this parent. |
| POST | /{position_id}/merge | management | ✓ | Merge a child sub-position back into parent position. |
| GET | /{position_id}/materials | any_auth | ✓ | Get material requirements for a position with reservation status. |

---

## Schedule (`/api/schedule`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /resources | any_auth | ✓ | List resources |
| GET | /batches | any_auth | ✓ | List batches |
| POST | /batches | management | ✓ | Create batch |
| GET | /glazing-schedule | any_auth | ✓ | Get glazing schedule |
| GET | /firing-schedule | any_auth | ✓ | Get firing schedule |
| GET | /sorting-schedule | any_auth | ✓ | Get sorting schedule |
| GET | /qc-schedule | any_auth | ✓ | Positions currently in QC pipeline. |
| GET | /kiln-schedule | any_auth | ✓ | Batches grouped by kiln. |
| PATCH | /positions/reorder | management | ✓ | Bulk reorder positions — assigns sequential priority_order values. |
| POST | /batches/{batch_id}/positions | management | ✓ | Assign positions to an existing batch. |
| GET | /orders/{order_id}/schedule | any_auth | ✓ | Full production schedule for an order — visible to Sales for |
| POST | /orders/{order_id}/reschedule | management | ✓ | Manually trigger a full reschedule of all positions in an order. |
| POST | /orders/{order_id}/reschedule-debug | management | `[API-only]` | Debug: reschedule order and return errors. |
| POST | /factory/{factory_id}/reschedule | management | ✓ | Reschedule all active positions across all orders in a factory. |
| POST | /factory/{factory_id}/reschedule-overdue | management | ✓ | Replan all overdue positions using the full scheduling engine. |
| GET | /positions/{position_id}/schedule | any_auth | ✓ | Schedule details for a single position — planned dates, kiln |
| POST | /optimize-batch/{batch_id} | management | `[API-only]` | Find candidate positions to fill remaining capacity in a batch. |
| GET | /kiln-utilization | any_auth | `[API-only]` | Kiln utilization metrics for a factory over the past N days. |
| GET | /production-schedule | any_auth | ✓ | Forward-looking daily production schedule view for N days. |
| POST | /recalculate | management | ✓ | Full factory schedule recalculation orchestrator. |
| GET | /config/{factory_id} | management | ✓ | Get scheduler configuration for a factory (buffer days, auto-buffer settings). |
| PUT | /config/{factory_id} | management | ✓ | Update scheduler configuration for a factory. PM/CEO only. |
| POST | /factory/{factory_id}/check-readiness | management | ✓ | Re-check readiness for ALL active positions: stone, materials, |

---

## Materials (`/api/materials`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | ✓ | List materials |
| GET | /low-stock | any_auth | ✓ | Low stock alerts — accessible to warehouse + purchaser. |
| GET | /effective-balance | any_auth | `[API-only]` | Effective balance = current balance minus reserved for active orders. |
| GET | /consumption-adjustments | any_auth | ✓ | List consumption adjustments — pending corrections for PM review. |
| POST | /consumption-adjustments/{adj_id}/approve | management | ✓ | Approve a consumption adjustment — updates shape coefficient. |
| POST | /consumption-adjustments/{adj_id}/reject | management | ✓ | Reject a consumption adjustment — no coefficient change. |
| GET | /duplicates | admin | ✓ | Find potential duplicate materials by similar names. |
| POST | /merge | admin | ✓ | Merge multiple materials into one. Moves all references, sums stock balances, |
| POST | /cleanup-duplicates | admin | ✓ | Auto-detect and merge duplicate materials. |
| POST | /ensure-all-stocks | admin | ✓ | Backfill: create missing MaterialStock rows for all active factories. |
| GET | /substitutions | any_auth | `[API-only]` | List all active material substitution pairs. |
| POST | /substitutions | management | `[API-only]` | Create a new material substitution pair. |
| DELETE | /substitutions/{sub_id} | management | `[API-only]` | Soft-delete a substitution pair. |
| GET | /substitutions/check/{material_id} | any_auth | ✓ | Check available substitutes for a material at a factory. |
| GET | /{material_id} | any_auth | ✓ | Get material |
| POST | / | any_auth | ✓ | Create material |
| PATCH | /{material_id} | any_auth | ✓ | Update material |
| PUT | /{material_id}/min-balance | management | ✓ | PM manually overrides min_balance for a material. Disables auto-calculation. |
| DELETE | /{material_id} | admin | ✓ | Delete a material and all its related records. Owner/Admin only. |
| GET | /{material_id}/transactions | any_auth | ✓ | List material transactions |
| POST | /transactions | any_auth | ✓ | Manual receive, write-off, or inventory adjustment transaction. |
| POST | /transactions/{transaction_id}/approve | management | ✓ | PM approves/rejects/partially accepts a pending material receipt. |
| DELETE | /transactions/{transaction_id} | any_auth | ✓ | Delete a material transaction and reverse its stock effect. |
| POST | /purchase-requests | any_auth | ✓ | Create purchase request |
| POST | /purchase-requests/{pr_id}/approve | management | ✓ | PM approves auto-reorder purchase request. |
| POST | /purchase-requests/{pr_id}/edit-approve | management | ✓ | PM edits quantities and approves. CEO gets notification about changes. |
| POST | /purchase-requests/{pr_id}/reject | management | ✓ | PM rejects auto-reorder with reason. CEO gets notification. |
| POST | /purchase-requests/{pr_id}/receive-partial | management | ✓ | Record a partial delivery for a purchase request. |
| POST | /purchase-requests/{pr_id}/resolve-deficit | management | ✓ | PM resolves a partial delivery deficit. |

---

## Recipes (`/api/recipes`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /engobe/shelf-coating | any_auth | `[API-only]` | List shelf coating engobe recipes. |
| GET | / | any_auth | ✓ | List recipes |
| GET | /lookup | any_auth | ✓ | Look up recipe by up to 7 fields.  Returns best match + alternatives. |
| POST | /import-csv | admin | `[API-only]` | Import recipes from a CSV file. |
| GET | /temperature-groups | management | ✓ | List all firing temperature groups. Management role required. |
| GET | /temperature-groups/{group_id}/recipes | management | ✓ | Get all recipes linked to a temperature group. Management role required. |
| GET | /{item_id} | any_auth | ✓ | Get recipes item |
| POST | / | any_auth | ✓ | Create recipes item |
| PATCH | /{item_id} | any_auth | ✓ | Update recipes item |
| DELETE | /{item_id} | any_auth | ✓ | Delete recipes item |
| POST | /bulk-delete | any_auth | ✓ | Delete multiple recipes by IDs. |
| GET | /{recipe_id}/materials | any_auth | ✓ | Get all ingredients for a recipe, with material name/type. |
| PUT | /{recipe_id}/materials | any_auth | ✓ | Replace all ingredients of a recipe (bulk upsert). |
| GET | /{recipe_id}/firing-stages | any_auth | ✓ | Get all firing stages for a recipe, ordered by stage_number. |
| PUT | /{recipe_id}/firing-stages | any_auth | ✓ | Replace all firing stages for a recipe (bulk upsert). |

---

## Quality (`/api/quality`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /calendar-matrix | any_auth | `[API-only]` | QC calendar matrix -- for each day in a date range, returns: |
| GET | /defect-causes | any_auth | ✓ | List all defect causes, optional filter by category. |
| POST | /defect-causes | role(owner,administrator,quality_manager) | ✓ | Create a new defect cause (admin or quality_manager only). |
| GET | /inspections | any_auth | ✓ | List inspections |
| POST | /inspections | any_auth | ✓ | Create QC inspection. OK → quality_check_done. Defect → blocked_by_qm + QmBlock. |
| PATCH | /inspections/{inspection_id} | any_auth | ✓ | Update inspection |
| POST | /inspections/{inspection_id}/photo | any_auth | ✓ | Upload a photo for a QC inspection. Stores as base64 data URL in DB. |
| GET | /positions-for-qc | any_auth | ✓ | Positions awaiting quality check. |
| GET | /stats | any_auth | ✓ | Dashboard KPI stats. |
| POST | /analyze-photo | any_auth | `[API-only]` | Analyze a production photo using LLM vision (Claude). |
| GET | /checklist-items | any_auth | ✓ | Return the list of checklist items for a given check type. |
| POST | /pre-kiln-check | any_auth | ✓ | Create a pre-kiln quality checklist. |
| GET | /pre-kiln-checks | any_auth | ✓ | Get pre-kiln checklist records, optionally filtered by position or factory. |
| POST | /final-check | any_auth | ✓ | Create a final quality checklist for packed goods. |
| GET | /final-checks | any_auth | ✓ | Get final checklist records, optionally filtered by position or factory. |

---

## Defects (`/api/defects`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | ✓ | List defects |
| GET | /repair-queue | any_auth | `[API-only]` | Return positions currently in repair status with SLA info. |
| GET | /coefficients | management | ✓ | Get current effective defect coefficients for a factory. |
| POST | /positions/{position_id}/override | role(owner,ceo) | ✓ | Override defect coefficient for a specific position (Owner / CEO only). |
| POST | /record | management | ✓ | Record actual defect percentage after firing and check vs target threshold. |
| GET | /surplus-dispositions | any_auth | `[API-only]` | List surplus disposition records — positions routed to showroom, casters, or mana. |
| GET | /surplus-summary | any_auth | `[API-only]` | Surplus summary for a factory: total quantities, breakdown by disposition type, |
| POST | /surplus-dispositions/auto-assign | management | `[API-only]` | Preview or execute auto-disposition for a surplus position. |
| POST | /surplus-dispositions/batch | management | ✓ | Process multiple surplus positions at once — assigns dispositions, |
| GET | /supplier-reports | management | `[API-only]` | List supplier defect reports — aggregated on-the-fly from production_defects. |
| POST | /supplier-reports/generate | management | ✓ | Generate a detailed supplier defect report for a date range and supplier (glaze_type). |
| GET | /{item_id} | any_auth | ✓ | Get defects item |
| POST | / | any_auth | ✓ | Create defects item |
| PATCH | /{item_id} | any_auth | ✓ | Update defects item |
| DELETE | /{item_id} | any_auth | ✓ | Delete defects item |

---

## Tasks (`/api/tasks`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | ✓ | List tasks |
| GET | /{task_id} | any_auth | ✓ | Get task |
| POST | / | management | ✓ | Create task |
| PATCH | /{task_id} | management | ✓ | Update task |
| POST | /{task_id}/complete | any_auth | ✓ | Complete task |
| POST | /{task_id}/resolve-shortage | management | ✓ | PM resolves a stock shortage: manufacture or decline. |
| POST | /{task_id}/resolve-size | management | ✓ | Admin/PM resolves a size ambiguity: pick existing size or create new. |
| POST | /{task_id}/resolve-consumption | management | ✓ | PM resolves consumption measurement: enters measured rate(s) for recipe. |

---

## Suppliers (`/api/suppliers`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | ✓ | List suppliers |
| GET | /{item_id}/lead-times | any_auth | ✓ | Get lead time history and stats for a supplier. |
| GET | /{item_id} | any_auth | ✓ | Get suppliers item |
| POST | / | any_auth | ✓ | Create suppliers item |
| PATCH | /{item_id} | any_auth | ✓ | Update suppliers item |
| DELETE | /{item_id} | any_auth | ✓ | Delete suppliers item |

---

## Integration (`/api/integration`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /health | admin | ✓ | Admin-only diagnostic: check if Sales integration keys are configured (no secrets leaked). |
| GET | /db-check | admin | `[API-only]` | Admin-only diagnostic: check actual database state — alembic version, key tables, row counts. |
| GET | /orders/{external_id}/production-status | public | `[API-only]` | Public endpoint for Sales app to query order production status. |
| GET | /orders/status-updates | public | `[API-only]` | Bulk status endpoint for Sales polling (every 30 min). |
| POST | /orders/{external_id}/request-cancellation | public | `[API-only]` | Sales App calls this to request PM review an order cancellation. |
| POST | /webhook/sales-order | public | `[API-only]` | Receive order from Sales app. |
| GET | /webhooks | admin | `[API-only]` | Admin-only: list Sales webhook events history (for diagnostics). |
| GET | /stubs | any_auth | ✓ | Get current state of integration stubs. |
| POST | /stubs | any_auth | ✓ | Toggle integration stubs on/off. |

---

## Users (`/api/users`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | management | ✓ | List users |
| GET | /{user_id} | admin | ✓ | Get user |
| POST | / | admin | ✓ | Create user |
| PATCH | /{user_id} | admin | ✓ | Update user |
| POST | /{user_id}/toggle-active | admin | ✓ | Toggle user active |
| POST | /{user_id}/reset-password | admin | ✓ | Admin resets another user's password. |

---

## Factories (`/api/factories`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | ✓ | List factories |
| PATCH | /{item_id}/kiln-mode | admin | ✓ | Toggle factory kiln constants mode between 'manual' and 'production'. |
| GET | /{factory_id}/estimate | any_auth | ✓ | Estimate factory workload: count open positions by stage, |
| GET | /{item_id} | any_auth | ✓ | Get factories item |
| POST | / | admin | ✓ | Create factories item |
| PATCH | /{item_id} | admin | ✓ | Update factories item |
| DELETE | /{item_id} | admin | ✓ | Delete factories item |
| GET | /{factory_id}/rotation-rules | any_auth | ✓ | Get factory-wide default rotation rules (kiln_id IS NULL). |
| PUT | /{factory_id}/rotation-rules | admin | ✓ | Create or update factory-wide default rotation rule. |

---

## Kilns (`/api/kilns`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /collections | any_auth | ✓ | List all collections (for kiln loading rules configuration). |
| GET | / | any_auth | ✓ | List kilns |
| GET | /maintenance/upcoming | management | ✓ | List upcoming maintenance across all kilns in a factory. |
| GET | /{kiln_id} | any_auth | ✓ | Get kiln |
| POST | / | management | ✓ | Create kiln |
| PATCH | /{kiln_id} | management | ✓ | Update kiln |
| PATCH | /{kiln_id}/status | management | ✓ | Update kiln status |
| DELETE | /{kiln_id} | management | ✓ | Delete a kiln. Removes associated loading rules via CASCADE. |
| GET | /{kiln_id}/maintenance | any_auth | ✓ | List maintenance schedule for a specific kiln. |
| POST | /{kiln_id}/maintenance | management | ✓ | Schedule new maintenance for a kiln. |
| PUT | /{kiln_id}/maintenance/{schedule_id} | management | ✓ | Update a maintenance schedule entry for a kiln. |
| POST | /{kiln_id}/maintenance/{schedule_id}/complete | management | ✓ | Mark maintenance as completed. If recurring, auto-create next occurrence. |
| DELETE | /{kiln_id}/maintenance/{schedule_id} | management | ✓ | Cancel (delete) a scheduled maintenance entry for a kiln. |
| POST | /{kiln_id}/breakdown | management | ✓ | Report kiln breakdown — triggers emergency reschedule. |
| POST | /{kiln_id}/restore | management | ✓ | Mark kiln as operational again after repair. |
| GET | /{kiln_id}/rotation-rules | any_auth | ✓ | Get rotation rules for a specific kiln (falls back to factory default). |
| PUT | /{kiln_id}/rotation-rules | management | ✓ | Create or update rotation rule for a specific kiln. |
| GET | /{kiln_id}/rotation-check | any_auth | ✓ | Check if proposed glaze type complies with rotation rules for this kiln. |

---

## Kiln Equipment (`/api`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /kilns/{kiln_id}/equipment | any_auth | ✓ | Full history of equipment configurations for a kiln (newest first). |
| GET | /kilns/{kiln_id}/equipment/current | any_auth | ✓ | Currently installed equipment config (the one with effective_to IS NULL). |
| POST | /kilns/{kiln_id}/equipment | management | ✓ | Install a new equipment config. |
| PATCH | /kilns/{kiln_id}/equipment/{config_id} | management | ✓ | Patch fields on an existing config. |
| DELETE | /kilns/{kiln_id}/equipment/{config_id} | management | ✓ | Delete an equipment config. |
| GET | /temperature-groups/{group_id}/setpoints | any_auth | ✓ | Return a calibration row for every kiln, optionally scoped to a factory. |
| PUT | /temperature-groups/{group_id}/setpoints | management | ✓ | Create or update the set-point for (temperature_group × current config of kiln). |
| DELETE | /temperature-groups/{group_id}/setpoints/{setpoint_id} | management | ✓ | Clear a set-point (e.g. if it was entered by mistake). |

---

## Recipe-Kiln Capability (`/api`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /recipes/{recipe_id}/kiln-capabilities | any_auth | ✓ | Returns one row per active kiln in the system (across factories). |
| PUT | /recipes/{recipe_id}/kiln-capabilities/{kiln_id} | any_auth | ✓ | Upsert capability |
| DELETE | /recipes/{recipe_id}/kiln-capabilities/{kiln_id} | any_auth | ✓ | Delete capability |
| GET | /kilns/{kiln_id}/recipe-capabilities | any_auth | ✓ | List kiln recipes |
| POST | /kilns/{kiln_id}/recipe-capabilities/mark-requalification | any_auth | ✓ | Flip needs_requalification=true on all capabilities for this kiln. |

---

## Kiln Maintenance (`/api/kiln-maintenance`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /types | any_auth | ✓ | List all maintenance types (any authenticated user). |
| POST | /types | management | ✓ | Create a new maintenance type (management only). |
| PUT | /types/{type_id} | management | ✓ | Update a maintenance type (management only). |
| GET | /kilns/{kiln_id} | any_auth | ✓ | List scheduled maintenance for a specific kiln (any authenticated user). |
| POST | /kilns/{kiln_id} | management | ✓ | Schedule new maintenance for a kiln (management only). |
| PUT | /kilns/{kiln_id}/{schedule_id} | management | ✓ | Update a maintenance schedule entry (management only). |
| POST | /kilns/{kiln_id}/{schedule_id}/complete | management | ✓ | Mark maintenance as completed. If recurring, auto-create the next occurrence. |
| DELETE | /kilns/{kiln_id}/{schedule_id} | management | ✓ | Cancel (delete) a scheduled maintenance entry (management only). |
| GET | /upcoming | management | ✓ | List upcoming maintenance across all kilns in a factory. |
| GET | / | any_auth | ✓ | List all maintenance schedules (backward-compatible). |
| GET | /{item_id} | any_auth | ✓ | Get a single maintenance schedule entry. |
| POST | / | management | ✓ | Create a maintenance schedule entry (management only, backward-compatible). |
| PATCH | /{item_id} | management | ✓ | Update a maintenance schedule entry (management only). |
| DELETE | /{item_id} | management | ✓ | Delete a maintenance schedule entry (management only). |

---

## Kiln Inspections (`/api/kiln-inspections`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /items | any_auth | ✓ | List all active inspection checklist items grouped by category. |
| GET | / | any_auth | ✓ | List inspections with optional filters. |
| GET | /{inspection_id} | any_auth | ✓ | Get inspection |
| DELETE | /{inspection_id} | management | ✓ | Delete a kiln inspection and its results. |
| POST | / | management | ✓ | Create a new kiln inspection with all checklist results. |
| GET | /repairs | any_auth | ✓ | List repair log entries. |
| POST | /repairs | management | ✓ | Create a new repair log entry. |
| PATCH | /repairs/{repair_id} | management | ✓ | Update repair log entry. |
| DELETE | /repairs/{repair_id} | management | ✓ | Delete repair |
| GET | /matrix | any_auth | ✓ | Return inspection data in matrix format: dates × kilns × items. |

---

## Kiln Constants (`/api/kiln-constants`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | ✓ | List kiln constants |
| GET | /{item_id} | any_auth | ✓ | Get kiln constants item |
| POST | / | admin | ✓ | Create kiln constants item |
| PATCH | /{item_id} | admin | ✓ | Update kiln constants item |
| DELETE | /{item_id} | admin | ✓ | Delete kiln constants item |

---

## Reference Data (`/api/reference`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /product-types | any_auth | ✓ | Return all product types (enum values). |
| GET | /stone-types | any_auth | ✓ | Return distinct stone material names from the materials table. |
| GET | /glaze-types | any_auth | ✓ | Return distinct glaze material names from the materials table. |
| GET | /finish-types | any_auth | ✓ | Return distinct finishing values from existing order positions. |
| GET | /shape-types | any_auth | ✓ | Return all shape types (enum values). |
| GET | /material-types | any_auth | ✓ | Return material types from subgroups (dynamic) with enum fallback. |
| GET | /position-statuses | any_auth | ✓ | Return all position statuses (enum values). |
| GET | /collections | any_auth | ✓ | Return all collections from the collections table. |
| GET | /application-methods | any_auth | ✓ | List all application methods (SS, S, BS, etc.). |
| GET | /application-collections | any_auth | ✓ | List all application collections (Authentic, Creative, Exclusive, etc.). |
| GET | /all | any_auth | ✓ | Return all reference data in a single payload (for initial frontend load). |
| GET | /shape-coefficients | any_auth | `[API-only]` | List all shape consumption coefficients. |
| PUT | /shape-coefficients/{shape}/{product_type} | management | `[API-only]` | Update (or create) shape consumption coefficient. PM/Admin only. |
| GET | /bowl-shapes | any_auth | `[API-only]` | Return all bowl shape types (for sink configuration). |
| GET | /temperature-groups | any_auth | ✓ | List all firing temperature groups with their attached recipes. |
| POST | /temperature-groups | management | ✓ | Create a new firing temperature group. PM/Admin only. |
| PUT | /temperature-groups/{group_id} | management | ✓ | Update a firing temperature group. PM/Admin only. |
| POST | /temperature-groups/{group_id}/recipes | management | ✓ | Attach a recipe to a temperature group. PM/Admin only. |
| DELETE | /temperature-groups/{group_id}/recipes/{recipe_id} | management | ✓ | Detach a recipe from a temperature group. PM/Admin only. |
| POST | /collections | management | ✓ | Create collection |
| PUT | /collections/{item_id} | management | ✓ | Update collection |
| DELETE | /collections/{item_id} | management | ✓ | Delete collection |
| GET | /color-collections | any_auth | ✓ | Return all color collections (for glaze recipes). |
| POST | /color-collections | management | ✓ | Create color collection |
| PUT | /color-collections/{item_id} | management | ✓ | Update color collection |
| DELETE | /color-collections/{item_id} | management | ✓ | Delete color collection |
| GET | /colors | any_auth | ✓ | List colors |
| POST | /colors | management | ✓ | Create color |
| PUT | /colors/{item_id} | management | ✓ | Update color |
| DELETE | /colors/{item_id} | management | ✓ | Delete color |
| GET | /application-types | any_auth | ✓ | List application types |
| POST | /application-types | management | ✓ | Create application type |
| PUT | /application-types/{item_id} | management | ✓ | Update application type |
| DELETE | /application-types/{item_id} | management | ✓ | Delete application type |
| GET | /places-of-application | any_auth | ✓ | List places of application |
| POST | /places-of-application | management | ✓ | Create place of application |
| PUT | /places-of-application/{item_id} | management | ✓ | Update place of application |
| DELETE | /places-of-application/{item_id} | management | ✓ | Delete place of application |
| GET | /finishing-types | any_auth | ✓ | List finishing types |
| POST | /finishing-types | management | ✓ | Create finishing type |
| PUT | /finishing-types/{item_id} | management | ✓ | Update finishing type |
| DELETE | /finishing-types/{item_id} | management | ✓ | Delete finishing type |
| POST | /bulk-import | management | ✓ | Generic bulk import for any reference entity. PM/Admin only. |

---

## TOC (Theory of Constraints) (`/api/toc`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /constraints | any_auth | ✓ | List TOC constraints (bottleneck config per factory). |
| PATCH | /constraints/{constraint_id} | management | ✓ | Update TOC constraint parameters. |
| PATCH | /bottleneck/batch-mode | management | `[API-only]` | Toggle constraint batch processing mode. |
| PATCH | /bottleneck/buffer-target | management | `[API-only]` | Set buffer target hours for a factory's constraint. |
| GET | /buffer-health | any_auth | ✓ | Buffer health metrics — glazed items before kiln constraint. |
| GET | /buffer-zones | any_auth | ✓ | TOC buffer zones for active orders. |

---

## TPS (Toyota Production System) (`/api/tps`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /parameters | any_auth | ✓ | List TPS parameters (targets & tolerances per stage). |
| POST | /parameters | management | ✓ | Create a TPS parameter target. |
| PATCH | /parameters/{param_id} | management | ✓ | Update a TPS parameter. |
| GET | / | any_auth | ✓ | List TPS shift metrics. |
| POST | / | management | ✓ | Record a shift metric using the TPS metrics service. |
| GET | /{metric_id} | any_auth | ✓ | Get a single TPS shift metric by ID. |
| PATCH | /{metric_id} | management | ✓ | Update a TPS shift metric (partial update). |
| DELETE | /{metric_id} | management | ✓ | Delete a TPS shift metric. |
| GET | /dashboard-summary | management | ✓ | Aggregated TPS dashboard summary. |
| GET | /shift-summary | any_auth | `[API-only]` | Collect and return all shift metrics for a factory on a given date. |
| GET | /signal | any_auth | ✓ | Evaluate the TPS signal (green/yellow/red) for a factory today. |
| GET | /deviations | any_auth | `[API-only]` | List TPS deviations. |
| POST | /deviations | management | `[API-only]` | Report a TPS deviation. |
| PATCH | /deviations/{deviation_id} | management | `[API-only]` | Update/resolve a TPS deviation. |
| POST | /record | any_auth | ✓ | Record operation start/end time for a position. |
| GET | /position/{position_id}/timeline | any_auth | ✓ | Get full operation timeline for a position. |
| GET | /throughput | management | ✓ | Get stage throughput statistics per factory and date range. |
| GET | /deviations/operations | management | ✓ | Get positions with abnormal operation times. |
| GET | /operations | management | ✓ | List all operations for a factory. |
| GET | /master-permissions/check/{user_id}/{operation_id} | any_auth | ✓ | Check if a user has permission for a specific operation. |
| GET | /master-permissions/{user_id} | management | `[API-only]` | List all operation permissions for a master/senior_master. |
| POST | /master-permissions | management | `[API-only]` | Grant an operation permission to a master/senior_master. |
| DELETE | /master-permissions/{permission_id} | management | `[API-only]` | Revoke an operation permission from a master/senior_master. |
| GET | /achievements/{user_id} | any_auth | ✓ | Get achievements for a user with level, progress, next milestone. |
| POST | /achievements/{user_id}/recalculate | management | ✓ | Force recalculate all achievements for a user. |
| GET | /process-steps | any_auth | ✓ | List process steps with filtering. |
| POST | /process-steps | management | ✓ | Create a new process step. |
| PATCH | /process-steps/reorder | management | ✓ | Reorder process steps. Sets sequence = index for each step. |
| GET | /process-steps/pipeline | any_auth | ✓ | Return filtered pipeline for a specific collection+method combo. |
| PATCH | /process-steps/{step_id} | management | ✓ | Partial update of a process step. |
| DELETE | /process-steps/{step_id} | management | ✓ | Soft-delete: set is_active=false. |
| GET | /process-steps/{step_id}/standard-work | any_auth | ✓ | List all standard work items for a process step. |
| POST | /process-steps/{step_id}/standard-work | management | ✓ | Create a standard work item for a process step. |
| POST | /process-steps/{step_id}/standard-work/reorder | management | ✓ | Reorder standard work items. Sets sequence = index for each item. |
| PATCH | /process-steps/{step_id}/standard-work/{work_id} | management | ✓ | Partial update of a standard work item. |
| DELETE | /process-steps/{step_id}/standard-work/{work_id} | management | ✓ | Delete a standard work item. |
| GET | /calibration/log | any_auth | ✓ | List calibration log entries with step and factory names. |
| GET | /calibration/status | management | ✓ | Current calibration status for all steps in a factory. |
| POST | /calibration/run | management | ✓ | Manually trigger calibration analysis for a factory. |
| POST | /calibration/apply | management | ✓ | Apply a calibration suggestion. |
| PATCH | /calibration/toggle/{step_id} | management | ✓ | Toggle auto_calibrate on/off for a ProcessStep. PM only. |
| PATCH | /calibration/typology-toggle/{speed_id} | management | ✓ | Toggle auto_calibrate on/off for a StageTypologySpeed. PM only. |
| POST | /calibration/apply/{step_id} | management | ✓ | Manually apply the current EMA-suggested rate for a specific step. PM only. |
| GET | /typologies | management | ✓ | List all active typologies. If factory_id omitted — returns cross-factory |
| POST | /typologies/calculate-all | management | ✓ | Recalculate capacities for ALL typologies in a factory. |
| POST | /typologies | management | ✓ | Create a new kiln loading typology. |
| GET | /typologies/match | management | ✓ | Find matching typology for given product parameters. |
| GET | /typologies/{typology_id} | management | ✓ | Get a single typology with capacities. |
| PATCH | /typologies/{typology_id} | management | ✓ | Partially update a typology. |
| DELETE | /typologies/{typology_id} | management | ✓ | Soft-delete a typology (set is_active=False). |
| POST | /typologies/{typology_id}/calculate | management | ✓ | Recalculate capacities for a single typology across all kilns. |
| GET | /typologies/{typology_id}/capacities | management | ✓ | Get per-kiln capacities for a typology. |
| GET | /stage-speeds | any_auth | ✓ | List stage typology speeds with optional filters. |
| POST | /stage-speeds | management | ✓ | Create a new stage typology speed entry. |
| PATCH | /stage-speeds/{speed_id} | management | ✓ | Partially update a stage typology speed. |
| DELETE | /stage-speeds/{speed_id} | management | ✓ | Delete a stage typology speed entry. |
| GET | /stage-speeds/matrix | any_auth | ✓ | Return all speeds grouped by typology then stage, for a frontend matrix view. |
| GET | /line-resources | any_auth | ✓ | List production line resources (work tables, drying racks, boards). |
| POST | /line-resources | management | ✓ | Create a production line resource. |
| PATCH | /line-resources/{resource_id} | management | ✓ | Update a production line resource. |
| DELETE | /line-resources/{resource_id} | management | ✓ | Soft-delete a production line resource. |
| GET | /kiln-shelves | any_auth | ✓ | List kiln shelves, optionally filtered by kiln. |
| POST | /kiln-shelves | management | ✓ | Create a kiln shelf linked to a specific kiln. |
| PATCH | /kiln-shelves/{shelf_id} | management | ✓ | Update a kiln shelf. |
| POST | /kiln-shelves/{shelf_id}/write-off | management | ✓ | Write off a kiln shelf with reason and optional photo. |
| POST | /kiln-shelves/{shelf_id}/increment-cycles | any_auth | ✓ | Increment firing cycles counter. Auto-warns when approaching max. |
| GET | /kiln-shelves/analytics | any_auth | ✓ | Lifecycle analytics for kiln shelves — OPEX impact, projected replacements. |

#### GET `/api/tps/kiln-shelves`

List kiln shelves for a factory/kiln.

**Query parameters:**

| Param | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| factory_id | UUID | yes | — | Filter by factory |
| resource_id | UUID | no | — | Filter by specific kiln resource |
| include_written_off | bool | no | false | Include written-off shelves |

**Response:** `{ items: KilnShelfItem[], total: number }`

#### POST `/api/tps/kiln-shelves`

Create a new kiln shelf. Name is auto-generated if omitted (e.g. `SiC-KilnName-001`).

**Body:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| resource_id | UUID | yes | — | Kiln resource to assign shelf to |
| factory_id | UUID | yes | — | Factory |
| name | string | no | auto-generated | Shelf display name |
| length_cm | number | yes | — | Shelf length in cm |
| width_cm | number | yes | — | Shelf width in cm |
| thickness_mm | number | no | — | Shelf thickness in mm |
| material | string | no | — | Material type (SiC, Cordierite, Mullite, Alumina) |
| purchase_date | date | no | — | Date of purchase |
| purchase_cost | number | no | — | Cost in IDR |
| max_firing_cycles | int | no | auto from material | Override max cycles |

**Material defaults for `max_firing_cycles`:** SiC = 200, Cordierite = 150, Mullite = 300, Alumina = 250.

**Response:** `{ id: UUID, name: string, max_firing_cycles: int, status: "created" }`

#### PATCH `/api/tps/kiln-shelves/{shelf_id}`

Update shelf properties. Supports moving shelf to a different kiln via `resource_id`.

**Body (all optional):**

| Field | Type | Description |
|-------|------|-------------|
| name | string | Display name |
| length_cm | number | Length in cm |
| width_cm | number | Width in cm |
| thickness_mm | number | Thickness in mm |
| material | string | Material type |
| condition_notes | string | Free-text condition notes |
| purchase_date | date | Date of purchase |
| purchase_cost | number | Cost in IDR |
| max_firing_cycles | int | Override max cycles |
| resource_id | UUID | Move to different kiln |

**Response:** `{ status: "updated", id: UUID }`

#### POST `/api/tps/kiln-shelves/{shelf_id}/write-off`

Write off a shelf (damaged, end-of-life, etc).

**Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| reason | string | yes | Write-off reason |
| photo_url | string | no | Photo evidence URL |

**Response:** `{ status: "written_off", id: UUID, remaining_shelves: int }`

**Side effects:**
- Creates `FinancialEntry` (OPEX / equipment) if `purchase_cost > 0`.
- Creates `SHELF_REPLACEMENT_NEEDED` task if remaining active shelves for kiln is critically low.

#### POST `/api/tps/kiln-shelves/{shelf_id}/increment-cycles`

Increment firing cycle counter (called after each firing).

**Query parameters:**

| Param | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| count | int | no | 1 | Number of cycles to add (1-10) |

**Response:** `{ status: "updated", firing_cycles_count: int, warning?: string }`

**Notes:** Warning string returned when shelf is at 90%+ of `max_firing_cycles`.

#### GET `/api/tps/kiln-shelves/analytics`

Shelf lifecycle analytics and OPEX projections. CEO-level widget.

**Query parameters:**

| Param | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| factory_id | UUID | no | all factories | Filter by factory |

**Response:**
```json
{
  "overview": { "total_active": 42, "total_written_off": 8, "avg_utilization_pct": 67.3 },
  "by_material": [
    { "material": "SiC", "count": 20, "avg_cycles_used": 120, "avg_max_cycles": 200 }
  ],
  "nearing_end_of_life": [
    { "id": "...", "name": "SiC-Kiln1-003", "cycles_used": 185, "max_cycles": 200, "pct": 92.5 }
  ],
  "projections": { "replacements_next_30d": 3, "estimated_cost_idr": 4500000 },
  "monthly_opex_trend": [
    { "month": "2026-03", "write_offs": 2, "total_cost_idr": 3000000 }
  ]
}
```

---

#### GET `/api/tps/line-resources`

List production line resources for a factory.

**Query parameters:**

| Param | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| factory_id | UUID | yes | — | Filter by factory |
| resource_type | string | no | — | Filter: `work_table`, `drying_rack`, `glazing_board` |

**Response:** `{ items: LineResourceItem[] }`

#### POST `/api/tps/line-resources`

Create a line resource. UPSERT on `(factory_id, resource_type, name)` conflict.

**Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| factory_id | UUID | yes | Factory |
| resource_type | string | yes | `work_table`, `drying_rack`, `glazing_board` |
| name | string | yes | Resource name |
| capacity_sqm | number | no | Capacity in square meters |
| capacity_boards | int | no | Capacity in boards |
| capacity_pcs | int | no | Capacity in pieces |
| num_units | int | no | Number of units |
| notes | string | no | Free-text notes |

**Response:** `{ id: UUID, status: "created" }`

#### PATCH `/api/tps/line-resources/{id}`

Update a line resource. Accepts partial body (same fields as POST, all optional).

**Response:** `{ status: "updated" }`

#### DELETE `/api/tps/line-resources/{id}`

Soft-delete a line resource (sets `is_active = false`).

**Response:** `{ status: "deleted" }`

---

## Notifications (`/api/notifications`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /unread-count | any_auth | ✓ | Return count of unread notifications for current user. |
| GET | / | any_auth | ✓ | List notifications for the current user, newest first. |
| PATCH | /{notification_id}/read | any_auth | ✓ | Mark a single notification as read. |
| POST | /read-all | any_auth | ✓ | Mark all notifications as read for the current user. |

---

## Analytics (`/api/analytics`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /dashboard-summary | management | ✓ | Summary metrics for Owner/CEO dashboard. |
| GET | /production-metrics | management | ✓ | Production metrics: daily output, pipeline funnel, critical positions. |
| GET | /material-metrics | management | ✓ | Material usage metrics: deficit items. |
| GET | /factory-comparison | owner | ✓ | Owner only: per-factory KPI comparison cards. |
| GET | /buffer-health | management | ✓ | CEO: per-kiln buffer health status. |
| GET | /trend-data | management | ✓ | Time series data for trend charts. |
| GET | /activity-feed | management | ✓ | CEO: recent activity events feed. |
| GET | /inventory-report | management | `[API-only]` | Monthly inventory adjustment report for CEO/Owner. |
| GET | /anomalies | management | ✓ | Get detected anomalies for a factory (or all factories). |
| GET | /factory-leaderboard | management | ✓ | Factory leaderboard: compare factories across key metrics. |
| GET | /lead-time/{factory_id} | management | ✓ | Factory lead time estimate: active positions, avg cycle, queue days. |
| GET | /streaks | management | ✓ | Streaks + daily challenge for the logged-in PM user. |

---

## AI Chat (`/api/ai-chat`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| POST | /chat | any_auth | ✓ | Send a message to the AI assistant. |
| GET | /sessions | any_auth | ✓ | List user's chat sessions, most recent first. |
| GET | /sessions/{session_id}/messages | any_auth | ✓ | Get all messages in a chat session. |

---

## Export (`/api/export`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /materials/excel | management | ✓ | Export materials data to Excel (XLSX). |
| GET | /quality/excel | management | ✓ | Export quality inspection data to Excel (XLSX). |
| GET | /orders/excel | management | ✓ | Export orders to Excel (XLSX). |
| GET | /orders/pdf | management | ✓ | Export orders to PDF. |
| GET | /positions/pdf | management | ✓ | Export positions to PDF. |
| POST | /owner-monthly | owner | ✓ | Owner monthly report with KPIs + financial summary. |
| POST | /ceo-daily | management | ✓ | CEO daily summary report. |
| GET | /ceo-daily/excel | management | ✓ | CEO daily report as a multi-sheet Excel workbook. |
| GET | /owner-monthly/excel | owner | ✓ | Owner monthly report as a multi-sheet Excel workbook. |

---

## Reports (`/api/reports`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | management | ✓ | Available report types. |
| GET | /orders-summary | management | ✓ | Orders summary report: totals, completion stats, on-time %. |
| GET | /kiln-load | management | ✓ | Per-kiln utilization report. |

---

## Stages (`/api/stages`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | ✓ | List stages |
| GET | /{item_id} | any_auth | ✓ | Get stages item |
| POST | / | any_auth | ✓ | Create stages item |
| PATCH | /{item_id} | any_auth | ✓ | Update stages item |
| DELETE | /{item_id} | any_auth | ✓ | Delete stages item |

---

## Transcription (`/api/transcription`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | management | `[API-only]` | List transcription logs with pagination and optional filters. |
| GET | /{log_id} | management | `[API-only]` | Get a single transcription log by ID. |

---

## Telegram (`/api/telegram`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /bot-status | admin | ✓ | Check Telegram bot connection status. |
| GET | /owner-chat | admin | ✓ | Get the current owner/admin Telegram chat ID. |
| PUT | /owner-chat | admin | ✓ | Set the owner/admin Telegram chat ID (stored in database). |
| POST | /test-chat | admin | ✓ | Send a test message to a Telegram chat to verify the chat ID is correct. |
| POST | /send-message | admin | `[API-only]` | Send a custom message via the Telegram bot. Admin only. |
| POST | /trigger-summary | admin | `[API-only]` | Manually trigger evening summary or morning briefing for a factory. |
| GET | /recent-chats | admin | ✓ | Return chats the bot has seen via webhook since last server restart. |
| POST | /webhook | public | `[Telegram-only]` | Telegram webhook endpoint. |
| POST | /subscribe | any_auth | ✓ | Link a Telegram user ID to the authenticated PMS user. |
| DELETE | /unsubscribe | any_auth | ✓ | Unlink Telegram from the authenticated PMS user. |
| GET | /invite-link/{user_id} | admin | `[API-only]` | Generate a Telegram deep link URL for a PMS user. |

---

## Health (`/api`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /health | public | ✓ | Health check |
| GET | /health/env-check | public | `[API-only]` | Public diagnostic: which integration keys are configured (values hidden). |
| GET | /health/seed-status | admin | `[API-only]` | Admin-only diagnostic: count rows in key reference tables. |
| GET | /health/backup | admin | `[API-only]` | Return backup monitoring data from the backup_logs table. |
| POST | /admin/backup | admin | `[API-only]` | Trigger a database backup immediately (runs in background). |
| GET | /internal/poll-pms-status | public | `[API-only]` | Cloud Scheduler keep-alive / status polling endpoint. |

---

## Purchaser (`/api/purchaser`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | ✓ | List purchaser |
| GET | /stats | any_auth | ✓ | Dashboard KPI stats with lead-time analytics. |
| GET | /deliveries | any_auth | ✓ | Completed or partially received deliveries. |
| GET | /deficits | any_auth | ✓ | Material deficits — materials where current balance < min_balance. |
| GET | /consolidation-suggestions | any_auth | `[API-only]` | Return suggestions for consolidating approved PRs by supplier. |
| POST | /consolidate | any_auth | ✓ | Execute consolidation of specified PR IDs into a single PR. |
| GET | /lead-times | any_auth | ✓ | Supplier lead times from supplier_lead_times table. |
| GET | /{item_id} | any_auth | ✓ | Get purchaser item |
| POST | / | any_auth | ✓ | Create purchaser item |
| PATCH | /{item_id} | any_auth | ✓ | Update purchaser item |
| PATCH | /{item_id}/status | any_auth | ✓ | Full status workflow: |
| DELETE | /{item_id} | any_auth | ✓ | Delete purchaser item |

---

## Kiln Loading Rules (`/api/kiln-loading-rules`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | ✓ | List kiln loading rules |
| GET | /{item_id} | any_auth | ✓ | Get kiln loading rules item |
| POST | / | management | ✓ | Create kiln loading rules item |
| PATCH | /{item_id} | management | ✓ | Update kiln loading rules item |
| DELETE | /{item_id} | management | ✓ | Delete kiln loading rules item |

---

## Kiln Firing Schedules (`/api/kiln-firing-schedules`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | ✓ | List kiln firing schedules |
| GET | /{item_id} | any_auth | ✓ | Get kiln firing schedules item |
| POST | / | any_auth | ✓ | Create kiln firing schedules item |
| PATCH | /{item_id} | any_auth | ✓ | Update kiln firing schedules item |
| DELETE | /{item_id} | any_auth | ✓ | Delete kiln firing schedules item |

---

## Dashboard Access (`/api/dashboard-access`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | admin | ✓ | List dashboard access |
| GET | /my | any_auth | `[API-only]` | Return current user's accessible dashboards. |
| GET | /{item_id} | admin | ✓ | Get dashboard access item |
| POST | / | admin | ✓ | Create dashboard access item |
| PATCH | /{item_id} | admin | ✓ | Update dashboard access item |
| DELETE | /{item_id} | admin | ✓ | Delete dashboard access item |

---

## Notification Preferences (`/api/notification-preferences`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | ✓ | List notification preferences |
| GET | /{item_id} | any_auth | ✓ | Get notification preferences item |
| POST | / | any_auth | ✓ | Create notification preferences item |
| PATCH | /{item_id} | any_auth | ✓ | Update notification preferences item |
| DELETE | /{item_id} | any_auth | ✓ | Delete notification preferences item |

---

## Financials (`/api/financials`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /summary | role(owner,ceo) | ✓ | Financial summary: OPEX/CAPEX totals, revenue, margin, cost per sqm. |
| GET | / | role(owner,ceo) | ✓ | List financials |
| GET | /{item_id} | role(owner,ceo) | ✓ | Get financials item |
| POST | / | role(owner) | ✓ | Create financials item |
| PATCH | /{item_id} | role(owner) | ✓ | Update financials item |
| DELETE | /{item_id} | role(owner) | ✓ | Delete financials item |

---

## Warehouse Sections (`/api/warehouse-sections`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | ✓ | List warehouse sections with optional filters. |
| GET | /all | admin_or_pm | ✓ | List ALL warehouse sections (admin view, including inactive). |
| GET | /{item_id} | any_auth | ✓ | Get warehouse section |
| POST | / | admin_or_pm | ✓ | Create a new warehouse section. Owner/Admin only. |
| PATCH | /{item_id} | admin_or_pm | ✓ | Update a warehouse section. Owner/Admin only. |
| DELETE | /{item_id} | admin_or_pm | ✓ | Delete a warehouse section. Owner/Admin only. |

---

## Reconciliations (`/api/reconciliations`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | ✓ | List reconciliations |
| GET | /{reconciliation_id}/items | any_auth | ✓ | Return all items for a reconciliation, with material name. |
| POST | /{reconciliation_id}/items | any_auth | ✓ | Add items to an in-progress reconciliation. |
| POST | /{reconciliation_id}/complete | management | ✓ | Finalize a reconciliation: mark as completed and create adjustment |
| GET | /{item_id} | any_auth | ✓ | Get reconciliations item |
| POST | / | any_auth | ✓ | Create reconciliations item |
| PATCH | /{item_id} | any_auth | ✓ | Update reconciliations item |
| DELETE | /{item_id} | any_auth | ✓ | Delete reconciliations item |

---

## QM Blocks (`/api/qm-blocks`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | ✓ | List qm blocks |
| GET | /{item_id} | any_auth | ✓ | Get qm blocks item |
| POST | / | any_auth | ✓ | Create qm blocks item |
| PATCH | /{item_id} | any_auth | ✓ | Update qm blocks item |
| DELETE | /{item_id} | any_auth | ✓ | Delete qm blocks item |

---

## Problem Cards (`/api/problem-cards`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | ✓ | List problem cards |
| GET | /{item_id} | any_auth | ✓ | Get problem cards item |
| POST | / | any_auth | ✓ | Create problem cards item |
| PATCH | /{item_id} | any_auth | ✓ | Update problem cards item |
| DELETE | /{item_id} | any_auth | ✓ | Delete problem cards item |

---

## Security (`/api/security`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /audit-log | admin | ✓ | Paginated, filterable audit log. |
| GET | /audit-log/summary | admin | ✓ | Audit log summary: failed logins, unique IPs, anomalies. |
| GET | /sessions | any_auth | ✓ | List active sessions. Admins see all, users see own. |
| DELETE | /sessions/{session_id} | any_auth | ✓ | Revoke a specific session. |
| DELETE | /sessions | any_auth | ✓ | Revoke all other sessions for the current user. |
| GET | /ip-allowlist | admin | `[API-only]` | List IP allowlist entries. |
| POST | /ip-allowlist | admin | `[API-only]` | Add IP to allowlist. |
| DELETE | /ip-allowlist/{entry_id} | admin | `[API-only]` | Remove IP from allowlist (soft delete). |
| POST | /totp/setup | any_auth | ✓ | Begin TOTP setup: generate secret, provisioning URI, and backup codes. |
| POST | /totp/verify | any_auth | ✓ | Verify a TOTP code to confirm setup and enable 2FA. |
| POST | /totp/disable | any_auth | ✓ | Disable TOTP 2FA. Requires a valid TOTP code or backup code. |
| GET | /totp/status | any_auth | ✓ | Check whether TOTP 2FA is enabled for the current user. |
| POST | /totp/backup-codes/regenerate | any_auth | `[API-only]` | Regenerate backup codes. Requires a valid TOTP code. Old codes are invalidated. |
| GET | /rate-limit-events | admin | `[API-only]` | List recent rate limit violation events (admin only). |
| DELETE | /rate-limit-events/clear | admin | ✓ | Clear rate limit events older than N days (default: 30). Admin only. |

---

## WebSocket (`/api/ws`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| WS | /notifications | public | ✓ | Websocket endpoint |

---

## Packing Photos (`/api/packing-photos`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | ✓ | List packing photos |
| POST | / | sorting+ | ✓ | Create packing photo |
| DELETE | /{photo_id} | sorting+ | ✓ | Delete packing photo |
| POST | /upload | sorting+ | ✓ | Upload a packing photo file directly (multipart form). |

---

## Finished Goods (`/api/finished-goods`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | ✓ | List finished goods |
| POST | / | management | ✓ | Create or update finished goods stock (upsert by unique constraint). |
| PATCH | /{stock_id} | management | ✓ | Update finished goods |
| DELETE | /{stock_id} | management | ✓ | Delete / write-off a finished goods stock record. Audit-logged. |
| GET | /availability | any_auth | ✓ | Check finished goods availability across all factories. |

---

## Firing Profiles (`/api/firing-profiles`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | ✓ | List firing profiles |
| GET | /{item_id} | any_auth | ✓ | Get firing profile |
| POST | / | any_auth | ✓ | Create firing profile |
| PATCH | /{item_id} | any_auth | ✓ | Update firing profile |
| DELETE | /{item_id} | any_auth | ✓ | Soft-delete: sets is_active=False. |
| POST | /match | any_auth | ✓ | Test endpoint: find best matching profile for given product_type + collection + thickness. |

---

## Batches (`/api/batches`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| POST | /auto-form | management | ✓ | Automatically form batches for a factory. |
| POST | /capacity-preview | any_auth | `[API-only]` | Preview how a position would load in a specific kiln. |
| GET | / | any_auth | ✓ | List batches with optional filters. |
| GET | /{batch_id} | any_auth | ✓ | Get batch detail with all assigned positions. |
| POST | /{batch_id}/start | management | ✓ | Mark batch as in_progress (kiln loaded, firing started). |
| POST | /{batch_id}/complete | management | ✓ | Mark batch as completed (firing done). |
| POST | /{batch_id}/confirm | management | ✓ | PM confirms a suggested batch (with optional adjustments). |
| POST | /{batch_id}/reject | management | ✓ | PM rejects a suggested batch. Positions are unassigned, batch deleted. |
| POST | / | management | ✓ | Manually create a batch. |
| PATCH | /{batch_id} | management | ✓ | Update batch fields. |
| POST | /{batch_id}/photos | any_auth | ✓ | Upload a firing photo for a batch (after kiln unloading). |
| GET | /{batch_id}/photos | any_auth | ✓ | Get all photos for a batch. |

---

### Firing Logs (`/api/batches`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| POST | /{batch_id}/firing-log | any_auth | ✓ | Create/start a firing log for a batch. |
| PATCH | /{batch_id}/firing-log/{log_id} | any_auth | ✓ | Update firing log — set end time, peak temp, result. |
| POST | /{batch_id}/firing-log/{log_id}/reading | any_auth | ✓ | Add a temperature reading to the firing log. |
| GET | /{batch_id}/firing-log | any_auth | ✓ | Get all firing logs for a batch. |

---

## Cleanup (`/api/cleanup`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /permissions | role(owner,administrator,ceo,production_manager) | ✓ | Get current PM cleanup toggles for a factory. |
| PATCH | /permissions | role(owner,administrator,ceo) | ✓ | Admin/CEO/Owner: toggle PM cleanup permissions for a factory. |
| DELETE | /tasks/{task_id} | role(owner,administrator,ceo,production_manager) | ✓ | Hard-delete a task. PM requires pm_can_delete_tasks toggle. |
| DELETE | /positions/{position_id} | role(owner,administrator,ceo,production_manager) | ✓ | Hard-delete a position, its split children and all linked tasks. |
| DELETE | /orders/{order_id} | role(owner,administrator,ceo,production_manager) | ✓ | Hard-delete an order + all positions, split children, tasks, and order items. |

---

## Material Groups (`/api/material-groups`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /hierarchy | any_auth | ✓ | Full nested hierarchy: groups → subgroups with material counts. |
| GET | /groups | any_auth | ✓ | List all material groups (flat, no subgroups). |
| POST | /groups | admin | ✓ | Create a new material group. Admin only. |
| PUT | /groups/{group_id} | admin | ✓ | Update a material group. Admin only. |
| DELETE | /groups/{group_id} | admin | ✓ | Delete a material group. Admin only. Fails if group has materials. |
| GET | /subgroups | any_auth | ✓ | List subgroups, optionally filtered by group. |
| POST | /subgroups | admin | ✓ | Create a new material subgroup. Admin only. |
| PUT | /subgroups/{subgroup_id} | admin | ✓ | Update a material subgroup. Admin only. |
| DELETE | /subgroups/{subgroup_id} | admin | ✓ | Delete a material subgroup. Admin only. Fails if subgroup has materials. |

---

## Packaging (`/api/packaging`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | admin_or_pm | ✓ | List all packaging box types with capacities and spacer rules. |
| GET | /sizes | admin_or_pm | ✓ | List all tile sizes for dropdown. |
| GET | /{box_type_id} | admin_or_pm | ✓ | Get box type |
| POST | / | admin_or_pm | ✓ | Create box type |
| PATCH | /{box_type_id} | admin_or_pm | ✓ | Update box type |
| DELETE | /{box_type_id} | admin_or_pm | ✓ | Delete box type |
| PUT | /{box_type_id}/capacities | admin_or_pm | ✓ | Bulk-replace all capacity entries for a box type. |
| PUT | /{box_type_id}/spacers | admin_or_pm | ✓ | Bulk-replace all spacer rules for a box type. |

---

## Sizes (`/api/sizes`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /search | any_auth | ✓ | Search sizes by dimensions, name, or shape. Used by size resolution UI. |
| GET | / | any_auth | ✓ | List all sizes ordered by name. |
| POST | /recalculate-all-boards | admin_or_pm | `[API-only]` | Recalculate glazing board specs for ALL sizes. Use after formula changes. |
| GET | /{size_id}/glazing-board | any_auth | ✓ | Get (or recalculate) glazing board spec for a size. |
| GET | /{size_id} | any_auth | ✓ | Get size |
| POST | / | admin_or_pm | ✓ | Create size |
| PATCH | /{size_id} | admin_or_pm | ✓ | Update size |
| DELETE | /{size_id} | admin_or_pm | ✓ | Delete size |

---

## Consumption Rules (`/api/consumption-rules`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | ✓ | List all consumption rules, ordered by rule_number. |
| GET | /{rule_id} | any_auth | ✓ | Get consumption rule |
| POST | / | admin_or_pm | ✓ | Create consumption rule |
| PATCH | /{rule_id} | admin_or_pm | ✓ | Update consumption rule |
| DELETE | /{rule_id} | admin_or_pm | ✓ | Delete consumption rule |

---

## Grinding Stock (`/api/grinding-stock`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | ✓ | List grinding stock items, optionally filtered by factory and status. |
| GET | /stats | any_auth | ✓ | Count grinding stock items by status per factory. |
| GET | /{item_id} | any_auth | ✓ | Get a single grinding stock item by ID. |
| POST | / | management | ✓ | Create a new grinding stock entry (PM/management only). |
| DELETE | /{item_id} | management | ✓ | Delete a grinding stock item (management only). |
| POST | /{item_id}/decide | management | ✓ | PM decision on a grinding stock item: grind, wait (pending), or send to Mana. |

---

## Factory Calendar (`/api/factory-calendar`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /working-days | any_auth | ✓ | Count working days between two dates for a factory. |
| GET | / | any_auth | ✓ | List calendar entries (non-working days / overrides) for a factory. |
| POST | / | management | ✓ | Add a non-working day (or working-day override) to factory calendar. |
| POST | /bulk | management | ✓ | Add multiple holidays / non-working days at once (e.g., Balinese holidays). |
| DELETE | /{entry_id} | management | ✓ | Remove a non-working day from factory calendar. |

---

## Stone Reservations (`/api/stone-reservations`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | management | ✓ | List stone reservations with optional filters. |
| GET | /{reservation_id} | management | ✓ | Get a single stone reservation with its adjustment log. |
| GET | /weekly-report | management | ✓ | Weekly stone waste report. |
| GET | /defect-rates | management | ✓ | Get stone defect rates configuration. |
| PUT | /defect-rates | management | ✓ | Upsert stone defect rate for a size_category × product_type combination. |
| POST | /{reservation_id}/adjustments | management | ✓ | Create a stone reservation adjustment (writeoff or return). |
| GET | /{reservation_id}/adjustments | management | ✓ | List all adjustments for a stone reservation. |

---

## Settings (`/api/settings`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /service-lead-times | management | ✓ | Returns configured lead times for all service types at the given factory. |
| PUT | /service-lead-times/{factory_id} | admin | ✓ | Upsert service lead times for the given factory. |
| POST | /service-lead-times/{factory_id}/reset-defaults | admin | ✓ | Delete all custom lead times for the factory, reverting to system defaults. |

---

## Admin Settings (`/api/admin-settings`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /escalation-rules | admin | ✓ | List escalation rules |
| POST | /escalation-rules | admin | ✓ | Create escalation rule |
| PATCH | /escalation-rules/{rule_id} | admin | ✓ | Update escalation rule |
| DELETE | /escalation-rules/{rule_id} | admin | ✓ | Delete escalation rule |
| GET | /receiving-settings | admin | ✓ | Get receiving settings |
| PUT | /receiving-settings/{factory_id} | admin | ✓ | Upsert receiving settings |
| GET | /defect-thresholds | admin | ✓ | List defect thresholds |
| PUT | /defect-thresholds/{material_id} | admin | ✓ | Upsert defect threshold |
| DELETE | /defect-thresholds/{material_id} | admin | ✓ | Delete defect threshold |
| GET | /consolidation-settings | admin | ✓ | Get consolidation settings |
| PUT | /consolidation-settings/{factory_id} | admin | ✓ | Upsert consolidation settings |

---

## Guides (`/api/guides`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /{role}/{language} | any_auth | ✓ | Get a user guide in markdown format for a specific role and language. |
| GET | / | any_auth | ✓ | List available guides and languages. |

---

## Delivery (`/api/delivery`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| POST | /process-photo | public | ✓ | Process a delivery note photo end-to-end: |

---

## Employees (`/api/employees`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | ✓ | List employees, optionally filtered by factory, active status, department, and category. |
| GET | /payroll-summary | management | ✓ | Calculate full payroll summary with Indonesian tax/BPJS for a given month. |
| GET | /hr-costs/yearly | finance | ✓ | Yearly HR costs breakdown by month — for owner/ceo visibility. |
| GET | /hr-costs/employee/{employee_id}/history | finance | ✓ | Per-employee monthly payroll history for a year — for owner/ceo drill-down. |
| GET | /payroll-pdf | management | ✓ | Generate and return payroll summary as PDF. |
| GET | /payroll-pdf-employee | management | ✓ | Generate and return individual employee payslip as PDF. |
| GET | /{employee_id} | any_auth | ✓ | Get a single employee by ID. |
| POST | / | management | ✓ | Create a new employee. |
| PATCH | /{employee_id} | management | ✓ | Update an employee. Partial update. |
| DELETE | /{employee_id} | management | ✓ | Soft-delete: set is_active=False. |
| GET | /{employee_id}/attendance | any_auth | ✓ | Get attendance records for an employee, filtered by date range or year/month. |
| POST | /{employee_id}/attendance | management | ✓ | Record attendance for an employee on a date. |
| PATCH | /attendance/{attendance_id} | management | ✓ | Update an attendance record. |
| DELETE | /attendance/{attendance_id} | management | ✓ | Delete (reset) an attendance record for a specific day. |

---

## Mana Shipments (`/api/mana-shipments`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | ✓ | List mana shipments |
| GET | /{item_id} | any_auth | ✓ | Get mana shipment |
| PATCH | /{item_id} | any_auth | ✓ | Update mana shipment |
| POST | /{item_id}/confirm | any_auth | ✓ | Confirm mana shipment |
| POST | /{item_id}/ship | any_auth | ✓ | Ship mana shipment |
| DELETE | /{item_id} | any_auth | ✓ | Delete mana shipment |

---

## Gamification (`/api/gamification`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /skills/badges | any_auth | ✓ | List all skill badges for a factory. |
| POST | /skills/badges/seed | management | ✓ | Seed default skill badges for a factory. |
| GET | /skills/user/{user_id} | any_auth | ✓ | Get all skills and progress for a user. |
| POST | /skills/start | any_auth | ✓ | Start learning a new skill. |
| POST | /skills/request-certification | any_auth | `[API-only]` | Worker requests certification after meeting all requirements. |
| POST | /skills/certify | management | ✓ | PM/CEO approves skill certification. |
| POST | /skills/revoke | management | ✓ | PM/CEO revokes a certification. |
| GET | /leaderboard | any_auth | ✓ | Top-20 workers by points for a given period (year/month/week). |
| GET | /points/my | any_auth | `[API-only]` | Current user's points summary and rank. |
| GET | /competitions | any_auth | ✓ | List competitions for a factory. |
| GET | /competitions/{competition_id}/standings | any_auth | ✓ | Get competition standings/leaderboard. |
| POST | /competitions | management | ✓ | PM/CEO creates a new individual competition. |
| POST | /competitions/team | management | ✓ | PM/CEO creates a team competition. |
| POST | /competitions/propose | any_auth | ✓ | Worker proposes a challenge (needs PM approval). |
| POST | /competitions/{competition_id}/approve | management | ✓ | PM/CEO approves a proposed challenge. |
| POST | /competitions/update-scores | management | ✓ | Manually trigger score update for active competitions. |
| GET | /prizes | management | ✓ | List prize recommendations. |
| POST | /prizes/generate-monthly | owner | ✓ | Generate monthly prize recommendations. |
| POST | /prizes/generate-quarterly | owner | `[API-only]` | Generate quarterly prize recommendations (budget = 2.5x monthly). |
| POST | /prizes/{prize_id}/approve | owner | ✓ | CEO/Owner approves a prize recommendation. |
| POST | /prizes/{prize_id}/reject | owner | ✓ | CEO/Owner rejects a prize recommendation. |
| POST | /prizes/{prize_id}/award | owner | ✓ | Mark a prize as awarded. |
| GET | /ceo-dashboard | owner | ✓ | Get CEO gamification dashboard data. |
| GET | /ceo-dashboard/impact | owner | ✓ | Get productivity impact analysis. |
| POST | /ceo-dashboard/send-report | owner | ✓ | Manually trigger CEO weekly gamification report. |
| GET | /seasons | any_auth | ✓ | List gamification seasons. |

---

## Workforce (`/api/workforce`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /skills | any_auth | ✓ | List all worker-stage skills for a factory. |
| GET | /skills/user/{user_id} | any_auth | ✓ | Get all stage skills for a specific user. |
| POST | /skills | management | ✓ | Assign a stage skill to a worker. |
| PUT | /skills/{skill_id} | management | ✓ | Update proficiency level for a worker-stage skill. |
| DELETE | /skills/{skill_id} | management | ✓ | Remove a skill assignment from a worker. |
| GET | /shifts | any_auth | ✓ | List shift definitions for a factory. |
| POST | /shifts | management | ✓ | Create a new shift definition. |
| PUT | /shifts/{shift_id} | management | ✓ | Update a shift definition. |
| DELETE | /shifts/{shift_id} | management | ✓ | Delete a shift definition (only if no assignments reference it). |
| GET | /assignments | any_auth | ✓ | Get shift assignments for a specific date. |
| POST | /assignments | management | ✓ | Assign a worker to a shift on a specific date. |
| DELETE | /assignments/{assignment_id} | management | ✓ | Remove a shift assignment. |
| GET | /daily-capacity | any_auth | ✓ | Get aggregated worker count per stage for a date (from shift assignments). |
| GET | /optimization/{factory_id} | management | `[API-only]` | AI-driven optimal worker distribution suggestions. |

---

## Onboarding (`/api/onboarding`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /progress | any_auth | ✓ | Get full onboarding progress for the current user and role. |
| POST | /complete-section | any_auth | ✓ | Mark a section as read (awards XP_SECTION_READ). |
| POST | /submit-quiz | any_auth | ✓ | Submit quiz answers, calculate score, award XP if passing. |
| GET | /content/{lang} | any_auth | ✓ | Get all onboarding content for a specific role. |
| GET | /roles | any_auth | ✓ | List all roles that have onboarding content. |

---

## Shipments (`/api/shipments`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | ✓ | List shipments, optionally filtered by order_id, factory_id, status. |
| GET | /{shipment_id} | any_auth | ✓ | Get a single shipment with all items. |
| POST | / | management | ✓ | Create a new shipment with selected positions (partial shipment support). |
| PATCH | /{shipment_id} | management | ✓ | Update shipment details (tracking, carrier, weight, etc.). |
| POST | /{shipment_id}/ship | management | ✓ | Mark shipment as shipped. Transitions positions to SHIPPED, notifies Sales webhook. |
| POST | /{shipment_id}/deliver | management | ✓ | Mark shipment as delivered. |
| DELETE | /{shipment_id} | management | ✓ | Cancel (delete) a shipment. Only allowed when status is 'prepared'. |

---

## PDF Templates (`/api/pdf/templates`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | `[API-only]` | List all registered PDF templates with metadata. |
| GET | /{template_id} | any_auth | `[API-only]` | Get a specific PDF template by ID. |

---

## Telegram Bot Commands

| Command | Description |
|---------|-------------|
| `/mystats` | Personal points breakdown and statistics |
| `/leaderboard` | Top performers ranking |
| `/stock` | Low stock materials summary |
| `/challenge` | Current daily challenge details |
| `/achievements` | Earned badges and milestones |
| `/points` | Current points balance |
| `/cancel_verify` | Cancel an in-progress recipe verification |

---

*Generated 2026-04-17 by `scripts/generate_api_contracts.py`. Total: ~67 routers, ~667 endpoints.*
