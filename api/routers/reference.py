"""Reference data router — enums + dynamic lookup values for frontend dropdowns."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from decimal import Decimal

from api.database import get_db
from api.auth import get_current_user
from api.roles import require_management
from api.models import Material, OrderPosition, Recipe, ShapeConsumptionCoefficient
from api.enums import (
    ProductType,
    ShapeType,
    BowlShape,
    MaterialType,
    SplitCategory,
    DefectOutcome,
    DefectStage,
    QcStage,
    TaskType,
    BatchStatus,
    PositionStatus,
    OrderStatus,
    NotificationType,
)

router = APIRouter()


def _enum_to_list(enum_cls) -> list[dict]:
    """Convert Python enum to [{value, label}] for frontend dropdowns."""
    return [{"value": e.value, "label": e.value.replace("_", " ").title()} for e in enum_cls]


@router.get("/product-types")
async def list_product_types(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return all product types (enum values)."""
    return _enum_to_list(ProductType)


@router.get("/stone-types")
async def list_stone_types(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return distinct stone material names from the materials table."""
    rows = (
        db.query(Material.name)
        .filter(Material.material_type == "stone")
        .distinct()
        .order_by(Material.name)
        .all()
    )
    return [{"value": r[0], "label": r[0]} for r in rows]


@router.get("/glaze-types")
async def list_glaze_types(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return distinct glaze material names from the materials table."""
    rows = (
        db.query(Material.name)
        .filter(Material.material_type == "glaze")
        .distinct()
        .order_by(Material.name)
        .all()
    )
    return [{"value": r[0], "label": r[0]} for r in rows]


@router.get("/finish-types")
async def list_finish_types(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return distinct finishing values from existing order positions."""
    rows = (
        db.query(OrderPosition.finishing)
        .filter(OrderPosition.finishing.isnot(None))
        .distinct()
        .order_by(OrderPosition.finishing)
        .all()
    )
    return [{"value": r[0], "label": r[0]} for r in rows]


@router.get("/shape-types")
async def list_shape_types(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return all shape types (enum values)."""
    return _enum_to_list(ShapeType)


@router.get("/material-types")
async def list_material_types(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return all material types (enum values)."""
    return _enum_to_list(MaterialType)


@router.get("/position-statuses")
async def list_position_statuses(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return all position statuses (enum values)."""
    return _enum_to_list(PositionStatus)


@router.get("/collections")
async def list_collections(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return distinct collection names from recipes + order positions."""
    recipe_cols = (
        db.query(Recipe.collection)
        .filter(Recipe.collection.isnot(None))
        .distinct()
        .all()
    )
    pos_cols = (
        db.query(OrderPosition.collection)
        .filter(OrderPosition.collection.isnot(None))
        .distinct()
        .all()
    )
    all_cols = sorted({r[0] for r in recipe_cols} | {r[0] for r in pos_cols})
    return [{"value": c, "label": c} for c in all_cols]


@router.get("/all")
async def list_all_reference_data(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return all reference data in a single payload (for initial frontend load)."""
    # Static enums
    result = {
        "product_types": _enum_to_list(ProductType),
        "shape_types": _enum_to_list(ShapeType),
        "material_types": _enum_to_list(MaterialType),
        "position_statuses": _enum_to_list(PositionStatus),
        "order_statuses": _enum_to_list(OrderStatus),
        "split_categories": _enum_to_list(SplitCategory),
        "defect_outcomes": _enum_to_list(DefectOutcome),
        "defect_stages": _enum_to_list(DefectStage),
        "qc_stages": _enum_to_list(QcStage),
        "task_types": _enum_to_list(TaskType),
        "batch_statuses": _enum_to_list(BatchStatus),
        "notification_types": _enum_to_list(NotificationType),
    }

    # Dynamic from DB
    stone_rows = (
        db.query(Material.name)
        .filter(Material.material_type == "stone")
        .distinct().order_by(Material.name).all()
    )
    result["stone_types"] = [{"value": r[0], "label": r[0]} for r in stone_rows]

    glaze_rows = (
        db.query(Material.name)
        .filter(Material.material_type == "glaze")
        .distinct().order_by(Material.name).all()
    )
    result["glaze_types"] = [{"value": r[0], "label": r[0]} for r in glaze_rows]

    finish_rows = (
        db.query(OrderPosition.finishing)
        .filter(OrderPosition.finishing.isnot(None))
        .distinct().order_by(OrderPosition.finishing).all()
    )
    result["finish_types"] = [{"value": r[0], "label": r[0]} for r in finish_rows]

    recipe_cols = db.query(Recipe.collection).filter(Recipe.collection.isnot(None)).distinct().all()
    pos_cols = db.query(OrderPosition.collection).filter(OrderPosition.collection.isnot(None)).distinct().all()
    all_cols = sorted({r[0] for r in recipe_cols} | {r[0] for r in pos_cols})
    result["collections"] = [{"value": c, "label": c} for c in all_cols]

    # Shape consumption coefficients
    coeff_rows = db.query(ShapeConsumptionCoefficient).order_by(
        ShapeConsumptionCoefficient.shape, ShapeConsumptionCoefficient.product_type
    ).all()
    result["shape_coefficients"] = [
        {
            "id": str(c.id), "shape": c.shape, "product_type": c.product_type,
            "coefficient": float(c.coefficient), "description": c.description,
        }
        for c in coeff_rows
    ]
    result["bowl_shapes"] = _enum_to_list(BowlShape)

    return result


# ─── Shape Consumption Coefficients CRUD ──────────────────

class ShapeCoefficientUpdate(BaseModel):
    coefficient: float = Field(..., gt=0, le=10.0, description="Area conversion coefficient")
    description: Optional[str] = None


@router.get("/shape-coefficients")
async def list_shape_coefficients(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List all shape consumption coefficients."""
    rows = db.query(ShapeConsumptionCoefficient).order_by(
        ShapeConsumptionCoefficient.shape,
        ShapeConsumptionCoefficient.product_type,
    ).all()
    return [
        {
            "id": str(c.id),
            "shape": c.shape,
            "product_type": c.product_type,
            "coefficient": float(c.coefficient),
            "description": c.description,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }
        for c in rows
    ]


@router.put("/shape-coefficients/{shape}/{product_type}")
async def update_shape_coefficient(
    shape: str,
    product_type: str,
    body: ShapeCoefficientUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Update (or create) shape consumption coefficient. PM/Admin only."""
    from sqlalchemy import func as sa_func

    coeff = db.query(ShapeConsumptionCoefficient).filter(
        ShapeConsumptionCoefficient.shape == shape,
        ShapeConsumptionCoefficient.product_type == product_type,
    ).first()

    if coeff:
        coeff.coefficient = Decimal(str(body.coefficient))
        if body.description is not None:
            coeff.description = body.description
        coeff.updated_by = current_user.id
        coeff.updated_at = sa_func.now()
    else:
        import uuid
        coeff = ShapeConsumptionCoefficient(
            id=uuid.uuid4(),
            shape=shape,
            product_type=product_type,
            coefficient=Decimal(str(body.coefficient)),
            description=body.description,
            updated_by=current_user.id,
        )
        db.add(coeff)

    db.commit()
    db.refresh(coeff)
    return {
        "id": str(coeff.id),
        "shape": coeff.shape,
        "product_type": coeff.product_type,
        "coefficient": float(coeff.coefficient),
        "description": coeff.description,
        "updated_at": coeff.updated_at.isoformat() if coeff.updated_at else None,
    }


@router.get("/bowl-shapes")
async def list_bowl_shapes(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return all bowl shape types (for sink configuration)."""
    return _enum_to_list(BowlShape)
