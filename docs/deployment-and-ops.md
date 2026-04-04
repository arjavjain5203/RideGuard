# Deployment and Ops

This document describes the current runtime topology and operational caveats for the project as it exists today.

## Current Runtime Topology

| Component | How it runs today | Notes |
| --- | --- | --- |
| PostgreSQL | Docker Compose service `db` | initialized from `db/migrations/001_init.sql` on first boot |
| Backend API | Docker Compose service `backend` or local `uvicorn` | owns HTTP traffic, startup seeding, and optional trigger monitoring |
| Frontend | Docker Compose service `frontend` or local Next.js dev server | served on port `3000`, defaults to `NEXT_PUBLIC_API_URL=http://localhost:8000/api` |

## Docker Compose Details

The checked-in `docker-compose.yml` defines three services.

### `db`

- image: `postgres:15`
- port: `5432:5432`
- database: `rideguard`
- user/password: `rideguard` / `rideguard`
- volume: named volume `pgdata`
- init script: mounts `db/migrations/001_init.sql` into `/docker-entrypoint-initdb.d/`

### `backend`

- built from `backend/Dockerfile`
- port: `8000:8000`
- environment override: `DATABASE_URL=postgresql://rideguard:rideguard@db:5432/rideguard`
- additional env: `CORS_ORIGINS`, `SECRET_KEY`, `TOKEN_ISSUER`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `ENABLE_TRIGGER_MONITOR`
- startup command from Dockerfile: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- healthcheck: HTTP probe against `http://127.0.0.1:8000/`

### `frontend`

- built from `frontend/Dockerfile`
- port: `3000:3000`
- Next.js standalone runtime image
- build arg and runtime env: `NEXT_PUBLIC_API_URL=http://localhost:8000/api`
- depends on a healthy `backend` service

## Startup Side Effects To Expect

Every backend startup currently does the following:

- creates ORM tables if they do not exist
- runs SQLite compatibility updates when using SQLite
- seeds coverage modules and zones if missing
- seeds the demo rider and demo admin if missing
- may start the background trigger monitor loop

Operationally, that means application startup is not purely read-only against the database.

## Configuration Notes

- `CORS_ORIGINS` is a comma-separated string that defaults to `http://localhost:3000`.
- `ENABLE_TRIGGER_MONITOR` defaults to `True` and should be turned off when you want a quiet local environment.
- `SECRET_KEY` must be set explicitly outside prototype work.
- `GEMINI_API_KEY` is optional and only affects explanatory text endpoints.

## Persistence Notes

- PostgreSQL data persists in the named `pgdata` volume.
- Local SQLite runs create `backend/rideguard.db` plus `-wal` and `-shm` sidecar files.
- Test runs create SQLite database files under `backend/tests/`.

## Observability In The Current App

- FastAPI exposes a simple health payload at `/`.
- Trigger-monitor messages are written through the `trigger_monitor` logger.
- Important underwriting and payout events are stored in the `audit_logs` table.
- There is no dedicated metrics endpoint, tracing system, or centralized log pipeline in the current repo.

## Operational Caveats

- The trigger monitor runs in the same process as the API server, so there is no worker isolation.
- Database initialization depends on a bootstrap SQL file rather than a formal migration workflow.
- The root `.env.example` is not fully aligned with the current runtime settings.
- Access tokens are bearer tokens stored in the browser, not secure HTTP-only cookies.
- `/mock/*` endpoints are open and should not exist unchanged in a production deployment.
- The frontend image bakes `NEXT_PUBLIC_API_URL` at build time, so changing the browser-facing API URL requires rebuilding the frontend image.

## Production Hardening Checklist

- Replace mock providers with real service integrations behind clear interfaces.
- Move trigger monitoring into a separate worker or scheduler.
- Adopt a real migration process and remove SQLite runtime schema patching from the main app path.
- Put the frontend, backend, and database behind environment-specific configuration and secret management.
- Add reverse proxy, TLS termination, structured logging, metrics, and alerts.
