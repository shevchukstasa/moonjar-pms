# Moonjar PMS — Frontend Architecture

> Component tree, routing, and UI patterns for the React dashboard.

---

## Sidebar Navigation

The sidebar (`Sidebar.tsx`) renders role-based navigation links. Recent styling changes:
- Header: `text-2xl` font size
- Section labels: `13px`
- Nav items: `text-base` (~30% increase from previous sizing)

### Kiln Inspections Link (NEW)
- **Visible to:** `production_manager` role only (NOT owner, CEO, or other roles)
- **Route:** `/kiln-inspections`
- **Section:** Production Management tools

---

## Pages

### KilnInspectionsPage (NEW)

**File:** `src/pages/KilnInspectionsPage.tsx`
**Route:** `/kiln-inspections`
**Access:** `production_manager`

Three-tab layout:

| Tab | Label | Content |
|-----|-------|---------|
| `inspections` | Inspections | List of past inspections with summary badges (ok/issues/n-a counts). Filters by factory, kiln, date range. |
| `repairs` | Repair Log | List of repair log entries. Filters by kiln, status (open/in_progress/done). Create/edit repair entries. |
| `new` | + New Inspection | Form to create a new inspection. Selects kiln, date, then shows full checklist grouped by category. Each item gets ok/n-a/damaged/needs_repair radio. |

**Result badge colors:**
- OK: green (`bg-green-100 text-green-700`)
- N/A: gray (`bg-gray-100 text-gray-500`)
- Damaged: red (`bg-red-100 text-red-700`)
- Needs Repair: orange (`bg-orange-100 text-orange-700`)

**API client:** `src/api/kilnInspections.ts`

### BlockingTasksTab Updates (NEW)
- Now handles `awaiting_consumption_data` position status
- Shows consumption measurement tasks with resolve action

---

### QualityCheckDialog (UPDATED — Session 2)

**File:** `src/components/QualityCheckDialog.tsx`

Wired to two pages:
- **ManagerSchedulePage** — QC tab: PM can trigger pre-kiln or final QC from the schedule view
- **QualityManagerDashboard** — Quality manager's primary workflow for reviewing and completing QC checklists

### BatchGroup (UPDATED — Session 2)

**File:** `src/components/BatchGroup.tsx`

Wired to **TabloDashboard** (Firing tab). Displays batch grouping for kiln firing view — groups positions by batch with summary of items, fill %, and firing profile.

### DatePicker (NOTE — Session 2)

**File:** `src/components/DatePicker.tsx`

Component exists but is currently **unused**. All pages use native `<input type="date">` instead. Candidate for removal in dead code cleanup.

---

## Smart Force Unblock Dialog (NEW — April 1-2, 2026)

**Trigger:** PM clicks "Force Unblock" on a blocked position.

Instead of a generic confirmation, the dialog now presents **3 context-aware options** based on the blocking type:

- For `INSUFFICIENT_MATERIALS`: Proceed with available / Wait for delivery / Substitute material
- For `AWAITING_RECIPE`: Use closest match / Create temporary / Skip glazing
- For `AWAITING_STENCIL_SILKSCREEN`: Proceed without / Use alternative / Delay
- For `AWAITING_COLOR_MATCHING`: Accept current / Re-match / Use standard
- For `AWAITING_CONSUMPTION_DATA`: Use defaults / Measure now / Copy from similar

Selection triggers `POST /positions/{id}/force-unblock` with the chosen option and sends CEO Telegram notification.

---

## Morning Briefing v2 — Telegram Format (NEW — April 1-2, 2026)

The bot sends a daily morning briefing with 7 blocks (greeting, yesterday summary, today's plan, blocking issues, achievements, challenge, action buttons).

### 6 Inline Buttons
Rendered as Telegram inline keyboard below the briefing message:

| Button | Callback Action |
|--------|----------------|
| Start Day | Confirms attendance, starts shift timer |
| Details | Shows expanded schedule for today |
| Problem | Opens problem report flow |
| Stats | Shows personal statistics |
| Leaders | Shows current leaderboard |
| Stock | Shows low stock materials |

---

## Routing (additions)

| Path | Component | Role Guard |
|------|-----------|------------|
| `/kiln-inspections` | `KilnInspectionsPage` | `production_manager` |

---

## New Components (April 2026)

### KilnShelvesSection (`components/kilns/KilnShelvesSection.tsx`)

**Embedded in:** `ManagerKilnsPage` — between kiln grid and constants table
**Props:** `{ factoryId: string, kilns: KilnItem[] }`

**Features:**
- Shelves grouped by kiln with area stats and count
- CycleBar progress bars (green <70%, yellow 70-90%, red 90%+)
- Filter by kiln + toggle written-off visibility
- Visual alerts for nearing end-of-life (80%+ cycles)

**Dialogs:**

| Dialog | Purpose | Key Fields |
|--------|---------|------------|
| `CreateShelfDialog` | Add new shelf | Kiln select, dimensions, material (auto-sets max cycles), auto-naming |
| `EditShelfDialog` | Modify shelf | All fields + kiln reassignment (move shelf between kilns) |
| `WriteOffDialog` | Retire shelf | Mandatory reason + optional photo URL, shows remaining count |

---

### ShelfOpexCard (`pages/CeoDashboard.tsx`)

**Embedded in:** CEO Dashboard "Kilns & Schedule" tab
**Data source:** `kilnShelvesApi.analytics()` endpoint

**Displays:**
- 4 KPI cards: active shelves, avg lifespan, cost/cycle, total investment
- Projected replacements alert (30/90 day forecast)
- Nearing end-of-life list with progress bars
- By-material breakdown grid
- Monthly write-off cost bar chart (6 months)

---

### LineResourcesSection (`pages/ManagerDashboard.tsx`)

**Embedded in:** TPS tab in ManagerDashboard
**Data source:** `lineResourcesApi` for CRUD operations

**Features:**
- Inline add forms per resource type card (`work_table`, `drying_rack`, `glazing_board`)
- Contextual field labels and hints per resource type

---

### API Module Updates (`api/tpsDashboard.ts`)

**New interfaces:**
- `KilnShelfItem` — shelf entity with dimensions, material, cycle count, status
- `KilnShelfCreate` — creation payload
- `ShelfAnalytics` — aggregated analytics response

**New API clients:**

| Client | Methods |
|--------|---------|
| `kilnShelvesApi` | `list`, `create`, `update`, `writeOff`, `incrementCycles`, `analytics` |
| `lineResourcesApi` | `list`, `create`, `update`, `remove` |

**New constants:**
- `SHELF_MATERIALS` — material options with `defaultCycles` per material type
- `LINE_RESOURCE_TYPES` — resource type definitions (`work_table`, `drying_rack`, `glazing_board`)
