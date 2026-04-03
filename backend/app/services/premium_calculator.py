"""Premium Calculator — modular premium computation."""

from sqlalchemy.orm import Session

from app.models import CoverageModule, Earnings
from app.services.risk_engine import get_zone_multiplier, get_premium_multiplier


def calculate_premium(
    db: Session,
    rider_id: str,
    zone: str,
    selected_modules: list[str],
    risk_score: float = 0.5,
) -> dict:
    """
    Calculate weekly premium for a rider.

    Returns:
        dict with zone_multiplier, risk_score, module_breakdown, total_weekly_premium
    """
    zone_mult = get_zone_multiplier(zone)
    premium_mult = get_premium_multiplier(risk_score)

    modules = (
        db.query(CoverageModule)
        .filter(CoverageModule.name.in_(selected_modules))
        .all()
    )

    if not modules:
        raise ValueError(f"No valid coverage modules found for: {selected_modules}")

    earnings = db.query(Earnings).filter(Earnings.user_id == rider_id).first()
    active_days = earnings.active_days if earnings else 5

    activity_mult = 1.0
    if active_days <= 2:
        activity_mult = 0.0
    elif active_days <= 4:
        activity_mult = 0.5

    breakdown = {}
    total = 0.0

    for mod in modules:
        price = float(mod.base_price) * zone_mult * premium_mult * activity_mult
        price = round(price, 2)
        breakdown[mod.name] = price
        total += price

    return {
        "zone_multiplier": zone_mult,
        "risk_score": risk_score,
        "module_breakdown": breakdown,
        "total_weekly_premium": round(total, 2),
    }
