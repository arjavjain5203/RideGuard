# Backend API

This document summarizes the current FastAPI surface exposed by RideGuard.

## Base URLs

- Health endpoint: `/`
- Main API prefix: `/api`
- Mock data endpoints: `/mock`
- OpenAPI docs: `/docs`

## Authentication Model

- Most `/api/*` routes require `Authorization: Bearer <access_token>`.
- Tokens are issued by `POST /api/auth/login`.
- Tokens contain `sub`, `role`, `iss`, `iat`, and `exp` claims.
- The backend signs tokens with `SECRET_KEY` using HMAC SHA-256.
- Rider-scoped routes enforce `rider_id == current_user.id` unless the caller is an admin.

## Health And Mock Endpoints

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/` | none | API health payload |
| `GET` | `/mock/weather?zone=Koramangala` | none | mock temperature and rainfall snapshot |
| `GET` | `/mock/aqi?zone=Koramangala` | none | mock AQI snapshot |
| `GET` | `/mock/traffic?zone=Koramangala` | none | mock traffic-speed snapshot |
| `POST` | `/mock/set-extreme?zone=Koramangala&event_type=rain` | none | force the mock state for demo testing |

`event_type` for `/mock/set-extreme` supports `rain`, `flood`, `heat`, and `aqi`.

## Auth Endpoints

| Method | Path | Auth | Request | Response |
| --- | --- | --- | --- | --- |
| `POST` | `/api/auth/login` | none | `login_id`, `password` | bearer token plus current user profile |
| `GET` | `/api/auth/me` | bearer | none | current user profile |

Notes:

- `login_id` is normalized to lowercase in schema validation.
- Invalid credentials return `401`.

## Rider And Earnings Endpoints

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `POST` | `/api/riders/` | none | register a new rider and seed earnings/trust state |
| `GET` | `/api/riders/{rider_id}` | bearer | fetch one rider profile |
| `GET` | `/api/riders/{rider_id}/score` | bearer | fetch the rider's current base URTS and last trust-log event |
| `GET` | `/api/zomato/earnings/{rider_id}` | bearer | fetch summarized earnings plus a synthetic four-week breakdown |

`POST /api/riders/` expects:

```json
{
  "login_id": "rider@example.com",
  "password": "RiderPass123",
  "zomato_partner_id": "ZMT-BLR-001",
  "name": "Rider Example",
  "phone": "9876543210",
  "zone": "Koramangala",
  "upi_handle": "rider@ybl"
}
```

Validation highlights:

- password must be at least 8 characters and contain letters and numbers
- phone must be exactly 10 digits
- zone must map to a configured zone multiplier
- login ID and UPI handle are normalized

## Policy Endpoints

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/api/policies/modules` | bearer | list seeded coverage modules |
| `POST` | `/api/policies/calculate-premium` | bearer | compute weekly premium for a rider and module set |
| `POST` | `/api/policies/` | bearer | create one active policy for a rider |
| `GET` | `/api/policies/rider/{rider_id}` | bearer | list the rider's policies |

Premium and policy creation requests both use:

```json
{
  "rider_id": "uuid",
  "modules": ["rain", "aqi"]
}
```

Backend behavior:

- module names are normalized and deduplicated
- unsupported modules return `400`
- existing active policy returns `409` on create
- risk score is calculated from live mock zone conditions at request time

## Trigger Endpoints

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `POST` | `/api/triggers/check` | bearer | evaluate trigger conditions for a zone and create claims/payouts when applicable |

Request body:

```json
{
  "zone": "Koramangala",
  "rainfall_mm_hr": 18.0,
  "temperature_c": 30.0,
  "aqi": 90.0,
  "traffic_speed_kmh": 18.0
}
```

Important rules:

- riders may only evaluate triggers for their own zone
- admins may evaluate any zone
- if any numeric field is greater than zero, the request is treated as a simulation
- simulation mode backdates trigger start time so a single request can create mature claims immediately

Response fields:

- `zone`
- `triggers_fired`
- `claims_created`
- `payouts_created`
- `message`

## Claim Endpoints

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/api/claims/rider/{rider_id}` | bearer | list claims for one rider |
| `GET` | `/api/claims/{claim_id}` | bearer | fetch one claim with payout details when present |

Claim responses include:

- trigger metadata
- disruption times and hours
- loss amount
- effective URTS
- behavioral risk signals
- payout amount and payout status when a payout exists

## Payout Endpoints

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `POST` | `/api/payouts/process` | bearer | manually process a pending claim into a payout |
| `GET` | `/api/payouts/claim/{claim_id}` | bearer | fetch one claim payload through the payouts router |
| `GET` | `/api/payouts/rider/{rider_id}` | bearer | list payouts for one rider |

`POST /api/payouts/process` expects:

```json
{
  "claim_id": "uuid"
}
```

Manual payout processing returns:

- `404` when the claim does not exist
- `409` if the claim is already paid or already capped with a payout record
- `400` if the claim was rejected or effective URTS blocks payment
- `201` with a payout payload on success

## Admin Endpoints

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/api/admin/metrics` | admin | portfolio summary metrics |
| `GET` | `/api/admin/claims` | admin | recent claims feed |
| `GET` | `/api/admin/fraud-alerts` | admin | recent low-URTS claim feed |

The admin dashboard is read-only in the current codebase.

## LLM Endpoints

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `POST` | `/api/llm/explain-claim` | bearer | explain a claim outcome in one sentence |
| `POST` | `/api/llm/explain-risk` | bearer | explain a zone risk score |
| `POST` | `/api/llm/explain-fraud` | bearer | explain a score penalty |
| `POST` | `/api/llm/generate-insights` | admin | generate one admin insight string |

Example request bodies:

```json
{
  "trigger": "rain",
  "hours": 2,
  "payout": 320,
  "urts": 85
}
```

```json
{
  "zone": "Koramangala",
  "risk_score": 0.76
}
```

```json
{
  "signals": {"gps_anomaly": 0.8},
  "penalty": 20
}
```

```json
{
  "zone_data": "Koramangala rainfall elevated"
}
```

## Current API Caveats

- The trigger monitor and trigger simulation both call the same route handler, so route logic doubles as background-job logic.
- Some endpoints return ORM objects directly, while others build response payloads manually.
- The payout router has a claim-detail endpoint that overlaps conceptually with the claims router.
- `/mock/*` routes are open and intended for prototype and demo use only.
