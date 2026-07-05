-- sql/remediation_supabase_ddl.sql
-- Ingestion Lineage & Incremental Sync Remediation for Supabase

SET search_path TO jarvis_insights_schema;

-- 1. Create ingestion_batches table
CREATE TABLE IF NOT EXISTS jarvis_insights_schema.ingestion_batches (
    batch_id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,
    source_name TEXT,
    file_name TEXT,
    file_hash TEXT,
    status TEXT NOT NULL,
    raw_records INTEGER DEFAULT 0,
    accepted_records INTEGER DEFAULT 0,
    duplicate_records INTEGER DEFAULT 0,
    rejected_records INTEGER DEFAULT 0,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- 2. Create sync_audit_log table
CREATE TABLE IF NOT EXISTS jarvis_insights_schema.sync_audit_log (
    id BIGSERIAL PRIMARY KEY,
    entity_name TEXT NOT NULL,
    record_id TEXT,
    batch_id TEXT,
    operation TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- 3. Add columns to core tables
ALTER TABLE jarvis_insights_schema.mobile_signals ADD COLUMN IF NOT EXISTS batch_id TEXT;
ALTER TABLE jarvis_insights_schema.mobile_signals ADD COLUMN IF NOT EXISTS sync_status VARCHAR(50) DEFAULT 'SYNCED';
ALTER TABLE jarvis_insights_schema.mobile_signals ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE;
ALTER TABLE jarvis_insights_schema.mobile_signals ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

ALTER TABLE jarvis_insights_schema.qualified_signals ADD COLUMN IF NOT EXISTS batch_id TEXT;
ALTER TABLE jarvis_insights_schema.qualified_signals ADD COLUMN IF NOT EXISTS sync_status VARCHAR(50) DEFAULT 'SYNCED';
ALTER TABLE jarvis_insights_schema.qualified_signals ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE;
ALTER TABLE jarvis_insights_schema.qualified_signals ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

ALTER TABLE jarvis_insights_schema.understood_signals ADD COLUMN IF NOT EXISTS batch_id TEXT;
ALTER TABLE jarvis_insights_schema.understood_signals ADD COLUMN IF NOT EXISTS sync_status VARCHAR(50) DEFAULT 'SYNCED';
ALTER TABLE jarvis_insights_schema.understood_signals ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE;
ALTER TABLE jarvis_insights_schema.understood_signals ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

ALTER TABLE jarvis_insights_schema.financial_facts ADD COLUMN IF NOT EXISTS batch_id TEXT;
ALTER TABLE jarvis_insights_schema.financial_facts ADD COLUMN IF NOT EXISTS sync_status VARCHAR(50) DEFAULT 'SYNCED';
ALTER TABLE jarvis_insights_schema.financial_facts ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE;
ALTER TABLE jarvis_insights_schema.financial_facts ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

ALTER TABLE jarvis_insights_schema.facts ADD COLUMN IF NOT EXISTS batch_id TEXT;
ALTER TABLE jarvis_insights_schema.facts ADD COLUMN IF NOT EXISTS sync_status VARCHAR(50) DEFAULT 'SYNCED';
ALTER TABLE jarvis_insights_schema.facts ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE;
ALTER TABLE jarvis_insights_schema.facts ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

ALTER TABLE jarvis_insights_schema.todo_items ADD COLUMN IF NOT EXISTS batch_id TEXT;
ALTER TABLE jarvis_insights_schema.todo_items ADD COLUMN IF NOT EXISTS sync_status VARCHAR(50) DEFAULT 'SYNCED';
ALTER TABLE jarvis_insights_schema.todo_items ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE;
ALTER TABLE jarvis_insights_schema.todo_items ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

ALTER TABLE jarvis_insights_schema.fyi_events ADD COLUMN IF NOT EXISTS batch_id TEXT;
ALTER TABLE jarvis_insights_schema.fyi_events ADD COLUMN IF NOT EXISTS sync_status VARCHAR(50) DEFAULT 'SYNCED';
ALTER TABLE jarvis_insights_schema.fyi_events ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE;
ALTER TABLE jarvis_insights_schema.fyi_events ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

ALTER TABLE jarvis_insights_schema.daily_briefs ADD COLUMN IF NOT EXISTS batch_id TEXT;
ALTER TABLE jarvis_insights_schema.daily_briefs ADD COLUMN IF NOT EXISTS sync_status VARCHAR(50) DEFAULT 'SYNCED';
ALTER TABLE jarvis_insights_schema.daily_briefs ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE;
ALTER TABLE jarvis_insights_schema.daily_briefs ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
