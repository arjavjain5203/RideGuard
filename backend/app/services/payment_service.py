"""Payment service for automatic and manual payout processing."""

import json
import logging
import math
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import AuditLog, Claim, Payout, Policy, TrustLog, UrtsHistory, User
from app.services.behavior_engine import evaluate_event

logger = logging.getLogger(__name__)
MATERIAL_ANOMALY_THRESHOLD = 0.2
FRAUD_REDUCTION_THRESHOLD = 0.7
FRAUD_BLOCK_THRESHOLD = 0.9
FRAUD_PAYOUT_REDUCTION_FACTOR = 0.8


def calculate_income_loss(hourly_income: float, disruption_hours: float) -> float:
    return round(hourly_income * disruption_hours, 2)


def _calculate_cap_adjusted_amount(
    db: Session,
    user_id: str,
    requested_amount: float,
    weekly_premium: float,
) -> float:
    now_ts = datetime.now(UTC)
    week_start = (now_ts - timedelta(days=now_ts.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now_ts.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    weekly_total = (
        db.query(func.sum(Payout.amount))
        .filter(Payout.user_id == user_id, Payout.created_at >= week_start, Payout.status.in_(["completed", "capped"]))
        .scalar()
        or 0.0
    )
    monthly_total = (
        db.query(func.sum(Payout.amount))
        .filter(Payout.user_id == user_id, Payout.created_at >= month_start, Payout.status.in_(["completed", "capped"]))
        .scalar()
        or 0.0
    )

    max_weekly_payout = 2.0 * weekly_premium
    max_monthly_payout = 6.0 * weekly_premium

    available_weekly = max(0.0, max_weekly_payout - weekly_total)
    available_monthly = max(0.0, max_monthly_payout - monthly_total)

    return round(min(requested_amount, available_weekly, available_monthly), 2)


def _has_material_anomaly(evaluation: dict) -> bool:
    signals = evaluation.get("signals", {})
    return any(float(signals.get(signal_name, 0.0)) >= MATERIAL_ANOMALY_THRESHOLD for signal_name in signals)


def _event_zone_for_claim(claim: Claim, user: User) -> str:
    if claim.trigger and claim.trigger.zone:
        return claim.trigger.zone
    return user.zone


def _record_urts_history(db: Session, claim: Claim, evaluation: dict) -> UrtsHistory:
    existing = claim.urts_history or db.query(UrtsHistory).filter(UrtsHistory.claim_id == claim.id).first()
    if existing:
        return existing

    history = UrtsHistory(
        user_id=claim.user_id,
        claim_id=claim.id,
        base_urts=int(evaluation["base_urts"]),
        event_adjustment=float(evaluation["event_adjustment"]),
        effective_urts=int(evaluation["effective_urts"]),
    )
    db.add(history)
    return history


def _update_base_urts_after_event(db: Session, user: User, claim: Claim, evaluation: dict, payout_status: str | None) -> None:
    old_base = int(user.base_urts or 70)
    has_anomaly = _has_material_anomaly(evaluation)

    if has_anomaly:
        penalty = max(1, math.ceil(abs(float(evaluation["event_adjustment"])) / 10.0))
        new_base = max(0, old_base - penalty)
        reason = f"URTS penalty for anomalous claim {claim.id}"
        change = new_base - old_base
    elif payout_status == "completed" and old_base < 100:
        new_base = min(100, old_base + 1)
        reason = f"URTS reward for clean paid claim {claim.id}"
        change = new_base - old_base
    else:
        return

    if change == 0:
        return

    user.base_urts = new_base
    db.add(
        TrustLog(
            user_id=user.id,
            change=change,
            reason=reason,
        )
    )
    logger.info(
        "base URTS updated",
        extra={
            "claim_id": claim.id,
            "user_id": user.id,
            "base_urts_before": old_base,
            "base_urts_after": new_base,
            "event_adjustment": evaluation["event_adjustment"],
            "payout_decision": payout_status or "rejected",
        },
    )


def process_claim_payout(db: Session, claim: Claim, auto_source: str = "manual") -> Payout | None:
    """
    Process a claim into a payout record when eligible.

    Returns a payout row for completed/capped cases.
    Returns None if the claim is rejected because the effective URTS blocks payment.
    """
    existing_payout = claim.payout or db.query(Payout).filter(Payout.claim_id == claim.id).first()
    if existing_payout:
        return existing_payout

    if claim.status in {"paid", "capped"}:
        return None
    if claim.status == "rejected":
        return None

    user = db.query(User).filter(User.id == claim.user_id).first()
    if not user:
        raise ValueError("User not found for claim")

    evaluation = evaluate_event(db, user.id, _event_zone_for_claim(claim, user), claim)
    effective_urts = int(evaluation["effective_urts"])
    urts_factor = float(evaluation["payout_factor"])
    fraud_result = evaluation.get("fraud_result", {})
    anomaly_score = float(fraud_result.get("anomaly_score", evaluation["signals"].get("anomaly_score", 0.0)))
    is_model_anomaly = bool(fraud_result.get("is_anomaly", False))
    fraud_flag = anomaly_score > FRAUD_BLOCK_THRESHOLD
    claim.effective_urts = effective_urts
    claim.effective_urts_at_event = effective_urts
    claim.event_adjustment = float(evaluation["event_adjustment"])
    claim.anomaly_score = anomaly_score
    claim.fraud_flag = fraud_flag
    claim.behavioral_signals = json.dumps(
        {
            **evaluation["signals"],
            "event_adjustment": evaluation["event_adjustment"],
            "effective_urts": effective_urts,
            "payout_factor": urts_factor,
            "fraud_payout_factor": FRAUD_PAYOUT_REDUCTION_FACTOR if anomaly_score > FRAUD_REDUCTION_THRESHOLD else 1.0,
            "fraud_result": fraud_result,
            "fraud_features": evaluation.get("fraud_features", {}),
            "flags": evaluation["flags"],
        }
    )
    _record_urts_history(db, claim, evaluation)

    if fraud_flag:
        claim.status = "rejected"
        db.add(
            AuditLog(
                entity_type="claim",
                entity_id=claim.id,
                action="REJECTED",
                details=json.dumps(
                    {
                        "reason": "fraud_model_block",
                        "effective_urts": effective_urts,
                        "event_adjustment": evaluation["event_adjustment"],
                        "anomaly_score": anomaly_score,
                        "is_anomaly": is_model_anomaly,
                        "risk_signals": evaluation["signals"],
                        "fraud_features": evaluation.get("fraud_features", {}),
                        "source": auto_source,
                    }
                ),
            )
        )
        _update_base_urts_after_event(db, user, claim, evaluation, payout_status=None)
        logger.info(
            "payout rejected by fraud model",
            extra={
                "claim_id": claim.id,
                "payout_decision": "rejected_fraud",
                "base_urts_before": evaluation["base_urts"],
                "effective_urts": effective_urts,
                "event_adjustment": evaluation["event_adjustment"],
                "anomaly_score": anomaly_score,
                "is_anomaly": is_model_anomaly,
                "disruption_probability": claim.trigger.disruption_probability if claim.trigger else None,
            },
        )
        return None

    if urts_factor == 0.0:
        claim.status = "rejected"
        db.add(
            AuditLog(
                entity_type="claim",
                entity_id=claim.id,
                action="REJECTED",
                details=json.dumps(
                    {
                        "reason": "effective_urts_below_threshold",
                        "effective_urts": effective_urts,
                        "event_adjustment": evaluation["event_adjustment"],
                        "risk_signals": evaluation["signals"],
                        "payout_factor": urts_factor,
                        "source": auto_source,
                    }
                ),
            )
        )
        _update_base_urts_after_event(db, user, claim, evaluation, payout_status=None)
        logger.info(
            "payout rejected by URTS",
            extra={
                "claim_id": claim.id,
                "payout_decision": "rejected_urts",
                "base_urts_before": evaluation["base_urts"],
                "effective_urts": effective_urts,
                "event_adjustment": evaluation["event_adjustment"],
                "payout_factor": urts_factor,
                "disruption_probability": claim.trigger.disruption_probability if claim.trigger else None,
            },
        )
        return None

    policy = db.query(Policy).filter(Policy.id == claim.policy_id).first()
    weekly_premium = policy.weekly_premium if policy else 0.0

    fraud_payout_factor = FRAUD_PAYOUT_REDUCTION_FACTOR if anomaly_score > FRAUD_REDUCTION_THRESHOLD else 1.0
    applied_payout_factor = round(urts_factor * fraud_payout_factor, 4)
    requested_amount = round(claim.loss_amount * applied_payout_factor, 2)
    payout_amount = _calculate_cap_adjusted_amount(db, user.id, requested_amount, weekly_premium)

    if effective_urts < 60:
        payout_status = "pending"
        claim_status_val = "under_review"
    else:
        payout_status = "completed" if payout_amount == requested_amount and payout_amount > 0 else "capped"
        claim_status_val = "paid" if payout_status == "completed" else "capped"

    payout = Payout(
        claim_id=claim.id,
        user_id=user.id,
        amount=payout_amount,
        urts_factor=applied_payout_factor,
        transaction_id=f"UPI-RG-{str(uuid.uuid4())[:12].upper()}",
        status=payout_status,
        paid_at=datetime.now(UTC) if payout_status == "completed" else None,
    )
    db.add(payout)
    db.flush()

    claim.status = claim_status_val

    action_str = "PROCESSED" if payout_status == "completed" else ("CAPPED" if payout_status == "capped" else "PENDING")
    db.add(
        AuditLog(
            entity_type="payout",
            entity_id=payout.id,
            action=action_str,
            details=json.dumps(
                {
                    "claim_id": claim.id,
                    "effective_urts": effective_urts,
                    "event_adjustment": evaluation["event_adjustment"],
                    "anomaly_score": anomaly_score,
                    "is_anomaly": is_model_anomaly,
                    "risk_signals": evaluation["signals"],
                    "urts_payout_factor": urts_factor,
                    "fraud_payout_factor": fraud_payout_factor,
                    "payout_factor": applied_payout_factor,
                    "requested_amount": requested_amount,
                    "paid_amount": payout_amount,
                    "source": auto_source,
                }
            ),
        )
    )
    logger.info(
        "payout processed",
        extra={
            "claim_id": claim.id,
            "payout_id": payout.id,
            "payout_decision": payout_status,
            "requested_amount": requested_amount,
            "paid_amount": payout_amount,
            "status": payout_status,
            "base_urts_before": evaluation["base_urts"],
            "effective_urts": effective_urts,
            "event_adjustment": evaluation["event_adjustment"],
            "anomaly_score": anomaly_score,
            "payout_factor": applied_payout_factor,
            "disruption_probability": claim.trigger.disruption_probability if claim.trigger else None,
        },
    )
    _update_base_urts_after_event(db, user, claim, evaluation, payout_status=payout_status)

    return payout
