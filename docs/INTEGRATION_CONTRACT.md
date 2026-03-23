# Sales <-> PMS Integration Contract

**Last updated:** 2026-03-23
**Status:** Audited and fixed

---

## A. POST /api/integration/webhook/sales-order (Incoming)

### Authentication
- `X-API-Key` header (compared against `SALES_APP_API_KEY`)
- OR `Authorization: Bearer <token>` (compared against `PRODUCTION_WEBHOOK_BEARER_TOKEN`)
- HMAC-SHA256 signature via `X-Webhook-Signature` header (when `PRODUCTION_WEBHOOK_HMAC_SECRET` configured)

### Payload Format
Supports two formats:
1. **Nested (legacy):** `{ "event_id": "...", "event_type": "new_order", "order_data": { ... } }`
2. **Flat (Sales current):** `{ "event_id": "...", "event_type": "new_order", "external_id": "...", "items": [...], ... }`

### Event Types
| event_type     | Behavior |
|----------------|----------|
| `new_order`    | Create production order + positions. If order with same `external_id` already exists and is active, creates a change request for PM review. |
| `order_update` | Creates a ChangeRequest for PM review. Does NOT auto-apply changes. |
| `order_cancel` | Creates a cancellation request for PM review. Does NOT auto-cancel. |

### Order-Level Fields Accepted

| Sales Field            | PMS Model Column              | Type      | Required | Notes |
|------------------------|-------------------------------|-----------|----------|-------|
| `external_id`          | `external_id`                 | string    | Yes      | Unique per source, used for idempotency |
| `order_number`         | `order_number`                | string    | No       | Auto-generated if missing: `SALES-{uuid8}` |
| `client`               | `client`                      | string    | No       | Fallback to `customer_name`, then "Unknown" |
| `customer_name`        | `client`                      | string    | No       | Alternative name for `client` |
| `client_location`      | `client_location`             | string    | No       | Used for factory auto-assignment |
| `sales_manager_name`   | `sales_manager_name`          | string    | No       | |
| `sales_manager_contact`| `sales_manager_contact`       | string    | No       | |
| `factory_id`           | `factory_id`                  | uuid str  | No       | Explicit factory; auto-assigned if missing |
| `final_deadline`       | `final_deadline`               | date str  | No       | ISO format YYYY-MM-DD |
| `desired_delivery_date`| `desired_delivery_date`       | date str  | No       | ISO format YYYY-MM-DD |
| `mandatory_qc`         | `mandatory_qc`                | boolean   | No       | Default: false |
| `notes`                | `notes`                       | string    | No       | |

### Item-Level Fields Accepted

| Sales Field              | PMS Model Column          | Type      | Required | Notes |
|--------------------------|---------------------------|-----------|----------|-------|
| `color`                  | `color`                   | string    | Yes      | Default: "" |
| `color_2`                | `color_2`                 | string    | No       | Second color for stencil/silkscreen |
| `size`                   | `size`                    | string    | No       | E.g. "20x20". Constructed from `size_width_cm` x `size_height_cm` if absent |
| `size_width_cm`          | *(used for size calc)*    | number    | No       | Used to construct size string and calculate sqm |
| `size_height_cm`         | *(used for size calc)*    | number    | No       | Used to construct size string and calculate sqm |
| `application`            | `application`             | string    | No       | Also mapped to `application_method_code` on position (SS, BS, Stencil, etc.) |
| `finishing`              | `finishing`               | string    | No       | |
| `thickness`              | `thickness`               | decimal   | No       | Accepts string "11mm" or number. Default: 11.0 |
| `thickness_mm`           | `thickness`               | number    | No       | Preferred over `thickness` string |
| `quantity`               | `quantity_pcs`            | integer   | Yes*     | Sales name; mapped to `quantity_pcs` |
| `quantity_pcs`           | `quantity_pcs`            | integer   | Yes*     | PMS native name; takes priority over `quantity` |
| `quantity_sqm`           | `quantity_sqm`            | decimal   | No       | Auto-calculated from dimensions x qty if missing |
| `collection`             | `collection`              | string    | No       | Also used as fallback for `application_collection_code` on position |
| `product_type`           | `product_type`            | string    | No       | Default: "tile". Enum: tile, table_top, sink, countertop, 3d, custom |
| `shape`                  | `shape`                   | string    | No       | rectangle, round, circle, oval, etc. |
| `length_cm`              | `length_cm`               | decimal   | No       | |
| `width_cm`               | `width_cm`                | decimal   | No       | |
| `depth_cm`               | `depth_cm`                | decimal   | No       | Sinks only |
| `bowl_shape`             | `bowl_shape`              | string    | No       | Sinks only |
| `shape_dimensions`       | `shape_dimensions`        | JSON      | No       | Shape-specific measurements |
| `edge_profile`           | `edge_profile`            | string    | No       | straight, bullnose, ogee, etc. |
| `edge_profile_sides`     | `edge_profile_sides`      | integer   | No       | 1-4 |
| `edge_profile_notes`     | `edge_profile_notes`      | string    | No       | |
| `place_of_application`   | `place_of_application`    | string    | No       | |
| `is_additional_item`     | *(transient)*             | boolean   | No       | Used to detect service items (not stored in DB) |
| `description`            | *(transient)*             | string    | No       | Used for service item detection (not stored in DB) |
| `application_collection` | *(transient)*             | string    | No       | Mapped to `application_collection_code` on OrderPosition |
| `application_method`     | *(transient)*             | string    | No       | Mapped to `application_method_code` on OrderPosition |
| `colors_for_splashing`   | *(transient)*             | list      | No       | Stored as transient attr; not yet used by position creation |
| `application_type`       | `application_type`        | string    | No       | Fallback for application method code |

### Fields PMS Ignores (Not Stored)
These Sales fields are used transiently during processing but have no dedicated DB column on `ProductionOrderItem`:
- `is_additional_item` -- used for service-item detection logic
- `description` -- used for service-item detection logic
- `application_collection` -- mapped to `application_collection_code` on `OrderPosition`
- `application_method` -- mapped to `application_method_code` on `OrderPosition`
- `colors_for_splashing` -- stored as transient attr, not yet persisted

### Fields PMS Adds Internally
- `order.document_date` -- set to `date.today()`
- `order.production_received_date` -- set to `date.today()`
- `order.status` -- `NEW` or `IN_PRODUCTION` based on position blocking
- `order.source` -- `sales_webhook`
- `order.sales_payload_json` -- full raw webhook payload
- `item.id` -- auto-generated UUID
- `position.position_number` -- sequential within order
- `position.shape` -- defaults to RECTANGLE if not provided/invalid
- `position.thickness_mm` -- copied from item thickness
- `position.recipe_id` -- auto-looked-up from recipe table
- `position.firing_round` -- always 1 for new positions
- `position.mandatory_qc` -- inherited from order
- `position.quantity_with_defect_margin` -- calculated from defect coefficient
- `position.glazeable_sqm` -- calculated from shape + dimensions
- `position.application_collection_code` -- mapped from Sales `collection` or `application_collection`
- `position.application_method_code` -- mapped from Sales `application` field via method map
- `order.schedule_deadline` -- estimated by scheduler

### Webhook Response

#### Success (new order)
```json
{
  "status": "processed",
  "order_id": "uuid",
  "factory_name": "Bali Factory",
  "factory_location": "Bali",
  "estimated_completion_date": "2026-04-15"
}
```

#### Duplicate event
```json
{
  "status": "duplicate",
  "order_id": null
}
```

#### Existing order (change request)
```json
{
  "status": "change_request_created",
  "order_id": "uuid",
  "factory_name": "Bali Factory",
  "factory_location": "Bali"
}
```

---

## B. Outgoing Webhooks (PMS -> Sales)

PMS sends status updates to Sales via `POST {SALES_APP_URL}/api/webhooks/production-status`.

### Authentication
- `Authorization: Bearer {PRODUCTION_WEBHOOK_BEARER_TOKEN}`

### Retry Logic
- 3 attempts with exponential backoff (2s, 4s, 8s)
- Failed deliveries logged to `sales_webhook_events` table

### Events Sent

#### 1. Status Change (position-level)
Triggered from: `api/routers/positions.py` on status transitions
```json
{
  "event": "status_change",
  "external_id": "sales-order-123",
  "order_number": "ORD-001",
  "position_id": "uuid",
  "old_status": "planned",
  "new_status": "glazed",
  "order_status": "in_production"
}
```

#### 2. Order Ready for Shipment
Triggered from: `api/routers/orders.py` when all positions ready
```json
{
  "event": "order_ready",
  "external_id": "...",
  "order_number": "...",
  ...
}
```

#### 3. Order Shipped
Triggered from: `api/routers/orders.py` on ship action

#### 4. Cancellation Decision
Triggered from: `api/routers/orders.py` when PM approves/rejects cancellation

### Stub Toggle
- `GET /api/integration/stubs` -- view current stub state
- `POST /api/integration/stubs` -- toggle stubs
- `intermediate_callbacks` stub: when ON, skips sending status_change webhooks

---

## C. GET /api/integration/orders/{external_id}/production-status

### Authentication
- `X-API-Key` header OR `Authorization: Bearer <token>`

### Response
```json
{
  "external_id": "sales-123",
  "order_number": "ORD-001",
  "client": "Client Name",
  "status": "in_production",
  "current_stage": "glazing",
  "factory_id": "uuid",
  "factory_name": "Bali Factory",
  "factory_location": "Bali",
  "positions_total": 5,
  "positions_ready": 2,
  "progress_percent": 40.0,
  "estimated_completion_date": "2026-04-15",
  "earliest_glazing_start": "2026-03-25",
  "latest_completion": "2026-04-10",
  "position_schedules": [
    {
      "position_number": 1,
      "status": "glazed",
      "color": "White",
      "size": "20x20",
      "quantity": 100,
      "planned_glazing_date": "2026-03-25",
      "planned_kiln_date": "2026-03-28",
      "planned_sorting_date": "2026-03-30",
      "planned_completion_date": "2026-04-05",
      "schedule_version": 1
    }
  ],
  "shipped_at": null,
  "updated_at": "2026-03-23T10:00:00Z",
  "cancellation_requested": false,
  "cancellation_decision": null,
  "cancellation_requested_at": null
}
```

### Bulk Endpoint: GET /api/integration/orders/status-updates
- Optional `since` query param (ISO date) -- only orders updated after this date
- Returns up to 200 orders
- Response: `{ "items": [...], "total": N }`
- Per-item fields: external_id, order_number, client, status, current_stage, factory_name, positions_total, positions_ready, progress_percent, estimated_completion_date, shipped_at, updated_at

---

## D. POST /api/integration/orders/{external_id}/request-cancellation

### Authentication
- `X-API-Key` header OR `Authorization: Bearer <token>`

### Payload
```json
{
  "external_id": "sales-123",
  "order_number": "ORD-001"
}
```

### Response
```json
{
  "message": "Cancellation requested",
  "cancellation_decision": "pending",
  "order_id": "uuid",
  "order_status": "in_production"
}
```

---

## E. Discrepancies Found and Fixed (2026-03-23 Audit)

### BUG FIX: application_collection / application_method / colors_for_splashing crash

**Problem:** In `api/routers/integration.py`, the `_create_order_from_webhook()` function passed
`application_collection`, `application_method`, and `colors_for_splashing` as keyword arguments
to the `ProductionOrderItem()` constructor. These fields do NOT exist as columns on the
`ProductionOrderItem` model, causing SQLAlchemy to raise `TypeError: unexpected keyword argument`.

**Root cause:** These fields were added to the webhook handler but never added to the SQLAlchemy
model. The downstream code in `order_intake.py` already handles mapping these to
`OrderPosition.application_collection_code` and `OrderPosition.application_method_code` via
`getattr()`, but the constructor crashed before that code could run.

**Fix applied:**
1. Removed the three invalid kwargs from the `ProductionOrderItem()` constructor in
   `api/routers/integration.py` (line ~1040)
2. Added transient attributes (`item._sales_application_collection`, etc.) after `db.flush()`
   so that `process_order_item()` can read them via `getattr()`
3. Updated `business/services/order_intake.py` to check `_sales_application_collection` and
   `_sales_application_method` transient attributes first

### FIX: quantity field name mismatch in order_intake.py

**Problem:** The `process_incoming_order()` in `order_intake.py` only read `quantity_pcs` from
the payload, but Sales sends the field as `quantity`. This meant orders created through this
code path would have `quantity_pcs=0` for all items.

**Fix applied:** Changed to `item_data.get("quantity_pcs") or item_data.get("quantity", 0)` in
both the sqm calculation and the `ProductionOrderItem` constructor.

### FIX: Missing shape/dimension/edge fields in order_intake.py

**Problem:** The `process_incoming_order()` code path did not pass shape, dimension, or edge
profile fields to the `ProductionOrderItem` constructor, even though the model supports them.
Only the `_create_order_from_webhook()` path in integration.py passed these fields.

**Fix applied:** Added `shape`, `length_cm`, `width_cm`, `depth_cm`, `bowl_shape`,
`shape_dimensions`, `edge_profile`, `edge_profile_sides`, `edge_profile_notes` to the
constructor in `order_intake.py`.

### FIX: Transient Sales attributes in order_intake.py path

**Problem:** The `process_incoming_order()` code path did not store `application_collection`,
`application_method`, `colors_for_splashing`, `is_additional_item`, or `description` as
transient attributes on items, so `process_order_item()` could never read them.

**Fix applied:** Added transient attribute storage after `db.flush()` in the same pattern
as the integration.py fix.

---

## F. Field Mapping: Sales -> PMS -> DB

| Sales Sends             | PMS Reads As             | Stored In (DB Column)                  |
|-------------------------|--------------------------|----------------------------------------|
| `product_type`          | `product_type`           | `production_order_items.product_type`  |
| `color`                 | `color`                  | `production_order_items.color`         |
| `color_2`               | `color_2`                | `production_order_items.color_2`       |
| `size`                  | `size`                   | `production_order_items.size`          |
| `size_width_cm`         | `size_width_cm`          | *(used for size calc, not stored)*     |
| `size_height_cm`        | `size_height_cm`         | *(used for size calc, not stored)*     |
| `quantity`              | → `quantity_pcs`         | `production_order_items.quantity_pcs`  |
| `quantity_pcs`          | `quantity_pcs`           | `production_order_items.quantity_pcs`  |
| `quantity_sqm`          | `quantity_sqm`           | `production_order_items.quantity_sqm`  |
| `collection`            | `collection`             | `production_order_items.collection`    |
| `thickness`             | → `thickness`            | `production_order_items.thickness`     |
| `thickness_mm`          | → `thickness`            | `production_order_items.thickness`     |
| `application`           | `application`            | `production_order_items.application`   |
| `finishing`             | `finishing`              | `production_order_items.finishing`     |
| `shape`                 | `shape`                  | `production_order_items.shape`         |
| `place_of_application`  | `place_of_application`   | `production_order_items.place_of_application` |
| `is_additional_item`    | *(transient)*            | *(not stored)*                         |
| `description`           | *(transient)*            | *(not stored)*                         |
| `application_collection`| *(transient)*            | `order_positions.application_collection_code` |
| `application_method`    | *(transient)*            | `order_positions.application_method_code` |
| `application_type`      | `application_type`       | `production_order_items.application_type` |

**Note:** Sales sends `application` (e.g. "SS", "BS", "Stencil") which PMS stores verbatim
on `ProductionOrderItem.application` AND maps to `OrderPosition.application_method_code` via
a lowercase lookup table. The `collection` field serves double duty: stored on the item AND
used as fallback for `OrderPosition.application_collection_code`.

---

## G. Remaining TODOs

1. **`colors_for_splashing` not persisted:** Stored as transient attribute but never written
   to any DB column. If needed for production, a column should be added to
   `ProductionOrderItem` or `OrderPosition`.

2. **`description` and `is_additional_item` not stored:** These Sales fields are only used for
   service-item detection heuristics. If they need to be queryable later, columns should be
   added.

3. **Outgoing webhook payloads not fully documented:** The exact payload shapes for
   `order_ready`, `order_shipped`, and `cancellation_decision` events should be documented
   by reading the respective handlers in `api/routers/orders.py`.

4. **No outgoing webhook for order creation:** When PMS processes a new order, it does NOT
   send a webhook back to Sales. Sales only learns the result from the synchronous webhook
   response. If Sales needs async confirmation, an outgoing webhook event should be added.

5. **`application_type` vs `application` ambiguity:** Both fields exist on `ProductionOrderItem`.
   Sales primarily sends `application` (the method code like "SS") and may or may not send
   `application_type`. The distinction and intended use should be clarified with the Sales team.
