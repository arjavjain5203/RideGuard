from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

from app.auth import get_current_user, require_admin
from app.core.celery_app import enqueue_task
from app.models import User
from app.schemas import TaskEnqueueResponse
from app.tasks.jobs import generate_llm_insight
from app.services.llm_service import explain_claim, explain_risk, explain_fraud, generate_admin_insights

router = APIRouter(prefix="/api/llm", tags=["LLM"])

class ClaimExplainRequest(BaseModel):
    trigger: str
    hours: float
    payout: float
    urts: int

class RiskExplainRequest(BaseModel):
    zone: str
    risk_score: float

class FraudExplainRequest(BaseModel):
    signals: Dict[str, Any]
    penalty: int

class InsightsRequest(BaseModel):
    zone_data: str

@router.post("/explain-claim")
def explain_claim_endpoint(req: ClaimExplainRequest, current_user: User = Depends(get_current_user)):
    text = explain_claim(req.trigger, req.hours, req.payout, req.urts)
    return {"explanation": text}

@router.post("/explain-risk")
def explain_risk_endpoint(req: RiskExplainRequest, current_user: User = Depends(get_current_user)):
    text = explain_risk(req.zone, req.risk_score)
    return {"explanation": text}

@router.post("/explain-fraud")
def explain_fraud_endpoint(req: FraudExplainRequest, current_user: User = Depends(get_current_user)):
    text = explain_fraud(req.signals, req.penalty)
    return {"explanation": text}

def generate_insights_endpoint(req: InsightsRequest, current_user: User = Depends(require_admin)):
    text = generate_admin_insights(req.zone_data)
    return {"insight": text}


@router.post("/generate-insights", response_model=TaskEnqueueResponse, status_code=202)
def queue_generate_insights_endpoint(req: InsightsRequest, current_user: User = Depends(require_admin)):
    try:
        task = enqueue_task(
            generate_llm_insight,
            "admin_insight",
            req.model_dump(),
            requested_by_user_id=current_user.id,
        )
        return TaskEnqueueResponse(
            task_id=task.id,
            task_name="generate_llm_insight",
            status="queued",
            message="Insight generation has been queued.",
            queued_at=datetime.now(UTC),
            entity_id=current_user.id,
            executed_inline=bool(getattr(task, "successful", lambda: False)()),
            summary={"kind": "admin_insight"},
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
