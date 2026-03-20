"""
Daily Task Distribution service.
Business Logic: §11, §34

Generates tomorrow's task list per factory, formats as Telegram message,
sends to masters group chat, and saves record to daily_task_distributions table.
"""
from uuid import UUID
from datetime import date, datetime, timedelta
from decimal import Decimal
from math import ceil
from typing import Optional
import logging

from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func

from api.models import (
    Factory,
    OrderPosition,
    ProductionOrder,
    Recipe,
    RecipeKilnConfig,
    Resource,
    Batch,
    ScheduleSlot,
    Task,
    DefectRecord,
    DailyTaskDistribution,
    GlazingBoardSpec,
    Size,
)
from api.enums import (
    PositionStatus,
    OrderStatus,
    BatchStatus,
    ResourceType,
    ResourceStatus,
    TaskType,
    TaskStatus,
)
from business.services.notifications import send_telegram_message, send_telegram_message_with_buttons

logger = logging.getLogger("moonjar.daily_distribution")

# Statuses that indicate a position is ready for glazing (pre-kiln pipeline)
GLAZING_ELIGIBLE_STATUSES = [
    PositionStatus.PLANNED.value,
    PositionStatus.ENGOBE_APPLIED.value,
    PositionStatus.ENGOBE_CHECK.value,
    PositionStatus.SENT_TO_GLAZING.value,
]

# Statuses that indicate a position is ready for kiln preparation
KILN_PREP_ELIGIBLE_STATUSES = [
    PositionStatus.GLAZED.value,
    PositionStatus.PRE_KILN_CHECK.value,
]

# Default glaze consumption: 500 g/sqm (0.5 kg/sqm)
DEFAULT_GLAZE_CONSUMPTION_KG_PER_SQM = Decimal("0.5")

# Default max positions per day for rope constraint
DEFAULT_ROPE_MAX_POSITIONS = 20


# ────────────────────────────────────────────────────────────────
# §1  Main entry point
# ────────────────────────────────────────────────────────────────

def daily_task_distribution(db: Session, factory_id: UUID) -> dict:
    """Generate tomorrow's task distribution for a factory.

    1. Collects glazing positions eligible for tomorrow
    2. Collects planned kiln batches for tomorrow
    3. Checks for overdue/urgent orders
    4. Computes yesterday's KPI snapshot
    5. Saves distribution record
    6. Sends formatted message to Telegram masters group

    Returns the distribution dict.
    """
    factory = db.query(Factory).filter(Factory.id == factory_id).first()
    if not factory:
        logger.error("Factory %s not found", factory_id)
        return {}

    tomorrow = date.today() + timedelta(days=1)

    # --- Build distribution ---
    glazing_tasks = _collect_glazing_tasks(db, factory_id, tomorrow)
    kiln_prep_tasks = _collect_kiln_prep_tasks(db, factory_id, tomorrow)
    kiln_loading = _collect_kiln_loading(db, factory_id, tomorrow)
    urgent_alerts = _collect_urgent_alerts(db, factory_id)

    # Count urgent (behind schedule) positions
    urgent_count = sum(
        1 for t in glazing_tasks
        if t.get("behind_schedule")
    ) + sum(
        1 for t in kiln_prep_tasks
        if t.get("behind_schedule")
    )

    total_positions = len(glazing_tasks) + len(kiln_prep_tasks)

    distribution = {
        "factory_id": str(factory_id),
        "factory_name": factory.name,
        "distribution_date": tomorrow.isoformat(),
        "glazing_tasks": glazing_tasks,
        "kiln_prep_tasks": kiln_prep_tasks,
        "kiln_loading": kiln_loading,
        "urgent_alerts": urgent_alerts,
        "kpi_yesterday": _compute_kpi_yesterday(db, factory_id),
        "total_positions": total_positions,
        "urgent_count": urgent_count,
    }

    # --- Persist to daily_task_distributions ---
    _save_distribution_record(db, factory_id, tomorrow, distribution)

    # --- Send Telegram message with inline buttons ---
    language = factory.telegram_language or "id"
    if factory.masters_group_chat_id:
        message = format_daily_message(distribution, language)
        chat_id = str(factory.masters_group_chat_id)
        date_str = tomorrow.isoformat()
        fid = str(factory_id)

        # Compact callback_data (must be <= 64 bytes):
        #   d:a:{factory_id}:{date}  — acknowledge
        #   d:p:{factory_id}:{date}  — report problem
        #   d:d:{factory_id}:{date}  — show detail
        # Use short UUID (first 8 chars) to save bytes
        fid_short = fid[:8]
        inline_keyboard = [
            [{"text": "\u2705 Terima tugas", "callback_data": f"d:a:{fid_short}:{date_str}"}],
            [{"text": "\u26a0\ufe0f Laporkan masalah", "callback_data": f"d:p:{fid_short}:{date_str}"}],
            [{"text": "\U0001f4cb Detail tugas", "callback_data": f"d:d:{fid_short}:{date_str}"}],
        ]

        try:
            result = send_telegram_message_with_buttons(chat_id, message, inline_keyboard)
            telegram_message_id = None
            if result:
                telegram_message_id = result.get("message_id")
            # Store message_id on the distribution record
            if telegram_message_id:
                _update_distribution_message_id(db, factory_id, tomorrow, telegram_message_id)
            logger.info(
                "Daily distribution sent to factory %s (chat %s, msg_id=%s)",
                factory.name, factory.masters_group_chat_id, telegram_message_id,
            )
        except Exception as e:
            logger.error(
                "Failed to send daily distribution for factory %s: %s",
                factory.name, e,
            )
    else:
        logger.warning(
            "Factory %s has no masters_group_chat_id, skipping Telegram",
            factory.name,
        )

    return distribution


# ────────────────────────────────────────────────────────────────
# §2  Glazing tasks collection
# ────────────────────────────────────────────────────────────────

def get_glazing_positions_for_tomorrow(db: Session, factory_id: UUID) -> list:
    """Get positions eligible for glazing, filtered through TOC rope limit.

    Filters:
      - Status in GLAZING_ELIGIBLE_STATUSES (planned, sent_to_glazing,
        engobe_applied, engobe_check)
      - planned_glazing_date <= tomorrow (due or overdue for glazing)
      - Order is in active production
      - Not cancelled / not shipped

    Returns list of OrderPosition objects ready for glazing work tomorrow.
    """
    from sqlalchemy import or_

    tomorrow = date.today() + timedelta(days=1)

    positions = (
        db.query(OrderPosition)
        .join(ProductionOrder, OrderPosition.order_id == ProductionOrder.id)
        .filter(
            OrderPosition.factory_id == factory_id,
            OrderPosition.status.in_(GLAZING_ELIGIBLE_STATUSES),
            ProductionOrder.status.in_([
                OrderStatus.IN_PRODUCTION.value,
                OrderStatus.PARTIALLY_READY.value,
            ]),
            # Position is scheduled for glazing by tomorrow or has no date
            # (unscheduled positions are included so they don't get lost)
            or_(
                OrderPosition.planned_glazing_date <= tomorrow,
                OrderPosition.planned_glazing_date.is_(None),
            ),
        )
        .order_by(
            OrderPosition.priority_order.desc(),
            OrderPosition.planned_glazing_date.asc().nullslast(),
            ProductionOrder.final_deadline.asc().nullslast(),
            OrderPosition.created_at.asc(),
        )
        .all()
    )

    # Apply TOC rope limit if available
    try:
        from business.services.buffer_health import apply_rope_limit
        positions = apply_rope_limit(db, factory_id, positions)
    except Exception as e:
        logger.warning("Rope limit failed, using full list: %s", e)

    # Fallback limit if rope limit is not configured
    if len(positions) > DEFAULT_ROPE_MAX_POSITIONS:
        positions = positions[:DEFAULT_ROPE_MAX_POSITIONS]

    return positions


def _collect_glazing_tasks(db: Session, factory_id: UUID, target_date: date) -> list:
    """Build glazing task list for tomorrow."""
    positions = get_glazing_positions_for_tomorrow(db, factory_id)
    tasks = []

    for pos in positions:
        order = pos.order
        recipe = pos.recipe

        # Estimate glaze quantity (kg)
        glaze_qty_kg = _estimate_glaze_qty_kg(pos, recipe)

        # Check if engobe is needed (recipe has engobe sub-recipe or engobe materials)
        engobe_needed = _check_engobe_needed(recipe)

        # Build human-readable position label: "#3" or "#3.1" for splits
        position_label = _format_position_label(pos)

        # Build consumption info string
        consumption_info = f"{glaze_qty_kg:.1f} kg"
        if engobe_needed:
            consumption_info += " + engobe"

        # ── Glazing board info ──
        board_info = _get_board_info_for_position(db, pos, recipe)

        # Check if position is behind schedule
        behind_schedule = (
            pos.planned_glazing_date is not None
            and pos.planned_glazing_date < date.today()
        )

        tasks.append({
            "position_id": str(pos.id),
            "order_number": order.order_number if order else "???",
            "position_number": pos.position_number or 0,
            "position_label": position_label,
            "color": pos.color or "",
            "color_2": pos.color_2,
            "size": pos.size or "",
            "quantity": pos.quantity,
            "recipe_name": recipe.name if recipe else "No recipe",
            "recipe_id": str(recipe.id) if recipe else None,
            "glaze_qty_kg": float(glaze_qty_kg),
            "consumption_info": consumption_info,
            "engobe_needed": engobe_needed,
            "behind_schedule": behind_schedule,
            "collection": getattr(pos, "collection", None) or "",
            "application_type": getattr(pos, "application_type", None) or "",
            # Board info for workers
            "board_info": board_info,
        })

    return tasks


def _get_board_info_for_position(db: Session, position, recipe) -> Optional[dict]:
    """Get glazing board info for a position: board size, tiles per board, ml per 2 boards.

    Workers need to know:
    - Which board to use (standard 122×21 or custom)
    - How many tiles per board
    - How many ml of glaze per 2 boards (they glaze 2 boards simultaneously)
    """
    try:
        size_id = getattr(position, 'size_id', None)
        if not size_id:
            return None

        board = db.query(GlazingBoardSpec).filter(GlazingBoardSpec.size_id == size_id).first()
        if not board:
            return None

        # Calculate ml per 2 boards from recipe consumption rate
        area_2boards = float(board.area_per_two_boards_m2) if board.area_per_two_boards_m2 else float(board.area_per_board_m2) * 2
        ml_per_2boards = 0.0

        if recipe:
            ml_per_sqm = None
            app_method = (getattr(position, 'application_method_code', None) or '').lower()

            SPRAY_METHODS = {'ss', 's', 'bs', 'stencil', 'raku', 'gold'}
            BRUSH_METHODS = {'sb', 'splashing'}

            if app_method in SPRAY_METHODS and getattr(recipe, 'consumption_spray_ml_per_sqm', None):
                ml_per_sqm = float(recipe.consumption_spray_ml_per_sqm)
            elif app_method in BRUSH_METHODS and getattr(recipe, 'consumption_brush_ml_per_sqm', None):
                ml_per_sqm = float(recipe.consumption_brush_ml_per_sqm)
            elif getattr(recipe, 'consumption_spray_ml_per_sqm', None):
                ml_per_sqm = float(recipe.consumption_spray_ml_per_sqm)
            elif getattr(recipe, 'consumption_brush_ml_per_sqm', None):
                ml_per_sqm = float(recipe.consumption_brush_ml_per_sqm)
            elif recipe.glaze_settings:
                gs_val = recipe.glaze_settings.get("consumption_ml_per_sqm")
                if gs_val:
                    ml_per_sqm = float(gs_val)

            if ml_per_sqm:
                ml_per_2boards = round(ml_per_sqm * area_2boards, 0)

        return {
            "board_size": f"{float(board.board_length_cm):.0f}×{float(board.board_width_cm):.0f}",
            "board_width_cm": float(board.board_width_cm),
            "is_standard": not board.is_custom_board,
            "tiles_per_board": board.tiles_per_board,
            "tiles_per_2boards": board.tiles_per_board * 2,
            "area_per_2boards_m2": round(area_2boards, 4),
            "ml_per_2boards": int(ml_per_2boards),
        }
    except Exception as e:
        logger.warning("BOARD_INFO_FAIL | position=%s | %s", getattr(position, 'id', '?'), e)
        return None


def _estimate_glaze_qty_kg(position, recipe) -> Decimal:
    """Estimate total glaze needed in kg for a position.

    Uses recipe consumption settings if available, otherwise defaults.
    Formula: glazeable_area_sqm * quantity * consumption_per_sqm / 1000
    """
    # Get per-piece area
    per_piece_sqm = Decimal("0")
    if position.glazeable_sqm and float(position.glazeable_sqm) > 0:
        per_piece_sqm = Decimal(str(position.glazeable_sqm))
    elif position.quantity_sqm and position.quantity:
        per_piece_sqm = Decimal(str(position.quantity_sqm)) / Decimal(str(position.quantity))

    if per_piece_sqm <= 0:
        # Fallback: parse size string "WxH" in cm -> sqm
        try:
            parts = (position.size or "10x10").lower().split("x")
            w_cm = float(parts[0])
            h_cm = float(parts[1]) if len(parts) > 1 else w_cm
            per_piece_sqm = Decimal(str(w_cm * h_cm / 10000))
        except (ValueError, IndexError):
            per_piece_sqm = Decimal("0.01")  # 10x10 cm fallback

    total_area = per_piece_sqm * Decimal(str(position.quantity))

    # Consumption rate (ml/sqm -> kg/sqm, using SG for ml→grams conversion)
    consumption_kg_per_sqm = DEFAULT_GLAZE_CONSUMPTION_KG_PER_SQM
    if recipe:
        # Prefer dedicated columns, fallback to glaze_settings
        ml_per_sqm = None
        if getattr(recipe, 'consumption_spray_ml_per_sqm', None):
            ml_per_sqm = float(recipe.consumption_spray_ml_per_sqm)
        elif getattr(recipe, 'consumption_brush_ml_per_sqm', None):
            ml_per_sqm = float(recipe.consumption_brush_ml_per_sqm)
        elif recipe.glaze_settings:
            gs_val = recipe.glaze_settings.get("consumption_ml_per_sqm")
            if gs_val:
                ml_per_sqm = float(gs_val)

        if ml_per_sqm:
            sg = float(recipe.specific_gravity) if recipe.specific_gravity and float(recipe.specific_gravity) > 0 else 1.0
            # ml × SG → grams → kg
            consumption_kg_per_sqm = Decimal(str(ml_per_sqm * sg)) / Decimal("1000")

    return round(total_area * consumption_kg_per_sqm, 2)


def _check_engobe_needed(recipe) -> bool:
    """Check if engobe application is needed for this recipe."""
    if not recipe:
        return False
    # Check glaze_settings for engobe flag
    gs = recipe.glaze_settings or {}
    if gs.get("engobe_required"):
        return True
    # Check recipe type
    if recipe.recipe_type == "engobe":
        return True
    return False


def _format_position_label(pos) -> str:
    """Format human-readable position label: '#3' or '#3.1' for splits."""
    num = pos.position_number or 0
    if pos.split_index:
        return f"{num}.{pos.split_index}"
    return str(num)


# ────────────────────────────────────────────────────────────────
# §2b Kiln prep tasks collection
# ────────────────────────────────────────────────────────────────

def _collect_kiln_prep_tasks(db: Session, factory_id: UUID, target_date: date) -> list:
    """Collect positions ready for kiln preparation (GLAZED / PRE_KILN_CHECK).

    These are positions that have been glazed and need to be prepared
    for kiln loading by tomorrow.
    """
    from sqlalchemy import or_

    positions = (
        db.query(OrderPosition)
        .join(ProductionOrder, OrderPosition.order_id == ProductionOrder.id)
        .filter(
            OrderPosition.factory_id == factory_id,
            OrderPosition.status.in_(KILN_PREP_ELIGIBLE_STATUSES),
            ProductionOrder.status.in_([
                OrderStatus.IN_PRODUCTION.value,
                OrderStatus.PARTIALLY_READY.value,
            ]),
            or_(
                OrderPosition.planned_kiln_date <= target_date,
                OrderPosition.planned_kiln_date.is_(None),
            ),
        )
        .order_by(
            OrderPosition.priority_order.desc(),
            OrderPosition.planned_kiln_date.asc().nullslast(),
            ProductionOrder.final_deadline.asc().nullslast(),
            OrderPosition.created_at.asc(),
        )
        .all()
    )

    tasks = []
    for pos in positions:
        order = pos.order
        position_label = _format_position_label(pos)

        behind_schedule = (
            pos.planned_kiln_date is not None
            and pos.planned_kiln_date < date.today()
        )

        tasks.append({
            "position_id": str(pos.id),
            "order_number": order.order_number if order else "???",
            "position_number": pos.position_number or 0,
            "position_label": position_label,
            "color": pos.color or "",
            "size": pos.size or "",
            "quantity": pos.quantity,
            "status": pos.status if isinstance(pos.status, str) else pos.status.value,
            "behind_schedule": behind_schedule,
        })

    return tasks


# ────────────────────────────────────────────────────────────────
# §3  Kiln loading collection
# ────────────────────────────────────────────────────────────────

def _collect_kiln_loading(db: Session, factory_id: UUID, target_date: date) -> list:
    """Collect planned kiln batches for tomorrow."""
    batches = (
        db.query(Batch)
        .join(Resource, Batch.resource_id == Resource.id)
        .filter(
            Batch.factory_id == factory_id,
            Batch.batch_date == target_date,
            Batch.status.in_([
                BatchStatus.PLANNED.value,
                BatchStatus.SUGGESTED.value,
            ]),
            Resource.resource_type == ResourceType.KILN.value,
            Resource.is_active.is_(True),
        )
        .all()
    )

    kiln_loading = []
    for batch in batches:
        resource = batch.resource

        # Count positions assigned to this batch
        positions = db.query(OrderPosition).filter(
            OrderPosition.batch_id == batch.id,
        ).all()

        # Get firing config from recipe of first position (or batch target_temperature)
        temperature = batch.target_temperature
        duration_hours = None

        if positions and positions[0].recipe_id:
            kiln_config = db.query(RecipeKilnConfig).filter(
                RecipeKilnConfig.recipe_id == positions[0].recipe_id,
            ).first()
            if kiln_config:
                if not temperature and kiln_config.firing_temperature:
                    temperature = kiln_config.firing_temperature
                if kiln_config.firing_duration_hours:
                    duration_hours = float(kiln_config.firing_duration_hours)

        # Build position summaries
        pos_summaries = []
        for pos in positions:
            order = pos.order
            pos_summaries.append({
                "position_id": str(pos.id),
                "order_number": order.order_number if order else "???",
                "color": pos.color or "",
                "size": pos.size or "",
                "quantity": pos.quantity,
            })

        kiln_loading.append({
            "kiln_name": resource.name if resource else "Unknown",
            "kiln_id": str(resource.id) if resource else None,
            "batch_id": str(batch.id),
            "positions_count": len(positions),
            "temperature": temperature or 0,
            "duration_hours": duration_hours or 0,
            "positions": pos_summaries,
        })

    return kiln_loading


# ────────────────────────────────────────────────────────────────
# §4  Urgent alerts
# ────────────────────────────────────────────────────────────────

def _collect_urgent_alerts(db: Session, factory_id: UUID) -> list:
    """Identify overdue and near-deadline orders."""
    today = date.today()
    alerts = []

    # Overdue orders
    overdue_orders = (
        db.query(ProductionOrder)
        .filter(
            ProductionOrder.factory_id == factory_id,
            ProductionOrder.status.in_([
                OrderStatus.IN_PRODUCTION.value,
                OrderStatus.PARTIALLY_READY.value,
            ]),
            ProductionOrder.final_deadline.isnot(None),
            ProductionOrder.final_deadline < today,
        )
        .order_by(ProductionOrder.final_deadline.asc())
        .all()
    )

    for order in overdue_orders:
        days_overdue = (today - order.final_deadline).days
        alerts.append({
            "order": order.order_number,
            "message": f"OVERDUE {days_overdue} day{'s' if days_overdue != 1 else ''}!",
            "deadline": order.final_deadline.isoformat(),
            "days_overdue": days_overdue,
        })

    # Due tomorrow
    due_tomorrow = (
        db.query(ProductionOrder)
        .filter(
            ProductionOrder.factory_id == factory_id,
            ProductionOrder.status.in_([
                OrderStatus.IN_PRODUCTION.value,
                OrderStatus.PARTIALLY_READY.value,
            ]),
            ProductionOrder.final_deadline == today + timedelta(days=1),
        )
        .all()
    )

    for order in due_tomorrow:
        alerts.append({
            "order": order.order_number,
            "message": "Due TOMORROW!",
            "deadline": order.final_deadline.isoformat(),
            "days_overdue": -1,
        })

    # Blocking tasks still pending
    blocking_tasks = (
        db.query(Task)
        .filter(
            Task.factory_id == factory_id,
            Task.blocking.is_(True),
            Task.status.in_([TaskStatus.PENDING.value, TaskStatus.IN_PROGRESS.value]),
            Task.type.in_([
                TaskType.STENCIL_ORDER.value,
                TaskType.SILK_SCREEN_ORDER.value,
                TaskType.COLOR_MATCHING.value,
            ]),
        )
        .all()
    )

    for task in blocking_tasks:
        order = task.related_order
        order_num = order.order_number if order else "???"
        task_label = task.type.replace("_", " ").title() if isinstance(task.type, str) else task.type.value.replace("_", " ").title()
        alerts.append({
            "order": order_num,
            "message": f"Blocking: {task_label} pending",
            "deadline": None,
            "days_overdue": 0,
        })

    return alerts


# ────────────────────────────────────────────────────────────────
# §5  KPI (yesterday's snapshot)
# ────────────────────────────────────────────────────────────────

def _compute_kpi_yesterday(db: Session, factory_id: UUID) -> dict:
    """Compute yesterday's key metrics."""
    yesterday = date.today() - timedelta(days=1)

    # Defect rate: defects_yesterday / total_pieces_processed_yesterday * 100
    defect_count = db.query(
        sa_func.coalesce(sa_func.sum(DefectRecord.quantity), 0)
    ).filter(
        DefectRecord.factory_id == factory_id,
        DefectRecord.date == yesterday,
    ).scalar()

    # Total pieces that changed status yesterday (rough: positions updated yesterday)
    # Use position status changes as proxy for processed pieces
    processed_count = db.query(
        sa_func.coalesce(sa_func.sum(OrderPosition.quantity), 0)
    ).filter(
        OrderPosition.factory_id == factory_id,
        sa_func.date(OrderPosition.updated_at) == yesterday,
        OrderPosition.status.in_([
            PositionStatus.GLAZED.value,
            PositionStatus.FIRED.value,
            PositionStatus.TRANSFERRED_TO_SORTING.value,
            PositionStatus.PACKED.value,
        ]),
    ).scalar()

    defect_rate = 0.0
    processed = int(processed_count or 0)
    defects = int(defect_count or 0)
    if processed > 0:
        defect_rate = round((defects / processed) * 100, 1)

    # Kiln utilization: batches done yesterday / total kiln slots yesterday
    batches_done = db.query(sa_func.count(Batch.id)).filter(
        Batch.factory_id == factory_id,
        Batch.status == BatchStatus.DONE.value,
        Batch.batch_date == yesterday,
    ).scalar() or 0

    total_kilns = db.query(sa_func.count(Resource.id)).filter(
        Resource.factory_id == factory_id,
        Resource.resource_type == ResourceType.KILN.value,
        Resource.is_active.is_(True),
    ).scalar() or 1

    kiln_utilization = round((batches_done / max(total_kilns, 1)) * 100, 1)

    # Orders completed yesterday
    orders_completed = db.query(sa_func.count(ProductionOrder.id)).filter(
        ProductionOrder.factory_id == factory_id,
        ProductionOrder.status == OrderStatus.READY_FOR_SHIPMENT.value,
        sa_func.date(ProductionOrder.updated_at) == yesterday,
    ).scalar() or 0

    return {
        "defect_rate": defect_rate,
        "defect_count": defects,
        "pieces_processed": processed,
        "kiln_utilization": kiln_utilization,
        "batches_done": batches_done,
        "orders_completed": int(orders_completed),
    }


# ────────────────────────────────────────────────────────────────
# §6  Persistence
# ────────────────────────────────────────────────────────────────

def _save_distribution_record(
    db: Session,
    factory_id: UUID,
    distribution_date: date,
    distribution: dict,
) -> None:
    """Save or update the daily distribution record."""
    existing = db.query(DailyTaskDistribution).filter(
        DailyTaskDistribution.factory_id == factory_id,
        DailyTaskDistribution.distribution_date == distribution_date,
    ).first()

    extra_json = {
        "kiln_prep_tasks": distribution.get("kiln_prep_tasks"),
        "urgent_alerts": distribution.get("urgent_alerts"),
        "kpi_yesterday": distribution.get("kpi_yesterday"),
        "total_positions": distribution.get("total_positions"),
        "urgent_count": distribution.get("urgent_count"),
    }

    if existing:
        existing.glazing_tasks_json = distribution.get("glazing_tasks")
        existing.kiln_loading_json = distribution.get("kiln_loading")
        existing.glaze_recipes_json = extra_json
        existing.sent_at = datetime.utcnow()
        existing.sent_to_chat = True
    else:
        record = DailyTaskDistribution(
            factory_id=factory_id,
            distribution_date=distribution_date,
            glazing_tasks_json=distribution.get("glazing_tasks"),
            kiln_loading_json=distribution.get("kiln_loading"),
            glaze_recipes_json=extra_json,
            sent_at=datetime.utcnow(),
            sent_to_chat=True,
        )
        db.add(record)

    try:
        db.commit()
    except Exception as e:
        logger.error("Failed to save distribution record: %s", e)
        db.rollback()


def _update_distribution_message_id(
    db: Session,
    factory_id: UUID,
    distribution_date: date,
    message_id: int,
) -> None:
    """Store the Telegram message_id on the distribution record for future edits."""
    record = db.query(DailyTaskDistribution).filter(
        DailyTaskDistribution.factory_id == factory_id,
        DailyTaskDistribution.distribution_date == distribution_date,
    ).first()
    if record:
        record.message_id = message_id
        try:
            db.commit()
        except Exception as e:
            logger.error("Failed to update distribution message_id: %s", e)
            db.rollback()


# ────────────────────────────────────────────────────────────────
# §7  Message formatting
# ────────────────────────────────────────────────────────────────

def format_daily_message(distribution: dict, language: str = "id") -> str:
    """Format distribution as Telegram message.

    Language: 'id' = Indonesian (default), 'en' = English, 'ru' = Russian.
    """
    if language == "en":
        return _format_message_en(distribution)
    elif language == "ru":
        return _format_message_ru(distribution)
    else:
        return _format_message_id(distribution)


def _format_message_id(distribution: dict) -> str:
    """Format daily message in Indonesian.

    Produces a structured Telegram message with sections for glazing tasks,
    kiln preparation, kiln loading batches, urgent alerts, and KPI.
    """
    dist_date = distribution.get("distribution_date", "")
    factory_name = distribution.get("factory_name", "")
    total_positions = distribution.get("total_positions", 0)
    urgent_count = distribution.get("urgent_count", 0)
    separator = "\u2501" * 20  # ━━━━━━━━━━━━━━━━━━━━

    lines = [
        f"\U0001f4cb *TUGAS BESOK \u2014 {dist_date}*",
        f"\U0001f3ed Pabrik: {factory_name}",
    ]

    # ── Glazing section ──
    glazing = distribution.get("glazing_tasks", [])
    if glazing:
        lines.append(f"\n\U0001f3a8 *GLASIR ({len(glazing)} posisi)*")
        lines.append(separator)
        for i, task in enumerate(glazing, 1):
            pos_label = task.get("position_label", task.get("position_number", 0))
            behind = " \u26a0\ufe0f" if task.get("behind_schedule") else ""
            lines.append(f"{i}. Order #{task['order_number']} Pos #{pos_label}{behind}")
            color_str = task["color"]
            if task.get("color_2"):
                color_str += f" / {task['color_2']}"
            lines.append(f"   \u2022 Warna: {color_str} | Ukuran: {task['size']}")
            lines.append(f"   \u2022 Jumlah: {task['quantity']} pcs")
            lines.append(f"   \u2022 Resep: {task['recipe_name']}")
            consumption = task.get("consumption_info", "")
            if consumption:
                lines.append(f"   \u2022 Glasir: {consumption}")
            # Board info for workers
            bi = task.get("board_info")
            if bi:
                board_type = "standar" if bi["is_standard"] else f"khusus {bi['board_size']} cm"
                lines.append(f"   \U0001f4d0 Papan: {board_type} | {bi['tiles_per_board']} pcs/papan")
                if bi.get("ml_per_2boards"):
                    lines.append(f"   \U0001f4a7 Glasir: {bi['ml_per_2boards']} ml / 2 papan ({bi['area_per_2boards_m2']:.2f} m\u00b2)")
            if i < len(glazing):
                lines.append("")  # blank line between items
    else:
        lines.append(f"\n\U0001f3a8 *GLASIR*: tidak ada tugas")

    # ── Kiln prep section ──
    kiln_prep = distribution.get("kiln_prep_tasks", [])
    if kiln_prep:
        lines.append(f"\n\U0001f525 *PERSIAPAN KILN ({len(kiln_prep)} posisi)*")
        lines.append(separator)
        for i, task in enumerate(kiln_prep, 1):
            pos_label = task.get("position_label", task.get("position_number", 0))
            behind = " \u26a0\ufe0f" if task.get("behind_schedule") else ""
            lines.append(f"{i}. Order #{task['order_number']} Pos #{pos_label}{behind}")
            lines.append(f"   \u2022 Warna: {task['color']} | Ukuran: {task['size']}")
            lines.append(f"   \u2022 Jumlah: {task['quantity']} pcs")
            lines.append(f"   \u2022 Status: siap muat")
            if i < len(kiln_prep):
                lines.append("")

    # ── Kiln loading section ──
    kiln = distribution.get("kiln_loading", [])
    if kiln:
        lines.append(f"\n\U0001f3ed *PEMUATAN TUNGKU ({len(kiln)} batch)*")
        lines.append(separator)
        for batch in kiln:
            duration_str = f"{batch['duration_hours']}j" if batch.get("duration_hours") else "TBD"
            lines.append(
                f"\u2022 {batch['kiln_name']}: "
                f"{batch['positions_count']} posisi, "
                f"{batch['temperature']}\u00b0C, {duration_str}"
            )
            # Show individual positions in the batch
            for pos in batch.get("positions", []):
                lines.append(f"  \u2514 {pos['order_number']} | {pos['color']} {pos['size']} ({pos['quantity']} pcs)")

    # ── Urgent alerts ──
    urgent = distribution.get("urgent_alerts", [])
    if urgent:
        lines.append(f"\n\u26a0\ufe0f *MENDESAK ({len(urgent)})*")
        for alert in urgent:
            lines.append(f"\u2022 {alert['order']} \u2014 {alert['message']}")

    # ── Urgent positions behind schedule ──
    if urgent_count > 0:
        lines.append(f"\n\u26a0\ufe0f *MENDESAK: {urgent_count} posisi terlambat!*")

    # ── KPI ──
    kpi = distribution.get("kpi_yesterday", {})
    if kpi:
        lines.append("")
        lines.append(
            f"\U0001f4ca KPI kemarin: "
            f"{kpi.get('defect_rate', 0):.1f}% cacat "
            f"({kpi.get('defect_count', 0)} pcs dari {kpi.get('pieces_processed', 0)}) | "
            f"Tungku {kpi.get('kiln_utilization', 0):.0f}% | "
            f"{kpi.get('orders_completed', 0)} pesanan selesai"
        )

    # ── Summary line ──
    lines.append(f"\n\U0001f4ca Total: {total_positions} posisi untuk besok")

    return "\n".join(lines)


def _format_message_en(distribution: dict) -> str:
    """Format daily message in English."""
    dist_date = distribution.get("distribution_date", "")
    factory_name = distribution.get("factory_name", "")
    total_positions = distribution.get("total_positions", 0)
    urgent_count = distribution.get("urgent_count", 0)
    separator = "\u2501" * 20

    lines = [
        f"\U0001f4cb *TASKS FOR TOMORROW \u2014 {dist_date}*",
        f"\U0001f3ed Factory: {factory_name}",
    ]

    # Glazing section
    glazing = distribution.get("glazing_tasks", [])
    if glazing:
        lines.append(f"\n\U0001f3a8 *GLAZING ({len(glazing)} positions)*")
        lines.append(separator)
        for i, task in enumerate(glazing, 1):
            pos_label = task.get("position_label", task.get("position_number", 0))
            behind = " \u26a0\ufe0f" if task.get("behind_schedule") else ""
            lines.append(f"{i}. Order #{task['order_number']} Pos #{pos_label}{behind}")
            color_str = task["color"]
            if task.get("color_2"):
                color_str += f" / {task['color_2']}"
            lines.append(f"   \u2022 Color: {color_str} | Size: {task['size']}")
            lines.append(f"   \u2022 Qty: {task['quantity']} pcs")
            lines.append(f"   \u2022 Recipe: {task['recipe_name']}")
            consumption = task.get("consumption_info", "")
            if consumption:
                lines.append(f"   \u2022 Glaze: {consumption}")
            bi = task.get("board_info")
            if bi:
                board_type = "standard" if bi["is_standard"] else f"custom {bi['board_size']} cm"
                lines.append(f"   \U0001f4d0 Board: {board_type} | {bi['tiles_per_board']} pcs/board")
                if bi.get("ml_per_2boards"):
                    lines.append(f"   \U0001f4a7 Glaze: {bi['ml_per_2boards']} ml / 2 boards ({bi['area_per_2boards_m2']:.2f} m\u00b2)")
            if i < len(glazing):
                lines.append("")
    else:
        lines.append(f"\n\U0001f3a8 *GLAZING*: no tasks")

    # Kiln prep section
    kiln_prep = distribution.get("kiln_prep_tasks", [])
    if kiln_prep:
        lines.append(f"\n\U0001f525 *KILN PREPARATION ({len(kiln_prep)} positions)*")
        lines.append(separator)
        for i, task in enumerate(kiln_prep, 1):
            pos_label = task.get("position_label", task.get("position_number", 0))
            behind = " \u26a0\ufe0f" if task.get("behind_schedule") else ""
            lines.append(f"{i}. Order #{task['order_number']} Pos #{pos_label}{behind}")
            lines.append(f"   \u2022 Color: {task['color']} | Size: {task['size']}")
            lines.append(f"   \u2022 Qty: {task['quantity']} pcs")
            lines.append(f"   \u2022 Status: ready to load")
            if i < len(kiln_prep):
                lines.append("")

    # Kiln loading section
    kiln = distribution.get("kiln_loading", [])
    if kiln:
        lines.append(f"\n\U0001f3ed *KILN LOADING ({len(kiln)} batches)*")
        lines.append(separator)
        for batch in kiln:
            duration_str = f"{batch['duration_hours']}h" if batch.get("duration_hours") else "TBD"
            lines.append(
                f"\u2022 {batch['kiln_name']}: "
                f"{batch['positions_count']} positions, "
                f"{batch['temperature']}\u00b0C, {duration_str}"
            )
            for pos in batch.get("positions", []):
                lines.append(f"  \u2514 {pos['order_number']} | {pos['color']} {pos['size']} ({pos['quantity']} pcs)")

    # Urgent alerts
    urgent = distribution.get("urgent_alerts", [])
    if urgent:
        lines.append(f"\n\u26a0\ufe0f *URGENT ({len(urgent)})*")
        for alert in urgent:
            lines.append(f"\u2022 {alert['order']} \u2014 {alert['message']}")

    if urgent_count > 0:
        lines.append(f"\n\u26a0\ufe0f *URGENT: {urgent_count} positions behind schedule!*")

    # KPI
    kpi = distribution.get("kpi_yesterday", {})
    if kpi:
        lines.append("")
        lines.append(
            f"\U0001f4ca Yesterday's KPI: "
            f"{kpi.get('defect_rate', 0):.1f}% defect "
            f"({kpi.get('defect_count', 0)} pcs of {kpi.get('pieces_processed', 0)}) | "
            f"Kiln {kpi.get('kiln_utilization', 0):.0f}% | "
            f"{kpi.get('orders_completed', 0)} orders completed"
        )

    lines.append(f"\n\U0001f4ca Total: {total_positions} positions for tomorrow")

    return "\n".join(lines)


def _format_message_ru(distribution: dict) -> str:
    """Format daily message in Russian."""
    dist_date = distribution.get("distribution_date", "")
    factory_name = distribution.get("factory_name", "")
    total_positions = distribution.get("total_positions", 0)
    urgent_count = distribution.get("urgent_count", 0)
    separator = "\u2501" * 20

    lines = [
        f"\U0001f4cb *\u0417\u0410\u0414\u0410\u0427\u0418 \u041d\u0410 \u0417\u0410\u0412\u0422\u0420\u0410 \u2014 {dist_date}*",
        f"\U0001f3ed \u0424\u0430\u0431\u0440\u0438\u043a\u0430: {factory_name}",
    ]

    # Glazing section
    glazing = distribution.get("glazing_tasks", [])
    if glazing:
        lines.append(f"\n\U0001f3a8 *\u0413\u041b\u0410\u0417\u0423\u0420\u041e\u0412\u041a\u0410 ({len(glazing)} \u043f\u043e\u0437\u0438\u0446\u0438\u0439)*")
        lines.append(separator)
        for i, task in enumerate(glazing, 1):
            pos_label = task.get("position_label", task.get("position_number", 0))
            behind = " \u26a0\ufe0f" if task.get("behind_schedule") else ""
            lines.append(f"{i}. \u0417\u0430\u043a\u0430\u0437 #{task['order_number']} \u041f\u043e\u0437 #{pos_label}{behind}")
            color_str = task["color"]
            if task.get("color_2"):
                color_str += f" / {task['color_2']}"
            lines.append(f"   \u2022 \u0426\u0432\u0435\u0442: {color_str} | \u0420\u0430\u0437\u043c\u0435\u0440: {task['size']}")
            lines.append(f"   \u2022 \u041a\u043e\u043b-\u0432\u043e: {task['quantity']} \u0448\u0442")
            lines.append(f"   \u2022 \u0420\u0435\u0446\u0435\u043f\u0442: {task['recipe_name']}")
            consumption = task.get("consumption_info", "")
            if consumption:
                lines.append(f"   \u2022 \u0413\u043b\u0430\u0437\u0443\u0440\u044c: {consumption}")
            bi = task.get("board_info")
            if bi:
                board_type = "\u0441\u0442\u0430\u043d\u0434\u0430\u0440\u0442" if bi["is_standard"] else f"\u043a\u0430\u0441\u0442\u043e\u043c {bi['board_size']} \u0441\u043c"
                lines.append(f"   \U0001f4d0 \u0414\u043e\u0441\u043a\u0430: {board_type} | {bi['tiles_per_board']} \u0448\u0442/\u0434\u043e\u0441\u043a\u0443")
                if bi.get("ml_per_2boards"):
                    lines.append(f"   \U0001f4a7 \u0420\u0430\u0441\u0445\u043e\u0434: {bi['ml_per_2boards']} \u043c\u043b / 2 \u0434\u043e\u0441\u043a\u0438 ({bi['area_per_2boards_m2']:.2f} \u043c\u00b2)")
            if i < len(glazing):
                lines.append("")
    else:
        lines.append(f"\n\U0001f3a8 *\u0413\u041b\u0410\u0417\u0423\u0420\u041e\u0412\u041a\u0410*: \u043d\u0435\u0442 \u0437\u0430\u0434\u0430\u0447")

    # Kiln prep section
    kiln_prep = distribution.get("kiln_prep_tasks", [])
    if kiln_prep:
        lines.append(f"\n\U0001f525 *\u041f\u041e\u0414\u0413\u041e\u0422\u041e\u0412\u041a\u0410 \u041a \u041f\u0415\u0427\u0418 ({len(kiln_prep)} \u043f\u043e\u0437\u0438\u0446\u0438\u0439)*")
        lines.append(separator)
        for i, task in enumerate(kiln_prep, 1):
            pos_label = task.get("position_label", task.get("position_number", 0))
            behind = " \u26a0\ufe0f" if task.get("behind_schedule") else ""
            lines.append(f"{i}. \u0417\u0430\u043a\u0430\u0437 #{task['order_number']} \u041f\u043e\u0437 #{pos_label}{behind}")
            lines.append(f"   \u2022 \u0426\u0432\u0435\u0442: {task['color']} | \u0420\u0430\u0437\u043c\u0435\u0440: {task['size']}")
            lines.append(f"   \u2022 \u041a\u043e\u043b-\u0432\u043e: {task['quantity']} \u0448\u0442")
            lines.append(f"   \u2022 \u0421\u0442\u0430\u0442\u0443\u0441: \u0433\u043e\u0442\u043e\u0432\u043e \u043a \u0437\u0430\u0433\u0440\u0443\u0437\u043a\u0435")
            if i < len(kiln_prep):
                lines.append("")

    # Kiln loading section
    kiln = distribution.get("kiln_loading", [])
    if kiln:
        lines.append(f"\n\U0001f3ed *\u0417\u0410\u0413\u0420\u0423\u0417\u041a\u0410 \u041f\u0415\u0427\u0415\u0419 ({len(kiln)} \u043f\u0430\u0440\u0442\u0438\u0439)*")
        lines.append(separator)
        for batch in kiln:
            duration_str = f"{batch['duration_hours']}\u0447" if batch.get("duration_hours") else "TBD"
            lines.append(
                f"\u2022 {batch['kiln_name']}: "
                f"{batch['positions_count']} \u043f\u043e\u0437\u0438\u0446\u0438\u0439, "
                f"{batch['temperature']}\u00b0C, {duration_str}"
            )
            for pos in batch.get("positions", []):
                lines.append(f"  \u2514 {pos['order_number']} | {pos['color']} {pos['size']} ({pos['quantity']} \u0448\u0442)")

    # Urgent alerts
    urgent = distribution.get("urgent_alerts", [])
    if urgent:
        lines.append(f"\n\u26a0\ufe0f *\u0421\u0420\u041e\u0427\u041d\u041e ({len(urgent)})*")
        for alert in urgent:
            lines.append(f"\u2022 {alert['order']} \u2014 {alert['message']}")

    if urgent_count > 0:
        lines.append(f"\n\u26a0\ufe0f *\u0421\u0420\u041e\u0427\u041d\u041e: {urgent_count} \u043f\u043e\u0437\u0438\u0446\u0438\u0439 \u0441 \u043e\u043f\u043e\u0437\u0434\u0430\u043d\u0438\u0435\u043c!*")

    # KPI
    kpi = distribution.get("kpi_yesterday", {})
    if kpi:
        lines.append("")
        lines.append(
            f"\U0001f4ca KPI \u0432\u0447\u0435\u0440\u0430: "
            f"{kpi.get('defect_rate', 0):.1f}% \u0431\u0440\u0430\u043a "
            f"({kpi.get('defect_count', 0)} \u0448\u0442 \u0438\u0437 {kpi.get('pieces_processed', 0)}) | "
            f"\u041f\u0435\u0447\u044c {kpi.get('kiln_utilization', 0):.0f}% | "
            f"{kpi.get('orders_completed', 0)} \u0437\u0430\u043a\u0430\u0437\u043e\u0432 \u0433\u043e\u0442\u043e\u0432\u043e"
        )

    lines.append(f"\n\U0001f4ca \u0418\u0442\u043e\u0433\u043e: {total_positions} \u043f\u043e\u0437\u0438\u0446\u0438\u0439 \u043d\u0430 \u0437\u0430\u0432\u0442\u0440\u0430")

    return "\n".join(lines)
