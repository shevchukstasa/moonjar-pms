# Production Manager (PM) Guide -- Moonjar PMS

> Version: 1.0 | Date: 2026-03-20
> Moonjar Production Management System

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Dashboard Overview](#2-dashboard-overview)
3. [Materials Management](#3-materials-management)
4. [Orders and Positions](#4-orders-and-positions)
5. [Tasks](#5-tasks)
6. [Consumption Rules](#6-consumption-rules)
7. [Schedule Management](#7-schedule-management)
8. [Kiln Inspections](#8-kiln-inspections)
9. [Consumption Measurement Tasks](#9-consumption-measurement-tasks)
10. [Tips and Best Practices](#10-tips-and-best-practices)

---

## 1. Getting Started

### 1.1. Logging In

1. Open the Moonjar PMS dashboard in your browser.
2. Sign in using one of the available methods:
   - **Google OAuth** -- click "Sign in with Google"
   - **Email and password** -- enter your credentials and click "Login"
3. After authentication, the system detects your role and redirects you to `/manager` -- the PM dashboard.

### 1.2. Factory Auto-Selection

When you log in, the system checks which factories you are assigned to:

- **One factory assigned**: The factory is selected automatically. You will not see a factory dropdown -- all data is already filtered to your factory.
- **Multiple factories assigned**: A **Factory Selector** dropdown appears in the top-right corner of every page. Select the factory you want to work with.

> **Important**: Many operations (creating orders, auto-forming batches, receiving materials) require a specific factory to be selected. If you see "Select a factory first," choose one from the dropdown.

### 1.3. Navigation

As a Production Manager, you have access to the following pages:

| Page | URL | Purpose |
|---|---|---|
| PM Dashboard | `/manager` | Main control panel with tabs for orders, tasks, materials, defects, and more |
| Schedule | `/manager/schedule` | Production schedule by section (Glazing, Firing, Sorting, QC, Kilns) |
| Kilns | `/manager/kilns` | Kiln management, maintenance, loading rules |
| Materials | `/manager/materials` | Material inventory, receiving, audit, transaction history |
| Consumption Rules | `/consumption-rules` | Glaze/engobe consumption rates per square meter |
| Order Details | `/orders/:id` | Detailed view of a specific order and its positions |

The top navigation bar also includes:

- **NotificationsBell** -- shows unread notifications (new orders, kiln breakdowns, low stock alerts, sales requests)
- **Factory Selector** -- switch between factories (only visible if you have access to multiple factories)

---

## 2. Dashboard Overview

The PM Dashboard (`/manager`) is your command center. It is organized as a tabbed interface with the following sections.

### 2.1. Orders Tab

The default tab. Shows all production orders for the selected factory.

**Sub-tabs**: Current / Archive

**Filters**:
- Search by order number or client name
- Filter by status: New, In Production, Partially Ready, Ready for Shipment, Cancelled

**Actions available**:
- **Create Order** -- manually create a new production order
- **Upload PDF** -- upload a PDF order file for AI-powered parsing
- Click any order row to open its detail page

**KPI cards** at the top show:
- Total orders, orders in production, orders ready for shipment

### 2.2. Tasks Tab

Lists all tasks assigned to you or your team. Tasks are sorted by priority (highest first), then by creation date.

**Filters**: by status (pending, in_progress, done, cancelled), by task type, by assigned role.

Blocking tasks are visually highlighted -- these prevent positions from advancing through production.

### 2.3. Materials Tab

A summary of material status:

- **Low Stock** alerts -- materials with balance below their minimum threshold
- **Purchase Requests** -- requests sent to the Purchaser
- **Consumption Adjustments** -- discrepancies between calculated and actual material usage that need your approval or rejection

### 2.4. Defects Tab

Production quality monitoring:

- **DefectAlertBanner** -- appears when defect rates exceed normal thresholds
- **AnomalyAlertBanner** -- appears when material consumption deviates significantly from expected values

### 2.5. TPS Tab (Toyota Production System)

Production system parameters for efficiency monitoring.

### 2.6. TOC Tab (Theory of Constraints)

Visual display of buffer zones using the TOC/DBR methodology:

| Zone | Condition | Action |
|---|---|---|
| Green | delta >= -5% | On track, continue normal work |
| Yellow | -20% <= delta < -5% | Pay attention, consider raising priority |
| Red | delta < -20% or deadline passed | Urgent: raise priority, add resources, resolve blockages |

The **BottleneckVisualization** component shows which kilns are the current bottleneck.

### 2.7. Stone Tab

Stone reservation management -- reserve stone blanks for specific positions.

### 2.8. Kilns Tab

Quick overview of all kilns and their statuses directly from the dashboard.

### 2.9. AI Chat Tab

Built-in AI assistant for quick questions about production, orders, and materials.

### 2.10. Dynamic Tabs

Additional tabs appear automatically when relevant data exists:

- **Blocking** -- positions blocked by material shortages, missing recipes, stencils, color matching, missing consumption data (`AWAITING_CONSUMPTION_DATA`), or QM holds
- **Cancellations** -- cancellation requests from Sales
- **Change Requests** -- order modification requests from Sales
- **Mismatch** -- positions with color mismatches that require your decision

---

## 3. Materials Management

This is one of the most important areas for PM. The Materials page (`/manager/materials`) provides full inventory control.

### 3.1. Page Layout

When you open the Materials page, you see:

1. **Header** with the page title, low stock count badge, and buttons:
   - **Dashboard** -- return to PM dashboard
   - **+ Add Material** -- create a new material
2. **Filter row**:
   - Factory selector (if you have multiple factories)
   - Search box -- search materials by name
3. **Type tabs** -- dynamic tabs based on material hierarchy (subgroups). Each tab shows the count of materials in that category. Click a tab to filter, or select "All" to see everything.
4. **Materials table** -- the main data table

### 3.2. Understanding the Materials Table

The table shows the following columns:

| Column | Description |
|---|---|
| **Code** | Auto-generated material code (e.g., M-0042) |
| **Type** | Material subgroup with icon |
| **Balance** | Current stock balance (red if below minimum) |
| **Min** | Minimum balance threshold |
| **Unit** | Unit of measurement (kg, g, L, ml, pcs, m, m2) |
| **Status** | "OK" (green) or deficit amount (red) |
| **Actions** | Receive, Audit, History, Edit buttons |

> **Note for PM**: The Name column is hidden in your view for a cleaner interface. Materials are identified by their Code. You can still see the name when editing or in the transaction dialog.

### 3.3. Creating a New Material

1. Click **"+ Add Material"** (top right, or the button in the empty state).
2. Fill in the form:
   - **Name** -- descriptive name (e.g., "Zinc Oxide ZnO")
   - **Subgroup** -- select from the hierarchy (e.g., "Pigments / Iron Oxide"). This automatically sets the material type.
   - **Unit** -- kg, g, L, ml, pcs, m, or m2
   - **Initial Balance** -- starting stock quantity
   - **Min Balance** -- threshold for low stock alerts
   - **Supplier** -- select from the supplier list (optional)
   - **Warehouse Section** -- where the material is stored
3. Click **"Create"**.

> **Note**: If no factory is specified during creation, stock entries are automatically created for ALL active factories with the specified balance and min balance.

### 3.4. Editing a Material

As a PM, you can edit the following fields:

| Field | PM Can Edit? |
|---|---|
| Subgroup / Type | Yes |
| Warehouse Section | Yes |
| Min Balance | Yes |
| Supplier | Yes |
| Name | No -- contact Admin |
| Balance | No -- use Receive or Inventory Audit |
| Factory | No -- contact Admin |
| Unit | No -- set at creation |

**To edit**:
1. Find the material in the table.
2. Click the **"Edit"** button in the actions column.
3. The edit dialog opens showing the current balance as read-only. Below it: "To change balance, use Inventory Audit."
4. Modify the allowed fields.
5. Click **"Update"**.

### 3.5. Receiving Materials

When materials arrive at the warehouse, record the receipt:

1. Find the material in the table.
2. Click the **up arrow button** in the actions column. This opens the Transaction dialog in "Receive" mode.
3. The dialog shows the current balance at the top.
4. Enter the **Quantity** received.
5. Optionally add **Notes** (e.g., delivery reference, batch number).
6. Click **"Receive"**.

The balance updates immediately after the transaction is saved.

### 3.6. Inventory Audit

The Inventory Audit feature lets you correct the balance when the actual physical count differs from what the system shows. This is the proper way to adjust balances -- PM cannot edit balances directly.

**Step-by-step**:

1. Find the material in the table.
2. Click the **three-line button** (the audit button) in the actions column.
3. The Transaction dialog opens in "Inventory Audit" mode.
4. You see the **current balance** displayed at the top.
5. In the **"New actual balance"** field, enter the real quantity you counted.
6. The system automatically calculates and displays the **difference** (green for surplus, red for deficit).
7. Fill in the **Reason** field -- this is **mandatory**. Explain why the balance differs (e.g., "Spillage during transfer," "Measurement error in previous count," "Found extra stock in secondary storage").
8. Click **"Confirm Audit"**.

**What happens internally**: The system creates an `inventory` transaction with the calculated delta (new balance minus current balance). The notes include the previous balance, new balance, and your reason for the audit.

> **Important**: Always provide a clear, honest reason. Inventory audit records are part of the audit trail and are reviewed by management.

### 3.7. Switching Between Receive and Audit

When the Transaction dialog is open, you can switch between operations:

- Click **"Receive"** (green button) to record incoming materials
- Click **"Inventory Audit"** (amber button) to perform a stock count correction

The form fields change depending on which mode is selected.

### 3.8. Transaction History

To view the complete transaction history for a material:

1. Click the **"Hst"** button in the actions column.
2. A dialog opens showing all transactions sorted by date (newest first).
3. Each transaction shows:
   - **Date** -- when the transaction occurred
   - **Type** -- receive (green), consume/write-off (red), reserve/unreserve (blue), audit (amber)
   - **Qty** -- the amount (+ for incoming, - for outgoing)
   - **By** -- who performed the transaction
   - **Notes** -- any comments or automatic descriptions

Transaction types you will see:

| Type | Description | Color |
|---|---|---|
| `receive` | Material received at warehouse | Green |
| `consume` | Material consumed during glazing | Red |
| `manual_write_off` | Manual write-off | Red |
| `reserve` | Reserved for a position | Blue |
| `unreserve` | Reservation cancelled | Blue |
| `audit` (inventory) | Inventory audit correction | Amber |

### 3.9. Low Stock Alerts

Materials with a balance below their minimum threshold are highlighted:

- The row background turns red in the table.
- The **Status** column shows "Deficit: X.X unit" in red.
- The page subtitle shows a red badge with the count of low-stock materials.

When you see low stock alerts:
1. Check if the material has an active purchase request.
2. If not, coordinate with the Purchaser to order more.
3. If the shortage blocks positions, consider whether a force-unblock is needed.

### 3.10. Aggregate Mode (All Factories)

If you have access to multiple factories and select no specific factory:

- Materials are shown in aggregate mode with a **Factories** column showing how many factories stock the material.
- The **Receive** and **Audit** buttons are disabled -- you must select a specific factory to perform transactions.
- A "Select factory" message appears in the actions column.

---

## 4. Orders and Positions

### 4.1. Viewing Orders

**Path**: Dashboard > Orders tab

Orders are displayed as a table with:
- Order number, client name, source (webhook / PDF / manual)
- Status (New, In Production, Partially Ready, Ready for Shipment, Shipped, Cancelled)
- Deadline
- Number of positions

Click any order row to open its detail page.

### 4.2. Creating an Order

1. Click **"Create Order"** on the Orders tab.
2. Fill in:
   - **Order Number** -- unique identifier
   - **Client** -- client name
   - **Factory** -- select Bali or Java
   - **Deadline** -- final delivery date
   - **Items** -- add line items with: Color, Size, Application, Finishing, Quantity (pcs), Thickness (mm, default 11), Collection, Product Type (tile/sink/pebble), Shape (rectangle/round/triangle/octagon/freeform)
3. Click **"Create"**.

The system automatically creates an `OrderPosition` for each item with status `PLANNED`.

### 4.3. Uploading an Order from PDF

1. Click **"Upload PDF"**.
2. Select the PDF file.
3. The AI parser extracts order data.
4. Review and confirm the parsed data.

### 4.4. Order Statuses

| Status | Meaning |
|---|---|
| `new` | All positions are PLANNED |
| `in_production` | At least one position is in progress |
| `partially_ready` | Some positions are complete |
| `ready_for_shipment` | All positions are ready |
| `shipped` | All positions shipped |
| `cancelled` | All positions cancelled |

Order status is calculated automatically from the positions. PM can set a `status_override` for manual control.

### 4.5. Position Lifecycle

Every order item becomes an `OrderPosition` that moves through these stages:

```
PLANNED
  |
  +-- INSUFFICIENT_MATERIALS (blocked: not enough materials)
  +-- AWAITING_RECIPE (blocked: no recipe assigned)
  +-- AWAITING_STENCIL_SILKSCREEN (blocked: no stencil)
  +-- AWAITING_COLOR_MATCHING (blocked: color matching needed)
  +-- AWAITING_SIZE_CONFIRMATION (blocked: size unclear)
  +-- AWAITING_CONSUMPTION_DATA (blocked: missing consumption rate for recipe)
  |
  v
SENT_TO_GLAZING -> ENGOBE_APPLIED -> ENGOBE_CHECK -> GLAZED
  |
  v
PRE_KILN_CHECK -> LOADED_IN_KILN -> FIRED
  |
  +-- REFIRE (needs re-firing)
  +-- AWAITING_REGLAZE (needs re-glazing)
  |
  v
TRANSFERRED_TO_SORTING -> PACKED
  |
  v
SENT_TO_QUALITY_CHECK -> QUALITY_CHECK_DONE
  |
  +-- BLOCKED_BY_QM (held by Quality Manager)
  |
  v
READY_FOR_SHIPMENT -> SHIPPED
```

### 4.6. Changing Position Status

1. Open the order detail page or the Schedule page.
2. Find the position.
3. Use the **Status Dropdown** to select a new status.
4. The system validates that the transition is allowed.
5. When the status changes:
   - The order status is recalculated automatically.
   - The position is rescheduled.
   - For glazing statuses, material reservation/consumption occurs.

### 4.7. Position Splits

**Production Split**: Divide a position to process parts separately (e.g., different kilns).
- Creates child positions with split indexes: `#1.1`, `#1.2`, etc.

**Sorting Split**: Divide at the sorting stage by quality category (A-sort, B-sort, C-sort, showroom, repair, grinding, utilization).

**Merge**: Recombine previously split positions back together.

### 4.8. Force-Unblock

When a position is blocked and the standard solution is not available or practical, you can force-unblock it:

1. Find the blocked position (on the **Blocking** tab or in the schedule).
2. Click **"Force Unblock"**.
3. **Enter a reason** in the Notes field -- this is mandatory for the audit trail.
4. Confirm the action.

**What happens for each blockage type**:

| Blockage | Effect of Force-Unblock |
|---|---|
| `insufficient_materials` | Forced reservation -- balance may go negative |
| `awaiting_recipe` | Position moves to PLANNED (PM takes responsibility) |
| `awaiting_stencil_silkscreen` | Blocking tasks closed, position moves to PLANNED |
| `awaiting_color_matching` | Blocking tasks closed, position moves to PLANNED |
| `awaiting_consumption_data` | Consumption measurement task closed, position moves to PLANNED (PM accepts default rate risk) |
| `blocked_by_qm` | QM blocking tasks closed, position moves to PLANNED |

> **Warning**: Force-unblock for `insufficient_materials` can result in negative material balances. These are tracked in the `negative_balances` table and will appear as alerts.

### 4.9. Cancellation and Change Requests

When Sales sends a cancellation or change request, it appears on the dynamic **Cancellations** or **Change Requests** tab:

**Cancellation**:
- **Accept** -- order is cancelled, all positions move to CANCELLED, material reservations are released.
- **Reject** -- order continues production, Sales is notified.

**Change Request**:
- **Approve** -- changes are applied, positions updated, rescheduling triggered.
- **Reject** -- no changes applied, Sales is notified.

---

## 5. Tasks

### 5.1. Task Types

| Type | Description | Typical Assignee |
|---|---|---|
| `stencil_order` | Order a stencil | PM / Purchaser |
| `silk_screen_order` | Order silk screen | PM / Purchaser |
| `color_matching` | Color matching needed | PM |
| `material_order` | Order materials | Purchaser |
| `quality_check` | Quality inspection | Quality Manager |
| `kiln_maintenance` | Kiln maintenance | PM |
| `showroom_transfer` | Transfer to showroom | Warehouse |
| `photographing` | Product photography | Sorter/Packer |
| `packing_photo` | Packaging photography | Sorter/Packer |
| `recipe_configuration` | Set up recipe | PM / Admin |
| `stock_shortage` | Stone stock shortage | PM |
| `size_resolution` | Clarify size | PM |
| `glazing_board_needed` | Custom glazing board | PM |
| `consumption_measurement` | Measure missing consumption rate (ml/m2) for a recipe | PM |

### 5.2. Creating a Task

1. Go to Dashboard > Tasks tab > click **"Create Task"**.
2. Fill in:
   - **Factory** -- which factory
   - **Type** -- select from the list above
   - **Assignee** -- specific user or role
   - **Related Order/Position** -- link to the relevant order or position (optional)
   - **Blocking** -- check if this task should block position advancement
   - **Description** -- what needs to be done
   - **Priority** -- 0 to 10 (10 = highest)
3. Click **"Create"**.

### 5.3. Resolving Tasks

**Standard completion**: Click "Complete" on any task to mark it as done.

**Shortage Resolution** (for `stock_shortage` tasks):
- **Manufacture** -- create a new manufacturing position for the missing items. You can specify the quantity and target factory.
- **Decline** -- decline production, provide a reason. Sales will be notified.

**Size Resolution** (for `size_resolution` tasks):
- Select an existing size from the database, or
- Create a new custom size (name, width, height, thickness, shape).
- The system automatically calculates glazing board requirements and may create a follow-up `glazing_board_needed` task.

### 5.4. Monitoring Tasks

Filter tasks by:
- **Status**: pending, in_progress, done, cancelled
- **Type**: any task type
- **Assigned role**: production_manager, purchaser, warehouse, etc.
- **Factory**: filter by factory

Tasks are sorted by priority (highest first), then by creation date.

---

## 6. Consumption Rules

### 6.1. What Are Consumption Rules?

Consumption Rules define how glaze and engobe are applied to products. The **application method** is the key field -- it determines which rate fields from the recipe are used to calculate material consumption.

**Path**: `/consumption-rules`
**Access**: PM and Admin only

### 6.2. Application Methods

The application method is the most important parameter. It tells the system how the engobe and glaze are applied:

| Code | Description |
|---|---|
| `ss` | Spray engobe + Spray glaze -- uses recipe spray fields |
| `s` | Spray glaze only (no engobe) -- uses recipe spray field |
| `bs` | Brush engobe + Spray glaze |
| `sb` | Spray engobe + Brush glaze |
| `splashing` | Splashing method -- uses recipe splash field |
| `silk_screen` | Silk screen method -- uses recipe silk screen field |
| `stencil` | Stencil method -- uses recipe spray field |
| `raku` | Raku method -- uses recipe spray field |
| `gold` | Gold application -- uses recipe spray field |

### 6.3. Creating a Rule

1. Click **"+ Add Rule"**.
2. Fill in the form:
   - **Rule #** -- sequential number (auto-suggested)
   - **Name** -- descriptive name (e.g., "SS standard tile 30x60")
   - **Description** -- when this rule applies
3. Set **Matching Criteria** (the system uses these to find the right rule for each position):
   - Recipe Type (glaze / engobe)
   - Product Type (tile, sink, etc.)
   - Place of Application (face only, edges, all surfaces, etc.)
   - Size (single or multi-select to create rules for multiple sizes at once)
   - Shape (rectangle, round, etc.)
   - Collection
   - Thickness range (min/max mm)
   - Color Collection
4. Set **Consumption Calculation**:
   - **Application Method** (required) -- this is the key field
   - **Coats** -- number of application layers (default: 1)
   - **Override recipe rates** (optional, advanced) -- only check this if the recipe rates do not apply. You can set a custom ml/m2 rate and/or a specific gravity override.
5. Set **Priority** (higher number = checked first when multiple rules match).
6. Click **"Create"**.

> **Multi-size mode**: When creating a new rule, check "Multi-size" to select multiple sizes. The system creates a separate rule for each selected size automatically.

### 6.4. Editing a Rule

Click **"Edit"** next to any rule. The same form opens pre-filled with the current values. Modify and click **"Update"**.

### 6.5. Deactivating vs. Deleting

- **Deactivate**: Uncheck the "Active" checkbox. The rule remains in the system but is not used for matching. Use this when you temporarily want to disable a rule.
- **Delete**: Click **"Delete"** and confirm. This is permanent and cannot be undone.

### 6.6. When to Override Rates

By default, rates come from the recipe. Only override when:
- The product has unusual properties that cause standard rates to be inaccurate.
- You have measured actual consumption and it consistently differs from recipe values.
- A special application technique requires a custom rate.

---

## 7. Schedule Management

### 7.1. Schedule Page Overview

**Path**: `/manager/schedule`

The schedule is divided into five section tabs:

| Section | Positions Shown |
|---|---|
| **Glazing** | Planned, blocked statuses, engobe stages, glazed, pre-kiln check |
| **Firing** | Loaded in kiln, fired, refire, awaiting reglaze |
| **Sorting** | Transferred to sorting, packed, ready for shipment |
| **QC** | Sent to quality check, quality check done, blocked by QM |
| **Kilns** | Kiln batches (planned / in progress) |

At the top, **KPI cards** show the total count for each section.

### 7.2. Position Table Columns

Each section shows positions in a table with these columns:

| Column | Description |
|---|---|
| Order | Order number |
| # | Position number (e.g., #1, #1.1) |
| Color | Position color |
| Size | Tile/product size |
| Thickness | In mm |
| Shape | Rectangle, round, etc. |
| Glaze Place | Where glaze is applied (face, edges, all surfaces) |
| Edge | Edge profile info |
| Application | Application type |
| Collection | Product collection |
| Qty | Quantity in pieces |
| Status | Current status (clickable dropdown to change) |
| Type | Product type (tile, sink, etc.) |
| Priority | Priority order number |

### 7.3. Changing Status from the Schedule

Click the **Status** dropdown on any position row to see allowed transitions. Select the new status. The system validates the transition and updates automatically.

### 7.4. Auto-Form Batches

Available on the **Firing** and **Kilns** tabs:

1. Select a specific factory (required).
2. Click **"Auto-Form Batches"**.
3. Confirm the action.
4. The system:
   - Collects kiln-ready positions (pre_kiln_check, glazed)
   - Groups them by firing temperature
   - Assigns them to appropriate kilns
   - Creates batches

A result message shows how many batches and positions were assigned.

### 7.5. Kilns Tab

Shows each kiln as a card with:
- Kiln name, status badge, type (big/small/raku)
- Capacity (m2) and number of levels
- A table of scheduled batches with: date, status, position count, piece count, notes

### 7.6. Deleting Positions (Cleanup Mode)

If your factory has cleanup mode enabled (configured by Admin), you will see:
- An amber banner: "Cleanup mode: delete buttons are visible on each position row."
- A red trash icon on each position row.

To delete a position:
1. Click the trash icon.
2. Confirm the deletion.
3. The position and all its linked tasks are permanently removed.

> **Warning**: Deletion is irreversible. Only use this for test data or incorrect entries.

---

## 8. Kiln Inspections

Regular kiln inspections are essential to maintaining safe and efficient firing operations. The Kiln Inspections feature provides a structured checklist-based workflow for documenting kiln condition and tracking repairs.

### 10.1. Overview

The weekly kiln inspection covers **8 categories with 35 inspection items** in total. Each inspection is tied to a specific kiln and performed by a Production Manager.

**Path**: `/manager/kiln-inspections`

### 10.2. Inspection Categories

| # | Category | Items | What to Check |
|---|---|---|---|
| 1 | Exterior Structure | 4-5 | Cracks, mortar joints, metal frame, door seals, ventilation openings |
| 2 | Interior / Firing Chamber | 4-5 | Brick lining, shelves, posts, kiln wash, floor condition |
| 3 | Heating Elements | 4-5 | Element integrity, connections, resistance readings, element supports |
| 4 | Temperature Control | 4-5 | Thermocouple accuracy, controller function, pyrometric cones, zone consistency |
| 5 | Electrical System | 4-5 | Wiring, contactors, fuses, grounding, control panel condition |
| 6 | Gas System (if applicable) | 3-4 | Burners, gas lines, regulators, flame sensors, ventilation |
| 7 | Safety Equipment | 3-4 | Emergency shutoff, warning labels, fire extinguisher proximity, PPE availability |
| 8 | Operational Readiness | 3-4 | Kiln furniture inventory, loading tools, logbook up to date, cleaning status |

### 10.3. How to Perform an Inspection

1. Go to **Kiln Inspections** page (`/manager/kiln-inspections`).
2. Click the **New Inspection** tab.
3. **Select the kiln** you are inspecting from the dropdown.
4. The checklist loads automatically with all 35 items grouped by category.
5. Go through each item and select a rating:

| Rating | Meaning | Action Required |
|---|---|---|
| **OK** | Item is in good condition | None |
| **Not Applicable** | Item does not apply to this kiln type | None |
| **Damaged** | Item is damaged but kiln can still operate with caution | Auto-flagged for follow-up |
| **Needs Repair** | Item requires repair before next use | Auto-flagged for follow-up, repair log entry created |

6. Add optional notes to any item for additional context (e.g., "Small crack on upper left corner, monitor next week").
7. Click **Submit Inspection** when all items are rated.

> **Important**: Items marked as **Damaged** or **Needs Repair** are automatically highlighted in the inspection report and generate entries in the Repair Log for tracking.

### 10.4. Reviewing Past Inspections

- The **Inspection History** tab shows all completed inspections sorted by date.
- Click any inspection to view the full report with all ratings and notes.
- Use the filter to view inspections for a specific kiln.
- Compare inspections over time to track deterioration trends.

### 10.5. Repair Log

The Repair Log tracks every issue identified during inspections from report to resolution.

**Repair statuses**:

| Status | Meaning |
|---|---|
| `open` | Issue identified, not yet addressed |
| `in_progress` | Repair work has started |
| `completed` | Repair finished and verified |

**Workflow**:
1. When an inspection item is rated **Damaged** or **Needs Repair**, a repair log entry is automatically created with status `open`.
2. Assign the repair to the appropriate person or team.
3. Update the status to `in_progress` when work begins.
4. Mark as `completed` when the repair is done and verified.
5. The next kiln inspection should confirm the repair was effective.

> **Best practice**: Review the Repair Log at the start of each week. Prioritize open items for kilns scheduled for upcoming firings.

---

## 9. Consumption Measurement Tasks

### 9.1. What Are Consumption Measurement Tasks?

When a new order arrives and the position uses an application method (e.g., SS, BS, SB) but the assigned recipe is **missing the required consumption rate** (spray rate or brush rate in ml/m2), the system cannot calculate how much material to reserve. In this case, the position is blocked with status `AWAITING_CONSUMPTION_DATA` and a **blocking task** of type `consumption_measurement` is created and assigned to the PM.

### 9.2. When Does This Happen?

This occurs when **all three conditions** are met:
1. A position has a recipe assigned (glaze or engobe).
2. The consumption rule specifies an application method that requires a specific rate (e.g., spray rate for SS method, brush rate for BS method).
3. The recipe does **not** have the required rate field filled in.

**Application method codes and which rate they require**:

| Code | Full Name | Engobe Rate | Glaze Rate |
|---|---|---|---|
| `SS` | Spray engobe + Spray glaze | Spray rate | Spray rate |
| `BS` | Brush engobe + Spray glaze | Brush rate | Spray rate |
| `SB` | Spray engobe + Brush glaze | Spray rate | Brush rate |
| `S` | Spray glaze only (no engobe) | -- | Spray rate |
| `splashing` | Splashing method | -- | Splash rate |

### 9.3. How to Handle a Consumption Measurement Task

**Step 1: Find the task**

The task appears on your **Tasks** tab with type `consumption_measurement`. It is marked as **blocking**, meaning the associated position cannot proceed until it is resolved.

The task description includes:
- **Recipe name** -- which recipe is missing the rate
- **Missing rate type** -- spray rate (ml/m2) or brush rate (ml/m2)
- **Order number and position** -- which order is waiting

**Step 2: Physically measure the consumption rate**

1. Prepare a test piece of the correct size and material.
2. Apply the glaze or engobe using the specified method (spray or brush).
3. Measure the volume of material used (in ml).
4. Calculate the area of the test piece (in m2).
5. Divide: **consumption rate = volume used (ml) / area (m2)**.

> **Tip**: Perform at least 2-3 test applications and average the results for accuracy. Document the test conditions (nozzle size, pressure, distance for spray; brush type and technique for brush).

**Step 3: Enter the measured rate**

1. Open the task and click the action to enter the consumption rate.
2. Enter the measured rate in **ml/m2**.
3. Confirm the entry.

**Step 4: What happens next**

After you enter the consumption rate:
- The recipe is updated with the new rate value.
- The blocking task is marked as `done`.
- The position status changes from `AWAITING_CONSUMPTION_DATA` back to `PLANNED`.
- The system proceeds with material reservation using the newly entered rate.
- All other positions using the same recipe and application method also benefit from this rate going forward.

### 9.4. Practical Tips for Measurement

- **Keep a measurement log**: Record all measurements with date, recipe, method, test piece size, and result. This helps resolve future disputes about rates.
- **Standardize conditions**: Use consistent spray pressure, nozzle size, and distance for reproducible results.
- **For brush application**: Note the brush type and technique used, as these significantly affect the rate.
- **Update rates proactively**: If you notice a recipe will be used with a new application method, measure the rate in advance to avoid blocking when the order arrives.

---

## 10. Tips and Best Practices

### 10.1. Daily Routine

**Morning (start of shift)**:
1. Check the **Orders** tab -- any new orders?
2. Check the **Blocking** tab -- how many positions are blocked? Any critical ones?
3. Check the **TOC** tab -- any orders in the red zone?
4. Check the **Materials** tab -- any critical stock shortages?
5. Check the **Tasks** tab -- any overdue tasks?

**During the day**:
6. Review the **Glazing** schedule -- check the queue, adjust priorities if needed.
7. Form batches on the **Kilns** tab -- create batches for firing, start firing.
8. Resolve blockages -- force-unblock or organize solutions (order stencils, restock materials).
9. Monitor firing -- check IN_PROGRESS batches, complete finished ones.
10. Approve **Consumption Adjustments** -- review discrepancies between calculated and actual usage.

**Evening (end of shift)**:
11. Check daily completion -- how many positions were completed today?
12. Prepare tomorrow's batches -- form batches for the next day.
13. Review Sales requests -- handle any pending Cancellation or Change Requests.

**Weekly**:
14. **Perform kiln inspections** -- complete the 35-item checklist for each active kiln (see Section 8).
15. **Review the Repair Log** -- follow up on open and in-progress repair items.
16. Check kiln maintenance schedule.
17. Review and update consumption rules if needed.
18. Consider a full factory reschedule if significant changes have occurred.

### 10.2. Factory Selector Best Practices

- Always select a **specific factory** before performing operations that modify data (creating orders, forming batches, receiving materials).
- Use "All Factories" mode only for overview and monitoring.
- If you are assigned to one factory, the selector is hidden and your factory is always active.

### 10.3. Handling Material Shortages

1. First, check the transaction history to understand consumption trends.
2. Verify the min_balance setting is still accurate -- adjust via Edit if needed.
3. Coordinate with the Purchaser to place orders for critical materials.
4. Only use force-unblock for material shortages as a last resort -- it creates negative balances.

### 10.4. Inventory Audit Best Practices

- Perform regular audits (weekly or monthly) for high-turnover materials.
- Always enter a clear, specific reason -- "recount" is not helpful; "Recount after spillage on March 15" is.
- Compare the audit difference with recent transaction history to identify patterns.
- If you consistently see discrepancies, review the consumption rules -- the rates may need adjustment.

### 10.5. Notifications

PM receives notifications for:
- New orders arriving from Sales webhook
- Kiln breakdowns
- Critical material shortages
- Cancellation and change requests from Sales

The **Telegram bot** sends a daily summary at 21:00 (Indonesian language) with:
- Full task list for the next day
- KPI for the current day

### 10.6. Keyboard and Interface Tips

- Use the **search box** on the Materials page to quickly find materials by name or code.
- On the Schedule page, the **Status Dropdown** shows only valid transitions -- you cannot accidentally select an invalid status.
- The **Transaction History** dialog is scrollable -- older transactions are at the bottom.
- When creating consumption rules with multiple sizes, use **Multi-size mode** to save time.

---

> **Questions?** Contact your system administrator or use the built-in **AI Chat** on the PM dashboard.
