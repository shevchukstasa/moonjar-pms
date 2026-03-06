"""Orders router — CRUD + webhook + attachments + change requests.
See API_CONTRACTS.md for full specification.
"""

from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user
from api.roles import require_management

router = APIRouter()


@router.get("/")
async def list_orders(
    page: int = Query(1, ge=1), per_page: int = Query(50, ge=1, le=200),
    factory_id: UUID | None = None, status: str | None = None,
    priority: str | None = None, search: str | None = None,
    date_from: str | None = None, date_to: str | None = None,
    db: Session = Depends(get_db), current_user=Depends(get_current_user),
):
    # TODO: Implement with factory scoping, filters, pagination — see API_CONTRACTS §3
    raise HTTPException(501, "Not implemented")


@router.get("/{order_id}")
async def get_order(order_id: UUID, db: Session = Depends(get_db),
                    current_user=Depends(get_current_user)):
    # TODO: Implement — see API_CONTRACTS §3
    raise HTTPException(501, "Not implemented")


@router.post("/", status_code=201)
async def create_order(request: Request, db: Session = Depends(get_db),
                       current_user=Depends(get_current_user)):
    # TODO: Implement order creation — see BL §1 (Order Intake)
    raise HTTPException(501, "Not implemented")


@router.patch("/{order_id}")
async def update_order(order_id: UUID, request: Request, db: Session = Depends(get_db),
                       current_user=Depends(get_current_user)):
    # TODO: Implement — see API_CONTRACTS §3
    raise HTTPException(501, "Not implemented")


@router.delete("/{order_id}", status_code=204)
async def cancel_order(order_id: UUID, db: Session = Depends(get_db),
                       current_user=Depends(get_current_user)):
    # TODO: Implement order cancellation — see BL §2
    raise HTTPException(501, "Not implemented")


@router.post("/{order_id}/upload")
async def upload_attachment(order_id: UUID, file: UploadFile = File(...),
                            db: Session = Depends(get_db),
                            current_user=Depends(get_current_user)):
    # TODO: Upload to Supabase Storage — see API_CONTRACTS §3
    raise HTTPException(501, "Not implemented")


@router.patch("/{order_id}/mandatory-qc")
async def toggle_mandatory_qc(order_id: UUID, request: Request,
                               db: Session = Depends(get_db),
                               current_user=Depends(get_current_user)):
    # TODO: Toggle mandatory QC flag — see API_CONTRACTS §3
    raise HTTPException(501, "Not implemented")


@router.get("/{order_id}/alerts")
async def get_order_alerts(order_id: UUID, db: Session = Depends(get_db),
                           current_user=Depends(get_current_user)):
    # TODO: Red alerts for positions behind schedule — see BL §3
    raise HTTPException(501, "Not implemented")


@router.get("/{external_id}/production-status")
async def get_production_status(external_id: str, request: Request,
                                db: Session = Depends(get_db)):
    # TODO: Public endpoint for Sales app (API key auth) — see API_CONTRACTS §3
    raise HTTPException(501, "Not implemented")


@router.get("/{order_id}/change-requests")
async def list_change_requests(order_id: UUID, db: Session = Depends(get_db),
                               current_user=Depends(get_current_user)):
    # TODO: List change requests for order — see API_CONTRACTS §4
    raise HTTPException(501, "Not implemented")


@router.post("/{order_id}/change-requests/{cr_id}/approve")
async def approve_change_request(order_id: UUID, cr_id: UUID,
                                 db: Session = Depends(get_db),
                                 current_user=Depends(get_current_user)):
    # TODO: Approve change request — see API_CONTRACTS §4
    raise HTTPException(501, "Not implemented")


@router.post("/{order_id}/change-requests/{cr_id}/reject")
async def reject_change_request(order_id: UUID, cr_id: UUID,
                                db: Session = Depends(get_db),
                                current_user=Depends(get_current_user)):
    # TODO: Reject change request — see API_CONTRACTS §4
    raise HTTPException(501, "Not implemented")
