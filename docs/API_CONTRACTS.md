# Moonjar PMS — API Contracts

> Complete endpoint reference. Base path: `/api`
>
> **Auth levels:** `public` = no auth, `any_auth` = any JWT user, `management` = PM/Admin/Owner,
> `admin` = Admin/Owner, `owner` = Owner only, `owner/ceo` = Owner or CEO.
>
> **Frontend column:** checkmark = wired to frontend, `[API-only]` = backend only,
> `[Telegram-only]` = used by Telegram bot, `[Frontend planned]` = not yet wired,
> `[Admin-only]` = admin panel / CLI.

---

## Health (`/api`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /health | public | checkmark | Liveness check |
| GET | /health/seed-status | admin | checkmark | Row counts in reference tables |
| GET | /health/backup | admin | checkmark | Last backup status |
| POST | /admin/backup | admin | checkmark | Trigger manual backup |
| GET | /internal/poll-pms-status | any_auth | `[API-only]` | Polling endpoint for Sales app |

---

## Auth (`/api/auth`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| POST | /login | public | checkmark | Email/password login |
| POST | /google | public | checkmark | Google OAuth login |
| POST | /refresh | public | checkmark | Refresh JWT token pair |
| POST | /logout | any_auth | checkmark | Revoke current session |
| GET | /me | any_auth | checkmark | Get current user profile |
| POST | /logout-all | any_auth | checkmark | Revoke all sessions |
| POST | /verify-owner-key | any_auth | checkmark | Verify owner setup key |
| POST | /totp-verify | any_auth | checkmark | Verify TOTP code during login |
| POST | /change-password | any_auth | checkmark | Change user password |

---

## Orders (`/api/orders`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | management | checkmark | List orders with filters |
| GET | /cancellation-requests | management | checkmark | List pending cancellation requests |
| GET | /change-requests | management | checkmark | List pending change requests |
| POST | /upload-pdf | management | checkmark | Upload order PDF for AI parsing |
| POST | /confirm-pdf | management | checkmark | Confirm parsed PDF and create order |
| POST | /{order_id}/reprocess | management | checkmark | Reprocess order (re-parse items) |
| POST | /{order_id}/reschedule | management | checkmark | Reschedule order positions |
| GET | /{order_id} | management | checkmark | Get order detail |
| POST | / | management | checkmark | Create manual order |
| PATCH | /{order_id} | management | checkmark | Update order fields |
| DELETE | /{order_id} | management | checkmark | Delete order |
| PATCH | /{order_id}/ship | management | checkmark | Mark order as shipped |
| POST | /{order_id}/accept-cancellation | management | checkmark | Accept cancellation request |
| POST | /{order_id}/reject-cancellation | management | checkmark | Reject cancellation request |
| GET | /{order_id}/change-requests | management | checkmark | Get change requests for order |
| POST | /{order_id}/approve-change | management | checkmark | Approve change request |
| POST | /{order_id}/reject-change | management | checkmark | Reject change request |

---

## Positions (`/api/positions`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | checkmark | List positions with filters |
| GET | /blocking-summary | any_auth | checkmark | Summary of blocked positions |
| GET | /{position_id} | any_auth | checkmark | Get position detail |
| PATCH | /{position_id} | management | checkmark | Update position fields |
| GET | /{position_id}/allowed-transitions | any_auth | checkmark | Get allowed status transitions |
| POST | /{position_id}/status | any_auth | checkmark | Change position status |
| POST | /{position_id}/split | sorting+ | checkmark | Split position (QC split) |
| POST | /{position_id}/resolve-color-mismatch | management | checkmark | Resolve color mismatch |
| GET | /{position_id}/stock-availability | any_auth | checkmark | Check material stock for position |
| POST | /{position_id}/force-unblock | management | checkmark | Force unblock a position |
| GET | /{position_id}/material-reservations | any_auth | checkmark | Get material reservations |
| POST | /reorder | management | checkmark | Reorder positions within batch |
| POST | /{position_id}/reassign-batch | management | checkmark | Reassign position to another batch |
| POST | /{position_id}/split-production | management | checkmark | Split for production (pre-firing) |
| GET | /{position_id}/split-tree | management | checkmark | Get split hierarchy tree |
| GET | /{position_id}/mergeable-children | any_auth | checkmark | List children that can be merged |
| POST | /{position_id}/merge | management | checkmark | Merge child positions back |
| GET | /{position_id}/materials | any_auth | checkmark | Get materials needed for position |

---

## Schedule (`/api/schedule`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /resources | any_auth | checkmark | List schedule resources (kilns, lines) |
| GET | /batches | any_auth | checkmark | List scheduled batches |
| POST | /batches | management | checkmark | Create scheduled batch |
| GET | /glazing-schedule | any_auth | checkmark | Glazing stage schedule |
| GET | /firing-schedule | any_auth | checkmark | Firing stage schedule |
| GET | /sorting-schedule | any_auth | checkmark | Sorting stage schedule |
| GET | /qc-schedule | any_auth | checkmark | QC stage schedule |
| GET | /kiln-schedule | any_auth | checkmark | Kiln occupation schedule |
| PATCH | /positions/reorder | management | checkmark | Reorder positions in schedule |
| POST | /batches/{batch_id}/positions | management | checkmark | Add positions to batch |
| GET | /orders/{order_id}/schedule | any_auth | checkmark | Get schedule for an order |
| POST | /orders/{order_id}/reschedule | management | checkmark | Reschedule order |
| POST | /factory/{factory_id}/reschedule | management | checkmark | Reschedule entire factory |
| GET | /positions/{position_id}/schedule | any_auth | checkmark | Get schedule for a position |

---

## Materials (`/api/materials`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | checkmark | List materials with filters |
| GET | /low-stock | any_auth | checkmark | Materials below min balance |
| GET | /effective-balance | any_auth | checkmark | Effective balance (stock minus reserved) |
| GET | /consumption-adjustments | any_auth | checkmark | List pending consumption adjustments |
| POST | /consumption-adjustments/{adj_id}/approve | management | checkmark | Approve consumption adjustment |
| POST | /consumption-adjustments/{adj_id}/reject | management | checkmark | Reject consumption adjustment |
| GET | /duplicates | admin | checkmark | Find duplicate materials |
| POST | /merge | admin | checkmark | Merge duplicate materials |
| POST | /cleanup-duplicates | admin | checkmark | Auto-cleanup duplicate materials |
| POST | /ensure-all-stocks | admin | checkmark | Create missing MaterialStock rows |
| GET | /{material_id} | any_auth | checkmark | Get material detail |
| POST | / | any_auth | checkmark | Create material |
| PATCH | /{material_id} | any_auth | checkmark | Update material |
| PUT | /{material_id}/min-balance | management | `[Frontend planned]` | PM override min balance |
| DELETE | /{material_id} | admin | checkmark | Delete material |
| GET | /{material_id}/transactions | any_auth | checkmark | List material transactions |
| POST | /transactions | any_auth | checkmark | Create material transaction |
| POST | /transactions/{transaction_id}/approve | management | checkmark | Approve receiving transaction |
| DELETE | /transactions/{transaction_id} | any_auth | checkmark | Delete transaction |
| POST | /purchase-requests | any_auth | checkmark | Create purchase request |
| POST | /purchase-requests/{pr_id}/receive-partial | management | `[Frontend planned]` | Receive partial delivery |
| POST | /purchase-requests/{pr_id}/resolve-deficit | management | `[Frontend planned]` | Resolve delivery deficit |

---

## Recipes (`/api/recipes`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /engobe/shelf-coating | any_auth | checkmark | Get shelf coating recipes |
| GET | / | any_auth | checkmark | List recipes with filters |
| GET | /lookup | any_auth | checkmark | Lookup recipe by product/color/size |
| POST | /import-csv | admin | checkmark | Import recipes from CSV |
| GET | /temperature-groups | management | checkmark | List temperature groups |
| GET | /temperature-groups/{group_id}/recipes | management | checkmark | Recipes in temperature group |
| GET | /{item_id} | any_auth | checkmark | Get recipe detail |
| POST | / | any_auth | checkmark | Create recipe |
| PATCH | /{item_id} | any_auth | checkmark | Update recipe |
| DELETE | /{item_id} | any_auth | checkmark | Delete recipe |
| POST | /bulk-delete | any_auth | checkmark | Bulk delete recipes |
| GET | /{recipe_id}/materials | any_auth | checkmark | Get recipe materials |
| PUT | /{recipe_id}/materials | any_auth | checkmark | Set recipe materials |
| GET | /{recipe_id}/firing-stages | any_auth | checkmark | Get recipe firing stages |
| PUT | /{recipe_id}/firing-stages | any_auth | checkmark | Set recipe firing stages |

---

## Quality (`/api/quality`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /calendar-matrix | any_auth | checkmark | QC calendar matrix view |
| GET | /defect-causes | any_auth | checkmark | List defect causes |
| POST | /defect-causes | any_auth | checkmark | Create defect cause |
| GET | /inspections | any_auth | checkmark | List QC inspections |
| POST | /inspections | any_auth | checkmark | Create QC inspection |
| PATCH | /inspections/{inspection_id} | any_auth | checkmark | Update inspection |
| POST | /inspections/{inspection_id}/photo | any_auth | checkmark | Upload inspection photo |
| GET | /positions-for-qc | any_auth | checkmark | Positions awaiting QC |
| GET | /stats | any_auth | checkmark | Quality statistics |
| POST | /analyze-photo | any_auth | checkmark | AI-powered defect photo analysis |
| GET | /checklist-items | any_auth | checkmark | Get QC checklist items |
| POST | /pre-kiln-check | any_auth | checkmark | Create pre-kiln QC check |
| GET | /pre-kiln-checks | any_auth | checkmark | List pre-kiln checks |
| POST | /final-check | any_auth | checkmark | Create final QC check |
| GET | /final-checks | any_auth | checkmark | List final checks |

---

## Defects (`/api/defects`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | checkmark | List defect records |
| GET | /repair-queue | any_auth | checkmark | Repair queue |
| GET | /coefficients | management | checkmark | Get defect coefficients |
| POST | /positions/{position_id}/override | owner/ceo | checkmark | Override defect coefficient |
| POST | /record | management | checkmark | Record a defect |
| GET | /surplus-dispositions | any_auth | checkmark | List surplus dispositions |
| GET | /surplus-summary | any_auth | checkmark | Surplus summary |
| POST | /surplus-dispositions/auto-assign | management | checkmark | Auto-assign surplus |
| POST | /surplus-dispositions/batch | management | `[API-only]` | Batch process surplus dispositions |
| GET | /supplier-reports | management | `[Frontend planned]` | List supplier defect reports |
| POST | /supplier-reports/generate | management | `[Frontend planned]` | Generate supplier defect report |
| GET | /{item_id} | any_auth | checkmark | Get defect cause detail |
| POST | / | any_auth | checkmark | Create defect cause |
| PATCH | /{item_id} | any_auth | checkmark | Update defect cause |
| DELETE | /{item_id} | any_auth | checkmark | Delete defect cause |

---

## Tasks (`/api/tasks`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | checkmark | List tasks with filters |
| GET | /{task_id} | any_auth | checkmark | Get task detail |
| POST | / | management | checkmark | Create task |
| PATCH | /{task_id} | management | checkmark | Update task |
| POST | /{task_id}/complete | any_auth | checkmark | Complete task |
| POST | /{task_id}/resolve-shortage | management | checkmark | Resolve material shortage task |
| POST | /{task_id}/resolve-size | management | checkmark | Resolve size confirmation task |
| POST | /{task_id}/resolve-consumption | management | `[Frontend planned]` | Resolve consumption measurement task |

---

## Suppliers (`/api/suppliers`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | checkmark | List suppliers |
| GET | /{item_id}/lead-times | any_auth | checkmark | Get supplier lead times |
| GET | /{item_id} | any_auth | checkmark | Get supplier detail |
| POST | / | any_auth | checkmark | Create supplier |
| PATCH | /{item_id} | any_auth | checkmark | Update supplier |
| DELETE | /{item_id} | any_auth | checkmark | Delete supplier |

---

## Integration (`/api/integration`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /health | admin | checkmark | Integration diagnostics |
| GET | /db-check | admin | checkmark | Database state diagnostics |
| GET | /orders/{external_id}/production-status | webhook-auth | `[API-only]` | Production status for Sales app |
| GET | /orders/status-updates | webhook-auth | `[API-only]` | Batch status updates for Sales app |
| POST | /orders/{external_id}/request-cancellation | webhook-auth | `[API-only]` | Request order cancellation from Sales |
| POST | /webhook/sales-order | webhook-auth | `[API-only]` | Receive order from Sales webhook |
| GET | /webhooks | admin | checkmark | List webhook events |
| GET | /stubs | any_auth | checkmark | List integration stubs |
| POST | /stubs | any_auth | checkmark | Create integration stub |

---

## Users (`/api/users`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | admin | checkmark | List users |
| GET | /{user_id} | admin | checkmark | Get user detail |
| POST | / | admin | checkmark | Create user |
| PATCH | /{user_id} | admin | checkmark | Update user |
| POST | /{user_id}/toggle-active | admin | checkmark | Activate/deactivate user |

---

## Factories (`/api/factories`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | checkmark | List factories |
| PATCH | /{item_id}/kiln-mode | admin | checkmark | Set kiln constants mode (manual/auto) |
| GET | /{factory_id}/estimate | any_auth | checkmark | Get factory lead time estimate |
| GET | /{item_id} | any_auth | checkmark | Get factory detail |
| POST | / | admin | checkmark | Create factory |
| PATCH | /{item_id} | admin | checkmark | Update factory |
| DELETE | /{item_id} | admin | checkmark | Delete factory |
| GET | /{factory_id}/rotation-rules | any_auth | checkmark | Get kiln rotation rules |
| PUT | /{factory_id}/rotation-rules | admin | checkmark | Set kiln rotation rules |

---

## Kilns (`/api/kilns`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /collections | any_auth | checkmark | List kiln collections |
| GET | / | any_auth | checkmark | List kilns |
| GET | /maintenance/upcoming | management | checkmark | Upcoming maintenance |
| GET | /{kiln_id} | any_auth | checkmark | Get kiln detail |
| POST | / | management | checkmark | Create kiln |
| PATCH | /{kiln_id} | management | checkmark | Update kiln |
| PATCH | /{kiln_id}/status | management | checkmark | Change kiln status |
| DELETE | /{kiln_id} | management | checkmark | Delete kiln |
| GET | /{kiln_id}/maintenance | any_auth | checkmark | List kiln maintenance schedules |
| POST | /{kiln_id}/maintenance | management | checkmark | Create maintenance schedule |
| PUT | /{kiln_id}/maintenance/{schedule_id} | management | checkmark | Update maintenance schedule |
| POST | /{kiln_id}/maintenance/{schedule_id}/complete | management | checkmark | Complete maintenance |
| DELETE | /{kiln_id}/maintenance/{schedule_id} | management | checkmark | Delete maintenance schedule |
| POST | /{kiln_id}/breakdown | management | checkmark | Report kiln breakdown |
| POST | /{kiln_id}/restore | management | checkmark | Restore kiln from breakdown |
| GET | /{kiln_id}/rotation-rules | any_auth | checkmark | Get kiln rotation rules |
| PUT | /{kiln_id}/rotation-rules | management | checkmark | Set kiln rotation rules |
| GET | /{kiln_id}/rotation-check | any_auth | checkmark | Check kiln rotation status |

---

## Kiln Maintenance (`/api/kiln-maintenance`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /types | any_auth | checkmark | List maintenance types |
| POST | /types | management | checkmark | Create maintenance type |
| PUT | /types/{type_id} | management | checkmark | Update maintenance type |
| GET | /kilns/{kiln_id} | any_auth | checkmark | List maintenance for kiln |
| POST | /kilns/{kiln_id} | management | checkmark | Create maintenance entry |
| PUT | /kilns/{kiln_id}/{schedule_id} | management | checkmark | Update maintenance entry |
| POST | /kilns/{kiln_id}/{schedule_id}/complete | management | checkmark | Complete maintenance |
| DELETE | /kilns/{kiln_id}/{schedule_id} | management | checkmark | Delete maintenance entry |
| GET | /upcoming | management | checkmark | Upcoming maintenance across kilns |
| GET | / | any_auth | checkmark | List all maintenance records |
| GET | /{item_id} | any_auth | checkmark | Get maintenance detail |
| POST | / | management | checkmark | Create maintenance record |
| PATCH | /{item_id} | management | checkmark | Update maintenance record |
| DELETE | /{item_id} | management | checkmark | Delete maintenance record |

---

## Kiln Inspections (`/api/kiln-inspections`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /items | any_auth | checkmark | List checklist items by category |
| GET | / | any_auth | checkmark | List inspections (filterable) |
| GET | /{inspection_id} | any_auth | checkmark | Get single inspection |
| DELETE | /{inspection_id} | management | checkmark | Delete inspection |
| POST | / | management | checkmark | Create inspection with results |
| GET | /repairs | any_auth | checkmark | List repair logs |
| POST | /repairs | management | checkmark | Create repair log |
| PATCH | /repairs/{repair_id} | management | checkmark | Update repair log |
| DELETE | /repairs/{repair_id} | management | checkmark | Delete repair log |
| GET | /matrix | any_auth | checkmark | Matrix view (dates x kilns x items) |

---

## Kiln Constants (`/api/kiln-constants`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | checkmark | List kiln constants |
| GET | /{item_id} | any_auth | checkmark | Get kiln constant |
| POST | / | admin | checkmark | Create kiln constant |
| PATCH | /{item_id} | admin | checkmark | Update kiln constant |
| DELETE | /{item_id} | admin | checkmark | Delete kiln constant |

---

## Kiln Loading Rules (`/api/kiln-loading-rules`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | checkmark | List loading rules |
| GET | /{item_id} | any_auth | checkmark | Get loading rule |
| POST | / | management | checkmark | Create loading rule |
| PATCH | /{item_id} | management | checkmark | Update loading rule |
| DELETE | /{item_id} | management | checkmark | Delete loading rule |

---

## Kiln Firing Schedules (`/api/kiln-firing-schedules`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | checkmark | List firing schedules |
| GET | /{item_id} | any_auth | checkmark | Get firing schedule |
| POST | / | any_auth | checkmark | Create firing schedule |
| PATCH | /{item_id} | any_auth | checkmark | Update firing schedule |
| DELETE | /{item_id} | any_auth | checkmark | Delete firing schedule |

---

## Reference Data (`/api/reference`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /product-types | any_auth | checkmark | List product types |
| GET | /stone-types | any_auth | checkmark | List stone types |
| GET | /glaze-types | any_auth | checkmark | List glaze types |
| GET | /finish-types | any_auth | checkmark | List finish types |
| GET | /shape-types | any_auth | checkmark | List shape types |
| GET | /material-types | any_auth | checkmark | List material types |
| GET | /position-statuses | any_auth | checkmark | List position statuses |
| GET | /collections | any_auth | checkmark | List product collections |
| GET | /application-methods | any_auth | checkmark | List application methods |
| GET | /application-collections | any_auth | checkmark | List application collections |
| GET | /all | any_auth | checkmark | All reference data in one call |
| GET | /shape-coefficients | any_auth | checkmark | Get shape coefficients |
| PUT | /shape-coefficients/{shape}/{product_type} | management | checkmark | Update shape coefficient |
| GET | /bowl-shapes | any_auth | checkmark | List bowl shapes |
| GET | /temperature-groups | any_auth | checkmark | List temperature groups |
| POST | /temperature-groups | management | checkmark | Create temperature group |
| PUT | /temperature-groups/{group_id} | management | checkmark | Update temperature group |
| POST | /temperature-groups/{group_id}/recipes | management | checkmark | Add recipe to temp group |
| DELETE | /temperature-groups/{group_id}/recipes/{recipe_id} | management | checkmark | Remove recipe from temp group |
| POST | /collections | management | checkmark | Create collection |
| PUT | /collections/{item_id} | management | checkmark | Update collection |
| DELETE | /collections/{item_id} | management | checkmark | Delete collection |
| GET | /color-collections | any_auth | checkmark | List color collections |
| POST | /color-collections | management | checkmark | Create color collection |
| PUT | /color-collections/{item_id} | management | checkmark | Update color collection |
| DELETE | /color-collections/{item_id} | management | checkmark | Delete color collection |
| GET | /colors | any_auth | checkmark | List colors |
| POST | /colors | management | checkmark | Create color |
| PUT | /colors/{item_id} | management | checkmark | Update color |
| DELETE | /colors/{item_id} | management | checkmark | Delete color |
| GET | /application-types | any_auth | checkmark | List application types |
| POST | /application-types | management | checkmark | Create application type |
| PUT | /application-types/{item_id} | management | checkmark | Update application type |
| DELETE | /application-types/{item_id} | management | checkmark | Delete application type |
| GET | /places-of-application | any_auth | checkmark | List places of application |
| POST | /places-of-application | management | checkmark | Create place of application |
| PUT | /places-of-application/{item_id} | management | checkmark | Update place of application |
| DELETE | /places-of-application/{item_id} | management | checkmark | Delete place of application |
| GET | /finishing-types | any_auth | checkmark | List finishing types |
| POST | /finishing-types | management | checkmark | Create finishing type |
| PUT | /finishing-types/{item_id} | management | checkmark | Update finishing type |
| DELETE | /finishing-types/{item_id} | management | checkmark | Delete finishing type |
| POST | /bulk-import | management | checkmark | Bulk import reference data |

---

## TOC (Theory of Constraints) (`/api/toc`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /constraints | any_auth | checkmark | List constraints |
| PATCH | /constraints/{constraint_id} | management | checkmark | Update constraint |
| PATCH | /bottleneck/batch-mode | management | checkmark | Set bottleneck batch mode |
| PATCH | /bottleneck/buffer-target | management | checkmark | Set buffer target |
| GET | /buffer-health | any_auth | checkmark | Get buffer health status |
| GET | /buffer-zones | any_auth | checkmark | Get buffer zones |

---

## TPS (Toyota Production System) (`/api/tps`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /parameters | any_auth | checkmark | List TPS parameters |
| POST | /parameters | management | checkmark | Create TPS parameter |
| PATCH | /parameters/{param_id} | management | checkmark | Update TPS parameter |
| GET | / | any_auth | checkmark | List TPS records |
| POST | / | management | checkmark | Create TPS record |
| GET | /dashboard-summary | management | checkmark | TPS dashboard summary |
| GET | /shift-summary | any_auth | checkmark | Shift summary |
| GET | /signal | any_auth | `[API-only / TPS integration]` | TPS signal (andon) |
| GET | /deviations | any_auth | `[API-only / TPS integration]` | List deviations |
| POST | /deviations | management | checkmark | Create deviation |
| PATCH | /deviations/{deviation_id} | management | checkmark | Update deviation |
| POST | /record | any_auth | `[API-only / TPS integration]` | Record TPS measurement |
| GET | /position/{position_id}/timeline | any_auth | checkmark | Position production timeline |
| GET | /throughput | management | `[API-only / TPS integration]` | Throughput metrics |
| GET | /deviations/operations | management | checkmark | Deviations by operation |
| GET | /operations | management | checkmark | List operations |
| GET | /achievements/{user_id} | any_auth | checkmark | Get user achievements, points, badges |
| GET | /master-permissions/check/{user_id}/{operation_id} | any_auth | `[Frontend planned]` | Check user permission |
| GET | /master-permissions/{user_id} | management | `[Frontend planned]` | List user permissions |
| POST | /master-permissions | management | `[Frontend planned]` | Grant permission |
| DELETE | /master-permissions/{permission_id} | management | `[Frontend planned]` | Revoke permission |

---

## Notifications (`/api/notifications`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /unread-count | any_auth | checkmark | Unread notification count |
| GET | / | any_auth | checkmark | List notifications |
| PATCH | /{notification_id}/read | any_auth | checkmark | Mark notification as read |
| POST | /read-all | any_auth | checkmark | Mark all as read |

---

## Analytics (`/api/analytics`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /dashboard-summary | management | checkmark | Dashboard summary metrics |
| GET | /production-metrics | management | checkmark | Production metrics |
| GET | /material-metrics | management | checkmark | Material metrics |
| GET | /factory-comparison | owner | checkmark | Cross-factory comparison |
| GET | /buffer-health | management | checkmark | Buffer health analytics |
| GET | /trend-data | management | checkmark | Trend data over time |
| GET | /activity-feed | management | checkmark | Activity feed |
| GET | /inventory-report | management | `[Frontend planned]` | Inventory report |
| GET | /anomalies | management | checkmark | Anomaly detection |
| GET | /lead-time/{factory_id} | management | checkmark | Factory lead time analytics |

---

## AI Chat (`/api/ai-chat`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| POST | /chat | any_auth | checkmark | Send message to AI assistant |
| GET | /sessions | any_auth | checkmark | List chat sessions |
| GET | /sessions/{session_id}/messages | any_auth | checkmark | Get session messages |

---

## Export (`/api/export`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /materials/excel | management | checkmark | Export materials to Excel |
| GET | /quality/excel | management | checkmark | Export quality data to Excel |
| GET | /orders/excel | management | checkmark | Export orders to Excel |
| GET | /orders/pdf | management | checkmark | Export order to PDF |
| GET | /positions/pdf | management | checkmark | Export position label PDF |
| POST | /owner-monthly | owner | checkmark | Generate owner monthly report |
| POST | /ceo-daily | management | checkmark | Generate CEO daily report |

---

## Reports (`/api/reports`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | management | checkmark | List available reports |
| GET | /orders-summary | management | checkmark | Orders summary report |
| GET | /kiln-load | management | checkmark | Kiln load report |

---

## Stages (`/api/stages`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | checkmark | List production stages |
| GET | /{item_id} | any_auth | checkmark | Get stage detail |
| POST | / | any_auth | checkmark | Create stage |
| PATCH | /{item_id} | any_auth | checkmark | Update stage |
| DELETE | /{item_id} | any_auth | checkmark | Delete stage |

---

## Transcription (`/api/transcription`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | `[API-only]` | List transcriptions |

---

## Telegram (`/api/telegram`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /bot-status | admin | checkmark | Telegram bot status |
| GET | /owner-chat | admin | checkmark | Get owner chat ID |
| PUT | /owner-chat | admin | checkmark | Set owner chat ID |
| POST | /test-chat | admin | checkmark | Send test message |
| GET | /recent-chats | admin | checkmark | List recent chats |
| POST | /webhook | webhook-auth | `[Telegram-only]` | Telegram webhook receiver |
| POST | /subscribe | any_auth | `[Telegram-only]` | Subscribe to notifications |
| DELETE | /unsubscribe | any_auth | `[Telegram-only]` | Unsubscribe from notifications |

---

## Purchaser (`/api/purchaser`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | checkmark | List purchase orders |
| GET | /stats | any_auth | checkmark | Purchaser statistics |
| GET | /deliveries | any_auth | checkmark | List deliveries |
| GET | /deficits | any_auth | checkmark | List material deficits |
| GET | /consolidation-suggestions | any_auth | `[Frontend planned]` | Get consolidation suggestions |
| POST | /consolidate | any_auth | checkmark | Consolidate purchase orders |
| GET | /lead-times | any_auth | checkmark | Supplier lead times |
| GET | /{item_id} | any_auth | checkmark | Get purchase order detail |
| POST | / | any_auth | checkmark | Create purchase order |
| PATCH | /{item_id} | any_auth | checkmark | Update purchase order |
| PATCH | /{item_id}/status | any_auth | checkmark | Change PO status |
| DELETE | /{item_id} | any_auth | checkmark | Delete purchase order |

---

## Dashboard Access (`/api/dashboard-access`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | admin | checkmark | List all dashboard access rules |
| GET | /my | any_auth | checkmark | Get current user's dashboard access |
| GET | /{item_id} | admin | checkmark | Get access rule detail |
| POST | / | admin | checkmark | Create access rule |
| PATCH | /{item_id} | admin | checkmark | Update access rule |
| DELETE | /{item_id} | admin | checkmark | Delete access rule |

---

## Notification Preferences (`/api/notification-preferences`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | checkmark | List preferences |
| GET | /{item_id} | any_auth | checkmark | Get preference |
| POST | / | any_auth | checkmark | Create preference |
| PATCH | /{item_id} | any_auth | checkmark | Update preference |
| DELETE | /{item_id} | any_auth | checkmark | Delete preference |

---

## Financials (`/api/financials`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /summary | owner/ceo | checkmark | Financial summary (OPEX/CAPEX/margin) |
| GET | / | owner/ceo | checkmark | List financial entries |
| GET | /{item_id} | owner/ceo | checkmark | Get financial entry |
| POST | / | owner | checkmark | Create financial entry |
| PATCH | /{item_id} | owner | checkmark | Update financial entry |
| DELETE | /{item_id} | owner | checkmark | Delete financial entry |

---

## Warehouse Sections (`/api/warehouse-sections`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | checkmark | List sections for current factory |
| GET | /all | admin | checkmark | List all sections across factories |
| GET | /{item_id} | any_auth | checkmark | Get section detail |
| POST | / | admin | checkmark | Create section |
| PATCH | /{item_id} | admin | checkmark | Update section |
| DELETE | /{item_id} | admin | checkmark | Delete section |

---

## Reconciliations (`/api/reconciliations`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | checkmark | List reconciliations |
| GET | /{reconciliation_id}/items | any_auth | checkmark | Get reconciliation items |
| POST | /{reconciliation_id}/items | any_auth | checkmark | Add reconciliation item |
| POST | /{reconciliation_id}/complete | management | checkmark | Complete reconciliation |
| GET | /{item_id} | any_auth | checkmark | Get reconciliation detail |
| POST | / | any_auth | checkmark | Create reconciliation |
| PATCH | /{item_id} | any_auth | checkmark | Update reconciliation |
| DELETE | /{item_id} | any_auth | checkmark | Delete reconciliation |

---

## QM Blocks (`/api/qm-blocks`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | checkmark | List QM blocks |
| GET | /{item_id} | any_auth | checkmark | Get QM block |
| POST | / | any_auth | checkmark | Create QM block |
| PATCH | /{item_id} | any_auth | checkmark | Update QM block |
| DELETE | /{item_id} | any_auth | checkmark | Delete QM block |

---

## Problem Cards (`/api/problem-cards`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | checkmark | List problem cards |
| GET | /{item_id} | any_auth | checkmark | Get problem card |
| POST | / | any_auth | checkmark | Create problem card |
| PATCH | /{item_id} | any_auth | checkmark | Update problem card |
| DELETE | /{item_id} | any_auth | checkmark | Delete problem card |

---

## Security (`/api/security`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /audit-log | admin | checkmark | View audit log |
| GET | /audit-log/summary | admin | checkmark | Audit log summary |
| GET | /sessions | any_auth | checkmark | List active sessions |
| DELETE | /sessions/{session_id} | any_auth | checkmark | Revoke specific session |
| DELETE | /sessions | any_auth | checkmark | Revoke all sessions |
| GET | /ip-allowlist | admin | `[Admin-only]` | List IP allowlist |
| POST | /ip-allowlist | admin | `[Admin-only]` | Add IP to allowlist |
| DELETE | /ip-allowlist/{entry_id} | admin | `[Admin-only]` | Remove IP from allowlist |
| POST | /totp/setup | any_auth | checkmark | Setup TOTP 2FA |
| POST | /totp/verify | any_auth | checkmark | Verify TOTP token |
| POST | /totp/disable | any_auth | checkmark | Disable TOTP |
| GET | /totp/status | any_auth | checkmark | Get TOTP status |
| POST | /totp/backup-codes/regenerate | any_auth | checkmark | Regenerate backup codes |
| GET | /rate-limit-events | admin | checkmark | View rate limit events |
| DELETE | /rate-limit-events/clear | admin | checkmark | Clear rate limit events |

---

## Packing Photos (`/api/packing-photos`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | checkmark | List packing photos |
| POST | / | sorting+ | checkmark | Create packing photo record |
| DELETE | /{photo_id} | sorting+ | checkmark | Delete packing photo |
| POST | /upload | sorting+ | checkmark | Upload packing photo file |

---

## Finished Goods (`/api/finished-goods`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | checkmark | List finished goods stock |
| POST | / | management | checkmark | Add finished goods entry |
| PATCH | /{stock_id} | management | checkmark | Update finished goods entry |
| DELETE | /{stock_id} | management | checkmark | Delete finished goods entry |
| GET | /availability | any_auth | checkmark | Check finished goods availability |

---

## Firing Profiles (`/api/firing-profiles`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | checkmark | List firing profiles |
| GET | /{item_id} | any_auth | checkmark | Get firing profile |
| POST | / | any_auth | checkmark | Create firing profile |
| PATCH | /{item_id} | any_auth | checkmark | Update firing profile |
| DELETE | /{item_id} | any_auth | checkmark | Delete firing profile |
| POST | /match | any_auth | checkmark | Match best firing profile for position |

---

## Batches (`/api/batches`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| POST | /auto-form | management | checkmark | Auto-form batch (optimization) |
| POST | /capacity-preview | any_auth | checkmark | Preview batch capacity |
| GET | / | any_auth | checkmark | List batches |
| GET | /{batch_id} | any_auth | checkmark | Get batch detail |
| POST | /{batch_id}/start | management | checkmark | Start firing batch |
| POST | /{batch_id}/complete | management | checkmark | Complete firing batch |
| POST | /{batch_id}/confirm | management | checkmark | Confirm batch results |
| POST | /{batch_id}/reject | management | checkmark | Reject batch results |
| POST | / | management | checkmark | Create batch manually |
| PATCH | /{batch_id} | management | checkmark | Update batch |
| POST | /{batch_id}/photos | any_auth | checkmark | Upload batch photo |
| GET | /{batch_id}/photos | any_auth | checkmark | List batch photos |

---

## Firing Logs (`/api/batches` — firing-logs tag)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| POST | /{batch_id}/firing-log | any_auth | checkmark | Create firing log entry |
| PATCH | /{batch_id}/firing-log/{log_id} | any_auth | checkmark | Update firing log entry |
| POST | /{batch_id}/firing-log/{log_id}/reading | any_auth | checkmark | Add temperature reading |
| GET | /{batch_id}/firing-log | any_auth | checkmark | List firing logs for batch |

---

## Cleanup (`/api/cleanup`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /permissions | management | checkmark | Get cleanup permissions |
| PATCH | /permissions | admin | checkmark | Update cleanup permissions |
| DELETE | /tasks/{task_id} | management | checkmark | Delete task |
| DELETE | /positions/{position_id} | management | checkmark | Delete position |
| DELETE | /orders/{order_id} | management | checkmark | Delete order with cascade |

---

## Material Groups (`/api/material-groups`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /hierarchy | any_auth | checkmark | Get full material group hierarchy |
| GET | /groups | any_auth | checkmark | List material groups |
| POST | /groups | admin | checkmark | Create material group |
| PUT | /groups/{group_id} | admin | checkmark | Update material group |
| DELETE | /groups/{group_id} | admin | checkmark | Delete material group |
| GET | /subgroups | any_auth | checkmark | List subgroups |
| POST | /subgroups | admin | checkmark | Create subgroup |
| PUT | /subgroups/{subgroup_id} | admin | checkmark | Update subgroup |
| DELETE | /subgroups/{subgroup_id} | admin | checkmark | Delete subgroup |

---

## Packaging (`/api/packaging`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | admin/pm | checkmark | List box types |
| GET | /sizes | admin/pm | checkmark | List packaging sizes |
| GET | /{box_type_id} | admin/pm | checkmark | Get box type detail |
| POST | / | admin/pm | checkmark | Create box type |
| PATCH | /{box_type_id} | admin/pm | checkmark | Update box type |
| DELETE | /{box_type_id} | admin/pm | checkmark | Delete box type |
| PUT | /{box_type_id}/capacities | admin/pm | checkmark | Set box capacities |
| PUT | /{box_type_id}/spacers | admin/pm | checkmark | Set box spacer settings |

---

## Sizes (`/api/sizes`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /search | any_auth | checkmark | Search sizes |
| GET | / | any_auth | checkmark | List sizes |
| POST | /recalculate-all-boards | admin | checkmark | Recalculate all glazing boards |
| GET | /{size_id}/glazing-board | any_auth | checkmark | Get glazing board spec |
| GET | /{size_id} | any_auth | checkmark | Get size detail |
| POST | / | admin | checkmark | Create size |
| PATCH | /{size_id} | admin | checkmark | Update size |
| DELETE | /{size_id} | admin | checkmark | Delete size |

---

## Consumption Rules (`/api/consumption-rules`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | checkmark | List consumption rules |
| GET | /{rule_id} | any_auth | checkmark | Get consumption rule |
| POST | / | admin | checkmark | Create consumption rule |
| PATCH | /{rule_id} | admin | checkmark | Update consumption rule |
| DELETE | /{rule_id} | admin | checkmark | Delete consumption rule |

---

## Grinding Stock (`/api/grinding-stock`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | checkmark | List grinding stock |
| GET | /stats | any_auth | checkmark | Grinding stock statistics |
| GET | /{item_id} | any_auth | checkmark | Get grinding stock item |
| POST | / | management | checkmark | Create grinding stock entry |
| POST | /{item_id}/decide | management | checkmark | Decide on grinding stock item |

---

## Stone Reservations (`/api/stone-reservations`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | management | checkmark | List stone reservations |
| GET | /{reservation_id} | management | checkmark | Get reservation detail |
| GET | /weekly-report | management | checkmark | Weekly reservation report |
| GET | /defect-rates | management | checkmark | Get defect rates |
| PUT | /defect-rates | management | checkmark | Update defect rates |
| POST | /{reservation_id}/adjustments | management | checkmark | Create adjustment |
| GET | /{reservation_id}/adjustments | management | checkmark | List adjustments |

---

## Factory Calendar (`/api/factory-calendar`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /working-days | any_auth | checkmark | Get working days count |
| GET | / | any_auth | checkmark | List calendar entries |
| POST | / | management | checkmark | Create calendar entry |
| POST | /bulk | management | checkmark | Bulk create calendar entries |
| DELETE | /{entry_id} | management | checkmark | Delete calendar entry |

---

## Settings (`/api/settings`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /service-lead-times | management | checkmark | Get service lead times |
| PUT | /service-lead-times/{factory_id} | admin | checkmark | Set service lead times |
| POST | /service-lead-times/{factory_id}/reset-defaults | admin | checkmark | Reset lead times to defaults |

---

## Admin Settings (`/api/admin-settings`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /escalation-rules | admin | checkmark | List escalation rules |
| POST | /escalation-rules | admin | checkmark | Create escalation rule |
| PATCH | /escalation-rules/{rule_id} | admin | checkmark | Update escalation rule |
| DELETE | /escalation-rules/{rule_id} | admin | checkmark | Delete escalation rule |
| GET | /receiving-settings | admin | checkmark | Get receiving settings |
| PUT | /receiving-settings/{factory_id} | admin | checkmark | Set receiving settings |
| GET | /defect-thresholds | admin | checkmark | List defect thresholds |
| PUT | /defect-thresholds/{material_id} | admin | checkmark | Set defect threshold |
| DELETE | /defect-thresholds/{material_id} | admin | checkmark | Delete defect threshold |
| GET | /consolidation-settings | admin | checkmark | Get consolidation settings |
| PUT | /consolidation-settings/{factory_id} | admin | checkmark | Set consolidation settings |

---

## Guides (`/api/guides`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | /{role}/{language} | any_auth | checkmark | Get guide content |
| GET | / | any_auth | checkmark | List available guides |

---

## Delivery (`/api/delivery`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| POST | /process-photo | any_auth | `[Telegram-only]` | Process delivery photo via AI OCR |

---

## Employees (`/api/employees`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | checkmark | List employees (salary hidden for non-management) |
| GET | /payroll-summary | management | checkmark | Payroll summary |
| GET | /{employee_id} | any_auth | checkmark | Get employee detail |
| POST | / | management | checkmark | Create employee |
| PATCH | /{employee_id} | management | checkmark | Update employee |
| DELETE | /{employee_id} | management | checkmark | Delete employee |
| GET | /{employee_id}/attendance | any_auth | checkmark | List attendance records |
| POST | /{employee_id}/attendance | management | checkmark | Create attendance record |
| PATCH | /attendance/{attendance_id} | management | checkmark | Update attendance record |

---

## Mana Shipments (`/api/mana-shipments`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | checkmark | List mana shipments |
| GET | /{item_id} | any_auth | checkmark | Get shipment detail |
| PATCH | /{item_id} | any_auth | checkmark | Update shipment |
| POST | /{item_id}/confirm | any_auth | checkmark | Confirm shipment |
| POST | /{item_id}/ship | any_auth | checkmark | Mark as shipped |
| DELETE | /{item_id} | any_auth | checkmark | Delete shipment |

---

## Shipments (`/api/shipments`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | checkmark | List shipments |
| GET | /{shipment_id} | any_auth | checkmark | Get shipment detail |
| POST | / | management | checkmark | Create shipment |
| PATCH | /{shipment_id} | management | checkmark | Update shipment |
| POST | /{shipment_id}/ship | management | checkmark | Mark shipment as shipped |
| POST | /{shipment_id}/deliver | management | checkmark | Mark shipment as delivered |
| DELETE | /{shipment_id} | management | checkmark | Delete shipment |

---

## PDF Templates (`/api/pdf/templates`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| GET | / | any_auth | checkmark | List PDF templates |
| GET | /{template_id} | any_auth | checkmark | Get PDF template |

---

## WebSocket (`/api/ws`)

| Method | Path | Auth | Frontend | Description |
|--------|------|------|----------|-------------|
| WS | /notifications | any_auth | checkmark | Real-time notification stream |

---

## Telegram Bot Commands (NEW — April 1-2, 2026)

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

*Generated 2026-04-02. Total: ~55 routers, ~360+ endpoints.*
