"""Payment Service — UPI payout simulation."""

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Payout, Claim, User as Rider


def calculate_income_loss(hourly_income: float, disruption_hours: float) -> float:
    """Calculate raw income loss: hourly_income × disruption_hours."""
    return round(hourly_income * disruption_hours, 2)


def simulate_upi_payout(
    db: Session,
    claim: Claim,
    rider: Rider,
    urts_factor: float,
    disruption_hours: float = 3.0,
) -> Payout:
    """
    Simulate a UPI payout for an approved claim.

    Payout = hourly_income × disruption_hours × URTS_factor
    """
    hourly = float(rider.hourly_income or 200.0)
    raw_loss = calculate_income_loss(hourly, disruption_hours)
    payout_amount = round(raw_loss * urts_factor, 2)

    # Per-event cap: 8 hours × hourly income
    max_payout = hourly * 8.0
    payout_amount = min(payout_amount, max_payout)

    # Generate simulated UPI transaction ID
    txn_id = f"UPI-RG-{uuid.uuid4().hex[:12].upper()}"

    payout = Payout(
        claim_id=claim.id,
        rider_id=rider.id,
        amount=payout_amount,
        urts_factor=urts_factor,
        upi_transaction_id=txn_id,
        status="completed",
        paid_at=datetime.now(timezone.utc),
    )

    db.add(payout)

    # Update claim status
    claim.status = "paid"
    claim.disruption_hours = disruption_hours

    db.commit()
    db.refresh(payout)

    return payout
