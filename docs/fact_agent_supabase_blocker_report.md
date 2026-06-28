# Fact Agent Supabase Blocker Report

**Status:** BLOCKED - USER ACTION REQUIRED  
**Date:** 2026-06-28  
**Component:** Fact Agent Persistence (Supabase Integration)  

---

## 1. Failed Operations

1. **Write to `facts` Table Failed:**
   * **Operation:** Ingesting a V2 Fact Candidate (inserting columns: `fact_id`, `fact_type`, `fact_value`, `confidence`, `status`, `source_agent`).
   * **Exact Error:** 
     `postgrest.exceptions.APIError: {'message': "Could not find the 'fact_type' column of 'facts' in the schema cache", 'code': 'PGRST204', 'hint': None, 'details': None}`
2. **Read/Write to `fact_relationships` Table Failed:**
   * **Operation:** Creating/checking directional edges between facts.
   * **Exact Error:**
     `postgrest.exceptions.APIError: {'message': "Could not find the table 'jarvis_insights_schema.fact_relationships' in the schema cache", 'code': 'PGRST205', 'hint': "Perhaps you meant the table 'jarvis_insights_schema.user_actions'", 'details': None}`

---

## 2. Root Cause

1. The remote Supabase database currently contains a legacy V1 definition of the `facts` table (containing `entity` and `fact` text fields instead of the polymorphic V2 `fact_type` and `fact_value` JSONB columns).
2. The remote database is missing the `fact_relationships` table entirely in the `jarvis_insights_schema` schema cache.
3. Postgrest clients do not possess DDL permissions to create or alter tables dynamically; these operations must be performed by an administrator.

---

## 3. Required User Action

The database administrator must execute the following migration script on the Supabase SQL editor to align the remote database with the V2 Fact Agent specifications.

### Recommended SQL Migration Script

```sql
-- Migration Script to upgrade facts table and create fact_relationships on Supabase (Postgres)

-- 1. Drop old legacy columns and add V2 columns to the facts table in jarvis_insights_schema
ALTER TABLE jarvis_insights_schema.facts 
  DROP COLUMN IF EXISTS entity,
  DROP COLUMN IF EXISTS fact,
  DROP COLUMN IF EXISTS source_signal_id;

ALTER TABLE jarvis_insights_schema.facts
  ADD COLUMN IF NOT EXISTS fact_type VARCHAR(50) NOT NULL,
  ADD COLUMN IF NOT EXISTS fact_value JSONB NOT NULL,
  ADD COLUMN IF NOT EXISTS status VARCHAR(30) NOT NULL DEFAULT 'UNCONFIRMED',
  ADD COLUMN IF NOT EXISTS owner_agent VARCHAR(50),
  ADD COLUMN IF NOT EXISTS source_agent VARCHAR(50) NOT NULL,
  ADD COLUMN IF NOT EXISTS source_type VARCHAR(30) NOT NULL DEFAULT 'OBSERVED',
  ADD COLUMN IF NOT EXISTS first_seen TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
  ADD COLUMN IF NOT EXISTS last_seen TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
  ADD COLUMN IF NOT EXISTS evidence JSONB,
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL;

-- 2. Create the fact_relationships table
CREATE TABLE IF NOT EXISTS jarvis_insights_schema.fact_relationships (
  id SERIAL PRIMARY KEY,
  subject_id VARCHAR(36) NOT NULL REFERENCES jarvis_insights_schema.facts(fact_id) ON DELETE CASCADE,
  predicate VARCHAR(50) NOT NULL,
  object_id VARCHAR(36) NOT NULL REFERENCES jarvis_insights_schema.facts(fact_id) ON DELETE CASCADE,
  confidence FLOAT NOT NULL DEFAULT 0.5,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Indexing for performance
CREATE INDEX IF NOT EXISTS idx_facts_type ON jarvis_insights_schema.facts(fact_type);
CREATE INDEX IF NOT EXISTS idx_fact_relationships_subject ON jarvis_insights_schema.fact_relationships(subject_id);
CREATE INDEX IF NOT EXISTS idx_fact_relationships_object ON jarvis_insights_schema.fact_relationships(object_id);
```

---

## 4. Next Steps
* The local SQLite backend is **100% functional** and behaves correctly for all Fact Agent operations.
* Once the migration script is run on the remote Supabase console, the schema cache will refresh and remote replication will automatically succeed.
