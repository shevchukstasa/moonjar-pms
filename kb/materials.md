# Materials

## Transaction Types

All material movements are recorded as transactions. Defined in `api/enums.py` — `TransactionType`:

- `order` — purchase order placed (outgoing commitment)
- `receive` — material received from supplier
- `consume` — material consumed in production
- `reserve` — material reserved for a position
- `unreserve` — reserved material released
- `manual_write_off` — manual write-off (breakage, loss, damage, etc.)
- `inventory` — inventory adjustment (stocktake correction)

## Write-Off Reasons

When `transaction_type = manual_write_off`, a reason is required (`WriteOffReason`):

- `breakage`
- `loss`
- `damage`
- `expired`
- `adjustment`
- `other`

## Material Status per Position

Each position tracks its material status:

- `not_reserved` — materials not yet reserved
- `reserved` — materials reserved from stock
- `insufficient` — not enough stock to fulfill
- `consumed` — materials consumed in production
