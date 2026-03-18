"""Telegram bot router — bot status, chat testing, webhook, subscriptions."""

import logging
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.roles import require_admin
from api.config import get_settings

logger = logging.getLogger("moonjar.telegram")

router = APIRouter()


# ────────────────────────────────────────────────────────────────
# In-memory cache for bot status (avoids repeated Telegram API calls)
# ────────────────────────────────────────────────────────────────
_bot_status_cache: dict | None = None
_bot_status_cached_at: float = 0
_BOT_STATUS_TTL = 300  # 5 minutes

# ────────────────────────────────────────────────────────────────
# In-memory store: recent chats seen via webhook (for chat ID discovery)
# Key: chat_id (str) → {chat_id, title, type, username, last_seen}
# ────────────────────────────────────────────────────────────────
_recent_webhook_chats: dict[str, dict] = {}
_MAX_RECENT_CHATS = 50


def _record_chat_from_update(body: dict) -> None:
    """Extract chat info from a Telegram webhook update and store it."""
    global _recent_webhook_chats
    chat = None

    # Try all possible locations where chat info lives in an update
    for key in ("message", "edited_message", "channel_post", "edited_channel_post"):
        if key in body and "chat" in body[key]:
            chat = body[key]["chat"]
            break

    if not chat:
        # my_chat_member / chat_member updates
        for key in ("my_chat_member", "chat_member"):
            if key in body and "chat" in body[key]:
                chat = body[key]["chat"]
                break

    if not chat:
        # callback_query
        cb = body.get("callback_query", {})
        if "message" in cb and "chat" in cb["message"]:
            chat = cb["message"]["chat"]

    if not chat:
        return

    chat_id = str(chat.get("id", ""))
    if not chat_id:
        return

    _recent_webhook_chats[chat_id] = {
        "chat_id": chat_id,
        "title": chat.get("title") or chat.get("first_name", ""),
        "type": chat.get("type", ""),
        "username": chat.get("username"),
        "last_seen": time.time(),
    }

    # Evict oldest if too many
    if len(_recent_webhook_chats) > _MAX_RECENT_CHATS:
        oldest_key = min(_recent_webhook_chats, key=lambda k: _recent_webhook_chats[k]["last_seen"])
        del _recent_webhook_chats[oldest_key]


# ────────────────────────────────────────────────────────────────
# Bot status & testing (admin-only)
# ────────────────────────────────────────────────────────────────

@router.get("/bot-status")
async def get_bot_status(
    force: bool = False,
    current_user=Depends(require_admin),
):
    """
    Check Telegram bot connection status.
    Results are cached for 5 minutes to avoid slow API calls on every page load.
    Pass ?force=true to bypass the cache.
    """
    global _bot_status_cache, _bot_status_cached_at

    # Return cached result if still valid
    if not force and _bot_status_cache and (time.time() - _bot_status_cached_at < _BOT_STATUS_TTL):
        return _bot_status_cache

    settings = get_settings()
    token = settings.TELEGRAM_BOT_TOKEN

    if not token:
        result = {
            "connected": False,
            "message": "Bot token not configured. Set TELEGRAM_BOT_TOKEN environment variable.",
        }
        _bot_status_cache = result
        _bot_status_cached_at = time.time()
        return result

    import httpx

    # Mask token for debug: show first 5 and last 4 chars
    masked = f"{token[:5]}...{token[-4:]}" if len(token) > 12 else "***"

    last_error = ""
    for attempt in range(2):  # retry once on timeout
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"https://api.telegram.org/bot{token}/getMe",
                    timeout=8.0,
                )

            if resp.status_code == 401:
                logger.warning(f"Telegram bot token invalid (401): {masked}")
                result = {
                    "connected": False,
                    "error": f"Invalid bot token ({masked}). Check TELEGRAM_BOT_TOKEN.",
                }
                _bot_status_cache = result
                _bot_status_cached_at = time.time()
                return result

            data = resp.json()

            if data.get("ok"):
                bot = data["result"]
                logger.info(f"Telegram bot connected: @{bot.get('username', '')}")
                result = {
                    "connected": True,
                    "bot_username": f"@{bot.get('username', '')}",
                    "bot_name": bot.get("first_name", ""),
                    "bot_id": bot.get("id"),
                    "owner_chat_configured": bool(settings.TELEGRAM_OWNER_CHAT_ID),
                }
                _bot_status_cache = result
                _bot_status_cached_at = time.time()
                return result
            else:
                err_desc = data.get("description", "Unknown error from Telegram API")
                logger.warning(f"Telegram getMe error: {err_desc}")
                result = {
                    "connected": False,
                    "error": err_desc,
                }
                _bot_status_cache = result
                _bot_status_cached_at = time.time()
                return result
        except httpx.TimeoutException:
            last_error = f"Telegram API timeout (attempt {attempt + 1}/2, token: {masked})"
            logger.warning(last_error)
            continue
        except httpx.ConnectError as e:
            last_error = f"Cannot connect to Telegram API: {e}"
            logger.warning(last_error)
            break
        except Exception as e:
            last_error = f"Telegram bot check failed: {e}"
            logger.warning(last_error)
            break

    # On total failure: return stale cache if available (better than empty spinner)
    if _bot_status_cache and _bot_status_cache.get("connected"):
        logger.info("Returning stale bot-status cache after timeout")
        return {**_bot_status_cache, "cached": True}

    result = {"connected": False, "error": last_error or "Failed to check bot status"}
    # Cache failures for 60s (shorter TTL so we retry sooner)
    _bot_status_cache = result
    _bot_status_cached_at = time.time() - _BOT_STATUS_TTL + 60
    return result


class OwnerChatRequest(BaseModel):
    chat_id: str

    @field_validator('chat_id')
    @classmethod
    def validate_chat_id(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('chat_id is required')
        if not v.lstrip('-').isdigit():
            raise ValueError('chat_id must be numeric (e.g. -1001234567890)')
        return v


@router.get("/owner-chat")
async def get_owner_chat(
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Get the current owner/admin Telegram chat ID."""
    from api.models import SystemSetting
    setting = db.query(SystemSetting).filter(
        SystemSetting.key == "telegram_owner_chat_id"
    ).first()
    db_value = setting.value if setting else None

    # Fallback to env var
    env_value = get_settings().TELEGRAM_OWNER_CHAT_ID or None

    return {
        "chat_id": db_value or env_value,
        "source": "database" if db_value else ("environment" if env_value else "not_set"),
    }


@router.put("/owner-chat")
async def set_owner_chat(
    data: OwnerChatRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Set the owner/admin Telegram chat ID (stored in database)."""
    from api.models import SystemSetting

    setting = db.query(SystemSetting).filter(
        SystemSetting.key == "telegram_owner_chat_id"
    ).first()

    if setting:
        setting.value = data.chat_id
    else:
        setting = SystemSetting(key="telegram_owner_chat_id", value=data.chat_id)
        db.add(setting)

    db.commit()
    logger.info(f"Owner chat ID set to {data.chat_id} by {current_user.email}")

    return {"success": True, "chat_id": data.chat_id}


class TestChatRequest(BaseModel):
    chat_id: str

    @field_validator('chat_id')
    @classmethod
    def validate_chat_id(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('chat_id is required')
        if not v.lstrip('-').isdigit():
            raise ValueError('chat_id must be numeric (e.g. -1001234567890)')
        return v


@router.post("/test-chat")
async def test_chat(
    data: TestChatRequest,
    current_user=Depends(require_admin),
):
    """
    Send a test message to a Telegram chat to verify the chat ID is correct.
    Includes bot identity in error messages so user can verify it's the right bot.
    """
    settings = get_settings()
    token = settings.TELEGRAM_BOT_TOKEN

    if not token:
        raise HTTPException(400, "Bot token not configured")

    import httpx

    # Get bot username for diagnostics (from cache if available)
    bot_hint = ""
    if _bot_status_cache and _bot_status_cache.get("bot_username"):
        bot_hint = f" (bot: {_bot_status_cache['bot_username']})"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={
                    "chat_id": data.chat_id,
                    "text": "✅ *Moonjar PMS connected!*\nThis chat is now linked to your production system.",
                    "parse_mode": "Markdown",
                },
            )
            result = resp.json()

        if result.get("ok"):
            chat = result["result"].get("chat", {})
            return {
                "success": True,
                "chat_title": chat.get("title") or chat.get("first_name", ""),
                "chat_type": chat.get("type", ""),
            }
        else:
            error = result.get("description", "Unknown error")
            # Add bot identity hint to common errors
            if "not a member" in error.lower() or "forbidden" in error.lower():
                error = f"{error}{bot_hint}. Make sure THIS bot is added to the group as admin."
            elif "chat not found" in error.lower():
                error = f"{error}. Check the chat ID — use 'Discover Chat IDs' button to find correct IDs."
            return {"success": False, "error": error}
    except httpx.TimeoutException:
        return {"success": False, "error": f"Telegram API timeout{bot_hint}"}
    except Exception as e:
        logger.warning(f"Telegram test-chat failed: {e}")
        return {"success": False, "error": f"Failed to send test message: {e}"}


# ────────────────────────────────────────────────────────────────
# Discover chat IDs from webhook history (admin-only)
# ────────────────────────────────────────────────────────────────

@router.get("/recent-chats")
async def get_recent_chats(current_user=Depends(require_admin)):
    """
    Return chats the bot has seen via webhook since last server restart.
    Write a message or use /start in a group, then call this endpoint.
    No external API calls needed — reads from in-memory store.
    """
    chats = sorted(
        _recent_webhook_chats.values(),
        key=lambda c: c.get("last_seen", 0),
        reverse=True,
    )
    # Strip last_seen from response
    clean = [
        {k: v for k, v in c.items() if k != "last_seen"}
        for c in chats
    ]
    return {
        "chats": clean,
        "hint": (
            "No chats recorded yet. Write any message (or /start) in the group "
            "where the bot is added, then click Discover again."
        ) if not clean else None,
    }


# ────────────────────────────────────────────────────────────────
# Webhook (NO auth — Telegram sends updates directly)
# ────────────────────────────────────────────────────────────────

@router.post("/webhook")
async def telegram_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Telegram webhook endpoint.
    Receives Update JSON from Telegram, dispatches to bot handler.
    Must always return 200 OK (Telegram retries on non-200).
    Verified via X-Telegram-Bot-Api-Secret-Token header if TELEGRAM_WEBHOOK_SECRET is set.
    """
    from fastapi.responses import JSONResponse
    import os

    # Verify Telegram webhook secret token if configured
    webhook_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
    if webhook_secret:
        header_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if header_secret != webhook_secret:
            logger.warning("Telegram webhook: invalid or missing secret token")
            return JSONResponse(status_code=403, content={"detail": "Forbidden"})

    try:
        body = await request.json()
    except Exception:
        logger.warning("Telegram webhook: invalid JSON body")
        return JSONResponse({"ok": True})

    # Record chat info for the "Discover Chat IDs" feature
    try:
        _record_chat_from_update(body)
    except Exception:
        pass  # never fail on recording

    # Dispatch to bot handler (fire-and-forget style, but we await to catch errors)
    try:
        from business.services.telegram_bot import handle_update
        await handle_update(db, body)
    except Exception as e:
        # Never crash — Telegram will retry endlessly on non-200
        logger.error(f"Telegram webhook handler error: {e}", exc_info=True)

    return JSONResponse({"ok": True})


# ────────────────────────────────────────────────────────────────
# Subscribe / Unsubscribe (authenticated PMS endpoints)
# ────────────────────────────────────────────────────────────────

class SubscribeRequest(BaseModel):
    telegram_user_id: int

    @field_validator('telegram_user_id')
    @classmethod
    def validate_telegram_user_id(cls, v: int) -> int:
        if v <= 0:
            raise ValueError('telegram_user_id must be a positive integer')
        return v


@router.post("/subscribe")
async def telegram_subscribe(
    data: SubscribeRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Link a Telegram user ID to the authenticated PMS user.
    Called from the PMS frontend settings page.
    """
    from api.models import User

    # Check if this telegram_user_id is already linked to another user
    existing = (
        db.query(User)
        .filter(
            User.telegram_user_id == data.telegram_user_id,
            User.id != current_user.id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            409,
            "This Telegram account is already linked to another PMS user.",
        )

    current_user.telegram_user_id = data.telegram_user_id
    db.commit()

    logger.info(
        f"User {current_user.email} subscribed Telegram ID {data.telegram_user_id}"
    )

    return {
        "success": True,
        "telegram_user_id": data.telegram_user_id,
        "message": "Telegram account linked successfully.",
    }


@router.delete("/unsubscribe")
async def telegram_unsubscribe(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Unlink Telegram from the authenticated PMS user.
    Clears telegram_user_id.
    """
    old_id = current_user.telegram_user_id
    if not old_id:
        return {
            "success": True,
            "message": "No Telegram account was linked.",
        }

    current_user.telegram_user_id = None
    db.commit()

    logger.info(f"User {current_user.email} unsubscribed Telegram ID {old_id}")

    return {
        "success": True,
        "message": "Telegram account unlinked successfully.",
    }
