# Moonjar PMS — Comprehensive QA Test Plan

## How to use
Copy this prompt and run it as a Claude Code session against the codebase.
It will systematically verify every feature, API endpoint, and UI page.

Base URL: `https://moonjar-pms-production.up.railway.app/api`

For each test: verify the endpoint returns the expected HTTP status code,
response shape, and correct business logic. Use `curl` or the test framework.

---

## 1. Health & Infrastructure

### 1.1 Health Check
- [ ] `GET /api/health` returns `{"status":"ok"}` (200)
- [ ] `GET /api/health/seed-status` returns seed data summary (200)
- [ ] `GET /api/health/backup` returns backup info (200)

### 1.2 Integration Health
- [ ] `GET /api/integration/health` returns integration status (200)
- [ ] `GET /api/integration/db-check` returns database connectivity info (200)

---

## 2. Authentication & Authorization

### 2.1 Login Flow
- [ ] `POST /api/auth/login` with valid email/password returns access_token + refresh_token (200)
- [ ] `POST /api/auth/login` with wrong password returns 401
- [ ] `POST /api/auth/login` with non-existent email returns 401
- [ ] After 5 failed login attempts within 1 minute, returns 429 (rate limited)
- [ ] `POST /api/auth/google` with valid Google OAuth token returns tokens (200)
- [ ] `POST /api/auth/google` with invalid token returns 401

### 2.2 Token Management
- [ ] `POST /api/auth/refresh` with valid refresh_token returns new access_token (200)
- [ ] `POST /api/auth/refresh` with expired refresh_token returns 401
- [ ] `GET /api/auth/me` with valid token returns user profile (200)
- [ ] `GET /api/auth/me` without token returns 401
- [ ] `POST /api/auth/logout` invalidates current session (200)
- [ ] `POST /api/auth/logout-all` invalidates all sessions (200)

### 2.3 Password & TOTP
- [ ] `POST /api/auth/change-password` with correct old password works (200)
- [ ] `POST /api/auth/change-password` with wrong old password returns 400
- [ ] `POST /api/auth/verify-owner-key` verifies owner secret key (200)
- [ ] `POST /api/auth/totp-verify` validates TOTP code (200)

### 2.4 Role-Based Access Control (8 Roles)
Test each role can ONLY access its allowed routes:

| Role | Home Route | Allowed Routes |
|------|-----------|----------------|
| owner | /owner | /owner, /ceo, /ceo/employees, /admin/*, /manager/*, /reports, /warehouse/*, /quality, /packing, /purchaser, /users |
| administrator | /admin | /admin/*, /ceo, /ceo/employees, /manager/*, /reports, /warehouse/*, /quality, /packing, /purchaser, /users |
| ceo | /ceo | /ceo, /ceo/employees, /reports, /users |
| production_manager | /manager | /manager/*, /admin/recipes, /admin/temperature-groups, /admin/warehouses, /admin/packaging, /admin/sizes, /admin/consumption-rules, /admin/firing-profiles, /admin/stages, /admin/firing-schedules, /admin/factory-calendar, /reports, /warehouse/*, /packing, /purchaser |
| quality_manager | /quality | /quality |
| warehouse | /warehouse | /warehouse, /warehouse/finished-goods, /warehouse/reconciliations, /warehouse/mana-shipments |
| sorter_packer | /packing | /packing |
| purchaser | /purchaser | /purchaser |

- [ ] PM cannot access /ceo — returns redirect to /
- [ ] Warehouse cannot access /admin/employees — returns redirect
- [ ] Sorter/Packer cannot access /manager — returns redirect
- [ ] CEO cannot access /admin — returns redirect
- [ ] Unauthenticated user redirected to /login on any protected route

### 2.5 Security Endpoints
- [ ] `GET /api/security/audit-log` returns paginated audit entries (200)
- [ ] `GET /api/security/audit-log/summary` returns summary stats (200)
- [ ] `GET /api/security/sessions` lists active sessions (200)
- [ ] `DELETE /api/security/sessions/{id}` revokes specific session (200)
- [ ] `DELETE /api/security/sessions` revokes all other sessions (200)
- [ ] `GET /api/security/ip-allowlist` lists IP allowlist (200)
- [ ] `POST /api/security/ip-allowlist` adds IP to allowlist (201)
- [ ] `DELETE /api/security/ip-allowlist/{id}` removes IP entry (200)
- [ ] TOTP setup: `POST /api/security/totp/setup` returns QR code (200)
- [ ] TOTP verify: `POST /api/security/totp/verify` validates code (200)
- [ ] TOTP disable: `POST /api/security/totp/disable` removes TOTP (200)
- [ ] TOTP status: `GET /api/security/totp/status` returns enabled/disabled (200)
- [ ] Backup codes: `POST /api/security/totp/backup-codes/regenerate` (200)
- [ ] Rate limit events: `GET /api/security/rate-limit-events` (200)
- [ ] Clear rate limit events: `DELETE /api/security/rate-limit-events/clear` (200)

---

## 3. Factories

### 3.1 Factory CRUD
- [ ] `GET /api/factories` lists all factories with pagination (200)
- [ ] `GET /api/factories/{id}` returns single factory (200)
- [ ] `POST /api/factories` creates new factory (201) — admin only
- [ ] `PATCH /api/factories/{id}` updates factory (200) — admin only
- [ ] `DELETE /api/factories/{id}` deletes factory (204) — admin only
- [ ] PM sees only their assigned factories, not all

### 3.2 Factory Settings
- [ ] `PATCH /api/factories/{id}/kiln-mode` toggles kiln mode (200)
- [ ] `GET /api/factories/{id}/estimate` returns production estimate (200)
- [ ] `GET /api/factories/{id}/rotation-rules` returns rotation config (200)
- [ ] `PUT /api/factories/{id}/rotation-rules` updates rotation rules (200)

---

## 4. Factory Calendar

### 4.1 Calendar CRUD
- [ ] `GET /api/factory-calendar?factory_id=X&year=Y&month=Z` returns entries (200)
- [ ] Response includes: id, date, is_working_day, num_shifts, holiday_name, holiday_source
- [ ] `GET /api/factory-calendar/working-days?factory_id=X&start_date=Y&end_date=Z` returns working day counts (200)
- [ ] Response includes: total_days, working_days, holidays, sundays
- [ ] `POST /api/factory-calendar` creates single entry (201)
- [ ] `POST /api/factory-calendar/bulk` creates multiple entries (200)
- [ ] `DELETE /api/factory-calendar/{id}` removes entry (204)

### 4.2 UI: Factory Calendar Page (/admin/factory-calendar)
- [ ] Page loads with calendar grid for current month
- [ ] Factory selector shows user's factories
- [ ] Month navigation (prev/next) works
- [ ] Holidays shown in red, Sundays in gray, working days in green
- [ ] Click on date opens holiday creation dialog
- [ ] Bulk import: Indonesian holidays preset loads correctly
- [ ] Bulk import: Balinese holidays preset loads correctly
- [ ] Working days counter at bottom matches API response
- [ ] Toggle holiday->working day works
- [ ] Toggle Sunday->overtime working day works

---

## 5. Orders

### 5.1 Order CRUD
- [ ] `GET /api/orders` returns paginated orders list (200)
- [ ] Response includes: items array with order headers, total, page, per_page
- [ ] `GET /api/orders/{id}` returns single order with positions (200)
- [ ] `POST /api/orders` creates order manually (201)
- [ ] `PATCH /api/orders/{id}` updates order header (client, deadline, factory, notes) (200)

### 5.2 Sales Integration Webhook
- [ ] `POST /api/integration/webhook/sales-order` creates order from external system (201)
- [ ] Webhook validates required fields (external_id, client, items)
- [ ] Duplicate external_id returns 409 or updates existing
- [ ] `GET /api/integration/orders/{external_id}/production-status` returns status (200)
- [ ] `GET /api/integration/orders/status-updates` returns recent changes (200)
- [ ] `POST /api/integration/orders/{external_id}/request-cancellation` initiates cancel (200)

### 5.3 UI: Manager Dashboard (/manager)
- [ ] Dashboard loads with orders table
- [ ] Order list shows: order number, client, status, factory, deadline, position count
- [ ] Click on order navigates to /manager/orders/{id}
- [ ] Order detail page shows header + positions table
- [ ] Position status badges display correctly
- [ ] Material status badge shows reserved/not reserved/insufficient

---

## 6. Positions

### 6.1 Position Operations
- [ ] `GET /api/positions` returns paginated positions (200)
- [ ] `GET /api/positions/{id}` returns single position (200)
- [ ] `PATCH /api/positions/{id}` updates position fields (color, size, shape, etc.) (200)
- [ ] `GET /api/positions/{id}/allowed-transitions` returns valid next statuses (200)
- [ ] `POST /api/positions/{id}/status` changes position status (200)
- [ ] Status change is recorded in audit log
- [ ] `GET /api/positions/blocking-summary` returns blocking issues summary (200)

---

## 7. Materials & Inventory

### 7.1 Materials CRUD
- [ ] `GET /api/materials` returns materials list with names (not just codes) (200)
- [ ] `GET /api/materials/{id}` returns material detail (200)
- [ ] `POST /api/materials` creates material (201) — admin only
- [ ] `PATCH /api/materials/{id}` updates material (200) — admin only
- [ ] `DELETE /api/materials/{id}` deletes material (204) — admin only

### 7.2 Material Transactions
- [ ] `GET /api/materials/{id}/transactions` returns transaction history (200)
- [ ] `POST /api/materials/transactions` records receive/write-off/adjustment (201)
- [ ] Transaction types: receive, write_off, adjustment, reserve, release
- [ ] `POST /api/materials/transactions/{id}/approve` approves pending transaction (200)
- [ ] `DELETE /api/materials/transactions/{id}` cancels transaction (204)

### 7.3 Purchase Requests
- [ ] `POST /api/materials/purchase-requests` creates PR (201)
- [ ] `POST /api/materials/purchase-requests/{id}/receive-partial` records partial receipt (200)
- [ ] `POST /api/materials/purchase-requests/{id}/resolve-deficit` resolves deficit (200)

### 7.4 Material Groups
- [ ] `GET /api/material-groups/hierarchy` returns full group tree (200)
- [ ] `GET /api/material-groups/groups` lists groups (200)
- [ ] `POST /api/material-groups/groups` creates group (201)
- [ ] `PUT /api/material-groups/groups/{id}` updates group (200)
- [ ] `DELETE /api/material-groups/groups/{id}` deletes group (204)
- [ ] `GET /api/material-groups/subgroups` lists subgroups (200)
- [ ] `POST /api/material-groups/subgroups` creates subgroup (201)
- [ ] `PUT /api/material-groups/subgroups/{id}` updates subgroup (200)
- [ ] `DELETE /api/material-groups/subgroups/{id}` deletes subgroup (204)

### 7.5 UI: Manager Materials Page (/manager/materials)
- [ ] Page loads with materials list
- [ ] Material names shown (not codes) for PM
- [ ] Transaction modal opens and submits correctly
- [ ] Stock levels update after transaction

---

## 8. Recipes & Consumption Rules

### 8.1 Recipes
- [ ] `GET /api/recipes` returns recipe list (200) — accessible to PM + admin
- [ ] Recipe lookup by color + size + application method works
- [ ] Recipe includes glaze types, firing temperatures, required materials

### 8.2 Consumption Rules
- [ ] `GET /api/consumption-rules` returns rules list (200)
- [ ] `POST /api/consumption-rules` creates rule (201)
- [ ] `PATCH /api/consumption-rules/{id}` updates rule (200)
- [ ] `DELETE /api/consumption-rules/{id}` deletes rule (204)

### 8.3 UI: Consumption Rules Page (/admin/consumption-rules)
- [ ] Page loads with rules table
- [ ] Create dialog opens with material/color/size fields
- [ ] Edit and delete work

---

## 9. Kilns & Firing

### 9.1 Kilns CRUD
- [ ] `GET /api/kilns` returns kiln list with status badges (200)
- [ ] `GET /api/kilns/{id}` returns kiln detail (200)
- [ ] `POST /api/kilns` creates kiln (201)
- [ ] `PATCH /api/kilns/{id}` updates kiln (200)
- [ ] `DELETE /api/kilns/{id}` deletes kiln (204)

### 9.2 Kiln Inspections
- [ ] `GET /api/kiln-inspections` returns paginated inspections (200)
- [ ] `GET /api/kiln-inspections/{id}` returns single inspection (200)
- [ ] `POST /api/kiln-inspections` creates inspection record (201)
- [ ] `GET /api/kiln-inspections/items` returns inspectable items (200)
- [ ] `GET /api/kiln-inspections/matrix` returns inspection matrix (200)
- [ ] `GET /api/kiln-inspections/repairs` returns repair log (200)
- [ ] `POST /api/kiln-inspections/repairs` creates repair record (201)
- [ ] `PATCH /api/kiln-inspections/repairs/{id}` updates repair (200)
- [ ] `DELETE /api/kiln-inspections/repairs/{id}` deletes repair (200)

### 9.3 Kiln Maintenance
- [ ] `GET /api/kiln-maintenance/types` returns maintenance types (200)
- [ ] `POST /api/kiln-maintenance/types` creates type (201)
- [ ] `PUT /api/kiln-maintenance/types/{id}` updates type (200)
- [ ] `GET /api/kiln-maintenance/kilns/{kiln_id}` returns schedules for kiln (200)
- [ ] `POST /api/kiln-maintenance/kilns/{kiln_id}` creates schedule (201)
- [ ] `PUT /api/kiln-maintenance/kilns/{kiln_id}/{schedule_id}` updates schedule (200)
- [ ] `POST /api/kiln-maintenance/kilns/{kiln_id}/{schedule_id}/complete` marks complete (200)
- [ ] `DELETE /api/kiln-maintenance/kilns/{kiln_id}/{schedule_id}` deletes schedule (204)
- [ ] `GET /api/kiln-maintenance/upcoming` returns upcoming maintenance (200)

### 9.4 Firing Profiles
- [ ] `GET /api/firing-profiles` returns profiles list (200)
- [ ] `POST /api/firing-profiles` creates profile with heating/cooling intervals (201)
- [ ] `PATCH /api/firing-profiles/{id}` updates profile (200)
- [ ] `DELETE /api/firing-profiles/{id}` deletes profile (204)

### 9.5 Kiln Firing Schedules
- [ ] `GET /api/kiln-firing-schedules` returns schedules (200)
- [ ] `GET /api/kiln-firing-schedules/{id}` returns single schedule (200)
- [ ] `POST /api/kiln-firing-schedules` creates schedule (201)
- [ ] `PATCH /api/kiln-firing-schedules/{id}` updates schedule (200)
- [ ] `DELETE /api/kiln-firing-schedules/{id}` deletes schedule (204)

### 9.6 Kiln Constants & Loading Rules
- [ ] `GET /api/kiln-constants` returns kiln capacity constants (200)
- [ ] `GET /api/kiln-loading-rules` returns per-kiln loading rules (JSONB) (200)

### 9.7 UI: Manager Kilns Page (/manager/kilns)
- [ ] Page loads with kiln cards/list
- [ ] Status badges display correctly (active, maintenance, offline)
- [ ] Click through to inspection/maintenance pages works

---

## 10. Batches (Firing Batches)

### 10.1 Batch Operations
- [ ] `POST /api/batches/auto-form` auto-forms optimal batch for a kiln (200)
- [ ] `POST /api/batches/capacity-preview` shows what would fit (200)
- [ ] `GET /api/batches` returns batch list (200)
- [ ] `GET /api/batches/{id}` returns batch detail with positions (200)
- [ ] `POST /api/batches` creates batch manually (201)
- [ ] `PATCH /api/batches/{id}` updates batch (200)
- [ ] `POST /api/batches/{id}/start` starts firing (200)
- [ ] `POST /api/batches/{id}/complete` marks firing complete (200)
- [ ] `POST /api/batches/{id}/confirm` QM confirms batch (200)
- [ ] `POST /api/batches/{id}/reject` QM rejects batch (200)
- [ ] `POST /api/batches/{id}/photos` uploads batch photo (200)
- [ ] `GET /api/batches/{id}/photos` returns batch photos (200)

---

## 11. Schedule & Planning

### 11.1 Schedule API
- [ ] `GET /api/schedule` returns schedule data (glazing, firing, sorting, QC sections) (200)
- [ ] Sections load without error for each factory

### 11.2 UI: Manager Schedule Page (/manager/schedule)
- [ ] Page loads with 4 sections: Glazing, Firing, Sorting, QC
- [ ] Each section shows positions/batches in correct status
- [ ] Drag-and-drop or status change within schedule works

---

## 12. Tasks

### 12.1 Task CRUD
- [ ] `GET /api/tasks` returns task list (200)
- [ ] `GET /api/tasks/{id}` returns task detail (200)
- [ ] `POST /api/tasks` creates task (201)
- [ ] `PATCH /api/tasks/{id}` updates task (200)
- [ ] `POST /api/tasks/{id}/complete` completes task (200)
- [ ] `POST /api/tasks/{id}/resolve-shortage` resolves material shortage (200)
- [ ] `POST /api/tasks/{id}/resolve-size` resolves size issue (200)
- [ ] `POST /api/tasks/{id}/resolve-consumption` resolves consumption measurement (200)

---

## 13. Defects & Quality

### 13.1 Defect Causes
- [ ] `GET /api/defects` returns defect causes list (200)
- [ ] `GET /api/defects/{id}` returns single defect cause (200)
- [ ] `POST /api/defects` creates defect cause (201)
- [ ] `PATCH /api/defects/{id}` updates defect cause (200)
- [ ] `DELETE /api/defects/{id}` deletes defect cause (204)

### 13.2 Defect Recording
- [ ] `POST /api/defects/record` records defect on position (200)
- [ ] `GET /api/defects/repair-queue` shows items needing repair (200)
- [ ] `GET /api/defects/coefficients` returns defect coefficients (200)
- [ ] `POST /api/defects/positions/{id}/override` overrides coefficient (200)

### 13.3 Surplus Dispositions
- [ ] `GET /api/defects/surplus-dispositions` returns surplus items (200)
- [ ] `GET /api/defects/surplus-summary` returns summary (200)
- [ ] `POST /api/defects/surplus-dispositions/auto-assign` auto-assigns (200)

### 13.4 Supplier Reports
- [ ] `GET /api/defects/supplier-reports` returns reports (200)
- [ ] `POST /api/defects/supplier-reports/generate` generates report (200)

### 13.5 UI: Quality Manager Dashboard (/quality)
- [ ] Dashboard loads with QC queue
- [ ] Defect recording form works
- [ ] Repair queue shows items

---

## 14. Warehouse

### 14.1 Finished Goods
- [ ] `GET /api/finished-goods` returns goods list with pagination (200)
- [ ] Product type filter works (planters, bowls, etc.)
- [ ] `POST /api/finished-goods` creates record (201)
- [ ] `PATCH /api/finished-goods/{id}` updates record (200)
- [ ] `DELETE /api/finished-goods/{id}` deletes record (204)

### 14.2 Reconciliations
- [ ] `GET /api/reconciliations` returns reconciliation list (200)
- [ ] `POST /api/reconciliations` creates new reconciliation (201)
- [ ] `GET /api/reconciliations/{id}` returns detail (200)
- [ ] `GET /api/reconciliations/{id}/items` returns reconciliation items (200)
- [ ] `POST /api/reconciliations/{id}/items` adds item to reconciliation (201)
- [ ] `POST /api/reconciliations/{id}/complete` completes reconciliation (200)
- [ ] `PATCH /api/reconciliations/{id}` updates reconciliation (200)
- [ ] `DELETE /api/reconciliations/{id}` deletes reconciliation (204)

### 14.3 Mana Shipments
- [ ] `GET /api/mana-shipments` returns shipments list (200)
- [ ] `GET /api/mana-shipments/{id}` returns shipment detail (200)
- [ ] `PATCH /api/mana-shipments/{id}` updates shipment (200)
- [ ] `POST /api/mana-shipments/{id}/confirm` confirms shipment (200)
- [ ] `POST /api/mana-shipments/{id}/ship` marks as shipped (200)
- [ ] `DELETE /api/mana-shipments/{id}` deletes shipment (204)

### 14.4 Warehouse Sections
- [ ] `GET /api/warehouse-sections` returns sections (200)
- [ ] Section CRUD works

### 14.5 UI: Warehouse Dashboard (/warehouse)
- [ ] Dashboard loads with inventory summary
- [ ] Navigation to finished goods, reconciliations, shipments works
- [ ] Finished goods page: product type filter toggles work
- [ ] Reconciliation workflow: create -> add items -> complete

---

## 15. Employees, Attendance & Payroll

### 15.1 Employee CRUD
- [ ] `GET /api/employees` returns employee list (200)
- [ ] `GET /api/employees/{id}` returns employee detail (200)
- [ ] `POST /api/employees` creates employee with formal/contractor type (201)
- [ ] `PATCH /api/employees/{id}` updates employee (200)
- [ ] `POST /api/employees/{id}/deactivate` deactivates employee (200)
- [ ] PM sees only production staff from their factory
- [ ] CEO sees all employees across factories

### 15.2 Attendance
- [ ] `GET /api/employees/{id}/attendance?year=Y&month=M` returns monthly attendance (200)
- [ ] `POST /api/employees/{id}/attendance` records attendance (201)
- [ ] Attendance statuses: present, absent, sick, leave, half_day
- [ ] Overtime hours tracked per record
- [ ] Attendance grid column headers color-coded by factory calendar:
  - Green = working day, Red = holiday, Gray = Sunday
- [ ] Recording attendance on holiday marks as overtime
- [ ] Working days counter at bottom matches factory calendar

### 15.3 Payroll
- [ ] `GET /api/employees/payroll-summary?factory_id=X&year=Y&month=M` returns payroll (200)
- [ ] Payroll includes: base salary, allowances, overtime pay, deductions
- [ ] BPJS calculation correct
- [ ] PPh 21 calculation correct
- [ ] Prorated salary for partial months correct

### 15.4 Salary Data Security
- [ ] Warehouse role cannot see salary data (returns 403 or filtered response)
- [ ] Sorter/Packer role cannot access /admin/employees
- [ ] Only management roles (owner, admin, CEO, PM) see salary columns

### 15.5 UI: Employees Page (/admin/employees, /manager/staff)
- [ ] Employee list tab: shows name, position, phone, type, hire date, base salary
- [ ] Attendance tab: grid shows all days with color-coded headers
- [ ] Payroll tab: shows calculated gross/net with all components
- [ ] PM at /manager/staff sees only production department
- [ ] Admin at /admin/employees sees all departments

---

## 16. Admin Panel & Settings

### 16.1 Admin Panel (/admin)
- [ ] Admin panel page loads with navigation cards
- [ ] All admin sub-pages accessible

### 16.2 Admin Settings (/admin/settings)
- [ ] Settings page loads with 5 tabs:
  1. Escalation rules
  2. Receiving settings
  3. Defect settings
  4. Consolidation settings
  5. Lead time defaults
- [ ] Each tab saves correctly via `GET/PUT /api/admin-settings/{section}`

### 16.3 Dashboard Access (/admin/dashboard-access)
- [ ] `GET /api/dashboard-access` returns access matrix (200)
- [ ] `PUT /api/dashboard-access` updates access rules (200)
- [ ] PM can be granted access to additional dashboards

### 16.4 User Management (/users)
- [ ] `GET /api/users` returns user list (200) — CEO/admin/owner only
- [ ] `GET /api/users/{id}` returns user detail (200)
- [ ] `POST /api/users` creates user with role (201)
- [ ] `PATCH /api/users/{id}` updates user (200)
- [ ] `POST /api/users/{id}/toggle-active` enables/disables user (200)

### 16.5 Reference Data Admin Pages
- [ ] /admin/recipes — recipes CRUD works
- [ ] /admin/suppliers — suppliers CRUD works
- [ ] /admin/collections — collections CRUD works
- [ ] /admin/color-collections — color collections CRUD works
- [ ] /admin/colors — colors CRUD works
- [ ] /admin/application-types — app types CRUD works
- [ ] /admin/places-of-application — POA CRUD works
- [ ] /admin/finishing-types — finishing CRUD works
- [ ] /admin/materials — materials admin CRUD works
- [ ] /admin/warehouses — warehouses CRUD works
- [ ] /admin/packaging — packaging CRUD works
- [ ] /admin/sizes — sizes CRUD works
- [ ] /admin/firing-profiles — firing profiles CRUD works
- [ ] /admin/stages — stages CRUD works
- [ ] /admin/firing-schedules — firing schedules CRUD works
- [ ] /admin/temperature-groups — temperature groups with recipe assignment works

### 16.6 Reference Data API
- [ ] `GET /api/reference/all` returns all reference data in one call (200)
- [ ] `GET /api/reference/product-types` returns product types (200)
- [ ] `GET /api/reference/stone-types` returns stone types (200)
- [ ] `GET /api/reference/glaze-types` returns glaze types (200)
- [ ] `GET /api/reference/finish-types` returns finish types (200)
- [ ] `GET /api/reference/shape-types` returns shapes (200)
- [ ] `GET /api/reference/material-types` returns material types (200)
- [ ] `GET /api/reference/position-statuses` returns statuses (200)
- [ ] `GET /api/reference/collections` returns collections (200)
- [ ] `GET /api/reference/application-methods` returns methods (200)
- [ ] `GET /api/reference/application-collections` returns app collections (200)
- [ ] `GET /api/reference/shape-coefficients` returns coefficients (200)
- [ ] `PUT /api/reference/shape-coefficients/{shape}/{product_type}` updates coefficient (200)
- [ ] `GET /api/reference/bowl-shapes` returns bowl shapes (200)
- [ ] `GET /api/reference/temperature-groups` returns temp groups (200)
- [ ] Temperature group recipe assignment: POST/DELETE work
- [ ] `POST /api/reference/bulk-import` imports reference data (200)

---

## 17. Stages

### 17.1 Stages CRUD
- [ ] `GET /api/stages` returns stages list (200)
- [ ] `POST /api/stages` creates stage (201)
- [ ] `PATCH /api/stages/{id}` updates stage (200)
- [ ] `DELETE /api/stages/{id}` deletes stage (204)

---

## 18. Suppliers

### 18.1 Suppliers CRUD
- [ ] `GET /api/suppliers` returns supplier list (200)
- [ ] `POST /api/suppliers` creates supplier (201)
- [ ] `PATCH /api/suppliers/{id}` updates supplier (200)
- [ ] `DELETE /api/suppliers/{id}` deletes supplier (204)

---

## 19. TOC/DBR Scheduling

### 19.1 Constraints
- [ ] `GET /api/toc/constraints` returns system constraints (kilns as bottleneck) (200)
- [ ] `PATCH /api/toc/constraints/{id}` updates constraint settings (200)
- [ ] `PATCH /api/toc/bottleneck/batch-mode` changes batch mode (200)
- [ ] `PATCH /api/toc/bottleneck/buffer-target` adjusts buffer target (200)

### 19.2 Buffer Health
- [ ] `GET /api/toc/buffer-health` returns buffer penetration data (200)
- [ ] `GET /api/toc/buffer-zones` returns zone definitions (200)

---

## 20. TPS (Toyota Production System) Metrics

### 20.1 TPS Parameters
- [ ] `GET /api/tps/parameters` returns TPS parameters (200)
- [ ] `POST /api/tps/parameters` creates parameter (201)
- [ ] `PATCH /api/tps/parameters/{id}` updates parameter (200)

### 20.2 TPS Records & Dashboard
- [ ] `GET /api/tps` returns TPS records (200)
- [ ] `POST /api/tps` creates TPS record (201)
- [ ] `POST /api/tps/record` records TPS measurement (201)
- [ ] `GET /api/tps/dashboard-summary` returns summary (200)
- [ ] `GET /api/tps/shift-summary` returns shift data (200)
- [ ] `GET /api/tps/signal` returns current signal status (200)
- [ ] `GET /api/tps/throughput` returns throughput data (200)

### 20.3 TPS Deviations
- [ ] `GET /api/tps/deviations` returns deviations list (200)
- [ ] `POST /api/tps/deviations` creates deviation (201)
- [ ] `PATCH /api/tps/deviations/{id}` updates deviation (200)
- [ ] `GET /api/tps/deviations/operations` returns operations data (200)
- [ ] `GET /api/tps/position/{id}/timeline` returns position timeline (200)

---

## 21. Reports & Analytics

### 21.1 Reports
- [ ] `GET /api/reports` returns available reports (200)

### 21.2 Analytics
- [ ] `GET /api/analytics/dashboard-summary` returns summary cards (200)
- [ ] `GET /api/analytics/production-metrics` returns production data (200)
- [ ] `GET /api/analytics/material-metrics` returns material data (200)
- [ ] `GET /api/analytics/factory-comparison` returns multi-factory comparison (200)
- [ ] `GET /api/analytics/buffer-health` returns TOC buffer health (200)
- [ ] `GET /api/analytics/trend-data` returns trend charts data (200)
- [ ] `GET /api/analytics/activity-feed` returns recent activity (200)
- [ ] `GET /api/analytics/inventory-report` returns inventory report (200)
- [ ] `GET /api/analytics/anomalies` returns detected anomalies (200)

### 21.3 Export
- [ ] `GET /api/export/materials/excel` downloads materials Excel (200)
- [ ] `GET /api/export/quality/excel` downloads quality Excel (200)
- [ ] `GET /api/export/orders/excel` downloads orders Excel (200)
- [ ] `GET /api/export/orders/pdf` downloads orders PDF (200)
- [ ] `GET /api/export/positions/pdf` downloads positions PDF (200)
- [ ] `POST /api/export/owner-monthly` generates owner monthly report (200)
- [ ] `POST /api/export/ceo-daily` generates CEO daily report (200)

### 21.4 UI: Reports Page (/reports)
- [ ] Reports page loads with orders summary + kiln utilization
- [ ] Dashboard summary cards show: active orders, positions, on-time %

---

## 22. Financials

### 22.1 Financial Entries
- [ ] `GET /api/financials/summary` returns financial summary (200)
- [ ] `GET /api/financials` returns entries list (200)
- [ ] `GET /api/financials/{id}` returns single entry (200)
- [ ] `POST /api/financials` creates entry (201)
- [ ] `PATCH /api/financials/{id}` updates entry (200)
- [ ] `DELETE /api/financials/{id}` deletes entry (204)

---

## 23. Telegram Bot

### 23.1 Bot Status & Config
- [ ] `GET /api/telegram/bot-status` returns bot status (200)
- [ ] `GET /api/telegram/owner-chat` returns owner chat config (200)
- [ ] `PUT /api/telegram/owner-chat` updates owner chat (200)
- [ ] `POST /api/telegram/test-chat` sends test message (200)
- [ ] `GET /api/telegram/recent-chats` returns recent chat IDs (200)

### 23.2 Webhook & Subscriptions
- [ ] `POST /api/telegram/webhook` receives Telegram updates (200)
- [ ] `POST /api/telegram/subscribe` subscribes to notifications (200)
- [ ] `DELETE /api/telegram/unsubscribe` unsubscribes (200)

### 23.3 Delivery Photo Processing
- [ ] `POST /api/delivery/process-photo` processes delivery note photo via OCR (200)
- [ ] Returns extracted items, quantities, supplier info

### 23.4 Bot Features (manual verification)
- [ ] Daily task distribution message sent at 21:00 (Indonesian)
- [ ] Photo analysis: delivery note OCR works
- [ ] Edit items flow: user can correct OCR results
- [ ] Material matching: supplier-aware fuzzy matching
- [ ] Natural language commands understood

---

## 24. Grinding

### 24.1 Grinding Stock
- [ ] `GET /api/grinding` returns grinding stock list (200)
- [ ] `GET /api/grinding/stats` returns grinding stats (200)
- [ ] `GET /api/grinding/{id}` returns single item (200)
- [ ] `POST /api/grinding` creates grinding stock item (201)
- [ ] `POST /api/grinding/{id}/decide` records grinding decision (200)

### 24.2 UI: Grinding Decisions (/manager/grinding)
- [ ] Page loads with grinding stock items
- [ ] Decision buttons work (grind, discard, etc.)

---

## 25. Stone Reservations

- [ ] `GET /api/stone-reservations` returns reservations (200)
- [ ] Stone reservation CRUD works

---

## 26. Packing Photos

- [ ] `GET /api/packing-photos` returns photos list (200)
- [ ] `POST /api/packing-photos` creates record (201)
- [ ] `POST /api/packing-photos/upload` uploads photo file (201)
- [ ] `DELETE /api/packing-photos/{id}` deletes photo (204)
- [ ] File upload validates magic bytes (not just extension)

---

## 27. QM Blocks

- [ ] `GET /api/qm-blocks` returns QM block list (200)
- [ ] QM block CRUD works

---

## 28. Problem Cards

- [ ] `GET /api/problem-cards` returns problem cards (200)
- [ ] Problem card CRUD works

---

## 29. Notifications

### 29.1 Notifications API
- [ ] `GET /api/notifications` returns user notifications (200)
- [ ] Notifications marked as read works
- [ ] `GET /api/notification-preferences` returns preferences (200)
- [ ] `PUT /api/notification-preferences` updates preferences (200)

---

## 30. AI Chat

- [ ] `POST /api/ai-chat/chat` sends message and returns AI response (200)
- [ ] `GET /api/ai-chat/sessions` returns chat sessions (200)
- [ ] `GET /api/ai-chat/sessions/{id}/messages` returns session messages (200)

---

## 31. Purchaser Dashboard

### 31.1 Purchaser API
- [ ] `GET /api/purchaser` returns purchaser dashboard data (200)
- [ ] Purchaser sees purchase requests, lead times, supplier info
- [ ] Lead time overrides work

### 31.2 UI: Purchaser Dashboard (/purchaser)
- [ ] Dashboard loads with pending purchase requests
- [ ] Supplier info displayed
- [ ] Lead time adjustment works

---

## 32. Guides

- [ ] `GET /api/guides/{role}/{language}` returns role-specific guide (200)
- [ ] `GET /api/guides` returns available guides list (200)
- [ ] PM guide accessible at /manager/guide

---

## 33. Dashboard-Specific UI Tests

### 33.1 Owner Dashboard (/owner)
- [ ] Strategic overview loads: revenue, costs, margins
- [ ] Multi-factory comparison visible
- [ ] Financial summary cards display

### 33.2 CEO Dashboard (/ceo)
- [ ] Operational overview loads: production status, orders, KPIs
- [ ] Read-only except task assignment
- [ ] Employee page accessible at /ceo/employees

### 33.3 Tablo Dashboard (/tablo)
- [ ] Real-time production board loads
- [ ] Auto-refreshes data
- [ ] Accessible to all authenticated users

### 33.4 Sorter/Packer Dashboard (/packing)
- [ ] Packing queue loads
- [ ] Photo upload for packed items works

---

## 34. Cross-Cutting Concerns

### 34.1 File Uploads
- [ ] Uploads validated by magic bytes (not just extension)
- [ ] Maximum file size enforced
- [ ] Uploaded files stored correctly

### 34.2 Audit Logging
- [ ] All mutations recorded in audit log
- [ ] Audit log includes: who, what, when, old_value, new_value
- [ ] `GET /api/security/audit-log` returns entries with pagination

### 34.3 Rate Limiting
- [ ] Rate limiting headers present on responses (X-RateLimit-*)
- [ ] Login endpoint: 5 attempts/minute
- [ ] General API: reasonable limits enforced

### 34.4 CORS & Security Headers
- [ ] CORS configured for frontend domain only
- [ ] Security headers present (X-Content-Type-Options, X-Frame-Options, etc.)
- [ ] CSRF protection active

### 34.5 Pagination
- [ ] All list endpoints support page/per_page params
- [ ] Response includes: items, total, page, per_page
- [ ] Default per_page is reasonable (20-50)

### 34.6 Error Handling
- [ ] 404 for non-existent resources (not 500)
- [ ] 422 for validation errors with detail message
- [ ] 403 for forbidden actions with clear message
- [ ] 500 errors logged (not silently swallowed)

### 34.7 WebSocket
- [ ] WebSocket connection at /ws establishes successfully
- [ ] Real-time updates received for relevant changes

---

## 35. Sizes

- [ ] `GET /api/sizes` returns sizes list (200)
- [ ] Sizes CRUD works
- [ ] Size resolution flow: `POST /api/tasks/{id}/resolve-size` (200)

---

## 36. Packaging

- [ ] `GET /api/packaging` returns packaging types (200)
- [ ] Packaging CRUD works

---

## Test Execution Notes

1. **Auth token**: Obtain via `POST /api/auth/login` first, include as `Authorization: Bearer <token>` header
2. **Factory context**: Most endpoints require `factory_id` — get from `GET /api/factories`
3. **Order of testing**: Start with health (1), then auth (2), then factories (3), then proceed numerically
4. **Data dependencies**: Some tests require existing data (orders need factories, positions need orders, etc.)
5. **Cleanup**: Tests that create data should track IDs for cleanup
6. **Environment**: Test against staging first, then production
