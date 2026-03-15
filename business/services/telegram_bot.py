"""
Telegram Bot handler service.
Business Logic: §27 (Notifications), §37 (Telegram Bot)

Processes incoming Telegram webhook updates:
- Commands: /start, /status, /help, /stop
- Photos: receive from masters, store with position linking
- Callback queries: inline button presses
"""

import logging
from typing import Optional
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from api.config import get_settings
from api.models import (
    User, Task, OrderPosition, ProductionOrder,
    Factory, UserFactory, PositionPhoto,
)
from api.enums import TaskStatus

logger = logging.getLogger("moonjar.telegram_bot")

TELEGRAM_API = "https://api.telegram.org/bot{token}"


# ────────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────────

async def handle_update(db: Session, update_data: dict) -> None:
    """
    Main dispatcher for incoming Telegram updates.
    Routes to the appropriate handler based on update type.
    """
    update_id = update_data.get("update_id", "?")
    logger.info(f"Telegram update #{update_id}: {_safe_summary(update_data)}")

    try:
        # Callback query (inline button press) — highest priority
        if "callback_query" in update_data:
            await handle_callback_query(db, update_data["callback_query"])
            return

        message = update_data.get("message")
        if not message:
            # edited_message, channel_post, etc. — ignore silently
            logger.debug(f"Ignoring non-message update #{update_id}")
            return

        # Photo message
        if message.get("photo"):
            await handle_photo(db, message)
            return

        # Text command
        text = (message.get("text") or "").strip()
        if text.startswith("/"):
            await handle_command(db, message)
            return

        # Plain text in private chat — could be email for linking flow
        chat_type = message.get("chat", {}).get("type", "")
        if chat_type == "private" and text:
            await _handle_private_text(db, message)
            return

        logger.debug(f"Ignoring message type in update #{update_id}")

    except Exception as e:
        logger.error(f"Error handling update #{update_id}: {e}", exc_info=True)


async def handle_command(db: Session, message: dict) -> None:
    """Route /commands to specific handlers."""
    text = (message.get("text") or "").strip()
    chat_id = message["chat"]["id"]
    parts = text.split(maxsplit=1)
    command = parts[0].lower().split("@")[0]  # strip @botname suffix
    args = parts[1] if len(parts) > 1 else ""

    if command == "/start":
        await _cmd_start(db, message, args)
    elif command == "/status":
        await _cmd_status(db, message)
    elif command == "/help":
        await _cmd_help(db, message)
    elif command == "/stop":
        await _cmd_stop(db, message)
    else:
        await _send_message(
            chat_id,
            "Unknown command. Send /help for available commands.",
        )


async def handle_photo(db: Session, message: dict) -> None:
    """
    Receive a photo from a master in a group chat.
    Downloads the file_id and creates a PositionPhoto record.
    """
    chat_id = message["chat"]["id"]
    from_user = message.get("from", {})
    telegram_user_id = from_user.get("id")
    caption = (message.get("caption") or "").strip()

    # Get the highest-resolution photo (last in the array)
    photos = message.get("photo", [])
    if not photos:
        return
    best_photo = photos[-1]
    file_id = best_photo["file_id"]

    # Determine factory from group chat_id
    factory = (
        db.query(Factory)
        .filter(Factory.masters_group_chat_id == chat_id)
        .first()
    )
    if not factory:
        # Also check purchaser_chat_id
        factory = (
            db.query(Factory)
            .filter(Factory.purchaser_chat_id == chat_id)
            .first()
        )

    if not factory:
        # Private chat or unlinked group — try to find factory via user
        user = _find_user_by_telegram(db, telegram_user_id)
        if user:
            uf = (
                db.query(UserFactory)
                .filter(UserFactory.user_id == user.id)
                .first()
            )
            if uf:
                factory = db.query(Factory).filter(Factory.id == uf.factory_id).first()

    if not factory:
        logger.warning(f"Photo from unknown chat {chat_id}, user {telegram_user_id} — no factory found")
        await _send_message(chat_id, "Cannot determine factory for this photo.")
        return

    # Look up the PMS user
    user = _find_user_by_telegram(db, telegram_user_id)

    # Determine photo_type from caption keywords
    photo_type = _detect_photo_type(caption)

    # Create the photo record
    photo = PositionPhoto(
        factory_id=factory.id,
        telegram_file_id=file_id,
        telegram_chat_id=chat_id,
        uploaded_by_telegram_id=telegram_user_id,
        uploaded_by_user_id=user.id if user else None,
        photo_type=photo_type,
        caption=caption or None,
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)

    logger.info(
        f"Photo saved: id={photo.id}, factory={factory.name}, "
        f"type={photo_type}, file_id={file_id[:20]}..."
    )

    # Acknowledge receipt
    type_label = photo_type.replace("_", " ").title() if photo_type else "Photo"
    await _send_message(chat_id, f"Foto diterima ({type_label}).")


async def handle_callback_query(db: Session, callback_query: dict) -> None:
    """Handle inline button presses.

    Routes compact callback data prefixes to the appropriate handler:
      d:*  — daily distribution callbacks (ack, problem, detail)
      a:*  — alert callbacks (view position, reschedule kiln)
      t:*  — task callbacks (start, done, issue)
      link_confirm / task_done — legacy actions
    """
    callback_id = callback_query.get("id")
    data = callback_query.get("data", "")
    from_user = callback_query.get("from", {})
    telegram_user_id = from_user.get("id")

    logger.info(f"Callback query from {telegram_user_id}: data={data}")

    # Parse callback data format: "action:param1:param2"
    parts = data.split(":", maxsplit=2)
    action = parts[0] if parts else ""

    # Route daily/alert/task callbacks to the dedicated handler service
    if action in ("d", "a", "t"):
        try:
            from business.services.telegram_callbacks import handle_callback
            response_text = handle_callback(db, callback_query)
            await answer_callback_query(callback_id, response_text)
        except Exception as e:
            logger.error(f"Callback handler error for data={data}: {e}", exc_info=True)
            await answer_callback_query(callback_id, "Terjadi kesalahan")
        return

    if action == "link_confirm":
        # Future: confirm account linking
        await answer_callback_query(callback_id, "Account linked!")
    elif action == "task_done":
        # Future: mark task as done from Telegram
        await answer_callback_query(callback_id, "Task completion not yet implemented.")
    else:
        await answer_callback_query(callback_id, "OK")


async def answer_callback_query(
    callback_query_id: str,
    text: str,
    show_alert: bool = False,
) -> None:
    """Send answerCallbackQuery to Telegram API."""
    settings = get_settings()
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        return

    url = f"{TELEGRAM_API.format(token=token)}/answerCallbackQuery"
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                url,
                json={
                    "callback_query_id": callback_query_id,
                    "text": text,
                    "show_alert": show_alert,
                },
                timeout=10.0,
            )
    except Exception as e:
        logger.warning(f"answerCallbackQuery failed: {e}")


async def send_message_with_buttons(
    chat_id: int,
    text: str,
    inline_keyboard: list[list[dict]],
    parse_mode: str = "Markdown",
) -> Optional[dict]:
    """
    Send a message with InlineKeyboardMarkup.

    inline_keyboard format:
    [
        [{"text": "Button 1", "callback_data": "action:param"}],
        [{"text": "Button 2", "url": "https://..."}],
    ]
    """
    settings = get_settings()
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        return None

    url = f"{TELEGRAM_API.format(token=token)}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "reply_markup": {
            "inline_keyboard": inline_keyboard,
        },
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=10.0)
            data = resp.json()
            if not data.get("ok"):
                logger.warning(f"sendMessage with buttons failed: {data.get('description')}")
            return data
    except Exception as e:
        logger.warning(f"sendMessage with buttons failed: {e}")
        return None


async def download_telegram_photo(file_id: str) -> Optional[bytes]:
    """
    Download a photo from Telegram via getFile API.
    Returns the raw bytes, or None on failure.
    """
    settings = get_settings()
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        return None

    try:
        async with httpx.AsyncClient() as client:
            # Step 1: get file path
            resp = await client.get(
                f"{TELEGRAM_API.format(token=token)}/getFile",
                params={"file_id": file_id},
                timeout=10.0,
            )
            data = resp.json()
            if not data.get("ok"):
                logger.warning(f"getFile failed: {data.get('description')}")
                return None

            file_path = data["result"]["file_path"]

            # Step 2: download the file
            file_url = f"https://api.telegram.org/file/bot{token}/{file_path}"
            file_resp = await client.get(file_url, timeout=30.0)
            if file_resp.status_code == 200:
                return file_resp.content
            else:
                logger.warning(f"File download failed: HTTP {file_resp.status_code}")
                return None
    except Exception as e:
        logger.warning(f"download_telegram_photo failed: {e}")
        return None


def set_webhook(webhook_url: str) -> bool:
    """
    Register webhook URL with Telegram Bot API.
    Called synchronously on startup.
    Returns True if successful.
    """
    settings = get_settings()
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        logger.debug("set_webhook: TELEGRAM_BOT_TOKEN not configured, skipping")
        return False

    url = f"{TELEGRAM_API.format(token=token)}/setWebhook"
    try:
        resp = httpx.post(
            url,
            json={
                "url": webhook_url,
                "allowed_updates": ["message", "callback_query"],
                "drop_pending_updates": False,
            },
            timeout=15.0,
        )
        data = resp.json()
        if data.get("ok"):
            logger.info(f"Telegram webhook set to: {webhook_url}")
            return True
        else:
            logger.warning(f"setWebhook failed: {data.get('description')}")
            return False
    except Exception as e:
        logger.warning(f"setWebhook failed: {e}")
        return False


# ────────────────────────────────────────────────────────────────
# Command handlers
# ────────────────────────────────────────────────────────────────

async def _cmd_start(db: Session, message: dict, args: str) -> None:
    """
    /start — Account linking flow (private) or welcome (group).
    /start {deep_link_code} — Deep linking (logged for future use).
    """
    chat_id = message["chat"]["id"]
    chat_type = message["chat"].get("type", "private")
    from_user = message.get("from", {})
    telegram_user_id = from_user.get("id")
    first_name = from_user.get("first_name", "")

    if args:
        # Deep link — log for future use
        logger.info(f"Deep link start: user={telegram_user_id}, code={args}")
        await _send_message(
            chat_id,
            f"Welcome, {first_name}! Deep link code received: `{args}`\n"
            f"This feature is coming soon.",
        )
        return

    if chat_type != "private":
        # Group chat — just welcome
        await _send_message(
            chat_id,
            f"Moonjar PMS Bot aktif di grup ini.\n"
            f"Kirim foto untuk dokumentasi produksi.\n"
            f"Ketik /help untuk daftar perintah.",
        )
        return

    # Private chat — check if already linked
    existing = _find_user_by_telegram(db, telegram_user_id)
    if existing:
        await _send_message(
            chat_id,
            f"Akun Anda sudah terhubung sebagai *{existing.name}* ({existing.email}).\n"
            f"Ketik /stop untuk memutuskan koneksi.",
        )
        return

    # Ask for email to link
    await _send_message(
        chat_id,
        f"Selamat datang di *Moonjar PMS*, {first_name}!\n\n"
        f"Untuk menghubungkan akun Telegram Anda, "
        f"silakan kirim email yang terdaftar di sistem PMS.",
    )


async def _cmd_status(db: Session, message: dict) -> None:
    """
    /status — Show user's pending tasks.
    Queries Task where assigned_to = user.id and status not completed.
    """
    chat_id = message["chat"]["id"]
    from_user = message.get("from", {})
    telegram_user_id = from_user.get("id")

    user = _find_user_by_telegram(db, telegram_user_id)
    if not user:
        await _send_message(chat_id, "Akun belum terhubung. Ketik /start untuk menghubungkan.")
        return

    # Find pending/in-progress tasks assigned to this user
    tasks = (
        db.query(Task)
        .filter(
            Task.assigned_to == user.id,
            Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS]),
        )
        .order_by(Task.priority.desc(), Task.created_at)
        .limit(20)
        .all()
    )

    if not tasks:
        await _send_message(chat_id, "Tidak ada tugas yang tertunda.")
        return

    lines = ["Tugas Anda:"]
    for i, task in enumerate(tasks, 1):
        # Try to get order number if task has related_order_id
        order_label = ""
        position_label = ""
        if task.related_order_id:
            order = db.query(ProductionOrder).filter(
                ProductionOrder.id == task.related_order_id
            ).first()
            if order:
                order_label = f" {order.order_number}"
        if task.related_position_id:
            pos = db.query(OrderPosition).filter(
                OrderPosition.id == task.related_position_id
            ).first()
            if pos and pos.position_number:
                pos_label = f"#{pos.position_number}"
                if pos.split_index:
                    pos_label += f".{pos.split_index}"
                position_label = f" Pos {pos_label}"

        task_type_display = task.type.value.replace("_", " ").title() if task.type else "Task"
        status_icon = "" if task.status == TaskStatus.IN_PROGRESS else ""

        desc = task.description[:60] if task.description else task_type_display
        line = f"{i}. {status_icon}{order_label}{position_label} — {desc}"
        lines.append(line)

    await _send_message(chat_id, "\n".join(lines))


async def _cmd_help(db: Session, message: dict) -> None:
    """/help — List available commands."""
    chat_id = message["chat"]["id"]
    help_text = (
        "*Moonjar PMS Bot*\n\n"
        "Perintah yang tersedia:\n"
        "/start — Hubungkan akun Telegram\n"
        "/status — Lihat tugas yang tertunda\n"
        "/help — Tampilkan bantuan ini\n"
        "/stop — Putuskan koneksi akun\n\n"
        "Kirim foto di grup untuk dokumentasi produksi."
    )
    await _send_message(chat_id, help_text)


async def _cmd_stop(db: Session, message: dict) -> None:
    """/stop — Unlink Telegram account."""
    chat_id = message["chat"]["id"]
    from_user = message.get("from", {})
    telegram_user_id = from_user.get("id")

    user = _find_user_by_telegram(db, telegram_user_id)
    if not user:
        await _send_message(chat_id, "Akun tidak terhubung.")
        return

    user.telegram_user_id = None
    db.commit()
    logger.info(f"User {user.email} unlinked Telegram account {telegram_user_id}")

    await _send_message(
        chat_id,
        "Akun Telegram Anda telah diputuskan dari Moonjar PMS.\n"
        "Ketik /start untuk menghubungkan kembali.",
    )


# ────────────────────────────────────────────────────────────────
# Private text handler (email linking flow)
# ────────────────────────────────────────────────────────────────

async def _handle_private_text(db: Session, message: dict) -> None:
    """
    Handle plain text in private chat — part of the /start email linking flow.
    If the text looks like an email, attempt to link the account.
    """
    chat_id = message["chat"]["id"]
    from_user = message.get("from", {})
    telegram_user_id = from_user.get("id")
    text = (message.get("text") or "").strip()

    # Check if already linked
    existing = _find_user_by_telegram(db, telegram_user_id)
    if existing:
        await _send_message(
            chat_id,
            f"Akun sudah terhubung sebagai *{existing.name}*.\n"
            f"Ketik /stop untuk memutuskan, lalu /start untuk menghubungkan akun lain.",
        )
        return

    # Check if it looks like an email
    if "@" not in text or "." not in text:
        await _send_message(
            chat_id,
            "Silakan kirim email yang terdaftar di Moonjar PMS untuk menghubungkan akun.",
        )
        return

    email = text.lower().strip()

    # Look up user by email
    user = db.query(User).filter(User.email == email, User.is_active.is_(True)).first()
    if not user:
        await _send_message(chat_id, "Email tidak ditemukan di sistem.")
        return

    # Check if this user already has a different Telegram linked
    if user.telegram_user_id and user.telegram_user_id != telegram_user_id:
        await _send_message(
            chat_id,
            "Akun PMS ini sudah terhubung ke akun Telegram lain.\n"
            "Hubungi administrator untuk bantuan.",
        )
        return

    # Link the account
    user.telegram_user_id = telegram_user_id
    db.commit()
    logger.info(f"Linked Telegram {telegram_user_id} to user {user.email} (id={user.id})")

    await _send_message(
        chat_id,
        f"Terhubung! Akun Telegram Anda sekarang terhubung ke *{user.name}* ({user.email}).\n\n"
        f"Anda akan menerima notifikasi produksi di sini.\n"
        f"Ketik /status untuk melihat tugas Anda.",
    )


# ────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────

def _find_user_by_telegram(db: Session, telegram_user_id: int) -> Optional[User]:
    """Find active User by telegram_user_id."""
    if not telegram_user_id:
        return None
    return (
        db.query(User)
        .filter(User.telegram_user_id == telegram_user_id, User.is_active.is_(True))
        .first()
    )


def _detect_photo_type(caption: str) -> str:
    """Detect photo type from caption keywords."""
    if not caption:
        return "other"
    caption_lower = caption.lower()

    if any(kw in caption_lower for kw in ("glaz", "glasir", "engobe")):
        return "glazing"
    if any(kw in caption_lower for kw in ("fir", "bakar", "kiln", "oven")):
        return "firing"
    if any(kw in caption_lower for kw in ("defect", "cacat", "reject", "pecah", "retak")):
        return "defect"
    if any(kw in caption_lower for kw in ("pack", "kemas", "box")):
        return "packing"
    return "other"


async def _send_message(
    chat_id: int,
    text: str,
    parse_mode: str = "Markdown",
) -> Optional[dict]:
    """Send a plain text message via Telegram Bot API (async)."""
    settings = get_settings()
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        logger.debug("_send_message: no bot token configured")
        return None

    url = f"{TELEGRAM_API.format(token=token)}/sendMessage"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": parse_mode,
                },
                timeout=10.0,
            )
            data = resp.json()
            if not data.get("ok"):
                logger.warning(
                    f"sendMessage failed (chat={chat_id}): {data.get('description')}"
                )
            return data
    except Exception as e:
        logger.warning(f"sendMessage failed (chat={chat_id}): {e}")
        return None


def _safe_summary(update_data: dict) -> str:
    """Create a safe log summary of a Telegram update (no sensitive data)."""
    parts = []
    if "message" in update_data:
        msg = update_data["message"]
        chat = msg.get("chat", {})
        parts.append(f"chat_type={chat.get('type')}")
        parts.append(f"chat_id={chat.get('id')}")
        if msg.get("text"):
            text_preview = msg["text"][:50]
            parts.append(f"text={text_preview!r}")
        if msg.get("photo"):
            parts.append(f"photo_count={len(msg['photo'])}")
        from_user = msg.get("from", {})
        parts.append(f"from_id={from_user.get('id')}")
    elif "callback_query" in update_data:
        cq = update_data["callback_query"]
        parts.append(f"callback_data={cq.get('data', '')!r}")
        parts.append(f"from_id={cq.get('from', {}).get('id')}")
    return ", ".join(parts) or "empty"
