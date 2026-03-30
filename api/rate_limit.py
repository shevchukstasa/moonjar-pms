"""
Moonjar PMS — Rate limiting engine.

In-memory sliding-window counters with DB logging on violations.
Designed for minimal overhead: dict lookups + timestamp comparisons only.
DB writes happen asynchronously only when a limit is exceeded.
"""

import os
import time
import logging
import threading
from collections import defaultdict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger("moonjar.ratelimit")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() in ("true", "1", "yes")

# Tier definitions: max requests per window (seconds)
TIERS = {
    "login": {
        "paths": ("/api/auth/login", "/api/auth/google"),
        "methods": ("POST",),
        "max": 5,
        "window": 60,
        "message": "Too many login attempts. Try again later.",
    },
    "webhook": {
        "prefix": "/api/integration/webhook",
        "methods": ("POST",),
        "max": 30,
        "window": 60,
        "message": "Webhook rate limit exceeded.",
    },
    "upload": {
        "prefix": "/api/packing-photos",
        "methods": ("POST",),
        "max": 10,
        "window": 60,
        "message": "Upload rate limit exceeded.",
    },
    "authenticated": {
        "prefix": "/api/",
        "methods": None,  # all methods
        "max": 100,
        "window": 60,
        "message": "API rate limit exceeded.",
        "keyed_by": "user",  # track per user_id (falls back to IP)
    },
    "unauthenticated": {
        "prefix": "/api/",
        "methods": None,
        "max": 30,
        "window": 60,
        "message": "API rate limit exceeded. Please authenticate for higher limits.",
        "keyed_by": "ip",
    },
}

# Paths to skip entirely (health checks, WebSocket upgrades)
SKIP_PATHS = ("/api/health", "/api/ws/", "/api/ws")


# ---------------------------------------------------------------------------
# In-memory bucket store
# ---------------------------------------------------------------------------

class _BucketStore:
    """Thread-safe sliding-window counters.

    Structure: tier -> key -> [timestamps]
    Key is IP address or user_id depending on tier config.
    """

    def __init__(self):
        self._data: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
        self._lock = threading.Lock()

    def record_and_check(self, tier: str, key: str, max_requests: int, window: float) -> tuple[bool, int, float]:
        """Record a request and check if limit is exceeded.

        Returns: (allowed, remaining, reset_at)
          - allowed: True if request is within limits
          - remaining: number of requests left in the window
          - reset_at: unix timestamp when the window resets
        """
        now = time.time()
        window_start = now - window

        with self._lock:
            bucket = self._data[tier][key]
            # Prune expired entries
            bucket[:] = [t for t in bucket if t > window_start]
            count = len(bucket)

            if count >= max_requests:
                # Limit exceeded — don't record this request
                reset_at = bucket[0] + window if bucket else now + window
                return False, 0, reset_at

            bucket.append(now)
            remaining = max_requests - count - 1
            reset_at = now + window
            return True, remaining, reset_at

    def cleanup(self, max_keys_per_tier: int = 2000):
        """Periodic cleanup of stale buckets."""
        now = time.time()
        with self._lock:
            for tier_name, tier_data in self._data.items():
                if len(tier_data) > max_keys_per_tier:
                    stale = [k for k, ts in tier_data.items() if not ts or ts[-1] < now - 120]
                    for k in stale:
                        del tier_data[k]


_store = _BucketStore()

# Cleanup counter — run cleanup every N requests to avoid unbounded memory
_request_counter = 0
_CLEANUP_INTERVAL = 5000


# ---------------------------------------------------------------------------
# DB logging (fire-and-forget on violation)
# ---------------------------------------------------------------------------

def _log_violation_to_db(ip_address: str, user_id: str | None, endpoint: str):
    """Write a RateLimitEvent row. Runs in the calling thread but uses its own
    short-lived session to avoid blocking the request pipeline."""
    try:
        from api.database import SessionLocal
        from api.models import RateLimitEvent

        db = SessionLocal()
        try:
            import uuid as _uuid
            event = RateLimitEvent(
                ip_address=ip_address,
                user_id=_uuid.UUID(user_id) if user_id else None,
                endpoint=endpoint,
            )
            db.add(event)
            db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to log rate limit event: {e}")


# ---------------------------------------------------------------------------
# User ID extraction (lightweight — no DB query)
# ---------------------------------------------------------------------------

def _extract_user_id(request: Request) -> str | None:
    """Try to extract user_id from JWT in cookie without DB lookup."""
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        from api.auth import decode_token
        payload = decode_token(token)
        return payload.get("sub")
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Tier classification
# ---------------------------------------------------------------------------

def _classify(request: Request, user_id: str | None) -> tuple[str | None, dict | None]:
    """Determine which rate-limit tier applies to a request.

    Returns (tier_name, tier_config) or (None, None) if no limit applies.
    """
    path = request.url.path
    method = request.method

    # Skip paths
    for skip in SKIP_PATHS:
        if path.startswith(skip):
            return None, None

    # Login tier (highest priority, most restrictive)
    login = TIERS["login"]
    if method in login["methods"] and path in login["paths"]:
        return "login", login

    # Webhook tier
    webhook = TIERS["webhook"]
    if method in webhook["methods"] and path.startswith(webhook["prefix"]):
        return "webhook", webhook

    # Upload tier
    upload = TIERS["upload"]
    if method in upload["methods"] and path.startswith(upload["prefix"]):
        return "upload", upload

    # General API — split by authentication status
    if path.startswith("/api/"):
        if user_id:
            return "authenticated", TIERS["authenticated"]
        else:
            return "unauthenticated", TIERS["unauthenticated"]

    return None, None


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Production rate-limiting middleware.

    Features:
      - Per-IP tracking for login / unauthenticated requests
      - Per-user tracking for authenticated API requests
      - In-memory sliding window (no DB reads)
      - DB write only on violations (RateLimitEvent table)
      - X-RateLimit-Remaining / X-RateLimit-Reset response headers
      - Configurable via RATE_LIMIT_ENABLED env var
    """

    async def dispatch(self, request: Request, call_next):
        if not RATE_LIMIT_ENABLED:
            return await call_next(request)

        # Periodic cleanup
        global _request_counter
        _request_counter += 1
        if _request_counter >= _CLEANUP_INTERVAL:
            _request_counter = 0
            _store.cleanup()

        client_ip = request.client.host if request.client else "unknown"
        user_id = _extract_user_id(request)

        tier_name, tier_cfg = _classify(request, user_id)
        if tier_name is None:
            return await call_next(request)

        # Determine the bucket key
        keyed_by = tier_cfg.get("keyed_by", "ip")
        if keyed_by == "user" and user_id:
            bucket_key = f"user:{user_id}"
        else:
            bucket_key = f"ip:{client_ip}"

        allowed, remaining, reset_at = _store.record_and_check(
            tier_name, bucket_key, tier_cfg["max"], tier_cfg["window"]
        )

        if not allowed:
            logger.warning(
                f"Rate limit [{tier_name}] exceeded: key={bucket_key} "
                f"endpoint={request.url.path}"
            )
            # Log violation to DB (fire-and-forget)
            _log_violation_to_db(client_ip, user_id, request.url.path)

            reset_seconds = max(1, int(reset_at - time.time()))
            return JSONResponse(
                status_code=429,
                content={"detail": tier_cfg["message"]},
                headers={
                    "Retry-After": str(reset_seconds),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(reset_at)),
                },
            )

        response = await call_next(request)

        # Add rate limit headers to successful responses
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(reset_at))

        return response
