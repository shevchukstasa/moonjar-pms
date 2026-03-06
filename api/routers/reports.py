"""Reports router — stub (reports table not in schema)."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_reports():
    # TODO: Implement report generation endpoints
    return {"items": [], "total": 0, "page": 1, "per_page": 50}
