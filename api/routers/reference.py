"""Reference data router — enums + dynamic lookup values for frontend dropdowns."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from decimal import Decimal

from api.database import get_db
from api.auth import get_current_user
from api.roles import require_management
from api.models import (
    Material, OrderPosition, Recipe, ShapeConsumptionCoefficient,
    FiringTemperatureGroup, FiringTemperatureGroupRecipe,
)
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


# ─── Firing Temperature Groups CRUD ────────────────────────

class TemperatureGroupCreate(BaseModel):
    name: str = Field(..., max_length=100, description="Group name, e.g. 'Low Temperature'")
    min_temperature: int = Field(..., ge=0, le=2000, description="Min temperature in °C")
    max_temperature: int = Field(..., ge=0, le=2000, description="Max temperature in °C")
    description: Optional[str] = None
    display_order: int = Field(default=0, description="Sort order in UI")


class TemperatureGroupUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    min_temperature: Optional[int] = Field(None, ge=0, le=2000)
    max_temperature: Optional[int] = Field(None, ge=0, le=2000)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None


class TemperatureGroupRecipeAttach(BaseModel):
    recipe_id: str = Field(..., description="UUID of the recipe to attach")
    is_default: bool = Field(default=False, description="Mark as default recipe for this group")


def _serialize_temperature_group(group: FiringTemperatureGroup) -> dict:
    """Serialize a temperature group with its linked recipes."""
    return {
        "id": str(group.id),
        "name": group.name,
        "min_temperature": group.min_temperature,
        "max_temperature": group.max_temperature,
        "description": group.description,
        "is_active": group.is_active,
        "display_order": group.display_order,
        "created_at": group.created_at.isoformat() if group.created_at else None,
        "updated_at": group.updated_at.isoformat() if group.updated_at else None,
        "recipes": [
            {
                "id": str(link.id),
                "recipe_id": str(link.recipe_id),
                "recipe_name": link.recipe.name if link.recipe else None,
                "recipe_collection": link.recipe.collection if link.recipe else None,
                "is_default": link.is_default,
            }
            for link in (group.recipes or [])
        ],
    }


@router.get("/temperature-groups")
async def list_temperature_groups(
    include_inactive: bool = Query(False, description="Include deactivated groups"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List all firing temperature groups with their attached recipes."""
    query = db.query(FiringTemperatureGroup)
    if not include_inactive:
        query = query.filter(FiringTemperatureGroup.is_active.is_(True))
    groups = query.order_by(FiringTemperatureGroup.display_order, FiringTemperatureGroup.name).all()
    return [_serialize_temperature_group(g) for g in groups]


@router.post("/temperature-groups", status_code=201)
async def create_temperature_group(
    body: TemperatureGroupCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Create a new firing temperature group. PM/Admin only."""
    import uuid

    if body.min_temperature >= body.max_temperature:
        raise HTTPException(400, "min_temperature must be less than max_temperature")

    group = FiringTemperatureGroup(
        id=uuid.uuid4(),
        name=body.name,
        min_temperature=body.min_temperature,
        max_temperature=body.max_temperature,
        description=body.description,
        display_order=body.display_order,
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    return _serialize_temperature_group(group)


@router.put("/temperature-groups/{group_id}")
async def update_temperature_group(
    group_id: str,
    body: TemperatureGroupUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Update a firing temperature group. PM/Admin only."""
    import uuid as uuid_mod

    group = db.query(FiringTemperatureGroup).filter(
        FiringTemperatureGroup.id == uuid_mod.UUID(group_id)
    ).first()
    if not group:
        raise HTTPException(404, "Temperature group not found")

    if body.name is not None:
        group.name = body.name
    if body.min_temperature is not None:
        group.min_temperature = body.min_temperature
    if body.max_temperature is not None:
        group.max_temperature = body.max_temperature
    if body.description is not None:
        group.description = body.description
    if body.is_active is not None:
        group.is_active = body.is_active
    if body.display_order is not None:
        group.display_order = body.display_order

    # Validate range after updates
    if group.min_temperature >= group.max_temperature:
        raise HTTPException(400, "min_temperature must be less than max_temperature")

    group.updated_at = func.now()
    db.commit()
    db.refresh(group)
    return _serialize_temperature_group(group)


@router.post("/temperature-groups/{group_id}/recipes", status_code=201)
async def attach_recipe_to_temperature_group(
    group_id: str,
    body: TemperatureGroupRecipeAttach,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Attach a recipe to a temperature group. PM/Admin only."""
    import uuid as uuid_mod

    group = db.query(FiringTemperatureGroup).filter(
        FiringTemperatureGroup.id == uuid_mod.UUID(group_id)
    ).first()
    if not group:
        raise HTTPException(404, "Temperature group not found")

    recipe = db.query(Recipe).filter(Recipe.id == uuid_mod.UUID(body.recipe_id)).first()
    if not recipe:
        raise HTTPException(404, "Recipe not found")

    # Check for duplicate
    existing = db.query(FiringTemperatureGroupRecipe).filter(
        FiringTemperatureGroupRecipe.temperature_group_id == group.id,
        FiringTemperatureGroupRecipe.recipe_id == recipe.id,
    ).first()
    if existing:
        raise HTTPException(409, "Recipe is already attached to this temperature group")

    # If marking as default, clear other defaults in this group
    if body.is_default:
        db.query(FiringTemperatureGroupRecipe).filter(
            FiringTemperatureGroupRecipe.temperature_group_id == group.id,
            FiringTemperatureGroupRecipe.is_default.is_(True),
        ).update({"is_default": False})

    link = FiringTemperatureGroupRecipe(
        id=uuid_mod.uuid4(),
        temperature_group_id=group.id,
        recipe_id=recipe.id,
        is_default=body.is_default,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return {
        "id": str(link.id),
        "temperature_group_id": str(link.temperature_group_id),
        "recipe_id": str(link.recipe_id),
        "recipe_name": recipe.name,
        "is_default": link.is_default,
    }


@router.delete("/temperature-groups/{group_id}/recipes/{recipe_id}")
async def detach_recipe_from_temperature_group(
    group_id: str,
    recipe_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Detach a recipe from a temperature group. PM/Admin only."""
    import uuid as uuid_mod

    link = db.query(FiringTemperatureGroupRecipe).filter(
        FiringTemperatureGroupRecipe.temperature_group_id == uuid_mod.UUID(group_id),
        FiringTemperatureGroupRecipe.recipe_id == uuid_mod.UUID(recipe_id),
    ).first()
    if not link:
        raise HTTPException(404, "Recipe is not attached to this temperature group")

    db.delete(link)
    db.commit()
    return {"detail": "Recipe detached from temperature group"}
