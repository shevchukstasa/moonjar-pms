"""
Notification Routing service.
Business Logic: §27

Creates in-app notifications and optionally pushes via WebSocket / Telegram.
"""
from uuid import UUID
from typing import Optional
import logging

from sqlalchemy.orm import Session

from api.models import Notification, User, UserFactory, NotificationPreference
from api.enums import NotificationType, RelatedEntityType, UserRole, NotificationChannel

logger = logging.getLogger("moonjar.notifications")


def create_notification(
    db: Session,
    user_id: UUID,
    type: str,
    title: str,
    message: Optional[str] = None,
    related_entity_type: Optional[str] = None,
    related_entity_id: Optional[UUID] = None,
    factory_id: Optional[UUID] = None,
) -> Notification:
    """
    Create an in-app notification for a user.

    Also attempts to push via WebSocket (real-time) and Telegram
    (if user has telegram_chat_id and notification preference allows it).
    """
    notif = Notification(
        user_id=user_id,
        factory_id=factory_id,
        type=type,
        title=title,
        message=message,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        is_read=False,
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)

    # --- Push channels (best-effort, don't fail the notification) ---

    # 1. WebSocket push (non-blocking)
    try:
        _push_websocket(user_id, notif)
    except Exception as e:
        logger.warning(f"WebSocket push failed for user {user_id}: {e}")

    # 2. Telegram push (if enabled)
    try:
        _maybe_push_telegram(db, user_id, type, title, message)
    except Exception as e:
        logger.warning(f"Telegram push failed for user {user_id}: {e}")

    return notif


def notify_pm(
    db: Session,
    factory_id: UUID,
    type: str,
    title: str,
    message: Optional[str] = None,
    related_entity_type: Optional[str] = None,
    related_entity_id: Optional[UUID] = None,
) -> list[Notification]:
    """
    Shortcut: notify all Production Managers of a factory.
    """
    # Users are linked to factories via user_factories join table
    pms = (
        db.query(User)
        .join(UserFactory, UserFactory.user_id == User.id)
        .filter(
            UserFactory.factory_id == factory_id,
            User.role == UserRole.PRODUCTION_MANAGER,
            User.is_active.is_(True),
        )
        .all()
    )

    notifications = []
    for pm in pms:
        notif = create_notification(
            db=db,
            user_id=pm.id,
            type=type,
            title=title,
            message=message,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            factory_id=factory_id,
        )
        notifications.append(notif)

    return notifications


def notify_role(
    db: Session,
    factory_id: UUID,
    role: UserRole,
    type: str,
    title: str,
    message: Optional[str] = None,
    related_entity_type: Optional[str] = None,
    related_entity_id: Optional[UUID] = None,
) -> list[Notification]:
    """Notify all active users of a specific role in a factory."""
    users = (
        db.query(User)
        .join(UserFactory, UserFactory.user_id == User.id)
        .filter(
            UserFactory.factory_id == factory_id,
            User.role == role,
            User.is_active.is_(True),
        )
        .all()
    )

    notifications = []
    for user in users:
        notif = create_notification(
            db=db,
            user_id=user.id,
            type=type,
            title=title,
            message=message,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            factory_id=factory_id,
        )
        notifications.append(notif)

    return notifications


# ────────────────────────────────────────────────────────────────
# Private helpers
# ────────────────────────────────────────────────────────────────

def _push_websocket(user_id: UUID, notif: Notification) -> None:
    """Push notification via WebSocket to connected client."""
    # WebSocket manager is in api/routers/ws.py — import lazily to avoid circular deps.
    # If no active connection, silently skip.
    try:
        from api.routers.ws import manager
        import asyncio

        payload = {
            "type": "notification",
            "data": {
                "id": str(notif.id),
                "type": notif.type,
                "title": notif.title,
                "message": notif.message,
                "is_read": False,
                "created_at": notif.created_at.isoformat() if notif.created_at else None,
            },
        }
        # Best-effort async send from sync context
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(manager.send_to_user(str(user_id), payload))
        except RuntimeError:
            # No running event loop — skip WebSocket push
            pass
    except (ImportError, AttributeError):
        pass


def _maybe_push_telegram(
    db: Session,
    user_id: UUID,
    notif_type: str,
    title: str,
    message: Optional[str],
) -> None:
    """
    Check user's notification preferences; if Telegram is enabled and
    user has a chat_id, send a Telegram message.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.telegram_user_id:
        return

    # Check notification preferences
    pref = (
        db.query(NotificationPreference)
        .filter(NotificationPreference.user_id == user_id)
        .first()
    )

    # Default: in_app only. Only send Telegram if preference says so.
    if pref and pref.channel in (NotificationChannel.TELEGRAM, NotificationChannel.BOTH):
        text = f"📋 *{title}*"
        if message:
            text += f"\n{message}"
        send_telegram_message(str(user.telegram_user_id), text)


def send_telegram_message(chat_id: str, text: str) -> None:
    """
    Send message via Telegram Bot API.
    Uses TELEGRAM_BOT_TOKEN from config (cached via lru_cache).
    """
    import httpx
    from api.config import get_settings

    token = get_settings().TELEGRAM_BOT_TOKEN
    if not token:
        logger.debug("TELEGRAM_BOT_TOKEN not set, skipping Telegram message")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        resp = httpx.post(
            url,
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown",
            },
            timeout=10.0,
        )
        if resp.status_code != 200:
            logger.warning(f"Telegram API returned {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"Telegram send failed: {e}")
