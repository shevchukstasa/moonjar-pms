"""
Moonjar PMS — Middleware: CSRF validation + rate limiting.
"""

import time
import logging
from collections import defaultdict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from api.auth import validate_csrf
from api.config import get_settings

settings = get_settings()
_rate_limit_logger = logging.getLogger("moonjar.ratelimit")


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


class LoginRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiter for authentication endpoints.
    Limits: 10 requests per 60 seconds per IP.
    """

    RATE_LIMIT_PATHS = ("/api/auth/login", "/api/auth/google")
    MAX_REQUESTS = 10
    WINDOW_SECONDS = 60

    def __init__(self, app):
        super().__init__(app)
        self._requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        if request.method == "POST" and request.url.path in self.RATE_LIMIT_PATHS:
            client_ip = request.client.host if request.client else "unknown"
            now = time.time()
            window_start = now - self.WINDOW_SECONDS

            # Clean old entries
            self._requests[client_ip] = [
                t for t in self._requests[client_ip] if t > window_start
            ]

            if len(self._requests[client_ip]) >= self.MAX_REQUESTS:
                _rate_limit_logger.warning(
                    f"Rate limit exceeded for {client_ip} on {request.url.path}"
                )
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many login attempts. Try again later."},
                    headers={"Retry-After": str(self.WINDOW_SECONDS)},
                )

            self._requests[client_ip].append(now)

            # Periodic cleanup: remove IPs with no recent requests
            if len(self._requests) > 1000:
                stale = [
                    ip for ip, times in self._requests.items()
                    if not times or times[-1] < window_start
                ]
                for ip in stale:
                    del self._requests[ip]

        return await call_next(request)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log request method, path, status, and duration."""

    async def dispatch(self, request: Request, call_next):
        logger = logging.getLogger("moonjar.access")
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start
        logger.info(
            f"{request.method} {request.url.path} "
            f"status={response.status_code} duration={duration:.3f}s"
        )
        return response
