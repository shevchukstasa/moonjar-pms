"""
Moonjar PMS — Middleware: CSRF validation + rate limiting.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from api.auth import validate_csrf
from api.config import get_settings

settings = get_settings()


class CSRFMiddleware(BaseHTTPMiddleware):
    """Validate CSRF token on mutating requests."""

    # Paths that don't need CSRF (webhooks, auth login, health, internal cron)
    SKIP_PREFIXES = (
        "/api/integration/",
        "/api/health",
        "/api/internal/",
        "/api/auth/login",
        "/api/auth/google",
        "/api/auth/refresh",
        "/api/telegram/webhook",
        "/api/ws/",
    )

    async def dispatch(self, request: Request, call_next):
        if request.method in ("POST", "PATCH", "PUT", "DELETE"):
            if not request.url.path.startswith(self.SKIP_PREFIXES):
                validate_csrf(request)
        response = await call_next(request)
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log request method, path, status, and duration."""

    async def dispatch(self, request: Request, call_next):
        import time
        import logging
        logger = logging.getLogger("moonjar.access")
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start
        logger.info(
            f"{request.method} {request.url.path} "
            f"status={response.status_code} duration={duration:.3f}s"
        )
        return response
