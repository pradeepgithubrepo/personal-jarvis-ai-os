-- Phase 3B — Financial Agent V1 Migration
-- File: sql/migrations/phase3b_financial_agent.sql
--
-- Creates three tables:
--   1. financial_transactions  — canonical trusted ledger (1 row per real event)
--   2. transaction_evidence    — preserves every source signal (1 row per source)
--   3. merchant_normalization_rules — deterministic merchant lookup + LLM override cache
--
-- Schema: jarvis_insights_schemav1
-- Design decisions: PHASE1_IMPLEMENTATION_PLAN.md

-- ─────────────────────────────────────────────────────────────────────────────
-- ENUMs
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TYPE jarvis_insights_schemav1.ft_direction AS ENUM (
    'DEBIT',
    'CREDIT'
);

CREATE TYPE jarvis_insights_schemav1.ft_transaction_type AS ENUM (
    'EXPENSE',
    'INCOME',
    'TRANSFER',
    'REFUND',
    'REVERSAL',
    'INVESTMENT',
    'FEE',
    'INTEREST',
    'TAX',
    'OTHER'
);

CREATE TYPE jarvis_insights_schemav1.ft_source AS ENUM (
    'SMS',
    'GPAY_PDF',
    'BANK_STATEMENT_PDF'
);

CREATE TYPE jarvis_insights_schemav1.ft_settlement_status AS ENUM (
    'PENDING',    -- SMS only, not yet confirmed by statement
    'SETTLED',    -- Confirmed by bank statement or GPay PDF
    'DISPUTED',   -- User-flagged for manual review
    'REVERSED'    -- Fully reversed / refunded (net = 0)
);

CREATE TYPE jarvis_insights_schemav1.mnr_match_type AS ENUM (
    'EXACT',       -- Direct string match before canonicalize()
    'CANONICAL',   -- Match after canonicalize() — catches all geographic/legal variants
    'CONTAINS'     -- Substring match for partial captures
);

-- ─────────────────────────────────────────────────────────────────────────────
-- TABLE 1: financial_transactions
-- The canonical trusted ledger. One row per real financial event.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS jarvis_insights_schemav1.financial_transactions (

    -- Identity
    transaction_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_hash          VARCHAR(64) NOT NULL UNIQUE,
    -- SHA256 dedup key.
    -- Tier 1: SHA256(reference_number) when present.
    -- Tier 2: SHA256(amount + YYYYMMDD + direction + source_account) as fallback.

    -- Event Data
    event_date              DATE NOT NULL,
    amount                  NUMERIC(12, 2) NOT NULL CHECK (amount > 0),
    currency                VARCHAR(3) NOT NULL DEFAULT 'INR',
    direction               jarvis_insights_schemav1.ft_direction NOT NULL,
    transaction_type        jarvis_insights_schemav1.ft_transaction_type NOT NULL DEFAULT 'OTHER',

    -- Source & Confidence
    -- Source precedence: BANK_STATEMENT_PDF > GPAY_PDF > SMS
    -- When a higher-precedence source arrives, this row is promoted and the
    -- lower-source signal is moved to transaction_evidence.
    source                  jarvis_insights_schemav1.ft_source NOT NULL,
    confidence_score        SMALLINT NOT NULL DEFAULT 60
                                CHECK (confidence_score BETWEEN 0 AND 100),
    settlement_status       jarvis_insights_schemav1.ft_settlement_status NOT NULL DEFAULT 'PENDING',

    -- Merchant & Category
    raw_narration           TEXT,
    reference_number        VARCHAR(64),
    merchant                VARCHAR(100),
    counterparty            VARCHAR(150),
    category                VARCHAR(30),
    source_account          VARCHAR(20),   -- 'HDFC' | 'SBI' | 'GPAY'

    -- Flags
    is_self_transfer        BOOLEAN NOT NULL DEFAULT FALSE,
    is_override             BOOLEAN NOT NULL DEFAULT FALSE,

    -- Lineage (full traceability: transaction → route → understood → qualified → raw)
    signal_route_id         UUID REFERENCES jarvis_insights_schemav1.signal_routes(id) ON DELETE SET NULL,

    -- Refund/Reversal link: points to the original EXPENSE this reverses
    linked_transaction_id   UUID REFERENCES jarvis_insights_schemav1.financial_transactions(transaction_id) ON DELETE SET NULL,

    -- System
    created_at              TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_ft_canonical_hash
    ON jarvis_insights_schemav1.financial_transactions(canonical_hash);

CREATE INDEX IF NOT EXISTS idx_ft_event_date
    ON jarvis_insights_schemav1.financial_transactions(event_date);

CREATE INDEX IF NOT EXISTS idx_ft_route_id
    ON jarvis_insights_schemav1.financial_transactions(signal_route_id)
    WHERE signal_route_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_ft_settlement
    ON jarvis_insights_schemav1.financial_transactions(settlement_status);

CREATE INDEX IF NOT EXISTS idx_ft_source_account
    ON jarvis_insights_schemav1.financial_transactions(source_account);

-- ─────────────────────────────────────────────────────────────────────────────
-- TABLE 2: transaction_evidence
-- Preserves every source signal linked to a transaction. Never deleted.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS jarvis_insights_schemav1.transaction_evidence (

    evidence_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id          UUID NOT NULL
                                REFERENCES jarvis_insights_schemav1.financial_transactions(transaction_id)
                                ON DELETE CASCADE,

    -- Source signal links
    source                  jarvis_insights_schemav1.ft_source NOT NULL,
    signal_route_id         UUID REFERENCES jarvis_insights_schemav1.signal_routes(id) ON DELETE SET NULL,
    understood_signal_id    UUID REFERENCES jarvis_insights_schemav1.understood_signals(id) ON DELETE SET NULL,
    qualified_signal_id     UUID REFERENCES jarvis_insights_schemav1.qualified_signals(id) ON DELETE SET NULL,

    -- What this source claimed (may differ from canonical row if SMS rounded amount)
    amount_reported         NUMERIC(12, 2),
    raw_narration           TEXT,
    reference_number        VARCHAR(64),

    captured_at             TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_te_transaction_id
    ON jarvis_insights_schemav1.transaction_evidence(transaction_id);

CREATE INDEX IF NOT EXISTS idx_te_route_id
    ON jarvis_insights_schemav1.transaction_evidence(signal_route_id)
    WHERE signal_route_id IS NOT NULL;

-- ─────────────────────────────────────────────────────────────────────────────
-- TABLE 3: merchant_normalization_rules
-- Deterministic merchant lookup table + user-override cache.
-- canonicalize() strips geo/legal tokens before lookup.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS jarvis_insights_schemav1.merchant_normalization_rules (

    rule_id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_key           VARCHAR(150) NOT NULL UNIQUE,
    -- The key AFTER canonicalize() has been applied (stripped of LTD, PVT, city names, etc.)
    -- Example: 'SWIGGY BANGALORE' → canonical_key = 'SWIGGY'

    raw_examples            TEXT[],
    -- Raw strings seen in the wild that map to this rule (for auditing)
    -- Example: ['SWIGGY*BANGALORE', 'SWIGGY LTD', 'SWIGGY INSTAMART']

    normalized_merchant     VARCHAR(100) NOT NULL,
    -- Human-readable clean name. Example: 'Swiggy'

    category_override       VARCHAR(30),
    -- Recommended category. Example: 'Food'

    is_self_transfer_override BOOLEAN DEFAULT FALSE,
    -- True if this merchant is always a self-transfer (e.g., 'HDFC TO SBI')

    match_type              jarvis_insights_schemav1.mnr_match_type NOT NULL DEFAULT 'CANONICAL',
    -- Lookup order: EXACT → CANONICAL → CONTAINS → LLM Stage 2

    approved_by_user        BOOLEAN DEFAULT FALSE,
    -- True if the user has manually verified this mapping

    created_at              TIMESTAMPTZ DEFAULT clock_timestamp(),
    updated_at              TIMESTAMPTZ DEFAULT clock_timestamp()
);

-- Index for high-speed lookups during ingestion
CREATE INDEX IF NOT EXISTS idx_mnr_canonical_key
    ON jarvis_insights_schemav1.merchant_normalization_rules(canonical_key);

CREATE INDEX IF NOT EXISTS idx_mnr_match_type
    ON jarvis_insights_schemav1.merchant_normalization_rules(match_type);

-- ─────────────────────────────────────────────────────────────────────────────
-- SEED: Baseline merchant normalization rules (deterministic Stage 1)
-- ─────────────────────────────────────────────────────────────────────────────

INSERT INTO jarvis_insights_schemav1.merchant_normalization_rules
    (canonical_key, raw_examples, normalized_merchant, category_override, match_type, approved_by_user)
VALUES
    ('SWIGGY',          ARRAY['SWIGGY*BANGALORE', 'SWIGGY LTD', 'SWIGGY INSTAMART'], 'Swiggy',          'Food',          'CANONICAL', TRUE),
    ('ZOMATO',          ARRAY['ZOMATO*', 'ZOMATOLTD'],                                'Zomato',          'Food',          'CANONICAL', TRUE),
    ('AMAZON',          ARRAY['AMAZON PAY', 'AMAZON MX', 'AMZN', 'AMAZON PAY INDIA'],'Amazon',          'Shopping',      'CANONICAL', TRUE),
    ('FLIPKART',        ARRAY['FLIPKART', 'FK'],                                      'Flipkart',        'Shopping',      'CANONICAL', TRUE),
    ('APOLLO',          ARRAY['APOLLO PHARMACY', 'APOLLO PHAR'],                      'Apollo Pharmacy', 'Health',        'CONTAINS',  TRUE),
    ('UBER',            ARRAY['UBER INDIA', 'UBER*'],                                 'Uber',            'Transport',     'CANONICAL', TRUE),
    ('OLA',             ARRAY['OLA CABS', 'ANI TECHNOLOGIES'],                        'Ola',             'Transport',     'CANONICAL', TRUE),
    ('NETFLIX',         ARRAY['NETFLIX.COM', 'NETFLIX INDIA'],                        'Netflix',         'Entertainment', 'CANONICAL', TRUE),
    ('SPOTIFY',         ARRAY['SPOTIFY INDIA', 'SPOTIFY AB'],                         'Spotify',         'Entertainment', 'CANONICAL', TRUE),
    ('BSNL',            ARRAY['BSNL MOBILE', 'BSNL LANDLINE'],                       'BSNL',            'Utilities',     'CANONICAL', TRUE),
    ('AIRTEL',          ARRAY['AIRTEL PREPAID', 'AIRTEL DTH', 'BHARTI AIRTEL'],      'Airtel',          'Utilities',     'CANONICAL', TRUE),
    ('JIO',             ARRAY['RELIANCE JIO', 'JIO PREPAID'],                         'Jio',             'Utilities',     'CANONICAL', TRUE),
    ('TNEB',            ARRAY['TNEB', 'TANGEDCO'],                                    'TNEB Electricity','Utilities',     'CANONICAL', TRUE),
    ('HDFC',            ARRAY['HDFC BANK', 'HDFCBANK'],                               'HDFC Bank',       'Banking',       'CANONICAL', TRUE),
    ('SBI',             ARRAY['STATE BANK', 'SBI BANK'],                              'SBI',             'Banking',       'CANONICAL', TRUE),
    ('LIC',             ARRAY['LIC PREMIUM', 'LIFE INSURANCE'],                       'LIC',             'Insurance',     'CONTAINS',  TRUE)
ON CONFLICT (canonical_key) DO NOTHING;
