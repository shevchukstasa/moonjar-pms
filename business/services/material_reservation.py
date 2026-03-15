"""
Material Reservation service.
Business Logic: §4

Handles:
- Automatic material reservation when order positions are created
- Force-reservation (PM override for insufficient materials)
- Unreserving materials when positions are cancelled
- Auto-creation of purchase requests for shortages
- Smart material availability check (ordered material awareness)
"""
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID
from typing import Optional

from sqlalchemy.orm import Session
import logging

logger = logging.getLogger("moonjar.material_reservation")


# ────────────────────────────────────────────────────────────────
# Data classes
# ────────────────────────────────────────────────────────────────

@dataclass
class MaterialNeed:
    """Single material requirement with availability info."""
    material_id: UUID
    material_name: str
    material_type: str
    required: Decimal
    available: Decimal
    deficit: Decimal
    supplier_id: Optional[UUID]


@dataclass
class ReservationResult:
    """Outcome of a reservation attempt for one position."""
    reserved: list       # MaterialNeed items successfully reserved
    shortages: list      # MaterialNeed items with deficit > 0
    all_sufficient: bool  # True when shortages is empty


# ────────────────────────────────────────────────────────────────
# Helper: Calculate required material quantity per position
# ────────────────────────────────────────────────────────────────

def _get_area_for_position(position) -> Decimal:
    """Get the glazeable surface area (total for all pieces in the position).

    Priority:
    1. glazeable_sqm × quantity (shape-aware area per piece)
    2. quantity_sqm (bounding-box total — legacy fallback)
    3. quantity (treat as per-piece)
    """
    if position.glazeable_sqm and position.glazeable_sqm > 0:
        return Decimal(str(position.glazeable_sqm)) * Decimal(str(position.quantity))
    if position.quantity_sqm and position.quantity_sqm > 0:
        return Decimal(str(position.quantity_sqm))
    return Decimal(str(position.quantity))


def _calculate_required(rm, position, recipe=None) -> Decimal:
    """Calculate required material quantity based on recipe-material unit.

    Units:
    - per_sqm:    qty_per_unit × total_glazeable_area (m²)
    - g_per_100g: qty_per_unit is grams per 100g of dry glaze batch.
                  Formula: area × rate_ml_per_sqm → total_ml × SG → total_grams
                  Then: (qty_per_100g / 100) × total_grams
                  Rate is chosen by position.application_type (spray/brush).
    - per_piece:  qty_per_unit × quantity (default)

    Args:
        rm: RecipeMaterial row
        position: OrderPosition / ProductionOrderItem
        recipe: Recipe object (optional, falls back to rm.recipe)
    """
    qty = Decimal(str(rm.quantity_per_unit))

    if rm.unit == "per_sqm":
        area = _get_area_for_position(position)
        return qty * area

    if rm.unit == "g_per_100g":
        area = _get_area_for_position(position)

        # Resolve recipe object
        r = recipe
        if not r:
            try:
                if hasattr(rm, 'recipe') and rm.recipe:
                    r = rm.recipe
            except Exception:
                pass

        # Determine consumption rate (ml/m²) based on application type
        rate_ml_per_sqm = Decimal("500")  # default fallback
        if r:
            app_type = (getattr(position, 'application_type', None) or "").lower().strip()
            if app_type == "spray" and r.consumption_spray_ml_per_sqm:
                rate_ml_per_sqm = Decimal(str(r.consumption_spray_ml_per_sqm))
            elif app_type == "brush" and r.consumption_brush_ml_per_sqm:
                rate_ml_per_sqm = Decimal(str(r.consumption_brush_ml_per_sqm))
            elif r.consumption_spray_ml_per_sqm:
                # Default to spray rate if no specific match
                rate_ml_per_sqm = Decimal(str(r.consumption_spray_ml_per_sqm))
            elif r.consumption_brush_ml_per_sqm:
                rate_ml_per_sqm = Decimal(str(r.consumption_brush_ml_per_sqm))
            else:
                # Legacy fallback: glaze_settings.consumption_ml_per_sqm
                gs = r.glaze_settings or {} if hasattr(r, 'glaze_settings') else {}
                if gs.get("consumption_ml_per_sqm"):
                    rate_ml_per_sqm = Decimal(str(gs["consumption_ml_per_sqm"]))

        # Determine SG (specific gravity) for ml → grams conversion
        sg = Decimal("1.0")
        if r and r.specific_gravity and float(r.specific_gravity) > 0:
            sg = Decimal(str(r.specific_gravity))

        # Formula: area × rate_ml → total_ml × SG → total_grams
        total_ml = area * rate_ml_per_sqm
        total_grams = total_ml * sg
        return (qty / Decimal("100")) * total_grams

    # Default: per_piece
    return qty * Decimal(str(position.quantity))


# ────────────────────────────────────────────────────────────────
# §4.0  Smart material availability check
# ────────────────────────────────────────────────────────────────

@dataclass
class SmartAvailabilityResult:
    """Outcome of smart availability check for a single material."""
    available: bool
    reason: str       # "in_stock", "ordered_arriving_in_time", "not_ordered", "ordered_late"
    deficit: Decimal
    ordered_qty: Decimal  # total qty across pending purchase requests


def check_material_availability_smart(
    db: Session,
    material_id: UUID,
    factory_id: UUID,
    required_qty: Decimal,
    effective_available: Decimal,
    planned_glazing_date: Optional[date] = None,
    buffer_days: int = 3,
) -> SmartAvailabilityResult:
    """Check if material will be available when needed.

    Smart blocking rule: do NOT block if material is already ordered
    AND expected to arrive before (planned_glazing_date - buffer_days).

    Returns SmartAvailabilityResult:
    - (True,  "in_stock")                — enough in stock now
    - (True,  "ordered_arriving_in_time") — ordered, will arrive before deadline
    - (False, "not_ordered")             — not enough and not ordered
    - (False, "ordered_late")            — ordered but won't arrive in time
    """
    from api.models import MaterialPurchaseRequest
    from api.enums import PurchaseStatus

    deficit = required_qty - max(effective_available, Decimal("0"))

    # 1. Enough in stock right now — no need to check orders
    if effective_available >= required_qty:
        return SmartAvailabilityResult(
            available=True,
            reason="in_stock",
            deficit=Decimal("0"),
            ordered_qty=Decimal("0"),
        )

    # 2. Not enough in stock — check pending purchase requests
    #    PurchaseStatus has: PENDING, APPROVED, SENT, PARTIALLY_RECEIVED, RECEIVED
    #    Only RECEIVED is terminal (material already counted in stock.balance).
    #    We consider PENDING, APPROVED, SENT, PARTIALLY_RECEIVED as "in-flight".
    active_statuses = [
        PurchaseStatus.PENDING,
        PurchaseStatus.APPROVED,
        PurchaseStatus.SENT,
        PurchaseStatus.PARTIALLY_RECEIVED,
    ]

    pending_requests = (
        db.query(MaterialPurchaseRequest)
        .filter(
            MaterialPurchaseRequest.factory_id == factory_id,
            MaterialPurchaseRequest.status.in_(active_statuses),
        )
        .all()
    )

    # Filter to requests that contain our material_id in materials_json
    # materials_json is a list of dicts: [{"material_id": "...", "quantity": ...}, ...]
    material_id_str = str(material_id)
    relevant_requests = []
    total_ordered_qty = Decimal("0")

    for pr in pending_requests:
        if not pr.materials_json or not isinstance(pr.materials_json, list):
            continue
        for mat_entry in pr.materials_json:
            if mat_entry.get("material_id") == material_id_str:
                qty = Decimal(str(mat_entry.get("quantity", 0)))
                total_ordered_qty += qty
                relevant_requests.append(pr)
                break  # one match per PR is enough

    if not relevant_requests:
        return SmartAvailabilityResult(
            available=False,
            reason="not_ordered",
            deficit=deficit,
            ordered_qty=Decimal("0"),
        )

    # 3. Material is ordered — check if it arrives in time
    if planned_glazing_date:
        deadline = planned_glazing_date - timedelta(days=buffer_days)

        # Check if ANY request with expected_delivery_date arrives by deadline.
        # Requests without expected_delivery_date are treated optimistically
        # (purchaser hasn't set date yet — don't block, they're working on it).
        has_timely_delivery = False
        timely_ordered_qty = Decimal("0")

        for pr in relevant_requests:
            if pr.expected_delivery_date is None:
                # No date set yet — treat as "will arrive in time"
                # (purchaser is still negotiating; don't penalize)
                has_timely_delivery = True
                for mat_entry in pr.materials_json:
                    if mat_entry.get("material_id") == material_id_str:
                        timely_ordered_qty += Decimal(str(mat_entry.get("quantity", 0)))
                        break
            elif pr.expected_delivery_date <= deadline:
                has_timely_delivery = True
                for mat_entry in pr.materials_json:
                    if mat_entry.get("material_id") == material_id_str:
                        timely_ordered_qty += Decimal(str(mat_entry.get("quantity", 0)))
                        break

        if has_timely_delivery:
            timely_projected = max(effective_available, Decimal("0")) + timely_ordered_qty
            if timely_projected >= required_qty:
                return SmartAvailabilityResult(
                    available=True,
                    reason="ordered_arriving_in_time",
                    deficit=deficit,
                    ordered_qty=total_ordered_qty,
                )
            # Enough arriving in time but qty not sufficient
            # — still ordered_late because timely portion doesn't cover need
            return SmartAvailabilityResult(
                available=False,
                reason="ordered_late",
                deficit=deficit,
                ordered_qty=total_ordered_qty,
            )

        # All orders have dates past the deadline
        return SmartAvailabilityResult(
            available=False,
            reason="ordered_late",
            deficit=deficit,
            ordered_qty=total_ordered_qty,
        )

    # 4. No planned glazing date — can't evaluate timing.
    #    Material is ordered → don't block (benefit of the doubt).
    return SmartAvailabilityResult(
        available=True,
        reason="ordered_arriving_in_time",
        deficit=deficit,
        ordered_qty=total_ordered_qty,
    )


# ────────────────────────────────────────────────────────────────
# §4.1  Reserve materials for a single position
# ────────────────────────────────────────────────────────────────

def reserve_materials_for_position(
    db: Session,
    position,                # OrderPosition
    recipe,                  # Recipe
    factory_id: UUID,
) -> ReservationResult:
    """
    For each RecipeMaterial in the recipe:
    1. Calculate required qty = quantity_per_unit * position.quantity
       (if unit is 'per_sqm', use position.quantity_sqm instead)
    2. Compute effective available = stock.balance - net_reserved
       (net_reserved = sum(reserve txns) - sum(unreserve txns))
    3. If effective_available >= required:
       create MaterialTransaction(type=RESERVE), mark position.reservation_at
    4. If effective_available < required:
       add to shortages (do NOT partial-reserve)

    Returns ReservationResult.
    """
    from api.models import RecipeMaterial, MaterialStock, MaterialTransaction, Material
    from api.enums import TransactionType
    from sqlalchemy import func
    from datetime import datetime, timezone

    recipe_materials = (
        db.query(RecipeMaterial)
        .filter(RecipeMaterial.recipe_id == recipe.id)
        .all()
    )

    reserved = []
    shortages = []

    for rm in recipe_materials:
        material = db.query(Material).get(rm.material_id)
        if not material:
            logger.warning(
                "MATERIAL_NOT_FOUND | recipe=%s material_id=%s — skipped",
                recipe.id, rm.material_id,
            )
            continue

        # --- Calculate required quantity ---
        required = _calculate_required(rm, position, recipe=recipe)

        # --- Current stock balance ---
        stock = (
            db.query(MaterialStock)
            .filter(
                MaterialStock.material_id == rm.material_id,
                MaterialStock.factory_id == factory_id,
            )
            .first()
        )
        balance = Decimal(str(stock.balance)) if stock else Decimal("0")

        # --- Net reserved across all positions for this material+factory ---
        total_reserved = (
            db.query(func.coalesce(func.sum(MaterialTransaction.quantity), 0))
            .filter(
                MaterialTransaction.material_id == rm.material_id,
                MaterialTransaction.factory_id == factory_id,
                MaterialTransaction.type == TransactionType.RESERVE,
            )
            .scalar()
        )
        total_unreserved = (
            db.query(func.coalesce(func.sum(MaterialTransaction.quantity), 0))
            .filter(
                MaterialTransaction.material_id == rm.material_id,
                MaterialTransaction.factory_id == factory_id,
                MaterialTransaction.type == TransactionType.UNRESERVE,
            )
            .scalar()
        )
        net_reserved = Decimal(str(total_reserved)) - Decimal(str(total_unreserved))
        effective_available = balance - net_reserved

        # --- Decision ---
        if effective_available >= required:
            txn = MaterialTransaction(
                material_id=rm.material_id,
                factory_id=factory_id,
                type=TransactionType.RESERVE,
                quantity=required,
                related_order_id=position.order_id,
                related_position_id=position.id,
                notes=f"Auto-reserved for position #{position.position_number or ''}",
            )
            db.add(txn)
            reserved.append(MaterialNeed(
                material_id=rm.material_id,
                material_name=material.name,
                material_type=material.material_type or "",
                required=required,
                available=effective_available,
                deficit=Decimal("0"),
                supplier_id=material.supplier_id,
            ))
        else:
            deficit = required - max(effective_available, Decimal("0"))
            shortages.append(MaterialNeed(
                material_id=rm.material_id,
                material_name=material.name,
                material_type=material.material_type or "",
                required=required,
                available=max(effective_available, Decimal("0")),
                deficit=deficit,
                supplier_id=material.supplier_id,
            ))

    # Only stamp reservation_at when ALL materials are sufficient
    if reserved and not shortages:
        from datetime import datetime, timezone
        position.reservation_at = datetime.now(timezone.utc)

    all_ok = len(shortages) == 0
    if all_ok:
        logger.info(
            "MATERIAL_RESERVED | position=%s | %d materials reserved",
            position.id, len(reserved),
        )

    return ReservationResult(
        reserved=reserved,
        shortages=shortages,
        all_sufficient=all_ok,
    )


# ────────────────────────────────────────────────────────────────
# §4.2  Force-reserve (PM override)
# ────────────────────────────────────────────────────────────────

def force_reserve_materials(
    db: Session,
    position,
    recipe,
    factory_id: UUID,
) -> list:
    """
    PM override: reserve materials regardless of balance (can go negative).
    Used when PM force-unblocks an insufficient_materials position.

    Returns list of dicts describing materials that went to negative effective balance.
    """
    from api.models import RecipeMaterial, MaterialStock, MaterialTransaction, Material
    from api.enums import TransactionType
    from sqlalchemy import func
    from datetime import datetime, timezone

    recipe_materials = (
        db.query(RecipeMaterial)
        .filter(RecipeMaterial.recipe_id == recipe.id)
        .all()
    )
    negative_balances = []

    for rm in recipe_materials:
        material = db.query(Material).get(rm.material_id)
        if not material:
            continue

        # Calculate required quantity
        required = _calculate_required(rm, position, recipe=recipe)

        # Create reserve transaction regardless of balance
        txn = MaterialTransaction(
            material_id=rm.material_id,
            factory_id=factory_id,
            type=TransactionType.RESERVE,
            quantity=required,
            related_order_id=position.order_id,
            related_position_id=position.id,
            notes=f"Force-reserved (PM override) for position #{position.position_number or ''}",
        )
        db.add(txn)

        # Check resulting effective balance
        stock = (
            db.query(MaterialStock)
            .filter(
                MaterialStock.material_id == rm.material_id,
                MaterialStock.factory_id == factory_id,
            )
            .first()
        )
        balance = Decimal(str(stock.balance)) if stock else Decimal("0")

        # Existing net reserved (including the txn we just added — not flushed yet,
        # so we calculate from DB + this new amount)
        total_reserved = (
            db.query(func.coalesce(func.sum(MaterialTransaction.quantity), 0))
            .filter(
                MaterialTransaction.material_id == rm.material_id,
                MaterialTransaction.factory_id == factory_id,
                MaterialTransaction.type == TransactionType.RESERVE,
            )
            .scalar()
        )
        total_unreserved = (
            db.query(func.coalesce(func.sum(MaterialTransaction.quantity), 0))
            .filter(
                MaterialTransaction.material_id == rm.material_id,
                MaterialTransaction.factory_id == factory_id,
                MaterialTransaction.type == TransactionType.UNRESERVE,
            )
            .scalar()
        )
        # The new txn hasn't been flushed, so add it manually
        net_after = (
            Decimal(str(total_reserved)) + required
            - Decimal(str(total_unreserved))
        )
        effective_after = balance - net_after

        if effective_after < Decimal("0"):
            negative_balances.append({
                "material_id": str(rm.material_id),
                "material_name": material.name,
                "balance": float(balance),
                "reserved": float(required),
                "resulting_effective": float(effective_after),
            })

    position.reservation_at = datetime.now(timezone.utc)

    logger.warning(
        "FORCE_RESERVE | position=%s | %d materials forced | %d negative",
        position.id, len(recipe_materials), len(negative_balances),
    )
    return negative_balances


# ────────────────────────────────────────────────────────────────
# §4.3  Unreserve (position cancellation / split release)
# ────────────────────────────────────────────────────────────────

def unreserve_materials_for_position(db: Session, position_id: UUID) -> None:
    """
    Remove all reservations for a cancelled/released position.
    Creates UNRESERVE transactions to offset each RESERVE transaction,
    taking into account any partial unreservations already applied.
    """
    from api.models import MaterialTransaction
    from api.enums import TransactionType
    from sqlalchemy import func

    # Find all reserve transactions for this position
    reserves = (
        db.query(MaterialTransaction)
        .filter(
            MaterialTransaction.related_position_id == position_id,
            MaterialTransaction.type == TransactionType.RESERVE,
        )
        .all()
    )

    for reserve_txn in reserves:
        # How much already unreserved for this position + material?
        already_unreserved = (
            db.query(func.coalesce(func.sum(MaterialTransaction.quantity), 0))
            .filter(
                MaterialTransaction.related_position_id == position_id,
                MaterialTransaction.material_id == reserve_txn.material_id,
                MaterialTransaction.type == TransactionType.UNRESERVE,
            )
            .scalar()
        )

        remaining = Decimal(str(reserve_txn.quantity)) - Decimal(str(already_unreserved))
        if remaining > Decimal("0"):
            db.add(MaterialTransaction(
                material_id=reserve_txn.material_id,
                factory_id=reserve_txn.factory_id,
                type=TransactionType.UNRESERVE,
                quantity=remaining,
                related_order_id=reserve_txn.related_order_id,
                related_position_id=position_id,
                notes="Unreserved (position cancelled)",
            ))

    logger.info(
        "UNRESERVE | position=%s | %d reserve txns processed",
        position_id, len(reserves),
    )


# ────────────────────────────────────────────────────────────────
# §4.4  Auto purchase request creation
# ────────────────────────────────────────────────────────────────

def create_auto_purchase_request(
    db: Session,
    factory_id: UUID,
    shortages: list,  # list[MaterialNeed]
    order,            # ProductionOrder
) -> None:
    """
    Create automatic purchase request(s) for material shortages.

    Grouping: by supplier (materials without supplier go to a single catch-all PR).
    Quantity rules:
    - Pigments: exact deficit
    - Stone / frit: max(deficit, avg_monthly_consumption)
    """
    from api.models import MaterialPurchaseRequest, MaterialStock
    from api.enums import PurchaseStatus

    if not shortages:
        return

    # Group by supplier
    by_supplier: dict[str, list] = {}
    for s in shortages:
        key = str(s.supplier_id) if s.supplier_id else "no_supplier"
        by_supplier.setdefault(key, []).append(s)

    requests_created = 0
    for supplier_key, items in by_supplier.items():
        supplier_id_val = None if supplier_key == "no_supplier" else items[0].supplier_id

        materials_json = []
        for item in items:
            quantity = float(item.deficit)

            # Stone / frit: order at least avg monthly consumption
            if item.material_type in ("stone", "frit"):
                stock = (
                    db.query(MaterialStock)
                    .filter(
                        MaterialStock.material_id == item.material_id,
                        MaterialStock.factory_id == factory_id,
                    )
                    .first()
                )
                if stock and stock.avg_monthly_consumption:
                    quantity = max(quantity, float(stock.avg_monthly_consumption))

            materials_json.append({
                "material_id": str(item.material_id),
                "name": item.material_name,
                "quantity": round(quantity, 3),
                "unit": "pcs",
            })

        pr = MaterialPurchaseRequest(
            factory_id=factory_id,
            supplier_id=supplier_id_val,
            materials_json=materials_json,
            status=PurchaseStatus.PENDING,
            source="auto",
            notes=f"Auto: material shortage for order {order.order_number}",
        )
        db.add(pr)
        requests_created += 1

    logger.info(
        "AUTO_PURCHASE_REQUEST | order=%s | shortages=%d materials | %d requests created",
        order.order_number, len(shortages), requests_created,
    )
