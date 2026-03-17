<p align="center">
  <img src="https://img.shields.io/badge/RideGuard-AI%20Parametric%20Insurance-blueviolet?style=for-the-badge&logo=shield&logoColor=white" alt="RideGuard Badge"/>
</p>

<h1 align="center">🛡️ RideGuard</h1>
<p align="center"><b>AI-Powered Parametric Insurance for Gig Economy Workers</b></p>

<p align="center">
  <img src="https://img.shields.io/badge/Built%20For-Zomato%20Delivery%20Partners-E23744?style=flat-square" alt="Zomato"/>
  <img src="https://img.shields.io/badge/Location-Bangalore-blue?style=flat-square" alt="Bangalore"/>
  <img src="https://img.shields.io/badge/Insurance-Parametric-green?style=flat-square" alt="Parametric"/>
  <img src="https://img.shields.io/badge/Payouts-Instant%20UPI-orange?style=flat-square" alt="UPI"/>
  <img src="https://img.shields.io/badge/Status-Hackathon%20Prototype-yellow?style=flat-square" alt="Status"/>
</p>

---

## Table of Contents

- [Problem Statement](#problem-statement)
- [What is RideGuard?](#what-is-rideguard)
- [How It Works](#how-it-works)
- [Parametric Triggers](#parametric-triggers)
- [AI & ML Components](#ai--ml-components)
- [Trust Score System](#trust-score-system)
- [Payout Model](#payout-model)
- [Activity-Based Premium](#activity-based-premium)
- [System Architecture](#system-architecture)
- [Database Design](#database-design)
- [Admin Dashboard](#admin-dashboard)
- [Example Calculation](#example-calculation)
- [Key Innovations](#key-innovations)
- [Why This Matters](#why-this-matters)
- [Development Roadmap](#development-roadmap)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [License](#license)

---

## Problem Statement

India has **7.7 million gig workers** (NITI Aayog, 2022), with food delivery riders accounting for the largest share. These workers face a critical gap:

- **No income protection** during environmental disruptions — heavy rain, extreme heat, floods, hazardous air quality.
- **Traditional insurance** requires manual claims, lengthy processing, and documentation they rarely have.
- A single day of heavy rain in Bangalore can wipe out **₹800–₹1500** of a rider's daily earnings.

**There is no insurance product in India designed for the gig economy's unique rhythm: daily work, hourly income, real-time risk.**

---

## What is RideGuard?

RideGuard is a **parametric micro-insurance platform** purpose-built for Zomato delivery partners operating in Bangalore.

Instead of "file a claim and wait," RideGuard works on a simple principle:

> **If a pre-defined environmental trigger is met → payout is automatic. No claim. No paperwork. No delay.**

The platform continuously monitors weather, air quality, and traffic conditions. When disruption thresholds are breached, lost income is calculated and disbursed instantly via UPI — all within minutes, not weeks.

### Target User Profile

| Attribute | Detail |
|---|---|
| **User** | Full-time Zomato delivery partner |
| **Location** | Bangalore (multi-zone) |
| **Weekly Income** | ₹7,000 – ₹10,000 |
| **Work Pattern** | 5–7 active days/week |
| **Income Source** | Zomato Driver API (simulated) |
| **Payment Method** | UPI-linked bank account |

---

## How It Works

RideGuard operates as a fully automated insurance pipeline — from registration to payout — with zero manual intervention required from the rider.

<p align="center">
  <img src="./diagram-export-17-03-2026-22_07_55.png" alt="RideGuard System Workflow" width="100%"/>
</p>

### Step-by-Step Workflow

**Step 1 — Registration**
Rider registers via the web dashboard with their Zomato partner ID, zone, and UPI handle.

**Step 2 — Income Fetch**
System calls the simulated Zomato Driver API to retrieve the rider's recent earnings history (last 4 weeks).

**Step 3 — Hourly Income Calculation**
Average hourly income is derived:

```
hourly_income = total_earnings / total_active_hours
```

**Step 4 — Coverage Selection**
Rider selects one or more coverage modules:

| Module | What It Covers |
|---|---|
| ☔ Rain Shield | Heavy rainfall disruption |
| 🌊 Flood Guard | Waterlogged roads & flooding |
| 🌡️ Heat Cover | Extreme temperature conditions |
| 💨 AQI Protect | Hazardous air quality |

**Step 5 — Premium Calculation**

```
Weekly Premium = Σ (Module Base Price × Zone Multiplier × AI Risk Score)
```

Premiums are designed to be **micro-payments** (₹15–₹60/week per module) — affordable within a gig worker's budget.

**Step 6 — Environmental Monitoring**
The backend continuously polls:
- **OpenWeatherMap API** → rainfall, temperature
- **AQICN API** → real-time AQI data
- **Google Maps / TomTom API** → traffic speed and congestion

Polling frequency: **every 15 minutes** per active zone.

**Step 7 — Trigger Detection**
When a parametric threshold is breached (see [Parametric Triggers](#parametric-triggers)), the system logs a disruption event, begins measuring duration, and flags the affected zone.

**Step 8 — Fraud Detection & Trust Scoring**
Before payout, the Fraud Detection Engine runs checks:
- **GPS validation** — Is the rider's registered zone consistent with the disruption zone?
- **Duplicate claim detection** — Has a payout already been issued for this event window?
- **Weather cross-validation** — Do multiple data sources confirm the disruption?

The rider's **trust score** determines the payout percentage (see [Trust Score System](#trust-score-system)).

**Step 9 — Instant Payout**

```
Payout = hourly_income × disruption_hours × trust_multiplier
```

Disbursed via simulated UPI to the rider's linked account. The rider receives a notification with a payout breakdown.

**Step 10 — Audit Trail**
Every event — trigger detection, fraud check result, payout — is logged immutably for regulatory compliance and dispute resolution.

---

## Parametric Triggers

Parametric insurance eliminates subjective claim assessment. Payouts are governed by **objective, measurable environmental thresholds** that are pre-defined and non-negotiable.

| Trigger | Threshold | Sustained Duration | Rationale |
|---|---|---|---|
| ☔ **Heavy Rain** | ≥ 15 mm/hour | 2 consecutive hours | IMD classifies ≥15 mm/hr as "heavy rainfall." Bangalore's unplanned drainage makes roads unrideable at this level. 2-hour minimum filters out brief showers. |
| 🌊 **Flood** | ≥ 60 mm in 6 hours **OR** traffic speed < 5 km/h | 6 hours (rainfall) / real-time (traffic) | 60 mm/6hr exceeds Bangalore's storm-drain capacity in most zones. Traffic speed < 5 km/h indicates roads are practically impassable. Either condition independently qualifies. |
| 🌡️ **Extreme Heat** | ≥ 42°C | Instantaneous | India's National Disaster Management Authority classifies ≥42°C as "severe heat wave." Prolonged outdoor exposure at this level is a medical risk. No duration requirement — immediate trigger. |
| 💨 **Hazardous AQI** | ≥ 300 (AQI scale) | 3 consecutive hours | AQI ≥ 300 = "Hazardous" (EPA standard). Continuous outdoor activity causes respiratory harm. 3-hour minimum ensures it's a sustained event, not a transient spike from a local source. |

### Why These Specific Thresholds?

- **Calibrated to Bangalore**: Thresholds are tuned to Bangalore's geography — its urban heat island effect, monsoon drainage limitations, and traffic congestion patterns.
- **Based on authoritative standards**: IMD rainfall classification, NDMA heat wave guidelines, EPA AQI categories.
- **Duration filters reduce false positives**: Sustained-duration requirements ensure payouts are triggered by genuine disruptions, not momentary fluctuations.
- **Compound triggers for floods**: Rainfall alone doesn't capture urban flooding — traffic speed acts as a ground-truth proxy for road accessibility.

---

## AI & ML Components

### 1. Risk Scoring Model

Each rider's zone is assigned a dynamic **risk score** that reflects current environmental conditions. The model uses a weighted linear combination:

```
Risk Score = 0.35 × R_rain + 0.25 × R_temp + 0.25 × R_aqi + 0.15 × R_traffic
```

| Factor | Weight | Source | Normalization |
|---|---|---|---|
| Rainfall intensity | 0.35 | Weather API | 0–1 scale, 0 = dry, 1 = ≥25 mm/hr |
| Temperature | 0.25 | Weather API | 0–1 scale, 0 = ≤30°C, 1 = ≥45°C |
| AQI | 0.25 | AQI API | 0–1 scale, 0 = ≤50, 1 = ≥400 |
| Traffic congestion | 0.15 | Traffic API | 0–1 scale, 0 = free flow, 1 = gridlock |

**Weight rationale**: Rainfall is weighted highest because it is the most frequent and impactful disruption for Bangalore riders. Temperature and AQI are equally weighted as secondary risks. Traffic carries the lowest independent weight since it often correlates with rainfall.

### 2. Dynamic Premium Adjustment

The risk score directly modulates the weekly premium:

```python
if risk_score > 0.7:
    premium_multiplier = 1.3   # High-risk zone surcharge
elif risk_score < 0.3:
    premium_multiplier = 0.85  # Low-risk zone discount
else:
    premium_multiplier = 1.0   # Standard rate
```

This creates a **fair pricing model** — riders in historically safer zones pay less, incentivizing broad adoption.

### 3. Fraud Detection Engine

A two-layer approach:

**Layer 1 — Rule-Based Checks**
| Check | Logic |
|---|---|
| GPS mismatch | Rider's registered zone ≠ disruption zone |
| Duplicate claim | Same rider + same event window already paid |
| Weather mismatch | Rider's zone data doesn't match the trigger conditions |
| Temporal anomaly | Claim timestamp falls outside rider's active hours |

**Layer 2 — Anomaly Detection**
Statistical outlier detection on claim frequency and patterns:
- Riders with claim rates >2σ above the zone mean are flagged for review.
- Payout amounts deviating significantly from zone averages trigger alerts.

Fraud flags **reduce the trust score** rather than blocking payouts outright — this avoids penalizing legitimate high-risk-zone riders.

---

## Trust Score System

Every rider has a dynamic trust score that determines their payout eligibility. This replaces binary "approved/denied" decisions with a gradient system that rewards honest behavior.

### Score Mechanics

| Event | Impact |
|---|---|
| Initial registration | Score = **75** |
| Valid claim paid | **+2 points** |
| No claims in a billing cycle (good standing) | **+1 point** |
| GPS mismatch detected | **−10 points** |
| Duplicate claim attempt | **−15 points** |
| Weather data inconsistency | **−8 points** |
| Flagged by anomaly detection | **−5 points** |
| Score cap | **0 – 100** |

### Payout Tiers

| Trust Score | Tier | Payout Multiplier | Behavior |
|---|---|---|---|
| **80 – 100** | ✅ Trusted | 100% of calculated payout | Full payout, no delay |
| **60 – 79** | ⚠️ Standard | 90% of calculated payout | Minor deduction, normal processing |
| **40 – 59** | 🔶 Under Review | 75% of calculated payout | Reduced payout, manual review optional |
| **< 40** | 🚫 Flagged | Payout **held** | Account flagged for investigation |

### Design Philosophy

- **Graduated penalties** prevent one-time errors from destroying a rider's coverage.
- **Positive reinforcement** (valid claims and good standing increase score) incentivizes honest participation.
- **No permanent blacklisting** — riders can recover their score through consistent legitimate behavior.

---

## Payout Model

RideGuard uses a **parametric payout model**, which is fundamentally different from traditional indemnity insurance.

### Parametric vs. Traditional

| Aspect | Traditional Insurance | RideGuard (Parametric) |
|---|---|---|
| Trigger | Manual claim filed by user | Automatic — environmental threshold breached |
| Assessment | Adjuster evaluates actual loss | None — payout is formula-based |
| Documentation | Photos, receipts, police reports | None required |
| Time to payout | Days to weeks | **Minutes** |
| Dispute potential | High | Low — thresholds are objective |

### Payout Formula

```
Payout = hourly_income × disruption_hours × trust_multiplier
```

Where:
- `hourly_income` = rider's calculated average hourly earnings from Zomato API data
- `disruption_hours` = measured duration of the trigger event (capped at 8 hours/event)
- `trust_multiplier` = percentage based on trust score tier (1.0, 0.9, 0.75, or 0.0)

### Payout Cap

- **Per-event cap**: 8 hours × hourly income
- **Weekly cap**: 2× weekly premium paid
- **Monthly cap**: 6× monthly premium paid

Caps prevent excessive exposure while ensuring meaningful coverage.

---

## Activity-Based Premium

RideGuard does not charge riders who aren't actively working. The premium adjusts based on actual activity:

| Active Days (per week) | Premium Charged | Rationale |
|---|---|---|
| **0 – 2 days** | **₹0** (no charge) | Rider is inactive — no risk exposure, no premium |
| **3 – 4 days** | **50%** of full premium | Part-time rider — reduced exposure |
| **5 – 7 days** | **100%** of full premium | Full-time rider — full coverage |

### Why Activity-Based?

- **Fairness**: Riders who take a week off shouldn't pay for coverage they can't use.
- **Affordability**: Reduces the financial barrier for part-time workers.
- **Fraud deterrence**: Only active riders are covered, limiting opportunistic claims.
- **Activity detection**: Based on Zomato API login/delivery data — not self-reported.

---

## Example Calculation

> **Scenario**: Rider Priya in Koramangala zone experiences heavy rain (18 mm/hr sustained for 3 hours) on a Tuesday afternoon.

### Rider Profile

| Field | Value |
|---|---|
| Rider | Priya |
| Zone | Koramangala |
| Weekly earnings | ₹8,400 |
| Active hours/week | 42 |
| Hourly income | ₹200/hr |
| Trust score | 82 (Trusted tier) |
| Active days this week | 6 |
| Subscribed modules | Rain Shield, Flood Guard |

### Premium Calculation

```
Rain Shield base price     = ₹25/week
Flood Guard base price     = ₹20/week
Zone multiplier (Koramangala) = 1.15  (historically flood-prone)
AI risk score multiplier   = 1.10  (moderate monsoon risk)

Rain premium  = 25 × 1.15 × 1.10  = ₹31.63
Flood premium = 20 × 1.15 × 1.10  = ₹25.30

Total weekly premium = ₹56.93 ≈ ₹57
```

### Trigger & Payout

```
Trigger:       Rain ≥ 15 mm/hr sustained for 2+ hours  ✅ MET
Observed:      18 mm/hr for 3 hours
Disruption:    3 hours

Payout = hourly_income × disruption_hours × trust_multiplier
       = ₹200 × 3 × 1.0
       = ₹600

Fraud check:   GPS confirmed in Koramangala  ✅
                No duplicate claims           ✅
                Weather data cross-validated  ✅

Final payout:  ₹600 via UPI
```

**Priya pays ₹57/week and receives ₹600 for a single rain event.** The payout covers ~70% of her lost afternoon income, delivered within minutes of the disruption ending.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                            │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐     │
│  │ Rider Portal │  │ Admin Panel  │  │ Real-time Dashboard   │     │
│  └──────┬───────┘  └──────┬───────┘  └───────────┬───────────┘     │
└─────────┼─────────────────┼──────────────────────┼─────────────────┘
          │                 │                      │
          ▼                 ▼                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    API GATEWAY (Node.js / FastAPI)                  │
│         Authentication · Rate Limiting · Request Routing           │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   RISK ENGINE   │  │    TRIGGER      │  │     FRAUD       │
│                 │  │    MONITOR      │  │    DETECTION     │
│ • Risk scoring  │  │                 │  │                 │
│ • Premium calc  │  │ • API polling   │  │ • GPS check     │
│ • Zone analysis │  │ • Threshold     │  │ • Anomaly det.  │
│                 │  │   evaluation    │  │ • Trust scoring │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                    │                    │
         └────────────────────┼────────────────────┘
                              ▼
                    ┌─────────────────┐
                    │ PAYMENT SERVICE │
                    │                 │
                    │ • Payout calc   │
                    │ • UPI dispatch  │
                    │ • Receipt gen   │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐      ┌─────────────────────┐
                    │   PostgreSQL    │◀────▶│   AUDIT LOGGER      │
                    │                 │      │                     │
                    │ riders, claims, │      │ • Immutable logs    │
                    │ policies, etc.  │      │ • Compliance trail  │
                    └─────────────────┘      └─────────────────────┘
```

### Component Responsibilities

| Component | Technology | Role |
|---|---|---|
| **Frontend** | React | Rider registration, dashboard, policy management, admin analytics |
| **API Gateway** | Node.js / FastAPI | Authentication, routing, rate limiting, request validation |
| **Risk Engine** | Python (scikit-learn) | Real-time risk scoring, premium calculation, zone risk profiling |
| **Trigger Monitor** | Python (async workers) | Polls external APIs every 15 min, evaluates thresholds, emits disruption events |
| **Fraud Detection** | Python | Rule-based checks + statistical anomaly detection, trust score management |
| **Payment Service** | Node.js | Payout computation, UPI simulation, receipt generation |
| **Audit Logger** | Python | Append-only event log for every system action — compliance and dispute resolution |
| **Database** | PostgreSQL | Persistent storage for all entities |

### External API Integrations

| API | Purpose | Polling Frequency |
|---|---|---|
| **Zomato Driver API** (simulated) | Rider earnings, active hours, delivery history | On registration + weekly sync |
| **OpenWeatherMap API** | Rainfall (mm/hr), temperature (°C), humidity | Every 15 minutes per zone |
| **AQICN API** | Real-time Air Quality Index by station | Every 15 minutes per zone |
| **Google Maps / TomTom API** | Traffic speed, congestion level by zone | Every 15 minutes per zone |
| **UPI Payment API** (simulated) | Instant payout disbursement | On payout trigger |

### Data Flow

```
External APIs ──(poll)──▶ Trigger Monitor ──(event)──▶ Fraud Engine
                                                          │
                                                          ▼
Zomato API ──(earnings)──▶ Risk Engine ──(premium)──▶ Policy DB
                                                          │
                                                          ▼
                                              Payment Service ──▶ UPI
                                                          │
                                                          ▼
                                                    Audit Logger
```

---

## Database Design

### Entity-Relationship Overview

```
riders ──< policies ──< claims ──< payouts
  │                        │
  └──< trust_scores        └──> audit_logs
```

### Table Definitions

#### `riders`
| Column | Type | Description |
|---|---|---|
| `id` | UUID (PK) | Unique rider identifier |
| `zomato_partner_id` | VARCHAR | Zomato platform partner ID |
| `name` | VARCHAR | Rider's full name |
| `phone` | VARCHAR | Mobile number |
| `zone` | VARCHAR | Registered operational zone |
| `upi_handle` | VARCHAR | UPI payment address |
| `hourly_income` | DECIMAL | Calculated average hourly income |
| `active_days_per_week` | INT | Average active days |
| `created_at` | TIMESTAMP | Registration timestamp |

#### `policies`
| Column | Type | Description |
|---|---|---|
| `id` | UUID (PK) | Unique policy identifier |
| `rider_id` | UUID (FK) | Reference to rider |
| `modules` | JSONB | Selected coverage modules and config |
| `weekly_premium` | DECIMAL | Calculated weekly premium amount |
| `zone_multiplier` | DECIMAL | Zone-specific risk multiplier |
| `risk_score` | DECIMAL | AI-calculated risk score at issuance |
| `status` | ENUM | `active`, `paused`, `cancelled` |
| `valid_from` | TIMESTAMP | Policy start date |
| `valid_until` | TIMESTAMP | Policy expiry date |

#### `claims`
| Column | Type | Description |
|---|---|---|
| `id` | UUID (PK) | Unique claim identifier |
| `policy_id` | UUID (FK) | Reference to policy |
| `trigger_type` | ENUM | `rain`, `flood`, `heat`, `aqi` |
| `trigger_value` | DECIMAL | Observed trigger value |
| `disruption_start` | TIMESTAMP | When disruption began |
| `disruption_end` | TIMESTAMP | When disruption ended |
| `disruption_hours` | DECIMAL | Calculated disruption duration |
| `fraud_check_status` | ENUM | `passed`, `flagged`, `failed` |
| `fraud_flags` | JSONB | Details of any fraud indicators |
| `created_at` | TIMESTAMP | Claim creation timestamp |

#### `payouts`
| Column | Type | Description |
|---|---|---|
| `id` | UUID (PK) | Unique payout identifier |
| `claim_id` | UUID (FK) | Reference to claim |
| `amount` | DECIMAL | Payout amount in ₹ |
| `trust_multiplier` | DECIMAL | Applied trust multiplier |
| `upi_transaction_id` | VARCHAR | UPI transaction reference |
| `status` | ENUM | `pending`, `completed`, `failed` |
| `paid_at` | TIMESTAMP | Payout completion timestamp |

#### `trust_scores`
| Column | Type | Description |
|---|---|---|
| `id` | UUID (PK) | Record identifier |
| `rider_id` | UUID (FK) | Reference to rider |
| `score` | INT | Current trust score (0–100) |
| `last_change_reason` | VARCHAR | Reason for last score change |
| `last_change_delta` | INT | Points added/removed |
| `updated_at` | TIMESTAMP | Last update timestamp |

#### `audit_logs`
| Column | Type | Description |
|---|---|---|
| `id` | UUID (PK) | Log entry identifier |
| `entity_type` | VARCHAR | `claim`, `payout`, `policy`, `trust` |
| `entity_id` | UUID | Reference to the entity |
| `action` | VARCHAR | Action performed |
| `details` | JSONB | Full event payload |
| `timestamp` | TIMESTAMP | Event timestamp |

---

## Admin Dashboard

The admin panel provides operational visibility for underwriters and platform managers.

### Dashboard Metrics

| Metric | Description | Update Frequency |
|---|---|---|
| **Active Policies** | Number of currently active rider policies | Real-time |
| **Weekly Premium Collected** | Total premium revenue for the current week | Daily |
| **Claims Triggered** | Number of parametric claims triggered this week | Real-time |
| **Payouts Disbursed** | Total ₹ disbursed in payouts this week | Real-time |
| **Fraud Alerts** | Number of claims flagged by fraud detection | Real-time |
| **Average Trust Score** | Mean trust score across all active riders | Daily |
| **Loss Ratio** | Payouts / Premiums — key profitability indicator | Weekly |
| **Zone Risk Heatmap** | Visual risk distribution across Bangalore zones | Every 15 min |

### Admin Capabilities

- View and filter all claims by status, zone, trigger type
- Manually review flagged claims (trust score < 40)
- Override payout decisions with audit trail
- Export claim and financial reports
- Configure trigger thresholds per zone
- Monitor API health and polling status

---

## Key Innovations

### 1. Parametric Insurance for the Gig Economy
No parametric insurance product exists in India for gig workers. RideGuard is the first to apply this model to delivery partners — replacing "did you prove your loss?" with "did the environment breach a threshold?"

### 2. Zero-Claim Automation
The entire pipeline — from trigger detection to payout — runs without any rider action. The rider doesn't file a claim, upload documents, or wait for approval. The system observes, decides, and pays.

### 3. Trust Score Over Binary Decisions
Instead of approving or denying claims, RideGuard uses a gradient trust system. This is fairer (one mistake doesn't destroy coverage) and more fraud-resistant (repeated bad behavior is penalized progressively).

### 4. Modular Micro-Premium System
Riders choose which risks to cover and pay only for what they select. At ₹15–₹60/week per module, premiums are priced within the daily earnings of a single delivery — making insurance accessible to a population earning ₹7,000–₹10,000/week.

### 5. AI-Driven Dynamic Pricing
Premiums aren't static — they respond to real-time environmental risk. Riders in historically safer zones benefit from lower rates. This creates a self-correcting pricing model that stays actuarially sound without manual recalibration.

### 6. Compound Trigger Logic
Flood detection uses both rainfall accumulation *and* traffic speed as independent triggers. This dual-source approach captures urban flooding scenarios (waterlogged roads with moderate rain) that single-metric systems miss.

---

## Why This Matters

### The Gig Worker Protection Gap

- **300+ million** informal workers in India lack any form of income insurance.
- Gig workers have **zero employer-provided benefits** — no health insurance, no income protection, no paid leave.
- A single week of monsoon disruption can cost a Bangalore delivery rider **₹3,000–₹5,000** in lost income — nearly half their weekly earnings.

### Why Current Solutions Fail

| Approach | Problem |
|---|---|
| Traditional insurance | High premiums, complex documentation, weeks-long claims |
| Government schemes | Limited eligibility, bureaucratic, not real-time |
| Platform-provided benefits | Nearly nonexistent for delivery partners |
| Self-insurance (savings) | Riders live paycheck to paycheck — no buffer exists |

### What RideGuard Changes

- **Instant protection**: Payout within minutes of a disruption, not weeks.
- **Affordable**: ₹57–₹120/week — less than the cost of two deliveries.
- **Accessible**: No paperwork, no documentation, no literacy barrier.
- **Fair**: Pay only when active; payout scales with actual risk exposure.
- **Trust-building**: Riders build a financial trust record — a stepping stone toward broader financial inclusion.

---

## Development Roadmap

### Phase 1 — Foundation (Weeks 1–3)
- [x] System architecture design
- [x] Database schema definition
- [x] React dashboard scaffold
- [x] API gateway setup
- [x] Simulated Zomato Driver API
- [x] Rider registration flow

### Phase 2 — Core Automation (Weeks 4–6)
- [ ] Weather / AQI / Traffic API integration
- [ ] Trigger monitoring service (15-min polling)
- [ ] Parametric trigger evaluation engine
- [ ] Premium calculation with zone multipliers
- [ ] UPI payout simulation
- [ ] Real-time dashboard updates

### Phase 3 — Intelligence & Scale (Weeks 7–10)
- [ ] AI risk scoring model deployment
- [ ] Dynamic premium adjustment pipeline
- [ ] Fraud detection engine (rule-based + anomaly)
- [ ] Trust score system implementation
- [ ] Admin dashboard with analytics
- [ ] Multi-zone Bangalore coverage
- [ ] Load testing and performance optimization

### Future Scope
- Expand to other cities (Mumbai, Delhi, Hyderabad)
- Integrate with actual Zomato / Swiggy partner APIs
- Add accident and vehicle breakdown coverage modules
- Mobile app (React Native) for riders
- Regulatory compliance for IRDAI parametric insurance sandbox

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React, Recharts, Leaflet.js (maps) |
| **API Gateway** | Node.js (Express) / FastAPI (Python) |
| **Core Services** | Python 3.11+, scikit-learn, NumPy |
| **Database** | PostgreSQL 15 |
| **Task Queue** | Celery + Redis (trigger polling) |
| **Authentication** | JWT-based token auth |
| **Deployment** | Docker, Docker Compose |
| **CI/CD** | GitHub Actions |
| **Monitoring** | Prometheus + Grafana |

---

## Getting Started

### Prerequisites

- Node.js ≥ 18
- Python ≥ 3.11
- PostgreSQL ≥ 15
- Redis ≥ 7
- Docker & Docker Compose (recommended)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/your-org/rideguard.git
cd rideguard

# Start all services
docker-compose up -d

# Run database migrations
python manage.py migrate

# Seed sample data (riders, zones, policies)
python manage.py seed

# Start the frontend
cd frontend && npm install && npm run dev
```

The dashboard will be available at `http://localhost:3000`.

### Environment Variables

```env
# Database
DATABASE_URL=postgresql://rideguard:password@localhost:5432/rideguard

# External APIs
WEATHER_API_KEY=your_openweathermap_key
AQI_API_KEY=your_aqicn_key
TRAFFIC_API_KEY=your_google_maps_key

# Auth
JWT_SECRET=your_jwt_secret
JWT_EXPIRY=24h

# Payments
UPI_SIMULATION_MODE=true
```

---

## License

This project was built for the **Guidewire Hackathon 2026**. All rights reserved.

---

<p align="center">
  <b>RideGuard</b> — Because gig workers deserve insurance that works as fast as they do.
</p>
