# Qualification Layer V2 Migration & Rebuild Plan

This document details the migration path, SQL alterations (including promoted physical columns), manual execution scripts, and the post-rebuild validation framework.

---

## 1. Migration Strategy

To support `device_id`, `message_hash`, `metadata`, and promoted physical columns (`amount`, `currency`, `transaction_type`), we will execute a **Destructive Rebuild Strategy**:
1. Truncate downstream tables containing test data (`signal_routes`, `understood_signals`, `qualified_signals`).
2. Apply the DDL script to alter `qualified_signals` (adding columns and constraints).
3. Reset all `processed` flags to `False` in `mobile_signals`.
4. Run the updated Qualification Agent to qualify the entire corpus and populate all fields.

---

## 2. MANUAL ACTION REQUIRED

The following SQL script must be executed manually against the remote Supabase database:

```sql
-- ============================================================================
-- MANUAL MIGRATION SCRIPT - JARVIS V2 QUALIFICATION REDESIGN
-- Schema: jarvis_insights_schemav1
-- Target Table: qualified_signals
-- ============================================================================

BEGIN;

-- 1. TRUNCATE DOWNSTREAM TABLES (FK CASCADE)
-- This wipes all test records and downstream routes so we can run a clean rebuild
TRUNCATE TABLE jarvis_insights_schemav1.signal_routes CASCADE;
TRUNCATE TABLE jarvis_insights_schemav1.understood_signals CASCADE;
TRUNCATE TABLE jarvis_insights_schemav1.qualified_signals CASCADE;

-- 2. ALTER TABLE SCHEMA
-- Add new columns including the promoted physical columns for amount, currency, and tx type
ALTER TABLE jarvis_insights_schemav1.qualified_signals
ADD COLUMN IF NOT EXISTS device_id TEXT,
ADD COLUMN IF NOT EXISTS message_hash TEXT,
ADD COLUMN IF NOT EXISTS metadata JSONB,
ADD COLUMN IF NOT EXISTS amount NUMERIC(12, 2),
ADD COLUMN IF NOT EXISTS currency VARCHAR(3),
ADD COLUMN IF NOT EXISTS transaction_type VARCHAR(10);

-- 3. ADD CONSTRAINTS
-- Add UNIQUE constraint on message_hash
ALTER TABLE jarvis_insights_schemav1.qualified_signals
DROP CONSTRAINT IF EXISTS qualified_signals_message_hash_key,
ADD CONSTRAINT qualified_signals_message_hash_key UNIQUE (message_hash);

-- Add CHECK constraint on transaction_type
ALTER TABLE jarvis_insights_schemav1.qualified_signals
DROP CONSTRAINT IF EXISTS check_tx_type,
ADD CONSTRAINT check_tx_type CHECK (transaction_type IN ('DEBIT', 'CREDIT'));

-- 4. RESET PROCESS FLAG ON INGESTED MOBILE SIGNALS
-- Flipped to false so they are picked up in the next backfill run
UPDATE jarvis_insights_schemav1.mobile_signals
SET processed = false;

COMMIT;
```

### Rollback SQL
```sql
BEGIN;

ALTER TABLE jarvis_insights_schemav1.qualified_signals
DROP CONSTRAINT IF EXISTS qualified_signals_message_hash_key,
DROP CONSTRAINT IF EXISTS check_tx_type;

ALTER TABLE jarvis_insights_schemav1.qualified_signals
DROP COLUMN IF EXISTS device_id,
DROP COLUMN IF EXISTS message_hash,
DROP COLUMN IF EXISTS metadata,
DROP COLUMN IF EXISTS amount,
DROP COLUMN IF EXISTS currency,
DROP COLUMN IF EXISTS transaction_type;

UPDATE jarvis_insights_schemav1.mobile_signals
SET processed = true;

COMMIT;
```

---

## 3. Post-Rebuild Validation Framework

Run the following SQL queries after the rebuild process completes to prove that metadata, lineage, and context are fully preserved. **Expect 0 rows returned for all error-proving queries (failures = 0).**

### 3.1 Metadata Preservation Check
Proves that metadata is populated for all qualified/reviewed signals.
```sql
SELECT id, source, message FROM jarvis_insights_schemav1.qualified_signals
WHERE qualification_status IN ('QUALIFIED', 'REVIEW')
  AND (metadata IS NULL OR metadata = '{}'::jsonb);
```

### 3.2 Device ID Preservation Check
Proves that the origin device attribution is carried over correctly.
```sql
SELECT qs.id, qs.device_id, ms.device_id 
FROM jarvis_insights_schemav1.qualified_signals qs
JOIN jarvis_insights_schemav1.mobile_signals ms ON qs.signal_id = ms.id
WHERE qs.device_id IS DISTINCT FROM ms.device_id;
```

### 3.3 Message Hash Preservation Check
Proves that the unique content identifier is preserved intact.
```sql
SELECT qs.id, qs.message_hash, ms.message_hash 
FROM jarvis_insights_schemav1.qualified_signals qs
JOIN jarvis_insights_schemav1.mobile_signals ms ON qs.signal_id = ms.id
WHERE qs.message_hash IS DISTINCT FROM ms.message_hash;
```

### 3.4 Financial Metadata Preservation Check
Proves that the promoted physical columns correctly reflect the structured metadata parsed by collectors (ignores unstructured/non-financial signals).
```sql
SELECT id, amount, (metadata->'source_metadata'->>'amount')::numeric AS meta_amount
FROM jarvis_insights_schemav1.qualified_signals
WHERE source IN ('gpay', 'bank_statement')
  AND qualification_status = 'QUALIFIED'
  AND amount IS DISTINCT FROM (metadata->'source_metadata'->>'amount')::numeric;
```

### 3.5 Lineage Preservation Check
Proves that every record in `qualified_signals` references a valid record in `mobile_signals`.
```sql
SELECT qs.id FROM jarvis_insights_schemav1.qualified_signals qs
LEFT JOIN jarvis_insights_schemav1.mobile_signals ms ON qs.signal_id = ms.id
WHERE ms.id IS NULL;
```
