"""
Moonjar PMS — Middleware: CSRF validation + request logging.
Rate limiting has moved to api/rate_limit.py.
"""

import time
import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from api.config import get_settings

settings = get_settings()


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
        "/api/auth/totp-verify",
        "/api/telegram/webhook",
        "/api/ws/",
        "/api/ws",
    )

    def _cors_headers(self, request: Request) -> dict:
        """
        Build minimal CORS headers for early-return responses.

        CORSMiddleware sits INSIDE CSRFMiddleware in the middleware stack
        (add_middleware stacks in reverse: last-added = outermost).
        When CSRFMiddleware returns a response without calling call_next,
        CORSMiddleware is never invoked — so the response has no
        Access-Control-Allow-Origin and the browser blocks it as a CORS error.
        JS then sees error.response = null → generic fallback message.

        We replicate the minimal CORS headers here so the browser lets JS
        read the actual 403 error body.
        """
        origin = request.headers.get("origin", "")
        if not origin:
            return {}
        allowed = settings.cors_origins_list
        if origin in allowed or "*" in allowed:
            return {
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Expose-Headers": "X-CSRF-Token",
            }
        return {}

    async def dispatch(self, request: Request, call_next):
        if request.method in ("POST", "PATCH", "PUT", "DELETE"):
            if not request.url.path.startswith(self.SKIP_PREFIXES):
                csrf_cookie = request.cookies.get("csrf_token")
                csrf_header = request.headers.get("X-CSRF-Token")

                # Double-submit: cookie == header (fast path)
                csrf_ok = bool(csrf_cookie and csrf_header and csrf_cookie == csrf_header)

                # Fallback for cross-origin (third-party cookies blocked):
                # Verify header token against HMAC(SECRET_KEY, jti_from_jwt)
                if not csrf_ok and csrf_header:
                    access_token = request.cookies.get("access_token")
                    if access_token:
                        try:
                            from api.auth import decode_token, generate_csrf_token
                            payload = decode_token(access_token)
                            expected = generate_csrf_token(payload.get("jti", ""))
                            csrf_ok = (csrf_header == expected)
                        except Exception:
                            pass  # invalid JWT — let it fail as CSRF mismatch

                if not csrf_ok:
                    return JSONResponse(
                        {"detail": "CSRF token mismatch"},
                        status_code=403,
                        headers=self._cors_headers(request),
                    )

        response = await call_next(request)

        # Echo X-CSRF-Token on every successful response so the frontend can
        # populate sessionStorage from any request (GET included).
        # This solves the cross-origin Railway case: the csrf_token cookie is
        # set on the backend domain, JS on the frontend domain cannot read it
        # via document.cookie, but the backend CAN read it from the request
        # and echo it here — giving the frontend a token before its first
        # mutating request.
        csrf_token = request.cookies.get("csrf_token")
        if csrf_token and "X-CSRF-Token" not in response.headers:
            response.headers["X-CSRF-Token"] = csrf_token

        return response


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
