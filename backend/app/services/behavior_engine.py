"""Unified Risk & Trust Score behavioral risk engine."""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import Claim, Earnings, User
from app.services.fraud_model_service import evaluate_fraud

SIGNAL_WEIGHTS = {
    "gps_anomaly": 0.25,
    "cluster_risk": 0.25,
    "activity_mismatch": 0.20,
    "device_risk": 0.10,
    "anomaly_score": 0.20,
}
MAX_EVENT_PENALTY = 50.0
MAX_SINGLE_EVENT_URTS_DROP = 20.0
logger = logging.getLogger(__name__)


def normalize_zone(zone: str | None) -> str:
    return (zone or "").strip().lower().replace(" ", "_")


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def get_payout_factor(effective_urts: int) -> float:
    if effective_urts >= 80:
        return 1.0
    if effective_urts >= 60:
        return 0.9
    if effective_urts >= 40:
        return 0.7
    return 0.0


def get_device_risk(rider_id: str, claim_id: str | None) -> float:
    digest = hashlib.sha256(f"{rider_id}:{claim_id or ''}".encode("utf-8")).hexdigest()
    return round((int(digest[:4], 16) % 6) / 100.0, 2)


def calculate_event_adjustment(signals: dict[str, float]) -> float:
    weighted_risk = sum(SIGNAL_WEIGHTS[key] * signals.get(key, 0.0) for key in SIGNAL_WEIGHTS)
    raw_adjustment = -(weighted_risk * MAX_EVENT_PENALTY)
    return round(max(raw_adjustment, -MAX_SINGLE_EVENT_URTS_DROP), 2)


def build_fraud_features(db: Session, rider: User, zone: str, claim: Claim | None = None) -> dict:
    since_one_week = datetime.now(UTC) - timedelta(days=7)
    recent_claims_query = db.query(Claim).filter(Claim.user_id == rider.id, Claim.created_at >= since_one_week)
    if claim is not None:
        recent_claims_query = recent_claims_query.filter(Claim.id != claim.id)
    recent_claims = recent_claims_query.order_by(Claim.created_at.asc()).all()

    earnings = db.query(Earnings).filter(Earnings.user_id == rider.id).first()
    hours_worked = float(earnings.hours_worked if earnings else 0.0)
    active_days = max(1.0, float(earnings.active_days if earnings else 1.0))
    claim_hours = [float(claim_record.created_at.hour) for claim_record in recent_claims if claim_record.created_at]
    if len(claim_hours) >= 2:
        average_hour = sum(claim_hours) / len(claim_hours)
        claim_time_variance = sum((hour - average_hour) ** 2 for hour in claim_hours) / len(claim_hours)
    else:
        claim_time_variance = 0.0

    return {
        "claims_per_week": float(len(recent_claims)),
        "avg_working_hours_per_day": round(hours_worked / active_days, 2),
        "claim_to_work_ratio": round(float(len(recent_claims)) / max(hours_worked, 1.0), 4),
        "zone_mismatch_score": 1.0 if normalize_zone(rider.zone) != normalize_zone(zone) else 0.0,
        "claim_time_variance": round(claim_time_variance, 4),
    }


def evaluate_event(db: Session, rider_id: str, zone: str, claim: Claim | None = None) -> dict:
    rider = db.query(User).filter(User.id == rider_id).first()
    if not rider:
        raise ValueError("Rider not found for URTS evaluation")

    flags: list[str] = []
    gps_anomaly = 0.0
    if normalize_zone(rider.zone) != normalize_zone(zone):
        gps_anomaly = 0.85
        flags.append("zone_mismatch")

    since_two_hours = datetime.now(UTC) - timedelta(hours=2)
    cluster_query = (
        db.query(Claim)
        .join(User, Claim.user_id == User.id)
        .filter(User.zone == zone, Claim.created_at >= since_two_hours)
    )
    if claim is not None:
        cluster_query = cluster_query.filter(Claim.id != claim.id)
        if claim.trigger_type:
            cluster_query = cluster_query.filter(Claim.trigger_type == claim.trigger_type)
    cluster_count = cluster_query.count()
    cluster_risk = round(clamp((cluster_count - 2) / 6.0), 2)
    if cluster_risk >= 0.2:
        flags.append("cluster_risk")

    since_one_week = datetime.now(UTC) - timedelta(days=7)
    recent_claims_query = db.query(Claim).filter(Claim.user_id == rider.id, Claim.created_at >= since_one_week)
    if claim is not None:
        recent_claims_query = recent_claims_query.filter(Claim.id != claim.id)
    recent_claims = recent_claims_query.count()
    earnings = db.query(Earnings).filter(Earnings.user_id == rider.id).first()
    active_days = max(1, int(earnings.active_days if earnings else 1))
    activity_mismatch = round(clamp((recent_claims / active_days) / 2.0), 2)
    if not rider.is_active:
        activity_mismatch = max(activity_mismatch, 0.9)
        flags.append("rider_inactive")
    if activity_mismatch >= 0.2 and "rider_inactive" not in flags:
        flags.append("activity_mismatch")

    device_risk = get_device_risk(rider.id, claim.id if claim else None)
    if device_risk >= 0.2:
        flags.append("device_risk")

    fraud_features = build_fraud_features(db, rider, zone, claim)
    fraud_result = evaluate_fraud(fraud_features)
    anomaly_score = round(clamp(float(fraud_result.get("anomaly_score", 0.0))), 2)
    is_model_anomaly = bool(fraud_result.get("is_anomaly", False))
    logger.info(
        "fraud model evaluated for URTS",
        extra={
            "rider_id": rider.id,
            "claim_id": claim.id if claim else None,
            "anomaly_score": anomaly_score,
            "is_anomaly": is_model_anomaly,
            "fraud_features": fraud_features,
            "feature_emphasis": fraud_result.get("feature_emphasis", {}),
            "calibration_boost": fraud_result.get("calibration_boost", 0.0),
        },
    )
    if is_model_anomaly and anomaly_score >= 0.5:
        flags.append("fraud_model_anomaly")
    if anomaly_score > 0.7:
        flags.append("high_anomaly_score")
    if anomaly_score > 0.9:
        flags.append("fraud_block")

    signals = {
        "gps_anomaly": round(gps_anomaly, 2),
        "cluster_risk": cluster_risk,
        "activity_mismatch": activity_mismatch,
        "device_risk": device_risk,
        "anomaly_score": anomaly_score,
    }
    event_adjustment = calculate_event_adjustment(signals)
    base_urts = int(rider.base_urts or 70)
    effective_urts = max(0, min(100, int(round(base_urts + event_adjustment))))
    payout_factor = get_payout_factor(effective_urts)
    logger.info(
        "URTS evaluated",
        extra={
            "rider_id": rider.id,
            "claim_id": claim.id if claim else None,
            "base_urts_before": base_urts,
            "event_adjustment": event_adjustment,
            "effective_urts": effective_urts,
            "payout_factor": payout_factor,
            "anomaly_score": anomaly_score,
        },
    )

    return {
        **signals,
        "signals": signals,
        "flags": flags,
        "base_urts": base_urts,
        "event_adjustment": event_adjustment,
        "effective_urts": effective_urts,
        "payout_factor": payout_factor,
        "fraud_result": {
            **fraud_result,
            "anomaly_score": anomaly_score,
            "is_anomaly": is_model_anomaly,
        },
        "fraud_features": fraud_features,
    }
