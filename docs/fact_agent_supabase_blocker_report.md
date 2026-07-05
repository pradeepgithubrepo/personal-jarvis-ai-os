-- ==========================================
-- FACT AGENT V2 MIGRATION
-- ==========================================

-- STEP 1
-- Remove legacy columns

ALTER TABLE jarvis_insights_schema.facts
DROP COLUMN IF EXISTS entity;

ALTER TABLE jarvis_insights_schema.facts
DROP COLUMN IF EXISTS fact;

ALTER TABLE jarvis_insights_schema.facts
DROP COLUMN IF EXISTS source_signal_id;


-- STEP 2
-- Add Fact Agent V2 columns

ALTER TABLE jarvis_insights_schema.facts
ADD COLUMN IF NOT EXISTS fact_type VARCHAR(50);

ALTER TABLE jarvis_insights_schema.facts
ADD COLUMN IF NOT EXISTS fact_value JSONB;

ALTER TABLE jarvis_insights_schema.facts
ADD COLUMN IF NOT EXISTS status VARCHAR(30)
DEFAULT 'UNCONFIRMED';

ALTER TABLE jarvis_insights_schema.facts
ADD COLUMN IF NOT EXISTS owner_agent VARCHAR(50);

ALTER TABLE jarvis_insights_schema.facts
ADD COLUMN IF NOT EXISTS source_agent VARCHAR(50);

ALTER TABLE jarvis_insights_schema.facts
ADD COLUMN IF NOT EXISTS source_type VARCHAR(30)
DEFAULT 'OBSERVED';

ALTER TABLE jarvis_insights_schema.facts
ADD COLUMN IF NOT EXISTS first_seen TIMESTAMPTZ
DEFAULT NOW();

ALTER TABLE jarvis_insights_schema.facts
ADD COLUMN IF NOT EXISTS last_seen TIMESTAMPTZ
DEFAULT NOW();

ALTER TABLE jarvis_insights_schema.facts
ADD COLUMN IF NOT EXISTS evidence JSONB;

ALTER TABLE jarvis_insights_schema.facts
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ
DEFAULT NOW();


-- STEP 3
-- Create Fact Relationships

CREATE TABLE IF NOT EXISTS jarvis_insights_schema.fact_relationships (

    id BIGSERIAL PRIMARY KEY,

    subject_id UUID NOT NULL,

    predicate VARCHAR(50) NOT NULL,

    object_id UUID NOT NULL,

    confidence NUMERIC DEFAULT 0.5,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_fact_relationship_subject
        FOREIGN KEY(subject_id)
        REFERENCES jarvis_insights_schema.facts(fact_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_fact_relationship_object
        FOREIGN KEY(object_id)
        REFERENCES jarvis_insights_schema.facts(fact_id)
        ON DELETE CASCADE
);


-- STEP 4
-- Indexes

CREATE INDEX IF NOT EXISTS idx_facts_type
ON jarvis_insights_schema.facts(fact_type);

CREATE INDEX IF NOT EXISTS idx_fact_relationships_subject
ON jarvis_insights_schema.fact_relationships(subject_id);

CREATE INDEX IF NOT EXISTS idx_fact_relationships_object
ON jarvis_insights_schema.fact_relationships(object_id);


-- STEP 5
-- Refresh statistics

ANALYZE jarvis_insights_schema.facts;

ANALYZE jarvis_insights_schema.fact_relationships;