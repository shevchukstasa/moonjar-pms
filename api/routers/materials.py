"""Materials router — CRUD + transactions + purchase requests.
See API_CONTRACTS.md for full specification.
"""

from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.roles import require_warehouse, require_management

router = APIRouter()


@router.get("/")
async def list_materials(
    page: int = Query(1, ge=1), per_page: int = Query(50),
    factory_id: UUID | None = None, material_type: str | None = None,
    warehouse_section: str | None = None, low_stock: bool | None = None,
    search: str | None = None,
    db: Session = Depends(get_db), current_user=Depends(get_current_user),
):
    # TODO: List materials with effective balance — see API_CONTRACTS §6
    raise HTTPException(501, "Not implemented")


@router.get("/{material_id}")
async def get_material(material_id: UUID, db: Session = Depends(get_db),
                       current_user=Depends(get_current_user)):
    # TODO: Get material with balance info — see API_CONTRACTS §6
    raise HTTPException(501, "Not implemented")


@router.post("/", status_code=201)
async def create_material(request: Request, db: Session = Depends(get_db),
                          current_user=Depends(get_current_user)):
    # TODO: Create material — see API_CONTRACTS §6
    raise HTTPException(501, "Not implemented")


@router.patch("/{material_id}")
async def update_material(material_id: UUID, request: Request,
                          db: Session = Depends(get_db),
                          current_user=Depends(get_current_user)):
    # TODO: Update material — see API_CONTRACTS §6
    raise HTTPException(501, "Not implemented")


@router.get("/{material_id}/transactions")
async def list_material_transactions(material_id: UUID,
                                      page: int = Query(1), per_page: int = Query(50),
                                      db: Session = Depends(get_db),
                                      current_user=Depends(get_current_user)):
    # TODO: Transaction history — see API_CONTRACTS §6
    raise HTTPException(501, "Not implemented")


@router.post("/transactions")
async def create_transaction(request: Request, db: Session = Depends(get_db),
                             current_user=Depends(get_current_user)):
    # TODO: Manual receive/write-off — see BL §4
    raise HTTPException(501, "Not implemented")


@router.get("/effective-balance")
async def get_effective_balance(factory_id: UUID | None = None,
                                db: Session = Depends(get_db),
                                current_user=Depends(get_current_user)):
    # TODO: Stone balance adjusted for defect coefficient — see BL §4
    raise HTTPException(501, "Not implemented")


@router.get("/low-stock")
async def get_low_stock(factory_id: UUID | None = None,
                        db: Session = Depends(get_db),
                        current_user=Depends(get_current_user)):
    # TODO: Low stock alerts — see BL §5
    raise HTTPException(501, "Not implemented")


@router.post("/purchase-requests", status_code=201)
async def create_purchase_request(request: Request, db: Session = Depends(get_db),
                                  current_user=Depends(get_current_user)):
    # TODO: Create purchase request — see API_CONTRACTS §6
    raise HTTPException(501, "Not implemented")
