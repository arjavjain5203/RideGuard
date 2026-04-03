from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

from app.database import get_db
from app.models import User, Policy, CoverageModule
from app.schemas import (
    PremiumCalculateRequest, PremiumCalculateResponse,
    PolicyCreate, PolicyResponse, CoverageModuleResponse
)
from app.services.premium_calculator import calculate_premium
from app.services.risk_engine import calculate_zone_risk_score
import json

router = APIRouter(prefix="/api/policies", tags=["Policies"])

@router.get("/modules", response_model=list[CoverageModuleResponse])
def list_coverage_modules(db: Session = Depends(get_db)):
    return db.query(CoverageModule).all()

@router.post("/calculate-premium", response_model=PremiumCalculateResponse)
def calculate_rider_premium(payload: PremiumCalculateRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == payload.rider_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Rider not found")

    risk_score = calculate_zone_risk_score()
    result = calculate_premium(db=db, rider_id=user.id, zone=user.zone, selected_modules=payload.modules, risk_score=risk_score)

    return PremiumCalculateResponse(
        rider_id=user.id,
        zone=user.zone,
        modules=payload.modules,
        **result,
    )

@router.post("/", response_model=PolicyResponse, status_code=201)
def create_policy(payload: PolicyCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == payload.rider_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Rider not found")

    active = db.query(Policy).filter(Policy.user_id == user.id, Policy.status == "active").first()
    if active:
        raise HTTPException(status_code=409, detail="Rider already has an active policy")

    risk_score = calculate_zone_risk_score()
    premium_data = calculate_premium(db=db, rider_id=user.id, zone=user.zone, selected_modules=payload.modules, risk_score=risk_score)

    policy = Policy(
        user_id=user.id,
        coverage_types=json.dumps(payload.modules),
        weekly_premium=premium_data["total_weekly_premium"],
        status="active"
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy

@router.get("/rider/{rider_id}", response_model=list[PolicyResponse])
def get_rider_policies(rider_id: str, db: Session = Depends(get_db)):
    return db.query(Policy).filter(Policy.user_id == rider_id).all()
