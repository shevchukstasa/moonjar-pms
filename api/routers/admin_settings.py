"""
Admin Settings API — escalation rules, receiving settings, defect thresholds,
purchase consolidation settings.

All endpoints require admin role (owner or administrator).
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import (
    EscalationRule,
    ReceivingSetting,
    MaterialDefectThreshold,
    PurchaseConsolidationSetting,
    Material,
)
from api.roles import require_admin

router = APIRouter(tags=["admin-settings"])


# ==================== Pydantic schemas ====================

# --- Escalation Rules ---

class EscalationRuleCreate(BaseModel):
    factory_id: UUID
    task_type: str = Field(..., max_length=50)
    pm_timeout_hours: float = Field(..., ge=0)
    ceo_timeout_hours: float = Field(..., ge=0)
    owner_timeout_hours: float = Field(..., ge=0)
    night_level: int = Field(1, ge=1, le=3)
    is_active: bool = True


class EscalationRuleUpdate(BaseModel):
    task_type: Optional[str] = None
    pm_timeout_hours: Optional[float] = Field(None, ge=0)
    ceo_timeout_hours: Optional[float] = Field(None, ge=0)
    owner_timeout_hours: Optional[float] = Field(None, ge=0)
    night_level: Optional[int] = Field(None, ge=1, le=3)
    is_active: Optional[bool] = None


class EscalationRuleOut(BaseModel):
    id: str
    factory_id: str
    task_type: str
    pm_timeout_hours: float
    ceo_timeout_hours: float
    owner_timeout_hours: float
    night_level: int
    is_active: bool

    class Config:
        from_attributes = True


# --- Receiving Settings ---

class ReceivingSettingOut(BaseModel):
    factory_id: str
    approval_mode: str  # "all" or "auto"

    class Config:
        from_attributes = True


class ReceivingSettingUpdate(BaseModel):
    approval_mode: str = Field(..., pattern=r"^(all|auto)$")


# --- Material Defect Thresholds ---

class DefectThresholdOut(BaseModel):
    id: str
    material_id: str
    material_name: Optional[str] = None
    max_defect_percent: float

    class Config:
        from_attributes = True


class DefectThresholdUpdate(BaseModel):
    max_defect_percent: float = Field(..., ge=0, le=100)


# --- Purchase Consolidation ---

class ConsolidationSettingOut(BaseModel):
    factory_id: str
    consolidation_window_days: int
    urgency_threshold_days: int
    planning_horizon_days: int

    class Config:
        from_attributes = True


class ConsolidationSettingUpdate(BaseModel):
    consolidation_window_days: int = Field(..., ge=1)
    urgency_threshold_days: int = Field(..., ge=1)
    planning_horizon_days: int = Field(..., ge=1)


# ==================== ESCALATION RULES ====================

@router.get(
    "/escalation-rules",
    response_model=List[EscalationRuleOut],
    summary="List escalation rules for a factory",
)
def list_escalation_rules(
    factory_id: UUID = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    rows = (
        db.query(EscalationRule)
        .filter(EscalationRule.factory_id == factory_id)
        .order_by(EscalationRule.task_type)
        .all()
    )
    return [
        EscalationRuleOut(
            id=str(r.id),
            factory_id=str(r.factory_id),
            task_type=r.task_type,
            pm_timeout_hours=float(r.pm_timeout_hours),
            ceo_timeout_hours=float(r.ceo_timeout_hours),
            owner_timeout_hours=float(r.owner_timeout_hours),
            night_level=r.night_level or 1,
            is_active=r.is_active if r.is_active is not None else True,
        )
        for r in rows
    ]


@router.post(
    "/escalation-rules",
    response_model=EscalationRuleOut,
    status_code=201,
    summary="Create escalation rule",
)
def create_escalation_rule(
    data: EscalationRuleCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    existing = (
        db.query(EscalationRule)
        .filter(
            EscalationRule.factory_id == data.factory_id,
            EscalationRule.task_type == data.task_type,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Escalation rule for task_type '{data.task_type}' already exists for this factory.",
        )

    rule = EscalationRule(
        factory_id=data.factory_id,
        task_type=data.task_type,
        pm_timeout_hours=data.pm_timeout_hours,
        ceo_timeout_hours=data.ceo_timeout_hours,
        owner_timeout_hours=data.owner_timeout_hours,
        night_level=data.night_level,
        is_active=data.is_active,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)

    return EscalationRuleOut(
        id=str(rule.id),
        factory_id=str(rule.factory_id),
        task_type=rule.task_type,
        pm_timeout_hours=float(rule.pm_timeout_hours),
        ceo_timeout_hours=float(rule.ceo_timeout_hours),
        owner_timeout_hours=float(rule.owner_timeout_hours),
        night_level=rule.night_level or 1,
        is_active=rule.is_active if rule.is_active is not None else True,
    )


@router.patch(
    "/escalation-rules/{rule_id}",
    response_model=EscalationRuleOut,
    summary="Update escalation rule",
)
def update_escalation_rule(
    rule_id: UUID,
    data: EscalationRuleUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    rule = db.query(EscalationRule).filter(EscalationRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Escalation rule not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(rule, key, value)

    db.commit()
    db.refresh(rule)

    return EscalationRuleOut(
        id=str(rule.id),
        factory_id=str(rule.factory_id),
        task_type=rule.task_type,
        pm_timeout_hours=float(rule.pm_timeout_hours),
        ceo_timeout_hours=float(rule.ceo_timeout_hours),
        owner_timeout_hours=float(rule.owner_timeout_hours),
        night_level=rule.night_level or 1,
        is_active=rule.is_active if rule.is_active is not None else True,
    )


@router.delete(
    "/escalation-rules/{rule_id}",
    summary="Delete escalation rule",
)
def delete_escalation_rule(
    rule_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    rule = db.query(EscalationRule).filter(EscalationRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Escalation rule not found")
    db.delete(rule)
    db.commit()
    return {"status": "deleted", "id": str(rule_id)}


# ==================== RECEIVING SETTINGS ====================

@router.get(
    "/receiving-settings",
    response_model=ReceivingSettingOut,
    summary="Get receiving settings for a factory",
)
def get_receiving_settings(
    factory_id: UUID = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    row = (
        db.query(ReceivingSetting)
        .filter(ReceivingSetting.factory_id == factory_id)
        .first()
    )
    if not row:
        return ReceivingSettingOut(factory_id=str(factory_id), approval_mode="all")
    return ReceivingSettingOut(
        factory_id=str(row.factory_id),
        approval_mode=row.approval_mode,
    )


@router.put(
    "/receiving-settings/{factory_id}",
    response_model=ReceivingSettingOut,
    summary="Upsert receiving settings for a factory",
)
def upsert_receiving_settings(
    factory_id: UUID,
    data: ReceivingSettingUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    row = (
        db.query(ReceivingSetting)
        .filter(ReceivingSetting.factory_id == factory_id)
        .first()
    )
    if row:
        row.approval_mode = data.approval_mode
        row.updated_by = current_user.id
        row.updated_at = datetime.now(timezone.utc)
    else:
        row = ReceivingSetting(
            factory_id=factory_id,
            approval_mode=data.approval_mode,
            updated_by=current_user.id,
        )
        db.add(row)

    db.commit()
    db.refresh(row)
    return ReceivingSettingOut(
        factory_id=str(row.factory_id),
        approval_mode=row.approval_mode,
    )


# ==================== MATERIAL DEFECT THRESHOLDS ====================

@router.get(
    "/defect-thresholds",
    response_model=List[DefectThresholdOut],
    summary="List defect thresholds (optionally filter by factory via materials)",
)
def list_defect_thresholds(
    factory_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    query = db.query(MaterialDefectThreshold)
    rows = query.order_by(MaterialDefectThreshold.material_id).all()

    result = []
    for r in rows:
        mat = db.query(Material).filter(Material.id == r.material_id).first()
        result.append(
            DefectThresholdOut(
                id=str(r.id),
                material_id=str(r.material_id),
                material_name=mat.name if mat else None,
                max_defect_percent=float(r.max_defect_percent),
            )
        )
    return result


@router.put(
    "/defect-thresholds/{material_id}",
    response_model=DefectThresholdOut,
    summary="Upsert defect threshold for a material",
)
def upsert_defect_threshold(
    material_id: UUID,
    data: DefectThresholdUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    row = (
        db.query(MaterialDefectThreshold)
        .filter(MaterialDefectThreshold.material_id == material_id)
        .first()
    )
    if row:
        row.max_defect_percent = data.max_defect_percent
        row.updated_by = current_user.id
        row.updated_at = datetime.now(timezone.utc)
    else:
        row = MaterialDefectThreshold(
            material_id=material_id,
            max_defect_percent=data.max_defect_percent,
            updated_by=current_user.id,
        )
        db.add(row)

    db.commit()
    db.refresh(row)

    mat = db.query(Material).filter(Material.id == material_id).first()
    return DefectThresholdOut(
        id=str(row.id),
        material_id=str(row.material_id),
        material_name=mat.name if mat else None,
        max_defect_percent=float(row.max_defect_percent),
    )


@router.delete(
    "/defect-thresholds/{material_id}",
    summary="Delete defect threshold for a material",
)
def delete_defect_threshold(
    material_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    row = (
        db.query(MaterialDefectThreshold)
        .filter(MaterialDefectThreshold.material_id == material_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Defect threshold not found")
    db.delete(row)
    db.commit()
    return {"status": "deleted", "material_id": str(material_id)}


# ==================== PURCHASE CONSOLIDATION SETTINGS ====================

@router.get(
    "/consolidation-settings",
    response_model=ConsolidationSettingOut,
    summary="Get purchase consolidation settings for a factory",
)
def get_consolidation_settings(
    factory_id: UUID = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    row = (
        db.query(PurchaseConsolidationSetting)
        .filter(PurchaseConsolidationSetting.factory_id == factory_id)
        .first()
    )
    if not row:
        return ConsolidationSettingOut(
            factory_id=str(factory_id),
            consolidation_window_days=7,
            urgency_threshold_days=5,
            planning_horizon_days=30,
        )
    return ConsolidationSettingOut(
        factory_id=str(row.factory_id),
        consolidation_window_days=row.consolidation_window_days,
        urgency_threshold_days=row.urgency_threshold_days,
        planning_horizon_days=row.planning_horizon_days,
    )


@router.put(
    "/consolidation-settings/{factory_id}",
    response_model=ConsolidationSettingOut,
    summary="Upsert purchase consolidation settings for a factory",
)
def upsert_consolidation_settings(
    factory_id: UUID,
    data: ConsolidationSettingUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    row = (
        db.query(PurchaseConsolidationSetting)
        .filter(PurchaseConsolidationSetting.factory_id == factory_id)
        .first()
    )
    if row:
        row.consolidation_window_days = data.consolidation_window_days
        row.urgency_threshold_days = data.urgency_threshold_days
        row.planning_horizon_days = data.planning_horizon_days
        row.updated_by = current_user.id
        row.updated_at = datetime.now(timezone.utc)
    else:
        row = PurchaseConsolidationSetting(
            factory_id=factory_id,
            consolidation_window_days=data.consolidation_window_days,
            urgency_threshold_days=data.urgency_threshold_days,
            planning_horizon_days=data.planning_horizon_days,
            updated_by=current_user.id,
        )
        db.add(row)

    db.commit()
    db.refresh(row)
    return ConsolidationSettingOut(
        factory_id=str(row.factory_id),
        consolidation_window_days=row.consolidation_window_days,
        urgency_threshold_days=row.urgency_threshold_days,
        planning_horizon_days=row.planning_horizon_days,
    )
