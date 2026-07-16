-- ============================================================================
-- SQL DDL ALTERATIONS FOR UNDERSTOOD SIGNALS
-- Schema: jarvis_insights_schemav1
-- Target Table: understood_signals
-- ============================================================================

-- Since the table already exists, we alter it to add the lineage and metadata 
-- columns so that device_id, message_hash, and metadata are directly queryable
-- at the contract layer without requiring joins. We also add UNIQUE constraints.

BEGIN;

-- 1. ADD device_id, message_hash, AND metadata JSONB COLUMNS
ALTER TABLE jarvis_insights_schemav1.understood_signals
ADD COLUMN IF NOT EXISTS device_id TEXT,
ADD COLUMN IF NOT EXISTS message_hash TEXT,
ADD COLUMN IF NOT EXISTS metadata JSONB;

-- 2. ADD UNIQUE CONSTRAINT ON qualified_signal_id (ENFORCES STRICT 1:1 RELATION)
ALTER TABLE jarvis_insights_schemav1.understood_signals
DROP CONSTRAINT IF EXISTS understood_signals_qualified_signal_id_key,
ADD CONSTRAINT understood_signals_qualified_signal_id_key UNIQUE (qualified_signal_id);

-- 3. ADD UNIQUE CONSTRAINT ON message_hash (ENFORCES CONTRACT IDEMPOTENCY)
ALTER TABLE jarvis_insights_schemav1.understood_signals
DROP CONSTRAINT IF EXISTS understood_signals_message_hash_key,
ADD CONSTRAINT understood_signals_message_hash_key UNIQUE (message_hash);

COMMIT;
