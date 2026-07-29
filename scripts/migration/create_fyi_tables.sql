-- scripts/migration/create_fyi_tables.sql
-- Ingestion destination for fyi_agent routes.

-- Create processing path ENUM
CREATE TYPE jarvis_insights_schemav1.fyi_processing_path AS ENUM (
    'STRUCTURED',
    'RULE_BASED',
    'LLM_GEMINI',
    'LLM_CEREBRAS',
    'LLM_LOCAL'
);

-- Create information_items table
CREATE TABLE jarvis_insights_schemav1.information_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    route_id UUID REFERENCES jarvis_insights_schemav1.signal_routes(id) ON DELETE SET NULL,
    processing_path jarvis_insights_schemav1.fyi_processing_path NOT NULL,
    category VARCHAR(50) NOT NULL CHECK (
        category IN ('TRAVEL', 'ORDER_TRACKING', 'SECURITY_ALERT', 'FAMILY_SCHOOL', 'UTILITY_INFO', 'GENERAL')
    ),
    title VARCHAR(255) NOT NULL,
    summary TEXT NOT NULL,
    raw_payload JSONB NOT NULL,
    event_datetime TIMESTAMP WITH TIME ZONE NULL,
    timeline_group_id VARCHAR(100) NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Indexes for rapid timeline collation and daily briefs
CREATE INDEX idx_info_items_timeline ON jarvis_insights_schemav1.information_items(timeline_group_id, event_datetime ASC);
CREATE INDEX idx_info_items_path ON jarvis_insights_schemav1.information_items(processing_path);
CREATE INDEX idx_info_items_created ON jarvis_insights_schemav1.information_items(created_at DESC);
