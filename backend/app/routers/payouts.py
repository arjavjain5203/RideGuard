import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_rider_or_admin_access
from app.core.celery_app import enqueue_task
from app.database import get_db
from app.models import Claim, Payout, User
from app.schemas import ClaimResponse, PayoutProcessRequest, PayoutResponse, TaskEnqueueResponse
from app.tasks.jobs import process_payout as process_payout_task
from app.services.payment_service import process_claim_payout

router = APIRouter(prefix="/api/payouts", tags=["Payouts"])


def process_payout(
    payload: PayoutProcessRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    claim = db.query(Claim).filter(Claim.id == payload.claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    require_rider_or_admin_access(claim.user_id, current_user)
    if claim.status == "rejected":
        raise HTTPException(status_code=400, detail="Claim was rejected")

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


@router.post("/process", response_model=TaskEnqueueResponse, status_code=202)
def queue_payout_processing(
    payload: PayoutProcessRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    claim = db.query(Claim).filter(Claim.id == payload.claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    require_rider_or_admin_access(claim.user_id, current_user)
    if claim.status == "rejected":
        raise HTTPException(status_code=400, detail="Claim was rejected")

    try:
        task = enqueue_task(
            process_payout_task,
            claim.id,
            initiated_by_user_id=current_user.id,
            auto_source="manual",
        )
        return TaskEnqueueResponse(
            task_id=task.id,
            task_name="process_payout",
            status="queued",
            message="Payout processing has been queued.",
            queued_at=datetime.now(UTC),
            entity_id=claim.id,
            executed_inline=bool(getattr(task, "successful", lambda: False)()),
            summary={"claim_status": claim.status},
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


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


@router.get("/rider/{rider_id}", response_model=list[PayoutResponse])
def get_rider_payouts(
    rider_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_rider_or_admin_access(rider_id, current_user)
    return db.query(Payout).filter(Payout.user_id == rider_id).order_by(Payout.created_at.desc()).all()
