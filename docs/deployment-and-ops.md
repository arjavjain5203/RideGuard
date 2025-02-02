# Deployment and Ops

This document describes the current runtime topology and operational caveats for the project as it exists today.

## Current Runtime Topology

| Component | How it runs today | Notes |
| --- | --- | --- |
| PostgreSQL | Docker Compose service `postgres` | initialized from `db/migrations/001_init.sql` on first boot |
| Redis | Docker Compose service `redis` | used for cache, locks, Celery broker, and Celery result storage |
| Backend API | Docker Compose service `backend` or local `uvicorn` | owns HTTP traffic, startup seeding, and optional trigger monitoring |
| Worker | Docker Compose service `worker` | runs Celery jobs for queued fraud, payout, trigger, and insight work |
| Frontend | Docker Compose service `frontend` or local Next.js dev server | served on port `3000`, defaults to `NEXT_PUBLIC_API_URL=http://localhost:8000/api` |

## Docker Compose Details

The checked-in `docker-compose.yml` defines five services.

### `postgres`

- image: `postgres:15-alpine`
- port: `5432:5432`
- database: `rideguard`
- user/password: `rideguard` / `rideguard`
- volume: named volume `postgres_data`
- init script: mounts `db/migrations/001_init.sql` into `/docker-entrypoint-initdb.d/`
- healthcheck: `pg_isready -U rideguard -d rideguard`

### `redis`

- image: `redis:7-alpine`
- port: `6379:6379`
- healthcheck: `redis-cli ping`

### `backend`

- built from `backend/Dockerfile`
- port: `8000:8000`
- mounted source: `./backend:/app`
- mounted models: `./models:/app/models`
- environment override: `DATABASE_URL=postgresql://rideguard:rideguard@postgres:5432/rideguard`
- additional env: Redis, Celery, CORS, auth, token lifetime, and trigger monitor settings
- startup command: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
- healthcheck: HTTP probe against `http://127.0.0.1:8000/`
- depends on healthy `postgres` and `redis`

### `worker`

- built from `backend/Dockerfile`
- mounted source: `./backend:/app`
- mounted models: `./models:/app/models`
- command: `celery -A app.core.celery_app:celery_app worker --loglevel=info`
- environment override: same Postgres, Redis, Celery, and auth settings as the backend
- trigger monitor disabled in the worker container
- depends on healthy `postgres` and `redis`

### `frontend`

- built from `frontend/Dockerfile`
- port: `3000:3000`
- Next.js standalone runtime image
- build args: `NEXT_PUBLIC_API_URL=http://localhost:8000/api`, `INTERNAL_API_URL=http://backend:8000/api`
- runtime env: `NEXT_PUBLIC_API_URL=http://localhost:8000/api`, `INTERNAL_API_URL=http://backend:8000/api`
- depends on a healthy `backend` service

## Startup Side Effects To Expect

Every backend startup currently does the following:

- creates ORM tables if they do not exist
- runs SQLite compatibility updates when using SQLite
- seeds coverage modules and zones if missing
- seeds the demo rider and demo admin if missing
- may start the background trigger monitor loop, which can queue Celery work through Redis

Operationally, that means application startup is not purely read-only against the database.

## Configuration Notes

- `CORS_ORIGINS` is a comma-separated string that defaults to `http://localhost:3000`.
- `ENABLE_TRIGGER_MONITOR` defaults to `True` and should be turned off when you want a quiet local environment.
- `SECRET_KEY` must be set explicitly outside prototype work.
- `GEMINI_API_KEY` is optional and only affects explanatory text endpoints.
- Root `.env.example` summarizes local defaults; `backend/.env.example` and `frontend/.env.example` are the service-specific samples.

## Persistence Notes

- PostgreSQL data persists in the named `postgres_data` volume.
- Local SQLite runs create `backend/rideguard.db` plus `-wal` and `-shm` sidecar files.
- Test runs create SQLite database files under `backend/tests/`.

## Observability In The Current App

- FastAPI exposes a simple health payload at `/`.
- Trigger-monitor messages are written through the `trigger_monitor` logger.
- Celery worker output is written to the worker container logs.
- Important underwriting and payout events are stored in the `audit_logs` table.
- There is no dedicated metrics endpoint, tracing system, or centralized log pipeline in the current repo.

## Operational Caveats

- The trigger monitor runs in the API process and queues work to Celery, so scheduling is still tied to API process lifetime.
- Database initialization depends on a bootstrap SQL file rather than a formal migration workflow.
- Access tokens are bearer tokens stored in the browser, not secure HTTP-only cookies.
- `/mock/*` endpoints are open and should not exist unchanged in a production deployment.
- The frontend image bakes `NEXT_PUBLIC_API_URL` at build time, so changing the browser-facing API URL requires rebuilding the frontend image.

## Production Hardening Checklist

- Replace mock providers with real service integrations behind clear interfaces.
- Move trigger monitoring into a separate worker or scheduler.
- Adopt a real migration process and remove SQLite runtime schema patching from the main app path.
- Put the frontend, backend, and database behind environment-specific configuration and secret management.
- Add reverse proxy, TLS termination, structured logging, metrics, and alerts.
