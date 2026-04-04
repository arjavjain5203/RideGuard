from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.auth import get_current_user, require_rider_or_admin_access
from app.database import get_db
from app.models import User, Policy, CoverageModule
from app.schemas import (
    PremiumCalculateRequest, PremiumCalculateResponse,
    PolicyCreate, PolicyResponse, PolicyUpdate, CoverageModuleResponse
)
from app.services.premium_calculator import calculate_premium
from app.services.risk_engine import calculate_zone_risk_score
from app.routers.mock_external import get_weather, get_aqi, get_traffic
import json

router = APIRouter(prefix="/api/policies", tags=["Policies"])


def get_live_zone_risk_score(zone: str) -> float:
    weather = get_weather(zone)
    aqi_snapshot = get_aqi(zone)
    traffic = get_traffic(zone)
    return calculate_zone_risk_score(
        rainfall_mm_hr=weather.get("rainfall", 0.0),
        temperature_c=weather.get("temperature", 30.0),
        aqi=aqi_snapshot.get("aqi", 50.0),
        traffic_speed_kmh=traffic.get("avg_speed", 30.0),
    )


def validate_modules(db: Session, module_names: list[str]) -> None:
    supported_modules = {
        module.name for module in db.query(CoverageModule).filter(CoverageModule.name.in_(module_names)).all()
    }
    invalid = [module_name for module_name in module_names if module_name not in supported_modules]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Unsupported coverage modules: {', '.join(invalid)}")


@router.get("/modules", response_model=list[CoverageModuleResponse])
def list_coverage_modules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(CoverageModule).all()

@router.post("/calculate-premium", response_model=PremiumCalculateResponse)
def calculate_rider_premium(
    payload: PremiumCalculateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_rider_or_admin_access(payload.rider_id, current_user)
    user = db.query(User).filter(User.id == payload.rider_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Rider not found")

    validate_modules(db, payload.modules)

    risk_score = get_live_zone_risk_score(user.zone)
    result = calculate_premium(
        db=db,
        rider_id=user.id,
        zone=user.zone,
        selected_modules=payload.modules,
        risk_score=risk_score,
    )

    return PremiumCalculateResponse(
        rider_id=user.id,
        zone=user.zone,
        modules=payload.modules,
        **result,
    )

@router.post("/", response_model=PolicyResponse, status_code=201)
def create_policy(
    payload: PolicyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_rider_or_admin_access(payload.rider_id, current_user)
    user = db.query(User).filter(User.id == payload.rider_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Rider not found")

    active = db.query(Policy).filter(Policy.user_id == user.id, Policy.status == "active").first()
    if active:
        raise HTTPException(status_code=409, detail="Rider already has an active policy")

    validate_modules(db, payload.modules)

    risk_score = get_live_zone_risk_score(user.zone)
    premium_data = calculate_premium(
        db=db,
        rider_id=user.id,
        zone=user.zone,
        selected_modules=payload.modules,
        risk_score=risk_score,
    )

    policy = Policy(
        user_id=user.id,
        coverage_types=json.dumps(payload.modules),
        weekly_premium=premium_data["total_weekly_premium"],
        zone_multiplier=premium_data["zone_multiplier"],
        risk_score=premium_data["risk_score"],
        status="active",
        valid_from=datetime.utcnow(),
        valid_until=datetime.utcnow() + timedelta(days=7),
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy

@router.put("/{policy_id}", response_model=PolicyResponse)
def update_policy(
    policy_id: str,
    payload: PolicyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    policy = db.query(Policy).filter(Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    require_rider_or_admin_access(policy.user_id, current_user)

    if policy.status != "active":
        raise HTTPException(status_code=400, detail="Only active policies can be updated")

    user = db.query(User).filter(User.id == policy.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Rider not found")

    validate_modules(db, payload.modules)

    risk_score = get_live_zone_risk_score(user.zone)
    premium_data = calculate_premium(
        db=db,
        rider_id=user.id,
        zone=user.zone,
        selected_modules=payload.modules,
        risk_score=risk_score,
    )

    policy.coverage_types = json.dumps(payload.modules)
    policy.weekly_premium = premium_data["total_weekly_premium"]
    policy.zone_multiplier = premium_data["zone_multiplier"]
    policy.risk_score = premium_data["risk_score"]

    db.commit()
    db.refresh(policy)
    return policy

@router.get("/rider/{rider_id}", response_model=list[PolicyResponse])
def get_rider_policies(
    rider_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_rider_or_admin_access(rider_id, current_user)
    return db.query(Policy).filter(Policy.user_id == rider_id).all()
