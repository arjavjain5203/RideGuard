from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import json
import uuid

from app.database import get_db
from app.models import Claim, Payout, User, TrustLog, Policy, AuditLog
from app.schemas import PayoutProcessRequest, PayoutResponse, ClaimResponse
from app.services.fraud_detection import get_urts_factor
from datetime import datetime, timedelta
from sqlalchemy import func

router = APIRouter(prefix="/api/payouts", tags=["Payouts"])

@router.post("/process", response_model=PayoutResponse, status_code=201)
def process_payout(payload: PayoutProcessRequest, db: Session = Depends(get_db)):
    claim = db.query(Claim).filter(Claim.id == payload.claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    if claim.status == "paid":
        raise HTTPException(status_code=409, detail="Claim already paid")
    if claim.status == "rejected":
        raise HTTPException(status_code=400, detail="Claim was rejected")

    user = db.query(User).filter(User.id == claim.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Assuming we attach behavioral risk implicitly or skip for pure DB MVP
    urts_factor = get_urts_factor(user.base_urts)
    if urts_factor == 0.0:
        claim.status = "rejected"
        db.commit()
        raise HTTPException(status_code=400, detail="Payout blocked — Trust Score too low")

    # Get policy to check caps (Part 6)
    policy = db.query(Policy).filter(Policy.user_id == user.id, Policy.status == "active").first()
    weekly_premium = policy.weekly_premium if policy else 0.0

    # Part 16: Weekly & Monthly Tracking
    now_ts = datetime.utcnow()
    one_week_ago = now_ts - timedelta(days=7)
    one_month_ago = now_ts - timedelta(days=30)

    weekly_total = db.query(func.sum(Payout.amount)).filter(
        Payout.user_id == user.id, Payout.created_at >= one_week_ago
    ).scalar() or 0.0

    monthly_total = db.query(func.sum(Payout.amount)).filter(
        Payout.user_id == user.id, Payout.created_at >= one_month_ago
    ).scalar() or 0.0

    max_weekly_payout = 2.0 * weekly_premium
    max_monthly_payout = 6.0 * (weekly_premium * 4.0)

    # Calculate requested amount
    payout_amt = round(claim.loss_amount * urts_factor, 2)
    
    # Cap enforcement
    available_weekly = max(0.0, max_weekly_payout - weekly_total)
    available_monthly = max(0.0, max_monthly_payout - monthly_total)

    payout_amt = min(payout_amt, available_weekly, available_monthly)

    # Ensure transaction safety
    try:
        payout = Payout(
            claim_id=claim.id,
            user_id=user.id,
            amount=payout_amt,
            urts_factor=urts_factor,
            transaction_id=f"UPI-RG-{str(uuid.uuid4())[:12].upper()}",
            status="completed" if payout_amt > 0 else "capped"
        )
        claim.status = "paid" if payout_amt > 0 else "capped"
        db.add(payout)
        
        db.add(AuditLog(entity_type="payout", entity_id=payout.id, action="PROCESSED", details=json.dumps({"amount": payout_amt, "weekly_total": weekly_total})))

        # Trust Score reward logic +2
        new_score = min(100, user.base_urts + 2)
        user.base_urts = new_score
    
        tlog = TrustLog(
            user_id=user.id,
            change=2,
            reason=f"Valid claim {claim.id} paid"
        )
        db.add(tlog)

        db.commit()
        db.refresh(payout)
        return payout
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Transaction failed: {str(e)}")

@router.get("/claim/{claim_id}", response_model=ClaimResponse)
def get_claim(claim_id: str, db: Session = Depends(get_db)):
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
        
    return ClaimResponse(
        id=claim.id,
        rider_id=claim.user_id,
        trigger_type=claim.trigger.type if claim.trigger else "unknown",
        trigger_value=claim.trigger.value if claim.trigger else 0.0,
        disruption_start=claim.created_at,
        disruption_hours=claim.disruption_hours,
        effective_urts=claim.effective_urts,
        status=claim.status,
        created_at=claim.created_at,
        behavioral_risk_signals=json.loads(claim.behavioral_signals) if claim.behavioral_signals else {}
    )

@router.get("/rider/{rider_id}", response_model=list[PayoutResponse])
def get_rider_payouts(rider_id: str, db: Session = Depends(get_db)):
    return db.query(Payout).filter(Payout.user_id == rider_id).all()
