"""Telegram bot router — bot status, chat testing, webhook, subscriptions."""

import logging
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
# Bot status & testing (admin-only)
# ────────────────────────────────────────────────────────────────

@router.get("/bot-status")
async def get_bot_status(current_user=Depends(require_admin)):
    """
    Check Telegram bot connection status.
    Calls Telegram API getMe to verify the bot token is valid.
    Retries once on timeout.
    """
    settings = get_settings()
    token = settings.TELEGRAM_BOT_TOKEN

    if not token:
        return {
            "connected": False,
            "message": "Bot token not configured. Set TELEGRAM_BOT_TOKEN environment variable.",
        }

    import httpx

    # Mask token for debug: show first 5 and last 4 chars
    masked = f"{token[:5]}...{token[-4:]}" if len(token) > 12 else "***"

    last_error = ""
    for attempt in range(2):  # retry once on timeout
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"https://api.telegram.org/bot{token}/getMe",
                    timeout=15.0,
                )

            if resp.status_code == 401:
                logger.warning(f"Telegram bot token invalid (401): {masked}")
                return {
                    "connected": False,
                    "error": f"Invalid bot token ({masked}). Check TELEGRAM_BOT_TOKEN.",
                }

            data = resp.json()

            if data.get("ok"):
                bot = data["result"]
                logger.info(f"Telegram bot connected: @{bot.get('username', '')}")
                return {
                    "connected": True,
                    "bot_username": f"@{bot.get('username', '')}",
                    "bot_name": bot.get("first_name", ""),
                    "bot_id": bot.get("id"),
                    "owner_chat_configured": bool(settings.TELEGRAM_OWNER_CHAT_ID),
                }
            else:
                err_desc = data.get("description", "Unknown error from Telegram API")
                logger.warning(f"Telegram getMe error: {err_desc}")
                return {
                    "connected": False,
                    "error": err_desc,
                }
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

    return {"connected": False, "error": last_error or "Failed to check bot status"}


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
    """
    settings = get_settings()
    token = settings.TELEGRAM_BOT_TOKEN

    if not token:
        raise HTTPException(400, "Bot token not configured")

    import httpx
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={
                    "chat_id": data.chat_id,
                    "text": "✅ *Moonjar PMS connected!*\nThis chat is now linked to your production system.",
                    "parse_mode": "Markdown",
                },
                timeout=10.0,
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
            return {"success": False, "error": error}
    except httpx.TimeoutException:
        return {"success": False, "error": "Telegram API timeout"}
    except Exception as e:
        logger.warning(f"Telegram test-chat failed: {e}")
        return {"success": False, "error": "Failed to send test message"}


# ────────────────────────────────────────────────────────────────
# Webhook (NO auth — Telegram sends updates directly)
# ────────────────────────────────────────────────────────────────

@router.post("/webhook")
async def telegram_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Telegram webhook endpoint.
    Receives Update JSON from Telegram, dispatches to bot handler.
    Must always return 200 OK (Telegram retries on non-200).
    No authentication — Telegram sends raw POST requests.
    """
    from fastapi.responses import JSONResponse

    try:
        body = await request.json()
    except Exception:
        logger.warning("Telegram webhook: invalid JSON body")
        return JSONResponse({"ok": True})

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
