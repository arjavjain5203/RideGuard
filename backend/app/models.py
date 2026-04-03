import uuid
from datetime import datetime, timezone
import json
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(128), nullable=False)
    zomato_partner_id = Column(String(64), unique=True, nullable=True) # for backward compat
    phone = Column(String(15), nullable=True) # for backward compat
    upi_handle = Column(String(128), nullable=True) # for backward compat
    zone = Column(String(64), nullable=False)
    base_urts = Column(Integer, default=70) # Renamed from trust_score
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    earnings = relationship("Earnings", back_populates="user", uselist=False)
    policies = relationship("Policy", back_populates="user")
    claims = relationship("Claim", back_populates="user")
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
    coverage_types = Column(Text, default="[]") # JSON array string
    weekly_premium = Column(Float, nullable=False)
    status = Column(String(32), default="active")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    user = relationship("User", back_populates="policies")
    
    @property
    def coverage_list(self):
        try:
            return json.loads(self.coverage_types)
        except:
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
    type = Column(String(32), nullable=False) # rain, AQI, heat, traffic
    value = Column(Float, nullable=False)
    zone = Column(String(64), nullable=False)
    status = Column(String(32), default="ACTIVE") # ACTIVE, ONGOING, ENDED
    start_time = Column(DateTime(timezone=True), default=datetime.utcnow)
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration_hours = Column(Float, default=0.0)
    triggered_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    claims = relationship("Claim", back_populates="trigger")

class Claim(Base):
    __tablename__ = "claims"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
    trigger_id = Column(String(36), ForeignKey("triggers.id", ondelete="SET NULL"), nullable=True)
    loss_amount = Column(Float, nullable=False)
    status = Column(String(32), default="pending")
    disruption_hours = Column(Float, default=0.0)
    effective_urts = Column(Integer, default=0)
    behavioral_signals = Column(Text, default="{}")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    user = relationship("User", back_populates="claims")
    trigger = relationship("TriggerRecord", back_populates="claims")
    payout = relationship("Payout", back_populates="claim", uselist=False)

    @property
    def rider_id(self):
        return self.user_id

class Payout(Base):
    __tablename__ = "payouts"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    claim_id = Column(String(36), ForeignKey("claims.id", ondelete="CASCADE"))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE")) # Added for convenience
    amount = Column(Float, nullable=False)
    urts_factor = Column(Float, default=1.0)
    transaction_id = Column(String(64), unique=True, nullable=True)
    status = Column(String(32), default="completed")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    claim = relationship("Claim", back_populates="payout")

    @property
    def rider_id(self):
        return self.user_id

    @property
    def upi_transaction_id(self):
        return self.transaction_id
        
    @property
    def paid_at(self):
        return self.created_at

class TrustLog(Base):
    __tablename__ = "trust_logs"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
    change = Column(Integer, nullable=False)
    reason = Column(String(256), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    user = relationship("User", back_populates="trust_logs")

# Also recreate CoverageModule for the frontend
class CoverageModule(Base):
    __tablename__ = "coverage_modules"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(64), unique=True, nullable=False)
    display_name = Column(String(128), nullable=False)
    base_price = Column(Float, nullable=False)
    trigger_type = Column(String(32), nullable=False)
    trigger_threshold = Column(Float, nullable=False)
    description = Column(String)

class Zone(Base):
    __tablename__ = "zones"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(64), unique=True, nullable=False)
    risk_multiplier = Column(Float, default=1.0)
    geo_bounds = Column(Text, nullable=True) # JSON

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    entity_type = Column(String(32), nullable=False) # trigger, claim, payout, urts
    entity_id = Column(String(36), nullable=False)
    action = Column(String(64), nullable=False)
    details = Column(Text, default="{}") # JSON
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)
