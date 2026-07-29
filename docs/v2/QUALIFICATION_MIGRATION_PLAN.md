# Qualification Layer V2 Migration Plan

This document details the migration path, DDL execution, data backfill strategy, and reconstruction playbook required to transition Jarvis V2 to the redesigned qualification layer.

---

## 1. Migration Strategy

To support the newly added `device_id`, `message_hash`, and `metadata` columns in `qualified_signals` without producing duplicate primary key violations, the existing test records and database states must be wiped clean.

We will proceed with a **Destructive Rebuild Strategy**:
1. Truncate downstream tables containing test data (`signal_routes`, `understood_signals`, `qualified_signals`).
2. Apply the DDL script to alter `qualified_signals`.
3. Reset all `processed` flags to `False` in `mobile_signals` so that the entire corpus is eligible for re-processing.
4. Run the updated Qualification Agent backfill to re-populate the table with full metadata.

---

## 2. MANUAL ACTION REQUIRED

The following SQL must be executed manually against the remote Supabase database:

```sql
-- ============================================================================
-- MANUAL MIGRATION SCRIPT - JARVIS V2 QUALIFICATION REDESIGN
-- ============================================================================

BEGIN;

-- 1. TRUNCATE DOWNSTREAM TABLES (FK CASCADE)
-- This wipes all test records and downstream routes so we can run a clean rebuild
TRUNCATE TABLE jarvis_insights_schemav1.signal_routes CASCADE;
TRUNCATE TABLE jarvis_insights_schemav1.understood_signals CASCADE;
TRUNCATE TABLE jarvis_insights_schemav1.qualified_signals CASCADE;

-- 2. ALTER TABLE SCHEMA
ALTER TABLE jarvis_insights_schemav1.qualified_signals
ADD COLUMN IF NOT EXISTS device_id TEXT,
ADD COLUMN IF NOT EXISTS message_hash TEXT,
ADD COLUMN IF NOT EXISTS metadata JSONB;

-- 3. ADD UNIQUE CONSTRAINT
ALTER TABLE jarvis_insights_schemav1.qualified_signals
ADD CONSTRAINT qualified_signals_message_hash_key UNIQUE (message_hash);

-- 4. RESET PROCESS FLAG ON INGESTED MOBILE SIGNALS
-- Flipped to false so they are picked up in the next backfill run
UPDATE jarvis_insights_schemav1.mobile_signals
SET processed = false;

COMMIT;
```

### Expected Impact
* **Data Cleared**: The `qualified_signals`, `understood_signals`, and `signal_routes` tables will be temporarily empty.
* **Lineage Ready**: All 1,700 `mobile_signals` records will have `processed = false` and be ready to qualify.
* **Storage Footprint**: Minimal (schema alteration is metadata-only).

### Rollback Approach
If the manual migration fails or must be reverted, execute the following SQL:
```sql
BEGIN;

ALTER TABLE jarvis_insights_schemav1.qualified_signals
DROP CONSTRAINT IF EXISTS qualified_signals_message_hash_key;

ALTER TABLE jarvis_insights_schemav1.qualified_signals
DROP COLUMN IF EXISTS device_id,
DROP COLUMN IF EXISTS message_hash,
DROP COLUMN IF EXISTS metadata;

UPDATE jarvis_insights_schemav1.mobile_signals
SET processed = true; -- marks them processed again to avoid infinite queue loop

COMMIT;
```

---

## 3. Qualification Rebuild Plan

Once the manual database script is executed, the qualification layer can be rebuilt end-to-end.

### Step 1: Code Updates (Do not execute)
Update the Qualification Agent orchestrator code in the next phase to:
* Extract `device_id`, `message_hash`, and `metadata` from `mobile_signals`.
* Apply the **Source-Aware** Qualification Rules:
  - If source is `gpay` or `bank_statement` and structured metadata is present, qualify immediately (score 100).
  - Else, use the rule-based scoring (OTP, spam, boosts, overrides).
* Bulk insert these new columns into `qualified_signals`.

### Step 2: Reprocess Ingested Data (Do not execute)
Run the backfill script:
```bash
.venv/bin/python scripts/run_pipeline_backfill.py
```
*Because the pipeline is frozen at the qualification boundary, this backfill runner must be temporarily modified to stop execution after the Qualification Agent completes (i.e. do not run SUA or Router stages).*

### Step 3: Validate Outputs (Do not execute)
Run count checks to verify:
* `mobile_signals`: 1,700 records with `processed = true`.
* `qualified_signals`: ~1,700 records containing valid `device_id`, `message_hash`, and `metadata` payloads.
* `understood_signals`: 0 records (due to pipeline freeze).
* `signal_routes`: 0 records (due to pipeline freeze).
