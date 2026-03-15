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


def _norm_dims(d: Optional[dict]) -> Optional[dict]:
    """
    Normalise kiln dimension dict to plain {width, depth, height?} keys.
    Accepts both {width_cm, depth_cm, height_cm} (seed format) and
    {width, depth, height} (frontend format).  height is optional.
    """
    if not d:
        return d
    w = d.get("width") if d.get("width") is not None else d.get("width_cm")
    dp = d.get("depth") if d.get("depth") is not None else d.get("depth_cm")
    h = d.get("height") if d.get("height") is not None else d.get("height_cm")
    result = {}
    if w is not None:
        result["width"] = float(w)
    if dp is not None:
        result["depth"] = float(dp)
    if h is not None:
        result["height"] = float(h)
    return result if result else None


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
        "kiln_dimensions_cm": _norm_dims(resource.kiln_dimensions_cm),
        "kiln_working_area_cm": _norm_dims(resource.kiln_working_area_cm),
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


@router.get("")
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


@router.post("", status_code=201)
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
        kiln_dimensions_cm=_norm_dims(data.kiln_dimensions_cm),
        kiln_working_area_cm=_norm_dims(data.kiln_working_area_cm),
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
        kiln.kiln_dimensions_cm = _norm_dims(data.kiln_dimensions_cm)
    if data.kiln_working_area_cm is not None:
        kiln.kiln_working_area_cm = _norm_dims(data.kiln_working_area_cm)
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

    old_status = _ev(kiln.status)
    kiln.status = status
    kiln.is_active = status == "active"
    kiln.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(kiln)

    # ── Reschedule positions when kiln status changes ──────────
    # If kiln goes to maintenance_emergency or inactive, all positions
    # estimated to use this kiln need to be reassigned.
    if status in ("maintenance_emergency", "inactive") and old_status == "active":
        try:
            from business.services.production_scheduler import reschedule_affected_by_kiln
            count = reschedule_affected_by_kiln(db, kiln_id)
            if count > 0:
                db.commit()
        except Exception as e:
            import logging
            logging.getLogger("moonjar.kilns").warning(
                "Failed to reschedule after kiln %s status change: %s", kiln_id, e,
            )

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

    from api.models import Batch
    from api.enums import BatchStatus

    # BatchStatus values: suggested | planned | in_progress | done  (no "completed"/"cancelled")
    # Non-terminal = anything that is NOT done
    non_done_statuses = [BatchStatus.SUGGESTED, BatchStatus.PLANNED, BatchStatus.IN_PROGRESS]
    active_batches = db.query(Batch).filter(
        Batch.resource_id == kiln_id,
        Batch.status.in_(non_done_statuses),
    ).count()
    if active_batches > 0:
        raise HTTPException(
            409,
            f"Cannot delete kiln: {active_batches} active batch(es) are in progress. "
            "Complete or reassign them first.",
        )

    # Even done batches reference the kiln via FK — deleting the kiln would
    # violate the constraint.  Prefer setting status to 'inactive' for kilns
    # with historical data.
    historical_batches = db.query(Batch).filter(Batch.resource_id == kiln_id).count()
    if historical_batches > 0:
        raise HTTPException(
            409,
            f"Cannot delete kiln: {historical_batches} historical batch record(s) still reference it. "
            "Set the kiln status to 'inactive' instead of deleting.",
        )

    try:
        db.delete(kiln)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            409,
            "Cannot delete kiln: other records still reference it. "
            "Set the kiln status to 'inactive' instead of deleting.",
        )
