-- RideGuard - Initial Database Schema
-- PostgreSQL 15+

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- RIDERS
-- ============================================================
CREATE TABLE riders (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    zomato_partner_id VARCHAR(64) UNIQUE NOT NULL,
    name            VARCHAR(128) NOT NULL,
    phone           VARCHAR(15)  NOT NULL,
    zone            VARCHAR(64)  NOT NULL,
    upi_handle      VARCHAR(128) NOT NULL,
    hourly_income   NUMERIC(10,2),
    active_days_per_week INT DEFAULT 0,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- COVERAGE MODULES (lookup / reference table)
-- ============================================================
CREATE TABLE coverage_modules (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(64) UNIQUE NOT NULL,  -- rain, flood, heat, aqi
    display_name    VARCHAR(128) NOT NULL,
    base_price      NUMERIC(10,2) NOT NULL,       -- weekly base price in INR
    trigger_type    VARCHAR(32) NOT NULL,          -- rain, flood, heat, aqi
    trigger_threshold NUMERIC(10,2) NOT NULL,      -- e.g. 15 (mm/hr), 42 (°C)
    trigger_duration_hours NUMERIC(4,1) DEFAULT 0, -- sustained duration needed
    description     TEXT
);

-- Seed coverage modules
INSERT INTO coverage_modules (name, display_name, base_price, trigger_type, trigger_threshold, trigger_duration_hours, description) VALUES
    ('rain',  '☔ Rain Shield',  25.00, 'rain',  15.0,  2.0, 'Heavy rainfall ≥ 15 mm/hr for 2+ hours'),
    ('flood', '🌊 Flood Guard', 20.00, 'flood', 60.0,  6.0, 'Flooding ≥ 60mm/6hr OR traffic < 5 km/h'),
    ('heat',  '🌡️ Heat Cover',  15.00, 'heat',  42.0,  0.0, 'Extreme heat ≥ 42°C (instant trigger)'),
    ('aqi',   '💨 AQI Protect', 18.00, 'aqi',   300.0, 3.0, 'Hazardous AQI ≥ 300 for 3+ hours');

-- ============================================================
-- POLICIES
-- ============================================================
CREATE TABLE policies (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rider_id        UUID NOT NULL REFERENCES riders(id) ON DELETE CASCADE,
    modules         JSONB NOT NULL DEFAULT '[]',   -- list of module names selected
    weekly_premium  NUMERIC(10,2) NOT NULL,
    zone_multiplier NUMERIC(4,2) DEFAULT 1.00,
    risk_score      NUMERIC(4,2) DEFAULT 0.50,
    status          VARCHAR(16) DEFAULT 'active' CHECK (status IN ('active','paused','cancelled')),
    valid_from      TIMESTAMPTZ DEFAULT NOW(),
    valid_until     TIMESTAMPTZ DEFAULT NOW() + INTERVAL '7 days',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- CLAIMS
-- ============================================================
CREATE TABLE claims (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_id               UUID NOT NULL REFERENCES policies(id) ON DELETE CASCADE,
    rider_id                UUID NOT NULL REFERENCES riders(id) ON DELETE CASCADE,
    trigger_type            VARCHAR(16) NOT NULL CHECK (trigger_type IN ('rain','flood','heat','aqi')),
    trigger_value           NUMERIC(10,2) NOT NULL,
    disruption_start        TIMESTAMPTZ NOT NULL,
    disruption_end          TIMESTAMPTZ,
    disruption_hours        NUMERIC(4,1),
    effective_urts          INT,
    behavioral_risk_signals JSONB DEFAULT '{}',
    status                  VARCHAR(16) DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected','paid')),
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- PAYOUTS
-- ============================================================
CREATE TABLE payouts (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id            UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    rider_id            UUID NOT NULL REFERENCES riders(id) ON DELETE CASCADE,
    amount              NUMERIC(10,2) NOT NULL,
    urts_factor         NUMERIC(3,2) NOT NULL,
    upi_transaction_id  VARCHAR(64) UNIQUE NOT NULL,
    status              VARCHAR(16) DEFAULT 'pending' CHECK (status IN ('pending','completed','failed')),
    paid_at             TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- RIDER SCORES (URTS)
-- ============================================================
CREATE TABLE rider_scores (
    rider_id        UUID PRIMARY KEY REFERENCES riders(id) ON DELETE CASCADE,
    urts_score      INT NOT NULL DEFAULT 70 CHECK (urts_score >= 0 AND urts_score <= 100),
    last_event      VARCHAR(256),
    score_history   JSONB DEFAULT '[]',
    last_updated    TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- INDEXES
-- ============================================================
CREATE INDEX idx_policies_rider     ON policies(rider_id);
CREATE INDEX idx_claims_rider       ON claims(rider_id);
CREATE INDEX idx_claims_policy      ON claims(policy_id);
CREATE INDEX idx_payouts_rider      ON payouts(rider_id);
CREATE INDEX idx_payouts_claim      ON payouts(claim_id);
