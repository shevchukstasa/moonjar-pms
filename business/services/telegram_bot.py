"""
Telegram Bot handler service.
Business Logic: §27 (Notifications), §37 (Telegram Bot)

Processes incoming Telegram webhook updates:
- Commands: /start, /status, /help, /stop, /defect, /actual, /split, /glaze, /recipe, /plan, /photo
- Photos: receive from masters, store with position linking
- Callback queries: inline button presses
"""

import logging
from datetime import date, timedelta
from typing import Optional
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from api.config import get_settings
from api.models import (
    User, Task, OrderPosition, ProductionOrder,
    Factory, UserFactory, PositionPhoto,
    Recipe, RecipeMaterial, RecipeKilnConfig, Material,
    Batch, Resource, DailyTaskDistribution,
    MaterialTransaction, MaterialStock, MaterialPurchaseRequest,
)
from api.enums import (
    TaskStatus, PositionStatus, ResourceType, BatchStatus,
    TransactionType, PurchaseStatus,
)

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
    elif command == "/defect":
        await _cmd_defect(db, message, args)
    elif command == "/actual":
        await _cmd_actual(db, message, args)
    elif command == "/split":
        await _cmd_split(db, message, args)
    elif command == "/glaze":
        await _cmd_glaze(db, message, args)
    elif command == "/recipe":
        await _cmd_recipe(db, message, args)
    elif command == "/plan":
        await _cmd_plan(db, message)
    elif command == "/photo":
        await _cmd_photo(db, message)
    else:
        await _send_message(
            chat_id,
            "Perintah tidak dikenal. Ketik /help untuk daftar perintah.",
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

    # Try to extract position reference from caption (e.g. #123, POS-123)
    position_id = None
    linked_position = None
    if caption and user:
        pos_ref = _extract_position_ref(caption)
        if pos_ref:
            linked_position = _find_position_by_number_or_id(db, pos_ref, user)
            if linked_position:
                position_id = linked_position.id

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
    # Link to position if found (set position_id if the column exists)
    if position_id:
        try:
            photo.position_id = position_id
        except Exception:
            pass  # Column may not exist on model yet

    db.add(photo)
    db.commit()
    db.refresh(photo)

    logger.info(
        f"Photo saved: id={photo.id}, factory={factory.name}, "
        f"type={photo_type}, file_id={file_id[:20]}..."
        + (f", position={position_id}" if position_id else "")
    )

    # Upload to Supabase Storage (async, non-blocking for the user)
    try:
        image_bytes = await download_telegram_photo(file_id)
        if image_bytes:
            from business.services.photo_storage import upload_photo as storage_upload

            related_id = str(position_id) if position_id else str(photo.id)
            storage_result = await storage_upload(
                image_bytes=image_bytes,
                category="telegram",
                factory_id=factory.id,
                related_id=related_id,
                filename=f"{file_id[:20]}.jpg",
            )
            # Update photo record with Supabase URL
            if storage_result.get("url"):
                photo.photo_url = storage_result["url"]
                db.commit()
                logger.info(
                    f"Telegram photo uploaded to {storage_result['storage']}: "
                    f"{storage_result['path']}"
                )
    except Exception as e:
        logger.warning(f"Supabase upload for telegram photo failed (non-fatal): {e}")

    # Acknowledge receipt
    type_label = photo_type.replace("_", " ").title() if photo_type else "Photo"
    ack_msg = f"Foto diterima ({type_label})."
    if linked_position:
        pos_label = _format_position_label(linked_position)
        ack_msg += f" Terhubung ke posisi {pos_label}."
    await _send_message(chat_id, ack_msg)

    # ── Delivery Photo — special handler ─────────────────────────
    if photo_type == "delivery":
        try:
            image_bytes_for_delivery = await download_telegram_photo(file_id)
            if image_bytes_for_delivery:
                await _handle_delivery_photo(
                    db, chat_id, factory, user,
                    image_bytes_for_delivery, photo, caption,
                )
        except Exception as e:
            logger.error(f"Delivery photo handler failed: {e}", exc_info=True)
            await _send_message(chat_id, "Gagal memproses foto pengiriman. Foto tetap tersimpan.")
        return

    # ── LLM Photo Analysis ───────────────────────────────────────
    # Determine if this photo type warrants LLM analysis
    analysis_type_map = {
        "scale": "scale",
        "defect": "quality",
        "quality": "quality",
        "packing": "packing",
    }
    llm_analysis_type = analysis_type_map.get(photo_type)

    if llm_analysis_type:
        try:
            from business.services.photo_analysis import analyze_photo, format_analysis_message

            # Download the photo bytes from Telegram
            image_bytes = await download_telegram_photo(file_id)
            if image_bytes:
                # Build context for the analysis
                analysis_context = {}
                if linked_position:
                    analysis_context["position"] = _format_position_label(linked_position)
                    if hasattr(linked_position, "color") and linked_position.color:
                        analysis_context["expected_color"] = linked_position.color

                analysis_result = await analyze_photo(
                    image_bytes=image_bytes,
                    analysis_type=llm_analysis_type,
                    context=analysis_context if analysis_context else None,
                )

                if analysis_result:
                    pos_ref = _format_position_label(linked_position) if linked_position else None
                    analysis_msg = format_analysis_message(analysis_result, pos_ref)
                    await _send_message(chat_id, analysis_msg, parse_mode="")
                    logger.info(f"Photo analysis sent for photo {photo.id}")
                else:
                    logger.debug(f"Photo analysis returned None for photo {photo.id}")
            else:
                logger.warning(f"Could not download photo {file_id[:20]}... for analysis")
        except Exception as e:
            logger.error(f"LLM photo analysis failed: {e}", exc_info=True)
            # Analysis failure should not affect the main photo-saving flow


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
        "/defect <pos\\_id> <persen> — Lapor defect\n"
        "/actual <pos\\_id> <jumlah> — Catat output aktual\n"
        "/split <pos\\_id> <qty1> <qty2> ... — Bagi posisi\n"
        "/glaze <pos\\_id> — Info glasir posisi\n"
        "/recipe <koleksi> <warna> [ukuran] — Cari resep\n"
        "/plan — Rencana produksi besok\n"
        "/photo — Kirim foto untuk dokumentasi\n"
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
# New command handlers (§37)
# ────────────────────────────────────────────────────────────────

async def _cmd_defect(db: Session, message: dict, args: str) -> None:
    """
    /defect <position_id> <defect_percent> — Report defect for a position.
    Example: /defect 12345 8   (8% defect for position #12345)
    """
    chat_id = message["chat"]["id"]
    from_user = message.get("from", {})
    telegram_user_id = from_user.get("id")

    user = _find_user_by_telegram(db, telegram_user_id)
    if not user:
        await _send_message(chat_id, "Akun belum terhubung. Ketik /start untuk menghubungkan.")
        return

    parts = args.split()
    if len(parts) < 2:
        await _send_message(chat_id, "Format: /defect <pos\\_id> <persen>\nContoh: /defect 12345 8")
        return

    pos_id_str = parts[0]
    try:
        defect_pct = float(parts[1])
    except ValueError:
        await _send_message(chat_id, "Persen defect harus berupa angka. Contoh: /defect 12345 8")
        return

    position = _find_position_by_number_or_id(db, pos_id_str, user)
    if not position:
        await _send_message(chat_id, f"Posisi '{pos_id_str}' tidak ditemukan.")
        return

    # Convert percentage to fraction for the service
    defect_fraction = defect_pct / 100.0

    try:
        from business.services.defect_coefficient import record_actual_defect_and_check_threshold
        result = record_actual_defect_and_check_threshold(
            db, position, defect_fraction,
        )
        db.commit()

        pos_label = _format_position_label(position)
        target_pct = result.get('target_pct', 0)
        actual_pct = result.get('actual_pct', 0)

        msg = f"Defect dicatat: {actual_pct}% untuk posisi {pos_label}. Target: {target_pct}%."
        if result.get('exceeded'):
            msg += "\n\u26a0\ufe0f Batas terlampaui — tugas 5-Why dibuat."
        await _send_message(chat_id, msg)

    except Exception as e:
        logger.error(f"Error in /defect: {e}", exc_info=True)
        db.rollback()
        await _send_message(chat_id, f"Gagal mencatat defect: {e}")


async def _cmd_actual(db: Session, message: dict, args: str) -> None:
    """
    /actual <position_id> <quantity> — Record actual output quantity.
    Example: /actual 12345 95
    """
    chat_id = message["chat"]["id"]
    from_user = message.get("from", {})
    telegram_user_id = from_user.get("id")

    user = _find_user_by_telegram(db, telegram_user_id)
    if not user:
        await _send_message(chat_id, "Akun belum terhubung. Ketik /start untuk menghubungkan.")
        return

    parts = args.split()
    if len(parts) < 2:
        await _send_message(chat_id, "Format: /actual <pos\\_id> <jumlah>\nContoh: /actual 12345 95")
        return

    pos_id_str = parts[0]
    try:
        actual_qty = int(parts[1])
    except ValueError:
        await _send_message(chat_id, "Jumlah harus berupa angka bulat. Contoh: /actual 12345 95")
        return

    position = _find_position_by_number_or_id(db, pos_id_str, user)
    if not position:
        await _send_message(chat_id, f"Posisi '{pos_id_str}' tidak ditemukan.")
        return

    try:
        planned_qty = position.quantity
        # Update actual output on the position
        # Use raw SQL for actual_output field which may exist on the table
        from sqlalchemy import text
        db.execute(
            text("""
                UPDATE order_positions
                SET actual_output = :actual_qty,
                    updated_at = NOW()
                WHERE id = :id
            """),
            {'actual_qty': actual_qty, 'id': str(position.id)},
        )
        db.commit()

        pos_label = _format_position_label(position)
        msg = f"Output dicatat: {actual_qty} pcs untuk {pos_label} (rencana: {planned_qty})"
        if actual_qty < planned_qty:
            diff = planned_qty - actual_qty
            msg += f"\n\u26a0\ufe0f Kurang {diff} pcs dari rencana."
        await _send_message(chat_id, msg)

    except Exception as e:
        logger.error(f"Error in /actual: {e}", exc_info=True)
        db.rollback()
        await _send_message(chat_id, f"Gagal mencatat output: {e}")


async def _cmd_split(db: Session, message: dict, args: str) -> None:
    """
    /split <position_id> <qty1> <qty2> [qty3...] — Quick production split.
    Example: /split 12345 50 30 20
    """
    chat_id = message["chat"]["id"]
    from_user = message.get("from", {})
    telegram_user_id = from_user.get("id")

    user = _find_user_by_telegram(db, telegram_user_id)
    if not user:
        await _send_message(chat_id, "Akun belum terhubung. Ketik /start untuk menghubungkan.")
        return

    parts = args.split()
    if len(parts) < 3:
        await _send_message(
            chat_id,
            "Format: /split <pos\\_id> <qty1> <qty2> [qty3...]\nContoh: /split 12345 50 30 20",
        )
        return

    pos_id_str = parts[0]
    try:
        quantities = [int(p) for p in parts[1:]]
    except ValueError:
        await _send_message(chat_id, "Semua jumlah harus berupa angka bulat.")
        return

    if len(quantities) < 2:
        await _send_message(chat_id, "Minimal 2 bagian untuk membagi posisi.")
        return

    position = _find_position_by_number_or_id(db, pos_id_str, user)
    if not position:
        await _send_message(chat_id, f"Posisi '{pos_id_str}' tidak ditemukan.")
        return

    try:
        from business.services.production_split import can_split_position, split_position_mid_production

        can_split, reason = can_split_position(position)
        if not can_split:
            await _send_message(chat_id, f"Tidak bisa membagi posisi: {reason}")
            return

        total_qty = sum(quantities)
        if total_qty != position.quantity:
            await _send_message(
                chat_id,
                f"Total bagian ({total_qty}) harus sama dengan jumlah posisi ({position.quantity}).",
            )
            return

        splits = [{'quantity': q} for q in quantities]
        children = split_position_mid_production(
            db, position, splits,
            reason="Split via Telegram",
            created_by_id=user.id,
        )
        db.commit()

        pos_label = _format_position_label(position)
        child_labels = []
        for child in children:
            cl = _format_position_label(child)
            child_labels.append(f"{cl} ({child.quantity})")

        msg = f"Posisi dibagi: {pos_label} -> " + ", ".join(child_labels)
        await _send_message(chat_id, msg)

    except ValueError as e:
        db.rollback()
        await _send_message(chat_id, f"Gagal membagi posisi: {e}")
    except Exception as e:
        logger.error(f"Error in /split: {e}", exc_info=True)
        db.rollback()
        await _send_message(chat_id, f"Gagal membagi posisi: {e}")


async def _cmd_glaze(db: Session, message: dict, args: str) -> None:
    """
    /glaze <position_id> — Show glazing info for a position.
    """
    chat_id = message["chat"]["id"]
    from_user = message.get("from", {})
    telegram_user_id = from_user.get("id")

    user = _find_user_by_telegram(db, telegram_user_id)
    if not user:
        await _send_message(chat_id, "Akun belum terhubung. Ketik /start untuk menghubungkan.")
        return

    pos_id_str = args.strip()
    if not pos_id_str:
        await _send_message(chat_id, "Format: /glaze <pos\\_id>\nContoh: /glaze 12345")
        return

    position = _find_position_by_number_or_id(db, pos_id_str, user)
    if not position:
        await _send_message(chat_id, f"Posisi '{pos_id_str}' tidak ditemukan.")
        return

    pos_label = _format_position_label(position)
    lines = [f"*Info Glasir — {pos_label}*\n"]

    # Recipe info
    if position.recipe_id:
        recipe = db.query(Recipe).filter(Recipe.id == position.recipe_id).first()
        if recipe:
            lines.append(f"Resep: {recipe.name}")
            if recipe.recipe_type:
                lines.append(f"Tipe: {recipe.recipe_type}")

            # Kiln config (temperature, duration)
            kiln_config = db.query(RecipeKilnConfig).filter(
                RecipeKilnConfig.recipe_id == recipe.id
            ).first()
            if kiln_config:
                if kiln_config.firing_temperature:
                    lines.append(f"Suhu: {kiln_config.firing_temperature} C")
                if kiln_config.firing_duration_hours:
                    lines.append(f"Durasi: {kiln_config.firing_duration_hours} jam")
                if kiln_config.two_stage_firing:
                    lines.append("Pembakaran 2 tahap: Ya")

            # BOM / materials
            recipe_materials = (
                db.query(RecipeMaterial)
                .filter(RecipeMaterial.recipe_id == recipe.id)
                .all()
            )
            if recipe_materials:
                lines.append("\nBahan:")
                for rm in recipe_materials:
                    mat = db.query(Material).filter(Material.id == rm.material_id).first()
                    mat_name = mat.name if mat else "?"
                    lines.append(f"  - {mat_name}: {rm.quantity_per_unit} {rm.unit}")
        else:
            lines.append("Resep: tidak ditemukan")
    else:
        lines.append("Resep: belum ditentukan")

    # Position glazing info
    lines.append(f"\nWarna: {position.color or '-'}")
    if position.color_2:
        lines.append(f"Warna 2: {position.color_2}")
    lines.append(f"Ukuran: {position.size or '-'}")
    lines.append(f"Jumlah: {position.quantity} pcs")

    if position.planned_glazing_date:
        lines.append(f"Jadwal glasir: {position.planned_glazing_date}")
    if position.two_stage_firing:
        tst = position.two_stage_type or "-"
        lines.append(f"2-tahap: Ya ({tst})")

    status_val = position.status.value if hasattr(position.status, 'value') else str(position.status)
    lines.append(f"Status: {status_val}")

    await _send_message(chat_id, "\n".join(lines))


async def _cmd_recipe(db: Session, message: dict, args: str) -> None:
    """
    /recipe <collection> <color> [size] — Look up recipe.
    Example: /recipe Classic White 30x60
    """
    chat_id = message["chat"]["id"]
    from_user = message.get("from", {})
    telegram_user_id = from_user.get("id")

    user = _find_user_by_telegram(db, telegram_user_id)
    if not user:
        await _send_message(chat_id, "Akun belum terhubung. Ketik /start untuk menghubungkan.")
        return

    if not args.strip():
        await _send_message(
            chat_id,
            "Format: /recipe <koleksi> <warna> [ukuran]\nContoh: /recipe Classic White 30x60",
        )
        return

    parts = args.strip().split()
    if len(parts) < 2:
        await _send_message(chat_id, "Minimal: /recipe <koleksi> <warna>")
        return

    # Parse: first word is collection, second is color, rest is optional size
    collection = parts[0]
    color = parts[1]
    size_filter = parts[2] if len(parts) > 2 else None

    # Search recipes by name/collection matching
    query = db.query(Recipe).filter(Recipe.is_active.is_(True))

    # Try matching collection in color_collection or name
    from sqlalchemy import or_
    query = query.filter(
        or_(
            Recipe.color_collection.ilike(f"%{collection}%"),
            Recipe.name.ilike(f"%{collection}%"),
        )
    )
    query = query.filter(Recipe.name.ilike(f"%{color}%"))

    recipes = query.limit(5).all()

    if not recipes:
        # Broader search: just match color in name
        recipes = (
            db.query(Recipe)
            .filter(
                Recipe.is_active.is_(True),
                Recipe.name.ilike(f"%{color}%"),
            )
            .limit(5)
            .all()
        )

    if not recipes:
        await _send_message(chat_id, f"Resep tidak ditemukan untuk '{collection} {color}'.")
        return

    for recipe in recipes:
        lines = [f"*Resep: {recipe.name}*"]
        if recipe.color_collection:
            lines.append(f"Koleksi: {recipe.color_collection}")
        if recipe.recipe_type:
            lines.append(f"Tipe: {recipe.recipe_type}")

        # Kiln config
        kiln_config = db.query(RecipeKilnConfig).filter(
            RecipeKilnConfig.recipe_id == recipe.id
        ).first()
        if kiln_config:
            if kiln_config.firing_temperature:
                lines.append(f"Suhu: {kiln_config.firing_temperature} C")
            if kiln_config.firing_duration_hours:
                lines.append(f"Durasi: {kiln_config.firing_duration_hours} jam")

        # BOM
        recipe_materials = (
            db.query(RecipeMaterial)
            .filter(RecipeMaterial.recipe_id == recipe.id)
            .all()
        )
        if recipe_materials:
            lines.append("\nBahan:")
            for rm in recipe_materials:
                mat = db.query(Material).filter(Material.id == rm.material_id).first()
                mat_name = mat.name if mat else "?"
                lines.append(f"  - {mat_name}: {rm.quantity_per_unit} {rm.unit}")

        await _send_message(chat_id, "\n".join(lines))


async def _cmd_plan(db: Session, message: dict) -> None:
    """
    /plan — Show tomorrow's production plan for user's factory.
    """
    chat_id = message["chat"]["id"]
    from_user = message.get("from", {})
    telegram_user_id = from_user.get("id")

    user = _find_user_by_telegram(db, telegram_user_id)
    if not user:
        await _send_message(chat_id, "Akun belum terhubung. Ketik /start untuk menghubungkan.")
        return

    # Get user's factory
    uf = db.query(UserFactory).filter(UserFactory.user_id == user.id).first()
    if not uf:
        await _send_message(chat_id, "Anda belum terdaftar di pabrik manapun.")
        return

    factory = db.query(Factory).filter(Factory.id == uf.factory_id).first()
    if not factory:
        await _send_message(chat_id, "Pabrik tidak ditemukan.")
        return

    tomorrow = date.today() + timedelta(days=1)

    # Check if there's a DailyTaskDistribution for tomorrow
    distribution = db.query(DailyTaskDistribution).filter(
        DailyTaskDistribution.factory_id == factory.id,
        DailyTaskDistribution.distribution_date == tomorrow,
    ).first()

    lines = [f"*Rencana Produksi {tomorrow} — {factory.name}*\n"]

    if distribution:
        # Use pre-computed distribution data
        glazing = distribution.glazing_tasks_json or []
        kiln = distribution.kiln_loading_json or []

        if glazing:
            lines.append(f"*Glasir: {len(glazing)} posisi*")
            for i, t in enumerate(glazing, 1):
                lines.append(
                    f"{i}. #{t.get('order_number', '?')} "
                    f"Pos #{t.get('position_label', t.get('position_number', ''))}"
                    f" | {t.get('color', '')} {t.get('size', '')}"
                    f" | {t.get('quantity', 0)} pcs"
                )

        if kiln:
            lines.append(f"\n*Kiln: {len(kiln)} batch*")
            for b in kiln:
                lines.append(
                    f"- {b.get('kiln_name', '?')}: "
                    f"{b.get('positions_count', 0)} posisi, "
                    f"{b.get('temperature', 0)} C"
                )
    else:
        # Query positions directly from schedule
        glazing_positions = (
            db.query(OrderPosition)
            .filter(
                OrderPosition.factory_id == factory.id,
                OrderPosition.planned_glazing_date == tomorrow,
                OrderPosition.status.notin_([
                    PositionStatus.SHIPPED.value,
                    PositionStatus.CANCELLED.value,
                ]),
            )
            .order_by(OrderPosition.priority_order.desc())
            .limit(30)
            .all()
        )

        firing_positions = (
            db.query(OrderPosition)
            .filter(
                OrderPosition.factory_id == factory.id,
                OrderPosition.planned_kiln_date == tomorrow,
                OrderPosition.status.notin_([
                    PositionStatus.SHIPPED.value,
                    PositionStatus.CANCELLED.value,
                ]),
            )
            .order_by(OrderPosition.priority_order.desc())
            .limit(30)
            .all()
        )

        sorting_positions = (
            db.query(OrderPosition)
            .filter(
                OrderPosition.factory_id == factory.id,
                OrderPosition.planned_sorting_date == tomorrow,
                OrderPosition.status.notin_([
                    PositionStatus.SHIPPED.value,
                    PositionStatus.CANCELLED.value,
                ]),
            )
            .order_by(OrderPosition.priority_order.desc())
            .limit(30)
            .all()
        )

        if glazing_positions:
            lines.append(f"*Glasir: {len(glazing_positions)} posisi*")
            for i, pos in enumerate(glazing_positions, 1):
                pl = _format_position_label(pos)
                order_num = pos.order.order_number if pos.order else "?"
                lines.append(f"{i}. {order_num} {pl} | {pos.color or ''} {pos.size or ''} | {pos.quantity} pcs")

        if firing_positions:
            lines.append(f"\n*Kiln: {len(firing_positions)} posisi*")
            for i, pos in enumerate(firing_positions, 1):
                pl = _format_position_label(pos)
                order_num = pos.order.order_number if pos.order else "?"
                lines.append(f"{i}. {order_num} {pl} | {pos.color or ''} {pos.size or ''} | {pos.quantity} pcs")

        if sorting_positions:
            lines.append(f"\n*Sortir: {len(sorting_positions)} posisi*")
            for i, pos in enumerate(sorting_positions, 1):
                pl = _format_position_label(pos)
                order_num = pos.order.order_number if pos.order else "?"
                lines.append(f"{i}. {order_num} {pl} | {pos.quantity} pcs")

        if not glazing_positions and not firing_positions and not sorting_positions:
            lines.append("Tidak ada rencana produksi untuk besok.")

    await _send_message(chat_id, "\n".join(lines))


async def _cmd_photo(db: Session, message: dict) -> None:
    """
    /photo — Instructions for photo upload.
    Actual photo processing happens in handle_photo().
    """
    chat_id = message["chat"]["id"]
    await _send_message(
        chat_id,
        "*Kirim Foto Produksi*\n\n"
        "Kirim foto langsung di chat ini (tanpa perintah /photo).\n\n"
        "Tambahkan caption untuk menandai:\n"
        "- Nomor posisi (contoh: #123)\n"
        "- Tipe: glasir, bakar, defect, kemas\n\n"
        "Contoh: kirim foto dengan caption `#123 glasir`",
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


def _find_position_by_number_or_id(
    db: Session, identifier: str, user: "User"
) -> Optional["OrderPosition"]:
    """Find a position by position_number, UUID prefix, or POS-<number> format.

    Searches within the user's factory scope.
    """
    # Get user's factory IDs
    user_factories = (
        db.query(UserFactory.factory_id)
        .filter(UserFactory.user_id == user.id)
        .all()
    )
    factory_ids = [uf.factory_id for uf in user_factories]
    if not factory_ids:
        return None

    # Strip POS- prefix if present
    clean_id = identifier.strip()
    if clean_id.upper().startswith("POS-"):
        clean_id = clean_id[4:]
    if clean_id.startswith("#"):
        clean_id = clean_id[1:]

    # Try as position_number (integer)
    try:
        pos_num = int(clean_id)
        position = (
            db.query(OrderPosition)
            .filter(
                OrderPosition.position_number == pos_num,
                OrderPosition.factory_id.in_(factory_ids),
            )
            .order_by(OrderPosition.created_at.desc())
            .first()
        )
        if position:
            return position
    except ValueError:
        pass

    # Try as UUID prefix
    try:
        import sqlalchemy as sa
        from sqlalchemy import cast
        position = (
            db.query(OrderPosition)
            .filter(
                cast(OrderPosition.id, sa.String).like(f"{clean_id}%"),
                OrderPosition.factory_id.in_(factory_ids),
            )
            .first()
        )
        if position:
            return position
    except Exception:
        pass

    return None


def _format_position_label(position: "OrderPosition") -> str:
    """Format position label like #3 or #3.1."""
    if position.position_number:
        label = f"#{position.position_number}"
        if position.split_index:
            label += f".{position.split_index}"
        return label
    return f"#{str(position.id)[:8]}"


def _extract_position_ref(caption: str) -> Optional[str]:
    """Extract a position reference from caption text.

    Recognizes patterns like: #123, POS-123, pos123
    Returns the numeric/string part or None.
    """
    import re
    # Match #<number>, POS-<number>, or pos<number>
    match = re.search(r'(?:POS[- ]?|#)(\d+)', caption, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def _fuzzy_match_material(db: Session, name: str) -> Optional[Material]:
    """
    Fuzzy-match a material name from a delivery note against the DB.

    Strategy:
      1. Exact match (case-insensitive)
      2. Contains match (material name contains the query or vice versa)
      3. Word-overlap match (at least 50% of words match)

    Returns the best-matching Material or None.
    """
    if not name or not name.strip():
        return None

    name_lower = name.strip().lower()

    # 1) Exact match (case-insensitive)
    all_materials = db.query(Material).all()
    for m in all_materials:
        if m.name.lower() == name_lower:
            return m

    # 2) Contains match
    for m in all_materials:
        m_lower = m.name.lower()
        if name_lower in m_lower or m_lower in name_lower:
            return m

    # 3) Word-overlap: at least 50% of query words found in material name
    query_words = set(name_lower.split())
    best_match = None
    best_overlap = 0.0
    for m in all_materials:
        m_words = set(m.name.lower().split())
        if not query_words:
            continue
        overlap = len(query_words & m_words) / len(query_words)
        if overlap > best_overlap and overlap >= 0.5:
            best_overlap = overlap
            best_match = m

    return best_match


async def _handle_delivery_photo(
    db: Session,
    chat_id: int,
    factory: Factory,
    user: Optional[User],
    image_bytes: bytes,
    photo: PositionPhoto,
    caption: str,
) -> None:
    """
    Process a delivery note photo:
    1. Analyze with Claude Vision to extract items
    2. Fuzzy-match each item to materials in DB
    3. Create MaterialTransaction records and update stock
    4. Try to link with open purchase requests
    5. Send formatted confirmation
    """
    from business.services.photo_analysis import analyze_photo, format_delivery_message
    from decimal import Decimal

    # ── Step 1: Analyze the delivery note photo ───────────────────
    analysis_result = await analyze_photo(
        image_bytes=image_bytes,
        analysis_type="delivery",
    )

    if not analysis_result or not analysis_result.get("readings"):
        await _send_message(
            chat_id,
            "Foto pengiriman diterima, tetapi tidak bisa membaca isi dokumen. "
            "Silakan input penerimaan secara manual.",
            parse_mode="",
        )
        return

    readings = analysis_result.get("readings", {})
    items = readings.get("items", [])

    if not items:
        await _send_message(
            chat_id,
            "Foto pengiriman diterima, tetapi tidak ditemukan daftar material. "
            "Silakan input penerimaan secara manual.",
            parse_mode="",
        )
        return

    # ── Step 2-3: Match items and create transactions ─────────────
    matched_items = []
    unmatched_items = []

    for item in items:
        material_name = item.get("material_name", "")
        try:
            quantity = Decimal(str(item.get("quantity", 0)))
        except Exception:
            quantity = Decimal("0")
        unit = item.get("unit", "")

        if quantity <= 0:
            continue

        matched_material = _fuzzy_match_material(db, material_name)

        if matched_material:
            try:
                # Create receive transaction
                txn = MaterialTransaction(
                    material_id=matched_material.id,
                    factory_id=factory.id,
                    type=TransactionType.RECEIVE,
                    quantity=quantity,
                    notes=f"Telegram delivery photo. Ref: {readings.get('reference_number', '-')}. "
                          f"Supplier: {readings.get('supplier', '-')}",
                    created_by=user.id if user else None,
                )
                db.add(txn)

                # Update or create stock record
                stock = (
                    db.query(MaterialStock)
                    .filter(
                        MaterialStock.material_id == matched_material.id,
                        MaterialStock.factory_id == factory.id,
                    )
                    .first()
                )
                if stock:
                    stock.balance = (stock.balance or Decimal("0")) + quantity
                    new_balance = stock.balance
                else:
                    stock = MaterialStock(
                        material_id=matched_material.id,
                        factory_id=factory.id,
                        balance=quantity,
                    )
                    db.add(stock)
                    new_balance = quantity

                db.flush()  # ensure IDs are assigned

                matched_items.append({
                    "material_name": matched_material.name,
                    "quantity": str(quantity),
                    "unit": unit or matched_material.unit or "pcs",
                    "new_balance": str(new_balance),
                    "material_db_name": matched_material.name,
                })

                # ── Step 4: Try to link with purchase requests ────
                _try_link_purchase_request(db, matched_material, factory, quantity)

            except Exception as e:
                logger.error(
                    f"Failed to create transaction for {material_name}: {e}",
                    exc_info=True,
                )
                unmatched_items.append({
                    "material_name": material_name,
                    "quantity": str(quantity),
                    "unit": unit,
                })
        else:
            unmatched_items.append({
                "material_name": material_name,
                "quantity": str(quantity),
                "unit": unit,
            })

    # Commit all transactions at once
    try:
        db.commit()
    except Exception as e:
        logger.error(f"Failed to commit delivery transactions: {e}", exc_info=True)
        db.rollback()
        await _send_message(
            chat_id,
            "Gagal menyimpan transaksi penerimaan ke database. "
            "Silakan coba lagi atau input secara manual.",
            parse_mode="",
        )
        return

    # ── Step 5: Send formatted confirmation ───────────────────────
    msg = format_delivery_message(analysis_result, matched_items, unmatched_items)
    await _send_message(chat_id, msg, parse_mode="")

    logger.info(
        f"Delivery photo processed: {len(matched_items)} matched, "
        f"{len(unmatched_items)} unmatched, factory={factory.name}"
    )


def _try_link_purchase_request(
    db: Session,
    material: Material,
    factory: Factory,
    received_qty,
) -> None:
    """
    Try to find an open MaterialPurchaseRequest for this material and update it.
    Looks for requests with status in (PENDING, APPROVED, SENT, IN_TRANSIT)
    that contain this material in their materials_json.
    """
    from decimal import Decimal

    open_statuses = [
        PurchaseStatus.PENDING,
        PurchaseStatus.APPROVED,
        PurchaseStatus.SENT,
        PurchaseStatus.IN_TRANSIT,
    ]
    try:
        requests = (
            db.query(MaterialPurchaseRequest)
            .filter(
                MaterialPurchaseRequest.factory_id == factory.id,
                MaterialPurchaseRequest.status.in_(open_statuses),
            )
            .order_by(MaterialPurchaseRequest.created_at.desc())
            .all()
        )

        material_id_str = str(material.id)
        for pr in requests:
            materials_json = pr.materials_json or []
            for mat_entry in materials_json:
                entry_mat_id = str(mat_entry.get("material_id", ""))
                if entry_mat_id == material_id_str:
                    # Found a matching purchase request — update status
                    pr.actual_delivery_date = date.today()
                    # Update received quantities
                    received_json = pr.received_quantity_json or []
                    received_json.append({
                        "material_id": material_id_str,
                        "quantity": float(received_qty),
                        "source": "telegram_delivery_photo",
                    })
                    pr.received_quantity_json = received_json

                    # Check if all items are received to update status
                    total_items = len(materials_json)
                    total_received = len(set(
                        r.get("material_id") for r in received_json
                    ))
                    if total_received >= total_items:
                        pr.status = PurchaseStatus.RECEIVED
                    elif total_received > 0:
                        pr.status = PurchaseStatus.PARTIALLY_RECEIVED

                    logger.info(
                        f"Linked delivery to purchase request {pr.id}, "
                        f"status → {pr.status.value}"
                    )
                    return  # Link to the first matching request only

    except Exception as e:
        logger.warning(f"Failed to link purchase request: {e}", exc_info=True)


def _detect_photo_type(caption: str) -> str:
    """Detect photo type from caption keywords."""
    if not caption:
        return "other"
    caption_lower = caption.lower()

    # Delivery / material receiving — check BEFORE generic "material" matches
    if any(kw in caption_lower for kw in (
        "delivery", "arriving", "arrived", "raw material", "receiving", "receipt",
        "barang", "tiba", "kirim", "kiriman", "surat jalan", "terima", "penerimaan",
        "приход", "поставка", "накладная", "доставка",
    )):
        return "delivery"
    if any(kw in caption_lower for kw in ("scale", "timbang", "berat", "weight")):
        return "scale"
    if any(kw in caption_lower for kw in ("glaz", "glasir", "engobe")):
        return "glazing"
    if any(kw in caption_lower for kw in ("fir", "bakar", "kiln", "oven")):
        return "firing"
    if any(kw in caption_lower for kw in ("defect", "cacat", "reject", "pecah", "retak")):
        return "defect"
    if any(kw in caption_lower for kw in ("pack", "kemas", "box")):
        return "packing"
    if any(kw in caption_lower for kw in ("quality", "qc", "kualitas")):
        return "quality"
    # "материал" alone (Russian) — treat as delivery context
    if "материал" in caption_lower or "material" in caption_lower:
        return "delivery"
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
