# Setup and Running

This document describes the current working setup paths for the codebase. Prefer this over the root `README.md` and `frontend/README.md`, which still contain older or generic instructions.

## Prerequisites

- Node.js 20 or newer
- npm
- Python 3.11 or newer
- Docker and Docker Compose for the recommended full-stack path

## Recommended Local Path

The current repo is easiest to run fully in Docker with PostgreSQL, Redis, the backend API, a Celery worker, and the frontend web app under one Compose stack.

### 1. Start the full stack

From the repo root:

```bash
docker compose up --build
```

What this does:

- starts PostgreSQL 15 on `localhost:5432`
- starts Redis 7 on `localhost:6379`
- starts the FastAPI backend on `http://localhost:8000`
- starts the Celery worker for queued fraud, payout, trigger, and insight jobs
- starts the Next.js frontend on `http://localhost:3000`
- initializes the database from `db/migrations/001_init.sql` on first boot
- seeds coverage modules, zones, demo accounts, and demo earnings on API startup
- serves the frontend with `NEXT_PUBLIC_API_URL=http://localhost:8000/api`

### 2. Log in with seeded demo accounts

| Role | Login ID | Password |
| --- | --- | --- |
| Rider | `rider.demo@rideguard.local` | `RideGuardRider@123` |
| Admin | `admin@rideguard.local` | `RideGuardAdmin@123` |

### 3. Optional hybrid path: Docker backend plus local frontend

If you want live frontend edits without rebuilding the web image, run only the database and API in Docker and keep Next.js local.

```bash
docker compose up --build postgres redis backend worker

cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000/api npm run dev
```

## Alternative Backend Path: Local SQLite

Use this when you want a lightweight local backend without Docker.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=sqlite:///./rideguard.db
export SECRET_KEY=rideguard-local-secret
export ENABLE_TRIGGER_MONITOR=false
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Notes:

- SQLite is supported for local development and tests.
- On SQLite, the app enables WAL mode and runs runtime schema compatibility updates on startup.
- `ENABLE_TRIGGER_MONITOR=false` is useful locally to keep the background loop from mutating demo data while you are testing UI flows.

## Environment Variables In Use Today

### Backend settings from `backend/app/config.py`

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql://rideguard:rideguard@localhost:5432/rideguard` | SQLAlchemy connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection used for cache and locks |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Celery broker URL |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/1` | Celery result backend URL |
| `CELERY_TASK_ALWAYS_EAGER` | `False` | executes queued tasks inline when true |
| `CELERY_TASK_RESULT_EXPIRES` | `3600` | task result TTL in seconds |
| `CELERY_TASK_TIME_LIMIT_SECONDS` | `300` | hard Celery task timeout |
| `CELERY_TASK_SOFT_TIME_LIMIT_SECONDS` | `240` | soft Celery task timeout |
| `REDIS_LOCK_TTL_SECONDS` | `120` | Redis lock TTL for queued work |
| `RIDER_CACHE_TTL_SECONDS` | `300` | rider cache TTL in seconds |
| `ZONE_RISK_CACHE_TTL_SECONDS` | `300` | zone risk cache TTL in seconds |
| `ACTIVE_TRIGGER_CACHE_TTL_SECONDS` | `180` | active trigger cache TTL in seconds |
| `APP_NAME` | `RideGuard API` | application display name |
| `DEBUG` | `True` | debug-mode style flag |
| `CORS_ORIGINS` | `http://localhost:3000` | comma-separated CORS allow list |
| `SECRET_KEY` | `rideguard-dev-secret-change-me` | token signing secret |
| `TOKEN_ISSUER` | `rideguard-api` | token issuer claim |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` | access token lifetime in minutes |
| `ENABLE_TRIGGER_MONITOR` | `True` | enables the background zone polling loop |

### Additional runtime variables used outside `Settings`

| Variable | Purpose |
| --- | --- |
| `NEXT_PUBLIC_API_URL` | frontend API base URL, defaults to `http://localhost:8000/api` |
| `INTERNAL_API_URL` | server-side API URL used by Next.js rewrites, defaults to `http://127.0.0.1:8000/api` |
| `GEMINI_API_KEY` | optional key for live LLM responses in `llm_service.py` |
| `DISRUPTION_MODEL_PATH` / `DISRUPTION_SCALER_PATH` | optional overrides for disruption model artifacts |
| `FRAUD_MODEL_PATH` / `FRAUD_SCALER_PATH` / `FRAUD_SCORE_SCALER_PATH` | optional overrides for fraud model artifacts |

## Environment Samples

The checked-in env samples are aligned with the current local setup:

- root `.env.example` summarizes the Compose/local defaults.
- `backend/.env.example` contains backend, Redis, Celery, auth, cache, AI, and model settings.
- `frontend/.env.example` contains browser-facing and server-side API URLs.
- Real `.env` files are local-only and should not be committed.

## Ports

| Service | Port | Notes |
| --- | --- | --- |
| Frontend | `3000` | Docker Compose web app or local Next.js dev server |
| Backend | `8000` | FastAPI app |
| PostgreSQL | `5432` | Docker Compose database |
| Redis | `6379` | Docker Compose cache, lock, and Celery broker |

## Common Developer Flows

### Smoke test the API

- Open `http://localhost:8000/` for the health payload.
- Open `http://localhost:8000/docs` for the FastAPI-generated OpenAPI UI.

### Exercise the rider flow

1. Log in as the seeded rider.
2. Visit `/policy` and create a policy if none exists.
3. Use the dashboard button to simulate a rain trigger.
4. Check `/claims` and `/payout` for generated records.

### Exercise the admin flow

1. Log in at `/admin/login`.
2. Review `/admin` for metrics, recent claims, and fraud alerts.
