-- ============================================================
-- Moonjar PMS — Database Schema Documentation
-- Auto-maintained reference of tables, enums, and indexes
-- ============================================================

-- ────────────────────────────────────────────────────────────
-- §1  Enums (partial — recent additions)
-- ────────────────────────────────────────────────────────────

-- PositionStatus enum includes:
--   ... planned, insufficient_materials, awaiting_recipe,
--   awaiting_stencil_silkscreen, awaiting_color_matching,
--   awaiting_size_confirmation,
--   awaiting_consumption_data,          -- NEW: blocks position until PM measures consumption rate
--   engobe_applied, engobe_check, glazed, pre_kiln_check,
--   sent_to_glazing, loaded_in_kiln, fired, transferred_to_sorting,
--   refire, awaiting_reglaze, packed, sent_to_quality_check,
--   quality_check_done, ready_for_shipment, blocked_by_qm,
--   shipped, merged, cancelled

-- TaskType enum includes:
--   ... stencil_order, silk_screen_order, color_matching,
--   material_order, quality_check, kiln_maintenance,
--   showroom_transfer, photographing, mana_confirmation,
--   packing_photo, recipe_configuration, repair_sla_alert,
--   reconciliation_alert, stock_shortage, stock_transfer,
--   size_resolution, material_receiving, glazing_board_needed,
--   consumption_measurement                -- NEW: auto-created when recipe lacks required consumption rate


-- ────────────────────────────────────────────────────────────
-- §35  Kiln Inspection & Repair Log System (NEW)
-- ────────────────────────────────────────────────────────────

-- 35a. Inspection checklist template items
CREATE TABLE IF NOT EXISTS kiln_inspection_items (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category               VARCHAR(100) NOT NULL,          -- e.g. 'Frame & Stability', 'Electrical'
    item_text              VARCHAR(500) NOT NULL,          -- checklist question text
    sort_order             INTEGER NOT NULL DEFAULT 0,
    is_active              BOOLEAN NOT NULL DEFAULT TRUE,
    applies_to_kiln_types  JSONB                           -- NULL = applies to all kiln types
);

-- Seed: 35 default items across 8 categories:
--   Frame & Stability (6), Door - Hinged Kilns (4), Kiln Interior (3),
--   Heating Elements - Ceramic Tubes (4), Heating Elements - Spiral (5),
--   Thermocouple (3), Electrical (6), Other (4)


-- 35b. Inspections (one per kiln per date)
CREATE TABLE IF NOT EXISTS kiln_inspections (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_id       UUID NOT NULL REFERENCES resources(id),
    factory_id        UUID NOT NULL REFERENCES factories(id),
    inspection_date   DATE NOT NULL,
    inspected_by_id   UUID NOT NULL REFERENCES users(id),
    notes             TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_kiln_inspection_date UNIQUE (resource_id, inspection_date)
);
CREATE INDEX IF NOT EXISTS ix_kiln_inspections_date     ON kiln_inspections(inspection_date);
CREATE INDEX IF NOT EXISTS ix_kiln_inspections_resource  ON kiln_inspections(resource_id);


-- 35c. Inspection results (per item per inspection)
CREATE TABLE IF NOT EXISTS kiln_inspection_results (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    inspection_id   UUID NOT NULL REFERENCES kiln_inspections(id) ON DELETE CASCADE,
    item_id         UUID NOT NULL REFERENCES kiln_inspection_items(id),
    result          VARCHAR(20) NOT NULL,   -- ok | not_applicable | damaged | needs_repair
    notes           TEXT
);
CREATE INDEX IF NOT EXISTS ix_kiln_inspection_results_insp ON kiln_inspection_results(inspection_id);


-- 35d. Repair log (linked to inspections or standalone)
CREATE TABLE IF NOT EXISTS kiln_repair_logs (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_id           UUID NOT NULL REFERENCES resources(id),
    factory_id            UUID NOT NULL REFERENCES factories(id),
    date_reported         DATE NOT NULL DEFAULT CURRENT_DATE,
    reported_by_id        UUID NOT NULL REFERENCES users(id),
    issue_description     TEXT NOT NULL,
    diagnosis             TEXT,
    repair_actions        TEXT,
    spare_parts_used      TEXT,
    technician            VARCHAR(200),
    date_completed        DATE,
    status                VARCHAR(30) NOT NULL DEFAULT 'open',   -- open | in_progress | done
    notes                 TEXT,
    inspection_result_id  UUID REFERENCES kiln_inspection_results(id),
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_kiln_repair_logs_resource ON kiln_repair_logs(resource_id);
CREATE INDEX IF NOT EXISTS ix_kiln_repair_logs_status   ON kiln_repair_logs(status);


-- ────────────────────────────────────────────────────────────
-- §36  Production Line Resources (NEW)
-- ────────────────────────────────────────────────────────────

-- Generic resource registry for production line equipment
-- (grinding tables, glazing stations, drying racks, etc.)
CREATE TABLE IF NOT EXISTS production_line_resources (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    factory_id      UUID NOT NULL REFERENCES factories(id),
    resource_type   VARCHAR(50) NOT NULL,       -- e.g. 'grinding_table', 'glazing_station', 'drying_rack'
    name            VARCHAR(200) NOT NULL,
    capacity_sqm    NUMERIC(10,3),              -- area capacity (m2)
    capacity_boards INTEGER,                    -- board/shelf slots
    capacity_pcs    INTEGER,                    -- piece capacity
    num_units       INTEGER DEFAULT 1,
    notes           TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_prod_line_resource UNIQUE (factory_id, resource_type, name)
);


-- ────────────────────────────────────────────────────────────
-- §37  Kiln Shelves (NEW)
-- ────────────────────────────────────────────────────────────

-- Individual kiln shelf tracking — lifecycle, condition, write-off
CREATE TABLE IF NOT EXISTS kiln_shelves (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_id         UUID NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
    factory_id          UUID NOT NULL REFERENCES factories(id),
    name                VARCHAR(200) NOT NULL,
    length_cm           NUMERIC(8, 2) NOT NULL,
    width_cm            NUMERIC(8, 2) NOT NULL,
    thickness_mm        NUMERIC(6, 2) NOT NULL DEFAULT 15,
    material            VARCHAR(100) DEFAULT 'silicon_carbide',
    area_sqm            NUMERIC(10, 4) GENERATED ALWAYS AS (length_cm * width_cm / 10000.0) STORED,
    status              VARCHAR(30) NOT NULL DEFAULT 'active',  -- active | damaged | written_off
    condition_notes     TEXT,
    write_off_reason    TEXT,
    write_off_photo_url VARCHAR(500),
    written_off_at      TIMESTAMPTZ,
    written_off_by      UUID REFERENCES users(id),
    purchase_date       DATE,
    purchase_cost       NUMERIC(10, 2),
    firing_cycles_count INTEGER DEFAULT 0,
    max_firing_cycles   INTEGER,
    is_active           BOOLEAN NOT NULL DEFAULT true,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_kiln_shelves_resource ON kiln_shelves (resource_id, is_active);
CREATE INDEX idx_kiln_shelves_factory  ON kiln_shelves (factory_id, status);


-- ────────────────────────────────────────────────────────────
-- §38  Kiln Typology Capacities — zone column (ALTER)
-- ────────────────────────────────────────────────────────────

-- Adds placement zone to kiln typology capacity rows.
-- Values: 'edge', 'flat', 'filler', 'primary' (default).
ALTER TABLE kiln_typology_capacities
    ADD COLUMN IF NOT EXISTS zone VARCHAR(20) DEFAULT 'primary';
