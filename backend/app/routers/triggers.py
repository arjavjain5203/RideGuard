import httpx
import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.models import User, Policy, Claim, TriggerRecord, Earnings, AuditLog
from app.schemas import TriggerSimulateRequest, TriggerCheckResponse, TriggerEvent
from app.services.behavior_engine import evaluate_event

router = APIRouter(prefix="/api/triggers", tags=["Triggers"])

API_BASE = "http://127.0.0.1:8000/mock"

async def fetch_with_retry(client, url, retries=3):
    for attempt in range(retries):
        try:
            res = await client.get(url, timeout=5.0)
            res.raise_for_status()
            return res.json()
        except Exception:
            if attempt == retries - 1:
                return {}
            await asyncio.sleep(1)

async def fetch_external_triggers(zone: str):
    async with httpx.AsyncClient() as client:
        w_res, a_res, t_res = await asyncio.gather(
            fetch_with_retry(client, f"{API_BASE}/weather?zone={zone}"),
            fetch_with_retry(client, f"{API_BASE}/aqi?zone={zone}"),
            fetch_with_retry(client, f"{API_BASE}/traffic?zone={zone}")
        )
        return w_res, a_res, t_res

@router.post("/check", response_model=TriggerCheckResponse)
async def check_zone_triggers(payload: TriggerSimulateRequest, db: Session = Depends(get_db)):
    """
    Trigger State Machine implementation (ACTIVE -> ONGOING -> ENDED).
    Cap duration at 8 hours. Only create claim AFTER trigger ends.
    Policy Validation: check if policy active and covers trigger type.
    """
    weather, aqi_res, traffic = await fetch_external_triggers(payload.zone)
    
    # Process explicit UI payload as simulation overrides. Fallback to mock API response keys.
    is_simulation = payload.rainfall_mm_hr > 0 or payload.temperature_c > 0 or payload.aqi > 0 or payload.traffic_speed_kmh > 0
    
    rainfall = payload.rainfall_mm_hr if payload.rainfall_mm_hr > 0 else weather.get("rainfall", 0)
    temperature = payload.temperature_c if payload.temperature_c > 0 else weather.get("temperature", 30)
    aqi = payload.aqi if payload.aqi > 0 else aqi_res.get("aqi", 50)
    speed = payload.traffic_speed_kmh if payload.traffic_speed_kmh > 0 else traffic.get("avg_speed", 25)

    current_conditions = {}
    if rainfall >= 15.0:
        current_conditions["rain"] = rainfall
    if aqi >= 300.0:
        current_conditions["aqi"] = aqi
    if temperature >= 42.0:
        current_conditions["heat"] = temperature
    if rainfall >= 60.0 or speed < 5.0:
        current_conditions["flood"] = rainfall if rainfall >= 60.0 else (60.0 if speed < 5.0 else speed)

    current_time = datetime.utcnow()
    claims_created = 0

    try:
        existing_triggers = db.query(TriggerRecord).filter(
            TriggerRecord.zone == payload.zone,
            TriggerRecord.status.in_(["ACTIVE", "ONGOING"])
        ).all()
        
        active_types = {t.type: t for t in existing_triggers}
        
        # 1. Start or Update triggers
        for t_type, value in list(current_conditions.items()):
            if is_simulation:
                # If simulating from UI, immediately resolve state machine to produce payouts
                from datetime import timedelta
                t = TriggerRecord(
                    type=t_type, value=float(value), zone=payload.zone,
                    status="ONGOING", start_time=current_time - timedelta(hours=3)
                )
                db.add(t)
                db.flush()
                # Audit Log
                db.add(AuditLog(entity_type="trigger", entity_id=t.id, action="CREATED", details=json.dumps({"type": t_type, "zone": payload.zone, "simulated": True})))
                existing_triggers.append(t)
                del current_conditions[t_type]  # Remove from ongoing dictionary so loop 2 marks it ENDED
                continue

            if t_type in active_types:
                t = active_types[t_type]
                t.status = "ONGOING"
                t.value = max(t.value, float(value))
            else:
                t = TriggerRecord(
                    type=t_type, value=float(value), zone=payload.zone,
                    status="ACTIVE", start_time=current_time
                )
                db.add(t)
                db.flush()
                # Audit Log
                db.add(AuditLog(entity_type="trigger", entity_id=t.id, action="CREATED", details=json.dumps({"type": t_type, "zone": payload.zone})))

        # 2. End triggers no longer active and create claims
        for t in existing_triggers:
            if t.type not in current_conditions:
                t.status = "ENDED"
                t.end_time = current_time
                delta = t.end_time - t.start_time
                dur = delta.total_seconds() / 3600.0
                # Part 14: cap at 8 hours
                if dur <= 0: dur = 0.5 # Minimum half hour if it flips fast for testing
                t.duration_hours = min(dur, 8.0)
                
                db.add(AuditLog(entity_type="trigger", entity_id=t.id, action="ENDED", details=json.dumps({"duration_hours": t.duration_hours})))

                # Policy validation & Claim creation (Part 15)
                active_users = db.query(User).filter(User.zone == payload.zone).all()
                for user in active_users:
                    policy = db.query(Policy).filter(Policy.user_id == user.id, Policy.status == "active").first()
                    if not policy: continue
                    if t.type not in policy.coverage_list:
                        continue
                    
                    # They are covered
                    earnings_rec = db.query(Earnings).filter(Earnings.user_id == user.id).first()
                    hourly_rate = float(earnings_rec.weekly_earnings / max(1, earnings_rec.hours_worked)) if earnings_rec else 150.0
                    
                    # Apply Behavioral Risk Event Adjustment (Part 2)
                    beh_eval = evaluate_event(user.id, payload.zone)
                    event_adj = beh_eval["event_adjustment"]
                    effective_urts = int(max(0, min(100, user.base_urts + event_adj)))
                    
                    loss = hourly_rate * t.duration_hours
                    
                    c = Claim(
                        user_id=user.id,
                        trigger_id=t.id,
                        loss_amount=loss,
                        disruption_hours=t.duration_hours,
                        effective_urts=effective_urts,
                        behavioral_signals=json.dumps(beh_eval["signals"]),
                        status="pending"
                    )
                    db.add(c)
                    db.flush()
                    
                    # Audit Log for Claim
                    db.add(AuditLog(entity_type="claim", entity_id=c.id, action="CREATED", details=json.dumps({
                        "effective_urts": effective_urts, "loss": loss, "disruption_hours": t.duration_hours
                    })))
                    
                    claims_created += 1

        db.commit()

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Transaction failed: {str(e)}")

    # Construct response
    all_ongoing = db.query(TriggerRecord).filter(
        TriggerRecord.zone == payload.zone,
        TriggerRecord.status.in_(["ACTIVE", "ONGOING", "ENDED"])
    ).order_by(TriggerRecord.start_time.desc()).limit(10).all()
    
    evt_list = []
    for t in all_ongoing:
        # Just map existing objects to response informally
        evt_list.append(TriggerEvent(
            trigger_type=t.type, trigger_value=t.value, threshold=0.0,
            zone=t.zone, severity=t.status
        ))

    return TriggerCheckResponse(
        zone=payload.zone,
        triggers_fired=evt_list,
        claims_created=claims_created,
        message=f"Triggers processed. {claims_created} claim(s) created."
    )
