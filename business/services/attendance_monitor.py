"""
Attendance Monitor service.
Business Logic: Daily check for unfilled attendance days.

Runs at 7:30 AM Bali time (23:30 UTC) via scheduler.
Detects working days in the current month where NO attendance records exist,
notifies Production Managers (in-app) and CEO/Owner (Telegram) when gaps accumulate.
"""

import logging
from datetime import date, timedelta
from typing import Optional
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from api.models import (
    Attendance,
    Employee,
    Factory,
    FactoryCalendar,
    User,
    UserFactory,
)
from api.enums import UserRole

logger = logging.getLogger("moonjar.attendance_monitor")


def check_attendance_gaps(db: Session, factory_id: UUID) -> dict:
    """Check for unfilled attendance days this month.

    A day is "unfilled" if ZERO attendance records exist for that factory+date.
    Only checks from 1st of the month to yesterday (inclusive).
    Excludes Sundays and factory calendar holidays.

    Returns:
        {
            "unfilled_dates": [date, ...],
            "total_unfilled": int,
            "factory_id": UUID,
            "factory_name": str,
        }
    """
    today = date.today()
    month_start = today.replace(day=1)
    yesterday = today - timedelta(days=1)

    # If we're on the 1st, there's nothing to check
    if yesterday < month_start:
        return {
            "unfilled_dates": [],
            "total_unfilled": 0,
            "factory_id": factory_id,
            "factory_name": "",
        }

    factory = db.query(Factory).filter(Factory.id == factory_id).first()
    factory_name = factory.name if factory else "Unknown"

    # Check if factory has any active employees (skip if none)
    active_count = (
        db.query(sa.func.count(Employee.id))
        .filter(
            Employee.factory_id == factory_id,
            Employee.is_active.is_(True),
        )
        .scalar()
    )
    if not active_count:
        return {
            "unfilled_dates": [],
            "total_unfilled": 0,
            "factory_id": factory_id,
            "factory_name": factory_name,
        }

    # Get factory holidays (non-working days from calendar)
    holidays = set()
    calendar_entries = (
        db.query(FactoryCalendar.date)
        .filter(
            FactoryCalendar.factory_id == factory_id,
            FactoryCalendar.date >= month_start,
            FactoryCalendar.date <= yesterday,
            FactoryCalendar.is_working_day.is_(False),
        )
        .all()
    )
    for (cal_date,) in calendar_entries:
        holidays.add(cal_date)

    # Get dates that have at least one attendance record
    filled_dates = set()
    attendance_dates = (
        db.query(sa.func.distinct(Attendance.date))
        .join(Employee, Attendance.employee_id == Employee.id)
        .filter(
            Employee.factory_id == factory_id,
            Attendance.date >= month_start,
            Attendance.date <= yesterday,
        )
        .all()
    )
    for (att_date,) in attendance_dates:
        filled_dates.add(att_date)

    # Build list of working days and find unfilled ones
    unfilled = []
    current = month_start
    while current <= yesterday:
        # Skip Sundays (weekday() == 6) and calendar holidays
        if current.weekday() != 6 and current not in holidays:
            if current not in filled_dates:
                unfilled.append(current)
        current += timedelta(days=1)

    return {
        "unfilled_dates": unfilled,
        "total_unfilled": len(unfilled),
        "factory_id": factory_id,
        "factory_name": factory_name,
    }


def process_attendance_gaps(db: Session, factory_id: UUID) -> Optional[dict]:
    """Check attendance gaps and send notifications if needed.

    Returns the gap result dict, or None if no gaps found.
    """
    from business.services.notifications import (
        notify_pm,
        send_telegram_message,
    )

    result = check_attendance_gaps(db, factory_id)

    if not result["unfilled_dates"]:
        return None

    dates = result["unfilled_dates"]
    factory_name = result["factory_name"]

    # Format dates for display
    date_list = ", ".join(d.strftime("%b %-d") for d in dates)

    # 1. In-app notification for Production Managers
    title = "Посещаемость не заполнена"
    message = f"{len(dates)} рабочих дней без посещаемости в этом месяце: {date_list}"

    notify_pm(
        db=db,
        factory_id=factory_id,
        type="alert",
        title=title,
        message=message,
    )
    logger.info(
        "Attendance gap notification sent to PMs of factory %s: %d unfilled days",
        factory_name,
        len(dates),
    )

    # 2. Telegram alert to CEO/Owner if 3+ days unfilled
    if len(dates) >= 3:
        _send_ceo_telegram_alert(db, factory_id, factory_name, dates)

    return result


def _send_ceo_telegram_alert(
    db: Session,
    factory_id: UUID,
    factory_name: str,
    unfilled_dates: list[date],
) -> None:
    """Send Telegram alert to CEO and Owner users when 3+ days unfilled."""
    from business.services.notifications import send_telegram_message

    # Build message
    date_lines = "\n".join(
        f"- {d.strftime('%B %-d')} ({d.strftime('%A')})" for d in unfilled_dates
    )
    text = (
        f"⚠️ *Пропуски в посещаемости*\n"
        f"Фабрика: {factory_name}\n"
        f"{len(unfilled_dates)} рабочих дней без отметок посещаемости в этом месяце:\n"
        f"{date_lines}\n\n"
        f"Попросите менеджера производства заполнить посещаемость."
    )

    # Find CEO and Owner users linked to this factory
    ceo_owner_users = (
        db.query(User)
        .join(UserFactory, UserFactory.user_id == User.id)
        .filter(
            UserFactory.factory_id == factory_id,
            User.role.in_([UserRole.CEO, UserRole.OWNER]),
            User.is_active.is_(True),
            User.telegram_user_id.isnot(None),
        )
        .all()
    )

    for user in ceo_owner_users:
        try:
            send_telegram_message(str(user.telegram_user_id), text)
            logger.info(
                "Attendance gap Telegram alert sent to %s (role=%s) for factory %s",
                user.name,
                user.role.value if hasattr(user.role, 'value') else user.role,
                factory_name,
            )
        except Exception as e:
            logger.warning(
                "Failed to send attendance Telegram alert to %s: %s",
                user.name,
                e,
            )
