# Architecture

RideGuard is currently a single web application with a browser frontend, one FastAPI backend process, and one relational database. The design is intentionally simple for prototype and demo use.

## High-Level Structure

```text
Browser
  |
  v
Next.js frontend
  |
  v
Axios API client with bearer token
  |
  v
FastAPI app
  |- auth and rider routers
  |- policy, trigger, claim, payout routers
  |- admin and LLM routers
  |- mock external data router
  |
  v
SQLAlchemy
  |
  +--> PostgreSQL in Docker Compose
  |
  +--> SQLite for local dev and tests

Optional integrations:
- background trigger monitor loop inside the API process
- Gemini-backed text generation, with mock fallback
```

## Frontend Responsibilities

The frontend is a Next.js App Router app under `frontend/src/app`.

- `AppShell` wraps every page with `AuthProvider`, `ToastProvider`, and the top navbar.
- Rider-facing pages handle onboarding, policy selection, dashboard, claims, and payouts.
- Admin-facing pages handle admin login and the admin dashboard.
- `frontend/src/services/api.js` owns all HTTP calls, token storage, and Axios interceptors.
- Route protection is implemented in client-side `useEffect` checks and redirects.

## Backend Responsibilities

The backend is a FastAPI app assembled in `backend/app/main.py`.

- Routers expose grouped REST endpoints under `/api/*`.
- `auth.py` handles password hashing, token creation, token validation, and role checks.
- `models.py` and `database.py` define the ORM layer.
- `services/` contains pricing, risk, fraud, payout, trigger-monitor, and LLM logic.
- `main.py` owns startup lifecycle, schema initialization, seed data, and optional background tasks.

## Startup Lifecycle

On application startup, the FastAPI lifespan function does the following:

1. Calls `Base.metadata.create_all(bind=engine)`.
2. Calls `ensure_runtime_schema()` to patch older local SQLite databases forward.
3. Calls `seed_coverage_modules()` to seed coverage modules, zones, demo rider, demo admin, trust logs, and derived hourly income.
4. Starts `start_monitor_loop()` if `ENABLE_TRIGGER_MONITOR` is true.

Important implications:

- PostgreSQL production-like environments are expected to use `db/migrations/001_init.sql`.
- SQLite environments may be mutated at runtime for compatibility.
- Trigger monitoring is not a separate service; it shares the API process.

## Data And Control Flows

### Authentication flow

```text
Login page
  -> POST /api/auth/login
  -> backend verifies PBKDF2 password hash
  -> backend returns bearer token and user profile
  -> frontend stores token in localStorage
  -> subsequent requests send Authorization: Bearer <token>
```

### Policy pricing and creation flow

```text
Policy page
  -> GET /api/policies/modules
  -> POST /api/policies/calculate-premium
       -> backend fetches live mock zone conditions
       -> risk_engine computes risk score
       -> premium_calculator computes weekly premium
  -> POST /api/policies/
       -> backend writes one active policy for the rider
```

### Trigger to payout flow

```text
Trigger check
  -> POST /api/triggers/check
  -> backend evaluates current or simulated conditions
  -> trigger records are created or updated
  -> ended triggers that meet duration rules create claims
  -> fraud_detection computes signal vector and effective URTS
  -> payment_service processes payout eligibility and caps
  -> claims and payouts become visible in rider/admin views
```

## Background Monitoring

The background monitor in `services/trigger_monitor.py` is an asyncio loop that:

- wakes up every 900 seconds
- loads zones from the database, or falls back to a small default list
- finds the earliest admin account and uses it as the system actor
- calls the same `check_zone_triggers()` handler used by explicit trigger simulations

This design keeps trigger logic in one place, but it also means:

- monitoring and API traffic share one process
- a slow or failing monitor loop affects the same runtime as HTTP requests
- there is no queue, job persistence, or retry orchestration

## External Dependency Model

The current app does not call real environmental or payment providers.

- Policy pricing and trigger evaluation pull data from in-process mock helpers.
- The `/mock/*` routes exist for inspection and demo forcing.
- LLM text generation optionally uses Gemini if both a key and SDK are present.
- Payouts are synthetic database records with generated transaction IDs.

## Main Architectural Tradeoffs

- Simple startup seeding makes demos easy, but mixes bootstrap logic into application startup.
- SQLite compatibility logic is convenient for local work, but weakens strict migration discipline.
- Client-side route guards keep the frontend simple, but session handling is not production-grade.
- Shared API and worker responsibilities reduce infrastructure needs, but limit scalability and isolation.
