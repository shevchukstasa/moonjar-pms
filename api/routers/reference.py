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
    Collection, ColorCollection, Color, ApplicationType, PlacesOfApplication, FinishingType,
    Supplier, Size, WarehouseSection,
    ApplicationMethod, ApplicationCollection,
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
    """Return material types from subgroups (dynamic) with enum fallback."""
    from api.models import MaterialSubgroup
    subgroups = (
        db.query(MaterialSubgroup)
        .filter(MaterialSubgroup.is_active.is_(True))
        .order_by(MaterialSubgroup.display_order)
        .all()
    )
    if subgroups:
        return [{"value": sg.code, "label": sg.name} for sg in subgroups]
    # Fallback to enum if no subgroups seeded yet
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
    """Return all collections from the collections table."""
    rows = db.query(Collection).order_by(Collection.name).all()
    return [
        {"id": str(r.id), "name": r.name, "created_at": r.created_at.isoformat() if r.created_at else None}
        for r in rows
    ]


@router.get("/application-methods")
async def list_application_methods(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List all application methods (SS, S, BS, etc.)."""
    methods = db.query(ApplicationMethod).filter(
        ApplicationMethod.is_active == True
    ).order_by(ApplicationMethod.sort_order).all()
    return [
        {
            "id": str(m.id), "code": m.code, "name": m.name,
            "engobe_method": m.engobe_method, "glaze_method": m.glaze_method,
            "needs_engobe": m.needs_engobe, "two_stage_firing": m.two_stage_firing,
            "special_kiln": m.special_kiln, "consumption_group_glaze": m.consumption_group_glaze,
            "blocking_task_type": m.blocking_task_type,
        }
        for m in methods
    ]


@router.get("/application-collections")
async def list_application_collections(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List all application collections (Authentic, Creative, Exclusive, etc.)."""
    collections = db.query(ApplicationCollection).filter(
        ApplicationCollection.is_active == True
    ).order_by(ApplicationCollection.sort_order).all()
    return [
        {
            "id": str(c.id), "code": c.code, "name": c.name,
            "allowed_methods": c.allowed_methods, "any_method": c.any_method,
            "no_base_colors": c.no_base_colors, "no_base_sizes": c.no_base_sizes,
            "product_type_restriction": c.product_type_restriction,
        }
        for c in collections
    ]


@router.get("/all")
async def list_all_reference_data(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return all reference data in a single payload (for initial frontend load)."""
    from api.models import MaterialSubgroup, MaterialGroup
    from sqlalchemy.orm import joinedload

    # Dynamic material types from subgroups (with enum fallback)
    subgroups = (
        db.query(MaterialSubgroup)
        .filter(MaterialSubgroup.is_active.is_(True))
        .order_by(MaterialSubgroup.display_order)
        .all()
    )
    material_types_list = (
        [{"value": sg.code, "label": sg.name} for sg in subgroups]
        if subgroups else _enum_to_list(MaterialType)
    )

    # Material groups hierarchy
    groups = (
        db.query(MaterialGroup)
        .options(joinedload(MaterialGroup.subgroups))
        .filter(MaterialGroup.is_active.is_(True))
        .order_by(MaterialGroup.display_order)
        .all()
    )
    material_groups_list = [
        {
            "id": str(g.id),
            "name": g.name,
            "code": g.code,
            "subgroups": [
                {"id": str(sg.id), "code": sg.code, "name": sg.name}
                for sg in (g.subgroups or []) if sg.is_active
            ],
        }
        for g in groups
    ]

    # Static enums
    result = {
        "product_types": _enum_to_list(ProductType),
        "shape_types": _enum_to_list(ShapeType),
        "material_types": material_types_list,
        "material_groups": material_groups_list,
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

    recipe_cols = db.query(Recipe.color_collection).filter(Recipe.color_collection.isnot(None)).distinct().all()
    pos_cols = db.query(OrderPosition.collection).filter(OrderPosition.collection.isnot(None)).distinct().all()
    all_cols = sorted({r[0] for r in recipe_cols} | {r[0] for r in pos_cols})
    result["collections"] = [{"value": c, "label": c} for c in all_cols]

    # Color collections (for glaze recipes — separate from product collections)
    cc_rows = db.query(ColorCollection).filter(ColorCollection.is_active.is_(True)).order_by(ColorCollection.name).all()
    result["color_collections"] = [
        {"id": str(cc.id), "value": cc.name, "label": cc.name}
        for cc in cc_rows
    ]

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

    # Application methods & collections
    app_methods = db.query(ApplicationMethod).filter(
        ApplicationMethod.is_active == True
    ).order_by(ApplicationMethod.sort_order).all()
    result["application_methods"] = [
        {
            "id": str(m.id), "code": m.code, "name": m.name,
            "engobe_method": m.engobe_method, "glaze_method": m.glaze_method,
            "needs_engobe": m.needs_engobe, "two_stage_firing": m.two_stage_firing,
            "special_kiln": m.special_kiln, "consumption_group_glaze": m.consumption_group_glaze,
            "blocking_task_type": m.blocking_task_type,
        }
        for m in app_methods
    ]

    app_collections = db.query(ApplicationCollection).filter(
        ApplicationCollection.is_active == True
    ).order_by(ApplicationCollection.sort_order).all()
    result["application_collections"] = [
        {
            "id": str(c.id), "code": c.code, "name": c.name,
            "allowed_methods": c.allowed_methods, "any_method": c.any_method,
            "no_base_colors": c.no_base_colors, "no_base_sizes": c.no_base_sizes,
            "product_type_restriction": c.product_type_restriction,
        }
        for c in app_collections
    ]

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
    temperature: int = Field(..., ge=0, le=2000, description="Working temperature in °C")
    description: Optional[str] = None
    thermocouple: Optional[str] = Field(None, description="chinese | indonesia_manufacture")
    control_cable: Optional[str] = Field(None, description="indonesia_manufacture")
    control_device: Optional[str] = Field(None, description="oven | moonjar")
    display_order: int = Field(default=0, description="Sort order in UI")


class TemperatureGroupUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    temperature: Optional[int] = Field(None, ge=0, le=2000)
    description: Optional[str] = None
    thermocouple: Optional[str] = None
    control_cable: Optional[str] = None
    control_device: Optional[str] = None
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
        "temperature": group.temperature,
        "min_temperature": group.min_temperature,  # deprecated, kept for compat
        "max_temperature": group.max_temperature,  # deprecated, kept for compat
        "description": group.description,
        "thermocouple": group.thermocouple,
        "control_cable": group.control_cable,
        "control_device": group.control_device,
        "is_active": group.is_active,
        "display_order": group.display_order,
        "created_at": group.created_at.isoformat() if group.created_at else None,
        "updated_at": group.updated_at.isoformat() if group.updated_at else None,
        "recipes": [
            {
                "id": str(link.id),
                "recipe_id": str(link.recipe_id),
                "recipe_name": link.recipe.name if link.recipe else None,
                "recipe_color_collection": link.recipe.color_collection if link.recipe else None,
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

    group = FiringTemperatureGroup(
        id=uuid.uuid4(),
        name=body.name,
        temperature=body.temperature,
        min_temperature=body.temperature,  # deprecated compat
        max_temperature=body.temperature,  # deprecated compat
        description=body.description,
        thermocouple=body.thermocouple,
        control_cable=body.control_cable,
        control_device=body.control_device,
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
    if body.temperature is not None:
        group.temperature = body.temperature
        group.min_temperature = body.temperature  # deprecated compat
        group.max_temperature = body.temperature  # deprecated compat
    if body.description is not None:
        group.description = body.description
    if body.thermocouple is not None:
        group.thermocouple = body.thermocouple
    if body.control_cable is not None:
        group.control_cable = body.control_cable
    if body.control_device is not None:
        group.control_device = body.control_device
    if body.is_active is not None:
        group.is_active = body.is_active
    if body.display_order is not None:
        group.display_order = body.display_order

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


# ══════════════════════════════════════════════════════════════════════════
# CRUD for simple reference tables
# ══════════════════════════════════════════════════════════════════════════

import uuid as uuid_mod


# ─── Collections CRUD ────────────────────────────────────────────────────

class CollectionCreate(BaseModel):
    name: str = Field(..., max_length=100)

class CollectionUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)


@router.post("/collections", status_code=201)
async def create_collection(body: CollectionCreate, db: Session = Depends(get_db), current_user=Depends(require_management)):
    existing = db.query(Collection).filter(Collection.name == body.name).first()
    if existing:
        raise HTTPException(409, f"Collection '{body.name}' already exists")
    item = Collection(id=uuid_mod.uuid4(), name=body.name)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": str(item.id), "name": item.name, "created_at": item.created_at.isoformat() if item.created_at else None}


@router.put("/collections/{item_id}")
async def update_collection(item_id: str, body: CollectionUpdate, db: Session = Depends(get_db), current_user=Depends(require_management)):
    item = db.query(Collection).filter(Collection.id == uuid_mod.UUID(item_id)).first()
    if not item:
        raise HTTPException(404, "Collection not found")
    if body.name is not None:
        item.name = body.name
    db.commit()
    db.refresh(item)
    return {"id": str(item.id), "name": item.name, "created_at": item.created_at.isoformat() if item.created_at else None}


@router.delete("/collections/{item_id}")
async def delete_collection(item_id: str, db: Session = Depends(get_db), current_user=Depends(require_management)):
    item = db.query(Collection).filter(Collection.id == uuid_mod.UUID(item_id)).first()
    if not item:
        raise HTTPException(404, "Collection not found")
    db.delete(item)
    db.commit()
    return {"detail": "Deleted"}


# ─── Color Collections CRUD (for glaze recipes) ─────────────────────────

class ColorCollectionCreate(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = Field(None, max_length=255)

class ColorCollectionUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("/color-collections")
async def list_color_collections(
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return all color collections (for glaze recipes)."""
    query = db.query(ColorCollection)
    if not include_inactive:
        query = query.filter(ColorCollection.is_active.is_(True))
    rows = query.order_by(ColorCollection.name).all()
    return [
        {"id": str(r.id), "name": r.name, "description": r.description, "is_active": r.is_active, "created_at": r.created_at.isoformat() if r.created_at else None}
        for r in rows
    ]


@router.post("/color-collections", status_code=201)
async def create_color_collection(body: ColorCollectionCreate, db: Session = Depends(get_db), current_user=Depends(require_management)):
    existing = db.query(ColorCollection).filter(ColorCollection.name == body.name).first()
    if existing:
        raise HTTPException(409, f"Color collection '{body.name}' already exists")
    item = ColorCollection(id=uuid_mod.uuid4(), name=body.name, description=body.description)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": str(item.id), "name": item.name, "description": item.description, "is_active": item.is_active, "created_at": item.created_at.isoformat() if item.created_at else None}


@router.put("/color-collections/{item_id}")
async def update_color_collection(item_id: str, body: ColorCollectionUpdate, db: Session = Depends(get_db), current_user=Depends(require_management)):
    item = db.query(ColorCollection).filter(ColorCollection.id == uuid_mod.UUID(item_id)).first()
    if not item:
        raise HTTPException(404, "Color collection not found")
    if body.name is not None:
        item.name = body.name
    if body.description is not None:
        item.description = body.description
    if body.is_active is not None:
        item.is_active = body.is_active
    db.commit()
    db.refresh(item)
    return {"id": str(item.id), "name": item.name, "description": item.description, "is_active": item.is_active, "created_at": item.created_at.isoformat() if item.created_at else None}


@router.delete("/color-collections/{item_id}")
async def delete_color_collection(item_id: str, db: Session = Depends(get_db), current_user=Depends(require_management)):
    item = db.query(ColorCollection).filter(ColorCollection.id == uuid_mod.UUID(item_id)).first()
    if not item:
        raise HTTPException(404, "Color collection not found")
    db.delete(item)
    db.commit()
    return {"detail": "Deleted"}


# ─── Colors CRUD ─────────────────────────────────────────────────────────

class ColorCreate(BaseModel):
    name: str = Field(..., max_length=100)
    code: Optional[str] = Field(None, max_length=20)
    is_basic: bool = False

class ColorUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    code: Optional[str] = None
    is_basic: Optional[bool] = None


@router.get("/colors")
async def list_colors(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    rows = db.query(Color).order_by(Color.name).all()
    return [
        {"id": str(r.id), "name": r.name, "code": r.code, "is_basic": r.is_basic, "created_at": r.created_at.isoformat() if r.created_at else None}
        for r in rows
    ]


@router.post("/colors", status_code=201)
async def create_color(body: ColorCreate, db: Session = Depends(get_db), current_user=Depends(require_management)):
    existing = db.query(Color).filter(Color.name == body.name).first()
    if existing:
        raise HTTPException(409, f"Color '{body.name}' already exists")
    item = Color(id=uuid_mod.uuid4(), name=body.name, code=body.code, is_basic=body.is_basic)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": str(item.id), "name": item.name, "code": item.code, "is_basic": item.is_basic, "created_at": item.created_at.isoformat() if item.created_at else None}


@router.put("/colors/{item_id}")
async def update_color(item_id: str, body: ColorUpdate, db: Session = Depends(get_db), current_user=Depends(require_management)):
    item = db.query(Color).filter(Color.id == uuid_mod.UUID(item_id)).first()
    if not item:
        raise HTTPException(404, "Color not found")
    if body.name is not None:
        item.name = body.name
    if body.code is not None:
        item.code = body.code
    if body.is_basic is not None:
        item.is_basic = body.is_basic
    db.commit()
    db.refresh(item)
    return {"id": str(item.id), "name": item.name, "code": item.code, "is_basic": item.is_basic, "created_at": item.created_at.isoformat() if item.created_at else None}


@router.delete("/colors/{item_id}")
async def delete_color(item_id: str, db: Session = Depends(get_db), current_user=Depends(require_management)):
    item = db.query(Color).filter(Color.id == uuid_mod.UUID(item_id)).first()
    if not item:
        raise HTTPException(404, "Color not found")
    db.delete(item)
    db.commit()
    return {"detail": "Deleted"}


# ─── Application Types CRUD ─────────────────────────────────────────────

class AppTypeCreate(BaseModel):
    name: str = Field(..., max_length=100)

class AppTypeUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)


@router.get("/application-types")
async def list_application_types(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    rows = db.query(ApplicationType).order_by(ApplicationType.name).all()
    return [
        {"id": str(r.id), "name": r.name, "created_at": r.created_at.isoformat() if r.created_at else None}
        for r in rows
    ]


@router.post("/application-types", status_code=201)
async def create_application_type(body: AppTypeCreate, db: Session = Depends(get_db), current_user=Depends(require_management)):
    existing = db.query(ApplicationType).filter(ApplicationType.name == body.name).first()
    if existing:
        raise HTTPException(409, f"Application type '{body.name}' already exists")
    item = ApplicationType(id=uuid_mod.uuid4(), name=body.name)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": str(item.id), "name": item.name, "created_at": item.created_at.isoformat() if item.created_at else None}


@router.put("/application-types/{item_id}")
async def update_application_type(item_id: str, body: AppTypeUpdate, db: Session = Depends(get_db), current_user=Depends(require_management)):
    item = db.query(ApplicationType).filter(ApplicationType.id == uuid_mod.UUID(item_id)).first()
    if not item:
        raise HTTPException(404, "Application type not found")
    if body.name is not None:
        item.name = body.name
    db.commit()
    db.refresh(item)
    return {"id": str(item.id), "name": item.name, "created_at": item.created_at.isoformat() if item.created_at else None}


@router.delete("/application-types/{item_id}")
async def delete_application_type(item_id: str, db: Session = Depends(get_db), current_user=Depends(require_management)):
    item = db.query(ApplicationType).filter(ApplicationType.id == uuid_mod.UUID(item_id)).first()
    if not item:
        raise HTTPException(404, "Application type not found")
    db.delete(item)
    db.commit()
    return {"detail": "Deleted"}


# ─── Places of Application CRUD ─────────────────────────────────────────

class PoaCreate(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)

class PoaUpdate(BaseModel):
    code: Optional[str] = Field(None, max_length=50)
    name: Optional[str] = Field(None, max_length=100)


@router.get("/places-of-application")
async def list_places_of_application(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    rows = db.query(PlacesOfApplication).order_by(PlacesOfApplication.name).all()
    return [
        {"id": str(r.id), "code": r.code, "name": r.name, "created_at": r.created_at.isoformat() if r.created_at else None}
        for r in rows
    ]


@router.post("/places-of-application", status_code=201)
async def create_place_of_application(body: PoaCreate, db: Session = Depends(get_db), current_user=Depends(require_management)):
    existing = db.query(PlacesOfApplication).filter(PlacesOfApplication.code == body.code).first()
    if existing:
        raise HTTPException(409, f"Place of application with code '{body.code}' already exists")
    item = PlacesOfApplication(id=uuid_mod.uuid4(), code=body.code, name=body.name)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": str(item.id), "code": item.code, "name": item.name, "created_at": item.created_at.isoformat() if item.created_at else None}


@router.put("/places-of-application/{item_id}")
async def update_place_of_application(item_id: str, body: PoaUpdate, db: Session = Depends(get_db), current_user=Depends(require_management)):
    item = db.query(PlacesOfApplication).filter(PlacesOfApplication.id == uuid_mod.UUID(item_id)).first()
    if not item:
        raise HTTPException(404, "Place of application not found")
    if body.code is not None:
        item.code = body.code
    if body.name is not None:
        item.name = body.name
    db.commit()
    db.refresh(item)
    return {"id": str(item.id), "code": item.code, "name": item.name, "created_at": item.created_at.isoformat() if item.created_at else None}


@router.delete("/places-of-application/{item_id}")
async def delete_place_of_application(item_id: str, db: Session = Depends(get_db), current_user=Depends(require_management)):
    item = db.query(PlacesOfApplication).filter(PlacesOfApplication.id == uuid_mod.UUID(item_id)).first()
    if not item:
        raise HTTPException(404, "Place of application not found")
    db.delete(item)
    db.commit()
    return {"detail": "Deleted"}


# ─── Finishing Types CRUD ────────────────────────────────────────────────

class FinishingTypeCreate(BaseModel):
    name: str = Field(..., max_length=100)

class FinishingTypeUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)


@router.get("/finishing-types")
async def list_finishing_types(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    rows = db.query(FinishingType).order_by(FinishingType.name).all()
    return [
        {"id": str(r.id), "name": r.name, "created_at": r.created_at.isoformat() if r.created_at else None}
        for r in rows
    ]


@router.post("/finishing-types", status_code=201)
async def create_finishing_type(body: FinishingTypeCreate, db: Session = Depends(get_db), current_user=Depends(require_management)):
    existing = db.query(FinishingType).filter(FinishingType.name == body.name).first()
    if existing:
        raise HTTPException(409, f"Finishing type '{body.name}' already exists")
    item = FinishingType(id=uuid_mod.uuid4(), name=body.name)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": str(item.id), "name": item.name, "created_at": item.created_at.isoformat() if item.created_at else None}


@router.put("/finishing-types/{item_id}")
async def update_finishing_type(item_id: str, body: FinishingTypeUpdate, db: Session = Depends(get_db), current_user=Depends(require_management)):
    item = db.query(FinishingType).filter(FinishingType.id == uuid_mod.UUID(item_id)).first()
    if not item:
        raise HTTPException(404, "Finishing type not found")
    if body.name is not None:
        item.name = body.name
    db.commit()
    db.refresh(item)
    return {"id": str(item.id), "name": item.name, "created_at": item.created_at.isoformat() if item.created_at else None}


@router.delete("/finishing-types/{item_id}")
async def delete_finishing_type(item_id: str, db: Session = Depends(get_db), current_user=Depends(require_management)):
    item = db.query(FinishingType).filter(FinishingType.id == uuid_mod.UUID(item_id)).first()
    if not item:
        raise HTTPException(404, "Finishing type not found")
    db.delete(item)
    db.commit()
    return {"detail": "Deleted"}


# ══════════════════════════════════════════════════════════════════════════
# Generic Bulk Import
# ══════════════════════════════════════════════════════════════════════════

class BulkImportRequest(BaseModel):
    entity: str = Field(..., description="Entity type key")
    rows: List[dict] = Field(..., min_length=1, max_length=500)


# Config map: entity key → { model, unique fields, allowed fields, type coercions }
_BULK_ENTITY_CONFIG: dict = {
    "collections":           {"model": Collection,        "unique": ["name"],  "fields": {"name": str}},
    "color_collections":     {"model": ColorCollection,   "unique": ["name"],  "fields": {"name": str, "description": str}},
    "colors":                {"model": Color,             "unique": ["name"],  "fields": {"name": str, "code": str, "is_basic": bool}},
    "application_types":     {"model": ApplicationType,   "unique": ["name"],  "fields": {"name": str}},
    "places_of_application": {"model": PlacesOfApplication, "unique": ["code"], "fields": {"code": str, "name": str}},
    "finishing_types":       {"model": FinishingType,     "unique": ["name"],  "fields": {"name": str}},
    "recipes":               {"model": Recipe,            "unique": ["name"],  "fields": {"name": str, "color_collection": str, "recipe_type": str, "specific_gravity": float, "consumption_spray_ml_per_sqm": float, "consumption_brush_ml_per_sqm": float, "is_default": bool, "is_active": bool}},
    "suppliers":             {"model": Supplier,          "unique": ["name"],  "fields": {"name": str, "contact_person": str, "phone": str, "email": str, "address": str, "default_lead_time_days": int, "notes": str, "is_active": bool}},
    "sizes":                 {"model": Size,              "unique": ["name"],  "fields": {"name": str, "width_mm": int, "height_mm": int, "thickness_mm": int, "shape": str, "is_custom": bool}},
    "temperature_groups":    {"model": FiringTemperatureGroup, "unique": ["name"], "fields": {"name": str, "temperature": int, "description": str, "thermocouple": str, "control_cable": str, "control_device": str, "display_order": int}},
    "warehouse_sections":    {"model": WarehouseSection,  "unique": ["code"],  "fields": {"name": str, "code": str, "description": str, "warehouse_type": str, "display_order": int, "is_default": bool, "is_active": bool}},
    "materials":             {"model": Material,          "unique": ["name"],  "fields": {"name": str, "material_type": str, "unit": str}},
}


def _coerce(value, target_type):
    """Coerce a CSV string value to the target Python type."""
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return None
    if target_type == bool:
        if isinstance(value, bool):
            return value
        return str(value).lower().strip() in ("true", "1", "yes", "da")
    if target_type == int:
        return int(float(value))
    if target_type == float:
        return float(value)
    return str(value).strip()


@router.post("/bulk-import")
async def bulk_import(
    body: BulkImportRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Generic bulk import for any reference entity. PM/Admin only."""
    cfg = _BULK_ENTITY_CONFIG.get(body.entity)
    if not cfg:
        raise HTTPException(400, f"Unknown entity: {body.entity}. Valid: {', '.join(_BULK_ENTITY_CONFIG.keys())}")

    Model = cfg["model"]
    unique_fields = cfg["unique"]
    allowed_fields = cfg["fields"]

    created = 0
    skipped = 0
    errors: list[str] = []

    for i, raw_row in enumerate(body.rows, start=1):
        try:
            # Build cleaned row with type coercion
            row: dict = {}
            for field_name, field_type in allowed_fields.items():
                if field_name in raw_row:
                    val = _coerce(raw_row[field_name], field_type)
                    if val is not None:
                        row[field_name] = val

            # Check required unique fields
            missing = [f for f in unique_fields if not row.get(f)]
            if missing:
                errors.append(f"Row {i}: missing required field(s): {', '.join(missing)}")
                continue

            # Check for duplicate
            filters = [getattr(Model, f) == row[f] for f in unique_fields if f in row]
            existing = db.query(Model).filter(*filters).first() if filters else None
            if existing:
                skipped += 1
                continue

            # Create record
            item = Model(id=uuid_mod.uuid4(), **row)
            db.add(item)
            db.flush()  # Catch DB errors per row
            created += 1
        except Exception as e:
            errors.append(f"Row {i}: {str(e)[:120]}")

    db.commit()
    return {"created": created, "skipped": skipped, "errors": errors}
