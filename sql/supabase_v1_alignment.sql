-- sql/supabase_v1_alignment.sql
-- Idempotent Migration Script to consolidate Supabase schemas for Jarvis V1

-- Step 1: Drop Legacy Tables
DROP TABLE IF EXISTS jarvis_insights_schema.todos;


-- Step 2: Create Missing Tables

-- 2.1 mobile_signals
CREATE TABLE IF NOT EXISTS jarvis_insights_schema.mobile_signals (
    id BIGSERIAL PRIMARY KEY,
    device_id VARCHAR(100) NOT NULL,
    source VARCHAR(50) NOT NULL,
    sender VARCHAR(500) NOT NULL,
    message TEXT NOT NULL,
    mobile_timestamp VARCHAR(100) NOT NULL,
    processed BOOLEAN NOT NULL DEFAULT FALSE,
    message_hash VARCHAR(64) UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- 2.2 financial_facts
CREATE TABLE IF NOT EXISTS jarvis_insights_schema.financial_facts (
    fact_id UUID PRIMARY KEY,
    fact_type VARCHAR(50) NOT NULL,
    amount NUMERIC NOT NULL,
    currency VARCHAR(10) NOT NULL,
    merchant_canonical VARCHAR(100),
    category VARCHAR(50),
    classification_confidence NUMERIC NOT NULL DEFAULT 1.0,
    financial_event_id UUID,
    event_date DATE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- 2.3 salary_events
CREATE TABLE IF NOT EXISTS jarvis_insights_schema.salary_events (
    id BIGSERIAL PRIMARY KEY,
    amount NUMERIC NOT NULL,
    event_date DATE NOT NULL,
    detected_date TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- 2.4 salary_sources
CREATE TABLE IF NOT EXISTS jarvis_insights_schema.salary_sources (
    id BIGSERIAL PRIMARY KEY,
    employer_name VARCHAR(100) NOT NULL,
    account_number VARCHAR(50) NOT NULL
);

-- 2.5 merchant_profiles
CREATE TABLE IF NOT EXISTS jarvis_insights_schema.merchant_profiles (
    id BIGSERIAL PRIMARY KEY,
    merchant_name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL
);

-- 2.6 qualified_signals
CREATE TABLE IF NOT EXISTS jarvis_insights_schema.qualified_signals (
    id BIGSERIAL PRIMARY KEY,
    signal_id VARCHAR(100) NOT NULL,
    source VARCHAR(50) NOT NULL,
    sender VARCHAR(500) NOT NULL,
    message TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    qualification_score INT NOT NULL,
    qualification_status VARCHAR(50) NOT NULL,
    qualification_reason VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- 2.7 bank_accounts
CREATE TABLE IF NOT EXISTS jarvis_insights_schema.bank_accounts (
    id VARCHAR(36) PRIMARY KEY,
    bank_name VARCHAR(100) NOT NULL,
    ifsc_prefix VARCHAR(10),
    account_number_masked VARCHAR(20),
    account_type VARCHAR(20) NOT NULL DEFAULT 'savings',
    sender_aliases JSONB NOT NULL DEFAULT '[]'::jsonb,
    receiver_aliases JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    registered_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- 2.8 merchants
CREATE TABLE IF NOT EXISTS jarvis_insights_schema.merchants (
    id VARCHAR(36) PRIMARY KEY,
    canonical_name VARCHAR(200) NOT NULL UNIQUE,
    category VARCHAR(50) NOT NULL,
    aliases JSONB NOT NULL DEFAULT '[]'::jsonb,
    logo_url VARCHAR(500),
    is_trusted BOOLEAN NOT NULL DEFAULT TRUE,
    is_seed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- 2.9 runtime_events
CREATE TABLE IF NOT EXISTS jarvis_insights_schema.runtime_events (
    id BIGSERIAL PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    source VARCHAR(100) NOT NULL,
    payload TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'success',
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- 2.10 transfer_pairs
CREATE TABLE IF NOT EXISTS jarvis_insights_schema.transfer_pairs (
    id VARCHAR(36) PRIMARY KEY,
    debit_event_id UUID NOT NULL REFERENCES jarvis_insights_schema.financial_events(financial_event_id) ON DELETE CASCADE,
    credit_event_id UUID NOT NULL REFERENCES jarvis_insights_schema.financial_events(financial_event_id) ON DELETE CASCADE,
    amount NUMERIC NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'INR',
    transfer_type VARCHAR(20) NOT NULL DEFAULT 'UNKNOWN',
    window_seconds NUMERIC,
    confidence NUMERIC NOT NULL DEFAULT 1.0,
    detected_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);


-- Step 3: Indexes
CREATE INDEX IF NOT EXISTS idx_mobile_signals_hash ON jarvis_insights_schema.mobile_signals(message_hash);
CREATE INDEX IF NOT EXISTS idx_financial_facts_type ON jarvis_insights_schema.financial_facts(fact_type);
CREATE INDEX IF NOT EXISTS idx_qualified_signals_status ON jarvis_insights_schema.qualified_signals(qualification_status);
CREATE INDEX IF NOT EXISTS idx_runtime_events_type ON jarvis_insights_schema.runtime_events(event_type);


-- Step 4: Refresh Stats
ANALYZE jarvis_insights_schema.mobile_signals;
ANALYZE jarvis_insights_schema.financial_facts;
ANALYZE jarvis_insights_schema.salary_events;
ANALYZE jarvis_insights_schema.salary_sources;
ANALYZE jarvis_insights_schema.merchant_profiles;
ANALYZE jarvis_insights_schema.qualified_signals;
ANALYZE jarvis_insights_schema.bank_accounts;
ANALYZE jarvis_insights_schema.merchants;
ANALYZE jarvis_insights_schema.runtime_events;
ANALYZE jarvis_insights_schema.transfer_pairs;
