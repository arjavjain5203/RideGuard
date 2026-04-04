import json
import uuid
from datetime import datetime, timedelta

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(128), nullable=False)
    login_id = Column(String(128), unique=True, nullable=True)
    password_hash = Column(String(512), nullable=True)
    role = Column(String(16), default="rider", nullable=False)
    zomato_partner_id = Column(String(64), unique=True, nullable=True)
    phone = Column(String(15), nullable=True)
    upi_handle = Column(String(128), nullable=True)
    zone = Column(String(64), nullable=False)
    hourly_income = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True)
    base_urts = Column(Integer, default=70)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    earnings = relationship("Earnings", back_populates="user", uselist=False)
    policies = relationship("Policy", back_populates="user")
    claims = relationship("Claim", back_populates="user")
    payouts = relationship("Payout", back_populates="user")
    trust_logs = relationship("TrustLog", back_populates="user")


class Earnings(Base):
    __tablename__ = "earnings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
    weekly_earnings = Column(Float, nullable=False)
    hours_worked = Column(Integer, nullable=False)
    active_days = Column(Integer, nullable=False)

    user = relationship("User", back_populates="earnings")


class Policy(Base):
    __tablename__ = "policies"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
    coverage_types = Column(Text, default="[]")
    weekly_premium = Column(Float, nullable=False)
    zone_multiplier = Column(Float, default=1.0)
    risk_score = Column(Float, default=0.5)
    status = Column(String(32), default="active")
    valid_from = Column(DateTime(timezone=True), default=datetime.utcnow)
    valid_until = Column(DateTime(timezone=True), default=lambda: datetime.utcnow() + timedelta(days=7))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    user = relationship("User", back_populates="policies")
    claims = relationship("Claim", back_populates="policy")

    @property
    def coverage_list(self):
        try:
            return json.loads(self.coverage_types or "[]")
        except (TypeError, json.JSONDecodeError):
            return []

    @property
    def rider_id(self):
        return self.user_id

    @property
    def modules(self):
        return self.coverage_list


class TriggerRecord(Base):
    __tablename__ = "triggers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    type = Column(String(32), nullable=False)
    value = Column(Float, nullable=False)
    zone = Column(String(64), nullable=False)
    status = Column(String(32), default="ACTIVE")
    start_time = Column(DateTime(timezone=True), default=datetime.utcnow)
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration_hours = Column(Float, default=0.0)
    triggered_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    claims = relationship("Claim", back_populates="trigger")


class Claim(Base):
    __tablename__ = "claims"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    policy_id = Column(String(36), ForeignKey("policies.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
    trigger_id = Column(String(36), ForeignKey("triggers.id", ondelete="SET NULL"), nullable=True)
    trigger_type = Column(String(32), nullable=True)
    trigger_value = Column(Float, nullable=True)
    disruption_start = Column(DateTime(timezone=True), nullable=True)
    disruption_end = Column(DateTime(timezone=True), nullable=True)
    loss_amount = Column(Float, nullable=False)
    status = Column(String(32), default="pending")
    disruption_hours = Column(Float, default=0.0)
    effective_urts = Column(Integer, default=0)
    behavioral_signals = Column(Text, default="{}")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    user = relationship("User", back_populates="claims")
    policy = relationship("Policy", back_populates="claims")
    trigger = relationship("TriggerRecord", back_populates="claims")
    payout = relationship("Payout", back_populates="claim", uselist=False)

    @property
    def rider_id(self):
        return self.user_id

    @property
    def behavioral_risk_signals(self):
        try:
            return json.loads(self.behavioral_signals or "{}")
        except (TypeError, json.JSONDecodeError):
            return {}


class Payout(Base):
    __tablename__ = "payouts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    claim_id = Column(String(36), ForeignKey("claims.id", ondelete="CASCADE"))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
    amount = Column(Float, nullable=False)
    urts_factor = Column(Float, default=1.0)
    transaction_id = Column(String(64), unique=True, nullable=True)
    status = Column(String(32), default="completed")
    paid_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    claim = relationship("Claim", back_populates="payout")
    user = relationship("User", back_populates="payouts")

    @property
    def rider_id(self):
        return self.user_id

    @property
    def upi_transaction_id(self):
        return self.transaction_id


class TrustLog(Base):
    __tablename__ = "trust_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
    change = Column(Integer, nullable=False)
    reason = Column(String(256), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    user = relationship("User", back_populates="trust_logs")


class CoverageModule(Base):
    __tablename__ = "coverage_modules"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(64), unique=True, nullable=False)
    display_name = Column(String(128), nullable=False)
    base_price = Column(Float, nullable=False)
    trigger_type = Column(String(32), nullable=False)
    trigger_threshold = Column(Float, nullable=False)
    trigger_duration_hours = Column(Float, default=0.0)
    description = Column(String)


class Zone(Base):
    __tablename__ = "zones"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(64), unique=True, nullable=False)
    risk_multiplier = Column(Float, default=1.0)
    geo_bounds = Column(Text, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    entity_type = Column(String(32), nullable=False)
    entity_id = Column(String(36), nullable=False)
    action = Column(String(64), nullable=False)
    details = Column(Text, default="{}")
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)
