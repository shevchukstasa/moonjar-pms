"""Kilns router — stub (no kilns table, use kiln_constants)."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_kilns():
    # TODO: Kiln data is managed via kiln_constants endpoint
    return {"items": [], "total": 0, "page": 1, "per_page": 50}
