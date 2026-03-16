"""CRUD router for tile/stone sizes — a, b, thickness, shape."""

from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_

from api.database import get_db
from api.auth import get_current_user
from api.roles import require_admin_or_pm
from api.models import Size, PackagingBoxCapacity, PackagingSpacerRule

router = APIRouter()


# ── Pydantic schemas ──────────────────────────────────────


class SizeInput(BaseModel):
    name: str
    width_mm: int
    height_mm: int
    thickness_mm: Optional[int] = None
    shape: Optional[str] = "rectangle"
    is_custom: bool = False


class SizeUpdateInput(BaseModel):
    name: Optional[str] = None
    width_mm: Optional[int] = None
    height_mm: Optional[int] = None
    thickness_mm: Optional[int] = None
    shape: Optional[str] = None
    is_custom: Optional[bool] = None


# ── Helpers ───────────────────────────────────────────────

VALID_SHAPES = {"rectangle", "square", "round", "freeform", "triangle", "octagon"}


def _serialize_size(s: Size) -> dict:
    return {
        "id": str(s.id),
        "name": s.name,
        "width_mm": s.width_mm,
        "height_mm": s.height_mm,
        "thickness_mm": s.thickness_mm,
        "shape": s.shape,
        "is_custom": s.is_custom,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


# ── CRUD ──────────────────────────────────────────────────


@router.get("/search")
async def search_sizes(
    q: str | None = Query(None, description="Search by name"),
    width_mm: int | None = Query(None),
    height_mm: int | None = Query(None),
    shape: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Search sizes by dimensions, name, or shape. Used by size resolution UI."""
    query = db.query(Size)

    if width_mm is not None and height_mm is not None:
        # Match both orientations
        query = query.filter(
            or_(
                (Size.width_mm == width_mm) & (Size.height_mm == height_mm),
                (Size.width_mm == height_mm) & (Size.height_mm == width_mm),
            )
        )
    elif width_mm is not None:
        query = query.filter(or_(Size.width_mm == width_mm, Size.height_mm == width_mm))
    elif height_mm is not None:
        query = query.filter(or_(Size.width_mm == height_mm, Size.height_mm == height_mm))

    if shape:
        query = query.filter(Size.shape == shape)

    if q:
        query = query.filter(Size.name.ilike(f"%{q}%"))

    items = query.order_by(Size.name).limit(50).all()
    return [_serialize_size(s) for s in items]


@router.get("")
async def list_sizes(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List all sizes ordered by name."""
    items = db.query(Size).order_by(Size.name).all()
    return {"items": [_serialize_size(s) for s in items], "total": len(items)}


@router.get("/{size_id}")
async def get_size(
    size_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    s = db.query(Size).filter(Size.id == size_id).first()
    if not s:
        raise HTTPException(404, "Size not found")
    return _serialize_size(s)


@router.post("", status_code=201)
async def create_size(
    data: SizeInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin_or_pm),
):
    if data.shape and data.shape not in VALID_SHAPES:
        raise HTTPException(400, f"Invalid shape: {data.shape}. Must be one of: {', '.join(sorted(VALID_SHAPES))}")

    # Check uniqueness
    existing = db.query(Size).filter(Size.name == data.name).first()
    if existing:
        raise HTTPException(409, f"Size with name '{data.name}' already exists")

    s = Size(
        name=data.name,
        width_mm=data.width_mm,
        height_mm=data.height_mm,
        thickness_mm=data.thickness_mm,
        shape=data.shape or "rectangle",
        is_custom=data.is_custom,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return _serialize_size(s)


@router.patch("/{size_id}")
async def update_size(
    size_id: UUID,
    data: SizeUpdateInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin_or_pm),
):
    s = db.query(Size).filter(Size.id == size_id).first()
    if not s:
        raise HTTPException(404, "Size not found")

    if data.shape is not None and data.shape not in VALID_SHAPES:
        raise HTTPException(400, f"Invalid shape: {data.shape}. Must be one of: {', '.join(sorted(VALID_SHAPES))}")

    if data.name is not None:
        dup = db.query(Size).filter(Size.name == data.name, Size.id != size_id).first()
        if dup:
            raise HTTPException(409, f"Size with name '{data.name}' already exists")
        s.name = data.name
    if data.width_mm is not None:
        s.width_mm = data.width_mm
    if data.height_mm is not None:
        s.height_mm = data.height_mm
    if data.thickness_mm is not None:
        s.thickness_mm = data.thickness_mm
    if data.shape is not None:
        s.shape = data.shape
    if data.is_custom is not None:
        s.is_custom = data.is_custom

    db.commit()
    db.refresh(s)
    return _serialize_size(s)


@router.delete("/{size_id}")
async def delete_size(
    size_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin_or_pm),
):
    s = db.query(Size).filter(Size.id == size_id).first()
    if not s:
        raise HTTPException(404, "Size not found")

    # Check if size is used in packaging rules
    cap_count = db.query(PackagingBoxCapacity).filter(PackagingBoxCapacity.size_id == size_id).count()
    spacer_count = db.query(PackagingSpacerRule).filter(PackagingSpacerRule.size_id == size_id).count()
    if cap_count > 0 or spacer_count > 0:
        raise HTTPException(
            409,
            f"Cannot delete size '{s.name}': used in {cap_count} box capacity rule(s) and {spacer_count} spacer rule(s). Remove those first.",
        )

    db.delete(s)
    db.commit()
    return {"ok": True}
