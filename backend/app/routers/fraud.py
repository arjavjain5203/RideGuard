from datetime import UTC, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_rider_or_admin_access
from app.core.celery_app import enqueue_task
from app.database import get_db
from app.models import Claim, User
from app.schemas import TaskEnqueueResponse
from app.tasks.jobs import evaluate_fraud as evaluate_fraud_task
from app.services.behavior_engine import build_fraud_features
from app.services.fraud_model_service import evaluate_fraud

router = APIRouter(prefix="/api/fraud", tags=["Fraud"])


class FraudEvaluateRequest(BaseModel):
    rider_id: str
    claim_id: Optional[str] = None


def evaluate_fraud_endpoint(
    payload: FraudEvaluateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_rider_or_admin_access(payload.rider_id, current_user)
    rider = db.query(User).filter(User.id == payload.rider_id).first()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")

    claim = None
    zone = rider.zone
    if payload.claim_id:
        claim = db.query(Claim).filter(Claim.id == payload.claim_id).first()
        if not claim:
            raise HTTPException(status_code=404, detail="Claim not found")
        require_rider_or_admin_access(claim.user_id, current_user)
        if claim.user_id != rider.id:
            raise HTTPException(status_code=400, detail="Claim does not belong to rider")
        zone = claim.trigger.zone if claim.trigger and claim.trigger.zone else rider.zone

    features = build_fraud_features(db, rider, zone, claim)
    result = evaluate_fraud(features)
    return {
        "rider_id": rider.id,
        "claim_id": claim.id if claim else None,
        "anomaly_score": result["anomaly_score"],
        "is_anomaly": result["is_anomaly"],
        "model_available": result["model_available"],
        "features": features,
    }


@router.post("/evaluate", response_model=TaskEnqueueResponse, status_code=202)
def queue_fraud_evaluation(
    payload: FraudEvaluateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_rider_or_admin_access(payload.rider_id, current_user)
    rider = db.query(User).filter(User.id == payload.rider_id).first()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")
    if payload.claim_id:
        claim = db.query(Claim).filter(Claim.id == payload.claim_id).first()
        if not claim:
            raise HTTPException(status_code=404, detail="Claim not found")
        if claim.user_id != rider.id:
            raise HTTPException(status_code=400, detail="Claim does not belong to rider")

    try:
        task = enqueue_task(evaluate_fraud_task, payload.rider_id, claim_id=payload.claim_id)
        return TaskEnqueueResponse(
            task_id=task.id,
            task_name="evaluate_fraud",
            status="queued",
            message="Fraud evaluation has been queued.",
            queued_at=datetime.now(UTC),
            entity_id=payload.rider_id,
            executed_inline=bool(getattr(task, "successful", lambda: False)()),
            summary={"claim_id": payload.claim_id},
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
