-- Phase 3A — To-Do Agent V1 Migration
-- File: sql/migrations/phase3a_todo_agent.sql

CREATE TYPE jarvis_insights_schemav1.task_status AS ENUM (
    'OPEN',
    'IN_PROGRESS',
    'COMPLETED',
    'CANCELLED'
);

CREATE TYPE jarvis_insights_schemav1.task_priority AS ENUM (
    'LOW',
    'MEDIUM',
    'HIGH',
    'URGENT'
);

CREATE TYPE jarvis_insights_schemav1.task_source_type AS ENUM (
    'AUTO_GENERATED',
    'USER_TEXT',
    'USER_VOICE'
);

CREATE TYPE jarvis_insights_schemav1.task_created_by AS ENUM (
    'JARVIS',
    'USER'
);

CREATE TABLE IF NOT EXISTS jarvis_insights_schemav1.tasks (
    id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    title                TEXT        NOT NULL,
    description          TEXT,
    status               jarvis_insights_schemav1.task_status NOT NULL DEFAULT 'OPEN',
    priority             jarvis_insights_schemav1.task_priority NOT NULL DEFAULT 'MEDIUM',
    due_datetime         TIMESTAMPTZ,
    notification_profile TEXT        NOT NULL DEFAULT 'STANDARD', -- NONE | STANDARD | IMPORTANT | CRITICAL
    source_type          jarvis_insights_schemav1.task_source_type NOT NULL,
    route_id             UUID        REFERENCES jarvis_insights_schemav1.signal_routes(id) ON DELETE SET NULL,
    created_by           jarvis_insights_schemav1.task_created_by NOT NULL DEFAULT 'USER',
    assigned_to          TEXT        NOT NULL DEFAULT 'Pradeep',
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at         TIMESTAMPTZ
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_tasks_status ON jarvis_insights_schemav1.tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_due_datetime ON jarvis_insights_schemav1.tasks(due_datetime) WHERE status = 'OPEN';
CREATE INDEX IF NOT EXISTS idx_tasks_route_id ON jarvis_insights_schemav1.tasks(route_id) WHERE route_id IS NOT NULL;
