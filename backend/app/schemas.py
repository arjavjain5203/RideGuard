import json
import re
from typing import Any, List, Optional

from pydantic import BaseModel, field_validator
from datetime import datetime

from app.config import settings

# USER schemas
class UserCreate(BaseModel):
    login_id: str
    password: str
    zomato_partner_id: str
    name: str
    phone: str
    zone: str
    upi_handle: str

    @field_validator("login_id", "zomato_partner_id", "name", "upi_handle")
    @classmethod
    def strip_required_strings(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field cannot be empty")
        return cleaned

    @field_validator("login_id")
    @classmethod
    def validate_login_id(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if len(cleaned) < 4:
            raise ValueError("Login ID must be at least 4 characters")
        if not re.fullmatch(r"[a-z0-9._@-]+", cleaned):
            raise ValueError("Login ID may only contain letters, numbers, ., _, -, and @")
        return cleaned

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
            raise ValueError("Password must contain at least one letter and one number")
        return value

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        cleaned = re.sub(r"\s+", "", value)
        if not re.fullmatch(r"\d{10}", cleaned):
            raise ValueError("Phone number must be 10 digits")
        return cleaned

    @field_validator("upi_handle")
    @classmethod
    def validate_upi_handle(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if "@" not in cleaned or cleaned.startswith("@") or cleaned.endswith("@"):
            raise ValueError("UPI handle must look like name@bank")
        return cleaned

    @field_validator("zone")
    @classmethod
    def validate_zone(cls, value: str) -> str:
        cleaned = value.strip()
        normalized = cleaned.lower().replace(" ", "_")
        if normalized not in settings.ZONE_MULTIPLIERS:
            raise ValueError("Unsupported zone")
        return cleaned

class UserResponse(BaseModel):
    id: str
    login_id: Optional[str] = None
    role: str = "rider"
    zomato_partner_id: str
    name: str
    phone: str
    zone: str
    upi_handle: str
    is_active: bool = True
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


class LoginRequest(BaseModel):
    login_id: str
    password: str

    @field_validator("login_id")
    @classmethod
    def normalize_login_id(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not cleaned:
            raise ValueError("Login ID is required")
        return cleaned

    @field_validator("password")
    @classmethod
    def validate_login_password(cls, value: str) -> str:
        if not value:
            raise ValueError("Password is required")
        return value


class AuthUserResponse(BaseModel):
    id: str
    login_id: Optional[str] = None
    role: str
    name: str
    zomato_partner_id: Optional[str] = None
    phone: Optional[str] = None
    zone: Optional[str] = None
    upi_handle: Optional[str] = None
    base_urts: int
    created_at: datetime


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUserResponse

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

    @field_validator("modules")
    @classmethod
    def normalize_modules(cls, value: List[str]) -> List[str]:
        cleaned = []
        for module_name in value:
            normalized = module_name.strip().lower()
            if normalized and normalized not in cleaned:
                cleaned.append(normalized)
        if not cleaned:
            raise ValueError("At least one module is required")
        return cleaned

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

    @field_validator("modules")
    @classmethod
    def normalize_modules(cls, value: List[str]) -> List[str]:
        cleaned = []
        for module_name in value:
            normalized = module_name.strip().lower()
            if normalized and normalized not in cleaned:
                cleaned.append(normalized)
        if not cleaned:
            raise ValueError("At least one module is required")
        return cleaned

class PolicyUpdate(BaseModel):
    modules: List[str]

    @field_validator("modules")
    @classmethod
    def normalize_modules(cls, value: List[str]) -> List[str]:
        cleaned = []
        for module_name in value:
            normalized = module_name.strip().lower()
            if normalized and normalized not in cleaned:
                cleaned.append(normalized)
        if not cleaned:
            raise ValueError("At least one module is required")
        return cleaned

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
    trigger_duration_hours: float = 0.0
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
    disruption_probability: Optional[float] = None
    decision_reason: Optional[str] = None

class TriggerCheckResponse(BaseModel):
    zone: str
    triggers_fired: list[TriggerEvent]
    claims_created: int
    payouts_created: int
    message: str


class TaskEnqueueResponse(BaseModel):
    task_id: str
    task_name: str
    status: str = "queued"
    message: str
    queued_at: datetime
    entity_id: Optional[str] = None
    executed_inline: bool = False
    summary: dict = {}


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result_summary: Optional[dict] = None
    entity_id: Optional[str] = None
    error: Optional[str] = None

class TriggerStatusResponse(BaseModel):
    id: str
    type: str
    value: float
    zone: str
    status: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_hours: float
    disruption_probability: Optional[float] = None
    decision_reason: Optional[str] = None
    
    class Config:
        from_attributes = True

# CLAIMS
class ClaimResponse(BaseModel):
    id: str
    policy_id: Optional[str] = None
    rider_id: str
    trigger_type: str
    trigger_value: float
    disruption_start: datetime
    disruption_end: Optional[datetime] = None
    disruption_hours: Optional[float] = 0
    loss_amount: float
    effective_urts: Optional[int] = 0
    effective_urts_at_event: Optional[int] = None
    event_adjustment: Optional[float] = 0.0
    anomaly_score: Optional[float] = 0.0
    fraud_flag: bool = False
    status: str
    created_at: datetime
    behavioral_risk_signals: dict = {}
    payout_amount: Optional[float] = None
    payout_status: Optional[str] = None

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


class ClaimListResponse(BaseModel):
    claims: list[ClaimResponse]
