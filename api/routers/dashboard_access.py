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


@router.get("/", response_model=dict)
async def list_dashboard_access(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    query = db.query(UserDashboardAccess)
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return {"items": items, "total": total, "page": page, "per_page": per_page}


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


@router.post("/", response_model=UserDashboardAccessResponse, status_code=201)
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
