# Moonjar PMS — API Contracts

> Endpoint reference for recent feature additions.
> Base path: `/api`

---

## Kiln Inspections API

**Prefix:** `/api/kiln-inspections`
**Auth:** JWT required. Write endpoints require `require_management` (PM, Admin, Owner).

### Schemas

```python
class InspectionResultInput:
    item_id: str              # UUID of kiln_inspection_items row
    result: str               # ok | not_applicable | damaged | needs_repair
    notes: str | None

class InspectionCreateInput:
    resource_id: str           # kiln resource UUID
    factory_id: str
    inspection_date: date
    results: list[InspectionResultInput]
    notes: str | None

class RepairLogInput:
    resource_id: str
    factory_id: str
    date_reported: date | None   # defaults to today
    issue_description: str
    diagnosis: str | None
    repair_actions: str | None
    spare_parts_used: str | None
    technician: str | None
    date_completed: date | None
    status: str = "open"         # open | in_progress | done
    notes: str | None
    inspection_result_id: str | None

class RepairLogUpdateInput:
    issue_description: str | None
    diagnosis: str | None
    repair_actions: str | None
    spare_parts_used: str | None
    technician: str | None
    date_completed: date | None
    status: str | None
    notes: str | None
```

### Endpoints (9 total)

| # | Method | Path | Auth | Description |
|---|--------|------|------|-------------|
| 1 | GET | `/kiln-inspections/items` | any user | List active checklist items grouped by category |
| 2 | GET | `/kiln-inspections` | any user | List inspections (filters: resource_id, factory_id, date_from, date_to) |
| 3 | GET | `/kiln-inspections/{inspection_id}` | any user | Get single inspection with all results |
| 4 | POST | `/kiln-inspections` | management | Create inspection with checklist results. 409 if duplicate date+kiln |
| 5 | GET | `/kiln-inspections/repairs` | any user | List repair logs (filters: resource_id, factory_id, status) |
| 6 | POST | `/kiln-inspections/repairs` | management | Create repair log entry |
| 7 | PATCH | `/kiln-inspections/repairs/{repair_id}` | management | Update repair log (partial) |
| 8 | DELETE | `/kiln-inspections/repairs/{repair_id}` | management | Delete repair log entry |
| 9 | GET | `/kiln-inspections/matrix` | any user | Matrix view: dates x kilns x items (for spreadsheet UI) |

### Response shapes

**List inspections** returns:
```json
{
  "items": [{ "id", "resource_id", "resource_name", "factory_id",
              "inspection_date", "inspected_by_id", "inspected_by_name",
              "notes", "created_at", "results": [...], "summary": {
                "total", "ok", "issues", "not_applicable"
              }}],
  "total": int
}
```

**Matrix** returns:
```json
{
  "dates": ["2026-03-15", ...],
  "kilns": {"uuid": "Kiln Name", ...},
  "matrix": { "2026-03-15": { "Kiln Name": { "item_uuid": {"result", "notes"} }}}
}
```

---

## Tasks — Consumption Measurement Resolution (NEW)

**Endpoint:** `POST /api/tasks/{task_id}/resolve-consumption`
**Auth:** `require_management`

### Request Schema

```python
class ConsumptionResolutionInput:
    spray_ml_per_sqm: float | None
    brush_ml_per_sqm: float | None
```

### Behavior
1. Validates task type is `consumption_measurement` and not already done.
2. Reads `missing_rates` from task metadata (e.g. `["spray"]` or `["brush", "spray"]`).
3. Requires the corresponding rate fields to be provided.
4. Updates the recipe's `consumption_spray_ml_per_sqm` / `consumption_brush_ml_per_sqm`.
5. Unblocks the related position: `awaiting_consumption_data` -> `planned`.
6. Triggers material reservation for the unblocked position.
7. Closes the task as done.

### Response
```json
{
  "task_status": "done",
  "recipe_id": "uuid",
  "updated_fields": ["spray=150.0"],
  "position_status": "planned",
  "reservation": {"status": "reserved"} | null
}
```
