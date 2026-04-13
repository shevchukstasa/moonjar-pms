"""Kiln equipment configs — Layer 1 of the firing model.

Tracks a time-stamped history of what thermocouple / controller / cable /
typology is installed on each kiln. Exactly one config per kiln may be
"current" (effective_to IS NULL) at any time.

Endpoints:
    GET    /kilns/{kiln_id}/equipment           — full history
    GET    /kilns/{kiln_id}/equipment/current   — only the currently-installed config
    POST   /kilns/{kiln_id}/equipment           — install new config (closes previous)
    PATCH  /kilns/{kiln_id}/equipment/{id}      — edit fields (notes, specs) on existing config
    DELETE /kilns/{kiln_id}/equipment/{id}      — delete (allowed only if not referenced by downstream layers; for now always allowed)
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.auth import get_current_user
from api.database import get_db
from api.models import (
    FiringTemperatureGroup,
    KilnEquipmentConfig,
    KilnTemperatureSetpoint,
    RecipeKilnCapability,
    Resource,
    User,
)
from api.roles import require_management

logger = logging.getLogger("moonjar.kiln_equipment")

router = APIRouter()


# ── Pydantic schemas ────────────────────────────────────────────────────────

class KilnEquipmentConfigBase(BaseModel):
    typology: Optional[str] = Field(None, description="horizontal | vertical | raku")

    thermocouple_brand: Optional[str] = None
    thermocouple_model: Optional[str] = None
    thermocouple_length_cm: Optional[int] = None
    thermocouple_position: Optional[str] = None

    controller_brand: Optional[str] = None
    controller_model: Optional[str] = None

    cable_brand: Optional[str] = None
    cable_length_cm: Optional[int] = None
    cable_type: Optional[str] = None

    notes: Optional[str] = None
    extras: Optional[dict] = None
    reason: Optional[str] = None


class KilnEquipmentConfigCreate(KilnEquipmentConfigBase):
    """Payload for installing a new config.

    The API closes the previous current config (effective_to=now) and
    creates a fresh row with effective_from=now.
    """
    pass


class KilnEquipmentConfigUpdate(KilnEquipmentConfigBase):
    """Patch existing fields on a config without creating a new version.

    Use this for typo fixes / adding notes. For a real equipment change,
    POST a new config instead.
    """
    pass


class KilnEquipmentConfigResponse(KilnEquipmentConfigBase):
    id: str
    kiln_id: str
    effective_from: datetime
    effective_to: Optional[datetime] = None
    installed_by: Optional[str] = None
    installed_by_name: Optional[str] = None
    is_current: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Helpers ────────────────────────────────────────────────────────────────

def _serialize(db: Session, cfg: KilnEquipmentConfig) -> dict:
    user_name = None
    if cfg.installed_by:
        u = db.query(User).filter(User.id == cfg.installed_by).first()
        if u:
            user_name = getattr(u, "full_name", None) or u.email
    return {
        "id": str(cfg.id),
        "kiln_id": str(cfg.kiln_id),
        "typology": cfg.typology,
        "thermocouple_brand": cfg.thermocouple_brand,
        "thermocouple_model": cfg.thermocouple_model,
        "thermocouple_length_cm": cfg.thermocouple_length_cm,
        "thermocouple_position": cfg.thermocouple_position,
        "controller_brand": cfg.controller_brand,
        "controller_model": cfg.controller_model,
        "cable_brand": cfg.cable_brand,
        "cable_length_cm": cfg.cable_length_cm,
        "cable_type": cfg.cable_type,
        "notes": cfg.notes,
        "extras": cfg.extras,
        "reason": cfg.reason,
        "effective_from": cfg.effective_from,
        "effective_to": cfg.effective_to,
        "installed_by": str(cfg.installed_by) if cfg.installed_by else None,
        "installed_by_name": user_name,
        "is_current": cfg.effective_to is None,
        "created_at": cfg.created_at,
        "updated_at": cfg.updated_at,
    }


def _ensure_kiln(db: Session, kiln_id: UUID) -> Resource:
    kiln = db.query(Resource).filter(Resource.id == kiln_id).first()
    if not kiln:
        raise HTTPException(404, f"Kiln {kiln_id} not found")
    if getattr(kiln, "resource_type", None) and str(kiln.resource_type).lower().endswith("kiln") is False and "kiln" not in str(kiln.resource_type).lower():
        # Defensive: resources table has multiple types. Only kilns get equipment.
        raise HTTPException(400, f"Resource {kiln_id} is not a kiln")
    return kiln


# ── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/kilns/{kiln_id}/equipment", response_model=List[KilnEquipmentConfigResponse])
async def list_kiln_equipment_history(
    kiln_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Full history of equipment configurations for a kiln (newest first)."""
    _ensure_kiln(db, kiln_id)
    configs = (
        db.query(KilnEquipmentConfig)
        .filter(KilnEquipmentConfig.kiln_id == kiln_id)
        .order_by(KilnEquipmentConfig.effective_from.desc())
        .all()
    )
    return [_serialize(db, c) for c in configs]


@router.get("/kilns/{kiln_id}/equipment/current", response_model=Optional[KilnEquipmentConfigResponse])
async def get_current_kiln_equipment(
    kiln_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Currently installed equipment config (the one with effective_to IS NULL)."""
    _ensure_kiln(db, kiln_id)
    cfg = (
        db.query(KilnEquipmentConfig)
        .filter(
            KilnEquipmentConfig.kiln_id == kiln_id,
            KilnEquipmentConfig.effective_to.is_(None),
        )
        .first()
    )
    if not cfg:
        return None
    return _serialize(db, cfg)


@router.post("/kilns/{kiln_id}/equipment", response_model=KilnEquipmentConfigResponse, status_code=201)
async def install_kiln_equipment(
    kiln_id: UUID,
    data: KilnEquipmentConfigCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Install a new equipment config.

    Closes the currently-active config (effective_to=now) and creates a
    fresh row with effective_from=now. This is what the PM calls when
    equipment is physically swapped on the kiln.
    """
    _ensure_kiln(db, kiln_id)
    now = datetime.now(timezone.utc)

    # Close current config if any
    current = (
        db.query(KilnEquipmentConfig)
        .filter(
            KilnEquipmentConfig.kiln_id == kiln_id,
            KilnEquipmentConfig.effective_to.is_(None),
        )
        .first()
    )
    if current:
        current.effective_to = now
        current.updated_at = now

    new_cfg = KilnEquipmentConfig(
        kiln_id=kiln_id,
        typology=data.typology,
        thermocouple_brand=data.thermocouple_brand,
        thermocouple_model=data.thermocouple_model,
        thermocouple_length_cm=data.thermocouple_length_cm,
        thermocouple_position=data.thermocouple_position,
        controller_brand=data.controller_brand,
        controller_model=data.controller_model,
        cable_brand=data.cable_brand,
        cable_length_cm=data.cable_length_cm,
        cable_type=data.cable_type,
        notes=data.notes,
        extras=data.extras,
        reason=data.reason,
        effective_from=now,
        installed_by=current_user.id,
        created_at=now,
        updated_at=now,
    )
    db.add(new_cfg)
    db.commit()
    db.refresh(new_cfg)

    logger.info(
        "KILN_EQUIPMENT_INSTALL | kiln=%s user=%s reason=%s",
        kiln_id, current_user.id, data.reason or "n/a",
    )

    # Stage 6: equipment change cascades to Layer 2 & Layer 4.
    # Anything previously calibrated/qualified against the old config
    # is now suspect and must be re-verified before the scheduler
    # should trust it. We don't hard-delete — we just raise a flag
    # that the UI surfaces (orange row in the set-point table, amber
    # warning in the capability matrix).
    setpoints_flagged = 0
    capabilities_flagged = 0
    if current is not None:
        setpoints_flagged = (
            db.query(KilnTemperatureSetpoint)
            .filter(
                KilnTemperatureSetpoint.kiln_equipment_config_id == current.id,
                KilnTemperatureSetpoint.needs_recalibration.is_(False),
            )
            .update(
                {"needs_recalibration": True},
                synchronize_session=False,
            )
        )

    # Capability rows are keyed by (recipe, kiln) — we flip all rows
    # for this kiln regardless of which config was baseline, because
    # the physical equipment has been swapped.
    capabilities_flagged = (
        db.query(RecipeKilnCapability)
        .filter(
            RecipeKilnCapability.kiln_id == kiln_id,
            RecipeKilnCapability.needs_requalification.is_(False),
        )
        .update(
            {"needs_requalification": True},
            synchronize_session=False,
        )
    )
    if setpoints_flagged or capabilities_flagged:
        db.commit()
        logger.info(
            "KILN_EQUIPMENT_INSTALL_CASCADE | kiln=%s | "
            "setpoints_flagged=%d capabilities_flagged=%d",
            kiln_id, setpoints_flagged, capabilities_flagged,
        )

    return _serialize(db, new_cfg)


@router.patch("/kilns/{kiln_id}/equipment/{config_id}", response_model=KilnEquipmentConfigResponse)
async def update_kiln_equipment(
    kiln_id: UUID,
    config_id: UUID,
    data: KilnEquipmentConfigUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Patch fields on an existing config.

    Use this for typo fixes or adding notes to an already-installed config.
    For an actual equipment swap, POST a new config instead — this endpoint
    does NOT create a new version.
    """
    _ensure_kiln(db, kiln_id)
    cfg = (
        db.query(KilnEquipmentConfig)
        .filter(
            KilnEquipmentConfig.id == config_id,
            KilnEquipmentConfig.kiln_id == kiln_id,
        )
        .first()
    )
    if not cfg:
        raise HTTPException(404, "Equipment config not found")

    patch = data.model_dump(exclude_unset=True)
    for k, v in patch.items():
        setattr(cfg, k, v)
    cfg.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(cfg)
    return _serialize(db, cfg)


@router.delete("/kilns/{kiln_id}/equipment/{config_id}", status_code=204)
async def delete_kiln_equipment(
    kiln_id: UUID,
    config_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Delete an equipment config.

    Refuses to delete the current config if it's the only one (the kiln
    would be left with no config). In Stage 4+ this will also refuse if
    any firing profile or set-point references it.
    """
    _ensure_kiln(db, kiln_id)
    cfg = (
        db.query(KilnEquipmentConfig)
        .filter(
            KilnEquipmentConfig.id == config_id,
            KilnEquipmentConfig.kiln_id == kiln_id,
        )
        .first()
    )
    if not cfg:
        raise HTTPException(404, "Equipment config not found")

    # If this is the only config on the kiln, refuse
    total = (
        db.query(KilnEquipmentConfig)
        .filter(KilnEquipmentConfig.kiln_id == kiln_id)
        .count()
    )
    if total <= 1:
        raise HTTPException(
            400,
            "Cannot delete the only equipment config for this kiln. "
            "Install a new config first.",
        )

    # If deleting the current one, promote the most recent historical
    # one back to current (effective_to = NULL).
    was_current = cfg.effective_to is None
    db.delete(cfg)
    db.flush()

    if was_current:
        latest = (
            db.query(KilnEquipmentConfig)
            .filter(KilnEquipmentConfig.kiln_id == kiln_id)
            .order_by(KilnEquipmentConfig.effective_from.desc())
            .first()
        )
        if latest:
            latest.effective_to = None
            latest.updated_at = datetime.now(timezone.utc)

    db.commit()


# ══════════════════════════════════════════════════════════════════════════
# Layer 2 — Temperature set-points per (temperature_group × current kiln config)
# ══════════════════════════════════════════════════════════════════════════

class SetpointRow(BaseModel):
    """One row in the calibration table shown inside a temperature group.

    If setpoint_id is None, this kiln is NOT yet calibrated for this group —
    the row exists so the PM can fill it in. `target_c` is the abstract
    target of the group (same for everyone); `setpoint_c` is what the PM
    dials into the controller for this specific kiln+config.
    """
    kiln_id: str
    kiln_name: str
    factory_id: Optional[str] = None
    factory_name: Optional[str] = None
    kiln_equipment_config_id: Optional[str] = None
    equipment_summary: Optional[str] = None
    setpoint_id: Optional[str] = None
    setpoint_c: Optional[int] = None
    target_c: int
    needs_recalibration: bool = False
    calibrated_at: Optional[datetime] = None
    calibrated_by_name: Optional[str] = None
    notes: Optional[str] = None


class SetpointUpsert(BaseModel):
    kiln_id: str
    setpoint_c: int = Field(..., ge=0, le=2000)
    notes: Optional[str] = None


def _equipment_summary(cfg: KilnEquipmentConfig) -> str:
    parts = []
    if cfg.typology:
        parts.append(cfg.typology)
    tc = "/".join(filter(None, [cfg.thermocouple_brand, cfg.thermocouple_model]))
    if tc:
        parts.append(f"TC:{tc}")
    ctrl = "/".join(filter(None, [cfg.controller_brand, cfg.controller_model]))
    if ctrl:
        parts.append(f"Ctrl:{ctrl}")
    return " · ".join(parts) if parts else "no equipment recorded"


@router.get("/temperature-groups/{group_id}/setpoints", response_model=List[SetpointRow])
async def list_setpoints_for_group(
    group_id: UUID,
    factory_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return a calibration row for every kiln, optionally scoped to a factory.

    Rows include kilns that have NO set-point yet (setpoint_id=None) so the
    PM can see the full matrix and fill in the blanks.
    """
    group = db.query(FiringTemperatureGroup).filter(FiringTemperatureGroup.id == group_id).first()
    if not group:
        raise HTTPException(404, "Temperature group not found")

    # All kilns scoped to factory: explicit param → user's assigned factories → all
    kilns_q = db.query(Resource).filter(Resource.resource_type == 'kiln')
    if factory_id:
        kilns_q = kilns_q.filter(Resource.factory_id == factory_id)
    else:
        role_val = getattr(current_user, 'role', None)
        if hasattr(role_val, 'value'):
            role_val = role_val.value
        if role_val not in ('owner', 'ceo', 'administrator'):
            user_fids = [
                uf.factory_id for uf in getattr(current_user, 'user_factories', [])
            ]
            if user_fids:
                kilns_q = kilns_q.filter(Resource.factory_id.in_(user_fids))
    kilns = kilns_q.order_by(Resource.name).all()

    # Preload current configs in one query
    kiln_ids = [k.id for k in kilns]
    current_configs: dict[str, KilnEquipmentConfig] = {}
    if kiln_ids:
        cfgs = (
            db.query(KilnEquipmentConfig)
            .filter(
                KilnEquipmentConfig.kiln_id.in_(kiln_ids),
                KilnEquipmentConfig.effective_to.is_(None),
            )
            .all()
        )
        current_configs = {str(c.kiln_id): c for c in cfgs}

    # Preload existing set-points for this group + those configs
    config_ids = [c.id for c in current_configs.values()]
    existing_setpoints: dict[str, KilnTemperatureSetpoint] = {}
    if config_ids:
        sps = (
            db.query(KilnTemperatureSetpoint)
            .filter(
                KilnTemperatureSetpoint.temperature_group_id == group_id,
                KilnTemperatureSetpoint.kiln_equipment_config_id.in_(config_ids),
            )
            .all()
        )
        existing_setpoints = {str(sp.kiln_equipment_config_id): sp for sp in sps}

    # Preload factory names + user names
    factory_names: dict[str, str] = {}
    try:
        from api.models import Factory
        for f in db.query(Factory).all():
            factory_names[str(f.id)] = f.name
    except Exception:
        pass

    user_names: dict[str, str] = {}
    user_ids = [sp.calibrated_by for sp in existing_setpoints.values() if sp.calibrated_by]
    if user_ids:
        for u in db.query(User).filter(User.id.in_(user_ids)).all():
            user_names[str(u.id)] = getattr(u, "full_name", None) or u.email

    rows: List[SetpointRow] = []
    for k in kilns:
        cfg = current_configs.get(str(k.id))
        sp = existing_setpoints.get(str(cfg.id)) if cfg else None
        rows.append(SetpointRow(
            kiln_id=str(k.id),
            kiln_name=k.name,
            factory_id=str(k.factory_id) if k.factory_id else None,
            factory_name=factory_names.get(str(k.factory_id)),
            kiln_equipment_config_id=str(cfg.id) if cfg else None,
            equipment_summary=_equipment_summary(cfg) if cfg else "NO equipment config",
            setpoint_id=str(sp.id) if sp else None,
            setpoint_c=sp.setpoint_c if sp else None,
            target_c=group.temperature,
            needs_recalibration=sp.needs_recalibration if sp else False,
            calibrated_at=sp.calibrated_at if sp else None,
            calibrated_by_name=user_names.get(str(sp.calibrated_by)) if sp and sp.calibrated_by else None,
            notes=sp.notes if sp else None,
        ))
    return rows


@router.put("/temperature-groups/{group_id}/setpoints", response_model=SetpointRow)
async def upsert_setpoint(
    group_id: UUID,
    data: SetpointUpsert,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Create or update the set-point for (temperature_group × current config of kiln).

    Always targets the CURRENT equipment config of the given kiln. If the
    kiln has no current config, returns 400 — PM should set up equipment
    first (Stage 1).
    """
    group = db.query(FiringTemperatureGroup).filter(FiringTemperatureGroup.id == group_id).first()
    if not group:
        raise HTTPException(404, "Temperature group not found")

    kiln_uuid = UUID(data.kiln_id)
    kiln = db.query(Resource).filter(Resource.id == kiln_uuid).first()
    if not kiln:
        raise HTTPException(404, "Kiln not found")

    current_cfg = (
        db.query(KilnEquipmentConfig)
        .filter(
            KilnEquipmentConfig.kiln_id == kiln_uuid,
            KilnEquipmentConfig.effective_to.is_(None),
        )
        .first()
    )
    if not current_cfg:
        raise HTTPException(
            400,
            "This kiln has no current equipment config. Install one first via "
            "the Equipment dialog on the Kilns page.",
        )

    now = datetime.now(timezone.utc)
    sp = (
        db.query(KilnTemperatureSetpoint)
        .filter(
            KilnTemperatureSetpoint.temperature_group_id == group_id,
            KilnTemperatureSetpoint.kiln_equipment_config_id == current_cfg.id,
        )
        .first()
    )
    if sp:
        sp.setpoint_c = data.setpoint_c
        sp.notes = data.notes
        sp.calibrated_at = now
        sp.calibrated_by = current_user.id
        sp.needs_recalibration = False
        sp.updated_at = now
    else:
        sp = KilnTemperatureSetpoint(
            temperature_group_id=group_id,
            kiln_equipment_config_id=current_cfg.id,
            setpoint_c=data.setpoint_c,
            notes=data.notes,
            calibrated_at=now,
            calibrated_by=current_user.id,
            needs_recalibration=False,
        )
        db.add(sp)

    db.commit()
    db.refresh(sp)

    user_name = None
    u = db.query(User).filter(User.id == current_user.id).first()
    if u:
        user_name = getattr(u, "full_name", None) or u.email

    factory = None
    try:
        from api.models import Factory
        factory = db.query(Factory).filter(Factory.id == kiln.factory_id).first()
    except Exception:
        pass

    return SetpointRow(
        kiln_id=str(kiln.id),
        kiln_name=kiln.name,
        factory_id=str(kiln.factory_id) if kiln.factory_id else None,
        factory_name=factory.name if factory else None,
        kiln_equipment_config_id=str(current_cfg.id),
        equipment_summary=_equipment_summary(current_cfg),
        setpoint_id=str(sp.id),
        setpoint_c=sp.setpoint_c,
        target_c=group.temperature,
        needs_recalibration=sp.needs_recalibration,
        calibrated_at=sp.calibrated_at,
        calibrated_by_name=user_name,
        notes=sp.notes,
    )


@router.delete("/temperature-groups/{group_id}/setpoints/{setpoint_id}", status_code=204)
async def delete_setpoint(
    group_id: UUID,
    setpoint_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """Clear a set-point (e.g. if it was entered by mistake)."""
    sp = (
        db.query(KilnTemperatureSetpoint)
        .filter(
            KilnTemperatureSetpoint.id == setpoint_id,
            KilnTemperatureSetpoint.temperature_group_id == group_id,
        )
        .first()
    )
    if not sp:
        raise HTTPException(404, "Set-point not found")
    db.delete(sp)
    db.commit()
