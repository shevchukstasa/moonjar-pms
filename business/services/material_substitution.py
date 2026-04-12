"""
Material Substitution service.

Handles interchangeable materials (e.g. CMC ↔ Bentonite).
When one material is insufficient, suggests or auto-applies substitution
from the material_substitutions table.

Key rule: 0.2g CMC = 1g Bentonite (ratio = 5.0)
  → 1 unit CMC can be replaced by 5 units Bentonite
  → 1 unit Bentonite can be replaced by 0.2 units CMC
"""
import logging
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

logger = logging.getLogger("moonjar.material_substitution")


def find_substitutes(db: Session, material_id: UUID) -> list[dict]:
    """Find all active substitutes for a given material.

    Returns list of dicts:
    [
        {
            "substitute_id": UUID,
            "substitute_name": str,
            "ratio": Decimal,        # how many units of substitute per 1 unit of original
            "notes": str,
        }
    ]
    """
    from api.models import MaterialSubstitution, Material

    results = []

    # Case 1: material is material_a → substitute is material_b
    rows_a = (
        db.query(MaterialSubstitution)
        .filter(
            MaterialSubstitution.material_a_id == material_id,
            MaterialSubstitution.is_active.is_(True),
        )
        .all()
    )
    for row in rows_a:
        mat = db.query(Material).filter(Material.id == row.material_b_id).first()
        if mat:
            results.append({
                "substitute_id": row.material_b_id,
                "substitute_name": mat.name,
                "ratio": Decimal(str(row.ratio)),  # 1 unit A → ratio units B
                "notes": row.notes,
            })

    # Case 2: material is material_b → substitute is material_a
    rows_b = (
        db.query(MaterialSubstitution)
        .filter(
            MaterialSubstitution.material_b_id == material_id,
            MaterialSubstitution.is_active.is_(True),
        )
        .all()
    )
    for row in rows_b:
        mat = db.query(Material).filter(Material.id == row.material_a_id).first()
        if mat:
            # Reverse ratio: 1 unit B → (1/ratio) units A
            inverse = (Decimal("1") / Decimal(str(row.ratio))).quantize(Decimal("0.0001"))
            results.append({
                "substitute_id": row.material_a_id,
                "substitute_name": mat.name,
                "ratio": inverse,  # 1 unit B → 1/ratio units A
                "notes": row.notes,
            })

    return results


def check_substitution_available(
    db: Session,
    material_id: UUID,
    factory_id: UUID,
    needed_qty: Decimal,
) -> Optional[dict]:
    """Check if a substitute material has enough stock to cover a deficit.

    Args:
        material_id: the material that is short
        factory_id: factory where stock is checked
        needed_qty: how much of the ORIGINAL material is needed (in stock units)

    Returns:
        dict with substitution details if available, None otherwise:
        {
            "substitute_id": UUID,
            "substitute_name": str,
            "substitute_needed_qty": Decimal,  # in substitute's stock unit
            "substitute_available": Decimal,
            "ratio": Decimal,
            "sufficient": bool,
        }
    """
    from api.models import MaterialStock

    subs = find_substitutes(db, material_id)
    if not subs:
        return None

    for sub in subs:
        substitute_needed = (needed_qty * sub["ratio"]).quantize(Decimal("0.001"))

        stock = (
            db.query(MaterialStock)
            .filter(
                MaterialStock.material_id == sub["substitute_id"],
                MaterialStock.factory_id == factory_id,
            )
            .first()
        )

        available = Decimal(str(stock.balance)) if stock else Decimal("0")

        if available >= substitute_needed:
            return {
                "substitute_id": sub["substitute_id"],
                "substitute_name": sub["substitute_name"],
                "substitute_needed_qty": substitute_needed,
                "substitute_available": available,
                "ratio": sub["ratio"],
                "sufficient": True,
            }

    # Return first substitute even if insufficient (for info)
    if subs:
        first = subs[0]
        substitute_needed = (needed_qty * first["ratio"]).quantize(Decimal("0.001"))
        stock = (
            db.query(MaterialStock)
            .filter(
                MaterialStock.material_id == first["substitute_id"],
                MaterialStock.factory_id == factory_id,
            )
            .first()
        )
        available = Decimal(str(stock.balance)) if stock else Decimal("0")
        return {
            "substitute_id": first["substitute_id"],
            "substitute_name": first["substitute_name"],
            "substitute_needed_qty": substitute_needed,
            "substitute_available": available,
            "ratio": first["ratio"],
            "sufficient": False,
        }

    return None


def get_combined_availability(
    db: Session,
    material_id: UUID,
    factory_id: UUID,
) -> dict:
    """Get total available quantity considering material + all substitutes.

    Returns:
    {
        "material_balance": Decimal,
        "substitutes": [
            {"id": UUID, "name": str, "balance": Decimal, "equivalent": Decimal, "ratio": Decimal}
        ],
        "total_equivalent": Decimal,  # in terms of original material
    }
    """
    from api.models import MaterialStock

    # Original material stock
    stock = (
        db.query(MaterialStock)
        .filter(
            MaterialStock.material_id == material_id,
            MaterialStock.factory_id == factory_id,
        )
        .first()
    )
    mat_balance = Decimal(str(stock.balance)) if stock else Decimal("0")

    subs_info = []
    total_equiv = mat_balance

    subs = find_substitutes(db, material_id)
    for sub in subs:
        sub_stock = (
            db.query(MaterialStock)
            .filter(
                MaterialStock.material_id == sub["substitute_id"],
                MaterialStock.factory_id == factory_id,
            )
            .first()
        )
        sub_balance = Decimal(str(sub_stock.balance)) if sub_stock else Decimal("0")
        # Convert sub balance back to original material equivalent
        equivalent = (sub_balance / sub["ratio"]).quantize(Decimal("0.001")) if sub["ratio"] else Decimal("0")

        subs_info.append({
            "id": sub["substitute_id"],
            "name": sub["substitute_name"],
            "balance": sub_balance,
            "equivalent": equivalent,
            "ratio": sub["ratio"],
        })
        total_equiv += equivalent

    return {
        "material_balance": mat_balance,
        "substitutes": subs_info,
        "total_equivalent": total_equiv,
    }
