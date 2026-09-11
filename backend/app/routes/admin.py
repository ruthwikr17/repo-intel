from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.quota_monitor import get_remaining_capacity

router = APIRouter()


@router.get("/admin/quota")
async def get_quota_status(db: AsyncSession = Depends(get_db)):
    """
    Returns current API quota usage and remaining capacity.
    Shows how many more analyses can be done today.
    """
    capacity = await get_remaining_capacity(db)
    return {
        "status": "ok",
        "date": str(__import__("datetime").date.today()),
        "quota": capacity,
    }


@router.get("/admin/version")
async def get_version():
    return {"version": "v1.0.3-d46493d"}

