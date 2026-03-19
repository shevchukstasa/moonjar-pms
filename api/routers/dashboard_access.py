"""CRUD router for user_dashboard_access (auto-generated)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.roles import require_admin
from api.models import UserDashboardAccess
from api.schemas import UserDashboardAccessCreate, UserDashboardAccessUpdate, UserDashboardAccessResponse

router = APIRouter()


@router.get("", response_model=dict)
async def list_dashboard_access(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    query = db.query(UserDashboardAccess)
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return {
        "items": [UserDashboardAccessResponse.model_validate(item).model_dump(mode="json") for item in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/my")
async def get_my_dashboard_access(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return current user's accessible dashboards."""
    items = db.query(UserDashboardAccess).filter(
        UserDashboardAccess.user_id == current_user.id
    ).all()

    # Always include the user's default role-based dashboard
    role_dashboard = getattr(current_user, "role", None)
    role_str = role_dashboard.value if hasattr(role_dashboard, "value") else str(role_dashboard) if role_dashboard else None

    dashboards = []
    if role_str:
        dashboards.append({
            "dashboard_type": role_str,
            "source": "role",
            "granted_at": None,
        })

    for item in items:
        dt = item.dashboard_type
        dashboards.append({
            "dashboard_type": dt.value if hasattr(dt, "value") else str(dt),
            "source": "granted",
            "granted_at": item.granted_at.isoformat() if item.granted_at else None,
        })

    return {
        "dashboards": dashboards,
        "total": len(dashboards),
    }


@router.get("/{item_id}", response_model=UserDashboardAccessResponse)
async def get_dashboard_access_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    item = db.query(UserDashboardAccess).filter(UserDashboardAccess.id == item_id).first()
    if not item:
        raise HTTPException(404, "UserDashboardAccess not found")
    return item


@router.post("", response_model=UserDashboardAccessResponse, status_code=201)
async def create_dashboard_access_item(
    data: UserDashboardAccessCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    item = UserDashboardAccess(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=UserDashboardAccessResponse)
async def update_dashboard_access_item(
    item_id: UUID,
    data: UserDashboardAccessUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    item = db.query(UserDashboardAccess).filter(UserDashboardAccess.id == item_id).first()
    if not item:
        raise HTTPException(404, "UserDashboardAccess not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
async def delete_dashboard_access_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    item = db.query(UserDashboardAccess).filter(UserDashboardAccess.id == item_id).first()
    if not item:
        raise HTTPException(404, "UserDashboardAccess not found")
    db.delete(item)
    db.commit()
