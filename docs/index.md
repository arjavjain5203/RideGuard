# RideGuard Documentation

This folder is the engineering-first documentation set for the current RideGuard codebase. The root `README.md` remains the product and demo narrative; this directory documents how the project is actually wired today.

## Start Here

- [Project Overview](./project-overview.md): product scope, user roles, implemented flows, and current prototype boundaries.
- [Setup and Running](./setup-and-running.md): local development paths, environment variables, ports, and demo accounts.
- [Architecture](./architecture.md): system structure, lifecycle, request flows, and background processing.
- [Backend API](./backend-api.md): route inventory, auth model, and request/response expectations.
- [Data Model](./data-model.md): database tables, relationships, and schema ownership.
- [Frontend](./frontend.md): route map, UI responsibilities, and browser-side session behavior.
- [Business Rules](./business-rules.md): pricing, triggers, URTS, fraud checks, and payout logic.
- [Testing](./testing.md): automated coverage, commands, and known gaps.
- [Deployment and Ops](./deployment-and-ops.md): Docker, runtime behavior, and operational caveats.
- [Roadmap](./roadmap.md): prioritized project plan from prototype hardening to production readiness.

## System Snapshot

| Area | Current implementation |
| --- | --- |
| Frontend | Next.js 16 App Router, React 19, Tailwind CSS 4, Axios |
| Backend | FastAPI, SQLAlchemy, custom JWT implementation, optional background trigger loop |
| Database | PostgreSQL 15 in Docker Compose, SQLite used locally and in tests |
| External data | Mock weather, AQI, and traffic feeds via in-process helpers and `/mock/*` endpoints |
| AI integration | Optional Gemini-backed explanation endpoints with mock fallback |
| Core flows | Rider registration, login, earnings sync, policy creation, trigger simulation, claims, payouts, admin metrics |

## Source of Truth

- Runtime configuration lives in `backend/app/config.py`.
- Backend lifecycle and seeding live in `backend/app/main.py`.
- API routes live in `backend/app/routers/`.
- Business logic lives in `backend/app/services/`.
- Database schema starts in `db/migrations/001_init.sql`.
- SQLAlchemy models live in `backend/app/models.py`.
- Frontend pages live in `frontend/src/app/`.

## Repo Map

- `frontend/`: Next.js user interface and browser-side auth/session handling.
- `backend/`: FastAPI app, models, services, Dockerfile, and backend tests.
- `db/`: checked-in PostgreSQL bootstrap SQL.
- `docs/`: code-accurate project documentation.
- `README.md`: product overview and demo story.

## Known Drift From Older Docs

- The root README mentions technologies such as Node/Express, Celery, Redis, Recharts, Leaflet, Prometheus, and Grafana. Those are not present in the current codebase.
- `frontend/README.md` is still the default Create Next App template and does not describe the project.
- `.env.example` contains future-facing keys that do not fully match the backend settings currently read by the app.
- The current system uses mock environmental data and simulated payouts, not live provider integrations.
