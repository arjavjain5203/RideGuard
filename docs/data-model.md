# Data Model

The current schema is split between a checked-in PostgreSQL bootstrap script and SQLAlchemy models.

## Schema Ownership

- Primary schema source of truth: `db/migrations/001_init.sql`
- ORM representation: `backend/app/models.py`
- SQLite compatibility and backfill logic: `backend/app/main.py` in `ensure_runtime_schema()`

For PostgreSQL-style deployments, treat the SQL migration as authoritative. The SQLite path is a compatibility layer for local development and tests.

## Relationship Overview

```text
users 1---1 earnings
users 1---* policies
users 1---* claims
users 1---* payouts
users 1---* trust_logs

policies 1---* claims
triggers 1---* claims
claims 1---0..1 payouts

zones and coverage_modules are seeded reference tables
audit_logs record generic entity events
```

## Table Summary

| Table | Purpose | Key fields | Notes |
| --- | --- | --- | --- |
| `users` | unified account table for riders and admins | `id`, `login_id`, `password_hash`, `role`, `zomato_partner_id`, `zone`, `hourly_income`, `is_active`, `base_urts` | older local rows may be backfilled at runtime |
| `earnings` | rider income profile used by onboarding and payout calculations | `user_id`, `weekly_earnings`, `hours_worked`, `active_days` | one logical row per rider in the current app |
| `coverage_modules` | reference data for selectable coverage | `name`, `display_name`, `base_price`, `trigger_type`, `trigger_threshold`, `trigger_duration_hours` | seeded at startup |
| `zones` | zone-level pricing multipliers | `name`, `risk_multiplier`, `geo_bounds` | `geo_bounds` is currently unused |
| `policies` | rider coverage selections and premium state | `user_id`, `coverage_types`, `weekly_premium`, `zone_multiplier`, `risk_score`, `status`, `valid_from`, `valid_until` | `coverage_types` is stored as JSON text |
| `triggers` | environmental trigger records | `type`, `value`, `zone`, `status`, `start_time`, `end_time`, `duration_hours` | one row per observed trigger event |
| `claims` | auto-generated or manually processed claim records | `policy_id`, `user_id`, `trigger_id`, `loss_amount`, `effective_urts`, `behavioral_signals`, `status` | `behavioral_signals` is JSON text |
| `payouts` | simulated payout records | `claim_id`, `user_id`, `amount`, `urts_factor`, `transaction_id`, `status`, `paid_at` | `transaction_id` is surfaced as `upi_transaction_id` in API responses |
| `trust_logs` | URTS change history | `user_id`, `change`, `reason`, `created_at` | used by rider score views |
| `audit_logs` | generic audit trail for trigger, claim, and payout events | `entity_type`, `entity_id`, `action`, `details`, `timestamp` | `details` is JSON text |

## Entity Notes

### Users

- Riders and admins share the same table.
- `role` is constrained to `rider` or `admin`.
- `login_id` is the credential used by the current auth flow.
- `base_urts` is the rider's persistent trust baseline.
- `is_active` is used by fraud checks and zone-wide trigger processing.

### Earnings

- The UI treats earnings as a synced partner profile.
- The current backend generates random weekly earnings for newly registered riders.
- `hourly_income` is denormalized onto `users` and backfilled from earnings when possible.

### Coverage Modules

The default seeded modules are:

| Name | Base price | Threshold | Duration hours |
| --- | --- | --- | --- |
| `rain` | `25.00` | `15.0 mm/hr` | `2.0` |
| `flood` | `20.00` | `60.0 mm rainfall` or traffic below `5 km/h` | `6.0` |
| `heat` | `15.00` | `42.0 C` | `0.0` |
| `aqi` | `18.00` | `300 AQI` | `3.0` |

### Policies

- `coverage_types` is stored as a JSON string rather than a normalized join table.
- `status` allows `active`, `paused`, and `cancelled`, but the current UI and backend mostly operate on `active`.
- `valid_until` defaults to seven days after creation.

### Triggers

- Trigger rows move through `ACTIVE`, `ONGOING`, and `ENDED`.
- `duration_hours` is computed when a trigger ends.
- A single trigger can fan out to multiple claims if an admin processes a zone with multiple covered riders.

### Claims

- `status` allows `pending`, `paid`, `rejected`, and `capped`.
- `policy_id` and `trigger_id` are nullable because legacy or manual flows may not attach both values.
- `effective_urts` is stored at claim time so payout decisions can be audited later.

### Payouts

- `status` allows `pending`, `completed`, `failed`, and `capped` in the SQL schema.
- The current application code mainly writes `completed` and `capped` rows.
- Payout caps are calculated from prior payout history using `created_at` windows.

### Trust Logs And Audit Logs

- `trust_logs` record business-facing URTS changes.
- `audit_logs` record system events such as trigger creation, trigger end, claim rejection, and payout processing.
- There is no dedicated admin UI for browsing audit logs yet.

## SQLite Compatibility Notes

When `DATABASE_URL` points to SQLite, the backend also:

- enables WAL mode
- adds missing columns to older local databases
- backfills login IDs, hourly income, policy defaults, claim trigger metadata, and payout timestamps

This is helpful for local continuity, but it is not a substitute for a disciplined migration pipeline.

## Indexes And Constraints

The bootstrap SQL creates indexes on key relationship and lookup columns, including:

- `users.role`
- `earnings.user_id`
- `policies.user_id`
- `claims.user_id`, `claims.policy_id`, `claims.trigger_id`
- `payouts.user_id`, `payouts.claim_id`
- `trust_logs.user_id`
- `triggers.zone`

There are also important uniqueness constraints on:

- `users.login_id`
- `users.zomato_partner_id`
- `coverage_modules.name`
- `zones.name`
- `payouts.transaction_id`
