"""RideGuard — AI-Powered Parametric Insurance API."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base, SessionLocal
from app.models import (
    User, Earnings, Policy, TriggerRecord, 
    Claim, Payout, TrustLog, CoverageModule
)
from app.routers import riders, zomato, policies, triggers, payouts, mock_external, llm, admin


def seed_coverage_modules():
    """Seed default coverage modules if table is empty."""
    db = SessionLocal()
    try:
        if db.query(CoverageModule).count() == 0:
            modules = [
                CoverageModule(
                    name="rain", display_name="☔ Rain Shield", base_price=25.00,
                    trigger_type="rain", trigger_threshold=15.0,
                    description="Heavy rainfall ≥ 15 mm/hr",
                ),
                CoverageModule(
                    name="flood", display_name="🌊 Flood Guard", base_price=20.00,
                    trigger_type="flood", trigger_threshold=60.0,
                    description="Flooding ≥ 60mm OR traffic < 5 km/h",
                ),
                CoverageModule(
                    name="heat", display_name="🌡️ Heat Cover", base_price=15.00,
                    trigger_type="heat", trigger_threshold=42.0,
                    description="Extreme heat ≥ 42°C (instant trigger)",
                ),
                CoverageModule(
                    name="aqi", display_name="💨 AQI Protect", base_price=18.00,
                    trigger_type="aqi", trigger_threshold=300.0,
                    description="Hazardous AQI ≥ 300",
                ),
            ]
            db.add_all(modules)
            db.commit()
            
        # Optional: Pre-seed a few mock users if needed
        if db.query(User).count() == 0:
            u1 = User(zomato_partner_id="ZMT-BLR-001", name="Arun Kumar", zone="Koramangala", phone="9988776655", upi_handle="arun@ybl")
            u2 = User(zomato_partner_id="ZMT-BLR-002", name="Priya M", zone="Indiranagar", phone="8877665544", upi_handle="priya@okicici")
            u3 = User(zomato_partner_id="ZMT-BLR-003", name="Raju S", zone="HSR Layout", phone="7766554433", upi_handle="raju@upi")
            db.add_all([u1, u2, u3])
            db.commit()
            db.refresh(u1)
            
            e1 = Earnings(user_id=u1.id, weekly_earnings=7500.0, hours_worked=40, active_days=6)
            e2 = Earnings(user_id=u2.id, weekly_earnings=6200.0, hours_worked=35, active_days=5)
            e3 = Earnings(user_id=u3.id, weekly_earnings=9100.0, hours_worked=48, active_days=7)
            db.add_all([e1, e2, e3])
            db.commit()
    finally:
        db.close()


from app.services.trigger_monitor import start_monitor_loop

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables
    Base.metadata.create_all(bind=engine)
    seed_coverage_modules()
    
    # Start automated trigger monitor (Part 3)
    import asyncio
    task = asyncio.create_task(start_monitor_loop())
    
    yield
    
    task.cancel()


app = FastAPI(
    title="RideGuard API - Validated Enterprise Edition",
    description="AI-powered parametric insurance platform utilizing mock robust API services",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(riders.router)
app.include_router(zomato.router)
app.include_router(policies.router)
app.include_router(triggers.router)
app.include_router(payouts.router)
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
