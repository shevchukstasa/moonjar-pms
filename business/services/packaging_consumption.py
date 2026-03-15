"""
Packaging Consumption service.

Handles calculating, reserving, and consuming packaging materials
(boxes + spacers) based on position size and quantity.

Trigger points:
- reserve_packaging(): called when position enters TRANSFERRED_TO_SORTING
- consume_packaging(): called when position transitions to PACKED
"""

import logging
import math
from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from api.models import (
    OrderPosition, Size,
    PackagingBoxType, PackagingBoxCapacity, PackagingSpacerRule,
    Material, MaterialStock, MaterialTransaction,
)

logger = logging.getLogger(__name__)


@dataclass
class PackagingMaterialNeed:
    material_id: UUID
    material_name: str
    quantity_needed: Decimal
    is_box: bool  # True for box, False for spacer


@dataclass
class PackagingNeeds:
    box_type_id: UUID | None = None
    box_type_name: str | None = None
    box_material_id: UUID | None = None
    boxes_needed: int = 0
    size_id: UUID | None = None
    size_name: str | None = None
    materials: list[PackagingMaterialNeed] = field(default_factory=list)


def calculate_packaging_needs(db: Session, position: OrderPosition) -> PackagingNeeds:
    """Calculate packaging materials needed for a position.

    Returns a PackagingNeeds with the list of materials and quantities required.
    """
    result = PackagingNeeds()

    if not position.size or not position.quantity:
        logger.debug("Position %s has no size or quantity, skipping packaging", position.id)
        return result

    # 1. Find Size record
    size = db.query(Size).filter(Size.name == position.size).first()
    if not size:
        logger.warning("No Size record found for '%s', skipping packaging for position %s",
                       position.size, position.id)
        return result

    result.size_id = size.id
    result.size_name = size.name

    # 2. Find active box type with capacity for this size
    capacity = (
        db.query(PackagingBoxCapacity)
        .join(PackagingBoxType, PackagingBoxType.id == PackagingBoxCapacity.box_type_id)
        .filter(
            PackagingBoxCapacity.size_id == size.id,
            PackagingBoxType.is_active == True,
        )
        .first()
    )

    if not capacity:
        logger.info("No packaging box capacity configured for size '%s', position %s",
                     position.size, position.id)
        return result

    box_type = db.query(PackagingBoxType).filter(PackagingBoxType.id == capacity.box_type_id).first()
    if not box_type:
        return result

    result.box_type_id = box_type.id
    result.box_type_name = box_type.name
    result.box_material_id = box_type.material_id

    # 3. Calculate boxes needed
    qty = int(position.quantity)
    if capacity.pieces_per_box and capacity.pieces_per_box > 0:
        boxes_needed = math.ceil(qty / capacity.pieces_per_box)
    elif capacity.sqm_per_box and capacity.sqm_per_box > 0 and position.glazeable_sqm:
        total_sqm = float(position.glazeable_sqm) * qty
        boxes_needed = math.ceil(total_sqm / float(capacity.sqm_per_box))
    else:
        logger.warning("Box capacity for size '%s' has no valid pieces or sqm, position %s",
                       position.size, position.id)
        return result

    result.boxes_needed = boxes_needed

    # 4. Add box material need
    box_mat = db.query(Material).filter(Material.id == box_type.material_id).first()
    result.materials.append(PackagingMaterialNeed(
        material_id=box_type.material_id,
        material_name=box_mat.name if box_mat else "Box",
        quantity_needed=Decimal(boxes_needed),
        is_box=True,
    ))

    # 5. Find spacer rules for this box_type + size
    spacer_rules = (
        db.query(PackagingSpacerRule)
        .filter(
            PackagingSpacerRule.box_type_id == box_type.id,
            PackagingSpacerRule.size_id == size.id,
        )
        .all()
    )
    for sr in spacer_rules:
        spacer_mat = db.query(Material).filter(Material.id == sr.spacer_material_id).first()
        spacer_qty = sr.qty_per_box * boxes_needed
        result.materials.append(PackagingMaterialNeed(
            material_id=sr.spacer_material_id,
            material_name=spacer_mat.name if spacer_mat else "Spacer",
            quantity_needed=Decimal(spacer_qty),
            is_box=False,
        ))

    return result


def reserve_packaging(
    db: Session,
    position_id: UUID,
    factory_id: UUID,
    user_id: UUID | None = None,
) -> dict:
    """Reserve packaging materials when position enters sorting.

    Creates RESERVE transactions for boxes and spacers.
    Returns summary dict.
    """
    position = db.query(OrderPosition).filter(OrderPosition.id == position_id).first()
    if not position:
        logger.warning("Position %s not found for packaging reservation", position_id)
        return {"ok": False, "error": "Position not found"}

    needs = calculate_packaging_needs(db, position)
    if not needs.materials:
        return {"ok": True, "skipped": True, "reason": "No packaging config for this size"}

    reserved = []
    for need in needs.materials:
        t = MaterialTransaction(
            material_id=need.material_id,
            factory_id=factory_id,
            type="reserve",
            quantity=need.quantity_needed,
            related_position_id=position_id,
            notes=f"Packaging {'box' if need.is_box else 'spacer'} reservation for {needs.size_name}",
            created_by=user_id,
        )
        db.add(t)
        reserved.append({
            "material": need.material_name,
            "quantity": float(need.quantity_needed),
        })

    db.flush()
    logger.info("Reserved packaging for position %s: %d materials, %d boxes",
                position_id, len(reserved), needs.boxes_needed)
    return {"ok": True, "boxes_needed": needs.boxes_needed, "reserved": reserved}


def consume_packaging(
    db: Session,
    position_id: UUID,
    factory_id: UUID,
    user_id: UUID | None = None,
    actual_boxes: int | None = None,
) -> dict:
    """Consume (write off) packaging materials when position is packed.

    Creates CONSUME + UNRESERVE transactions and deducts from stock balance.
    If actual_boxes is provided, uses that instead of calculated amount.
    """
    position = db.query(OrderPosition).filter(OrderPosition.id == position_id).first()
    if not position:
        logger.warning("Position %s not found for packaging consumption", position_id)
        return {"ok": False, "error": "Position not found"}

    needs = calculate_packaging_needs(db, position)
    if not needs.materials:
        return {"ok": True, "skipped": True, "reason": "No packaging config for this size"}

    # If actual_boxes provided, recalculate quantities proportionally
    if actual_boxes is not None and needs.boxes_needed > 0:
        ratio = Decimal(actual_boxes) / Decimal(needs.boxes_needed)
        for need in needs.materials:
            if need.is_box:
                need.quantity_needed = Decimal(actual_boxes)
            else:
                need.quantity_needed = (need.quantity_needed * ratio).quantize(Decimal("1"))

    consumed = []
    for need in needs.materials:
        # CONSUME transaction — deduct from balance
        t_consume = MaterialTransaction(
            material_id=need.material_id,
            factory_id=factory_id,
            type="consume",
            quantity=need.quantity_needed,
            related_position_id=position_id,
            notes=f"Packaging {'box' if need.is_box else 'spacer'} consumed for {needs.size_name}",
            created_by=user_id,
        )
        db.add(t_consume)

        # UNRESERVE transaction — release reservation
        t_unreserve = MaterialTransaction(
            material_id=need.material_id,
            factory_id=factory_id,
            type="unreserve",
            quantity=need.quantity_needed,
            related_position_id=position_id,
            notes=f"Packaging reservation released for {needs.size_name}",
            created_by=user_id,
        )
        db.add(t_unreserve)

        # Deduct from stock balance
        stock = db.query(MaterialStock).filter(
            MaterialStock.material_id == need.material_id,
            MaterialStock.factory_id == factory_id,
        ).first()
        if stock:
            stock.balance -= need.quantity_needed
            stock.updated_at = datetime.now(timezone.utc)
        else:
            logger.warning("No stock record for material %s at factory %s",
                          need.material_id, factory_id)

        consumed.append({
            "material": need.material_name,
            "quantity": float(need.quantity_needed),
        })

    db.flush()
    logger.info("Consumed packaging for position %s: %d materials",
                position_id, len(consumed))
    return {"ok": True, "consumed": consumed}
