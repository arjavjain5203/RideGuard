import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_rider_or_admin_access
from app.database import get_db
from app.models import Claim, Payout, User
from app.schemas import ClaimResponse, PayoutProcessRequest, PayoutResponse
from app.services.payment_service import process_claim_payout

router = APIRouter(prefix="/api/payouts", tags=["Payouts"])


@router.post("/process", response_model=PayoutResponse, status_code=201)
def process_payout(
    payload: PayoutProcessRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    claim = db.query(Claim).filter(Claim.id == payload.claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    require_rider_or_admin_access(claim.user_id, current_user)
    if claim.status == "paid":
        raise HTTPException(status_code=409, detail="Claim already paid")
    if claim.status == "rejected":
        raise HTTPException(status_code=400, detail="Claim was rejected")
    if claim.status == "capped" and claim.payout:
        raise HTTPException(status_code=409, detail="Claim payout already capped")

    try:
        payout = process_claim_payout(db, claim, auto_source="manual")
        db.commit()
        if payout is None:
            raise HTTPException(status_code=400, detail="Payout blocked — Effective URTS too low")
        db.refresh(payout)
        return payout
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Transaction failed: {str(exc)}") from exc


@router.get("/claim/{claim_id}", response_model=ClaimResponse)
def get_claim(
    claim_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    require_rider_or_admin_access(claim.user_id, current_user)

    return ClaimResponse(
        id=claim.id,
        policy_id=claim.policy_id,
        rider_id=claim.user_id,
        trigger_type=claim.trigger_type or (claim.trigger.type if claim.trigger else "unknown"),
        trigger_value=claim.trigger_value or (claim.trigger.value if claim.trigger else 0.0),
        disruption_start=claim.disruption_start or claim.created_at,
        disruption_end=claim.disruption_end,
        disruption_hours=claim.disruption_hours,
        loss_amount=claim.loss_amount,
        effective_urts=claim.effective_urts,
        status=claim.status,
        created_at=claim.created_at,
        behavioral_risk_signals=json.loads(claim.behavioral_signals) if claim.behavioral_signals else {},
        payout_amount=claim.payout.amount if claim.payout else None,
        payout_status=claim.payout.status if claim.payout else None,
    )


@router.get("/rider/{rider_id}", response_model=list[PayoutResponse])
def get_rider_payouts(
    rider_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_rider_or_admin_access(rider_id, current_user)
    return db.query(Payout).filter(Payout.user_id == rider_id).order_by(Payout.created_at.desc()).all()
