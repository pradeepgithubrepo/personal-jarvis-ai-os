-- ============================================================================
-- SQL DDL ALTERATIONS FOR QUALIFICATION LAYER V2
-- Schema: jarvis_insights_schemav1
-- Target Table: qualified_signals
-- ============================================================================

-- 1. ADD device_id, message_hash, and metadata jsonb COLUMNS
ALTER TABLE jarvis_insights_schemav1.qualified_signals
ADD COLUMN IF NOT EXISTS device_id TEXT,
ADD COLUMN IF NOT EXISTS message_hash TEXT,
ADD COLUMN IF NOT EXISTS metadata JSONB;

-- 2. ADD UNIQUE CONSTRAINT ON message_hash TO PROTECT LINEAGE/IDEMPOTENCY
-- Note: Ensure existing table records are truncated or have unique message_hashes
-- before executing this constraint modification.
ALTER TABLE jarvis_insights_schemav1.qualified_signals
ADD CONSTRAINT qualified_signals_message_hash_key UNIQUE (message_hash);

-- ============================================================================
-- ROLLBACK SQL (FOR MANUAL EMERGENCY RESTORATION)
-- ============================================================================
-- ALTER TABLE jarvis_insights_schemav1.qualified_signals
-- DROP CONSTRAINT IF EXISTS qualified_signals_message_hash_key;
--
-- ALTER TABLE jarvis_insights_schemav1.qualified_signals
-- DROP COLUMN IF EXISTS device_id,
-- DROP COLUMN IF EXISTS message_hash,
-- DROP COLUMN IF EXISTS metadata;
-- ============================================================================
