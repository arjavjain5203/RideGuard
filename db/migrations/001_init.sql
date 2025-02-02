-- RideGuard - Initial Runtime-Compatible Database Schema
-- PostgreSQL 15+

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- USERS
-- ============================================================
CREATE TABLE users (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name              VARCHAR(128) NOT NULL,
    login_id          VARCHAR(128) UNIQUE,
    password_hash     VARCHAR(512),
    role              VARCHAR(16) NOT NULL DEFAULT 'rider' CHECK (role IN ('rider', 'admin')),
    zomato_partner_id VARCHAR(64) UNIQUE,
    phone             VARCHAR(15),
    upi_handle        VARCHAR(128),
    zone              VARCHAR(64) NOT NULL,
    hourly_income     NUMERIC(10,2),
    is_active         BOOLEAN DEFAULT TRUE,
    base_urts         INT DEFAULT 70 CHECK (base_urts >= 0 AND base_urts <= 100),
    last_login_at     TIMESTAMPTZ,
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- EARNINGS
-- ============================================================
CREATE TABLE earnings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    weekly_earnings NUMERIC(10,2) NOT NULL,
    hours_worked    INT NOT NULL,
    active_days     INT NOT NULL
);

-- ============================================================
-- COVERAGE MODULES
-- ============================================================
CREATE TABLE coverage_modules (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                   VARCHAR(64) UNIQUE NOT NULL,
    display_name           VARCHAR(128) NOT NULL,
    base_price             NUMERIC(10,2) NOT NULL,
    trigger_type           VARCHAR(32) NOT NULL,
    trigger_threshold      NUMERIC(10,2) NOT NULL,
    trigger_duration_hours NUMERIC(4,1) DEFAULT 0,
    description            TEXT
);

INSERT INTO coverage_modules (name, display_name, base_price, trigger_type, trigger_threshold, trigger_duration_hours, description) VALUES
    ('rain',  '☔ Rain Shield',  25.00, 'rain',  15.0, 2.0, 'Heavy rainfall ≥ 15 mm/hr'),
    ('flood', '🌊 Flood Guard', 20.00, 'flood', 60.0, 6.0, 'Flooding ≥ 60 mm rainfall or traffic < 5 km/h'),
    ('heat',  '🌡️ Heat Cover', 15.00, 'heat',  42.0, 0.0, 'Extreme heat ≥ 42°C'),
    ('aqi',   '💨 AQI Protect', 18.00, 'aqi',  300.0, 3.0, 'Hazardous AQI ≥ 300');

-- ============================================================
-- ZONES
-- ============================================================
CREATE TABLE zones (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(64) UNIQUE NOT NULL,
    risk_multiplier NUMERIC(4,2) DEFAULT 1.00,
    geo_bounds      TEXT
);

-- ============================================================
-- POLICIES
-- ============================================================
CREATE TABLE policies (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    coverage_types  TEXT NOT NULL DEFAULT '[]',
    weekly_premium  NUMERIC(10,2) NOT NULL,
    zone_multiplier NUMERIC(4,2) DEFAULT 1.00,
    risk_score      NUMERIC(4,2) DEFAULT 0.50,
    status          VARCHAR(16) DEFAULT 'active' CHECK (status IN ('active','paused','cancelled')),
    valid_from      TIMESTAMPTZ DEFAULT NOW(),
    valid_until     TIMESTAMPTZ DEFAULT NOW() + INTERVAL '7 days',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TRIGGERS
-- ============================================================
CREATE TABLE triggers (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type           VARCHAR(32) NOT NULL,
    value          NUMERIC(10,2) NOT NULL,
    zone           VARCHAR(64) NOT NULL,
    status         VARCHAR(16) DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','ONGOING','ENDED')),
    start_time     TIMESTAMPTZ DEFAULT NOW(),
    end_time       TIMESTAMPTZ,
    duration_hours NUMERIC(4,2) DEFAULT 0,
    disruption_probability NUMERIC(5,4),
    environment_inputs TEXT DEFAULT '{}',
    decision_reason VARCHAR(64),
    triggered_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- CLAIMS
-- ============================================================
CREATE TABLE claims (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_id          UUID REFERENCES policies(id) ON DELETE SET NULL,
    user_id            UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    trigger_id         UUID REFERENCES triggers(id) ON DELETE SET NULL,
    trigger_type       VARCHAR(16),
    trigger_value      NUMERIC(10,2),
    disruption_start   TIMESTAMPTZ,
    disruption_end     TIMESTAMPTZ,
    loss_amount        NUMERIC(10,2) NOT NULL,
    status             VARCHAR(16) DEFAULT 'pending' CHECK (status IN ('pending','paid','rejected','capped')),
    disruption_hours   NUMERIC(4,2),
    effective_urts     INT CHECK (effective_urts >= 0 AND effective_urts <= 100),
    effective_urts_at_event INT CHECK (effective_urts_at_event >= 0 AND effective_urts_at_event <= 100),
    event_adjustment   NUMERIC(5,2) DEFAULT 0,
    anomaly_score      NUMERIC(5,4) DEFAULT 0,
    fraud_flag         BOOLEAN DEFAULT FALSE,
    behavioral_signals TEXT DEFAULT '{}',
    created_at         TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- PAYOUTS
-- ============================================================
CREATE TABLE payouts (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id        UUID NOT NULL UNIQUE REFERENCES claims(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount          NUMERIC(10,2) NOT NULL,
    urts_factor     NUMERIC(3,2) NOT NULL,
    transaction_id  VARCHAR(64) UNIQUE NOT NULL,
    status          VARCHAR(16) DEFAULT 'pending' CHECK (status IN ('pending','completed','failed','capped')),
    paid_at         TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TRUST LOGS
-- ============================================================
CREATE TABLE trust_logs (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    change     INT NOT NULL,
    reason     VARCHAR(256) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- URTS HISTORY
-- ============================================================
CREATE TABLE urts_history (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    claim_id         UUID UNIQUE REFERENCES claims(id) ON DELETE CASCADE,
    base_urts        INT NOT NULL CHECK (base_urts >= 0 AND base_urts <= 100),
    event_adjustment NUMERIC(5,2) NOT NULL,
    effective_urts   INT NOT NULL CHECK (effective_urts >= 0 AND effective_urts <= 100),
    timestamp        TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- AUDIT LOGS
-- ============================================================
CREATE TABLE audit_logs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type VARCHAR(32) NOT NULL,
    entity_id   UUID NOT NULL,
    action      VARCHAR(64) NOT NULL,
    details     TEXT DEFAULT '{}',
    timestamp   TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- INDEXES
-- ============================================================
CREATE INDEX idx_earnings_user      ON earnings(user_id);
CREATE INDEX idx_users_role         ON users(role);
CREATE INDEX idx_policies_user      ON policies(user_id);
CREATE INDEX idx_claims_user        ON claims(user_id);
CREATE INDEX idx_claims_policy      ON claims(policy_id);
CREATE INDEX idx_claims_trigger     ON claims(trigger_id);
CREATE UNIQUE INDEX idx_claims_user_trigger_unique ON claims(user_id, trigger_id) WHERE trigger_id IS NOT NULL;
CREATE INDEX idx_payouts_user       ON payouts(user_id);
CREATE INDEX idx_payouts_claim      ON payouts(claim_id);
CREATE INDEX idx_trust_logs_user    ON trust_logs(user_id);
CREATE INDEX idx_triggers_zone      ON triggers(zone);
CREATE INDEX idx_urts_history_user  ON urts_history(user_id);
