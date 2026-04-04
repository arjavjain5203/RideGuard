"""Payment service for automatic and manual payout processing."""

import json
import uuid
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import AuditLog, Claim, Payout, Policy, TrustLog, User
from app.services.fraud_detection import get_urts_factor


def calculate_income_loss(hourly_income: float, disruption_hours: float) -> float:
    return round(hourly_income * disruption_hours, 2)


def _calculate_cap_adjusted_amount(
    db: Session,
    user_id: str,
    requested_amount: float,
    weekly_premium: float,
) -> float:
    now_ts = datetime.utcnow()
    one_week_ago = now_ts - timedelta(days=7)
    one_month_ago = now_ts - timedelta(days=30)

    weekly_total = (
        db.query(func.sum(Payout.amount))
        .filter(Payout.user_id == user_id, Payout.created_at >= one_week_ago)
        .scalar()
        or 0.0
    )
    monthly_total = (
        db.query(func.sum(Payout.amount))
        .filter(Payout.user_id == user_id, Payout.created_at >= one_month_ago)
        .scalar()
        or 0.0
    )

    max_weekly_payout = 2.0 * weekly_premium
    max_monthly_payout = 6.0 * (weekly_premium * 4.0)

    available_weekly = max(0.0, max_weekly_payout - weekly_total)
    available_monthly = max(0.0, max_monthly_payout - monthly_total)

    return round(min(requested_amount, available_weekly, available_monthly), 2)


def process_claim_payout(db: Session, claim: Claim, auto_source: str = "manual") -> Payout | None:
    """
    Process a claim into a payout record when eligible.

    Returns a payout row for completed/capped cases.
    Returns None if the claim is rejected because the effective URTS blocks payment.
    """
    if claim.status in {"paid", "capped", "rejected"}:
        return claim.payout

    user = db.query(User).filter(User.id == claim.user_id).first()
    if not user:
        raise ValueError("User not found for claim")

    effective_urts = claim.effective_urts if claim.effective_urts is not None else user.base_urts
    urts_factor = get_urts_factor(effective_urts)

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
                        "source": auto_source,
                    }
                ),
            )
        )
        return None

    policy = db.query(Policy).filter(Policy.id == claim.policy_id).first()
    weekly_premium = policy.weekly_premium if policy else 0.0

    requested_amount = round(claim.loss_amount * urts_factor, 2)
    payout_amount = _calculate_cap_adjusted_amount(db, user.id, requested_amount, weekly_premium)

    payout = Payout(
        claim_id=claim.id,
        user_id=user.id,
        amount=payout_amount,
        urts_factor=urts_factor,
        transaction_id=f"UPI-RG-{str(uuid.uuid4())[:12].upper()}",
        status="completed" if payout_amount > 0 else "capped",
        paid_at=datetime.utcnow() if payout_amount > 0 else None,
    )
    db.add(payout)
    db.flush()

    claim.status = "paid" if payout_amount > 0 else "capped"

    db.add(
        AuditLog(
            entity_type="payout",
            entity_id=payout.id,
            action="PROCESSED" if payout_amount > 0 else "CAPPED",
            details=json.dumps(
                {
                    "claim_id": claim.id,
                    "effective_urts": effective_urts,
                    "requested_amount": requested_amount,
                    "paid_amount": payout_amount,
                    "source": auto_source,
                }
            ),
        )
    )

    if payout_amount > 0:
        user.base_urts = min(100, (user.base_urts or 70) + 2)
        db.add(
            TrustLog(
                user_id=user.id,
                change=2,
                reason=f"Valid claim {claim.id} paid",
            )
        )

    return payout
