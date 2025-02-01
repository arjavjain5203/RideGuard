import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_rider_or_admin_access
from app.database import get_db
from app.models import Claim, User
from app.schemas import ClaimListResponse, ClaimResponse

router = APIRouter(prefix="/api/claims", tags=["Claims"])


def serialize_claim(claim: Claim) -> ClaimResponse:
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
        effective_urts_at_event=claim.effective_urts_at_event,
        event_adjustment=claim.event_adjustment,
        anomaly_score=claim.anomaly_score,
        fraud_flag=bool(claim.fraud_flag),
        status=claim.status,
        created_at=claim.created_at,
        behavioral_risk_signals=json.loads(claim.behavioral_signals) if claim.behavioral_signals else {},
        payout_amount=claim.payout.amount if claim.payout else None,
        payout_status=claim.payout.status if claim.payout else None,
    )


@router.get("/rider/{rider_id}", response_model=ClaimListResponse)
def list_rider_claims(
    rider_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_rider_or_admin_access(rider_id, current_user)
    claims = db.query(Claim).filter(Claim.user_id == rider_id).order_by(Claim.created_at.desc()).all()
    return ClaimListResponse(claims=[serialize_claim(claim) for claim in claims])


@router.get("/{claim_id}", response_model=ClaimResponse)
def get_claim(
    claim_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    require_rider_or_admin_access(claim.user_id, current_user)
    return serialize_claim(claim)
