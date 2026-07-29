-- Phase 3C — Lifecycle Agent & Health Planner Migration
-- File: sql/migrations/phase3c_lifecycle_agent.sql

CREATE TABLE IF NOT EXISTS jarvis_insights_schemav1.lifecycle_items (
    id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    domain               TEXT        NOT NULL,   -- e.g., 'HEALTH_PLANNER', 'INSURANCE', 'WARRANTY'
    title                TEXT        NOT NULL,
    description          TEXT,
    schedule_type        TEXT        NOT NULL,   -- 'ONCE', 'RECURRING_DAYS'
    interval_days        INTEGER,                -- interval in days (e.g., 30, 180, 365)
    next_occurrence_date DATE        NOT NULL,   -- when the event is next scheduled to occur
    reminder_offset_days INTEGER     NOT NULL DEFAULT 0, -- promote to ToDo N days before next_occurrence_date
    last_promoted_date   DATE,                   -- to prevent multiple promotions on the same day
    last_todo_id         UUID,                   -- REFERENCES jarvis_insights_schemav1.tasks(id) ON DELETE SET NULL, added below
    status               TEXT        NOT NULL DEFAULT 'ACTIVE', -- 'ACTIVE', 'PAUSED', 'COMPLETED'
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Alter tasks to link to lifecycle_items
ALTER TABLE jarvis_insights_schemav1.tasks
ADD COLUMN IF NOT EXISTS lifecycle_item_id UUID;

-- Now add foreign key constraints safely (only if they don't exist)
-- Add foreign key constraint on tasks
ALTER TABLE jarvis_insights_schemav1.tasks
DROP CONSTRAINT IF EXISTS fk_tasks_lifecycle_item_id,
ADD CONSTRAINT fk_tasks_lifecycle_item_id 
    FOREIGN KEY (lifecycle_item_id) 
    REFERENCES jarvis_insights_schemav1.lifecycle_items(id) 
    ON DELETE SET NULL;

-- Add foreign key constraint on lifecycle_items
ALTER TABLE jarvis_insights_schemav1.lifecycle_items
DROP CONSTRAINT IF EXISTS fk_lifecycle_items_last_todo_id,
ADD CONSTRAINT fk_lifecycle_items_last_todo_id 
    FOREIGN KEY (last_todo_id) 
    REFERENCES jarvis_insights_schemav1.tasks(id) 
    ON DELETE SET NULL;

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_lifecycle_items_status_domain 
    ON jarvis_insights_schemav1.lifecycle_items(status, domain);
CREATE INDEX IF NOT EXISTS idx_lifecycle_items_next_occurrence 
    ON jarvis_insights_schemav1.lifecycle_items(next_occurrence_date) WHERE status = 'ACTIVE';
CREATE INDEX IF NOT EXISTS idx_tasks_lifecycle_item_id 
    ON jarvis_insights_schemav1.tasks(lifecycle_item_id) WHERE lifecycle_item_id IS NOT NULL;
