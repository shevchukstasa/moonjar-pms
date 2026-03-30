# Kilns

## Kiln Types

The `kiln_type` field on the `resources` table is free-text (no strict enum), but the application validates against a known list:

- **big** — large kiln (high capacity)
- **small** — small kiln (lower capacity)
- **raku** — raku kiln (special firing process)

Valid types are defined in `api/routers/kilns.py`: `VALID_KILN_TYPES = ["big", "small", "raku"]`

## Kiln Loading Rules

Loading rules can target specific kiln types via the `applies_to_kiln_types` JSONB column:
- `null` — rule applies to all kiln types
- `["big", "raku"]` — rule applies only to listed types

## Kiln Statuses

- `active` — operational
- `maintenance_planned` — scheduled maintenance upcoming
- `maintenance_emergency` — emergency maintenance in progress
- `inactive` — not in use

## Seed Data

Each factory is seeded with kilns named like "{Factory} Large Kiln" (type `big`), "{Factory} Small Kiln" (type `small`), and "{Factory} Raku Kiln" (type `raku`).
