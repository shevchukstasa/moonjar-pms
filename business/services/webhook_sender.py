"""
Outgoing webhook sender with retry + exponential backoff.

All PMS → Sales App webhooks go through send_webhook().
Retries up to 3 times with delays: 2s, 4s, 8s.
Failed deliveries are logged in sales_webhook_events with direction='outgoing'.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BASE_DELAY_S = 2  # 2, 4, 8 seconds


async def send_webhook(
    payload: dict,
    *,
    event_type: Optional[str] = None,
    external_id: Optional[str] = None,
) -> bool:
    """
    Send a webhook to the Sales app with retry logic.

    Returns True if delivered successfully, False otherwise.
    Logs each attempt; stores failed attempts in DB.
    """
    from api.config import get_settings

    settings = get_settings()

    if not settings.SALES_APP_URL or not settings.PRODUCTION_WEBHOOK_ENABLED:
        logger.debug("Webhook skipped: SALES_APP_URL or PRODUCTION_WEBHOOK_ENABLED not set")
        return False

    url = f"{settings.SALES_APP_URL}/api/webhooks/production-status"
    headers = {
        "Authorization": f"Bearer {settings.PRODUCTION_WEBHOOK_BEARER_TOKEN}",
        "Content-Type": "application/json",
    }

    import httpx

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload, headers=headers, timeout=15)
                if resp.status_code < 400:
                    logger.info(
                        "Webhook delivered: event=%s external_id=%s attempt=%d status=%d",
                        event_type or payload.get("event"),
                        external_id or payload.get("external_id"),
                        attempt,
                        resp.status_code,
                    )
                    return True
                else:
                    last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                    logger.warning(
                        "Webhook attempt %d/%d failed: %s",
                        attempt, MAX_RETRIES, last_error,
                    )
        except Exception as exc:
            last_error = str(exc)
            logger.warning(
                "Webhook attempt %d/%d exception: %s",
                attempt, MAX_RETRIES, last_error,
            )

        # Exponential backoff before next attempt
        if attempt < MAX_RETRIES:
            delay = BASE_DELAY_S * (2 ** (attempt - 1))
            await asyncio.sleep(delay)

    # All retries exhausted — log to DB
    logger.error(
        "Webhook FAILED after %d attempts: event=%s external_id=%s error=%s",
        MAX_RETRIES,
        event_type or payload.get("event"),
        external_id or payload.get("external_id"),
        last_error,
    )
    _log_failed_webhook(payload, last_error)
    return False


def _log_failed_webhook(payload: dict, error: str):
    """Store failed outgoing webhook in sales_webhook_events for manual retry."""
    try:
        from api.database import SessionLocal
        from sqlalchemy import text
        import json
        import uuid

        db = SessionLocal()
        try:
            db.execute(
                text(
                    "INSERT INTO sales_webhook_events "
                    "(id, event_type, event_id, payload, status, error_message, created_at) "
                    "VALUES (:id, :etype, :eid, cast(:pl as JSONB), 'failed_outgoing', :err, NOW())"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "etype": payload.get("event", "unknown"),
                    "eid": f"out_{payload.get('external_id', 'unknown')}_{datetime.now(timezone.utc).isoformat()}",
                    "pl": json.dumps(payload, default=str),
                    "err": error[:500] if error else None,
                },
            )
            db.commit()
        finally:
            db.close()
    except Exception as exc:
        logger.error("Failed to log webhook failure to DB: %s", exc)
