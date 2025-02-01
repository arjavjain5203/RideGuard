from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import random

from app.auth import get_current_user, hash_password, require_rider_or_admin_access
from app.core.redis_client import get_cached_json, set_cached_json
from app.database import get_db
from app.models import User, Earnings, TrustLog
from app.schemas import UserCreate, UserResponse, ScoreResponse
from app.config import settings

router = APIRouter(prefix="/api/riders", tags=["Riders"])


def rider_cache_key(rider_id: str) -> str:
    return f"rider:{rider_id}"


def cache_rider(user: User) -> None:
    payload = UserResponse.model_validate(user).model_dump(mode="json")
    set_cached_json(rider_cache_key(user.id), payload, settings.RIDER_CACHE_TTL_SECONDS)

def create_rider_account(
    payload: UserCreate,
    db: Session,
    *,
    trust_reason: str = "Initial Registration",
) -> User:
    """Create a rider account with seeded earnings and an initial trust log."""
    existing = db.query(User).filter(User.zomato_partner_id == payload.zomato_partner_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Rider with this Zomato ID already exists")
    existing_login = db.query(User).filter(User.login_id == payload.login_id).first()
    if existing_login:
        raise HTTPException(status_code=409, detail="Login ID already in use")

    user = User(
        login_id=payload.login_id,
        zomato_partner_id=payload.zomato_partner_id,
        name=payload.name,
        phone=payload.phone,
        zone=payload.zone,
        upi_handle=payload.upi_handle,
        password_hash=hash_password(payload.password),
        role="rider",
        base_urts=70,
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
    user.hourly_income = round(weekly / max(1, hours), 2)
    user.is_active = True

    # Initial trust log
    tlog = TrustLog(
        user_id=user.id,
        change=70,
        reason=trust_reason
    )
    db.add(tlog)

    db.commit()
    db.refresh(user)
    cache_rider(user)
    return user

@router.post("", response_model=UserResponse, status_code=201, include_in_schema=False)
@router.post("/", response_model=UserResponse, status_code=201)
def register_rider(payload: UserCreate, db: Session = Depends(get_db)):
    """Register user, generate mock earnings and initial trust score."""
    return create_rider_account(payload, db)

@router.get("/{rider_id}", response_model=UserResponse)
def get_rider(
    rider_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_rider_or_admin_access(rider_id, current_user)
    cached_user = get_cached_json(rider_cache_key(rider_id))
    if cached_user:
        return UserResponse(**cached_user)
    user = db.query(User).filter(User.id == rider_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Rider not found")
    cache_rider(user)
    return user

@router.get("/{rider_id}/score", response_model=ScoreResponse)
def get_rider_score(
    rider_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_rider_or_admin_access(rider_id, current_user)
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
