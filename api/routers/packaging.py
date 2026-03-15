"""CRUD router for packaging box types, capacities, and spacer rules."""

from uuid import UUID
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.roles import require_admin
from api.models import (
    PackagingBoxType, PackagingBoxCapacity, PackagingSpacerRule,
    Material, Size,
)

router = APIRouter()


# ── Pydantic input schemas ──────────────────────────────


class BoxTypeInput(BaseModel):
    material_id: UUID
    name: str
    notes: Optional[str] = None
    is_active: bool = True


class BoxTypeUpdateInput(BaseModel):
    name: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class CapacityInput(BaseModel):
    size_id: UUID
    pieces_per_box: Optional[int] = None
    sqm_per_box: Optional[float] = None


class SpacerRuleInput(BaseModel):
    size_id: UUID
    spacer_material_id: UUID
    qty_per_box: int = 1


# ── Helpers ──────────────────────────────────────────────


def _ev(v):
    return v.value if hasattr(v, 'value') else v


def _serialize_box_type(bt: PackagingBoxType, db: Session) -> dict:
    material = db.query(Material).filter(Material.id == bt.material_id).first()
    capacities = (
        db.query(PackagingBoxCapacity)
        .filter(PackagingBoxCapacity.box_type_id == bt.id)
        .all()
    )
    spacer_rules = (
        db.query(PackagingSpacerRule)
        .filter(PackagingSpacerRule.box_type_id == bt.id)
        .all()
    )

    caps = []
    for c in capacities:
        size = db.query(Size).filter(Size.id == c.size_id).first()
        caps.append({
            "id": str(c.id),
            "size_id": str(c.size_id),
            "size_name": size.name if size else None,
            "pieces_per_box": c.pieces_per_box,
            "sqm_per_box": float(c.sqm_per_box) if c.sqm_per_box else None,
        })

    spacers = []
    for sr in spacer_rules:
        size = db.query(Size).filter(Size.id == sr.size_id).first()
        spacer_mat = db.query(Material).filter(Material.id == sr.spacer_material_id).first()
        spacers.append({
            "id": str(sr.id),
            "size_id": str(sr.size_id),
            "size_name": size.name if size else None,
            "spacer_material_id": str(sr.spacer_material_id),
            "spacer_material_name": spacer_mat.name if spacer_mat else None,
            "spacer_material_code": spacer_mat.material_code if spacer_mat else None,
            "qty_per_box": sr.qty_per_box,
        })

    return {
        "id": str(bt.id),
        "material_id": str(bt.material_id),
        "material_name": material.name if material else None,
        "material_code": material.material_code if material else None,
        "name": bt.name,
        "notes": bt.notes,
        "is_active": bt.is_active,
        "capacities": caps,
        "spacer_rules": spacers,
        "created_at": bt.created_at.isoformat() if bt.created_at else None,
        "updated_at": bt.updated_at.isoformat() if bt.updated_at else None,
    }


# ── Box type CRUD ────────────────────────────────────────


@router.get("")
async def list_box_types(
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """List all packaging box types with capacities and spacer rules."""
    items = db.query(PackagingBoxType).order_by(PackagingBoxType.name).all()
    return {"items": [_serialize_box_type(bt, db) for bt in items], "total": len(items)}


@router.get("/sizes")
async def list_sizes(
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """List all tile sizes for dropdown."""
    sizes = db.query(Size).order_by(Size.name).all()
    return {
        "items": [
            {
                "id": str(s.id),
                "name": s.name,
                "width_mm": s.width_mm,
                "height_mm": s.height_mm,
                "is_custom": s.is_custom,
            }
            for s in sizes
        ]
    }


@router.get("/{box_type_id}")
async def get_box_type(
    box_type_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    bt = db.query(PackagingBoxType).filter(PackagingBoxType.id == box_type_id).first()
    if not bt:
        raise HTTPException(404, "Box type not found")
    return _serialize_box_type(bt, db)


@router.post("", status_code=201)
async def create_box_type(
    data: BoxTypeInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    mat = db.query(Material).filter(Material.id == data.material_id).first()
    if not mat:
        raise HTTPException(404, "Material not found")

    bt = PackagingBoxType(
        material_id=data.material_id,
        name=data.name,
        notes=data.notes,
        is_active=data.is_active,
    )
    db.add(bt)
    db.commit()
    db.refresh(bt)
    return _serialize_box_type(bt, db)


@router.patch("/{box_type_id}")
async def update_box_type(
    box_type_id: UUID,
    data: BoxTypeUpdateInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    bt = db.query(PackagingBoxType).filter(PackagingBoxType.id == box_type_id).first()
    if not bt:
        raise HTTPException(404, "Box type not found")

    if data.name is not None:
        bt.name = data.name
    if data.notes is not None:
        bt.notes = data.notes
    if data.is_active is not None:
        bt.is_active = data.is_active
    bt.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(bt)
    return _serialize_box_type(bt, db)


@router.delete("/{box_type_id}")
async def delete_box_type(
    box_type_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    bt = db.query(PackagingBoxType).filter(PackagingBoxType.id == box_type_id).first()
    if not bt:
        raise HTTPException(404, "Box type not found")
    db.delete(bt)  # CASCADE deletes capacities + spacer rules
    db.commit()
    return {"ok": True}


# ── Capacities (bulk replace) ───────────────────────────


class CapacitiesBulkInput(BaseModel):
    capacities: list[CapacityInput]


@router.put("/{box_type_id}/capacities")
async def set_capacities(
    box_type_id: UUID,
    data: CapacitiesBulkInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Bulk-replace all capacity entries for a box type."""
    bt = db.query(PackagingBoxType).filter(PackagingBoxType.id == box_type_id).first()
    if not bt:
        raise HTTPException(404, "Box type not found")

    if len(data.capacities) > 10:
        raise HTTPException(400, "Maximum 10 capacity entries per box type")

    # Delete existing
    db.query(PackagingBoxCapacity).filter(
        PackagingBoxCapacity.box_type_id == box_type_id
    ).delete()

    # Also clean up spacer rules for sizes that are no longer in capacities
    new_size_ids = {str(c.size_id) for c in data.capacities}

    for cap in data.capacities:
        size = db.query(Size).filter(Size.id == cap.size_id).first()
        if not size:
            raise HTTPException(400, f"Size {cap.size_id} not found")
        if cap.pieces_per_box is None and cap.sqm_per_box is None:
            raise HTTPException(400, f"Either pieces_per_box or sqm_per_box required for size {size.name}")

        db.add(PackagingBoxCapacity(
            box_type_id=box_type_id,
            size_id=cap.size_id,
            pieces_per_box=cap.pieces_per_box,
            sqm_per_box=cap.sqm_per_box,
        ))

    bt.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(bt)
    return _serialize_box_type(bt, db)


# ── Spacer rules (bulk replace) ─────────────────────────


class SpacersBulkInput(BaseModel):
    spacers: list[SpacerRuleInput]


@router.put("/{box_type_id}/spacers")
async def set_spacers(
    box_type_id: UUID,
    data: SpacersBulkInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Bulk-replace all spacer rules for a box type."""
    bt = db.query(PackagingBoxType).filter(PackagingBoxType.id == box_type_id).first()
    if not bt:
        raise HTTPException(404, "Box type not found")

    # Delete existing spacer rules
    db.query(PackagingSpacerRule).filter(
        PackagingSpacerRule.box_type_id == box_type_id
    ).delete()

    for sr in data.spacers:
        size = db.query(Size).filter(Size.id == sr.size_id).first()
        if not size:
            raise HTTPException(400, f"Size {sr.size_id} not found")
        spacer_mat = db.query(Material).filter(Material.id == sr.spacer_material_id).first()
        if not spacer_mat:
            raise HTTPException(400, f"Spacer material {sr.spacer_material_id} not found")

        db.add(PackagingSpacerRule(
            box_type_id=box_type_id,
            size_id=sr.size_id,
            spacer_material_id=sr.spacer_material_id,
            qty_per_box=sr.qty_per_box,
        ))

    bt.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(bt)
    return _serialize_box_type(bt, db)
