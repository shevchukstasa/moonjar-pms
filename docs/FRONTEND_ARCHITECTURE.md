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

## Routing (additions)

| Path | Component | Role Guard |
|------|-----------|------------|
| `/kiln-inspections` | `KilnInspectionsPage` | `production_manager` |
