"""Kilns router — kiln management (CRUD on resources table with type='kiln')."""

from uuid import UUID
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.roles import require_management
from api.models import Resource, KilnLoadingRule, Factory, Collection
from api.enums import ResourceType

router = APIRouter()

VALID_KILN_TYPES = ["big", "small", "raku"]
VALID_STATUSES = ["active", "maintenance_planned", "maintenance_emergency", "inactive"]


def _ev(val):
    return val.value if hasattr(val, "value") else str(val) if val else None


def _serialize_kiln(resource: Resource, db: Session) -> dict:
    """Serialize a kiln resource with loading rules and factory name."""
    rules = db.query(KilnLoadingRule).filter(KilnLoadingRule.kiln_id == resource.id).first()
    factory = db.query(Factory).filter(Factory.id == resource.factory_id).first()
    return {
        "id": str(resource.id),
        "name": resource.name,
        "factory_id": str(resource.factory_id),
        "factory_name": factory.name if factory else None,
        "kiln_type": resource.kiln_type,
        "status": _ev(resource.status),
        "kiln_dimensions_cm": resource.kiln_dimensions_cm,
        "kiln_working_area_cm": resource.kiln_working_area_cm,
        "kiln_multi_level": resource.kiln_multi_level,
        "kiln_coefficient": float(resource.kiln_coefficient) if resource.kiln_coefficient else None,
        "num_levels": resource.num_levels,
        "capacity_sqm": float(resource.capacity_sqm) if resource.capacity_sqm else None,
        "capacity_pcs": resource.capacity_pcs,
        "is_active": resource.is_active,
        "loading_rules": rules.rules if rules else None,
        "loading_rules_id": str(rules.id) if rules else None,
        "created_at": resource.created_at.isoformat() if resource.created_at else None,
        "updated_at": resource.updated_at.isoformat() if resource.updated_at else None,
    }


class KilnCreateInput(BaseModel):
    name: str
    factory_id: str
    kiln_type: str
    kiln_dimensions_cm: Optional[dict] = None
    kiln_working_area_cm: Optional[dict] = None
    kiln_multi_level: bool = False
    kiln_coefficient: float = 0.8
    capacity_sqm: Optional[float] = None
    capacity_pcs: Optional[int] = None


class KilnUpdateInput(BaseModel):
    name: Optional[str] = None
    factory_id: Optional[str] = None
    kiln_dimensions_cm: Optional[dict] = None
    kiln_working_area_cm: Optional[dict] = None
    kiln_multi_level: Optional[bool] = None
    kiln_coefficient: Optional[float] = None
    capacity_sqm: Optional[float] = None
    capacity_pcs: Optional[int] = None


# --- Endpoints ---

@router.get("/collections")
async def list_collections(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List all collections (for kiln loading rules configuration)."""
    items = db.query(Collection).order_by(Collection.name).all()
    return {"items": [{"id": str(c.id), "name": c.name} for c in items]}


@router.get("/")
async def list_kilns(
    factory_id: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(Resource).filter(Resource.resource_type == ResourceType.KILN)

    if factory_id:
        query = query.filter(Resource.factory_id == UUID(factory_id))
    if status:
        query = query.filter(Resource.status == status)

    total = query.count()
    kilns = query.order_by(Resource.name).offset((page - 1) * per_page).limit(per_page).all()

    return {
        "items": [_serialize_kiln(k, db) for k in kilns],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/{kiln_id}")
async def get_kiln(
    kiln_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    kiln = db.query(Resource).filter(Resource.id == kiln_id, Resource.resource_type == ResourceType.KILN).first()
    if not kiln:
        raise HTTPException(404, "Kiln not found")
    return _serialize_kiln(kiln, db)


@router.post("/", status_code=201)
async def create_kiln(
    data: KilnCreateInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    if data.kiln_type not in VALID_KILN_TYPES:
        raise HTTPException(422, f"Invalid kiln_type '{data.kiln_type}'. Valid: {', '.join(VALID_KILN_TYPES)}")

    kiln = Resource(
        name=data.name,
        resource_type="kiln",
        factory_id=UUID(data.factory_id),
        kiln_type=data.kiln_type,
        kiln_dimensions_cm=data.kiln_dimensions_cm,
        kiln_working_area_cm=data.kiln_working_area_cm,
        kiln_multi_level=data.kiln_multi_level,
        kiln_coefficient=data.kiln_coefficient,
        capacity_sqm=data.capacity_sqm,
        capacity_pcs=data.capacity_pcs,
        status="active",
        is_active=True,
    )
    db.add(kiln)
    db.commit()
    db.refresh(kiln)
    return _serialize_kiln(kiln, db)


@router.patch("/{kiln_id}")
async def update_kiln(
    kiln_id: UUID,
    data: KilnUpdateInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    kiln = db.query(Resource).filter(Resource.id == kiln_id, Resource.resource_type == ResourceType.KILN).first()
    if not kiln:
        raise HTTPException(404, "Kiln not found")

    if data.name is not None:
        kiln.name = data.name
    if data.factory_id is not None:
        # Validate factory exists
        factory = db.query(Factory).filter(Factory.id == UUID(data.factory_id)).first()
        if not factory:
            raise HTTPException(404, "Factory not found")
        kiln.factory_id = UUID(data.factory_id)
    if data.kiln_dimensions_cm is not None:
        kiln.kiln_dimensions_cm = data.kiln_dimensions_cm
    if data.kiln_working_area_cm is not None:
        kiln.kiln_working_area_cm = data.kiln_working_area_cm
    if data.kiln_multi_level is not None:
        kiln.kiln_multi_level = data.kiln_multi_level
    if data.kiln_coefficient is not None:
        kiln.kiln_coefficient = data.kiln_coefficient
    if data.capacity_sqm is not None:
        kiln.capacity_sqm = data.capacity_sqm
    if data.capacity_pcs is not None:
        kiln.capacity_pcs = data.capacity_pcs

    kiln.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(kiln)
    return _serialize_kiln(kiln, db)


@router.patch("/{kiln_id}/status")
async def update_kiln_status(
    kiln_id: UUID,
    status: str = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    if status not in VALID_STATUSES:
        raise HTTPException(422, f"Invalid status '{status}'. Valid: {', '.join(VALID_STATUSES)}")

    kiln = db.query(Resource).filter(Resource.id == kiln_id, Resource.resource_type == ResourceType.KILN).first()
    if not kiln:
        raise HTTPException(404, "Kiln not found")

    kiln.status = status
    kiln.is_active = status == "active"
    kiln.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(kiln)
    return _serialize_kiln(kiln, db)


@router.delete("/{kiln_id}", status_code=204)
async def delete_kiln(
    kiln_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Delete a kiln. Removes associated loading rules via CASCADE."""
    kiln = db.query(Resource).filter(Resource.id == kiln_id, Resource.resource_type == ResourceType.KILN).first()
    if not kiln:
        raise HTTPException(404, "Kiln not found")

    # Check for active batches
    from api.models import Batch
    active_batches = db.query(Batch).filter(
        Batch.resource_id == kiln_id,
        Batch.status.notin_(["completed", "cancelled"]),
    ).count()
    if active_batches > 0:
        raise HTTPException(
            409, f"Cannot delete kiln with {active_batches} active batch(es). Complete or cancel them first."
        )

    db.delete(kiln)
    db.commit()
