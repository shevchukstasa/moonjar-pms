"""
Daily Task Distribution service.
Business Logic: §11, §34

Generates today's task list per factory (morning briefing), formats as Telegram message,
sends to masters group chat, and saves record to daily_task_distributions table.
"""
from uuid import UUID
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
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
    MaterialStock,
    Material,
    UserStreak,
    DailyChallenge,
    AuditLog,
    User,
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
from business.services.notifications import send_telegram_message, send_telegram_message_with_buttons, get_forum_topic

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

# Statuses for sorting section
SORTING_ELIGIBLE_STATUSES = [
    PositionStatus.TRANSFERRED_TO_SORTING.value,
    PositionStatus.FIRED.value,
]

# Statuses for QC section
QC_ELIGIBLE_STATUSES = [
    PositionStatus.SENT_TO_QUALITY_CHECK.value,
    PositionStatus.QUALITY_CHECK_DONE.value,
    PositionStatus.BLOCKED_BY_QM.value,
]

SEPARATOR = "──────────────────────────"


# ────────────────────────────────────────────────────────────────
# §1  Main entry point
# ────────────────────────────────────────────────────────────────

def daily_task_distribution(db: Session, factory_id: UUID) -> dict:
    """Generate today's task distribution for a factory (morning briefing).

    1. Collects glazing positions eligible for today
    2. Collects planned kiln batches for today
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

    target_date = date.today()
    yesterday = target_date - timedelta(days=1)

    # --- Build distribution ---
    glazing_tasks = _collect_glazing_tasks(db, factory_id, target_date)
    kiln_prep_tasks = _collect_kiln_prep_tasks(db, factory_id, target_date)
    kiln_loading = _collect_kiln_loading(db, factory_id, target_date)
    sorting_tasks = _collect_sorting_tasks(db, factory_id, target_date)
    qc_tasks = _collect_qc_tasks(db, factory_id, target_date)
    urgent_alerts = _collect_urgent_alerts(db, factory_id)
    stock_alerts = _collect_stock_alerts(db, factory_id)
    material_blocked = _collect_material_blocked(db, factory_id, target_date)
    top_performer = _collect_top_performer(db, factory_id, yesterday)
    streak_data = _collect_streak_data(db, factory_id)
    daily_challenge = _collect_daily_challenge(db, factory_id, target_date)

    # Count urgent (behind schedule) positions
    urgent_count = sum(
        1 for t in glazing_tasks
        if t.get("behind_schedule")
    ) + sum(
        1 for t in kiln_prep_tasks
        if t.get("behind_schedule")
    )

    total_positions = len(glazing_tasks) + len(kiln_prep_tasks) + len(sorting_tasks) + len(qc_tasks)

    distribution = {
        "factory_id": str(factory_id),
        "factory_name": factory.name,
        "distribution_date": target_date.isoformat(),
        "glazing_tasks": glazing_tasks,
        "kiln_prep_tasks": kiln_prep_tasks,
        "kiln_loading": kiln_loading,
        "sorting_tasks": sorting_tasks,
        "qc_tasks": qc_tasks,
        "urgent_alerts": urgent_alerts,
        "stock_alerts": stock_alerts,
        "material_blocked": material_blocked,
        "top_performer": top_performer,
        "streak": streak_data,
        "daily_challenge": daily_challenge,
        "kpi_yesterday": _compute_kpi_yesterday(db, factory_id),
        "total_positions": total_positions,
        "urgent_count": urgent_count,
    }

    # --- Persist to daily_task_distributions ---
    _save_distribution_record(db, factory_id, target_date, distribution)

    # --- Send Telegram message with inline buttons ---
    language = factory.telegram_language or "id"
    if factory.masters_group_chat_id:
        message = format_daily_message(distribution, language)

        # ── AI: Append smart daily insight ────────────────────────
        try:
            import asyncio
            from business.services.telegram_ai import generate_smart_daily_message
            coro = generate_smart_daily_message(
                factory_name=factory.name,
                glazing_tasks=distribution.get("glazing_tasks", []),
                kiln_tasks=distribution.get("kiln_loading", []),
                sorting_tasks=[],
                kpi_data=distribution.get("kpi_yesterday", {}),
                language=language,
            )
            # Handle both sync and async calling contexts
            try:
                loop = asyncio.get_running_loop()
                # Already in an async context — schedule as a task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    ai_insight = loop.run_in_executor(
                        pool, asyncio.run, coro
                    )
                    # Can't easily await here in sync code; skip AI
                    ai_insight = None
            except RuntimeError:
                # No running loop — safe to use asyncio.run
                ai_insight = asyncio.run(coro)
            if ai_insight:
                message += f"\n\n\U0001f9e0 *Insight:*\n{ai_insight}"
        except Exception as e:
            logger.warning("AI daily insight failed (non-fatal): %s", e)
        chat_id = str(factory.masters_group_chat_id)
        date_str = target_date.isoformat()
        fid = str(factory_id)

        # Compact callback_data (must be <= 64 bytes):
        #   d:a — acknowledge, d:d — details, d:p — problem
        #   d:s — my stats, d:l — leaderboard, d:k — stock check
        # Use short UUID (first 8 chars) to save bytes
        fid_short = fid[:8]
        inline_keyboard = [
            [
                {"text": "\u2705 Start Day", "callback_data": f"d:a:{fid_short}:{date_str}"},
                {"text": "\U0001f4cb Details", "callback_data": f"d:d:{fid_short}:{date_str}"},
                {"text": "\u26a0\ufe0f Problem", "callback_data": f"d:p:{fid_short}:{date_str}"},
            ],
            [
                {"text": "\U0001f4ca My Stats", "callback_data": f"d:s:{fid_short}:{date_str}"},
                {"text": "\U0001f3c6 Leaders", "callback_data": f"d:l:{fid_short}:{date_str}"},
                {"text": "\U0001f4e6 Stock", "callback_data": f"d:k:{fid_short}:{date_str}"},
            ],
        ]

        try:
            result = send_telegram_message_with_buttons(chat_id, message, inline_keyboard)
            telegram_message_id = None
            if result:
                telegram_message_id = result.get("message_id")
            # Store message_id on the distribution record
            if telegram_message_id:
                _update_distribution_message_id(db, factory_id, target_date, telegram_message_id)
            logger.info(
                "Daily distribution sent to factory %s (chat %s, msg_id=%s)",
                factory.name, factory.masters_group_chat_id, telegram_message_id,
            )
        except Exception as e:
            logger.error(
                "Failed to send daily distribution for factory %s: %s",
                factory.name, e,
            )

        # ── Forum topic routing (additional, non-blocking) ────────
        try:
            # Daily briefing → #daily-briefing topic
            forum_group, daily_topic = get_forum_topic("daily")
            if forum_group:
                send_telegram_message_with_buttons(
                    str(forum_group), message, inline_keyboard,
                    message_thread_id=daily_topic,
                )

            # Stock alerts → #materials topic (dedicated message)
            if stock_alerts:
                forum_group_m, materials_topic = get_forum_topic("materials")
                if forum_group_m:
                    stock_lines = [f"\U0001f4e6 *Stock Alerts — {factory.name}* ({target_date.isoformat()})"]
                    for sa in stock_alerts:
                        stock_lines.append(
                            f"  \U0001f7e1 {sa['material_name']}: "
                            f"{sa['balance']:.1f} {sa['unit']} "
                            f"(min {sa['min_balance']:.0f})"
                        )
                    send_telegram_message(
                        str(forum_group_m), "\n".join(stock_lines),
                        message_thread_id=materials_topic,
                    )
        except Exception as e:
            logger.warning("Forum topic routing failed (non-fatal): %s", e)
    else:
        logger.warning(
            "Factory %s has no masters_group_chat_id, skipping Telegram",
            factory.name,
        )

    return distribution


# ────────────────────────────────────────────────────────────────
# §2  Glazing tasks collection
# ────────────────────────────────────────────────────────────────

def get_glazing_positions_for_tomorrow(db: Session, factory_id: UUID, target_date: Optional[date] = None) -> list:
    """Get positions eligible for glazing, filtered through TOC rope limit.

    Filters:
      - Status in GLAZING_ELIGIBLE_STATUSES (planned, sent_to_glazing,
        engobe_applied, engobe_check)
      - planned_glazing_date <= target_date (due or overdue for glazing)
      - Order is in active production
      - Not cancelled / not shipped

    Returns list of OrderPosition objects ready for glazing work.
    """
    from sqlalchemy import or_

    if target_date is None:
        target_date = date.today()

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
            # Position is scheduled for glazing by target_date or has no date
            # (unscheduled positions are included so they don't get lost)
            or_(
                OrderPosition.planned_glazing_date <= target_date,
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
    """Build glazing task list for the target date."""
    positions = get_glazing_positions_for_tomorrow(db, factory_id, target_date)
    tasks = []

    for pos in positions:
        order = pos.order
        recipe = pos.recipe
        # Fallback: if recipe_id is set but relationship not loaded, query directly
        if recipe is None and pos.recipe_id:
            recipe = db.query(Recipe).filter(Recipe.id == pos.recipe_id).first()

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
    for kiln loading by the target date.
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
    """Collect planned kiln batches for the target date."""
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
        if not order and task.related_position_id:
            pos = db.query(OrderPosition).filter(OrderPosition.id == task.related_position_id).first()
            if pos:
                order = db.query(ProductionOrder).filter(ProductionOrder.id == pos.order_id).first()
        order_num = order.order_number if order else f"Task #{str(task.id)[:8]}"
        task_label = task.type.replace("_", " ").title() if isinstance(task.type, str) else task.type.value.replace("_", " ").title()
        alerts.append({
            "order": order_num,
            "message": f"Blocking: {task_label} pending",
            "deadline": None,
            "days_overdue": 0,
        })

    return alerts


# ────────────────────────────────────────────────────────────────
# §4b  Sorting tasks collection
# ────────────────────────────────────────────────────────────────

def _collect_sorting_tasks(db: Session, factory_id: UUID, target_date: date) -> list:
    """Collect positions ready for sorting (fired / transferred to sorting)."""
    positions = (
        db.query(OrderPosition)
        .join(ProductionOrder, OrderPosition.order_id == ProductionOrder.id)
        .filter(
            OrderPosition.factory_id == factory_id,
            OrderPosition.status.in_(SORTING_ELIGIBLE_STATUSES),
            ProductionOrder.status.in_([
                OrderStatus.IN_PRODUCTION.value,
                OrderStatus.PARTIALLY_READY.value,
            ]),
        )
        .order_by(
            OrderPosition.priority_order.desc(),
            ProductionOrder.final_deadline.asc().nullslast(),
        )
        .all()
    )
    tasks = []
    for pos in positions:
        order = pos.order
        tasks.append({
            "position_id": str(pos.id),
            "order_number": order.order_number if order else "???",
            "color": pos.color or "",
            "size": pos.size or "",
            "quantity": pos.quantity,
        })
    return tasks


# ────────────────────────────────────────────────────────────────
# §4c  QC tasks collection
# ────────────────────────────────────────────────────────────────

def _collect_qc_tasks(db: Session, factory_id: UUID, target_date: date) -> list:
    """Collect positions in quality check statuses."""
    positions = (
        db.query(OrderPosition)
        .join(ProductionOrder, OrderPosition.order_id == ProductionOrder.id)
        .filter(
            OrderPosition.factory_id == factory_id,
            OrderPosition.status.in_(QC_ELIGIBLE_STATUSES),
            ProductionOrder.status.in_([
                OrderStatus.IN_PRODUCTION.value,
                OrderStatus.PARTIALLY_READY.value,
            ]),
        )
        .order_by(
            OrderPosition.priority_order.desc(),
            ProductionOrder.final_deadline.asc().nullslast(),
        )
        .all()
    )
    tasks = []
    for pos in positions:
        order = pos.order
        tasks.append({
            "position_id": str(pos.id),
            "order_number": order.order_number if order else "???",
            "color": pos.color or "",
            "size": pos.size or "",
            "quantity": pos.quantity,
            "status": pos.status if isinstance(pos.status, str) else pos.status.value,
        })
    return tasks


# ────────────────────────────────────────────────────────────────
# §4d  Stock alerts (materials below min_balance)
# ────────────────────────────────────────────────────────────────

def _collect_stock_alerts(db: Session, factory_id: UUID) -> list:
    """Find materials where current balance < min_balance for the factory."""
    try:
        low_stock = (
            db.query(MaterialStock, Material)
            .join(Material, MaterialStock.material_id == Material.id)
            .filter(
                MaterialStock.factory_id == factory_id,
                MaterialStock.min_balance > 0,
                MaterialStock.balance < MaterialStock.min_balance,
            )
            .order_by(
                (MaterialStock.balance / MaterialStock.min_balance).asc(),
            )
            .limit(10)
            .all()
        )
        alerts = []
        for stock, material in low_stock:
            alerts.append({
                "material_name": material.name,
                "balance": float(stock.balance),
                "min_balance": float(stock.min_balance),
                "unit": material.unit,
            })
        return alerts
    except Exception as e:
        logger.warning("Stock alerts collection failed: %s", e)
        return []


# ────────────────────────────────────────────────────────────────
# §4d2  Material-blocked positions needing glazing within 3 days
# ────────────────────────────────────────────────────────────────

def _collect_material_blocked(db: Session, factory_id: UUID, target_date: date) -> list:
    """Find positions with INSUFFICIENT_MATERIALS that have glazing within 3 days."""
    try:
        horizon = target_date + timedelta(days=3)
        blocked = (
            db.query(OrderPosition)
            .join(ProductionOrder, OrderPosition.order_id == ProductionOrder.id)
            .filter(
                OrderPosition.factory_id == factory_id,
                OrderPosition.status == PositionStatus.INSUFFICIENT_MATERIALS.value,
                OrderPosition.planned_glazing_date.isnot(None),
                OrderPosition.planned_glazing_date >= target_date,
                OrderPosition.planned_glazing_date <= horizon,
            )
            .order_by(OrderPosition.planned_glazing_date.asc())
            .all()
        )
        results = []
        for pos in blocked:
            results.append({
                "position_number": pos.position_number or str(pos.id)[:8],
                "order_number": pos.order.order_number if pos.order else "?",
                "planned_glazing_date": pos.planned_glazing_date.isoformat() if pos.planned_glazing_date else "",
                "planned_glazing_display": pos.planned_glazing_date.strftime("%b %d") if pos.planned_glazing_date else "",
            })
        return results
    except Exception as e:
        logger.warning("Material blocked collection failed: %s", e)
        return []


# ────────────────────────────────────────────────────────────────
# §4e  Top performer (who processed most positions yesterday)
# ────────────────────────────────────────────────────────────────

def _collect_top_performer(db: Session, factory_id: UUID, yesterday: date) -> Optional[dict]:
    """Find the user who processed most position status changes yesterday."""
    try:
        # Query audit_logs for order_positions updates yesterday, group by user
        results = (
            db.query(
                AuditLog.user_id,
                sa_func.count(AuditLog.id).label("action_count"),
            )
            .filter(
                AuditLog.table_name == "order_positions",
                AuditLog.action == "UPDATE",
                AuditLog.user_id.isnot(None),
                sa_func.date(AuditLog.created_at) == yesterday,
            )
            .group_by(AuditLog.user_id)
            .order_by(sa_func.count(AuditLog.id).desc())
            .first()
        )
        if not results or not results.user_id:
            return None

        user = db.query(User).filter(User.id == results.user_id).first()
        if not user:
            return None

        return {
            "user_name": user.name,
            "action_count": results.action_count,
        }
    except Exception as e:
        logger.warning("Top performer collection failed: %s", e)
        return None


# ────────────────────────────────────────────────────────────────
# §4f  Streak data (factory-level zero defects streak)
# ────────────────────────────────────────────────────────────────

def _collect_streak_data(db: Session, factory_id: UUID) -> dict:
    """Get the factory's zero-defects streak from UserStreak model."""
    try:
        streak = (
            db.query(UserStreak)
            .filter(
                UserStreak.factory_id == factory_id,
                UserStreak.streak_type == "zero_defects",
            )
            .order_by(UserStreak.current_streak.desc())
            .first()
        )
        if streak:
            return {
                "zero_defects_days": streak.current_streak,
                "best_streak": streak.best_streak,
            }
    except Exception as e:
        logger.warning("Streak data collection failed: %s", e)
    return {"zero_defects_days": 0, "best_streak": 0}


# ────────────────────────────────────────────────────────────────
# §4g  Daily challenge
# ────────────────────────────────────────────────────────────────

def _collect_daily_challenge(db: Session, factory_id: UUID, target_date: date) -> Optional[dict]:
    """Get today's daily challenge for the factory (auto-creates if missing)."""
    try:
        from business.services.streaks import get_daily_challenge
        challenge_data = get_daily_challenge(db, factory_id, target_date)
        if challenge_data:
            return {
                "title": challenge_data["title"],
                "description": challenge_data["description"],
                "target_value": challenge_data["target_value"],
                "completed": challenge_data.get("completed", False),
                "bonus_points": 5,  # Standard daily challenge bonus
            }
    except Exception as e:
        logger.warning("Daily challenge collection failed: %s", e)
    return None


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

    # Kiln utilization: average fill percentage from completed batches yesterday
    done_batches = db.query(Batch).filter(
        Batch.factory_id == factory_id,
        Batch.status == BatchStatus.DONE.value,
        Batch.batch_date == yesterday,
    ).all()
    batches_done = len(done_batches)

    if done_batches:
        fill_pcts = []
        for b in done_batches:
            meta = b.metadata_json or {}
            pct = meta.get("kiln_utilization_pct")
            if pct is not None:
                fill_pcts.append(float(pct))
        kiln_utilization = round(sum(fill_pcts) / len(fill_pcts), 1) if fill_pcts else 0
    else:
        kiln_utilization = 0

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
        "sorting_tasks": distribution.get("sorting_tasks"),
        "qc_tasks": distribution.get("qc_tasks"),
        "urgent_alerts": distribution.get("urgent_alerts"),
        "stock_alerts": distribution.get("stock_alerts"),
        "top_performer": distribution.get("top_performer"),
        "streak": distribution.get("streak"),
        "daily_challenge": distribution.get("daily_challenge"),
        "kpi_yesterday": distribution.get("kpi_yesterday"),
        "total_positions": distribution.get("total_positions"),
        "urgent_count": distribution.get("urgent_count"),
    }

    if existing:
        existing.glazing_tasks_json = distribution.get("glazing_tasks")
        existing.kiln_loading_json = distribution.get("kiln_loading")
        existing.glaze_recipes_json = extra_json
        existing.sent_at = datetime.now(timezone.utc)
        existing.sent_to_chat = True
    else:
        record = DailyTaskDistribution(
            factory_id=factory_id,
            distribution_date=distribution_date,
            glazing_tasks_json=distribution.get("glazing_tasks"),
            kiln_loading_json=distribution.get("kiln_loading"),
            glaze_recipes_json=extra_json,
            sent_at=datetime.now(timezone.utc),
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
    """Format distribution as bilingual Telegram message (English + Indonesian).

    Always returns English first, then Indonesian.
    """
    en_msg = _format_message_en(distribution)
    id_msg = _format_message_id(distribution)
    separator = "\n\n" + "=" * 30 + "\n\U0001f1ee\U0001f1e9 Bahasa Indonesia:\n" + "=" * 30 + "\n\n"
    return en_msg + separator + id_msg


# ── Helper: quality emoji based on defect rate ──

def _quality_emoji_en(defect_rate: float, defect_count: int) -> str:
    """Return quality assessment string for English message."""
    if defect_count == 0:
        return "\U0001f525 PERFECT!"
    if defect_rate < 3.0:
        return "Good quality!"
    if defect_rate < 5.0:
        return "Acceptable"
    return "\u26a0\ufe0f Quality needs attention"


def _quality_emoji_id(defect_rate: float, defect_count: int) -> str:
    """Return quality assessment string for Indonesian message."""
    if defect_count == 0:
        return "\U0001f525 SEMPURNA!"
    if defect_rate < 3.0:
        return "Kualitas bagus!"
    if defect_rate < 5.0:
        return "Cukup baik"
    return "\u26a0\ufe0f Kualitas perlu perhatian"


def _mood_emoji(kpi: dict) -> str:
    """Return mood emoji based on yesterday's results.

    Good day (>10 pieces, <3% defects) = fire
    Average day (some work, <5% defects) = muscle
    Bad day (high defects or no work) = angry face
    """
    pieces = kpi.get("pieces_processed", 0)
    defect_rate = kpi.get("defect_rate", 0)
    if pieces > 0 and defect_rate < 3.0:
        return "\U0001f525"  # fire
    if pieces > 0 and defect_rate < 5.0:
        return "\U0001f4aa"  # muscle
    if pieces == 0:
        return "\U0001f4aa"  # no data — neutral
    return "\U0001f624"  # angry/determined


def _format_message_en(distribution: dict) -> str:
    """Format daily message in English — 7-block motivational format."""
    factory_name = distribution.get("factory_name", "")
    total_positions = distribution.get("total_positions", 0)
    kpi = distribution.get("kpi_yesterday", {})
    streak = distribution.get("streak", {})
    challenge = distribution.get("daily_challenge")
    lines = []

    # ═══════════════════════════════════════════════════════════
    # BLOCK 1: Greeting + Mood + Yesterday's Win + Streak
    # ═══════════════════════════════════════════════════════════
    mood = _mood_emoji(kpi)
    lines.append(f"{mood} *Good morning, {factory_name} team!*")

    pieces = kpi.get("pieces_processed", 0)
    defects = kpi.get("defect_count", 0)
    defect_rate = kpi.get("defect_rate", 0)
    if pieces > 0:
        quality_str = _quality_emoji_en(defect_rate, defects)
        lines.append(f"Yesterday: {pieces} positions completed, {defects} defects {quality_str}")
    else:
        lines.append("Yesterday: no production data")

    zero_streak = streak.get("zero_defects_days", 0)
    if zero_streak > 1:
        lines.append(f"Streak: {zero_streak} days zero defects! Keep going! \U0001f4aa")
    lines.append(SEPARATOR)

    # ═══════════════════════════════════════════════════════════
    # BLOCK 2: Daily Challenge + Bonus Points
    # ═══════════════════════════════════════════════════════════
    if challenge:
        bonus = challenge.get("bonus_points", 5)
        lines.append(f"\U0001f3af *Today's Challenge:* {challenge['title']}")
        if challenge.get("description"):
            lines.append(f"   {challenge['description']}")
        lines.append(f"   \U0001f4b0 Bonus: +{bonus} pts for completion!")
    else:
        if total_positions > 0:
            lines.append(f"\U0001f3af *Today's Challenge:* Complete all {total_positions} positions!")
    lines.append(SEPARATOR)

    # ═══════════════════════════════════════════════════════════
    # BLOCK 3: Today's Plan (compact)
    # ═══════════════════════════════════════════════════════════
    lines.append(f"\U0001f4cb *TODAY'S PLAN ({total_positions} positions)*")
    lines.append("")

    # ── Glazing ──
    glazing = distribution.get("glazing_tasks", [])
    if glazing:
        lines.append(f"\U0001f3a8 *GLAZING ({len(glazing)}):*")
        for i, task in enumerate(glazing, 1):
            behind = " \u26a0\ufe0f" if task.get("behind_schedule") else ""
            color_str = task["color"]
            if task.get("color_2"):
                color_str += f"/{task['color_2']}"
            consumption = task.get("consumption_info", "")
            cons_str = f" \u2014 {consumption}" if consumption else ""
            lines.append(
                f"  {i}. {color_str} {task['size']} "
                f"\u00d7{task['quantity']}{cons_str}{behind}"
            )
            # Board info (compact single line)
            bi = task.get("board_info")
            if bi and bi.get("ml_per_2boards"):
                board_type = "std" if bi["is_standard"] else f"{bi['board_size']}cm"
                lines.append(
                    f"     \U0001f4d0 {board_type} | {bi['tiles_per_board']}/board | "
                    f"{bi['ml_per_2boards']}ml/2boards"
                )
        lines.append("")

    # ── Kiln ──
    kiln = distribution.get("kiln_loading", [])
    kiln_prep = distribution.get("kiln_prep_tasks", [])
    if kiln or kiln_prep:
        batch_count = len(kiln) if kiln else 0
        prep_count = len(kiln_prep) if kiln_prep else 0
        header_parts = []
        if batch_count:
            header_parts.append(f"{batch_count} batch{'es' if batch_count > 1 else ''}")
        if prep_count:
            header_parts.append(f"{prep_count} prep")
        lines.append(f"\U0001f525 *KILN ({', '.join(header_parts)}):*")
        for batch in kiln:
            temp_str = f"{batch['temperature']}\u00b0C" if batch.get("temperature") else "TBD"
            lines.append(
                f"  \u2022 {batch['kiln_name']}: "
                f"{batch['positions_count']} pos, {temp_str}"
            )
        for task in kiln_prep:
            behind = " \u26a0\ufe0f" if task.get("behind_schedule") else ""
            lines.append(
                f"  \u2022 Prep: {task['color']} {task['size']} "
                f"\u00d7{task['quantity']}{behind}"
            )
        lines.append("")

    # ── Sorting ──
    sorting = distribution.get("sorting_tasks", [])
    if sorting:
        lines.append(f"\u2702\ufe0f *SORTING ({len(sorting)}):*")
        for task in sorting:
            lines.append(
                f"  \u2022 {task['color']} {task['size']} \u00d7{task['quantity']}"
            )
        lines.append("")

    # ── QC ──
    qc = distribution.get("qc_tasks", [])
    if qc:
        lines.append(f"\u2705 *QC ({len(qc)}):*")
        for task in qc:
            lines.append(
                f"  \u2022 {task['color']} \u00d7{task['quantity']}"
            )
        lines.append("")

    lines.append(SEPARATOR)

    # ═══════════════════════════════════════════════════════════
    # BLOCK 4: Alerts (only if any exist)
    # ═══════════════════════════════════════════════════════════
    urgent = distribution.get("urgent_alerts", [])
    stock_alerts = distribution.get("stock_alerts", [])
    mat_blocked = distribution.get("material_blocked", [])
    if urgent or stock_alerts or mat_blocked:
        lines.append("\u26a0\ufe0f *ATTENTION:*")
        if mat_blocked:
            lines.append("")
            lines.append("\u26a0\ufe0f *Material Blocked (need within 3 days):*")
            for mb in mat_blocked:
                lines.append(
                    f"  \u2022 Position {mb['position_number']} "
                    f"(Order #{mb['order_number']}) \u2014 glazing {mb['planned_glazing_display']}"
                )
            lines.append("")
        for alert in urgent:
            days = alert.get("days_overdue", 0)
            icon = "\U0001f534" if days > 0 else "\U0001f7e1"
            lines.append(f"  {icon} {alert['order']} \u2014 {alert['message']}")
        for sa in stock_alerts:
            lines.append(
                f"  \U0001f7e1 Low stock: {sa['material_name']} "
                f"({sa['balance']:.1f} {sa['unit']}, need {sa['min_balance']:.0f})"
            )
        lines.append(SEPARATOR)

    # ═══════════════════════════════════════════════════════════
    # BLOCK 5: Yesterday's Scorecard
    # ═══════════════════════════════════════════════════════════
    if pieces > 0:
        lines.append("\U0001f4ca *YESTERDAY:*")
        lines.append(f"  \u2705 Done: {pieces} positions")
        quality_label = _quality_emoji_en(defect_rate, defects)
        lines.append(f"  \U0001f3af Defects: {defect_rate:.1f}% \u2014 {quality_label}")
        kiln_util = kpi.get("kiln_utilization", 0)
        if kiln_util > 0:
            lines.append(f"  \U0001f525 Kiln fill: {kiln_util:.0f}%")
        orders_done = kpi.get("orders_completed", 0)
        if orders_done > 0:
            lines.append(f"  \U0001f4e6 Shipped: {orders_done} order{'s' if orders_done != 1 else ''}")
        lines.append(SEPARATOR)

    # ═══════════════════════════════════════════════════════════
    # BLOCK 6: Team Recognition
    # ═══════════════════════════════════════════════════════════
    top = distribution.get("top_performer")
    if top:
        lines.append(
            f"\U0001f3c5 *TOP:* {top['user_name']} \u2014 "
            f"{top['action_count']} positions processed yesterday"
        )
        lines.append(SEPARATOR)

    # ═══════════════════════════════════════════════════════════
    # BLOCK 7: Footer
    # ═══════════════════════════════════════════════════════════
    lines.append(f"\U0001f4cb *Total: {total_positions} positions for today*")

    return "\n".join(lines)


def _format_message_id(distribution: dict) -> str:
    """Format daily message in Indonesian — 7-block motivational format."""
    factory_name = distribution.get("factory_name", "")
    total_positions = distribution.get("total_positions", 0)
    kpi = distribution.get("kpi_yesterday", {})
    streak = distribution.get("streak", {})
    challenge = distribution.get("daily_challenge")
    lines = []

    # ═══════════════════════════════════════════════════════════
    # BLOCK 1: Greeting + Mood + Yesterday's Win + Streak
    # ═══════════════════════════════════════════════════════════
    mood = _mood_emoji(kpi)
    lines.append(f"{mood} *Selamat pagi, tim {factory_name}!*")

    pieces = kpi.get("pieces_processed", 0)
    defects = kpi.get("defect_count", 0)
    defect_rate = kpi.get("defect_rate", 0)
    if pieces > 0:
        quality_str = _quality_emoji_id(defect_rate, defects)
        lines.append(f"Kemarin: {pieces} posisi selesai, {defects} cacat {quality_str}")
    else:
        lines.append("Kemarin: tidak ada data produksi")

    zero_streak = streak.get("zero_defects_days", 0)
    if zero_streak > 1:
        lines.append(f"Rekor: {zero_streak} hari tanpa cacat! Terus semangat! \U0001f4aa")
    lines.append(SEPARATOR)

    # ═══════════════════════════════════════════════════════════
    # BLOCK 2: Daily Challenge + Bonus Points
    # ═══════════════════════════════════════════════════════════
    if challenge:
        bonus = challenge.get("bonus_points", 5)
        lines.append(f"\U0001f3af *Tantangan Hari Ini:* {challenge['title']}")
        if challenge.get("description"):
            lines.append(f"   {challenge['description']}")
        lines.append(f"   \U0001f4b0 Bonus: +{bonus} poin jika selesai!")
    else:
        if total_positions > 0:
            lines.append(f"\U0001f3af *Tantangan Hari Ini:* Selesaikan semua {total_positions} posisi!")
    lines.append(SEPARATOR)

    # ═══════════════════════════════════════════════════════════
    # BLOCK 3: Today's Plan (compact)
    # ═══════════════════════════════════════════════════════════
    lines.append(f"\U0001f4cb *RENCANA HARI INI ({total_positions} posisi)*")
    lines.append("")

    # ── Glazing ──
    glazing = distribution.get("glazing_tasks", [])
    if glazing:
        lines.append(f"\U0001f3a8 *GLASIR ({len(glazing)}):*")
        for i, task in enumerate(glazing, 1):
            behind = " \u26a0\ufe0f" if task.get("behind_schedule") else ""
            color_str = task["color"]
            if task.get("color_2"):
                color_str += f"/{task['color_2']}"
            consumption = task.get("consumption_info", "")
            cons_str = f" \u2014 {consumption}" if consumption else ""
            lines.append(
                f"  {i}. {color_str} {task['size']} "
                f"\u00d7{task['quantity']}{cons_str}{behind}"
            )
            bi = task.get("board_info")
            if bi and bi.get("ml_per_2boards"):
                board_type = "std" if bi["is_standard"] else f"{bi['board_size']}cm"
                lines.append(
                    f"     \U0001f4d0 {board_type} | {bi['tiles_per_board']}/papan | "
                    f"{bi['ml_per_2boards']}ml/2papan"
                )
        lines.append("")

    # ── Kiln ──
    kiln = distribution.get("kiln_loading", [])
    kiln_prep = distribution.get("kiln_prep_tasks", [])
    if kiln or kiln_prep:
        batch_count = len(kiln) if kiln else 0
        prep_count = len(kiln_prep) if kiln_prep else 0
        header_parts = []
        if batch_count:
            header_parts.append(f"{batch_count} batch")
        if prep_count:
            header_parts.append(f"{prep_count} persiapan")
        lines.append(f"\U0001f525 *TUNGKU ({', '.join(header_parts)}):*")
        for batch in kiln:
            temp_str = f"{batch['temperature']}\u00b0C" if batch.get("temperature") else "TBD"
            lines.append(
                f"  \u2022 {batch['kiln_name']}: "
                f"{batch['positions_count']} pos, {temp_str}"
            )
        for task in kiln_prep:
            behind = " \u26a0\ufe0f" if task.get("behind_schedule") else ""
            lines.append(
                f"  \u2022 Persiapan: {task['color']} {task['size']} "
                f"\u00d7{task['quantity']}{behind}"
            )
        lines.append("")

    # ── Sorting ──
    sorting = distribution.get("sorting_tasks", [])
    if sorting:
        lines.append(f"\u2702\ufe0f *SORTIR ({len(sorting)}):*")
        for task in sorting:
            lines.append(
                f"  \u2022 {task['color']} {task['size']} \u00d7{task['quantity']}"
            )
        lines.append("")

    # ── QC ──
    qc = distribution.get("qc_tasks", [])
    if qc:
        lines.append(f"\u2705 *QC ({len(qc)}):*")
        for task in qc:
            lines.append(
                f"  \u2022 {task['color']} \u00d7{task['quantity']}"
            )
        lines.append("")

    lines.append(SEPARATOR)

    # ═══════════════════════════════════════════════════════════
    # BLOCK 4: Alerts (only if any exist)
    # ═══════════════════════════════════════════════════════════
    urgent = distribution.get("urgent_alerts", [])
    stock_alerts = distribution.get("stock_alerts", [])
    mat_blocked = distribution.get("material_blocked", [])
    if urgent or stock_alerts or mat_blocked:
        lines.append("\u26a0\ufe0f *PERHATIAN:*")
        if mat_blocked:
            lines.append("")
            lines.append("\u26a0\ufe0f *Material Terblokir (butuh dalam 3 hari):*")
            for mb in mat_blocked:
                lines.append(
                    f"  \u2022 Posisi {mb['position_number']} "
                    f"(Pesanan #{mb['order_number']}) \u2014 glasir {mb['planned_glazing_display']}"
                )
            lines.append("")
        for alert in urgent:
            days = alert.get("days_overdue", 0)
            icon = "\U0001f534" if days > 0 else "\U0001f7e1"
            lines.append(f"  {icon} {alert['order']} \u2014 {alert['message']}")
        for sa in stock_alerts:
            lines.append(
                f"  \U0001f7e1 Stok rendah: {sa['material_name']} "
                f"({sa['balance']:.1f} {sa['unit']}, butuh {sa['min_balance']:.0f})"
            )
        lines.append(SEPARATOR)

    # ═══════════════════════════════════════════════════════════
    # BLOCK 5: Yesterday's Scorecard
    # ═══════════════════════════════════════════════════════════
    if pieces > 0:
        lines.append("\U0001f4ca *KEMARIN:*")
        lines.append(f"  \u2705 Selesai: {pieces} posisi")
        quality_label = _quality_emoji_id(defect_rate, defects)
        lines.append(f"  \U0001f3af Cacat: {defect_rate:.1f}% \u2014 {quality_label}")
        kiln_util = kpi.get("kiln_utilization", 0)
        if kiln_util > 0:
            lines.append(f"  \U0001f525 Isi tungku: {kiln_util:.0f}%")
        orders_done = kpi.get("orders_completed", 0)
        if orders_done > 0:
            lines.append(f"  \U0001f4e6 Dikirim: {orders_done} pesanan")
        lines.append(SEPARATOR)

    # ═══════════════════════════════════════════════════════════
    # BLOCK 6: Team Recognition
    # ═══════════════════════════════════════════════════════════
    top = distribution.get("top_performer")
    if top:
        lines.append(
            f"\U0001f3c5 *TOP:* {top['user_name']} \u2014 "
            f"{top['action_count']} posisi diproses kemarin"
        )
        lines.append(SEPARATOR)

    # ═══════════════════════════════════════════════════════════
    # BLOCK 7: Footer
    # ═══════════════════════════════════════════════════════════
    lines.append(f"\U0001f4cb *Total: {total_positions} posisi untuk hari ini*")

    return "\n".join(lines)


def _format_message_ru(distribution: dict) -> str:
    """Format daily message in Russian — 7-block motivational format."""
    factory_name = distribution.get("factory_name", "")
    total_positions = distribution.get("total_positions", 0)
    kpi = distribution.get("kpi_yesterday", {})
    streak = distribution.get("streak", {})
    challenge = distribution.get("daily_challenge")
    lines = []

    # BLOCK 1: Greeting + Mood
    mood = _mood_emoji(kpi)
    lines.append(f"{mood} *\u0414\u043e\u0431\u0440\u043e\u0435 \u0443\u0442\u0440\u043e, \u043a\u043e\u043c\u0430\u043d\u0434\u0430 {factory_name}!*")

    pieces = kpi.get("pieces_processed", 0)
    defects = kpi.get("defect_count", 0)
    defect_rate = kpi.get("defect_rate", 0)
    if pieces > 0:
        if defects == 0:
            q = "\U0001f525 \u0418\u0414\u0415\u0410\u041b\u042c\u041d\u041e!"
        elif defect_rate < 3.0:
            q = "\u0425\u043e\u0440\u043e\u0448\u0435\u0435 \u043a\u0430\u0447\u0435\u0441\u0442\u0432\u043e!"
        elif defect_rate < 5.0:
            q = "\u041f\u0440\u0438\u0435\u043c\u043b\u0435\u043c\u043e"
        else:
            q = "\u26a0\ufe0f \u041a\u0430\u0447\u0435\u0441\u0442\u0432\u043e \u0442\u0440\u0435\u0431\u0443\u0435\u0442 \u0432\u043d\u0438\u043c\u0430\u043d\u0438\u044f"
        lines.append(f"\u0412\u0447\u0435\u0440\u0430: {pieces} \u043f\u043e\u0437\u0438\u0446\u0438\u0439, {defects} \u0431\u0440\u0430\u043a {q}")
    else:
        lines.append("\u0412\u0447\u0435\u0440\u0430: \u043d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445")

    zero_streak = streak.get("zero_defects_days", 0)
    if zero_streak > 1:
        lines.append(f"\u0421\u0435\u0440\u0438\u044f: {zero_streak} \u0434\u043d\u0435\u0439 \u0431\u0435\u0437 \u0431\u0440\u0430\u043a\u0430! \U0001f4aa")
    lines.append(SEPARATOR)

    # BLOCK 2: Challenge + Bonus Points
    if challenge:
        bonus = challenge.get("bonus_points", 5)
        lines.append(f"\U0001f3af *\u0412\u044b\u0437\u043e\u0432 \u0434\u043d\u044f:* {challenge['title']}")
        if challenge.get("description"):
            lines.append(f"   {challenge['description']}")
        lines.append(f"   \U0001f4b0 \u0411\u043e\u043d\u0443\u0441: +{bonus} \u043e\u0447\u043a\u043e\u0432 \u0437\u0430 \u0432\u044b\u043f\u043e\u043b\u043d\u0435\u043d\u0438\u0435!")
    elif total_positions > 0:
        lines.append(f"\U0001f3af *\u0412\u044b\u0437\u043e\u0432 \u0434\u043d\u044f:* \u0417\u0430\u0432\u0435\u0440\u0448\u0438\u0442\u044c \u0432\u0441\u0435 {total_positions} \u043f\u043e\u0437\u0438\u0446\u0438\u0439!")
    lines.append(SEPARATOR)

    # BLOCK 3: Plan
    lines.append(f"\U0001f4cb *\u041f\u041b\u0410\u041d \u041d\u0410 \u0414\u0415\u041d\u042c ({total_positions} \u043f\u043e\u0437\u0438\u0446\u0438\u0439)*")
    lines.append("")

    glazing = distribution.get("glazing_tasks", [])
    if glazing:
        lines.append(f"\U0001f3a8 *\u0413\u041b\u0410\u0417\u0423\u0420\u041e\u0412\u041a\u0410 ({len(glazing)}):*")
        for i, task in enumerate(glazing, 1):
            behind = " \u26a0\ufe0f" if task.get("behind_schedule") else ""
            color_str = task["color"]
            if task.get("color_2"):
                color_str += f"/{task['color_2']}"
            consumption = task.get("consumption_info", "")
            cons_str = f" \u2014 {consumption}" if consumption else ""
            lines.append(f"  {i}. {color_str} {task['size']} \u00d7{task['quantity']}{cons_str}{behind}")
            bi = task.get("board_info")
            if bi and bi.get("ml_per_2boards"):
                board_type = "\u0441\u0442\u0434" if bi["is_standard"] else f"{bi['board_size']}\u0441\u043c"
                lines.append(f"     \U0001f4d0 {board_type} | {bi['tiles_per_board']}/\u0434\u043e\u0441\u043a\u0443 | {bi['ml_per_2boards']}\u043c\u043b/2\u0434\u043e\u0441\u043a\u0438")
        lines.append("")

    kiln = distribution.get("kiln_loading", [])
    kiln_prep = distribution.get("kiln_prep_tasks", [])
    if kiln or kiln_prep:
        header_parts = []
        if kiln:
            header_parts.append(f"{len(kiln)} \u043f\u0430\u0440\u0442\u0438\u0439")
        if kiln_prep:
            header_parts.append(f"{len(kiln_prep)} \u043f\u043e\u0434\u0433\u043e\u0442.")
        lines.append(f"\U0001f525 *\u041f\u0415\u0427\u042c ({', '.join(header_parts)}):*")
        for batch in kiln:
            temp_str = f"{batch['temperature']}\u00b0C" if batch.get("temperature") else "TBD"
            lines.append(f"  \u2022 {batch['kiln_name']}: {batch['positions_count']} \u043f\u043e\u0437, {temp_str}")
        for task in kiln_prep:
            behind = " \u26a0\ufe0f" if task.get("behind_schedule") else ""
            lines.append(f"  \u2022 \u041f\u043e\u0434\u0433\u043e\u0442: {task['color']} {task['size']} \u00d7{task['quantity']}{behind}")
        lines.append("")

    sorting = distribution.get("sorting_tasks", [])
    if sorting:
        lines.append(f"\u2702\ufe0f *\u0421\u041e\u0420\u0422\u0418\u0420\u041e\u0412\u041a\u0410 ({len(sorting)}):*")
        for task in sorting:
            lines.append(f"  \u2022 {task['color']} {task['size']} \u00d7{task['quantity']}")
        lines.append("")

    qc = distribution.get("qc_tasks", [])
    if qc:
        lines.append(f"\u2705 *\u041a\u041e\u041d\u0422\u0420\u041e\u041b\u042c ({len(qc)}):*")
        for task in qc:
            lines.append(f"  \u2022 {task['color']} \u00d7{task['quantity']}")
        lines.append("")

    lines.append(SEPARATOR)

    # BLOCK 4: Alerts
    urgent = distribution.get("urgent_alerts", [])
    stock_alerts = distribution.get("stock_alerts", [])
    mat_blocked = distribution.get("material_blocked", [])
    if urgent or stock_alerts or mat_blocked:
        lines.append("\u26a0\ufe0f *\u0412\u041d\u0418\u041c\u0410\u041d\u0418\u0415:*")
        if mat_blocked:
            lines.append("")
            lines.append("\u26a0\ufe0f *\u0411\u043b\u043e\u043a\u0438\u0440\u043e\u0432\u043a\u0430 \u043c\u0430\u0442\u0435\u0440\u0438\u0430\u043b\u043e\u0432 (\u043d\u0443\u0436\u043d\u044b \u0432 \u0442\u0435\u0447\u0435\u043d\u0438\u0435 3 \u0434\u043d\u0435\u0439):*")
            for mb in mat_blocked:
                lines.append(
                    f"  \u2022 \u041f\u043e\u0437\u0438\u0446\u0438\u044f {mb['position_number']} "
                    f"(\u0417\u0430\u043a\u0430\u0437 #{mb['order_number']}) \u2014 \u0433\u043b\u0430\u0437\u0443\u0440\u043e\u0432\u043a\u0430 {mb['planned_glazing_display']}"
                )
            lines.append("")
        for alert in urgent:
            days = alert.get("days_overdue", 0)
            icon = "\U0001f534" if days > 0 else "\U0001f7e1"
            lines.append(f"  {icon} {alert['order']} \u2014 {alert['message']}")
        for sa in stock_alerts:
            lines.append(f"  \U0001f7e1 \u041c\u0430\u043b\u043e: {sa['material_name']} ({sa['balance']:.1f} {sa['unit']}, \u043d\u0443\u0436\u043d\u043e {sa['min_balance']:.0f})")
        lines.append(SEPARATOR)

    # BLOCK 5: Scorecard
    if pieces > 0:
        lines.append("\U0001f4ca *\u0412\u0427\u0415\u0420\u0410:*")
        lines.append(f"  \u2705 \u0421\u0434\u0435\u043b\u0430\u043d\u043e: {pieces} \u043f\u043e\u0437\u0438\u0446\u0438\u0439")
        if defects == 0:
            ql = "\U0001f525 \u0418\u0414\u0415\u0410\u041b\u042c\u041d\u041e!"
        elif defect_rate < 3:
            ql = "\u0425\u043e\u0440\u043e\u0448\u043e!"
        else:
            ql = "\u26a0\ufe0f \u0412\u043d\u0438\u043c\u0430\u043d\u0438\u0435"
        lines.append(f"  \U0001f3af \u0411\u0440\u0430\u043a: {defect_rate:.1f}% \u2014 {ql}")
        kiln_util = kpi.get("kiln_utilization", 0)
        if kiln_util > 0:
            lines.append(f"  \U0001f525 \u0417\u0430\u043f\u043e\u043b\u043d\u0435\u043d\u0438\u0435 \u043f\u0435\u0447\u0438: {kiln_util:.0f}%")
        orders_done = kpi.get("orders_completed", 0)
        if orders_done > 0:
            lines.append(f"  \U0001f4e6 \u041e\u0442\u0433\u0440\u0443\u0436\u0435\u043d\u043e: {orders_done} \u0437\u0430\u043a\u0430\u0437\u043e\u0432")
        lines.append(SEPARATOR)

    # BLOCK 6: Recognition
    top = distribution.get("top_performer")
    if top:
        lines.append(f"\U0001f3c5 *\u041b\u0423\u0427\u0428\u0418\u0419:* {top['user_name']} \u2014 {top['action_count']} \u043f\u043e\u0437\u0438\u0446\u0438\u0439 \u0432\u0447\u0435\u0440\u0430")
        lines.append(SEPARATOR)

    # BLOCK 7: Footer
    lines.append(f"\U0001f4cb *\u0418\u0442\u043e\u0433\u043e: {total_positions} \u043f\u043e\u0437\u0438\u0446\u0438\u0439 \u043d\u0430 \u0441\u0435\u0433\u043e\u0434\u043d\u044f*")

    return "\n".join(lines)
