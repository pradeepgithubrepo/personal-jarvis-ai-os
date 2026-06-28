# FYI Agent Supabase Blocker Report

**Status:** BLOCKED - USER ACTION REQUIRED  
**Date:** 2026-06-28  
**Component:** FYI Agent Persistence (Supabase Integration)  

---

## 1. Failed Operation

* **Read/Write to `fyi_events` Table Failed:**
  * **Operation:** Checking/writing to the `fyi_events` table during initialization/ingestion.
  * **Exact Error:**
    `postgrest.exceptions.APIError: {'message': 'column fyi_events.event_id does not exist', 'code': '42703', 'hint': None, 'details': None}`

---

## 2. Root Cause

1. The remote database contains a legacy version of the `fyi_events` table where the primary key is an integer column named `id` instead of a UUID column named `event_id`.
2. The Postgrest client lacks administrative privileges to modify DDL schemas dynamically; table restructuring must be executed via the database console.

---

## 3. Required User Action

The database administrator must execute the following migration script in the Supabase SQL editor to upgrade the `fyi_events` table.

### Recommended SQL Migration Script

```sql
-- Migration Script to upgrade fyi_events table on Supabase (Postgres)

-- Step 1: Drop the legacy fyi_events table
DROP TABLE IF EXISTS jarvis_insights_schema.fyi_events;

-- Step 2: Create the V2 fyi_events table
CREATE TABLE IF NOT EXISTS jarvis_insights_schema.fyi_events (
    event_id UUID PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    importance VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
    status VARCHAR(30) NOT NULL DEFAULT 'UNREAD',
    source_signal_id UUID,
    duplicate_count INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Indexing for performance
CREATE INDEX IF NOT EXISTS idx_fyi_events_category ON jarvis_insights_schema.fyi_events(category);
CREATE INDEX IF NOT EXISTS idx_fyi_events_status ON jarvis_insights_schema.fyi_events(status);

-- Refresh stats
ANALYZE jarvis_insights_schema.fyi_events;
```

---

## 4. Next Steps
* The local SQLite backend is **100% functional** and processes all FYI events correctly.
* Once the migration script is run on the remote Supabase editor, the replication operations will automatically succeed.
