"""Stone design catalog — 3D variants / patterns that discriminate materials
of the same size. See BUSINESS_LOGIC_FULL §29.

Photos are optional: the system must render and function with design_name
alone when photo_url is NULL.
"""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.roles import require_admin
from api.models import StoneDesign, Material, User

router = APIRouter()


# ── Serialization ────────────────────────────────────────────────────────

def _serialize(d: StoneDesign, material_count: int = 0) -> dict:
    return {
        "id": str(d.id),
        "code": d.code,
        "name": d.name,
        "name_id": d.name_id,
        "typology": d.typology,
        "photo_url": d.photo_url,
        "description": d.description,
        "display_order": d.display_order,
        "is_active": d.is_active,
        "material_count": material_count,
        "created_at": d.created_at.isoformat() if d.created_at else None,
        "updated_at": d.updated_at.isoformat() if d.updated_at else None,
    }


# ── Pydantic ─────────────────────────────────────────────────────────────

class DesignCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    name_id: Optional[str] = Field(None, max_length=100)
    typology: Optional[str] = Field(None, max_length=30)
    photo_url: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    display_order: Optional[int] = 0


class DesignUpdate(BaseModel):
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    name_id: Optional[str] = Field(None, max_length=100)
    typology: Optional[str] = Field(None, max_length=30)
    photo_url: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


# ── Endpoints ────────────────────────────────────────────────────────────

@router.get("")
async def list_designs(
    typology: Optional[str] = Query(None, description="Filter by typology (3d, tiles, ...)"),
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(StoneDesign)
    if not include_inactive:
        q = q.filter(StoneDesign.is_active.is_(True))
    if typology:
        q = q.filter((StoneDesign.typology == typology) | (StoneDesign.typology.is_(None)))
    rows = q.order_by(StoneDesign.display_order, StoneDesign.name).all()

    # Count materials per design (single aggregate query)
    from sqlalchemy import func
    counts = dict(
        db.query(Material.design_id, func.count(Material.id))
          .filter(Material.design_id.isnot(None))
          .group_by(Material.design_id)
          .all()
    )

    return {
        "items": [_serialize(d, material_count=counts.get(d.id, 0)) for d in rows],
        "total": len(rows),
    }


@router.get("/{design_id}")
async def get_design(
    design_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    d = db.query(StoneDesign).filter(StoneDesign.id == design_id).first()
    if not d:
        raise HTTPException(404, "Design not found")
    from sqlalchemy import func
    count = db.query(func.count(Material.id)).filter(Material.design_id == design_id).scalar() or 0
    return _serialize(d, material_count=count)


@router.post("")
async def create_design(
    data: DesignCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    # Uniqueness check on code
    existing = db.query(StoneDesign).filter(StoneDesign.code == data.code).first()
    if existing:
        raise HTTPException(409, f"Design with code={data.code!r} already exists")

    d = StoneDesign(
        code=data.code.strip(),
        name=data.name.strip(),
        name_id=(data.name_id or "").strip() or None,
        typology=data.typology,
        photo_url=data.photo_url,
        description=data.description,
        display_order=data.display_order or 0,
        is_active=True,
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return _serialize(d, material_count=0)


@router.patch("/{design_id}")
async def update_design(
    design_id: UUID,
    data: DesignUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    d = db.query(StoneDesign).filter(StoneDesign.id == design_id).first()
    if not d:
        raise HTTPException(404, "Design not found")

    updates = data.model_dump(exclude_unset=True)
    if "code" in updates and updates["code"] != d.code:
        clash = db.query(StoneDesign).filter(
            StoneDesign.code == updates["code"],
            StoneDesign.id != design_id,
        ).first()
        if clash:
            raise HTTPException(409, f"Design with code={updates['code']!r} already exists")

    for k, v in updates.items():
        setattr(d, k, v)
    d.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(d)

    from sqlalchemy import func
    count = db.query(func.count(Material.id)).filter(Material.design_id == design_id).scalar() or 0
    return _serialize(d, material_count=count)


@router.delete("/{design_id}")
async def delete_design(
    design_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Soft-delete — mark inactive, do not cascade to materials."""
    d = db.query(StoneDesign).filter(StoneDesign.id == design_id).first()
    if not d:
        raise HTTPException(404, "Design not found")
    # Refuse if any material still linked (force explicit reassignment first)
    from sqlalchemy import func
    count = db.query(func.count(Material.id)).filter(Material.design_id == design_id).scalar() or 0
    if count > 0:
        raise HTTPException(
            409,
            f"Cannot delete — {count} material(s) still use this design. "
            f"Reassign them first or set is_active=false.",
        )
    db.delete(d)
    db.commit()
    return {"status": "deleted", "id": str(design_id)}
