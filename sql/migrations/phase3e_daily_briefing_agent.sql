-- Phase 3E — Daily Briefing Agent V1 Migration
-- File: sql/migrations/phase3e_daily_briefing_agent.sql
--
-- Creates the daily_briefings table for storing structured AI morning summaries.
-- Schema: jarvis_insights_schemav1

CREATE TABLE IF NOT EXISTS jarvis_insights_schemav1.daily_briefings (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    briefing_date          DATE NOT NULL DEFAULT CURRENT_DATE,
    generated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    overall_priority       TEXT NOT NULL DEFAULT 'MEDIUM',
    title                  TEXT NOT NULL,
    briefing_json          JSONB NOT NULL,
    llm_provider           TEXT NOT NULL,
    llm_model              TEXT NOT NULL,
    generation_duration_ms INTEGER NOT NULL DEFAULT 0,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Performance Index for retrieving latest daily briefings
CREATE INDEX IF NOT EXISTS idx_daily_briefings_date 
    ON jarvis_insights_schemav1.daily_briefings(briefing_date DESC, generated_at DESC);
