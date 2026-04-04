from fastapi import APIRouter, Depends, status
import json

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.database import get_db
from app.models import Policy, Payout, Claim, User
from app.routers.riders import create_rider_account
from app.schemas import UserCreate, UserResponse

router = APIRouter(prefix="/api/admin", tags=["Admin Dashboard"])

@router.get("/metrics")
def get_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    active_policies = db.query(Policy).filter(Policy.status == "active").count()
    total_payouts = db.query(func.sum(Payout.amount)).filter(Payout.status == "completed").scalar() or 0.0
    total_premiums = db.query(func.sum(Policy.weekly_premium)).filter(Policy.status == "active").scalar() or 0.0
    avg_urts = db.query(func.avg(User.base_urts)).filter(User.role == "rider").scalar() or 70.0
    
    loss_ratio = (total_payouts / total_premiums) if total_premiums > 0 else 0.0

    return {
        "active_policies": active_policies,
        "total_payouts": round(total_payouts, 2),
        "total_premiums_weekly": round(total_premiums, 2),
        "loss_ratio": round(loss_ratio, 2),
        "avg_urts": round(avg_urts, 1)
    }

@router.get("/claims")
def get_recent_claims(
    db: Session = Depends(get_db),
    limit: int = 20,
    current_user: User = Depends(require_admin),
):
    claims = db.query(Claim).order_by(Claim.created_at.desc()).limit(limit).all()
    # Simple transform mapped to dict
    return [{
        "id": c.id,
        "rider_id": c.user_id,
        "trigger_type": c.trigger_type,
        "loss_amount": c.loss_amount,
        "payout_amount": c.payout.amount if c.payout else None,
        "disruption_hours": c.disruption_hours,
        "effective_urts": c.effective_urts,
        "status": c.status,
        "created_at": c.created_at
    } for c in claims]

@router.get("/fraud-alerts")
def get_fraud_alerts(
    db: Session = Depends(get_db),
    limit: int = 20,
    current_user: User = Depends(require_admin),
):
    # Claims where effective URTS was very low, indicating penalty applied
    claims = db.query(Claim).filter(Claim.effective_urts < 60).order_by(Claim.created_at.desc()).limit(limit).all()
    return [{
        "claim_id": c.id,
        "rider_id": c.user_id,
        "effective_urts": c.effective_urts,
        "behavioral_signals": json.loads(c.behavioral_signals) if c.behavioral_signals else {},
        "created_at": c.created_at
    } for c in claims]

@router.get("/riders", response_model=list[UserResponse])
def list_riders(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return (
        db.query(User)
        .filter(User.role == "rider")
        .order_by(User.created_at.desc())
        .all()
    )

@router.post("/riders", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_rider(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return create_rider_account(payload, db, trust_reason=f"Admin created rider via {current_user.login_id}")
