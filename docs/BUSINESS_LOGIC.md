# Moonjar PMS — Business Logic

> Algorithms and decision flows for core production processes.

---

## Consumption Rate Auto-Detection (NEW)

### Overview
When an order arrives via webhook or manual entry, `process_order_item()` in `order_intake.py` checks whether the assigned recipe has the consumption rates required by the position's application method. If rates are missing, the position is blocked and a task is auto-created for PM to measure them.

### Application Method -> Required Consumption Rates

| Method Code | Description | Required Rates |
|-------------|-------------|----------------|
| `ss` | Spray engobe + Spray glaze | spray |
| `s` | Spray glaze only | spray |
| `bs` | Brush engobe + Spray glaze | brush, spray |
| `sb` | Spray engobe + Brush glaze | spray, brush |
| `splashing` | Spray + Splash glaze | spray |
| `stencil` | Spray through stencil | spray |
| `silk_screen` | Spray + Silk screen | spray |
| `gold` | 1st firing SS, 2nd brush gold | spray, brush |
| `raku` | Spray, raku kiln | spray |

### Recipe Fields Checked
- `recipe.consumption_spray_ml_per_sqm` — for "spray" requirement
- `recipe.consumption_brush_ml_per_sqm` — for "brush" requirement

### Flow

```
process_order_item(order, item)
  │
  ├─ match recipe by color + collection
  ├─ reserve materials
  │
  └─ _check_consumption_rates(db, order, position, recipe)
       │
       ├─ if no recipe or no application_method_code → skip (return False)
       │
       ├─ lookup _METHOD_REQUIRED_RATES[method]
       │
       ├─ for each required rate_type:
       │     if recipe lacks the rate → add to missing_methods[]
       │
       ├─ if no missing → return False (all OK)
       │
       └─ BLOCK:
            ├─ position.status = AWAITING_CONSUMPTION_DATA
            ├─ create Task(
            │     type = CONSUMPTION_MEASUREMENT,
            │     blocking = True,
            │     assigned_role = PRODUCTION_MANAGER,
            │     metadata = {recipe_id, missing_rates, method}
            │  )
            └─ return True (position was blocked)
```

### Resolution
PM opens the blocking task in the UI, enters measured ml/sqm values, calls `POST /tasks/{id}/resolve-consumption`. This updates the recipe, unblocks the position to `planned`, and triggers material reservation.

---

## Kiln Inspection & Repair Tracking (NEW)

### Inspection Model
- **Template items**: 35 seed checklist items across 8 categories (Frame & Stability, Door, Interior, Ceramic Tubes, Spiral, Thermocouple, Electrical, Other).
- **Inspection**: One per kiln per date. Performed by PM. Contains results for each checklist item.
- **Result values**: `ok`, `not_applicable`, `damaged`, `needs_repair`.
- **Summary**: Auto-calculated counts of ok/issues/not_applicable per inspection.

### Repair Log
- Created from inspection findings or standalone.
- Status flow: `open` -> `in_progress` -> `done`.
- Optionally linked to an `inspection_result_id` for traceability.
- Tracks: issue description, diagnosis, repair actions, spare parts, technician, dates.

### Matrix View
The `/kiln-inspections/matrix` endpoint returns data structured as `dates x kilns x items`, enabling the frontend to render a spreadsheet-like checklist overview across time and kilns.

---

## Planning Engine — Batch Fill Optimization (NEW — Session 2)

### optimize_batch_fill
Scores and optimizes batch composition for kiln firing. Uses a scoring function that considers:
- Kiln utilization % (fill ratio)
- Compatible product grouping (same firing profile)
- Priority weighting (urgent orders score higher)

### calculate_kiln_utilization
Analytics function returning current and historical kiln utilization rates per factory.

### generate_production_schedule
Generates a daily view of production schedule with assigned batches, stages, and resource allocation.

### recalculate_schedule
Orchestrator function that re-runs the full scheduling pipeline when conditions change (new orders, delays, kiln downtime). Triggers backward scheduling, batch optimization, and resource reassignment.

---

## Unit Conversion Fix (UPDATED — Session 2)

### convert_units — Recipe to Stock
Recipe units (grams) are properly converted to stock units (kilograms) using `specific_gravity` from the material record. Previously the conversion was missing, causing material reservation to request incorrect quantities.

```
stock_qty_kg = recipe_qty_g / 1000 * specific_gravity
```

---

## Engobe Shelf Coating — Per-Batch Consumption (NEW — Session 2)

For `EngobeType.shelf_coating`, consumption is calculated based on total kiln shelf area (sqm), not per-piece. This is because shelf coating covers the kiln shelves themselves regardless of how many pieces are loaded.

```
shelf_coating_qty = kiln_shelf_area_sqm * consumption_per_sqm
```

---

## Defect Coefficient — 2D Matrix (UPDATED — Session 2)

The defect coefficient now uses a 2D matrix combining both glaze type and product type (previously 1D, size-only). This gives more accurate waste predictions since defect rates vary by glaze complexity and product geometry.

```
defect_coefficient = DEFECT_MATRIX[glaze_type][product_type]
```

---

## Night Escalation Modes (NEW — Session 2)

Three escalation modes for overdue/critical tasks during night shifts:

| Mode | Behavior |
|------|----------|
| `MORNING` | Queue notification, deliver at 7 AM |
| `REPEAT` | Send Telegram message, repeat every N minutes until acknowledged |
| `CALL` | Send Telegram + trigger phone call via integration |

---

## Webhook Auth Modes (NEW — Session 2)

### WebhookAuthMode
Sales webhook now supports multiple authentication modes:

| Mode | Description |
|------|-------------|
| `bearer` | Standard Bearer token in Authorization header |
| `hmac` | HMAC-SHA256 signature verification of request body |
| `legacy` | Original shared-secret query parameter (backward compatible) |

---

## Order Intake — Service Items & Task Linking (UPDATED — Session 2)

### process_incoming_order
Now handles service items (non-production line items like installation, delivery). Service items create blocking `Task` records linked to the order. Tasks are assigned to appropriate roles and must be resolved before order can be marked complete.

Each task is linked to its parent position via `task.position_id`, enabling position-level blocking when the task requires resolution before production can proceed.

---

## Master Permission System (NEW — Session 2)

### MasterPermission
Operation-level access control for `master` and `senior_master` roles within TPS (Toyota Production System) framework.

- Each operation (e.g., "kiln_loading", "glaze_mixing") is defined in `tps_operations`
- Permissions are granted per-user per-operation by management
- Check before allowing a master to perform an operation at a workstation
- Supports audit trail: who granted, when, with optional notes

---

## Multi-Round Firing Profiles (NEW — Session 2)

Firing profiles now support multiple firing rounds. When `firing_round > 1`, the system selects a stage-specific profile instead of the default. This enables products that require multiple firings (e.g., bisque + glaze firing, or gold application requiring a separate low-temperature firing).

```
if firing_round > 1:
    profile = get_firing_profile(recipe, stage=current_stage, round=firing_round)
else:
    profile = get_firing_profile(recipe)
```
