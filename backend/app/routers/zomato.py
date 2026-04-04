from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import random

from app.auth import get_current_user, require_rider_or_admin_access
from app.database import get_db
from app.models import User, Earnings
from app.schemas import EarningsResponse

router = APIRouter(prefix="/api/zomato", tags=["Zomato (DB)"])

@router.get("/earnings/{rider_id}", response_model=EarningsResponse)
def get_rider_earnings(
    rider_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetch earnings from DB instead of pure mock generation."""
    require_rider_or_admin_access(rider_id, current_user)
    user = db.query(User).filter(User.id == rider_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Rider not found")
        
    earnings = db.query(Earnings).filter(Earnings.user_id == rider_id).first()
    if not earnings:
        raise HTTPException(status_code=404, detail="Earnings not found")

    weekly_data = []
    # Project 4 weeks based on core weekly avg to keep compatibility with UI
    for week in range(1, 5):
        weekly_data.append({
            "week": week,
            "earnings": earnings.weekly_earnings,
            "hours_worked": earnings.hours_worked,
            "active_days": earnings.active_days,
            "deliveries": random.randint(80, 140),
        })

    avg_hourly = round(earnings.weekly_earnings / earnings.hours_worked, 2) if earnings.hours_worked > 0 else 0
    total_4w = earnings.weekly_earnings * 4

    return EarningsResponse(
        rider_id=user.id,
        zomato_partner_id=user.zomato_partner_id,
        name=user.name,
        zone=user.zone,
        summary={
            "total_earnings_4w": total_4w,
            "total_hours_4w": earnings.hours_worked * 4,
            "avg_hourly_income": avg_hourly,
            "avg_active_days": earnings.active_days,
            "avg_weekly_earnings": earnings.weekly_earnings,
        },
        weekly_breakdown=weekly_data
    )
