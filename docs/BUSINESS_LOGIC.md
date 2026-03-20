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
