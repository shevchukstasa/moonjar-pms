"""
Material Consumption service.
Business Logic: §16, §21

Handles:
- Converting RESERVE → CONSUME transactions when glazing starts
- Creating ConsumptionAdjustment records when actual ≠ expected
- Refire/reglaze: consuming surface materials only (skip stone)
"""
from decimal import Decimal
from uuid import UUID
from typing import Optional
import logging

from sqlalchemy.orm import Session

from api.unit_conversion import get_calculation_unit, convert_to_stock_unit

logger = logging.getLogger("moonjar.material_consumption")


# ────────────────────────────────────────────────────────────────
# §16  On Glazing Start — consume BOM materials
# ────────────────────────────────────────────────────────────────

def on_glazing_start(
    db: Session,
    position_id: UUID,
    actual_quantities: Optional[dict] = None,
) -> dict:
    """Consume BOM materials when glazing starts.

    1. Load position + recipe + RecipeMaterial BOM list
    2. For each RecipeMaterial → expected = calculate(glazeable_sqm, unit, qty_per_unit)
    3. If actual_quantities provided by glazing master → use factual amounts
    4. Create CONSUME transaction for each material
    5. Create UNRESERVE transaction to release the reservation
    6. If actual ≠ expected → create ConsumptionAdjustment record

    Args:
        db: Database session
        position_id: UUID of the position starting glazing
        actual_quantities: Optional dict {material_id: actual_grams} from glazing master

    Returns:
        dict with consumed materials and any adjustments created
    """
    from api.models import (
        OrderPosition, Recipe, RecipeMaterial, Material,
        MaterialTransaction, MaterialStock, ConsumptionAdjustment,
    )
    from api.enums import TransactionType
    from business.services.material_reservation import _calculate_required

    position = db.query(OrderPosition).get(position_id)
    if not position:
        logger.error("on_glazing_start: position %s not found", position_id)
        return {"error": "Position not found"}

    recipe = db.query(Recipe).get(position.recipe_id) if position.recipe_id else None
    if not recipe:
        logger.warning("on_glazing_start: position %s has no recipe", position_id)
        return {"error": "No recipe assigned"}

    recipe_materials = (
        db.query(RecipeMaterial)
        .filter(RecipeMaterial.recipe_id == recipe.id)
        .all()
    )

    consumed = []
    failed = []
    adjustments = []
    actual_map = actual_quantities or {}

    for rm in recipe_materials:
        # ── PER-MATERIAL ISOLATION ─────────────────────────────────
        # One bad material (missing geometry, broken unit conversion,
        # invalid enum etc.) MUST NOT poison the rest. Anything that
        # raises is logged with full traceback and the loop continues.
        # See docs/BUSINESS_LOGIC_FULL.md §2 → "Consumption: required
        # side-effects".
        try:
            material = db.query(Material).get(rm.material_id)
            if not material:
                continue

            try:
                expected_calc = _calculate_required(rm, position, recipe=recipe)
            except Exception as e:
                logger.error(
                    "CONSUME_CALC_FAIL | position=%s | material=%s | %s",
                    position_id, getattr(material, "name", rm.material_id), e,
                    exc_info=True,
                )
                failed.append({
                    "material_id": str(rm.material_id),
                    "material_name": getattr(material, "name", "?"),
                    "stage": "_calculate_required",
                    "error": str(e),
                })
                continue

            if expected_calc is None or expected_calc <= 0:
                continue

            calc_unit = get_calculation_unit(rm.unit)
            stock_unit = (material.unit or "pcs").lower().strip()
            sg = recipe.specific_gravity if recipe else None

            expected = convert_to_stock_unit(
                expected_calc, calc_unit, stock_unit,
                specific_gravity=sg, material_name=material.name,
            )

            mat_id_str = str(rm.material_id)
            if mat_id_str in actual_map:
                actual = Decimal(str(actual_map[mat_id_str]))
            else:
                actual = expected

            # CONSUME txn (in stock unit)
            db.add(MaterialTransaction(
                material_id=rm.material_id,
                factory_id=position.factory_id,
                type=TransactionType.CONSUME,
                quantity=actual,
                related_order_id=position.order_id,
                related_position_id=position.id,
                notes=f"Glazing consumption for position #{position.position_number or ''}",
            ))

            # UNRESERVE txn to release the reservation
            db.add(MaterialTransaction(
                material_id=rm.material_id,
                factory_id=position.factory_id,
                type=TransactionType.UNRESERVE,
                quantity=expected,
                related_order_id=position.order_id,
                related_position_id=position.id,
                notes="Released reservation (glazing started)",
            ))

            # Deduct from stock balance
            stock = (
                db.query(MaterialStock)
                .filter(
                    MaterialStock.material_id == rm.material_id,
                    MaterialStock.factory_id == position.factory_id,
                )
                .first()
            )
            if stock:
                current_balance = Decimal(str(stock.balance))
                if current_balance < actual:
                    logger.warning(
                        "CONSUME_INSUFFICIENT | position=%s | material=%s | "
                        "balance=%.3f, needed=%.3f — consuming available",
                        position_id, material.name,
                        float(current_balance), float(actual),
                    )
                    actual = current_balance
                stock.balance = current_balance - actual

            consumed.append({
                "material_id": mat_id_str,
                "material_name": material.name,
                "expected": float(expected),
                "actual": float(actual),
                "unit": stock_unit,
            })

            # ConsumptionAdjustment if variance
            if expected > 0 and actual != expected:
                variance_pct = (
                    (actual - expected) / expected * Decimal("100")
                ).quantize(Decimal("0.01"))

                suggested_coeff = None
                shape_val = position.shape.value if position.shape else None
                ptype_val = position.product_type.value if position.product_type else None

                if expected > 0 and shape_val:
                    from business.services.surface_area import get_shape_coefficient
                    current_coeff = get_shape_coefficient(db, shape_val, ptype_val or "tile")
                    suggested_coeff = Decimal(str(current_coeff)) * (actual / expected)
                    suggested_coeff = suggested_coeff.quantize(Decimal("0.001"))

                db.add(ConsumptionAdjustment(
                    factory_id=position.factory_id,
                    position_id=position.id,
                    material_id=rm.material_id,
                    expected_qty=expected,
                    actual_qty=actual,
                    variance_pct=variance_pct,
                    shape=shape_val,
                    product_type=ptype_val,
                    suggested_coefficient=suggested_coeff,
                    status="pending",
                ))
                adjustments.append({
                    "material_name": material.name,
                    "expected": float(expected),
                    "actual": float(actual),
                    "variance_pct": float(variance_pct),
                    "suggested_coefficient": (
                        float(suggested_coeff) if suggested_coeff else None
                    ),
                })

        except Exception as e:
            # Catch-all per-material guard — anything else (DB error,
            # decimal overflow, …) gets logged and we move on.
            logger.error(
                "CONSUME_MATERIAL_FAIL | position=%s | material_id=%s | %s",
                position_id, rm.material_id, e, exc_info=True,
            )
            failed.append({
                "material_id": str(rm.material_id),
                "material_name": getattr(
                    db.query(Material).get(rm.material_id), "name", "?",
                ) if rm.material_id else "?",
                "stage": "consume_loop",
                "error": str(e),
            })
            continue

    # Mark position as materials written off — ALWAYS, even when some
    # materials failed. The failed list is logged + returned in the
    # response so callers can surface it. Without this flag the
    # status_machine would re-trigger consumption forever.
    from datetime import datetime, timezone
    position.materials_written_off_at = datetime.now(timezone.utc)

    if failed:
        logger.error(
            "GLAZING_CONSUME_PARTIAL | position=%s | consumed=%d | FAILED=%d | "
            "first_fail=%s",
            position_id, len(consumed), len(failed),
            failed[0] if failed else None,
        )
    else:
        logger.info(
            "GLAZING_CONSUME | position=%s | %d materials consumed | %d adjustments",
            position_id, len(consumed), len(adjustments),
        )

    return {
        "consumed": consumed,
        "failed": failed,
        "adjustments": adjustments,
        "total_consumed": len(consumed),
        "total_failed": len(failed),
    }


# ────────────────────────────────────────────────────────────────
# §21  Refire/Reglaze — consume surface materials only
# ────────────────────────────────────────────────────────────────

# Material types that are surface-only (consumed again on refire/reglaze)
_SURFACE_MATERIAL_TYPES = {"pigment", "frit", "oxide_carbonate", "other_bulk", "glaze_ingredient"}
# Material types to SKIP on refire (base material — stone/body)
_BASE_MATERIAL_TYPES = {"stone", "packaging", "consumable"}


def consume_refire_materials(
    db: Session,
    position_id: UUID,
    actual_quantities: Optional[dict] = None,
) -> dict:
    """Refire/reglaze: consume surface materials only (skip stone/base).

    Called when a position goes back through glazing after a defect.
    Only glaze-related materials (pigments, frits, oxides) are consumed.
    Stone/body materials are NOT consumed again.

    Args:
        db: Database session
        position_id: UUID of the position being refired
        actual_quantities: Optional dict {material_id: actual_grams}

    Returns:
        dict with consumed materials
    """
    from api.models import (
        OrderPosition, Recipe, RecipeMaterial, Material,
        MaterialTransaction, MaterialStock, ConsumptionAdjustment,
    )
    from api.enums import TransactionType
    from business.services.material_reservation import _calculate_required

    position = db.query(OrderPosition).get(position_id)
    if not position:
        logger.error("consume_refire_materials: position %s not found", position_id)
        return {"error": "Position not found"}

    recipe = db.query(Recipe).get(position.recipe_id) if position.recipe_id else None
    if not recipe:
        logger.warning("consume_refire_materials: position %s has no recipe", position_id)
        return {"error": "No recipe assigned"}

    recipe_materials = (
        db.query(RecipeMaterial)
        .filter(RecipeMaterial.recipe_id == recipe.id)
        .all()
    )

    consumed = []
    actual_map = actual_quantities or {}

    for rm in recipe_materials:
        material = db.query(Material).get(rm.material_id)
        if not material:
            continue

        # Skip non-surface materials (stone, packaging, etc.)
        mat_type = material.material_type or ""
        if mat_type in _BASE_MATERIAL_TYPES:
            continue

        # Expected quantity from calculation (in recipe's calculation unit)
        expected_calc = _calculate_required(rm, position, recipe=recipe)

        # Determine units for conversion
        calc_unit = get_calculation_unit(rm.unit)
        stock_unit = (material.unit or "pcs").lower().strip()
        sg = recipe.specific_gravity if recipe else None

        # Convert expected to stock unit
        expected = convert_to_stock_unit(
            expected_calc, calc_unit, stock_unit,
            specific_gravity=sg, material_name=material.name,
        )

        # Actual quantity (from glazing master — in stock unit, or use expected)
        mat_id_str = str(rm.material_id)
        if mat_id_str in actual_map:
            actual = Decimal(str(actual_map[mat_id_str]))
        else:
            actual = expected

        # --- CONSUME transaction (in stock unit) ---
        consume_txn = MaterialTransaction(
            material_id=rm.material_id,
            factory_id=position.factory_id,
            type=TransactionType.CONSUME,
            quantity=actual,
            related_order_id=position.order_id,
            related_position_id=position.id,
            notes=f"Refire/reglaze consumption for position #{position.position_number or ''}",
        )
        db.add(consume_txn)

        # --- Deduct from stock (both in stock unit now) ---
        stock = (
            db.query(MaterialStock)
            .filter(
                MaterialStock.material_id == rm.material_id,
                MaterialStock.factory_id == position.factory_id,
            )
            .first()
        )
        if stock:
            current_balance = Decimal(str(stock.balance))
            if current_balance < actual:
                logger.warning(
                    "Insufficient stock for %s (refire): balance=%.3f, needed=%.3f — consuming available",
                    material.name, float(current_balance), float(actual),
                )
                actual = current_balance
            stock.balance = current_balance - actual

        consumed.append({
            "material_id": mat_id_str,
            "material_name": material.name,
            "expected": float(expected),
            "actual": float(actual),
            "unit": stock_unit,
        })

        # --- ConsumptionAdjustment if variance ---
        if expected > 0 and actual != expected:
            variance_pct = ((actual - expected) / expected * Decimal("100")).quantize(Decimal("0.01"))
            adj = ConsumptionAdjustment(
                factory_id=position.factory_id,
                position_id=position.id,
                material_id=rm.material_id,
                expected_qty=expected,
                actual_qty=actual,
                variance_pct=variance_pct,
                shape=position.shape.value if position.shape else None,
                product_type=position.product_type.value if position.product_type else None,
                status="pending",
            )
            db.add(adj)

    logger.info(
        "REFIRE_CONSUME | position=%s | %d surface materials consumed",
        position_id, len(consumed),
    )

    return {
        "consumed": consumed,
        "total_consumed": len(consumed),
    }
