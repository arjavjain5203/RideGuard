# Setup and Running

This document describes the current working setup paths for the codebase. Prefer this over the root `README.md` and `frontend/README.md`, which still contain older or generic instructions.

## Prerequisites

- Node.js 20 or newer
- npm
- Python 3.11 or newer
- Docker and Docker Compose for the recommended full-stack path

## Recommended Local Path

The current repo is easiest to run fully in Docker with PostgreSQL, the backend API, and the frontend web app under one Compose stack.

### 1. Start the full stack

From the repo root:

```bash
docker compose up --build
```

What this does:

- starts PostgreSQL 15 on `localhost:5432`
- starts the FastAPI backend on `http://localhost:8000`
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
docker compose up --build db backend

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
| `GEMINI_API_KEY` | optional key for live LLM responses in `llm_service.py` |

## Important Notes About `.env.example`

The checked-in `.env.example` is only partially aligned with the running code.

- `JWT_SECRET` is not currently read by the backend. Use `SECRET_KEY`.
- `JWT_EXPIRY` is not currently read by the backend. Use `ACCESS_TOKEN_EXPIRE_MINUTES`.
- `UPI_SIMULATION_MODE` is documented but not consumed by the backend code.
- The weather, AQI, and traffic API keys are future-facing; the current app uses mock providers.

## Ports

| Service | Port | Notes |
| --- | --- | --- |
| Frontend | `3000` | Docker Compose web app or local Next.js dev server |
| Backend | `8000` | FastAPI app |
| PostgreSQL | `5432` | Docker Compose database |

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
