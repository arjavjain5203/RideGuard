import json
from typing import Optional, List, Any
from pydantic import BaseModel, field_validator
from datetime import datetime

# USER schemas
class UserCreate(BaseModel):
    zomato_partner_id: str
    name: str
    phone: str
    zone: str
    upi_handle: str

class UserResponse(BaseModel):
    id: str
    zomato_partner_id: str
    name: str
    phone: str
    zone: str
    upi_handle: str
    base_urts: int
    created_at: datetime
    class Config:
        from_attributes = True

class ScoreResponse(BaseModel):
    rider_id: str
    urts_score: int
    last_event: Optional[str] = None
    last_updated: datetime

class ZoneResponse(BaseModel):
    id: str
    name: str
    risk_multiplier: float
    geo_bounds: Optional[str] = None

    class Config:
        from_attributes = True

# EARNINGSschemas
class EarningsResponse(BaseModel):
    rider_id: str
    zomato_partner_id: str
    name: str
    zone: str
    summary: dict
    weekly_breakdown: list

# POLICY schemas
class PremiumCalculateRequest(BaseModel):
    rider_id: str
    modules: List[str]

class PremiumCalculateResponse(BaseModel):
    rider_id: str
    zone: str
    modules: List[str]
    zone_multiplier: float
    risk_score: float
    module_breakdown: dict
    total_weekly_premium: float

class PolicyCreate(BaseModel):
    rider_id: str
    modules: List[str]

class PolicyResponse(BaseModel):
    id: str
    rider_id: str
    modules: Any
    weekly_premium: float
    status: str
    created_at: datetime
    
    @field_validator("modules", mode="before")
    @classmethod
    def parse_modules(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except:
                return []
        if isinstance(v, list):
            return v
        return getattr(v, "coverage_list", [])

    class Config:
        from_attributes = True

class CoverageModuleResponse(BaseModel):
    id: str
    name: str
    display_name: str
    base_price: float
    trigger_type: str
    trigger_threshold: float
    description: Optional[str]

    class Config:
        from_attributes = True

# TRIGGER
class TriggerSimulateRequest(BaseModel):
    zone: str
    rainfall_mm_hr: float = 0
    temperature_c: float = 0
    aqi: float = 0
    traffic_speed_kmh: float = 0

class TriggerEvent(BaseModel):
    trigger_type: str
    trigger_value: float
    threshold: float
    zone: str
    severity: str

class TriggerCheckResponse(BaseModel):
    zone: str
    triggers_fired: list[TriggerEvent]
    claims_created: int
    message: str

class TriggerStatusResponse(BaseModel):
    id: str
    type: str
    value: float
    zone: str
    status: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_hours: float
    
    class Config:
        from_attributes = True

# CLAIMS
class ClaimResponse(BaseModel):
    id: str
    policy_id: str = "N/A"
    rider_id: str
    trigger_type: str
    trigger_value: float
    disruption_start: datetime
    disruption_hours: Optional[float] = 0
    effective_urts: Optional[int] = 0
    status: str
    created_at: datetime
    behavioral_risk_signals: dict = {}

    class Config:
        from_attributes = True

# PAYOUTS
class PayoutProcessRequest(BaseModel):
    claim_id: str

class PayoutResponse(BaseModel):
    id: str
    claim_id: str
    rider_id: str
    amount: float
    urts_factor: float = 1.0
    upi_transaction_id: str
    status: str
    paid_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True
