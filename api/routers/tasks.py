"""Tasks router — task assignments.
See API_CONTRACTS.md for full specification.
"""

from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user

router = APIRouter()


@router.get("/")
async def list_tasks(
    page: int = Query(1), per_page: int = Query(50),
    factory_id: UUID | None = None, assignee_id: UUID | None = None,
    status: str | None = None,
    db: Session = Depends(get_db), current_user=Depends(get_current_user),
):
    # TODO: List task assignments — see API_CONTRACTS §9
    raise HTTPException(501, "Not implemented")


@router.post("/", status_code=201)
async def create_task(request: Request, db: Session = Depends(get_db),
                      current_user=Depends(get_current_user)):
    # TODO: Create task assignment — see API_CONTRACTS §9
    raise HTTPException(501, "Not implemented")


@router.patch("/{task_id}")
async def update_task(task_id: UUID, request: Request, db: Session = Depends(get_db),
                      current_user=Depends(get_current_user)):
    # TODO: Update task — see API_CONTRACTS §9
    raise HTTPException(501, "Not implemented")


@router.post("/{task_id}/complete")
async def complete_task(task_id: UUID, db: Session = Depends(get_db),
                        current_user=Depends(get_current_user)):
    # TODO: Mark task complete — see API_CONTRACTS §9
    raise HTTPException(501, "Not implemented")
