# Purchaser / Purchase Requests

## Purchase Status Flow

```
pending → approved → sent → in_transit → partially_received → received → closed
```

Defined in `api/enums.py` — `PurchaseStatus`:

- `pending` — purchase request created, awaiting approval
- `approved` — approved by manager
- `sent` — order sent to supplier
- `in_transit` — supplier confirmed dispatch
- `partially_received` — some items received, others still pending
- `received` — warehouse confirmed full receipt
- `closed` — reconciled and archived

## Allowed Transitions

From `api/routers/purchaser.py`:

| From | Allowed To |
|------|-----------|
| pending | approved |
| approved | sent, partially_received, received |
| sent | in_transit, partially_received, received |
| in_transit | partially_received, received |
| partially_received | received |
| received | closed |

## Partial Delivery

When a delivery arrives with only some items, the purchase request moves to `partially_received`. Each partial delivery is recorded and tracked. When all items are received, the status advances to `received`.
