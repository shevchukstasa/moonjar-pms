"""
Telegram inline-button callback handler service.
Business Logic: §34 (Daily Distribution), §27 (Notifications)

Processes callback_query updates from Telegram inline keyboard buttons.
Called from the webhook handler in api/routers/telegram.py.

Callback data format (compact, <= 64 bytes):
  d:a:{fid8}:{date}   — daily: acknowledge tasks
  d:p:{fid8}:{date}   — daily: report problem
  d:d:{fid8}:{date}   — daily: show task detail
  a:v:{pid8}           — alert: view position detail
  a:r:{kid8}           — alert: reschedule kiln
  t:s:{pid8}           — task: start
  t:d:{pid8}           — task: done
  t:i:{pid8}           — task: report issue
"""
from uuid import UUID
from typing import Optional
import logging

import sqlalchemy as sa
from sqlalchemy.orm import Session
from sqlalchemy import cast

from api.models import (
    User,
    Factory,
    OrderPosition,
    ProductionOrder,
    Resource,
    DailyTaskDistribution,
)
from api.enums import ResourceType

logger = logging.getLogger("moonjar.telegram_callbacks")


# ────────────────────────────────────────────────────────────────
# Main dispatcher
# ────────────────────────────────────────────────────────────────

def handle_callback(db: Session, callback_query: dict) -> str:
    """Process a callback_query from a Telegram inline button press.

    Args:
        db: SQLAlchemy session.
        callback_query: The full callback_query object from the Telegram update.

    Returns:
        Short text response for answerCallbackQuery.
    """
    data = callback_query.get("data", "")
    parts = data.split(":")
    action = parts[0] if parts else ""

    try:
        if action == "d":
            return _handle_daily_callback(db, callback_query, parts)
        elif action == "a":
            return _handle_alert_callback(db, callback_query, parts)
        elif action == "t":
            return _handle_task_callback(db, callback_query, parts)
        else:
            logger.warning("Unknown callback action: %s", data)
            return "Aksi tidak dikenal"
    except Exception as e:
        logger.error("Callback handler error for data=%s: %s", data, e, exc_info=True)
        return "Terjadi kesalahan"


# ────────────────────────────────────────────────────────────────
# Daily distribution callbacks (d:*)
# ────────────────────────────────────────────────────────────────

def _handle_daily_callback(db: Session, cq: dict, parts: list[str]) -> str:
    """Handle daily distribution button callbacks.

    d:a:{fid8}:{date} — Master acknowledges daily tasks
    d:p:{fid8}:{date} — Master reports problem (notify PM)
    d:d:{fid8}:{date} — Show detailed task summary
    """
    if len(parts) < 4:
        return "Data tidak valid"

    sub_action = parts[1]  # a / p / d
    fid_short = parts[2]
    date_str = parts[3]

    from_user = cq.get("from", {})
    telegram_user_id = from_user.get("id")
    user_display = from_user.get("first_name", "User")

    # Resolve factory by short UUID prefix
    factory = _find_factory_by_prefix(db, fid_short)
    if not factory:
        return "Pabrik tidak ditemukan"

    if sub_action == "a":
        # Acknowledge — log and reply
        logger.info(
            "DAILY_ACK | factory=%s date=%s user=%s (tg_id=%s)",
            factory.name, date_str, user_display, telegram_user_id,
        )
        return f"\u2705 Tugas diterima oleh {user_display}! Semangat kerja!"

    elif sub_action == "p":
        # Report problem — notify PM
        logger.info(
            "DAILY_PROBLEM | factory=%s date=%s user=%s (tg_id=%s)",
            factory.name, date_str, user_display, telegram_user_id,
        )
        # Send notification to PM about problem report
        _notify_pm_problem_report(db, factory, date_str, user_display, telegram_user_id)
        return "\U0001f4dd Silakan kirim pesan dengan detail masalah di chat ini."

    elif sub_action == "d":
        # Detail — send summary privately via chat
        distribution = _get_distribution_record(db, factory.id, date_str)
        if not distribution:
            return "Data distribusi tidak ditemukan"

        # Build compact detail summary
        detail_text = _build_detail_summary(distribution, date_str)

        # Send detail as a reply in the same chat
        chat_id = cq.get("message", {}).get("chat", {}).get("id")
        if chat_id:
            from business.services.notifications import send_telegram_message
            send_telegram_message(str(chat_id), detail_text)

        return "\U0001f4cb Detail tugas dikirim"

    return "Aksi tidak dikenal"


# ────────────────────────────────────────────────────────────────
# Alert callbacks (a:*)
# ────────────────────────────────────────────────────────────────

def _handle_alert_callback(db: Session, cq: dict, parts: list[str]) -> str:
    """Handle alert button callbacks.

    a:v:{pid8} — View position details
    a:r:{kid8} — Trigger kiln reschedule notification to PM
    """
    if len(parts) < 3:
        return "Data tidak valid"

    sub_action = parts[1]  # v / r
    entity_short = parts[2]

    from_user = cq.get("from", {})
    user_display = from_user.get("first_name", "User")

    if sub_action == "v":
        # View position details
        position = _find_position_by_prefix(db, entity_short)
        if not position:
            return "Posisi tidak ditemukan"

        order = position.order
        order_num = order.order_number if order else "?"
        pos_label = f"#{position.position_number}" + (
            f".{position.split_index}" if position.split_index else ""
        )
        status_val = position.status.value if hasattr(position.status, "value") else str(position.status)

        detail = (
            f"\U0001f50d *Detail Posisi*\n"
            f"Pesanan: {order_num}\n"
            f"Posisi: {pos_label}\n"
            f"Warna: {position.color or '-'}\n"
            f"Ukuran: {position.size or '-'}\n"
            f"Jumlah: {position.quantity} pcs\n"
            f"Status: {status_val}"
        )

        # Send detail to the chat
        chat_id = cq.get("message", {}).get("chat", {}).get("id")
        if chat_id:
            from business.services.notifications import send_telegram_message
            send_telegram_message(str(chat_id), detail)

        return f"Detail posisi {pos_label} dikirim"

    elif sub_action == "r":
        # Reschedule kiln — notify PM
        kiln = _find_kiln_by_prefix(db, entity_short)
        if not kiln:
            return "Kiln tidak ditemukan"

        factory_id = kiln.factory_id
        if factory_id:
            from business.services.notifications import notify_pm
            notify_pm(
                db, factory_id,
                "kiln_reschedule_request",
                f"\U0001f4c5 Permintaan jadwal ulang: {kiln.name}",
                f"{user_display} meminta penjadwalan ulang kiln {kiln.name} via Telegram.",
                related_entity_type="resource",
                related_entity_id=kiln.id,
            )
            logger.info(
                "KILN_RESCHEDULE_REQUEST | kiln=%s user=%s",
                kiln.name, user_display,
            )

        return f"\U0001f4c5 Permintaan jadwal ulang kiln {kiln.name} dikirim ke PM"

    return "Aksi tidak dikenal"


# ────────────────────────────────────────────────────────────────
# Task callbacks (t:*)
# ────────────────────────────────────────────────────────────────

def _handle_task_callback(db: Session, cq: dict, parts: list[str]) -> str:
    """Handle per-task action callbacks.

    t:s:{pid8} — Master confirms task started
    t:d:{pid8} — Master confirms task done
    t:i:{pid8} — Report issue with task
    """
    if len(parts) < 3:
        return "Data tidak valid"

    sub_action = parts[1]  # s / d / i
    pid_short = parts[2]

    from_user = cq.get("from", {})
    telegram_user_id = from_user.get("id")
    user_display = from_user.get("first_name", "User")

    # Resolve user by telegram_user_id
    db_user = None
    if telegram_user_id:
        db_user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()

    # Resolve position
    position = _find_position_by_prefix(db, pid_short)
    if not position:
        return "Posisi tidak ditemukan"

    order = position.order
    order_num = order.order_number if order else "?"
    pos_label = f"#{position.position_number}" + (
        f".{position.split_index}" if position.split_index else ""
    )

    if sub_action == "s":
        # Task started
        logger.info(
            "TASK_START | order=%s pos=%s user=%s (tg_id=%s)",
            order_num, pos_label, user_display, telegram_user_id,
        )
        return f"\u2705 Tugas dimulai: {order_num} Pos {pos_label}"

    elif sub_action == "d":
        # Task done
        logger.info(
            "TASK_DONE | order=%s pos=%s user=%s (tg_id=%s)",
            order_num, pos_label, user_display, telegram_user_id,
        )
        return f"\u2705 Tugas selesai: {order_num} Pos {pos_label}"

    elif sub_action == "i":
        # Report issue
        logger.info(
            "TASK_ISSUE | order=%s pos=%s user=%s (tg_id=%s)",
            order_num, pos_label, user_display, telegram_user_id,
        )
        # Notify PM about the issue
        factory_id = position.factory_id
        if factory_id:
            from business.services.notifications import notify_pm
            notify_pm(
                db, factory_id,
                "task_issue",
                f"\u26a0\ufe0f Masalah tugas: {order_num} {pos_label}",
                f"{user_display} melaporkan masalah pada posisi {pos_label} ({order_num}).",
                related_entity_type="order_position",
                related_entity_id=position.id,
            )
        return f"\u26a0\ufe0f Masalah dilaporkan: {order_num} Pos {pos_label}"

    return "Aksi tidak dikenal"


# ────────────────────────────────────────────────────────────────
# Private helpers
# ────────────────────────────────────────────────────────────────

def _find_by_uuid_prefix(db: Session, model, prefix: str, extra_filters=None):
    """Find an entity whose UUID starts with the given 8-char hex prefix.

    Uses PostgreSQL text cast for efficient prefix matching.
    Falls back to in-memory scan for small tables if SQL cast fails.
    """
    from sqlalchemy import text as sa_text

    try:
        query = db.query(model).filter(
            cast(model.id, sa.String).like(f"{prefix}%")
        )
        if extra_filters is not None:
            for f in extra_filters:
                query = query.filter(f)
        result = query.limit(1).first()
        if result:
            return result
    except Exception:
        pass

    # Fallback: in-memory scan (only viable for small tables like Factory)
    try:
        query = db.query(model)
        if extra_filters is not None:
            for f in extra_filters:
                query = query.filter(f)
        for entity in query.limit(500).all():
            if str(entity.id).startswith(prefix):
                return entity
    except Exception as e:
        logger.warning("UUID prefix lookup failed for %s: %s", model.__tablename__, e)
    return None


def _find_factory_by_prefix(db: Session, prefix: str) -> Optional["Factory"]:
    """Find a factory whose UUID starts with the given 8-char prefix."""
    return _find_by_uuid_prefix(db, Factory, prefix)


def _find_position_by_prefix(db: Session, prefix: str) -> Optional["OrderPosition"]:
    """Find a position whose UUID starts with the given 8-char prefix."""
    return _find_by_uuid_prefix(db, OrderPosition, prefix)


def _find_kiln_by_prefix(db: Session, prefix: str) -> Optional["Resource"]:
    """Find a kiln resource whose UUID starts with the given 8-char prefix."""
    return _find_by_uuid_prefix(
        db, Resource, prefix,
        extra_filters=[Resource.resource_type == ResourceType.KILN],
    )


def _get_distribution_record(
    db: Session, factory_id: UUID, date_str: str
) -> Optional["DailyTaskDistribution"]:
    """Retrieve the daily distribution record for a factory and date."""
    from datetime import date as date_type

    try:
        dist_date = date_type.fromisoformat(date_str)
    except (ValueError, TypeError):
        return None

    return db.query(DailyTaskDistribution).filter(
        DailyTaskDistribution.factory_id == factory_id,
        DailyTaskDistribution.distribution_date == dist_date,
    ).first()


def _build_detail_summary(distribution: "DailyTaskDistribution", date_str: str) -> str:
    """Build a compact detail summary from a DailyTaskDistribution record."""
    lines = [f"\U0001f4cb *Detail Tugas {date_str}*\n"]

    glazing = distribution.glazing_tasks_json or []
    if glazing:
        lines.append(f"\U0001f3a8 *Glasir: {len(glazing)} posisi*")
        for i, t in enumerate(glazing, 1):
            behind = " \u26a0\ufe0f" if t.get("behind_schedule") else ""
            lines.append(
                f"{i}. #{t.get('order_number','?')} "
                f"Pos #{t.get('position_label', t.get('position_number',''))}{behind} "
                f"| {t.get('color','')} {t.get('size','')} "
                f"| {t.get('quantity',0)} pcs"
            )

    kiln = distribution.kiln_loading_json or []
    if kiln:
        lines.append(f"\n\U0001f525 *Kiln: {len(kiln)} batch*")
        for b in kiln:
            lines.append(
                f"\u2022 {b.get('kiln_name','?')}: "
                f"{b.get('positions_count',0)} posisi, "
                f"{b.get('temperature',0)}\u00b0C"
            )

    extra = distribution.glaze_recipes_json or {}
    kiln_prep = extra.get("kiln_prep_tasks", [])
    if kiln_prep:
        lines.append(f"\n\U0001f3ed *Persiapan: {len(kiln_prep)} posisi*")
        for i, t in enumerate(kiln_prep, 1):
            behind = " \u26a0\ufe0f" if t.get("behind_schedule") else ""
            lines.append(
                f"{i}. #{t.get('order_number','?')} "
                f"Pos #{t.get('position_label', t.get('position_number',''))}{behind} "
                f"| {t.get('quantity',0)} pcs"
            )

    urgent = extra.get("urgent_alerts", [])
    if urgent:
        lines.append(f"\n\u26a0\ufe0f *Mendesak: {len(urgent)}*")
        for a in urgent:
            lines.append(f"\u2022 {a.get('order','?')} \u2014 {a.get('message','')}")

    if not glazing and not kiln and not kiln_prep:
        lines.append("Tidak ada tugas untuk tanggal ini.")

    return "\n".join(lines)


def _notify_pm_problem_report(
    db: Session,
    factory: "Factory",
    date_str: str,
    user_display: str,
    telegram_user_id: Optional[int],
) -> None:
    """Notify PM that a master reported a problem via daily distribution button."""
    try:
        from business.services.notifications import notify_pm
        notify_pm(
            db, factory.id,
            "daily_problem_report",
            f"\u26a0\ufe0f Laporan masalah: {factory.name} ({date_str})",
            f"{user_display} (TG ID: {telegram_user_id}) melaporkan masalah "
            f"pada distribusi tugas {date_str}.",
        )
    except Exception as e:
        logger.warning("Failed to notify PM about problem report: %s", e)
