# Testing

RideGuard currently has backend automated coverage and no frontend automated test suite.

## Current Automated Coverage

The main automated test file is `backend/tests/test_api.py`.

It covers:

- root health handler and mock external handlers
- rider registration, duplicate protection, login, and authorization checks
- policy listing, premium calculation, policy creation, trigger processing, claim generation, and payout processing
- admin-only checks and the LLM explanation handlers

This test file calls route handlers directly rather than driving the app through HTTP requests, so it validates business behavior but does not fully exercise middleware, CORS, or generated OpenAPI contracts.

## Test Environment Behavior

The backend test suite overrides runtime settings before importing the app:

- `DATABASE_URL` points to a SQLite file under `backend/tests/`
- `SECRET_KEY` is set to a test-only value
- `ACCESS_TOKEN_EXPIRE_MINUTES` is shortened for tests
- `ENABLE_TRIGGER_MONITOR` is disabled

Each test run recreates the SQLite database, calls the runtime schema compatibility logic, and reseeds coverage modules and demo users.

## Commands To Run

### Backend tests

From `backend/`:

```bash
.venv/bin/python -m unittest tests.test_api
```

### Frontend lint

From `frontend/`:

```bash
npm run lint
```

## Manual Smoke Checklist

Use this after UI or business-rule changes:

1. Log in as the seeded rider and verify `/dashboard` loads.
2. Create a policy if the rider has none.
3. Simulate a rain trigger from the dashboard.
4. Confirm a claim appears in `/claims`.
5. Confirm a payout appears in `/payout` when URTS permits it.
6. Log in as the seeded admin and confirm `/admin` reflects the new activity.

## Current Gaps

- No frontend unit tests.
- No browser end-to-end tests.
- No dedicated tests for startup seeding and lifecycle behavior through FastAPI's lifespan.
- No automated validation of markdown docs or README links.
- No production-like integration test path for Docker Compose startup.

## Recommended Next Testing Steps

- Add HTTP-level backend tests using FastAPI's test client.
- Add a small frontend test suite for auth redirects and page-state transitions.
- Add one end-to-end happy-path test for registration, policy creation, trigger simulation, and payout visibility.
- Add CI checks for backend tests, frontend lint, and docs link validation.
