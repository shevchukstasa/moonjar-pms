"""
Moonjar PMS — Middleware: CSRF validation + rate limiting.
"""

import time
import logging
from collections import defaultdict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from api.config import get_settings

settings = get_settings()
_rate_limit_logger = logging.getLogger("moonjar.ratelimit")


class CSRFMiddleware(BaseHTTPMiddleware):
    """Validate CSRF token on mutating requests."""

    # Paths that don't need CSRF (webhooks, auth login, health, internal cron)
    SKIP_PREFIXES = (
        "/api/integration/",
        "/api/integration",
        "/api/health",
        "/api/internal/",
        "/api/internal",
        "/api/auth/login",
        "/api/auth/google",
        "/api/auth/refresh",
        "/api/auth/logout",
        "/api/auth/verify-owner-key",
        "/api/telegram/webhook",
        "/api/ai-chat",
        "/api/ws/",
        "/api/ws",
    )

    async def dispatch(self, request: Request, call_next):
        if request.method in ("POST", "PATCH", "PUT", "DELETE"):
            if not request.url.path.startswith(self.SKIP_PREFIXES):
                csrf_cookie = request.cookies.get("csrf_token")
                csrf_header = request.headers.get("X-CSRF-Token")
                if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
                    # Return JSON directly — do NOT raise HTTPException here.
                    # Raising inside BaseHTTPMiddleware bypasses ExceptionMiddleware
                    # (it's inner) and hits ServerErrorMiddleware (outer) which
                    # returns a plain-text 500, not a JSON 403.
                    return JSONResponse(
                        {"detail": "CSRF token mismatch"},
                        status_code=403,
                    )
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    In-memory rate limiter per IP address.
    Limits (per spec):
      - Login:   5/min
      - API:     100/min
      - Webhook: 30/min
      - Upload:  10/min
    """

    TIERS = {
        "login":   {"paths": ("/api/auth/login", "/api/auth/google"), "max": 5, "window": 60},
        "webhook": {"prefix": "/api/integration/webhook", "max": 30, "window": 60},
        "upload":  {"prefix": "/api/packing-photos", "max": 10, "window": 60},
        "api":     {"prefix": "/api/", "max": 100, "window": 60},
    }

    def __init__(self, app):
        super().__init__(app)
        # Buckets: tier -> ip -> [timestamps]
        self._buckets: dict[str, dict[str, list[float]]] = {
            tier: defaultdict(list) for tier in self.TIERS
        }

    def _classify(self, request: Request) -> str | None:
        """Classify request into a rate-limit tier."""
        path = request.url.path
        method = request.method

        # Login: only POST
        if method == "POST" and path in self.TIERS["login"]["paths"]:
            return "login"
        # Webhook: only POST
        if method == "POST" and path.startswith(self.TIERS["webhook"]["prefix"]):
            return "webhook"
        # Upload: POST to packing-photos
        if method == "POST" and path.startswith(self.TIERS["upload"]["prefix"]):
            return "upload"
        # General API (all methods)
        if path.startswith(self.TIERS["api"]["prefix"]):
            return "api"
        return None

    async def dispatch(self, request: Request, call_next):
        tier = self._classify(request)
        if tier:
            cfg = self.TIERS[tier]
            client_ip = request.client.host if request.client else "unknown"
            now = time.time()
            window_start = now - cfg["window"]
            bucket = self._buckets[tier]

            # Clean old entries
            bucket[client_ip] = [t for t in bucket[client_ip] if t > window_start]

            if len(bucket[client_ip]) >= cfg["max"]:
                _rate_limit_logger.warning(
                    f"Rate limit [{tier}] exceeded for {client_ip} on {request.url.path}"
                )
                msg = {
                    "login": "Too many login attempts. Try again later.",
                    "webhook": "Webhook rate limit exceeded.",
                    "upload": "Upload rate limit exceeded.",
                    "api": "API rate limit exceeded.",
                }
                return JSONResponse(
                    status_code=429,
                    content={"detail": msg.get(tier, "Rate limit exceeded")},
                    headers={"Retry-After": str(cfg["window"])},
                )

            bucket[client_ip].append(now)

            # Periodic cleanup per tier
            if len(bucket) > 1000:
                stale = [ip for ip, ts in bucket.items() if not ts or ts[-1] < window_start]
                for ip in stale:
                    del bucket[ip]

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
