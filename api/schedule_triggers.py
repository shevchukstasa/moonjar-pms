"""
Schedule auto-recalculation triggers.

Listens to two kinds of SQLAlchemy events:

  1. OrderPosition.status changes — mastered "nанёс глазурь" etc.
  2. MaterialTransaction inserts of type=RECEIVE — material arrived on
     the warehouse. Positions in INSUFFICIENT_MATERIALS that were
     waiting on this material may now unblock and shift left.

Both feed the same per-session "pending factories" set, debounced so
the after_commit handler fires reschedule_factory ONCE per factory,
not once per event.

Why event-driven: schedule is stale the moment statuses shift OR the
moment a missing material lands. Cron at 02:00 WITA catches drift;
this catches the rest in real time.

See docs/BUSINESS_LOGIC_FULL.md §4 → "Триггеры пересчёта расписания".
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
_MATERIAL_TXN_TABLE = "material_transactions"

# Debounce: within a single commit, collect factory_ids, reschedule each once.
_SESSION_FACTORIES_ATTR = "_pending_reschedule_factories"
# Subset of the above: factories that received a material delivery.
# These need a re-reserve pass BEFORE the reschedule so positions in
# INSUFFICIENT_MATERIALS can flip back to PLANNED and the new schedule
# treats them as live.
_SESSION_MATERIAL_FACTORIES_ATTR = "_pending_material_receipt_factories"
# Re-entrancy guard: when our own background thread runs reserve+reschedule
# it will commit, which fires the same after_commit listener again. Skip
# the second pass to avoid an infinite loop.
_SESSION_AUTO_BACKFILL_ATTR = "_inside_auto_backfill"


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


def _collect_material_receipts(session: Session, flush_context):
    """Before commit: scan newly-inserted MaterialTransactions; if any of
    them are receipts (type=RECEIVE), queue the factory for reschedule.

    Rationale: a material arriving on the warehouse can unblock
    positions in INSUFFICIENT_MATERIALS — but only if the scheduler
    re-runs and re-checks reservations. Without this trigger, those
    positions would stay blocked until 02:00 WITA the next day.
    """
    try:
        pending: Set[UUID] = getattr(session, _SESSION_FACTORIES_ATTR, set())

        for obj in session.new:
            if getattr(obj, "__tablename__", None) != _MATERIAL_TXN_TABLE:
                continue

            txn_type = getattr(obj, "type", None)
            if hasattr(txn_type, "value"):
                txn_type = txn_type.value
            # Only material arrivals matter for unblocking. RESERVE /
            # UNRESERVE / CONSUME / INVENTORY adjustments are already
            # covered by the position-status path.
            if str(txn_type or "").lower() != "receive":
                continue

            factory_id = getattr(obj, "factory_id", None)
            if factory_id:
                pending.add(factory_id)
                # Mark this factory for re-reserve (extra step beyond reschedule).
                mat_pending: Set[UUID] = getattr(
                    session, _SESSION_MATERIAL_FACTORIES_ATTR, set(),
                )
                mat_pending.add(factory_id)
                setattr(session, _SESSION_MATERIAL_FACTORIES_ATTR, mat_pending)
                qty = getattr(obj, "quantity", None)
                mat_id = getattr(obj, "material_id", None)
                logger.debug(
                    "MATERIAL_RECEIVED | material=%s factory=%s qty=%s",
                    mat_id, factory_id, qty,
                )

        if pending:
            setattr(session, _SESSION_FACTORIES_ATTR, pending)
    except Exception as e:
        logger.warning("schedule_triggers receipt scan error: %s", e)


def _trigger_reschedule(session: Session):
    """After commit: fire reschedule_factory for each affected factory.

    For factories that ALSO had a material receipt, run the
    reserve+stone backfill first so positions waiting on that material
    flip out of INSUFFICIENT_MATERIALS before the schedule recomputes.
    """
    if getattr(session, _SESSION_AUTO_BACKFILL_ATTR, False):
        # We're inside the background thread's own commit — bail out to
        # avoid recursion.
        return

    pending: Set[UUID] = getattr(session, _SESSION_FACTORIES_ATTR, None)
    if not pending:
        return

    mat_pending: Set[UUID] = getattr(session, _SESSION_MATERIAL_FACTORIES_ATTR, set())

    # Clear before firing to avoid re-entry loops
    setattr(session, _SESSION_FACTORIES_ATTR, set())
    setattr(session, _SESSION_MATERIAL_FACTORIES_ATTR, set())

    # Fire in background so we don't block the current request
    def _run(factory_ids: Set[UUID], mat_ids: Set[UUID]):
        from api.database import SessionLocal
        from api.models import OrderPosition, Recipe
        from api.enums import PositionStatus
        from business.services.production_scheduler import reschedule_factory
        from business.services.material_reservation import reserve_materials_for_position
        from business.services.stone_reservation import reserve_stone_for_position

        db = SessionLocal()
        # Mark this DB session so its post-commit hooks don't recurse.
        setattr(db, _SESSION_AUTO_BACKFILL_ATTR, True)
        try:
            for fid in factory_ids:
                try:
                    if fid in mat_ids:
                        # Re-reserve every active position so freshly-arrived
                        # material lifts INSUFFICIENT_MATERIALS where applicable.
                        # Mirrors /schedule/backfill-procurement-tasks
                        # but without the network round-trip.
                        terminal = {
                            PositionStatus.SHIPPED.value,
                            PositionStatus.CANCELLED.value,
                            PositionStatus.MERGED.value,
                            PositionStatus.PACKED.value,
                            PositionStatus.READY_FOR_SHIPMENT.value,
                        }
                        positions = db.query(OrderPosition).filter(
                            OrderPosition.factory_id == fid,
                            ~OrderPosition.status.in_(list(terminal)),
                        ).all()
                        for p in positions:
                            try:
                                reserve_stone_for_position(db, p)
                            except Exception as ee:
                                logger.warning(
                                    "AUTO_BACKFILL_STONE_FAIL | pos=%s | %s",
                                    p.id, ee,
                                )
                            if p.recipe_id:
                                try:
                                    recipe = db.query(Recipe).filter(
                                        Recipe.id == p.recipe_id,
                                    ).first()
                                    if recipe:
                                        reserve_materials_for_position(
                                            db, p, recipe, fid,
                                        )
                                except Exception as ee:
                                    logger.warning(
                                        "AUTO_BACKFILL_MATERIAL_FAIL | pos=%s | %s",
                                        p.id, ee,
                                    )
                        db.commit()
                        logger.info(
                            "AUTO_BACKFILL_RESERVES | factory=%s | %d positions",
                            fid, len(positions),
                        )

                    reschedule_factory(db, fid)
                    db.commit()
                    logger.info(
                        "AUTO_RESCHEDULE | factory=%s%s",
                        fid,
                        " (after material receipt)" if fid in mat_ids else "",
                    )
                except Exception as e:
                    logger.error("AUTO_RESCHEDULE_FAILED | factory=%s | %s", fid, e)
                    db.rollback()
        finally:
            db.close()

    thread = threading.Thread(target=_run, args=(pending, mat_pending), daemon=True)
    thread.start()


def register_schedule_triggers() -> None:
    """Register event listeners — called once at app startup."""
    event.listen(Session, "after_flush", _collect_status_changes)
    event.listen(Session, "after_flush", _collect_material_receipts)
    event.listen(Session, "after_commit", _trigger_reschedule)
    logger.info(
        "Schedule triggers registered "
        "(position.status + material.receive → reschedule_factory)"
    )
