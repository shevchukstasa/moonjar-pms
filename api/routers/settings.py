"""
Settings API — factory-level configuration.

Endpoints:
- GET  /settings/service-lead-times?factory_id=...    — get lead times (management)
- PUT  /settings/service-lead-times/{factory_id}      — update lead times (admin)
- POST /settings/service-lead-times/{factory_id}/reset-defaults  — reset to defaults (admin)
"""
from fastapi import APIRouter, Depends, Query, Body, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from uuid import UUID
from pydantic import BaseModel, Field

from api.database import get_db
from api.roles import require_management, require_admin

router = APIRouter(tags=["settings"])


# ==================== Pydantic schemas ====================

class ServiceLeadTimeItem(BaseModel):
    service_type: str = Field(..., description="Service type key, e.g. 'stencil', 'silkscreen'")
    lead_time_days: int = Field(..., ge=0, description="Lead time in days (>= 0)")


class ServiceLeadTimeDetail(BaseModel):
    service_type: str
    lead_time_days: int
    is_custom: bool


class ServiceLeadTimesResponse(BaseModel):
    factory_id: str
    lead_times: List[ServiceLeadTimeDetail]


# ==================== SERVICE LEAD TIMES ====================

@router.get(
    "/service-lead-times",
    response_model=ServiceLeadTimesResponse,
    summary="Get service lead times for a factory",
)
def get_service_lead_times(
    factory_id: UUID = Query(..., description="Factory UUID"),
    db: Session = Depends(get_db),
    current_user=Depends(require_management),
):
    """
    Returns configured lead times for all service types at the given factory.
    Falls back to system defaults if no factory-specific value is set.
    """
    from business.services.service_blocking import DEFAULT_LEAD_TIMES

    rows = db.execute(text("""
        SELECT service_type, lead_time_days
        FROM service_lead_times
        WHERE factory_id = :fid
        ORDER BY service_type
    """), {'fid': str(factory_id)}).fetchall()

    db_values = {r[0]: r[1] for r in rows}
    lead_times = []
    for stype, default_days in DEFAULT_LEAD_TIMES.items():
        lead_times.append(ServiceLeadTimeDetail(
            service_type=stype,
            lead_time_days=db_values.get(stype, default_days),
            is_custom=stype in db_values,
        ))

    return ServiceLeadTimesResponse(
        factory_id=str(factory_id),
        lead_times=lead_times,
    )


@router.put(
    "/service-lead-times/{factory_id}",
    response_model=ServiceLeadTimesResponse,
    summary="Update service lead times for a factory (admin only)",
)
def update_service_lead_times(
    factory_id: UUID,
    items: List[ServiceLeadTimeItem] = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """
    Upsert service lead times for the given factory.
    Only admin/owner can update. Validates lead_time_days >= 0.
    """
    from business.services.service_blocking import DEFAULT_LEAD_TIMES

    unknown_types = [
        item.service_type for item in items
        if item.service_type not in DEFAULT_LEAD_TIMES
    ]
    if unknown_types:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown service types: {unknown_types}. "
                   f"Valid types: {list(DEFAULT_LEAD_TIMES.keys())}",
        )

    for item in items:
        db.execute(text("""
            INSERT INTO service_lead_times (factory_id, service_type, lead_time_days, updated_by)
            VALUES (:fid, :stype, :days, :uid)
            ON CONFLICT (factory_id, service_type)
            DO UPDATE SET
                lead_time_days = EXCLUDED.lead_time_days,
                updated_at = NOW(),
                updated_by = EXCLUDED.updated_by
        """), {
            'fid': str(factory_id),
            'stype': item.service_type,
            'days': item.lead_time_days,
            'uid': str(current_user.id),
        })

    db.commit()

    # Return updated values
    return get_service_lead_times(factory_id=factory_id, db=db, current_user=current_user)


@router.post(
    "/service-lead-times/{factory_id}/reset-defaults",
    summary="Reset all service lead times to system defaults (admin only)",
)
def reset_service_lead_times_to_defaults(
    factory_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """
    Delete all custom lead times for the factory, reverting to system defaults.
    """
    result = db.execute(
        text("DELETE FROM service_lead_times WHERE factory_id = :fid"),
        {'fid': str(factory_id)},
    )
    db.commit()
    deleted_count = result.rowcount if hasattr(result, 'rowcount') else 0
    return {
        "status": "reset",
        "factory_id": str(factory_id),
        "deleted_overrides": deleted_count,
    }
