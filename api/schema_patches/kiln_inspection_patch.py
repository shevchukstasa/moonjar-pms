"""Schema patch: kiln inspection checklists and repair log tables."""

import logging
from sqlalchemy import text

logger = logging.getLogger("moonjar.patch.kiln_inspection")


def apply_patch(conn):
    """Create kiln inspection and repair log tables + seed default checklist items."""

    # ── 1. Inspection items (template)
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS kiln_inspection_items (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            category VARCHAR(100) NOT NULL,
            item_text VARCHAR(500) NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            applies_to_kiln_types JSONB
        );
    """))

    # ── 2. Inspections (one per kiln per date)
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS kiln_inspections (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            resource_id UUID NOT NULL REFERENCES resources(id),
            factory_id UUID NOT NULL REFERENCES factories(id),
            inspection_date DATE NOT NULL,
            inspected_by_id UUID NOT NULL REFERENCES users(id),
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_kiln_inspection_date UNIQUE (resource_id, inspection_date)
        );
        CREATE INDEX IF NOT EXISTS ix_kiln_inspections_date ON kiln_inspections(inspection_date);
        CREATE INDEX IF NOT EXISTS ix_kiln_inspections_resource ON kiln_inspections(resource_id);
    """))

    # ── 3. Inspection results (per item per inspection)
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS kiln_inspection_results (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            inspection_id UUID NOT NULL REFERENCES kiln_inspections(id) ON DELETE CASCADE,
            item_id UUID NOT NULL REFERENCES kiln_inspection_items(id),
            result VARCHAR(20) NOT NULL,
            notes TEXT
        );
        CREATE INDEX IF NOT EXISTS ix_kiln_inspection_results_insp ON kiln_inspection_results(inspection_id);
    """))

    # ── 4. Repair log
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS kiln_repair_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            resource_id UUID NOT NULL REFERENCES resources(id),
            factory_id UUID NOT NULL REFERENCES factories(id),
            date_reported DATE NOT NULL DEFAULT CURRENT_DATE,
            reported_by_id UUID NOT NULL REFERENCES users(id),
            issue_description TEXT NOT NULL,
            diagnosis TEXT,
            repair_actions TEXT,
            spare_parts_used TEXT,
            technician VARCHAR(200),
            date_completed DATE,
            status VARCHAR(30) NOT NULL DEFAULT 'open',
            notes TEXT,
            inspection_result_id UUID REFERENCES kiln_inspection_results(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS ix_kiln_repair_logs_resource ON kiln_repair_logs(resource_id);
        CREATE INDEX IF NOT EXISTS ix_kiln_repair_logs_status ON kiln_repair_logs(status);
    """))

    # ── 5. Seed default inspection checklist items (idempotent)
    conn.execute(text("""
        INSERT INTO kiln_inspection_items (id, category, item_text, sort_order)
        SELECT gen_random_uuid(), v.category, v.item_text, v.sort_order
        FROM (VALUES
            -- Frame & Stability
            ('Frame & Stability', 'Kiln stands stable, no wobble', 10),
            ('Frame & Stability', 'Check lid lifting mechanism', 20),
            ('Frame & Stability', 'Check steel cable for lifting: not worn/peeling', 30),
            ('Frame & Stability', 'Check steel cable tension', 40),
            ('Frame & Stability', 'Check bolts securing lifting mechanism', 50),
            ('Frame & Stability', 'Check bolts & motor mount for lifting', 60),

            -- Door (hinged kilns)
            ('Door (Hinged Kilns)', 'Hinge in good condition, not loose', 110),
            ('Door (Hinged Kilns)', 'No cracks or breaks on hinge', 120),
            ('Door (Hinged Kilns)', 'Door closes tightly', 130),
            ('Door (Hinged Kilns)', 'Hinge fastening bolts tight', 140),

            -- Kiln Interior
            ('Kiln Interior', 'Shelves/plates not cracked', 210),
            ('Kiln Interior', 'Shelf supports not damaged', 220),
            ('Kiln Interior', 'Interior surface in normal condition', 230),

            -- Heating Elements - Ceramic Tubes
            ('Heating Elements - Ceramic Tubes', 'Ceramic tubes intact, not cracked', 310),
            ('Heating Elements - Ceramic Tubes', 'No tubes sagging or drooping', 320),
            ('Heating Elements - Ceramic Tubes', 'Tubes installed properly and evenly', 330),
            ('Heating Elements - Ceramic Tubes', 'No tubes displaced from their seats', 340),

            -- Heating Elements - Spiral
            ('Heating Elements - Spiral', 'No breaks in spiral', 410),
            ('Heating Elements - Spiral', 'No thinning or excessive burning', 420),
            ('Heating Elements - Spiral', 'Spiral evenly distributed', 430),
            ('Heating Elements - Spiral', 'No spirals touching each other', 440),
            ('Heating Elements - Spiral', 'No spiral touching tubes or walls', 450),

            -- Thermocouple
            ('Thermocouple', 'Thermocouple properly installed', 510),
            ('Thermocouple', 'No oxidation or burning', 520),
            ('Thermocouple', 'Sensor tip length correct (not too deep/shallow)', 530),

            -- Electrical
            ('Electrical', 'Clamps/connectors tightened', 610),
            ('Electrical', 'Power cables not cracked or bent', 620),
            ('Electrical', 'No signs of hot/burnt cables', 630),
            ('Electrical', 'Controller & relay no burning smell', 640),
            ('Electrical', 'MCB/fuse not frequently tripping', 650),
            ('Electrical', 'Grounding connected', 660),

            -- Other
            ('Other', 'No burning smell', 710),
            ('Other', 'Kiln area clean', 720),
            ('Other', 'Tools & gloves available', 730),
            ('Other', 'Inspection notes filled', 740)
        ) AS v(category, item_text, sort_order)
        WHERE NOT EXISTS (SELECT 1 FROM kiln_inspection_items LIMIT 1);
    """))

    logger.info("PATCH | kiln_inspection tables created + checklist items seeded")
