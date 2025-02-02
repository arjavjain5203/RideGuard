# Project Overview

RideGuard is a prototype parametric micro-insurance platform for food delivery riders. The current implementation focuses on a rider-facing web flow, an admin dashboard, mock trigger data, automatic claim generation, and simulated payout processing.

## What The Current App Does

RideGuard currently supports two user roles:

| Role | What they can do |
| --- | --- |
| Rider | Register, log in, view earnings and URTS, select coverage modules, simulate trigger events for their own zone, review claims, review payouts |
| Admin | Log in, view portfolio metrics, recent claims, and fraud-alert style low-URTS claims |

The implemented rider journey is:

1. Register with login credentials, partner ID, zone, and UPI handle.
2. Receive seeded earnings data and an initial trust score.
3. Log in and fetch the rider profile through bearer-token auth.
4. Review a synced earnings summary on the onboarding page.
5. Select coverage modules and create a single active policy.
6. Simulate or monitor trigger conditions for the rider's zone.
7. Generate claims automatically when a trigger ends after the required duration.
8. Process payouts automatically when effective URTS and payout caps allow it.

## Current Capabilities

### Policy and pricing

- Coverage modules are seeded into the database at startup.
- Premiums are computed from module base price, zone multiplier, live mock risk score, and rider activity level.
- The backend currently allows one active policy per rider.

### Trigger detection and claims

- Environmental inputs come from mock weather, AQI, and traffic providers.
- Trigger checks can be driven by a background loop or by explicit simulation requests.
- Claims are created automatically for riders with active matching coverage.
- Audit log rows are written for trigger and payout events.

### Fraud and payouts

- A single Behavioral Risk and Fraud pipeline computes a signal vector and event adjustment.
- Effective URTS drives payout eligibility and payout factor.
- Payouts are simulated as database records with synthetic UPI transaction IDs.
- Successful paid claims add a small positive URTS adjustment.

### Admin and AI features

- Admin metrics summarize active policies, premiums, payouts, loss ratio, and average rider URTS.
- Admin claims and fraud-alert feeds are read-only in the current UI.
- LLM endpoints generate short claim, risk, fraud, and admin explanations.
- If `GEMINI_API_KEY` is missing or the Gemini SDK is unavailable, the LLM service returns mock text.

## Current Prototype Boundaries

- External weather, AQI, and traffic integrations are mocked.
- Payouts are simulated writes to the `payouts` table, not real bank or UPI transfers.
- There is no real billing, premium collection, or policy renewal scheduler.
- The background trigger monitor runs inside the API process and queues heavier work through Celery.
- The frontend stores the access token in `localStorage`.
- Frontend route protection is client-side only; backend authorization is still enforced server-side.
- Backend automated tests exist, but there are no frontend automated tests.

## Important Mismatches To Know

- The root README describes a broader and more ambitious platform than the current code implements.
- Env samples are split between the root overview and service-specific backend/frontend examples.
- The backend supports more configured zones than the registration UI currently exposes.
- The database schema uses a unified `users` table for riders and admins; older docs refer to a separate `riders` table.

## Actual Stack In Use

| Layer | Current implementation |
| --- | --- |
| Frontend | Next.js 16, React 19, Tailwind CSS 4, Axios |
| Backend | FastAPI 0.115, SQLAlchemy 2, Pydantic 2 |
| Data store | PostgreSQL 15 or SQLite, with Redis for cache, locks, and Celery |
| Auth | Custom PBKDF2 password hashing plus HMAC-signed JWT-style bearer tokens |
| Runtime | Docker Compose for `postgres`, `redis`, `backend`, `worker`, and `frontend`, with optional local frontend dev server |
