"""
Notification Routing service.
Business Logic: §27
"""
from uuid import UUID
from datetime import date, datetime, timedelta
from math import ceil, floor
from typing import Optional

from sqlalchemy.orm import Session

from api.models import *  # noqa
from api.schemas import *  # noqa


def create_notification(db: Session, user_id: UUID, type: str, title: str, message: str, related_entity_type: Optional[str], related_entity_id: Optional[UUID]) -> None:
    """Create notification + send via WebSocket + optional Telegram."""
    # TODO: implement — see BUSINESS_LOGIC.md §27
    raise NotImplementedError

def send_telegram_message(chat_id: str, text: str) -> None:
    """Send message via Telegram Bot API."""
    # TODO: implement — see BUSINESS_LOGIC.md §27
    raise NotImplementedError

def notify_pm(db: Session, factory_id: UUID, type: str, **kwargs) -> None:
    """Shortcut: notify all PMs of a factory."""
    # TODO: implement — see BUSINESS_LOGIC.md §27
    raise NotImplementedError
