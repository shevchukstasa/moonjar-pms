# Moonjar PMS — Complete Frontend Pages

> Auto-extracted from 51 page files in `presentation/dashboard/src/pages/`
> Tech stack: React 18 + TypeScript + Vite + Tailwind + TanStack Query + Zustand
> Generated: 2026-03-26

---

## Route Map

### Owner (`/owner`)
| Route | Page | Roles |
|-------|------|-------|
| `/owner` | OwnerDashboard | owner |

### CEO (`/ceo`)
| Route | Page | Roles |
|-------|------|-------|
| `/ceo` | CeoDashboard | ceo, owner, administrator |
| `/ceo/employees` | CeoEmployeesPage | ceo, owner, administrator |

### Admin (`/admin`)
| Route | Page | Roles |
|-------|------|-------|
| `/admin` | AdminPanelPage | owner, administrator |
| `/admin/suppliers` | AdminSuppliersPage | owner, administrator |
| `/admin/collections` | AdminCollectionsPage | owner, administrator |
| `/admin/color-collections` | AdminColorCollectionsPage | owner, administrator |
| `/admin/colors` | AdminColorsPage | owner, administrator |
| `/admin/application-types` | AdminAppTypesPage | owner, administrator |
| `/admin/places-of-application` | AdminPoaPage | owner, administrator |
| `/admin/finishing-types` | AdminFinishingPage | owner, administrator |
| `/admin/materials` | AdminMaterialsPage | owner, administrator |
| `/admin/size-resolution/:taskId` | SizeResolutionPage | owner, administrator |
| `/admin/dashboard-access` | DashboardAccessPage | owner, administrator |
| `/admin/settings` | AdminSettingsPage | owner, administrator |
| `/admin/employees` | EmployeesPage | owner, administrator |
| `/admin/recipes` | AdminRecipesPage | owner, administrator, production_manager |
| `/admin/temperature-groups` | AdminTemperatureGroupsPage | owner, administrator, production_manager |
| `/admin/warehouses` | AdminWarehousesPage | owner, administrator, production_manager |
| `/admin/packaging` | AdminPackagingPage | owner, administrator, production_manager |
| `/admin/sizes` | AdminSizesPage | owner, administrator, production_manager |
| `/admin/consumption-rules` | ConsumptionRulesPage | owner, administrator, production_manager |
| `/admin/firing-profiles` | AdminFiringProfilesPage | owner, administrator, production_manager |
| `/admin/stages` | AdminStagesPage | owner, administrator, production_manager |
| `/admin/firing-schedules` | KilnFiringSchedulesPage | owner, administrator, production_manager |
| `/admin/factory-calendar` | FactoryCalendarPage | owner, administrator, production_manager |

### Manager (`/manager`)
| Route | Page | Roles |
|-------|------|-------|
| `/manager` | ManagerDashboard | production_manager, owner, administrator |
| `/manager/orders/:orderId` | OrderDetailPage | production_manager, owner, administrator |
| `/manager/orders/:orderId/shipment` | ShipmentPage | production_manager, owner, administrator |
| `/manager/schedule` | ManagerSchedulePage | production_manager, owner, administrator |
| `/manager/kilns` | ManagerKilnsPage | production_manager, owner, administrator |
| `/manager/materials` | ManagerMaterialsPage | production_manager, owner, administrator |
| `/manager/kiln-inspections` | KilnInspectionsPage | production_manager, owner, administrator |
| `/manager/kiln-maintenance` | KilnMaintenancePage | production_manager, owner, administrator |
| `/manager/grinding` | GrindingDecisionsPage | production_manager, owner, administrator |
| `/manager/shortage/:taskId` | ShortageDecisionPage | production_manager, owner, administrator |
| `/manager/size-resolution/:taskId` | SizeResolutionPage | production_manager, owner, administrator |
| `/manager/guide` | PMGuidePage | production_manager, owner, administrator |
| `/manager/staff` | EmployeesPage | production_manager, owner, administrator |

### Quality Manager (`/quality`)
| Route | Page | Roles |
|-------|------|-------|
| `/quality` | QualityManagerDashboard | quality_manager, owner, administrator |

### Warehouse (`/warehouse`)
| Route | Page | Roles |
|-------|------|-------|
| `/warehouse` | WarehouseDashboard | warehouse, owner, administrator, production_manager |
| `/warehouse/finished-goods` | FinishedGoodsPage | warehouse, owner, administrator, production_manager |
| `/warehouse/reconciliations` | ReconciliationsPage | warehouse, owner, administrator, production_manager |
| `/warehouse/mana-shipments` | ManaShipmentsPage | warehouse, owner, administrator, production_manager |

### Sorter/Packer (`/packing`)
| Route | Page | Roles |
|-------|------|-------|
| `/packing` | SorterPackerDashboard | sorter_packer, owner, administrator, production_manager |

### Purchaser (`/purchaser`)
| Route | Page | Roles |
|-------|------|-------|
| `/purchaser` | PurchaserDashboard | purchaser, owner, administrator, production_manager |

### Shared
| Route | Page | Roles |
|-------|------|-------|
| `/login` | LoginPage | public |
| `/settings` | SettingsPage | any authenticated |
| `/tablo` | TabloDashboard | any authenticated |
| `/users` | UsersPage | owner, administrator, ceo |
| `/reports` | ReportsPage | owner, ceo, production_manager |
| `*` | NotFoundPage | any |

---

## Page Details

### OwnerDashboard
- **Route:** `/owner`
- **Roles:** owner
- **Features:**
  - Factory comparison metrics across all factories
  - Financial summary (revenue, costs, margin)
  - Strategic KPIs (on-time delivery rate, defect rate, kiln utilization)
  - Activity feed with recent events
  - Monthly/quarterly trend charts
- **API endpoints:** `/api/analytics/factory-comparison`, `/api/analytics/dashboard-summary`, `/api/analytics/trend-data`, `/api/analytics/activity-feed`, `/api/financials/summary`

### CeoDashboard
- **Route:** `/ceo`
- **Roles:** ceo, owner, administrator
- **Features:**
  - Operational overview with order pipeline
  - Task management (assign tasks to PMs)
  - Production status by factory
  - Alert feed (anomalies, SLA breaches)
- **API endpoints:** `/api/analytics/dashboard-summary`, `/api/tasks`, `/api/orders`, `/api/analytics/anomalies`

### CeoEmployeesPage
- **Route:** `/ceo/employees`
- **Roles:** ceo, owner, administrator
- **Features:**
  - Employee directory across factories
  - Payroll summary view (monthly breakdown)
  - Attendance overview
  - Create/edit employees
- **API endpoints:** `/api/employees`, `/api/employees/payroll-summary`, `/api/employees/{id}/attendance`

### AdminPanelPage
- **Route:** `/admin`
- **Roles:** owner, administrator
- **Features:**
  - System overview: factory count, user count, health status
  - Telegram bot configuration (owner chat ID)
  - Quick links to all admin sub-pages
  - Seed data status
  - Factory management (create/edit factories)
- **API endpoints:** `/api/factories`, `/api/telegram/owner-chat`, `/api/health/seed-status`

### AdminSuppliersPage
- **Route:** `/admin/suppliers`
- **Roles:** owner, administrator
- **Features:**
  - CRUD for suppliers
  - Lead time tracking per material type
  - Rating system
  - Material type tagging
- **API endpoints:** `/api/suppliers`, `/api/suppliers/{id}/lead-times`

### AdminCollectionsPage
- **Route:** `/admin/collections`
- **Roles:** owner, administrator
- **Features:**
  - CRUD for product collections (New Collection, Classic, etc.)
- **API endpoints:** `/api/reference/collections`

### AdminColorCollectionsPage
- **Route:** `/admin/color-collections`
- **Roles:** owner, administrator
- **Features:**
  - CRUD for color collections (Season 2025/2026, etc.)
  - Active/inactive toggle
- **API endpoints:** `/api/reference/color-collections`

### AdminColorsPage
- **Route:** `/admin/colors`
- **Roles:** owner, administrator
- **Features:**
  - CRUD for colors with code and base/custom flag
- **API endpoints:** `/api/reference/colors`

### AdminAppTypesPage
- **Route:** `/admin/application-types`
- **Roles:** owner, administrator
- **Features:**
  - CRUD for application types (Wall, Floor, etc.)
- **API endpoints:** `/api/reference/application-types`

### AdminPoaPage (Places of Application)
- **Route:** `/admin/places-of-application`
- **Roles:** owner, administrator
- **Features:**
  - CRUD for places of application (Face Only, Face and Sides, etc.)
- **API endpoints:** `/api/reference/places-of-application`

### AdminFinishingPage
- **Route:** `/admin/finishing-types`
- **Roles:** owner, administrator
- **Features:**
  - CRUD for finishing types (Glossy, Matte, etc.)
- **API endpoints:** `/api/reference/finishing-types`

### AdminMaterialsPage
- **Route:** `/admin/materials`
- **Roles:** owner, administrator
- **Features:**
  - Full material catalog management
  - Group/subgroup hierarchy management
  - Stock levels per factory
  - Duplicate detection and merge
  - CSV/Excel export
  - Bulk operations (ensure stocks, cleanup duplicates)
- **API endpoints:** `/api/materials`, `/api/material-groups/hierarchy`, `/api/materials/duplicates`, `/api/materials/merge`, `/api/sizes`

### AdminRecipesPage
- **Route:** `/admin/recipes`
- **Roles:** owner, administrator, production_manager
- **Features:**
  - Recipe CRUD with BOM (bill of materials)
  - Color collection grouping
  - Kiln config (temperature, duration, two-stage)
  - Multi-firing stages (Gold workflow)
  - CSV import for bulk recipe creation
  - Bulk delete
  - Material assignment per recipe
  - Temperature group linking
- **API endpoints:** `/api/recipes`, `/api/recipes/{id}/materials`, `/api/recipes/{id}/firing-stages`, `/api/recipes/import-csv`, `/api/materials`, `/api/reference/color-collections`, `/api/reference/temperature-groups`

### AdminTemperatureGroupsPage
- **Route:** `/admin/temperature-groups`
- **Roles:** owner, administrator, production_manager
- **Features:**
  - Create/edit temperature groups (Low Temp, High Temp)
  - Link recipes to temperature groups
  - Set default recipe per group
- **API endpoints:** `/api/reference/temperature-groups`, `/api/reference/temperature-groups/{id}/recipes`

### AdminWarehousesPage
- **Route:** `/admin/warehouses`
- **Roles:** owner, administrator, production_manager
- **Features:**
  - Warehouse section management (raw materials, finished goods, etc.)
  - Assign manager per section
  - Display order configuration
- **API endpoints:** `/api/warehouse-sections`, `/api/warehouse-sections/all`

### AdminPackagingPage
- **Route:** `/admin/packaging`
- **Roles:** owner, administrator, production_manager
- **Features:**
  - Box type management (linked to packaging materials)
  - Capacity per tile size (pieces per box)
  - Spacer rules per box type + size
- **API endpoints:** `/api/packaging`, `/api/packaging/{id}/capacities`, `/api/packaging/{id}/spacers`, `/api/packaging/sizes`

### AdminSizesPage
- **Route:** `/admin/sizes`
- **Roles:** owner, administrator, production_manager
- **Features:**
  - Tile size catalog (name, width, height, thickness, shape)
  - Auto-calculated glazing board specs
  - Custom size flag
  - Recalculate all boards button
- **API endpoints:** `/api/sizes`, `/api/sizes/{id}/glazing-board`, `/api/sizes/recalculate-all-boards`

### ConsumptionRulesPage
- **Route:** `/admin/consumption-rules`
- **Roles:** owner, administrator, production_manager
- **Features:**
  - Define glaze/engobe consumption rules per product configuration
  - Match criteria: collection, size, shape, thickness, product type, place of application
  - Consumption rate (ml/sqm), coats, specific gravity override
  - Priority-based rule matching
- **API endpoints:** `/api/consumption-rules`, `/api/reference/all`, `/api/reference/application-methods`, `/api/reference/collections`

### AdminFiringProfilesPage
- **Route:** `/admin/firing-profiles`
- **Roles:** owner, administrator, production_manager
- **Features:**
  - Universal firing profiles (temperature curves)
  - Link to temperature groups
  - Product type / collection / thickness matching
  - Priority-based auto-matching
  - Temperature stage editor (ramp segments)
- **API endpoints:** `/api/firing-profiles`, `/api/reference/temperature-groups`

### AdminStagesPage
- **Route:** `/admin/stages`
- **Roles:** owner, administrator, production_manager
- **Features:**
  - Production stage definitions with sequence order
- **API endpoints:** `/api/stages`

### KilnFiringSchedulesPage
- **Route:** `/admin/firing-schedules`
- **Roles:** owner, administrator, production_manager
- **Features:**
  - Per-kiln firing schedules (named temperature curves)
  - Default schedule per kiln
  - JSON schedule data editor
- **API endpoints:** `/api/kiln-firing-schedules`, `/api/kilns`

### FactoryCalendarPage
- **Route:** `/admin/factory-calendar`
- **Roles:** owner, administrator, production_manager
- **Features:**
  - Calendar view of working/non-working days per factory
  - Holiday management (government, Balinese, manual)
  - Bulk create holidays
  - Working days count for period
- **API endpoints:** `/api/factory-calendar`, `/api/factory-calendar/working-days`, `/api/factory-calendar/bulk`

### AdminSettingsPage
- **Route:** `/admin/settings`
- **Roles:** owner, administrator
- **Features:**
  - Escalation rules per task type per factory
  - Receiving approval settings (all vs auto)
  - Material defect thresholds
  - Purchase consolidation settings (window, urgency, horizon)
- **API endpoints:** `/api/admin-settings/escalation-rules`, `/api/admin-settings/receiving-settings`, `/api/admin-settings/defect-thresholds`, `/api/admin-settings/consolidation-settings`, `/api/factories`

### DashboardAccessPage
- **Route:** `/admin/dashboard-access`
- **Roles:** owner, administrator
- **Features:**
  - Grant users access to additional dashboards beyond their role default
  - User selection with role filter
  - Dashboard type selection
- **API endpoints:** `/api/dashboard-access`, `/api/users`

### ManagerDashboard
- **Route:** `/manager`
- **Roles:** production_manager, owner, administrator
- **Features:**
  - Production overview: orders pipeline by status
  - Kiln schedule (today/tomorrow)
  - Task board (blocking tasks, pending tasks)
  - Material alerts (low stock, pending purchases)
  - TPS metrics widget (OEE, signal)
  - TOC buffer health indicators
  - Defect summary
  - AI chat assistant
  - Order list with search/filter/sort
  - Quick actions: create order, form batch, reschedule
- **API endpoints:** `/api/analytics/dashboard-summary`, `/api/orders`, `/api/tasks`, `/api/materials/low-stock`, `/api/tps/dashboard-summary`, `/api/toc/buffer-health`, `/api/defects`, `/api/ai-chat/chat`, `/api/batches/auto-form`

### OrderDetailPage
- **Route:** `/manager/orders/:orderId`
- **Roles:** production_manager, owner, administrator
- **Features:**
  - Full order view with all positions
  - Position status board with drag-and-drop
  - Position details: recipe, schedule, materials, QC
  - Status transition buttons
  - Sorting/splitting interface
  - Reprocess order (re-run intake pipeline)
  - Reschedule order
  - Ship order
  - Cancellation management
  - Change request review
- **API endpoints:** `/api/orders/{id}`, `/api/positions`, `/api/positions/{id}/status`, `/api/positions/{id}/split`, `/api/orders/{id}/reprocess`, `/api/orders/{id}/reschedule`

### ShipmentPage
- **Route:** `/manager/orders/:orderId/shipment`
- **Roles:** production_manager, owner, administrator
- **Features:**
  - Create shipment for order
  - Add positions to shipment
  - Set tracking, carrier, shipping method
  - Ship and deliver actions
- **API endpoints:** `/api/shipments`, `/api/shipments/{id}/ship`, `/api/shipments/{id}/deliver`

### ManagerSchedulePage
- **Route:** `/manager/schedule`
- **Roles:** production_manager, owner, administrator
- **Features:**
  - Calendar view of kiln schedule
  - Gantt-style timeline per kiln
  - Glazing, firing, sorting schedule tabs
  - Drag to reschedule batches
  - Batch details popup
  - Factory filter
- **API endpoints:** `/api/schedule/kiln-schedule`, `/api/schedule/glazing-schedule`, `/api/schedule/firing-schedule`, `/api/schedule/sorting-schedule`, `/api/schedule/resources`

### ManagerKilnsPage
- **Route:** `/manager/kilns`
- **Roles:** production_manager, owner, administrator
- **Features:**
  - Kiln cards with status, capacity, equipment specs
  - Create/edit kilns
  - Kiln dimensions editor
  - Status change (active/maintenance)
  - Breakdown/restore actions
  - Loading rules configuration
  - Rotation rules per kiln
- **API endpoints:** `/api/kilns`, `/api/kilns/{id}`, `/api/kilns/{id}/breakdown`, `/api/kilns/{id}/restore`, `/api/kiln-loading-rules`

### ManagerMaterialsPage
- **Route:** `/manager/materials`
- **Roles:** production_manager, owner, administrator
- **Features:**
  - Material stock overview with factory filter
  - Low stock alerts
  - Transaction history per material
  - Create transactions (receive, write-off)
  - Consumption adjustment review
  - Purchase request management
- **API endpoints:** `/api/materials`, `/api/materials/low-stock`, `/api/materials/{id}/transactions`, `/api/materials/transactions`, `/api/materials/consumption-adjustments`

### KilnInspectionsPage
- **Route:** `/manager/kiln-inspections`
- **Roles:** production_manager, owner, administrator
- **Features:**
  - Inspection history per kiln
  - Create new inspection (checklist form)
  - Inspection result matrix (kilns x dates)
  - Repair log management
  - Issue tracking from inspection to repair
- **API endpoints:** `/api/kiln-inspections`, `/api/kiln-inspections/items`, `/api/kiln-inspections/repairs`, `/api/kiln-inspections/matrix`

### KilnMaintenancePage
- **Route:** `/manager/kiln-maintenance`
- **Roles:** production_manager, owner, administrator
- **Features:**
  - Maintenance schedule per kiln
  - Maintenance types management
  - Schedule new maintenance (with material requirements)
  - Complete maintenance
  - Upcoming maintenance view
  - Overdue maintenance alerts
- **API endpoints:** `/api/kiln-maintenance`, `/api/kiln-maintenance/types`, `/api/kiln-maintenance/kilns/{id}`, `/api/kiln-maintenance/upcoming`

### GrindingDecisionsPage
- **Route:** `/manager/grinding`
- **Roles:** production_manager, owner, administrator
- **Features:**
  - Grinding stock inventory
  - Decide disposition: grind, discard, reuse in another order
  - Statistics (total in stock, decided, pending)
- **API endpoints:** `/api/grinding-stock`, `/api/grinding-stock/stats`, `/api/grinding-stock/{id}/decide`

### ShortageDecisionPage
- **Route:** `/manager/shortage/:taskId`
- **Roles:** production_manager, owner, administrator
- **Features:**
  - Material shortage task resolution
  - Options: wait for delivery, find alternative material, accept shortage, force proceed
  - Shows affected positions and timeline impact
- **API endpoints:** `/api/tasks/{id}`, `/api/tasks/{id}/resolve-shortage`

### SizeResolutionPage
- **Route:** `/manager/size-resolution/:taskId` or `/admin/size-resolution/:taskId`
- **Roles:** production_manager, owner, administrator
- **Features:**
  - Size confirmation task resolution
  - Match to existing size from catalog
  - Create new custom size
  - Shows glazing board calculation preview
- **API endpoints:** `/api/tasks/{id}`, `/api/tasks/{id}/resolve-size`, `/api/sizes`, `/api/sizes/{id}/glazing-board`

### PMGuidePage
- **Route:** `/manager/guide`
- **Roles:** production_manager, owner, administrator
- **Features:**
  - Interactive production manager guide
  - Markdown-rendered content by language (EN/RU/ID)
  - Role-specific guide selection
- **API endpoints:** `/api/guides/{role}/{language}`, `/api/guides`

### EmployeesPage
- **Route:** `/admin/employees` or `/manager/staff`
- **Roles:** owner, administrator, production_manager
- **Features:**
  - Employee CRUD (full name, position, salary, allowances)
  - Attendance tracking (present/absent/sick/leave)
  - Payroll summary calculation (gross, deductions, net)
  - BPJS contributions breakdown
  - Factory calendar integration for working days
  - Overtime tracking
- **API endpoints:** `/api/employees`, `/api/employees/payroll-summary`, `/api/employees/{id}/attendance`, `/api/factory-calendar`, `/api/factory-calendar/working-days`

### QualityManagerDashboard
- **Route:** `/quality`
- **Roles:** quality_manager, owner, administrator
- **Features:**
  - Quality calendar matrix (dates x kilns with defect indicators)
  - Defect cause management
  - Quality inspections list and creation
  - Photo upload and AI analysis
  - Pre-kiln and final check checklists
  - QM block/unblock actions
  - Problem card management
  - Defect statistics
- **API endpoints:** `/api/quality/calendar-matrix`, `/api/quality/defect-causes`, `/api/quality/inspections`, `/api/quality/analyze-photo`, `/api/quality/checklist-items`, `/api/quality/pre-kiln-check`, `/api/quality/final-check`, `/api/quality/stats`, `/api/qm-blocks`, `/api/problem-cards`

### WarehouseDashboard
- **Route:** `/warehouse`
- **Roles:** warehouse, owner, administrator, production_manager
- **Features:**
  - Material stock overview by warehouse section
  - Receive materials (with approval flow)
  - Transaction history
  - Low stock alerts
  - Pending receipts requiring approval
- **API endpoints:** `/api/materials`, `/api/materials/transactions`, `/api/warehouse-sections`

### FinishedGoodsPage
- **Route:** `/warehouse/finished-goods`
- **Roles:** warehouse, owner, administrator, production_manager
- **Features:**
  - Finished goods inventory by color/size/collection
  - Add/edit stock entries
  - Availability check (reserved vs available)
- **API endpoints:** `/api/finished-goods`, `/api/finished-goods/availability`

### ReconciliationsPage
- **Route:** `/warehouse/reconciliations`
- **Roles:** warehouse, owner, administrator, production_manager
- **Features:**
  - Inventory reconciliation workflow
  - Start reconciliation session
  - Scan/enter actual quantities per material
  - System vs actual comparison with difference
  - Complete reconciliation (apply adjustments)
  - Explanation recording per discrepancy
- **API endpoints:** `/api/reconciliations`, `/api/reconciliations/{id}/items`, `/api/reconciliations/{id}/complete`, `/api/materials`

### ManaShipmentsPage
- **Route:** `/warehouse/mana-shipments`
- **Roles:** warehouse, owner, administrator, production_manager
- **Features:**
  - Internal transfers to Mana showroom
  - Confirm and ship workflow
  - Items list per shipment
- **API endpoints:** `/api/mana-shipments`, `/api/mana-shipments/{id}/confirm`, `/api/mana-shipments/{id}/ship`

### SorterPackerDashboard
- **Route:** `/packing`
- **Roles:** sorter_packer, owner, administrator, production_manager
- **Features:**
  - Positions ready for sorting/packing
  - Sorting interface (split by outcome)
  - Packing photo upload
  - Box count calculator
  - Task list for packing-related tasks
- **API endpoints:** `/api/positions` (status filter), `/api/positions/{id}/split`, `/api/packing-photos`, `/api/tasks`

### PurchaserDashboard
- **Route:** `/purchaser`
- **Roles:** purchaser, owner, administrator, production_manager
- **Features:**
  - Purchase request list with status pipeline
  - Stats: pending count, overdue, avg lead time
  - Upcoming deliveries
  - Material deficits requiring purchase
  - Consolidation suggestions
  - Lead time comparison (expected vs actual per supplier)
  - Full PR lifecycle (create -> approve -> send -> track -> receive)
- **API endpoints:** `/api/purchaser`, `/api/purchaser/stats`, `/api/purchaser/deliveries`, `/api/purchaser/deficits`, `/api/purchaser/consolidation-suggestions`, `/api/purchaser/lead-times`, `/api/purchaser/{id}/status`

### TabloDashboard
- **Route:** `/tablo`
- **Roles:** any authenticated
- **Features:**
  - Factory floor display (large screen mode)
  - Real-time production status
  - Kiln status indicators
  - Today's production numbers
- **API endpoints:** `/api/analytics/dashboard-summary`, `/api/schedule/kiln-schedule`

### UsersPage
- **Route:** `/users`
- **Roles:** owner, administrator, ceo
- **Features:**
  - User management CRUD
  - Role assignment (10 roles)
  - Factory assignment
  - Activate/deactivate users
- **API endpoints:** `/api/users`, `/api/factories`

### ReportsPage
- **Route:** `/reports`
- **Roles:** owner, ceo, production_manager
- **Features:**
  - Orders summary report (by status, factory, period)
  - Kiln loading report (utilization)
  - Export to Excel/PDF
- **API endpoints:** `/api/reports`, `/api/reports/orders-summary`, `/api/reports/kiln-load`, `/api/factories`

### SettingsPage
- **Route:** `/settings`
- **Roles:** any authenticated
- **Features:**
  - User profile settings (name, email)
  - Language preference (EN/RU/ID)
  - Notification preferences
  - Change password
  - TOTP 2FA setup
  - Active sessions management
- **API endpoints:** `/api/auth/me`, `/api/auth/change-password`, `/api/notification-preferences`, `/api/security/totp/*`, `/api/security/sessions`

### LoginPage
- **Route:** `/login`
- **Roles:** public
- **Features:**
  - Email + password login
  - Google OAuth login
  - TOTP 2FA verification (if enabled)
  - Auto-redirect based on role after login
- **API endpoints:** `/api/auth/login`, `/api/auth/google`, `/api/auth/totp-verify`
