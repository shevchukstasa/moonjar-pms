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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown events."""
    logger.info("Moonjar PMS starting up...")
    # Create tables if needed (dev only; production uses Alembic migrations)
    if not IS_PRODUCTION:
        from api.database import engine, Base
        Base.metadata.create_all(bind=engine)
        logger.info("Dev mode: create_all executed")

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
