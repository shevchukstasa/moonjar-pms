"""Telegram bot router — bot status, chat testing, webhook, subscriptions."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
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
    """
    settings = get_settings()
    token = settings.TELEGRAM_BOT_TOKEN

    if not token:
        return {
            "connected": False,
            "message": "Bot token not configured. Set TELEGRAM_BOT_TOKEN environment variable.",
        }

    import httpx
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://api.telegram.org/bot{token}/getMe",
                timeout=10.0,
            )
            data = resp.json()

        if data.get("ok"):
            bot = data["result"]
            return {
                "connected": True,
                "bot_username": f"@{bot.get('username', '')}",
                "bot_name": bot.get("first_name", ""),
                "bot_id": bot.get("id"),
                "owner_chat_configured": bool(settings.TELEGRAM_OWNER_CHAT_ID),
            }
        else:
            return {
                "connected": False,
                "error": data.get("description", "Unknown error from Telegram API"),
            }
    except httpx.TimeoutException:
        return {"connected": False, "error": "Telegram API timeout"}
    except Exception as e:
        logger.warning(f"Telegram bot status check failed: {e}")
        return {"connected": False, "error": str(e)}


class TestChatRequest(BaseModel):
    chat_id: str


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
        return {"success": False, "error": str(e)}


# ────────────────────────────────────────────────────────────────
# Webhook & subscriptions (to be implemented)
# ────────────────────────────────────────────────────────────────

@router.post("/webhook")
async def telegram_webhook(request: Request, db: Session = Depends(get_db)):
    # TODO: Process Telegram bot updates — see API_CONTRACTS §18
    raise HTTPException(501, "Not implemented")


@router.post("/subscribe")
async def telegram_subscribe(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # TODO: Subscribe user to Telegram notifications — see API_CONTRACTS §18
    raise HTTPException(501, "Not implemented")


@router.delete("/unsubscribe")
async def telegram_unsubscribe(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # TODO: Unsubscribe from Telegram — see API_CONTRACTS §18
    raise HTTPException(501, "Not implemented")
