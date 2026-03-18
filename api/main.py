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
from api.routers import batches
from api.routers import cleanup
from api.routers import material_groups
from api.routers import packaging
from api.routers import sizes
from api.routers import consumption_rules
from api.routers import grinding
from api.routers import factory_calendar


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
            ("factories", "receiving_approval_mode VARCHAR(20) NOT NULL DEFAULT 'all'"),
            ("factories", "kiln_constants_mode VARCHAR(20) NOT NULL DEFAULT 'manual'"),
            ("factories", "rotation_rules JSONB"),
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
            # Grinding stock — PM decision fields
            ("grinding_stock", "decided_by UUID REFERENCES users(id)"),
            ("grinding_stock", "decided_at TIMESTAMPTZ"),
            ("grinding_stock", "notes TEXT"),
            # Position photos — batch association + web URL
            ("position_photos", "batch_id UUID REFERENCES batches(id)"),
            ("position_photos", "photo_url VARCHAR(2048)"),
            # order_positions — columns added to model but never migrated
            ("order_positions", "application_type VARCHAR(50)"),
            ("order_positions", "place_of_application VARCHAR(50)"),
            ("order_positions", "two_stage_firing BOOLEAN NOT NULL DEFAULT FALSE"),
            ("order_positions", "two_stage_type VARCHAR(20)"),
            # Size Resolution — FK columns for size assignment
            ("order_positions", "size_id UUID REFERENCES sizes(id)"),
            ("materials", "size_id UUID REFERENCES sizes(id)"),
            # FiringProfile — model was updated to new schema; add missing columns to existing table
            ("firing_profiles", "product_type VARCHAR(20)"),
            ("firing_profiles", "collection VARCHAR(100)"),
            ("firing_profiles", "thickness_min_mm NUMERIC(5,1)"),
            ("firing_profiles", "thickness_max_mm NUMERIC(5,1)"),
            ("firing_profiles", "target_temperature INTEGER DEFAULT 1000"),
            ("firing_profiles", "total_duration_hours NUMERIC(5,1) DEFAULT 24"),
            ("firing_profiles", "stages JSONB DEFAULT '[]'"),
            ("firing_profiles", "match_priority INTEGER DEFAULT 0"),
            ("firing_profiles", "is_default BOOLEAN DEFAULT FALSE"),
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
        # Glazing board task type — custom board needed for non-standard tile size
        ("task_type", "glazing_board_needed"),
        # Material receiving task (Stage 2)
        ("task_type", "material_receiving"),
        # Grinding stock enum values (type created in table section above;
        # keep entries here for any future additions only).
        # Size Resolution (MUST be in AUTOCOMMIT block — not in DO $$ transactions)
        ("positionstatus", "awaiting_size_confirmation"),
        ("tasktype", "size_resolution"),
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
        # Backup logs — tracks backup execution and status
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS backup_logs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                completed_at TIMESTAMPTZ,
                status VARCHAR(20) NOT NULL DEFAULT 'in_progress',
                file_size_bytes BIGINT,
                s3_key VARCHAR(500),
                error_message TEXT,
                backup_type VARCHAR(20) NOT NULL DEFAULT 'scheduled'
            )
        """))
        # Firing temperature groups — named groups replacing ±50°C auto-grouping
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS firing_temperature_groups (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(100) NOT NULL,
                min_temperature INTEGER NOT NULL,
                max_temperature INTEGER NOT NULL,
                description TEXT,
                thermocouple VARCHAR(50),
                control_cable VARCHAR(50),
                control_device VARCHAR(50),
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                display_order INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
        # Join table: temperature group ↔ recipe
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS firing_temperature_group_recipes (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                temperature_group_id UUID NOT NULL REFERENCES firing_temperature_groups(id) ON DELETE CASCADE,
                recipe_id UUID NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
                is_default BOOLEAN NOT NULL DEFAULT FALSE,
                UNIQUE(temperature_group_id, recipe_id)
            )
        """))
        # Kiln maintenance types — predefined types of maintenance/inspection
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS kiln_maintenance_types (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(200) NOT NULL,
                description TEXT,
                duration_hours NUMERIC(5,1) NOT NULL DEFAULT 2,
                requires_empty_kiln BOOLEAN NOT NULL DEFAULT FALSE,
                requires_cooled_kiln BOOLEAN NOT NULL DEFAULT FALSE,
                requires_power_off BOOLEAN NOT NULL DEFAULT FALSE,
                default_interval_days INTEGER,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
        # Position photos — received via Telegram bot
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS position_photos (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                position_id UUID REFERENCES order_positions(id),
                factory_id UUID NOT NULL REFERENCES factories(id),
                telegram_file_id VARCHAR(200) NOT NULL,
                telegram_chat_id BIGINT,
                uploaded_by_telegram_id BIGINT,
                uploaded_by_user_id UUID REFERENCES users(id),
                photo_type VARCHAR(30),
                caption TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
        # Grinding status enum type
        conn.execute(text("""
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'grindingstatus') THEN
                    CREATE TYPE grindingstatus AS ENUM ('in_stock', 'pending', 'grinding', 'completed', 'sent_to_mana', 'used_in_production');
                END IF;
            END $$
        """))
        # Grinding stock — positions awaiting PM decision
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS grinding_stock (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                factory_id UUID NOT NULL REFERENCES factories(id),
                color VARCHAR(100) NOT NULL DEFAULT '',
                size VARCHAR(50) NOT NULL DEFAULT '',
                quantity INTEGER NOT NULL DEFAULT 0,
                source_order_id UUID REFERENCES production_orders(id),
                source_position_id UUID REFERENCES order_positions(id),
                status grindingstatus NOT NULL DEFAULT 'in_stock',
                decided_by UUID REFERENCES users(id),
                decided_at TIMESTAMPTZ,
                notes TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
        # Migrate grinding_stock: add missing columns + fix status type if needed
        for col_def in [
            "color VARCHAR(100) NOT NULL DEFAULT ''",
            "size VARCHAR(50) NOT NULL DEFAULT ''",
            "quantity INTEGER NOT NULL DEFAULT 0",
        ]:
            try:
                conn.execute(text(f"""
                    DO $$ BEGIN
                        IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'grinding_stock') THEN
                            ALTER TABLE grinding_stock ADD COLUMN IF NOT EXISTS {col_def};
                        END IF;
                    END $$
                """))
            except Exception as e:
                logger.warning(f"_ensure_schema: skip grinding_stock.{col_def.split()[0]}: {e}")
        # Migrate status column from VARCHAR to enum if needed
        try:
            conn.execute(text("""
                DO $$ BEGIN
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'grinding_stock' AND column_name = 'status'
                          AND data_type = 'character varying'
                    ) THEN
                        ALTER TABLE grinding_stock
                            ALTER COLUMN status TYPE grindingstatus
                            USING status::grindingstatus;
                    END IF;
                END $$
            """))
        except Exception as e:
            logger.warning(f"_ensure_schema: skip grinding_stock status migration: {e}")
        # System settings (key-value for Telegram owner chat, etc.)
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS system_settings (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                key VARCHAR(100) NOT NULL UNIQUE,
                value TEXT,
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        # Factory calendar — non-working days / holidays per factory
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS factory_calendar (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                factory_id UUID NOT NULL REFERENCES factories(id),
                date DATE NOT NULL,
                is_working_day BOOLEAN NOT NULL DEFAULT TRUE,
                num_shifts INTEGER NOT NULL DEFAULT 2,
                holiday_name VARCHAR(200),
                holiday_source VARCHAR(50),
                approved_by UUID REFERENCES users(id),
                approved_at TIMESTAMPTZ,
                notes TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                CONSTRAINT uq_factory_calendar_date UNIQUE (factory_id, date)
            )
        """))
        # Escalation rules — PM→CEO→Owner timeout chain
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS escalation_rules (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                factory_id UUID NOT NULL REFERENCES factories(id),
                task_type VARCHAR(50) NOT NULL,
                pm_timeout_hours NUMERIC(6,2) NOT NULL DEFAULT 4,
                ceo_timeout_hours NUMERIC(6,2) NOT NULL DEFAULT 8,
                owner_timeout_hours NUMERIC(6,2) NOT NULL DEFAULT 24,
                night_level INTEGER NOT NULL DEFAULT 1,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                CONSTRAINT uq_escalation_factory_type UNIQUE (factory_id, task_type)
            )
        """))
        # Receiving settings — per-factory approval mode
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS receiving_settings (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                factory_id UUID NOT NULL UNIQUE REFERENCES factories(id),
                approval_mode VARCHAR(20) NOT NULL DEFAULT 'all',
                updated_by UUID REFERENCES users(id),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        # ReconciliationStatus enum type
        conn.execute(text("""
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'reconciliationstatus') THEN
                    CREATE TYPE reconciliationstatus AS ENUM ('scheduled', 'in_progress', 'completed', 'cancelled');
                END IF;
            END $$
        """))
        # Inventory reconciliations — periodic stock count sessions
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS inventory_reconciliations (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                factory_id UUID NOT NULL REFERENCES factories(id),
                section_id UUID REFERENCES warehouse_sections(id),
                status reconciliationstatus NOT NULL DEFAULT 'in_progress',
                started_by UUID NOT NULL REFERENCES users(id),
                completed_at TIMESTAMPTZ,
                notes TEXT,
                staff_count INTEGER,
                scheduled_date DATE,
                approved_by UUID REFERENCES users(id),
                approved_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS inventory_reconciliation_items (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                reconciliation_id UUID NOT NULL REFERENCES inventory_reconciliations(id) ON DELETE CASCADE,
                material_id UUID NOT NULL REFERENCES materials(id),
                system_quantity NUMERIC(12,3) NOT NULL DEFAULT 0,
                actual_quantity NUMERIC(12,3) NOT NULL DEFAULT 0,
                difference NUMERIC(12,3) NOT NULL DEFAULT 0,
                adjustment_applied BOOLEAN NOT NULL DEFAULT FALSE,
                reason VARCHAR(50),
                explanation TEXT,
                explained_by UUID REFERENCES users(id),
                explained_at TIMESTAMPTZ
            )
        """))
        # Glazing board specs — board dimensions per tile size
        # Masters measure glaze in mL per two boards; target ~0.22–0.23 m²/board
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS glazing_board_specs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                size_id UUID NOT NULL UNIQUE REFERENCES sizes(id) ON DELETE CASCADE,
                board_length_cm NUMERIC(6,1) NOT NULL DEFAULT 122.0,
                board_width_cm NUMERIC(6,1) NOT NULL,
                tiles_per_board INTEGER NOT NULL,
                area_per_board_m2 NUMERIC(8,4) NOT NULL,
                tiles_along_length INTEGER NOT NULL,
                tiles_across_width INTEGER NOT NULL,
                tile_orientation_cm VARCHAR(30),
                is_custom_board BOOLEAN NOT NULL DEFAULT FALSE,
                notes TEXT,
                calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))

    _run_section("tables", _create_tables)

    # --- Section 2b: Add new columns to existing maintenance schedule table ---
    def _add_maintenance_columns(conn):
        maint_cols = [
            ("kiln_maintenance_schedule", "maintenance_type_id UUID REFERENCES kiln_maintenance_types(id)"),
            ("kiln_maintenance_schedule", "scheduled_time TIME"),
            ("kiln_maintenance_schedule", "estimated_duration_hours NUMERIC(5,1)"),
            ("kiln_maintenance_schedule", "completed_at TIMESTAMPTZ"),
            ("kiln_maintenance_schedule", "completed_by_id UUID REFERENCES users(id)"),
            ("kiln_maintenance_schedule", "factory_id UUID REFERENCES factories(id)"),
            ("kiln_maintenance_schedule", "is_recurring BOOLEAN NOT NULL DEFAULT FALSE"),
            ("kiln_maintenance_schedule", "recurrence_interval_days INTEGER"),
            ("kiln_maintenance_schedule", "requires_empty_kiln BOOLEAN NOT NULL DEFAULT FALSE"),
            ("kiln_maintenance_schedule", "requires_cooled_kiln BOOLEAN NOT NULL DEFAULT FALSE"),
            ("kiln_maintenance_schedule", "requires_power_off BOOLEAN NOT NULL DEFAULT FALSE"),
        ]
        for table, col_def in maint_cols:
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

    _run_section("maintenance_columns", _add_maintenance_columns)

    # --- Section 2c: Add equipment columns to firing_temperature_groups ---
    def _add_temp_group_columns(conn):
        cols = [
            ("firing_temperature_groups", "thermocouple VARCHAR(50)"),
            ("firing_temperature_groups", "control_cable VARCHAR(50)"),
            ("firing_temperature_groups", "control_device VARCHAR(50)"),
        ]
        for table, col_def in cols:
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

    _run_section("temp_group_columns", _add_temp_group_columns)

    # --- Section 2d: Add equipment columns to resources (kilns) ---
    def _add_kiln_equipment_columns(conn):
        cols = [
            ("resources", "thermocouple VARCHAR(50)"),
            ("resources", "control_cable VARCHAR(50)"),
            ("resources", "control_device VARCHAR(50)"),
        ]
        for table, col_def in cols:
            try:
                conn.execute(text(f"""
                    ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col_def}
                """))
            except Exception as e:
                logger.warning(f"_ensure_schema: skip {table}.{col_def.split()[0]}: {e}")

    _run_section("kiln_equipment_columns", _add_kiln_equipment_columns)

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

    # --- Section 21: Temperature groups — replace min/max with single temperature ---
    # (Must run BEFORE seed, because seed uses the 'temperature' column)
    def _temp_groups_single_temperature(conn):
        """Add 'temperature' column, populate from avg(min,max), remove NOT NULL from old cols."""
        conn.execute(text("""
            ALTER TABLE firing_temperature_groups
            ADD COLUMN IF NOT EXISTS temperature INTEGER;
        """))
        # Populate from average of existing min/max (for existing rows)
        conn.execute(text("""
            UPDATE firing_temperature_groups
            SET temperature = ROUND((COALESCE(min_temperature, 0) + COALESCE(max_temperature, 0)) / 2.0)
            WHERE temperature IS NULL
              AND (min_temperature IS NOT NULL OR max_temperature IS NOT NULL);
        """))
        # Make min/max nullable (they were NOT NULL before)
        conn.execute(text("""
            ALTER TABLE firing_temperature_groups
            ALTER COLUMN min_temperature DROP NOT NULL;
        """))
        conn.execute(text("""
            ALTER TABLE firing_temperature_groups
            ALTER COLUMN max_temperature DROP NOT NULL;
        """))

    _run_section("temp_groups_single_temperature", _temp_groups_single_temperature)

    # --- Section 6c: Firing temperature groups ---
    # DISABLED: seed was recreating groups on every startup when user renamed them.
    # User manages temperature groups manually via Admin UI.
    # def _seed_temperature_groups — removed

    # --- Section 6d: Kiln maintenance types ---
    def _seed_maintenance_types(conn):
        """Seed default kiln maintenance/inspection types."""
        types = [
            ("Thermocouple Calibration", "Calibrate thermocouple sensors for accurate temperature readings", 4.0, False, True, True, 90),
            ("Heating Element Inspection", "Inspect heating elements for wear, damage, or uneven heating", 3.0, False, True, True, 180),
            ("Refractory Lining Check", "Inspect refractory lining for cracks, spalling, or deterioration", 2.0, True, True, False, 60),
            ("Door Seal Inspection", "Check door seals for gaps and heat leakage", 1.0, False, True, False, 30),
            ("Ventilation System Check", "Inspect ventilation system, dampers, and exhaust for proper airflow", 1.5, False, False, False, 30),
            ("Electrical Connections Check", "Inspect wiring, terminals, contactors, and safety interlocks", 2.0, False, False, True, 90),
            ("Temperature Uniformity Test", "Run empty kiln to verify temperature distribution across all zones", 6.0, True, False, False, 90),
            ("Full Preventive Maintenance", "Complete preventive maintenance: all systems, cleaning, and calibration", 8.0, True, True, True, 365),
        ]
        for name, desc, hours, empty, cooled, power_off, interval in types:
            conn.execute(text(
                "INSERT INTO kiln_maintenance_types "
                "(id, name, description, duration_hours, requires_empty_kiln, "
                "requires_cooled_kiln, requires_power_off, default_interval_days) "
                "SELECT gen_random_uuid(), :name, :desc, :hours, :empty, :cooled, :power_off, :interval "
                "WHERE NOT EXISTS ("
                "  SELECT 1 FROM kiln_maintenance_types WHERE name = :name"
                ")"
            ), {
                "name": name, "desc": desc, "hours": hours,
                "empty": empty, "cooled": cooled, "power_off": power_off,
                "interval": interval,
            })

    _run_section("maintenance_types", _seed_maintenance_types)

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
    # --- Section 8: Glaze recipes seed ---
    # DISABLED: seed was recreating recipes + materials on every startup.
    # When user renamed/merged materials, the old names were not found → recreated as zombies.
    # User manages recipes and materials manually via Admin UI.
    # def _seed_glaze_recipes — removed

    # --- Section 9: Material groups & subgroups hierarchy ---
    def _create_material_groups_tables(conn):
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS material_groups (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(200) NOT NULL UNIQUE,
                code VARCHAR(50) NOT NULL UNIQUE,
                description TEXT,
                icon VARCHAR(10),
                display_order INTEGER NOT NULL DEFAULT 0,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS material_subgroups (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                group_id UUID NOT NULL REFERENCES material_groups(id) ON DELETE CASCADE,
                name VARCHAR(200) NOT NULL,
                code VARCHAR(50) NOT NULL UNIQUE,
                description TEXT,
                icon VARCHAR(10),
                default_lead_time_days INTEGER,
                default_unit VARCHAR(20) DEFAULT 'kg',
                display_order INTEGER NOT NULL DEFAULT 0,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT uq_subgroup_group_name UNIQUE(group_id, name)
            )
        """))

    _run_section("material_groups_tables", _create_material_groups_tables)

    def _add_material_subgroup_fk(conn):
        conn.execute(text(
            "ALTER TABLE materials ADD COLUMN IF NOT EXISTS subgroup_id UUID REFERENCES material_subgroups(id)"
        ))

    _run_section("materials_subgroup_fk", _add_material_subgroup_fk)

    def _seed_material_groups(conn):
        count = conn.execute(text("SELECT COUNT(*) FROM material_groups")).scalar()
        if count and count > 0:
            return

        # Create groups
        conn.execute(text("""
            INSERT INTO material_groups (name, code, icon, display_order) VALUES
                ('Tile Materials', 'tile_materials', '🧱', 1),
                ('Packaging & Consumables', 'packaging_consumables', '📦', 2),
                ('Other', 'other', '📋', 3)
        """))

        tile_gid = conn.execute(text(
            "SELECT id FROM material_groups WHERE code = 'tile_materials'"
        )).scalar()
        pack_gid = conn.execute(text(
            "SELECT id FROM material_groups WHERE code = 'packaging_consumables'"
        )).scalar()
        other_gid = conn.execute(text(
            "SELECT id FROM material_groups WHERE code = 'other'"
        )).scalar()

        # Create subgroups matching old material_type enum values
        conn.execute(text("""
            INSERT INTO material_subgroups (group_id, name, code, icon, default_lead_time_days, display_order) VALUES
                (:tile, 'Stone',               'stone',           '🪨', 35, 1),
                (:tile, 'Pigments',            'pigment',         '🎨',  7, 2),
                (:tile, 'Frits',               'frit',            '⚗️', 14, 3),
                (:tile, 'Oxides & Carbonates', 'oxide_carbonate', '🧪', 14, 4),
                (:tile, 'Other Bulk',          'other_bulk',      '📦', 14, 5),
                (:pack, 'Packaging',           'packaging',       '📦', 14, 1),
                (:pack, 'Consumables',         'consumable',      '🔧', 14, 2),
                (:other, 'Other',              'other',           '📋', 14, 1)
        """), {"tile": str(tile_gid), "pack": str(pack_gid), "other": str(other_gid)})

    _run_section("seed_material_groups", _seed_material_groups)

    def _backfill_material_subgroups(conn):
        conn.execute(text("""
            UPDATE materials m
            SET subgroup_id = sg.id
            FROM material_subgroups sg
            WHERE m.material_type = sg.code
              AND m.subgroup_id IS NULL
        """))

    _run_section("backfill_material_subgroups", _backfill_material_subgroups)

    # --- Section 9: Evolve warehouse_sections for independent warehouses ---
    def _evolve_warehouse_sections(conn):
        """Evolve warehouse_sections: nullable factory_id, new columns."""
        cols = [
            "description TEXT",
            "managed_by UUID REFERENCES users(id)",
            "warehouse_type VARCHAR(50) NOT NULL DEFAULT 'section'",
            "display_order INTEGER NOT NULL DEFAULT 0",
            "updated_at TIMESTAMPTZ DEFAULT now()",
        ]
        for col_def in cols:
            col_name = col_def.split()[0]
            conn.execute(text(f"""
                DO $$ BEGIN
                    ALTER TABLE warehouse_sections ADD COLUMN {col_def};
                EXCEPTION WHEN duplicate_column THEN NULL;
                END $$;
            """))
        # Make factory_id nullable (allows global warehouses)
        conn.execute(text(
            "ALTER TABLE warehouse_sections ALTER COLUMN factory_id DROP NOT NULL"
        ))
        # Partial unique index for global warehouses (factory_id IS NULL)
        conn.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_warehouse_section_code_global
            ON warehouse_sections (code) WHERE factory_id IS NULL
        """))

    _run_section("evolve_warehouse_sections", _evolve_warehouse_sections)

    # --- Section 10: Seed 'Finished Goods' material group ---
    def _seed_finished_goods_group(conn):
        """Add 'Finished Goods' material group if not exists."""
        existing = conn.execute(text(
            "SELECT id FROM material_groups WHERE code = 'finished_goods'"
        )).scalar()
        if existing:
            return  # Already seeded

        conn.execute(text("""
            INSERT INTO material_groups (id, name, code, icon, display_order, is_active)
            VALUES (gen_random_uuid(), 'Finished Goods', 'finished_goods', '🏭', 4, TRUE)
        """))

        fg_gid = conn.execute(text(
            "SELECT id FROM material_groups WHERE code = 'finished_goods'"
        )).scalar()

        for code, name, icon, order in [
            ('tile', 'Tiles', '🧱', 1),
            ('sink', 'Sinks', '🚿', 2),
            ('custom_product', 'Custom Products', '📦', 3),
        ]:
            conn.execute(text("""
                INSERT INTO material_subgroups (id, group_id, name, code, icon, default_unit, display_order, is_active)
                SELECT gen_random_uuid(), :gid, :name, :code, :icon, 'pcs', :ord, TRUE
                WHERE NOT EXISTS (SELECT 1 FROM material_subgroups WHERE code = :code)
            """), {"gid": str(fg_gid), "name": name, "code": code, "icon": icon, "ord": order})

    _run_section("seed_finished_goods_group", _seed_finished_goods_group)

    # --- Section 11b: Add material_code column + backfill ---
    def _add_material_code(conn):
        """Add material_code column to materials and backfill existing rows."""
        conn.execute(text("""
            ALTER TABLE materials ADD COLUMN IF NOT EXISTS material_code VARCHAR(20)
        """))
        # Create unique index (if not exists)
        conn.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_materials_material_code
            ON materials (material_code) WHERE material_code IS NOT NULL
        """))
        # Backfill: assign M-XXXX codes to materials that don't have one yet
        # Order by created_at so older materials get lower numbers
        conn.execute(text("""
            WITH numbered AS (
                SELECT id,
                       ROW_NUMBER() OVER (ORDER BY created_at, name) AS rn
                FROM materials
                WHERE material_code IS NULL
            )
            UPDATE materials
            SET material_code = 'M-' || LPAD(
                ((SELECT COALESCE(MAX(
                    CASE WHEN m2.material_code ~ '^M-[0-9]+$'
                         THEN CAST(SUBSTRING(m2.material_code FROM 3) AS INTEGER)
                         ELSE 0
                    END
                ), 0) FROM materials m2 WHERE m2.material_code IS NOT NULL)
                + numbered.rn)::TEXT,
                4, '0')
            FROM numbered
            WHERE materials.id = numbered.id
        """))

    _run_section("add_material_code", _add_material_code)

    # --- Section 12: Create supplier_subgroups junction table ---
    def _create_supplier_subgroups(conn):
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS supplier_subgroups (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                supplier_id UUID NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
                subgroup_id UUID NOT NULL REFERENCES material_subgroups(id) ON DELETE CASCADE,
                UNIQUE (supplier_id, subgroup_id)
            )
        """))

    _run_section("create_supplier_subgroups", _create_supplier_subgroups)

    # --- Section 13: Packaging tables + inventory enum ---
    def _create_packaging_tables(conn):
        # Add INVENTORY value to transaction_type enum
        conn.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'inventory'
                    AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'transaction_type'))
                THEN
                    ALTER TYPE transaction_type ADD VALUE 'inventory';
                END IF;
            END$$;
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS packaging_box_types (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                material_id UUID NOT NULL REFERENCES materials(id) ON DELETE CASCADE,
                name VARCHAR(200) NOT NULL,
                notes TEXT,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS packaging_box_capacities (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                box_type_id UUID NOT NULL REFERENCES packaging_box_types(id) ON DELETE CASCADE,
                size_id UUID NOT NULL REFERENCES sizes(id) ON DELETE CASCADE,
                pieces_per_box INTEGER,
                sqm_per_box NUMERIC(10, 4),
                UNIQUE (box_type_id, size_id)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS packaging_spacer_rules (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                box_type_id UUID NOT NULL REFERENCES packaging_box_types(id) ON DELETE CASCADE,
                size_id UUID NOT NULL REFERENCES sizes(id) ON DELETE CASCADE,
                spacer_material_id UUID NOT NULL REFERENCES materials(id) ON DELETE CASCADE,
                qty_per_box INTEGER NOT NULL DEFAULT 1,
                UNIQUE (box_type_id, size_id, spacer_material_id)
            )
        """))

    _run_section("create_packaging_tables", _create_packaging_tables)

    # --- Section 14: Add thickness_mm and shape to sizes table ---
    def _add_size_columns(conn):
        conn.execute(text("""
            ALTER TABLE sizes ADD COLUMN IF NOT EXISTS thickness_mm INTEGER;
        """))
        conn.execute(text("""
            ALTER TABLE sizes ADD COLUMN IF NOT EXISTS shape VARCHAR(20) DEFAULT 'rectangle';
        """))
        conn.execute(text("""
            ALTER TABLE sizes ADD COLUMN IF NOT EXISTS is_custom BOOLEAN NOT NULL DEFAULT FALSE;
        """))

    _run_section("add_size_columns", _add_size_columns)

    # --- Section 15: Restructure recipe columns ---
    def _restructure_recipe_columns(conn):
        # Rename collection → color_collection
        conn.execute(text("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'recipes' AND column_name = 'collection'
                ) THEN
                    ALTER TABLE recipes RENAME COLUMN collection TO color_collection;
                END IF;
            END $$;
        """))
        # Add new consumption columns
        conn.execute(text("""
            ALTER TABLE recipes ADD COLUMN IF NOT EXISTS consumption_spray_ml_per_sqm NUMERIC(8,2);
        """))
        conn.execute(text("""
            ALTER TABLE recipes ADD COLUMN IF NOT EXISTS consumption_brush_ml_per_sqm NUMERIC(8,2);
        """))
        # Migrate data from glaze_settings.consumption_ml_per_sqm into new columns
        conn.execute(text("""
            UPDATE recipes SET
                consumption_spray_ml_per_sqm = (glaze_settings->>'consumption_ml_per_sqm')::numeric,
                consumption_brush_ml_per_sqm = (glaze_settings->>'consumption_ml_per_sqm')::numeric
            WHERE glaze_settings->>'consumption_ml_per_sqm' IS NOT NULL
              AND consumption_spray_ml_per_sqm IS NULL;
        """))
        # Drop old unique constraint, create new one
        conn.execute(text("""
            ALTER TABLE recipes DROP CONSTRAINT IF EXISTS uq_recipes_collection_color_apptype;
        """))
        conn.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = 'uq_recipes_colcollection_name'
                ) THEN
                    ALTER TABLE recipes ADD CONSTRAINT uq_recipes_colcollection_name
                        UNIQUE (color_collection, name);
                END IF;
            END $$;
        """))
        # Drop removed columns
        conn.execute(text("""
            ALTER TABLE recipes DROP COLUMN IF EXISTS color;
        """))
        conn.execute(text("""
            ALTER TABLE recipes DROP COLUMN IF EXISTS application_type;
        """))

    _run_section("restructure_recipe_columns", _restructure_recipe_columns)

    # --- Section 16: Add is_default column to recipes ---
    # Engobe recipe seeds REMOVED — they used ON CONFLICT(color_collection, name)
    # but color_collection=NULL, and NULL != NULL in PostgreSQL, so ON CONFLICT
    # never fired → 4 duplicates created on every server restart.
    # User manages engobe recipes manually via Admin UI.
    def _add_recipe_is_default(conn):
        conn.execute(text("""
            ALTER TABLE recipes ADD COLUMN IF NOT EXISTS is_default BOOLEAN NOT NULL DEFAULT FALSE;
        """))

    _run_section("recipe_is_default_engobes", _add_recipe_is_default)

    # --- Section 17: Create color_collections table ---
    def _create_color_collections_table(conn):
        """Create separate color_collections table for glaze recipes."""
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS color_collections (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(100) NOT NULL UNIQUE,
                description VARCHAR(255),
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """))
        # Seed from existing distinct recipe.color_collection values
        conn.execute(text("""
            INSERT INTO color_collections (id, name)
            SELECT gen_random_uuid(), rc.color_collection
            FROM (
                SELECT DISTINCT color_collection
                FROM recipes
                WHERE color_collection IS NOT NULL AND color_collection != ''
            ) rc
            ON CONFLICT (name) DO NOTHING;
        """))

    _run_section("create_color_collections_table", _create_color_collections_table)

    # --- Section 18: Size resolution — add size_id FK + enum values ---
    def _size_resolution_migration(conn):
        """Add size_id FK to order_positions, new enum values for size resolution."""
        # Add enum values (only if enum types exist — they're created by SQLAlchemy table creation)
        conn.execute(text("""
            DO $$ BEGIN
                IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'positionstatus') THEN
                    EXECUTE 'ALTER TYPE positionstatus ADD VALUE IF NOT EXISTS ''awaiting_size_confirmation''';
                END IF;
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$;
        """))
        conn.execute(text("""
            DO $$ BEGIN
                IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'tasktype') THEN
                    EXECUTE 'ALTER TYPE tasktype ADD VALUE IF NOT EXISTS ''size_resolution''';
                END IF;
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$;
        """))
        # Add size_id column (only if table exists)
        conn.execute(text("""
            DO $$ BEGIN
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'order_positions') THEN
                    EXECUTE 'ALTER TABLE order_positions ADD COLUMN IF NOT EXISTS size_id UUID REFERENCES sizes(id)';
                    EXECUTE 'CREATE INDEX IF NOT EXISTS ix_order_positions_size_id ON order_positions(size_id)';
                END IF;
            END $$;
        """))

    _run_section("size_resolution_migration", _size_resolution_migration)

    # --- Section 19: Materials size_id + Recipe client_name + Consumption rules table + Russian→English names ---
    def _materials_recipes_consumption(conn):
        # Material → size_id FK
        conn.execute(text("""
            ALTER TABLE materials
            ADD COLUMN IF NOT EXISTS size_id UUID REFERENCES sizes(id);
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_materials_size_id ON materials(size_id);
        """))
        # Recipe → client_name
        conn.execute(text("""
            ALTER TABLE recipes
            ADD COLUMN IF NOT EXISTS client_name VARCHAR(200);
        """))
        # Consumption rules table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS consumption_rules (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                rule_number INTEGER NOT NULL,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                collection VARCHAR(200),
                color_collection VARCHAR(200),
                product_type VARCHAR(100),
                size_id UUID REFERENCES sizes(id),
                shape VARCHAR(100),
                thickness_mm_min NUMERIC(8,2),
                thickness_mm_max NUMERIC(8,2),
                place_of_application VARCHAR(200),
                recipe_type VARCHAR(100),
                application_method VARCHAR(100),
                consumption_ml_per_sqm NUMERIC(12,4) NOT NULL,
                coats INTEGER NOT NULL DEFAULT 1,
                specific_gravity_override NUMERIC(8,4),
                priority INTEGER NOT NULL DEFAULT 0,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                notes TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_consumption_rules_rule_number
            ON consumption_rules(rule_number);
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_consumption_rules_active
            ON consumption_rules(is_active) WHERE is_active = TRUE;
        """))
        # Russian → English: material_groups names
        conn.execute(text("""
            UPDATE material_groups SET name = 'Tile Materials'
            WHERE name = 'Материалы для плитки';
        """))
        conn.execute(text("""
            UPDATE material_groups SET name = 'Packaging & Consumables'
            WHERE name = 'Упаковка и расходные';
        """))
        conn.execute(text("""
            UPDATE material_groups SET name = 'Other'
            WHERE name = 'Прочее';
        """))
        conn.execute(text("""
            UPDATE material_groups SET name = 'Finished Goods'
            WHERE name = 'Готовая продукция';
        """))
        # Russian → English: material_subgroups names
        conn.execute(text("""
            UPDATE material_subgroups SET name = 'Tiles'
            WHERE name = 'Плитка';
        """))
        conn.execute(text("""
            UPDATE material_subgroups SET name = 'Sinks'
            WHERE name = 'Раковины';
        """))
        conn.execute(text("""
            UPDATE material_subgroups SET name = 'Custom Products'
            WHERE name = 'Прочие изделия';
        """))

    _run_section("materials_recipes_consumption", _materials_recipes_consumption)

    # --- Section 20: Cleanup zombie materials created by seed ---
    # Materials of type 'glaze_ingredient' that are NOT linked to any recipe
    # and have zero stock everywhere are orphans from seed re-creation after merge.
    def _cleanup_zombie_materials(conn):
        deleted = conn.execute(text("""
            DELETE FROM material_stock
            WHERE material_id IN (
                SELECT m.id FROM materials m
                WHERE m.material_type = 'glaze_ingredient'
                  AND NOT EXISTS (
                      SELECT 1 FROM recipe_materials rm WHERE rm.material_id = m.id
                  )
            )
            AND (balance = 0 OR balance IS NULL)
        """)).rowcount
        zombies = conn.execute(text("""
            DELETE FROM materials
            WHERE material_type = 'glaze_ingredient'
              AND NOT EXISTS (
                  SELECT 1 FROM recipe_materials rm WHERE rm.material_id = materials.id
              )
              AND NOT EXISTS (
                  SELECT 1 FROM material_stock ms
                  WHERE ms.material_id = materials.id AND ms.balance > 0
              )
            RETURNING id, name
        """)).fetchall()
        if zombies:
            names = [z[1] for z in zombies]
            logger.info(f"_cleanup_zombie_materials: removed {len(zombies)} orphan glaze_ingredient materials: {names}")
        else:
            logger.info("_cleanup_zombie_materials: no orphan materials found")

    _run_section("cleanup_zombie_materials", _cleanup_zombie_materials)

    # --- Section 22: Fix NULL glaze_settings in existing recipes ---
    def _fix_null_glaze_settings(conn):
        updated = conn.execute(text("""
            UPDATE recipes SET glaze_settings = '{}'::jsonb
            WHERE glaze_settings IS NULL
        """)).rowcount
        if updated:
            logger.info(f"_fix_null_glaze_settings: fixed {updated} recipes")

    _run_section("fix_null_glaze_settings", _fix_null_glaze_settings)

    # --- Section 23: Align recipe_firing_stages schema with model ---
    def _fix_recipe_firing_stages_schema(conn):
        """The CREATE TABLE used stage_order/target_temperature/hold_minutes/ramp_rate/atmosphere/notes
        but the ORM model expects stage_number/firing_profile_id/requires_glazing_before/description."""
        # Rename stage_order → stage_number if exists
        conn.execute(text("""
            DO $$ BEGIN
                ALTER TABLE recipe_firing_stages RENAME COLUMN stage_order TO stage_number;
            EXCEPTION WHEN undefined_column THEN NULL; END $$;
        """))
        # Add missing columns
        add_cols = [
            ("recipe_firing_stages", "stage_number INTEGER NOT NULL DEFAULT 1"),
            ("recipe_firing_stages", "firing_profile_id UUID"),
            ("recipe_firing_stages", "requires_glazing_before BOOLEAN NOT NULL DEFAULT TRUE"),
            ("recipe_firing_stages", "description VARCHAR(200)"),
        ]
        for tbl, col_def in add_cols:
            col_name = col_def.split()[0]
            conn.execute(text(f"""
                DO $$ BEGIN
                    ALTER TABLE {tbl} ADD COLUMN {col_def};
                EXCEPTION WHEN duplicate_column THEN NULL; END $$;
            """))

    _run_section("fix_recipe_firing_stages_schema", _fix_recipe_firing_stages_schema)

    # --- Section 11: Stamp alembic version ---
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

    # Auto-register Telegram webhook on startup
    if settings.TELEGRAM_BOT_TOKEN and settings.api_base_url:
        webhook_url = f"{settings.api_base_url}/api/telegram/webhook"
        try:
            from business.services.telegram_bot import set_webhook
            set_webhook(webhook_url)
        except Exception as e:
            logger.warning(f"Telegram webhook setup failed: {e}")
    elif settings.TELEGRAM_BOT_TOKEN:
        logger.info(
            "Telegram bot token configured but no API_BASE_URL / RAILWAY_PUBLIC_DOMAIN set — "
            "webhook not registered automatically. Set API_BASE_URL to enable."
        )

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
    app.include_router(batches.router, prefix="/api/batches", tags=["batches"])
    app.include_router(cleanup.router, prefix="/api/cleanup", tags=["cleanup"])
    app.include_router(material_groups.router, prefix="/api/material-groups", tags=["material-groups"])
    app.include_router(packaging.router, prefix="/api/packaging", tags=["packaging"])
    app.include_router(sizes.router, prefix="/api/sizes", tags=["sizes"])
    app.include_router(consumption_rules.router, prefix="/api/consumption-rules", tags=["consumption-rules"])
    app.include_router(grinding.router, prefix="/api/grinding-stock", tags=["grinding-stock"])
    app.include_router(factory_calendar.router, prefix="/api/factory-calendar", tags=["factory-calendar"])

setup_routers()
