"""Fraud Detection — Behavioral Risk Engine producing signal vectors for URTS."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import Claim, User as Rider


# Signal weights for Event Adjustment
SIGNAL_WEIGHTS = {
    "gps_anomaly": 0.30,
    "cluster_detection": 0.30,
    "activity_mismatch": 0.25,
    "device_inconsistency": 0.15,
}

MAX_EVENT_PENALTY = -50


@dataclass
class BehavioralSignalVector:
    """Structured output from the Behavioral Risk Engine."""
    gps_anomaly: float = 0.0        # 0.0 - 1.0
    cluster_detection: float = 0.0   # 0.0 - 1.0
    activity_mismatch: float = 0.0   # 0.0 - 1.0
    device_inconsistency: float = 0.0  # 0.0 - 1.0
    flags: list[str] = field(default_factory=list)

    def event_adjustment(self) -> int:
        """Calculate weighted event adjustment (0 to -50)."""
        raw = (
            SIGNAL_WEIGHTS["gps_anomaly"] * self.gps_anomaly
            + SIGNAL_WEIGHTS["cluster_detection"] * self.cluster_detection
            + SIGNAL_WEIGHTS["activity_mismatch"] * self.activity_mismatch
            + SIGNAL_WEIGHTS["device_inconsistency"] * self.device_inconsistency
        )
        # Scale raw (0-1) to penalty (0 to -50)
        penalty = int(round(raw * abs(MAX_EVENT_PENALTY)))
        return -penalty

    def to_dict(self) -> dict:
        return {
            "gps_anomaly": self.gps_anomaly,
            "cluster_detection": self.cluster_detection,
            "activity_mismatch": self.activity_mismatch,
            "device_inconsistency": self.device_inconsistency,
            "event_adjustment": self.event_adjustment(),
            "flags": self.flags,
        }


def run_fraud_checks(
    db: Session,
    rider: Rider,
    trigger_type: str,
    trigger_value: float,
    zone: str,
) -> BehavioralSignalVector:
    """
    Execute the Behavioral Risk Engine pipeline.

    Checks:
    1. GPS / zone mismatch
    2. Duplicate claim detection
    3. Cluster detection (simplified: high claim density in zone)
    4. Activity validation (rider is_active check)
    """
    signals = BehavioralSignalVector()

    # 1. GPS / Zone mismatch — rider's registered zone vs event zone
    if rider.zone.lower().replace(" ", "_") != zone.lower().replace(" ", "_"):
        signals.gps_anomaly = 0.8
        signals.flags.append("zone_mismatch")

    # 2. Duplicate claim detection — same rider + same trigger type within 6 hours
    six_hours_ago = datetime.utcnow() - timedelta(hours=6)
    duplicate = (
        db.query(Claim)
        .filter(
            Claim.user_id == rider.id,
            Claim.trigger_type == trigger_type,
            Claim.created_at >= six_hours_ago,
        )
        .first()
    )
    if duplicate:
        signals.gps_anomaly = max(signals.gps_anomaly, 0.6)
        signals.activity_mismatch = 0.7
        signals.flags.append("duplicate_claim_window")

    # 3. Cluster detection — more than 5 claims in same zone in last 2 hours
    two_hours_ago = datetime.utcnow() - timedelta(hours=2)
    zone_claims_count = (
        db.query(Claim)
        .join(Rider, Claim.user_id == Rider.id)
        .filter(
            Rider.zone == zone,
            Claim.trigger_type == trigger_type,
            Claim.created_at >= two_hours_ago,
        )
        .count()
    )
    if zone_claims_count > 5:
        signals.cluster_detection = min(zone_claims_count / 10.0, 1.0)
        signals.flags.append("cluster_anomaly")

    # 4. Activity mismatch — rider not currently active
    if not rider.is_active:
        signals.activity_mismatch = max(signals.activity_mismatch, 0.9)
        signals.flags.append("rider_inactive")

    recent_claims_count = (
        db.query(Claim)
        .filter(
            Claim.user_id == rider.id,
            Claim.created_at >= datetime.utcnow() - timedelta(days=7),
        )
        .count()
    )
    if recent_claims_count >= 3:
        signals.activity_mismatch = max(signals.activity_mismatch, min(recent_claims_count / 5.0, 1.0))
        signals.flags.append("high_claim_frequency")

    return signals


def calculate_effective_urts(base_urts: int, signal_vector: BehavioralSignalVector) -> int:
    """Effective URTS = Base URTS + Event Adjustment."""
    effective = base_urts + signal_vector.event_adjustment()
    return max(0, min(100, effective))


def get_urts_factor(effective_urts: int) -> float:
    """Map Effective URTS to payout factor."""
    if effective_urts >= 80:
        return 1.0
    elif effective_urts >= 60:
        return 0.9
    elif effective_urts >= 40:
        return 0.7
    return 0.0
