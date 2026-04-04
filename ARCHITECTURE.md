# Moonjar PMS — Architecture Overview

> Production Management System for stone products manufacturer.
> Multi-factory (Bali, Java), TOC/DBR scheduling, 8+ user roles.

---

## Tech Stack
- **Backend:** FastAPI, SQLAlchemy, PostgreSQL, APScheduler
- **Frontend:** React 18, Vite, TypeScript, Tailwind, TanStack Query, Zustand
- **Auth:** Google OAuth + email/password, JWT (access 1h + refresh 7d)
- **Deployment:** Railway (Nixpacks), auto-deploy on push to `main`

## User Roles
owner, administrator, ceo, production_manager, quality_manager, warehouse, sorter_packer, purchaser, master, senior_master

---

## Recent Feature Additions

### Kiln Inspection & Repair Log System
Structured checklist-based inspection workflow for kilns. PM performs periodic inspections using 35 seed checklist items across 8 categories (Frame & Stability, Door, Interior, Heating Elements, Thermocouple, Electrical, etc.). Each item is rated ok/not_applicable/damaged/needs_repair. Issues feed into a repair log with status tracking (open -> in_progress -> done).

- **Backend:** 4 new tables (`kiln_inspection_items`, `kiln_inspections`, `kiln_inspection_results`, `kiln_repair_logs`), 9 API endpoints under `/api/kiln-inspections`, schema patch with seed data.
- **Frontend:** `KilnInspectionsPage` with 3 tabs (Inspections, Repair Log, New Inspection). Matrix view for spreadsheet-like overview.
- **Access:** Sidebar link visible to `production_manager` only.

### Consumption Measurement Auto-Detection
When an order is processed, the system checks if the recipe has the consumption rates required by the position's application method (spray/brush). If rates are missing, the position is automatically blocked (`awaiting_consumption_data` status) and a `consumption_measurement` task is created for PM.

- **New enum values:** `PositionStatus.AWAITING_CONSUMPTION_DATA`, `TaskType.CONSUMPTION_MEASUREMENT`
- **Method mapping:** Each application method code (SS, S, BS, SB, Gold, etc.) maps to required consumption rate types (spray and/or brush).
- **Resolution:** PM enters measured rates via `POST /tasks/{id}/resolve-consumption`, which updates the recipe, unblocks the position, and triggers material reservation.
- **Integration point:** `business/services/order_intake.py` -> `_check_consumption_rates()`

### UI Refinements
- Sidebar font sizes increased ~30% (header text-2xl, section labels 13px, nav items text-base)
- BlockingTasksTab updated to handle `awaiting_consumption_data` status

---

## Production Resource Tracking (April 2026)

### Kiln Shelves Asset System
Individual tracking of fire-resistant kiln shelves (silicon carbide, cordierite, mullite, alumina). Each shelf is a first-class asset with a full lifecycle: **purchase → active → damaged → written_off**.

- **Data model:** `kiln_shelves` table with `resource_id` FK linking each shelf to a specific kiln. Area is a computed column (`area_sqm GENERATED ALWAYS AS width_m * depth_m`).
- **Material types:** `silicon_carbide`, `cordierite`, `mullite`, `alumina` — each with configurable `max_firing_cycles` threshold.
- **Firing cycle counter:** Incremented per firing batch. When a shelf exceeds `max_firing_cycles` for its material type, the system flags it for replacement review.
- **Write-off flow:** Mandatory `reason` field + optional photo evidence URL. On write-off:
  - Auto-creates an **OPEX financial entry** (cost attribution to the kiln's factory).
  - Auto-creates a **PM task** when remaining active shelves for a kiln fall below a critical threshold.
- **Access:** `production_manager` manages shelves; `ceo` views analytics.

### Zone-Based Kiln Scheduling
Kiln capacity is split into independent loading zones to prevent cross-zone overflow and enable more accurate batch planning.

- **Zones:** `edge`, `flat`, `filler` — each zone has its own capacity limit within a kiln.
- **Position classification:** Determined by `place_of_application` + physical `size` of the product. Positions are assigned to the appropriate zone before batch scheduling runs.
- **Independent zone checks:** The scheduler validates capacity per zone independently; exceeding one zone does not borrow from another.
- **Backward compatibility:** Legacy single-capacity kilns use a `primary` zone that maps to the full kiln volume, requiring no migration of existing data.

### Production Line Resource Constraints
Physical resources on the production floor (work tables, drying racks, glazing boards) now act as scheduling constraints alongside kiln capacity.

- **Resource types:** `work_table`, `drying_rack`, `glazing_board` — tracked with current counts and availability per factory.
- **Stage-to-resource mapping:** Defined in `_STAGE_RESOURCE_MAP`; each production stage declares which resource type it requires and how many units per position.
- **Duration formula:** `stage_days = max(speed_days, constraint_days)` — the stage takes whichever is longer: the recipe's ideal speed or the time imposed by resource scarcity.
- **GlazingBoardSpec integration:** For tile positions, tiles-per-board is calculated from board dimensions and tile size. Board deficit triggers automatic PM task creation when insufficient boards are available for the planned batch.
- **Board deficit auto-detection:** Runs during scheduling; creates a blocking `Task` linked to the affected positions with type `resource_shortage`.

### CEO OPEX Analytics
Dedicated analytics endpoint for executive visibility into production resource costs and replacement planning.

- **Shelf lifecycle analytics:** `GET /analytics/shelves/{factory_id}` — returns per-kiln and per-material breakdowns.
- **KPIs returned:**
  - Active shelf count (by material type)
  - Average lifespan (firing cycles before write-off)
  - Cost per cycle (write-off cost / total cycles at write-off)
  - Total investment (cumulative purchase cost of all shelves)
- **Projected replacements:** 30-day and 90-day forecasts based on current cycle counts vs. max thresholds.
- **Monthly OPEX trend:** Aggregated from write-off financial entries, broken down by month and factory.
- **Material-level breakdown:** Drill-down by shelf material type for cost comparison and procurement planning.

---

## Documentation Index
- `docs/DATABASE_SCHEMA.sql` — Table definitions and enum references
- `docs/API_CONTRACTS.md` — Endpoint specifications with schemas
- `docs/BUSINESS_LOGIC.md` — Algorithms and decision flows
- `docs/FRONTEND_ARCHITECTURE.md` — Component tree, routing, UI patterns
- `docs/guides/` — Role-specific user guides (PM, QM, Sorter/Packer)
- `docs/plans/` — Feature plans (Edge Profiles, Kiln Calculator)
- `docs/migrations/` — SQL migration scripts
