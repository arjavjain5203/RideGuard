import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import AuditLog, Claim, CoverageModule, Earnings, Policy, TriggerRecord, User
from app.routers.mock_external import get_aqi, get_traffic, get_weather
from app.schemas import TriggerCheckResponse, TriggerEvent, TriggerSimulateRequest
from app.services.fraud_detection import calculate_effective_urts, run_fraud_checks
from app.services.payment_service import calculate_income_loss, process_claim_payout

router = APIRouter(prefix="/api/triggers", tags=["Triggers"])


def get_zone_conditions(payload: TriggerSimulateRequest) -> tuple[dict, dict, dict, bool]:
    weather = get_weather(payload.zone)
    aqi_snapshot = get_aqi(payload.zone)
    traffic = get_traffic(payload.zone)

    is_simulation = any(
        value > 0
        for value in (
            payload.rainfall_mm_hr,
            payload.temperature_c,
            payload.aqi,
            payload.traffic_speed_kmh,
        )
    )

    if payload.rainfall_mm_hr > 0:
        weather["rainfall"] = payload.rainfall_mm_hr
    if payload.temperature_c > 0:
        weather["temperature"] = payload.temperature_c
    if payload.aqi > 0:
        aqi_snapshot["aqi"] = payload.aqi
    if payload.traffic_speed_kmh > 0:
        traffic["avg_speed"] = payload.traffic_speed_kmh

    return weather, aqi_snapshot, traffic, is_simulation


def get_current_conditions(weather: dict, aqi_snapshot: dict, traffic: dict) -> dict[str, float]:
    rainfall = weather.get("rainfall", 0.0)
    temperature = weather.get("temperature", 30.0)
    aqi = aqi_snapshot.get("aqi", 50.0)
    speed = traffic.get("avg_speed", 25.0)

    current_conditions: dict[str, float] = {}
    if rainfall >= 15.0:
        current_conditions["rain"] = rainfall
    if aqi >= 300.0:
        current_conditions["aqi"] = aqi
    if temperature >= 42.0:
        current_conditions["heat"] = temperature
    if rainfall >= 60.0 or speed < 5.0:
        current_conditions["flood"] = rainfall if rainfall >= 60.0 else speed
    return current_conditions


def get_coverage_rules(db: Session) -> tuple[dict[str, float], dict[str, float]]:
    duration_requirements = {"rain": 2.0, "flood": 6.0, "heat": 0.0, "aqi": 3.0}
    trigger_thresholds = {"rain": 15.0, "flood": 60.0, "heat": 42.0, "aqi": 300.0}
    for module in db.query(CoverageModule).all():
        duration_requirements[module.name] = float(module.trigger_duration_hours or 0.0)
        trigger_thresholds[module.name] = float(module.trigger_threshold or trigger_thresholds.get(module.name, 0.0))
    return duration_requirements, trigger_thresholds


def create_claim_for_trigger(
    db: Session,
    user: User,
    policy: Policy,
    trigger_record: TriggerRecord,
    current_time: datetime,
) -> tuple[Claim, bool]:
    earnings_rec = db.query(Earnings).filter(Earnings.user_id == user.id).first()
    hourly_rate = (
        float(earnings_rec.weekly_earnings / max(1, earnings_rec.hours_worked))
        if earnings_rec
        else float(user.hourly_income or 150.0)
    )
    user.hourly_income = round(hourly_rate, 2)

    signal_vector = run_fraud_checks(
        db=db,
        rider=user,
        trigger_type=trigger_record.type,
        trigger_value=trigger_record.value,
        zone=trigger_record.zone,
    )
    effective_urts = calculate_effective_urts(user.base_urts or 70, signal_vector)
    loss = calculate_income_loss(hourly_rate, trigger_record.duration_hours)

    claim = Claim(
        policy_id=policy.id,
        user_id=user.id,
        trigger_id=trigger_record.id,
        trigger_type=trigger_record.type,
        trigger_value=trigger_record.value,
        disruption_start=trigger_record.start_time,
        disruption_end=current_time,
        loss_amount=loss,
        disruption_hours=trigger_record.duration_hours,
        effective_urts=effective_urts,
        behavioral_signals=json.dumps(signal_vector.to_dict()),
        status="pending",
    )
    db.add(claim)
    db.flush()

    db.add(
        AuditLog(
            entity_type="claim",
            entity_id=claim.id,
            action="CREATED",
            details=json.dumps(
                {
                    "policy_id": policy.id,
                    "effective_urts": effective_urts,
                    "loss": loss,
                    "disruption_hours": trigger_record.duration_hours,
                }
            ),
        )
    )

    payout = process_claim_payout(db, claim, auto_source="trigger_monitor")
    payouts_created = payout is not None and payout.amount > 0
    return claim, payouts_created


@router.post("/check", response_model=TriggerCheckResponse)
async def check_zone_triggers(
    payload: TriggerSimulateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    normalized_payload_zone = payload.zone.lower().replace(" ", "_")
    normalized_user_zone = (current_user.zone or "").lower().replace(" ", "_")
    if current_user.role == "rider" and normalized_payload_zone != normalized_user_zone:
        raise HTTPException(status_code=403, detail="Riders may only evaluate triggers for their own zone")

    weather, aqi_snapshot, traffic, is_simulation = get_zone_conditions(payload)
    current_conditions = get_current_conditions(weather, aqi_snapshot, traffic)
    duration_requirements, trigger_thresholds = get_coverage_rules(db)

    current_time = datetime.utcnow()
    claims_created = 0
    payouts_created = 0

    try:
        existing_triggers = db.query(TriggerRecord).filter(
            TriggerRecord.zone == payload.zone,
            TriggerRecord.status.in_(["ACTIVE", "ONGOING"]),
        ).all()
        active_types = {trigger.type: trigger for trigger in existing_triggers}

        for trigger_type, value in current_conditions.items():
            if trigger_type in active_types:
                trigger_record = active_types[trigger_type]
                trigger_record.status = "ONGOING"
                trigger_record.value = max(float(trigger_record.value), float(value))
                continue

            start_time = current_time
            if is_simulation:
                simulated_duration = max(duration_requirements.get(trigger_type, 0.0), 0.5)
                start_time = current_time - timedelta(hours=simulated_duration)

            trigger_record = TriggerRecord(
                type=trigger_type,
                value=float(value),
                zone=payload.zone,
                status="ONGOING" if is_simulation else "ACTIVE",
                start_time=start_time,
            )
            db.add(trigger_record)
            db.flush()
            existing_triggers.append(trigger_record)
            active_types[trigger_type] = trigger_record
            db.add(
                AuditLog(
                    entity_type="trigger",
                    entity_id=trigger_record.id,
                    action="CREATED",
                    details=json.dumps(
                        {
                            "type": trigger_type,
                            "zone": payload.zone,
                            "simulated": is_simulation,
                        }
                    ),
                )
            )

        for trigger_record in existing_triggers:
            if trigger_record.type in current_conditions and not is_simulation:
                continue

            trigger_record.status = "ENDED"
            trigger_record.end_time = current_time
            duration = (trigger_record.end_time - trigger_record.start_time).total_seconds() / 3600.0
            trigger_record.duration_hours = round(min(max(duration, 0.0), 8.0), 2)

            db.add(
                AuditLog(
                    entity_type="trigger",
                    entity_id=trigger_record.id,
                    action="ENDED",
                    details=json.dumps({"duration_hours": trigger_record.duration_hours}),
                )
            )

            if trigger_record.duration_hours < duration_requirements.get(trigger_record.type, 0.0):
                db.add(
                    AuditLog(
                        entity_type="trigger",
                        entity_id=trigger_record.id,
                        action="IGNORED",
                        details=json.dumps(
                            {
                                "reason": "duration_below_threshold",
                                "required_hours": duration_requirements.get(trigger_record.type, 0.0),
                                "actual_hours": trigger_record.duration_hours,
                            }
                        ),
                    )
                )
                continue

            if current_user.role == "admin":
                covered_users = (
                    db.query(User)
                    .filter(
                        User.zone == payload.zone,
                        User.role == "rider",
                        User.is_active.is_(True),
                    )
                    .all()
                )
            else:
                covered_users = [current_user]
            for user in covered_users:
                policy = db.query(Policy).filter(Policy.user_id == user.id, Policy.status == "active").first()
                if not policy or trigger_record.type not in policy.coverage_list:
                    continue

                duplicate_claim = db.query(Claim).filter(
                    Claim.user_id == user.id,
                    Claim.trigger_id == trigger_record.id,
                ).first()
                if duplicate_claim:
                    continue

                _, payout_created = create_claim_for_trigger(db, user, policy, trigger_record, current_time)
                claims_created += 1
                payouts_created += 1 if payout_created else 0

        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Transaction failed: {str(exc)}") from exc

    recent_triggers = db.query(TriggerRecord).filter(TriggerRecord.zone == payload.zone).order_by(
        TriggerRecord.start_time.desc()
    ).limit(10).all()

    return TriggerCheckResponse(
        zone=payload.zone,
        triggers_fired=[
            TriggerEvent(
                trigger_type=trigger_record.type,
                trigger_value=trigger_record.value,
                threshold=trigger_thresholds.get(trigger_record.type, 0.0),
                zone=trigger_record.zone,
                severity=trigger_record.status,
            )
            for trigger_record in recent_triggers
        ],
        claims_created=claims_created,
        payouts_created=payouts_created,
        message=f"Triggers processed. {claims_created} claim(s) created and {payouts_created} payout(s) completed.",
    )
