from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.dashboard import DashboardStatsOut
from app.services.dashboard import get_dashboard_stats

router = APIRouter()


@router.get("/dashboard/stats", response_model=DashboardStatsOut)
async def get_stats(db: Session = Depends(get_db)):
    return get_dashboard_stats(db)
