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

## Routing (additions)

| Path | Component | Role Guard |
|------|-----------|------------|
| `/kiln-inspections` | `KilnInspectionsPage` | `production_manager` |
