from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import random

from app.database import get_db
from app.models import User, Earnings, TrustLog
from app.schemas import UserCreate, UserResponse, ScoreResponse

router = APIRouter(prefix="/api/riders", tags=["Riders"])

@router.post("/", response_model=UserResponse, status_code=201)
def register_rider(payload: UserCreate, db: Session = Depends(get_db)):
    """Register user, generate mock earnings and initial trust score."""
    existing = db.query(User).filter(User.zomato_partner_id == payload.zomato_partner_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Rider with this Zomato ID already exists")

    user = User(
        zomato_partner_id=payload.zomato_partner_id,
        name=payload.name,
        phone=payload.phone,
        zone=payload.zone,
        upi_handle=payload.upi_handle,
        base_urts=70
    )
    db.add(user)
    db.flush()

    # Create mock earnings based on zone realistic payouts (₹6000-₹10000/wk)
    weekly = round(random.uniform(6000.0, 10000.0), 2)
    # Average hours 35-50
    hours = random.randint(35, 50)
    
    earnings = Earnings(
        user_id=user.id,
        weekly_earnings=weekly,
        hours_worked=hours,
        active_days=random.randint(5, 7)
    )
    db.add(earnings)

    # Initial trust log
    tlog = TrustLog(
        user_id=user.id,
        change=70,
        reason="Initial Registration"
    )
    db.add(tlog)

    db.commit()
    db.refresh(user)
    return user

@router.get("/{rider_id}", response_model=UserResponse)
def get_rider(rider_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == rider_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Rider not found")
    return user

@router.get("/{rider_id}/score", response_model=ScoreResponse)
def get_rider_score(rider_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == rider_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Rider score not found")
    
    last_log = db.query(TrustLog).filter(TrustLog.user_id == rider_id).order_by(TrustLog.created_at.desc()).first()
    return ScoreResponse(
        rider_id=user.id,
        urts_score=user.base_urts,
        last_event=last_log.reason if last_log else "None",
        last_updated=last_log.created_at if last_log else user.created_at
    )
