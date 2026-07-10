-- Phase 2B — signal_routes audit table migration
-- File: sql/migrations/phase2b_signal_routes.sql
-- Applied: 2026-07-10 (confirmed created in Supabase by user)
--
-- Purpose: Full routing lineage, auditability, replay support, failure analysis.
-- Owner:   ContractDispatcher (src/intelligence/dispatch/dispatcher.py)
-- Reads:   ReplayRouter, monitoring queries

CREATE TABLE IF NOT EXISTS jarvis_insights_schemav1.signal_routes (
    id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    understood_signal_id UUID        NOT NULL
                            REFERENCES jarvis_insights_schemav1.understood_signals(id)
                            ON DELETE CASCADE,
    agent_name           TEXT        NOT NULL,
    route_status         TEXT        NOT NULL,   -- DISPATCHED | COMPLETED | FAILED | SKIPPED | VALIDATION_FAILED | NO_ROUTE
    started_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at         TIMESTAMPTZ,
    error_message        TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_signal_routes_understood_signal_id
    ON jarvis_insights_schemav1.signal_routes(understood_signal_id);

CREATE INDEX IF NOT EXISTS idx_signal_routes_agent_name
    ON jarvis_insights_schemav1.signal_routes(agent_name);

CREATE INDEX IF NOT EXISTS idx_signal_routes_route_status
    ON jarvis_insights_schemav1.signal_routes(route_status);

CREATE INDEX IF NOT EXISTS idx_signal_routes_created_at
    ON jarvis_insights_schemav1.signal_routes(created_at DESC);
