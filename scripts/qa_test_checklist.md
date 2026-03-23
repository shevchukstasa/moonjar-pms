# Moonjar PMS — QA Test Checklist

**Version:** 1.0
**Date:** 2026-03-23
**System:** Moonjar Production Management System
**Environment:** Production (`https://moonjar-pms-production.up.railway.app`)
**Tester:** _______________

---

## Legend

| Priority | Meaning |
|----------|---------|
| **P0** | Critical — system unusable if broken |
| **P1** | High — major feature broken |
| **P2** | Medium — feature degraded |
| **P3** | Low — cosmetic / minor |

| Status | Meaning |
|--------|---------|
| PASS | Test passed |
| FAIL | Test failed (add bug ID) |
| SKIP | Not applicable / blocked |

---

## 1. Authentication & Authorization

| ID | Description | Steps | Expected Result | Priority | Status |
|----|-------------|-------|-----------------|----------|--------|
| AUTH-001 | Login with valid email/password | 1. Navigate to /login 2. Enter valid owner credentials 3. Click Login | Redirect to /owner dashboard, JWT cookie set | P0 | |
| AUTH-002 | Login with invalid password | 1. Navigate to /login 2. Enter valid email, wrong password 3. Click Login | Error message, no redirect, login_failed audit logged | P0 | |
| AUTH-003 | Login with non-existent email | 1. Navigate to /login 2. Enter unknown email 3. Click Login | Generic error (no user enumeration) | P0 | |
| AUTH-004 | Google OAuth login | 1. Click "Login with Google" 2. Complete OAuth flow | Redirect to role-appropriate dashboard | P1 | |
| AUTH-005 | JWT token refresh | 1. Login 2. Wait for access token to expire (1h) 3. Make API request | Token auto-refreshes, request succeeds, token_refresh audit logged | P0 | |
| AUTH-006 | JWT expired refresh token | 1. Login 2. Wait 7 days (or manually expire) 3. Make API request | Redirect to /login | P0 | |
| AUTH-007 | Logout single session | 1. Login 2. POST /api/auth/logout | Cookie cleared, session invalidated, logout audit logged | P1 | |
| AUTH-008 | Logout all sessions | 1. Login on two devices 2. POST /api/auth/logout-all from one | Both sessions invalidated | P1 | |
| AUTH-009 | GET /api/auth/me returns current user | 1. Login 2. GET /api/auth/me | Returns user object with role, factory_id | P0 | |
| AUTH-010 | Owner key verification | 1. POST /api/auth/verify-owner-key with correct key | Returns success | P1 | |
| AUTH-011 | TOTP setup and verify | 1. POST /api/security/totp/setup 2. Scan QR 3. POST /api/auth/totp-verify | TOTP enabled, login requires 2FA | P2 | |
| AUTH-012 | TOTP disable | 1. POST /api/security/totp/disable with valid password | TOTP disabled | P2 | |
| AUTH-013 | Change password | 1. POST /api/auth/change-password with old + new | Password changed, audit logged | P1 | |
| AUTH-014 | Session restore on page refresh | 1. Login 2. Refresh browser page | User stays logged in (cookie-based restore) | P0 | |

### Role-Based Access Control

| ID | Description | Steps | Expected Result | Priority | Status |
|----|-------------|-------|-----------------|----------|--------|
| RBAC-001 | Owner sees /owner dashboard | 1. Login as owner 2. Check redirect | Redirects to /owner | P0 | |
| RBAC-002 | Owner can access ALL pages | 1. Login as owner 2. Navigate to each sidebar link | All 46+ pages accessible | P0 | |
| RBAC-003 | Administrator redirect to /admin | 1. Login as administrator | Redirects to /admin | P0 | |
| RBAC-004 | Administrator CANNOT access /owner | 1. Login as administrator 2. Navigate to /owner | Redirected to / | P0 | |
| RBAC-005 | CEO redirects to /ceo | 1. Login as ceo | Redirects to /ceo | P0 | |
| RBAC-006 | CEO can access /reports, /tablo, /users | 1. Login as ceo 2. Navigate to each | All accessible | P1 | |
| RBAC-007 | CEO CANNOT access /manager, /admin | 1. Login as ceo 2. Navigate to /manager | Redirected to / | P0 | |
| RBAC-008 | PM redirects to /manager | 1. Login as production_manager | Redirects to /manager | P0 | |
| RBAC-009 | PM can access schedule, kilns, materials, recipes | 1. Login as PM 2. Navigate to each PM page | All accessible | P1 | |
| RBAC-010 | PM CANNOT access /owner, /admin (except shared) | 1. Login as PM 2. Navigate to /owner | Redirected | P0 | |
| RBAC-011 | QM redirects to /quality | 1. Login as quality_manager | Redirects to /quality | P0 | |
| RBAC-012 | QM CANNOT access /manager, /admin | 1. Login as quality_manager 2. Navigate to /manager | Redirected | P0 | |
| RBAC-013 | Warehouse redirects to /warehouse | 1. Login as warehouse | Redirects to /warehouse | P0 | |
| RBAC-014 | Warehouse can access finished-goods, reconciliations | 1. Login as warehouse 2. Navigate to sub-pages | Accessible | P1 | |
| RBAC-015 | Sorter/Packer redirects to /packing | 1. Login as sorter_packer | Redirects to /packing | P0 | |
| RBAC-016 | Sorter/Packer CANNOT access any other dashboard | 1. Login as sorter_packer 2. Navigate to /manager | Redirected | P0 | |
| RBAC-017 | Purchaser redirects to /purchaser | 1. Login as purchaser | Redirects to /purchaser | P0 | |
| RBAC-018 | Purchaser CANNOT access /admin | 1. Login as purchaser 2. Navigate to /admin | Redirected | P0 | |
| RBAC-019 | Dashboard Access grants extra dashboards | 1. As admin, grant CEO dashboard to PM 2. Login as PM | PM can access /ceo | P2 | |
| RBAC-020 | Unauthenticated user redirects to /login | 1. Clear cookies 2. Navigate to /manager | Redirect to /login | P0 | |
| RBAC-021 | API returns 401 for unauthenticated requests | 1. GET /api/orders without token | 401 Unauthorized | P0 | |
| RBAC-022 | API returns 403 for wrong role | 1. Login as warehouse 2. DELETE /api/orders/{id} | 403 Forbidden | P0 | |

---

## 2. Per-Role Page Tests

### 2.1 Owner Dashboard (/owner)

| ID | Description | Steps | Expected Result | Priority | Status |
|----|-------------|-------|-----------------|----------|--------|
| OWN-001 | Owner dashboard loads KPIs | 1. Login as owner 2. Navigate to /owner | Dashboard summary, analytics, financials visible | P0 | |
| OWN-002 | Revenue and cost metrics display | 1. Check financial widgets | Numbers render, no NaN | P1 | |
| OWN-003 | Factory comparison chart | 1. Check factory comparison section | Chart renders with correct factories | P2 | |
| OWN-004 | Activity feed loads | 1. Check activity feed section | Recent actions displayed | P2 | |
| OWN-005 | Anomaly detection section | 1. Check anomalies section | Anomalies listed or "No anomalies" shown | P3 | |

### 2.2 CEO Dashboard (/ceo)

| ID | Description | Steps | Expected Result | Priority | Status |
|----|-------------|-------|-----------------|----------|--------|
| CEO-001 | CEO dashboard loads | 1. Login as ceo 2. Navigate to /ceo | Production metrics, buffer health visible | P0 | |
| CEO-002 | Production metrics widgets | 1. Check production section | Orders count, positions count, throughput | P1 | |
| CEO-003 | Buffer health indicators | 1. Check TOC buffer section | Green/Yellow/Red indicators render | P1 | |
| CEO-004 | Reports page accessible | 1. Navigate to /reports | Orders summary, kiln load reports render | P1 | |

### 2.3 Admin Pages (/admin/*)

| ID | Description | Steps | Expected Result | Priority | Status |
|----|-------------|-------|-----------------|----------|--------|
| ADM-001 | Admin Panel loads | 1. Login as admin 2. Navigate to /admin | Admin panel with system overview | P0 | |
| ADM-002 | Users page — list users | 1. Navigate to /users | Users table with role, factory columns | P0 | |
| ADM-003 | Users page — create user | 1. Click Add User 2. Fill form 3. Submit | User created, user_create audit logged | P0 | |
| ADM-004 | Users page — edit user role | 1. Click edit on user 2. Change role 3. Save | Role updated, role_change audit logged | P1 | |
| ADM-005 | Users page — toggle active | 1. Click toggle active | User deactivated, user_deactivate audit logged | P1 | |
| ADM-006 | Suppliers page — CRUD | 1. Create supplier 2. Edit name 3. View 4. Delete | All operations succeed | P1 | |
| ADM-007 | Collections page — CRUD | 1. Create collection 2. Edit 3. Delete | All operations succeed | P1 | |
| ADM-008 | Color Collections page — CRUD | 1. Create color collection 2. Edit 3. Delete | All operations succeed | P2 | |
| ADM-009 | Colors page — CRUD | 1. Create color 2. Edit 3. Delete | All operations succeed | P2 | |
| ADM-010 | Application Types page — CRUD | 1. Create type 2. Edit 3. Delete | All operations succeed | P2 | |
| ADM-011 | Places of Application page — CRUD | 1. Create PoA 2. Edit 3. Delete | All operations succeed | P2 | |
| ADM-012 | Finishing Types page — CRUD | 1. Create finishing type 2. Edit 3. Delete | All operations succeed | P2 | |
| ADM-013 | Materials admin page — CRUD | 1. Create material 2. Edit 3. Delete | All operations succeed, material groups respected | P1 | |
| ADM-014 | Warehouses page — CRUD | 1. Create warehouse section 2. Edit 3. Delete | All operations succeed | P1 | |
| ADM-015 | Packaging page — CRUD | 1. Create box type 2. Set capacities 3. Delete | All operations succeed | P2 | |
| ADM-016 | Sizes page — CRUD | 1. Create size 2. View glazing board calc 3. Delete | All operations succeed, board calculation works | P1 | |
| ADM-017 | Firing Profiles page — CRUD | 1. Create profile 2. Set stages 3. Delete | All operations succeed, match priority works | P1 | |
| ADM-018 | Stages page — CRUD | 1. Create stage 2. Edit 3. Delete | All operations succeed | P2 | |
| ADM-019 | Temperature Groups page — CRUD | 1. Create temp group 2. Add recipes 3. Delete | All operations succeed | P1 | |
| ADM-020 | Firing Schedules page — CRUD | 1. Create schedule 2. Edit 3. Delete | All operations succeed | P2 | |
| ADM-021 | Factory Calendar page | 1. Navigate to /admin/factory-calendar 2. Add holiday 3. Bulk add | Calendar entries created | P2 | |
| ADM-022 | Consumption Rules page — CRUD | 1. Create rule 2. Edit 3. Delete | All operations succeed | P1 | |
| ADM-023 | Dashboard Access page — grant/revoke | 1. Grant CEO dashboard to a PM 2. Verify | Access record created, user can see dashboard | P2 | |
| ADM-024 | Admin Settings page | 1. Navigate to /admin/settings 2. Edit settings | Settings saved | P1 | |
| ADM-025 | Recipes page — CRUD + materials | 1. Create recipe 2. Add recipe materials 3. Set firing stages 4. Delete | All operations succeed | P0 | |
| ADM-026 | Recipes — CSV import | 1. Upload CSV with recipes | Recipes imported correctly | P2 | |
| ADM-027 | Recipes — bulk delete | 1. Select multiple recipes 2. Bulk delete | All selected deleted | P2 | |

### 2.4 Manager Dashboard (/manager/*)

| ID | Description | Steps | Expected Result | Priority | Status |
|----|-------------|-------|-----------------|----------|--------|
| MGR-001 | Manager dashboard loads | 1. Login as PM 2. Navigate to /manager | Orders list, position kanban visible | P0 | |
| MGR-002 | Order detail page | 1. Click on order | Order detail with positions, status, timeline | P0 | |
| MGR-003 | Schedule page — resource view | 1. Navigate to /manager/schedule | Resources, batches, kiln schedule visible | P0 | |
| MGR-004 | Kilns page — list and manage | 1. Navigate to /manager/kilns | Kiln list with status, capacity, maintenance | P0 | |
| MGR-005 | Materials page — stock overview | 1. Navigate to /manager/materials | Material list with stock, reserved, effective balance | P0 | |
| MGR-006 | Kiln Inspections page | 1. Navigate to /manager/kiln-inspections | Inspection list, matrix, repair queue | P1 | |
| MGR-007 | Kiln Maintenance page | 1. Navigate to /manager/kiln-maintenance | Maintenance schedules, types, upcoming | P1 | |
| MGR-008 | Grinding Decisions page | 1. Navigate to /manager/grinding | Grinding stock items, decide actions | P1 | |
| MGR-009 | Shortage Decision page | 1. Navigate to /manager/shortage/{taskId} | Shortage details, resolution options | P1 | |
| MGR-010 | Size Resolution page | 1. Navigate to /manager/size-resolution/{taskId} | Size selection, assignment | P1 | |
| MGR-011 | PM Guide page | 1. Navigate to /manager/guide | Guide content renders | P3 | |
| MGR-012 | Tablo page | 1. Navigate to /tablo | Live production board | P1 | |

### 2.5 Quality Manager (/quality)

| ID | Description | Steps | Expected Result | Priority | Status |
|----|-------------|-------|-----------------|----------|--------|
| QM-001 | Quality dashboard loads | 1. Login as QM 2. Navigate to /quality | Quality inspections, calendar matrix, stats | P0 | |
| QM-002 | Create QC inspection | 1. Click create inspection 2. Fill form | Inspection created | P0 | |
| QM-003 | Record defect | 1. Select inspection 2. Record defect with outcome | Defect recorded, position updated | P0 | |
| QM-004 | Upload inspection photo | 1. Add photo to inspection | Photo uploaded, linked to inspection | P1 | |
| QM-005 | QM Block — block position | 1. Create QM block on position | Position status changes to blocked_by_qm | P1 | |
| QM-006 | Problem Cards — CRUD | 1. Create problem card 2. Update status 3. Close | Lifecycle works correctly | P2 | |

### 2.6 Warehouse (/warehouse/*)

| ID | Description | Steps | Expected Result | Priority | Status |
|----|-------------|-------|-----------------|----------|--------|
| WH-001 | Warehouse dashboard loads | 1. Login as warehouse 2. Navigate to /warehouse | Material stock, transactions visible | P0 | |
| WH-002 | Finished Goods page | 1. Navigate to /warehouse/finished-goods | Finished goods list, availability check | P1 | |
| WH-003 | Reconciliations page | 1. Navigate to /warehouse/reconciliations | Reconciliation list, create new | P1 | |
| WH-004 | Reconciliation workflow | 1. Create reconciliation 2. Add items 3. Complete | Status transitions: scheduled -> in_progress -> completed | P1 | |

### 2.7 Sorter/Packer (/packing)

| ID | Description | Steps | Expected Result | Priority | Status |
|----|-------------|-------|-----------------|----------|--------|
| SP-001 | Packing dashboard loads | 1. Login as sorter_packer 2. Navigate to /packing | Positions ready for packing visible | P0 | |
| SP-002 | Upload packing photo | 1. Select position 2. Upload photo | Photo saved, linked to position | P1 | |

### 2.8 Purchaser (/purchaser)

| ID | Description | Steps | Expected Result | Priority | Status |
|----|-------------|-------|-----------------|----------|--------|
| PUR-001 | Purchaser dashboard loads | 1. Login as purchaser 2. Navigate to /purchaser | Purchase orders, stats, deficits visible | P0 | |
| PUR-002 | Create purchase order | 1. Click create 2. Fill form 3. Submit | PO created in pending status | P0 | |
| PUR-003 | Purchase order status transitions | 1. Move PO: pending -> approved -> sent -> in_transit -> received -> closed | Each transition succeeds | P0 | |
| PUR-004 | View delivery schedule | 1. Check deliveries tab | Upcoming deliveries listed | P1 | |
| PUR-005 | View deficits | 1. Check deficits tab | Material deficits listed | P1 | |
| PUR-006 | Consolidation suggestions | 1. Check consolidation section | Suggestions displayed, can consolidate | P2 | |
| PUR-007 | Lead times view/override | 1. Check lead times | Default and override lead times displayed | P2 | |

### 2.9 Global Pages

| ID | Description | Steps | Expected Result | Priority | Status |
|----|-------------|-------|-----------------|----------|--------|
| GLO-001 | Settings page (/settings) | 1. Navigate to /settings | User profile, language, notification prefs | P1 | |
| GLO-002 | 404 page | 1. Navigate to /nonexistent | NotFoundPage renders | P3 | |

---

## 3. CRUD Operations & Entity Lifecycle

### 3.1 Orders

| ID | Description | Steps | Expected Result | Priority | Status |
|----|-------------|-------|-----------------|----------|--------|
| ORD-001 | Create order manually | 1. POST /api/orders with positions | Order created, status = new, positions created | P0 | |
| ORD-002 | Create order via PDF upload | 1. POST /api/orders/upload-pdf 2. POST /api/orders/confirm-pdf | PDF parsed, order created | P1 | |
| ORD-003 | Create order via sales webhook | 1. POST /api/integration/webhook/sales-order | Order auto-created, positions auto-generated | P0 | |
| ORD-004 | Read order list with filters | 1. GET /api/orders?status=new&factory_id=X | Filtered order list returned | P0 | |
| ORD-005 | Read order detail | 1. GET /api/orders/{id} | Full order with positions returned | P0 | |
| ORD-006 | Update order | 1. PATCH /api/orders/{id} | Order updated, audit trail | P1 | |
| ORD-007 | Delete order | 1. DELETE /api/orders/{id} | Order deleted (soft delete), audit trail | P1 | |
| ORD-008 | Ship order | 1. PATCH /api/orders/{id}/ship | Status -> shipped, shipped_at set | P0 | |
| ORD-009 | Cancellation request flow | 1. Request cancel via integration 2. Accept/reject | Status transitions correctly | P1 | |
| ORD-010 | Change request flow | 1. Submit change request 2. Approve/reject | Positions modified or request rejected | P1 | |
| ORD-011 | Reprocess order | 1. POST /api/orders/{id}/reprocess | Positions re-evaluated | P2 | |
| ORD-012 | Order audit log entry | 1. Create order 2. Check /api/security/audit-log | Audit entry with order details present | P1 | |

### 3.2 Positions

| ID | Description | Steps | Expected Result | Priority | Status |
|----|-------------|-------|-----------------|----------|--------|
| POS-001 | List positions with filters | 1. GET /api/positions?status=planned | Filtered list returned | P0 | |
| POS-002 | Get position detail | 1. GET /api/positions/{id} | Full position with batch, recipe info | P0 | |
| POS-003 | Update position | 1. PATCH /api/positions/{id} | Position updated | P1 | |
| POS-004 | Position status transition — happy path | 1. planned -> engobe_applied -> glazed -> pre_kiln_check -> loaded_in_kiln -> fired -> transferred_to_sorting -> packed -> ready_for_shipment -> shipped | Each transition succeeds | P0 | |
| POS-005 | Position status — invalid transition rejected | 1. Try planned -> shipped directly | 400 or 422 error | P0 | |
| POS-006 | Position split | 1. POST /api/positions/{id}/split | Child positions created with correct quantities | P0 | |
| POS-007 | Position merge | 1. POST /api/positions/{id}/merge | Children merged back, parent quantity updated | P1 | |
| POS-008 | Position split tree | 1. GET /api/positions/{id}/split-tree | Tree structure of parent and children | P2 | |
| POS-009 | Blocking summary | 1. GET /api/positions/blocking-summary | Summary of blocked positions by reason | P1 | |
| POS-010 | Allowed transitions | 1. GET /api/positions/{id}/allowed-transitions | Only valid next statuses returned | P1 | |
| POS-011 | Material reservations | 1. GET /api/positions/{id}/material-reservations | Reservation list for position | P1 | |
| POS-012 | Stock availability check | 1. GET /api/positions/{id}/stock-availability | Stock status for required materials | P1 | |
| POS-013 | Force unblock | 1. POST /api/positions/{id}/force-unblock | Position unblocked, audit trail | P1 | |
| POS-014 | Reorder positions | 1. POST /api/positions/reorder | Position order updated | P2 | |
| POS-015 | Reassign batch | 1. POST /api/positions/{id}/reassign-batch | Position moved to new batch | P2 | |
| POS-016 | Color mismatch resolution | 1. POST /api/positions/{id}/resolve-color-mismatch | Position resolved, appropriate status | P2 | |
| POS-017 | Production split | 1. POST /api/positions/{id}/split-production | Production split with firing rounds | P1 | |

### 3.3 Materials

| ID | Description | Steps | Expected Result | Priority | Status |
|----|-------------|-------|-----------------|----------|--------|
| MAT-001 | List materials | 1. GET /api/materials | Material list with stock levels | P0 | |
| MAT-002 | Create material | 1. POST /api/materials | Material created in correct group | P0 | |
| MAT-003 | Update material | 1. PATCH /api/materials/{id} | Material updated | P1 | |
| MAT-004 | Delete material | 1. DELETE /api/materials/{id} | Material deleted (if no transactions) | P1 | |
| MAT-005 | Material transactions — receive | 1. POST /api/materials/transactions type=receive | Stock increased | P0 | |
| MAT-006 | Material transactions — reserve | 1. POST /api/materials/transactions type=reserve | Reserved quantity increased | P0 | |
| MAT-007 | Material transactions — consume | 1. POST /api/materials/transactions type=consume | Stock decreased, reserved decreased | P0 | |
| MAT-008 | Material transactions — unreserve | 1. POST /api/materials/transactions type=unreserve | Reserved quantity decreased | P1 | |
| MAT-009 | Low stock alert | 1. GET /api/materials/low-stock | Materials below min_stock listed | P1 | |
| MAT-010 | Effective balance | 1. GET /api/materials/effective-balance | Balance = stock - reserved shown correctly | P1 | |
| MAT-011 | Consumption adjustments — approve/reject | 1. Create adjustment 2. Approve or reject | Stock adjusted or no change | P2 | |
| MAT-012 | Duplicate detection and merge | 1. GET /api/materials/duplicates 2. POST /api/materials/merge | Duplicates found, merge combines transactions | P2 | |
| MAT-013 | Purchase request creation | 1. POST /api/materials/purchase-requests | Purchase request created | P1 | |
| MAT-014 | Partial receiving | 1. POST /api/materials/purchase-requests/{id}/receive-partial | Partial qty received, status updated | P1 | |
| MAT-015 | Transaction approval | 1. POST /api/materials/transactions/{id}/approve | Transaction approved | P2 | |
| MAT-016 | Material groups hierarchy | 1. GET /api/material-groups/hierarchy | Groups -> Subgroups tree returned | P1 | |

### 3.4 Kilns

| ID | Description | Steps | Expected Result | Priority | Status |
|----|-------------|-------|-----------------|----------|--------|
| KLN-001 | List kilns | 1. GET /api/kilns | Kiln list with status, capacity | P0 | |
| KLN-002 | Create kiln | 1. POST /api/kilns | Kiln created for factory | P1 | |
| KLN-003 | Update kiln | 1. PATCH /api/kilns/{id} | Kiln updated | P1 | |
| KLN-004 | Change kiln status | 1. PATCH /api/kilns/{id}/status to maintenance_planned | Status updated, notifications sent | P0 | |
| KLN-005 | Delete kiln | 1. DELETE /api/kilns/{id} | Kiln deleted (if no active batches) | P2 | |
| KLN-006 | Kiln breakdown | 1. POST /api/kilns/{id}/breakdown | Status -> maintenance_emergency, kiln_breakdown notification | P0 | |
| KLN-007 | Kiln restore | 1. POST /api/kilns/{id}/restore | Status -> active | P0 | |
| KLN-008 | Kiln maintenance schedule CRUD | 1. Create 2. Update 3. Complete 4. Delete | All operations succeed | P1 | |
| KLN-009 | Kiln rotation rules | 1. GET /api/kilns/{id}/rotation-rules 2. PUT rules | Rules saved and returned | P2 | |
| KLN-010 | Kiln rotation check | 1. GET /api/kilns/{id}/rotation-check | Rotation compliance status | P2 | |
| KLN-011 | Kiln loading rules CRUD | 1. Create rule 2. Edit 3. Delete | Per-kiln loading rules managed | P1 | |
| KLN-012 | Kiln constants CRUD | 1. Create constant 2. Edit 3. Delete | Manual + production mode constants | P1 | |
| KLN-013 | Kiln inspections — create and list | 1. POST inspection 2. GET list | Inspection recorded with items | P1 | |
| KLN-014 | Kiln inspection repairs CRUD | 1. Create repair 2. Update 3. Delete | Repair tracked | P2 | |
| KLN-015 | Kiln inspection matrix | 1. GET /api/kiln-inspections/matrix | Matrix view of inspection status | P2 | |

### 3.5 Batches

| ID | Description | Steps | Expected Result | Priority | Status |
|----|-------------|-------|-----------------|----------|--------|
| BAT-001 | Create batch | 1. POST /api/batches | Batch created in suggested status | P0 | |
| BAT-002 | Auto-form batch | 1. POST /api/batches/auto-form | Batch auto-formed based on TOC rules | P0 | |
| BAT-003 | Capacity preview | 1. POST /api/batches/capacity-preview | Preview of kiln loading | P1 | |
| BAT-004 | Batch lifecycle | 1. suggested -> planned -> in_progress -> done | confirm, start, complete transitions work | P0 | |
| BAT-005 | Batch photos upload | 1. POST /api/batches/{id}/photos | Photos attached to batch | P2 | |
| BAT-006 | Batch reject (suggested) | 1. POST /api/batches/{id}/reject | Batch rejected, positions freed | P1 | |

### 3.6 Tasks

| ID | Description | Steps | Expected Result | Priority | Status |
|----|-------------|-------|-----------------|----------|--------|
| TSK-001 | List tasks with filters | 1. GET /api/tasks?status=pending | Filtered task list | P0 | |
| TSK-002 | Create task | 1. POST /api/tasks | Task created, assigned user notified | P0 | |
| TSK-003 | Update task | 1. PATCH /api/tasks/{id} | Task updated | P1 | |
| TSK-004 | Complete task | 1. POST /api/tasks/{id}/complete | Status -> done | P0 | |
| TSK-005 | Resolve shortage task | 1. POST /api/tasks/{id}/resolve-shortage | Shortage resolved, materials updated | P1 | |
| TSK-006 | Resolve size task | 1. POST /api/tasks/{id}/resolve-size | Size assigned to position | P1 | |
| TSK-007 | Resolve consumption task | 1. POST /api/tasks/{id}/resolve-consumption | Consumption data recorded | P1 | |

### 3.7 Quality & Defects

| ID | Description | Steps | Expected Result | Priority | Status |
|----|-------------|-------|-----------------|----------|--------|
| DEF-001 | List defect causes | 1. GET /api/defects | Defect causes returned | P1 | |
| DEF-002 | Create defect cause | 1. POST /api/defects | Cause created | P2 | |
| DEF-003 | Record defect on position | 1. POST /api/defects/record | Defect recorded, outcome applied | P0 | |
| DEF-004 | Defect coefficients | 1. GET /api/defects/coefficients | Per-factory coefficients | P2 | |
| DEF-005 | Override defect coefficient | 1. POST /api/defects/positions/{id}/override | Custom coefficient applied | P2 | |
| DEF-006 | Repair queue | 1. GET /api/defects/repair-queue | Positions needing repair listed | P1 | |
| DEF-007 | Surplus dispositions | 1. GET /api/defects/surplus-dispositions | Surplus items listed | P2 | |
| DEF-008 | Auto-assign surplus | 1. POST /api/defects/surplus-dispositions/auto-assign | Surplus auto-assigned to showroom/casters/mana | P2 | |
| DEF-009 | Supplier defect reports | 1. POST /api/defects/supplier-reports/generate | Report generated | P2 | |
| DEF-010 | QM blocks CRUD | 1. Create block 2. Update 3. Delete | Position/batch blocked and unblocked | P1 | |

---

## 4. Business Logic

### 4.1 Order Lifecycle

| ID | Description | Steps | Expected Result | Priority | Status |
|----|-------------|-------|-----------------|----------|--------|
| BL-001 | New order triggers material reservation | 1. Create order with materials 2. Check material stock | Reserved qty increased for each required material | P0 | |
| BL-002 | Insufficient materials -> position status | 1. Create order with unavailable material | Position status = insufficient_materials, task created | P0 | |
| BL-003 | Order status auto-calculation | 1. Move all positions to shipped | Order status auto-changes to shipped | P0 | |
| BL-004 | Partial readiness | 1. Ship some positions, not all | Order status = partially_ready | P1 | |
| BL-005 | Cancellation preserves shipped positions | 1. Cancel order with some shipped positions | Shipped positions preserved, others cancelled | P1 | |

### 4.2 Scheduling & TOC

| ID | Description | Steps | Expected Result | Priority | Status |
|----|-------------|-------|-----------------|----------|--------|
| BL-006 | Kiln schedule generation | 1. GET /api/schedule/kiln-schedule | Schedule respects kiln capacity and constraints | P0 | |
| BL-007 | Glazing schedule | 1. GET /api/schedule/glazing-schedule | Schedule generated for glazing stations | P1 | |
| BL-008 | TOC constraints — buffer health | 1. GET /api/toc/buffer-health | Green/Yellow/Red buffer status | P1 | |
| BL-009 | TOC buffer zones | 1. GET /api/toc/buffer-zones | Zone boundaries correct | P2 | |
| BL-010 | Batch mode — auto vs hybrid | 1. PATCH /api/toc/bottleneck/batch-mode | Batch mode updated, affects scheduling | P1 | |
| BL-011 | Reschedule order | 1. POST /api/schedule/orders/{id}/reschedule | Positions rescheduled | P1 | |
| BL-012 | Factory-wide reschedule | 1. POST /api/schedule/factory/{id}/reschedule | All positions rescheduled | P1 | |

### 4.3 TPS (Toyota Production System)

| ID | Description | Steps | Expected Result | Priority | Status |
|----|-------------|-------|-----------------|----------|--------|
| BL-013 | TPS record entry | 1. POST /api/tps/record | TPS entry created | P1 | |
| BL-014 | TPS dashboard summary | 1. GET /api/tps/dashboard-summary | Summary with deviations, throughput | P1 | |
| BL-015 | TPS signal (Andon) | 1. GET /api/tps/signal | Current signal status | P2 | |
| BL-016 | TPS throughput calculation | 1. GET /api/tps/throughput | Hourly/daily throughput numbers | P2 | |
| BL-017 | TPS position timeline | 1. GET /api/tps/position/{id}/timeline | Full timeline with stage durations | P2 | |
| BL-018 | TPS deviations CRUD | 1. Create deviation 2. Update 3. List | Deviations tracked | P2 | |

### 4.4 Stone Reservations

| ID | Description | Steps | Expected Result | Priority | Status |
|----|-------------|-------|-----------------|----------|--------|
| BL-019 | Stone reservation list | 1. GET /api/stone-reservations | Reservations with position links | P1 | |
| BL-020 | Defect rates for stone | 1. GET /api/stone-reservations/defect-rates | Per-type defect rates | P2 | |
| BL-021 | Weekly reservation report | 1. GET /api/stone-reservations/weekly-report | Weekly summary | P2 | |

---

## 5. Telegram Bot

| ID | Description | Steps | Expected Result | Priority | Status |
|----|-------------|-------|-----------------|----------|--------|
| TG-001 | /start — account linking (private chat) | 1. Send /start in private chat | Asks for email to link account | P0 | |
| TG-002 | /start — group welcome | 1. Send /start in group chat | Welcome message displayed | P1 | |
| TG-003 | /status — pending tasks | 1. Send /status as linked user | Lists pending/in-progress tasks | P0 | |
| TG-004 | /status — unlinked user | 1. Send /status without linked account | Error: "Akun belum terhubung" | P1 | |
| TG-005 | /help — command list | 1. Send /help | All 11 commands listed in Indonesian | P1 | |
| TG-006 | /stop — unlink account | 1. Send /stop | Account unlinked | P1 | |
| TG-007 | /defect <pos_id> <percent> — report defect | 1. Send /defect 12345 8 | Defect recorded for position | P0 | |
| TG-008 | /actual <pos_id> <qty> — record output | 1. Send /actual 12345 95 | Actual quantity recorded | P0 | |
| TG-009 | /split <pos_id> <q1> <q2> — production split | 1. Send /split 12345 50 30 20 | Position split into 3 parts | P1 | |
| TG-010 | /glaze <pos_id> — glazing info | 1. Send /glaze 12345 | Recipe, engobe, glaze info displayed | P1 | |
| TG-011 | /recipe <collection> <color> [size] — recipe lookup | 1. Send /recipe Classic White 30x60 | Recipe details shown | P1 | |
| TG-012 | /plan — tomorrow's production plan | 1. Send /plan | Next day production plan for user's factory | P1 | |
| TG-013 | /photo — photo upload instructions | 1. Send /photo | Instructions to send photo directly | P2 | |
| TG-014 | Photo processing (send photo directly) | 1. Send photo in chat | Photo saved, linked to relevant entity | P1 | |
| TG-015 | Callback query handling (daily/alert/task) | 1. Click inline button from daily message | Callback processed, action taken | P1 | |
| TG-016 | Unknown command | 1. Send /unknown | Error: "Perintah tidak dikenal" with /help hint | P3 | |
| TG-017 | Bot status endpoint | 1. GET /api/telegram/bot-status | Bot connection status returned | P2 | |
| TG-018 | Webhook registration | 1. POST /api/telegram/subscribe | Webhook registered with Telegram | P1 | |

---

## 6. API Endpoint Tests (Status Codes)

### 6.1 Health & System

| ID | Description | Steps | Expected Result | Priority | Status |
|----|-------------|-------|-----------------|----------|--------|
| API-001 | GET /api/health | 1. curl endpoint | 200 {"status":"ok"} | P0 | |
| API-002 | GET /api/health/seed-status | 1. curl endpoint | 200 with seed data status | P2 | |
| API-003 | GET /api/health/backup | 1. curl endpoint (admin) | 200 with backup info | P2 | |

### 6.2 Auth Endpoints

| ID | Description | Steps | Expected Result | Priority | Status |
|----|-------------|-------|-----------------|----------|--------|
| API-004 | POST /api/auth/login — valid | 1. POST with valid creds | 200 + cookies set | P0 | |
| API-005 | POST /api/auth/login — invalid | 1. POST with bad creds | 401 | P0 | |
| API-006 | GET /api/auth/me — authenticated | 1. GET with valid token | 200 + user data | P0 | |
| API-007 | GET /api/auth/me — unauthenticated | 1. GET without token | 401 | P0 | |

### 6.3 Core Entity Endpoints (authenticated as owner)

| ID | Description | Steps | Expected Result | Priority | Status |
|----|-------------|-------|-----------------|----------|--------|
| API-008 | GET /api/orders | 1. GET with token | 200 + paginated orders | P0 | |
| API-009 | GET /api/positions | 1. GET with token | 200 + paginated positions | P0 | |
| API-010 | GET /api/materials | 1. GET with token | 200 + paginated materials | P0 | |
| API-011 | GET /api/kilns | 1. GET with token | 200 + kiln list | P0 | |
| API-012 | GET /api/recipes | 1. GET with token | 200 + recipe list | P0 | |
| API-013 | GET /api/tasks | 1. GET with token | 200 + task list | P0 | |
| API-014 | GET /api/suppliers | 1. GET with token | 200 + supplier list | P0 | |
| API-015 | GET /api/batches | 1. GET with token | 200 + batch list | P0 | |
| API-016 | GET /api/defects | 1. GET with token | 200 + defect causes | P1 | |
| API-017 | GET /api/quality/inspections | 1. GET with token | 200 + inspections | P1 | |
| API-018 | GET /api/notifications | 1. GET with token | 200 + notifications | P1 | |
| API-019 | GET /api/notifications/unread-count | 1. GET with token | 200 + count | P1 | |
| API-020 | GET /api/schedule/resources | 1. GET with token | 200 + resources | P1 | |
| API-021 | GET /api/schedule/batches | 1. GET with token | 200 + scheduled batches | P1 | |
| API-022 | GET /api/schedule/kiln-schedule | 1. GET with token | 200 + kiln schedule | P1 | |
| API-023 | GET /api/factories | 1. GET with token | 200 + factory list | P1 | |
| API-024 | GET /api/users | 1. GET with token | 200 + user list | P1 | |
| API-025 | GET /api/reference/all | 1. GET with token | 200 + all reference data | P1 | |
| API-026 | GET /api/analytics/dashboard-summary | 1. GET with token | 200 + summary | P1 | |
| API-027 | GET /api/reports | 1. GET with token | 200 + report data | P1 | |
| API-028 | GET /api/toc/constraints | 1. GET with token | 200 + constraints | P1 | |
| API-029 | GET /api/toc/buffer-health | 1. GET with token | 200 + buffer health | P1 | |
| API-030 | GET /api/tps/parameters | 1. GET with token | 200 + TPS parameters | P2 | |
| API-031 | GET /api/financials | 1. GET with token | 200 + financial entries | P1 | |
| API-032 | GET /api/purchaser | 1. GET with token | 200 + purchase orders | P1 | |
| API-033 | GET /api/firing-profiles | 1. GET with token | 200 + profiles | P2 | |
| API-034 | GET /api/kiln-maintenance | 1. GET with token | 200 + maintenance records | P2 | |
| API-035 | GET /api/kiln-inspections | 1. GET with token | 200 + inspections | P2 | |
| API-036 | GET /api/kiln-constants | 1. GET with token | 200 + constants | P2 | |
| API-037 | GET /api/kiln-loading-rules | 1. GET with token | 200 + rules | P2 | |
| API-038 | GET /api/kiln-firing-schedules | 1. GET with token | 200 + schedules | P2 | |
| API-039 | GET /api/dashboard-access | 1. GET with token | 200 + access records | P2 | |
| API-040 | GET /api/notification-preferences | 1. GET with token | 200 + preferences | P2 | |
| API-041 | GET /api/warehouse-sections | 1. GET with token | 200 + sections | P2 | |
| API-042 | GET /api/reconciliations | 1. GET with token | 200 + reconciliations | P2 | |
| API-043 | GET /api/qm-blocks | 1. GET with token | 200 + blocks | P2 | |
| API-044 | GET /api/problem-cards | 1. GET with token | 200 + cards | P2 | |
| API-045 | GET /api/security/audit-log | 1. GET with token | 200 + audit entries | P1 | |
| API-046 | GET /api/security/sessions | 1. GET with token | 200 + sessions | P2 | |
| API-047 | GET /api/finished-goods | 1. GET with token | 200 + finished goods | P1 | |
| API-048 | GET /api/grinding-stock | 1. GET with token | 200 + grinding items | P2 | |
| API-049 | GET /api/stages | 1. GET with token | 200 + stages | P2 | |
| API-050 | GET /api/sizes | 1. GET with token | 200 + sizes | P2 | |
| API-051 | GET /api/consumption-rules | 1. GET with token | 200 + rules | P2 | |
| API-052 | GET /api/packaging | 1. GET with token | 200 + box types | P2 | |
| API-053 | GET /api/material-groups/hierarchy | 1. GET with token | 200 + hierarchy | P2 | |
| API-054 | GET /api/stone-reservations | 1. GET with token | 200 + reservations | P2 | |
| API-055 | GET /api/factory-calendar | 1. GET with token | 200 + calendar | P2 | |
| API-056 | GET /api/settings | 1. GET with token | 200 + user settings | P2 | |
| API-057 | GET /api/admin-settings | 1. GET with token | 200 + admin settings | P2 | |
| API-058 | GET /api/guides | 1. GET with token | 200 + guide list | P3 | |
| API-059 | GET /api/packing-photos | 1. GET with token | 200 + photos | P2 | |
| API-060 | GET /api/export/materials/excel | 1. GET with token | 200 + Excel file download | P2 | |
| API-061 | GET /api/export/quality/excel | 1. GET with token | 200 + Excel file download | P2 | |
| API-062 | GET /api/export/orders/excel | 1. GET with token | 200 + Excel file download | P2 | |
| API-063 | GET /api/integration/health | 1. GET (integration auth) | 200 + integration status | P1 | |

---

## 7. Edge Cases

| ID | Description | Steps | Expected Result | Priority | Status |
|----|-------------|-------|-----------------|----------|--------|
| EDGE-001 | Empty database — dashboard loads | 1. Clear all orders 2. Load dashboard | Empty state UI, no errors/crashes | P0 | |
| EDGE-002 | Large order — 100+ positions | 1. Create order with 100 positions | No timeout, all positions created | P1 | |
| EDGE-003 | Concurrent status transitions | 1. Two users try to change same position status | One succeeds, other gets conflict error | P1 | |
| EDGE-004 | Expired access token + valid refresh | 1. Let access token expire 2. Make request | Auto-refreshes, request succeeds | P0 | |
| EDGE-005 | Both tokens expired | 1. Let both tokens expire 2. Make request | Redirect to login | P0 | |
| EDGE-006 | Delete material with existing transactions | 1. Try to delete material with transactions | Error: cannot delete, has transactions | P1 | |
| EDGE-007 | Delete kiln with active batch | 1. Try to delete kiln with in_progress batch | Error: cannot delete, active batch | P1 | |
| EDGE-008 | Zero-quantity position | 1. Create position with qty=0 | Validation error | P2 | |
| EDGE-009 | Negative material stock | 1. Consume more than available | Error or stock capped at 0 | P1 | |
| EDGE-010 | Unicode in order fields | 1. Create order with Cyrillic/Indonesian text | Data saved and displayed correctly | P2 | |
| EDGE-011 | Very long text fields | 1. Submit 10KB description | Accepted or truncated gracefully | P3 | |
| EDGE-012 | Rapid API calls (rate limiting) | 1. Send 100 requests in 1 second | Rate limiting kicks in (429) after threshold | P1 | |
| EDGE-013 | SQL injection attempt | 1. PUT order with SQL in name field | Input sanitized, no injection | P0 | |
| EDGE-014 | XSS attempt in text fields | 1. Save <script> tag in description | HTML escaped in frontend display | P0 | |
| EDGE-015 | File upload — oversized | 1. Upload 50MB file | Error: file too large | P2 | |
| EDGE-016 | File upload — wrong MIME type | 1. Upload .exe as photo | Error: invalid file type | P2 | |

---

## 8. Data Integrity

| ID | Description | Steps | Expected Result | Priority | Status |
|----|-------------|-------|-----------------|----------|--------|
| DI-001 | Audit log on login | 1. Login 2. Check audit log | login_success entry with IP, user_agent | P0 | |
| DI-002 | Audit log on failed login | 1. Bad login 2. Check audit log | login_failed entry | P1 | |
| DI-003 | Audit log on user create | 1. Create user 2. Check audit log | user_create entry | P1 | |
| DI-004 | Audit log on role change | 1. Change user role 2. Check audit log | role_change entry with old/new values | P1 | |
| DI-005 | Audit log on settings change | 1. Change admin settings 2. Check audit log | settings_change entry | P2 | |
| DI-006 | Audit log on data export | 1. Export materials Excel 2. Check audit log | data_export entry | P2 | |
| DI-007 | Cascading delete — order -> positions | 1. Delete order 2. Check positions | All positions deleted/cancelled | P1 | |
| DI-008 | Material transaction totals match stock | 1. Sum all transactions for material 2. Compare to stock | Numbers match exactly | P0 | |
| DI-009 | Position number sequential per order | 1. Create order with 5 positions | position_number = 1,2,3,4,5 | P2 | |
| DI-010 | Split index sequential per parent | 1. Split position into 3 2. Check split_index | split_index = 1,2,3 | P2 | |
| DI-011 | Reconciliation discrepancy detection | 1. Complete reconciliation with differences | Discrepancy flagged, notification sent | P1 | |
| DI-012 | Factory data isolation | 1. Login as PM for Factory A 2. Check data | Only Factory A data visible (where scoped) | P0 | |

---

## 9. UI/UX

| ID | Description | Steps | Expected Result | Priority | Status |
|----|-------------|-------|-----------------|----------|--------|
| UX-001 | Responsive — desktop (1280px+) | 1. Open at 1280px width | Full sidebar, content area | P1 | |
| UX-002 | Responsive — tablet (768px) | 1. Resize to 768px | Sidebar collapsed, content fills | P2 | |
| UX-003 | Sidebar collapse/expand | 1. Click sidebar toggle | Sidebar collapses to icon-only mode | P1 | |
| UX-004 | Error boundary — component crash | 1. Force error in page component | Error boundary catches, fallback UI shown | P1 | |
| UX-005 | Loading states — data fetch | 1. Slow network 2. Load page | Spinner shown during loading | P1 | |
| UX-006 | Empty states — no data | 1. Navigate to page with no data | Friendly empty state message | P2 | |
| UX-007 | Toast notifications | 1. Create entity 2. Check toast | Success toast appears and auto-dismisses | P2 | |
| UX-008 | Form validation — required fields | 1. Submit form with empty required fields | Validation errors shown inline | P1 | |
| UX-009 | Form validation — email format | 1. Enter invalid email | Format error shown | P2 | |
| UX-010 | Sidebar — correct items per role | 1. Login as each role 2. Check sidebar items | Only role-appropriate nav items shown | P0 | |
| UX-011 | Active nav highlight | 1. Navigate to page | Corresponding sidebar item highlighted | P3 | |
| UX-012 | Section collapse/expand (sidebar) | 1. Click section header | Section collapses/expands | P3 | |

---

## 10. Security

| ID | Description | Steps | Expected Result | Priority | Status |
|----|-------------|-------|-----------------|----------|--------|
| SEC-001 | Rate limiting on login | 1. Send 20 failed logins in 1 minute | Rate limited after threshold | P0 | |
| SEC-002 | CORS — only allowed origins | 1. Request from unauthorized origin | CORS error | P1 | |
| SEC-003 | JWT in httponly cookie | 1. Login 2. Inspect cookies | JWT cookie is httponly, secure, samesite | P0 | |
| SEC-004 | No sensitive data in URL params | 1. Check all API calls | No tokens/passwords in query strings | P1 | |
| SEC-005 | IP allowlist enforcement | 1. Add IP to allowlist 2. Request from other IP | Request blocked for admin_panel scope | P2 | |
| SEC-006 | Session management — list sessions | 1. GET /api/security/sessions | Active sessions listed with details | P2 | |
| SEC-007 | Session management — revoke session | 1. DELETE /api/security/sessions/{id} | Session revoked, can't use that token | P2 | |
| SEC-008 | TOTP backup codes | 1. Setup TOTP 2. Regenerate backup codes | New codes generated, old ones invalidated | P2 | |
| SEC-009 | Password not returned in API responses | 1. GET /api/users/{id} | No password_hash in response | P0 | |
| SEC-010 | Webhook HMAC verification | 1. Send webhook without valid HMAC | 403 Forbidden | P1 | |
| SEC-011 | File upload path traversal | 1. Upload file with ../../../etc/passwd name | Sanitized, no path traversal | P0 | |
| SEC-012 | Rate limit events logged | 1. Trigger rate limit 2. GET /api/security/rate-limit-events | Events logged | P2 | |
| SEC-013 | TOTP status check | 1. GET /api/security/totp/status | Returns whether TOTP is enabled | P3 | |
| SEC-014 | Audit log summary | 1. GET /api/security/audit-log/summary | Summary stats of audit events | P2 | |

---

## Execution Summary

| Section | Total Tests | P0 | P1 | P2 | P3 | Passed | Failed | Skipped |
|---------|------------|----|----|----|----|--------|--------|---------|
| 1. Auth & RBAC | 36 | 17 | 10 | 5 | 4 | | | |
| 2. Per-Role Pages | 40 | 13 | 18 | 6 | 3 | | | |
| 3. CRUD Operations | 59 | 16 | 27 | 16 | 0 | | | |
| 4. Business Logic | 21 | 4 | 10 | 7 | 0 | | | |
| 5. Telegram Bot | 18 | 3 | 10 | 4 | 1 | | | |
| 6. API Endpoints | 63 | 6 | 18 | 36 | 3 | | | |
| 7. Edge Cases | 16 | 4 | 5 | 5 | 2 | | | |
| 8. Data Integrity | 12 | 2 | 5 | 4 | 1 | | | |
| 9. UI/UX | 12 | 1 | 4 | 4 | 3 | | | |
| 10. Security | 14 | 4 | 3 | 5 | 2 | | | |
| **TOTAL** | **291** | **70** | **110** | **92** | **19** | | | |

---

## Notes

- Run smoke test script first: `python scripts/qa_api_smoke_test.py`
- Telegram bot tests require a test Telegram account linked to the system
- Edge case tests should be run in a staging environment
- Security tests (SQL injection, XSS, rate limiting) should NOT be run against production
- All P0 tests must pass before any release
- Audit log verification should be done after each CRUD section
