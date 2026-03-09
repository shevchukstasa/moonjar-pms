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
            ("factories", "served_locations JSONB"),
            ("batches", "firing_profile_id UUID"),
            ("batches", "target_temperature INTEGER"),
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

    # --- Section 7: Kilns (resources) — 3 per factory ---
    def _seed_kilns(conn):
        for fname, fid in factory_ids.items():
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
                exists = conn.execute(text(
                    "SELECT 1 FROM resources WHERE factory_id = :fid AND name = :kname LIMIT 1"
                ), {"fid": fid, "kname": kname}).fetchone()
                if not exists:
                    conn.execute(text(
                        "INSERT INTO resources (id, factory_id, name, resource_type, kiln_type, "
                        "kiln_dimensions_cm, kiln_working_area_cm, kiln_multi_level, "
                        "kiln_coefficient, is_active, status) "
                        "VALUES (gen_random_uuid(), :fid, :kname, 'kiln', :ktype, "
                        "cast(:dims as JSONB), cast(:work_area as JSONB), :multi, :coeff, TRUE, 'active')"
                    ), {
                        "fid": fid, "kname": kname, "ktype": ktype,
                        "dims": json_mod.dumps(dims), "work_area": json_mod.dumps(work_area),
                        "multi": multi, "coeff": coeff,
                    })

    _run_section("kilns", _seed_kilns)

    # --- Section 7b: Clean up duplicate kilns (old names without prefix) ---
    def _cleanup_duplicate_kilns(conn):
        # Migration 003 created kilns named "Large Kiln", "Small Kiln", "Raku Kiln"
        # _ensure_schema created "Bali Large Kiln", "Java Large Kiln" etc.
        # Remove old duplicates (only if properly-named ones exist)
        for old_name in ["Large Kiln", "Small Kiln", "Raku Kiln"]:
            # Only delete if there's a properly-named replacement
            has_replacement = conn.execute(text(
                "SELECT 1 FROM resources WHERE name LIKE :pattern AND resource_type = 'kiln' LIMIT 1"
            ), {"pattern": f"% {old_name}"}).fetchone()
            if has_replacement:
                conn.execute(text(
                    "DELETE FROM resources WHERE name = :name AND resource_type = 'kiln'"
                ), {"name": old_name})

    _run_section("cleanup_kilns", _cleanup_duplicate_kilns)

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

setup_routers()
