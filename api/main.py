"""
Moonjar PMS — FastAPI application entry point.
"""

import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from contextlib import asynccontextmanager
import logging

from api.config import get_settings
from api.database import engine, Base

settings = get_settings()
logger = logging.getLogger("moonjar")

IS_PRODUCTION = os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("ENV", "").lower() == "production"

# --- Router imports ---
from api.routers import auth
from api.routers import orders
from api.routers import positions
from api.routers import schedule
from api.routers import materials
from api.routers import recipes
from api.routers import quality
from api.routers import defects
from api.routers import tasks
from api.routers import suppliers
from api.routers import integration
from api.routers import users
from api.routers import factories
from api.routers import kilns
from api.routers import kiln_maintenance
from api.routers import kiln_constants
from api.routers import reference
from api.routers import toc
from api.routers import tps
from api.routers import notifications
from api.routers import analytics
from api.routers import ai_chat
from api.routers import export
from api.routers import reports
from api.routers import stages
from api.routers import transcription
from api.routers import telegram
from api.routers import health
from api.routers import purchaser
from api.routers import kiln_loading_rules
from api.routers import kiln_firing_schedules
from api.routers import dashboard_access
from api.routers import notification_preferences
from api.routers import financials
from api.routers import warehouse_sections
from api.routers import reconciliations
from api.routers import qm_blocks
from api.routers import problem_cards
from api.routers import security
from api.routers import ws
from api.routers import packing_photos
from api.routers import finished_goods
from api.routers import firing_profiles
from api.routers import cleanup


def _ensure_schema():
    """Direct SQL: add any missing columns/tables that Alembic migrations failed to apply.
    Uses IF NOT EXISTS / IF EXISTS — safe to run every startup.
    Each section commits independently so one failure doesn't block others."""
    from sqlalchemy import text
    import json as json_mod

    def _run_section(section_name, fn):
        """Run a schema section with its own connection + commit."""
        try:
            with engine.connect() as conn:
                fn(conn)
                conn.commit()
                logger.info(f"_ensure_schema [{section_name}]: OK")
        except Exception as e:
            logger.error(f"_ensure_schema [{section_name}] FAILED: {e}", exc_info=True)

    # --- Section 1: Missing columns ---
    def _add_columns(conn):
        add_cols = [
            ("order_positions", "firing_round INTEGER NOT NULL DEFAULT 1"),
            ("order_positions", "quantity_sqm NUMERIC(10,3)"),
            ("order_positions", "color_2 VARCHAR(200)"),
            ("production_order_items", "color_2 VARCHAR(100)"),
            ("tasks", "metadata_json JSONB"),
            ("colors", "is_basic BOOLEAN NOT NULL DEFAULT FALSE"),
            ("production_orders", "shipped_at TIMESTAMPTZ"),
            ("production_orders", "sales_manager_contact VARCHAR(300)"),
            ("production_orders", "cancellation_requested BOOLEAN NOT NULL DEFAULT FALSE"),
            ("production_orders", "cancellation_requested_at TIMESTAMPTZ"),
            ("production_orders", "cancellation_decision VARCHAR(20)"),
            ("production_orders", "cancellation_decided_at TIMESTAMPTZ"),
            ("production_orders", "cancellation_decided_by UUID REFERENCES users(id)"),
            ("production_orders", "change_req_payload JSONB"),
            ("production_orders", "change_req_status VARCHAR(20) NOT NULL DEFAULT 'none'"),
            ("production_orders", "change_req_requested_at TIMESTAMPTZ"),
            ("production_orders", "change_req_decided_at TIMESTAMPTZ"),
            ("production_orders", "change_req_decided_by UUID REFERENCES users(id)"),
            ("factories", "served_locations JSONB"),
            ("batches", "firing_profile_id UUID"),
            ("batches", "target_temperature INTEGER"),
            # Position numbering — sequential per order
            ("order_positions", "position_number INTEGER"),
            ("order_positions", "split_index INTEGER"),
            # Recipe type fields
            ("recipes", "recipe_type VARCHAR(20) NOT NULL DEFAULT 'product'"),
            ("recipes", "color_type VARCHAR(20)"),
            ("recipes", "glaze_settings JSONB NOT NULL DEFAULT '{}'"),
            # Shape dimensions for glazeable surface area calculation
            ("order_positions", "length_cm NUMERIC(7,2)"),
            ("order_positions", "width_cm NUMERIC(7,2)"),
            ("order_positions", "depth_cm NUMERIC(7,2)"),
            ("order_positions", "bowl_shape VARCHAR(20)"),
            ("order_positions", "glazeable_sqm NUMERIC(10,4)"),
            ("production_order_items", "shape VARCHAR(20)"),
            ("production_order_items", "length_cm NUMERIC(7,2)"),
            ("production_order_items", "width_cm NUMERIC(7,2)"),
            ("production_order_items", "depth_cm NUMERIC(7,2)"),
            ("production_order_items", "bowl_shape VARCHAR(20)"),
        ]
        for table, col_def in add_cols:
            try:
                conn.execute(text(f"""
                    DO $$ BEGIN
                        IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}') THEN
                            ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col_def};
                        END IF;
                    END $$
                """))
            except Exception as e:
                logger.warning(f"_ensure_schema: skip {table}.{col_def.split()[0]}: {e}")

    _run_section("columns", _add_columns)

    # --- Section 1a: Enum value additions (AUTOCOMMIT required by PostgreSQL) ---
    # ALTER TYPE ... ADD VALUE cannot run inside a transaction.
    _enum_values_to_add = [
        ("notification_type", "cancellation_request"),
        ("notification_type", "change_request"),   # pre-add for future use
        # New split category for tiles that need re-firing without re-glazing
        ("split_category", "refire"),
        # Octagon shape for glaze surface area calculation
        ("shape_type", "octagon"),
    ]
    try:
        raw_conn = engine.raw_connection()
        try:
            raw_conn.set_isolation_level(0)  # AUTOCOMMIT
            cur = raw_conn.cursor()
            for enum_type, enum_val in _enum_values_to_add:
                try:
                    cur.execute(
                        f"ALTER TYPE {enum_type} ADD VALUE IF NOT EXISTS %s",
                        (enum_val,),
                    )
                    logger.info(f"_ensure_schema [enum]: ensured {enum_type}.{enum_val}")
                except Exception as e:
                    logger.warning(f"_ensure_schema [enum]: skip {enum_type}.{enum_val}: {e}")
            cur.close()
        finally:
            raw_conn.close()
    except Exception as e:
        logger.error(f"_ensure_schema [enum]: failed to obtain raw connection: {e}")

    # --- Section 1b: Backfill position_number / split_index for existing rows ---
    def _backfill_position_numbers(conn):
        # Root positions: assign sequential numbers within each order by created_at
        conn.execute(text("""
            UPDATE order_positions op
            SET position_number = sub.rn
            FROM (
                SELECT id,
                       ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY created_at, id) AS rn
                FROM order_positions
                WHERE parent_position_id IS NULL
            ) sub
            WHERE op.id = sub.id
              AND op.position_number IS NULL
        """))
        # Split sub-positions: assign sequential split_index within each parent
        conn.execute(text("""
            UPDATE order_positions op
            SET split_index = sub.rn
            FROM (
                SELECT id,
                       ROW_NUMBER() OVER (PARTITION BY parent_position_id ORDER BY created_at, id) AS rn
                FROM order_positions
                WHERE parent_position_id IS NOT NULL
            ) sub
            WHERE op.id = sub.id
              AND op.split_index IS NULL
        """))

    _run_section("position_numbers_backfill", _backfill_position_numbers)

    # --- Section 2: Missing tables ---
    def _create_tables(conn):
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS firing_profiles (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                factory_id UUID NOT NULL REFERENCES factories(id),
                name VARCHAR(200) NOT NULL, description TEXT,
                max_temperature INTEGER NOT NULL DEFAULT 1000,
                min_temperature INTEGER NOT NULL DEFAULT 0,
                duration_hours NUMERIC(6,2) NOT NULL DEFAULT 24,
                cooling_hours NUMERIC(6,2) NOT NULL DEFAULT 12,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                metadata_json JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS recipe_firing_stages (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                recipe_id UUID NOT NULL, stage_order INTEGER NOT NULL DEFAULT 1,
                target_temperature INTEGER NOT NULL, hold_minutes INTEGER NOT NULL DEFAULT 60,
                ramp_rate NUMERIC(5,1), atmosphere VARCHAR(50), notes TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS finished_goods_stock (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                factory_id UUID NOT NULL REFERENCES factories(id),
                position_id UUID REFERENCES order_positions(id),
                color VARCHAR(200), size VARCHAR(100), collection VARCHAR(200),
                quantity INTEGER NOT NULL DEFAULT 0, quantity_sqm NUMERIC(10,3),
                location VARCHAR(200), notes TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS rag_embeddings (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                content_type VARCHAR(50) NOT NULL, content_id UUID,
                content_text TEXT NOT NULL, embedding BYTEA,
                metadata_json JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        # Ensure warehouse_sections exists (may be missing if 001 migration failed)
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS warehouse_sections (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                factory_id UUID NOT NULL REFERENCES factories(id),
                code VARCHAR(100) NOT NULL,
                name VARCHAR(200) NOT NULL,
                is_default BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        # Ensure shifts table exists
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS shifts (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                factory_id UUID NOT NULL REFERENCES factories(id),
                shift_number INTEGER NOT NULL,
                start_time VARCHAR(10) NOT NULL,
                end_time VARCHAR(10) NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(factory_id, shift_number)
            )
        """))
        # Shape consumption coefficients — maps (shape, product_type) → coefficient
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS shape_consumption_coefficients (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                shape VARCHAR(20) NOT NULL,
                product_type VARCHAR(20) NOT NULL DEFAULT 'tile',
                coefficient NUMERIC(5,3) NOT NULL DEFAULT 1.0,
                description TEXT,
                updated_by UUID REFERENCES users(id),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE(shape, product_type)
            )
        """))
        # Consumption adjustments — actual vs expected material usage
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS consumption_adjustments (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                factory_id UUID NOT NULL REFERENCES factories(id),
                position_id UUID NOT NULL REFERENCES order_positions(id),
                material_id UUID NOT NULL REFERENCES materials(id),
                expected_qty NUMERIC(12,4) NOT NULL,
                actual_qty NUMERIC(12,4) NOT NULL,
                variance_pct NUMERIC(7,2),
                shape VARCHAR(20),
                product_type VARCHAR(20),
                suggested_coefficient NUMERIC(5,3),
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                approved_by UUID REFERENCES users(id),
                approved_at TIMESTAMPTZ,
                notes TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
        # Ensure quality_assignment_config exists
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS quality_assignment_config (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                factory_id UUID NOT NULL REFERENCES factories(id),
                stage VARCHAR(100) NOT NULL,
                base_percentage NUMERIC(5,2) NOT NULL DEFAULT 2.0,
                increase_on_defect_percentage NUMERIC(5,2) NOT NULL DEFAULT 2.0,
                current_percentage NUMERIC(5,2) NOT NULL DEFAULT 2.0,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(factory_id, stage)
            )
        """))

    _run_section("tables", _create_tables)

    # --- Section 3: Get factory IDs (needed for all seed sections) ---
    factory_ids = {}  # {"Bali Factory": "uuid", ...}
    try:
        with engine.connect() as conn:
            rows = conn.execute(text("SELECT id, name FROM factories WHERE is_active = TRUE")).fetchall()
            for row in rows:
                factory_ids[row[1]] = str(row[0])
            logger.info(f"_ensure_schema [factories]: found {list(factory_ids.keys())}")
    except Exception as e:
        logger.error(f"_ensure_schema [factories]: {e}")
        return  # Can't seed without factories

    if not factory_ids:
        logger.warning("_ensure_schema: no active factories found — skipping seed data")
        return

    # --- Section 4: Warehouse sections ---
    def _seed_warehouse(conn):
        for fname, fid in factory_ids.items():
            prefix = fname.replace(" Factory", "")  # "Bali Factory" → "Bali"
            for code, label in [("workshop", "Workshop"), ("finished_goods", "Finished Goods"), ("raw_materials", "Raw Materials")]:
                conn.execute(text(
                    "INSERT INTO warehouse_sections (id, factory_id, code, name, is_default) "
                    "SELECT gen_random_uuid(), :fid, :code, :name, TRUE "
                    "WHERE NOT EXISTS (SELECT 1 FROM warehouse_sections WHERE factory_id = :fid AND code = :code)"
                ), {"fid": fid, "code": code, "name": f"{prefix} {label}"})

    _run_section("warehouse_sections", _seed_warehouse)

    # --- Section 5: Shifts ---
    def _seed_shifts(conn):
        for fname, fid in factory_ids.items():
            conn.execute(text(
                "INSERT INTO shifts (id, factory_id, shift_number, start_time, end_time) "
                "VALUES (gen_random_uuid(), :fid, 1, '07:00', '15:00') "
                "ON CONFLICT (factory_id, shift_number) DO NOTHING"
            ), {"fid": fid})
            conn.execute(text(
                "INSERT INTO shifts (id, factory_id, shift_number, start_time, end_time) "
                "VALUES (gen_random_uuid(), :fid, 2, '15:00', '23:00') "
                "ON CONFLICT (factory_id, shift_number) DO NOTHING"
            ), {"fid": fid})

    _run_section("shifts", _seed_shifts)

    # --- Section 6: Quality assignment config ---
    def _seed_qc_config(conn):
        for fname, fid in factory_ids.items():
            for stage in ['glazing', 'firing', 'sorting']:
                conn.execute(text(
                    "INSERT INTO quality_assignment_config (id, factory_id, stage, base_percentage, increase_on_defect_percentage, current_percentage) "
                    "VALUES (gen_random_uuid(), :fid, :stage, 2.0, 2.0, 2.0) "
                    "ON CONFLICT (factory_id, stage) DO NOTHING"
                ), {"fid": fid, "stage": stage})

    _run_section("qc_config", _seed_qc_config)

    # --- Section 6b: Shape consumption coefficients ---
    def _seed_shape_coefficients(conn):
        """Seed default shape-to-area conversion coefficients.
        coefficient = actual_area / bounding_box_area
        E.g. circle inscribed in square: π/4 ≈ 0.785
        """
        coefficients = [
            # Tiles
            ("rectangle", "tile", 1.0, "Rectangle: full bounding box"),
            ("square", "tile", 1.0, "Square: full bounding box"),
            ("round", "tile", 0.785, "Circle: π/4 of bounding box"),
            ("triangle", "tile", 0.5, "Triangle: half of bounding box"),
            ("octagon", "tile", 0.828, "Regular octagon: 2(1+√2)s²/bbox"),
            ("freeform", "tile", 0.85, "Freeform: estimated 85% of bbox"),
            # Countertops (same as tiles for flat surfaces)
            ("rectangle", "countertop", 1.0, "Rectangle countertop"),
            ("round", "countertop", 0.785, "Round countertop"),
            ("freeform", "countertop", 0.85, "Freeform countertop"),
            # Sinks (include interior bowl — coefficient > 1.0)
            ("rectangle", "sink", 1.5, "Rectangular sink: flat + bowl interior"),
            ("round", "sink", 1.3, "Round sink: flat + bowl interior"),
            ("freeform", "sink", 1.4, "Freeform sink: estimated with bowl"),
            # 3D products
            ("freeform", "3d", 0.9, "3D product: estimated surface"),
        ]
        for shape, ptype, coeff, desc in coefficients:
            conn.execute(text(
                "INSERT INTO shape_consumption_coefficients (id, shape, product_type, coefficient, description) "
                "VALUES (gen_random_uuid(), :shape, :ptype, :coeff, :desc) "
                "ON CONFLICT (shape, product_type) DO NOTHING"
            ), {"shape": shape, "ptype": ptype, "coeff": coeff, "desc": desc})

    _run_section("shape_coefficients", _seed_shape_coefficients)

    # --- Section 7: Kilns (resources) — 3 per factory (one-time only) ---
    def _seed_kilns(conn):
        """
        Seeds 3 default kilns per factory ONLY on first setup.
        Once a factory has ANY kilns (active or not), or once the
        'kilns_seeded' flag is set in factory.settings, we never touch
        the kilns again — the user's manual changes are preserved.
        """
        import json as _j
        for fname, fid in factory_ids.items():
            # Check if kilns were already seeded for this factory
            frow = conn.execute(text(
                "SELECT settings FROM factories WHERE id = :fid"
            ), {"fid": fid}).fetchone()
            settings = (frow[0] if frow and frow[0] else {}) or {}
            if settings.get("kilns_seeded"):
                logger.debug(f"_seed_kilns: factory {fname} already configured, skip")
                continue  # User has manually configured kilns — never overwrite

            # Also skip if ANY kiln resource already exists for this factory
            kiln_count = conn.execute(text(
                "SELECT COUNT(*) FROM resources WHERE factory_id = :fid AND resource_type = 'kiln'"
            ), {"fid": fid}).scalar() or 0
            if kiln_count > 0:
                # Mark as seeded so we won't check again on future deploys
                settings["kilns_seeded"] = True
                conn.execute(text(
                    "UPDATE factories SET settings = cast(:s as JSONB) WHERE id = :fid"
                ), {"s": _j.dumps(settings), "fid": fid})
                continue

            prefix = fname.replace(" Factory", "")
            kilns_data = [
                (f"{prefix} Large Kiln", "big",
                 {"width_cm": 54, "depth_cm": 84, "height_cm": 80},
                 {"width_cm": 54, "depth_cm": 84}, True, 0.80),
                (f"{prefix} Small Kiln", "small",
                 {"width_cm": 100, "depth_cm": 160, "height_cm": 40},
                 {"width_cm": 100, "depth_cm": 150}, False, 0.92),
                (f"{prefix} Raku Kiln", "raku",
                 {"width_cm": 60, "depth_cm": 100, "height_cm": 40},
                 {"width_cm": 60, "depth_cm": 100}, False, 0.85),
            ]
            for kname, ktype, dims, work_area, multi, coeff in kilns_data:
                conn.execute(text(
                    "INSERT INTO resources (id, factory_id, name, resource_type, kiln_type, "
                    "kiln_dimensions_cm, kiln_working_area_cm, kiln_multi_level, "
                    "kiln_coefficient, is_active, status) "
                    "VALUES (gen_random_uuid(), :fid, :kname, 'kiln', :ktype, "
                    "cast(:dims as JSONB), cast(:work_area as JSONB), :multi, :coeff, TRUE, 'active') "
                    "ON CONFLICT DO NOTHING"
                ), {
                    "fid": fid, "kname": kname, "ktype": ktype,
                    "dims": json_mod.dumps(dims), "work_area": json_mod.dumps(work_area),
                    "multi": multi, "coeff": coeff,
                })
            # Mark factory kilns as seeded
            settings["kilns_seeded"] = True
            conn.execute(text(
                "UPDATE factories SET settings = cast(:s as JSONB) WHERE id = :fid"
            ), {"s": _j.dumps(settings), "fid": fid})
            logger.info(f"_seed_kilns: seeded 3 default kilns for {fname}")

    _run_section("kilns", _seed_kilns)

    # --- Section 7b: RESTORE kilns accidentally deactivated by a prior deploy ---
    def _restore_deactivated_kilns(conn):
        """
        A prior version of _ensure_schema ran _cleanup_duplicate_kilns which
        deactivated kilns named "Large Kiln", "Small Kiln", "Raku Kiln".
        Those are the user-configured kilns from migration 003.
        Re-activate them so the user's setup is preserved.
        """
        restored = []
        for old_name in ["Large Kiln", "Small Kiln", "Raku Kiln"]:
            result = conn.execute(text(
                "UPDATE resources SET is_active = TRUE, status = CASE "
                "  WHEN status = 'inactive' THEN 'active' ELSE status END "
                "WHERE name = :name AND resource_type = 'kiln' AND is_active = FALSE"
            ), {"name": old_name})
            if result.rowcount > 0:
                restored.append(old_name)
        if restored:
            logger.info(f"_restore_deactivated_kilns: re-activated {restored}")
        else:
            logger.debug("_restore_deactivated_kilns: nothing to restore")

    _run_section("restore_kilns", _restore_deactivated_kilns)

    # --- Section 8b: Seed New Collection glaze recipes ---
    def _seed_glaze_recipes(conn):
        """
        Idempotent seed for New Collection glaze formulas.
        Stores ingredient fractions (quantity_per_unit = fraction of dry batch).
        """
        import json as _json

        GLAZE_DATA = [
            {
                "name": "Wabi Beige", "reference_batch_g": 500, "water_fraction": 0.6,
                "coverage_note": "450ml/2papan", "special_kiln": None,
                "ingredients": [
                    ("Fritt Tomat", 0.2), ("Fritt Kasm", 0.8),
                    ("Black pigment", 0.0004), ("Yellow pigment", 0.0015),
                    ("Golden brown", 0.0012), ("Bentonite", 0.01), ("Water", 0.6),
                ],
            },
            {
                "name": "Frosted White", "reference_batch_g": 200, "water_fraction": 0.6,
                "coverage_note": "450ml/2papan", "special_kiln": None,
                "ingredients": [
                    ("Fritt Tomat", 0.2), ("Fritt Kasm", 0.8),
                    ("Bentonite", 0.01), ("Water", 0.6),
                ],
            },
            {
                "name": "Matcha Leaf", "reference_batch_g": 11000, "water_fraction": 0.6,
                "coverage_note": "450ml/2papan; large batch for pigment precision", "special_kiln": None,
                "ingredients": [
                    ("Fritt Tomat", 0.2), ("Fritt Kasm", 0.8),
                    ("Green 9444", 0.008), ("Yellow 9433", 0.03),
                    ("Bentonite", 0.01), ("Water", 0.6),
                ],
            },
            {
                "name": "Frost Blue", "reference_batch_g": 300, "water_fraction": 0.6,
                "coverage_note": "450ml/2papan", "special_kiln": None,
                "ingredients": [
                    ("Fritt Tomat", 0.2), ("Fritt Kasm", 0.8),
                    ("Turquoise 9411", 0.005), ("Bentonite", 0.01), ("Water", 0.6),
                ],
            },
            {
                "name": "Lavender Ash", "reference_batch_g": 200, "water_fraction": 0.6,
                "coverage_note": "450ml/2papan", "special_kiln": None,
                "ingredients": [
                    ("Fritt Tomat", 0.2), ("Fritt Kasm", 0.8),
                    ("Grey pigment", 0.012), ("Violet 9474", 0.027),
                    ("Bentonite", 0.01), ("Water", 0.6),
                ],
            },
            {
                "name": "Mocha Mousse", "reference_batch_g": 200, "water_fraction": 0.6,
                "coverage_note": "450ml/2papan", "special_kiln": None,
                "ingredients": [
                    ("Fritt Tomat", 0.2), ("Fritt Kasm", 0.8),
                    ("Golden brown", 0.008), ("Violet 9474", 0.018),
                    ("Bentonite", 0.01), ("Water", 0.6),
                ],
            },
            {
                "name": "Wild Olive", "reference_batch_g": 200, "water_fraction": 0.6,
                "coverage_note": None, "special_kiln": None,
                "ingredients": [
                    ("Fritt Tomat", 0.2), ("Fritt Kasm", 0.8),
                    ("Green pigment", 0.02), ("Golden brown", 0.03),
                    ("Bentonite", 0.01), ("Water", 0.6),
                ],
            },
            {
                "name": "Milk Crackle", "reference_batch_g": 500, "water_fraction": 0.6,
                "coverage_note": None, "special_kiln": None,
                "ingredients": [
                    ("Fritt Tomat", 0.2), ("Fritt Kasm", 0.8),
                    ("Zircosil", 0.1), ("Golden brown", 0.0015), ("Water", 0.6),
                ],
            },
            {
                "name": "Jade Mist", "reference_batch_g": 800, "water_fraction": 0.6,
                "coverage_note": None, "special_kiln": None,
                "ingredients": [
                    ("Fritt Tomat", 0.2), ("Fritt Kasm", 0.8),
                    ("Copper carbonate", 0.016), ("Iron oxide", 0.05),
                    ("Bentonite", 0.01), ("Water", 0.6),
                ],
            },
            {
                "name": "Lagoon Spark", "reference_batch_g": 6000, "water_fraction": 0.7,
                "coverage_note": "500ml/2papan", "special_kiln": "New kiln 1012\u00b0C \u2013 5 min hold",
                "ingredients": [
                    ("Fritt Tomat", 0.9), ("Kaolin", 0.1),
                    ("Copper carbonate", 0.05), ("Sodium silicate", 0.006),
                    ("CMC", 0.0015), ("Water", 0.7),
                ],
            },
            {
                "name": "Rose Dust", "reference_batch_g": 400, "water_fraction": 0.6,
                "coverage_note": None, "special_kiln": None,
                "ingredients": [
                    ("Fritt Tomat", 0.2), ("Fritt Kasm", 0.8),
                    ("Coral pigment", 0.004), ("Violet", 0.0024),
                    ("Bentonite", 0.01), ("Water", 0.6),
                ],
            },
            {
                "name": "Wild Honey", "reference_batch_g": 100, "water_fraction": 0.6,
                "coverage_note": None, "special_kiln": None,
                "ingredients": [
                    ("Fritt Tomat", 0.2), ("Fritt Kasm", 0.8),
                    ("Orange pigment", 0.005), ("Yellow pigment", 0.045),
                    ("Bentonite", 0.01), ("Water", 0.6),
                ],
            },
        ]

        created_recipes = 0
        created_materials = 0
        created_rm = 0

        for r in GLAZE_DATA:
            # 1. Create Recipe if not exists (match by name)
            existing = conn.execute(
                text("SELECT id FROM recipes WHERE name = :name"), {"name": r["name"]}
            ).fetchone()
            if existing:
                recipe_id = str(existing[0])
                # Backfill recipe_type / color_type if they were seeded before these columns existed
                conn.execute(text(
                    "UPDATE recipes SET recipe_type='glaze', color_type='base' "
                    "WHERE id = :id AND (recipe_type = 'product' OR color_type IS NULL)"
                ), {"id": recipe_id})
            else:
                recipe_id = str(__import__('uuid').uuid4())
                desc = _json.dumps({
                    "reference_batch_g": r["reference_batch_g"],
                    "water_fraction": r["water_fraction"],
                    "coverage_note": r["coverage_note"],
                    "special_kiln": r["special_kiln"],
                    "source": "new_collection spreadsheet",
                }, ensure_ascii=False)
                # Default glaze_settings: use defaults for g→ml and consumption
                glaze_settings = _json.dumps({
                    "grams_to_ml_use_default": True,
                    "grams_to_ml_ratio": None,
                    "consumption_use_default": True,
                    "consumption_ml_per_sqm": None,
                })
                conn.execute(text(
                    "INSERT INTO recipes (id, name, collection, color, description, "
                    "recipe_type, color_type, glaze_settings, is_active, created_at, updated_at) "
                    "VALUES (:id, :name, 'new_collection', :color, :desc, "
                    "'glaze', 'base', cast(:gs as JSONB), TRUE, NOW(), NOW())"
                ), {
                    "id": recipe_id, "name": r["name"], "color": r["name"],
                    "desc": desc, "gs": glaze_settings,
                })
                created_recipes += 1

            # 2. Create materials (global catalog) + link to recipe
            for ing_name, fraction in r["ingredients"]:
                # Ensure material exists in global catalog (no factory_id since migration 006)
                mat_row = conn.execute(text(
                    "SELECT id FROM materials WHERE name = :n"
                ), {"n": ing_name}).fetchone()
                if mat_row:
                    mat_id = str(mat_row[0])
                else:
                    mat_id = str(__import__('uuid').uuid4())
                    conn.execute(text(
                        "INSERT INTO materials (id, name, unit, material_type, created_at, updated_at) "
                        "VALUES (:id, :name, 'kg', 'glaze_ingredient', NOW(), NOW())"
                    ), {"id": mat_id, "name": ing_name})
                    created_materials += 1

                    # Create stock entries for each factory
                    for factory_id in factory_ids.values():
                        conn.execute(text(
                            "INSERT INTO material_stock (id, material_id, factory_id, balance, min_balance, "
                            "warehouse_section, created_at, updated_at) "
                            "VALUES (:id, :mid, :fid, 0, 0, 'raw_materials', NOW(), NOW()) "
                            "ON CONFLICT DO NOTHING"
                        ), {"id": str(__import__('uuid').uuid4()), "mid": mat_id, "fid": factory_id})

                # Link recipe ↔ material
                grams_in_ref = round(fraction * r["reference_batch_g"], 4)
                conn.execute(text(
                    "INSERT INTO recipe_materials (id, recipe_id, material_id, quantity_per_unit, unit, notes) "
                    "SELECT :id, :rid, :mid, :qty, 'g_per_100g', :notes "
                    "WHERE NOT EXISTS ("
                    "  SELECT 1 FROM recipe_materials WHERE recipe_id = :rid AND material_id = :mid"
                    ")"
                ), {
                    "id": str(__import__('uuid').uuid4()),
                    "rid": recipe_id, "mid": mat_id,
                    "qty": round(fraction * 100, 4),
                    "notes": f"{grams_in_ref}g per {r['reference_batch_g']}g ref batch",
                })
                created_rm += 1  # approximate — includes both new and existing

        logger.info(
            "_ensure_schema [glaze_recipes]: recipes+=%d materials+=%d recipe_materials~%d",
            created_recipes, created_materials, created_rm,
        )

    _run_section("glaze_recipes", _seed_glaze_recipes)

    # --- Section 8: Stamp alembic version ---
    def _stamp_alembic(conn):
        conn.execute(text("""
            UPDATE alembic_version SET version_num = '003_seed_data'
            WHERE version_num IN ('001_initial', '002_missing_cols')
        """))

    _run_section("alembic_stamp", _stamp_alembic)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown events."""
    logger.info("Moonjar PMS starting up...")
    # Create tables if needed (dev only; production uses Alembic migrations)
    if not IS_PRODUCTION:
        from api.database import engine, Base
        Base.metadata.create_all(bind=engine)
        logger.info("Dev mode: create_all executed")

    # Ensure schema is complete (handles cases where Alembic migrations fail)
    _ensure_schema()

    # Start background scheduler
    from api.scheduler import setup_scheduler
    sched = setup_scheduler()

    yield

    # Shutdown scheduler
    sched.shutdown(wait=False)
    logger.info("Moonjar PMS shutting down...")


app = FastAPI(
    title="Moonjar PMS API",
    version="1.0.0",
    description="Production Management System for stone products",
    lifespan=lifespan,
    redirect_slashes=False,
)


# --- Proxy headers (Railway runs behind a reverse proxy) ---
# In production, trust only known proxy IPs; in dev, trust all for convenience.
_trusted = ["127.0.0.1", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"] if IS_PRODUCTION else ["*"]
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=_trusted)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-CSRF-Token"],
)

# --- CSRF + Rate limiting + Request logging middleware ---
from api.middleware import CSRFMiddleware, RateLimitMiddleware, RequestLoggingMiddleware

app.add_middleware(CSRFMiddleware)
app.add_middleware(RateLimitMiddleware)
if IS_PRODUCTION:
    app.add_middleware(RequestLoggingMiddleware)


# --- Global exception handler ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)

    if IS_PRODUCTION:
        # Never expose internals in production
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    # Dev mode — include details for debugging
    import traceback
    tb = traceback.format_exc()
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"{type(exc).__name__}: {exc}",
            "path": str(request.url.path),
            "traceback": tb[-1000:] if tb else None,
        },
    )


# --- Mount routers ---
def setup_routers():
    """Mount all API routers."""
    app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
    app.include_router(orders.router, prefix="/api/orders", tags=["orders"])
    app.include_router(positions.router, prefix="/api/positions", tags=["positions"])
    app.include_router(schedule.router, prefix="/api/schedule", tags=["schedule"])
    app.include_router(materials.router, prefix="/api/materials", tags=["materials"])
    app.include_router(recipes.router, prefix="/api/recipes", tags=["recipes"])
    app.include_router(quality.router, prefix="/api/quality", tags=["quality"])
    app.include_router(defects.router, prefix="/api/defects", tags=["defects"])
    app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
    app.include_router(suppliers.router, prefix="/api/suppliers", tags=["suppliers"])
    app.include_router(integration.router, prefix="/api/integration", tags=["integration"])
    app.include_router(users.router, prefix="/api/users", tags=["users"])
    app.include_router(factories.router, prefix="/api/factories", tags=["factories"])
    app.include_router(kilns.router, prefix="/api/kilns", tags=["kilns"])
    app.include_router(kiln_maintenance.router, prefix="/api/kiln-maintenance", tags=["kiln-maintenance"])
    app.include_router(kiln_constants.router, prefix="/api/kiln-constants", tags=["kiln-constants"])
    app.include_router(reference.router, prefix="/api/reference", tags=["reference"])
    app.include_router(toc.router, prefix="/api/toc", tags=["toc"])
    app.include_router(tps.router, prefix="/api/tps", tags=["tps"])
    app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])
    app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
    app.include_router(ai_chat.router, prefix="/api/ai-chat", tags=["ai-chat"])
    app.include_router(export.router, prefix="/api/export", tags=["export"])
    app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
    app.include_router(stages.router, prefix="/api/stages", tags=["stages"])
    app.include_router(transcription.router, prefix="/api/transcription", tags=["transcription"])
    app.include_router(telegram.router, prefix="/api/telegram", tags=["telegram"])
    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(purchaser.router, prefix="/api/purchaser", tags=["purchaser"])
    app.include_router(kiln_loading_rules.router, prefix="/api/kiln-loading-rules", tags=["kiln-loading-rules"])
    app.include_router(kiln_firing_schedules.router, prefix="/api/kiln-firing-schedules", tags=["kiln-firing-schedules"])
    app.include_router(dashboard_access.router, prefix="/api/dashboard-access", tags=["dashboard-access"])
    app.include_router(notification_preferences.router, prefix="/api/notification-preferences", tags=["notification-preferences"])
    app.include_router(financials.router, prefix="/api/financials", tags=["financials"])
    app.include_router(warehouse_sections.router, prefix="/api/warehouse-sections", tags=["warehouse-sections"])
    app.include_router(reconciliations.router, prefix="/api/reconciliations", tags=["reconciliations"])
    app.include_router(qm_blocks.router, prefix="/api/qm-blocks", tags=["qm-blocks"])
    app.include_router(problem_cards.router, prefix="/api/problem-cards", tags=["problem-cards"])
    app.include_router(security.router, prefix="/api/security", tags=["security"])
    app.include_router(ws.router, prefix="/api/ws", tags=["websocket"])
    app.include_router(packing_photos.router, prefix="/api/packing-photos", tags=["packing-photos"])
    app.include_router(finished_goods.router, prefix="/api/finished-goods", tags=["finished-goods"])
    app.include_router(firing_profiles.router, prefix="/api/firing-profiles", tags=["firing-profiles"])
    app.include_router(cleanup.router, prefix="/api/cleanup", tags=["cleanup"])

setup_routers()
