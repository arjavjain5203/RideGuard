import asyncio
import json
import os
import sys
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TEST_DB_PATH = ROOT / "tests" / "rideguard_api_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["SECRET_KEY"] = "rideguard-test-secret"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "120"
os.environ["ENABLE_TRIGGER_MONITOR"] = "false"
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"
os.environ["CELERY_BROKER_URL"] = "memory://"
os.environ["CELERY_RESULT_BACKEND"] = "cache+memory://"

from fastapi import HTTPException  # noqa: E402

from app.auth import require_admin, require_rider_or_admin_access  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app, root, ensure_runtime_schema, seed_coverage_modules  # noqa: E402
from app.models import AuditLog, Claim, Payout, TriggerRecord, UrtsHistory, User  # noqa: E402
from app.routers.admin import create_rider as create_admin_rider, get_fraud_alerts, get_metrics, get_recent_claims, list_riders as list_admin_riders  # noqa: E402
from app.routers.auth import login as login_endpoint, me as me_endpoint  # noqa: E402
from app.routers.claims import get_claim as get_claim_endpoint, list_rider_claims  # noqa: E402
from app.routers.fraud import FraudEvaluateRequest, evaluate_fraud_endpoint, queue_fraud_evaluation  # noqa: E402
from app.routers.llm import (  # noqa: E402
    ClaimExplainRequest,
    FraudExplainRequest,
    InsightsRequest,
    RiskExplainRequest,
    explain_claim_endpoint,
    explain_fraud_endpoint,
    explain_risk_endpoint,
    generate_insights_endpoint,
    queue_generate_insights_endpoint,
)
from app.routers.ml import predict_disruption_endpoint  # noqa: E402
from app.routers.mock_external import MOCK_STATE, get_aqi, get_traffic, get_weather, set_extreme_conditions  # noqa: E402
from app.routers.payouts import (  # noqa: E402
    get_claim as get_payout_claim_endpoint,
    get_rider_payouts,
    process_payout,
    queue_payout_processing,
)
from app.routers.policies import (  # noqa: E402
    calculate_rider_premium,
    create_policy,
    get_rider_policies,
    list_coverage_modules,
    update_policy,
)
from app.routers.riders import get_rider, get_rider_score, register_rider  # noqa: E402
from app.routers.tasks import get_task_status  # noqa: E402
from app.routers.triggers import check_zone_triggers, queue_zone_trigger_check  # noqa: E402
from app.routers.zomato import get_rider_earnings  # noqa: E402
from app.schemas import (  # noqa: E402
    LoginRequest,
    PolicyCreate,
    PolicyUpdate,
    PremiumCalculateRequest,
    PayoutProcessRequest,
    TriggerSimulateRequest,
    UserCreate,
)


def reset_database():
    engine.dispose()
    for path in (
        TEST_DB_PATH,
        Path(f"{TEST_DB_PATH}-wal"),
        Path(f"{TEST_DB_PATH}-shm"),
    ):
        if path.exists():
            path.unlink()
    Base.metadata.create_all(bind=engine)
    ensure_runtime_schema()
    seed_coverage_modules()


class RideGuardApiTests(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        reset_database()
        MOCK_STATE["Koramangala"] = {"temp": 28, "rain": 0, "aqi": 80, "speed": 22}
        self.db = SessionLocal()

    def tearDown(self):
        self.db.close()

    def _register_rider(self, suffix="001"):
        payload = UserCreate(
            login_id=f"rider{suffix}@example.com",
            password="RiderPass123",
            zomato_partner_id=f"ZMT-BLR-{suffix}",
            name=f"Rider {suffix}",
            phone=f"9876500{suffix[-3:]}",
            zone="Koramangala",
            upi_handle=f"rider{suffix}@ybl",
        )
        user = register_rider(payload, self.db)
        return payload, user

    def test_health_and_mock_external_endpoints(self):
        health = root()
        weather = get_weather("Koramangala")
        aqi = get_aqi("Koramangala")
        traffic = get_traffic("Koramangala")
        forced = set_extreme_conditions("Koramangala", "rain")

        self.assertEqual(health["status"], "operational")
        self.assertEqual(weather["zone"], "Koramangala")
        self.assertEqual(aqi["zone"], "Koramangala")
        self.assertEqual(traffic["zone"], "Koramangala")
        self.assertEqual(forced["forced_event"], "rain")

    def test_slashless_protected_routes_do_not_redirect(self):
        route_paths = {(getattr(route, "path", None), tuple(sorted(getattr(route, "methods", set())))) for route in app.routes}

        self.assertFalse(app.router.redirect_slashes)
        self.assertIn(("/api/riders", ("POST",)), route_paths)
        self.assertIn(("/api/riders/", ("POST",)), route_paths)
        self.assertIn(("/api/policies", ("POST",)), route_paths)
        self.assertIn(("/api/policies/", ("POST",)), route_paths)

    def test_registration_auth_and_rider_scoped_handlers(self):
        payload, rider = self._register_rider("111")

        with self.assertRaises(HTTPException) as duplicate_exc:
            register_rider(payload, self.db)
        self.assertEqual(duplicate_exc.exception.status_code, 409)

        rider_auth = login_endpoint(LoginRequest(login_id=payload.login_id, password=payload.password), self.db)
        demo_rider_auth = login_endpoint(
            LoginRequest(login_id="rider.demo@rideguard.local", password="RideGuardRider@123"),
            self.db,
        )
        admin_auth = login_endpoint(
            LoginRequest(login_id="admin@rideguard.local", password="RideGuardAdmin@123"),
            self.db,
        )

        current_user = self.db.get(User, rider.id)
        me = me_endpoint(current_user)
        rider_details = get_rider(rider.id, self.db, current_user=current_user)
        rider_score = get_rider_score(rider.id, self.db, current_user=current_user)
        earnings = get_rider_earnings(rider.id, self.db, current_user=current_user)

        self.assertEqual(rider_auth.user.role, "rider")
        self.assertEqual(demo_rider_auth.user.role, "rider")
        self.assertEqual(admin_auth.user.role, "admin")
        self.assertEqual(me.id, rider.id)
        self.assertEqual(rider_details.id, rider.id)
        self.assertEqual(rider_score.rider_id, rider.id)
        self.assertEqual(earnings.rider_id, rider.id)

        require_rider_or_admin_access(rider.id, current_user)
        _, other_rider = self._register_rider("112")
        with self.assertRaises(HTTPException) as forbidden_exc:
            require_rider_or_admin_access(other_rider.id, current_user)
        self.assertEqual(forbidden_exc.exception.status_code, 403)

    def test_queue_endpoints_return_task_metadata(self):
        _, rider = self._register_rider("113")
        current_user = self.db.get(User, rider.id)
        policy = create_policy(
            PolicyCreate(rider_id=rider.id, modules=["rain"]),
            self.db,
            current_user=current_user,
        )
        policy.weekly_premium = 10_000.0
        self.db.commit()

        queue_trigger = asyncio.run(
            queue_zone_trigger_check(
                TriggerSimulateRequest(
                    zone="Koramangala",
                    rainfall_mm_hr=30.0,
                    temperature_c=30.0,
                    aqi=90.0,
                    traffic_speed_kmh=18.0,
                ),
                self.db,
                current_user=current_user,
            )
        )
        self.assertEqual(queue_trigger.status, "queued")
        self.assertEqual(queue_trigger.task_name, "process_trigger_event")

        claim = self.db.query(Claim).filter(Claim.user_id == rider.id).order_by(Claim.created_at.desc()).first()
        self.assertIsNotNone(claim)

        queue_payout = queue_payout_processing(
            PayoutProcessRequest(claim_id=claim.id),
            self.db,
            current_user=current_user,
        )
        self.assertEqual(queue_payout.status, "queued")
        self.assertEqual(queue_payout.entity_id, claim.id)

        fraud_task = queue_fraud_evaluation(
            FraudEvaluateRequest(rider_id=rider.id, claim_id=claim.id),
            self.db,
            current_user=current_user,
        )
        self.assertEqual(fraud_task.status, "queued")

        admin_user = self.db.query(User).filter_by(role="admin").first()
        insight_task = queue_generate_insights_endpoint(
            InsightsRequest(zone_data="Koramangala rainfall elevated"),
            current_user=admin_user,
        )
        self.assertEqual(insight_task.status, "queued")
        task_status = get_task_status(insight_task.task_id, current_user=admin_user)
        self.assertIn(task_status.status, {"success", "pending", "queued"})

    def test_policy_trigger_claim_and_payout_flow(self):
        payload, rider = self._register_rider("222")
        current_user = self.db.get(User, rider.id)

        modules = list_coverage_modules(self.db, current_user=current_user)
        premium = calculate_rider_premium(
            PremiumCalculateRequest(rider_id=rider.id, modules=["rain", "aqi"]),
            self.db,
            current_user=current_user,
        )
        created_policy = create_policy(
            PolicyCreate(rider_id=rider.id, modules=["rain", "aqi"]),
            self.db,
            current_user=current_user,
        )
        updated_policy = update_policy(
            created_policy.id,
            PolicyUpdate(modules=["rain", "aqi", "heat"]),
            self.db,
            current_user=current_user,
        )
        policies = get_rider_policies(rider.id, self.db, current_user=current_user)
        _, other_rider = self._register_rider("223")
        other_user = self.db.get(User, other_rider.id)
        with self.assertRaises(HTTPException) as forbidden_policy_exc:
            update_policy(
                created_policy.id,
                PolicyUpdate(modules=["rain"]),
                self.db,
                current_user=other_user,
            )

        trigger_result = asyncio.run(
            check_zone_triggers(
                TriggerSimulateRequest(
                    zone="Koramangala",
                    rainfall_mm_hr=30.0,
                    temperature_c=30.0,
                    aqi=90.0,
                    traffic_speed_kmh=18.0,
                ),
                self.db,
                current_user=current_user,
            )
        )
        claim_list = list_rider_claims(rider.id, self.db, current_user=current_user)
        claim = claim_list.claims[0]
        claim_details = get_claim_endpoint(claim.id, self.db, current_user=current_user)
        payout_claim_details = get_payout_claim_endpoint(claim.id, self.db, current_user=current_user)
        payouts = get_rider_payouts(rider.id, self.db, current_user=current_user)

        self.assertGreaterEqual(len(modules), 4)
        self.assertEqual(premium.rider_id, rider.id)
        self.assertEqual(created_policy.rider_id, rider.id)
        self.assertEqual(sorted(updated_policy.modules), ["aqi", "heat", "rain"])
        self.assertEqual(len(policies), 1)
        self.assertEqual(forbidden_policy_exc.exception.status_code, 403)
        self.assertGreaterEqual(trigger_result.claims_created, 1)
        self.assertGreaterEqual(len(claim_list.claims), 1)
        self.assertEqual(claim_details.id, claim.id)
        self.assertEqual(payout_claim_details.id, claim.id)
        self.assertGreaterEqual(len(payouts), 1)

        manual_claim = Claim(
            policy_id=created_policy.id,
            user_id=rider.id,
            trigger_type="aqi",
            trigger_value=320.0,
            disruption_hours=2.0,
            loss_amount=450.0,
            effective_urts=82,
            status="pending",
        )
        self.db.add(manual_claim)
        self.db.commit()
        self.db.refresh(manual_claim)

        manual_payout = process_payout(
            PayoutProcessRequest(claim_id=manual_claim.id),
            self.db,
            current_user=current_user,
        )
        self.assertIn(manual_payout.status, {"completed", "capped"})

    def test_trigger_lifecycle_policy_validation_and_idempotent_payout(self):
        _, rider = self._register_rider("224")
        current_user = self.db.get(User, rider.id)
        policy = create_policy(
            PolicyCreate(rider_id=rider.id, modules=["rain"]),
            self.db,
            current_user=current_user,
        )

        MOCK_STATE["Koramangala"] = {"temp": 28, "rain": 30, "aqi": 80, "speed": 22}
        first_check = asyncio.run(check_zone_triggers(TriggerSimulateRequest(zone="Koramangala"), self.db, current_user))
        trigger = self.db.query(TriggerRecord).filter_by(zone="Koramangala", type="rain").one()
        self.assertEqual(first_check.claims_created, 0)
        self.assertEqual(trigger.status, "ACTIVE")
        self.assertEqual(self.db.query(Claim).filter_by(trigger_id=trigger.id).count(), 0)

        second_check = asyncio.run(check_zone_triggers(TriggerSimulateRequest(zone="Koramangala"), self.db, current_user))
        self.db.refresh(trigger)
        self.assertEqual(second_check.claims_created, 0)
        self.assertEqual(trigger.status, "ONGOING")

        trigger.start_time = datetime.now(UTC) - timedelta(hours=3)
        self.db.commit()
        MOCK_STATE["Koramangala"] = {"temp": 28, "rain": 0, "aqi": 80, "speed": 22}
        ended_check = asyncio.run(check_zone_triggers(TriggerSimulateRequest(zone="Koramangala"), self.db, current_user))
        self.db.refresh(trigger)
        claim = self.db.query(Claim).filter_by(trigger_id=trigger.id, user_id=rider.id).one()
        payout = self.db.query(Payout).filter_by(claim_id=claim.id).one()

        self.assertEqual(ended_check.claims_created, 1)
        self.assertEqual(trigger.status, "ENDED")
        self.assertIsNotNone(trigger.end_time)
        self.assertGreaterEqual(trigger.duration_hours, 2.0)
        self.assertLessEqual(trigger.duration_hours, 8.0)
        self.assertEqual(claim.policy_id, policy.id)
        self.assertEqual(claim.trigger_id, trigger.id)
        self.assertEqual(claim.disruption_hours, trigger.duration_hours)

        duplicate_payout = process_payout(PayoutProcessRequest(claim_id=claim.id), self.db, current_user=current_user)
        self.assertEqual(duplicate_payout.id, payout.id)
        self.assertEqual(self.db.query(Payout).filter_by(claim_id=claim.id).count(), 1)

        no_policy_payload, no_policy_rider = self._register_rider("225")
        no_policy_user = self.db.get(User, no_policy_rider.id)
        no_policy_result = asyncio.run(
            check_zone_triggers(
                TriggerSimulateRequest(zone="Koramangala", rainfall_mm_hr=30, temperature_c=28, aqi=80, traffic_speed_kmh=22),
                self.db,
                current_user=no_policy_user,
            )
        )
        self.assertEqual(no_policy_result.claims_created, 0)
        self.assertIsNotNone(
            self.db.query(AuditLog)
            .filter(AuditLog.entity_id == no_policy_rider.id, AuditLog.action == "CLAIM_SKIPPED")
            .first()
        )

        _, heat_only_rider = self._register_rider("226")
        heat_only_user = self.db.get(User, heat_only_rider.id)
        create_policy(PolicyCreate(rider_id=heat_only_rider.id, modules=["heat"]), self.db, current_user=heat_only_user)
        uncovered_result = asyncio.run(
            check_zone_triggers(
                TriggerSimulateRequest(zone="Koramangala", rainfall_mm_hr=30, temperature_c=28, aqi=80, traffic_speed_kmh=22),
                self.db,
                current_user=heat_only_user,
            )
        )
        self.assertEqual(uncovered_result.claims_created, 0)
        self.assertIsNotNone(
            self.db.query(AuditLog)
            .filter(AuditLog.entity_id == heat_only_rider.id, AuditLog.action == "CLAIM_SKIPPED")
            .first()
        )

    def test_ml_hybrid_trigger_decisions_and_prediction_endpoint(self):
        _, rider = self._register_rider("228")
        current_user = self.db.get(User, rider.id)
        policy = create_policy(
            PolicyCreate(rider_id=rider.id, modules=["rain"]),
            self.db,
            current_user=current_user,
        )
        policy.weekly_premium = 10_000.0
        self.db.commit()

        with patch("app.routers.triggers.predict_disruption", return_value=0.2):
            normal_result = asyncio.run(
                check_zone_triggers(
                    TriggerSimulateRequest(
                        zone="Koramangala",
                        rainfall_mm_hr=4,
                        temperature_c=29,
                        aqi=80,
                        traffic_speed_kmh=22,
                    ),
                    self.db,
                    current_user=current_user,
                )
        )
        self.assertEqual(normal_result.claims_created, 0)
        self.assertEqual(self.db.query(TriggerRecord).count(), 0)

        with patch("app.routers.triggers.predict_disruption", return_value=0.88):
            ml_result = asyncio.run(
                check_zone_triggers(
                    TriggerSimulateRequest(
                        zone="Koramangala",
                        rainfall_mm_hr=18,
                        temperature_c=30,
                        aqi=90,
                        traffic_speed_kmh=18,
                    ),
                    self.db,
                    current_user=current_user,
                )
            )
        ml_trigger = self.db.query(TriggerRecord).filter_by(zone="Koramangala", decision_reason="ML triggered").one()
        self.assertEqual(ml_result.claims_created, 1)
        self.assertEqual(ml_trigger.type, "rain")
        self.assertEqual(ml_trigger.disruption_probability, 0.88)
        self.assertEqual(json.loads(ml_trigger.environment_inputs)["rainfall"], 18.0)

        _, fallback_rider = self._register_rider("229")
        fallback_user = self.db.get(User, fallback_rider.id)
        fallback_policy = create_policy(
            PolicyCreate(rider_id=fallback_rider.id, modules=["rain"]),
            self.db,
            current_user=fallback_user,
        )
        fallback_policy.weekly_premium = 10_000.0
        self.db.commit()
        with patch("app.routers.triggers.predict_disruption", return_value=None):
            fallback_result = asyncio.run(
                check_zone_triggers(
                    TriggerSimulateRequest(
                        zone="Koramangala",
                        rainfall_mm_hr=18,
                        temperature_c=28,
                        aqi=80,
                        traffic_speed_kmh=22,
                    ),
                    self.db,
                    current_user=fallback_user,
                )
            )
        fallback_trigger = (
            self.db.query(TriggerRecord)
            .filter_by(zone="Koramangala", decision_reason="fallback threshold")
            .one()
        )
        self.assertEqual(fallback_result.claims_created, 1)
        self.assertEqual(fallback_trigger.type, "rain")
        self.assertIsNone(fallback_trigger.disruption_probability)

        with patch("app.routers.ml.predict_disruption", return_value=0.81), patch(
            "app.routers.ml.is_model_available", return_value=True
        ):
            prediction = predict_disruption_endpoint(
                rainfall=12,
                temperature=32,
                aqi=120,
                traffic_speed=16,
            )
        self.assertEqual(prediction["probability"], 0.81)
        self.assertTrue(prediction["trigger"])
        self.assertTrue(prediction["model_available"])

    def test_weekly_payout_cap_reduces_and_prevents_duplicate_payouts(self):
        _, rider = self._register_rider("227")
        current_user = self.db.get(User, rider.id)
        current_user.base_urts = 100
        policy = create_policy(
            PolicyCreate(rider_id=rider.id, modules=["rain"]),
            self.db,
            current_user=current_user,
        )
        policy.weekly_premium = 100.0
        self.db.commit()

        first_claim = Claim(
            policy_id=policy.id,
            user_id=rider.id,
            trigger_type="rain",
            trigger_value=18.0,
            disruption_hours=1.5,
            loss_amount=150.0,
            effective_urts=100,
            status="pending",
        )
        second_claim = Claim(
            policy_id=policy.id,
            user_id=rider.id,
            trigger_type="rain",
            trigger_value=18.0,
            disruption_hours=1.0,
            loss_amount=100.0,
            effective_urts=100,
            status="pending",
        )
        self.db.add_all([first_claim, second_claim])
        self.db.commit()

        first_payout = process_payout(PayoutProcessRequest(claim_id=first_claim.id), self.db, current_user=current_user)
        second_payout = process_payout(PayoutProcessRequest(claim_id=second_claim.id), self.db, current_user=current_user)
        duplicate_second_payout = process_payout(PayoutProcessRequest(claim_id=second_claim.id), self.db, current_user=current_user)

        self.assertEqual(first_payout.amount, 150.0)
        self.assertEqual(first_payout.status, "completed")
        self.assertEqual(second_payout.amount, 50.0)
        self.assertEqual(second_payout.status, "capped")
        self.assertEqual(duplicate_second_payout.id, second_payout.id)
        self.assertEqual(self.db.query(Payout).filter_by(claim_id=second_claim.id).count(), 1)

    def test_urts_tiers_history_and_low_score_rejection(self):
        tier_cases = [
            ("240", 85, 1.0, 100.0, "completed"),
            ("241", 70, 0.9, 90.0, "completed"),
            ("242", 50, 0.7, 70.0, "completed"),
        ]

        for suffix, base_urts, expected_factor, expected_amount, expected_status in tier_cases:
            _, rider = self._register_rider(suffix)
            current_user = self.db.get(User, rider.id)
            current_user.base_urts = base_urts
            policy = create_policy(
                PolicyCreate(rider_id=rider.id, modules=["rain"]),
                self.db,
                current_user=current_user,
            )
            policy.weekly_premium = 10_000.0
            claim = Claim(
                policy_id=policy.id,
                user_id=rider.id,
                trigger_type="rain",
                trigger_value=18.0,
                disruption_hours=1.0,
                loss_amount=100.0,
                status="pending",
            )
            self.db.add(claim)
            self.db.commit()

            payout = process_payout(PayoutProcessRequest(claim_id=claim.id), self.db, current_user=current_user)
            self.db.refresh(claim)

            self.assertEqual(payout.urts_factor, expected_factor)
            self.assertEqual(payout.amount, expected_amount)
            self.assertEqual(payout.status, expected_status)
            self.assertEqual(claim.effective_urts_at_event, claim.effective_urts)
            self.assertLessEqual(claim.event_adjustment, 0)
            self.assertEqual(self.db.query(UrtsHistory).filter_by(claim_id=claim.id).count(), 1)

        _, low_rider = self._register_rider("243")
        low_user = self.db.get(User, low_rider.id)
        low_user.base_urts = 35
        low_policy = create_policy(
            PolicyCreate(rider_id=low_rider.id, modules=["rain"]),
            self.db,
            current_user=low_user,
        )
        low_policy.weekly_premium = 10_000.0
        low_claim = Claim(
            policy_id=low_policy.id,
            user_id=low_rider.id,
            trigger_type="rain",
            trigger_value=18.0,
            disruption_hours=1.0,
            loss_amount=100.0,
            status="pending",
        )
        self.db.add(low_claim)
        self.db.commit()

        with self.assertRaises(HTTPException) as blocked_exc:
            process_payout(PayoutProcessRequest(claim_id=low_claim.id), self.db, current_user=low_user)
        self.db.refresh(low_claim)

        self.assertEqual(blocked_exc.exception.status_code, 400)
        self.assertEqual(low_claim.status, "rejected")
        self.assertEqual(self.db.query(Payout).filter_by(claim_id=low_claim.id).count(), 0)
        self.assertEqual(self.db.query(UrtsHistory).filter_by(claim_id=low_claim.id).count(), 1)

    def test_fraud_model_reduces_payout_and_surfaces_claim_fields(self):
        _, rider = self._register_rider("245")
        current_user = self.db.get(User, rider.id)
        current_user.base_urts = 100
        policy = create_policy(
            PolicyCreate(rider_id=rider.id, modules=["rain"]),
            self.db,
            current_user=current_user,
        )
        policy.weekly_premium = 10_000.0
        claim = Claim(
            policy_id=policy.id,
            user_id=rider.id,
            trigger_type="rain",
            trigger_value=18.0,
            disruption_hours=1.0,
            loss_amount=100.0,
            status="pending",
        )
        self.db.add(claim)
        self.db.commit()

        with patch(
            "app.services.behavior_engine.evaluate_fraud",
            return_value={
                "anomaly_score": 0.8,
                "is_anomaly": False,
                "model_available": True,
                "features": {},
            },
        ):
            payout = process_payout(PayoutProcessRequest(claim_id=claim.id), self.db, current_user=current_user)
        self.db.refresh(claim)
        claim_response = get_claim_endpoint(claim.id, self.db, current_user=current_user)
        signals = json.loads(claim.behavioral_signals)

        self.assertEqual(payout.amount, 80.0)
        self.assertEqual(payout.urts_factor, 0.8)
        self.assertEqual(claim.anomaly_score, 0.8)
        self.assertFalse(claim.fraud_flag)
        self.assertEqual(claim_response.anomaly_score, 0.8)
        self.assertFalse(claim_response.fraud_flag)
        self.assertEqual(signals["anomaly_score"], 0.8)
        self.assertEqual(signals["fraud_payout_factor"], 0.8)

    def test_fraud_model_blocks_payout_for_high_anomaly(self):
        _, rider = self._register_rider("246")
        current_user = self.db.get(User, rider.id)
        current_user.base_urts = 100
        policy = create_policy(
            PolicyCreate(rider_id=rider.id, modules=["rain"]),
            self.db,
            current_user=current_user,
        )
        policy.weekly_premium = 10_000.0
        claim = Claim(
            policy_id=policy.id,
            user_id=rider.id,
            trigger_type="rain",
            trigger_value=18.0,
            disruption_hours=1.0,
            loss_amount=100.0,
            status="pending",
        )
        self.db.add(claim)
        self.db.commit()

        with patch(
            "app.services.behavior_engine.evaluate_fraud",
            return_value={
                "anomaly_score": 0.95,
                "is_anomaly": False,
                "model_available": True,
                "features": {},
            },
        ):
            with self.assertRaises(HTTPException) as fraud_exc:
                process_payout(PayoutProcessRequest(claim_id=claim.id), self.db, current_user=current_user)
        self.db.refresh(claim)

        self.assertEqual(fraud_exc.exception.status_code, 400)
        self.assertEqual(claim.status, "rejected")
        self.assertEqual(claim.anomaly_score, 0.95)
        self.assertTrue(claim.fraud_flag)
        self.assertEqual(self.db.query(Payout).filter_by(claim_id=claim.id).count(), 0)

    def test_fraud_model_failure_fallback_and_evaluate_endpoint(self):
        _, rider = self._register_rider("247")
        current_user = self.db.get(User, rider.id)
        current_user.base_urts = 100
        policy = create_policy(
            PolicyCreate(rider_id=rider.id, modules=["rain"]),
            self.db,
            current_user=current_user,
        )
        policy.weekly_premium = 10_000.0
        claim = Claim(
            policy_id=policy.id,
            user_id=rider.id,
            trigger_type="rain",
            trigger_value=18.0,
            disruption_hours=1.0,
            loss_amount=100.0,
            status="pending",
        )
        self.db.add(claim)
        self.db.commit()

        with patch(
            "app.services.behavior_engine.evaluate_fraud",
            return_value={
                "anomaly_score": 0.0,
                "is_anomaly": False,
                "model_available": False,
                "features": {},
            },
        ):
            payout = process_payout(PayoutProcessRequest(claim_id=claim.id), self.db, current_user=current_user)
        self.db.refresh(claim)

        self.assertEqual(payout.amount, 100.0)
        self.assertEqual(claim.anomaly_score, 0.0)
        self.assertFalse(claim.fraud_flag)

        with patch(
            "app.routers.fraud.evaluate_fraud",
            return_value={
                "anomaly_score": 0.42,
                "is_anomaly": False,
                "model_available": True,
                "features": {},
            },
        ):
            result = evaluate_fraud_endpoint(
                FraudEvaluateRequest(rider_id=rider.id, claim_id=claim.id),
                self.db,
                current_user=current_user,
            )
        self.assertEqual(result["anomaly_score"], 0.42)
        self.assertFalse(result["is_anomaly"])
        self.assertTrue(result["model_available"])
        self.assertIn("claims_per_week", result["features"])

    def test_behavioral_anomaly_reduces_urts_and_payout(self):
        _, rider = self._register_rider("244")
        current_user = self.db.get(User, rider.id)
        current_user.base_urts = 70
        policy = create_policy(
            PolicyCreate(rider_id=rider.id, modules=["rain"]),
            self.db,
            current_user=current_user,
        )
        policy.weekly_premium = 10_000.0
        trigger = TriggerRecord(
            zone="Indiranagar",
            type="rain",
            value=18.0,
            status="ENDED",
            start_time=datetime.now(UTC) - timedelta(hours=2),
            end_time=datetime.now(UTC),
            duration_hours=2.0,
        )
        self.db.add(trigger)
        self.db.flush()
        claim = Claim(
            policy_id=policy.id,
            user_id=rider.id,
            trigger_id=trigger.id,
            trigger_type="rain",
            trigger_value=18.0,
            disruption_hours=2.0,
            loss_amount=200.0,
            status="pending",
        )
        self.db.add(claim)
        self.db.commit()

        payout = process_payout(PayoutProcessRequest(claim_id=claim.id), self.db, current_user=current_user)
        self.db.refresh(claim)
        self.db.refresh(current_user)
        signals = json.loads(claim.behavioral_signals)

        self.assertGreaterEqual(signals["gps_anomaly"], 0.8)
        self.assertLess(claim.event_adjustment, -10)
        self.assertEqual(payout.urts_factor, 0.7)
        self.assertLess(current_user.base_urts, 70)

    def test_admin_and_llm_handlers(self):
        _, rider = self._register_rider("333")
        rider_user = self.db.get(User, rider.id)
        admin_user = self.db.query(User).filter_by(role="admin").first()
        admin_created_payload = UserCreate(
            login_id="admin.created.rider@example.com",
            password="RiderPass123",
            zomato_partner_id="ZMT-BLR-ADM-001",
            name="Admin Created Rider",
            phone="9876512333",
            zone="Koramangala",
            upi_handle="admin.created@ybl",
        )

        with self.assertRaises(HTTPException) as admin_exc:
            require_admin(rider_user)
        self.assertEqual(admin_exc.exception.status_code, 403)
        self.assertEqual(require_admin(admin_user).id, admin_user.id)

        metrics = get_metrics(self.db, current_user=admin_user)
        claims = get_recent_claims(self.db, current_user=admin_user)
        fraud_alerts = get_fraud_alerts(self.db, current_user=admin_user)
        admin_created_rider = create_admin_rider(admin_created_payload, self.db, current_user=admin_user)
        rider_list = list_admin_riders(self.db, current_user=admin_user)
        admin_created_auth = login_endpoint(
            LoginRequest(login_id=admin_created_payload.login_id, password=admin_created_payload.password),
            self.db,
        )

        with self.assertRaises(HTTPException) as duplicate_admin_rider_exc:
            create_admin_rider(admin_created_payload, self.db, current_user=admin_user)

        claim_explanation = explain_claim_endpoint(
            ClaimExplainRequest(trigger="rain", hours=2, payout=320, urts=85),
            current_user=rider_user,
        )
        risk_explanation = explain_risk_endpoint(
            RiskExplainRequest(zone="Koramangala", risk_score=0.76),
            current_user=rider_user,
        )
        fraud_explanation = explain_fraud_endpoint(
            FraudExplainRequest(signals={"gps_anomaly": 0.8}, penalty=20),
            current_user=rider_user,
        )
        admin_insight = generate_insights_endpoint(
            InsightsRequest(zone_data="Koramangala rainfall elevated"),
            current_user=admin_user,
        )

        self.assertIn("active_policies", metrics)
        self.assertIsInstance(claims, list)
        self.assertIsInstance(fraud_alerts, list)
        self.assertEqual(admin_created_rider.role, "rider")
        self.assertTrue(admin_created_rider.is_active)
        self.assertTrue(any(r.id == admin_created_rider.id for r in rider_list))
        self.assertEqual(admin_created_auth.user.id, admin_created_rider.id)
        self.assertEqual(duplicate_admin_rider_exc.exception.status_code, 409)
        self.assertIn("explanation", claim_explanation)
        self.assertIn("explanation", risk_explanation)
        self.assertIn("explanation", fraud_explanation)
        self.assertIn("insight", admin_insight)


if __name__ == "__main__":
    unittest.main()
