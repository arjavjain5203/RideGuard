import json
import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import settings
from app.core.celery_app import enqueue_task
from app.core.redis_client import get_cached_json, set_cached_json
from app.database import get_db
from app.models import AuditLog, Claim, CoverageModule, Earnings, Policy, TriggerRecord, User
from app.routers.mock_external import get_aqi, get_traffic, get_weather
from app.schemas import TaskEnqueueResponse, TriggerCheckResponse, TriggerEvent, TriggerSimulateRequest
from app.services.disruption_model_service import (
    MODEL_PROBABILITY_THRESHOLD,
    get_critical_breaches,
    get_dominant_ml_trigger_type,
    get_environment_inputs,
    predict_disruption,
)
from app.services.payment_service import calculate_income_loss, process_claim_payout
from app.tasks.jobs import process_claim as process_claim_task, process_trigger_event as process_trigger_event_task

router = APIRouter(prefix="/api/triggers", tags=["Triggers"])
logger = logging.getLogger(__name__)

MAX_DISRUPTION_HOURS = 8.0
FALLBACK_THRESHOLDS = {
    "rain": 15.0,
    "aqi": 300.0,
    "heat": 42.0,
    "flood_rain": 60.0,
    "flood_speed": 5.0,
}


def active_trigger_cache_key(zone: str) -> str:
    return f"trigger:{zone.strip().lower().replace(' ', '_')}"


def add_audit_log(db: Session, entity_type: str, entity_id: str, action: str, details: dict) -> None:
    db.add(
        AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            details=json.dumps(details),
        )
    )


def calculate_disruption_hours(start_time: datetime, end_time: datetime) -> float:
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=UTC)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=UTC)
    duration = (end_time - start_time).total_seconds() / 3600.0
    return round(min(max(duration, 0.0), MAX_DISRUPTION_HOURS), 2)


def end_trigger(db: Session, trigger_record: TriggerRecord, end_time: datetime) -> None:
    trigger_record.status = "ENDED"
    trigger_record.end_time = end_time
    trigger_record.duration_hours = calculate_disruption_hours(trigger_record.start_time, end_time)
    add_audit_log(
        db,
        entity_type="trigger",
        entity_id=trigger_record.id,
        action="ENDED",
        details={"duration_hours": trigger_record.duration_hours},
    )
    logger.info(
        "trigger ended",
        extra={
            "trigger_id": trigger_record.id,
            "type": trigger_record.type,
            "zone": trigger_record.zone,
            "duration_hours": trigger_record.duration_hours,
        },
    )


def log_claim_skip(db: Session, user: User, trigger_record: TriggerRecord, reason: str, **details) -> None:
    add_audit_log(
        db,
        entity_type="user",
        entity_id=user.id,
        action="CLAIM_SKIPPED",
        details={
            "reason": reason,
            "trigger_id": trigger_record.id,
            "trigger_type": trigger_record.type,
            **details,
        },
    )


def cache_active_triggers(zone: str, triggers: list[TriggerRecord]) -> None:
    set_cached_json(
        active_trigger_cache_key(zone),
        [trigger.id for trigger in triggers if trigger.status in {"ACTIVE", "ONGOING"}],
        settings.ACTIVE_TRIGGER_CACHE_TTL_SECONDS,
    )


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


def get_environment_values(weather: dict, aqi_snapshot: dict, traffic: dict) -> tuple[float, float, float, float]:
    return (
        float(weather.get("rainfall", 0.0)),
        float(weather.get("temperature", 30.0)),
        float(aqi_snapshot.get("aqi", 50.0)),
        float(traffic.get("avg_speed", 25.0)),
    )


def get_fallback_conditions(rainfall: float, temperature: float, aqi: float, speed: float) -> dict[str, float]:
    current_conditions: dict[str, float] = {}
    if rainfall >= FALLBACK_THRESHOLDS["rain"]:
        current_conditions["rain"] = rainfall
    if aqi >= FALLBACK_THRESHOLDS["aqi"]:
        current_conditions["aqi"] = aqi
    if temperature >= FALLBACK_THRESHOLDS["heat"]:
        current_conditions["heat"] = temperature
    if rainfall >= FALLBACK_THRESHOLDS["flood_rain"] or speed < FALLBACK_THRESHOLDS["flood_speed"]:
        current_conditions["flood"] = rainfall if rainfall >= FALLBACK_THRESHOLDS["flood_rain"] else speed
    return current_conditions


def get_hybrid_conditions(weather: dict, aqi_snapshot: dict, traffic: dict) -> tuple[dict[str, float], dict[str, dict]]:
    rainfall, temperature, aqi, speed = get_environment_values(weather, aqi_snapshot, traffic)
    environment_inputs = get_environment_inputs(rainfall, temperature, aqi, speed)
    probability = predict_disruption(rainfall, temperature, aqi, speed)
    critical_breaches = get_critical_breaches(rainfall, temperature, aqi, speed)

    logger.info(
        "disruption model evaluated",
        extra={
            **environment_inputs,
            "disruption_probability": probability,
            "model_threshold": MODEL_PROBABILITY_THRESHOLD,
        },
    )

    condition_metadata: dict[str, dict] = {}
    if critical_breaches:
        for trigger_type, value in critical_breaches.items():
            condition_metadata[trigger_type] = {
                "disruption_probability": probability,
                "environment_inputs": environment_inputs,
                "decision_reason": "threshold triggered",
            }
        return critical_breaches, condition_metadata

    if probability is not None and probability > MODEL_PROBABILITY_THRESHOLD:
        trigger_type, value = get_dominant_ml_trigger_type(rainfall, temperature, aqi, speed)
        return {
            trigger_type: value,
        }, {
            trigger_type: {
                "disruption_probability": probability,
                "environment_inputs": environment_inputs,
                "decision_reason": "ML triggered",
            }
        }

    if probability is None:
        fallback_conditions = get_fallback_conditions(rainfall, temperature, aqi, speed)
        for trigger_type in fallback_conditions:
            condition_metadata[trigger_type] = {
                "disruption_probability": None,
                "environment_inputs": environment_inputs,
                "decision_reason": "fallback threshold",
            }
        return fallback_conditions, condition_metadata

    return {}, {}


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
    enqueue_claim_processing: bool = False,
) -> tuple[Claim, bool]:
    if trigger_record.status != "ENDED":
        raise ValueError("Claims can only be created after a trigger has ended")

    earnings_rec = db.query(Earnings).filter(Earnings.user_id == user.id).first()
    hourly_rate = (
        float(earnings_rec.weekly_earnings / max(1, earnings_rec.hours_worked))
        if earnings_rec
        else float(user.hourly_income or 150.0)
    )
    user.hourly_income = round(hourly_rate, 2)

    loss = calculate_income_loss(hourly_rate, trigger_record.duration_hours)

    claim = Claim(
        policy_id=policy.id,
        user_id=user.id,
        trigger_id=trigger_record.id,
        trigger_type=trigger_record.type,
        trigger_value=trigger_record.value,
        disruption_start=trigger_record.start_time,
        disruption_end=trigger_record.end_time or current_time,
        loss_amount=loss,
        disruption_hours=trigger_record.duration_hours,
        status="pending",
    )
    db.add(claim)
    db.flush()

    add_audit_log(
        db,
        entity_type="claim",
        entity_id=claim.id,
        action="CREATED",
        details={
            "trigger_id": trigger_record.id,
            "policy_id": policy.id,
            "loss": loss,
            "disruption_hours": trigger_record.duration_hours,
        },
    )
    logger.info(
        "claim created",
        extra={
            "claim_id": claim.id,
            "trigger_id": trigger_record.id,
            "policy_id": policy.id,
            "user_id": user.id,
        },
    )

    if enqueue_claim_processing:
        return claim, False

    payout = process_claim_payout(db, claim, auto_source="trigger_monitor")
    return claim, payout is not None


def process_zone_trigger_check(
    payload: TriggerSimulateRequest,
    db: Session,
    current_user: User,
    enqueue_claim_processing: bool = False,
):
    normalized_payload_zone = payload.zone.lower().replace(" ", "_")
    normalized_user_zone = (current_user.zone or "").lower().replace(" ", "_")
    if current_user.role == "rider" and normalized_payload_zone != normalized_user_zone:
        raise HTTPException(status_code=403, detail="Riders may only evaluate triggers for their own zone")

    weather, aqi_snapshot, traffic, is_simulation = get_zone_conditions(payload)
    current_conditions, condition_metadata = get_hybrid_conditions(weather, aqi_snapshot, traffic)
    duration_requirements, trigger_thresholds = get_coverage_rules(db)

    current_time = datetime.now(UTC)
    claims_created = 0
    payouts_created = 0
    pending_claims_to_enqueue = []

    try:
        cached_trigger_ids = get_cached_json(active_trigger_cache_key(payload.zone)) or []
        if cached_trigger_ids:
            existing_triggers = (
                db.query(TriggerRecord)
                .filter(TriggerRecord.id.in_(cached_trigger_ids), TriggerRecord.status.in_(["ACTIVE", "ONGOING"]))
                .all()
            )
        else:
            existing_triggers = db.query(TriggerRecord).filter(
                TriggerRecord.zone == payload.zone,
                TriggerRecord.status.in_(["ACTIVE", "ONGOING"]),
            ).all()
        active_types = {trigger.type: trigger for trigger in existing_triggers}

        for trigger_type, value in current_conditions.items():
            metadata = condition_metadata.get(trigger_type, {})
            if trigger_type in active_types:
                trigger_record = active_types[trigger_type]
                if trigger_record.status == "ACTIVE":
                    trigger_record.status = "ONGOING"
                    add_audit_log(
                        db,
                        entity_type="trigger",
                        entity_id=trigger_record.id,
                        action="ONGOING",
                        details={"type": trigger_type, "zone": payload.zone},
                    )
                trigger_record.value = max(float(trigger_record.value), float(value))
                trigger_record.disruption_probability = metadata.get("disruption_probability")
                trigger_record.environment_inputs = json.dumps(metadata.get("environment_inputs", {}))
                trigger_record.decision_reason = metadata.get("decision_reason")
                continue

            start_time = current_time
            if is_simulation:
                simulated_duration = max(duration_requirements.get(trigger_type, 0.0), 0.5)
                start_time = current_time - timedelta(hours=simulated_duration)

            trigger_record = TriggerRecord(
                type=trigger_type,
                value=float(value),
                zone=payload.zone,
                status="ACTIVE",
                start_time=start_time,
                disruption_probability=metadata.get("disruption_probability"),
                environment_inputs=json.dumps(metadata.get("environment_inputs", {})),
                decision_reason=metadata.get("decision_reason"),
            )
            db.add(trigger_record)
            db.flush()
            existing_triggers.append(trigger_record)
            active_types[trigger_type] = trigger_record
            add_audit_log(
                db,
                entity_type="trigger",
                entity_id=trigger_record.id,
                action="STARTED",
                details={
                    "type": trigger_type,
                    "zone": payload.zone,
                    "simulated": is_simulation,
                    "disruption_probability": metadata.get("disruption_probability"),
                    "environment_inputs": metadata.get("environment_inputs", {}),
                    "decision_reason": metadata.get("decision_reason"),
                },
            )
            logger.info(
                "trigger started",
                extra={
                    "trigger_id": trigger_record.id,
                    "type": trigger_type,
                    "zone": payload.zone,
                    "disruption_probability": metadata.get("disruption_probability"),
                    "decision_reason": metadata.get("decision_reason"),
                },
            )

            if is_simulation:
                end_trigger(db, trigger_record, current_time)

        for trigger_record in existing_triggers:
            if trigger_record.status != "ENDED" and trigger_record.type in current_conditions and not is_simulation:
                continue

            if trigger_record.status != "ENDED":
                end_trigger(db, trigger_record, current_time)

            if trigger_record.duration_hours < duration_requirements.get(trigger_record.type, 0.0):
                add_audit_log(
                    db,
                    entity_type="trigger",
                    entity_id=trigger_record.id,
                    action="IGNORED",
                    details={
                        "reason": "duration_below_threshold",
                        "required_hours": duration_requirements.get(trigger_record.type, 0.0),
                        "actual_hours": trigger_record.duration_hours,
                    },
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
                if not policy:
                    log_claim_skip(db, user, trigger_record, "no_active_policy")
                    continue
                if trigger_record.type not in policy.coverage_list:
                    log_claim_skip(
                        db,
                        user,
                        trigger_record,
                        "coverage_not_in_policy",
                        policy_id=policy.id,
                        coverage_types=policy.coverage_list,
                    )
                    continue

                duplicate_claim = db.query(Claim).filter(
                    Claim.user_id == user.id,
                    Claim.trigger_id == trigger_record.id,
                ).first()
                if duplicate_claim:
                    log_claim_skip(db, user, trigger_record, "duplicate_claim", claim_id=duplicate_claim.id)
                    continue

                claim_obj, payout_created = create_claim_for_trigger(
                    db,
                    user,
                    policy,
                    trigger_record,
                    current_time,
                    enqueue_claim_processing=enqueue_claim_processing,
                )
                if enqueue_claim_processing and claim_obj:
                    pending_claims_to_enqueue.append((claim_obj.id, user.id))

                claims_created += 1
                payouts_created += 1 if payout_created else 0

        cache_active_triggers(payload.zone, existing_triggers)
        db.commit()

        for claim_id, actor_id in pending_claims_to_enqueue:
            enqueue_task(process_claim_task, claim_id, initiated_by_user_id=actor_id, auto_source="trigger_monitor")
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
                disruption_probability=trigger_record.disruption_probability,
                decision_reason=trigger_record.decision_reason,
            )
            for trigger_record in recent_triggers
        ],
        claims_created=claims_created,
        payouts_created=payouts_created,
        message=f"Triggers processed. {claims_created} claim(s) created and {payouts_created} payout(s) completed.",
    )


async def check_zone_triggers(
    payload: TriggerSimulateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    enqueue_claim_processing: bool = False,
):
    return process_zone_trigger_check(
        payload,
        db,
        current_user,
        enqueue_claim_processing=enqueue_claim_processing,
    )


@router.post("/check", response_model=TaskEnqueueResponse, status_code=202)
async def queue_zone_trigger_check(
    payload: TriggerSimulateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    normalized_payload_zone = payload.zone.lower().replace(" ", "_")
    normalized_user_zone = (current_user.zone or "").lower().replace(" ", "_")
    if current_user.role == "rider" and normalized_payload_zone != normalized_user_zone:
        raise HTTPException(status_code=403, detail="Riders may only evaluate triggers for their own zone")

    simulation_payload = payload.model_dump(exclude={"zone"})
    try:
        task = enqueue_task(
            process_trigger_event_task,
            payload.zone,
            initiated_by_user_id=current_user.id,
            simulation_payload=simulation_payload,
        )
        return TaskEnqueueResponse(
            task_id=task.id,
            task_name="process_trigger_event",
            status="queued",
            message=f"Trigger processing has been queued for {payload.zone}.",
            queued_at=datetime.now(UTC),
            entity_id=payload.zone,
            executed_inline=bool(getattr(task, "successful", lambda: False)()),
            summary={"claims_created": 0, "payouts_created": 0, "zone": payload.zone},
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
