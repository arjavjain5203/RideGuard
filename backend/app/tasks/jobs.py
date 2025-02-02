"""Celery tasks for background trigger, claim, payout, fraud, and LLM work."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from celery.utils.log import get_task_logger

from app.core.celery_app import celery_app, enqueue_task
from app.core.redis_client import cache_task_result, redis_lock
from app.database import SessionLocal
from app.models import Claim, User
from app.schemas import TriggerSimulateRequest
from app.services.behavior_engine import build_fraud_features
from app.services.fraud_model_service import evaluate_fraud as evaluate_fraud_sync
from app.services.llm_service import generate_admin_insights
from app.services.payment_service import process_claim_payout

logger = get_task_logger(__name__)
app_logger = logging.getLogger(__name__)


def _task_summary(status: str, **extra):
    return {
        "status": status,
        "timestamp": datetime.now(UTC).isoformat(),
        **extra,
    }


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3}, name="app.tasks.process_trigger_event")
def process_trigger_event(self, zone: str, initiated_by_user_id: str | None = None, simulation_payload: dict | None = None):
    from app.routers.triggers import process_zone_trigger_check

    with redis_lock(f"lock:trigger:{zone}") as acquired:
        if not acquired:
            summary = _task_summary("duplicate", zone=zone, reason="trigger task already running")
            cache_task_result(self.request.id, summary)
            return summary

        db = SessionLocal()
        try:
            if initiated_by_user_id:
                actor = db.query(User).filter(User.id == initiated_by_user_id).first()
            else:
                actor = db.query(User).filter(User.role == "admin").order_by(User.created_at.asc()).first()
            if actor is None:
                summary = _task_summary("skipped", zone=zone, reason="no system actor available")
                cache_task_result(self.request.id, summary)
                return summary

            payload = TriggerSimulateRequest(zone=zone, **(simulation_payload or {}))
            logger.info("task start process_trigger_event", extra={"task_id": self.request.id, "zone": zone})
            response = process_zone_trigger_check(payload, db, actor, enqueue_claim_processing=True)
            summary = _task_summary(
                "completed",
                zone=zone,
                claims_created=response.claims_created,
                payouts_created=response.payouts_created,
                message=response.message,
            )
            cache_task_result(self.request.id, summary)
            logger.info("task end process_trigger_event", extra={"task_id": self.request.id, **summary})
            return summary
        finally:
            db.close()


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3}, name="app.tasks.process_claim")
def process_claim(self, claim_id: str, initiated_by_user_id: str | None = None, auto_source: str = "trigger_monitor"):
    with redis_lock(f"lock:claim:{claim_id}") as acquired:
        if not acquired:
            summary = _task_summary("duplicate", claim_id=claim_id, reason="claim task already running")
            cache_task_result(self.request.id, summary)
            return summary

        db = SessionLocal()
        try:
            claim = db.query(Claim).filter(Claim.id == claim_id).first()
            if claim is None:
                summary = _task_summary("missing", claim_id=claim_id)
                cache_task_result(self.request.id, summary)
                return summary

            enqueue_task(process_payout, claim.id, initiated_by_user_id=initiated_by_user_id, auto_source=auto_source)
            summary = _task_summary("queued", claim_id=claim.id, next_task="process_payout")
            cache_task_result(self.request.id, summary)
            return summary
        finally:
            db.close()


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3}, name="app.tasks.process_payout")
def process_payout(self, claim_id: str, initiated_by_user_id: str | None = None, auto_source: str = "manual"):
    with redis_lock(f"lock:payout:{claim_id}") as acquired:
        if not acquired:
            summary = _task_summary("duplicate", claim_id=claim_id, reason="payout task already running")
            cache_task_result(self.request.id, summary)
            return summary

        db = SessionLocal()
        try:
            claim = db.query(Claim).filter(Claim.id == claim_id).first()
            if claim is None:
                summary = _task_summary("missing", claim_id=claim_id)
                cache_task_result(self.request.id, summary)
                return summary

            payout = process_claim_payout(db, claim, auto_source=auto_source)
            db.commit()
            summary = _task_summary(
                "completed",
                claim_id=claim.id,
                payout_id=payout.id if payout else None,
                claim_status=claim.status,
            )
            cache_task_result(self.request.id, summary)
            return summary
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3}, name="app.tasks.evaluate_fraud")
def evaluate_fraud(self, rider_id: str, claim_id: str | None = None):
    with redis_lock(f"lock:fraud:{rider_id}:{claim_id or 'none'}") as acquired:
        if not acquired:
            summary = _task_summary("duplicate", rider_id=rider_id, claim_id=claim_id)
            cache_task_result(self.request.id, summary)
            return summary

        db = SessionLocal()
        try:
            rider = db.query(User).filter(User.id == rider_id).first()
            if rider is None:
                summary = _task_summary("missing", rider_id=rider_id)
                cache_task_result(self.request.id, summary)
                return summary
            claim = db.query(Claim).filter(Claim.id == claim_id).first() if claim_id else None
            zone = claim.trigger.zone if claim and claim.trigger and claim.trigger.zone else rider.zone
            features = build_fraud_features(db, rider, zone, claim)
            result = evaluate_fraud_sync(features)
            summary = _task_summary(
                "completed",
                rider_id=rider.id,
                claim_id=claim.id if claim else None,
                anomaly_score=result["anomaly_score"],
                is_anomaly=result["is_anomaly"],
                model_available=result["model_available"],
            )
            cache_task_result(self.request.id, {**summary, "features": features})
            return {**summary, "features": features}
        finally:
            db.close()


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3}, name="app.tasks.generate_llm_insight")
def generate_llm_insight(self, kind: str, payload: dict, requested_by_user_id: str | None = None):
    logger.info("task start generate_llm_insight", extra={"task_id": self.request.id, "kind": kind})
    if kind != "admin_insight":
        summary = _task_summary("failed", kind=kind, error="unsupported insight kind")
        cache_task_result(self.request.id, summary)
        return summary

    zone_data = payload.get("zone_data", "")
    insight = generate_admin_insights(zone_data)
    summary = _task_summary("completed", kind=kind, requested_by_user_id=requested_by_user_id, insight=insight)
    cache_task_result(self.request.id, summary)
    logger.info("task end generate_llm_insight", extra={"task_id": self.request.id, "kind": kind})
    return summary
