"""RideGuard — AI-Powered Parametric Insurance API."""

from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.auth import hash_password
from app.database import engine, Base, SessionLocal
from app.models import (
    User,
    Earnings,
    Policy,
    TriggerRecord,
    Claim,
    Payout,
    TrustLog,
    CoverageModule,
    Zone,
)
from app.routers import admin, auth, claims, llm, mock_external, payouts, policies, riders, triggers, zomato
from app.config import settings

ZONE_DISPLAY_NAMES = {
    "koramangala": "Koramangala",
    "indiranagar": "Indiranagar",
    "hsr_layout": "HSR Layout",
    "whitefield": "Whitefield",
    "jayanagar": "Jayanagar",
    "btm_layout": "BTM Layout",
    "electronic_city": "Electronic City",
    "marathahalli": "Marathahalli",
}

DEMO_RIDER = {
    "login_id": "rider.demo@rideguard.local",
    "password": "RideGuardRider@123",
    "zomato_partner_id": "RG-DEMO-RIDER-001",
    "name": "Demo Rider",
    "phone": "9876543210",
    "zone": "Koramangala",
    "upi_handle": "rider.demo@ybl",
    "weekly_earnings": 8400.0,
    "hours_worked": 42,
    "active_days": 6,
}

DEMO_ADMIN = {
    "login_id": "admin@rideguard.local",
    "password": "RideGuardAdmin@123",
    "name": "RideGuard Admin",
    "phone": "9000000000",
    "zone": "Koramangala",
    "upi_handle": "admin@rideguard",
}


def seed_coverage_modules():
    """Seed default coverage modules if table is empty."""
    db = SessionLocal()
    try:
        if db.query(CoverageModule).count() == 0:
            modules = [
                CoverageModule(
                    name="rain", display_name="☔ Rain Shield", base_price=25.00,
                    trigger_type="rain", trigger_threshold=15.0,
                    trigger_duration_hours=2.0,
                    description="Heavy rainfall ≥ 15 mm/hr",
                ),
                CoverageModule(
                    name="flood", display_name="🌊 Flood Guard", base_price=20.00,
                    trigger_type="flood", trigger_threshold=60.0,
                    trigger_duration_hours=6.0,
                    description="Flooding ≥ 60mm OR traffic < 5 km/h",
                ),
                CoverageModule(
                    name="heat", display_name="🌡️ Heat Cover", base_price=15.00,
                    trigger_type="heat", trigger_threshold=42.0,
                    trigger_duration_hours=0.0,
                    description="Extreme heat ≥ 42°C (instant trigger)",
                ),
                CoverageModule(
                    name="aqi", display_name="💨 AQI Protect", base_price=18.00,
                    trigger_type="aqi", trigger_threshold=300.0,
                    trigger_duration_hours=3.0,
                    description="Hazardous AQI ≥ 300",
                ),
            ]
            db.add_all(modules)
            db.commit()
        else:
            duration_defaults = {"rain": 2.0, "flood": 6.0, "heat": 0.0, "aqi": 3.0}
            for module in db.query(CoverageModule).all():
                module.trigger_duration_hours = duration_defaults.get(module.name, 0.0)
            db.commit()

        if db.query(Zone).count() == 0:
            zones = [
                Zone(name=ZONE_DISPLAY_NAMES.get(zone_name, zone_name.replace("_", " ").title()), risk_multiplier=multiplier)
                for zone_name, multiplier in settings.ZONE_MULTIPLIERS.items()
                if zone_name != "default"
            ]
            db.add_all(zones)
            db.commit()

        demo_rider = db.query(User).filter(User.login_id == DEMO_RIDER["login_id"]).first()
        if not demo_rider:
            demo_rider = User(
                login_id=DEMO_RIDER["login_id"],
                password_hash=hash_password(DEMO_RIDER["password"]),
                role="rider",
                zomato_partner_id=DEMO_RIDER["zomato_partner_id"],
                name=DEMO_RIDER["name"],
                zone=DEMO_RIDER["zone"],
                phone=DEMO_RIDER["phone"],
                upi_handle=DEMO_RIDER["upi_handle"],
                base_urts=72,
                is_active=True,
            )
            db.add(demo_rider)
            db.flush()
            db.add(
                Earnings(
                    user_id=demo_rider.id,
                    weekly_earnings=DEMO_RIDER["weekly_earnings"],
                    hours_worked=DEMO_RIDER["hours_worked"],
                    active_days=DEMO_RIDER["active_days"],
                )
            )
            db.add(
                TrustLog(
                    user_id=demo_rider.id,
                    change=72,
                    reason="Seeded demo rider",
                )
            )
            db.commit()

        demo_admin = db.query(User).filter(User.login_id == DEMO_ADMIN["login_id"]).first()
        if not demo_admin:
            demo_admin = User(
                login_id=DEMO_ADMIN["login_id"],
                password_hash=hash_password(DEMO_ADMIN["password"]),
                role="admin",
                zomato_partner_id=None,
                name=DEMO_ADMIN["name"],
                zone=DEMO_ADMIN["zone"],
                phone=DEMO_ADMIN["phone"],
                upi_handle=DEMO_ADMIN["upi_handle"],
                base_urts=100,
                is_active=False,
            )
            db.add(demo_admin)
            db.commit()

        users = db.query(User).all()
        for user in users:
            if not user.login_id and user.zomato_partner_id:
                user.login_id = user.zomato_partner_id.strip().lower()
            if user.role == "rider" and not user.password_hash and user.phone:
                # Transitional compatibility for riders created before credential auth existed.
                user.password_hash = hash_password(user.phone)
            if user.hourly_income:
                continue
            earnings = db.query(Earnings).filter(Earnings.user_id == user.id).first()
            if earnings and earnings.hours_worked:
                user.hourly_income = round(earnings.weekly_earnings / earnings.hours_worked, 2)
        db.commit()
    finally:
        db.close()


def ensure_runtime_schema():
    """
    Bring existing local SQLite databases forward to the current runtime schema.

    PostgreSQL production deployments are expected to use the checked-in SQL migration.
    """
    if not str(engine.url).startswith("sqlite"):
        return

    expected_columns = {
        "users": {
            "login_id": "ALTER TABLE users ADD COLUMN login_id VARCHAR(128)",
            "password_hash": "ALTER TABLE users ADD COLUMN password_hash VARCHAR(512)",
            "role": "ALTER TABLE users ADD COLUMN role VARCHAR(16) DEFAULT 'rider'",
            "hourly_income": "ALTER TABLE users ADD COLUMN hourly_income FLOAT",
            "is_active": "ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1",
            "last_login_at": "ALTER TABLE users ADD COLUMN last_login_at DATETIME",
            "updated_at": "ALTER TABLE users ADD COLUMN updated_at DATETIME",
        },
        "coverage_modules": {
            "trigger_duration_hours": "ALTER TABLE coverage_modules ADD COLUMN trigger_duration_hours FLOAT DEFAULT 0",
        },
        "policies": {
            "zone_multiplier": "ALTER TABLE policies ADD COLUMN zone_multiplier FLOAT DEFAULT 1.0",
            "risk_score": "ALTER TABLE policies ADD COLUMN risk_score FLOAT DEFAULT 0.5",
            "valid_from": "ALTER TABLE policies ADD COLUMN valid_from DATETIME",
            "valid_until": "ALTER TABLE policies ADD COLUMN valid_until DATETIME",
        },
        "claims": {
            "policy_id": "ALTER TABLE claims ADD COLUMN policy_id VARCHAR(36)",
            "trigger_type": "ALTER TABLE claims ADD COLUMN trigger_type VARCHAR(32)",
            "trigger_value": "ALTER TABLE claims ADD COLUMN trigger_value FLOAT",
            "disruption_start": "ALTER TABLE claims ADD COLUMN disruption_start DATETIME",
            "disruption_end": "ALTER TABLE claims ADD COLUMN disruption_end DATETIME",
        },
        "payouts": {
            "paid_at": "ALTER TABLE payouts ADD COLUMN paid_at DATETIME",
        },
    }

    inspector = inspect(engine)
    with engine.begin() as conn:
        for table_name, table_columns in expected_columns.items():
            existing = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, ddl in table_columns.items():
                if column_name not in existing:
                    conn.execute(text(ddl))

        conn.execute(
            text(
                """
                UPDATE coverage_modules
                SET trigger_duration_hours = CASE name
                    WHEN 'rain' THEN 2.0
                    WHEN 'flood' THEN 6.0
                    WHEN 'heat' THEN 0.0
                    WHEN 'aqi' THEN 3.0
                    ELSE COALESCE(trigger_duration_hours, 0.0)
                END
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE users
                SET login_id = COALESCE(login_id, LOWER(zomato_partner_id)),
                password_hash = COALESCE(
                    password_hash,
                    CASE
                        WHEN role IS NULL OR role = 'rider' THEN NULL
                        ELSE password_hash
                    END
                ),
                role = COALESCE(role, 'rider'),
                hourly_income = COALESCE(
                    hourly_income,
                    (
                        SELECT ROUND(e.weekly_earnings / CASE WHEN e.hours_worked = 0 THEN 1 ELSE e.hours_worked END, 2)
                        FROM earnings e
                        WHERE e.user_id = users.id
                    )
                ),
                is_active = COALESCE(is_active, 1),
                updated_at = COALESCE(updated_at, created_at)
                """
            )
        )
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_login_id ON users(login_id)"))
        conn.execute(
            text(
                """
                UPDATE policies
                SET zone_multiplier = COALESCE(zone_multiplier, 1.0),
                    risk_score = COALESCE(risk_score, 0.5),
                    valid_from = COALESCE(valid_from, created_at),
                    valid_until = COALESCE(valid_until, DATETIME(created_at, '+7 day'))
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE claims
                SET trigger_type = COALESCE(trigger_type, (SELECT type FROM triggers WHERE triggers.id = claims.trigger_id)),
                    trigger_value = COALESCE(trigger_value, (SELECT value FROM triggers WHERE triggers.id = claims.trigger_id)),
                    disruption_start = COALESCE(disruption_start, (SELECT start_time FROM triggers WHERE triggers.id = claims.trigger_id), created_at),
                    disruption_end = COALESCE(disruption_end, (SELECT end_time FROM triggers WHERE triggers.id = claims.trigger_id)),
                    policy_id = COALESCE(policy_id, (SELECT id FROM policies WHERE policies.user_id = claims.user_id AND policies.status = 'active' ORDER BY created_at DESC LIMIT 1))
                """
            )
        )
        conn.execute(text("UPDATE payouts SET paid_at = COALESCE(paid_at, created_at)"))


from app.services.trigger_monitor import start_monitor_loop

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables
    Base.metadata.create_all(bind=engine)
    ensure_runtime_schema()
    seed_coverage_modules()
    
    task = None
    if settings.ENABLE_TRIGGER_MONITOR:
        task = asyncio.create_task(start_monitor_loop())
    
    yield
    
    if task is not None:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="RideGuard API - Validated Enterprise Edition",
    description="AI-powered parametric insurance platform utilizing mock robust API services",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(riders.router)
app.include_router(auth.router)
app.include_router(zomato.router)
app.include_router(policies.router)
app.include_router(triggers.router)
app.include_router(payouts.router)
app.include_router(claims.router)
app.include_router(mock_external.router)
app.include_router(llm.router)
app.include_router(admin.router)


@app.get("/", tags=["Health"])
def root():
    return {
        "service": "RideGuard Data-Integrated API",
        "version": "2.0.0",
        "status": "operational",
    }
