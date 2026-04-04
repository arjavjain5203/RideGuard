import asyncio
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TEST_DB_PATH = ROOT / "tests" / "rideguard_api_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["SECRET_KEY"] = "rideguard-test-secret"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "120"
os.environ["ENABLE_TRIGGER_MONITOR"] = "false"

from fastapi import HTTPException  # noqa: E402

from app.auth import require_admin, require_rider_or_admin_access  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import root, ensure_runtime_schema, seed_coverage_modules  # noqa: E402
from app.models import Claim, User  # noqa: E402
from app.routers.admin import create_rider as create_admin_rider, get_fraud_alerts, get_metrics, get_recent_claims, list_riders as list_admin_riders  # noqa: E402
from app.routers.auth import login as login_endpoint, me as me_endpoint  # noqa: E402
from app.routers.claims import get_claim as get_claim_endpoint, list_rider_claims  # noqa: E402
from app.routers.llm import (  # noqa: E402
    ClaimExplainRequest,
    FraudExplainRequest,
    InsightsRequest,
    RiskExplainRequest,
    explain_claim_endpoint,
    explain_fraud_endpoint,
    explain_risk_endpoint,
    generate_insights_endpoint,
)
from app.routers.mock_external import get_aqi, get_traffic, get_weather, set_extreme_conditions  # noqa: E402
from app.routers.payouts import (  # noqa: E402
    get_claim as get_payout_claim_endpoint,
    get_rider_payouts,
    process_payout,
)
from app.routers.policies import (  # noqa: E402
    calculate_rider_premium,
    create_policy,
    get_rider_policies,
    list_coverage_modules,
    update_policy,
)
from app.routers.riders import get_rider, get_rider_score, register_rider  # noqa: E402
from app.routers.triggers import check_zone_triggers  # noqa: E402
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
                    rainfall_mm_hr=18.0,
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
