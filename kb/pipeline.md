# Production Pipeline

## Position Statuses

A position moves through these statuses during production (defined in `api/enums.py` — `PositionStatus`):

### Pre-production
- `planned` — initial state after order creation
- `insufficient_materials` — materials not available
- `awaiting_recipe` — recipe not yet assigned
- `awaiting_stencil_silkscreen` — waiting for stencil/silkscreen
- `awaiting_color_matching` — color matching in progress
- `awaiting_size_confirmation` — size needs confirmation
- `awaiting_consumption_data` — consumption data missing

### Glazing
- `engobe_applied` — engobe layer applied
- `engobe_check` — engobe quality check
- `sent_to_glazing` — sent to glazing station
- `glazed` — glazing complete

### Firing
- `pre_kiln_check` — pre-kiln QC checklist
- `loaded_in_kiln` — loaded into kiln for firing
- `fired` — firing complete

### Post-firing
- `transferred_to_sorting` — sent to sorting area
- `refire` — needs refiring
- `awaiting_reglaze` — needs reglazing before refire

### Quality & Packing
- `sent_to_quality_check` — sent for QC inspection
- `quality_check_done` — QC passed
- `packed` — packed and ready
- `blocked_by_qm` — blocked by quality manager

### Shipment
- `ready_for_shipment` — ready to ship
- `shipped` — shipped to customer

### Terminal
- `merged` — position merged into another (child merged back into parent)
- `cancelled` — position cancelled
