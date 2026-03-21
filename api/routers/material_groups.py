"""Material Groups & Subgroups — hierarchical material categorization."""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from api.database import get_db
from api.auth import get_current_user
from api.roles import require_admin

logger = logging.getLogger("moonjar.material_groups")

router = APIRouter()


# ────────────────────────────────────────────────────────────────
# Pydantic schemas
# ────────────────────────────────────────────────────────────────

class MaterialGroupInput(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    icon: Optional[str] = None
    display_order: int = 0

    @field_validator('name', 'code')
    @classmethod
    def not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('must not be empty')
        return v


class MaterialGroupUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


class MaterialSubgroupInput(BaseModel):
    group_id: UUID
    name: str
    code: str
    description: Optional[str] = None
    icon: Optional[str] = None
    default_lead_time_days: Optional[int] = None
    default_unit: str = 'kg'
    display_order: int = 0

    @field_validator('name', 'code')
    @classmethod
    def not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('must not be empty')
        return v


class MaterialSubgroupUpdate(BaseModel):
    group_id: Optional[UUID] = None
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    default_lead_time_days: Optional[int] = None
    default_unit: Optional[str] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


# ────────────────────────────────────────────────────────────────
# Serialization helpers
# ────────────────────────────────────────────────────────────────

def _serialize_group(group, include_subgroups: bool = False, material_counts: dict | None = None) -> dict:
    result = {
        "id": str(group.id),
        "name": group.name,
        "code": group.code,
        "description": group.description,
        "icon": group.icon,
        "display_order": group.display_order,
        "is_active": group.is_active,
        "created_at": group.created_at.isoformat() if group.created_at else None,
        "updated_at": group.updated_at.isoformat() if group.updated_at else None,
    }
    if include_subgroups:
        result["subgroups"] = [
            _serialize_subgroup(sg, material_count=material_counts.get(str(sg.id), 0) if material_counts else 0)
            for sg in (group.subgroups or [])
        ]
    return result


def _serialize_subgroup(sg, material_count: int = 0) -> dict:
    return {
        "id": str(sg.id),
        "group_id": str(sg.group_id),
        "group_name": sg.group.name if sg.group else None,
        "name": sg.name,
        "code": sg.code,
        "description": sg.description,
        "icon": sg.icon,
        "default_lead_time_days": sg.default_lead_time_days,
        "default_unit": sg.default_unit,
        "display_order": sg.display_order,
        "is_active": sg.is_active,
        "material_count": material_count,
        "created_at": sg.created_at.isoformat() if sg.created_at else None,
        "updated_at": sg.updated_at.isoformat() if sg.updated_at else None,
    }


# ────────────────────────────────────────────────────────────────
# Hierarchy (nested tree)
# ────────────────────────────────────────────────────────────────

@router.get("/hierarchy")
async def get_material_hierarchy(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Full nested hierarchy: groups → subgroups with material counts."""
    from api.models import MaterialGroup, MaterialSubgroup, Material

    query = db.query(MaterialGroup).options(
        joinedload(MaterialGroup.subgroups)
    ).order_by(MaterialGroup.display_order)

    if not include_inactive:
        query = query.filter(MaterialGroup.is_active.is_(True))

    groups = query.all()

    # Get material counts per subgroup
    counts_q = (
        db.query(Material.subgroup_id, func.count(Material.id))
        .filter(Material.subgroup_id.isnot(None))
        .group_by(Material.subgroup_id)
        .all()
    )
    material_counts = {str(sg_id): cnt for sg_id, cnt in counts_q}

    result = []
    for g in groups:
        subgroups = g.subgroups
        if not include_inactive:
            subgroups = [sg for sg in subgroups if sg.is_active]
        g_dict = _serialize_group(g, include_subgroups=False)
        g_dict["subgroups"] = [
            _serialize_subgroup(sg, material_count=material_counts.get(str(sg.id), 0))
            for sg in subgroups
        ]
        result.append(g_dict)

    return result


# ────────────────────────────────────────────────────────────────
# Groups CRUD
# ────────────────────────────────────────────────────────────────

@router.get("/groups")
async def list_groups(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List all material groups (flat, no subgroups)."""
    from api.models import MaterialGroup

    query = db.query(MaterialGroup).order_by(MaterialGroup.display_order)
    if not include_inactive:
        query = query.filter(MaterialGroup.is_active.is_(True))

    return [_serialize_group(g) for g in query.all()]


@router.post("/groups", status_code=201)
async def create_group(
    data: MaterialGroupInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Create a new material group. Admin only."""
    from api.models import MaterialGroup

    # Check uniqueness
    existing = db.query(MaterialGroup).filter(
        (MaterialGroup.name == data.name) | (MaterialGroup.code == data.code)
    ).first()
    if existing:
        field = "name" if existing.name == data.name else "code"
        raise HTTPException(409, f"Group with this {field} already exists")

    group = MaterialGroup(
        name=data.name,
        code=data.code,
        description=data.description,
        icon=data.icon,
        display_order=data.display_order,
    )
    db.add(group)
    db.commit()
    db.refresh(group)

    logger.info(f"Material group created: {group.name} ({group.code}) by {current_user.email}")
    return _serialize_group(group)


@router.put("/groups/{group_id}")
async def update_group(
    group_id: UUID,
    data: MaterialGroupUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Update a material group. Admin only."""
    from api.models import MaterialGroup

    group = db.query(MaterialGroup).filter(MaterialGroup.id == group_id).first()
    if not group:
        raise HTTPException(404, "Group not found")

    if data.name is not None:
        group.name = data.name.strip()
    if data.code is not None:
        group.code = data.code.strip()
    if data.description is not None:
        group.description = data.description
    if data.icon is not None:
        group.icon = data.icon
    if data.display_order is not None:
        group.display_order = data.display_order
    if data.is_active is not None:
        group.is_active = data.is_active

    db.commit()
    db.refresh(group)

    logger.info(f"Material group updated: {group.name} by {current_user.email}")
    return _serialize_group(group)


@router.delete("/groups/{group_id}", status_code=204)
async def delete_group(
    group_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Delete a material group. Admin only. Fails if group has materials."""
    from api.models import MaterialGroup, Material

    group = db.query(MaterialGroup).filter(MaterialGroup.id == group_id).first()
    if not group:
        raise HTTPException(404, "Group not found")

    # Check for materials in this group
    mat_count = db.query(Material).filter(Material.group_id == group_id).count()
    if mat_count > 0:
        raise HTTPException(
            400,
            f"Cannot delete group '{group.name}': {mat_count} materials still assigned. "
            "Move or delete them first.",
        )

    db.delete(group)
    db.commit()
    logger.info(f"Material group deleted: {group.name} by {current_user.email}")
    return None


# ────────────────────────────────────────────────────────────────
# Subgroups CRUD
# ────────────────────────────────────────────────────────────────

@router.get("/subgroups")
async def list_subgroups(
    group_id: UUID | None = None,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List subgroups, optionally filtered by group."""
    from api.models import MaterialSubgroup, Material

    query = db.query(MaterialSubgroup).options(
        joinedload(MaterialSubgroup.group)
    ).order_by(MaterialSubgroup.display_order)

    if group_id:
        query = query.filter(MaterialSubgroup.group_id == group_id)
    if not include_inactive:
        query = query.filter(MaterialSubgroup.is_active.is_(True))

    subgroups = query.all()

    # Get material counts
    counts_q = (
        db.query(Material.subgroup_id, func.count(Material.id))
        .filter(Material.subgroup_id.isnot(None))
        .group_by(Material.subgroup_id)
        .all()
    )
    material_counts = {str(sg_id): cnt for sg_id, cnt in counts_q}

    return [
        _serialize_subgroup(sg, material_count=material_counts.get(str(sg.id), 0))
        for sg in subgroups
    ]


@router.post("/subgroups", status_code=201)
async def create_subgroup(
    data: MaterialSubgroupInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Create a new material subgroup. Admin only."""
    from api.models import MaterialSubgroup, MaterialGroup

    # Verify group exists
    group = db.query(MaterialGroup).filter(MaterialGroup.id == data.group_id).first()
    if not group:
        raise HTTPException(404, "Parent group not found")

    # Check uniqueness
    existing = db.query(MaterialSubgroup).filter(
        MaterialSubgroup.code == data.code
    ).first()
    if existing:
        raise HTTPException(409, f"Subgroup with code '{data.code}' already exists")

    sg = MaterialSubgroup(
        group_id=data.group_id,
        name=data.name,
        code=data.code,
        description=data.description,
        icon=data.icon,
        default_lead_time_days=data.default_lead_time_days,
        default_unit=data.default_unit,
        display_order=data.display_order,
    )
    db.add(sg)
    db.commit()
    db.refresh(sg)

    logger.info(f"Material subgroup created: {sg.name} ({sg.code}) in group {group.name} by {current_user.email}")
    return _serialize_subgroup(sg)


@router.put("/subgroups/{subgroup_id}")
async def update_subgroup(
    subgroup_id: UUID,
    data: MaterialSubgroupUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Update a material subgroup. Admin only."""
    from api.models import MaterialSubgroup, Material

    sg = db.query(MaterialSubgroup).options(
        joinedload(MaterialSubgroup.group)
    ).filter(MaterialSubgroup.id == subgroup_id).first()
    if not sg:
        raise HTTPException(404, "Subgroup not found")

    old_code = sg.code

    if data.group_id is not None:
        sg.group_id = data.group_id
    if data.name is not None:
        sg.name = data.name.strip()
    if data.code is not None:
        sg.code = data.code.strip()
    if data.description is not None:
        sg.description = data.description
    if data.icon is not None:
        sg.icon = data.icon
    if data.default_lead_time_days is not None:
        sg.default_lead_time_days = data.default_lead_time_days
    if data.default_unit is not None:
        sg.default_unit = data.default_unit
    if data.display_order is not None:
        sg.display_order = data.display_order
    if data.is_active is not None:
        sg.is_active = data.is_active

    # If code changed, sync material_type on all linked materials
    if data.code and data.code.strip() != old_code:
        updated = (
            db.query(Material)
            .filter(Material.subgroup_id == subgroup_id)
            .update({"material_type": data.code.strip()})
        )
        if updated:
            logger.info(f"Synced material_type to '{data.code.strip()}' on {updated} materials")

    db.commit()
    db.refresh(sg)

    logger.info(f"Material subgroup updated: {sg.name} by {current_user.email}")
    return _serialize_subgroup(sg)


@router.delete("/subgroups/{subgroup_id}", status_code=204)
async def delete_subgroup(
    subgroup_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Delete a material subgroup. Admin only. Fails if subgroup has materials."""
    from api.models import MaterialSubgroup, Material

    sg = db.query(MaterialSubgroup).filter(MaterialSubgroup.id == subgroup_id).first()
    if not sg:
        raise HTTPException(404, "Subgroup not found")

    mat_count = db.query(Material).filter(Material.subgroup_id == subgroup_id).count()
    if mat_count > 0:
        raise HTTPException(
            400,
            f"Cannot delete subgroup '{sg.name}': {mat_count} materials still assigned. "
            "Move or delete them first.",
        )

    db.delete(sg)
    db.commit()
    logger.info(f"Material subgroup deleted: {sg.name} by {current_user.email}")
    return None
