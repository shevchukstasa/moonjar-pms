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

from api.unit_conversion import get_calculation_unit, convert_to_stock_unit

logger = logging.getLogger("moonjar.material_reservation")


# ────────────────────────────────────────────────────────────────
# ConsumptionRule lookup — find best matching override for a position
# ────────────────────────────────────────────────────────────────

def find_best_consumption_rule(db: Session, position, recipe_type: str = "glaze") -> Optional["ConsumptionRule"]:
    """Find the most specific matching ConsumptionRule for a position.

    ConsumptionRule overrides are used for:
    - Non-standard shapes (triangle, octagon, trapezoid, etc.)
    - Sinks and countertops (different application method)
    - Specific size/collection combos that need different rates

    Matching: every non-null field in the rule must match the position.
    The rule with the most matching fields wins (most specific).
    """
    from api.models import ConsumptionRule

    rules = db.query(ConsumptionRule).filter(
        ConsumptionRule.is_active.is_(True),
    ).all()

    if not rules:
        return None

    # Position attributes for matching
    pos_product_type = (getattr(position, 'product_type', None) or '')
    if hasattr(pos_product_type, 'value'):
        pos_product_type = pos_product_type.value
    pos_product_type = pos_product_type.lower().strip()

    pos_shape = (getattr(position, 'shape', None) or '')
    if hasattr(pos_shape, 'value'):
        pos_shape = pos_shape.value
    pos_shape = pos_shape.lower().strip()

    pos_size_id = str(getattr(position, 'size_id', '') or '')
    pos_collection = (getattr(position, 'collection', '') or '').lower().strip()
    pos_color_collection = (getattr(position, 'color_collection', '') or '').lower().strip()
    pos_method = (getattr(position, 'application_method_code', '') or '').lower().strip()
    pos_poa = (getattr(position, 'place_of_application', '') or '').lower().strip()
    pos_thickness = float(getattr(position, 'thickness_mm', 0) or 0)

    best_rule = None
    best_score = -1

    for rule in rules:
        # Filter by recipe_type if specified on rule
        if rule.recipe_type and rule.recipe_type.lower() != recipe_type.lower():
            continue

        score = 0
        match = True

        # Each non-null criterion must match
        if rule.product_type:
            if rule.product_type.lower().strip() == pos_product_type:
                score += 1
            else:
                match = False
                continue

        if rule.shape:
            if rule.shape.lower().strip() == pos_shape:
                score += 1
            else:
                match = False
                continue

        if rule.size_id:
            if str(rule.size_id) == pos_size_id:
                score += 2  # size match is very specific
            else:
                match = False
                continue

        if rule.collection:
            if rule.collection.lower().strip() == pos_collection:
                score += 1
            else:
                match = False
                continue

        if rule.color_collection:
            if rule.color_collection.lower().strip() == pos_color_collection:
                score += 1
            else:
                match = False
                continue

        if rule.application_method:
            if rule.application_method.lower().strip() == pos_method:
                score += 1
            else:
                match = False
                continue

        if rule.place_of_application:
            if rule.place_of_application.lower().strip() == pos_poa:
                score += 1
            else:
                match = False
                continue

        if rule.thickness_mm_min is not None:
            if pos_thickness < float(rule.thickness_mm_min):
                match = False
                continue

        if rule.thickness_mm_max is not None:
            if pos_thickness > float(rule.thickness_mm_max):
                match = False
                continue

        if rule.thickness_mm_min is not None or rule.thickness_mm_max is not None:
            score += 1

        # Use rule.priority as tiebreaker
        effective_score = score * 100 + (rule.priority or 0)

        if match and effective_score > best_score:
            best_score = effective_score
            best_rule = rule

    return best_rule


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

def _get_area_for_position(position, db=None) -> Decimal:
    """Get the total glazeable surface area (face + edges) for the position.

    Priority for face area:
    1. glazeable_sqm × quantity (shape-aware area per piece)
    2. quantity_sqm (bounding-box total — legacy fallback)
    3. quantity (treat as per-piece)

    Edge area is added when the position has edge_profile != 'straight'.
    Edge height is determined by EdgeHeightRule for the tile thickness,
    or defaults to tile thickness if no rule exists.
    """
    # Face area — use defect-adjusted quantity when available
    effective_quantity = (
        getattr(position, 'quantity_with_defect_margin', None) or position.quantity
    )
    if position.glazeable_sqm and position.glazeable_sqm > 0:
        face_total = Decimal(str(position.glazeable_sqm)) * Decimal(str(effective_quantity))
    elif position.quantity_sqm and position.quantity_sqm > 0:
        # quantity_sqm is total area for the order line; scale by defect ratio
        base_qty = position.quantity or 1
        defect_ratio = Decimal(str(effective_quantity)) / Decimal(str(base_qty))
        face_total = Decimal(str(position.quantity_sqm)) * defect_ratio
    else:
        # No area data — calculate glazeable_sqm dynamically instead of
        # using raw quantity (which would be interpreted as m² and give
        # absurdly large material requirements for g_per_100g recipes).
        try:
            from business.services.surface_area import calculate_glazeable_sqm_for_position
            computed_sqm = calculate_glazeable_sqm_for_position(db, position)
            if computed_sqm and float(computed_sqm) > 0:
                # computed_sqm is per-piece; multiply by effective_quantity
                face_total = Decimal(str(computed_sqm)) * Decimal(str(effective_quantity))
                # Cache on position to avoid repeated calculation
                position.glazeable_sqm = computed_sqm
                logger.info(
                    "AREA_COMPUTED | position=%s | glazeable_sqm=%s | total_area=%s",
                    getattr(position, 'id', '?'), computed_sqm, face_total,
                )
            else:
                face_total = Decimal(str(effective_quantity))
        except Exception as exc:
            logger.warning("Failed to compute glazeable_sqm in _get_area_for_position: %s", exc)
            face_total = Decimal(str(effective_quantity))

    # Edge area — only when edge profile requires glazing
    edge_profile = getattr(position, 'edge_profile', None) or 'straight'
    if edge_profile.lower() != 'straight' and db is not None:
        try:
            from business.services.surface_area import (
                calculate_edge_surface,
                get_edge_height_for_thickness,
            )
            thickness_mm = float(position.thickness_mm) if position.thickness_mm else 10.0
            factory_id = getattr(position, 'factory_id', None)
            if not factory_id and hasattr(position, 'order') and position.order:
                factory_id = position.order.factory_id

            edge_height_cm = get_edge_height_for_thickness(
                db, factory_id, thickness_mm
            ) if factory_id else (thickness_mm / 10.0)

            shape = (position.shape.value if hasattr(position.shape, 'value')
                     else str(position.shape)) if position.shape else 'rectangle'
            width_cm = float(position.width_cm) if position.width_cm else 0
            length_cm = float(position.length_cm) if position.length_cm else 0
            edge_sides = int(position.edge_profile_sides) if getattr(position, 'edge_profile_sides', None) else 4

            if width_cm > 0 and length_cm > 0 and edge_height_cm > 0:
                edge_per_piece = calculate_edge_surface(
                    shape, length_cm, width_cm, edge_height_cm, edge_sides
                )
                edge_total = Decimal(str(edge_per_piece)) * Decimal(str(effective_quantity))
                face_total += edge_total
        except Exception as exc:
            logger.debug("Edge area calculation failed: %s", exc)

    return face_total


def _calculate_required(rm, position, recipe=None, db=None) -> Decimal:
    """Calculate required material quantity based on recipe-material unit.

    Units:
    - per_sqm:    rate × total_glazeable_area (m²)
                  Rate may come from method-specific columns on RecipeMaterial
                  (spray_rate, brush_rate, splash_rate, silk_screen_rate) if the
                  position has application_method_code set. Falls back to qty_per_unit.
    - g_per_100g: qty_per_unit is grams per 100g of dry glaze batch.
                  Formula: area × rate_ml_per_sqm → total_ml × SG → total_grams
                  Then: (qty_per_100g / 100) × total_grams
                  Rate is chosen by position.application_method_code (spray/brush).
    - per_piece:  qty_per_unit × quantity (default)

    Args:
        rm: RecipeMaterial row
        position: OrderPosition / ProductionOrderItem
        recipe: Recipe object (optional, falls back to rm.recipe)
    """
    qty = Decimal(str(rm.quantity_per_unit))

    # ── Resolve method-specific rate if available ──
    # Application method codes mapped to consumption groups:
    #   SPRAY methods: ss, s, bs(glaze part), stencil, raku, gold
    #   BRUSH methods: sb(glaze part), splashing
    #   SILK_SCREEN methods: silk_screen
    SPRAY_METHODS = {'ss', 's', 'bs', 'stencil', 'raku', 'gold'}
    BRUSH_METHODS = {'sb', 'splashing'}
    SILK_SCREEN_METHODS = {'silk_screen'}

    method_code = (
        getattr(position, 'application_method_code', None) or ''
    ).lower().strip()

    # ConsumptionRule can override the application method
    cr = getattr(position, '_consumption_rule', None)
    if cr and cr.application_method:
        method_code = cr.application_method.lower().strip()

    def _get_method_rate() -> Optional[Decimal]:
        """Try to get a method-specific rate from RecipeMaterial columns.

        Returns the rate if a method-specific column exists and is set,
        or None to fall back to the default qty_per_unit.

        Special rules:
        - Engobe + method 's': return 0 (S method has no engobe)
        - Engobe + method 'bs': use brush_rate (BS uses brush for engobe)
        """
        if not method_code:
            return None

        # Check if RecipeMaterial has the method-specific columns
        # (Agent 1 adds these — gracefully degrade if not yet present)
        has_method_rates = hasattr(rm, 'spray_rate')
        if not has_method_rates:
            return None

        # Determine material type from the linked material
        mat_type = ''
        if hasattr(rm, 'material') and rm.material:
            mat_type = (getattr(rm.material, 'material_type', '') or '').lower()
        elif hasattr(rm, 'material_type'):
            mat_type = (rm.material_type or '').lower()

        # ── Engobe special rules ──
        if mat_type == 'engobe':
            if method_code == 's':
                return Decimal('0')  # S method has no engobe
            if method_code == 'bs' and rm.brush_rate:
                return Decimal(str(rm.brush_rate))
            if rm.spray_rate:
                return Decimal(str(rm.spray_rate))
            return None  # fall back to default

        # ── Glaze / pigment / oxide materials ──
        if mat_type in ('glaze', 'pigment', 'oxide', 'oxide_carbonate', 'frit'):
            if method_code in SPRAY_METHODS and rm.spray_rate:
                return Decimal(str(rm.spray_rate))
            elif method_code in BRUSH_METHODS and rm.brush_rate:
                return Decimal(str(rm.brush_rate))
            elif method_code == 'splashing' and getattr(rm, 'splash_rate', None):
                return Decimal(str(rm.splash_rate))
            elif method_code in SILK_SCREEN_METHODS and getattr(rm, 'silk_screen_rate', None):
                return Decimal(str(rm.silk_screen_rate))

        return None  # no method-specific rate → use default

    method_rate = _get_method_rate()

    if rm.unit == "per_sqm":
        area = _get_area_for_position(position, db=db)
        rate = method_rate if method_rate is not None else qty
        return rate * area

    if rm.unit == "g_per_100g":
        area = _get_area_for_position(position, db=db)

        # Resolve recipe object
        r = recipe
        if not r:
            try:
                if hasattr(rm, 'recipe') and rm.recipe:
                    r = rm.recipe
            except Exception as e:
                logger.debug("Failed to resolve recipe from rm: %s", e)

        # Check for ConsumptionRule override (pre-attached by caller)
        cr = getattr(position, '_consumption_rule', None)

        # Determine consumption rate (ml/m²) based on application method
        rate_ml_per_sqm = Decimal("500")  # default fallback

        # ConsumptionRule override takes priority
        if cr and cr.consumption_ml_per_sqm:
            rate_ml_per_sqm = Decimal(str(cr.consumption_ml_per_sqm))
            if cr.coats and cr.coats > 1:
                rate_ml_per_sqm *= Decimal(str(cr.coats))
        elif r:
            # Prefer new method_code-based lookup, fall back to legacy application_type
            app_method = method_code or (getattr(position, 'application_type', None) or "").lower().strip()

            if app_method in SPRAY_METHODS and r.consumption_spray_ml_per_sqm:
                rate_ml_per_sqm = Decimal(str(r.consumption_spray_ml_per_sqm))
            elif app_method in BRUSH_METHODS and r.consumption_brush_ml_per_sqm:
                rate_ml_per_sqm = Decimal(str(r.consumption_brush_ml_per_sqm))
            elif app_method == "spray" and r.consumption_spray_ml_per_sqm:
                rate_ml_per_sqm = Decimal(str(r.consumption_spray_ml_per_sqm))
            elif app_method == "brush" and r.consumption_brush_ml_per_sqm:
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
        # ConsumptionRule SG override takes priority over recipe SG
        sg = Decimal("1.0")
        if cr and cr.specific_gravity_override:
            sg = Decimal(str(cr.specific_gravity_override))
        elif r and r.specific_gravity and float(r.specific_gravity) > 0:
            sg = Decimal(str(r.specific_gravity))

        # For g_per_100g, also apply method-specific component ratio if available
        effective_qty = method_rate if method_rate is not None else qty

        # Formula: area × rate_ml → total_ml × SG → total_grams
        total_ml = area * rate_ml_per_sqm
        total_grams = total_ml * sg
        return (effective_qty / Decimal("100")) * total_grams

    # Default: per_piece — use defect-adjusted quantity when available
    effective_quantity = (
        getattr(position, 'quantity_with_defect_margin', None) or position.quantity
    )
    return qty * Decimal(str(effective_quantity))


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
    expected_delivery_date: Optional[date] = None  # earliest delivery date from purchase requests


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

    # Compute earliest expected delivery date across all relevant requests
    _delivery_dates = [
        pr.expected_delivery_date for pr in relevant_requests
        if pr.expected_delivery_date is not None
    ]
    _earliest_delivery = min(_delivery_dates) if _delivery_dates else None

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
                    expected_delivery_date=_earliest_delivery,
                )
            # Enough arriving in time but qty not sufficient
            # — still ordered_late because timely portion doesn't cover need
            return SmartAvailabilityResult(
                available=False,
                reason="ordered_late",
                deficit=deficit,
                ordered_qty=total_ordered_qty,
                expected_delivery_date=_earliest_delivery,
            )

        # All orders have dates past the deadline
        return SmartAvailabilityResult(
            available=False,
            reason="ordered_late",
            deficit=deficit,
            ordered_qty=total_ordered_qty,
            expected_delivery_date=_earliest_delivery,
        )

    # 4. No planned glazing date — can't evaluate timing.
    #    Material is ordered → don't block (benefit of the doubt).
    return SmartAvailabilityResult(
        available=True,
        reason="ordered_arriving_in_time",
        deficit=deficit,
        ordered_qty=total_ordered_qty,
        expected_delivery_date=_earliest_delivery,
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

    # Find best matching ConsumptionRule (if any) for overrides
    try:
        glaze_rule = find_best_consumption_rule(db, position, recipe_type="glaze")
        engobe_rule = find_best_consumption_rule(db, position, recipe_type="engobe")
        if glaze_rule:
            logger.info("CONSUMPTION_RULE | position=%s | glaze override: rule #%d '%s' ml/m²=%.1f",
                        position.id, glaze_rule.rule_number, glaze_rule.name, float(glaze_rule.consumption_ml_per_sqm))
        if engobe_rule:
            logger.info("CONSUMPTION_RULE | position=%s | engobe override: rule #%d '%s' ml/m²=%.1f",
                        position.id, engobe_rule.rule_number, engobe_rule.name, float(engobe_rule.consumption_ml_per_sqm))
    except Exception as e:
        logger.warning("CONSUMPTION_RULE_LOOKUP_FAIL | %s", e)
        glaze_rule = None
        engobe_rule = None

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

        # Determine which consumption rule applies to this material
        mat_type = ''
        if hasattr(rm, 'material') and rm.material:
            mat_type = (getattr(rm.material, 'material_type', '') or '').lower()

        if mat_type == 'engobe' and engobe_rule:
            position._consumption_rule = engobe_rule
        elif glaze_rule:
            position._consumption_rule = glaze_rule
        else:
            position._consumption_rule = None

        # --- Calculate required quantity (with edge area via EdgeHeightRule) ---
        required_calc = _calculate_required(rm, position, recipe=recipe, db=db)

        # --- Convert to stock unit ---
        calc_unit = get_calculation_unit(rm.unit)
        stock_unit = (material.unit or "pcs").lower().strip()
        sg = recipe.specific_gravity if recipe else None
        required = convert_to_stock_unit(
            required_calc, calc_unit, stock_unit,
            specific_gravity=sg, material_name=material.name,
        )

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

        # Calculate required quantity and convert to stock unit
        required_calc = _calculate_required(rm, position, recipe=recipe)
        calc_unit = get_calculation_unit(rm.unit)
        stock_unit = (material.unit or "pcs").lower().strip()
        sg = recipe.specific_gravity if recipe else None
        required = convert_to_stock_unit(
            required_calc, calc_unit, stock_unit,
            specific_gravity=sg, material_name=material.name,
        )

        # Create reserve transaction regardless of balance (in stock unit)
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


# ────────────────────────────────────────────────────────────────
# §4.5  Auto-unblock positions after material receive
# ────────────────────────────────────────────────────────────────

def check_and_unblock_positions_after_receive(
    db: Session,
    material_id: UUID,
    factory_id: UUID,
) -> list[UUID]:
    """
    After material is received, check all INSUFFICIENT_MATERIALS positions
    at this factory. If ALL recipe materials are now available, auto-unblock
    the position back to PLANNED and reserve materials.

    Returns list of position IDs that were unblocked.
    """
    from api.models import (
        OrderPosition, RecipeMaterial, MaterialStock,
        MaterialTransaction, Material, Recipe,
    )
    from api.enums import PositionStatus, TransactionType
    from sqlalchemy import func
    from datetime import datetime, timezone

    # 1. Find all positions stuck in INSUFFICIENT_MATERIALS at this factory
    blocked_positions = (
        db.query(OrderPosition)
        .filter(
            OrderPosition.factory_id == factory_id,
            OrderPosition.status == PositionStatus.INSUFFICIENT_MATERIALS,
            OrderPosition.recipe_id.isnot(None),
        )
        .all()
    )

    if not blocked_positions:
        return []

    unblocked_ids = []

    for position in blocked_positions:
        try:
            recipe = db.query(Recipe).get(position.recipe_id)
            if not recipe:
                continue

            # Get all recipe materials
            recipe_materials = (
                db.query(RecipeMaterial)
                .filter(RecipeMaterial.recipe_id == recipe.id)
                .all()
            )
            if not recipe_materials:
                continue

            # Check if ALL materials are now sufficient
            all_sufficient = True
            for rm in recipe_materials:
                material = db.query(Material).get(rm.material_id)
                if not material:
                    continue

                required_calc = _calculate_required(rm, position, recipe=recipe)
                calc_unit = get_calculation_unit(rm.unit)
                stock_unit = (material.unit or "pcs").lower().strip()
                sg = recipe.specific_gravity if recipe else None
                required = convert_to_stock_unit(
                    required_calc, calc_unit, stock_unit,
                    specific_gravity=sg, material_name=material.name,
                )

                # Current stock balance
                stock = (
                    db.query(MaterialStock)
                    .filter(
                        MaterialStock.material_id == rm.material_id,
                        MaterialStock.factory_id == factory_id,
                    )
                    .first()
                )
                balance = Decimal(str(stock.balance)) if stock else Decimal("0")

                # Net reserved across all positions for this material+factory
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

                if effective_available < required:
                    all_sufficient = False
                    break

            if not all_sufficient:
                continue

            # All materials sufficient — reserve and unblock
            result = reserve_materials_for_position(db, position, recipe, factory_id)

            if result.all_sufficient:
                position.status = PositionStatus.PLANNED
                position.updated_at = datetime.now(timezone.utc)
                unblocked_ids.append(position.id)

                mat_name = (
                    db.query(Material.name)
                    .filter(Material.id == material_id)
                    .scalar()
                ) or str(material_id)

                logger.info(
                    "AUTO_UNBLOCK | position=%s | material received: %s",
                    position.id, mat_name,
                )
            else:
                # Reservation failed (race condition — stock changed between check and reserve)
                # Unreserve any partial reservations that were created
                if result.reserved:
                    for need in result.reserved:
                        unreserve_txns = (
                            db.query(MaterialTransaction)
                            .filter(
                                MaterialTransaction.related_position_id == position.id,
                                MaterialTransaction.material_id == need.material_id,
                                MaterialTransaction.type == TransactionType.RESERVE,
                            )
                            .order_by(MaterialTransaction.created_at.desc())
                            .first()
                        )
                        if unreserve_txns:
                            db.add(MaterialTransaction(
                                material_id=need.material_id,
                                factory_id=factory_id,
                                type=TransactionType.UNRESERVE,
                                quantity=unreserve_txns.quantity,
                                related_order_id=position.order_id,
                                related_position_id=position.id,
                                notes="Rolled back: auto-unblock reservation failed",
                            ))

        except Exception as e:
            logger.warning(
                "AUTO_UNBLOCK_ERROR | position=%s | error=%s",
                position.id, str(e),
            )
            continue

    if unblocked_ids:
        logger.info(
            "AUTO_UNBLOCK_SUMMARY | factory=%s | material=%s | %d positions unblocked",
            factory_id, material_id, len(unblocked_ids),
        )

    return unblocked_ids
