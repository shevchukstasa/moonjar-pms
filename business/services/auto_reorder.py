"""
Auto-reorder service: detects low stock → creates purchase request + mandatory PM task.

Flow:
1. Daily job detects materials where balance < min_balance
2. Creates MaterialPurchaseRequest (PENDING, source='auto_reorder')
3. Creates Task (MATERIAL_ORDER, blocking=False) assigned to PM
4. Sends PM Telegram message with action buttons: ✅ Approve / ✏️ Edit / ❌ Reject
5. PM action → CEO Telegram notification (both edit and reject cases)
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from api.enums import PurchaseStatus, TaskType, TaskStatus, UserRole
from api.models import (
    Material,
    MaterialPurchaseRequest,
    MaterialStock,
    Supplier,
    Task,
    User,
    UserFactory,
)

logger = logging.getLogger(__name__)


# ── 1. Detection & auto-creation ─────────────────────────────────────────


def check_and_create_reorders(db: Session, factory_id: UUID) -> dict:
    """Check all materials for low stock and create purchase requests + tasks.

    Called by daily scheduler after min_balance recalculation.
    Skips materials that already have a PENDING auto_reorder purchase request.

    Returns: {"created": N, "skipped": N, "materials": [...]}
    """
    # Find low-stock materials
    low_stocks = (
        db.query(MaterialStock, Material)
        .join(Material, MaterialStock.material_id == Material.id)
        .filter(
            MaterialStock.factory_id == factory_id,
            MaterialStock.balance < MaterialStock.min_balance,
            MaterialStock.min_balance > 0,
        )
        .all()
    )

    if not low_stocks:
        return {"created": 0, "skipped": 0, "materials": []}

    # Check existing pending auto_reorder PRs to avoid duplicates
    existing_pr_material_ids = set()
    existing_prs = (
        db.query(MaterialPurchaseRequest)
        .filter(
            MaterialPurchaseRequest.factory_id == factory_id,
            MaterialPurchaseRequest.status == PurchaseStatus.PENDING,
            MaterialPurchaseRequest.source == "auto_reorder",
        )
        .all()
    )
    for pr in existing_prs:
        for item in (pr.materials_json or []):
            mid = item.get("material_id")
            if mid:
                existing_pr_material_ids.add(mid)

    # Group by supplier (skip materials covered by substitutes)
    from business.services.material_substitution import check_substitution_available

    by_supplier: dict[str, list[tuple]] = {}
    skipped = 0
    substitution_notes = []
    for stock, mat in low_stocks:
        if str(mat.id) in existing_pr_material_ids:
            skipped += 1
            continue

        # Check if a substitute material covers the deficit
        deficit = stock.min_balance - stock.balance
        sub_info = check_substitution_available(db, mat.id, factory_id, deficit)
        if sub_info and sub_info["sufficient"]:
            skipped += 1
            substitution_notes.append(
                f"{mat.name} deficit covered by {sub_info['substitute_name']} "
                f"(need {sub_info['substitute_needed_qty']:.1f}, have {sub_info['substitute_available']:.1f})"
            )
            logger.info(
                "AUTO_REORDER | skipping %s — substitute %s has sufficient stock",
                mat.name, sub_info["substitute_name"],
            )
            continue

        key = str(mat.supplier_id) if mat.supplier_id else "no_supplier"
        by_supplier.setdefault(key, []).append((stock, mat))

    # Create purchase requests grouped by supplier
    created_prs = []
    for supplier_key, items in by_supplier.items():
        supplier_id_val = None if supplier_key == "no_supplier" else items[0][1].supplier_id

        materials_json = []
        for stock, mat in items:
            deficit = float(stock.min_balance - stock.balance)
            # For stone/frit: order at least avg monthly consumption
            quantity = deficit
            if mat.material_type in ("stone", "frit"):
                if stock.avg_monthly_consumption:
                    quantity = max(deficit, float(stock.avg_monthly_consumption))

            # Check for partial substitution info to show PM
            sub_note = None
            sub_info = check_substitution_available(db, mat.id, factory_id, stock.min_balance - stock.balance)
            if sub_info and not sub_info["sufficient"]:
                sub_note = (
                    f"Partial substitute: {sub_info['substitute_name']} "
                    f"(have {float(sub_info['substitute_available']):.1f}, "
                    f"need {float(sub_info['substitute_needed_qty']):.1f})"
                )

            materials_json.append({
                "material_id": str(mat.id),
                "name": mat.name,
                "quantity": round(quantity, 3),
                "unit": mat.unit or "pcs",
                "current_balance": float(stock.balance),
                "min_balance": float(stock.min_balance),
                **({"substitution_note": sub_note} if sub_note else {}),
            })

        supplier_name = None
        if supplier_id_val:
            sup = db.query(Supplier).filter(Supplier.id == supplier_id_val).first()
            supplier_name = sup.name if sup else None

        pr = MaterialPurchaseRequest(
            factory_id=factory_id,
            supplier_id=supplier_id_val,
            materials_json=materials_json,
            status=PurchaseStatus.PENDING,
            source="auto_reorder",
            notes=f"Auto-reorder: {len(materials_json)} material(s) below min balance",
        )
        db.add(pr)
        db.flush()  # get pr.id

        # Create mandatory task for PM
        mat_names = ", ".join(m["name"] for m in materials_json[:3])
        if len(materials_json) > 3:
            mat_names += f" +{len(materials_json) - 3} more"

        task = Task(
            factory_id=factory_id,
            type=TaskType.MATERIAL_ORDER,
            status=TaskStatus.PENDING,
            assigned_role=UserRole.PRODUCTION_MANAGER,
            blocking=False,
            priority=7,  # high priority
            description=(
                f"⚠️ Auto-reorder: review purchase request for {mat_names} "
                f"(supplier: {supplier_name or 'unassigned'})"
            ),
            metadata_json={
                "purchase_request_id": str(pr.id),
                "supplier_name": supplier_name,
                "materials_count": len(materials_json),
                "source": "auto_reorder",
            },
        )
        db.add(task)
        db.flush()

        created_prs.append({
            "pr_id": str(pr.id),
            "task_id": str(task.id),
            "supplier": supplier_name,
            "materials": materials_json,
        })

    db.flush()

    # Send Telegram notifications to PMs
    for pr_info in created_prs:
        try:
            _notify_pm_telegram(db, factory_id, pr_info)
        except Exception as e:
            logger.error("Failed to send PM reorder notification: %s", e)

    logger.info(
        "AUTO_REORDER | factory=%s | created=%d PRs | skipped=%d (already pending)",
        factory_id, len(created_prs), skipped,
    )

    return {
        "created": len(created_prs),
        "skipped": skipped,
        "materials": [m["name"] for items in by_supplier.values() for _, m in items],
    }


def _notify_pm_telegram(db: Session, factory_id: UUID, pr_info: dict) -> None:
    """Send Telegram message to PMs with action buttons."""
    from business.services.notifications import send_telegram_message_with_buttons

    # Find PM users with telegram
    pms = (
        db.query(User)
        .join(UserFactory, UserFactory.user_id == User.id)
        .filter(
            UserFactory.factory_id == factory_id,
            User.role == UserRole.PRODUCTION_MANAGER.value,
            User.is_active.is_(True),
            User.telegram_user_id.isnot(None),
        )
        .all()
    )

    pr_id = pr_info["pr_id"]
    supplier = pr_info.get("supplier") or "No supplier"
    materials = pr_info.get("materials", [])

    lines = [
        "📦 *ЗАКАЗ МАТЕРИАЛОВ — ТРЕБУЕТСЯ ПРОВЕРКА*\n",
        f"Поставщик: *{supplier}*",
        f"Позиций: {len(materials)}\n",
    ]
    for m in materials[:5]:
        balance = m.get("current_balance", 0)
        minimum = m.get("min_balance", 0)
        qty = m.get("quantity", 0)
        severity = "🔴" if balance < minimum * 0.5 else "🟡"
        lines.append(
            f"{severity} {m['name']}: {balance:.1f} → заказ {qty:.1f} {m.get('unit', '')}"
        )
    if len(materials) > 5:
        lines.append(f"... ещё {len(materials) - 5}")

    # Show substitution notes if any
    sub_notes = [m.get("substitution_note") for m in materials if m.get("substitution_note")]
    if sub_notes:
        lines.append("\n🔄 *Возможные замены:*")
        for note in sub_notes[:3]:
            lines.append(f"  ↳ {note}")

    lines.append("\n⚡ *Действие обязательно:*")

    text = "\n".join(lines)

    buttons = [
        [
            {"text": "✅ Подтвердить заказ", "callback_data": f"reorder:approve:{pr_id}"},
        ],
        [
            {"text": "✏️ Изменить кол-во", "callback_data": f"reorder:edit:{pr_id}"},
            {"text": "❌ Отклонить", "callback_data": f"reorder:reject:{pr_id}"},
        ],
    ]

    for pm in pms:
        try:
            send_telegram_message_with_buttons(
                chat_id=str(pm.telegram_user_id),
                text=text,
                inline_keyboard=buttons,
            )
        except Exception as e:
            logger.warning("Failed to send reorder notification to PM %s: %s", pm.name, e)


# ── 2. PM actions ─────────────────────────────────────────────────────────


def approve_purchase_request(
    db: Session,
    pr_id: UUID,
    pm_user_id: UUID,
) -> dict:
    """PM approves auto-reorder → status becomes APPROVED, closes related task."""
    pr = db.query(MaterialPurchaseRequest).filter(
        MaterialPurchaseRequest.id == pr_id,
    ).first()
    if not pr:
        raise ValueError(f"Purchase request {pr_id} not found")
    if pr.status != PurchaseStatus.PENDING:
        raise ValueError(f"PR is not pending (status={pr.status})")

    pr.status = PurchaseStatus.APPROVED
    pr.approved_by = pm_user_id
    pr.updated_at = datetime.now(timezone.utc)

    # Close related task
    _close_pr_task(db, pr_id, pm_user_id)

    db.flush()
    return {"status": "approved", "pr_id": str(pr_id)}


def edit_purchase_request(
    db: Session,
    pr_id: UUID,
    pm_user_id: UUID,
    updated_materials: list[dict],
    notes: Optional[str] = None,
) -> dict:
    """PM edits quantities/materials → updates PR, approves it, notifies CEO."""
    pr = db.query(MaterialPurchaseRequest).filter(
        MaterialPurchaseRequest.id == pr_id,
    ).first()
    if not pr:
        raise ValueError(f"Purchase request {pr_id} not found")
    if pr.status != PurchaseStatus.PENDING:
        raise ValueError(f"PR is not pending (status={pr.status})")

    original_materials = pr.materials_json or []
    pr.materials_json = updated_materials
    pr.status = PurchaseStatus.APPROVED
    pr.approved_by = pm_user_id
    pr.updated_at = datetime.now(timezone.utc)
    if notes:
        pr.notes = (pr.notes or "") + f"\nPM edit: {notes}"

    _close_pr_task(db, pr_id, pm_user_id)

    db.flush()

    # Notify CEO about changes
    _notify_ceo_reorder_action(
        db, pr, pm_user_id, action="edited",
        original_materials=original_materials,
    )

    return {"status": "approved_with_edits", "pr_id": str(pr_id)}


def reject_purchase_request(
    db: Session,
    pr_id: UUID,
    pm_user_id: UUID,
    reason: str,
) -> dict:
    """PM rejects auto-reorder → closes PR, notifies CEO with reason."""
    pr = db.query(MaterialPurchaseRequest).filter(
        MaterialPurchaseRequest.id == pr_id,
    ).first()
    if not pr:
        raise ValueError(f"Purchase request {pr_id} not found")
    if pr.status != PurchaseStatus.PENDING:
        raise ValueError(f"PR is not pending (status={pr.status})")

    pr.status = PurchaseStatus.CLOSED
    pr.approved_by = pm_user_id
    pr.updated_at = datetime.now(timezone.utc)
    pr.notes = (pr.notes or "") + f"\n❌ Rejected by PM: {reason}"

    _close_pr_task(db, pr_id, pm_user_id)

    db.flush()

    _notify_ceo_reorder_action(db, pr, pm_user_id, action="rejected", reason=reason)

    return {"status": "rejected", "pr_id": str(pr_id), "reason": reason}


def _close_pr_task(db: Session, pr_id: UUID, pm_user_id: UUID) -> None:
    """Close the Task linked to this purchase request."""
    from sqlalchemy import cast
    from sqlalchemy.dialects.postgresql import JSONB as _JSONB

    tasks = (
        db.query(Task)
        .filter(
            Task.type == TaskType.MATERIAL_ORDER,
            Task.status == TaskStatus.PENDING,
            Task.metadata_json["purchase_request_id"].astext == str(pr_id),
        )
        .all()
    )
    now = datetime.now(timezone.utc)
    for task in tasks:
        task.status = TaskStatus.DONE
        task.completed_at = now
        task.assigned_to = pm_user_id
        task.updated_at = now


def _notify_ceo_reorder_action(
    db: Session,
    pr: MaterialPurchaseRequest,
    pm_user_id: UUID,
    action: str,
    reason: Optional[str] = None,
    original_materials: Optional[list] = None,
) -> None:
    """Notify CEO/Owner via Telegram about PM's reorder decision."""
    from business.services.notifications import send_telegram_message

    pm = db.query(User).filter(User.id == pm_user_id).first()
    pm_name = pm.name if pm else "PM"

    supplier_name = None
    if pr.supplier_id:
        sup = db.query(Supplier).filter(Supplier.id == pr.supplier_id).first()
        supplier_name = sup.name if sup else None

    materials = pr.materials_json or []

    if action == "rejected":
        emoji = "❌"
        header = "ЗАКАЗ ОТКЛОНЁН"
        detail = f"Причина: _{reason}_"
    else:
        emoji = "✏️"
        header = "ЗАКАЗ ИЗМЕНЁН И ПОДТВЕРЖДЁН"
        # Build diff
        changes = []
        orig_map = {m.get("material_id"): m for m in (original_materials or [])}
        for m in materials:
            mid = m.get("material_id")
            orig = orig_map.get(mid)
            if orig and abs(m.get("quantity", 0) - orig.get("quantity", 0)) > 0.01:
                changes.append(
                    f"  • {m['name']}: {orig['quantity']:.1f} → {m['quantity']:.1f}"
                )
        if changes:
            detail = "Изменения:\n" + "\n".join(changes)
        else:
            detail = "Состав заказа изменён"

    lines = [
        f"{emoji} *{header}*\n",
        f"PM: {pm_name}",
        f"Поставщик: {supplier_name or 'не указан'}",
        f"Позиций: {len(materials)}",
        "",
        detail,
    ]
    text = "\n".join(lines)

    # Find CEO/Owner users
    ceos = (
        db.query(User)
        .join(UserFactory, UserFactory.user_id == User.id)
        .filter(
            UserFactory.factory_id == pr.factory_id,
            User.role.in_([UserRole.CEO.value, UserRole.OWNER.value]),
            User.is_active.is_(True),
            User.telegram_user_id.isnot(None),
        )
        .all()
    )

    for ceo in ceos:
        try:
            send_telegram_message(chat_id=str(ceo.telegram_user_id), text=text)
        except Exception as e:
            logger.warning("Failed to notify CEO %s about reorder: %s", ceo.name, e)
