"""
Position Status Machine service.
Business Logic: Implementation Guide §4.1, §32b

Defines allowed transitions and provides validated transition logic.
"""
import logging
from uuid import UUID
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from api.models import OrderPosition, OrderStageHistory, ProductionStage
from api.enums import PositionStatus

logger = logging.getLogger("moonjar.status_machine")


# ────────────────────────────────────────────────────────────────
# §4.1  Allowed status transitions
# ────────────────────────────────────────────────────────────────
# Key = current status, Value = set of allowed next statuses.
# "blocked_by_qm" and "cancelled" are reachable from ANY status.

_TRANSITIONS: dict[PositionStatus, set[PositionStatus]] = {
    PositionStatus.PLANNED: {
        PositionStatus.INSUFFICIENT_MATERIALS,
        PositionStatus.AWAITING_RECIPE,
        PositionStatus.AWAITING_STENCIL_SILKSCREEN,
        PositionStatus.AWAITING_COLOR_MATCHING,
        PositionStatus.AWAITING_SIZE_CONFIRMATION,
        PositionStatus.AWAITING_CONSUMPTION_DATA,
        PositionStatus.ENGOBE_APPLIED,
        PositionStatus.GLAZED,  # if no engobe needed
    },
    PositionStatus.INSUFFICIENT_MATERIALS: {
        PositionStatus.PLANNED,
    },
    PositionStatus.AWAITING_RECIPE: {
        PositionStatus.PLANNED,
    },
    PositionStatus.AWAITING_STENCIL_SILKSCREEN: {
        PositionStatus.PLANNED,
    },
    PositionStatus.AWAITING_COLOR_MATCHING: {
        PositionStatus.PLANNED,
    },
    PositionStatus.AWAITING_SIZE_CONFIRMATION: {
        PositionStatus.PLANNED,
    },
    PositionStatus.AWAITING_CONSUMPTION_DATA: {
        PositionStatus.PLANNED,
    },
    PositionStatus.ENGOBE_APPLIED: {
        PositionStatus.ENGOBE_CHECK,
    },
    PositionStatus.ENGOBE_CHECK: {
        PositionStatus.GLAZED,
        PositionStatus.ENGOBE_APPLIED,  # redo
    },
    PositionStatus.GLAZED: {
        PositionStatus.PRE_KILN_CHECK,
    },
    PositionStatus.PRE_KILN_CHECK: {
        PositionStatus.LOADED_IN_KILN,
        PositionStatus.SENT_TO_GLAZING,  # needs redo
    },
    PositionStatus.SENT_TO_GLAZING: {
        PositionStatus.PLANNED,  # re-enters glazing pipeline
    },
    PositionStatus.LOADED_IN_KILN: {
        PositionStatus.FIRED,
    },
    PositionStatus.FIRED: {
        PositionStatus.TRANSFERRED_TO_SORTING,
        PositionStatus.REFIRE,
        PositionStatus.SENT_TO_GLAZING,  # multi-firing route
    },
    PositionStatus.TRANSFERRED_TO_SORTING: {
        PositionStatus.PACKED,
        PositionStatus.SENT_TO_GLAZING,  # repair
        PositionStatus.AWAITING_REGLAZE,
    },
    PositionStatus.AWAITING_REGLAZE: {
        PositionStatus.SENT_TO_GLAZING,
    },
    PositionStatus.REFIRE: {
        PositionStatus.LOADED_IN_KILN,
    },
    PositionStatus.PACKED: {
        PositionStatus.SENT_TO_QUALITY_CHECK,
        PositionStatus.READY_FOR_SHIPMENT,
        PositionStatus.SHIPPED,             # direct ship (already dispatched)
        PositionStatus.MERGED,              # child merged back into parent
    },
    PositionStatus.SENT_TO_QUALITY_CHECK: {
        PositionStatus.QUALITY_CHECK_DONE,
    },
    PositionStatus.QUALITY_CHECK_DONE: {
        PositionStatus.READY_FOR_SHIPMENT,
        PositionStatus.MERGED,              # child merged back into parent
    },
    PositionStatus.READY_FOR_SHIPMENT: {
        PositionStatus.SHIPPED,
        PositionStatus.MERGED,              # child merged back into parent
    },
    PositionStatus.BLOCKED_BY_QM: set(),  # dynamically returns to previous status
    PositionStatus.SHIPPED: set(),
    PositionStatus.MERGED: set(),   # terminal: child merged back into parent
    PositionStatus.CANCELLED: set(),
}

# Universal transitions: any status → blocked_by_qm / cancelled
_UNIVERSAL_TARGETS = {PositionStatus.BLOCKED_BY_QM, PositionStatus.CANCELLED}


# ────────────────────────────────────────────────────────────────
# Position status → production stage name mapping
# ────────────────────────────────────────────────────────────────
_STATUS_TO_STAGE: dict[PositionStatus, str] = {
    PositionStatus.PLANNED: "incoming_inspection",
    PositionStatus.ENGOBE_APPLIED: "engobe",
    PositionStatus.ENGOBE_CHECK: "engobe",
    PositionStatus.GLAZED: "glazing",
    PositionStatus.SENT_TO_GLAZING: "glazing",
    PositionStatus.PRE_KILN_CHECK: "pre_kiln_inspection",
    PositionStatus.LOADED_IN_KILN: "kiln_loading",
    PositionStatus.FIRED: "firing",
    PositionStatus.REFIRE: "firing",
    PositionStatus.TRANSFERRED_TO_SORTING: "sorting",
    PositionStatus.AWAITING_REGLAZE: "sorting",
    PositionStatus.PACKED: "packing",
    PositionStatus.SENT_TO_QUALITY_CHECK: "quality_check",
    PositionStatus.QUALITY_CHECK_DONE: "quality_check",
    PositionStatus.READY_FOR_SHIPMENT: "ready_for_shipment",
}


# ────────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────────

def validate_status_transition(current: str, new: str) -> bool:
    """
    Check if status transition is allowed.
    Returns True if the transition is valid, False otherwise.
    """
    try:
        current_ps = PositionStatus(current)
        new_ps = PositionStatus(new)
    except ValueError:
        return False

    # Universal targets (blocked_by_qm, cancelled) allowed from any status
    if new_ps in _UNIVERSAL_TARGETS:
        return True

    # blocked_by_qm can go to any status (returns to previous)
    if current_ps == PositionStatus.BLOCKED_BY_QM:
        return True

    allowed = _TRANSITIONS.get(current_ps, set())
    return new_ps in allowed


def get_allowed_transitions(current: str, role: str = "") -> list[str]:
    """Return list of allowed next statuses for a given current status.

    Management roles (owner, administrator, ceo, production_manager)
    get extra transitions — e.g. un-cancel back to PLANNED.
    """
    try:
        current_ps = PositionStatus(current)
    except ValueError:
        return []

    allowed = set(_TRANSITIONS.get(current_ps, set()))
    # Always add universal targets
    allowed |= _UNIVERSAL_TARGETS

    # Management override: allow recovery from terminal states
    _MGMT_ROLES = {"owner", "administrator", "ceo", "production_manager"}
    if role in _MGMT_ROLES:
        if current_ps == PositionStatus.CANCELLED:
            allowed.add(PositionStatus.PLANNED)
        if current_ps == PositionStatus.SHIPPED:
            allowed.add(PositionStatus.READY_FOR_SHIPMENT)

    return sorted([s.value for s in allowed])


def _track_stage_history(
    db: Session,
    position: OrderPosition,
    old_status_str: str,
    new_status: PositionStatus,
) -> None:
    """Record stage enter/exit times in OrderStageHistory.

    Best-effort: never raises — failures are logged and swallowed.
    """
    try:
        old_stage_name = _STATUS_TO_STAGE.get(PositionStatus(old_status_str)) if old_status_str else None
        new_stage_name = _STATUS_TO_STAGE.get(new_status)

        # If the stage changed, close the old entry and open a new one
        if old_stage_name and old_stage_name != new_stage_name:
            old_stage = db.query(ProductionStage).filter(
                ProductionStage.name == old_stage_name
            ).first()
            if old_stage:
                prev_entry = (
                    db.query(OrderStageHistory)
                    .filter(
                        OrderStageHistory.order_id == position.order_id,
                        OrderStageHistory.stage_id == old_stage.id,
                        OrderStageHistory.exited_at.is_(None),
                    )
                    .order_by(OrderStageHistory.entered_at.desc())
                    .first()
                )
                if prev_entry:
                    prev_entry.exited_at = datetime.now(timezone.utc)

        if new_stage_name and new_stage_name != old_stage_name:
            new_stage = db.query(ProductionStage).filter(
                ProductionStage.name == new_stage_name
            ).first()
            if new_stage:
                db.add(OrderStageHistory(
                    order_id=position.order_id,
                    stage_id=new_stage.id,
                ))
    except Exception:
        import logging
        logging.getLogger("moonjar.status_machine").warning(
            "Failed to track stage history for position %s", position.id,
            exc_info=True,
        )


def transition_position_status(
    db: Session,
    position_id: UUID,
    new_status: str,
    changed_by: UUID,
    is_override: bool = False,
    notes: Optional[str] = None,
) -> OrderPosition:
    """
    Validate and apply a status transition on an OrderPosition.

    - Validates transition (unless is_override=True for PM/admin overrides)
    - Updates position status
    - Fires special routing for FIRED status (multi-firing)
    - Returns updated position

    Raises ValueError if transition is invalid.
    """
    position = db.query(OrderPosition).filter(OrderPosition.id == position_id).first()
    if not position:
        raise ValueError(f"Position {position_id} not found")

    old_status = position.status.value if isinstance(position.status, PositionStatus) else str(position.status)
    new_status_str = new_status

    # Validate unless override
    if not is_override:
        if not validate_status_transition(old_status, new_status_str):
            allowed = get_allowed_transitions(old_status)
            raise ValueError(
                f"Invalid transition: {old_status} → {new_status_str}. "
                f"Allowed: {allowed}"
            )
    else:
        # Audit log: admin/PM override bypassing normal transition rules
        from api.auth import log_security_event
        log_security_event(
            db,
            action="status_override",
            actor_id=str(changed_by),
            target_entity="order_position",
            target_id=str(position_id),
            details={
                "old_status": old_status,
                "new_status": new_status_str,
                "notes": notes,
            },
        )

    # Apply status
    try:
        new_ps = PositionStatus(new_status_str)
    except ValueError:
        raise ValueError(f"Invalid status value: {new_status_str}")

    position.status = new_ps
    position.updated_at = datetime.now(timezone.utc)

    # ── Track stage history ────────────────────────────────────
    _track_stage_history(db, position, old_status, new_ps)

    # ── Batch assignment check for LOADED_IN_KILN ──────────────
    # When a position transitions to LOADED_IN_KILN, it should
    # already be assigned to a batch. Log a warning if not.
    if new_ps == PositionStatus.LOADED_IN_KILN:
        if not position.batch_id:
            import logging
            logging.getLogger("moonjar.status_machine").warning(
                "Position %s transitioning to LOADED_IN_KILN without batch assignment. "
                "Positions should be assigned to a batch before kiln loading.",
                position_id,
            )

    # Special routing: FIRED → multi-firing check
    if new_ps == PositionStatus.FIRED:
        route_after_firing(db, position)

    # ── Material consumption on glazing start ─────────────────────
    # When position transitions to ENGOBE_APPLIED or GLAZED (first time),
    # consume BOM materials and release reservations.
    if new_ps in (PositionStatus.ENGOBE_APPLIED, PositionStatus.GLAZED):
        if not position.materials_written_off_at:
            try:
                from business.services.material_consumption import on_glazing_start
                on_glazing_start(db, position.id)
            except Exception as _e:
                import logging
                logging.getLogger("moonjar.status_machine").warning(
                    "Failed to consume materials for position %s on glazing start: %s",
                    position_id, _e,
                )
        elif (position.firing_round or 1) > 1:
            # Refire/reglaze cycle — consume only surface materials
            try:
                from business.services.material_consumption import consume_refire_materials
                consume_refire_materials(db, position.id)
            except Exception as _e:
                import logging
                logging.getLogger("moonjar.status_machine").warning(
                    "Failed to consume refire materials for position %s: %s",
                    position_id, _e,
                )

    # ── Reschedule on status change ──────────────────────────────
    # When a position transitions to a status that indicates delay
    # or requires re-routing, recalculate its production schedule.
    _DELAY_STATUSES = {
        PositionStatus.INSUFFICIENT_MATERIALS,
        PositionStatus.AWAITING_RECIPE,
        PositionStatus.AWAITING_STENCIL_SILKSCREEN,
        PositionStatus.AWAITING_COLOR_MATCHING,
        PositionStatus.SENT_TO_GLAZING,        # re-entering glazing pipeline
        PositionStatus.REFIRE,                  # needs another firing
        PositionStatus.AWAITING_REGLAZE,        # repair → reglaze
        PositionStatus.BLOCKED_BY_QM,           # quality hold
    }
    if new_ps in _DELAY_STATUSES:
        try:
            from business.services.production_scheduler import reschedule_position
            reschedule_position(db, position)
        except Exception as _e:
            import logging
            logging.getLogger("moonjar.status_machine").warning(
                "Failed to reschedule position %s after status change: %s",
                position_id, _e,
            )

    # ── Unreserve materials on cancellation ──────────────────────
    if new_ps == PositionStatus.CANCELLED:
        try:
            from business.services.material_reservation import unreserve_materials_for_position
            unreserve_materials_for_position(db, position.id)
        except Exception as _e:
            import logging
            logging.getLogger("moonjar.status_machine").warning(
                "Failed to unreserve materials for position %s: %s",
                position_id, _e,
            )

    # ── Real-time alerts for critical events ─────────────────────
    # These trigger immediately via Telegram (not waiting for 21:00 daily batch)
    _send_realtime_alerts(db, position, old_status, new_ps, notes)

    # ── Pull System: auto-pull next work when capacity available ──
    try:
        from business.services.pull_system import try_pull_next_work
        pulled = try_pull_next_work(db, position, new_ps.value, changed_by)
        if pulled:
            logger.info(
                "PULL_TRIGGERED | position=%s → %s | pulled %d forward",
                position_id, new_ps.value, len(pulled),
            )
    except Exception as _e:
        logger.warning("Pull system error (non-blocking): %s", _e)

    db.commit()
    db.refresh(position)
    return position


def _send_realtime_alerts(
    db: Session,
    position: OrderPosition,
    old_status: str,
    new_status: PositionStatus,
    notes: Optional[str] = None,
) -> None:
    """
    Send instant Telegram alerts for critical production events.
    Best-effort: never fails the transition.
    """
    import logging
    _logger = logging.getLogger("moonjar.realtime_alerts")

    try:
        from business.services.notifications import notify_pm, create_notification  # noqa: dead-code
        from api.models import ProductionOrder, Factory
        from api.enums import NotificationType, RelatedEntityType  # noqa: dead-code

        order = db.query(ProductionOrder).get(position.order_id) if position.order_id else None
        order_num = order.order_number if order else "?"
        pos_label = f"#{position.position_number}" + (f".{position.split_index}" if position.split_index else "")
        factory_id = position.factory_id

        if not factory_id:
            return

        # 1. QM Block — quality issue detected
        if new_status == PositionStatus.BLOCKED_BY_QM:
            title = f"⛔ БЛОК ОТК: Заказ {order_num} {pos_label}"
            msg = (
                f"Позиция {pos_label} заблокирована ОТК.\n"
                f"Заказ: {order_num}\n"
                f"Цвет: {position.color or '-'}\n"
                f"Предыдущий статус: {old_status}"
            )
            if notes:
                msg += f"\nПримечание: {notes}"
            notify_pm(db, factory_id, "qm_block", title, msg,
                      related_entity_type="order_position",
                      related_entity_id=position.id)
            # Also send to factory's masters chat with action button
            pid_short = str(position.id)[:8]
            qm_buttons = [
                [{"text": "\U0001f50d Подробнее", "callback_data": f"a:v:{pid_short}"}],
            ]
            _send_to_factory_chat(db, factory_id, f"⛔ *БЛОК ОТК*\n{msg}", inline_keyboard=qm_buttons)
            _logger.info("REALTIME_ALERT | qm_block | order=%s pos=%s", order_num, pos_label)

        # 2. Refire needed — significant delay
        elif new_status == PositionStatus.REFIRE:
            title = f"🔄 ПОВТОРНЫЙ ОБЖИГ: Заказ {order_num} {pos_label}"
            msg = (
                f"Позиция {pos_label} требует повторного обжига.\n"
                f"Заказ: {order_num}\n"
                f"Раунд: {position.firing_round + 1}"
            )
            notify_pm(db, factory_id, "refire_needed", title, msg,
                      related_entity_type="order_position",
                      related_entity_id=position.id)
            _logger.info("REALTIME_ALERT | refire | order=%s pos=%s", order_num, pos_label)

        # 3. Material shortage — position blocked
        elif new_status == PositionStatus.INSUFFICIENT_MATERIALS:
            title = f"📦 НЕХВАТКА МАТЕРИАЛА: Заказ {order_num} {pos_label}"
            msg = (
                f"Позиция {pos_label} не обеспечена материалами.\n"
                f"Заказ: {order_num}\n"
                f"Цвет: {position.color or '-'}"
            )
            notify_pm(db, factory_id, "material_shortage", title, msg,
                      related_entity_type="order_position",
                      related_entity_id=position.id)
            _logger.info("REALTIME_ALERT | material_shortage | order=%s pos=%s", order_num, pos_label)

        # 4. Awaiting reglaze — defect repair loop
        elif new_status == PositionStatus.AWAITING_REGLAZE:
            title = f"🔧 ПОВТОРНАЯ ГЛАЗУРОВКА: Заказ {order_num} {pos_label}"
            msg = (
                f"Позиция {pos_label} требует повторной глазуровки после ремонта.\n"
                f"Заказ: {order_num}"
            )
            notify_pm(db, factory_id, "reglaze_needed", title, msg,
                      related_entity_type="order_position",
                      related_entity_id=position.id)
            _logger.info("REALTIME_ALERT | reglaze | order=%s pos=%s", order_num, pos_label)

        # 5. Position ready for shipment — notify warehouse
        elif new_status == PositionStatus.READY_FOR_SHIPMENT:
            from api.enums import UserRole
            from business.services.notifications import notify_role
            title = f"📦 ГОТОВО К ОТГРУЗКЕ: Заказ {order_num} {pos_label}"
            msg = (
                f"Позиция {pos_label} готова к отгрузке.\n"
                f"Заказ: {order_num}\n"
                f"Количество: {position.quantity} шт"
            )
            notify_role(db, factory_id, UserRole.WAREHOUSE, "ready_for_shipment",
                        title, msg,
                        related_entity_type="order_position",
                        related_entity_id=position.id)
            _logger.info("REALTIME_ALERT | ready_for_shipment | order=%s pos=%s", order_num, pos_label)

    except Exception as e:
        import logging
        logging.getLogger("moonjar.realtime_alerts").warning(
            "Failed to send realtime alert for position %s: %s", position.id, e
        )


def _send_to_factory_chat(
    db: Session,
    factory_id: UUID,
    text: str,
    inline_keyboard: list[list[dict]] | None = None,
) -> None:
    """Send message to factory's masters group chat (best-effort).

    If inline_keyboard is provided, sends with inline buttons.
    """
    try:
        from api.models import Factory

        factory = db.query(Factory).get(factory_id)
        if factory and factory.masters_group_chat_id:
            chat_id = str(factory.masters_group_chat_id)
            if inline_keyboard:
                from business.services.notifications import send_telegram_message_with_buttons
                send_telegram_message_with_buttons(chat_id, text, inline_keyboard)
            else:
                from business.services.notifications import send_telegram_message
                send_telegram_message(chat_id, text)
    except Exception as e:
        logger.warning("Failed to send Telegram notification to masters group: %s", e)


# ────────────────────────────────────────────────────────────────
# Multi-firing routing (from §32b)
# ────────────────────────────────────────────────────────────────

def _try_reserve_packaging(db: Session, position: OrderPosition):
    """Best-effort packaging reservation + availability check when entering sorting."""
    try:
        from business.services.packaging_consumption import on_sorting_start
        if position.factory_id:
            on_sorting_start(db, position.id, position.factory_id)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(
            "Failed to process sorting start for position %s: %s", position.id, e
        )


def route_after_firing(db: Session, position: OrderPosition) -> str:
    """
    Called when a position transitions to FIRED status.
    Determines next status based on multi-firing configuration.

    If position has more firing rounds remaining → route to SENT_TO_GLAZING
    (or PRE_KILN_CHECK if glazing not required) and increment firing_round.

    If this was the final firing → route to TRANSFERRED_TO_SORTING.

    Returns the new status string.
    """
    from business.services.firing_profiles import (
        get_total_firing_rounds,
        get_recipe_firing_stage,
    )

    if not position.recipe_id:
        # No recipe → single firing, go to sorting
        position.status = PositionStatus.TRANSFERRED_TO_SORTING
        _try_reserve_packaging(db, position)
        return PositionStatus.TRANSFERRED_TO_SORTING.value

    total_rounds = get_total_firing_rounds(db, position.recipe_id)

    if position.firing_round < total_rounds:
        # More firing rounds needed → route back to glazing pipeline
        next_round = position.firing_round + 1
        next_stage = get_recipe_firing_stage(db, position.recipe_id, next_round)

        if next_stage and next_stage.requires_glazing_before:
            position.status = PositionStatus.SENT_TO_GLAZING
        else:
            position.status = PositionStatus.PRE_KILN_CHECK

        position.firing_round = next_round
        position.batch_id = None       # Unassign from current batch
        position.resource_id = None    # Unassign kiln

        return position.status.value
    else:
        # Final firing done → sorting
        position.status = PositionStatus.TRANSFERRED_TO_SORTING
        _try_reserve_packaging(db, position)
        return PositionStatus.TRANSFERRED_TO_SORTING.value
