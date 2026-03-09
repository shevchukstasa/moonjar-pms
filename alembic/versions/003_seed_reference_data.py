"""Seed all reference data: factories, kilns, colors, sizes, stages, etc.

Uses INSERT ... ON CONFLICT DO NOTHING — safe to run multiple times.
Data matches DATABASE_SCHEMA.sql sections 32-34 + Sales app reference data.

Revision ID: 003_seed_data
Revises: 002_missing_cols
Create Date: 2026-03-09
"""
from alembic import op
from sqlalchemy import text
import uuid

revision = "003_seed_data"
down_revision = "002_missing_cols"
branch_labels = None
depends_on = None


def _uid():
    return str(uuid.uuid4())


def upgrade() -> None:
    conn = op.get_bind()

    # ═══════════════════════════════════════════════════════════
    # 1. KILN CONSTANTS (Section 32)
    # ═══════════════════════════════════════════════════════════
    conn.execute(text("""
        INSERT INTO kiln_constants (id, constant_name, value, unit, description) VALUES
        (gen_random_uuid(), 'TILE_GAP', 1.2, 'cm', 'Gap between tiles (flat loading)'),
        (gen_random_uuid(), 'AIR_GAP', 2.0, 'cm', 'Vertical gap between kiln levels'),
        (gen_random_uuid(), 'SHELF_THICKNESS', 3.0, 'cm', 'Kiln shelf thickness'),
        (gen_random_uuid(), 'MIN_PRODUCT_SIZE', 3.0, 'cm', 'Minimum product length/width'),
        (gen_random_uuid(), 'MIN_THICKNESS', 0.8, 'cm', 'Minimum product thickness'),
        (gen_random_uuid(), 'MAX_EDGE_HEIGHT_LARGE', 15.0, 'cm', 'Max tile height on edge in Large kiln'),
        (gen_random_uuid(), 'MAX_EDGE_HEIGHT_SMALL', 30.0, 'cm', 'Max tile height on edge in Small kiln'),
        (gen_random_uuid(), 'MAX_BIG_KILN_TILE_MIN', 30.0, 'cm', 'Max min-dimension for tile in Large kiln'),
        (gen_random_uuid(), 'MAX_BIG_KILN_TILE_MAX', 40.0, 'cm', 'Max max-dimension for tile in Large kiln'),
        (gen_random_uuid(), 'SINK_COUNTERTOP_LARGE_MIN', 20.0, 'cm', 'Max min-dim for sink in Large kiln'),
        (gen_random_uuid(), 'SINK_COUNTERTOP_LARGE_MAX', 40.0, 'cm', 'Max max-dim for sink in Large kiln'),
        (gen_random_uuid(), 'FILLER_SIZE', 10.0, 'cm', 'Filler tile size in Small kiln (10x10)'),
        (gen_random_uuid(), 'FILLER_MAX_AREA', 20000.0, 'cm2', 'Max filler area (2 m2 = 20000 cm2)'),
        (gen_random_uuid(), 'FLAT_ON_EDGE_COEFFICIENT', 0.3, '', 'Flat-on-top area = 30% of shelf when edge loading'),
        (gen_random_uuid(), 'KILN_COEFF_LARGE', 0.8, '', 'Utilization coefficient for Large kiln'),
        (gen_random_uuid(), 'KILN_COEFF_SMALL', 0.92, '', 'Utilization coefficient for Small kiln')
        ON CONFLICT (constant_name) DO NOTHING
    """))

    # ═══════════════════════════════════════════════════════════
    # 2. PRODUCTION STAGES (Section 33)
    # ═══════════════════════════════════════════════════════════
    conn.execute(text("""
        INSERT INTO production_stages (id, name, "order") VALUES
        (gen_random_uuid(), 'incoming_inspection', 1),
        (gen_random_uuid(), 'pre_glazing_sorting', 2),
        (gen_random_uuid(), 'engobe', 3),
        (gen_random_uuid(), 'glazing', 4),
        (gen_random_uuid(), 'pre_kiln_inspection', 5),
        (gen_random_uuid(), 'kiln_loading', 6),
        (gen_random_uuid(), 'firing', 7),
        (gen_random_uuid(), 'unloading', 8),
        (gen_random_uuid(), 'sorting', 9),
        (gen_random_uuid(), 'packing', 10),
        (gen_random_uuid(), 'quality_check', 11),
        (gen_random_uuid(), 'ready_for_shipment', 12)
        ON CONFLICT (name) DO NOTHING
    """))

    # ═══════════════════════════════════════════════════════════
    # 3. COLLECTIONS (Section 34) — matches Sales app exactly
    # ═══════════════════════════════════════════════════════════
    conn.execute(text("""
        INSERT INTO collections (id, name) VALUES
        (gen_random_uuid(), 'Authentic'),
        (gen_random_uuid(), 'Creative'),
        (gen_random_uuid(), 'Stencil'),
        (gen_random_uuid(), 'Silkscreen'),
        (gen_random_uuid(), 'Raku'),
        (gen_random_uuid(), 'Exclusive'),
        (gen_random_uuid(), 'Gold'),
        (gen_random_uuid(), 'Top Table'),
        (gen_random_uuid(), 'Wash Basin'),
        (gen_random_uuid(), 'Mix')
        ON CONFLICT (name) DO NOTHING
    """))

    # ═══════════════════════════════════════════════════════════
    # 4. APPLICATION TYPES (Section 34) — matches Sales app
    # ═══════════════════════════════════════════════════════════
    conn.execute(text("""
        INSERT INTO application_types (id, name) VALUES
        (gen_random_uuid(), 'SS'),
        (gen_random_uuid(), 'BS'),
        (gen_random_uuid(), 'S'),
        (gen_random_uuid(), 'SB'),
        (gen_random_uuid(), 'Stencil'),
        (gen_random_uuid(), 'Silkscreen'),
        (gen_random_uuid(), 'Raku'),
        (gen_random_uuid(), 'Splashing'),
        (gen_random_uuid(), 'Gold')
        ON CONFLICT (name) DO NOTHING
    """))

    # ═══════════════════════════════════════════════════════════
    # 5. PLACES OF APPLICATION (Section 34)
    # ═══════════════════════════════════════════════════════════
    conn.execute(text("""
        INSERT INTO places_of_application (id, code, name) VALUES
        (gen_random_uuid(), 'face_only', 'Face only'),
        (gen_random_uuid(), 'edges_1', 'Edges (1)'),
        (gen_random_uuid(), 'edges_2', 'Edges (2)'),
        (gen_random_uuid(), 'all_edges', 'All edges'),
        (gen_random_uuid(), 'with_back', 'With back')
        ON CONFLICT (code) DO NOTHING
    """))

    # ═══════════════════════════════════════════════════════════
    # 6. FINISHING TYPES (Section 34)
    # ═══════════════════════════════════════════════════════════
    conn.execute(text("""
        INSERT INTO finishing_types (id, name) VALUES
        (gen_random_uuid(), 'Mix'),
        (gen_random_uuid(), 'Minimal character'),
        (gen_random_uuid(), 'Middle character'),
        (gen_random_uuid(), 'Full character'),
        (gen_random_uuid(), 'Honed')
        ON CONFLICT (name) DO NOTHING
    """))

    # ═══════════════════════════════════════════════════════════
    # 7. SIZES (Section 34) — dimensions in mm, matches Sales
    # ═══════════════════════════════════════════════════════════
    conn.execute(text("""
        INSERT INTO sizes (id, name, width_mm, height_mm) VALUES
        (gen_random_uuid(), '5x20', 50, 200),
        (gen_random_uuid(), '10x10', 100, 100),
        (gen_random_uuid(), '10x20', 100, 200),
        (gen_random_uuid(), '10x40', 100, 400),
        (gen_random_uuid(), '20x20', 200, 200),
        (gen_random_uuid(), '20x40', 200, 400)
        ON CONFLICT (name) DO NOTHING
    """))

    # ═══════════════════════════════════════════════════════════
    # 8. COLORS (Section 34) — 25 colors, matches Sales + Gold
    # ═══════════════════════════════════════════════════════════
    conn.execute(text("""
        INSERT INTO colors (id, name) VALUES
        (gen_random_uuid(), 'Burgundy'),
        (gen_random_uuid(), 'Lava Core'),
        (gen_random_uuid(), 'Raw Turmeric'),
        (gen_random_uuid(), 'Wild Honey'),
        (gen_random_uuid(), 'Mocha Nude'),
        (gen_random_uuid(), 'Rose Dust'),
        (gen_random_uuid(), 'Wabi Beige'),
        (gen_random_uuid(), 'Wild Olive'),
        (gen_random_uuid(), 'Basalt Green'),
        (gen_random_uuid(), 'Moss Glaze'),
        (gen_random_uuid(), 'Jade Dream'),
        (gen_random_uuid(), 'Matcha Leaf'),
        (gen_random_uuid(), 'Turquoise Depth'),
        (gen_random_uuid(), 'Lagoon Spark'),
        (gen_random_uuid(), 'Frost Blue'),
        (gen_random_uuid(), 'Frosted White'),
        (gen_random_uuid(), 'Milk Crackle'),
        (gen_random_uuid(), 'Soft Graphite'),
        (gen_random_uuid(), 'Lavender Ash'),
        (gen_random_uuid(), 'Velvet Fig'),
        (gen_random_uuid(), 'Raw Indigo'),
        (gen_random_uuid(), 'Black Rock'),
        (gen_random_uuid(), 'Raku Turquoise'),
        (gen_random_uuid(), 'Raku Green'),
        (gen_random_uuid(), 'Gold')
        ON CONFLICT (name) DO NOTHING
    """))

    # ═══════════════════════════════════════════════════════════
    # 9. FACTORIES — Bali + Java
    # ═══════════════════════════════════════════════════════════
    bali_id = "a0000000-0000-0000-0000-000000000001"
    java_id = "a0000000-0000-0000-0000-000000000002"

    # Insert only if not exists (no unique constraint on name → use DO NOTHING on PK)
    conn.execute(text(f"""
        INSERT INTO factories (id, name, location, timezone, region, is_active, served_locations)
        VALUES ('{bali_id}', 'Bali Factory', 'Bali, Indonesia', 'Asia/Makassar', 'bali', TRUE,
                '["Bali", "Lombok", "Nusa Penida", "Nusa Lembongan"]'::JSONB)
        ON CONFLICT (id) DO UPDATE SET
            served_locations = EXCLUDED.served_locations,
            timezone = EXCLUDED.timezone,
            region = EXCLUDED.region
    """))
    conn.execute(text(f"""
        INSERT INTO factories (id, name, location, timezone, region, is_active, served_locations)
        VALUES ('{java_id}', 'Java Factory', 'Java, Indonesia', 'Asia/Jakarta', 'java', TRUE,
                '["Java", "Sumatra", "Kalimantan", "Sulawesi", "Papua", "International"]'::JSONB)
        ON CONFLICT (id) DO UPDATE SET
            served_locations = EXCLUDED.served_locations,
            timezone = EXCLUDED.timezone,
            region = EXCLUDED.region
    """))

    # If factories existed before with different IDs, find them
    result = conn.execute(text(
        "SELECT id, name FROM factories WHERE name IN ('Bali Factory', 'Java Factory')"
    ))
    factory_map = {}
    for row in result:
        factory_map[row[1]] = str(row[0])
    bali_id = factory_map.get("Bali Factory", bali_id)
    java_id = factory_map.get("Java Factory", java_id)

    # ═══════════════════════════════════════════════════════════
    # 10. KILNS (resources) — 3 per factory
    #     Model columns: kiln_dimensions_cm (JSONB), kiln_working_area_cm (JSONB),
    #     kiln_coefficient (Numeric), kiln_multi_level (Boolean), kiln_type (String)
    # ═══════════════════════════════════════════════════════════
    kilns = [
        # (factory_id, name, kiln_type, dims_json, working_area_json, multi_level, coefficient)
        (bali_id, "Bali Large Kiln", "big",
         '{"width_cm":54,"depth_cm":84,"height_cm":80}',
         '{"width_cm":54,"depth_cm":84}',
         True, 0.80),
        (bali_id, "Bali Small Kiln", "small",
         '{"width_cm":100,"depth_cm":160,"height_cm":40}',
         '{"width_cm":100,"depth_cm":150}',
         False, 0.92),
        (bali_id, "Bali Raku Kiln", "raku",
         '{"width_cm":60,"depth_cm":100,"height_cm":40}',
         '{"width_cm":60,"depth_cm":100}',
         False, 0.85),
        (java_id, "Java Large Kiln", "big",
         '{"width_cm":54,"depth_cm":84,"height_cm":80}',
         '{"width_cm":54,"depth_cm":84}',
         True, 0.80),
        (java_id, "Java Small Kiln", "small",
         '{"width_cm":100,"depth_cm":160,"height_cm":40}',
         '{"width_cm":100,"depth_cm":150}',
         False, 0.92),
        (java_id, "Java Raku Kiln", "raku",
         '{"width_cm":60,"depth_cm":100,"height_cm":40}',
         '{"width_cm":60,"depth_cm":100}',
         False, 0.85),
    ]
    for fid, name, ktype, dims, work_area, multi, coeff in kilns:
        conn.execute(text(f"""
            INSERT INTO resources (id, factory_id, name, resource_type, kiln_type,
                kiln_dimensions_cm, kiln_working_area_cm, kiln_multi_level,
                kiln_coefficient, is_active, status)
            VALUES (gen_random_uuid(), '{fid}', '{name}', 'kiln', '{ktype}',
                '{dims}'::JSONB, '{work_area}'::JSONB, {multi},
                {coeff}, TRUE, 'active')
            ON CONFLICT DO NOTHING
        """))

    # ═══════════════════════════════════════════════════════════
    # 11. WAREHOUSE SECTIONS — 3 per factory
    # ═══════════════════════════════════════════════════════════
    sections = [
        ("workshop", "Workshop"),
        ("finished_goods", "Finished Goods"),
        ("raw_materials", "Raw Materials"),
    ]
    for fid in [bali_id, java_id]:
        fname = "Bali" if fid == bali_id else "Java"
        for code, label in sections:
            # Check if exists first (no unique constraint on code+factory)
            exists = conn.execute(text(
                f"SELECT 1 FROM warehouse_sections WHERE factory_id='{fid}' AND code='{code}' LIMIT 1"
            )).fetchone()
            if not exists:
                conn.execute(text(f"""
                    INSERT INTO warehouse_sections (id, factory_id, code, name, is_default)
                    VALUES (gen_random_uuid(), '{fid}', '{code}', '{fname} {label}', TRUE)
                """))

    # ═══════════════════════════════════════════════════════════
    # 12. SHIFTS — 2 per factory (default)
    # ═══════════════════════════════════════════════════════════
    for fid in [bali_id, java_id]:
        conn.execute(text(f"""
            INSERT INTO shifts (id, factory_id, shift_number, start_time, end_time)
            VALUES (gen_random_uuid(), '{fid}', 1, '07:00', '15:00')
            ON CONFLICT (factory_id, shift_number) DO NOTHING
        """))
        conn.execute(text(f"""
            INSERT INTO shifts (id, factory_id, shift_number, start_time, end_time)
            VALUES (gen_random_uuid(), '{fid}', 2, '15:00', '23:00')
            ON CONFLICT (factory_id, shift_number) DO NOTHING
        """))

    # ═══════════════════════════════════════════════════════════
    # 13. QUALITY ASSIGNMENT CONFIG — 3 stages per factory
    # ═══════════════════════════════════════════════════════════
    for fid in [bali_id, java_id]:
        for stage in ['glazing', 'firing', 'sorting']:
            conn.execute(text(f"""
                INSERT INTO quality_assignment_config
                    (id, factory_id, stage, base_percentage, increase_on_defect_percentage, current_percentage)
                VALUES (gen_random_uuid(), '{fid}', '{stage}', 2.0, 2.0, 2.0)
                ON CONFLICT (factory_id, stage) DO NOTHING
            """))

    print("INFO: Migration 003 — all reference data seeded.")


def downgrade() -> None:
    pass
