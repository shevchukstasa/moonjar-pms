"""CRUD router for reports (auto-generated)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.models import Report
from api.schemas import ReportCreate, ReportUpdate, ReportResponse

router = APIRouter()


@router.get("/", response_model=dict)
async def list_reports(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(Report)
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return {"items": items, "total": total, "page": page, "per_page": per_page}


@router.get("/{item_id}", response_model=ReportResponse)
async def get_reports_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(Report).filter(Report.id == item_id).first()
    if not item:
        raise HTTPException(404, "Report not found")
    return item


@router.post("/", response_model=ReportResponse, status_code=201)
async def create_reports_item(
    data: ReportCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = Report(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=ReportResponse)
async def update_reports_item(
    item_id: UUID,
    data: ReportUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(Report).filter(Report.id == item_id).first()
    if not item:
        raise HTTPException(404, "Report not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
async def delete_reports_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(Report).filter(Report.id == item_id).first()
    if not item:
        raise HTTPException(404, "Report not found")
    db.delete(item)
    db.commit()
