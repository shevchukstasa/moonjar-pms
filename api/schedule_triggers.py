"""
Schedule auto-recalculation triggers.

Listens to OrderPosition.status changes via SQLAlchemy events.
When ANY position status changes, marks the factory for reschedule.
After commit, triggers reschedule_factory ONCE per factory
(debounced — not once per position).

Why event-driven: schedule is stale the moment statuses shift.
Cron every hour catches drift; this catches the rest in real-time.
"""

import logging
import threading
from uuid import UUID
from typing import Set

from sqlalchemy import event
from sqlalchemy.orm import Session

logger = logging.getLogger("moonjar.schedule_triggers")

# Tables/columns we care about
_POSITIONS_TABLE = "order_positions"

# Debounce: within a single commit, collect factory_ids, reschedule each once.
_SESSION_FACTORIES_ATTR = "_pending_reschedule_factories"


def _collect_status_changes(session: Session, flush_context):
    """Before commit: scan dirty positions, if status changed, queue factory."""
    try:
        pending: Set[UUID] = getattr(session, _SESSION_FACTORIES_ATTR, set())

        for obj in session.dirty:
            if getattr(obj, "__tablename__", None) != _POSITIONS_TABLE:
                continue
            if not session.is_modified(obj, include_collections=False):
                continue

            # Check if status actually changed
            from sqlalchemy import inspect as sa_inspect
            insp = sa_inspect(obj)
            status_hist = insp.attrs.status.history
            if not status_hist.has_changes():
                continue

            factory_id = getattr(obj, "factory_id", None)
            if factory_id:
                pending.add(factory_id)
                logger.debug(
                    "STATUS_CHANGED | position=%s factory=%s old=%s new=%s",
                    getattr(obj, "id", "?"),
                    factory_id,
                    status_hist.deleted[0] if status_hist.deleted else "?",
                    status_hist.added[0] if status_hist.added else "?",
                )

        if pending:
            setattr(session, _SESSION_FACTORIES_ATTR, pending)
    except Exception as e:
        logger.warning("schedule_triggers after_flush error: %s", e)


def _trigger_reschedule(session: Session):
    """After commit: fire reschedule_factory for each affected factory."""
    pending: Set[UUID] = getattr(session, _SESSION_FACTORIES_ATTR, None)
    if not pending:
        return

    # Clear before firing to avoid re-entry loops
    setattr(session, _SESSION_FACTORIES_ATTR, set())

    # Fire in background so we don't block the current request
    def _run(factory_ids: Set[UUID]):
        from api.database import SessionLocal
        from business.services.production_scheduler import reschedule_factory
        db = SessionLocal()
        try:
            for fid in factory_ids:
                try:
                    reschedule_factory(db, fid)
                    db.commit()
                    logger.info("AUTO_RESCHEDULE | factory=%s", fid)
                except Exception as e:
                    logger.error("AUTO_RESCHEDULE_FAILED | factory=%s | %s", fid, e)
                    db.rollback()
        finally:
            db.close()

    thread = threading.Thread(target=_run, args=(pending,), daemon=True)
    thread.start()


def register_schedule_triggers() -> None:
    """Register event listeners — called once at app startup."""
    event.listen(Session, "after_flush", _collect_status_changes)
    event.listen(Session, "after_commit", _trigger_reschedule)
    logger.info("Schedule triggers registered (position.status → reschedule_factory)")
