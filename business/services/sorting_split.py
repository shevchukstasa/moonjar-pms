"""
Sorting & Split service.
Business Logic: §8-9
"""
from uuid import UUID
import uuid as uuid_mod
from datetime import date, datetime, timedelta, timezone
from math import ceil, floor
from typing import Optional
import logging

from sqlalchemy.orm import Session
from sqlalchemy import func

from api.models import *  # noqa
from api.schemas import *  # noqa
from api.enums import (
    TaskType, TaskStatus, SurplusDispositionType,
    PositionStatus, UserRole, ManaShipmentStatus,
    SplitCategory, DefectStage, DefectOutcome,
    GrindingStatus, RepairStatus,
)

logger = logging.getLogger("moonjar.sorting_split")

# Threshold for creating a PM decision task for Coaster box and Mana accumulations
_ACCUMULATION_TASK_THRESHOLD = 100

# Defect types that go straight to Mana (write-off)
_MANA_DEFECT_TYPES = {"crack", "stuck"}

# Defect types that need repair (re-glazing or grinding)
_REPAIR_DEFECT_TYPES = {"glaze_defect", "shape_defect"}


def _next_split_index(db: Session, parent_position_id) -> int:
    """Return the next sequential split_index for a sub-position under this parent."""
    result = db.query(func.max(OrderPosition.split_index)).filter(
        OrderPosition.parent_position_id == parent_position_id,
    ).scalar()
    return (result or 0) + 1


def _ev(val):
    """Extract enum value safely."""
    return val.value if hasattr(val, "value") else str(val) if val else None


# ────────────────────────────────────────────────────────────────
# Core: process_sorting_split
# ────────────────────────────────────────────────────────────────

def process_sorting_split(db: Session, position_id: UUID, split_data: dict) -> dict:
    """
    Sorter enters quantities after kiln → sub-positions + defect records.

    split_data expected keys:
      - ok_count: int              — tiles that passed sorting
      - defect_counts: dict        — {crack: N, color_mismatch: N, glaze_defect: N,
                                       shape_defect: N, stuck: N}
      - grind_count: int           — tiles needing grinding

    Defect routing:
      - crack / stuck        → Mana (write-off)
      - color_mismatch       → AWAITING_COLOR_MATCHING (blocking task for PM)
      - glaze_defect         → REPAIR: sub-position sent to re-glazing
      - shape_defect         → REPAIR: sub-position sent to re-glazing (grinding path)
      - grind_count          → GrindingStock entry
    """
    position = db.query(OrderPosition).filter(OrderPosition.id == position_id).first()
    if not position:
        raise ValueError(f"Position {position_id} not found")

    current_status = _ev(position.status)
    if current_status != "transferred_to_sorting":
        raise ValueError(
            f"Position must be in 'transferred_to_sorting' status, got '{current_status}'"
        )

    ok_count = split_data.get("ok_count", 0)
    defect_counts = split_data.get("defect_counts", {})
    grind_count = split_data.get("grind_count", 0)

    # Validate totals
    total_defects = sum(defect_counts.get(k, 0) for k in defect_counts)
    total = ok_count + total_defects + grind_count
    if total != position.quantity:
        raise ValueError(
            f"Total ({total}) must equal position quantity ({position.quantity}). "
            f"ok={ok_count}, defects={total_defects}, grind={grind_count}"
        )

    now = datetime.now(timezone.utc)
    sub_positions = []
    defect_records = []
    mana_entries = []

    # Split-index counter
    _base_si = _next_split_index(db, position.id) - 1

    def _si():
        nonlocal _base_si
        _base_si += 1
        return _base_si

    # 1. Update parent position — good quantity, mark as packed
    position.quantity = ok_count
    position.status = PositionStatus.PACKED
    position.updated_at = now

    # 2. Process each defect type
    for defect_type, count in defect_counts.items():
        if count <= 0:
            continue

        if defect_type in _MANA_DEFECT_TYPES:
            # crack / stuck → write off to Mana
            sub = create_sub_position(
                db, position, count,
                split_category=SplitCategory.REPAIR,
                status=PositionStatus.CANCELLED,
                split_index=_si(),
            )
            sub_positions.append(sub)
            sub.is_merged = True  # written off, won't come back

            # Create defect record
            dr = DefectRecord(
                id=uuid_mod.uuid4(),
                factory_id=position.factory_id,
                stage=DefectStage.SORTING,
                position_id=position.id,
                defect_type=defect_type,
                quantity=count,
                outcome=DefectOutcome.TO_MANA,
                reported_via="dashboard",
                created_at=now,
            )
            db.add(dr)
            defect_records.append(dr)

            # Route to Mana shipment
            mana_entry = route_to_mana(
                db, position, count,
                reason=f"Sorting defect: {defect_type}",
            )
            mana_entries.append(mana_entry)

        elif defect_type == "color_mismatch":
            # → AWAITING_COLOR_MATCHING: blocking task for PM
            sub = create_sub_position(
                db, position, count,
                split_category=SplitCategory.COLOR_MISMATCH,
                status=PositionStatus.AWAITING_COLOR_MATCHING,
                split_index=_si(),
            )
            sub_positions.append(sub)

            # Create blocking task for PM to decide
            task = Task(
                id=uuid_mod.uuid4(),
                factory_id=position.factory_id,
                type=TaskType.COLOR_MATCHING,
                assigned_role=UserRole.PRODUCTION_MANAGER,
                related_order_id=position.order_id,
                related_position_id=sub.id,
                blocking=True,
                description=(
                    f"Color mismatch on {position.color} {position.size} — "
                    f"{count} pcs need decision (re-color / write-off / Mana)"
                ),
                priority=2,
                created_at=now,
            )
            db.add(task)

            # Defect record
            dr = DefectRecord(
                id=uuid_mod.uuid4(),
                factory_id=position.factory_id,
                stage=DefectStage.SORTING,
                position_id=position.id,
                defect_type="color_mismatch",
                quantity=count,
                outcome=DefectOutcome.REPAIR,
                reported_via="dashboard",
                created_at=now,
            )
            db.add(dr)
            defect_records.append(dr)

        elif defect_type == "glaze_defect":
            # → REPAIR: needs re-glazing
            sub = create_sub_position(
                db, position, count,
                split_category=SplitCategory.REPAIR,
                status=PositionStatus.SENT_TO_GLAZING,
                split_index=_si(),
            )
            sub_positions.append(sub)

            # Repair queue for SLA tracking
            rq = RepairQueue(
                id=uuid_mod.uuid4(),
                factory_id=position.factory_id,
                color=position.color,
                size=position.size,
                quantity=count,
                defect_type="glaze_defect",
                source_order_id=position.order_id,
                source_position_id=position.id,
                status=RepairStatus.IN_REPAIR,
                created_at=now,
                updated_at=now,
            )
            db.add(rq)

            # Defect record
            dr = DefectRecord(
                id=uuid_mod.uuid4(),
                factory_id=position.factory_id,
                stage=DefectStage.SORTING,
                position_id=position.id,
                defect_type="glaze_defect",
                quantity=count,
                outcome=DefectOutcome.REGLAZE,
                reported_via="dashboard",
                created_at=now,
            )
            db.add(dr)
            defect_records.append(dr)

        elif defect_type == "shape_defect":
            # → REPAIR: needs grinding then re-glazing
            sub = create_sub_position(
                db, position, count,
                split_category=SplitCategory.REPAIR,
                status=PositionStatus.SENT_TO_GLAZING,
                split_index=_si(),
            )
            sub_positions.append(sub)

            # Repair queue
            rq = RepairQueue(
                id=uuid_mod.uuid4(),
                factory_id=position.factory_id,
                color=position.color,
                size=position.size,
                quantity=count,
                defect_type="shape_defect",
                source_order_id=position.order_id,
                source_position_id=position.id,
                status=RepairStatus.IN_REPAIR,
                created_at=now,
                updated_at=now,
            )
            db.add(rq)

            # Defect record
            dr = DefectRecord(
                id=uuid_mod.uuid4(),
                factory_id=position.factory_id,
                stage=DefectStage.SORTING,
                position_id=position.id,
                defect_type="shape_defect",
                quantity=count,
                outcome=DefectOutcome.GRINDING,
                reported_via="dashboard",
                created_at=now,
            )
            db.add(dr)
            defect_records.append(dr)

        else:
            logger.warning("Unknown defect type '%s' — treating as write-off", defect_type)
            dr = DefectRecord(
                id=uuid_mod.uuid4(),
                factory_id=position.factory_id,
                stage=DefectStage.SORTING,
                position_id=position.id,
                defect_type=defect_type,
                quantity=count,
                outcome=DefectOutcome.WRITE_OFF,
                reported_via="dashboard",
                created_at=now,
            )
            db.add(dr)
            defect_records.append(dr)

    # 3. Grinding stock
    grinding_record = None
    if grind_count > 0:
        grinding_record = add_to_grinding_stock(db, position, grind_count)

        # Defect record for grinding
        dr = DefectRecord(
            id=uuid_mod.uuid4(),
            factory_id=position.factory_id,
            stage=DefectStage.SORTING,
            position_id=position.id,
            defect_type="grinding",
            quantity=grind_count,
            outcome=DefectOutcome.GRINDING,
            reported_via="dashboard",
            created_at=now,
        )
        db.add(dr)
        defect_records.append(dr)

    # 4. Flush to get IDs before building response
    db.flush()

    return {
        "position_id": str(position.id),
        "status": _ev(position.status),
        "ok_count": ok_count,
        "sub_positions": [
            {
                "id": str(sp.id),
                "split_category": _ev(sp.split_category),
                "status": _ev(sp.status),
                "quantity": sp.quantity,
                "split_index": sp.split_index,
            }
            for sp in sub_positions
        ],
        "defect_records": [
            {
                "id": str(dr.id),
                "defect_type": dr.defect_type,
                "quantity": dr.quantity,
                "outcome": _ev(dr.outcome),
            }
            for dr in defect_records
        ],
        "grinding_record": (
            {
                "id": str(grinding_record.id),
                "quantity": grinding_record.quantity,
                "status": _ev(grinding_record.status),
            }
            if grinding_record else None
        ),
        "mana_entries": len(mana_entries),
    }


# ────────────────────────────────────────────────────────────────
# create_sub_position
# ────────────────────────────────────────────────────────────────

def create_sub_position(
    db: Session,
    parent: OrderPosition,
    quantity: int,
    split_category: str,
    status: str,
    split_index: Optional[int] = None,
) -> OrderPosition:
    """
    Create a sub-position inheriting parent characteristics.

    Args:
        db: Database session
        parent: Parent OrderPosition
        quantity: Number of tiles in sub-position
        split_category: SplitCategory enum value (repair, refire, color_mismatch, reglaze)
        status: PositionStatus for the new sub-position
        split_index: Optional explicit split index; auto-calculated if None

    Returns:
        The newly created OrderPosition (sub-position)
    """
    if split_index is None:
        split_index = _next_split_index(db, parent.id)

    # Coerce string to enum if needed
    if isinstance(split_category, str):
        split_category = SplitCategory(split_category) if split_category in [e.value for e in SplitCategory] else split_category
    if isinstance(status, str):
        status = PositionStatus(status) if status in [e.value for e in PositionStatus] else status

    now = datetime.now(timezone.utc)

    sub = OrderPosition(
        id=uuid_mod.uuid4(),
        order_id=parent.order_id,
        order_item_id=parent.order_item_id,
        parent_position_id=parent.id,
        factory_id=parent.factory_id,
        status=status,
        quantity=quantity,
        color=parent.color,
        color_2=parent.color_2,
        size=parent.size,
        application=parent.application,
        finishing=parent.finishing,
        collection=parent.collection,
        application_type=parent.application_type,
        place_of_application=parent.place_of_application,
        product_type=parent.product_type,
        shape=parent.shape,
        thickness_mm=parent.thickness_mm,
        recipe_id=parent.recipe_id,
        mandatory_qc=parent.mandatory_qc,
        split_category=split_category,
        priority_order=parent.priority_order,
        position_number=parent.position_number,
        split_index=split_index,
        firing_round=parent.firing_round + 1,
        created_at=now,
        updated_at=now,
    )
    db.add(sub)
    return sub


# ────────────────────────────────────────────────────────────────
# merge_sub_position_back
# ────────────────────────────────────────────────────────────────

def merge_sub_position_back(db: Session, sub_position_id: UUID) -> OrderPosition:
    """
    Merge a repaired sub-position back into its parent.

    Preconditions:
      - Sub-position must have a parent_position_id
      - Sub-position status should indicate it's been repaired/packed
        (PACKED status after going through re-glazing + re-firing + re-sorting)

    Actions:
      1. Add sub-position quantity back to parent's quantity
      2. Mark sub-position as merged (is_merged = True)
      3. Update associated RepairQueue entry to RETURNED_TO_PRODUCTION
      4. If all sub-positions for parent are resolved, parent can advance

    Returns:
        The parent OrderPosition
    """
    sub = db.query(OrderPosition).filter(OrderPosition.id == sub_position_id).first()
    if not sub:
        raise ValueError(f"Sub-position {sub_position_id} not found")

    if not sub.parent_position_id:
        raise ValueError(f"Position {sub_position_id} is not a sub-position (no parent)")

    sub_status = _ev(sub.status)
    if sub_status != "packed":
        raise ValueError(
            f"Sub-position must be in 'packed' status to merge, got '{sub_status}'"
        )

    if sub.is_merged:
        raise ValueError(f"Sub-position {sub_position_id} is already merged")

    parent = db.query(OrderPosition).filter(
        OrderPosition.id == sub.parent_position_id
    ).first()
    if not parent:
        raise ValueError(f"Parent position {sub.parent_position_id} not found")

    now = datetime.now(timezone.utc)

    # 1. Add sub-position quantity back to parent
    parent.quantity += sub.quantity
    parent.updated_at = now

    # 2. Mark sub-position as merged
    sub.is_merged = True
    sub.status = PositionStatus.PACKED
    sub.updated_at = now

    # 3. Update RepairQueue entry if exists
    repair_entry = db.query(RepairQueue).filter(
        RepairQueue.source_position_id == parent.id,
        RepairQueue.status == RepairStatus.IN_REPAIR,
        RepairQueue.quantity == sub.quantity,
    ).first()
    if repair_entry:
        repair_entry.status = RepairStatus.RETURNED_TO_PRODUCTION
        repair_entry.repaired_at = now
        repair_entry.updated_at = now

    # 4. Check if all sub-positions for this parent are resolved
    #    (all either merged or cancelled/written-off)
    unresolved_subs = db.query(OrderPosition).filter(
        OrderPosition.parent_position_id == parent.id,
        OrderPosition.is_merged.is_(False),
        OrderPosition.status.notin_([
            PositionStatus.CANCELLED,
            PositionStatus.PACKED,
        ]),
    ).count()

    if unresolved_subs == 0:
        # All sub-positions resolved — parent can advance to packing/QC
        logger.info(
            "All sub-positions resolved for parent %s — ready for next stage",
            parent.id,
        )

    db.flush()
    return parent


# ────────────────────────────────────────────────────────────────
# route_to_mana
# ────────────────────────────────────────────────────────────────

def route_to_mana(
    db: Session,
    position: OrderPosition,
    count: int,
    reason: str,
) -> dict:
    """
    Create/update a Mana shipment entry for defective tiles being written off.

    Adds items to the current PENDING ManaShipment for the factory.
    Creates a PM decision task when accumulation exceeds threshold.

    Returns:
        dict with Mana item entry details
    """
    item_entry = {
        "color": position.color,
        "size": position.size,
        "quantity": count,
        "reason": reason,
        "source_order_id": str(position.order_id),
        "source_position_id": str(position.id),
    }

    pending_shipment = db.query(ManaShipment).filter(
        ManaShipment.factory_id == position.factory_id,
        ManaShipment.status == ManaShipmentStatus.PENDING,
    ).first()

    if pending_shipment:
        current_items = list(pending_shipment.items_json) if pending_shipment.items_json else []
        current_items.append(item_entry)
        pending_shipment.items_json = current_items
    else:
        current_items = [item_entry]
        new_shipment = ManaShipment(
            id=uuid_mod.uuid4(),
            factory_id=position.factory_id,
            items_json=current_items,
            status=ManaShipmentStatus.PENDING,
        )
        db.add(new_shipment)

    # Create PM task when Mana shipment exceeds threshold
    total_mana_qty = sum(item.get("quantity", 0) for item in current_items)
    if total_mana_qty >= _ACCUMULATION_TASK_THRESHOLD:
        _create_pm_accumulation_task(
            db, position.factory_id, total_mana_qty,
            f"Mana shipment ({position.size})"
        )

    return item_entry


# ────────────────────────────────────────────────────────────────
# add_to_grinding_stock
# ────────────────────────────────────────────────────────────────

def add_to_grinding_stock(db: Session, position: OrderPosition, count: int) -> GrindingStock:
    """
    Track tiles needing grinding by creating a GrindingStock entry.

    Args:
        position: Source OrderPosition
        count: Number of tiles for grinding

    Returns:
        The GrindingStock record
    """
    now = datetime.now(timezone.utc)
    gs = GrindingStock(
        id=uuid_mod.uuid4(),
        factory_id=position.factory_id,
        color=position.color,
        size=position.size,
        quantity=count,
        source_order_id=position.order_id,
        source_position_id=position.id,
        status=GrindingStatus.IN_STOCK,
        created_at=now,
        updated_at=now,
    )
    db.add(gs)
    return gs


# ────────────────────────────────────────────────────────────────
# Helper: check basic color
# ────────────────────────────────────────────────────────────────

def _check_is_basic_color(db: Session, color_name: str) -> bool:
    """Check if a color is basic by looking up colors.is_basic."""
    color = db.query(Color).filter(Color.name == color_name).first()
    if color is None:
        return False
    return bool(color.is_basic)


# ────────────────────────────────────────────────────────────────
# Helper: PM accumulation task
# ────────────────────────────────────────────────────────────────

def _create_pm_accumulation_task(db: Session, factory_id, total_qty: int, label: str) -> None:
    """Create a PM decision task when Coaster box or Mana shipment exceeds threshold.
    Skips creation if an active MANA_CONFIRMATION task already exists for this factory.
    """
    active_task = db.query(Task).filter(
        Task.factory_id == factory_id,
        Task.type == TaskType.MANA_CONFIRMATION,
        Task.status.notin_([TaskStatus.DONE, TaskStatus.CANCELLED]),
    ).first()
    if active_task:
        # Update description to reflect current total
        active_task.description = (
            f"{label} accumulated {total_qty} pcs — decide next steps (ship / hold)"
        )
        return
    task = Task(
        id=uuid_mod.uuid4(),
        factory_id=factory_id,
        type=TaskType.MANA_CONFIRMATION,
        assigned_role=UserRole.PRODUCTION_MANAGER,
        description=f"{label} accumulated {total_qty} pcs — decide next steps (ship / hold)",
        priority=2,
    )
    db.add(task)


# ────────────────────────────────────────────────────────────────
# Surplus handling (unchanged from original)
# ────────────────────────────────────────────────────────────────

def handle_surplus(db: Session, position: OrderPosition, surplus_quantity: int) -> Optional[SurplusDisposition]:
    """
    After sorting: if good tiles > ordered quantity, distribute surplus.
    Rules by size and base color (BUSINESS_LOGIC.md §9):
      - 10x10 + basic color  → Showroom (+ photographing task)
      - 10x10 + non-basic    → Coaster box (PM decides when > 100 pcs)
      - All other sizes      → Mana shipment (PM decides when > 100 pcs)
    """
    size = position.size
    color = position.color
    is_basic = _check_is_basic_color(db, color)

    if size == '10x10' and is_basic:
        # → Showroom: create transfer task + photographing task
        showroom_task = Task(
            id=uuid_mod.uuid4(),
            factory_id=position.factory_id,
            type=TaskType.SHOWROOM_TRANSFER,
            assigned_role=UserRole.SORTER_PACKER,
            related_order_id=position.order_id,
            related_position_id=position.id,
            description=f"Send {surplus_quantity} pcs {color} 10x10 to showroom display board",
            priority=3,
        )
        db.add(showroom_task)

        photo_task = Task(
            id=uuid_mod.uuid4(),
            factory_id=position.factory_id,
            type=TaskType.PHOTOGRAPHING,
            assigned_role=UserRole.PRODUCTION_MANAGER,
            related_order_id=position.order_id,
            related_position_id=position.id,
            description=f"Photograph surplus {color} 10x10 for catalog",
            priority=3,
        )
        db.add(photo_task)

        disposition = SurplusDisposition(
            id=uuid_mod.uuid4(),
            factory_id=position.factory_id,
            order_id=position.order_id,
            position_id=position.id,
            surplus_quantity=surplus_quantity,
            disposition_type=SurplusDispositionType.SHOWROOM,
            size=size,
            color=color,
            is_base_color=True,
            task_id=showroom_task.id,
        )
        db.add(disposition)
        return disposition

    elif size == '10x10' and not is_basic:
        # → Coaster box: accumulate by color+size into casters_boxes table.
        # When the box accumulates > 100 pcs, PM decides what to do with it.
        existing_box = db.query(CastersBox).filter(
            CastersBox.factory_id == position.factory_id,
            CastersBox.color == color,
            CastersBox.size == size,
            CastersBox.removed_at.is_(None),  # only active boxes
        ).first()
        if existing_box:
            existing_box.quantity += surplus_quantity
            total_box_qty = existing_box.quantity
        else:
            new_box = CastersBox(
                id=uuid_mod.uuid4(),
                factory_id=position.factory_id,
                color=color,
                size=size,
                quantity=surplus_quantity,
                source_order_id=position.order_id,
            )
            db.add(new_box)
            total_box_qty = surplus_quantity

        # Create PM task when Coaster box exceeds threshold
        # Note: Coaster box accumulates mixed colors — no color specified in label
        if total_box_qty >= _ACCUMULATION_TASK_THRESHOLD:
            _create_pm_accumulation_task(
                db, position.factory_id, total_box_qty,
                "Coaster box (10x10 mixed colors)"
            )

        disposition = SurplusDisposition(
            id=uuid_mod.uuid4(),
            factory_id=position.factory_id,
            order_id=position.order_id,
            position_id=position.id,
            surplus_quantity=surplus_quantity,
            disposition_type=SurplusDispositionType.CASTERS,
            size=size,
            color=color,
            is_base_color=False,
        )
        db.add(disposition)
        return disposition

    else:
        # → Mana: accumulate items into the current PENDING Mana shipment.
        # When Mana exceeds 100 pcs, PM decides when to ship.
        pending_shipment = db.query(ManaShipment).filter(
            ManaShipment.factory_id == position.factory_id,
            ManaShipment.status == ManaShipmentStatus.PENDING,
        ).first()
        item_entry = {
            "color": color,
            "size": size,
            "quantity": surplus_quantity,
            "source_order_id": str(position.order_id),
            "source_position_id": str(position.id),
        }
        if pending_shipment:
            current_items = list(pending_shipment.items_json) if pending_shipment.items_json else []
            current_items.append(item_entry)
            pending_shipment.items_json = current_items
        else:
            current_items = [item_entry]
            new_shipment = ManaShipment(
                id=uuid_mod.uuid4(),
                factory_id=position.factory_id,
                items_json=current_items,
                status=ManaShipmentStatus.PENDING,
            )
            db.add(new_shipment)

        # Create PM task when Mana shipment exceeds threshold
        total_mana_qty = sum(item.get('quantity', 0) for item in current_items)
        if total_mana_qty >= _ACCUMULATION_TASK_THRESHOLD:
            _create_pm_accumulation_task(
                db, position.factory_id, total_mana_qty,
                f"Mana shipment ({size})"
            )

        disposition = SurplusDisposition(
            id=uuid_mod.uuid4(),
            factory_id=position.factory_id,
            order_id=position.order_id,
            position_id=position.id,
            surplus_quantity=surplus_quantity,
            disposition_type=SurplusDispositionType.MANA,
            size=size,
            color=color,
            is_base_color=is_basic,
        )
        db.add(disposition)
        return disposition
