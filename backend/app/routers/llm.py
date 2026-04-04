from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Dict, Any

from app.auth import get_current_user, require_admin
from app.models import User
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

@router.post("/generate-insights")
def generate_insights_endpoint(req: InsightsRequest, current_user: User = Depends(require_admin)):
    text = generate_admin_insights(req.zone_data)
    return {"insight": text}
