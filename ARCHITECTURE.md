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

## Documentation Index
- `docs/DATABASE_SCHEMA.sql` — Table definitions and enum references
- `docs/API_CONTRACTS.md` — Endpoint specifications with schemas
- `docs/BUSINESS_LOGIC.md` — Algorithms and decision flows
- `docs/FRONTEND_ARCHITECTURE.md` — Component tree, routing, UI patterns
- `docs/guides/` — Role-specific user guides (PM, QM, Sorter/Packer)
- `docs/plans/` — Feature plans (Edge Profiles, Kiln Calculator)
- `docs/migrations/` — SQL migration scripts
