# Production Manager (PM) Guide -- Moonjar PMS

> Version: 1.4 | Date: 2026-04-06
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
11. [Kiln Maintenance](#11-kiln-maintenance)
12. [Grinding Decisions](#12-grinding-decisions)
13. [Finished Goods](#13-finished-goods)
14. [Reconciliations](#14-reconciliations)
15. [Reports and Analytics](#15-reports-and-analytics)
16. [Factory Calendar](#16-factory-calendar)
17. [Recipes Management](#17-recipes-management)
18. [Firing Profiles](#18-firing-profiles)
19. [Temperature Groups](#19-temperature-groups)
20. [Stages Management](#20-stages-management)
21. [Firing Schedules](#21-firing-schedules)
22. [Warehouses Management](#22-warehouses-management)
23. [Packaging Management](#23-packaging-management)
24. [Sizes Management](#24-sizes-management)
25. [Tablo (Production Display)](#25-tablo-production-display)
26. [Tips and Best Practices](#26-tips-and-best-practices)
27. [Pre-Kiln QC Checklist](#27-pre-kiln-qc-checklist)
28. [Final QC Checklist](#28-final-qc-checklist)
29. [Shipment Workflow](#29-shipment-workflow)
30. [Employee Management and Attendance](#30-employee-management-and-attendance)
31. [Firing Temperature Logging](#31-firing-temperature-logging)
32. [Smart Force Unblock](#32-smart-force-unblock)
33. [Points System and Recipe Verification](#33-points-system-and-recipe-verification)
34. [Telegram Bot Commands](#34-telegram-bot-commands)
35. [Morning Briefing](#35-morning-briefing)
36. [Kiln Shelves Management](#36-kiln-shelves-management)
37. [Production Line Resources](#37-production-line-resources)
38. [Zone-Based Kiln Loading](#38-zone-based-kiln-loading)
39. [Position Status Machine](#39-position-status-machine)
40. [Skill Badges System](#40-skill-badges-system)
41. [Competitions and Challenges](#41-competitions-and-challenges)
42. [TPS Operations and Master Permissions](#42-tps-operations-and-master-permissions)
43. [Real-Time Notifications (WebSocket)](#43-real-time-notifications-websocket)
44. [Delivery Photo Processing](#44-delivery-photo-processing)
45. [Vision-Based Photo Analysis](#45-vision-based-photo-analysis)

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
| Kiln Inspections | `/manager/kiln-inspections` | Weekly checklist-based kiln condition assessments |
| Kiln Maintenance | `/manager/kiln-maintenance` | Scheduled preventive and corrective maintenance |
| Grinding | `/manager/grinding` | Grinding decisions for defective products |
| Materials | `/manager/materials` | Material inventory, receiving, audit, transaction history |
| Recipes | `/admin/recipes` | Glaze, engobe, and product recipe management |
| Firing Profiles | `/admin/firing-profiles` | Multi-interval heating/cooling curves for kilns |
| Temp Groups | `/admin/temperature-groups` | Temperature group definitions for co-firing |
| Warehouses | `/admin/warehouses` | Warehouse section management |
| Packaging | `/admin/packaging` | Box types, capacities, and spacer definitions |
| Sizes | `/admin/sizes` | Product size definitions with shape-specific dimensions |
| Consumption Rules | `/admin/consumption-rules` | Glaze/engobe consumption rates per square meter |
| Factory Calendar | `/admin/factory-calendar` | Working days, holidays, and non-working days per factory |
| Finished Goods | `/warehouse/finished-goods` | Finished product inventory and availability checks |
| Reconciliations | `/warehouse/reconciliations` | Formal multi-material inventory check sessions |
| Reports | `/reports` | Orders summary, kiln utilization, and production analytics |
| Tablo | `/tablo` | Full-screen production display board for workshop monitors |
| Order Details | `/orders/:id` | Detailed view of a specific order and its positions |
| Guide | `/manager/guide` | This PM guide (in-app) |

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

### 8.1. Overview

The weekly kiln inspection covers **8 categories with 35 inspection items** in total. Each inspection is tied to a specific kiln and performed by a Production Manager.

**Path**: `/manager/kiln-inspections`

### 8.2. Inspection Categories

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

### 8.3. How to Perform an Inspection

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

### 8.4. Reviewing Past Inspections

- The **Inspection History** tab shows all completed inspections sorted by date.
- Click any inspection to view the full report with all ratings and notes.
- Use the filter to view inspections for a specific kiln.
- Compare inspections over time to track deterioration trends.

### 8.5. Repair Log

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


## 11. Kiln Maintenance

### 11.1. Overview

The Kiln Maintenance page provides a structured workflow for scheduling, tracking, and completing preventive and corrective maintenance on kilns. Unlike Kiln Inspections (Section 8), which focus on weekly condition assessments, Kiln Maintenance manages scheduled work: element replacements, thermocouple calibrations, brick repairs, deep cleans, and more.

**Path**: `/manager/kiln-maintenance`

### 11.2. Page Tabs

| Tab | Purpose |
|---|---|
| **Upcoming** | Shows all planned maintenance items sorted by date, with overdue items highlighted in red |
| **History** | Completed and cancelled maintenance records |
| **Maintenance Types** | Manage the catalogue of maintenance type definitions (e.g., "Element replacement", "Deep clean") |

### 11.3. Scheduling Maintenance

1. On the **Upcoming** tab, click **"+ Schedule Maintenance"**.
2. Fill in the form:
   - **Kiln** -- select the kiln (filtered by factory if a factory is selected).
   - **Maintenance Type** -- choose from predefined types.
   - **Scheduled Date** -- when the maintenance should be performed.
   - **Notes** -- any additional instructions.
3. Requirements are set automatically based on the maintenance type:
   - **Requires empty kiln** -- the kiln must be unloaded before work begins.
   - **Requires cooled kiln** -- the kiln must be at room temperature.
   - **Requires power off** -- electrical supply must be disconnected.
4. For recurring maintenance, set the **Recurrence Interval** (in days). The system automatically schedules the next occurrence after each completion.

### 11.4. Completing Maintenance

1. Find the maintenance item on the **Upcoming** tab.
2. Click **"Complete"**.
3. Optionally add **Completion Notes** describing what was done.
4. Click **"Confirm"**. The item moves to the History tab.
5. If the item is recurring, a new scheduled item is automatically created for the next interval.

### 11.5. Summary Cards

The Upcoming tab shows four summary cards at the top:

| Card | Description |
|---|---|
| Total Scheduled | All planned maintenance items in the next 90 days |
| Overdue | Items past their scheduled date (highlighted red) |
| Today | Items due today (highlighted yellow) |
| + Schedule | Quick-action button to add new maintenance |

### 11.6. Managing Maintenance Types

On the **Maintenance Types** tab you can create, edit, and delete type definitions. Each type has:
- **Name** -- e.g., "Element replacement", "Thermocouple calibration"
- **Default requirements** -- whether the kiln must be empty, cooled, or powered off
- **Default recurrence interval** -- automatic repeat period in days

---

## 12. Grinding Decisions

### 12.1. Overview

The Grinding Decisions page manages products that were sorted into the "grinding" category during the Sorting stage. These items have minor surface defects that can potentially be recovered by grinding or, alternatively, sent to Mana (an external party) for disposal or rework.

**Path**: `/manager/grinding`

### 12.2. Status Workflow

Each grinding stock item has one of three statuses:

| Status | Meaning |
|---|---|
| **Pending** | Awaiting PM decision |
| **Grinding** | Decided: will be ground and reused |
| **Sent to Mana** | Decided: sent to external party for processing |

### 12.3. Making Decisions

For each pending item you see three action buttons:

- **Grind** (green) -- mark the item for internal grinding and reuse.
- **Hold** (amber) -- keep the item in pending status for later decision.
- **Mana** (red) -- send to Mana. A confirmation dialog appears before this action is finalised.

### 12.4. Summary Cards

Four KPI cards are displayed at the top:

| Card | Description |
|---|---|
| Total Items | All grinding stock items |
| Pending Decision | Items awaiting PM action |
| Decided (Grind) | Items approved for grinding |
| Sent to Mana | Items sent to external party |

### 12.5. Filters

- **Status tabs**: All / Pending / Decided (Grind) / Sent to Mana
- **Factory selector**: Filter by factory
- **Pagination**: 50 items per page

---

## 13. Finished Goods

### 13.1. Overview

The Finished Goods page tracks the inventory of completed products that are ready for shipment or storage. It records stock by colour, size, collection, product type, and factory.

**Path**: `/warehouse/finished-goods`

### 13.2. Key Actions

- **+ Add Stock** -- add a new finished goods record (factory, colour, size, collection, product type, quantity, reserved quantity).
- **Edit** -- update quantity or reserved quantity for an existing item.
- **Check Availability** -- query across all factories to see if a specific colour/size combination is available in the required quantity. The system shows which factories hold matching stock and how many pieces are available.

### 13.3. Understanding the Table

| Column | Description |
|---|---|
| **Color** | Product colour name |
| **Size** | Product size |
| **Collection** | Product collection |
| **Type** | Product type (tile, sink, pebble) |
| **Factory** | Which factory holds the stock |
| **Quantity** | Total pieces in stock |
| **Reserved** | Pieces reserved for orders |
| **Available** | Quantity minus reserved (colour-coded: red if zero, yellow if low, green if sufficient) |

### 13.4. Filters

- **Factory** dropdown -- filter by a specific factory or view all.
- **Color search** -- search by colour name (debounced).
- **Pagination** -- 50 items per page.

### 13.5. Totals

Summary totals at the bottom of the page show aggregate Quantity, Reserved, and Available across all visible items.

---

## 14. Reconciliations

### 14.1. Overview

The Reconciliations page manages formal inventory check sessions. Unlike the single-material Inventory Audit (Section 3.6), a Reconciliation is a structured event that can cover multiple materials at once. It is used for periodic full or partial stock-takes.

**Path**: `/warehouse/reconciliations`

### 14.2. Reconciliation Statuses

| Status | Meaning |
|---|---|
| **Scheduled** | Planned for a future date |
| **Draft** | Created but not yet started |
| **In Progress** | Currently being counted |
| **Completed** | All items counted and adjustments applied |
| **Cancelled** | Reconciliation cancelled |

### 14.3. Creating a Reconciliation

1. Click **"+ New Reconciliation"**.
2. Select the **Factory**.
3. Add optional **Notes** (e.g., "Monthly stock-take -- warehouse A").
4. Click **"Create"**.

### 14.4. Working with a Reconciliation

1. Click on a reconciliation row to expand it.
2. **Add items** -- select materials to include in the count.
3. For each item, enter the **actual counted quantity**.
4. The system shows the **system balance** alongside the counted quantity and calculates the **difference**.
5. When all items are counted, click **"Complete"**.
6. On completion the system applies the balance adjustments as inventory audit transactions.

### 14.5. Summary Cards

| Card | Description |
|---|---|
| Total | All reconciliations |
| In Progress | Active reconciliations being counted |
| Completed | Finished reconciliations |
| Scheduled | Reconciliations planned for the future |

### 14.6. Filters

- **Factory Selector** -- filter by factory.
- **Status tabs** -- All / In Progress / Completed / Scheduled / Cancelled.

---

## 15. Reports and Analytics

### 15.1. Overview

The Reports page provides aggregated production metrics with date-range and factory filters.

**Path**: `/reports`

### 15.2. Filters

- **Factory** -- select a specific factory or "All Factories".
- **Date range** -- From / To date pickers (defaults to the last 30 days).

### 15.3. Orders Summary

Four KPI cards at the top:

| Card | Description |
|---|---|
| **Total Orders** | Number of orders in the selected period (with in-progress count as subtitle) |
| **Completed** | Orders that reached shipped status (with on-time count as subtitle) |
| **On-time %** | Percentage of completed orders delivered by their deadline. Green >= 80%, Yellow >= 50%, Red < 50% |
| **Avg Days to Complete** | Average number of days from order creation to shipped status |

### 15.4. Kiln Utilization

For each kiln, a card displays:

- **Kiln name** and utilization percentage badge (green >= 80%, yellow >= 50%, red < 50%).
- A **progress bar** showing visual utilization.
- **Total firings** count for the period.
- **Average load** (m2 per firing).

This section helps you identify under-utilized kilns that could take additional batches and over-loaded kilns that may need scheduling adjustments.

---

## 16. Factory Calendar

### 16.1. Overview

The Factory Calendar manages working days, holidays, and non-working days for each factory. The schedule engine uses this calendar to calculate accurate production timelines and deadlines.

**Path**: `/admin/factory-calendar`

### 16.2. Calendar View

The page displays a visual monthly calendar grid. Each day is colour-coded:

| Colour | Meaning |
|---|---|
| **White** | Normal working day |
| **Red / marked** | Non-working day (holiday, day off) |

Click any day to add or remove a holiday entry. Click and drag to select a range of dates.

### 16.3. Navigation

- **Month arrows** -- move forward or backward by month.
- **Year arrows** -- move forward or backward by year.
- **Factory selector** -- choose which factory's calendar to manage.

### 16.4. Bulk Holiday Presets

Two quick-import presets are available:

- **Indonesian National Holidays** -- imports major government holidays (New Year, Eid, Independence Day, Christmas, etc.).
- **Balinese Holidays** -- imports Nyepi, Galungan, Kuningan, and other Balinese ceremony days.

Click a preset to preview the dates, then confirm to add them all at once. Existing entries are not duplicated.

### 16.5. Adding and Removing Holidays

**Add**: Click a day on the calendar, enter a name (e.g., "Nyepi"), and save.

**Remove**: Click an existing holiday day and confirm deletion.

> **Important**: Changes to the factory calendar may affect scheduled production timelines. After significant calendar changes, consider triggering a reschedule from the Schedule page.

---

## 17. Recipes Management

### 17.1. Overview

The Recipes page allows PM to view and manage glaze, engobe, and product recipes. Each recipe defines its ingredients with quantities, application rates (spray, brush, splash, silk screen), and links to temperature groups for firing.

**Path**: `/admin/recipes`

### 17.2. Recipe Fields

| Field | Description |
|---|---|
| **Name** | Recipe name (e.g., "Moonjar White Glaze M-01") |
| **Type** | Product, Glaze, or Engobe |
| **Color Collection** | Which colour collection this recipe belongs to |
| **Client** | Client name (if recipe is client-specific) |
| **Specific Gravity** | Density of the mixed glaze/engobe (g/ml) |
| **Spray Rate** | Consumption rate for spray application (ml/m2) |
| **Brush Rate** | Consumption rate for brush application (ml/m2) |
| **Default** | Whether this recipe is the default for its type |
| **Active** | Whether the recipe is currently in use |

### 17.3. Ingredients

Each recipe has a list of ingredients grouped by material type (Frits, Pigments, Oxides/Carbonates, Other). For each ingredient:
- **Material** -- selected from the materials catalogue.
- **Quantity** -- weight in the recipe formula.
- **Per-ingredient rates** -- spray, brush, splash, and silk screen rates can be set individually.

### 17.4. Key Actions

- **Create** -- add a new recipe with ingredients.
- **Edit** -- modify recipe fields or ingredient list.
- **Duplicate** -- copy an existing recipe to create a variant.
- **CSV Import** -- bulk import recipes from a CSV file.

### 17.5. Temperature Group Links

Recipes can be linked to one or more temperature groups. This determines which kiln temperatures are compatible with the recipe and is used by the batch formation algorithm when grouping positions for co-firing.

---

## 18. Firing Profiles

### 18.1. Overview

Firing Profiles define the heating and cooling curves used during kiln firing. Each profile specifies multi-interval temperature stages: how fast the kiln heats from one temperature to another, and how it cools down afterward.

**Path**: `/admin/firing-profiles`

### 18.2. Profile Fields

| Field | Description |
|---|---|
| **Name** | Profile name (e.g., "Standard 1012°C -- 14h") |
| **Temperature Group** | Which temperature group this profile is for |
| **Total Duration** | Expected total firing time in hours |
| **Active** | Whether this profile is available for use |

### 18.3. Heating and Cooling Stages

Each profile has two lists of temperature stages:

**Heating stages** (type = heating):
- **Start Temp** -- starting temperature in °C (first stage typically starts at ~20°C).
- **End Temp** -- target temperature for this stage.
- **Rate** -- heating rate in °C per hour.

**Cooling stages** (type = cooling):
- **Start Temp** -- temperature at the start of cooling (typically the peak firing temperature).
- **End Temp** -- temperature at the end of this cooling stage.
- **Rate** -- cooling rate in °C per hour.

You can add multiple intervals to create complex curves. For example:
- Stage 1: 20°C -> 600°C at 100°C/h (slow initial heating)
- Stage 2: 600°C -> 1012°C at 50°C/h (slow approach to target)
- Cooling 1: 1012°C -> 600°C at 80°C/h (controlled initial cooling)
- Cooling 2: 600°C -> 20°C at 120°C/h (natural cooling)

### 18.4. Key Actions

- **Create** -- define a new profile with heating and cooling stages.
- **Edit** -- modify stages, rates, or duration.
- **Activate / Deactivate** -- toggle profile availability.

---

## 19. Temperature Groups

### 19.1. Overview

Temperature Groups categorise firing temperatures. Each group has a name, a target temperature (°C), and a display order. Recipes and firing profiles are linked to temperature groups, allowing the system to automatically group compatible positions for co-firing.

**Path**: `/admin/temperature-groups`

### 19.2. Fields

| Field | Description |
|---|---|
| **Name** | Group name (e.g., "Standard 1012°C", "Low-fire 800°C") |
| **Temperature** | Target firing temperature in °C |
| **Description** | Optional notes |
| **Display Order** | Sort position in lists |

### 19.3. Recipe Links

Each temperature group shows its linked recipes. This makes it easy to see which glazes and engobes fire at the same temperature and can share a kiln batch.

### 19.4. Key Actions

- **Create** -- add a new temperature group.
- **Edit** (inline) -- modify name, temperature, description, or display order.
- **Delete** -- remove a temperature group (only if no recipes are linked).
- **CSV Import** -- bulk import from a CSV file.

---

## 20. Stages Management

### 20.1. Overview

The Stages page manages the production stage definitions that positions move through. Each stage has a name and a sort order that determines its sequence in the production pipeline.

**Path**: `/admin/stages`

### 20.2. Fields

| Field | Description |
|---|---|
| **Name** | Stage name (e.g., "Glazing", "Firing", "Sorting", "QC") |
| **Order** | Numeric position in the production sequence |

### 20.3. Key Actions

- **Create** -- add a new production stage.
- **Edit** -- modify name or order.
- **Delete** -- remove a stage (only if not referenced by active positions).

> **Note**: Stage definitions are used by the schedule engine and the position lifecycle. Changing stage order or names may affect how positions are displayed on the Schedule page.

---

## 21. Firing Schedules

### 21.1. Overview

The Firing Schedules page manages per-kiln firing schedule templates. A firing schedule defines the planned firing parameters for a specific kiln, including timing and configuration data.

**Path**: `/admin/firing-schedules`

### 21.2. Fields

| Field | Description |
|---|---|
| **Kiln** | Which kiln this schedule applies to |
| **Name** | Schedule name (e.g., "Standard weekday firing") |
| **Schedule Data** | JSON configuration with firing parameters |
| **Default** | Whether this is the default schedule for the kiln |

### 21.3. Filters

- **Kiln dropdown** -- filter schedules by kiln.

### 21.4. Key Actions

- **Create** -- add a new firing schedule for a kiln.
- **Edit** -- modify schedule parameters.
- **Set as Default** -- mark a schedule as the default for its kiln.
- **Delete** -- remove a schedule.

---

## 22. Warehouses Management

### 22.1. Overview

The Warehouses page manages warehouse sections where materials are stored. Each section belongs to a factory and can be assigned to a specific user.

**Path**: `/admin/warehouses`

### 22.2. Fields

| Field | Description |
|---|---|
| **Name** | Section name (e.g., "Raw Materials Store A") |
| **Code** | Short identifier code |
| **Factory** | Which factory this section belongs to |
| **Type** | Section (physical), Warehouse (full warehouse), or Virtual |
| **Managed By** | User responsible for this section |
| **Display Order** | Sort position |
| **Default** | Whether this is the default section for its factory |
| **Active** | Whether the section is currently in use |

### 22.3. Key Actions

- **Create** -- add a new warehouse section.
- **Edit** -- modify section details.
- **Delete** -- remove a section.
- **CSV Import** -- bulk import from a CSV file.

---

## 23. Packaging Management

### 23.1. Overview

The Packaging page manages box type definitions and their capacities. Each box type specifies how many pieces of each size fit per box, and which spacer materials are used.

**Path**: `/admin/packaging`

### 23.2. Key Concepts

- **Box Type** -- a specific packaging box linked to a material (the box itself is a material in the inventory).
- **Capacity** -- for each product size, defines the number of pieces per box and the area (m2) per box.
- **Spacers** -- for each product size, defines which spacer material is used and how many spacers go in each box.

### 23.3. Key Actions

- **Create** -- add a new box type with capacities and spacer definitions.
- **Edit** -- modify capacities or spacer configurations.
- **CSV Import** -- bulk import packaging definitions.

---

## 24. Sizes Management

### 24.1. Overview

The Sizes page manages product size definitions. Each size has dimensions, a shape, and an automatically calculated area used for material consumption calculations.

**Path**: `/admin/sizes`

### 24.2. Fields

| Field | Description |
|---|---|
| **Name** | Size name (e.g., "30x60", "20x20 round") |
| **Width** | Width in mm |
| **Height** | Height in mm |
| **Thickness** | Default thickness in mm |
| **Shape** | Rectangle, Round, Triangle, Octagon, Freeform |
| **Shape Dimensions** | Additional dimension parameters for non-rectangular shapes |
| **Area** | Calculated area in cm2 (automatic based on shape and dimensions) |
| **Custom** | Whether this is a one-off custom size |

### 24.3. Key Actions

- **Create** -- add a new size definition with shape-specific dimension editors.
- **Edit** -- modify dimensions or shape.
- **Delete** -- remove a size (only if not used by active positions).
- **CSV Import** -- bulk import sizes.

---

## 25. Tablo (Production Display)

### 25.1. Overview

The Tablo page is a full-screen production display board designed to be shown on a workshop TV or monitor. It provides a real-time overview of production status without requiring interaction.

**Path**: `/tablo`

### 25.2. Usage

- Open the Tablo page on a dedicated screen in the production area.
- The display auto-refreshes to show current production status.
- No authentication actions are needed on this page -- it is a read-only view.

---
## 26. Tips and Best Practices

### 26.1. Daily Routine

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

### 26.2. Factory Selector Best Practices

- Always select a **specific factory** before performing operations that modify data (creating orders, forming batches, receiving materials).
- Use "All Factories" mode only for overview and monitoring.
- If you are assigned to one factory, the selector is hidden and your factory is always active.

### 26.3. Handling Material Shortages

1. First, check the transaction history to understand consumption trends.
2. Verify the min_balance setting is still accurate -- adjust via Edit if needed.
3. Coordinate with the Purchaser to place orders for critical materials.
4. Only use force-unblock for material shortages as a last resort -- it creates negative balances.

### 26.4. Inventory Audit Best Practices

- Perform regular audits (weekly or monthly) for high-turnover materials.
- Always enter a clear, specific reason -- "recount" is not helpful; "Recount after spillage on March 15" is.
- Compare the audit difference with recent transaction history to identify patterns.
- If you consistently see discrepancies, review the consumption rules -- the rates may need adjustment.

### 26.5. Notifications

PM receives notifications for:
- New orders arriving from Sales webhook
- Kiln breakdowns
- Critical material shortages
- Cancellation and change requests from Sales

The **Telegram bot** sends a daily summary at 21:00 (Indonesian language) with:
- Full task list for the next day
- KPI for the current day

### 26.6. Keyboard and Interface Tips

- Use the **search box** on the Materials page to quickly find materials by name or code.
- On the Schedule page, the **Status Dropdown** shows only valid transitions -- you cannot accidentally select an invalid status.
- The **Transaction History** dialog is scrollable -- older transactions are at the bottom.
- When creating consumption rules with multiple sizes, use **Multi-size mode** to save time.

---

## 27. Pre-Kiln QC Checklist

Before a batch enters the kiln, a Pre-Kiln QC check ensures all positions meet quality standards.

### 27.1. Opening the Pre-Kiln QC Dialog

1. Navigate to the **Schedule** page (`/manager/schedule`), section **Kilns**.
2. Find the batch that is ready for firing.
3. Click the **QC** button (checklist icon) on the position row. Select **Pre-Kiln QC**.

### 27.2. Completing the Checklist

The dialog shows a list of quality check items specific to pre-kiln inspection (e.g., glaze coverage, surface defects, correct positioning).

For each item:
- Click **Pass** if the item meets standards.
- Click **Fail** if it does not.
- Click **N/A** if the item is not applicable to this position.

All items must be evaluated before submission.

### 27.3. Adding Notes

At the bottom of the checklist, there is a free-text **Notes** field. Use it to record any observations, especially for items marked as Fail.

### 27.4. Submitting

Click **Submit** to save the QC result. The overall result (Pass/Fail) is computed automatically:
- **Pass**: all items are Pass or N/A.
- **Fail**: any item is Fail.

If the result is Fail, the position will be flagged and may require corrective action before firing.

---

## 28. Final QC Checklist

After firing, a Final QC check verifies the finished product quality.

### 28.1. Opening the Final QC Dialog

1. Navigate to the **Schedule** page, section **Sorting/QC**.
2. Find the position that has completed firing.
3. Click the **QC** button and select **Final QC**.

### 28.2. Completing the Checklist

The Final QC checklist contains items specific to post-firing quality (e.g., color accuracy, dimensional tolerance, surface finish, edge quality).

For each item:
- Click **Pass** or **Fail**. (N/A is not available for Final QC -- all items must be evaluated.)

### 28.3. Submitting

Click **Submit** to save the result. Failed positions will be routed to the Grinding decision workflow or flagged for defect reporting.

### 28.4. Material Details on Position Cards

Position cards on the Schedule page now display material information:
- Glaze recipe name and materials used.
- This helps QC inspectors verify the correct recipe was applied.

---

## 29. Shipment Workflow

The Shipment page allows you to manage outbound shipments for completed orders.

### 29.1. Accessing the Shipment Page

- From the **Order Detail** page (`/orders/:id`), click the **Shipments** tab or **Create Shipment** button.
- Or navigate directly to `/manager/shipments` for a list of all shipments.

### 29.2. Creating a Shipment

1. Click **Create Shipment**.
2. Select the **shipping method**: Courier, Pickup, or Container.
3. Select the **carrier** (JNE, TIKI, J&T, SiCepat, AnterAja, Pickup, Container, Other).
4. Select which **positions** to include in the shipment. Only positions with status "Ready for Shipment" are available.
5. Click **Create** to generate the shipment record. Status starts as **Prepared**.

### 29.3. Adding Tracking Information

After creating a shipment:
1. Enter the **tracking number** provided by the carrier.
2. Optionally add **shipping notes** (e.g., special handling instructions).

### 29.4. Marking as Shipped

1. Once the package is handed off to the carrier, click **Mark Shipped**.
2. The shipment status changes to **Shipped** and included positions transition to the Shipped status.

### 29.5. Shipment Statuses

| Status | Meaning |
|---|---|
| Prepared | Shipment created, awaiting pickup |
| Shipped | Handed to carrier |
| In Transit | Carrier confirmed in transit |
| Delivered | Confirmed delivered to client |
| Cancelled | Shipment cancelled |

### 29.6. Cancelling a Shipment

Click **Cancel Shipment** to revert. Positions will return to their previous status (Ready for Shipment).

---

## 30. Employee Management and Attendance

The Employees page (`/manager/employees`) provides tools for managing factory staff and tracking attendance.

### 30.1. Employee List

The page displays all employees assigned to your factory with the following details:
- Name, position/role, employment type (Full Time, Part Time, Contract)
- Contact information
- Active/inactive status

### 30.2. Adding a New Employee

1. Click **Add Employee**.
2. Fill in: name, position, employment type, daily rate, contact info.
3. Click **Save**.

### 30.3. Attendance Tracking

The **Attendance** tab shows a monthly calendar grid:

- Rows = employees, Columns = days of the month.
- Click a cell to cycle through attendance statuses:
  - **P** (Present) -- green
  - **A** (Absent) -- red
  - **S** (Sick) -- yellow
  - **L** (Leave) -- blue
  - **H** (Half Day) -- orange

Non-working days (holidays) from the Factory Calendar are shaded and cannot be edited.

### 30.4. Payroll Summary

The **Payroll** tab calculates monthly pay based on:
- Number of days present (full days + half days at 50%)
- Daily rate per employee
- Total working days in the month (from Factory Calendar)

This provides a quick overview for payroll processing.

---

## 31. Firing Temperature Logging

During kiln firing, you can log temperature readings to track the firing curve and record peak temperatures.

### 31.1. Accessing the Temperature Log

1. Navigate to the **Schedule** page, **Kilns** section.
2. Find the active batch/firing session.
3. Click the **thermometer icon** ("Log temperature readings") on the batch row.

### 31.2. Logging a Temperature Reading

The Firing Temperature Log dialog shows:
- **Peak temperature** (if already recorded).
- **Temperature readings timeline** -- all readings logged so far with timestamps.

To add a reading:
1. Enter the **temperature** in degrees Celsius.
2. The system records the timestamp automatically.
3. Click **Add** to save the reading.

### 31.3. Why Log Temperatures

- Ensures the firing profile was followed correctly.
- Helps diagnose defects caused by temperature deviations.
- Builds a historical record for recipe optimization.
- Peak temperature is compared against the recipe's target firing temperature.

---

---

## 32. Smart Force Unblock

When a position is blocked, you can force-unblock it to keep production moving. The system now offers **3 context-aware options** instead of a generic "Force Unblock" button.

### 32.1. How to Use

1. Go to the **Blocking** tab on your Dashboard.
2. Find the blocked position.
3. Click **"Force Unblock"**.
4. A dialog appears with 3 options specific to the blocking reason.

### 32.2. Options by Blocking Type

| Blocking Reason | Option 1 | Option 2 | Option 3 |
|----------------|----------|----------|----------|
| Material Shortage | Proceed with available stock | Wait for next delivery | Substitute material |
| Missing Recipe | Use closest matching recipe | Create temporary recipe | Skip glazing |
| Missing Stencil | Proceed without stencil | Use alternative stencil | Delay until ready |
| Color Mismatch | Accept current color | Request re-matching | Use standard color |
| Missing Consumption Data | Use default rates | Measure now | Copy from similar recipe |

### 32.3. CEO Notification

Every force unblock automatically sends a Telegram notification to the CEO with the position details, blocking reason, chosen option, and your name.

> **Important**: Force unblock is a last resort. Always try to resolve the underlying issue first.

---

## 33. Points System and Recipe Verification

### 33.1. Points System

You earn points for accurate recipe preparation. Points accumulate throughout the year and appear on leaderboards.

**Scoring:**

| Accuracy (deviation from spec) | Points |
|-------------------------------|--------|
| Within +/-1% | 10 |
| Within +/-3% | 7 |
| Within +/-5% | 5 |
| Within +/-10% | 3 |
| Beyond +/-10% | 1 |
| Photo verification bonus | +2 |

Points reset on January 1 each year. Check your points anytime with `/mystats` or `/points` in Telegram.

### 33.2. Recipe Verification

To verify a recipe preparation:

1. Prepare the recipe according to specifications.
2. Take a photo of the measured quantities (scale reading, graduated cylinder, etc.).
3. Send the photo to the Telegram bot or upload via the app.
4. The system uses OCR to extract measured values and compares them to the recipe spec.
5. Points are awarded based on accuracy.

To cancel an in-progress verification, use `/cancel_verify` in Telegram.

### 33.3. Daily Challenges

Each morning briefing includes a daily challenge (e.g., "Zero defects today = +20 pts"). Complete the challenge for bonus points.

---

## 34. Telegram Bot Commands

The Telegram bot supports these commands for production managers:

| Command | What It Does |
|---------|-------------|
| `/mystats` | Your personal points breakdown and statistics |
| `/leaderboard` | Top performers ranking |
| `/stock` | Low stock materials summary |
| `/challenge` | Current daily challenge details |
| `/achievements` | Your earned badges and milestones |
| `/points` | Current points balance |
| `/cancel_verify` | Cancel an in-progress recipe verification |

You can also send natural language messages to the bot for AI-powered assistance with production questions.

---

## 35. Morning Briefing

Every morning at the configured time (default 7:00 AM), the bot sends a briefing to the production group chat.

### 35.1. Briefing Structure

The briefing contains 7 blocks:

1. **Greeting** -- personalized with mood based on yesterday's results
2. **Yesterday Summary** -- pieces produced, defect rate, kiln utilization
3. **Today's Plan** -- scheduled batches, expected output, key deadlines
4. **Blocking Issues** -- active blocks requiring immediate attention
5. **Achievements** -- points earned yesterday, top performers, streaks
6. **Challenge** -- daily challenge with bonus points
7. **Action Buttons** -- 6 inline buttons for quick actions

### 35.2. Inline Buttons

Below the briefing message, you will see 6 buttons:

- **Start Day** -- tap to confirm attendance and start your shift
- **Details** -- see the full expanded schedule for today
- **Problem** -- quickly report a problem
- **Stats** -- view your personal statistics
- **Leaders** -- see the current leaderboard
- **Stock** -- check low stock materials

### 35.3. Evening Summary

At 6 PM, the bot sends an evening summary with today's results: pieces completed vs plan, defect rate, points earned, and a preview of tomorrow's first batch.

---

## 36. Kiln Shelves Management

Kiln shelves are fire-resistant platforms used inside kilns during firing. They are expensive consumables with a limited lifespan, so the system tracks each shelf individually.

### 36.1. Viewing Shelves

Navigate to **Kilns** page. Below the kiln cards, you will see the **Kiln Shelves** section:
- Shelves are grouped by kiln
- Each group shows total active shelves and combined area (m²)
- Each shelf row shows: name, material, dimensions, area, status, and firing cycle progress bar

**Cycle progress bar colors:**
- **Green** -- below 70% of max cycles (healthy)
- **Yellow** -- 70-90% of max cycles (monitor closely)
- **Red** -- above 90% of max cycles (schedule replacement)

Use the **filter** dropdown to show shelves for a specific kiln. Check **Show written-off** to see decommissioned shelves.

### 36.2. Adding a New Shelf

1. Click **+ Add Shelf**
2. Select the **Kiln** this shelf belongs to
3. Enter **dimensions**: length (cm), width (cm), thickness (mm)
4. Select **Material** -- the system will auto-set the default max firing cycles:
   - Silicon Carbide (SiC): 200 cycles
   - Cordierite: 150 cycles
   - Mullite: 300 cycles
   - Alumina: 250 cycles
5. Optionally enter purchase date, cost (IDR), and notes
6. **Name** is auto-generated if left empty: e.g., `SiC-SmallK-001`

### 36.3. Editing a Shelf

Click **Edit** on any shelf row. You can:
- Change dimensions, material, notes, max firing cycles
- **Move the shelf to a different kiln** by selecting a new kiln from the dropdown
- Change status between Active and Damaged

### 36.4. Recording Firing Cycles

Click **+1** on a shelf row after each firing. The system will:
- Increment the firing cycle counter
- Show a **warning** when the shelf reaches 90% of its max cycles
- The cycle progress bar updates automatically

### 36.5. Writing Off a Shelf

When a shelf is cracked, warped, or otherwise unusable:

1. Click **Write Off** on the shelf row
2. Enter the **reason** (mandatory): e.g., "Cracked after thermal shock"
3. Optionally attach a **photo URL** of the damage
4. Click **Confirm Write Off**

**What happens automatically:**
- Shelf status changes to `written_off`, becomes inactive
- If the shelf had a purchase cost, an **OPEX expense entry** is created with cost-per-cycle calculation
- If remaining shelves for that kiln are critically low (0 shelves or <0.5 m²), a **SHELF_REPLACEMENT_NEEDED** task is created for you

### 36.6. Understanding Shelf Lifecycle

The system tracks the full lifecycle of each shelf:
- **Purchase** → track date and cost
- **Active use** → count firing cycles, monitor wear
- **Damage** → mark as damaged, add condition notes
- **Write-off** → record reason with photo evidence
- **OPEX impact** → cost per cycle calculated automatically

CEO sees a dedicated **OPEX analytics widget** with: average lifespan per material, projected replacements, monthly write-off costs.

---

## 37. Production Line Resources

Production line resources (work tables, drying racks, glazing boards) directly affect how fast the factory can process tiles. The scheduler uses these resources to calculate realistic stage durations.

### 37.1. What Are Line Resources?

| Resource Type | What It Is | How It Constrains |
|--------------|------------|-------------------|
| **Work Table** | Table area for engobe/glazing | Limits how much area can be processed per cycle |
| **Drying Rack** | Shelving for drying boards | Limits how many boards can dry simultaneously |
| **Glazing Board** | Boards tiles sit on during glazing | Total available boards limit batch throughput |

### 37.2. Managing Resources

On the **PM Dashboard** → TPS tab, find the **Line Resources** section:
- Resources are grouped by type (work table, drying rack, glazing board)
- Each card shows name, capacity, and number of units
- Use the inline form to add new resources

### 37.3. How Resources Affect Scheduling

The scheduler formula: **stage_days = max(speed_days, constraint_days)**

- If you have enough resources, the stage completes at normal speed
- If resources are limited, the stage takes longer (constraint extends it)
- If no resources are configured, the scheduler uses speed-only calculation (backward compatible)

### 37.4. Board Deficit Alerts

If the scheduler detects that more glazing boards are needed than available:
- A **BOARD_ORDER_NEEDED** task is automatically created for you
- The task includes: how many boards are needed, how many are available, and the deficit
- One task per factory (no spam — deduplication is built in)

---

## 38. Zone-Based Kiln Loading

Kilns have different loading zones for different tile types:

### 38.1. Loading Zones

- **Edge zone** -- tiles loaded on edge (face only, 1-2 edges). High density, used for smaller tiles (≤15cm)
- **Flat zone** -- tiles loaded flat (all edges, with back). Lower density, required for larger tiles or full-coverage glazing

### 38.2. How Zones Work in Scheduling

The scheduler automatically classifies each position:
- face_only, edges_1, edges_2 tiles ≤15cm → **Edge zone**
- all_edges, with_back, or tiles >15cm → **Flat zone**

Each zone has its own capacity. Overflow in one zone does **not** spill into the other — they are physically separate areas in the kiln. If the edge zone is full but flat zone has space, edge positions must wait for the next firing day.

---

## 39. Position Status Machine

Every production position follows a strict status flow. The system validates every transition -- you cannot skip stages or move backward arbitrarily.

### 39.1. Status Flow Overview

The normal production flow is:

```
PLANNED --> ENGOBE_APPLIED --> ENGOBE_CHECK --> GLAZED --> PRE_KILN_CHECK
  --> LOADED_IN_KILN --> FIRED --> TRANSFERRED_TO_SORTING --> PACKED
  --> SENT_TO_QUALITY_CHECK --> QUALITY_CHECK_DONE --> READY_FOR_SHIPMENT --> SHIPPED
```

### 39.2. Blocking Statuses

When a position cannot proceed, it enters one of these blocking statuses:

| Status | Reason | Resolution |
|--------|--------|------------|
| `INSUFFICIENT_MATERIALS` | Not enough stock to reserve | Receive materials or force-unblock |
| `AWAITING_RECIPE` | No recipe assigned for the glaze/engobe | Create or assign a recipe |
| `AWAITING_STENCIL_SILKSCREEN` | Stencil not available | Order/prepare the stencil |
| `AWAITING_COLOR_MATCHING` | Color match needed | Complete color matching process |
| `AWAITING_SIZE_CONFIRMATION` | Size not confirmed | Confirm or create the size definition |
| `AWAITING_CONSUMPTION_DATA` | Missing spray/brush rate | Measure and enter the rate (see Section 9) |
| `BLOCKED_BY_QM` | Quality Manager hold | QM must release the hold |

All blocking statuses can return to `PLANNED` once the issue is resolved.

### 39.3. Special Transitions

- **Refire**: After `FIRED`, a position can go to `REFIRE` and then back to `LOADED_IN_KILN` for another firing round.
- **Reglaze**: From `TRANSFERRED_TO_SORTING`, a position can go to `AWAITING_REGLAZE` then `SENT_TO_GLAZING` for re-glazing.
- **Merged**: Child positions (split from a parent) can be merged back at `PACKED`, `QUALITY_CHECK_DONE`, or `READY_FOR_SHIPMENT` stages.
- **Cancelled**: Any position can be cancelled from any status.
- **Blocked by QM**: Quality Manager can block any position from any status. When unblocked, it returns to its previous status.

### 39.4. Tips

- The system prevents invalid transitions -- if a button is greyed out, the position must complete the current stage first.
- Each status change is recorded in the Stage History for full traceability.
- The frontend mirrors the status machine logic locally, so allowed transitions are displayed without extra API calls.

---

## 40. Skill Badges System

The Skill Badges system tracks worker competencies. Workers earn certifications by completing operations with high quality, and PM/CEO can formally certify their skills.

### 40.1. What Are Skill Badges?

Each badge represents a specific factory skill, such as:

| Category | Examples |
|----------|---------|
| **Production** | Engobe application, glazing, kiln loading |
| **Specialized** | Stencil work, silkscreen, raku firing |
| **Quality** | Pre-kiln inspection, final QC |
| **Safety** | Kiln safety protocols, chemical handling |
| **Leadership** | Team coordination, training others |

Each badge has requirements:
- **Required operations**: Number of times the worker must perform the operation (default: 50)
- **Zero-defect percentage**: Minimum defect-free rate required (default: 90%)
- **Mentor approval**: Whether PM/CEO manual approval is needed
- **Points on earn**: Points awarded when the badge is earned (default: 100)

### 40.2. Skill Learning Flow

1. **Start learning**: Worker or PM initiates skill learning via the system.
2. **Track progress**: The system counts completed operations and tracks defect-free percentage.
3. **Certification**: When requirements are met, PM or CEO approves the certification.
4. **Badge earned**: Worker receives the badge and bonus points.

### 40.3. Managing Skill Badges (PM)

**Seeding default badges**: On first setup, go to the TPS/Gamification section and seed default badges for your factory. This creates a standard set of production skills.

**Viewing worker skills**: Check any worker's skill progress -- see which skills they are learning, their operation count, defect-free percentage, and certification status.

**Certifying skills**: When a worker meets the requirements, review their progress and approve or deny certification.

**Revoking certification**: If a worker's quality drops significantly, you can revoke a certification. The worker will need to re-earn it.

### 40.4. Tips

- Seed default badges when setting up a new factory to get a standard skill matrix.
- Use skill badges when assigning workers to operations -- prefer certified workers for critical tasks.
- Review skill progress weekly as part of your TPS dashboard routine.

---

## 41. Competitions and Challenges

Competitions motivate workers through friendly, time-bounded contests with real prizes.

### 41.1. Competition Types

| Type | Description |
|------|------------|
| **Individual** | Each worker competes on their own score |
| **Team** | Workers grouped into teams (e.g., by section), team totals compete |

### 41.2. Scoring Metrics

Competitions can track different metrics:

- **Throughput**: Number of pieces or m2 processed
- **Quality**: Defect-free percentage
- **Combined** (default): Throughput x Quality weight -- rewards both speed and quality

The `quality_weight` parameter controls how much quality affects the combined score (default: 1.0). Higher weight makes quality more important.

### 41.3. Competition Lifecycle

| Status | Meaning |
|--------|---------|
| `proposed` | Worker proposed a challenge, awaiting PM approval |
| `upcoming` | Approved, not yet started (start_date in the future) |
| `active` | Currently running |
| `completed` | End date passed, final standings calculated |

### 41.4. Creating a Competition (PM)

1. Define the competition: title (EN + Indonesian optional), type (individual or team), metric, quality weight.
2. Set date range: start and end dates.
3. Optionally add prize description and budget (IDR).
4. For team competitions, define teams (e.g., "Glazing Section" vs "Sorting Section").

### 41.5. Worker-Proposed Challenges

Workers can propose challenges via the Telegram bot or the system. Proposed challenges appear with status `proposed` and require PM approval before they become active.

To approve: find the proposed challenge and click **Approve**. It moves to `upcoming` status and becomes active on its start date.

### 41.6. Standings and Leaderboard

View real-time standings for any active competition. Standings show:
- Rank, participant name, throughput score, quality score, combined score, bonus points
- For team competitions: team totals and individual contributions

To manually refresh scores: use the **Update Scores** action (useful if automatic scoring needs a nudge).

### 41.7. Prizes

After a competition completes, the system can generate AI-based prize recommendations:
- Recommendations consider performance, improvement trajectory, and budget
- CEO/Owner reviews and approves, rejects, or awards prizes
- Prize statuses: `pending` --> `approved` --> `awarded` (or `rejected`)

### 41.8. Gamification Seasons

Competitions can be grouped into monthly seasons. Each season has:
- Start and end dates
- Final standings snapshot
- Prize award records

View season history to track long-term engagement trends.

### 41.9. Tips

- Keep competitions short (1-2 weeks) for maximum engagement.
- Use combined scoring to prevent speed-at-the-cost-of-quality behavior.
- Rotate between individual and team competitions to build both personal excellence and team spirit.
- Even small prizes (IDR 50,000-100,000) create significant motivation when combined with public recognition.

---

## 42. TPS Operations and Master Permissions

The Toyota Production System (TPS) module tracks production operations and controls which masters can perform which tasks.

### 42.1. Operations

Operations are the atomic units of production work (e.g., "Apply engobe", "Load kiln", "Sort tiles"). Each operation belongs to a factory and has a sort order for display.

**Viewing operations**: Navigate to the TPS section on your dashboard. The operations list shows all defined operations for your factory, sorted by their configured order.

### 42.2. Master Permissions

Master and Senior Master roles require explicit permission to perform specific operations. This ensures:
- Workers only perform tasks they are trained for
- Quality accountability is clear per operation
- Skill progression is tracked per operation

### 42.3. Managing Permissions (PM)

**Check permission**: Quickly verify if a specific master has permission for an operation.

**View all permissions**: See the full list of operations a master is permitted to perform.

**Grant permission**: Assign a new operation permission to a master or senior master.
- Only `master` and `senior_master` roles can receive permissions.
- The system prevents duplicate grants.

**Revoke permission**: Remove a permission if a worker should no longer perform that operation (e.g., after quality issues or role change).

### 42.4. How Permissions Are Enforced

When a master logs a production operation through the Tablo or Telegram bot:
1. The system checks if the master has permission for the operation.
2. If no permission exists, the operation is rejected with an error message.
3. If permission exists, the operation is logged with full traceability (who, when, what).

### 42.5. Tips

- Grant permissions incrementally as workers earn skill badges.
- Review permissions quarterly -- revoke unused ones to keep the matrix clean.
- Use the permission check endpoint before assigning tasks to avoid rejection at the workstation.

---

## 43. Real-Time Notifications (WebSocket)

The system delivers real-time updates to your browser without requiring page refresh.

### 43.1. How It Works

When you are logged in, the system automatically establishes a WebSocket connection. You will see real-time updates for:

- **New orders** arriving from the Sales webhook
- **Kiln status changes** (firing started, firing complete, breakdown)
- **Low stock alerts** when materials drop below minimum balance
- **Task assignments** and status changes
- **Blocking events** when positions get blocked
- **Cancellation and change requests** from Sales

### 43.2. Connection Status

The WebSocket connection indicator appears in the navigation bar:
- **Connected**: Real-time updates are flowing
- **Reconnecting**: Temporary disconnection, auto-reconnecting with exponential backoff (up to 30 seconds)
- **Disconnected**: No connection (check your network)

The system sends periodic heartbeats (every 30 seconds) to keep the connection alive.

### 43.3. Factory-Scoped Notifications

Notifications are scoped to your selected factory. If you switch factories, the WebSocket connection updates to deliver notifications for the new factory only. This prevents notification noise from other factories.

### 43.4. Tips

- Keep your browser tab open to receive real-time alerts -- critical for monitoring kiln firings and material shortages.
- If notifications stop arriving, refresh the page to re-establish the WebSocket connection.
- The notification bell in the top bar shows unread count -- click to see the full notification list.

---

## 44. Delivery Photo Processing

When materials arrive at the factory, you can process delivery notes by photo instead of manual data entry.

### 44.1. How to Process a Delivery Photo

**Via Telegram bot:**
1. Send a photo of the delivery note to the bot.
2. The bot uses Vision AI (OCR) to read the document.
3. It extracts: supplier name, date, item list with quantities and units.
4. The smart material matcher maps delivery items to existing materials in the database.
5. You review the matched items, confirm, edit, or skip each one.

**Via the web app:**
1. Go to **Materials** page.
2. Click **Upload Delivery Photo**.
3. Upload a photo (JPEG, PNG, or WebP).
4. Review the OCR results and matched materials.
5. Confirm to receive the materials into inventory.

### 44.2. Smart Material Matching

The system matches delivery note items to database materials using:
1. **Token-based matching**: Splits item names into words and compares against material names.
2. **AI fallback**: If basic matching fails, an AI model suggests the best match.

For each item, you can:
- **Accept match**: Confirm the suggested material
- **Change match**: Select a different material from the database
- **Create new**: Add a new material if it does not exist yet
- **Skip**: Ignore the item (e.g., service charges, delivery fees)

### 44.3. Image Validation

The system validates uploaded images by checking magic bytes (file signature). Only JPEG, PNG, and WebP files are accepted. This prevents accidental upload of non-image files.

### 44.4. Tips

- Take photos in good lighting with the full delivery note visible.
- Include both the header (supplier, date) and all line items in the frame.
- For multi-page delivery notes, process each page as a separate photo.
- The OCR works best with printed text -- handwritten notes may need manual correction.

---

## 45. Vision-Based Photo Analysis

The system uses AI vision models to analyze production photos for different purposes.

### 45.1. Analysis Types

| Type | AI Model | Purpose |
|------|----------|---------|
| **Delivery** | GPT-4.1 Nano (cheap OCR) | Read delivery notes, extract items and quantities |
| **Scale** | GPT-4.1 Nano (cheap OCR) | Read weight from scale display, identify pigment color |
| **Packing** | GPT-4.1 Nano (cheap OCR) | Read packing labels -- order number, quantity, size |
| **Quality** | Claude Sonnet (smart analysis) | Detect defects: cracks, glaze issues, color mismatches, warping |
| **Defect** | Claude Sonnet (smart analysis) | Deep defect analysis with severity and location |

### 45.2. How Quality Analysis Works

1. Take a photo of the fired product showing the area of concern.
2. Upload via the app or send to the Telegram bot with context.
3. The AI analyzes the image and returns:
   - **Defects found**: Type, severity (low/medium/high), location on the product
   - **Overall quality**: Pass, fail, or needs_review
   - **Description**: Brief summary of findings

### 45.3. Cost Optimization

The system automatically selects the cheapest appropriate model:
- OCR tasks (delivery, scale, packing) use the cheaper GPT-4.1 Nano model (~$0.10 per million tokens)
- Complex visual analysis (quality, defect) uses Claude Sonnet for higher accuracy (~$2.00 per million tokens)

This means routine delivery processing costs almost nothing, while quality inspection gets the best available AI model.

### 45.4. Tips

- For quality photos: use consistent lighting and include a size reference.
- Capture defects from multiple angles for the most accurate analysis.
- The AI is a tool to assist, not replace human judgment -- always verify critical quality decisions.
- Scale photos work best when the display is clearly visible and not at an extreme angle.

---

> **Questions?** Contact your system administrator or use the built-in **AI Chat** on the PM dashboard.
