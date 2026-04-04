# Business Rules

This document centralizes the main pricing, trigger, fraud, URTS, and payout rules implemented in the current backend.

## Zone Multipliers

Configured in `backend/app/config.py`:

| Zone | Multiplier |
| --- | --- |
| `koramangala` | `1.15` |
| `indiranagar` | `1.10` |
| `hsr_layout` | `1.12` |
| `whitefield` | `1.05` |
| `jayanagar` | `1.08` |
| `btm_layout` | `1.10` |
| `electronic_city` | `1.03` |
| `marathahalli` | `1.07` |
| `default` | `1.00` |

The backend accepts all of these zones. The current registration UI exposes only a subset.

## Coverage Modules

Seeded in `backend/app/main.py` and persisted in `coverage_modules`:

| Module | Base price | Trigger threshold | Required duration |
| --- | --- | --- | --- |
| `rain` | `25.00` | rainfall `>= 15 mm/hr` | `2.0` hours |
| `flood` | `20.00` | rainfall `>= 60 mm` or traffic `< 5 km/h` | `6.0` hours |
| `heat` | `15.00` | temperature `>= 42 C` | `0.0` hours |
| `aqi` | `18.00` | AQI `>= 300` | `3.0` hours |

## Risk Score Rules

Zone risk is calculated from live mock environmental conditions using:

```text
risk_score = 0.35 * rain + 0.25 * temp + 0.25 * aqi + 0.15 * traffic
```

Normalization rules:

- rainfall: `min(mm_hr / 25.0, 1.0)`
- temperature: `0` at `<= 30 C`, then linear to `1.0` at `45 C`
- AQI: `0` at `<= 50`, then linear to `1.0` at `400`
- traffic: `0` at `>= 40 km/h`, `1.0` at `<= 5 km/h`

## Premium Rules

Premium calculation happens in `premium_calculator.py`.

Per-module price:

```text
module_price = base_price * zone_multiplier * premium_multiplier * activity_multiplier
```

Where:

- `zone_multiplier` comes from the rider's zone.
- `premium_multiplier` comes from the current risk score.
- `activity_multiplier` comes from `earnings.active_days`.

### Premium multiplier by risk score

| Condition | Multiplier |
| --- | --- |
| `risk_score > 0.7` | `1.30` |
| `risk_score < 0.3` | `0.85` |
| otherwise | `1.00` |

### Activity multiplier by active days

| Active days | Multiplier |
| --- | --- |
| `<= 2` | `0.0` |
| `<= 4` | `0.5` |
| `>= 5` | `1.0` |

The total weekly premium is the sum of all selected module prices.

## Trigger Evaluation Rules

Trigger processing happens in `backend/app/routers/triggers.py`.

### Conditions that currently fire

- `rain` when rainfall is `>= 15.0`
- `aqi` when AQI is `>= 300.0`
- `heat` when temperature is `>= 42.0`
- `flood` when rainfall is `>= 60.0` or traffic speed is `< 5.0`

### Who can evaluate what

- Riders can only evaluate their own zone.
- Admins can evaluate any zone.
- Admin-triggered checks can create claims for all active riders in that zone with matching active coverage.

### Simulation behavior

If any submitted trigger metric is greater than zero, the request is treated as a simulation.

In simulation mode, the backend:

- overrides the mock snapshot with the provided values
- backdates the new trigger's `start_time` by the required duration or `0.5` hours, whichever is greater
- ends the trigger in the same request so a claim can be created immediately

This is why the dashboard can create demo claims and payouts with a single request.

### Non-simulated behavior

In non-simulated mode, trigger records remain active until a later check finds the condition no longer true.

When a trigger ends:

- duration is calculated from `start_time` to `end_time`
- duration is clamped to the range `0.0` to `8.0` hours
- claims are only created if the duration meets the module requirement

## Fraud And URTS Rules

Fraud detection lives in `backend/app/services/fraud_detection.py`.

### Signal weights

| Signal | Weight |
| --- | --- |
| `gps_anomaly` | `0.30` |
| `cluster_detection` | `0.30` |
| `activity_mismatch` | `0.25` |
| `device_inconsistency` | `0.15` |

### Current checks

- zone mismatch between rider profile and trigger zone
- duplicate claim window for the same rider and trigger type within six hours
- claim cluster anomaly when more than five claims of the same trigger type occur in the same zone within two hours
- rider inactivity
- high recent claim frequency when the rider has at least three claims in seven days

### Effective URTS

```text
effective_urts = clamp(base_urts + event_adjustment, 0, 100)
```

`event_adjustment` is always zero or negative and is scaled to a maximum penalty of `-50`.

### Payout factor mapping

| Effective URTS | Payout factor |
| --- | --- |
| `>= 80` | `1.0` |
| `>= 60` | `0.9` |
| `>= 40` | `0.7` |
| `< 40` | `0.0` |

An effective URTS below `40` rejects the claim for payment.

## Loss And Payout Rules

### Income loss

```text
loss_amount = hourly_income * disruption_hours
```

Hourly income comes from the rider's earnings row when available, otherwise the user's cached hourly income.

### Requested payout

```text
requested_amount = loss_amount * urts_factor
```

### Cap logic

Payout caps are calculated against historical payouts for the same user:

- weekly cap: `2.0 * weekly_premium`
- monthly cap: `6.0 * (weekly_premium * 4.0)`

The backend subtracts prior payout totals from the last 7 and 30 days and pays the minimum available amount.

### Claim and payout status outcomes

| Outcome | Claim status | Payout row |
| --- | --- | --- |
| effective URTS below threshold | `rejected` | none |
| payout amount greater than zero | `paid` | `completed` |
| payout allowed but fully capped to zero | `capped` | `capped` |

Successful paid payouts also:

- increase the rider's `base_urts` by `2`, capped at `100`
- create a `trust_logs` row recording the positive adjustment

## LLM Rules

The LLM endpoints are advisory only.

- They do not influence underwriting, trigger evaluation, or payout decisions.
- Without a live Gemini setup, the backend returns short mock responses prefixed with `[MOCK AI RESPONSE]`.
