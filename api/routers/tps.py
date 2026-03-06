"""TPS router — stub (tps_improvements not in schema)."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_tps():
    # TODO: Implement TPS improvements tracking
    return {"items": [], "total": 0, "page": 1, "per_page": 50}
