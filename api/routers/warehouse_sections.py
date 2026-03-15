"""CRUD router for warehouse_sections — evolved for independent warehouses."""

from uuid import UUID
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.roles import require_admin
from api.models import WarehouseSection, User, Factory
from api.schemas import WarehouseSectionCreate, WarehouseSectionUpdate, WarehouseSectionResponse

router = APIRouter()


def _serialize(item: WarehouseSection, db: Session) -> dict:
    """Serialize a WarehouseSection with computed fields."""
    d = WarehouseSectionResponse.model_validate(item).model_dump(mode="json")
    # Compute managed_by_name
    if item.managed_by:
        user = db.query(User.name).filter(User.id == item.managed_by).first()
        d["managed_by_name"] = user.name if user else None
    else:
        d["managed_by_name"] = None
    # Add factory_name for convenience
    if item.factory_id:
        factory = db.query(Factory.name).filter(Factory.id == item.factory_id).first()
        d["factory_name"] = factory.name if factory else None
    else:
        d["factory_name"] = None
    return d


@router.get("", response_model=dict)
async def list_warehouse_sections(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    factory_id: UUID | None = None,
    warehouse_type: str | None = None,
    managed_by: UUID | None = None,
    include_global: bool = True,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List warehouse sections with optional filters."""
    query = db.query(WarehouseSection)
    if factory_id:
        if include_global:
            query = query.filter(
                or_(
                    WarehouseSection.factory_id == factory_id,
                    WarehouseSection.factory_id.is_(None),
                )
            )
        else:
            query = query.filter(WarehouseSection.factory_id == factory_id)
    if warehouse_type:
        query = query.filter(WarehouseSection.warehouse_type == warehouse_type)
    if managed_by:
        query = query.filter(WarehouseSection.managed_by == managed_by)

    query = query.filter(WarehouseSection.is_active.is_(True))

    total = query.count()
    items = (
        query.order_by(WarehouseSection.display_order, WarehouseSection.name)
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return {
        "items": [_serialize(item, db) for item in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/all", response_model=dict)
async def list_all_warehouse_sections(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """List ALL warehouse sections (admin view, including inactive)."""
    query = db.query(WarehouseSection)
    if not include_inactive:
        query = query.filter(WarehouseSection.is_active.is_(True))
    items = query.order_by(WarehouseSection.display_order, WarehouseSection.name).all()
    return {
        "items": [_serialize(item, db) for item in items],
        "total": len(items),
    }


@router.get("/{item_id}")
async def get_warehouse_section(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(WarehouseSection).filter(WarehouseSection.id == item_id).first()
    if not item:
        raise HTTPException(404, "WarehouseSection not found")
    return _serialize(item, db)


@router.post("", status_code=201)
async def create_warehouse_section(
    data: WarehouseSectionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Create a new warehouse section. Owner/Admin only."""
    item = WarehouseSection(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize(item, db)


@router.patch("/{item_id}")
async def update_warehouse_section(
    item_id: UUID,
    data: WarehouseSectionUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Update a warehouse section. Owner/Admin only."""
    item = db.query(WarehouseSection).filter(WarehouseSection.id == item_id).first()
    if not item:
        raise HTTPException(404, "WarehouseSection not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    item.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)
    return _serialize(item, db)


@router.delete("/{item_id}", status_code=204)
async def delete_warehouse_section(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Delete a warehouse section. Owner/Admin only."""
    item = db.query(WarehouseSection).filter(WarehouseSection.id == item_id).first()
    if not item:
        raise HTTPException(404, "WarehouseSection not found")
    db.delete(item)
    db.commit()
